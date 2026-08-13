# Desk tilt-stand for the round display

Custom angled cradle for the GUITION **ESP32-2424S012** (1.28" round, ESP32-C3),
sized for the unit **in the plastic shell it ships in** — not a bare PCB.
No off-the-shelf round-board tilt stand exists, so this is a parametric design.

## Files
- `stand.scad` — parametric source (edit + re-render in OpenSCAD)
- `stand.stl` — ready to slice
- `preview_iso.png` / `preview_side.png` / `preview_front.png` — renders
- `fit_check.png` — the shell drawn seated in the cradle (see below)

## What it holds
The shell is a rounded **pebble**, not a cylinder: **40.5 mm** across at its
widest (its equator), **11 mm** thick, domed glass front, flat-ish back, and the
**USB-C port on the rim**.

## What it is
A ring cradle leaning back **20°** toward a seated viewer, on a rearward base
with a back leg. Single solid piece, prints flat on the base.

The seat is a **straight bore plus a front lip**. The shell drops in from the
**back** and stops when its face meets the lip; the backward lean means gravity
presses it onto that lip, so nothing needs to snap or clamp and it still lifts
straight out. About **2 mm of the shell stands proud at the back**, which is what
you push on to pop it out.

> A conical seat was tried first and abandoned: where a cone grips depends on how
> the shell's rim curves, which can't be measured off a photo. The lip doesn't
> care — it stops the shell in the same place whatever the rim does.

### The USB-C exits sideways
Not downward. A right-angle plug needs ~10 mm of radial clearance, and at the
bottom of the ring that clearance is below the desk. Out the side it costs
nothing and leaves the load-bearing bottom arc of the ring intact.

Set `port_angle` to move it: `0` = bottom, **`90` = viewer's left (default)**,
`270` = viewer's right. **Rotate the UI in firmware to match.**

## Size
- Footprint **52 × 62 mm**, height **~52 mm**
- ~24 cm³ (~30 g PLA solid; well under that at normal infill)

## ⚠️ The one dimension still unverified
`aperture` (default **38.0 mm**) is the front lip's bore. It must clear the
**black glass** and land on the plastic rim around it. Measure the glass
diameter and keep `aperture` at least 0.5 mm larger. Too small and the lip
creeps over the screen edge; too large and it loses its grip on the rim.

`disc_d` (40.5) and `disc_t` (11) are measured and confirmed.

## Checking the fit before you print
`stand.scad` can draw a stand-in for the shell seated in the cradle:

```
openscad -D show_pebble=true -o fit_check.png stand.scad
```

The shape of that stand-in depends on `rim_r`, an eyeballed guess at the rim's
corner radius. It affects **the check only, never the printed part**.

The seat was verified by intersecting that stand-in with the model and measuring
the overlap volume — **0.00 mm³**, i.e. pure tangential contact, no clash with
the ring, leg, or base. That check caught two real faults: the base slab filling
the bottom of the pocket (the seat has to be cut *after* the base and leg are
unioned on), and the ring's back-bottom edge hanging 1.3 mm below the build
plate. Worth re-running after any change to the seat or the stance.

## Re-render after editing
```
"E:\dev\openscad\openscad-2021.01\openscad.exe" -o stand.stl stand.scad
```
Or open `stand.scad` in OpenSCAD, F5 to preview / F6 to render, then export STL.
A clean render reports **`Volumes: 2`** — one solid plus the surrounding void,
i.e. a single body.

## Printing
- Print **base-down** (as oriented). PLA/PETG, 3 perimeters, ~15% infill.
- The underside of the leaning cradle is a mild overhang — enable **light
  supports** (touching buildplate only) if your slicer flags it; the ~20° lean
  keeps overhangs modest.
- A brim helps the small footprint stay put.
