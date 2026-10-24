# Changelog

All notable changes to Auto Trim for zMod are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

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
