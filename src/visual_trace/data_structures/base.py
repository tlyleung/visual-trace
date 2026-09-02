from typing import Any, Callable

import manim as mn


PLACEHOLDER_OPACITY = 0.35


class Animated:
    """A data structure that narrates itself as it is used.

    Subclasses pair a builtin container with a Manim mobject and override the
    container's methods so that ordinary use has a visual side effect: the
    animation falls out of the algorithm's own data access rather than being
    scripted separately.

    Two queues make that work, and the scene drains both each step:

    ``animation_queue``
        Animations to play. `create_table111` moves them onto the scene.

    ``pending_operations``
        Mobject-tree mutations that must not happen yet. `create_table111`
        applies them *before* laying the table out, so a structure whose group
        is still empty at layout time is not arranged as nothing. Use it for
        removals, which have to outlive the fade that animates them; additions
        may equally well be applied inline, as `Dict` does.

    Positioning a new cell has to account for both: sit it against the last cell
    already in the group, then step it over however many cells are queued in this
    same batch (``len(self.pending_operations)``). Absolute placement by logical
    index looks equivalent while the group is still at the origin and breaks the
    moment the table moves it into a cell.
    """

    def __init__(self, mobject: mn.Mobject, *args: Any, **kwargs: Any):
        self.mobject = mobject
        # Cells live in their own group so that anything else parented to the
        # mobject -- the empty-state placeholder -- is not mistaken for one.
        self.mobject.items = mn.VGroup()
        self.mobject.add(self.mobject.items)
        self.animation_queue: list = []
        self.pending_operations: list[Callable[[], None]] = []
        # Kept so the scene can rebuild the structure between tracing passes.
        self._initial_arguments = (args, kwargs)

    def _init_placeholder(self, rows: int) -> None:
        """Give the container an outline to occupy while it is empty.

        Drawing nothing for an empty container is indistinguishable from a
        rendering failure, and it hides real logic -- searching an empty dict
        would otherwise animate nothing at all. The outline is sized to overlap
        the first real cell exactly, so showing and hiding it never moves the
        container's bounds.
        """
        squares = [
            mn.Square(
                side_length=0.5,
                stroke_opacity=PLACEHOLDER_OPACITY,
                fill_opacity=0.0,
            )
            for _ in range(rows)
        ]
        for upper, lower in zip(squares, squares[1:]):
            upper.next_to(lower, mn.UP, buff=0)

        self.mobject.placeholder = mn.VGroup(*squares)
        self.mobject.add(self.mobject.placeholder)
        if len(self):
            self.mobject.placeholder.set_stroke(opacity=0.0)

    def _show_placeholder(self, visible: bool) -> None:
        """Queue the fade between empty and occupied."""
        target = PLACEHOLDER_OPACITY if visible else 0.0
        self.animation_queue.append(
            self.mobject.placeholder.animate.set_stroke(opacity=target)
        )

    def reset(self):
        """Return a fresh instance with the same initial arguments.

        `Animation.construct` traces twice -- once to collect variable names and
        once to animate -- so the first pass's mutations have to be undone.
        """
        args, kwargs = self._initial_arguments
        return type(self)(*args, **kwargs)

    def drain_animations(self) -> list:
        """Hand over the queued animations and forget them."""
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
