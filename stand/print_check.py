"""Printability check for stand.stl against a target printer.

Answers the questions a slicer preview would, but numerically: does it fit the
build volume, how much of it is steep enough to want support, and how much of
it is actually touching the bed. Defaults are the Creality K1 Max.

    python print_check.py [stand.stl]
"""
import math
import pathlib
import struct
import sys

BED = (300.0, 300.0, 300.0)   # K1 Max build volume, mm
NOZZLE = 0.4
LAYER = 0.2
PRINTER = "Creality K1 Max"

# A surface is quoted by how far it leans from vertical: 0 deg is a vertical
# wall, 90 deg is a flat ceiling. Most printers manage 45 deg unsupported.
BUCKETS = [(0, 45, "safe"), (45, 60, "marginal"), (60, 80, "needs support"),
           (80, 90.01, "near-horizontal ceiling")]


def load(path):
    with open(path, "rb") as f:
        if f.read(5) == b"solid":
            f.seek(0)
            tris, cur = [], []
            for line in f.read().decode("utf-8", "replace").splitlines():
                p = line.split()
                if p and p[0] == "vertex":
                    cur.append(tuple(float(x) for x in p[1:4]))
                    if len(cur) == 3:
                        tris.append(cur)
                        cur = []
            return tris
        f.seek(80)
        n = struct.unpack("<I", f.read(4))[0]
        out = []
        for _ in range(n):
            d = struct.unpack("<12fH", f.read(50))
            out.append([d[3:6], d[6:9], d[9:12]])
        return out


def cross(u, v):
    return (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])


def sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "stand.stl")
    tris = load(path)

    pts = [p for t in tris for p in t]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    size = [hi[i] - lo[i] for i in range(3)]

    # signed volume tells us whether the winding gives outward normals
    vol = 0.0
    for a, b, c in tris:
        vol += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0])
                + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    flip = -1.0 if vol < 0 else 1.0

    total = bed_area = 0.0
    buckets = {label: [0.0, None, None] for _, _, label in BUCKETS}
    for a, b, c in tris:
        n = cross(sub(b, a), sub(c, a))
        mag = math.sqrt(sum(k*k for k in n))
        if mag == 0:
            continue
        area = mag / 2.0
        total += area
        nz = flip * n[2] / mag
        zmin, zmax = min(p[2] for p in (a, b, c)), max(p[2] for p in (a, b, c))

        # the face resting on the bed is supported by definition
        if nz < -0.999 and zmax <= lo[2] + 1e-6:
            bed_area += area
            continue
        if nz >= 0:
            continue
        lean = math.degrees(math.asin(min(1.0, -nz)))
        for a0, a1, label in BUCKETS:
            if a0 <= lean < a1:
                rec = buckets[label]
                rec[0] += area
                rec[1] = zmin if rec[1] is None else min(rec[1], zmin)
                rec[2] = zmax if rec[2] is None else max(rec[2], zmax)
                break

    print(f"model    : {path.name}   {len(tris)} triangles")
    print(f"printer  : {PRINTER}   bed {BED[0]:.0f}x{BED[1]:.0f}x{BED[2]:.0f} mm")
    print()
    print(f"size     : {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} mm")
    fits = all(size[i] <= BED[i] for i in range(3))
    used = max(size[i] / BED[i] for i in range(3)) * 100
    print(f"           {'FITS' if fits else 'DOES NOT FIT'} - "
          f"largest axis uses {used:.1f}% of the build volume")
    print(f"sits at  : z = {lo[2]:.3f} mm")
    print(f"bed area : {bed_area:.1f} mm^2 in contact "
          f"({bed_area / (size[0]*size[1]) * 100:.0f}% of its footprint box)")
    print(f"volume   : {abs(vol):.0f} mm^3  "
          f"(~{abs(vol) * 1.24 / 1000:.1f} g PLA solid)")
    print()
    print("downward-facing surface, by lean from vertical:")
    for _, _, label in BUCKETS:
        area, zmin, zmax = buckets[label]
        if area <= 0.01:
            print(f"  {label:24} {0.0:8.1f} mm^2")
            continue
        print(f"  {label:24} {area:8.1f} mm^2   z {zmin:5.1f} to {zmax:5.1f} mm")
    steep = sum(buckets[l][0] for _, _, l in BUCKETS if l != "safe")
    print()
    print(f"  {steep:.1f} mm^2 leans past 45 deg "
          f"({steep / total * 100:.1f}% of the whole surface)")
    print()
    print(f"thin-feature floor: {NOZZLE} mm nozzle, {LAYER} mm layers - "
          f"anything under {NOZZLE * 2:.1f} mm wide prints as loose perimeters")


if __name__ == "__main__":
    main()
