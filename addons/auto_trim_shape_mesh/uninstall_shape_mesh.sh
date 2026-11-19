#!/bin/sh
# Auto Trim shape mesh addon: removes the links the installer made. Only links
# are removed, never real files.
set -eu
for EXTRAS_DIR in /usr/data/zmod/klipper/klippy/extras /usr/prog/klipper/klippy/extras; do
    TARGET="$EXTRAS_DIR/auto_trim_shape_mesh.py"
    if [ -L "$TARGET" ]; then rm "$TARGET"; echo "Removed $TARGET"; fi
done
echo "Now remove [include auto_trim_shape_mesh/auto_trim_shape_mesh.cfg] from"
echo "mod_data/user.cfg FIRST if you have not (Klipper stops at start with an"
echo "unknown [auto_trim_shape_mesh] section otherwise), then reboot."
echo "MESH=SHAPE then falls back to a KAMP mesh, with a warning."
