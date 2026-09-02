import sys
from types import FrameType
from typing import Any, Callable

import manim as mn

from .highlight import HIGHLIGHT_OFFSET
from .table import create_table111


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
                line = scene.code.code_lines[lineno]
                center = scene.highlight.get_center()
                center[1] = line.get_center()[1]
                animation = scene.highlight.animate.move_to(center + HIGHLIGHT_OFFSET)
                scene.animation_queue.append(animation)

                # Animate variables table
                old_table = scene.table
                new_table = create_table111(frame.f_locals, scene)
                old_table.become(new_table)

            # Play animation
            if scene.animation_queue:
                scene.play(*scene.animation_queue)
                scene.animation_queue.clear()

            if scene.pending_operations:
                for operation in scene.pending_operations:
                    operation()
                scene.pending_operations.clear()

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
