"""Reading a structure should be visible, not just writing to it.

two_sum spends most of its steps reading -- `nums[i]` and `target - num in d` --
and both were silent, so the array it scans never reacted and the branch the
algorithm turns on showed nothing.
"""

from stubs import drain, realize, render_step, settle, square_opacities
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List


cell_opacities = square_opacities   # a List cell is (square, label)
key_opacities = square_opacities     # a Dict cell is (key_square, ..., val_square, ...)


def drawn_list() -> List:
    nums = List(2, 7, 11)
    render_step({"target": 9, "nums": nums})
    settle(nums)
    return nums


def drawn_dict() -> Dict:
    d = Dict(a=1, b=2, c=3)
    drain(d)
    settle(d)
    return d


def test_indexing_lights_the_cell_it_read():
    nums = drawn_list()
    assert nums[1] == 7
    assert cell_opacities(nums) == [0.0, 0.5, 0.0]
    settle(nums)
    assert cell_opacities(nums) == [0.0, 0.0, 0.0], "the highlight never faded"


def test_a_negative_index_lights_the_cell_it_read():
    nums = drawn_list()
    assert nums[-1] == 11
    assert cell_opacities(nums) == [0.0, 0.0, 0.5]


def test_slicing_animates_nothing():
    """A slice reads every cell; lighting them all would be noise, not signal."""
    nums = drawn_list()
    assert nums[0:2] == [2, 7]
    assert not nums.animation_queue


def test_membership_sweeps_every_key():
    d = drawn_dict()
    assert "b" in d
    assert key_opacities(d) == [0.5, 0.5, 0.5], "the search did not sweep"


def test_a_hit_leaves_only_the_match_lit():
    d = drawn_dict()
    assert "b" in d
    settle(d)
    assert key_opacities(d) == [0.0, 0.5, 0.0]


def test_a_miss_fades_every_key():
    d = drawn_dict()
    assert "z" not in d
    settle(d)
    assert key_opacities(d) == [0.0, 0.0, 0.0]


def test_lookup_does_not_also_trigger_a_search():
    """`__getitem__` tests membership internally; that must not animate twice."""
    d = drawn_dict()
    d["b"]
    lit = [index for index, value in enumerate(key_opacities(d)) if value]
    assert lit == [1], f"expected only the looked-up key to light, got {lit}"


def highlighted_cells(structure, slot: int = 0) -> list[int]:
    """Which cells the queued animations point at, in order."""
    cells = {id(cell[slot]): index for index, cell in enumerate(structure.mobject.items)}
    return [
        cells[id(animation.mobject)]
        for animation in realize(structure.animation_queue)
        if id(animation.mobject) in cells
    ]


def test_iterating_lights_each_cell_in_turn():
    """`for num in nums` genuinely walks the container, so it earns a cell each.

    This is the read `max_sub_array` is made of; without it the array being
    scanned never reacts for the whole video.
    """
    nums = drawn_list()
    assert list(nums) == [2, 7, 11]
    assert highlighted_cells(nums) == [0, 1, 2]


def test_a_partial_iteration_only_lights_what_it_reached():
    """The animation has to track what was consumed, not what exists."""
    nums = drawn_list()
    for value in nums:
        if value == 7:
            break
    assert highlighted_cells(nums) == [0, 1]
