# Auto Trim shape mesh addon

Optional addon for [Auto Trim](../../README.md) on zMod: `MESH=SHAPE` probes only the bed mesh grid points near your parts and fills the rest from your saved full-bed mesh. Version 1.2.0: with a saved mesh denser than the probe grid (`AUTO_TRIM_MESH_CALIBRATE PROBE_COUNT=21,21`, Auto Trim 3.9.17), the final mesh is built on that mesh's grid, carrying the plate's hills and valleys finer than the probe grid can see.

What it does, how to install and remove it, and what happens when you update Auto Trim, zMod or Klipper: see [Shape mesh addon (optional)](../../README.md#shape-mesh-addon-optional) in the Auto Trim README.

Files:
- `auto_trim_shape_mesh.py`: the Klipper module (GPLv3, see `LICENSE`)
- `auto_trim_shape_mesh.cfg`: its settings; include it in `mod_data/user.cfg`
- `install_shape_mesh.sh`, `uninstall_shape_mesh.sh`: link it into zMod's Klipper, or remove the links
- `tests/`: software tests (`python3 -m pytest tests`); `tests/kextras/bed_mesh.py` is Klipper's own mesh code, used unchanged
