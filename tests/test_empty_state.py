"""An empty container has to look like an empty container.

Drawing nothing is indistinguishable from a rendering failure, and it hid real
logic: two_sum's first `target - num in d` searches an empty dict, so the miss
that sets up the whole algorithm drew nothing at all.
"""

from stubs import drain, render_step, settle, visible_size
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List

def placeholder_opacity(structure) -> float:
    return round(float(structure.mobject.placeholder[0].get_stroke_opacity()), 2)

def test_an_empty_dict_draws_something():
    d = Dict()
    assert d.mobject.family_members_with_points(), "an empty dict drew nothing"
    assert placeholder_opacity(d) > 0

def test_an_empty_list_draws_something():
    nums = List()
    assert nums.mobject.family_members_with_points(), "an empty list drew nothing"
    assert placeholder_opacity(nums) > 0

def test_a_populated_dict_shows_no_placeholder():
    d = Dict(a=1)
    drain(d)
    settle(d)
    assert placeholder_opacity(d) == 0

def test_a_populated_list_shows_no_placeholder():
    nums = List(1, 2)
    drain(nums)
    settle(nums)
    assert placeholder_opacity(nums) == 0

def test_the_first_entry_hides_the_placeholder():
    d = Dict()
    settle(d)
    d["a"] = 1
    drain(d)
    settle(d)
    assert placeholder_opacity(d) == 0

def test_the_first_append_hides_the_placeholder():
    nums = List()
    settle(nums)
    nums.append(1)
    drain(nums)
    settle(nums)
    assert placeholder_opacity(nums) == 0

def test_clearing_brings_the_placeholder_back():
    d = Dict(a=1)
    drain(d)
    settle(d)
    d.clear()
    drain(d)
    settle(d)
    assert placeholder_opacity(d) > 0

def test_deleting_the_last_entry_brings_the_placeholder_back():
    d = Dict(a=1)
    drain(d)
    settle(d)
    del d["a"]
    drain(d)
    settle(d)
    assert placeholder_opacity(d) > 0

def container_width(structure) -> float:
    return visible_size(structure.mobject)[0]

def test_the_dict_placeholder_overlaps_the_first_cell():
    """Filling an empty container must not move or widen it.

    The placeholder stands exactly where the first cell will be drawn, so the
    transition is a crossfade rather than a reflow.
    """
    d = Dict()
    drain(d)
    settle(d)
    empty = container_width(d)
    d["a"] = 1
    drain(d)
    settle(d)
    assert container_width(d) == empty, "the dict changed width when first filled"

def test_the_list_placeholder_overlaps_the_first_cell():
    nums = List()
    drain(nums)
    settle(nums)
    empty = container_width(nums)
    nums.append(1)
    drain(nums)
    settle(nums)
    assert container_width(nums) == empty, "the list changed width when first filled"

def test_the_first_cell_lands_where_the_placeholder_stood():
    """After the table has moved the container, a new cell must follow it.

    New cells are built at the world origin, so anything created *after* a
    layout has to be anchored to what is already drawn. `List` anchors to its
    last cell; the first cell of an empty container has only the placeholder,
    which stands exactly where it should go.
    """
    for structure, name, fill in (
        (Dict(), "d", lambda s: s.__setitem__("a", 1)),
        (List(), "nums", lambda s: s.append(1)),
    ):
        drain(structure)
        settle(structure)
        render_step({"target": 9, name: structure})  # moves it into its cell
        empty = visible_size(structure.mobject)

        fill(structure)
        render_step({"target": 9, name: structure})
        filled = visible_size(structure.mobject)

        assert filled == empty, (
            f"{name} changed size when filled after a layout: {empty} -> {filled}"
        )

def test_a_three_row_placeholder_stacks_without_overlapping():
    """`_init_placeholder(rows=n)` is the extension point for new structures.

    Stacking forwards moves each square against an anchor that has not been
    placed yet, so from three rows up they pile onto each other.
    """
    import manim as mn

    from visual_trace.data_structures.base import Animated

    class ThreeRow(Animated, list):
        def __init__(self):
            list.__init__(self, [])
            Animated.__init__(self, mn.VGroup())
            self._init_placeholder(rows=3)

    squares = list(ThreeRow().mobject.placeholder)
    centres = [round(float(square.get_center()[1]), 3) for square in squares]
    assert len(set(centres)) == 3, f"squares share a position: {centres}"
    gaps = [round(centres[i] - centres[i + 1], 3) for i in range(len(centres) - 1)]
    assert gaps == [0.5, 0.5], f"squares are not stacked contiguously: {gaps}"
    assert centres[-1] == 0.0, "the bottom square should sit on the origin"

def test_a_cell_added_after_a_removal_lands_in_the_freed_slot():
    """Removals shift the survivors, and that shift is deferred.

    Anchoring a new cell to the previous cell's *current* position reads geometry
    that is about to move, leaving a cell-width hole. `_relayout` resolves every
    slot after the layout instead, so the two cannot disagree.
    """
    d = Dict(a=1, b=2, c=3)
    drain(d)
    settle(d)
    del d["a"]
    d["z"] = 9
    drain(d)
    settle(d)

    centres = [round(float(cell.get_center()[0]), 3) for cell in d.mobject.items]
    gaps = [round(centres[i + 1] - centres[i], 3) for i in range(len(centres) - 1)]
    assert gaps == [0.5, 0.5], f"row is not contiguous after a removal: {gaps}"
