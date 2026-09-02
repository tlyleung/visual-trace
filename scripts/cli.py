import sys
from pathlib import Path

import manim as mn

from visual_trace.scenes.base import Animation
from visual_trace.utils.loader import load_target


def main():
    if len(sys.argv) != 2:
        print("Usage: visual-trace <python_file>")
        sys.exit(1)

    script_path = sys.argv[1]
    if not Path(script_path).is_file():
        print(f"Error: File {script_path} does not exist.")
        sys.exit(1)

    try:
        func, args = load_target(Path(script_path))
    except AttributeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    # Configure Manim
    mn.config.quality = "low_quality"
    mn.config.media_dir = "./media"
    mn.config.output_file = Path(script_path).stem

    # Generate Animation
    scene = Animation(func=func, args=args)
    scene.render()

    print(f"Animation exported to {mn.config.output_file}")


if __name__ == "__main__":
    main()
