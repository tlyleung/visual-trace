"""A queued animation must not move the mobject it animates.

Animations are queued while user code runs, and `build_table` repositions
every cell afterwards when it lays the table out. `.animate` snapshots its target
the moment the builder is created, so an animation built before the layout and
played after it interpolates the mobject back to where it used to be -- a cell
visibly flying in from wherever the previous table put it.

No settled-frame check can see this: the animation ends at the correct position.
"""


from stubs import StubScene, drain, play_all, settle
from visual_trace.data_structures.dict import Dict
from visual_trace.data_structures.list import List
from visual_trace.utils.table import build_table


def positions(mobject) -> list[tuple[float, float]]:
    return [
        (round(float(m.get_center()[0]), 3), round(float(m.get_center()[1]), 3))
        for m in mobject.family_members_with_points()
    ]


def lay_out_and_play(structure, name):
    """Queue, lay out (which moves things), then play -- the real order."""
    local = {"target": 9, name: structure}
    scene = StubScene(dict.fromkeys(local))
    build_table(scene, local)
    before = positions(structure.mobject)
    play_all(scene.animation_queue)
    return before, positions(structure.mobject)


def test_a_dict_insert_does_not_drag_the_container():
    d = Dict(a=1)
    drain(d)
    settle(d)
    d["b"] = 2
    before, after = lay_out_and_play(d, "d")
    assert before == after, "playing the queued animation moved the dict"


def test_filling_an_empty_dict_does_not_drag_the_placeholder():
    d = Dict()
    drain(d)
    settle(d)
    d["a"] = 1
    before, after = lay_out_and_play(d, "d")
    assert before == after, "the placeholder flew back to its old position"


def test_a_list_read_does_not_drag_the_container():
    nums = List(2, 7, 11)
    drain(nums)
    settle(nums)
    nums[1]
    before, after = lay_out_and_play(nums, "nums")
    assert before == after, "the highlight animation moved the list"
