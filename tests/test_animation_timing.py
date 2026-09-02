"""When an animation plays, relative to the line that caused it.

`sys.settrace` fires a `line` event *before* the line runs, so an append on line
N is only visible to the tracer at line N+1's event. If that event moves the
highlight and plays the append's animation together, the square appears just as
the highlight lands on N+1 -- the effect is attributed to the wrong line.

These drive the scene through the real tracer with a stub that records where the
highlight was at the moment of each play, instead of rendering.
"""

import inspect

import manim as mn
from manim.animation.animation import prepare_animation

from visual_trace.data_structures.list import List
from visual_trace.utils.highlight import create_highlight, row_center
from visual_trace.utils.table import create_table
from visual_trace.utils.tracing import start_tracing


class RecordingScene:
    """Drives the tracer without a renderer, logging each play() call."""

    def __init__(self, func):
        self.func = func
        self.source_lines, self.start_line_number = inspect.getsourcelines(func)
        self.code = mn.Code(
            code_string=inspect.getsource(func),
            tab_width=4,
            background="window",
            language="Python",
        )
        self.code.scale(0.5)
        self.highlight = create_highlight(1, self.code)
        self.right_col = mn.Rectangle(
            width=mn.config.frame_width / 2,
            height=mn.config.frame_height,
            stroke_width=0,
        )
        self.right_col.to_edge(mn.RIGHT, buff=0)
        self.animation_queue = []
        self.variables = {}
        self.trace_pass = 2
        self.step = 0
        self.trace_log = None
        self.plays: list[dict] = []

    def play(self, *animations):
        # `.animate` yields a builder; Scene.play is what turns it into an
        # Animation, so the stub has to do the same before inspecting it.
        prepared = [prepare_animation(a) for a in animations]
        before = float(self.highlight.get_center()[1])
        # Advance geometry to each animation's end state, as a render would.
        for animation in prepared:
            animation.begin()
            animation.interpolate(1)
            animation.finish()
        self.plays.append(
            {
                "before": before,
                "after": float(self.highlight.get_center()[1]),
                "kinds": [type(a).__name__ for a in prepared],
            }
        )


def drive(func, *args):
    """Mirror Animation.construct: harvest names, reset, then animate."""
    scene = RecordingScene(func)
    _, scene.variables = start_tracing(scene, func, *args)
    scene.table = create_table(scene)
    # Without this the second pass inherits the first pass's mutations and
    # its leftover animation queue, exactly as the real scene would.
    args = tuple(a.reset() if hasattr(a, "reset") else a for a in args)
    scene.step = 0
    scene.plays.clear()
    start_tracing(scene, func, *args)
    return scene


def appends_then_returns(nums):
    nums.append(1)
    nums.append(2)
    return nums


def test_content_animates_while_its_own_line_is_highlighted():
    """The square for `nums.append(1)` must appear while line 1 is highlighted."""
    scene = drive(appends_then_returns, List())
    content = [p for p in scene.plays if any("Method" not in k for k in p["kinds"])]
    assert content, f"no content animation was ever played; plays={scene.plays}"

    expected = float(row_center(scene.code, 1)[1])
    first = content[0]
    assert abs(first["before"] - expected) < 0.02, (
        f"line 1's square started drawing with the highlight at "
        f"y={first['before']:.3f}, but line 1 is at y={expected:.3f}"
    )
    # Sampling only the start is not enough: the original bug moved the
    # highlight *during* this very play, so it began on the right line and
    # ended on the next one.
    assert abs(first["after"] - expected) < 0.02, (
        f"the highlight moved to y={first['after']:.3f} while line 1's square "
        f"was still being drawn; line 1 is at y={expected:.3f}"
    )


def test_highlight_moves_separately_from_content():
    """A play must not both move the highlight and animate content."""
    scene = drive(appends_then_returns, List())
    mixed = [
        p for p in scene.plays
        if any("Method" in k for k in p["kinds"])
        and any("Method" not in k for k in p["kinds"])
    ]
    assert not mixed, f"plays mixing highlight movement with content: {mixed}"
