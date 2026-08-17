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
#   enable_support        0             only 46 mm^2 past 55 deg, all forgiving
#   curr_bed_type  Cool Plate -> Textured PEI Plate   the CLI default is wrong
#                                       for a K1 Max and gives a 35 C bed
#   filament_density      0  -> 1.24     stock profile reports 0 g otherwise
#
# ADHESION (2026-08-17 -- the first print came unstuck mid-job):
#   brim_type       no_brim -> outer_brim_only   8 mm, brim_object_gap 0
#   initial_layer_print_height 0.2 -> 0.25       thicker first layer squashes in
#   initial_layer_speed         60 -> 30 mm/s    time to weld, not to skid
#   initial_layer_infill_speed  60 -> 40 mm/s
#   textured_plate_temp         45 -> 60 C       filament.json
#   nozzle_temperature      200/200 -> 215/210 C filament.json
#   close_fan_the_first_x_layers 1 -> 3          filament.json
#
# The bed temperature was the real fault, not the missing brim. This filament
# inherits the GENERIC pla library profile, which puts textured PEI at 45 C and
# the nozzle at 200 C; Creality's own PLA is 60 C / 220 C. A 45 C plate barely
# holds PLA, and the K1's part fan hitting 100% at layer 2 does the rest.
# Check it in the G-code, not in the UI: `grep "^; textured_plate_temp"`.
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

# Same settings, as a PROJECT 3mf: model + every resolved setting in
# Metadata/project_settings.config. That is the portable form of this profile --
# Creality Print / Creality Opus / OrcaSlicer / Bambu Studio are all forks of the
# same slicer and open it with the settings already applied, no preset import and
# no vendor-folder juggling. stand.3mf stays plain geometry; don't confuse them.
"$ORCA/orca-slicer.exe" \
  --load-settings "$VEND/machine/roundtft K1 Max (0.4 nozzle).json;$VEND/process/roundtft-stand @Creality K1Max (0.4 nozzle).json" \
  --load-filaments "$VEND/filament/roundtft Generic PLA.json" \
  --export-3mf "$HERE/stand_K1Max_project.3mf" "$HERE/stand.3mf"
echo "wrote stand_K1Max_project.3mf"

# Sanity-check the result rather than trusting it: every move must sit inside
# the build volume, and the start macro must be the Klipper one.
grep -m1 "^START_PRINT" "$HERE/gcode/stand_K1Max_PLA_0.20mm.gcode"
grep -E "^; (printer_model|curr_bed_type|wall_loops|sparse_infill_density|brim_type|brim_width|brim_object_gap|enable_support|textured_plate_temp|nozzle_temperature|initial_layer_speed|initial_layer_print_height|close_fan_the_first_x_layers) = " \
     "$HERE/gcode/stand_K1Max_PLA_0.20mm.gcode"

# ...and every move must land inside the build volume. A wrong profile will
# happily emit coordinates off the bed; the failure mode is a toolhead crash.
python "$HERE/gcode_check.py" "$HERE/gcode/stand_K1Max_PLA_0.20mm.gcode"
