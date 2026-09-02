import inspect
from typing import Any, Callable

import manim as mn

from ..data_structures.base import Animated
from ..utils.highlight import create_highlight
from ..utils.table import build_table
from ..utils.trace_log import open_log
from ..utils.tracing import ANIMATING_PASS, RETURN_ROW, flush, start_tracing


class Animation(mn.Scene):
    def __init__(self, func: Callable, args: tuple[Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.kwargs = {}
        self.func = func
        self.args = args

    def construct(self):
        self.animation_queue = []

        # Verification instrumentation. Inert unless VISUAL_TRACE_LOG is set.
        self.trace_log = open_log()
        self.step = 0

        # Layout
        width = mn.config.frame_width / 2
        height = mn.config.frame_height
        self.left_col = mn.Rectangle(width=width, height=height, stroke_width=0)
        self.right_col = mn.Rectangle(width=width, height=height, stroke_width=0)
        self.left_col.to_edge(mn.LEFT, buff=0)
        self.right_col.to_edge(mn.RIGHT, buff=0)
        self.add(self.left_col, self.right_col)

        # Create code listing with highlight
        code_string = inspect.getsource(self.func)
        self.source_lines, self.start_line_number = inspect.getsourcelines(self.func)

        # Transform code to use animated data structures
        # code = transform_code(code)

        if not code_string:
            raise ValueError("Could not retrieve source code for the function.")

        self.code = mn.Code(
            code_string=code_string, tab_width=4, background="window", language="Python"
        )
        self.code.scale(0.5)
        self.code.move_to(self.left_col.get_center())
        self.add(self.code)

        self.highlight = create_highlight(1, self.code)
        self.add(self.highlight)

        # Create variables table using first trace
        self.trace_pass = 1
        _, self.variables = start_tracing(self, self.func, *self.args, **self.kwargs)
        # Reserved from the first frame so the row set never shifts, and the
        # answer has somewhere to land when the function finally returns.
        self.variables[RETURN_ROW] = None
        # No locals yet, so every row reads "Undefined".
        self.table, _ = build_table(self, {})
        self.add(self.table)

        # Reset data structures between traces
        self.args = tuple(
            arg.reset() if isinstance(arg, Animated) else arg for arg in self.args
        )

        # Animate using second trace
        self.trace_pass = ANIMATING_PASS
        result, _ = start_tracing(self, self.func, *self.args, **self.kwargs)
        flush(self, result)
        self.wait()

        if self.trace_log is not None:
            self.trace_log.close()
