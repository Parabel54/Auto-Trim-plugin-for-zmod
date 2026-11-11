# Changelog

All notable changes to Auto Trim for zMod are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

## [3.9.10] - 2026-11-11

### Fixed
- `SOAK=AUTO` did not count the time the bed had already been hot during the nozzle clean (the console said `0 s covered by the nozzle clean`), so prints waited the full soak on top of the clean. The time from the start of `AUTO_TRIM_PREPARE`, when `START_PRINT` has finished heating the bed, now counts. Prints wait less; never less than the soak needs.

## [3.9.9] - 2026-11-11

### Fixed
- `SOAK=AUTO` waited only for the centre of the bed, although the soak calibration also measures points near the corners, which can settle later. It now waits for the slowest measured point.
- A measured soak was cut to `soak_max` (600 s), the limit meant for the per-degree estimate, so a bed that takes longer to settle was probed too early even after calibrating. A measured soak now has its own limit, `soak_cal_max` (2700 s).

## [3.9.8] - 2026-11-10

### Added
- Bed heat soak before probing (from the 4.0 beta), off by default: `soak` setting or `SOAK=` on the start line (`AUTO`, `OFF` or seconds). `AUTO_TRIM_SOAK_CALIBRATE BED=` measures it from a cold bed; `AUTO_TRIM_SOAK_ABORT` stops it. A print is refused while a soak calibration runs, and a soak round finding a print running stops the calibration without touching the heaters.
- `AUTO_TRIM_MESH_CALIBRATE BED=`: from a cold bed, nozzle clean, soak calibration, then (only if the bed settled) a full mesh at probing temperature saved as the profile used by `MESH=SAVED`, and `SAVE_CONFIG`.
- Soak probes use `probe_speed` (1 mm/s), like the meshes.

## [3.9.7] - 2026-11-09

### Changed
- Probe speed 1 mm/s for every bed mesh (Auto Trim, zMod and KAMP) and Auto Trim's bed-check probes, through a new `probe_speed` setting (0 = Klipper's own speed). Travel, lifts, homing and zMod's other probing keep their stock speeds.

### Fixed
- 3.9.6 set `[probe]` and `[stepper_z]` from inside `auto_trim.cfg`: all probing at 1 mm/s, and Z homing at 1 mm/s. On the AD5X, Z homes to an endstop at the bottom (stock 20 mm/s), so each homing could take minutes. Both overrides are removed.
- AD5X trash chute: the nozzle went to the chute right after homing, at its lowest height, before rising to Z 20. It now rises first, as zMod's own pre-clean does, also before the reheat.
- Every rubber wipe retracts the filament 2 mm, but only the 3 mm retracted after the purge was pushed back at the reheat, so the purge line started with the filament several millimetres back. All of it is now pushed back.
- `zmod_preclean: KEEP` runs zMod's own pre-clean sequence again (3.9.6 replaced its wipes).
- Auto Trim for zMod installed on Forge-X stopped with `'...GetStatusWrapper object' has no attribute 'save_variables'`. It now says that Forge-X needs Auto Trim for Forge-X.

## [3.9.6] - 2026-11-08

Config-only update based on the GitHub 3.9.4 package. No new Python modules or installer scripts.

### Changed
- Default native bed probing to 1 mm/s and both Z homing touches to 1 mm/s. Keep 5 mm/s lift; preserve retract distance, samples, tolerances and offsets. Explicitly request 1 mm/s for Auto Trim full meshes and bed-check probes; KAMP inherits the global probe default because its wrapper drops command parameters.
- Default AD5X cooling-wipe interval to 70 C. Keep hot post-purge and final cool wipes. Add optional `COOL_WIPE_STEP` on `AUTO_TRIM_PREPARE`.
- Default AD5X rubber wipe to four gentle alternating X65/X81 sweeps from the slower zMod 1.7.5 pass, retaining the stock three Y in/out chute-knocking cycles and omitting the aggressive fast X shaking. Keep the entry/exit corridor and 2 mm retraction. Restore caller coordinate/extrusion modes without returning to the saved position.
- Add optional `RUBBER_WIPE=SOFT|STOCK`; use `COOL_WIPE_STEP=25 RUBBER_WIPE=STOCK` to select the older interval and installed stock wipe for Auto Trim's trash-clean/reheat path. The earlier optional pre-clean follows the configured default.

### Scope and validation
- A true guarded 5-to-1 approach requires native helper code and is not represented as a config setting. This config-only version uses 1 mm/s throughout, as selected.
- Keep calibration, learned trims, offset math, mesh selection and print heating sequence unchanged. No Deep Calibration/startup experiments are imported.
- Macro compilation and offline route/motion/option checks pass; physical 3.9.6 validation remains pending.

## [3.9.4] - 2026-11-05

### Changed
- zMod 1.7.5: without labelled objects, the purge line is planned outside the first-layer area zMod finds in the file (Fast KAMP) instead of using a stock edge line or skipping the purge. The stock edge line fallback uses that area too.
- zMod 1.7.5: without labelled objects, the `!! no labelled objects, so KAMP cannot size the mesh` warning (a touch screen popup) is no longer shown when zMod sized the mesh itself (Fast KAMP); an information line says so instead.
- README: a section on zMod 1.7.5 (print dialog leveling option, Fast KAMP, labelled objects, 3MF files, screen).

## [3.9.3] - 2026-11-04

### Fixed
- Without layer numbers from the slicer, a Z-hop, pause or lift above 1 mm during the first layer could end the first layers early, so later first-layer babysteps were not learned. The nozzle height now only counts while printing (not paused) and when it stays above 1 mm for two checks in a row, and the console says when layer numbers are missing.
- An error during `AUTO_TRIM_PREPARE` after the offset was set (a heater fault, a failing purge or wipe macro) left the offset applied. The watcher now starts right after the offset is set, so the offset is reset when the print stops.
- `AUTO_TRIM_SET MATERIAL=PLA TRIM=...` saved a trim that is never used, and the status listed it as learned. The baseline filament is now refused, with a pointer to `CALIBRATION=`.
- State left over from an earlier print that stopped early (filament, the saved-mesh flag) is cleared at the start of `AUTO_TRIM_PREPARE`.
- AD5M with the parts filling the bed: the console said an edge line would be used, then that there was none. It now gives one message.
- Purge and wipe macro names are no longer case-sensitive, and a wipe macro that does not exist stops the print before heating.
- A start line without `MATERIAL=` now uses the `baseline` filament instead of PLA.
- Without labelled objects, the purge line was drawn across the front of the bed, where the print could be. A stock edge line is used instead (AD5X), or the purge is skipped with a notice (AD5M).

### Changed
- The purge line wipe move stays within the printer travel limits.
- The stock edge line runs inside save and restore of the G-code state, as the zMod purge does.
- README: the layer change G-code is needed for reliable learning, `CHECK=AREA` mostly measures probe repeatability, the edge line clearance is small on purpose, and `zmod_preclean: KEEP` copies the zMod 1.7 sequence.

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

