"""Geometry of the variables table, at unit speed.

`utils/probe.py` checks the same properties against a real render, but that
costs ~8s a run. These cover the same ground in milliseconds, so a fix can be
driven test-first rather than verified afterwards.

Assertions are made against each value's own **row label**, never against the
table's bounds. The value is a child of the table, so anything derived from the
table's geometry is inflated by the value itself and passes vacuously. The label
is positioned by the same layout but is unaffected by what the value does later.
For the same reason every case uses at least two rows: in a single-row table the
row sits at y=0, which is exactly where a mislaid mobject lands, so the bug hides.
"""

import manim as mn

from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List
from visual_trace.utils.table import create_table111

TOL = 0.02


class StubScene:
    """The slice of `Animation` that `create_table111` actually touches."""

    def __init__(self, variables: dict):
        self.variables = variables
        self.animation_queue = []
        self.right_col = mn.Rectangle(
            width=mn.config.frame_width / 2,
            height=mn.config.frame_height,
            stroke_width=0,
        )
        self.right_col.to_edge(mn.RIGHT, buff=0)


def render_step(local_vars: dict):
    """One traced step. `create_table111` applies deferred work itself."""
    scene = StubScene(dict.fromkeys(local_vars))
    table = create_table111(local_vars, scene)
    return scene, table


def row_label(table: mn.MobjectTable, index: int):
    return table.get_rows()[index][0]


def assert_drawn(mobject, name: str) -> None:
    assert mobject.family_members_with_points(), f"{name} drew nothing at all"


def assert_in_row(value, label, name: str) -> None:
    """The value must sit on its label's row, and to the right of it."""
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


def test_list_materialises_in_its_row():
    """A List drawn on its first step lands in its cell, not at the origin."""
    nums = List(2, 7, 11, 15)
    _, table = render_step({"target": 9, "nums": nums})
    assert_in_row(nums.mobject, row_label(table, 1), "nums")


def test_dict_materialises_in_its_row():
    d = Dict(a=1, b=2)
    _, table = render_step({"target": 9, "d": d})
    assert_in_row(d.mobject, row_label(table, 1), "d")


def test_list_draws_one_cell_per_element():
    nums = List(2, 7, 11, 15)
    render_step({"target": 9, "nums": nums})
    assert len(nums.mobject) == len(nums)
