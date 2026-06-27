// Desk tilt-stand for the GUITION ESP32-2424S012 (1.28" round, ESP32-C3).
// Board drops into the ring pocket from the BACK; a thin front lip holds it by
// the bezel (screen fully visible). Cradle leans back ~tilt deg toward a seated
// viewer. Support is a back leg + rearward base (never in front of the screen);
// the bottom-back is left open so the USB-C plug + cable exit downward.
//
// Units: mm.  *** VERIFY disc_d and disc_t with calipers before printing. ***
//   Viewer is at +Y; screen faces +Y. Support & base extend toward -Y.

/* ---------- fit parameters (measure these) ---------- */
disc_d      = 40.5;  // board OUTER diameter (round PCB)
disc_t      = 4.6;   // board depth seated in the pocket (PCB+glass; NOT the USB-C plug)

/* ---------- holder ---------- */
front_lip   = 2.2;   // front rim overlap onto the bezel (screen still visible)
front_thick = 1.8;   // thickness of that front lip
wall        = 2.6;   // pocket wall thickness
fit         = 0.5;   // diametral clearance
cable_w     = 13;    // USB-C plug/cable clearance width

/* ---------- stance ---------- */
tilt        = 20;    // lean-back from vertical (deg)
place_z     = 24;    // cradle height (bottom rim rests on base)
base_w      = 50;    // base width
base_d      = 60;    // base depth (front-back)
base_t      = 4.5;   // base thickness
foot_r      = 7;     // base corner radius
leg_w       = 18;    // back-leg width
$fn         = 150;

outer  = disc_d + 2*wall;
depth  = front_thick + disc_t;
R      = outer/2;
base_y = -(base_d/2) + 14;   // shift base rearward (front edge ~ +y14)

module rrect(w,d,t,r){
  hull() for(sx=[-1,1], sy=[-1,1])
    translate([sx*(w/2-r), sy*(d/2-r), 0]) cylinder(r=r, h=t);
}

// flat cradle: axis Z, screen faces -Z (front), pocket open +Z (back)
module holder(){
  difference(){
    cylinder(d=outer, h=depth);
    translate([0,0,-1])          cylinder(d=disc_d-2*front_lip, h=depth+2); // window
    translate([0,0,front_thick]) cylinder(d=disc_d+fit,         h=depth+1); // pocket
    translate([-cable_w/2, -R-1, front_thick]) cube([cable_w, wall+2, depth]); // cable notch
  }
}

// place flat cradle into the leaned pose (screen -> +Y & up)
module place(){ translate([0,0,place_z]) rotate([90+tilt,0,0]) children(); }

// stub biting into the ring's UPPER wall ring (radius >= board radius), through
// the pocket thickness, so the leg truly interpenetrates the ring -> single solid
module neck(){ translate([-leg_w/2, disc_d/2 - 0.8, front_thick]) cube([leg_w, 5.5, disc_t + 3]); }

difference(){
  union(){
    place() holder();
    // base plate (rearward)
    translate([0, base_y, base_t/2]) rrect(base_w, base_d, base_t, foot_r);
    // back leg: smooth hull from base-back bar up to the ring's upper back
    hull(){
      translate([-leg_w/2, base_y - base_d/2 + 4, 0]) cube([leg_w, 8, base_t]);
      place() neck();
    }
  }
  // keep a clear channel under the bottom-back of the board for USB-C + cable
  translate([-cable_w/2, -3, -1]) cube([cable_w, 20, base_t + 6]);
}
