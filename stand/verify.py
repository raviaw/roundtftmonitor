"""Verify the cradle before printing it.

Every check here exists because something got through without it:

  shell fits        a conical seat drove the shell 1208 mm^3 into the ring
  full bed contact  the base plate floated 2.25 mm while the bbox still read 0
  sits on the plate the ring's back-bottom edge hung 1.31 mm under the plate
  watertight        cheap, and a torn mesh slices into nonsense
  invariants        the lip bore twice ended up on the wrong side of the glass

Run it after ANY change to the seat, the stance or the shell dimensions:

    python verify.py
"""
import math
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from print_check import load, cross, sub  # noqa: E402

HERE = pathlib.Path(__file__).parent
SCAD = HERE / "stand.scad"
PROBE = HERE / "verify.scad"
OPENSCAD = r"E:\dev\openscad\openscad-2021.01\openscad.exe"

BED = (300.0, 300.0, 300.0)
SLAB_T = 0.8
TOL_INTERFERENCE = 0.5   # mm^3; tangential contact leaves zero-volume slivers
TOL_AREA = 0.5           # %


def params():
    """Read the scalar parameters straight out of stand.scad."""
    txt = SCAD.read_text(encoding="utf-8")
    return {m.group(1): float(m.group(2))
            for m in re.finditer(r"^(\w+)\s*=\s*(-?[\d.]+)\s*;", txt, re.M)}


def run(args):
    return subprocess.run([OPENSCAD, *args], capture_output=True, text=True)


def measure(stl):
    tris = load(stl)
    if not tris:
        return 0.0, None, tris
    vol = 0.0
    for a, b, c in tris:
        vol += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0])
                + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    pts = [p for t in tris for p in t]
    box = [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]
    return abs(vol), box, tris


def probe(mode, out, **extra):
    args = ["-D", f'mode="{mode}"']
    for k, v in extra.items():
        args += ["-D", f"{k}={v}"]
    r = run([*args, "-o", str(out), str(PROBE)])
    if "ERROR" in (r.stderr or ""):
        raise SystemExit(r.stderr.strip()[:400])
    # an empty result writes no file, which is a pass for the overlap probe
    return out if out.exists() and out.stat().st_size else None


def main():
    p = params()
    results = []

    def check(name, ok, detail):
        results.append((ok, name, detail))

    # --- design invariants, straight from the source ------------------------
    check("lip clears the glass",
          p["aperture"] > p["glass_d"],
          f'aperture {p["aperture"]} > glass {p["glass_d"]} '
          f'({(p["aperture"]-p["glass_d"])/2:.2f} mm radial)')
    check("lip still catches the shell",
          p["aperture"] < p["disc_d"],
          f'aperture {p["aperture"]} < shell {p["disc_d"]} '
          f'({(p["disc_d"]-p["aperture"])/2:.2f} mm of ledge)')
    check("shell stands proud to grip",
          p["disc_t"] > p["ring_d"],
          f'shell {p["disc_t"]} > ring depth {p["ring_d"]}')
    check("clear of the active display",
          p["aperture"] > p["active_d"] + 3,
          f'aperture {p["aperture"]} vs active {p["active_d"]} '
          f'({(p["aperture"]-p["active_d"])/2:.2f} mm radial)')

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        # --- the model itself ----------------------------------------------
        body = td / "body.stl"
        r = run(["-o", str(body), str(SCAD)])
        vols = re.search(r"Volumes:\s+(\d+)", r.stderr or "")
        check("one solid body", bool(vols) and vols.group(1) == "2",
              f'CGAL reports Volumes: {vols.group(1) if vols else "?"} '
              f'(2 = one solid + the void around it)')

        vol, box, tris = measure(body)
        size = [box[i][1] - box[i][0] for i in range(3)]
        check("sits on the build plate", abs(box[2][0]) < 1e-6,
              f"lowest point z = {box[2][0]:.4f}")
        check("fits the printer",
              all(size[i] <= BED[i] for i in range(3)),
              f"{size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm "
              f"in {BED[0]:.0f}^3")

        # --- watertight ------------------------------------------------------
        edges = {}
        for a, b, c in tris:
            for u, v in ((a, b), (b, c), (c, a)):
                k = tuple(sorted((tuple(round(q, 4) for q in u),
                                  tuple(round(q, 4) for q in v))))
                edges[k] = edges.get(k, 0) + 1
        naked = sum(1 for n in edges.values() if n == 1)
        weird = sum(1 for n in edges.values() if n > 2)
        check("watertight mesh", naked == 0 and weird == 0,
              f"{naked} naked, {weird} non-manifold of {len(edges)} edges")

        # --- the shell actually fits ----------------------------------------
        got = probe("interference", td / "hit.stl")
        hit = measure(got)[0] if got else 0.0
        check("shell seats without fouling", hit <= TOL_INTERFERENCE,
              f"{hit:.2f} mm^3 of overlap with the cradle")

        # --- the whole base is on the bed ------------------------------------
        got = probe("slab", td / "slab.stl", slab_z=0, slab_t=SLAB_T)
        slab = measure(got)[0] if got else 0.0
        want = (p["base_w"]*p["base_d"] - (4-math.pi)*p["foot_r"]**2) * SLAB_T
        off = abs(slab-want)/want*100 if want else 100
        check("full base on the bed", off <= TOL_AREA,
              f"{slab:.0f} mm^3 in the lowest {SLAB_T} mm vs {want:.0f} "
              f"for an intact footprint ({off:.2f}% off)")

    width = max(len(n) for _, n, _ in results)
    print()
    for ok, name, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<{width}}  {detail}")
    bad = [n for ok, n, _ in results if not ok]
    print()
    if bad:
        print(f"{len(bad)} CHECK(S) FAILED: {', '.join(bad)}")
        return 1
    print(f"all {len(results)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
