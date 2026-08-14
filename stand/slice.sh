#!/usr/bin/env sh
# Re-slice the stand for the Creality K1 Max.
#
# The three profiles in slicer/ are copies of OrcaSlicer's own Creality
# profiles with a handful of values changed (see below). They must be dropped
# back into OrcaSlicer's vendor folders before slicing, because their
# `inherits:` chains only resolve from inside the bundle -- and because the
# machine profile's NAME must stay "Creality K1 Max (0.4 nozzle)" or the
# process/filament compatibility check rejects it and the CLI just says
# "found error, exit".
#
# What was changed from Creality's stock 0.20mm Standard:
#   wall_loops            2  -> 3        load-bearing lip; ring wall is 7 lines
#   sparse_infill_density 15% -> 40%     mass, so it doesn't skid when swiped
#   brim_type       auto_brim -> no_brim 3902 mm^2 of bed contact already
#   enable_support        0             only 46 mm^2 past 55 deg, all forgiving
#   curr_bed_type  Cool Plate -> Textured PEI Plate   the CLI default is wrong
#                                       for a K1 Max and gives a 35 C bed
#   filament_density      0  -> 1.24     stock profile reports 0 g otherwise
#
# slow_down_layer_time is a FILAMENT setting, not a process one -- overriding it
# in the process profile is silently ignored. Creality already ship it at 8 s,
# which is what this part needs.

set -e
ORCA="${ORCA:-E:/dev/orcaslicer}"
HERE="$(cd "$(dirname "$0")" && pwd)"
VEND="$ORCA/resources/profiles/Creality"

[ -x "$ORCA/orca-slicer.exe" ] || {
  echo "OrcaSlicer not found at $ORCA (portable zip from the OrcaSlicer releases)" >&2
  exit 1
}

cp "$HERE/slicer/machine.json"  "$VEND/machine/roundtft K1 Max (0.4 nozzle).json"
cp "$HERE/slicer/process.json"  "$VEND/process/roundtft-stand @Creality K1Max (0.4 nozzle).json"
cp "$HERE/slicer/filament.json" "$VEND/filament/roundtft Generic PLA.json"

mkdir -p "$HERE/gcode"
"$ORCA/orca-slicer.exe" \
  --load-settings "$VEND/machine/roundtft K1 Max (0.4 nozzle).json;$VEND/process/roundtft-stand @Creality K1Max (0.4 nozzle).json" \
  --load-filaments "$VEND/filament/roundtft Generic PLA.json" \
  --slice 0 --outputdir "$HERE/gcode" "$HERE/stand.3mf"

mv -f "$HERE/gcode/plate_1.gcode" "$HERE/gcode/stand_K1Max_PLA_0.20mm.gcode"
echo "wrote gcode/stand_K1Max_PLA_0.20mm.gcode"

# Sanity-check the result rather than trusting it: every move must sit inside
# the build volume, and the start macro must be the Klipper one.
grep -m1 "^START_PRINT" "$HERE/gcode/stand_K1Max_PLA_0.20mm.gcode"
grep -E "^; (printer_model|curr_bed_type|wall_loops|sparse_infill_density|brim_type|enable_support) " \
     "$HERE/gcode/stand_K1Max_PLA_0.20mm.gcode"
