# Auto Trim for zMod

Automatic first-layer Z offset management for Flashforge AD5X, AD5M and AD5M Pro printers running zMod.

Version 3.4.0 (2026-10-21). For printers running Forge-X, use Auto Trim for Forge-X.

Auto Trim sets the first-layer Z offset at the start of every print from a stored calibration, a per-filament adjustment and a bed measurement taken immediately before printing. Babystep corrections made during the first layer are stored and applied to later prints.

## Features

- One command at print start: cleans the nozzle, maps the bed under the model (KAMP), re-checks the mapped area, sets the Z offset and draws a purge line, with a single cool-down and a single reheat.
- Clean probing on the AD5X: the nozzle cools and is wiped at the trash chute, so no filament oozes onto the bed before probing.
- Per-filament first layers: a shared base offset plus a small adjustment per filament type, picked automatically from the filament type set in the slicer.
- Learns from babysteps: corrections made during the first layer are saved, so the next print of that filament starts where the last one finished.
- Bed check across the printed area: re-probes the corners and centre of the mapped area right after mapping, and applies any shift it finds.
- Purge line outside the print area: placed clear of all parts plus a margin for supports, brims and skirts.
- Safety stops: the print stops before printing if settings are wrong, the bed check looks wrong, or the offset would be out of range.
- Detailed console output: every measurement, the offset breakdown and every learned change is printed.
- Leaves the offset at 0 after every finished print.

## Requirements

| | |
|---|---|
| Printer | Flashforge AD5X, AD5M or AD5M Pro |
| Firmware | [zMod](https://github.com/ghzserg/zmod) (built against zMod 1.7.4) |
| Slicer | OrcaSlicer (any slicer works if it can fill in the same values; the G-code below uses OrcaSlicer placeholders) |
| Slicer setting | Label objects (exclude objects) turned on, so the mesh and the purge line can be placed around the parts |

Not for Forge-X: use Auto Trim for Forge-X instead.

## Status

Beta. Built against the zMod 1.7.4 macros and tested extensively in a Klipper simulation of the print start (fresh installs, restarts, every safety stop, KAMP and full meshes, different temperatures and filaments). It has not yet been confirmed across many real printers. Watch the console on your first few prints, and please report anything unexpected (see Reporting problems).

## Overview

Before each print, the printer probes the bed with the nozzle at a grid of points. The resulting mesh describes the shape of the bed, so the printer can follow it while printing. The mesh does not determine how far the nozzle sits above the bed on the first layer; that is set by the Z offset. If the offset is too high, the first layer does not adhere. If it is too low, the nozzle scrapes the bed and the extruder can clog.

Auto Trim manages the Z offset as follows:

- It stores a base offset for the printer (the calibration).
- It applies a per-filament adjustment (the trim). PETG, for example, typically needs slightly more clearance than PLA.
- It re-checks the mapped area immediately before printing and corrects for any shift.
- It records babystep corrections made during the first layer and applies them to later prints.

Example: a PLA first layer looks slightly high, and the nozzle is lowered by 0.02 mm while it prints. Auto Trim stores the correction, and the next PLA print starts 0.02 mm lower.

## Print start sequence

No input is needed during these steps. The sequence takes a few minutes.

On the AD5X the nozzle is cleaned at the trash chute, so nothing hot or oozing is held over the bed:

| Step | What the printer does | Why |
|---|---|---|
| 1 | Homes, heats the bed and nozzle | Standard zMod start (`START_PRINT`) |
| 2 | Purges 10 mm into the trash chute at print temperature | Clears old filament from the nozzle |
| 3 | Waits at the trash chute while the nozzle cools to 121 C | Any ooze during cooling falls into the chute, not onto the bed |
| 4 | Wipes the cooled nozzle on the rubber pad | The nozzle is clean and no longer oozing when probing starts |
| 5 | Maps the bed under your model | The KAMP mesh: only the area you are printing on |
| 6 | Re-checks 5 spots of that area | Makes sure the bed has not moved since step 5 |
| 7 | Sets the Z offset | Saved calibration + filament adjustment + any shift found in step 6 |
| 8 | Returns to the trash chute, heats back up, refills the nozzle and wipes it | The nozzle reaches the print ready to extrude and clean |
| 9 | Draws a purge line outside the print area | Primes the nozzle where it cannot touch parts, supports, brims or skirts |
| 10 | Prints | Babystep corrections can be made during the first layer |
| 11 | Stores babystep corrections, then resets the offset to 0 | Improves the start of the next print |

On the AD5M and AD5M Pro, which have no trash chute, steps 2 to 4 use the standard zMod nozzle clean instead (wipe hot, then cool), and step 8 heats the nozzle above the start of the purge line, outside the print area.

The nozzle is heated, cooled and reheated once each. This is the minimum, because purging requires a hot nozzle, probing requires a cool one and printing requires a hot one. For filaments printed above 230 C, the nozzle cools to 151 C instead of 121 C.

## Terminology

| Word | Meaning | Example |
|---|---|---|
| Z offset | How far the nozzle sits above the bed for the first layer | `0.23` |
| Babystep | A small adjustment of the nozzle height while printing, from Fluidd, Mainsail or the screen | "lower by 0.01" |
| Calibration | The base offset of the printer, learned from PLA prints | `0.23` |
| Trim | The difference between a filament and PLA | PETG `+0.025` |
| Drift | How much the bed moved between mapping and the re-check. Normally almost zero | `0.004` |
| Mesh | The map of the bed shape | A grid of up to 5 x 5 points |
| KAMP | Mapping only the part of the bed you are printing on | A small part gets a small map |

The final offset is calibration + trim + drift.

Example: calibration `0.23` + PETG trim `0.025` + drift `0.004` = `0.259`

## Installation

### 1. Upload the file

In Fluidd or Mainsail, open Configuration > mod_data and upload `auto_trim.cfg`.

### 2. Include the file

Open `user.cfg` in the same folder and add this as the very first line:
```
[include auto_trim.cfg]
```
Save.

### 3. Set three zMod parameters

Run in the console:
```
SAVE_ZMOD_DATA DISABLE_PRIMING=1 MESH_TEST=0 PRINT_LEVELING=0
```

| Setting | Set to | Why |
|---|---|---|
| `DISABLE_PRIMING` | 1 | Stops zMod drawing its own purge line inside `START_PRINT`, before Auto Trim has set the height |
| `MESH_TEST` | 0 | Auto Trim runs its own check. The zMod check would add another heat-and-cool cycle |
| `PRINT_LEVELING` | 0 | Stops zMod making its own mesh. Auto Trim makes it instead |

If one of these is wrong, Auto Trim stops the print and tells you which one to fix.

### 4. Restart

Type `RESTART` in the console. To make sure it loaded, type `AUTO_TRIM_STATUS`. You should see a line starting `AUTO TRIM v` followed by the version number.

### 5. Configure OrcaSlicer

Machine start G-code (Printer settings > Machine G-code > Machine start G-code). Replace everything with:
```
START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer] BED_TEMP=[bed_temperature_initial_layer_single] SKIP_LEVELING=True
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]}
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
```
The same three lines work on the AD5X, AD5M and AD5M Pro.

Machine end G-code. Replace everything with:
```
AUTO_TRIM_LEARN
END_PRINT
```

Keep the `START_PRINT` and `END_PRINT` lines exactly as they are: zMod checks every print file for them.

Additional OrcaSlicer settings:
- Label objects: turn it on (Process > Others > Label objects). Without it the printer cannot tell where your model is, so it cannot map just that area.
- Filament type: check every filament profile has the right type (PLA, PETG, TPU...). That is how Auto Trim knows which adjustment to use.
- Old offset lines: if the Filament start G-code of any filament profile contains `SET_GCODE_OFFSET`, delete those lines. They would override Auto Trim.

### 6. Re-slice

Previously sliced files contain the old start code and must be sliced again.

## First print calibration

The first print establishes the base offset of the printer. Use PLA and something with a big flat first layer, like a 100 x 100 mm square one layer thick.

1. Start the print. After the bed check the console shows a line such as:
```
AUTO TRIM: PLA offset = calibration 0.25 (default) + trim 0.0 + drift 0.0 = 0.25
```
`0.25` is a starting value. If zMod already had an offset saved, it uses that instead and says `(from existing zMod offset)`.

2. Watch the first layer. Adjust the nozzle height with babysteps of 0.01 to 0.02 mm until it looks right:

| What you see | Means | Do this |
|---|---|---|
| Round lines with gaps between them, or lines not sticking | Too high | Babystep down |
| Thin, see-through lines, rough ridges, nozzle scraping, extruder clicking | Too low | Babystep up |
| Flat lines that just touch each other, smooth surface | Right | Leave it |

3. Let the print finish. At the end the console shows:
```
AUTO TRIM: calibration 0.25 -> 0.23 (babysteps -0.02)
AUTO TRIM: learned PLA drift (first) -> 0.0
AUTO TRIM: Z offset reset to 0
```
Subsequent prints start at `0.23`.

If the correct offset is already known, set it before the first print:
```
AUTO_TRIM_SET CALIBRATION=0.23
```

Cancelled prints: nothing is learned from a cancelled print, so a failed first layer cannot store a bad value. If the correct height was found before cancelling, read the current offset in Fluidd and save it with `AUTO_TRIM_SET CALIBRATION=<value>`.

## Purge line

Before printing, Auto Trim draws a short purge line to prime the nozzle. It is placed outside the whole print area, so it cannot run into parts, supports, brims or skirts:

- The print area is every labelled part plus a clearance of 10 mm (`purge_clearance`). Object outlines from the slicer may not include supports, brims or skirts; the clearance covers them.
- The line goes in the free strip between that area and the edge of the bed, halfway across the strip, centred on the parts. The front is used when it has room. Otherwise the back, left or right side with the most room is used.
- If the parts plus clearance leave no room on any side, the purge is skipped and the console says so. The print continues.
- Without labelled objects (Label objects off in OrcaSlicer), the print area is unknown, so the line is drawn along the front edge of the bed.

Before the line is drawn, the filament is pushed back to the nozzle tip, so the line is full from the start. On the AD5X the nozzle is reheated and wiped at the trash chute before moving to the line. On the AD5M and AD5M Pro it is reheated while hovering above the start of the line, so any ooze lands where the line begins, not on the print area.

The console shows where the line goes:
```
AUTO TRIM: purge line planned on the front side, outside the print area (parts X80 to 140 Y90 to 130 plus 10.0 mm clearance), from X95.0 Y40.0 to X125.0 Y40.0
```

To skip the purge line, add `PURGE=0` to the `AUTO_TRIM_PREPARE` line.

## Ongoing use

No routine action is needed. If a first layer looks wrong, babystep during the first layer and Auto Trim stores the correction.

Where babystep corrections are stored:

| You babystep while printing... | It changes... | Effect |
|---|---|---|
| PLA | the calibration | Every filament moves with it |
| Any other filament | only the trim of that filament | Only that filament changes |
| The first print after installation (any filament) | the calibration | The starting value was an estimate |

Example:
- Your calibration is `0.23` and PETG starts at its default trim of `+0.025`, so PETG prints at `0.255`.
- PETG looks a bit low, so you babystep up `+0.01`. Its trim becomes `+0.035`.
- Next PETG print: `0.23 + 0.035` = `0.265`. Your PLA is unaffected.
- Later you swap to a new nozzle, and a PLA print needs `-0.02`. The calibration becomes `0.21`. Now PLA prints at `0.21` and PETG at `0.21 + 0.035 = 0.245`, both moved together.

Corrections can be any size, up or down. Negative values are supported (for example a calibration of `-0.05`).

## Bed check output

Before each print, Auto Trim re-measures 5 spots of the mapped area: the four corners and the middle. It compares each one with the map it just made. The console shows all of it:

```
AUTO TRIM: KAMP area X77.0-143.0 Y87.0-133.0 (print X80-140 Y90-130)
AUTO TRIM: checking 5 points across the KAMP area (3x3 mesh)
AUTO TRIM:   X77.0 Y87.0: probe -1.4342 mesh -1.4382 difference 0.004
AUTO TRIM:   X143.0 Y87.0: probe -1.3946 mesh -1.3986 difference 0.004
AUTO TRIM:   X77.0 Y133.0: probe -1.4526 mesh -1.4566 difference 0.004
AUTO TRIM:   X143.0 Y133.0: probe -1.4130 mesh -1.4170 difference 0.004
AUTO TRIM:   X110.0 Y110.0: probe -1.4290 mesh -1.4330 difference 0.004
AUTO TRIM: KAMP-area check: 5 points, drift (average) 0.004, spread 0.0
AUTO TRIM: PLA drift this print 0.004 (5 points, spread 0.0), learned 0.002, difference 0.002
AUTO TRIM: PLA offset = calibration 0.23 (saved) + trim 0.0 + drift 0.004 = 0.234
```

How to read it:
- `KAMP area`: the region that was mapped, i.e. the footprint of the model plus a few millimetres.
- `difference`: how far that point moved since it was mapped. A few thousandths of a millimetre is normal.
- `drift`: the average of the differences, added to the offset for this print.
- `spread`: the range between the highest and lowest difference. A value near zero means the area moved evenly, which is expected.
- `learned` / `difference`: compares the drift on this print with the usual value for this filament. A large change usually means the plate was swapped or moved.

At the end of the print, the learned value is updated:
```
AUTO TRIM: learned PLA drift 0.002 -> 0.003 (this print 0.004, difference 0.002)
```
The learned drift is used only for comparison and history. It does not change the saved offset; only babystep corrections do. This prevents measurement noise from accumulating over many prints.

## Safety stops and notices

Auto Trim stops the print before printing starts, so nothing is damaged. The console states the reason.

| Message contains | What it means | What to do |
|---|---|---|
| `MESH_TEST must be 0`, `PRINT_LEVELING must be 0` or `DISABLE_PRIMING=1` | A zMod setting is wrong | Run the command from Installation step 3, then `RESTART` |
| `differs from the fresh mesh by 0.35` | One spot measured very differently seconds after mapping | Make sure the plate is clean and seated flat, then reprint |
| `check points disagree by 0.46` | The spots do not agree with each other by more than 0.4 mm | Look for something under the plate, or a bent or lifted plate |
| `outside safe range` | The final offset would be beyond -0.8 / +0.8 mm | Check your numbers with `AUTO_TRIM_STATUS`, fix with `AUTO_TRIM_SET` |
| `does not cover this print` | The map does not match where your model is | Make sure Label objects is on in Orca and re-slice |
| `no bed mesh` | Mapping failed | Check the console above for a probing error |
| `not found. Is this zMod?` | A zMod command is missing | Update zMod, or check you are not on Forge-X |

Notices (lines starting `!!` that do not stop the print):
- `drift is 0.15 mm away from its learned value`: the bed check found a bigger change than usual for this filament. The print continues. If the plate was swapped or moved, that is expected. If not, check it is clean.
- `START_PRINT should have SKIP_LEVELING=True`: your Orca start G-code is out of date. The print still works but takes longer. Update it as in Installation step 5.
- `no labelled objects`: Label objects is off in Orca, so the whole bed gets mapped and the purge line goes to the front edge. Turn it on.
- `no room for a purge line outside the print area`: the parts plus clearance fill the bed. The purge is skipped and the print continues. Lower `purge_clearance` if your prints have no supports, brims or skirts.

## Default filament adjustments

Until a filament has been printed and corrected, it uses a typical adjustment relative to PLA (positive values raise the nozzle):

| Filament | Starts at |
|---|---|
| PLA | 0 (this is the base) |
| PLA-CF | -0.01 |
| PETG | +0.025 |
| PETG-CF | +0.04 |
| ABS | 0 |
| ASA | +0.01 |
| TPU | +0.025 |
| PA, PA-CF, PA6-CF, PA12-CF, PC | 0 |
| Anything else | 0 |

These are approximate community values. Babystep corrections replace them.

## Bed and build plate

Accurate measurements require:

- One plate, seated flat, with nothing under it: no filament bits, dust or a lifted corner. Anything under the plate gets measured as if it were the bed.
- Clean surface: fingerprints, glue or blobs change where the nozzle "feels" the bed.
- Firm, undamaged surface: very soft coatings, gouges or peeled spots give uneven readings.
- Reasonably level: the mesh corrects tilt, but if one corner is several tenths of a millimetre off, level it first with the zMod `BED_LEVEL_SCREWS_TUNE`.

Heat-sensitive plates (PC, some G10 and coated plates) can get small marks from measuring at 120 C. Lower the measuring temperature:
```
SAVE_VARIABLE VARIABLE=temp_test_min VALUE=110
SAVE_VARIABLE VARIABLE=temp_test_max VALUE=140
```
(`temp_test_max` is used for filaments printed above 230 C.)

Swapping plates: the mesh accounts for the thickness of a different plate automatically. A different surface may still need a different first-layer height (textured plates often print best slightly lower). A babystep correction on a PLA print with the new plate is applied to every filament. When alternating between plates, record the calibration for each plate and set it before printing, e.g. `AUTO_TRIM_SET CALIBRATION=0.21`.

## Commands

Run these in the Fluidd or Mainsail console.

| Command | What it does | Example |
|---|---|---|
| `AUTO_TRIM_STATUS` | Shows the version, your calibration, the trim and learned drift of every filament | `AUTO_TRIM_STATUS` |
| `AUTO_TRIM_SET CALIBRATION=<value>` | Sets your base offset by hand | `AUTO_TRIM_SET CALIBRATION=0.23` |
| `AUTO_TRIM_SET MATERIAL=<type> TRIM=<value>` | Sets the adjustment of one filament manually | `AUTO_TRIM_SET MATERIAL=PETG TRIM=0.03` |

`AUTO_TRIM_PREPARE` and `AUTO_TRIM_LEARN` run from the start and end G-code and are not entered manually.

## Start options

Add these to the end of the `AUTO_TRIM_PREPARE` line in the OrcaSlicer start G-code.

| Add | What it does | Example |
|---|---|---|
| `MESH=FULL` | Maps the whole bed instead of only the area under the model. Slower | `MESH=FULL` |
| `CHECK=ALL` | Re-checks every mesh point instead of 5. Slower, more thorough | `CHECK=ALL` |
| `PURGE=0` | Skips the purge line | `PURGE=0` |
| `CLEAN=ZMOD` | Uses the standard zMod nozzle clean instead of the trash-chute clean on the AD5X | `CLEAN=ZMOD` |

Example with a full-bed mesh and a check of every point:
```
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]} MESH=FULL CHECK=ALL
```

Full mesh and KAMP together: KAMP does not refine a full mesh; it builds its own. Running both would probe the same area twice, and only the KAMP mesh would be used. zMod also builds only one mesh per print. Select one with `MESH=`.

### Denser mesh

By default the printer measures at most 5 x 5 = 25 points. For a denser mesh, add `probe_count` to the `[bed_mesh]` section of `user.cfg` (add the section if it is not there), then `RESTART`:
```
[bed_mesh]
probe_count: 7, 7
```

| `probe_count` | Full-bed points | Points at most this far apart |
|---|---|---|
| 5, 5 (default) | 25 | 54 mm |
| 7, 7 | 49 | 36 mm |
| 9, 9 | 81 | 27 mm |

More points take longer: increasing from 25 to 49 roughly doubles the probing time. KAMP also uses the closer spacing, so large models receive more points while small models still need only a few.

## Advanced settings

These settings do not normally need changing. They are defined at the top of each macro in `auto_trim.cfg`.

In `AUTO_TRIM`:

| Setting | Default | What it does |
|---|---|---|
| `baseline` | `pla` | The filament whose babystep corrections set the calibration |
| `default_calibration` | 0.25 | Starting value for the first print if nothing is saved |
| `min_offset` / `max_offset` | -0.8 / 0.8 | Safety limits for the final offset |
| `unset_below` | 0.01 | Saved zMod offsets closer to 0 than this are treated as "never set" |
| `seed_trims` | see table above | Starting adjustment for each filament |
| `drift_learn_rate` | 0.5 | How far the drift from each print moves the learned value (0.5 = halfway) |
| `drift_jump` | 0.1 | How far from normal the drift can be before a notice is shown |

In `AUTO_TRIM_PREPARE`:

| Setting | Default | What it does |
|---|---|---|
| `mesh` | `KAMP` | `KAMP` or `FULL` |
| `check` | `AREA` | `AREA` (5 points) or `ALL` |
| `purge` | on | Draw the purge line |
| `purge_clearance` | 10 mm | Space kept clear around the labelled parts, for supports, brims and skirts |
| `purge_length` | 30 mm | Length of the purge line |
| `purge_amount` | 30 mm | Filament extruded for the line |
| `purge_height` | 0.8 mm | Nozzle height for the line |
| `purge_flow` | 12 mm3/s | Flow rate for the line |
| `clean` | `AUTO` | `AUTO` (trash-chute clean on the AD5X, standard zMod clean on the AD5M and AD5M Pro), `TRASH` or `ZMOD` |
| `restore_tip` | automatic | Filament pushed back to the nozzle tip after reheating, in mm. Automatic: 3 on the AD5X (its clean retracts 3 mm), 0 on the AD5M and AD5M Pro |
| `max_drift` | 0.3 | Stop if any checked spot is this far from the map |
| `max_spread` | 0.4 | Stop if the checked spots disagree by more than this |
| `kamp_slack` | 10 | How much bigger than the model a map can be before it is called a full-bed map |

Notes:
- Values are stored in the existing zMod `[save_variables]` section. Do not add a second one.
- `LOAD_ZOFFSET` can be on or off. Auto Trim sets the offset itself every print. It only matters on the very first print, as a starting point.
- On multi-colour AD5X prints, the adjustment follows the filament in the first slot used, since that one prints the first layer.
- Filament names come from the OrcaSlicer filament type, lowercased, with `-` turned into `_` (`PLA-CF` is stored as `pla_cf`).

## Files

- `auto_trim.cfg`: the Auto Trim macros
- `README.md`: this document
- `CHANGELOG.md`: release history

## Reporting problems

Please include:
- the output of `AUTO_TRIM_STATUS`,
- your zMod version,
- the console lines from the print start, from `START_PRINT` to `AUTO TRIM: ready to print` (all lines starting with `AUTO TRIM` are the most useful),
- your Orca start and end G-code.

## Credits

- [zMod](https://github.com/ghzserg/zmod) by ghzserg: the firmware whose nozzle cleaning, KAMP integration and probing Auto Trim builds on.
- [KAMP (Klipper Adaptive Meshing & Purging)](https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging) by kyleisah: adaptive meshing.
- [Klipper](https://www.klipper3d.org/): the underlying firmware.
