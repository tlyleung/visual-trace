"""The tracer must not leave anything behind.

`sys.settrace` is process-global: a hook left installed outruns the render that
installed it, line-traces every frame afterwards, and fights any debugger or
coverage tool in the same process.
"""

import sys

import pytest

from visual_trace.utils.tracing import start_tracing


class Bare:
    """Enough scene for the tracer to walk without animating."""

    trace_pass = 1
    start_line_number = 0

    def __init__(self):
        self.animation_queue = []


def test_the_trace_hook_is_removed_when_the_traced_code_raises():
    def boom():
        raise RuntimeError("user code failed")

    with pytest.raises(RuntimeError):
        start_tracing(Bare(), boom)
    assert sys.gettrace() is None, "the trace hook outlived the traced function"


def test_the_trace_hook_is_removed_on_success():
    start_tracing(Bare(), lambda: None)
    assert sys.gettrace() is None


def test_variables_records_the_type_of_the_value():
    """Not the type of the name -- `type(variable)` is always `str`."""

    def has_locals():
        count = 1
        label = "x"
        return count, label

    _, variables = start_tracing(Bare(), has_locals)
    assert variables == {"count": int, "label": str}


def test_frames_outside_the_traced_function_are_not_line_traced():
    """Line-tracing everything the traced code calls is ~8x slower.

    Every nested frame -- all of Manim's mobject construction inside an
    overridden method -- was line-traced only for its events to be discarded by
    the name check.
    """
    import sys as _sys

    from visual_trace.utils.tracing import trace_func

    def traced():
        pass

    def somewhere_else():
        return _sys._getframe()

    handler = trace_func(None, None, None, traced, Bare(), {})
    assert handler(somewhere_else(), "call", None) is None
