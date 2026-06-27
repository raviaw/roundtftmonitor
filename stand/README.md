# Desk tilt-stand for the round display

Custom angled cradle for the GUITION **ESP32-2424S012** (1.28" round, ESP32-C3).
No off-the-shelf round-board tilt stand exists, so this is a parametric design.

## Files
- `stand.scad` — parametric source (edit + re-render in OpenSCAD)
- `stand.stl` — ready to slice
- `preview_iso.png` / `preview_side.png` / `preview_front.png` — renders

## What it is
A ring cradle that holds the board (drops in from the **back**, a thin front lip
holds it by the bezel so the screen stays fully visible), leaning back **20°**
toward a seated viewer. A back leg + rearward base give stability; a **notch at
the bottom-front** lets the USB-C plug + cable exit downward. Single solid piece.

## Size
- Footprint **50 × 60 mm**, height **~47 mm**
- ~22 cm³ (~27 g PLA)

## ⚠️ Verify before printing (the fit-critical bits)
Measure your board with calipers and set these at the top of `stand.scad`:
- `disc_d` = round PCB **outer diameter** (default **40.5 mm**)
- `disc_t` = board **depth** that seats in the pocket — PCB + glass, **not** the
  USB-C plug (default **4.6 mm**)

If your unit is in the **plastic shell** it ships with (not a bare PCB), measure
that instead — it's larger.

Other handy params: `tilt` (lean angle), `front_lip` (how much rim covers the
bezel), `fit` (clearance), `cable_w` (USB-C slot width), `base_w`/`base_d`.

## Re-render after editing
```
"E:\dev\openscad\openscad-2021.01\openscad.exe" -o stand.stl stand.scad
```
Or open `stand.scad` in OpenSCAD, F5 to preview / F6 to render, then export STL.

## Printing
- Print **base-down** (as oriented). PLA/PETG, 3 perimeters, ~15% infill.
- The underside of the leaning cradle is a mild overhang — enable **light
  supports** (touching buildplate only) if your slicer flags it; the ~20° lean
  keeps overhangs modest.
- A brim helps the small footprint stay put.
