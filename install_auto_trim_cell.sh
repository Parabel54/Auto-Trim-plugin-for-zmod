#!/bin/sh
# Install the Auto Trim load cell add-on (auto_trim_cell.py) on zMod.
# Run once over SSH, after copying auto_trim_cell.py to mod_data:
#   sh /usr/data/config/mod_data/install_auto_trim_cell.sh
# Then add [auto_trim_cell] to user.cfg and run FIRMWARE_RESTART.
# Run it again after a zMod update if AUTO_TRIM_STATUS no longer lists the add-on.

SRC=""
for F in /usr/data/config/mod_data/auto_trim_cell.py /opt/config/mod_data/auto_trim_cell.py; do
    [ -f "$F" ] && SRC="$F" && break
done
if [ -z "$SRC" ]; then
    echo "auto_trim_cell.py not found in mod_data. Copy it there first."
    exit 1
fi

DONE=0
# zMod Klipper 13 and the stock Flashforge Klipper keep their extras here
for D in /usr/data/zmod/klipper/klippy/extras /usr/prog/klipper/klippy/extras; do
    if [ -d "$D" ]; then
        ln -sf "$SRC" "$D/auto_trim_cell.py" && echo "Linked into $D" && DONE=1
    fi
done
if [ "$DONE" = "0" ]; then
    echo "No Klipper extras folder found. Is this zMod?"
    exit 1
fi
echo "Now add [auto_trim_cell] to user.cfg and run FIRMWARE_RESTART."
