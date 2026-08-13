# Desk tilt-stand for the round display

Custom angled cradle for the GUITION **ESP32-2424S012** (1.28" round, ESP32-C3),
sized for the unit **in the plastic shell it ships in** — not a bare PCB.
No off-the-shelf round-board tilt stand exists, so this is a parametric design.

## Files
- `stand.scad` — parametric source (edit + re-render in OpenSCAD)
- `stand.3mf` — **load this to print**; 3MF carries units so it imports at
  the right size and orientation
- `stand.stl` — same mesh, for anything that wants STL
- `print_check.py` — build-volume fit, overhang and bed-contact numbers
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
The shell is a rounded **pebble**, not a cylinder: **45 mm** across at its widest
(its equator), **11 mm** thick, domed glass front, flat-ish back, and the
**USB-C port on the rim**. The black glass is **42 mm**, leaving only **1.5 mm**
of plastic rim — that rim is the entire ledge the cradle has to grip.

> An earlier 40.5 mm figure for the outer edge was wrong and everything derived
> from it was undersized. 45/42 are the measured values.

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
- Footprint **58 × 68 mm** (70 mm overall — the ring's lip overhangs the base
  front by ~1.7 mm), height **~51 mm**
- ~28.7 cm³ (~36 g PLA solid; well under that at normal infill)

## The tightest fit in the part
There is only **1.5 mm** of plastic rim between the glass (⌀42) and the shell's
outer edge (⌀45), and the front lip has to land inside it. `aperture` = **43.0**
splits that budget:

| | ⌀ | |
|---|---|---|
| Shell outer edge | 45.0 | measured |
| **Front lip bore** | **43.0** | leaves **1.0 mm** of ledge under the shell |
| Black glass | 42.0 | lip stops **0.5 mm** short of it |

Holes print undersize on FDM, so the glass side gets the clearance and the ledge
absorbs the error: a lip 0.3 mm tight still holds, a lip on the glass rocks.

`stand.scad` **asserts** `glass_d < aperture < disc_d` and `disc_t > ring_d`, so
a bad edit fails the render instead of quietly printing a cradle that sits on
the screen.

Still worth confirming: `disc_t` (11) came from the same session as the
superseded 40.5. It only sets how far the shell stands proud at the back, and
the assert catches it going too small.

**Reading the edge:** glass and rim are both glossy black, so the boundary
hides head-on. Tilt the shell under a light until the glass catches a
reflection and the plastic doesn't; a fingernail dragged inward catches the
step. `drawing.html` shows this drawn, with good/bad sections.

Also worth ten seconds: the **width of your right-angle USB-C plug's moulded
body**. The rim notch is `cable_w` = 16 mm, so up to ~15 mm drops through.

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
footprint (**3121 mm³** in the lowest 0.8 mm) — a bbox reports `z = 0` just as
happily when a single small bar is all that touches the bed.

## Re-render after editing
```
"E:\dev\openscad\openscad-2021.01\openscad.exe" -o stand.stl stand.scad
```
Or open `stand.scad` in OpenSCAD, F5 to preview / F6 to render, then export STL.
A clean render reports **`Volumes: 2`** — one solid plus the surrounding void,
i.e. a single body.

## Printing

Load **`stand.3mf`** rather than the STL — 3MF carries units, so it lands at the
right size and orientation with nothing to set. It is already base-down and
sitting on z = 0; do not rotate it.

Run `python print_check.py` for the numbers below on the current geometry.

### On the K1 Max
Everything here is comfortably inside the machine — 58 × 70 × 51 mm is 23 % of
the 300³ build volume.

| Setting | Value | Why |
|---|---|---|
| Orientation | as supplied | base-down, no rotation |
| Layer height | 0.2 mm | the 1.8 mm front lip is 9 layers |
| Walls | 3 | the 2.8 mm ring wall is 7 extrusions wide |
| Infill | ~15 % | nothing here is structural |
| **Supports** | **off** | see below |
| **Brim** | **not needed** | 3902 mm² of bed contact |
| **Min layer time** | **8–10 s** | the one setting that matters, see below |

**Supports: don't.** Only **46 mm² of the whole part** leans past 55°, and it is
all one feature — the lead-in chamfer at the top-back of the ring. That chamfer
is cut at 45° to the ring's axis, and because the ring leans 38° it ends up
facing nearly straight down. It will droop slightly. That is harmless: the
chamfer exists purely to let the shell start into the bore, so a soft edge there
costs nothing, and supports would scar the seat instead.

**Minimum layer time is the real K1 Max setting.** The stock profiles are built
for speed, and this part has a tiny cross-section per layer — up in the ring
each layer is a thin arc. At full speed those layers finish before the previous
one has set, and the ring turns out soft and glossy. Setting a minimum layer
time of 8–10 s (or capping speed to ~30 % on the outer wall) fixes it.

**PLA in an enclosed machine:** leave the door and top open, or the chamber
heat-soaks and you get heat creep in the extruder.

### Bed contact
The base makes full contact — 3902 mm², the entire footprint. That was not true
until the base-plate bug above was fixed, when the part balanced on 144 mm² and
genuinely did need a brim.
