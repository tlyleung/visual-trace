import sys
from types import FrameType
from typing import Any, Callable

import manim as mn

from .highlight import row_center
from .probe import probe_step
from .table import create_table111
from .trace_log import safe_repr


def record_step(
    scene: mn.Scene, frame: FrameType, lineno: int, queued: int, pending: int
) -> None:
    """Log and probe a settled step. No-op outside the animating pass."""
    if getattr(scene, "trace_pass", 0) != 2:
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
        "abs_lineno": frame.f_lineno,
        "src": source,
        "locals": {k: safe_repr(v) for k, v in frame.f_locals.items()},
        "queued": queued,
        "pending": pending,
        # Only a step that queued animations produces a partial movie file, so
        # frame extraction needs this to line steps up with the files on disk.
        "played": queued > 0,
    }
    record.update(probe_step(scene, lineno, frame.f_locals))
    log.emit(**record)


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

            # Second pass: animate code highlight and variables table
            if hasattr(scene, "table"):
                # Animate code highlight
                animation = scene.highlight.animate.move_to(
                    row_center(scene.code, lineno)
                )
                scene.animation_queue.append(animation)

                # Animate variables table
                old_table = scene.table
                new_table = create_table111(frame.f_locals, scene)
                old_table.become(new_table)

            # What this step queued, captured before the queues drain below
            queued = len(scene.animation_queue)
            pending = len(scene.pending_operations)

            # Play animation
            if scene.animation_queue:
                scene.play(*scene.animation_queue)
                scene.animation_queue.clear()

            if scene.pending_operations:
                for operation in scene.pending_operations:
                    operation()
                scene.pending_operations.clear()

            record_step(scene, frame, lineno, queued, pending)

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
