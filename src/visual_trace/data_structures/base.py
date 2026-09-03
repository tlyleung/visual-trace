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


def move_to_slot(mobject, placeholder, index: int) -> Callable[[], Any]:
    """Animate a cell to slot `index`, measured from the placeholder.

    The target is computed when the builder runs -- after the table has laid
    out -- so it survives the container being moved between queueing and
    playing.
    """
    return lambda: mobject.animate.move_to(
        placeholder.get_center() + mn.RIGHT * (index * CELL_SIZE)
    )


def replace_label(label, value, anchor) -> Callable[[], Any]:
    """Transform a cell label to show `value`.

    `Transform` does not carry `original_text` across, so it is updated here --
    otherwise the label displays the new value while still reporting the old one
    to `drawn_values`.
    """

    def build():
        replacement = mn.Text(str(value), font_size=24).move_to(anchor.get_center())
        label.original_text = replacement.original_text
        return mn.Transform(label, replacement)

    return build


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
        # Set once a structural change has queued slot moves that have not
        # played yet, so a cell added before then is placed by slot rather
        # than against a neighbour that is about to move.
        self._pending_relayout = False

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
        self._pending_relayout = False
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
        if self._pending_relayout:
            # A queued removal is about to move the row; anchoring to a
            # neighbour would read geometry that has not shifted yet.
            cell.move_to(self.mobject.placeholder)
            cell.shift(mn.RIGHT * (len(self.mobject.items) * CELL_SIZE))
        elif len(self.mobject.items):
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

    #
    # Cell primitives
    #
    # Every overridden container method reduces to one of these. Subclasses
    # describe their cell shape with SLOTS and VALUE_SLOT and otherwise just
    # wire methods to them.
    #

    # (square index, label index) pairs within one cell.
    SLOTS: tuple[tuple[int, int], ...] = ((0, 1),)
    # Which slot `_write` replaces.
    VALUE_SLOT = 0

    def _parts(self, index: int, slot: int):
        square_at, label_at = self.SLOTS[slot]
        cell = self.mobject.items[index]
        return cell[square_at], cell[label_at]

    def _light(self, index: int, slot: int = 0, settled: float = 0.0) -> None:
        """Pulse one half of a cell, settling at `settled`."""
        if not 0 <= index < len(self.mobject.items):
            return
        square, _ = self._parts(index, slot)
        square.set_fill(mn.WHITE, opacity=0.5)
        self.queue_deferred(fade_fill(square, settled))

    def _sweep(self, hit: int | None = None, slot: int = 0) -> None:
        """Scan every cell, leaving `hit` lit.

        Both outcomes animate: a miss that drew nothing would be
        indistinguishable from a frame the tool forgot to render.
        """
        for index in range(len(self.mobject.items)):
            self._light(index, slot, settled=0.5 if index == hit else 0.0)

    def _write(self, index: int, value: object, slot: int | None = None) -> None:
        """Replace what a cell shows, in place."""
        if not 0 <= index < len(self.mobject.items):
            return
        square, label = self._parts(index, self.VALUE_SLOT if slot is None else slot)
        square.set_fill(mn.WHITE, opacity=1.0)
        self.queue_deferred(fade_fill(square, 0.0))
        self.queue_deferred(replace_label(label, value, square))

    def _append_cell(self, cell) -> None:
        """Add a cell at the end, relaying out if the row is mid-change."""
        self._place_cell(cell)
        self.mobject.items.add(cell)
        if self._pending_relayout:
            self._relayout()

    def _insert_cell(self, index: int, cell) -> None:
        """Add a cell at `index` and slide the rest along."""
        self._place_cell(cell)
        self.mobject.items.insert(index, cell)
        self._relayout()

    def _remove_cell(self, index: int) -> None:
        """Fade a cell out and close the gap."""
        cell = self.mobject.items[index]
        self.mobject.items.remove(cell)
        self.queue(mn.FadeOut(cell))
        self._relayout()

    def _relayout(self) -> None:
        """Send every cell to its slot.

        Used after a structural change rather than shifting neighbours by hand:
        the target is resolved after the layout, so a cell added in the same step
        as a removal still lands in the right place.
        """
        self._pending_relayout = True
        for index, cell in enumerate(self.mobject.items):
            self.queue_deferred(move_to_slot(cell, self.mobject.placeholder, index))

    #
    # What is drawn, versus what is held
    #

    def drawn_values(self) -> list[str]:
        """The text each drawn cell is currently showing.

        Read via `original_text`, not `.text`, which strips spaces.
        """
        raise NotImplementedError

    def expected_values(self) -> list[str]:
        """What the cells should be showing, taken from the container.

        Must not go through an animated method -- reading the container to check
        the drawing would queue animations of its own.
        """
        raise NotImplementedError

    def reset(self):
        """Return a fresh instance with the same initial arguments.

        `Animation.construct` traces twice -- once to collect variable names and
        once to animate -- so the first pass's mutations have to be undone.
        """
        args, kwargs = self._initial_arguments
        return type(self)(*args, **kwargs)
