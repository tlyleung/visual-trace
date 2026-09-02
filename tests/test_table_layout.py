"""Geometry of the variables table, at unit speed.

`utils/probe.py` checks the same properties against a real render, but that
costs ~8s a run. These cover the same ground in milliseconds, so a fix can be
driven test-first rather than verified afterwards.

Every case uses at least two rows: in a single-row table the row sits at y=0,
which is exactly where a mislaid mobject lands, so the bug hides.
"""

import manim as mn

from stubs import (
    TOL,
    StubScene,
    assert_in_row,
    drain,
    render_step,
    row_label,
)
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List
from visual_trace.utils.table import create_table, refresh_table


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


def test_emptied_cell_leaves_no_phantom_row_geometry():
    """A cell going from populated to empty must not pollute the row bounds.

    `become` aligns two mobject families by padding the shorter one, and the
    padding lands zero-area points at the origin. Nothing renders there, but the
    row's bounding box is dragged to y=0 and swallows its neighbour -- which
    breaks anything that positions relative to the table.
    """
    scores = Dict(a=5, b=5, c=9)
    drain(scores)
    local = {"scores": scores, "total": 19, "value": 9}

    scene = StubScene(dict.fromkeys(local))
    scene.table = create_table(scene)
    refresh_table(scene, local)

    scores.clear()
    drain(scores)
    refresh_table(scene, local)

    rows = list(scene.table.get_rows())
    for index, (upper, lower) in enumerate(zip(rows, rows[1:])):
        overlap = min(
            float(upper.get_corner(mn.UL)[1]), float(lower.get_corner(mn.UL)[1])
        ) - max(
            float(upper.get_corner(mn.DR)[1]), float(lower.get_corner(mn.DR)[1])
        )
        assert overlap <= TOL, (
            f"rows {index} and {index + 1} overlap by {overlap:.3f} after a "
            f"cell emptied"
        )


def test_cells_stay_contiguous_across_steps():
    """A cell appended after the group is already placed must sit flush.

    Single-step tests cannot see this: the group starts at the origin, so
    absolute and relative positioning agree. Once the table has moved the group
    into its cell they diverge.
    """
    nums = List(1, 2)
    render_step({"target": 9, "nums": nums})
    nums.append(3)
    render_step({"target": 9, "nums": nums})

    cells = list(nums.mobject)
    gaps = [
        float(right.get_corner(mn.UL)[0]) - float(left.get_corner(mn.DR)[0])
        for left, right in zip(cells, cells[1:])
    ]
    assert all(abs(gap) <= TOL for gap in gaps), f"cells are not contiguous: {gaps}"
