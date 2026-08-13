# Desk tilt-stand for the round display

Custom angled cradle for the GUITION **ESP32-2424S012** (1.28" round, ESP32-C3),
sized for the unit **in the plastic shell it ships in** — not a bare PCB.
No off-the-shelf round-board tilt stand exists, so this is a parametric design.

## Files
- `stand.scad` — parametric source (edit + re-render in OpenSCAD)
- `stand.stl` — ready to slice
- `preview_iso.png` / `preview_side.png` / `preview_front.png` — renders
- `fit_check.png` — the shell drawn seated in the cradle (see below)
- `drawing.html` — a single-file drawing sheet: dimensioned section through the
  seat, all views, the dimension schedule and the fit-check results
- `page.tpl.html` + `build_page.py` + `views/` — how `drawing.html` is generated

## The drawing sheet
`drawing.html` is self-contained — every view is inlined as a data URI, because
it gets published as an Artifact and that CSP blocks all external hosts. Rebuild
it with:

```
python build_page.py            # reuse views/
python build_page.py --render   # re-render every view first (~3 min)
```

Both grounds are rendered (`Cornfield` / `Tomorrow Night`) and the page swaps
them with the viewer's theme, so edit `CAMERAS` in `build_page.py` rather than
adding one-off renders.

## What it holds
The shell is a rounded **pebble**, not a cylinder: **40.5 mm** across at its
widest (its equator), **11 mm** thick, domed glass front, flat-ish back, and the
**USB-C port on the rim**.

## What it is
A ring cradle leaning back **38°** toward a seated viewer, on a rearward base
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
- Footprint **52 × 62 mm**, height **~47 mm**
- ~23.6 cm³ (~29 g PLA solid; well under that at normal infill)

## ⚠️ The one dimension still unverified
`aperture` (default **38.0 mm**) is the front lip's bore. It must clear the
**black glass** and land on the plastic rim around it. Measure the glass
diameter and keep `aperture` at least 0.5 mm larger. Too small and the lip
creeps over the screen edge; too large and it loses its grip on the rim.

`disc_d` (40.5) and `disc_t` (11) are measured and confirmed.

## Changing the lean
Set `tilt` (currently **38°**) and re-render — nothing else needs touching.
`place_z` is *derived* from it, because leaning the cradle moves its lowest
point; a hard-coded height is how the part once ended up below the build plate.
Re-run the fit check afterwards.

## Checking the fit before you print
`stand.scad` can draw a stand-in for the shell seated in the cradle:

```
openscad -D show_pebble=true -o fit_check.png stand.scad
```

The shape of that stand-in depends on `rim_r`, an eyeballed guess at the rim's
corner radius. It affects **the check only, never the printed part**.

The seat was verified by intersecting that stand-in with the model and measuring
the overlap volume — **0.00 mm³**, i.e. pure tangential contact, no clash with
the ring, leg, or base. Worth re-running after any change to the seat or stance.

Measuring caught three real faults that eyeballing renders did not:
- the base slab filled the bottom of the pocket — the seat must be cut *after*
  the base and leg are unioned on, not before;
- the ring's back-bottom edge hung 1.3 mm below the build plate;
- the **base plate floated 2.25 mm off the plate**, leaving the part balanced on
  an 18 × 8 mm bar, because it was lifted by half its thickness as though
  `rrect()` were centred on the origin when it already builds up from it.

That last one is why the bounding box is not enough on its own. Intersect the
model with a thin slab at the bottom and check the volume matches the base
footprint (**2545 mm³** in the lowest 0.8 mm) — a bbox reports `z = 0` just as
happily when a single small bar is all that touches the bed.

## Re-render after editing
```
"E:\dev\openscad\openscad-2021.01\openscad.exe" -o stand.stl stand.scad
```
Or open `stand.scad` in OpenSCAD, F5 to preview / F6 to render, then export STL.
A clean render reports **`Volumes: 2`** — one solid plus the surrounding void,
i.e. a single body.

## Printing
- Print **base-down** (as oriented). PLA/PETG, 3 perimeters, ~15% infill.
- At 38° the underside of the cradle is a genuine overhang, though still inside
  the ~45° most printers manage unsupported. Enable **light supports** (touching
  buildplate only) if your slicer flags it.
- A brim helps the small footprint stay put.
