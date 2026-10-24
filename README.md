# Auto Trim for zMod

Automatic first-layer Z offset management for Flashforge AD5X, AD5M and AD5M Pro printers running zMod.

Version 3.8.0 (2026-10-24). For printers running Forge-X, use Auto Trim for Forge-X.

Auto Trim sets the first-layer Z offset at the start of every print from a stored calibration, a per-filament adjustment and a bed measurement taken immediately before printing. Babystep corrections made during the first layer are stored and applied to later prints.

## Features

- One command at print start: cleans the nozzle, maps the bed under the model (KAMP), checks the mesh, sets the Z offset and draws a purge line, with a single cool-down and a single reheat.
- Clean probing on the AD5X: the nozzle cools and is wiped at the trash chute, so no filament oozes onto the bed before probing.
- Per-filament first layers: a shared base offset plus a small adjustment per filament type, picked automatically from the filament type set in the slicer.
- Learns from babysteps: corrections made during the first layers are saved as soon as those layers are printed, so the next print of that filament starts where the first layer ended up. Later changes are not learned.
- The KAMP mesh is the only probing: the mesh is checked for coverage and for an unusual range (a lifted plate or debris), at no extra time. An optional re-probe of the mapped area is available (`CHECK=AREA`).
- Purge line outside the print area: placed clear of all parts plus a margin for supports, brims and skirts.
- Safety stops: the print stops before printing if settings are wrong, the bed check looks wrong, or the offset would be out of range.
- Detailed console output: every measurement, the offset breakdown and every learned change is printed.
- Leaves the offset at 0 after every finished print.

## Requirements

| | |
|---|---|
| Printer | Flashforge AD5X, AD5M or AD5M Pro |
| Firmware | [zMod](https://github.com/ghzserg/zmod) 1.7.1 or newer (built against 1.7.4, tested on 1.7.1 with an AD5X) |
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
- It checks the fresh mesh before printing and stops if the plate looks lifted or has debris under it.
- It records babystep corrections made during the first layer and applies them to later prints.

Example: a PLA first layer looks slightly high, and the nozzle is lowered by 0.02 mm while it prints. Auto Trim stores the correction, and the next PLA print starts 0.02 mm lower.

## Print start sequence

No input is needed during these steps. The sequence takes a few minutes.

On the AD5X the nozzle is cleaned at the trash chute, so nothing hot or oozing is held over the bed:

| Step | What the printer does | Why |
|---|---|---|
| 1 | Homes, heats the bed and nozzle | Standard zMod start (`START_PRINT`). The zMod nozzle pre-clean is skipped, because Auto Trim cleans the nozzle itself in steps 2 to 4 |
| 2 | Purges 10 mm into the trash chute and wipes the nozzle on the rubber pad while it is still hot | Clears old filament and removes the purged strand before it can cool and fall onto the bed |
| 3 | Waits at the trash chute while the nozzle cools to 121 C, wiping it on the rubber pad every 25 C (195, 170, 145) and returning to the chute in between | Ooze is removed in stages as it forms, instead of building into one long string |
| 4 | Wipes the cooled nozzle on the rubber pad a final time | The nozzle is clean and no longer oozing when probing starts |
| 5 | Maps the bed under your model | The KAMP mesh: only the area you are printing on |
| 6 | Checks the mesh | It must cover the print and stay within a normal range |
| 7 | Sets the Z offset | Saved calibration + filament adjustment |
| 8 | Returns to the trash chute, heats back up, refills the nozzle and wipes it, then re-zeroes the load cell | The nozzle reaches the print ready to extrude and clean, and the zMod collision protection starts from a fresh zero |
| 9 | Draws a purge line outside the print area | Primes the nozzle where it cannot touch parts, supports, brims or skirts |
| 10 | Prints | Babystep corrections can be made during the first layer |
| 11 | Saves the first-layer babystep corrections when layer 3 starts, and resets the offset to 0 at the end | Improves the start of the next print |

On the AD5M and AD5M Pro, which have no trash chute, steps 2 to 4 use the standard zMod nozzle clean instead (wipe hot, then cool), and step 8 heats the nozzle above the start of the purge line, outside the print area.

The nozzle is heated, cooled and reheated once each. This is the minimum, because purging requires a hot nozzle, probing requires a cool one and printing requires a hot one. For filaments printed above 230 C, the nozzle cools to 151 C instead of 121 C.

## Terminology

| Word | Meaning | Example |
|---|---|---|
| Z offset | How far the nozzle sits above the bed for the first layer | `0.23` |
| Babystep | A small adjustment of the nozzle height while printing, from Fluidd, Mainsail or the screen | "lower by 0.01" |
| Calibration | The base offset of the printer, learned from PLA prints | `0.23` |
| Trim | The difference between a filament and PLA | PETG `+0.025` |
| Drift | How much the bed moved between mapping and an optional re-check (`CHECK=AREA`). 0 when the check is off (the default) | `0.004` |
| Mesh | The map of the bed shape | A grid of up to 5 x 5 points |
| KAMP | Mapping only the part of the bed you are printing on | A small part gets a small map |

The final offset is calibration + trim (+ drift when the optional check is on).

Example: calibration `0.23` + PETG trim `0.025` = `0.255`

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

1. Start the print. After the mesh the console shows a line such as:
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

3. Keep printing. When layer 3 starts, the correction is saved and the console shows:
```
AUTO TRIM: first 2 layers printed (now on layer 3), learning the first-layer offset
AUTO TRIM: calibration 0.25 -> 0.23 (babysteps -0.02)
```
At the end of the print the offset is reset to 0.
Subsequent prints start at `0.23`.

If the correct offset is already known, set it before the first print:
```
AUTO_TRIM_SET CALIBRATION=0.23
```

Cancelled prints: a print cancelled during the first two layers teaches nothing, so a failed first layer cannot store a bad value. A print cancelled later keeps its first-layer correction, because it was already saved. If the correct height was found before cancelling on the first layers, read the current offset in Fluidd and save it with `AUTO_TRIM_SET CALIBRATION=<value>`.

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

To use your own purge routine instead of the built-in line (for example one that loops back to catch the string some filaments such as PETG leave behind), add `PURGE_MACRO=<your macro>`:
```
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]} PURGE_MACRO=MY_PURGE
```
Your macro runs at the same point as the built-in line: after the reheat, at print temperature, with the Z offset already set. It receives the planned position outside the print area as `X0`, `Y0`, `X1` and `Y1`, which it can use or ignore. If the macro does not exist, the print stops before heating with a clear message.

## Saved mesh instead of probing

For large prints, probing a fresh mesh takes several minutes (about 6.6 seconds per point on an AD5X, so about 5.5 minutes for a full 7 x 7 mesh). `MESH=SAVED` skips it: Auto Trim loads a saved full-bed mesh and probes only 5 points, at the corners and centre of the print area, to measure how far the whole bed has moved since the mesh was saved. That shift is applied to the Z offset.

```
AUTO TRIM: loaded saved mesh 'auto' instead of probing
AUTO TRIM: checking 5 points at the print area corners and centre (7x7 mesh)
AUTO TRIM: KAMP-area check: 5 points, drift (average) 0.03, spread 0.02
AUTO TRIM: saved mesh matches the bed under this print (spread 0.02 mm), offset corrected by 0.03 mm
```

If the saved mesh no longer fits the bed, a fresh KAMP mesh is built automatically, still before reheating:
- the 5 points disagree by more than `saved_max_spread` (0.15 mm): the bed has changed shape since the mesh was saved, or
- the whole bed has shifted by more than `max_drift` (0.3 mm): usually a different plate.

Setting it up:
1. Heat the bed to the temperature you normally print at and let it settle for a few minutes. The bed changes shape slightly with temperature.
2. Run a full bed leveling from the zMod menu or `AUTO_FULL_BED_LEVEL`. zMod saves it as the profile `auto`.
3. Run `SAVE_CONFIG` so the mesh survives a restart.

Redo this after changing plates or re-levelling the bed screws. `saved_profile` selects a different profile name.

`MESH=AUTO` chooses for you: KAMP when the print needs at most 16 mesh points (`auto_kamp_points`), the saved mesh for larger prints, and KAMP when no saved mesh exists. The console shows which was chosen:
```
AUTO TRIM: preparing (SAVED mesh (AUTO: KAMP would need 25 points), TRASH clean, print 220/60 C)
```

## Ongoing use

No routine action is needed. If a first layer looks wrong, babystep during the first layer and Auto Trim stores the correction once the first two layers are printed.

Only first-layer corrections are learned. If you change the offset later in the print (for example to fix a later layer), that change applies to the rest of this print but is not learned, and the console reports it at the end:
```
AUTO TRIM: offset changed by 0.05 after the first layers, not learned (first-layer offset 0.0711 was learned)
```

When the first layers count as done:
- If the slicer reports layer numbers, when layer 3 starts. To enable this in OrcaSlicer, add `SET_PRINT_STATS_INFO CURRENT_LAYER={layer_num + 1}` to Printer settings > Machine G-code > Layer change G-code (many printer profiles already have it).
- Otherwise, when the nozzle first rises above Z 1.0 mm (about layer 5 at 0.2 mm layers). This threshold is above typical first-layer Z-hops.
- Prints too short to get there are learned at the end instead.

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

## Mesh check output

The KAMP mesh is the only probing by default. Right after it, Auto Trim checks that it covers the print and that its range is normal, then sets the offset:

```
AUTO TRIM: KAMP area X77.0-143.0 Y87.0-133.0 (print X80-140 Y90-130)
AUTO TRIM: mesh range 0.087 mm over 9 points
AUTO TRIM: bed check off, using the KAMP mesh only (drift 0)
AUTO TRIM: PLA offset = calibration 0.23 (saved) + trim 0.0 + drift 0.0 = 0.23
```

- `KAMP area`: the region that was mapped, i.e. the footprint of the model plus a few millimetres.
- `mesh range`: the difference between the highest and lowest point of the mesh. A normal bed under a single print area is usually well under 0.3 mm. Above `max_mesh_range` (0.6 mm) the print is stopped, because that usually means a lifted plate or something under it.

### Optional bed check

`CHECK=AREA` on the `AUTO_TRIM_PREPARE` line re-probes 5 points of the mapped area (the four corners and the middle) after the mesh and applies the average difference as drift. `CHECK=ALL` re-probes every mesh point. This adds about 35 to 40 seconds per print. Measured on an AD5X, the difference is usually a steady few hundredths of a millimetre, which the calibration absorbs anyway, so the check is off by default.

```
AUTO TRIM:   X77.0 Y87.0: probe -1.4342 mesh -1.4382 difference 0.004
...
AUTO TRIM: KAMP-area check: 5 points, drift (average) 0.004, spread 0.0
AUTO TRIM: PLA drift this print 0.004 (5 points, spread 0.0), learned 0.002, difference 0.002
```

With the check on, each filament keeps a learned drift used for comparison only. If you switch the check off after using it, the first print may start a few hundredths of a millimetre higher than before; one babystep corrects it.

## Safety stops and notices

Auto Trim stops the print before printing starts, so nothing is damaged. The console states the reason.

| Message contains | What it means | What to do |
|---|---|---|
| `MESH_TEST must be 0`, `PRINT_LEVELING must be 0` or `DISABLE_PRIMING=1` | A zMod setting is wrong | Run the command from Installation step 3, then `RESTART` |
| `the mesh varies by` | The mesh range is above `max_mesh_range` (0.6 mm) | Check the plate is seated flat with nothing under it, then reprint |
| `differs from the fresh mesh by 0.35` (with `CHECK=AREA`) | One spot measured very differently seconds after mapping | Make sure the plate is clean and seated flat, then reprint |
| `check points disagree by 0.46` (with `CHECK=AREA`) | The spots do not agree with each other by more than 0.4 mm | Look for something under the plate, or a bent or lifted plate |
| `outside safe range` | The final offset would be beyond -0.8 / +0.8 mm | Check your numbers with `AUTO_TRIM_STATUS`, fix with `AUTO_TRIM_SET` |
| `does not cover this print` | The map does not match where your model is | Make sure Label objects is on in Orca and re-slice |
| `no bed mesh` | Mapping failed | Check the console above for a probing error |
| `not found. Is this zMod?` | A zMod command is missing | Update zMod, or check you are not on Forge-X |

Notices (lines starting `!!` that do not stop the print):
- `drift is 0.15 mm away from its learned value` (with `CHECK=AREA`): the bed check found a bigger change than usual for this filament. The print continues. If the plate was swapped or moved, that is expected. If not, check it is clean.
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
(`temp_test_max` is used for filaments printed above 230 C.) On the AD5X these settings are used by the Auto Trim trash-chute clean on any zMod version. With the standard zMod clean (AD5M, AD5M Pro, or `CLEAN=ZMOD`), they need zMod 1.7.4 or newer; zMod 1.7.1 always cools to 121 C and 151 C.

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
| `MESH=SAVED` | Uses the saved full-bed mesh and probes only 5 points (see Saved mesh instead of probing) | `MESH=SAVED` |
| `MESH=AUTO` | KAMP for small prints, the saved mesh for large ones | `MESH=AUTO` |
| `CHECK=AREA` | Re-probes 5 points of the mapped area after the mesh and applies the drift. About 35 to 40 seconds longer | `CHECK=AREA` |
| `CHECK=ALL` | Re-probes every mesh point. Slower | `CHECK=ALL` |
| `PURGE=0` | Skips the purge line | `PURGE=0` |
| `PURGE_MACRO=<macro>` | Runs your own purge macro instead of the built-in line | `PURGE_MACRO=MY_PURGE` |
| `CLEAN=ZMOD` | Uses the standard zMod nozzle clean instead of the trash-chute clean on the AD5X | `CLEAN=ZMOD` |

Example with a full-bed mesh and the optional bed check:
```
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]} MESH=FULL CHECK=AREA
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

7 x 7 is the recommended maximum on the AD5X. A 9 x 9 mesh has been seen to stop the printer with `MCU 'mcu' shutdown: Timer too close`: after probing, Klipper interpolates the mesh into 41 x 41 points (`mesh_pps: 5, 5`), which can overload the small processor in the printer. A smaller `move_check_distance` adds to the load, so do not set it below the stock value. If you want 9 x 9 anyway, reduce the interpolation:
```
[bed_mesh]
probe_count: 9, 9
mesh_pps: 2, 2
```

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

In `AUTO_TRIM_LEARN`:

| Setting | Default | What it does |
|---|---|---|
| `learn_after_layers` | 2 | First-layer corrections are learned once this many layers are printed (when the slicer reports layer numbers) |
| `learn_above_z` | 1.0 mm | Otherwise, learned once the nozzle first rises above this height |

In `AUTO_TRIM_PREPARE`:

| Setting | Default | What it does |
|---|---|---|
| `mesh` | `KAMP` | `KAMP`, `FULL`, `SAVED` or `AUTO` |
| `saved_profile` | `auto` | Saved mesh used by `SAVED` and `AUTO` |
| `saved_max_spread` | 0.15 mm | With the saved mesh: build a fresh KAMP mesh if the 5 points disagree by more than this |
| `auto_kamp_points` | 16 | With `AUTO`: largest KAMP mesh (in points) before the saved mesh is used instead |
| `check` | `OFF` | `OFF` (mesh only), `AREA` (re-probe 5 points) or `ALL` (re-probe every point) |
| `max_mesh_range` | 0.6 mm | Stop if the mesh varies by more than this |
| `purge` | on | Draw the purge line |
| `purge_macro` | none | Your own purge macro, used instead of the built-in line |
| `purge_clearance` | 10 mm | Space kept clear around the labelled parts, for supports, brims and skirts |
| `purge_length` | 30 mm | Length of the purge line |
| `purge_amount` | 30 mm | Filament extruded for the line |
| `purge_height` | 0.8 mm | Nozzle height for the line |
| `purge_flow` | 12 mm3/s | Flow rate for the line |
| `clean` | `AUTO` | `AUTO` (trash-chute clean on the AD5X, standard zMod clean on the AD5M and AD5M Pro), `TRASH` or `ZMOD` |
| `cool_wipe_step` | 25 C | AD5X: wipe on the rubber pad every this many degrees while the nozzle cools. 0 = only after the purge and at probing temperature |
| `zmod_preclean` | `SKIP` | AD5X: `SKIP` the zMod nozzle pre-clean inside `START_PRINT` (Auto Trim cleans the nozzle itself), or `KEEP` it |
| `restore_tip` | automatic | Filament pushed back to the nozzle tip after reheating, in mm. Automatic: 3 on the AD5X (its clean retracts 3 mm), 0 on the AD5M and AD5M Pro |
| `max_drift` | 0.3 | With the check on: stop if any checked spot is this far from the map |
| `max_spread` | 0.4 | With the check on: stop if the checked spots disagree by more than this |
| `kamp_slack` | 10 | How much bigger than the model a map can be before it is called a full-bed map |
| `settle_ms` | 1000 | Pause in milliseconds after the mesh, so the printer can finish processing it before motion restarts |

Notes:
- Values are stored in the existing zMod `[save_variables]` section. Do not add a second one.
- On the AD5X, `auto_trim.cfg` replaces the zMod pre-clean macro `_PRINT_CLEAR_NOZZLE`, which zMod calls only from `START_PRINT`. With `zmod_preclean: SKIP` it does nothing; with `KEEP` it runs the original zMod sequence. Because the replacement applies to every print, prints sliced without `AUTO_TRIM_PREPARE` also skip the zMod pre-clean while it is set to `SKIP`.
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
