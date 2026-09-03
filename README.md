# Visual Trace

Visualize Python traces in an animated video.

## Installation

```bash
uv sync
```

## Usage

```bash
uv run scripts/cli.py examples/max_sub_array.py
```

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
| [`dict_operations`](examples/dict_operations.py) | values(), clear() |

## Implementation

See [CLAUDE.md](CLAUDE.md) for how tracing, the animation queue, and the
verification loop fit together.

## Verifying changes

```bash
uv run pytest tests/ -q                       # fast geometry checks
uv run scripts/verify.py examples/two_sum.py   # full render + probe
```

Renders an example and reports per-step geometry assertions plus a contact sheet
in `media/verify/`, so a change can be checked without watching the video.

## License

This project is licensed under the GNU General Public License v3.0 License. See the [LICENSE](LICENSE) file for details.
