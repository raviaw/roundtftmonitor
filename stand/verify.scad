// Geometry probes for verify.py. Not part of the printed model.
//
//   openscad -D mode=\"interference\" -o out.stl verify.scad
//   openscad -D mode=\"slab\" -D slab_z=0 -o out.stl verify.scad
//
// `use` imports the modules without running stand.scad's own top-level output.
use <stand.scad>

mode   = "interference";
slab_z = 0;      // height of the bottom slice, mm
slab_t = 0.8;    // its thickness, mm

// Where the shell sits versus where the cradle is. Should be empty: the two
// touch tangentially and nothing more.
if (mode == "interference")
  intersection() { stand(); seated_pebble(); }

// A thin slice at the bottom. Its area is what actually touches the bed -- a
// bounding box says z=0 just as happily when one small bar is all that lands.
if (mode == "slab")
  intersection() {
    stand();
    translate([-200, -200, slab_z]) cube([400, 400, slab_t]);
  }
