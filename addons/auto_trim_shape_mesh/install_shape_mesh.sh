#!/bin/sh
# Auto Trim shape mesh addon: links the module into zMod's Klipper. Never
# overwrites a real file, never edits a config, never restarts anything.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODULE="$SCRIPT_DIR/auto_trim_shape_mesh.py"
[ -f "$MODULE" ] || { echo "auto_trim_shape_mesh.py not found beside the installer." >&2; exit 1; }
DONE=0
for EXTRAS_DIR in /usr/data/zmod/klipper/klippy/extras /usr/prog/klipper/klippy/extras; do
    [ -d "$EXTRAS_DIR" ] || continue
    TARGET="$EXTRAS_DIR/auto_trim_shape_mesh.py"
    if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
        echo "Refusing to overwrite a real file: $TARGET" >&2; exit 1
    fi
done
for EXTRAS_DIR in /usr/data/zmod/klipper/klippy/extras /usr/prog/klipper/klippy/extras; do
    [ -d "$EXTRAS_DIR" ] || continue
    ln -sf "$MODULE" "$EXTRAS_DIR/auto_trim_shape_mesh.py"
    echo "Linked $EXTRAS_DIR/auto_trim_shape_mesh.py"
    DONE=1
done
[ "$DONE" = 1 ] || { echo "zMod's Klipper folder not found. Nothing installed." >&2; exit 1; }
echo "Add once to mod_data/user.cfg, after the Auto Trim include:"
echo "  [include auto_trim_shape_mesh/auto_trim_shape_mesh.cfg]"
echo "Then reboot the printer (a reboot loads new Python; RESTART does not)."
echo "Use MESH=SHAPE on the AUTO_TRIM_PREPARE line."
