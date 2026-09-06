# Visual Trace

Render a Python function's execution as an animated video: a highlight walks the
source listing while the variables update alongside it.

## Installation

```bash
uv sync
```

Manim ships its own rendering wheels, but shells out to **ffmpeg**, which you
need on your `PATH`:

```bash
ffmpeg -version    # apt install ffmpeg / brew install ffmpeg
```

## Usage

A script to be traced defines `main()`, returning the function to trace and the
arguments to trace it with. Write ordinary Python:

```python
def two_sum(nums, target):
    seen = {}
    for i in range(len(nums)):
        num = nums[i]
        if target - num in seen:
            return seen[target - num], i
        seen[num] = i


def main():
    return two_sum, ([2, 7, 11, 15], 9)
```

```bash
uv run visual-trace examples/two_sum.py
uv run visual-trace examples/two_sum.py --quality high_quality
```

The video lands in `media/videos/`. The default is 854x480, which is fine as a
smoke test but too small to read the code listing — use `--quality
high_quality` for anything you intend to watch.

## How your containers get animated

`list` and `dict` are rewritten into animated containers before your code runs,
so `[2, 7, 11, 15]` draws as a row of cells and `{}` as stacked key/value cells.
Indexing lights a cell, `in` sweeps the keys, a write transforms the label — the
animation falls out of your code's own data access rather than being scripted.

The rewrite happens on the syntax tree and is compiled against your original
file, so **the code panel shows exactly what you wrote**, not the rewrite, and
line numbers line up.

You can still name the containers directly if you prefer. Importing them is
not a conflict -- the rewrite seeds the same two objects into your module, so
your import simply rebinds them, and your plain literals are still rewritten
around it:

```python
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List

nums = List(2, 7, 11, 15)
```

Nothing in `examples/` needs to, so none of them do. Pass `--no-rewrite` to have
your `list` and `dict` taken literally instead.

### What the rewrite does not reach

- **Other modules.** Only the traced file is rewritten, so a helper imported from
  elsewhere keeps its plain containers and they render as text.
- **Containers built by something else.** `sorted(...)`, `json.loads(...)` and
  third-party returns are plain, and render as text.
- **Modules that use `list` or `dict` as a name of their own.** The whole file is
  left alone rather than guessing at scope.
- **Anything over 32 elements** renders as text: each cell costs a Manim
  mobject, and the panel only fits about eight across anyway.

## Data Structures

| Data Structure | Implemented | Link                                             |
| -------------- | ----------- | ------------------------------------------------ |
| List           | ✅          | [List](src/visual_trace/data_structures/list.py) |
| Dict           | ✅          | [Dict](src/visual_trace/data_structures/dict.py) |
| Stack          | ❌          |                                                  |
| Queue          | ❌          |                                                  |
| Tree           | ❌          |                                                  |
| Graph          | ❌          |                                                  |

Reads, writes, insertions and removals all animate. Anything left inherited from
the builtin would desync the drawing from the data, so `cell_values_match` fails
the render rather than letting it show stale values.

## Examples

| Example | Shows |
| ------- | ----- |
| [`two_sum`](examples/two_sum.py) | dict lookups, membership sweeps |
| [`max_sub_array`](examples/max_sub_array.py) | iterating a list |
| [`bubble_sort`](examples/bubble_sort.py) | in-place swaps |
| [`binary_search`](examples/binary_search.py) | indexed reads |
| [`list_operations`](examples/list_operations.py) | appends |
| [`dict_operations`](examples/dict_operations.py) | `values()`, `clear()` |

## Known limits

- The variables panel fits about **eight cells** across. A longer container is
  drawn past the right edge of the frame and clipped, and past 32 elements it is
  shown as text instead.
- A traced function runs **twice** — once to collect variable names, once to
  animate — so it should not have side effects outside its arguments.
- Only integer indices animate; slice assignment redraws rather than animating
  the change.

## Contributing

```bash
uv run pytest tests/ -q                        # fast geometry checks
uv run scripts/verify.py examples/two_sum.py   # full render + probe
```

`verify.py` renders an example and reports per-step geometry assertions, a
landmark-drift check and a captioned contact sheet in `media/verify/`, so a
change can be reviewed without watching the video.
[CLAUDE.md](CLAUDE.md) covers how tracing, the animation queue and that loop fit
together.

## License

This project is licensed under the GNU General Public License v3.0. See the
[LICENSE](LICENSE) file for details.
