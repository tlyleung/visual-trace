import types
from pathlib import Path

from ..data_structures.dict import Dict
from ..data_structures.list import List
from .transform import rewrite


def load_script(script_path: Path, rewrite_containers: bool = True) -> types.ModuleType:
    """Load a Python script and return its namespace.

    Plain `list` and `dict` are rewritten into `List` and `Dict` so a user does
    not have to port their code to our types -- see `utils.transform`.

    `List` and `Dict` are seeded into the module namespace rather than injected
    as an import node, which would be the one change capable of disturbing the
    line numbers the code panel and tracer read straight from the file. A module
    that imports them itself simply rebinds the same objects.
    """
    source = script_path.read_text()
    module = types.ModuleType("user_script")
    module.__file__ = str(script_path)

    if rewrite_containers:
        module.__dict__.update({"List": List, "Dict": Dict})
        code = rewrite(source, str(script_path))
    else:
        code = compile(source, str(script_path), "exec")

    exec(code, module.__dict__)
    return module


def load_target(script_path: Path, rewrite_containers: bool = True):
    """Load a script and return its ``(func, args)`` pair.

    Every example script defines a ``main()`` that hands back the function to
    trace along with the arguments to trace it with.
    """
    script = load_script(script_path, rewrite_containers)
    if not hasattr(script, "main"):
        raise AttributeError("The script must define a `main()` function.")
    return script.main()
