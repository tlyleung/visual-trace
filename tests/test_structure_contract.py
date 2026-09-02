"""The contract a data structure must satisfy to be animated by the scene.

`List` and `Dict` are the only two today, but the README plans Stack, Queue, Tree
and Graph. This drives the contract through a deliberately minimal structure, so
the next one can be written against a documented base rather than by copying
`List` and hoping the scene notices it.
"""

import manim as mn

from stubs import assert_in_row, render_step, row_label
from visual_trace.data_structures.base import CELL_SIZE, Animated


class Blob(Animated, list):
    """The smallest structure that satisfies the contract."""

    def __init__(self, *args):
        list.__init__(self, args)
        Animated.__init__(self, mn.VGroup(), *args)
        self._init_placeholder(rows=1)
        for value in args:
            self._draw(value)

    def _draw(self, value) -> None:
        square = mn.Square(side_length=CELL_SIZE, fill_opacity=0.0)
        label = mn.Text(str(value), font_size=24)
        cell = mn.VGroup(square, label)
        self._place_cell(cell)
        self.mobject.items.add(cell)
        self.queue(mn.AnimationGroup(mn.Create(square), mn.FadeIn(label)))

    def append(self, value) -> None:
        list.append(self, value)
        self._sync_placeholder()
        self._draw(value)


def test_a_new_structure_is_laid_out_without_special_casing():
    blob = Blob(1, 2, 3)
    table = render_step({"target": 9, "blob": blob}).table
    assert_in_row(blob.mobject, row_label(table, 1), "blob")


def test_a_new_structure_draws_one_cell_per_element():
    blob = Blob(1, 2, 3)
    render_step({"target": 9, "blob": blob})
    assert len(blob.mobject.items) == len(blob)


def test_the_scene_drains_the_queue_and_applies_deferred_work():
    blob = Blob(1, 2, 3)
    step = render_step({"target": 9, "blob": blob})
    assert not blob.animation_queue, "queue was not drained into the scene"
    assert not blob.pending_operations, "deferred work was not applied"
    assert len(step.scene.animation_queue) == 3
    assert step.applied == 0


def test_a_new_structure_resets_to_its_initial_arguments():
    blob = Blob(1, 2, 3)
    blob.append(4)
    fresh = blob.reset()
    assert list(fresh) == [1, 2, 3]
    assert fresh is not blob
