import manim as mn

from .base import Animated


class List(Animated, list):
    """A list that draws itself as a contiguous row of cells."""

    FADE_TIME = 0.2

    def __init__(self, *args):
        list.__init__(self, args)
        Animated.__init__(self, mn.VGroup(), *args)
        for item in args:
            self.__draw(item)

    #
    # Animation methods
    #

    def __draw(self, value: object) -> None:
        square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
        label = mn.Text(str(value), font_size=24)
        cell = mn.VGroup(square, label)

        # Sit against the last drawn cell -- absolute placement would be wrong
        # once the table has moved the group into its own cell -- then step over
        # any cells queued in this same step that are not in the group yet.
        if len(self.mobject):
            cell.next_to(self.mobject[-1], mn.RIGHT, buff=0)
        cell.shift(mn.RIGHT * (len(self.pending_operations) * 0.5))

        self.animation_queue.append(
            mn.AnimationGroup(mn.Create(square), mn.FadeIn(label))
        )
        self.pending_operations.append(lambda: self.mobject.add(cell))

    def __highlight_animation(self, index: int) -> list:
        if index < 0:
            index += len(self.mobject)
        if not 0 <= index < len(self.mobject):
            return []
        square, _ = self.mobject[index]
        square.set_fill(mn.WHITE, opacity=0.5)
        return [square.animate.set_fill(mn.WHITE, opacity=0.0)]

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
            self.animation_queue.extend(self.__highlight_animation(index))
        return value

    def append(self, value: object) -> None:
        """Animate adding a new square and label."""
        list.append(self, value)
        self.__draw(value)
