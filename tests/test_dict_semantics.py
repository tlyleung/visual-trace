"""`Dict` behaviour that the current examples never exercise.

Nothing in `examples/` calls `values()` or `clear()`, and no example passes a
Dict as an argument, so none of this is covered by a render. These are the cases
the probe cannot reach.
"""


from stubs import drain, realize

from visual_trace.data_structures.dict import Dict


def highlighted_value_cells(d: Dict) -> list[int]:
    """Which value cells the queued animations point at, in order."""
    cells = {id(item[2]): index for index, item in enumerate(d.mobject.items)}
    return [
        cells[id(animation.mobject)]
        for animation in realize(d.animation_queue)
        if id(animation.mobject) in cells
    ]


def highlighted_key_cells(d: Dict) -> list[int]:
    cells = {id(item[0]): index for index, item in enumerate(d.mobject.items)}
    return [
        cells[id(animation.mobject)]
        for animation in realize(d.animation_queue)
        if id(animation.mobject) in cells
    ]


def test_values_highlights_each_cell_in_turn():
    """Duplicate values must still highlight their own cell.

    Resolving position with `list(values()).index(value)` finds the *first* match,
    so a repeated value re-highlights the earlier cell and never its own.
    """
    d = Dict(a=5, b=5, c=9)
    d.animation_queue.clear()
    list(d.values())
    assert highlighted_value_cells(d) == [0, 1, 2]


def test_items_highlights_each_cell_in_turn():
    d = Dict(a=5, b=5, c=9)
    d.animation_queue.clear()
    list(d.items())
    assert highlighted_value_cells(d) == [0, 1, 2]


def test_keys_highlights_each_cell_in_turn():
    d = Dict(a=5, b=5, c=9)
    d.animation_queue.clear()
    list(d.keys())
    assert highlighted_key_cells(d) == [0, 1, 2]


def test_clear_empties_the_group_that_is_actually_drawn():
    """`clear` must empty the attached group, not swap in a detached one."""
    d = Dict(a=1, b=2)
    drain(d)

    d.clear()
    # The cells must survive until the fade has played; detaching them at call
    # time would leave the table laying out an empty group mid-animation.
    assert len(d.mobject.items) == 2, "cells were detached before their fade played"
    drain(d)

    attached = [id(m) for m in d.mobject.submobjects]
    assert id(d.mobject.items) in attached, "items group is not attached to the mobject"
    assert len(d.mobject.items) == 0, "cleared dict still draws its old cells"
    assert len(d) == 0


def test_dict_can_reset_between_tracing_passes():
    """`Animation.construct` traces twice and resets arguments in between."""
    d = Dict(a=1, b=2)
    fresh = d.reset()
    assert fresh == {"a": 1, "b": 2}
    assert fresh is not d
    fresh["c"] = 3
    assert "c" not in d
