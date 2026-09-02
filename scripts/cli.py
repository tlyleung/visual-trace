import sys
import types
from importlib import util
from pathlib import Path

import manim as mn

from visual_trace.scenes.base import Animation


def load_script(script_path: Path) -> types.ModuleType:
    """Dynamically load a Python script and return its namespace."""
    spec = util.spec_from_file_location("user_script", script_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) != 2:
        print("Usage: visual-trace <python_file>")
        sys.exit(1)

    script_path = sys.argv[1]
    if not Path(script_path).is_file():
        print(f"Error: File {script_path} does not exist.")
        sys.exit(1)

    script = load_script(script_path)

    # Extract function and arguments
    if not hasattr(script, "main"):
        print("Error: The script must define a `main()` function.")
        sys.exit(1)

    func, args = script.main()

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
