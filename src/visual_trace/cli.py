import argparse
import sys
from pathlib import Path

import manim as mn

from visual_trace.scenes.base import Animation
from visual_trace.utils.loader import load_target

QUALITIES = ["low_quality", "medium_quality", "high_quality", "production_quality"]


def main():
    parser = argparse.ArgumentParser(
        description="Render a Python function's execution as an animated video."
    )
    parser.add_argument("script", type=Path, help="a script defining main() -> (func, args)")
    parser.add_argument(
        "--quality",
        choices=QUALITIES,
        default="low_quality",
        help="render quality (default: low_quality, 854x480 -- the code listing "
        "is drawn small and is hard to read below medium)",
    )
    parser.add_argument(
        "--no-rewrite",
        action="store_true",
        help="take the script's `list` and `dict` literally instead of "
        "rewriting them into animated containers",
    )
    args = parser.parse_args()

    if not args.script.is_file():
        print(f"Error: File {args.script} does not exist.")
        sys.exit(1)

    try:
        func, func_args = load_target(args.script, not args.no_rewrite)
    except AttributeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    # Configure Manim
    mn.config.quality = args.quality
    # Manim's finish() deletes the oldest partial movie files once the
    # directory passes max_files_cached (default 100). Frame extraction
    # reads every path in the list file, so eviction would break a long
    # render after it had already been paid for.
    mn.config.max_files_cached = -1
    mn.config.media_dir = "./media"
    mn.config.output_file = args.script.stem

    # Generate Animation
    scene = Animation(func=func, args=func_args)
    scene.render()

    print(f"Animation exported to {scene.renderer.file_writer.movie_file_path}")


if __name__ == "__main__":
    main()
