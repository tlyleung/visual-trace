import inspect
from typing import Any, Callable

import manim as mn

from ..utils.highlight import create_highlight
from ..utils.table import create_table
from ..utils.tracing import start_tracing


class Animation(mn.Scene):
    def __init__(self, func: Callable, args: tuple[Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.kwargs = {}
        self.func = func
        self.args = args

    def construct(self):
        self.animation_queue = []
        self.pending_operations = []

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
        self.start_line_number = inspect.getsourcelines(self.func)[1]

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
        _, self.variables = start_tracing(self, self.func, *self.args, **self.kwargs)
        self.table = create_table(self)
        self.add(self.table)

        # Reset data structures between traces
        self.args = tuple(
            arg.reset() if hasattr(arg, "reset") else arg for arg in self.args
        )

        # Animate using second trace
        start_tracing(self, self.func, *self.args, **self.kwargs)
        self.wait()
