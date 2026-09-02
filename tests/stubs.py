"""Stand-ins for the parts of `manim.Scene` the code under test touches.

Rendering is what makes the real scene slow, and none of these tests need it.
"""

import manim as mn


class SceneGraph:
    """Scene-graph bookkeeping, without a renderer."""

    def __init__(self):
        self.mobjects: list = []

    def add(self, *mobjects):
        for mobject in mobjects:
            if not any(mobject is held for held in self.mobjects):
                self.mobjects.append(mobject)

    def remove(self, *mobjects):
        for mobject in mobjects:
            self.mobjects = [held for held in self.mobjects if held is not mobject]


def right_column() -> mn.Rectangle:
    """The invisible anchor `create_table111` aligns the table against."""
    column = mn.Rectangle(
        width=mn.config.frame_width / 2,
        height=mn.config.frame_height,
        stroke_width=0,
    )
    column.to_edge(mn.RIGHT, buff=0)
    return column
