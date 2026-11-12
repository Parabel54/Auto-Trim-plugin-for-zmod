#!/bin/sh
set -eu
# Run from the extracted package in mod_data; never writes user.cfg or core cfg.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODULE="$SCRIPT_DIR/deep_calibration.py"
if [ ! -f "$SCRIPT_DIR/deep_calibration_approach.py" ] || [ ! -f "$SCRIPT_DIR/deep_calibration_auto_mesh.cfg" ] || [ ! -f "$MODULE" ] || [ ! -f "$SCRIPT_DIR/deep_calibration_sensors.py" ] || [ ! -f "$SCRIPT_DIR/deep_calibration_mesh.py" ] || [ ! -f "$SCRIPT_DIR/deep_calibration_start.cfg" ]; then
    echo 'Missing a bundled Deep Calibration module or preparation cfg beside installer.' >&2
    exit 1
fi
DONE=0
for EXTRAS_DIR in /usr/data/zmod/klipper/klippy/extras /usr/prog/klipper/klippy/extras; do
    if [ -d "$EXTRAS_DIR" ]; then
        for MODULE_NAME in deep_calibration.py deep_calibration_sensors.py deep_calibration_mesh.py deep_calibration_approach.py; do
            TARGET="$EXTRAS_DIR/$MODULE_NAME"
            if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
                echo "Refusing to overwrite existing non-symlink: $TARGET" >&2
                exit 1
            fi
        done
    fi
done
for EXTRAS_DIR in /usr/data/zmod/klipper/klippy/extras /usr/prog/klipper/klippy/extras; do
    if [ -d "$EXTRAS_DIR" ]; then
        for MODULE_NAME in deep_calibration.py deep_calibration_sensors.py deep_calibration_mesh.py deep_calibration_approach.py; do
            ln -sf "$SCRIPT_DIR/$MODULE_NAME" "$EXTRAS_DIR/$MODULE_NAME"
        done
        DONE=1
    fi
done
if [ "$DONE" = 0 ]; then
    echo 'Supported zMod Klipper extras directory not found. Nothing installed.' >&2
    exit 1
fi
echo 'Modules linked. Add once to mod_data/user.cfg: [include deep_calibration_development_beta/deep_calibration.cfg]'
echo 'Auto Trim is bundled. Remove separate Auto Trim, old Live Z Mesh and standalone combo includes.'
echo 'Use normal START_PRINT followed by AUTO_TRIM_PREPARE; Deep Calibration startup takeover is disabled.'
echo 'Set SAVE_ZMOD_DATA PRINT_LEVELING=0 MESH_TEST=0 DISABLE_PRIMING=1 before using integrated START_PRINT.'
echo 'Reboot while idle to load the bundled Python code and macros.'
echo 'This installer does not restart, home, heat, tare, or alter offsets.'
