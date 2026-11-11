# Auto Trim for zMod

Automatic first-layer Z offset management for Flashforge AD5X, AD5M and AD5M Pro printers running zMod.

Version 3.9.10 (2026-11-11). For printers running Forge-X, use Auto Trim for Forge-X.

## Contents

1. [What Auto Trim does](#what-auto-trim-does)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Your first print](#your-first-print)
5. [What happens when a print starts](#what-happens-when-a-print-starts)
6. [How the offset is built and learned](#how-the-offset-is-built-and-learned)
7. [Bed mesh: KAMP, FULL, SAVED or AUTO](#bed-mesh-kamp-full-saved-or-auto)
8. [Probe speed](#probe-speed)
9. [Bed heat soak](#bed-heat-soak)
10. [Nozzle cleaning and wipes](#nozzle-cleaning-and-wipes)
11. [Purge line](#purge-line)
12. [Safety stops and messages](#safety-stops-and-messages)
13. [Build plate](#build-plate)
14. [Commands](#commands)
15. [Start options](#start-options)
16. [Advanced settings](#advanced-settings)
17. [zMod 1.7.5](#zmod-175)
18. [Reporting problems](#reporting-problems)

## What Auto Trim does

Before a print, the printer touches the bed with the nozzle at a grid of points. That grid, the bed mesh, describes the shape of the bed, so the printer can follow its dips and rises while it prints. The mesh does not decide how far the nozzle sits above the bed on the first layer. That is the Z offset:

- **Too high:** the first layer comes out as round lines with gaps between them, and does not stick.
- **Too low:** the lines are squashed thin, the nozzle scrapes the bed, and the extruder can click or clog.
- **Right:** flat lines that just touch each other, with a smooth surface.

The right offset is not fixed. It differs between filaments (PETG usually wants a little more room than PLA), and it changes when you swap a nozzle or a build plate. Auto Trim takes care of it in four ways:

1. **It keeps a base offset for your printer**, the calibration, and a small adjustment for each filament, the trim. Every print starts at calibration + trim for the filament set in the slicer.
2. **It prepares the bed and nozzle before measuring:** it cleans the nozzle and lets it cool, so nothing oozing touches the bed, waits for the bed to settle if you want it to, and probes at a slow, precise speed.
3. **It checks the measurement:** a mesh that varies too much (a lifted plate, something under it) stops the print before anything is printed.
4. **It learns from you:** when you babystep during the first layer, Auto Trim saves that correction, so the next print with that filament starts where you left off.

Example: a PLA first layer looks slightly high, and you lower the nozzle by 0.02 mm while it prints. Auto Trim saves the correction, and the next PLA print starts 0.02 mm lower. After a few prints you rarely need to touch it.

## Requirements

| | |
|---|---|
| Printer | Flashforge AD5X, AD5M or AD5M Pro |
| Firmware | [zMod](https://github.com/ghzserg/zmod) 1.7.1 or newer. Works with zMod 1.7.5 (see [zMod 1.7.5](#zmod-175)) |
| Tested on | AD5X with Flashforge firmware 3.1.0 and zMod 1.7.5 |
| Screen | GuppyScreen or HelixScreen. With the native Flashforge screen, zMod hands prints to the Flashforge firmware, which Auto Trim does not support |
| Slicer | OrcaSlicer. Any slicer works if it can fill in the same values; the G-code below uses OrcaSlicer placeholders |
| Slicer setting | Label objects turned on (recommended), so the mesh and the purge line can be placed around your parts |

Not for Forge-X: use Auto Trim for Forge-X instead.

**Status:** tested extensively in a Klipper simulation of the print start (fresh installs, restarts, every safety stop, every mesh mode, different temperatures and filaments) and in use on AD5X printers. Watch the console on your first few prints, and please report anything unexpected (see [Reporting problems](#reporting-problems)).

## Installation

### 1. Upload the file

In Fluidd or Mainsail, open Configuration > `mod_data` and upload `auto_trim.cfg`.

### 2. Include it

Open `user.cfg` in the same folder and add this as the very first line, then save:
```
[include auto_trim.cfg]
```

### 3. Set three zMod settings

Run this once in the console:
```
SAVE_ZMOD_DATA DISABLE_PRIMING=1 MESH_TEST=0 PRINT_LEVELING=0
```

| Setting | Set to | Why |
|---|---|---|
| `DISABLE_PRIMING` | 1 | zMod would otherwise draw its own purge line inside `START_PRINT`, before Auto Trim has set the height. Auto Trim draws its own line after |
| `MESH_TEST` | 0 | Auto Trim checks the mesh itself. The zMod test would add another heat-and-cool cycle |
| `PRINT_LEVELING` | 0 | zMod would otherwise make its own mesh, with a hot nozzle and too early. Auto Trim makes the mesh at the right moment |

If one of these is wrong, Auto Trim stops the print before heating and tells you which one to fix.

### 4. Restart and check

Type `RESTART` in the console. Then type `AUTO_TRIM_STATUS`: you should see a line starting `AUTO TRIM v` with the version number.

### 5. Set up OrcaSlicer

**Machine start G-code** (Printer settings > Machine G-code > Machine start G-code). Replace everything with:
```
START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer] BED_TEMP=[bed_temperature_initial_layer_single] SKIP_LEVELING=True
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]}
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
```

| Line | What it does |
|---|---|
| `START_PRINT ... SKIP_LEVELING=True` | zMod's own start: homes the printer and heats the bed and nozzle. `SKIP_LEVELING=True` stops zMod from meshing here, because Auto Trim meshes later, after the nozzle has been cleaned and cooled |
| `AUTO_TRIM_PREPARE MATERIAL=...` | Auto Trim's preparation: nozzle clean, optional bed soak, mesh, checks, offset and purge line. `MATERIAL` tells it which filament adjustment to use. Options go at the end of this line (see [Start options](#start-options)) |
| `SET_PRINT_STATS_INFO TOTAL_LAYER=...` | Tells the printer how many layers the print has |

**Layer change G-code** (same page). Add:
```
SET_PRINT_STATS_INFO CURRENT_LAYER={layer_num + 1}
```
This tells Auto Trim exactly when the first layers are finished, which is when it saves your corrections. Without it, Auto Trim judges by nozzle height instead, which a colour change or a long lift on the first layer can confuse (see [When the first layers count as done](#when-the-first-layers-count-as-done)).

**Machine end G-code.** Replace everything with:
```
AUTO_TRIM_LEARN
END_PRINT
```
`AUTO_TRIM_LEARN` saves the corrections of prints too short to reach layer 3, and sets the offset back to 0.

Keep the `START_PRINT` and `END_PRINT` lines exactly as they are: zMod checks every print file for them. The same lines work on the AD5X, AD5M and AD5M Pro.

**Other OrcaSlicer settings:**
- **Label objects:** turn it on (Process > Others > Label objects). It tells the printer where your parts are, for the mesh and the purge line.
- **Filament type:** check that every filament profile has the right type (PLA, PETG, TPU...). That is how Auto Trim picks the adjustment.
- **Old offset lines:** if the Filament start G-code of any filament profile contains `SET_GCODE_OFFSET`, delete those lines. They would override Auto Trim.

### 6. Re-slice

Files sliced before the change contain the old start code. Slice them again.

## Your first print

The first print sets the base offset of your printer. Use PLA and something with a large flat first layer, for example a 100 x 100 mm square one layer thick.

**1. Start the print.** After the mesh, the console shows the offset it starts with:
```
AUTO TRIM: PLA offset = calibration 0.25 (default) + trim 0.0 + drift 0.0 = 0.25
```
`0.25` is a starting value. If zMod already had an offset saved, Auto Trim starts from that instead and says `(from existing zMod offset)`.

**2. Watch the first layer** and adjust the nozzle height with babysteps of 0.01 to 0.02 mm (Fluidd, Mainsail or the screen) until it looks right. Hold each change for a few seconds of printing before judging it.

| What you see | It means | Do this |
|---|---|---|
| Round lines with gaps between them, lines not sticking | Too high | Babystep down (closer) |
| Thin, see-through lines, rough ridges, nozzle scraping, extruder clicking | Too low | Babystep up (away) |
| Flat lines that just touch each other, smooth surface | Right | Leave it |

**3. Keep printing.** When layer 3 starts, the correction is saved:
```
AUTO TRIM: first 2 layers printed (now on layer 3), learning the first-layer offset
AUTO TRIM: calibration 0.25 -> 0.23 (babysteps -0.02)
```
At the end of the print the offset is set back to 0. Your next print starts at `0.23`.

If you already know the right offset, you can set it before the first print:
```
AUTO_TRIM_SET CALIBRATION=0.23
```

**Cancelled prints:** a print cancelled during the first two layers teaches nothing, so a failed first layer cannot store a bad value. A print cancelled later keeps its first-layer correction, because it was already saved. If you found the right height on the first layer and then cancelled, read the current offset in Fluidd and save it with `AUTO_TRIM_SET CALIBRATION=<value>`.

## What happens when a print starts

Nothing needs to be done during these steps. They take a few minutes, longer with the bed soak on.

On the AD5X, the nozzle is cleaned at the trash chute, so nothing hot or oozing is ever held over the bed:

| Step | What the printer does | Why |
|---|---|---|
| 1 | Homes, heats the bed and nozzle | zMod's `START_PRINT`. zMod's own nozzle pre-clean is skipped, because Auto Trim cleans the nozzle in steps 2 to 4 |
| 2 | Rises to Z 20, moves to the trash chute, purges 10 mm and wipes the nozzle on the rubber pad while it is hot | Clears old filament, and removes the purged strand before it can cool and fall onto the bed |
| 3 | Waits at the chute while the nozzle cools to 121 C, wiping it every 70 C on the way | Ooze is removed in stages as it forms, instead of building into one long string |
| 4 | Wipes the cooled nozzle a final time | The nozzle is clean and no longer oozing when probing starts |
| 5 | Optional: waits for the bed to settle (bed heat soak, off by default) | A freshly heated plate keeps moving for minutes. See [Bed heat soak](#bed-heat-soak) |
| 6 | Measures the bed: a KAMP mesh of your print area, by default | See [Bed mesh](#bed-mesh-kamp-full-saved-or-auto) |
| 7 | Checks the mesh | It must cover the print and stay within a normal range |
| 8 | Sets the Z offset | Calibration + filament trim |
| 9 | Rises to Z 20, returns to the chute, reheats, pushes the filament back to the tip, wipes, and re-zeroes the load cell | The nozzle reaches the print ready to extrude and clean, and zMod's collision protection starts from a fresh zero |
| 10 | Draws a purge line outside the print area | Primes the nozzle where it cannot touch your parts, supports, brims or skirts |
| 11 | Prints | You can babystep during the first layer |
| 12 | Saves the first-layer corrections when layer 3 starts, and sets the offset back to 0 at the end | Improves the start of the next print |

On the AD5M and AD5M Pro, which have no trash chute, steps 2 to 4 use zMod's standard nozzle clean (wipe hot, then cool), and in step 9 the nozzle reheats above the start of the purge line, outside the print area.

The nozzle is heated, cooled and reheated once each. That is the minimum: purging needs a hot nozzle, probing needs a cool one, and printing needs a hot one. For filaments printed above 230 C, the nozzle cools to 151 C instead of 121 C.

## How the offset is built and learned

### The calibration and the trims

The offset of every print is:

**offset = calibration + trim of the filament** (+ drift, only with the optional bed check)

| Word | Meaning | Example |
|---|---|---|
| Calibration | The base offset of your printer, learned from PLA prints | `0.23` |
| Trim | How much a filament differs from PLA | PETG `+0.025` |
| Drift | How much the bed moved between the mesh and an optional re-check (`CHECK=AREA`). 0 when the check is off, which is the default | `0.004` |
| Babystep | A small change of the nozzle height while printing, from Fluidd, Mainsail or the screen | "lower by 0.01" |

Example: calibration `0.23` + PETG trim `0.025` = `0.255`.

### Where a correction goes

| You babystep while printing... | It changes... | Effect |
|---|---|---|
| PLA | the calibration | Every filament moves with it |
| Any other filament | only the trim of that filament | Only that filament changes |
| The first print after installation (any filament) | the calibration | The starting value was only an estimate |

Example:
- Your calibration is `0.23`, and PETG starts at its default trim of `+0.025`, so PETG prints at `0.255`.
- PETG looks a little low, so you babystep up `+0.01`. Its trim becomes `+0.035`.
- Next PETG print: `0.23 + 0.035 = 0.265`. Your PLA is unaffected.
- Later you fit a new nozzle, and a PLA print needs `-0.02`. The calibration becomes `0.21`. Now PLA prints at `0.21` and PETG at `0.21 + 0.035 = 0.245`: both moved together.

Corrections can be any size, up or down. Negative values are fine (for example a calibration of `-0.05`).

### Starting adjustments per filament

Until a filament has been printed and corrected, it starts with a typical adjustment relative to PLA (positive values raise the nozzle):

| Filament | Starts at |
|---|---|
| PLA | 0 (the base) |
| PLA-CF | -0.01 |
| PETG | +0.025 |
| PETG-CF | +0.04 |
| ABS | 0 |
| ASA | +0.01 |
| TPU | +0.025 |
| PA, PA-CF, PA6-CF, PA12-CF, PC | 0 |
| Anything else | 0 |

These are approximate community values. Your babystep corrections replace them.

### When the first layers count as done

Only corrections made during the first layers are learned. A change made later (for example to fix a later layer) applies to the rest of that print, but is not learned, and the console says so at the end:
```
AUTO TRIM: offset changed by 0.05 after the first layers, not learned (first-layer offset 0.0711 was learned)
```

How Auto Trim knows the first layers are done:
- **With the Layer change G-code** (recommended): when layer 3 starts.
- **Without it:** when the nozzle stays above Z 1.0 mm (about layer 5 at 0.2 mm layers) for two checks in a row, after it has been on the first layer, while printing. A short Z-hop or a pause does not count, but a colour change or a long lift on the first layer can still end the first layers early. The console says when layer numbers are missing.
- **Prints too short to get there:** learned at the end, by `AUTO_TRIM_LEARN`.

## Bed mesh: KAMP, FULL, SAVED or AUTO

The `MESH=` option on the `AUTO_TRIM_PREPARE` line decides how the bed is measured for each print. Auto Trim does not make the mesh itself: it runs zMod's KAMP or a full-bed mesh at the right moment (after the nozzle clean and the bed soak, at probing temperature and at the `probe_speed`), and then checks the result.

| Option | What happens |
|---|---|
| none, or `MESH=KAMP` (default) | A fresh adaptive mesh of your print area, for every print (zMod KAMP) |
| `MESH=FULL` | A fresh full-bed mesh, for every print |
| `MESH=SAVED` | A saved full-bed mesh, checked at 5 points instead of probed |
| `MESH=AUTO` | KAMP for small prints, the saved mesh for large ones |

### KAMP

KAMP (adaptive meshing) measures only the part of the bed you are printing on, plus a few millimetres. A small part gets a small mesh with few points; a large part gets more. The mesh is always fresh, so it shows the bed exactly as it is for this print. KAMP comes with zMod; since zMod 1.7.5 it sizes the mesh from the print file itself.

### SAVED

Probing a fresh mesh takes time: about 6.6 seconds per point on an AD5X at the stock probe speed (about 5.5 minutes for a full 7 x 7 mesh), and longer at the 1 mm/s `probe_speed`. `MESH=SAVED` skips it. Auto Trim loads a saved full-bed mesh and probes only 5 points, at the corners and centre of your print area, to measure how far the whole bed has moved since the mesh was saved. That shift is added to the offset.
```
AUTO TRIM: loaded saved mesh 'auto' instead of probing
AUTO TRIM: checking 5 points at the print area corners and centre (7x7 mesh)
AUTO TRIM: KAMP-area check: 5 points, drift (average) 0.03, spread 0.02
AUTO TRIM: saved mesh matches the bed under this print (spread 0.02 mm), offset corrected by 0.03 mm
```

The saved mesh is never used blindly. A fresh KAMP mesh is probed instead, still before reheating, when:
- the 5 points disagree with each other by more than `saved_max_spread` (0.15 mm): the bed has changed shape since the mesh was saved, or
- the whole bed has moved by more than `max_drift` (0.3 mm): usually a different plate.

**Saving a mesh.** The easiest way, from a cold bed:
```
AUTO_TRIM_MESH_CALIBRATE BED=60
```
Use the bed temperature you print at. This measures how long your bed takes to settle (see [Bed heat soak](#bed-heat-soak)), then probes a full mesh once it has settled, saves it as `auto` and keeps it with `SAVE_CONFIG` (Klipper restarts). Or by hand: heat the bed to your printing temperature and let it settle for several minutes, run a full bed leveling from the zMod menu or `AUTO_FULL_BED_LEVEL` (saved as `auto`), then `SAVE_CONFIG`.

Save a new mesh after changing plates or re-levelling the bed screws. `saved_profile` selects a different profile name.

### AUTO

`MESH=AUTO` decides for each print:
1. It works out how many points a KAMP mesh would probe: your print area, at the point spacing of the `probe_count` in your printer config.
2. More than 16 points (`auto_kamp_points`) and a saved mesh exists: the saved mesh, with its 5-point check. Without a saved mesh: KAMP.
3. 16 points or fewer: KAMP.

For example, with a 7 x 7 `probe_count` (points about 36 mm apart on an AD5X):

| Print | A KAMP mesh would need | `MESH=AUTO` uses |
|---|---|---|
| a 60 x 40 mm part | 3 x 3 = 9 points | KAMP |
| a 150 x 150 mm part | 6 x 6 = 36 points | the saved mesh (5-point check) |

The console shows the choice:
```
AUTO TRIM: preparing (SAVED mesh (AUTO: KAMP would need 36 points), TRASH clean, print 220/60 C)
```

### Which to choose

- **`KAMP`** is the most accurate for each print, because the mesh is always fresh. Large prints take longer to probe, especially at 1 mm/s.
- **`AUTO`** is about as accurate for small prints and much faster for large ones, as long as the saved mesh was made in the same conditions: the same bed temperature, on a settled bed (`AUTO_TRIM_MESH_CALIBRATE` does both). If the bed has changed, the 5-point check notices and a fresh KAMP mesh is probed anyway.
- **`SAVED`** always uses the saved mesh, whatever the print size.
- **`FULL`** measures the whole bed every print. Slower than KAMP and rarely needed: the first layer only touches the area KAMP measures.

Running a full mesh and KAMP together does not help: KAMP does not refine a full mesh, it builds its own, so the same area would be probed twice and only the KAMP mesh used. Choose one with `MESH=`.

### Mesh checks

Right after the mesh, Auto Trim checks it before setting the offset:
```
AUTO TRIM: KAMP area X77.0-143.0 Y87.0-133.0 (print X80-140 Y90-130)
AUTO TRIM: mesh range 0.087 mm over 9 points
AUTO TRIM: bed check off, using the KAMP mesh only (drift 0)
AUTO TRIM: PLA offset = calibration 0.23 (saved) + trim 0.0 + drift 0.0 = 0.23
```

- **KAMP area:** the region that was measured, your parts plus a few millimetres.
- **Mesh range:** the difference between the highest and lowest point. Under a single print area it is usually well under 0.3 mm. Above `max_mesh_range` (0.6 mm) the print stops, because that usually means a lifted plate or something under it.
- **Coverage:** the mesh must reach under your parts. A part that is wider higher up than on its first layer (a flared base, a bowl, an overhang) gives an information line and the print continues, because KAMP measures the first layer and only the first layer needs the mesh. A saved mesh that does not cover the print stops it. `mesh_coverage: STOP` makes every mesh strict.

### Optional bed check

`CHECK=AREA` on the `AUTO_TRIM_PREPARE` line re-probes 5 points of the measured area (the four corners and the middle) after the mesh, and adds the average difference to the offset as drift. `CHECK=ALL` re-probes every mesh point. This adds about 35 to 40 seconds per print.

It is off by default for a reason: the check runs seconds after the mesh, at the same temperature, so what it measures is mostly how repeatable the probe is, not movement of the plate. On an AD5X the difference is usually a steady few hundredths of a millimetre, which the calibration absorbs anyway.
```
AUTO TRIM:   X77.0 Y87.0: probe -1.4342 mesh -1.4382 difference 0.004
...
AUTO TRIM: KAMP-area check: 5 points, drift (average) 0.004, spread 0.0
AUTO TRIM: PLA drift this print 0.004 (5 points, spread 0.0), learned 0.002, difference 0.002
```

With the check on, each filament keeps a learned drift, used for comparison only. If you switch the check off after using it, the first print may start a few hundredths of a millimetre higher than before; one babystep corrects it.

### Denser mesh

The printer measures at most 5 x 5 = 25 points by default. For a denser mesh, add `probe_count` to the `[bed_mesh]` section of `user.cfg` (add the section if it is not there), then `RESTART`:
```
[bed_mesh]
probe_count: 7, 7
```

| `probe_count` | Full-bed points | Points at most this far apart |
|---|---|---|
| 5, 5 (default) | 25 | 54 mm |
| 7, 7 | 49 | 36 mm |

More points take longer: 49 points take about twice as long as 25. KAMP uses the closer spacing too, so large parts get more points while small parts still need only a few.

7 x 7 is the recommended maximum on the AD5X. After probing, Klipper interpolates the mesh into a much finer one (`mesh_pps: 5, 5` turns 9 x 9 into 41 x 41 points), and that work has been seen to stop the printer with `MCU 'mcu' shutdown: Timer too close`. It happens again whenever a saved mesh is loaded (`MESH=SAVED`, or `MESH=AUTO` choosing it), and the pause after the mesh (`settle_ms`) does not prevent it, because the work happens inside the mesh command. A smaller `move_check_distance` adds to the load, so keep the stock value. If you want 9 x 9 anyway, reduce the interpolation:
```
[bed_mesh]
probe_count: 9, 9
mesh_pps: 2, 2
```

## Probe speed

Every bed mesh is probed at 1 mm/s (`probe_speed`): KAMP and full meshes from Auto Trim, meshes zMod starts itself, and the saved-mesh and bed checks. On a load cell probe, a slower touch gives a more repeatable measurement than the stock 5 mm/s.

Only the probing move down is slower. Travel over the bed, lifts, homing and zMod's other probing keep their normal speeds.

How it works: every zMod mesh goes through one command, `_BED_MESH_CALIBRATE` (zMod's KAMP included, which passes no speed of its own). Auto Trim adds its probe speed to that command whenever no speed is given; a `PROBE_SPEED=` written on a mesh command is kept. This needs Auto Trim to be included after zMod's own configuration, which the first line of `user.cfg` is. If it were not, Klipper would report at start that `_BED_MESH_CALIBRATE` was not found.

**After changing the probe speed** (including the first print after updating from a version before 3.9.7): a load cell probe triggers at a slightly different height at another speed. Check the first layer of the next print and babystep if needed; Auto Trim learns it.

`probe_speed: 0` uses Klipper's own probe speed again.

## Bed heat soak

When the bed heater reaches its target, the plate is not done moving. It keeps warming through and changes shape for several more minutes, often by a few hundredths of a millimetre, sometimes more at the corners. A mesh taken during that time measures a bed that is still moving. The soak waits for it to settle before the mesh is probed.

The soak is off by default (`soak: OFF`). Turn it on for one print with `SOAK=` on the `AUTO_TRIM_PREPARE` line, or for every print by changing `soak`:

| Setting | What happens |
|---|---|
| `SOAK=OFF` (default) | No soak |
| `SOAK=AUTO` | Waits as long as your bed needs: the measured time if you calibrated it, otherwise an estimate from how far the bed rose |
| `SOAK=300` | Waits that many seconds |

### How SOAK=AUTO decides

1. **The bed was already hot** (it started within 5 C of its target, for example back-to-back prints): no soak.
2. **A calibration exists** (from `AUTO_TRIM_SOAK_CALIBRATE` or `AUTO_TRIM_MESH_CALIBRATE`): it uses the calibration at the nearest bed temperature, and the slowest of the measured points, centre or corners. It is scaled by how far the bed rose this time compared with during the calibration: a bed that rose half as far soaks half as long. Measured soaks are limited to 2700 s (`soak_cal_max`).
3. **No calibration:** 3 s per degree the bed rose (`soak_per_degree`), at most 600 s (`soak_max`).

Time the bed already spent hot during the nozzle clean counts, so the printer only waits for what is left.

Example, with a calibration at 60 C from a 20 C bed that settled after 900 s at its slowest corner:

| This print | Bed rose | Soak |
|---|---|---|
| 60 C from a cold bed (20 C) | 40 C, as much as the calibration | 900 s |
| 60 C from a warm bed (40 C) | 20 C, half as much | 450 s |
| 60 C, straight after another print (58 C) | under 5 C | none |
| 60 C without any calibration, from 20 C | 40 C x 3 s | 120 s |

The console shows the decision and counts down:
```
AUTO TRIM: bed heat soak 900 s (calibrated at 60 C, slowest point, bed started at 20 C), 180 s covered by the nozzle clean, waiting 720 s
```

If Klipper was restarted just before the print, the starting bed temperature is unknown and `AUTO` skips the soak for that print. A bed preheated from the screen just before printing also counts as already hot, although the plate has not settled: start from a cold bed, or wait a few minutes after preheating.

### Measuring your bed

From a cold bed (below 40 C):
```
AUTO_TRIM_SOAK_CALIBRATE BED=60
```
Use the bed temperature you print at. The nozzle is held at probing temperature for 5 minutes, then the bed is heated, and the centre and four points near the corners are probed every minute until all of them stay within 0.02 mm for 4 minutes (at most 25 minutes). The settling time is saved for that bed temperature, and the heaters are switched off. `AUTO_TRIM_SOAK_ABORT` stops it.

`AUTO_TRIM_MESH_CALIBRATE BED=60` does the same and then saves a full mesh for `MESH=SAVED` and `MESH=AUTO` (see [SAVED](#saved)). If the bed never settles, no mesh is saved and your existing one is kept.

Calibrate each bed temperature you use often (for example 60 C for PLA and 80 C for PETG). A print at another temperature uses the nearest calibration.

All soak probes use the `probe_speed` (1 mm/s), and a print cannot start while a soak calibration is running.

## Nozzle cleaning and wipes

### On the AD5X: the trash chute

The nozzle is purged and cleaned at the trash chute, then cooled there before probing, so nothing hot or oozing is held over the bed (steps 2 to 4 of the print start). While it cools, it is wiped on the rubber pad in stages.

**How often it is wiped** (`cool_wipe_step`, 70 C): after the purge, every 70 C on the way down, and once more at probing temperature. For PLA at 220 C that means wipes at 220, 150 and 121 C.

| Setting | Wipes while cooling from 220 C | When to use |
|---|---|---|
| `COOL_WIPE_STEP=70` (default) | 220, 150, 121 C | Most filaments |
| `COOL_WIPE_STEP=25` | 220, 195, 170, 145, 121 C | Stringy filaments that ooze a lot while cooling |
| `COOL_WIPE_STEP=0` | 220, 121 C only | Filaments that barely ooze; the shortest start |

**How it wipes** (`rubber_wipe`):
- `SOFT` (default): zMod's own wipe, three knocks at the chute and its slow side-to-side pass over the rubber, without the fast shaking. Gentle on the nozzle and the pad.
- `STOCK`: zMod's full wipe, including the fast shaking. Stronger cleaning, more wear on the pad.

`COOL_WIPE_STEP=25 RUBBER_WIPE=STOCK` gives the wipes of Auto Trim 3.9.4 and earlier.

**Filament at the tip:** every wipe pulls the filament back 2 mm, so it cannot drip. When the nozzle is reheated before printing, Auto Trim pushes back all of it (the 3 mm retracted after the purge, plus 2 mm per wipe), so the purge line starts with filament at the tip. With the defaults that is 11 mm.

Before every move to the chute, the nozzle first rises to Z 20, as zMod does, so it never travels low over the bed.

**zMod's own pre-clean:** zMod normally cleans the nozzle inside `START_PRINT`. Auto Trim replaces that step (`zmod_preclean: SKIP`), because it cleans the nozzle itself later, after heating. `zmod_preclean: KEEP` runs zMod's pre-clean as well. Because the replacement applies to every print, prints sliced without `AUTO_TRIM_PREPARE` also skip zMod's pre-clean while it is set to `SKIP`.

### On the AD5M and AD5M Pro

There is no trash chute, so Auto Trim uses zMod's standard nozzle clean (wipe hot, then cool) before probing, and reheats the nozzle above the start of the purge line, outside the print area, so any ooze lands where the line begins. `CLEAN=ZMOD` selects this on the AD5X too.

## Purge line

Before printing, Auto Trim draws a purge line to prime the nozzle. It is placed outside your whole print area, so it cannot run into parts, supports, brims or skirts.

**Where it goes:**
1. The print area is every labelled part plus 10 mm of clearance (`purge_clearance`). The slicer's part outlines may not include supports, brims or skirts; the clearance covers them.
2. The line is drawn in the free strip between that area and the edge of the bed, halfway across the strip and centred on your parts.
3. The front is used when it has room. Otherwise the back, left or right side with the most room is used.

The console shows where it goes:
```
AUTO TRIM: purge line planned on the front side, outside the print area (parts X80 to 140 Y90 to 130 plus 10.0 mm clearance), from X95.0 Y40.0 to X125.0 Y40.0
```

**When there is no room** (your parts plus clearance fill the bed): on the AD5X, one of zMod's stock edge lines at the very edge of the bed is used instead. It tries your zMod `CLEAR=` choice first, then the rear line `_CLEAR1` (which loops back to catch strings), the right-side line `_CLEAR4` and the front lines, and uses the first that stays 3 mm clear of your parts (`edge_clearance`). If your parts reach every edge line, the purge is skipped with a notice and the print continues. On the AD5M there are no edge lines, so the purge is skipped with a notice. `purge_fallback: OFF` always skips instead of using an edge line.

**Without labelled objects:** with zMod 1.7.5, Auto Trim uses the first-layer area zMod finds in the print file and plans the line outside it, as with labels. With older zMod, or when zMod found no area, the print area is unknown, and a line across the bed could run under the print: a stock edge line is used instead on the AD5X, and the purge is skipped on the AD5M. Turning Label objects on gives the best placement.

**Your own purge macro:** `PURGE_MACRO=<macro>` on the `AUTO_TRIM_PREPARE` line runs your macro instead of the built-in line, for example one that loops back to catch the string PETG leaves:
```
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]} PURGE_MACRO=MY_PURGE
```
It runs at the same point as the built-in line: after the reheat, at print temperature, with the offset set. It receives the planned position outside the print area as `X0`, `Y0`, `X1` and `Y1`, which it can use or ignore. If the macro does not exist, the print stops before heating. zMod's stock edge lines (`_CLEAR1` to `_CLEAR4`) draw outside the bed, so with `PURGE_MACRO=_CLEAR1`, for example, nothing is planned inside the bed and the purge always runs.

**No purge:** `PURGE=0` skips the purge line.

## Safety stops and messages

Auto Trim stops the print before printing starts, so nothing is damaged, and the console says why.

| Message contains | What it means | What to do |
|---|---|---|
| `MESH_TEST must be 0`, `PRINT_LEVELING must be 0` or `DISABLE_PRIMING=1` | A zMod setting is wrong | Run the command from [Installation](#3-set-three-zmod-settings) step 3, then `RESTART` |
| `the mesh varies by` | The mesh range is above `max_mesh_range` (0.6 mm) | Check that the plate is seated flat with nothing under it, then print again |
| `outside safe range` | The final offset would be beyond -0.8 or +0.8 mm | Check your values with `AUTO_TRIM_STATUS` and fix them with `AUTO_TRIM_SET` |
| `does not cover this print` | A saved mesh, or any mesh with `mesh_coverage: STOP`, does not reach under the whole print | Make sure Label objects is on and re-slice, or save a new full-bed mesh |
| `differs from the fresh mesh by` (with `CHECK=AREA`) | One spot measured very differently seconds after the mesh | Clean the plate and check it is seated flat |
| `check points disagree by` (with `CHECK=AREA`) | The checked spots disagree by more than 0.4 mm | Look for something under the plate, or a bent or lifted plate |
| `no bed mesh` | The mesh failed | Look further up the console for a probing error |
| `a bed soak calibration is running` | A soak calibration is still measuring | Wait for it, or stop it with `AUTO_TRIM_SOAK_ABORT` |
| `not found. Is this zMod?` | A zMod command is missing | Update zMod, or check you are not on Forge-X |
| `this printer has no [save_variables]` | Auto Trim for zMod is installed on Forge-X | Install Auto Trim for Forge-X instead |

**Notices** (lines starting `!!`, which do not stop the print):
- `drift is 0.15 mm away from its learned value` (with `CHECK=AREA`): the bed check found a bigger change than usual for this filament. Expected after swapping or moving the plate; otherwise check that it is clean.
- `START_PRINT should have SKIP_LEVELING=True`: your start G-code is out of date. The print works but takes longer. Update it as in [Installation](#5-set-up-orcaslicer).
- `no labelled objects, so KAMP cannot size the mesh to the print`: Label objects is off and zMod found no print area, so the whole bed is measured. Turn Label objects on.
- `no room for a purge line outside the print area`: your parts fill the bed and reach every stock edge line, or `purge_fallback` is `OFF`. The purge is skipped and the print continues. Lower `purge_clearance` if your prints have no supports, brims or skirts.

**Information lines** worth knowing:
- `the mesh ... is smaller than the part outlines`: the part is wider higher up than on its first layer (see [Mesh checks](#mesh-checks)). The print continues.
- `the slicer does not report layer numbers`: add the Layer change G-code (see [Installation](#5-set-up-orcaslicer)).
- `no labelled objects: zMod sized the mesh from the first-layer area it found in the file`: zMod 1.7.5 handled the missing labels.

## Build plate

The measurements are only as good as the plate under the nozzle:

- **One plate, seated flat, with nothing under it:** no filament bits, dust or lifted corner. Anything under the plate is measured as if it were the bed.
- **A clean surface:** fingerprints, glue or blobs change where the nozzle "feels" the bed.
- **A firm, undamaged surface:** very soft coatings, gouges or peeled spots give uneven readings.
- **A reasonably level bed:** the mesh corrects tilt, but if one corner is several tenths of a millimetre off, level it first with zMod's `BED_LEVEL_SCREWS_TUNE`.

**Heat-sensitive plates** (PC, some G10 and coated plates) can get small marks from probing at 121 C. Lower the probing temperature:
```
SAVE_VARIABLE VARIABLE=temp_test_min VALUE=110
SAVE_VARIABLE VARIABLE=temp_test_max VALUE=140
```
`temp_test_max` is used for filaments printed above 230 C. On the AD5X these are used by Auto Trim's trash-chute clean on any zMod version. With zMod's standard clean (AD5M, AD5M Pro, or `CLEAN=ZMOD`) they need zMod 1.7.4 or newer; zMod 1.7.1 always cools to 121 C and 151 C.

**Swapping plates:** the mesh accounts for the thickness of a different plate automatically. A different surface may still want a different first-layer height (textured plates often print best slightly lower). A babystep correction on a PLA print with the new plate applies to every filament. If you alternate between plates, note the calibration for each and set it before printing, for example `AUTO_TRIM_SET CALIBRATION=0.21`.

## Commands

Run these in the Fluidd or Mainsail console.

| Command | What it does | Example |
|---|---|---|
| `AUTO_TRIM_STATUS` | Shows the version, your calibration, and the trim and learned drift of every filament | `AUTO_TRIM_STATUS` |
| `AUTO_TRIM_SET CALIBRATION=<value>` | Sets your base offset by hand | `AUTO_TRIM_SET CALIBRATION=0.23` |
| `AUTO_TRIM_SET MATERIAL=<type> TRIM=<value>` | Sets the adjustment of one filament by hand (not PLA: use `CALIBRATION=` for that) | `AUTO_TRIM_SET MATERIAL=PETG TRIM=0.03` |
| `AUTO_TRIM_SOAK_CALIBRATE BED=<C>` | Measures how long your bed takes to settle, from a cold bed | `AUTO_TRIM_SOAK_CALIBRATE BED=60` |
| `AUTO_TRIM_MESH_CALIBRATE BED=<C>` | From a cold bed: nozzle clean, soak calibration, then a full mesh saved for `MESH=SAVED` and `MESH=AUTO` | `AUTO_TRIM_MESH_CALIBRATE BED=60` |
| `AUTO_TRIM_SOAK_ABORT` | Stops a running soak calibration | `AUTO_TRIM_SOAK_ABORT` |

`AUTO_TRIM_PREPARE` and `AUTO_TRIM_LEARN` run from the start and end G-code; you do not type them.

## Start options

Add these at the end of the `AUTO_TRIM_PREPARE` line in the OrcaSlicer start G-code.

| Add | What it does |
|---|---|
| `MESH=KAMP` | A fresh adaptive mesh of the print area (the default) |
| `MESH=FULL` | A fresh full-bed mesh. Slower |
| `MESH=SAVED` | The saved mesh, checked at 5 points |
| `MESH=AUTO` | KAMP for small prints, the saved mesh for large ones |
| `SOAK=AUTO`, `SOAK=300`, `SOAK=OFF` | Bed heat soak: as long as the bed needs, a fixed time, or none |
| `CHECK=AREA` | Re-probes 5 points after the mesh and applies the drift. About 35 to 40 seconds longer |
| `CHECK=ALL` | Re-probes every mesh point. Slower |
| `COOL_WIPE_STEP=70` | AD5X: wipe every this many degrees while the nozzle cools; 0 = only after the purge and at probing temperature |
| `RUBBER_WIPE=SOFT` | AD5X: zMod's gentle wipe (default); `STOCK` for its full wipe |
| `CLEAN=ZMOD` | Use zMod's standard nozzle clean instead of the trash chute on the AD5X |
| `PURGE=0` | No purge line |
| `PURGE_MACRO=<macro>` | Your own purge macro instead of the built-in line |

Example: soak as long as the bed needs, then use the saved mesh for large prints:
```
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]} SOAK=AUTO MESH=AUTO
```

## Advanced settings

These rarely need changing. They are at the top of each macro in `auto_trim.cfg`.

In `AUTO_TRIM`:

| Setting | Default | What it does |
|---|---|---|
| `baseline` | `pla` | The filament whose corrections change the calibration |
| `default_calibration` | 0.25 | Starting offset for the first print, if nothing is saved |
| `min_offset` / `max_offset` | -0.8 / 0.8 | Safety limits for the final offset |
| `unset_below` | 0.01 | Saved zMod offsets closer to 0 than this are treated as "never set" |
| `seed_trims` | see [Starting adjustments](#starting-adjustments-per-filament) | Starting adjustment for each filament |
| `drift_learn_rate` | 0.5 | With the bed check: how far each print's drift moves the learned value (0.5 = halfway) |
| `drift_jump` | 0.1 | With the bed check: how far from normal the drift may be before a notice |

In `AUTO_TRIM_LEARN`:

| Setting | Default | What it does |
|---|---|---|
| `learn_after_layers` | 2 | Corrections are learned once this many layers are printed (with layer numbers) |
| `learn_above_z` | 1.0 mm | Without layer numbers: learned once the nozzle stays above this height |

In `AUTO_TRIM_PREPARE`:

| Setting | Default | What it does |
|---|---|---|
| `mesh` | `KAMP` | `KAMP`, `FULL`, `SAVED` or `AUTO` |
| `saved_profile` | `auto` | The saved mesh used by `SAVED` and `AUTO` |
| `saved_max_spread` | 0.15 mm | Saved mesh: probe a fresh KAMP mesh if the 5 points disagree by more than this |
| `auto_kamp_points` | 16 | `AUTO`: the largest KAMP mesh, in points, before the saved mesh is used |
| `check` | `OFF` | `OFF` (mesh only), `AREA` (re-probe 5 points) or `ALL` (every point) |
| `max_mesh_range` | 0.6 mm | Stop if the mesh varies by more than this |
| `mesh_coverage` | `WARN` | A mesh probed for this print that is smaller than the part outlines: `WARN` and print on, or `STOP` |
| `probe_speed` | 1 mm/s | Probe speed for every bed mesh and Auto Trim's probes. 0 = Klipper's own speed |
| `soak` | `OFF` | Bed heat soak: `OFF`, `AUTO` or a number of seconds |
| `soak_per_degree` / `soak_max` | 3 s / 600 s | `SOAK=AUTO` without a calibration: seconds per degree risen, and the most |
| `soak_cal_max` | 2700 s | `SOAK=AUTO` with a calibration: the longest soak taken from it |
| `clean` | `AUTO` | `AUTO` (trash chute on the AD5X, zMod's clean on the AD5M and AD5M Pro), `TRASH` or `ZMOD` |
| `cool_wipe_step` | 70 C | AD5X: wipe every this many degrees while the nozzle cools |
| `rubber_wipe` | `SOFT` | AD5X: `SOFT` (zMod's gentle wipe) or `STOCK` (its full wipe) |
| `zmod_preclean` | `SKIP` | AD5X: `SKIP` zMod's pre-clean inside `START_PRINT`, or `KEEP` it. `KEEP` runs a copy of zMod 1.7's sequence, so check it after a zMod update |
| `restore_tip` | automatic | Filament pushed back to the tip after the purge retraction, in mm: 3 on the AD5X, 0 on the AD5M. The wipes' retraction is added to it |
| `purge` | on | Draw the purge line |
| `purge_macro` | none | Your own purge macro |
| `purge_fallback` | `EDGE` | No room for the line: a stock edge line (`EDGE`) or no purge (`OFF`) |
| `purge_clearance` | 10 mm | Space kept clear around your parts, for supports, brims and skirts |
| `edge_clearance` | 3 mm | Space an edge line must keep from your parts. Small on purpose: edge lines are only used when the parts nearly fill the bed, so a brim wider than this near the edge can still meet one |
| `purge_length` | 30 mm | Length of the purge line |
| `purge_amount` | 30 mm | Filament extruded for it |
| `purge_height` | 0.8 mm | Nozzle height for it |
| `purge_flow` | 12 | Line speed in mm/s is this divided by 5 (about 6 mm3/s with the default line) |
| `max_drift` | 0.3 mm | Bed check and saved mesh: the largest shift accepted |
| `max_spread` | 0.4 mm | Bed check: stop if the checked spots disagree by more than this |
| `kamp_slack` | 10 mm | How much bigger than your parts a mesh may be before it counts as a full-bed mesh |
| `settle_ms` | 1000 | Pause in milliseconds after the mesh, before the bed check |

Notes:
- Values are stored in zMod's existing `[save_variables]` section. Do not add a second one.
- `LOAD_ZOFFSET` in zMod can be on or off. Auto Trim sets the offset itself on every print; zMod's saved offset only matters as a starting point for the very first print.
- On multi-colour AD5X prints, the adjustment follows the filament in the first slot used, since that one prints the first layer.
- Filament names come from the OrcaSlicer filament type, lowercased, with `-` turned into `_` (`PLA-CF` is stored as `pla_cf`).

## zMod 1.7.5

Auto Trim works with zMod 1.7.5. What changed there, and what it means:

- **The print dialog's leveling option** is saved as `PRINT_LEVELING`. Leave leveling unticked: Auto Trim makes its own mesh, and stops before printing (with a message) if `PRINT_LEVELING` is on.
- **Fast KAMP:** zMod now sizes the KAMP mesh from the print file. With labelled objects, the mesh covers your parts and their first layer. With a `.gcode.3mf` file it covers the first layer, so a part that is wider higher up gives the information line about part outlines, and the print continues.
- **Labelled objects** are no longer needed by zMod, and Auto Trim works without them too: the purge line is planned outside the first-layer area zMod found in the file. Labels are still better, because they include the whole part outline.
- **3MF files** (Orca sending `.gcode.3mf`) work: zMod unpacks the G-code and runs it, start G-code included.
- **Screen:** GuppyScreen or HelixScreen. With the native Flashforge screen, zMod hands the print to the Flashforge firmware, which Auto Trim does not support.

## Reporting problems

Please include:
- the output of `AUTO_TRIM_STATUS`,
- your zMod version,
- the console lines from the print start, from `START_PRINT` to `AUTO TRIM: ready to print` (all lines starting `AUTO TRIM` are the most useful),
- your OrcaSlicer start, layer change and end G-code.

## Files

- `auto_trim.cfg`: the Auto Trim macros
- `README.md`: this document
- `CHANGELOG.md`: release history

## Credits

- [zMod](https://github.com/ghzserg/zmod) by ghzserg: the firmware whose nozzle cleaning, KAMP integration and probing Auto Trim builds on.
- [KAMP (Klipper Adaptive Meshing & Purging)](https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging) by kyleisah: adaptive meshing.
- [Klipper](https://www.klipper3d.org/): the underlying firmware.
