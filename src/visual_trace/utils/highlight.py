import manim as mn

HIGHLIGHT_OFFSET = mn.DOWN * 0.035


def create_highlight(lineno: int, code: mn.Code) -> mn.SurroundingRectangle:
    if not 0 <= lineno < len(code.code_lines):
        raise IndexError(f"Line number {lineno} is out of range.")

    highlight = mn.SurroundingRectangle(
        code.code_lines[lineno],
        stroke_width=0,
        fill_color=mn.BLUE,
        fill_opacity=0.5,
        buff=0,
    )
    highlight.stretch_to_fit_width(code.background.width)
    highlight.align_to(code.background, mn.LEFT)
    highlight.shift(HIGHLIGHT_OFFSET)  # add offset for alignment
    return highlight
