"""Shared test support: scene stand-ins and table-geometry assertions.

Rendering is what makes the real scene slow, and none of these tests need it.
"""

import manim as mn

from visual_trace.utils.table import create_table111

TOL = 0.02


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


class StubScene(SceneGraph):
    """The slice of `Animation` that `create_table111` actually touches."""

    def __init__(self, variables: dict):
        super().__init__()
        self.variables = variables
        self.animation_queue = []
        self.right_col = right_column()


def render_step(local_vars: dict):
    """One traced step. `create_table111` applies deferred work itself."""
    scene = StubScene(dict.fromkeys(local_vars))
    table = create_table111(local_vars, scene)
    return scene, table


def drain(structure) -> None:
    for operation in structure.pending_operations:
        operation()
    structure.pending_operations.clear()


def row_label(table: mn.MobjectTable, index: int):
    return table.get_rows()[index][0]


def assert_drawn(mobject, name: str) -> None:
    assert mobject.family_members_with_points(), f"{name} drew nothing at all"


def assert_in_row(value, label, name: str) -> None:
    """The value must sit on its label's row, and to the right of it.

    Asserted against the label, never the table's own bounds: the value is a
    child of the table, so anything derived from the table is inflated by the
    value itself and passes vacuously.
    """
    assert_drawn(value, name)
    label_y = float(label.get_center()[1])
    value_y = float(value.get_center()[1])
    assert abs(label_y - value_y) <= TOL, (
        f"{name} sits at y={value_y:.3f} but its row label is at y={label_y:.3f}"
    )
    label_right = float(label.get_corner(mn.DR)[0])
    value_left = float(value.get_corner(mn.UL)[0])
    assert value_left >= label_right - TOL, (
        f"{name} starts at x={value_left:.3f}, left of its label's "
        f"right edge at x={label_right:.3f}"
    )


def settle(structure) -> None:
    """Play the queued animations to their end state, as a render would."""
    from manim.animation.animation import prepare_animation

    for queued in structure.animation_queue:
        animation = prepare_animation(queued)
        animation.begin()
        animation.interpolate(1)
        animation.finish()
    structure.animation_queue.clear()
