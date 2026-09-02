import numpy as np

import manim as mn


def _line_numbers(code: mn.Code) -> mn.Paragraph:
    numbers = getattr(code, "line_numbers", None)
    if numbers is None or not len(numbers):
        raise ValueError(
            "Highlight positioning needs the listing's line numbers; "
            "construct mn.Code with them enabled."
        )
    return numbers


def row_pitch(code: mn.Code) -> float:
    """Vertical distance between consecutive rows of the listing.

    Taken end to end rather than between neighbours, so per-digit glyph
    variation cannot accumulate into the pitch.
    """
    numbers = _line_numbers(code)
    if len(numbers) < 2:
        return float(numbers[0].height)
    first = float(numbers[0].get_center()[1])
    last = float(numbers[-1].get_center()[1])
    return abs(last - first) / (len(numbers) - 1)


def row_center(code: mn.Code, lineno: int) -> np.ndarray:
    """Centre point of row ``lineno``, spanning the full listing width.

    Anchored to the line-number ladder, which is uniform. The glyph bounding
    boxes in ``code.code_lines`` cannot be used for this: Manim renders leading
    indentation as zero-size Dots, and when a blank line precedes a row those
    Dots are parked at the blank row's y -- inflating the row's bounding box
    across two rows. A blank line's own box collapses to the origin.
    """
    numbers = _line_numbers(code)
    if not 0 <= lineno < len(numbers):
        raise IndexError(f"Line number {lineno} is out of range.")
    y = float(numbers[0].get_center()[1]) - lineno * row_pitch(code)
    return np.array([code.background.get_center()[0], y, 0.0])


def create_highlight(lineno: int, code: mn.Code) -> mn.Rectangle:
    """A band one row tall, spanning the listing, sitting on ``lineno``."""
    highlight = mn.Rectangle(
        width=code.background.width,
        height=row_pitch(code),
        stroke_width=0,
        fill_color=mn.BLUE,
        fill_opacity=0.5,
    )
    highlight.move_to(row_center(code, lineno))
    return highlight
