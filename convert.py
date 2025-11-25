import json
import math
import sys
import os

import ezdxf
from ezdxf import units

SCALE_TO_MM = 10.0


def to_mm_point(p):
    return p["x"] * SCALE_TO_MM, p["y"] * SCALE_TO_MM


def update_extents(extents, x, y):
    if extents is None:
        return [x, y, x, y]
    if x < extents[0]:
        extents[0] = x
    if y < extents[1]:
        extents[1] = y
    if x > extents[2]:
        extents[2] = x
    if y > extents[3]:
        extents[3] = y
    return extents


def ensure_layer(doc, name, color=None):
    if name in doc.layers:
        if color is not None:
            doc.layers.get(name).dxf.color = color
        return
    if color is None:
        doc.layers.add(name)
    else:
        doc.layers.add(name, color=color)


def element_belongs_to_plan(obj, plan_code):
    if plan_code is None:
        return True
    if not isinstance(obj, dict):
        return True
    p = obj.get("plan")
    if isinstance(p, str):
        return p == plan_code
    if isinstance(p, dict):
        v = p.get(plan_code)
        return bool(v)
    return True


def add_wall_entities(doc, msp, plan, extents, plan_code=None):
    walls = plan.get("walls", {})
    for wall_id, wall in walls.items():
        if wall.get("role") != "wall":
            continue
        if not element_belongs_to_plan(wall, plan_code):
            continue

        l1 = wall.get("l1")
        l2 = wall.get("l2")
        r1 = wall.get("r1")
        r2 = wall.get("r2")
        if not (l1 and l2 and r1 and r2):
            continue

        pts_plan = [l1, l2, r2, r1]
        pts = []
        for p in pts_plan:
            x_mm, y_mm = to_mm_point(p)
            pts.append((x_mm, y_mm))
            extents = update_extents(extents, x_mm, y_mm)

        plan_letter = wall.get("plan")
        if isinstance(plan_letter, str):
            layer = f"Walls_{plan_letter.upper()}"
        else:
            layer = "Walls"

        ensure_layer(doc, layer, color=7)
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

        holes = wall.get("holes", {})
        for hole_id, hole in holes.items():
            if not element_belongs_to_plan(hole, plan_code):
                continue
            pts_hole = []
            if "polygon" in hole:
                for pt in hole["polygon"]:
                    x_mm, y_mm = to_mm_point(pt)
                    pts_hole.append((x_mm, y_mm))
                    extents = update_extents(extents, x_mm, y_mm)
            else:
                hl1 = hole.get("l1")
                hl2 = hole.get("l2")
                hr1 = hole.get("r1")
                hr2 = hole.get("r2")
                if hl1 and hl2 and hr1 and hr2:
                    for pt in [hl1, hl2, hr2, hr1]:
                        x_mm, y_mm = to_mm_point(pt)
                        pts_hole.append((x_mm, y_mm))
                        extents = update_extents(extents, x_mm, y_mm)

            if not pts_hole:
                continue

            group = (hole.get("group") or "").lower()
            if "door" in group:
                layer_h = "Doors"
            elif "window" in group:
                layer_h = "Windows"
            else:
                layer_h = "Openings"

            ensure_layer(doc, layer_h, color=3)
            msp.add_lwpolyline(pts_hole, close=True, dxfattribs={"layer": layer_h})

    return extents


def add_room_entities(doc, msp, plan, extents, plan_code=None):
    rooms = plan.get("rooms2", {})
    if not isinstance(rooms, dict):
        return extents

    ensure_layer(doc, "Rooms", color=252)
    ensure_layer(doc, "Rooms_Text", color=7)

    for room_id, room in rooms.items():
        if not element_belongs_to_plan(room, plan_code):
            continue

        polygon = room.get("polygon") or room.get("points") or []
        if not polygon:
            continue

        pts = []
        sx = sy = 0.0
        for pt in polygon:
            x_mm, y_mm = to_mm_point(pt)
            pts.append((x_mm, y_mm))
            sx += x_mm
            sy += y_mm
            extents = update_extents(extents, x_mm, y_mm)

        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "Rooms"})

        cx = sx / len(pts)
        cy = sy / len(pts)
        extents = update_extents(extents, cx, cy)

        name = (room.get("name") or "").strip()
        area = room.get("area")
        if area is not None:
            try:
                area_val = float(area)
                if name and name.lower() != "none":
                    label = f"{name} {area_val:.2f} m2"
                else:
                    label = f"{area_val:.2f} m2"
            except Exception:
                label = name or ""
        else:
            label = name

        if label:
            height = 150.0
            txt = msp.add_text(
                label,
                dxfattribs={"height": height, "layer": "Rooms_Text"},
            )
            txt.dxf.insert = (cx, cy, 0.0)

    return extents


def add_items_entities(doc, msp, plan, extents, plan_code=None):
    items = plan.get("items", {})
    if not isinstance(items, dict):
        return extents

    ensure_layer(doc, "Furniture", color=2)

    for item_id, item in items.items():
        if not element_belongs_to_plan(item, plan_code):
            continue

        w = item.get("width")
        h = item.get("height")
        if w is None or h is None:
            continue

        cx = cy = None
        icon_center = item.get("icon_center")
        pc = item.get("pc")
        if icon_center and "x" in icon_center and "y" in icon_center:
            cx, cy = to_mm_point(icon_center)
        elif pc and "x" in pc and "y" in pc:
            cx, cy = to_mm_point(pc)
        if cx is None or cy is None:
            continue

        angle = float(item.get("angle", 0.0))
        w2 = float(w) * SCALE_TO_MM / 2.0
        h2 = float(h) * SCALE_TO_MM / 2.0

        corners = [(-w2, h2), (w2, h2), (w2, -h2), (-w2, -h2)]

        theta = math.radians(angle)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        pts = []
        for dx, dy in corners:
            rx = dx * cos_t - dy * sin_t
            ry = dx * sin_t + dy * cos_t
            x = cx + rx
            y = cy + ry
            pts.append((x, y))
            extents = update_extents(extents, x, y)

        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "Furniture"})
    return extents


def add_pipes_entities(doc, msp, plan, extents, plan_code=None):
    pipes = plan.get("pipes_ventilation", {})
    if not isinstance(pipes, dict):
        return extents

    ensure_layer(doc, "Ventilation", color=4)

    for pid, pipe in pipes.items():
        if not element_belongs_to_plan(pipe, plan_code):
            continue
        verts = pipe.get("vertexes") or pipe.get("vertices") or []
        if not verts:
            continue
        pts = []
        for v in verts:
            p = v.get("point")
            if not p:
                continue
            x_mm, y_mm = to_mm_point(p)
            pts.append((x_mm, y_mm))
            extents = update_extents(extents, x_mm, y_mm)
        if len(pts) < 2:
            continue
        msp.add_lwpolyline(pts, close=False, dxfattribs={"layer": "Ventilation"})
    return extents


def add_rulers_entities(doc, msp, plan, extents, plan_code=None):
    rulers = plan.get("rulers", {})
    if not isinstance(rulers, dict):
        return extents

    ensure_layer(doc, "Rulers", color=5)

    for rid, ruler in rulers.items():
        if not element_belongs_to_plan(ruler, plan_code):
            continue
        p1 = ruler.get("p1")
        p2 = ruler.get("p2")
        if not p1 or not p2:
            continue
        x1, y1 = to_mm_point(p1)
        x2, y2 = to_mm_point(p2)
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "Rulers"})
        extents = update_extents(extents, x1, y1)
        extents = update_extents(extents, x2, y2)
    return extents


def build_dxf_from_plan(plan, output_path, plan_code=None):
    doc = ezdxf.new(dxfversion="R2010", setup=True)

    doc.units = units.MM
    doc.header["$INSUNITS"] = units.MM
    doc.header["$MEASUREMENT"] = 1

    msp = doc.modelspace()

    extents = None

    extents = add_wall_entities(doc, msp, plan, extents, plan_code)
    extents = add_room_entities(doc, msp, plan, extents, plan_code)
    extents = add_items_entities(doc, msp, plan, extents, plan_code)
    extents = add_pipes_entities(doc, msp, plan, extents, plan_code)
    extents = add_rulers_entities(doc, msp, plan, extents, plan_code)

    if extents is not None:
        min_x, min_y, max_x, max_y = extents
        doc.header["$EXTMIN"] = (min_x, min_y, 0.0)
        doc.header["$EXTMAX"] = (max_x, max_y, 0.0)

    doc.saveas(output_path)


def collect_plan_codes(plan):
    codes = set()

    walls = plan.get("walls", {})
    for w in walls.values():
        val = w.get("plan")
        if isinstance(val, str):
            codes.add(val)

    rooms = plan.get("rooms2", {})
    for r in rooms.values():
        val = r.get("plan")
        if isinstance(val, str):
            codes.add(val)

    items = plan.get("items", {})
    for it in items.values():
        val = it.get("plan")
        if isinstance(val, str):
            codes.add(val)
        elif isinstance(val, dict):
            for k in val.keys():
                if isinstance(k, str) and len(k) == 1:
                    codes.add(k)

    rulers = plan.get("rulers", {})
    for r in rulers.values():
        val = r.get("plan")
        if isinstance(val, str) and len(val) == 1:
            codes.add(val)

    clean_codes = {c for c in codes if isinstance(c, str) and len(c) == 1}
    return sorted(clean_codes)


def main():
    input_path = input("Введите путь к .plan.json файлу: ").strip()
    output_path = input(
        "Введите базовый путь для сохранения .dxf (например /tmp/Plan.dxf или /tmp/Plan): "
    ).strip()

    if not input_path:
        print("Не указан путь к входному файлу.")
        sys.exit(1)

    if not output_path:
        print("Не указан путь к выходному файлу.")
        sys.exit(1)

    if not os.path.isfile(input_path):
        print(f"Файл '{input_path}' не найден.")
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения JSON: {e}")
        sys.exit(1)

    plan = data.get("plan")
    if not isinstance(plan, dict):
        print("В JSON нет раздела 'plan' или он имеет неверный формат.")
        sys.exit(1)

    codes = collect_plan_codes(plan)

    base, ext = os.path.splitext(output_path)
    if ext.lower() == ".dxf":
        base_out = base
    else:
        base_out = output_path

    try:
        if not codes:
            out_path = base_out + ".dxf"
            build_dxf_from_plan(plan, out_path, plan_code=None)
            print(f"DXF успешно сохранён в: {out_path}")
        elif len(codes) == 1:
            code = codes[0]
            out_path = base_out + ".dxf"
            build_dxf_from_plan(plan, out_path, plan_code=code)
            print(f"DXF успешно сохранён в: {out_path} (план '{code}')")
        else:
            for idx, code in enumerate(codes, start=1):
                out_path = f"{base_out}_{idx}.dxf"
                build_dxf_from_plan(plan, out_path, plan_code=code)
                print(f"DXF успешно сохранён в: {out_path} (план '{code}')")
    except Exception as e:
        print(f"Ошибка при построении DXF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
