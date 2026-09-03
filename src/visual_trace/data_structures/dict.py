import manim as mn

from .base import CELL_SIZE, Animated

# Slot indices for `Animated`'s cell primitives.
KEY, VALUE = 0, 1


class Dict(Animated, dict):
    """A dict that draws itself as a row of stacked key/value cells."""

    # A cell is (key_square, key_label, val_square, val_label).
    SLOTS = ((0, 1), (2, 3))
    VALUE_SLOT = VALUE

    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
        Animated.__init__(self, mn.VMobject(), **kwargs)
        self._init_placeholder(rows=2)
        for key, value in kwargs.items():
            self.__draw(key, value)

    #
    # Drawing
    #

    def __cell(self, key: object, value: object) -> mn.VGroup:
        key_square = mn.Square(
            side_length=CELL_SIZE, fill_color=mn.WHITE, fill_opacity=0.0
        )
        val_square = mn.Square(
            side_length=CELL_SIZE, fill_color=mn.WHITE, fill_opacity=0.0
        )
        key_square.next_to(val_square, mn.UP, buff=0)
        return mn.VGroup(
            key_square,
            mn.Text(str(key), font_size=24).move_to(key_square),
            val_square,
            mn.Text(str(value), font_size=24).move_to(val_square),
        )

    def __appear(self, cell: mn.VGroup) -> None:
        for part in cell:
            self.queue(
                mn.Create(part) if isinstance(part, mn.Square) else mn.FadeIn(part)
            )

    def __draw(self, key: object, value: object) -> None:
        cell = self.__cell(key, value)
        self._append_cell(cell)
        self.__appear(cell)

    def __insert_at(self, index: int, key: object, value: object) -> None:
        cell = self.__cell(key, value)
        self._insert_cell(index, cell)
        self.__appear(cell)

    def __sync(self) -> None:
        """Bring the drawing back in line with the data, cell by cell.

        The fallback for bulk changes -- `update`, `|=` -- where following each
        individual insert would say less than showing the result.
        """
        while len(self.mobject.items) > len(self):
            self._remove_cell(len(self.mobject.items) - 1)
        for index, (key, value) in enumerate(dict.items(self)):
            if index >= len(self.mobject.items):
                self.__insert_at(index, key, value)
                continue
            cell = self.mobject.items[index]
            if cell[1].original_text != str(key):
                self._write(index, key, slot=KEY)
            if cell[3].original_text != str(value):
                self._write(index, value, slot=VALUE)

    def __index_of(self, key: object) -> int:
        return list(dict.keys(self)).index(key)

    def __show(self, index: int) -> None:
        self._light(index, KEY)
        self._light(index, VALUE)

    def drawn_values(self) -> list[str]:
        return [
            f"{cell[1].original_text}={cell[3].original_text}"
            for cell in self.mobject.items
        ]

    def expected_values(self) -> list[str]:
        # dict.items, not self: our own items() animates.
        return [f"{key}={value}" for key, value in dict.items(self)]

    #
    # Reads
    #

    def __contains__(self, key) -> bool:
        """Show the search that `in` performs, hit or miss.

        A miss that drew nothing would be indistinguishable from a frame the
        tool forgot to render, so both outcomes sweep; only the settle differs.
        """
        found = dict.__contains__(self, key)
        self._sweep(self.__index_of(key) if found else None, slot=KEY)
        return found

    def __getitem__(self, key):
        if not dict.__contains__(self, key):
            raise KeyError(key)
        self.__show(self.__index_of(key))
        return dict.__getitem__(self, key)

    def __iter__(self):
        """Light each key as it is handed out."""
        for index, key in enumerate(list(dict.keys(self))):
            self._light(index, KEY)
            yield key

    def get(self, key, default=None):
        if not dict.__contains__(self, key):
            self._sweep(None, slot=KEY)
            return default
        self.__show(self.__index_of(key))
        return dict.__getitem__(self, key)

    def items(self):
        """Return an animated list of key-value pairs."""
        for index, (key, value) in enumerate(list(dict.items(self))):
            self.__show(index)
            yield key, value

    def keys(self):
        """Return an animated list of keys."""
        for index, key in enumerate(list(dict.keys(self))):
            self._light(index, KEY)
            yield key

    def values(self):
        """Return an animated list of values.

        Indexed by position, not by looking the value up: `list(...).index(v)`
        returns the first match, so a repeated value would re-highlight the
        earlier cell and never its own.
        """
        for index, value in enumerate(list(dict.values(self))):
            self._light(index, VALUE)
            yield value

    #
    # Writes
    #

    def __setitem__(self, key, value) -> None:
        if dict.__contains__(self, key):
            index = self.__index_of(key)
            dict.__setitem__(self, key, value)
            self._light(index, KEY)
            self._write(index, value)
            return
        dict.__setitem__(self, key, value)
        self._sync_placeholder()
        self.__draw(key, value)

    def setdefault(self, key, default=None):
        if dict.__contains__(self, key):
            self.__show(self.__index_of(key))
            return dict.__getitem__(self, key)
        self[key] = default
        return default

    def update(self, *args, **kwargs) -> None:
        dict.update(self, *args, **kwargs)
        self._sync_placeholder()
        self.__sync()

    def __ior__(self, other):
        self.update(other)
        return self

    #
    # Removals
    #

    def __delitem__(self, key) -> None:
        if not dict.__contains__(self, key):
            raise KeyError(key)
        index = self.__index_of(key)
        dict.__delitem__(self, key)
        self._remove_cell(index)
        self._sync_placeholder()

    def pop(self, key, *default):
        if not dict.__contains__(self, key):
            self._sweep(None, slot=KEY)
            if default:
                return default[0]
            raise KeyError(key)
        index = self.__index_of(key)
        self._sweep(index, slot=KEY)
        value = dict.pop(self, key)
        self._remove_cell(index)
        self._sync_placeholder()
        return value

    def popitem(self):
        if not len(self):
            raise KeyError("popitem(): dictionary is empty")
        index = len(self) - 1
        item = dict.popitem(self)
        self._remove_cell(index)
        self._sync_placeholder()
        return item

    def clear(self) -> None:
        """Clear all items from the dict and animate their removal.

        Empties the attached group rather than rebinding the attribute to a new
        one: the group added in `__init__` is what is actually drawn, so swapping
        it leaves the old cells on screen and the replacement detached.
        """
        cells = list(self.mobject.items)
        for cell in cells:
            self.queue(mn.FadeOut(cell))
        if cells:
            # Detached by `apply_pending`, which the table runs just before it
            # lays out -- late enough that the cells are still parented while
            # the fade is being built, early enough that the layout sees the
            # container empty.
            self.pending_operations.append(
                lambda: self.mobject.items.remove(*cells)
            )
        dict.clear(self)
        self._sync_placeholder()

    #
    # Derived containers stay animated
    #

    def copy(self):
        """A drawn copy. Built by assignment so non-identifier keys survive --
        `__init__` only takes keyword arguments."""
        clone = type(self)()
        for key, value in dict.items(self):
            clone[key] = value
        return clone

    def __or__(self, other):
        clone = self.copy()
        clone.update(other)
        return clone
