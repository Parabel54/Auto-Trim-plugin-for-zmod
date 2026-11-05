# Changelog

All notable changes to Auto Trim for zMod are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

## [4.0.0-beta.5] - unreleased (beta)

Development work since 3.8.0, not released. Changes existing options (the purge choice, `purge_flow`), so the next release from it will be 4.0.0. The steps below are numbered in the order the work was done. Step 5 was also released on its own as 3.9.0, the purge fixes from steps 3 and 4 as 3.9.1, step 6 as 3.9.2, part of step 7 as 3.9.3, and step 9 as 3.9.4.

### Beta step 9 (2026-11-05)

#### Changed
- zMod 1.7.5: without labelled objects, the purge line and the stock edge line use the first-layer area zMod finds in the file (Fast KAMP), and the "KAMP cannot size the mesh" warning is not shown when zMod sized the mesh itself.
- README: a section on zMod 1.7.5.

### Beta step 8 (2026-11-04)

#### Added
- Automatic first-layer correction from the load cells (`force_mode: AUTO`, with the add-on): calibration stripes (`AUTO_TRIM_FORCE_SWEEP`, `AUTO_TRIM_FORCE_PICK`) measure the target force and the gain for given first-layer settings (`FL_HEIGHT`, `FL_WIDTH`, `FL_SPEED` on the start line); `AUTO_TRIM_FORCE_GOOD` takes the target from a good print. During the first layer the median force of every 8 readings is compared with the target, and the offset corrected proportionally, within a deadband and limits per step and per print. Correction stops if the force does not follow, the zero drifts, or the error is too large to be a height problem. Corrections are learned only when 3 prints in a row agree.
- Load cell add-on: `AUTO_TRIM_CELL_MARK` and `AUTO_TRIM_CELL_MEASURE` (median force over a move).

#### Changed
- The `force_band`, `force_step`, `force_max_steps`, `force_min_samples` and `force_min_prints` settings are replaced by the settings of the new correction.

### Beta step 7 (2026-11-04)

#### Fixed
- The 3.9.3 fixes: learning without layer numbers, the offset after a failed start, `AUTO_TRIM_SET` for the baseline filament, leftover state, AD5M purge messages, macro name case, the `MATERIAL` default, and no labelled objects.
- A print could start while a bed soak calibration was running, and the next calibration round would probe the bed mid-print and switch the heaters off. Starting a print is now refused while a calibration runs, and a round during a print stops the calibration without touching the heaters.
- A flush test stopped by a failed tool change left zMod `use_trash_on_print` at 0. It is backed up first and put back at the next print start or `AUTO_TRIM_STATUS`. The number of dots is limited to what fits across the bed.
- Load cell add-on: it reported "connected" as soon as it was hooked in, even without readings. It now does so only after the first reading, and keeps 50 readings instead of 600.

#### Changed
- `force_mode: AUTO` nudges apply to the current print only and are not learned.
- The wipe macro and the stock edge line run inside save and restore of the G-code state; the purge wipe move stays within the travel limits; the purge size check runs only for the built-in line and checks a hand-set `purge_amount`.
- README: re-run the add-on installer after a zMod update before restarting; preheating from the screen skips the bed soak; the layer change G-code is needed for reliable learning.

### Beta step 6 (2026-11-04)

#### Fixed
- First-layer learning could happen before the first layer: until layer 1 starts the layer number is 0, so the nozzle height was used, and the nozzle is above 1 mm after the purge line. If the start took more than a few seconds (an IFS filament load, for example), "no babysteps" was learned and the first-layer corrections were then reported as not learned. The nozzle height now only counts once the nozzle has been on the first layer.
- `MESH=AUTO` stopped the print with a template error when `probe_count` has a single value (`probe_count: 7`). A single value now counts for both directions.
- With `MESH=SAVED`, the shift of the saved mesh was learned as drift. It is still applied, but no longer learned.
- A cancelled or stopped print kept its Z offset and filament. Both are now cleared and the offset set back to 0.

#### Changed
- The load cells are zeroed after a short pause (1 s, 2 s after the part fan turns off), including in the bed heat soak and its calibration.
- The `settle_ms` description and the README mesh size notes: the pause does not prevent `Timer too close` on dense meshes, and the 7 x 7 limit applies to saved meshes too.

### Beta step 5 (2026-11-02), released on its own as 3.9.0

#### Fixed
- Parts that are wider above their first layer (a flared base, a bowl, an overhang) stopped every print with `the mesh ... does not cover this print`. KAMP meshes the first layer, while the check compared the mesh with the outline of the whole part from the slicer. For a mesh probed for this print, the difference is now reported and the print continues (`mesh_coverage`, default `WARN`). A saved mesh, or `mesh_coverage: STOP`, still stops the print.
- The coverage message shows the mesh area rounded to 0.1 mm.

### Beta step 4 (2026-10-30)

#### Changed
- One purge choice, `PURGE=` / `purge_mode`: `AUTO` (the Auto Trim line outside the print area), `ZMOD` (the zMod purge chosen with `SAVE_ZMOD_DATA CLEAR=`: `LINE_PURGE`, the stock `_CLEAR1` to `_CLEAR4`, or your own macro in `user.cfg`, run after the Z offset is set) or `OFF`.
- Replaces `PURGE_MACRO`, `purge_macro` and `PURGE_OUTSIDE`, since zMod already selects any purge macro. Start G-code with `PURGE_MACRO=<name>` still runs that macro, and `PURGE=0` / `PURGE=1` work as before.

### Beta step 3 (2026-10-29)

#### Added
- Purge macros that draw outside the build area: the zMod stock line-clears (`_CLEAR1` to `_CLEAR4`) are recognised automatically, and `PURGE_OUTSIDE=1` / `purge_macro_outside` marks your own. Auto Trim then plans no line inside the bed for them.
- Edge-line fallback (`purge_fallback`): when the parts leave no room for the built-in line, a stock Flashforge edge line that stays clear of the parts is used instead of skipping the purge.

#### Fixed
- With a purge macro and no room inside the bed, Auto Trim showed an error saying the purge was skipped, although the macro still ran. It now shows an information line.
- Load cell add-on: a failed zero at print start (for example a stalled zMod reader) could stop the print. It now continues with the 20 g readings.
- Load cell add-on: a single nonsense reading from the board (above 5 kg) could distort the precise force for a second. These are now ignored.

### Beta step 2 (2026-10-28)

#### Added
- Optional load cell add-on `auto_trim_cell.py`: keeps the raw count from the bed weighing board, which zMod discards, for a signed force to a fraction of a gram instead of 20 g steps. Reads the replies zMod already receives. Commands `AUTO_TRIM_CELL_TARE`, `AUTO_TRIM_CELL_READ`, `AUTO_TRIM_CELL_CALIBRATE`.
- First-layer force uses the add-on when it is installed (`force_contact`), and falls back to the 20 g readings otherwise.

### Beta step 1 (2026-10-28)

#### Added
- Bed heat soak: `AUTO_TRIM_SOAK_CALIBRATE` measures how long the bed keeps moving after heating. Prints starting from a cold bed wait for it before probing; the nozzle clean counts towards the wait.
- Live first-layer adjustment: `AUTO_TRIM_CLOSER` and `AUTO_TRIM_AWAY`.
- First-layer force from the bed load cell (`force_mode`): measured on every print, kept as a per-filament reference when the first layer needed no correction, and with `AUTO` used to nudge the offset (experimental; the default only measures).
- Nozzle size: `AUTO_TRIM_SET NOZZLE=`. The purge line is 2.5 x the nozzle wide and 0.75 x high, and is checked against the extruder limit.
- Colour-change flush test for the AD5X IFS: `AUTO_TRIM_FLUSH_TEST` and `AUTO_TRIM_FLUSH_RESULT`.

#### Changed
- Purge line: 60 mm at 10 mm/s with the filament amount worked out from its size (about 7.5 mm for a 0.4 mm nozzle). `purge_flow` is replaced by `purge_speed`.

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
