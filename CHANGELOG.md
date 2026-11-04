# Changelog

All notable changes to Auto Trim for zMod are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

## [3.9.2] - 2026-11-04

### Fixed
- First-layer learning could happen before the first layer. Until layer 1 starts, the layer number is 0, so Auto Trim used the nozzle height instead, and the nozzle is above 1 mm after the purge line. If the start took more than a few seconds (an IFS filament load, for example), Auto Trim learned "no babysteps", and corrections made on the first layer were then reported as not learned. The nozzle height is now only used once the nozzle has been on the first layer.
- `MESH=AUTO` misjudged the mesh size when `probe_count` has a single value (`probe_count: 7`), and always chose KAMP. A single value now counts for both directions.
- With `MESH=SAVED`, the shift of the saved mesh was learned as drift, mixing it with the drift measured by the bed check, and could give false "drift is ... away from its learned value" notices. The shift is still applied, but no longer learned.
- A print that was cancelled or stopped kept its Z offset and filament. Both are now cleared and the offset is set back to 0.

### Changed
- The load cells are zeroed after a short pause (1 s, 2 s after the part fan turns off), so the toolhead and the fan have settled.
- The `settle_ms` description and the README mesh size notes: the pause does not prevent `Timer too close` on dense meshes, and the 7 x 7 limit applies to saved meshes too.
- The `purge_flow` description gives the real flow of the default line (about 6 mm3/s).

## [3.9.1] - 2026-11-03

### Fixed
- With a purge macro set and parts filling the bed, Auto Trim showed `!! no room for a purge line ... Purge skipped.` (a Printer Error popup on the touch screen), although the purge macro still ran. The zMod stock line-clears (`_CLEAR1` to `_CLEAR4`) are now recognised as drawing outside the build area, so no line is planned and no message is shown. For your own macro, the message is an information line.
- With no purge macro and no room for the built-in line, the purge is no longer skipped: a stock Flashforge edge line that stays clear of the parts is used instead (`purge_fallback`, `edge_clearance`).

## [3.9.0] - 2026-11-02

### Fixed
- Parts that are wider above their first layer (a flared base, a bowl, an overhang) stopped every print with `the mesh ... does not cover this print`. KAMP meshes the first layer, while the check compared the mesh with the outline of the whole part from the slicer. For a mesh probed for this print, the difference is now reported and the print continues (`mesh_coverage`, default `WARN`). A saved mesh, or `mesh_coverage: STOP`, still stops the print.
- The coverage message shows the mesh area rounded to 0.1 mm.

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
