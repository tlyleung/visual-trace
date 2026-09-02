# visual-trace

Renders a Python function as a Manim video: a highlight bar walks down the source
listing on the left while a variables table updates on the right.

```bash
uv run scripts/cli.py examples/max_sub_array.py   # render
uv run scripts/verify.py examples/two_sum.py      # render + check
```

## How it works

`scripts/cli.py` loads a user script that must define `main() -> (func, args)`,
then renders `scenes/base.py:Animation` over it.

`Animation.construct` runs the traced function **twice**:

1. **Pass 1** harvests the set of local variable names so the table has a stable
   row set for the whole video.
2. Arguments are rebuilt via `.reset()` to undo pass 1's mutations.
3. **Pass 2** emits the actual animation.

`utils/tracing.py` drives it with `sys.settrace`. `trace_func` is curried: it
returns a lambda that re-invokes itself with `func`/`scene`/`variables` bound, so
one function serves as both the global and per-frame trace. On each `line` event
inside the target it moves the highlight, rebuilds the table, plays the queued
animations, then drains `pending_operations`.

The interesting design: `data_structures/List` and `Dict` subclass `list`/`dict`
and carry a `.mobject` plus an `.animation_queue`. Overridden methods push Manim
animations as a **side effect** of ordinary use — `Dict.__getitem__` highlights a
cell just because you indexed it. `utils/table.py:create_table111` drains those
queues into the scene each step. The animation is not scripted; it falls out of
the algorithm's own data access pattern.

`pending_operations` is the subtle part: the *animation* is queued for this step,
but the mobject-tree mutation (`self.mobject.add(item)`) is deferred until after
`scene.play()` returns, so the tree does not change mid-animation.

## Verifying changes

An agent cannot watch an MP4, so `scripts/verify.py` turns a render into things
that can be inspected. Three tiers — **read the invariant table before spending
image context**.

```bash
uv run scripts/verify.py examples/list_operations.py
uv run scripts/verify.py examples/two_sum.py --steps 3-5 --roi table
uv run scripts/verify.py examples/list_operations.py --step 2 --dense 4
uv run scripts/verify.py examples/list_operations.py --save-baseline good
uv run scripts/verify.py examples/list_operations.py --diff good
```

| Tier | What it catches |
|---|---|
| Trace log (`trace.jsonl`) | Lines visited, locals, whether a step queued animations |
| Geometry probe (`utils/probe.py`) | Misalignment, overlap, off-screen, spacing — numerically |
| Contact sheet (`sheet.png`) | What geometry can't express |

Useful flags: `--steps K-M` to narrow the sheet, `--roi code|table` to crop to one
panel at full resolution, `--dense N` for N frames per step (timing bugs — a step
sampled only at its settled frame hides them), `--step K` for a full-res
filmstrip of one step, `--diff NAME` for a pixel diff against a saved baseline.

Everything lands in `media/verify/<example>/`, which is gitignored.

### Things that will bite you

- **Instrumentation is env-gated and must stay inert.** `VISUAL_TRACE_LOG` turns
  on the log and probe. Without it, renders are byte-identical — verified by MD5
  against a pre-instrumentation render. Keep it that way.
- **Never glob the partial-movie directory.** Partials are hash-named and cached,
  so it accumulates stale files from every previous render — there are ~99 in
  `media/videos/480p15/` against a 6-entry list. Parse
  `partial_movie_file_list.txt`, which `verify.py:partial_movies` does.
- **`ffmpeg -sseof` writes nothing on these clips and still exits 0.** Partials are
  ~8 frames; seeking from the end silently yields an empty output. `verify.py`
  dumps all frames and takes the last.
- **Renders are deterministic** — a `--diff` against an unchanged tree reports 0
  pixels on every step, so any non-zero diff is real signal.
- `verify.py` wipes its output directory each run, trading render caching for the
  guarantee that no stale artifact can leak into a result.
- **Resolution and frame rate are independent of the `quality` preset.** Verify
  renders at 1920x1080 @ 8fps: the code listing is drawn at `scale(0.5)` and is
  unreadable at 480p. Set `pixel_width`/`pixel_height`/`frame_rate` after `quality`.
- **Never position anything from `code.code_lines[i]` bounding boxes.** Manim
  renders leading indentation as zero-size `Dot`s, and when a blank line precedes
  a row those dots are parked at the *blank* row's y — so the row's box stretches
  across two rows (0.463 against a 0.253 norm). A blank line's own box collapses to
  the origin. Use the `code.line_numbers` ladder, which is uniform to 2e-03;
  `utils/highlight.row_center` does this.
- Probe reads must stay side-effect free. `repr()` on `Dict` is safe (it goes
  through the C implementation, not the overridden `items`/`keys`/`values`), but
  anything calling those methods would push spurious animations.

### Known-failing invariants

These fail on `master` today. They are pre-existing bugs, not regressions — treat
them as the background, and watch for *changes* to this list.

- `structures_inside_table` — fails at step 0 in both examples. `create_table111`
  puts `v.mobject` into a freshly built table and then `become`s the old one onto
  it; `become` copies points but the mobject stays parented to the discarded
  table, so it is left at its construction position near the origin.
- `table_rows_disjoint` — fails at step 0 of `two_sum`, same root cause.
- **One-step animation lag** (no invariant yet). `create_table111` reads
  `frame.f_locals` at the *start* of a line, so an append on line N is not drawn
  until step N+1. Visible in the log as `queued` attributed to the wrong line, and
  in the sheet as `nums` showing `[-1,0]` while `nums.append(1)` is highlighted.

Other latent bugs, unrelated to rendering: `tracing.py` stores
`variables[variable] = type(variable)` — the type of the *name string*, always
`str`; only the keys are used downstream, so it is harmless but misleading.
`utils/table.py:update_table` is dead code superseded by `create_table111`, and
`utils/transform.py` is an entirely commented-out AST approach that would have
rewritten `list` -> `List` automatically.
