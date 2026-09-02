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

                # if hasattr(v, "pending_operations"):
                #     scene.pending_operations.extend(v.pending_operations)
                #     v.pending_operations.clear()

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
    for name in scene.variables.keys():
        if name in local_vars:
            v = local_vars[name]

            if hasattr(v, "mobject"):
                mobject = v.mobject

                if hasattr(v, "animation_queue"):
                    scene.animation_queue.extend(v.animation_queue)
                    # scene.animation_queue.append(mn.AnimationGroup(*v.animation_queue))
                    v.animation_queue.clear()

                if hasattr(v, "pending_operations"):
                    scene.pending_operations.extend(v.pending_operations)
                    v.pending_operations.clear()

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
    return table
