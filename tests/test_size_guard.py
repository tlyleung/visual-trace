"""A container too big to draw falls back to text.

Every cell builds a Manim `Text` (~9ms). Before the AST rewriter a user writing
`List(...)` by hand knew that cost; afterwards `list(range(1000))` would silently
build a thousand mobjects and hang the render. This is a failure mode the
rewriter introduces, so the guard belongs with it.
"""

import time

from stubs import render_step
from visual_trace.data_structures.base import MAX_DRAWN_CELLS
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List


def test_a_small_container_is_drawn():
    nums = List(1, 2, 3)
    assert nums.is_drawable()


def test_an_oversized_list_is_not_drawn_but_is_still_correct():
    nums = List(*range(MAX_DRAWN_CELLS + 1))
    assert not nums.is_drawable()
    assert len(nums.mobject.items) == 0, "built cells it will never show"
    assert list(list.__iter__(nums)) == list(range(MAX_DRAWN_CELLS + 1))


def test_an_oversized_dict_is_not_drawn():
    d = Dict({index: index for index in range(MAX_DRAWN_CELLS + 1)})
    assert not d.is_drawable()
    assert len(d.mobject.items) == 0


def test_an_oversized_container_renders_as_text():
    nums = List(*range(MAX_DRAWN_CELLS + 1))
    table = render_step({"target": 9, "nums": nums}).table
    cell = table.get_rows()[1][1]
    assert hasattr(cell, "original_text"), "expected a text cell, not drawn cells"


def test_building_an_oversized_container_stays_cheap():
    """The whole point: it must not pay for mobjects it will not show."""
    started = time.perf_counter()
    List(*range(2000))
    assert time.perf_counter() - started < 1.0
