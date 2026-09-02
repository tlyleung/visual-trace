import manim as mn

from .base import CELL_SIZE, Animated, fade_fill


class List(Animated, list):
    """A list that draws itself as a contiguous row of cells."""

    def __init__(self, *args):
        list.__init__(self, args)
        Animated.__init__(self, mn.VGroup(), *args)
        self._init_placeholder(rows=1)
        for item in args:
            self.__draw(item)

    #
    # Animation methods
    #

    def __draw(self, value: object) -> None:
        square = mn.Square(
            side_length=CELL_SIZE, fill_color=mn.WHITE, fill_opacity=0.0
        )
        label = mn.Text(str(value), font_size=24)
        cell = mn.VGroup(square, label)

        self._place_cell(cell)
        self.mobject.items.add(cell)
        self.queue(mn.AnimationGroup(mn.Create(square), mn.FadeIn(label)))

    def __highlight(self, index: int) -> None:
        if index < 0:
            index += len(self.mobject.items)
        if not 0 <= index < len(self.mobject.items):
            return
        square, _ = self.mobject.items[index]
        square.set_fill(mn.WHITE, opacity=0.5)
        self.queue_deferred(fade_fill(square, 0.0))

    #
    # List methods
    #

    def __getitem__(self, index):
        """Light the cell being read.

        Only for a single index: a slice reads every cell, and lighting them all
        would be noise rather than a signal about what the algorithm looked at.
        """
        value = list.__getitem__(self, index)
        if isinstance(index, int):
            self.__highlight(index)
        return value

    def __iter__(self):
        """Light each cell as it is handed out.

        Iteration is the one read that genuinely walks the container, one
        element at a time, so unlike `len` it earns an animation per element --
        and it is what a `for num in nums` loop is made of. Lighting happens as
        each value is yielded, so a loop that breaks early only lights what it
        actually reached.
        """
        for index, value in enumerate(list.__iter__(self)):
            self.__highlight(index)
            yield value

    def append(self, value: object) -> None:
        """Animate adding a new square and label."""
        list.append(self, value)
        self._sync_placeholder()
        self.__draw(value)
