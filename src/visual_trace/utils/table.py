import manim as mn

from ..data_structures.base import Animated

# Comfortably clears the tallest cell a structure draws, so a row never
# has to grow and the rows below never have to move.
ROW_PITCH = 1.15


def build_table(
    scene: mn.Scene, local_vars: dict
) -> tuple[mn.MobjectTable, int]:
    """Build the variables table for the current locals.

    Called with no locals it renders every row "Undefined", which is what the
    scene wants before the traced function has run.
    """
    data = []
    applied = 0
    deferred = []
    for name in scene.variables.keys():
        if name in local_vars:
            v = local_vars[name]

            if isinstance(v, Animated):
                deferred.extend(v.drain_animations())
                # Apply deferred tree mutations before the table lays the
                # mobject out. Carrying them past this point means the table
                # arranges an empty group, and the contents then materialise at
                # the origin instead of in the cell they were assigned.
                applied += v.apply_pending()
                mobject = v.mobject

            else:
                mobject = mn.Text(str(v), font_size=24)

        else:
            mobject = mn.Text("Undefined", font_size=24)

        data.append([mn.Text(name, font_size=24), mobject])

    table = mn.MobjectTable(
        data,
        line_config={"stroke_width": 0},
        arrange_in_grid_config={"cell_alignment": mn.LEFT},
    )
    table.align_to(scene.right_col, mn.LEFT)
    _pin_rows(table)

    # Now that every cell is in its final position, realise the animations that
    # had to wait for it. Anything already an Animation reads the mobject's
    # current state when it begins and is safe to pass through.
    scene.animation_queue.extend(realize_animations(deferred))
    return table, applied


def realize_animations(deferred: list) -> list:
    """Build queued animations. Only call once every cell is in its final place.

    The structures queue builders rather than animations precisely so this can
    happen after the layout -- see `data_structures.base`.
    """
    return [build() for build in deferred]


def refresh_table(
    scene: mn.Scene, local_vars: dict
) -> tuple[mn.MobjectTable, int]:
    """Update the displayed variables table to match the current locals.

    Swaps the mobject in rather than `become`-ing the old one onto the new.
    `become` aligns the two families by padding the shorter one, which strands
    zero-area points at the origin whenever a cell empties; nothing renders
    there, but every bounding box that contains them is wrong. Swapping is
    equivalent on screen -- this runs outside any animation, so the table
    updates instantly either way.
    """
    new_table, applied = build_table(scene, local_vars)
    scene.remove(scene.table)
    scene.add(new_table)
    scene.table = new_table
    return new_table, applied


def _pin_rows(table: mn.MobjectTable) -> None:
    """Put every row label at a fixed y, centred as a block.

    MobjectTable sizes each row to its tallest cell, so a value changing from
    text to a drawn structure resizes that row and the centred table shifts
    every other row with it -- the whole panel appears to jump. Pinning to the
    labels keeps the layout independent of what the cells happen to hold.
    """
    rows = table.get_rows()
    span = (len(rows) - 1) * ROW_PITCH
    for index, row in enumerate(rows):
        target = span / 2 - index * ROW_PITCH
        row.shift(mn.UP * (target - float(row[0].get_center()[1])))
