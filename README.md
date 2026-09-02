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
