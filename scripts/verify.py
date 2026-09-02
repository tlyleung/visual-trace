"""Render an example and bring the result back as something checkable.

Manim emits an MP4, which is useless to an agent that cannot watch video. This
turns a render into two things that can actually be inspected:

  * a JSONL trace carrying per-step locals and geometry assertions, and
  * a captioned contact sheet built from the settled frame of each step.

Layered on purpose -- read the invariant table first, and only spend image
context on frames when the numbers are inconclusive.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERIFY_DIR = REPO / "media" / "verify"
BASELINE_DIR = VERIFY_DIR / "_baselines"
CAPTION_BAR = 40


def sh(*cmd) -> subprocess.CompletedProcess:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cmd[0]} failed ({proc.returncode}):\n{proc.stderr.strip()[:2000]}"
        )
    return proc


#
# Render
#


def render(script_path: Path, out_dir: Path, width: int, height: int, fps: int):
    import manim as mn

    from visual_trace.scenes.base import Animation
    from visual_trace.utils.loader import load_target
    from visual_trace.utils.trace_log import ENV_VAR

    func, args = load_target(script_path)
    os.environ[ENV_VAR] = str(out_dir / "trace.jsonl")

    mn.config.verbosity = "ERROR"
    mn.config.progress_bar = "none"
    mn.config.quality = "low_quality"
    # Resolution and frame rate are independent of the quality preset, so we buy
    # spatial detail (needed to read the code listing) without paying for frames.
    mn.config.pixel_width = width
    mn.config.pixel_height = height
    mn.config.frame_rate = fps
    # Manim's finish() deletes the oldest partial movie files once the
    # directory passes max_files_cached (default 100). Frame extraction
    # reads every path in the list file, so eviction would break a long
    # render after it had already been paid for.
    mn.config.max_files_cached = -1
    mn.config.media_dir = str(out_dir / "manim")
    mn.config.output_file = script_path.stem

    scene = Animation(func=func, args=args)
    scene.render()
    return scene


def partial_movies(scene) -> list[Path]:
    """Ordered partial movie files for THIS render.

    Read from the list file Manim writes, never by globbing the directory --
    partials are hash-named and cached, so the directory accumulates stale files
    from every previous render and a glob silently mixes them in.
    """
    directory = Path(scene.renderer.file_writer.partial_movie_directory)
    listing = directory / "partial_movie_file_list.txt"
    files = []
    for raw in listing.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        path = raw.split("'", 1)[1].rsplit("'", 1)[0]  # file 'file:/abs/path.mp4'
        files.append(Path(path.removeprefix("file:")))
    return files


#
# Frames
#


def extract_frames(movie: Path, dest_dir: Path, every: bool = True) -> list[Path]:
    """Dump frames of one animation step, in order.

    `every=False` writes only the settled last frame, which is all the default
    sheet and the baselines ever read -- decoding is unavoidable but encoding
    eight 1080p PNGs per step when one is wanted is not.

    Deliberately not `-sseof`: on the 8-frame clips Manim produces it writes
    nothing and still exits 0, which is precisely the silent failure this tool
    exists to catch. `reverse` buffers the clip and takes its true last frame.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    if every:
        sh("ffmpeg", "-y", "-v", "error", "-i", movie, "-vsync", "0",
           dest_dir / "f_%03d.png")
    else:
        sh("ffmpeg", "-y", "-v", "error", "-i", movie, "-vf", "reverse",
           "-frames:v", "1", "-update", "1", dest_dir / "f_001.png")
    frames = sorted(dest_dir.glob("f_*.png"))
    if not frames:
        raise RuntimeError(f"no frames extracted from {movie}")
    return frames


def pick(frames: list[Path], count: int) -> list[Path]:
    """The settled last frame, or `count` evenly spaced frames across the step."""
    if count <= 1 or len(frames) <= 1:
        return [frames[-1]]
    step = (len(frames) - 1) / (count - 1)
    return [frames[min(len(frames) - 1, round(i * step))] for i in range(count)]


# Gravity, not an offset: ImageMagick reads "+50%+0" as +50 *pixels*, so a
# percentage offset silently crops the wrong half.
ROIS = {"code": "West", "table": "East"}


def caption(src: Path, dest: Path, text: str, tile_width: int, roi: str | None) -> None:
    crop = (
        ["-gravity", ROIS[roi], "-crop", "50%x100%+0+0", "+repage"] if roi else []
    )
    sh("convert", src, *crop,
       "-resize", f"{tile_width}x",
       "-background", "#101014", "-gravity", "North", "-splice", f"0x{CAPTION_BAR}",
       "-fill", "#f0f0f0", "-pointsize", "20", "-annotate", "+0+10", text,
       "-bordercolor", "#3a3a44", "-border", "2", dest)
    if not dest.exists():
        raise RuntimeError(f"caption produced nothing for {src}")


def auto_tile(count: int) -> str:
    """Keep sheets roughly landscape; very tall sheets just get downsampled."""
    if count <= 2:
        return f"{count}x"
    return "3x" if count > 8 else "2x"


def build_sheet(
    frames: list[Path],
    labels: list[str],
    dest: Path,
    tiles_dir: Path,
    prefix: str,
    tile: str | None,
    tile_width: int,
    roi: str | None,
    what: str = "sheet",
) -> None:
    """Caption each frame and tile them. Used for both the sheet and filmstrips."""
    tiles = []
    for index, (frame, text) in enumerate(zip(frames, labels)):
        tile_path = tiles_dir / f"{prefix}{index:03d}.png"
        caption(frame, tile_path, text, tile_width, roi)
        tiles.append(tile_path)
    if tiles:
        montage(tiles, dest, tile, what)


def montage(frames: list[Path], dest: Path, tile: str | None, label: str = "sheet") -> None:
    sh("montage", *frames, "-tile", tile or auto_tile(len(frames)),
       "-geometry", "+8+8", "-background", "#26262e", dest)
    if not dest.exists():
        raise RuntimeError("montage produced nothing")
    dims = sh("identify", "-format", "%wx%h", dest).stdout.strip()
    w, h = (int(v) for v in dims.split("x"))
    print(f"{label} {dims}")
    if max(w, h) > 4000 or h > 3 * w:
        print("  warning: sheet is awkwardly shaped and will be downsampled on "
              "read -- narrow it with --steps or change --tile")


def make_gif(movie: Path, dest: Path, width: int = 720) -> None:
    sh("ffmpeg", "-y", "-v", "error", "-i", movie, "-vf",
       f"scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
       dest)


#
# Reporting
#


def parse_steps(spec: str | None, total: int) -> set[int]:
    if not spec:
        return set(range(total))
    lo, _, hi = spec.partition("-")
    return set(range(int(lo), int(hi or lo) + 1)) & set(range(total))


def load_trace(out_dir: Path) -> list[dict]:
    path = out_dir / "trace.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


STABLE = ("code", "label:", "struct:")


DRIFT_TOL = 0.02


def drift(records: list[dict]) -> list[dict]:
    """Landmarks that moved between one settled step and the next.

    Every probe invariant judges a single step in isolation, so a frame can be
    correct on its own and still jump from the one before it. Motion bugs live
    exactly there: a mid-play fly-in ends in the right place, and a layout
    reflow leaves every frame internally consistent. Only comparing steps sees
    them.

    The highlight and its target line are excluded -- moving is their job.
    """
    found = []
    for previous, current in zip(records, records[1:]):
        before = previous.get("geometry", {})
        for key, box in current.get("geometry", {}).items():
            if not key.startswith(STABLE) or key not in before:
                continue
            dx = box["left"] - before[key]["left"]
            dy = box["top"] - before[key]["top"]
            if abs(dx) > DRIFT_TOL or abs(dy) > DRIFT_TOL:
                found.append(
                    {"step": current["step"], "what": key, "dx": dx, "dy": dy}
                )
    return found


def report_drift(records: list[dict]) -> int:
    moved = drift(records)
    print("\nlandmark drift between steps")
    print("-" * 78)
    if not moved:
        print("  none -- nothing that should hold still moved")
        return 0
    for item in moved:
        print(f"  step {item['step']:>2}  {item['what']:<16} "
              f"moved dx={item['dx']:+.3f} dy={item['dy']:+.3f}")
    return len(moved)


def report(records: list[dict]) -> int:
    failures = 0
    print(f"\n{'step':>4} {'line':>4} {'c/a':>6}  source")
    print("-" * 78)
    tally: dict[str, list[int]] = {}
    for rec in records:
        print(f"{rec['step']:>4} {rec['lineno']:>4} "
              f"{rec['content']:>2}/{rec['applied']:<3}  {rec['src'].strip()[:56]}")
        for check in rec.get("checks", []):
            slot = tally.setdefault(check["name"], [0, 0])
            slot[0] += 1
            if check["ok"] is True:
                continue
            slot[1] += 1
            failures += 1
            mark = "FAIL" if check["ok"] is False else "ERR "
            print(f"       {mark} {check['name']}: {check['detail']}")
    print("-" * 78)
    for name, (total, bad) in sorted(tally.items()):
        print(f"  {'FAIL' if bad else ' ok '}  {name:<28} "
              f"{f'{bad}/{total} steps' if bad else f'{total} steps'}")
    return failures


def diff_against(baseline: Path, frames: list[Path], out_dir: Path) -> None:
    saved = sorted(baseline.glob("*.png"))
    if not saved:
        print(f"\nno baseline frames in {baseline}")
        return
    print(f"\npixel diff vs baseline '{baseline.name}':")
    dest = out_dir / "diff"
    dest.mkdir(exist_ok=True)
    for i, current in enumerate(frames):
        if i >= len(saved):
            print(f"  step {i}: no baseline frame (baseline is shorter)")
            continue
        proc = subprocess.run(
            ["compare", "-metric", "AE", str(saved[i]), str(current),
             str(dest / f"{i:03d}.png")],
            capture_output=True, text=True,
        )
        changed = proc.stderr.strip().split()[0] if proc.stderr.strip() else "?"
        marker = "  " if changed in ("0", "?") else "->"
        print(f"  {marker} step {i}: {changed} pixels differ")
    print(f"  heatmaps: {dest}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("script", type=Path)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=8)
    ap.add_argument("--tile", help="montage tiling, e.g. 2x; default adapts to count")
    ap.add_argument("--tile-width", type=int, default=760)
    ap.add_argument("--dense", type=int, default=1, metavar="N",
                    help="N frames per step instead of the settled frame only")
    ap.add_argument("--step", type=int, metavar="K",
                    help="expand step K into a full-resolution filmstrip")
    ap.add_argument("--steps", metavar="K-M",
                    help="only sheet these steps, e.g. 2 or 1-3")
    ap.add_argument("--roi", choices=sorted(ROIS), help="crop to one panel")
    ap.add_argument("--diff", metavar="NAME", help="pixel-diff against a saved baseline")
    ap.add_argument("--save-baseline", metavar="NAME")
    ap.add_argument("--gif", action="store_true")
    args = ap.parse_args()

    for tool in ("ffmpeg", "convert", "montage", "compare"):
        if shutil.which(tool) is None:
            print(f"error: {tool} not found on PATH")
            return 2

    script_path = args.script.resolve()
    out_dir = VERIFY_DIR / script_path.stem
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    scene = render(script_path, out_dir, args.width, args.height, args.fps)
    records = load_trace(out_dir)
    movies = partial_movies(scene)

    # A step that queued nothing never reaches scene.play() and so produces no
    # partial file; only played steps consume one, in order.
    # A step plays once to draw the previous line's effects and once to move
    # the highlight, so it owns one or two partials. Walk them in order rather
    # than assuming one apiece.
    played = []
    offset = 0
    for rec in records:
        count = rec.get("plays", 0)
        if count:
            played.append((rec, movies[offset:offset + count]))
            offset += count
    wanted = parse_steps(args.steps, len(played))
    print(f"\n{len(records)} steps ({len(played)} animated), "
          f"{offset} plays, {len(movies)} partial movie files")
    if len(movies) < offset:
        print("warning: fewer partial files than recorded plays -- mapping is suspect")

    raw_dir = out_dir / "raw"
    tiles_dir = out_dir / "frames"
    tiles_dir.mkdir()
    settled: list[Path] = []
    sheet_frames: list[Path] = []
    sheet_labels: list[str] = []

    for i, (rec, step_movies) in enumerate(played):
        if not step_movies:
            break
        # Only the steps actually being expanded need every frame.
        every = i == args.step or (args.dense > 1 and i in wanted)
        frames = []
        for j, movie in enumerate(step_movies):
            frames.extend(extract_frames(movie, raw_dir / f"{i:03d}_{j}", every))
        # Every step contributes its settled frame, so baselines and diffs stay
        # comparable even when --steps narrows what gets drawn onto the sheet.
        settled.append(frames[-1])
        if i not in wanted:
            continue
        label = f"step {rec['step']}  L{rec['lineno']}  {rec['src'].strip()[:52]}"
        chosen = pick(frames, args.dense)
        for j, frame in enumerate(chosen):
            sheet_frames.append(frame)
            sheet_labels.append(
                label + (f"   [{j + 1}/{len(chosen)}]" if len(chosen) > 1 else "")
            )

    sheet = out_dir / "sheet.png"
    build_sheet(sheet_frames, sheet_labels, sheet, tiles_dir, "",
                args.tile, args.tile_width, args.roi)

    if args.step is not None:
        k = args.step
        if not (0 <= k < len(played)):
            print(f"error: --step {k} out of range (0..{len(played) - 1})")
        else:
            frames = [f for d in sorted(raw_dir.glob(f"{k:03d}_*"))
                      for f in sorted(d.glob("f_*.png"))]
            build_sheet(
                frames,
                [f"step {k} frame {j + 1}/{len(frames)}" for j in range(len(frames))],
                out_dir / f"step_{k}.png", tiles_dir, "strip_", "4x",
                args.tile_width, args.roi, what="filmstrip",
            )
            print(f"\nfilmstrip: {out_dir / f'step_{k}.png'}")

    if args.save_baseline:
        dest = BASELINE_DIR / args.save_baseline
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for i, frame in enumerate(settled):
            shutil.copy(frame, dest / f"{i:03d}.png")
        print(f"\nbaseline '{args.save_baseline}' saved: {len(settled)} frames")

    if args.diff:
        diff_against(BASELINE_DIR / args.diff, settled, out_dir)

    if args.gif:
        gif = out_dir / f"{script_path.stem}.gif"
        make_gif(Path(scene.renderer.file_writer.movie_file_path), gif)
        print(f"\ngif:    {gif}")

    failures = report(records)
    failures += report_drift(records)
    print(f"\nsheet:  {sheet}")
    print(f"trace:  {out_dir / 'trace.jsonl'}")
    print(f"video:  {scene.renderer.file_writer.movie_file_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
