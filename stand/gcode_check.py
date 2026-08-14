"""Bounds-check sliced G-code before it goes anywhere near the printer.

A slicer will happily emit moves outside the build volume if a profile is wrong,
and the failure mode is the toolhead hitting a gantry or the plate. Parsing
every move is cheap insurance.

    python gcode_check.py gcode/stand_K1Max_PLA_0.20mm.gcode
"""
import pathlib
import re
import sys

BED = (300.0, 300.0, 300.0)   # Creality K1 Max
MOVE = re.compile(r"([XYZ])(-?\d+\.?\d*)")


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                        else "gcode/stand_K1Max_PLA_0.20mm.gcode")
    axes = {"X": [], "Y": [], "Z": []}
    moves = 0
    for line in path.open(encoding="utf-8", errors="replace"):
        if not line.startswith(("G0", "G1")):
            continue
        moves += 1
        for ax, val in MOVE.findall(line):
            axes[ax].append(float(val))

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

    if not ok:
        print("\nDO NOT PRINT - moves fall outside the build volume")
        return 1
    print("\nall moves inside the build volume")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
