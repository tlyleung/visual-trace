# visual-trace

Renders a Python function as a Manim video: a highlight bar walks down the source
listing on the left while a variables table updates on the right.

```bash
uv run visual-trace examples/max_sub_array.py     # render
uv run scripts/verify.py examples/two_sum.py      # render + check
```

## How it works

`visual_trace/cli.py` loads a user script that must define `main() -> (func, args)`,
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

The interesting design: `data_structures/List` and `Dict` pair a builtin
container with a Manim mobject and override its methods so ordinary use has a
visual side effect — `Dict.__getitem__` highlights a cell just because you indexed
it. `utils/table.py:build_table` drains those queues into the scene each step.
The animation is not scripted; it falls out of the algorithm's own data access
pattern.

Every container keeps its drawn cells in `mobject.items` and an empty-state
outline in `mobject.placeholder`, so nothing else parented to the mobject is
mistaken for a cell. An empty container must draw *something*: drawing nothing is
indistinguishable from a rendering failure, and it hid real logic — searching an
empty dict animated nothing at all.

The variables table reserves a `return` row from the first frame, filled in by
`flush`. Reserving it keeps the row set stable so nothing shifts at the end.

Every overridden container method reduces to one of five primitives on
`Animated` — `_light`, `_sweep`, `_write`, `_insert_cell`, `_remove_cell` — plus
`_relayout`, which sends every cell to its slot after a structural change.
Subclasses describe their cell shape with `SLOTS` and `VALUE_SLOT` and otherwise
just wire methods to those. Adding a method should not mean designing an
animation.

**Plain `list` and `dict` are rewritten before the module runs.**
`utils/transform.py` replaces literals, comprehensions and constructor calls with
`List`/`Dict`, and `utils/loader.py` compiles the result **against the original
filename, never through `ast.unparse`**. Node locations survive, so
`inspect.getsource` still reads the user's file and `frame.f_lineno` still points
at the line they wrote — the code panel and the tracer's line arithmetic know
nothing about any of it. `List` and `Dict` are seeded into the exec globals
rather than injected as an import node, which is the one change that could
disturb that numbering.

The rewriter never visits bare `Name` nodes, which is what keeps
`isinstance(x, list)` correct — `List` is a subclass, so rewriting the second
argument would narrow the test. There is no guard for this; the property comes
from the design, and `tests/test_transform.py` fails if a `visit_Name` is ever
added.

**Nothing is inherited usefully.** `list` and `dict` methods are pure C on the
internal array and never route through a Python-level override — overriding
`__setitem__` does not make `sort()` animate. The only exceptions are external
consumers: `sorted(s)`/`list(s)` go through `__iter__`, and `dict(s)`/`d.copy()`
through `__getitem__`. Any method left inherited silently desyncs the drawing
from the data, which is what `cell_values_match` exists to catch.

Two are left inherited on purpose:

- **`__len__`** is O(1) and never reads the elements, so animating it would teach
  that it scans. It is also called by `probe.cell_count_matches` twice a step, so
  an override would have the verification tool corrupt what it measures.
- **`__eq__`, `__lt__` and friends** are full scans whose animation would be
  noise rather than signal.

`data_structures/base.py:Animated` is the contract they share, and is what a new
structure (Stack, Queue, Tree, Graph) should be built on. It owns `mobject`, the
two queues, and `reset()`; the scene tests `isinstance(v, Animated)` rather than
guessing at attributes. Read its docstring before adding one — the positioning
rule in there is not obvious and a single-step test will not catch getting it
wrong.

`pending_operations` is the subtle part. Additions go into `mobject.items`
inline, because a structure whose group is still empty when the table lays out
gets arranged as nothing and its contents then materialise at the origin. Only
*removals* are deferred: a cell has to stay parented long enough for its fade to
be built against it. `build_table` runs the deferred work immediately before
laying out.

`refresh_table` swaps the whole table mobject in rather than `become`-ing the old
one onto the new. `become` aligns families by padding, which strands zero-area
points at the origin when a cell empties and silently corrupts every bounding box
containing them.

**Each traced step plays twice.** `sys.settrace` fires a `line` event *before*
the line runs, so a line's animations only reach the tracer at the following
event. The tracer therefore draws the previous line's effects while the highlight
is still on that line, and only then advances the highlight. Doing both in one
`play` credits the effect to the wrong line.

Because harvesting happens one event late, the final line has nobody to collect
its animations; `tracing.flush` draws them after the run and records itself as a
step so the frame reaches the contact sheet.

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
filmstrip of one step, `--diff NAME` for a pixel diff against a saved baseline, and `--gif` for a
small looping GIF of the whole render.

Everything lands in `media/verify/<example>/`, which is gitignored.

### Working test-first

There are two tiers, and a change should be driven by the fastest one that can
express it.

```bash
uv run pytest tests/ -q                              # ~1s, pure geometry and state
uv run scripts/verify.py examples/two_sum.py         # ~8s, real render + probe
```

`tests/` covers what can be checked without rendering, using a `StubScene` that
supplies only the handful of attributes the code under test touches. The probe
covers the rest. Add to `tests/` when you can; fall back to a probe invariant
when the property only exists in a rendered frame.

The loop is **red, confirm, green, mutate**:

1. Write the failing check first.
2. **Read the failure text and confirm it fails for the reason you expect.** Red
   is not evidence the test is right.
3. Fix until green.
4. **Break the code a second, different way and confirm it goes red again.**

Step 4 is not optional here, because in this codebase a check that cannot fail
looks exactly like a check that passes. Three real cases, all caught only by
mutating:

- `highlight_covers_line` was red for two commits over a genuine bug, but was
  itself **unsatisfiable** — consecutive `code_lines` boxes overlap by ~0.099, so
  no band could ever contain one without covering its neighbours.
- The first table-layout test compared a value against the bounds of the table
  that **owns** it. Draining the deferred work inflated the parent to swallow the
  child, so it passed vacuously. Never assert a child against its parent's bounds;
  use a sibling, such as the row's label.
- The second version passed because an **empty** mobject has a degenerate bbox at
  the origin, which is trivially "inside" anything. Assert
  `family_members_with_points()` before asserting position.

Related trap: use at least two table rows in a layout test. A single row sits at
y=0, which is exactly where a mislaid mobject lands, so the bug hides.

### Motion bugs need a cross-step check

Every probe invariant judges one settled step in isolation, so a frame can be
correct on its own and still jump from the one before it. `verify.py` prints a
**landmark drift** section comparing consecutive steps: the code panel, each row
label and each structure must not move. The highlight and its target line are
excluded, since moving is their job.

Three reported artifacts -- a cell flying in from the right, and the panel
shifting at two different steps -- were all invisible to the settled-frame sheet
and to every invariant, and the drift table located all three on the first run.
If a rendering complaint is about *movement*, read that table before anything else.

### Things that will bite you

- **Instrumentation is env-gated and must stay inert.** `VISUAL_TRACE_LOG` turns
  on the log and probe. Without it, renders are byte-identical — verified by MD5
  against a pre-instrumentation render. Keep it that way.
- **A step owns one or two partials, not one.** It plays once to draw the
  previous line's effects and once to move the highlight, and skips the first
  when there is nothing to draw. The trace log's `plays` field carries the count;
  `verify.py` walks the partials in order against it rather than assuming.
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
- **Manim bounding boxes count anything with points, visible or not**, and this
  has bitten four times: blank code lines collapse to the origin, a `List` whose
  group is still empty reports zero extent there, `become` padding strands
  zero-area points there, and `MobjectTable` draws its grid with
  `stroke_width=0` lines running far wider than any cell. Every one made a
  correct frame look wrong. Use `probe.visible_range`, which counts only what
  actually puts ink on the frame.
- **`.animate` snapshots its target when the builder is created**, not when it
  plays. Cells are queued while user code runs and only positioned when the
  table is laid out, so an animation built with `.animate` will drag its mobject
  back to wherever the previous table had it. `Animated.queue` takes an already
  built animation and rejects anything else; `.animate` goes through
  `Animated.queue_deferred` with one of the builders in `data_structures/base.py`,
  which the table realises once every cell is in its final place.
- **New cells are built at the world origin**, so anything created after a layout
  must be anchored to something already drawn — the previous cell, or the
  placeholder when the container is empty. Forget this and the cell appears
  wherever the container used to be.
- **Row positions are pinned to a fixed pitch** (`table.ROW_PITCH`). MobjectTable
  sizes each row to its tallest cell, so a value going from text to a drawn
  structure resized its row and the centred table shifted every other row with
  it. If you add a structure taller than the pitch, the drift table will say so.
- Only the steps being expanded have every frame extracted; the rest keep just
  the settled one. `--dense`/`--step` opt back in.
- Probe reads must stay side-effect free. `repr()` on `Dict` is safe (it goes
  through the C implementation, not the overridden `items`/`keys`/`values`), but
  anything calling those methods would push spurious animations.

### Known-failing invariants

None. Every invariant is green on all six examples, so any failure is a
regression you just introduced, not background noise. Keep it that way: if you
add an invariant that cannot pass yet, record it here with the reason.

An invariant with no subject is silent, not passing -- read the per-invariant
step counts, not just the absence of failures.

### Known limits

- The variables panel fits about **eight cells** across (4.117 units of value
  column at `CELL_SIZE`). A longer container is drawn past the frame edge and
  clipped; `within_frame` catches it. Past `MAX_DRAWN_CELLS` a container is not
  drawn at all and shows as text -- a cell costs a Manim mobject, and the AST
  rewriter makes it easy to construct a thousand of them by accident. The fix belongs in `build_table` -- scale an
  oversized structure to fit its cell -- so it covers whatever structure comes
  next as well. `examples/max_sub_array.py` is sized to fit rather than working
  around it.
- One structure bound to two locals (`arr = nums`) puts a single mobject into two
  table cells. Manim does not reparent, so the last placement wins and the other
  row renders empty for the rest of the video.
- The rewriter only reaches the traced module. A helper imported from elsewhere
  keeps its plain containers, and so does anything returned by `sorted`,
  `json.loads` or a third-party call.
