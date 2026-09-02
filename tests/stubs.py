"""Shared test support: scene stand-ins and table-geometry assertions.

Rendering is what makes the real scene slow, and none of these tests need it.
"""

from typing import NamedTuple

import manim as mn
from manim.animation.animation import prepare_animation

from visual_trace.utils.probe import visible_range, x_range
from visual_trace.utils.table import build_table, realize_animations

TOL = 0.02

# Production realises the queued builders once the table has positioned every
# cell; tests that touch a structure's queue directly have to do the same.
realize = realize_animations


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
    """The invisible anchor `build_table` aligns the table against."""
    column = mn.Rectangle(
        width=mn.config.frame_width / 2,
        height=mn.config.frame_height,
        stroke_width=0,
    )
    column.to_edge(mn.RIGHT, buff=0)
    return column


class StubScene(SceneGraph):
    """The slice of `Animation` that `build_table` actually touches."""

    def __init__(self, variables: dict):
        super().__init__()
        self.variables = variables
        self.animation_queue = []
        self.right_col = right_column()


class Step(NamedTuple):
    scene: StubScene
    table: mn.MobjectTable
    applied: int


def render_step(local_vars: dict) -> Step:
    """One traced step. `build_table` applies deferred work itself."""
    scene = StubScene(dict.fromkeys(local_vars))
    table, applied = build_table(scene, local_vars)
    return Step(scene, table, applied)


def play_all(queue) -> None:
    """Advance every animation in `queue` to its end state, as a render would."""
    for queued in queue:
        animation = prepare_animation(queued)
        animation.begin()
        animation.interpolate(1)
        animation.finish()


def settle(structure) -> None:
    """Play a structure's own queue, realising its builders first."""
    play_all(realize(structure.animation_queue))
    structure.animation_queue.clear()


def drain(structure) -> None:
    """Run a structure's deferred tree mutations."""
    structure.apply_pending()


#
# Geometry assertions
#


def visible_size(mobject) -> tuple[float, float]:
    """(width, height) of what actually renders.

    Raw Manim bounds count invisible geometry; MobjectTable in particular leaves
    a cell reporting several units wide when its only drawn part is half a unit.
    """
    horizontal = visible_range(mobject, axis=0)
    vertical = visible_range(mobject, axis=1)
    if horizontal is None or vertical is None:
        return (0.0, 0.0)
    return (
        round(horizontal[1] - horizontal[0], 3),
        round(vertical[1] - vertical[0], 3),
    )


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
    label_right = x_range(label)[1]
    value_left = x_range(value)[0]
    assert value_left >= label_right - TOL, (
        f"{name} starts at x={value_left:.3f}, left of its label's "
        f"right edge at x={label_right:.3f}"
    )


def square_opacities(structure, slot: int = 0) -> list[float]:
    """Fill opacity of one square per drawn cell -- `slot` picks which."""
    return [
        round(float(cell[slot].get_fill_opacity()), 2)
        for cell in structure.mobject.items
    ]
