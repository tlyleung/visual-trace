import manim as mn


def create_table(scene: mn.Scene) -> mn.MobjectTable:
    table = mn.MobjectTable(
        [
            [mn.Text(name, font_size=24), mn.Text("Undefined", font_size=24)]
            for name in scene.variables.keys()
        ],
        line_config={"stroke_width": 0},
        arrange_in_grid_config={"cell_alignment": mn.LEFT},
    )
    table.align_to(scene.right_col, mn.LEFT)
    return table


def update_table(local_vars: dict, scene: mn.Scene) -> list[mn.Animation]:
    for row in scene.table.get_rows():
        name = row[0].get_text()
        old_cell = row[1]
        if name in local_vars:
            v = local_vars[name]

            if hasattr(v, "mobject"):
                new_cell = v.mobject

                if hasattr(v, "animation_queue"):
                    scene.animation_queue.extend(v.animation_queue)
                    v.animation_queue.clear()


            else:
                new_cell = mn.Text(str(v), font_size=24)

        else:
            new_cell = mn.Text("Undefined", font_size=24)

        # Only swap in the new cell if it is different from the old one
        if new_cell is not old_cell:
            new_cell.move_to(old_cell, mn.LEFT)
            old_cell.become(new_cell)


def create_table111(local_vars: dict, scene: mn.Scene) -> mn.MobjectTable:
    data = []
    applied = 0
    for name in scene.variables.keys():
        if name in local_vars:
            v = local_vars[name]

            if hasattr(v, "mobject"):
                if hasattr(v, "animation_queue"):
                    scene.animation_queue.extend(v.animation_queue)
                    v.animation_queue.clear()

                # Apply deferred tree mutations before the table lays the
                # mobject out. Carrying them past this point means the table
                # arranges an empty group, and the contents then materialise at
                # the origin instead of in the cell they were assigned.
                if hasattr(v, "pending_operations"):
                    for operation in v.pending_operations:
                        operation()
                    applied += len(v.pending_operations)
                    v.pending_operations.clear()

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
    scene.applied_operations = applied
    return table


def refresh_table(scene: mn.Scene, local_vars: dict) -> mn.MobjectTable:
    """Update the displayed variables table to match the current locals.

    Swaps the mobject in rather than `become`-ing the old one onto the new.
    `become` aligns the two families by padding the shorter one, which strands
    zero-area points at the origin whenever a cell empties; nothing renders
    there, but every bounding box that contains them is wrong. Swapping is
    equivalent on screen -- this runs outside any animation, so the table
    updates instantly either way.
    """
    new_table = create_table111(local_vars, scene)
    scene.remove(scene.table)
    scene.add(new_table)
    scene.table = new_table
    return new_table
