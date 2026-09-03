import manim as mn

from .base import CELL_SIZE, Animated


class List(Animated, list):
    """A list that draws itself as a contiguous row of cells."""

    SLOTS = ((0, 1),)
    VALUE_SLOT = 0

    def __init__(self, *args):
        list.__init__(self, args)
        Animated.__init__(self, mn.VGroup(), *args)
        self._init_placeholder(rows=1)
        for item in args:
            self.__draw(item)

    #
    # Drawing
    #

    def __cell(self, value: object) -> mn.VGroup:
        square = mn.Square(
            side_length=CELL_SIZE, fill_color=mn.WHITE, fill_opacity=0.0
        )
        return mn.VGroup(square, mn.Text(str(value), font_size=24))

    def __appear(self, cell: mn.VGroup) -> None:
        self.queue(mn.AnimationGroup(mn.Create(cell[0]), mn.FadeIn(cell[1])))

    def __draw(self, value: object) -> None:
        if not self.is_drawable():
            return
        cell = self.__cell(value)
        self._append_cell(cell)
        self.__appear(cell)

    def __insert_at(self, index: int, value: object) -> None:
        if not self.is_drawable():
            return
        cell = self.__cell(value)
        self._insert_cell(index, cell)
        self.__appear(cell)

    def __sync(self) -> None:
        """Bring the drawing back in line with the data, cell by cell.

        The fallback for bulk changes -- sort, reverse, extend, slice assignment
        -- where tracking individual moves would say less than simply showing the
        result.
        """
        while len(self.mobject.items) > len(self):
            self._remove_cell(len(self.mobject.items) - 1)
        for index, value in enumerate(list.__iter__(self)):
            if index >= len(self.mobject.items):
                self.__insert_at(index, value)
            elif self.mobject.items[index][1].original_text != str(value):
                self._write(index, value)

    def __at(self, index: int) -> int:
        return index + len(self) if index < 0 else index

    def drawn_values(self) -> list[str]:
        return [cell[1].original_text for cell in self.mobject.items]

    def expected_values(self) -> list[str]:
        # list.__iter__, not self: our own __iter__ animates.
        return [str(value) for value in list.__iter__(self)]

    #
    # Reads
    #

    def __getitem__(self, index):
        """Light the cell being read; a slice yields another animated list."""
        value = list.__getitem__(self, index)
        if isinstance(index, slice):
            return type(self)(*value)
        self._light(self.__at(index))
        return value

    def __iter__(self):
        """Light each cell as it is handed out.

        Iteration genuinely walks the container one element at a time, so unlike
        `len` it earns an animation per element. Lighting on yield means a loop
        that breaks early only lights what it reached.
        """
        for index, value in enumerate(list.__iter__(self)):
            self._light(index)
            yield value

    def __contains__(self, value) -> bool:
        found = list.__contains__(self, value)
        self._sweep(list.index(self, value) if found else None)
        return found

    def index(self, value, *bounds) -> int:
        try:
            at = list.index(self, value, *bounds)
        except ValueError:
            self._sweep(None)
            raise
        self._sweep(at)
        return at

    def count(self, value) -> int:
        for index, item in enumerate(list.__iter__(self)):
            self._light(index, settled=0.5 if item == value else 0.0)
        return list.count(self, value)

    #
    # Writes
    #

    def __setitem__(self, index, value) -> None:
        if isinstance(index, slice):
            list.__setitem__(self, index, value)
            self._sync_placeholder()
            self.__sync()
            return
        at = self.__at(index)
        list.__setitem__(self, index, value)
        self._write(at, value)

    def append(self, value: object) -> None:
        list.append(self, value)
        self._sync_placeholder()
        self.__draw(value)

    def insert(self, index: int, value: object) -> None:
        at = min(max(index + len(self) if index < 0 else index, 0), len(self))
        list.insert(self, index, value)
        self._sync_placeholder()
        self.__insert_at(at, value)

    def extend(self, values) -> None:
        list.extend(self, values)
        self._sync_placeholder()
        self.__sync()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def sort(self, **kwargs) -> None:
        list.sort(self, **kwargs)
        self.__sync()

    def reverse(self) -> None:
        list.reverse(self)
        self.__sync()

    #
    # Removals
    #

    def __delitem__(self, index) -> None:
        if isinstance(index, slice):
            list.__delitem__(self, index)
            self.__sync()
        else:
            at = self.__at(index)
            list.__delitem__(self, index)
            self._remove_cell(at)
        self._sync_placeholder()

    def pop(self, index: int = -1):
        at = self.__at(index)
        value = list.pop(self, index)
        self._remove_cell(at)
        self._sync_placeholder()
        return value

    def remove(self, value) -> None:
        at = list.index(self, value)
        self._sweep(at)
        list.remove(self, value)
        self._remove_cell(at)
        self._sync_placeholder()

    def clear(self) -> None:
        list.clear(self)
        self.__sync()
        self._sync_placeholder()

    #
    # Derived containers stay animated
    #

    def copy(self):
        return type(self)(*list.__iter__(self))

    def __add__(self, other):
        return type(self)(*list.__add__(self, list(other)))

    def __mul__(self, count: int):
        return type(self)(*list.__mul__(self, count))

    __rmul__ = __mul__
