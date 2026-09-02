import types
from importlib import util
from pathlib import Path


def load_script(script_path: Path) -> types.ModuleType:
    """Dynamically load a Python script and return its namespace."""
    spec = util.spec_from_file_location("user_script", script_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_target(script_path: Path):
    """Load a script and return its ``(func, args)`` pair.

    Every example script defines a ``main()`` that hands back the function to
    trace along with the arguments to trace it with.
    """
    script = load_script(script_path)
    if not hasattr(script, "main"):
        raise AttributeError("The script must define a `main()` function.")
    return script.main()
