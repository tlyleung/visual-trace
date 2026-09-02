from typing import Any, Callable

import manim as mn

CELL_SIZE = 0.5
PLACEHOLDER_OPACITY = 0.35


#
# Deferred animation builders.
#
# `.animate` snapshots its target the moment the builder is created, but cells
# are queued while user code runs and only positioned when the table is laid
# out. An animation built too early therefore interpolates its mobject back to
# wherever the previous table had it -- a cell flying in from offscreen. Pass one
# of these to `queue_deferred`; the table realises them once everything is in
# its final place. Taking the mobject as a parameter also gives each closure its
# own binding, which a lambda written inside a loop would not have.
#


def fade_fill(mobject, opacity: float) -> Callable[[], Any]:
    return lambda: mobject.animate.set_fill(mn.WHITE, opacity=opacity)


def fade_stroke(mobject, opacity: float) -> Callable[[], Any]:
    return lambda: mobject.animate.set_stroke(opacity=opacity)


def shift_by(mobject, vector) -> Callable[[], Any]:
    return lambda: mobject.animate.shift(vector)


class Animated:
    """A data structure that narrates itself as it is used.

    Subclasses pair a builtin container with a Manim mobject and override the
    container's methods so that ordinary use has a visual side effect: the
    animation falls out of the algorithm's own data access rather than being
    scripted separately.

    Drawn cells live in ``mobject.items`` and the empty-state outline in
    ``mobject.placeholder``, so nothing else parented to the mobject is mistaken
    for a cell.

    ``animation_queue``
        Uniformly a list of zero-argument callables returning an animation. Use
        `queue` for one already built and `queue_deferred` for a `.animate`
        builder; the table realises them all once every cell is positioned.

    ``pending_operations``
        Mobject-tree mutations that must not happen yet -- removals, which have
        to outlive the fade that animates them. Additions go in directly, since
        `build_table` needs a populated group to lay out.
    """

    def __init__(self, mobject: mn.Mobject, *args: Any, **kwargs: Any):
        self.mobject = mobject
        self.mobject.items = mn.VGroup()
        self.mobject.add(self.mobject.items)
        self.animation_queue: list[Callable[[], Any]] = []
        self.pending_operations: list[Callable[[], None]] = []
        # Kept so the scene can rebuild the structure between tracing passes.
        self._initial_arguments = (args, kwargs)

    #
    # Queueing
    #

    def queue(self, animation: mn.Animation) -> None:
        """Queue an animation that is already built.

        Safe to build eagerly: `Create`, `FadeIn` and friends read the mobject's
        state when they begin, not when they are constructed.
        """
        if not isinstance(animation, mn.Animation):
            raise TypeError(
                "queue() takes a built Animation. For a `.animate` builder use "
                "queue_deferred(): `.animate` snapshots its target when created, "
                "so queueing one eagerly drags its mobject back to where the "
                "previous layout had it."
            )
        self.animation_queue.append(lambda: animation)

    def queue_deferred(self, build: Callable[[], Any]) -> None:
        """Queue a factory, realised only once the table has positioned cells."""
        self.animation_queue.append(build)

    def drain_animations(self) -> list[Callable[[], Any]]:
        """Hand over the queued builders and forget them."""
        queued = list(self.animation_queue)
        self.animation_queue.clear()
        return queued

    def apply_pending(self) -> int:
        """Run the deferred tree mutations. Returns how many ran."""
        operations = list(self.pending_operations)
        self.pending_operations.clear()
        for operation in operations:
            operation()
        return len(operations)

    #
    # Cells and the empty state
    #

    def _init_placeholder(self, rows: int) -> None:
        """Give the container an outline to occupy while it is empty.

        Drawing nothing for an empty container is indistinguishable from a
        rendering failure, and it hides real logic -- searching an empty dict
        would otherwise animate nothing at all. The outline stands exactly where
        the first cell goes, so filling the container is a crossfade rather than
        a reflow.
        """
        squares = [
            mn.Square(
                side_length=CELL_SIZE,
                stroke_opacity=PLACEHOLDER_OPACITY,
                fill_opacity=0.0,
            )
            for _ in range(rows)
        ]
        # Bottom-up: `next_to` moves the upper square against the lower one, so
        # the lower must already be placed. Going forwards leaves the top rows
        # anchored to squares that move afterwards, and from three rows up they
        # pile onto each other.
        for upper, lower in reversed(list(zip(squares, squares[1:]))):
            upper.next_to(lower, mn.UP, buff=0)

        self.mobject.placeholder = mn.VGroup(*squares)
        self.mobject.add(self.mobject.placeholder)
        self._was_empty = not len(self)
        if not self._was_empty:
            self.mobject.placeholder.set_stroke(opacity=0.0)

    def _place_cell(self, cell: mn.Mobject) -> None:
        """Position a new cell in the next slot of the row.

        Cells are built at the world origin, so one created after the table has
        moved the container must anchor to something on screen. The placeholder
        is the right anchor: it marks slot zero, it moves with the container, and
        unlike the previous cell it is never mid-animation. Anchoring to
        ``items[-1]`` instead reads a position that a queued removal is about to
        shift, leaving a cell-width hole in the row.
        """
        if len(self.mobject.items):
            cell.next_to(self.mobject.items[-1], mn.RIGHT, buff=0)
        else:
            cell.move_to(self.mobject.placeholder)

    def _sync_placeholder(self) -> None:
        """Fade the outline in or out, but only when emptiness actually changed.

        Called from every mutating method so no future one has to remember the
        transition -- forgetting it fails silently, as an outline stuck behind
        real cells or an empty container drawing nothing.
        """
        empty = not len(self)
        if empty == self._was_empty:
            return
        self._was_empty = empty
        self.queue_deferred(
            fade_stroke(
                self.mobject.placeholder, PLACEHOLDER_OPACITY if empty else 0.0
            )
        )

    def reset(self):
        """Return a fresh instance with the same initial arguments.

        `Animation.construct` traces twice -- once to collect variable names and
        once to animate -- so the first pass's mutations have to be undone.
        """
        args, kwargs = self._initial_arguments
        return type(self)(*args, **kwargs)
