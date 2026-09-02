import sys
from types import FrameType
from typing import Any, Callable

import manim as mn

from ..data_structures.base import Animated
from .highlight import row_center
from .probe import probe_step
from .table import refresh_table
from .trace_log import safe_repr

RETURN_ROW = "return"

# `Animation.construct` traces twice; only the second one draws.
ANIMATING_PASS = 2


def record_step(
    scene: mn.Scene,
    lineno: int,
    abs_lineno: int,
    local_vars: dict,
    content: int,
    applied: int,
    plays: int,
) -> None:
    """Log and probe a settled step. No-op outside the animating pass."""
    if scene.trace_pass != ANIMATING_PASS:
        return

    step = scene.step
    scene.step += 1

    log = getattr(scene, "trace_log", None)
    if log is None:
        return

    source = ""
    if 0 <= lineno < len(scene.source_lines):
        source = scene.source_lines[lineno].rstrip("\n")

    record = {
        "step": step,
        "lineno": lineno,
        "abs_lineno": abs_lineno,
        "src": source,
        "locals": {k: safe_repr(v) for k, v in local_vars.items()},
        "content": content,
        "applied": applied,
        # Each play() writes one partial movie file, and a step makes one or
        # two, so frame extraction needs the count to line steps up with the
        # files on disk.
        "plays": plays,
    }
    record.update(probe_step(scene, lineno, local_vars))
    log.emit(**record)


def _settle(
    scene: mn.Scene,
    lineno: int,
    abs_lineno: int,
    local_vars: dict,
    advance_highlight: bool,
) -> int:
    """Refresh the table, draw what the previous line queued, and record it.

    Shared by the per-line path and the final flush, which differ only in
    whether the highlight moves on afterwards.
    """
    _, applied = refresh_table(scene, local_vars)

    queued = list(scene.animation_queue)
    scene.animation_queue.clear()
    plays = 0
    if queued:
        scene.play(*queued)
        plays += 1

    if advance_highlight:
        scene.play(scene.highlight.animate.move_to(row_center(scene.code, lineno)))
        plays += 1

    record_step(scene, lineno, abs_lineno, local_vars, len(queued), applied, plays)
    return len(queued)


def flush(scene: mn.Scene, result: Any = None) -> int:
    """Draw whatever the final traced line queued.

    Every other line's animations are harvested at the *following* line event.
    The last line has no following event, so without this its effects -- often
    the answer the algorithm just computed -- are silently dropped.
    """
    local_vars = getattr(scene, "last_locals", None)
    if local_vars is None:
        return 0

    # A returned structure is shown as text, not as its own mobject: it is
    # already on screen under its variable name, and one mobject cannot occupy
    # two cells. Anything else is passed through so the table and the log both
    # render it once rather than repr-ing a repr.
    display = safe_repr(result) if isinstance(result, Animated) else result
    return _settle(
        scene,
        scene.last_lineno,
        scene.last_abs_lineno,
        {**local_vars, RETURN_ROW: display},
        advance_highlight=False,
    )


def trace_func(
    frame: FrameType,
    event: str,
    arg: Any,
    func: Callable,
    scene: mn.Scene,
    variables: dict[str, Any],
) -> Callable:
    if event == "line":
        code = frame.f_code
        lineno = frame.f_lineno - scene.start_line_number  # adjust for function offset

        function_name = code.co_name
        if function_name == func.__name__:
            # First pass: save variables
            for variable, _ in frame.f_locals.items():
                variables[variable] = type(variable)

            # Kept so the run can be flushed once the function has returned.
            scene.last_locals = dict(frame.f_locals)
            scene.last_lineno = lineno
            scene.last_abs_lineno = frame.f_lineno

            # Second pass only: the first just collects variable names.
            #
            # The trace fires *before* a line runs, so a line's animations only
            # reach us at the next event. `_settle` draws them while the
            # highlight is still on the line that caused them, and only then
            # advances it -- moving and drawing together would credit the effect
            # to the following line.
            if scene.trace_pass == ANIMATING_PASS:
                _settle(
                    scene,
                    lineno,
                    frame.f_lineno,
                    frame.f_locals,
                    advance_highlight=True,
                )

    return lambda *args, **kwargs: trace_func(
        *args, **kwargs, func=func, scene=scene, variables=variables
    )


def start_tracing(
    scene: mn.Scene, func: Callable, *args: Any, **kwargs: Any
) -> tuple[Any, dict[str, type]]:
    variables = dict[Any, type]()
    sys.settrace(trace_func(None, None, None, func, scene, variables))
    result = func(*args, **kwargs)
    sys.settrace(None)
    return result, variables
