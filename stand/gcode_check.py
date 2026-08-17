"""Bounds-check sliced G-code before it goes anywhere near the printer.

A slicer will happily emit moves outside the build volume if a profile is wrong,
and the failure mode is the toolhead hitting a gantry or the plate. Parsing
every move is cheap insurance.

It also proves the brim is really there. Asking for one is not the same as
getting one: `brim_type: outer_brim_only` is not a value OrcaSlicer 2.4.2 knows,
so it fell back to `auto_brim` without a word, auto_brim decided this part didn't
need a brim, and the G-code came out identical to the run that let go of the bed.
The settings comment said "brim"; the toolpaths said otherwise. Read the
toolpaths. (The spelling it wants is `outer_only`.)

    python gcode_check.py gcode/stand_K1Max_PLA_0.20mm.gcode
"""
import pathlib
import re
import sys

BED = (300.0, 300.0, 300.0)   # Creality K1 Max
# G2/G3 too: enable_arc_fitting is on, so a large share of this part's outline
# is arcs. Checking only G0/G1 left every one of them unbounded.
MOVES = ("G0", "G1", "G2", "G3")
MOVE = re.compile(r"([XYZ])(-?\d+\.?\d*)")
SETTING = re.compile(r"^; (\w+) = (.*)$")


def bbox(pts):
    xs = [p[0] for p in pts if p[0] is not None]
    ys = [p[1] for p in pts if p[1] is not None]
    return (min(xs), max(xs), min(ys), max(ys)) if xs and ys else None


def check_brim(brim, first_layer, settings):
    """The brim must exist, and must stand proud of the part it is holding down.

    Measured against the rest of the first layer rather than against brim_width,
    because the brim follows the footprint's outline: on a rounded rectangle the
    corners gain less than a flat edge does. 60% of the asked-for width on every
    side is comfortably past "a skirt" and well short of "8 mm everywhere".
    """
    want = settings.get("brim_type", "no_brim")
    if want == "no_brim":
        print("  brim   not requested")
        return True

    width = float(settings.get("brim_width", 0) or 0)
    if not brim:
        print(f"  brim   REQUESTED ({want}) BUT NOT EXTRUDED"
              f" - the slicer ignored it")
        return False

    b, p = bbox(brim), bbox(first_layer)
    if not b or not p:
        print("  brim   cannot measure - no first-layer geometry")
        return False

    margins = (p[0] - b[0], b[1] - p[1], p[2] - b[2], b[3] - p[3])
    worst, need = min(margins), 0.6 * width
    good = worst >= need
    print(f"  brim   {want} {width:.1f} mm, narrowest side {worst:.2f} mm"
          f"   need >={need:.2f}   {'ok' if good else 'TOO NARROW'}")
    return good


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                        else "gcode/stand_K1Max_PLA_0.20mm.gcode")
    axes = {"X": [], "Y": [], "Z": []}
    settings = {}
    brim, first_layer = [], []
    section, layer, x, y = None, 0, None, None
    moves = 0
    for line in path.open(encoding="utf-8", errors="replace"):
        if line.startswith(";"):
            if line.startswith(";TYPE:"):
                section = line[6:].strip()
            elif line.startswith(";LAYER_CHANGE"):
                layer += 1
            else:
                m = SETTING.match(line.rstrip("\n"))
                if m:
                    settings[m.group(1)] = m.group(2).strip()
            continue
        if not line.startswith(MOVES):
            continue
        moves += 1
        found = MOVE.findall(line)
        for ax, val in found:
            axes[ax].append(float(val))
            if ax == "X":
                x = float(val)
            elif ax == "Y":
                y = float(val)
        # Only EXTRUDING moves that actually carry a coordinate. A bare
        # `G1 E.8` is a prime, not a position: crediting it with the last known
        # XY put a Custom-section prime blob into the footprint and made the
        # brim measure 4 mm on two sides when it was really 7.3.
        if (layer <= 1 and "E" in line and section != "Custom"
                and any(ax in "XY" for ax, _ in found)
                and x is not None and y is not None):
            (brim if section == "Brim" else first_layer).append((x, y))

    if not moves:
        raise SystemExit(f"{path}: no G0/G1 moves found")

    ok = True
    print(f"{path.name}: {moves} moves")
    for i, ax in enumerate("XYZ"):
        lo, hi = min(axes[ax]), max(axes[ax])
        good = lo >= 0 and hi <= BED[i]
        ok &= good
        print(f"  {ax}  {lo:8.2f} .. {hi:8.2f}   bed 0..{BED[i]:.0f}"
              f"   {'ok' if good else 'OUT OF BOUNDS'}")

    cx = (min(axes['X']) + max(axes['X'])) / 2
    cy = (min(axes['Y']) + max(axes['Y'])) / 2
    print(f"  centred on {cx:.1f}, {cy:.1f}")

    in_bounds = ok
    ok &= check_brim(brim, first_layer, settings)

    if not in_bounds:
        print("\nDO NOT PRINT - moves fall outside the build volume")
        return 1
    if not ok:
        print("\nmoves are in bounds, but the bed adhesion this file was sliced"
              " for is not in it")
        return 1
    print("\nall moves inside the build volume, brim present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
