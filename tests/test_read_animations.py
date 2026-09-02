"""Reading a structure should be visible, not just writing to it.

two_sum spends most of its steps reading -- `nums[i]` and `target - num in d` --
and both were silent, so the array it scans never reacted and the branch the
algorithm turns on showed nothing.
"""

from stubs import drain, render_step, settle, square_opacities
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
