// Desk tilt-stand for the GUITION ESP32-2424S012 in its PLASTIC SHELL.
//
// The shell is a rounded "pebble", not a cylinder: 40.5 mm across at its
// equator, 11 mm thick, domed glass front, flat-ish back, USB-C on the RIM.
//
// Seat = straight bore + a front lip. The pebble drops in from the BACK and
// stops when its face meets the lip; the 20 deg backward lean means gravity
// presses it onto that lip, so no snap-fit is needed and it still lifts out.
// (A conical seat was tried first and dropped: where a cone grips depends on
// the rim's curvature, which can't be measured off a photo. The lip doesn't
// care -- it stops the pebble at the same place whatever the rim does.)
//
// Units: mm.  Viewer is at +Y; screen faces +Y. Support & base extend to -Y.

/* ---------- published specs for a stock ESP32-2424S012C ----------
   Fixed by the part, not measurable off one unit. Use them to sanity-check any
   caliper reading before it becomes geometry.
     bare PCB          38.5 x 37.0 mm
     active display    32.4 mm dia      <- cannot vary, it is the 1.28" panel
     LCD panel outline ~35.6 x 38.1 mm
     cased diameter    "about 42 mm" (CNX Software) -- see the NOTE below     */
active_d    = 32.4;

/* ---------- fit parameters (measured off the shell) ---------- */
// NOTE: the only published cased diameter is ~42 mm, while this unit measured
// 45 mm at the widest and 42 mm across the glossy front. Those reconcile if 45
// is the equator and 42 the front face -- but if the true widest is 42, the
// 43 mm lip bore is LARGER than the shell and it drops straight through the
// front of the ring. Gauge it: set calipers to `aperture` and try to pass the
// shell through. It must NOT fit.
disc_d      = 45;    // shell diameter at its widest -- the equator
disc_t      = 11;    // shell thickness front-to-back
glass_d     = 42;    // outermost glossy front area the lip must not sit on

/* ---------- seat ---------- */
// The lip bore must clear the glass and still catch the rim, and there is only
// 1.5 mm of rim to aim at. 43.0 splits it: 0.5 mm clear of the glass on radius,
// 1.0 mm of ledge under the shell. Holes print undersize on FDM, so the 0.5 mm
// glass clearance is the half that must not be spent.
aperture    = 43.0;  // front lip bore. MUST stay between glass_d and disc_d
// Diametral clearance on the bore. 0.5 was carried over from when the shell was
// thought to be 40.5; on a 45 mm bore it dies at the pessimistic end of FDM hole
// shrink -- 0.5 mm of shrink leaves zero and the shell simply will not go in.
// 0.8 still enters with 0.3 mm to spare, and the 0.4 mm of slop it allows only
// eats into a 1.0 mm ledge.
fit         = 0.8;
front_thick = 1.8;   // thickness of the front lip
ring_d      = 10.0;  // ring depth. < disc_t so the back stands proud to grip
wall        = 2.8;   // ring wall thickness
lead_in     = 1.0;   // 45 deg chamfer at the back opening, to start the pebble

bore        = disc_d + fit;

// The lip only works inside this window, and the window is 1.5 mm wide. Fail
// the render rather than quietly print a cradle that sits on the screen.
assert(aperture > glass_d,
       "aperture is inside the glass -- the lip would sit on the screen");
assert(aperture < disc_d,
       "aperture is wider than the shell -- the lip would not catch it at all");
assert(disc_t > ring_d,
       "shell is shallower than the ring -- it would sink in with no edge to grip");
// active_d is the one dimension that cannot vary between units, so it makes the
// only backstop that survives a bad caliper reading on everything else.
assert(aperture > active_d + 3,
       "lip is closing on the 32.4 mm active area -- a measurement is wrong");

/* ---------- USB-C on the rim ---------- */
// The port exits SIDEWAYS, not downward: a right-angle plug needs ~10 mm of
// radial room, and at the bottom that room is below the desk. Out the side it
// costs nothing and leaves the load-bearing bottom arc of the cone intact.
// Rotate the UI in firmware to match. port_angle: 0 = bottom, 90 = viewer's
// left, 270 = viewer's right.
port_angle  = 90;
cable_w     = 16;    // notch width -- clears the right-angle plug's moulded body

/* ---------- stance ---------- */
// Lean back from vertical. The screen's normal rises by this angle, so it aims
// at a seated viewer's eye when they're ~1.4x as far away as they are above it.
tilt        = 38;
merge       = 2.0;   // how far the ring's lowest edge sinks into the base
// Base is sized off the ring: it has to stay wider than the 51.1 mm ring OD or
// the cradle overhangs its own footprint.
base_w      = 58;    // base width
base_d      = 68;    // base depth (front-back)
base_t      = 4.5;   // base thickness
foot_r      = 7;     // base corner radius
leg_w       = 20;    // back-leg width
$fn         = 150;

outer   = bore + 2*wall;
Rb      = outer/2;
base_y  = -(base_d/2) + 14;                  // shift base rearward

// Cradle centre height, DERIVED -- do not hard-code it. Because the ring leans,
// its BACK-bottom edge hangs lowest, at place_z - (Rb*cos(tilt) + ring_d*sin(tilt)).
// This puts that edge `merge` below the base's top face, so the two fuse and
// nothing pokes under the build plate. A hard-coded value is exactly how the
// part once ended up 1.3 mm below the plate after the stance changed.
place_z = base_t - merge + Rb*cos(tilt) + ring_d*sin(tilt);

module rrect(w,d,t,r){
  hull() for(sx=[-1,1], sy=[-1,1])
    translate([sx*(w/2-r), sy*(d/2-r), 0]) cylinder(r=r, h=t);
}

// flat cradle blank: axis Z, screen faces -Z (front), pocket opens toward +Z
module ring_blank(){ cylinder(d=outer, h=ring_d); }

// everything removed to form the seat. Cut LAST, after the base and leg are
// unioned on -- the ring merges into the base, so the base slab would
// otherwise fill the bottom of the pocket and the shell would foul on it.
module seat_cuts(){
  translate([0,0,-1])          cylinder(d=aperture, h=ring_d+2);  // window
  // Pocket. Runs the FULL depth of the shell plus margin, not just the ring
  // depth: the shell stands ~2 mm proud of the back face, and the leg's hull
  // sweeps past there -- without this it clips the shell's back edge.
  translate([0,0,front_thick]) cylinder(d=bore, h=disc_t + 3);
  // 45 deg lead-in at the back opening so the pebble starts square
  translate([0,0,ring_d - lead_in])
    cylinder(d1=bore, d2=bore + 2*lead_in, h=lead_in + 0.01);
  // rim notch for the USB-C plug, swung round to port_angle
  rotate([0,0,port_angle])
    translate([-cable_w/2, -Rb-1, -1])
      cube([cable_w, Rb+1 - (aperture/2 - 4), ring_d+2]);
}

// place flat cradle into the leaned pose (screen -> +Y & up)
module place(){ translate([0,0,place_z]) rotate([90+tilt,0,0]) children(); }

// stub biting into the ring's upper wall, held clear of the pocket bore so it
// survives seat_cuts() and never fouls the shell going in
module neck(){
  translate([-leg_w/2, bore/2 + 0.4, 0]) cube([leg_w, 4.5, ring_d]);
}

// base plate (rearward). rrect() already builds up from z=0, so this sits ON
// the build plate -- do NOT lift it by base_t/2 as if rrect were centred, or
// the whole plate floats and the part balances on the back leg's bar alone.
module base_plate(){
  translate([0, base_y, 0]) rrect(base_w, base_d, base_t, foot_r);
}

// back leg: smooth hull from a base-back bar up to the ring's upper back
module back_leg(){
  hull(){
    translate([-leg_w/2, base_y - base_d/2 + 4, 0]) cube([leg_w, 8, base_t]);
    place() neck();
  }
}

module stand(){
  difference(){
    union(){ place() ring_blank(); base_plate(); back_leg(); }
    place() seat_cuts();
  }
}

/* ---------- fit check (never part of the STL) ----------
   openscad -D show_pebble=true -D section=true -o fit_check.png stand.scad   */
show_pebble = false;   // draw a stand-in for the shell, seated in the cone
section     = false;   // slice the model in half to see the seat

// stand-in for the shell: disc_d at the equator, disc_t thick, rounded rim.
//
// rim_r is DERIVED, not eyeballed. The glass sits on the front face, so the
// face must be at least glass_d across; the widest point is disc_d; therefore
// the edge cannot pull in by more than half the difference. Guessing 3.5 here
// implied a 38 mm front face carrying a 42 mm glass, which is impossible -- and
// every interference check ran against that impossible shape.
rim_r = (disc_d - glass_d) / 2;
module pebble(){
  rotate_extrude($fn=120)
    hull(){
      translate([disc_d/2 - rim_r, rim_r])          circle(r=rim_r);
      translate([disc_d/2 - rim_r, disc_t - rim_r]) circle(r=rim_r);
      square([0.01, disc_t]);
    }
}

// how far the rounded rim sinks past the lip before it lands on the aperture
rim_c  = disc_d/2 - rim_r;
sink   = (aperture/2 <= rim_c) ? 0
       : rim_r - sqrt(max(0, rim_r*rim_r - pow(aperture/2 - rim_c, 2)));
seat_z = front_thick - sink;

module seated_pebble(){ place() translate([0,0,seat_z]) pebble(); }

module assembly(){
  stand();
  if (show_pebble) color("SteelBlue") seated_pebble();
}

if (section) difference(){ assembly(); translate([0,-70,-25]) cube([70,140,150]); }
else assembly();
