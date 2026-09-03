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
arguments to trace it with:

```python
from visual_trace.data_structures.list import List


def max_sub_array(nums: List[int]) -> int:
    ans = float("-inf")
    curr = float("-inf")
    for num in nums:
        curr = max(curr + num, num)
        ans = max(ans, curr)
    return ans


def main():
    return max_sub_array, (List(-2, 1, -3, 4, -1, 2, 1, -5),)
```

```bash
uv run visual-trace examples/max_sub_array.py
uv run visual-trace examples/max_sub_array.py --quality high_quality
```

The video lands in `media/videos/`. The default is 854x480, which is fine as a
smoke test but too small to read the code listing — use `--quality
high_quality` for anything you intend to watch.

## Use `List` and `Dict`, not `list` and `dict`

This is the one thing to get right. `visual_trace`'s containers subclass the
builtins and override their methods so that ordinary use draws itself — indexing
lights a cell, `in` sweeps the keys, a write transforms the label. The animation
falls out of the algorithm's own data access rather than being scripted.

```python
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List

nums = List(2, 7, 11, 15)     # drawn as cells, and animates
seen = Dict(a=1)              # drawn as stacked key/value cells
```

**A plain `list` or `dict` still works, but is not animated.** It renders in the
variables panel as flat text, with no error and no warning — so if your array
shows up as `[2, 7, 11, 15]` instead of a row of boxes, this is why. Everything
else (ints, floats, strings, tuples) is expected to render as text.

Only these two containers exist today. Anything else you pass is shown as text.

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
  drawn past the right edge of the frame and clipped.
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
