# plan2dxf

**Lite Python script to convert `.plan.json` files (from Remplanner) into `.dxf` drawings (AutoCAD format).**

This tool parses 2D floor plans exported from [Remplanner](https://remplanner.ru/) in JSON format and generates clean, structured `.dxf` files containing layers for walls, rooms, furniture, ventilation, rulers, and more.

---

## Features

- Supports full 2D floor plans with:
  - **Walls** and **Openings** (windows, doors)
  - **Rooms** with auto-labeled area
  - **Furniture**
  - **Ventilation pipes**
  - **Rulers** (dimensions)
- Automatically generates per-layer DXF with styling
- Supports **multi-plan exports** (generates one DXF per plan code)
- Simple CLI interface
- Supports plan-based filtering via `plan` code (like 'A', 'B', etc.)

---

## Installation

```bash
pip install ezdxf
```

Make sure you are using **Python 3.6+**

---

## Usage

```bash
python plan2dxf.py
```

The script will prompt for:

1. **Path to the `.plan.json` file** exported from Remplanner
2. **Output base path** for the `.dxf` file (e.g., `/tmp/Plan` or `/tmp/Plan.dxf`)

> If multiple floor plans are found (via `plan` codes), the script will generate multiple DXF files like `Plan_1.dxf`, `Plan_2.dxf`, etc.

---

## Input Format

The input `.plan.json` file must contain a `"plan"` dictionary with structures like:

- `walls`: dictionary of wall objects with `l1`, `l2`, `r1`, `r2`
- `rooms2`: room polygons, names, and areas
- `items`: furniture with `width`, `height`, `icon_center`, or `pc`
- `pipes_ventilation`: ventilation lines with vertex points
- `rulers`: dimension lines with `p1`, `p2`
- Each element may contain a `plan` field (used to filter/export per-plan)

---

## DXF Layers

Each type of entity is added to a separate layer with colors:

| Layer         | Entities                          | Color |
|---------------|-----------------------------------|--------|
| `Walls_*`     | Walls per plan (e.g., `Walls_A`)  | 7      |
| `Rooms`       | Room boundaries                   | 252    |
| `Rooms_Text`  | Room names and areas              | 7      |
| `Doors`       | Door holes                        | 3      |
| `Windows`     | Window holes                      | 3      |
| `Openings`    | Generic openings                  | 3      |
| `Furniture`   | Furniture outlines                | 2      |
| `Ventilation` | Ventilation lines                 | 4      |
| `Rulers`      | Dimension rulers                  | 5      |

---

## Examples

```plaintext
Input: /home/user/myproject/flat.plan.json
Output: /home/user/myproject/flat.dxf
```

If multiple plans (`"plan": "A"`, `"B"`, etc.) are detected:

```plaintext
Output: /home/user/myproject/flat_1.dxf (plan A)
        /home/user/myproject/flat_2.dxf (plan B)
```

---

## Troubleshooting

- ❌ **"JSON decode error"** – Check if the input `.json` is valid and well-formed.
- ❌ **"No plan section"** – The file must contain a top-level `"plan"` object.
- ❌ **"Missing file"** – Ensure correct path to `.plan.json` file is given.
- ❌ **"No plan codes found"** – The script expects at least one object with a `plan` value.

---

## Dependencies

- [Python 3.6+](https://www.python.org/)
- [ezdxf](https://pypi.org/project/ezdxf/)

Install with:

```bash
pip install ezdxf
```

---

## License

This project is released under the **GPL-3.0 license**.
