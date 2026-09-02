import manim as mn


class List(list):
    """
    A list containing an mobject that can be animated by consuming the animation queue.
    """

    FADE_TIME = 0.2

    def __init__(self, *args):
        super().__init__(args)
        self.args = args
        self.mobject = mn.VGroup()
        self.animation_queue = []
        self.pending_items = []
        self.pending_operations = []

        for item in args:
            self.__append_animation(item)

    def reset(self):
        """Return a fresh instance with the same initial arguments."""
        return type(self)(*self.args)

    #
    # Animation methods
    #

    # def __append_animation(self, item):
    #     square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
    #     label = mn.Text(str(item), font_size=24)
    #     item = mn.VGroup(square, label)

    #     if len(self.pending_items) > 0:
    #         item.next_to(self.pending_items[-1][1], mn.RIGHT, buff=0)
    #     elif len(self.mobject) > 0:
    #         item.next_to(self.mobject[-1], mn.RIGHT, buff=0)

    #     self.animation_queue.extend([mn.Create(square), mn.FadeIn(label)])
    #     self.pending_items.append((self.mobject, item))

    def __append_animation(self, item):
        square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
        label = mn.Text(str(item), font_size=24)
        item = mn.VGroup(square, label)

        if len(self.mobject) > 0:
            item.next_to(self.mobject[-1], mn.RIGHT, buff=0)

        index = len(self.animation_queue)
        item.shift(mn.RIGHT * (index * 0.5))

        animation = mn.AnimationGroup(mn.Create(square), mn.FadeIn(label))
        self.animation_queue.append(animation)
        self.pending_operations.append(lambda: self.mobject.add(item))

    # def __append_animation(self, item):
    #     square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
    #     label = mn.Text(str(item), font_size=24)
    #     item = mn.VGroup(square, label)

    #     index = len(self.mobject) + len(self.pending_operations)
    #     item.shift(mn.RIGHT * (index * 0.7))

    #     # animation = mn.AnimationGroup(mn.Create(square), mn.FadeIn(label))
    #     # self.animation_queue.append(animation)
    #     self.animation_queue.extend([mn.Create(square), mn.FadeIn(label)])
    #     self.pending_operations.append(lambda: self.mobject.add(item))

    # def __insert_animation(self, item, index):
    #     if index < 0:
    #         index = (len(self.mobject) + index) % len(self.mobject)
    #     elif index > len(self.mobject):
    #         index = len(self.mobject)  # clamp

    #     square = mn.Square(side_length=0.5, fill_color=mn.WHITE, fill_opacity=0.0)
    #     label = mn.Text(str(item), font_size=24)
    #     item = mn.VGroup(square, label)

    #     # If the item is being inserted at the end
    #     if index == len(self.mobject):
    #         if len(self.mobject) > 0:
    #             # Place it to the right of the last item
    #             square.next_to(self.mobject[-2], mn.RIGHT, buff=0)
    #         else:
    #             # If it's the first item, align it to the left edge
    #             square.to_edge(mn.LEFT)
    #     else:
    #         # Place the square to the left of the item at the given index
    #         square.next_to(self.mobject[index], mn.LEFT, buff=0)

    #     # label.move_to(square.get_center())

    #     # item = mn.VGroup(square, label)
    #     # self.mobject.insert(index, item)

    #     animations = [mn.Create(square), mn.FadeIn(label)]

    #     for item in self.mobject[index:]:
    #         animations.append(item.animate.shift(mn.RIGHT / 2))

    #     return animations

    #
    # List methods
    #

    def append(self, value: any) -> None:
        """Animate adding a new square and label."""
        super().append(value)
        self.__append_animation(value)
