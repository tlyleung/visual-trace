import manim as mn

from .base import CELL_SIZE, Animated, fade_fill, shift_by

# Which half of a cell to light: a cell is (key_square, key_label, val_square,
# val_label), stacked vertically.
KEY, VALUE = 0, 2


class Dict(Animated, dict):
    """A dict that draws itself as a row of stacked key/value cells."""

    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
        Animated.__init__(self, mn.VMobject(), **kwargs)
        self._init_placeholder(rows=2)

        for key, value in kwargs.items():
            self.__draw(key, value)

    #
    # Animation methods
    #

    def __draw(self, key: object, value: object) -> None:
        key_square = mn.Square(
            side_length=CELL_SIZE, fill_color=mn.WHITE, fill_opacity=0.0
        )
        val_square = mn.Square(
            side_length=CELL_SIZE, fill_color=mn.WHITE, fill_opacity=0.0
        )
        key_square.next_to(val_square, mn.UP, buff=0)

        key_label = mn.Text(str(key), font_size=24).move_to(key_square)
        val_label = mn.Text(str(value), font_size=24).move_to(val_square)

        cell = mn.VGroup(key_square, key_label, val_square, val_label)
        self._place_cell(cell)
        self.mobject.items.add(cell)

        for part in (key_square, key_label, val_square, val_label):
            self.queue(
                mn.Create(part) if isinstance(part, mn.Square) else mn.FadeIn(part)
            )

    def __highlight(self, index: int, slot: int, settled: float = 0.0) -> None:
        """Light one half of a cell, settling at `settled` when the fade ends."""
        square = self.mobject.items[index][slot]
        square.set_fill(mn.WHITE, opacity=0.5)
        self.queue_deferred(fade_fill(square, settled))

    def __search(self, key: object, found: bool) -> None:
        """Sweep every key as if scanning, then settle on the outcome."""
        for index, candidate in enumerate(dict.keys(self)):
            self.__highlight(
                index, KEY, settled=0.5 if found and candidate == key else 0.0
            )

    def __remove(self, index: int) -> None:
        cell = self.mobject.items[index]
        self.mobject.items.remove(cell)
        self.queue(mn.FadeOut(cell))
        for following in self.mobject.items[index:]:
            self.queue_deferred(shift_by(following, mn.LEFT * CELL_SIZE))

    def __replace_value(self, index: int, value: object) -> None:
        _, _, val_square, val_label = self.mobject.items[index]
        val_square.set_fill(mn.WHITE, opacity=1.0)
        self.queue_deferred(fade_fill(val_square, 0.0))
        # The replacement is positioned at play time too: building it now would
        # aim at wherever the cell sits before the table lays out.
        self.queue_deferred(
            lambda: mn.Transform(
                val_label,
                mn.Text(str(value), font_size=24).move_to(val_square.get_center()),
            )
        )

    def __index_of(self, key: object) -> int:
        return list(dict.keys(self)).index(key)

    #
    # Dict methods
    #

    def __contains__(self, key):
        """Show the search that `in` performs, hit or miss.

        A miss that drew nothing would be indistinguishable from a frame the
        tool forgot to render, so both outcomes sweep; only the settle differs.
        """
        found = dict.__contains__(self, key)
        self.__search(key, found)
        return found

    def __getitem__(self, key):
        """Highlight the key-value pair for the given key."""
        if not dict.__contains__(self, key):
            raise KeyError(f"Key {key} not found.")
        index = self.__index_of(key)
        self.__highlight(index, KEY)
        self.__highlight(index, VALUE)
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if dict.__contains__(self, key):
            index = self.__index_of(key)
            dict.__setitem__(self, key, value)
            self.__highlight(index, KEY)
            self.__replace_value(index, value)
        else:
            dict.__setitem__(self, key, value)
            self._sync_placeholder()
            self.__draw(key, value)

    def __delitem__(self, key):
        if not dict.__contains__(self, key):
            raise KeyError(key)
        index = self.__index_of(key)
        dict.__delitem__(self, key)
        self.__remove(index)
        self._sync_placeholder()

    def items(self):
        """Return an animated list of key-value pairs."""
        for index, (key, value) in enumerate(dict.items(self)):
            self.__highlight(index, KEY)
            self.__highlight(index, VALUE)
            yield key, value

    def keys(self):
        """Return an animated list of keys."""
        for index, key in enumerate(dict.keys(self)):
            self.__highlight(index, KEY)
            yield key

    def values(self):
        """Return an animated list of values.

        Indexed by position, not by looking the value up: `list(...).index(v)`
        returns the first match, so a repeated value would re-highlight the
        earlier cell and never its own.
        """
        for index, value in enumerate(dict.values(self)):
            self.__highlight(index, VALUE)
            yield value

    def clear(self):
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
