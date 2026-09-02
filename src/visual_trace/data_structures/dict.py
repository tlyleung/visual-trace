import manim as mn


class Dict(dict):
    """
    A dict containing mobjects that can be animated by consuming the animation queue.
    """

    FADE_TIME = 0.2

    def __init__(self, **kwargs):
        super().__init__(kwargs)
        self.mobject = mn.VMobject()
        self.mobject.items = mn.VGroup()

        self.animation_queue = []
        for key, value in kwargs.items():
            self.animation_queue.extend(self.__append_animation(key, value))

        self.mobject.add(self.mobject.items)

    def __append_animation(self, key, value):
        key_square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
        key_label = mn.Text(str(key), font_size=24)

        val_square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
        val_label = mn.Text(str(value), font_size=24)

        # Stack key and value squares vertically
        key_square.next_to(val_square, mn.UP, buff=0)
        key_label.move_to(key_square.get_center())
        val_label.move_to(val_square.get_center())

        item = mn.VGroup(key_square, key_label, val_square, val_label)
        item.next_to(self.mobject.items, mn.RIGHT, buff=0)

        self.mobject.items.add(item)

        return [
            mn.Create(key_square),
            mn.FadeIn(key_label),
            mn.Create(val_square),
            mn.FadeIn(val_label),
        ]

    def __remove_animation(self, index):
        item = self.mobject.items[index]
        self.mobject.items.remove(item)

        animations = [mn.FadeOut(item)]

        for item in self.mobject.items[index:]:
            animations.append(item.animate.shift(mn.LEFT / 2))

        return animations

    def __highlight_key_animation(self, index):
        key_square, _, _, _ = self.mobject.items[index]
        key_square.set_fill(mn.WHITE, opacity=0.5)
        return [key_square.animate.set_fill(mn.WHITE, opacity=0.0)]

    def __highlight_val_animation(self, index):
        _, _, val_square, _ = self.mobject.items[index]
        val_square.set_fill(mn.WHITE, opacity=0.5)
        return [val_square.animate.set_fill(mn.WHITE, opacity=0.0)]

    def __replace_val_animation(self, index, value):
        _, _, val_square, val_label = self.mobject.items[index]
        val_square.set_fill(mn.WHITE, opacity=1.0)

        new_val_label = mn.Text(str(value), font_size=24).move_to(
            val_square.get_center()
        )

        return [
            val_square.animate.set_fill(mn.WHITE, opacity=0.0),
            mn.Transform(val_label, new_val_label),
        ]

    def __delitem__(self, key):
        index = list(super().keys()).index(key)
        super().__delitem__(key)
        self.animation_queue.extend(self.__remove_animation(index))

    def __getitem__(self, key):
        """Highlight the key-value pair for the given key."""
        if key in self:
            index = list(super().keys()).index(key)
            self.animation_queue.extend(self.__highlight_key_animation(index))
            self.animation_queue.extend(self.__highlight_val_animation(index))
            return super().__getitem__(key)
        else:
            raise KeyError(f"Key {key} not found.")

    def __setitem__(self, key, value):
        if key in self:
            index = list(super().keys()).index(key)
            super().__setitem__(key, value)
            self.animation_queue.extend(self.__highlight_key_animation(index))
            self.animation_queue.extend(self.__replace_val_animation(index, value))
        else:
            super().__setitem__(key, value)
            self.animation_queue.extend(self.__append_animation(key, value))

    def items(self):
        """Return an animated list of key-value pairs."""
        for key, value in super().items():
            index = list(super().keys()).index(key)
            self.animation_queue.extend(self.__highlight_key_animation(index))
            self.animation_queue.extend(self.__highlight_val_animation(index))
            yield key, value

    def keys(self):
        """Return an animated list of keys."""
        for key in super().keys():
            index = list(super().keys()).index(key)
            self.animation_queue.extend(self.__highlight_key_animation(index))
            yield key

    def values(self):
        """Return an animated list of values."""
        for value in super().values():
            index = list(super().values()).index(value)
            self.animation_queue.extend(self.__highlight_val_animation(index))
            yield value

    def clear(self):
        """Clear all items from the dict and animate their removal."""
        animations = []
        for item in self.mobject.items:
            animations.extend([mn.FadeOut(item)])
        self.mobject.items = mn.VGroup()
        self.animation_queue.extend(animations)
        super().clear()
