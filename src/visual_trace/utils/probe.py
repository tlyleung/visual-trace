"""Geometric assertions over a settled Manim scene.

Most visual bugs in this project are geometric: something sits in the wrong
place, overlaps something else, runs off screen, or is spaced wrong. Those are
cheaper and far more reliable to check numerically than by eye, so the probe
runs a set of invariants after each animation step and reports pass/fail.

Every read here is side-effect free -- notably it never calls the overridden
``items``/``keys``/``values`` on ``Dict``, which would push spurious animations.
"""

from typing import Any

import manim as mn
import numpy as np

from ..data_structures.base import Animated

TOL = 0.02


def _renders(mobject) -> bool:
    """Whether a leaf actually puts ink on the frame."""
    stroke = float(mobject.get_stroke_width() or 0) * float(
        mobject.get_stroke_opacity() or 0
    )
    return stroke > 0 or float(mobject.get_fill_opacity() or 0) > 0


def visible_extent(mobject) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """((left, right), (bottom, top)) of the parts that actually render, or None.

    Manim bounding boxes count anything with points, visible or not, and this
    project keeps tripping over that: MobjectTable draws its grid with
    ``stroke_width=0`` lines that run far wider than any cell, `become` strands
    zero-area points at the origin, and an empty group collapses there too. Every
    one of those made a correct frame look wrong.

    Both axes come out of one pass over the point cloud: the code listing alone
    is ~61k points, and measuring it per axis doubled the cost of every box.
    """
    arrays = [
        m.points
        for m in mobject.family_members_with_points()
        if len(m.points) and _renders(m)
    ]
    if not arrays:
        return None
    stacked = np.vstack(arrays)
    low = stacked.min(axis=0)
    high = stacked.max(axis=0)
    return (float(low[0]), float(high[0])), (float(low[1]), float(high[1]))


def visible_range(mobject, axis: int) -> tuple[float, float] | None:
    """Extent of the rendering parts along one axis. See `visible_extent`."""
    extent = visible_extent(mobject)
    return None if extent is None else extent[axis]


def x_range(m) -> tuple[float, float]:
    return float(m.get_corner(mn.UL)[0]), float(m.get_corner(mn.DR)[0])


def y_range(m) -> tuple[float, float]:
    """Return ``(bottom, top)``."""
    return float(m.get_corner(mn.DR)[1]), float(m.get_corner(mn.UL)[1])


def bbox(m) -> dict:
    """Recorded bounds, measured on ink wherever there is any.

    Raw Manim bounds count invisible geometry, which has produced a false
    reading every time it has come up here. Falls back to the raw box only when
    nothing in the mobject renders, so an empty container still reports a
    position.
    """
    extent = visible_extent(m)
    if extent is None:
        left, right = x_range(m)
        bottom, top = y_range(m)
    else:
        (left, right), (bottom, top) = extent
    return {
        "left": round(left, 4),
        "right": round(right, 4),
        "bottom": round(bottom, 4),
        "top": round(top, 4),
        "width": round(right - left, 4),
        "height": round(top - bottom, 4),
    }


def overlap(a, b) -> tuple[float, float]:
    """Overlap extent on each axis. Positive on both axes means intersecting."""
    ax0, ax1 = x_range(a)
    bx0, bx1 = x_range(b)
    ay0, ay1 = y_range(a)
    by0, by1 = y_range(b)
    return min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def _tracked(local_vars: dict, container: type = object) -> list[tuple[str, Any]]:
    """Animated structures in scope, optionally narrowed to one container type."""
    return [
        (n, v)
        for n, v in local_vars.items()
        if isinstance(v, Animated) and isinstance(v, container)
    ]


def _drawn(value) -> bool:
    mobject = value.mobject
    return bool(len(mobject.family_members_with_points()))


#
# Invariants. Each takes (scene, lineno, local_vars) and returns checks.
#


def highlight_on_row(scene, lineno, local_vars) -> list[dict]:
    """The band must sit on the executing row, and on no other.

    Checked against the rendered line-number glyphs rather than against the
    positioning helper, so the invariant cannot be satisfied by agreeing with a
    bug in that helper. Line numbers are also the only per-row geometry that is
    trustworthy -- see `utils/highlight.row_center` for why `code_lines` is not.
    """
    numbers = scene.code.line_numbers
    hb, ht = y_range(scene.highlight)
    nb, nt = y_range(numbers[lineno])
    checks = [
        _check(
            "highlight_on_row",
            ht >= nt - TOL and hb <= nb + TOL,
            f"band y=[{hb:.3f},{ht:.3f}] vs line number {lineno} y=[{nb:.3f},{nt:.3f}]",
        )
    ]
    for neighbour in (lineno - 1, lineno + 1):
        if not 0 <= neighbour < len(numbers):
            continue
        jb, jt = y_range(numbers[neighbour])
        overlap = min(ht, jt) - max(hb, jb)
        checks.append(
            _check(
                "highlight_clears_neighbours",
                overlap <= TOL,
                f"band overlaps line number {neighbour} by {overlap:.3f}",
            )
        )
    return checks


def highlight_row_height(scene, lineno, local_vars) -> list[dict]:
    """One row tall. Guards against the band being sized once and never again."""
    numbers = scene.code.line_numbers
    if len(numbers) < 2:
        return []
    span = abs(
        float(numbers[-1].get_center()[1]) - float(numbers[0].get_center()[1])
    )
    pitch = span / (len(numbers) - 1)
    height = float(scene.highlight.height)
    return [
        _check(
            "highlight_row_height",
            abs(height - pitch) <= TOL,
            f"band height {height:.3f} vs row pitch {pitch:.3f}",
        )
    ]


def highlight_spans_code_width(scene, lineno, local_vars) -> list[dict]:
    hl, hr = x_range(scene.highlight)
    bl, br = x_range(scene.code.background)
    ok = hl <= bl + TOL and hr >= br - TOL
    return [
        _check(
            "highlight_spans_code_width",
            ok,
            f"highlight x=[{hl:.3f},{hr:.3f}] vs background x=[{bl:.3f},{br:.3f}]",
        )
    ]


def panels_disjoint(scene, lineno, local_vars) -> list[dict]:
    code = visible_range(scene.code, axis=0)
    table = visible_range(scene.table, axis=0)
    if code is None or table is None:
        return []
    ox = min(code[1], table[1]) - max(code[0], table[0])
    code_y, table_y = y_range(scene.code), y_range(scene.table)
    oy = min(code_y[1], table_y[1]) - max(code_y[0], table_y[0])
    ok = not (ox > TOL and oy > TOL)
    return [
        _check(
            "panels_disjoint",
            ok,
            f"code/table overlap x={ox:.3f} y={oy:.3f}",
        )
    ]


def structures_inside_table(scene, lineno, local_vars) -> list[dict]:
    """Animated structures are table cells, so they must sit inside the table.

    A structure whose group is empty when the table lays out gets arranged as
    nothing, and its contents then materialise at the world origin rather than in
    the cell they were assigned -- which is why `build_table` applies the
    deferred tree mutations before it builds the table.
    """
    checks = []
    tl, tr = x_range(scene.table)
    tb, tt = y_range(scene.table)
    for name, value in _tracked(local_vars):
        if not _drawn(value):
            continue
        left, right = x_range(value.mobject)
        bottom, top = y_range(value.mobject)
        ok = (left >= tl - TOL and right <= tr + TOL
              and bottom >= tb - TOL and top <= tt + TOL)
        checks.append(
            _check(
                "structures_inside_table",
                ok,
                f"{name} x=[{left:.3f},{right:.3f}] y=[{bottom:.3f},{top:.3f}] "
                f"vs table x=[{tl:.3f},{tr:.3f}] y=[{tb:.3f},{tt:.3f}]",
            )
        )
    return checks


def structures_clear_of_code(scene, lineno, local_vars) -> list[dict]:
    checks = []
    # Measured once: the code listing is a ~61k-point family, so re-measuring it
    # per structure dominated the whole probe pass.
    code_x, code_y = x_range(scene.code), y_range(scene.code)
    for name, value in _tracked(local_vars):
        if not _drawn(value):
            continue
        value_x, value_y = x_range(value.mobject), y_range(value.mobject)
        ox = min(code_x[1], value_x[1]) - max(code_x[0], value_x[0])
        oy = min(code_y[1], value_y[1]) - max(code_y[0], value_y[0])
        checks.append(
            _check(
                "structures_clear_of_code",
                not (ox > TOL and oy > TOL),
                f"{name} overlaps code panel by x={ox:.3f} y={oy:.3f}",
            )
        )
    return checks


def within_frame(scene, lineno, local_vars) -> list[dict]:
    half_w = mn.config.frame_width / 2
    half_h = mn.config.frame_height / 2
    checks = []
    targets = {"code": scene.code, "highlight": scene.highlight, "table": scene.table}
    for name, value in _tracked(local_vars):
        if len(value.mobject.items):
            targets[f"struct:{name}"] = value.mobject
    for name, m in targets.items():
        horizontal = visible_range(m, axis=0)
        vertical = visible_range(m, axis=1)
        if horizontal is None or vertical is None:
            continue
        left, right = horizontal
        bottom, top = vertical
        ok = (
            left >= -half_w - TOL
            and right <= half_w + TOL
            and bottom >= -half_h - TOL
            and top <= half_h + TOL
        )
        if not ok:
            checks.append(
                _check(
                    "within_frame",
                    False,
                    f"{name} x=[{left:.3f},{right:.3f}] y=[{bottom:.3f},{top:.3f}] "
                    f"exceeds frame +-({half_w:.3f},{half_h:.3f})",
                )
            )
    if not checks:
        checks.append(_check("within_frame", True, f"{len(targets)} mobjects in frame"))
    return checks


def cell_count_matches(scene, lineno, local_vars) -> list[dict]:
    """One drawn cell per element, once ``pending_operations`` have drained."""
    checks = []
    for name, value in _tracked(local_vars):
        drawn = len(value.mobject.items)
        ok = drawn == len(value)
        checks.append(
            _check(
                "cell_count_matches",
                ok,
                f"{name}: {drawn} drawn vs {len(value)} elements",
            )
        )
    return checks


def cell_values_match(scene, lineno, local_vars) -> list[dict]:
    """Each cell must show what the container actually holds.

    `cell_count_matches` only counts, so an operation that changes values without
    changing length -- an assignment, a swap, a sort -- left the drawing showing
    stale data with every invariant green. That is worse than drawing nothing.
    """
    checks = []
    for name, value in _tracked(local_vars):
        drawn = value.drawn_values()
        expected = value.expected_values()
        checks.append(
            _check(
                "cell_values_match",
                drawn == expected,
                f"{name}: drawn {drawn} vs held {expected}",
            )
        )
    return checks


def cells_contiguous(scene, lineno, local_vars) -> list[dict]:
    """Adjacent cells should touch; a growing gap means positioning is wrong."""
    checks = []
    for name, value in _tracked(local_vars):
        items = list(value.mobject.items)
        if len(items) < 2:
            continue
        gaps = []
        for prev, cur in zip(items, items[1:]):
            gaps.append(x_range(cur)[0] - x_range(prev)[1])
        worst = max(gaps, key=abs)
        ok = abs(worst) <= TOL
        checks.append(
            _check(
                "cells_contiguous",
                ok,
                f"{name}: gaps={[round(g, 3) for g in gaps]} worst={worst:.3f}",
            )
        )
    return checks


def table_rows_disjoint(scene, lineno, local_vars) -> list[dict]:
    rows = list(scene.table.get_rows())
    bad = []
    for i, (a, b) in enumerate(zip(rows, rows[1:])):
        _, oy = overlap(a, b)
        if oy > TOL:
            bad.append(f"rows {i}/{i + 1} overlap y={oy:.3f}")
    ok = not bad
    return [
        _check(
            "table_rows_disjoint",
            ok,
            "; ".join(bad) if bad else f"{len(rows)} rows, no vertical overlap",
        )
    ]


def table_row_count(scene, lineno, local_vars) -> list[dict]:
    rows = len(scene.table.get_rows())
    expected = len(scene.variables)
    ok = rows == expected
    return [
        _check("table_row_count", ok, f"{rows} rows vs {expected} tracked variables")
    ]


INVARIANTS = [
    highlight_on_row,
    highlight_row_height,
    structures_inside_table,
    structures_clear_of_code,
    highlight_spans_code_width,
    panels_disjoint,
    within_frame,
    cell_count_matches,
    cell_values_match,
    cells_contiguous,
    table_rows_disjoint,
    table_row_count,
]


def probe_step(scene, lineno: int, local_vars: dict) -> dict:
    """Snapshot geometry and evaluate every invariant for a settled step."""
    geometry = {
        "code": bbox(scene.code),
        "code_background": bbox(scene.code.background),
        "highlight": bbox(scene.highlight),
        "table": bbox(scene.table),
        "line": bbox(scene.code.code_lines[lineno]),
    }
    for name, value in _tracked(local_vars):
        if _drawn(value):
            geometry[f"struct:{name}"] = bbox(value.mobject)

    # Row labels never legitimately move. Recorded so a cross-step check can
    # catch layout drift, which no single-step invariant can see.
    rows = scene.table.get_rows()
    for index, name in enumerate(scene.variables):
        if index < len(rows):
            geometry[f"label:{name}"] = bbox(rows[index][0])

    checks: list[dict] = []
    for invariant in INVARIANTS:
        try:
            checks.extend(invariant(scene, lineno, local_vars))
        except Exception as exc:
            # A probe that blows up must not take the render down with it.
            checks.append(
                _check(invariant.__name__, None, f"probe error: {type(exc).__name__}: {exc}")
            )
    return {"geometry": geometry, "checks": checks}
