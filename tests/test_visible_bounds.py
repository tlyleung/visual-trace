"""Bounding boxes must only count geometry that actually renders.

This has bitten four times now: blank code lines collapsing to the origin, an
empty List reporting zero extent there, `become` padding stranding zero-area
points, and MobjectTable's stroke_width=0 grid lines running far wider than any
cell. In every case the frame was correct and the bounding box was not.
"""

import manim as mn

from visual_trace.utils.probe import visible_range


def test_an_invisible_line_does_not_widen_the_bounds():
    square = mn.Square(side_length=1.0)
    line = mn.Line(mn.LEFT * 5, mn.RIGHT * 5, stroke_width=0)
    group = mn.VGroup(square, line)

    assert float(group.width) > 9, "precondition: the raw bbox spans the line"
    left, right = visible_range(group, axis=0)
    assert right - left < 1.5, f"visible bounds still span the invisible line: [{left}, {right}]"


def test_a_fully_transparent_mobject_is_ignored():
    square = mn.Square(side_length=1.0)
    ghost = mn.Square(side_length=8.0, stroke_opacity=0.0, fill_opacity=0.0)
    left, right = visible_range(mn.VGroup(square, ghost), axis=0)
    assert right - left < 1.5


def test_a_filled_but_unstroked_mobject_still_counts():
    filled = mn.Square(side_length=4.0, stroke_width=0, fill_opacity=1.0)
    assert visible_range(filled, axis=0) is not None


def test_nothing_visible_reports_none():
    assert visible_range(mn.VGroup(), axis=0) is None
