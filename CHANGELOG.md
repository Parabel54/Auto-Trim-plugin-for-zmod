# Changelog

All notable changes to Auto Trim for zMod are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

## [3.8.0] - 2026-10-24

### Changed
- AD5X trash-chute clean: the nozzle is wiped on the rubber pad every 25 C while it cools (`cool_wipe_step`), returning to the chute in between, so ooze is removed in stages.
- The zMod nozzle pre-clean inside `START_PRINT` is skipped on the AD5X (`zmod_preclean: SKIP`), since Auto Trim cleans the nozzle itself. `KEEP` restores it.

## [3.7.0] - 2026-10-24

### Added
- `MESH=SAVED`: uses the saved full-bed mesh instead of probing, probes 5 points at the print area corners and centre, and applies the measured shift. Falls back to a fresh KAMP mesh if the bed has changed shape or shifted too far.
- `MESH=AUTO`: KAMP for small prints, the saved mesh for large ones (`auto_kamp_points`).
- `PURGE_MACRO=<macro>`: run your own purge routine instead of the built-in line. It receives the planned position outside the print area.

### Changed
- AD5X trash-chute clean: the nozzle is wiped on the rubber pad right after the purge, while still hot, so the purged strand no longer cools on the nozzle and falls into the print area. It is wiped again after cooling.

## [3.6.0] - 2026-10-24

### Changed
- The bed check is off by default (`check: OFF`). The KAMP mesh is now the only probing, which saves 35 to 40 seconds per print. `CHECK=AREA` and `CHECK=ALL` re-enable it.

### Added
- Mesh range check: the print stops if the mesh varies by more than `max_mesh_range` (0.6 mm), which catches a lifted plate or debris without extra probing.

## [3.5.1] - 2026-10-24

### Fixed
- Short pause between the mesh and the bed check (`settle_ms`, 1000 ms), to avoid `Timer too close` shutdowns after dense meshes.
- The load cell is re-zeroed after the final reheat, so zMod collision protection starts from a fresh zero.

### Documented
- 7 x 7 is the recommended maximum mesh on the AD5X. Notes for 9 x 9 and `move_check_distance`.
- `temp_test_min` / `temp_test_max` with the standard zMod clean need zMod 1.7.4.
- Tested on zMod 1.7.1.

## [3.5.0] - 2026-10-21

First public release.

### Added
- `AUTO_TRIM_PREPARE`: nozzle clean, KAMP mesh, bed check, Z offset and purge line in one command after `START_PRINT`.
- Trash-chute nozzle clean on the AD5X. Standard zMod clean on the AD5M and AD5M Pro.
- Bed check: re-probes the corners and centre of the KAMP area and applies the measured drift.
- Per-filament trims, with starting values for common filament types.
- Learning from babysteps made during the first layers.
- Purge line placed outside the print area.
- Safety stops for wrong zMod settings, failed bed checks and out-of-range offsets.
- `AUTO_TRIM_STATUS` and `AUTO_TRIM_SET` commands.
