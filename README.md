> **OrcaSlicer factor review:** the full 378-setting audit for OrcaSlicer 2.5.0-dev 606b50f1 is in [the factor review](reference/orca_606b50f1/ORCA_FACTOR_REVIEW.md). It documents additional inputs/segment gates needed; this documentation does not claim they are already captured by beta10.1.

# Deep Calibration

A first-layer research suite for the Flashforge AD5X running zMod: it records what the printer measures during the first layer, labels it with what you judged by eye, finds the first-layer offset automatically with the load cell, and measures how long the bed takes to settle.

Version 0.1.0-beta.10.1 (2026-11-14). **Current official development continuation of beta 9.** Used together with [Auto Trim for zMod](https://github.com/Parabel54/Auto-Trim-plugin-for-zmod) 3.9.12 or newer.

## Contents

1. [What Deep Calibration does](#what-deep-calibration-does)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Set up OrcaSlicer](#set-up-orcaslicer)
5. [Your first recording](#your-first-recording)
6. [What is recorded](#what-is-recorded)
7. [Labels](#labels)
8. [Knee search: finding the offset automatically](#knee-search-finding-the-offset-automatically)
9. [Guarded approach](#guarded-approach)
10. [Strict bed soak calibration](#strict-bed-soak-calibration)
11. [The 9 x 9 saved mesh macro](#the-9-x-9-saved-mesh-macro)
12. [Recording by hand](#recording-by-hand)
13. [Timing](#timing)
14. [Sensor problems during a recording](#sensor-problems-during-a-recording)
15. [Analysing recordings](#analysing-recordings)
16. [What the recordings have shown so far](#what-the-recordings-have-shown-so-far)
17. [Commands](#commands)
18. [Settings](#settings)
19. [Limits](#limits)
20. [Files](#files)

## What Deep Calibration does

Auto Trim sets the first-layer offset and learns from your babysteps. Deep Calibration looks underneath that: what the load cell, the accelerometer and the motion system actually measure while the first layer is printed, and how that relates to what a good first layer looks like.

It does four things:

1. **Records the first layer.** The load cell under the bed, the accelerometer on the toolhead, the temperatures, and the exact nozzle position and offset, continuously from the first move of layer 1 until layer 2 starts.
2. **Labels it.** Every babystep you make tells it something: lowering the nozzle means the offset before was too high, raising it means it was too close, and the offset you keep until layer 2 is labelled good. No typing during the print.
3. **Finds the offset by itself (knee search).** It lowers the nozzle in small steps during the first layer until the load cell shows the nozzle starting to press the line, then backs off by a small margin. Auto Trim learns the result.
4. **Measures the bed soak strictly.** How long your bed keeps moving after it is heated, with repeated probing until it is still within 0.01 mm for 10 minutes. Auto Trim's `SOAK=AUTO` uses the result.

Everything except the knee search is passive: recording and labelling never change the print. The knee search is the one command that moves the nozzle, and only when you ask for it.

## Requirements

| | |
|---|---|
| Printer | Flashforge AD5X with the stock load cell and accelerometer |
| Firmware | [zMod](https://github.com/ghzserg/zmod) 1.7.5 (Klipper 13) |
| Auto Trim | Auto Trim for zMod 3.9.12 or newer, installed separately |
| Screen | GuppyScreen or HelixScreen; babysteps from the screen, Fluidd or Mainsail are all recognised |
| Slicer | OrcaSlicer, with the Layer change G-code below |
| Storage | Room on the printer for recordings: about 125 MB for a 25-minute first layer (about 55 MB of `.jsonl`, 70 MB of acceleration data), so about 300 MB per hour of first layer |
| Tested on | AD5X with Flashforge firmware 3.1.0 and zMod 1.7.5 |

**Status:** development beta, used on one AD5X. It hooks into Klipper's probe code (see [Guarded approach](#guarded-approach)) and is tested against a simulation of that code, but zMod updates can change it.

## Installation

### 1. Install Auto Trim

Install Auto Trim for zMod 3.9.12 or newer as its README says: `auto_trim.cfg` in `mod_data`, included from `user.cfg`.

### 2. Upload the folder

Download the [beta branch ZIP](https://github.com/Parabel54/Auto-Trim-plugin-for-zmod/archive/refs/heads/beta.zip), unzip it, and rename the extracted repository folder to `deep_calibration_development_beta`. Copy that whole folder into `mod_data` (Fluidd or Mainsail: Configuration > `mod_data`). When updating, replace the whole folder. Your recordings (`deep_calibration_data`) and saved soak calibrations are separate and are kept.

### 3. Include it

In `mod_data/user.cfg`, include both, Auto Trim first:
```ini
[include auto_trim.cfg]
[include deep_calibration_development_beta/deep_calibration.cfg]
```

### 4. Run the installer

Over SSH:
```sh
sh /usr/data/config/mod_data/deep_calibration_development_beta/install_deep_calibration.sh
```
It links the four Python modules (`deep_calibration.py`, `deep_calibration_sensors.py`, `deep_calibration_mesh.py`, `deep_calibration_approach.py`) into Klipper's extras folder. It never writes `user.cfg` or zMod's files, and refuses to overwrite a file of the same name that is not its own link. Run it again after every update.

### 5. zMod settings and restart

If not already set for Auto Trim:
```gcode
SAVE_ZMOD_DATA PRINT_LEVELING=0 MESH_TEST=0 DISABLE_PRIMING=1
```
Then `RESTART` while idle.

### 6. Check

| Command | Should show |
|---|---|
| `DEEP_CALIBRATION_STATUS` | version 0.1.0-beta.7 |
| `DC_APPROACH_STATUS` | installed, contact 1.0 mm/s |
| `AUTO_TRIM_STATUS` | Auto Trim 3.9.12 or newer |

If Klipper does not start and names `deep_calibration_approach`, see [Guarded approach](#guarded-approach).

## Set up OrcaSlicer

**Machine start G-code:**
```gcode
START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer] BED_TEMP=[bed_temperature_initial_layer_single] SKIP_LEVELING=True
AUTO_TRIM_PREPARE MATERIAL={filament_type[initial_extruder]} SOAK=AUTO
DEEP_CALIBRATION_ARM MATERIAL={filament_type[initial_extruder]} HEIGHT=[initial_layer_print_height] WIDTH=[initial_layer_line_width] SPEED=[initial_layer_speed] FILAMENT=[filament_diameter]
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
```

| Line | What it does |
|---|---|
| `START_PRINT ... SKIP_LEVELING=True` | zMod's start: homing and heating, without zMod's own mesh |
| `AUTO_TRIM_PREPARE ...` | Auto Trim's preparation: nozzle clean, bed soak, mesh, offset, purge line |
| `DEEP_CALIBRATION_ARM ...` | Tells Deep Calibration to record this print's first layer, with the slicer's first-layer settings (material, height, line width, speed, filament diameter) as the recipe |
| `SET_PRINT_STATS_INFO TOTAL_LAYER=...` | The number of layers |

For a knee search on this print, add after the `DEEP_CALIBRATION_ARM` line:
```gcode
DEEP_CALIBRATION_KNEE ARM=1
```

**Layer change G-code:**
```gcode
SET_PRINT_STATS_INFO CURRENT_LAYER={layer_num + 1}
```
Deep Calibration and Auto Trim both use it to know exactly when layer 1 starts and ends. Without it, Deep Calibration judges by nozzle height, which is less precise.

**Machine end G-code:**
```gcode
AUTO_TRIM_LEARN
END_PRINT
```

**A good test print:** a large flat square, one or two layers, Monotonic or Spiral Inset first layer. A long first layer gives more data and room for a knee search; a 0.2 mm first layer is easier to judge by eye than a thin one.

## Your first recording

Start the print and watch the console. Nothing needs to be typed.

1. Auto Trim prepares the print. When it is done:
```
DEEP CALIBRATION: armed for this print (PLA, first layer 0.2 mm): recording starts with the first layer, babysteps label the offsets, and it stops when layer 2 starts
```
2. Recording starts as the first layer begins:
```
DEEP CALIBRATION: live recording started: /usr/data/config/mod_data/deep_calibration_data/20261111T095854Z_PLA_firstlayer_079f897a.jsonl.
```
3. Watch the first layer and babystep as you normally would. Each change is labelled at once:
```
DEEP CALIBRATION: Z 0.250 was too high (TOO_HIGH, from your babystep); new offset Z 0.150 being recorded
```
4. When layer 2 starts, the offset you kept is labelled GOOD and the recording stops by itself.

The files are in `mod_data/deep_calibration_data`: one `.jsonl` file per recording, plus one or more `.dca` files with the acceleration data. Download them with Fluidd or Mainsail (right-click > Download; dragging them out of the browser can create link shortcuts instead of files).

## What is recorded

| Data | How often | From |
|---|---|---|
| Load cell (raw counts, and the board's gram reading) | About 3 times a second | The load cell under the bed |
| Acceleration X, Y, Z | About 1600 times a second | The toolhead accelerometer (LIS2DW) |
| Temperatures | Several times a second | Toolhead, filament, cutter, bed, extruder |
| Position, speed, extrusion, Z offset, fan, layer | 10 times a second | Klipper |
| Labels and events | When they happen | Your babysteps, `MARK`, the knee search, start and stop |
| Session details | Once | Recipe, bed mesh, probe settings, versions |

Each reading carries the motion at that moment, so a load cell reading can be matched with what the nozzle was doing: printing at speed, travelling, or turning.

Storage limits: the `.jsonl` file stops at 256 MB (`max_file_mb`); acceleration files rotate every 32 MB (`accel_rotate_mb`) up to 512 MB per recording (`accel_max_mb`); and recording stops before the printer's storage drops below 64 MB free (`storage_reserve_mb`).

## Labels

A label says what the first layer looked like at a given offset. They come from three places.

**From your babysteps (automatic):**

| You... | The offset before the change is labelled |
|---|---|
| Lower the nozzle (closer) | `TOO_HIGH` |
| Raise the nozzle (away) | `TOO_LOW` (too close) |
| Keep an offset until layer 2 starts | `GOOD` |

Only relative babysteps count (`SET_GCODE_OFFSET Z_ADJUST=`, which is what the screen, Fluidd and Mainsail send). Absolute offset changes (`Z=`) are ignored, because start-up and clean-up routines use them. Babysteps count from the moment Auto Trim is ready until layer 2 starts. Automatic labels are marked as inferred in the data.

**By hand:** `DEEP_CALIBRATION_MARK LABEL=<label> NOTE="..."` during a recording. Labels: `GOOD`, `TOO_HIGH`, `TOO_LOW`, `TRAVEL`, `TRANSITION` and `UNLABELLED`. `DC_MARK_GOOD` is a shortcut for `GOOD`, handy as a screen button. A label you set by hand after the last babystep is kept: the automatic `GOOD` at layer 2 does not replace it.

**What `GOOD` means:** the automatic `GOOD` means "kept until layer 2", not "checked and confirmed". If you did not look at the first layer, it is just the last offset. For analysis, note how the first layer actually came out, and whether layer 2 scraped.

## Beta 10.1: flow-aware knee search and temporary fast polling

Beta 10.1 is the official continuation of the existing Deep Calibration development beta and supersedes beta 9. It is the current working baseline, not a separate experimental fork. This version is published on the repository's `beta` branch; the stable `main` branch is separate. Keep official Auto Trim 3.9.13 separate; there is no bundled Auto Trim. Replace the complete Deep Calibration folder, rerun its existing installer, and restart while idle. Check DEEP_CALIBRATION_STATUS for 0.1.0-beta.10.1. If updating Python does not load the new version on your zMod setup, use a full printer reboot. Publishing this source does not install it on your printer.

### Polling

During a recording (including a knee search) Deep Calibration recognizes the installed LOAD_CELL_POLL-patched native reader and temporarily sets its post-reading pause to zero. It does not install or modify that driver, send extra serial requests, or change WAIT. It restores the exact prior pause on stop, automatic end, shutdown/disconnect, sensor startup failure and writer failures. Unpatched readers continue normally. `poll_accelerate: False` opts out. Set your driver WAIT to its native 0.05 before recording if desired; the recorder preserves whatever WAIT you selected.

Measured board-side throughput remains about9.8 Hz, not the console's theoretical33 Hz. `polling_accelerated` status and `poll_policy` events expose the policy. This uses the patched driver's poll_time attribute; changing the driver/patch API requires review. A native driver without that interface is left untouched.

### Margin policy and flow keys

There is no established universal knee-to-good margin. By default an unfamiliar flow recipe requires an explicit `MARGIN=` or a manually initialized learned entry. The legacy0.125 fallback still exists only for compatibility when `knee_require_margin: False`; it is not recommended as a validated default. A `knee_margin` config value alone does not bypass the new requirement.

Keys include material, layer height, line width, print speed, filament diameter and nominal `HEIGHT * WIDTH * SPEED` flow in mm3/s (four decimal places). Equal-flow recipes with different dimensions/speeds have distinct entries. This is nominal metadata, not measured extrusion. Actual bead cross-section, temperature, nozzle, extrusion multiplier and path history can change force at the same nominal flow. Do not assume one entry transfers universally. Old height-only and beta10 flow-only entries stay in knee_margins.json but are not silently reused or converted. Accurate slicer recipe values are necessary; a metadata edit or speed/extrusion override change during a search aborts it and restores the original offset.

For a one-off experiment with a margin you explicitly choose:
```gcode
DEEP_CALIBRATION_KNEE ARM=1 MARGIN=0.0075
```
That number is the user's fast-recipe candidate, not a recommendation for arbitrary prints. Put the line after DEEP_CALIBRATION_ARM in the existing slicer startup, before layer1. Explicit MARGIN remains one-off and is not learned. Omit it only when a matching flow entry exists.

To initialize a provisional flow entry that can subsequently learn from first-layer babysteps:
```gcode
DEEP_CALIBRATION_KNEE_MARGIN MATERIAL=PLA HEIGHT=0.2 WIDTH=0.5 SPEED=110 FILAMENT=1.75 FLOW=11 MARGIN=0.0075
```
Use your actual nominal flow and chosen margin. Use the same MATERIAL/HEIGHT/WIDTH/SPEED/FILAMENT parameters for ADJUST or RESET=1. FILAMENT defaults to1.75; optional FLOW must agree with HEIGHT*WIDTH*SPEED within0.1%. Flow-only and height-only editing are rejected. The listing command with no arguments remains available. Only user adjustments after a successful non-fixed search teach margins at first-layer completion, and invalid/negative or >0.3mm observed margins are rejected. The user's clean-0.075 fixed-offset confirmation is still pending; do not silently reset Auto Trim's calibration to that value.

### Descending result and ascending diagnostic

The descending fit determines the selected knee and target. Ascending data is fitted and reported separately with its disagreement, but has zero weight in the selected knee. A lower sample error does not justify treating pressure/path hysteresis as geometric repeatability. The existing CONFIRM option remains; CONFIRM=0 skips the ascending diagnostic. Default up steps discard6s after queue lead, then measure for at least12s. Maximum hold remains at least the chosen minimum. First-layer end, force/travel guards, abort and restoration remain.

Down steps normally retain the6s minimum. With temporary polling active and at least8 samples/s actually accumulated over the step, the minimum can drop to2s; the sample-count and precision checks still apply. `knee_fast_hold` can be raised to6 to retain conservative timing. Do not interpret a changed sample value as proof of independence or claim a1.7x precision gain. Temperature drift, path variation and pressure history still need hardware evaluation.

Recommend a controlled faster-flow first-layer pad within your hotend/material's validated capability, not an automatic generated pattern. Begin at higher nozzle clearance and approach downward over fresh lines. Avoid reusing over-squeezed areas. Confirm the selected fixed offset on a clean print and inspect layer2; a successful recipe does not prove all recipes share the same offset. No new tuning-pattern macro is added.

### Added settings

| Setting | Default | Meaning |
|---|---|---|
| poll_accelerate | True | Temporarily remove patched driver's post-reading pause |
| knee_require_margin | True | Require explicit or learned margin for an uncalibrated flow recipe |
| knee_fast_hold | 2 | Minimum down measurement seconds only when observed rate>=8Hz |
| knee_up_settle | 6 | Discard time after upward step/queue lead |
| knee_up_hold | 12 | Minimum upward measurement seconds |

### Verification and scope

264 software tests plus28 subtests pass, including17 new policy tests. The extracted release is tested again. No printer execution, full Klipper batch run, driver installation or upstream driver submission was performed for this build. Native probe helper behavior is unchanged: this branch still forces1mm/s contact and does not include the optional0.1mm/s controls from the separate beta5.9 branch. Auto Trim's upper offset cap is also outside this package's scope.


## Guarded approach

Every probe touch on the bed is made at 1 mm/s: meshes, KAMP, `PROBE`, and Z homing that uses the probe. A slow touch gives a more repeatable measurement (0.0075 to 0.01 mm at 1 mm/s, against 0.02 to 0.045 mm at 5 mm/s, measured on an AD5X).

To keep probing fast anyway, the guarded approach moves down quickly first: when a probe touched the bed in the last 5 minutes (`reference_max_age`), the nozzle moves at 5 mm/s (`approach_speed`) to 1 mm (`slow_clearance`) above the highest recent touch, with the probe watched the whole way, then makes the touch at 1 mm/s. If anything touches during the fast part, the measurement is rejected. The first touch of a session, and Z homing to an unknown height, are slow all the way.

While it is installed, every touch is 1 mm/s whatever Auto Trim's `probe_speed` says. Homing to the stock Z endstop is not affected.

`DC_APPROACH_STATUS` shows its state; `DC_APPROACH_RESET` forgets the recent touches, so the next probe is slow all the way.

**After a zMod update:** the approach hooks into Klipper's probe code. If an update changes that code, Klipper refuses to start and names `deep_calibration_approach` (`requires the reviewed Klipper 13 native probe`). Remove the `[deep_calibration_approach]` section from `deep_calibration.cfg` and restart; everything else keeps working at Auto Trim's probe speed until the package is updated.

## Strict bed soak calibration

When the bed heater reaches its target, the plate keeps moving for many minutes as it warms through. Auto Trim's `SOAK=AUTO` waits for it before probing, using a measured settling time. Deep Calibration measures that time more strictly than Auto Trim does:

| | Deep Calibration | Auto Trim (`AUTO_TRIM_SOAK_CALIBRATE`) |
|---|---|---|
| Settled when the points stay within | 0.01 mm | 0.02 mm |
| For | 10 minutes, and at least 10 minutes in total | 4 minutes |
| Probing | Repeated touches at each point, checked for repeatability | One touch per point |
| Result | Longer, more conservative | Shorter |

From a cold bed (below 40 C):
```gcode
DEEP_CALIBRATION_SOAK_CALIBRATE BED=60
```

| Option | Default | What it does |
|---|---|---|
| `BED` | (required) | Bed temperature to calibrate, in C |
| `POINTS` | 5 | 5 (centre and four near the corners) or 1 (centre) |
| `NOZZLE` | 121 | Nozzle temperature while probing (zMod's `temp_test_min`) |
| `NOZZLE_SOAK` | 300 | Seconds the nozzle is held at that temperature before the bed is heated |
| `INTERVAL` | 90 | Seconds between rounds |
| `STABLE` | 0.01 | How still the points must be, in mm |
| `WINDOW` | 600 | For how many seconds they must stay that still |
| `MIN_SOAK` | 600 | Shortest result accepted, in seconds |
| `MAX` | 2700 | Longest it measures, in seconds |
| `FORCE` | 0 | 1 starts from a bed above 40 C |

`DEEP_CALIBRATION_SOAK_STATUS` shows progress; `DEEP_CALIBRATION_SOAK_ABORT` stops it.

**One saved result per temperature:** Deep Calibration and Auto Trim save their soak result in the same place (`soak_t60` for 60 C), and Auto Trim uses whichever ran last for that temperature. To keep the strict result, do not run Auto Trim's soak or soak-and-mesh calibration at the same temperature afterwards.

## The 9 x 9 saved mesh macro

`DC_CALIBRATE_ONE_MM_AUTO_MESH`, from a cold bed: a strict soak calibration at 60 C, then a full 9 x 9 mesh at 1 mm/s, saved as the profile `auto`, then `SAVE_CONFIG` (Klipper restarts).

Two things to know before using it:
- **The mesh is probed with the nozzle at 230 C.** Auto Trim probes at 121 C after cleaning. A hot nozzle touches slightly early, so this mesh reads about 0.06 mm higher than what Auto Trim measures, and Auto Trim's 5-point check corrects for it on every print that uses the saved mesh. For a saved mesh that matches Auto Trim, use `AUTO_TRIM_MESH_CALIBRATE BED=60 EXTRUDER=230` instead.
- **9 x 9 with `mesh_pps: 5, 5`** makes Klipper interpolate a large mesh, which has been seen to stop printers with `Timer too close`. It ran fine on the AD5X it was developed on; with other printers, use `mesh_pps: 2, 2` or 7 x 7.

## Recording by hand

Any recording can be started and stopped from the console, for example an idle check of the sensors:
```gcode
DEEP_CALIBRATION_START RUN=idle_check MATERIAL=PLA HEIGHT=0.20 WIDTH=0.45 SPEED=40 FAN=0 LAYER=1 FILAMENT=1.75 ACCEL=1 ADC=1 MAX=30
```
That records 30 seconds (`MAX`) with the printer standing still: the baseline noise of the load cell and accelerometer. Useful after updates, and as a reference for first-layer recordings.

| Command | What it does |
|---|---|
| `DEEP_CALIBRATION_START` | Starts recording. `RUN` names it; `MATERIAL`, `HEIGHT`, `WIDTH`, `SPEED`, `FAN`, `LAYER`, `FILAMENT` describe the recipe; `ACCEL=0` or `ADC=0` leave out the accelerometer or the temperatures; `MAX` stops after that many seconds |
| `DEEP_CALIBRATION_STOP` | Stops recording. The file is finished in the background; check `DEEP_CALIBRATION_STATUS` before downloading |
| `DEEP_CALIBRATION_SET` | Changes the recipe in the recording (the printer itself is not changed) |
| `DEEP_CALIBRATION_ZERO` | Takes a software reference of the load cell while idle and stationary (at least 10 quiet readings over 2 seconds). It does not tare the board |

## Timing

Klipper reads G-code ahead of the nozzle: usually one to two seconds of moves are queued before they print. Deep Calibration places every first-layer event at the time it physically happens:

- **Start:** the first layer counts from the moment its first queued move runs (event `first_layer_start`).
- **Babysteps:** a label boundary is placed when the change reaches the nozzle, after the moves queued before it (`queue_lead` in each event says by how much).
- **Stop:** when layer 2 is announced, recording continues until the queued end of layer 1 has printed, then labels `GOOD` and stops (event `first_layer_end`).

Commands are applied in the order they are read, so a babystep made after layer 2 was announced changes layer 2, and is not a first-layer label. Auto Trim does not need this correction: it learns from the offset value itself.

## Sensor problems during a recording

The load cell and the accelerometer are the measurements: if either fails, or the load cell is silent for 1.5 seconds or the accelerometer for 2 seconds, the recording stops, because the data would be incomplete.

The temperature channels are context. A late report is recorded as an `adc_gap` event and recording continues; an irregular report is skipped and recorded (`adc_report_skipped`); a channel silent for 2 seconds is recorded as `adc_channel_lost`, and `adc_channel_resumed` when it reports again. A failure to write the recording file still stops it.

## Analysing recordings

Analysis runs on a computer, never on the printer. Copy the `.jsonl` file and its `.dca` files into one folder, named as on the printer (`<session>.accel.0000.dca` and so on), then:

```sh
python3 analyze.py 20261111T095854Z_PLA_firstlayer_079f897a.jsonl --output results --fit
```

| Option | What it does |
|---|---|
| `--output` | Folder for the results: `samples.csv`, `adc.csv`, `report.json` and the vibration features |
| `--fit` | Fits the force against the offset |
| `--settle` | Seconds left out after every label, offset, recipe or fan change |
| `--skip-vibration` | Leaves out the acceleration analysis |

The analyser is strict on purpose: it only uses stretches it can trust. It rejects a recording that did not end normally, acceleration data with any gap, readings right after a change (`--settle`), and stretches where the bed mesh in use cannot be verified against the plan. If it reports `0 stable segments`, `report.json` lists how many readings were rejected for each reason.

Other tools:

| Tool | What it does |
|---|---|
| `export_acceleration.py parts... --output file.csv` | Writes the acceleration data to a CSV file |
| `make_plan.py --output plan --material PLA` | Writes an experiment plan (CSV) and test coupons (STL) for a planned series of first layers |

## What the recordings have shown so far

The user's reported1mm/s probe readings are more repeatable than5/2.5mm/s. Poll trials measured about9.8Hz with a0.100s interval whether WAIT was0.05,0.02 or0; removing WAIT produced no throughput gain and noise remained about3g. The console rate is only an estimate.

The latest faster-flow (~11mm3/s) first layer had a descending knee around-0.0825mm and a candidate good offset around-0.075mm. Earlier slower-flow knees near-0.135 did not establish a good offset: -0.125/-0.13 scraped, and -0.01 was unconfirmed and too high for the later fast trial. The earlier universal0.125mm-margin claim is withdrawn. Flow and path/pressure history are plausible influences, not a proven universal flow-only calibration law. Ascending force was higher at matching offsets; do not average that discrepancy into apparent precision. Clean fixed-offset and slower-recipe confirmation prints remain pending. Raw newer recordings were not re-analyzed in this build.

## Commands

| Command | What it does |
|---|---|
| `DEEP_CALIBRATION_ARM` | Records the first layer of this print (start G-code) |
| `DEEP_CALIBRATION_DISARM` | Cancels `ARM` before the first layer starts |
| `DEEP_CALIBRATION_KNEE` | Knee search; `ARM=1` waits for the first layer |
| `DEEP_CALIBRATION_KNEE_ABORT` | Stops the knee search and puts the offset back |
| `DEEP_CALIBRATION_KNEE_MARGIN` | Shows the learned knee margins; with `MATERIAL=` and `FLOW=`, `MARGIN=`, `ADJUST=` or `RESET=1` changes one |
| `DEEP_CALIBRATION_MARK LABEL=<label>` | Labels the current offset by hand |
| `DC_MARK_GOOD` | `MARK LABEL=GOOD` |
| `DEEP_CALIBRATION_START` / `STOP` / `SET` / `ZERO` | Recording by hand (see [Recording by hand](#recording-by-hand)) |
| `DEEP_CALIBRATION_STATUS` | Version, recording state, sensors, file sizes |
| `DEEP_CALIBRATION_SOAK_CALIBRATE BED=<C>` | Strict soak calibration |
| `DEEP_CALIBRATION_SOAK_STATUS` / `SOAK_ABORT` | Its progress, or stop it |
| `DC_CALIBRATE_ONE_MM_AUTO_MESH` | Strict soak, then a 9 x 9 mesh saved as `auto` |
| `DC_APPROACH_STATUS` / `DC_APPROACH_RESET` | The guarded approach |
| `DEEP_CALIBRATION_MESH_STATUS`, `MESH_TRACE`, `MESH_TRACE_STOP`, `MESH_REQUIRE`, `MESH_TRAVEL_TEST` | Bed mesh diagnostics: which mesh is in use, and a trace of how it is applied while moving |

## Settings

In `[deep_calibration]` in `deep_calibration.cfg`:

| Setting | Default | What it does |
|---|---|---|
| `auto_capture` | True | `DEEP_CALIBRATION_ARM` records the first layer by itself |
| `auto_stop_layer` | 2 | The layer whose start ends the recording |
| `auto_adjust_labels` | True | Babysteps label the offset before them |
| `knee_start` | 0.10 | Knee search: how far above Auto Trim's offset it starts (mm) |
| `knee_step` | 0.01 | Step size (mm) |
| `knee_hold` / `knee_hold_max` | 6 / 20 | Shortest and longest step (s) |
| `knee_se_g` | 2 | Precision a step aims for (g) |
| `knee_rise_g` | 12 | Rise needed until the noise is known (g) |
| `knee_noise_k` / `knee_rise_min_g` | 4 / 6 | Rise needed: this many times the measured noise, and at least this (g) |
| `knee_margin` | 0.125 legacy | Only used with knee_require_margin=False; unvalidated fallback, not a universal calibration |
| `knee_learn_rate` | 0.5 | How far each print moves the learned margin towards what you kept |
| `knee_confirm` | True | Step back up to measure the knee from both sides |
| `knee_max_force_g` | 80 | Rise that stops the search at once (g) |
| `knee_max_travel` | 0.35 | Furthest it goes below its start (mm) |
| `knee_min_readings` | 8 | Fewest readings a step needs |
| `log_directory` | `mod_data/deep_calibration_data` | Where recordings are saved |
| `context_interval` | 0.1 | Seconds between position and state snapshots |
| `filter_tau` | 0.5 | Smoothing of the live load cell value (s) |
| `counts_per_gram` | 0 | Load cell scale; 0 keeps raw counts (set only after calibrating with a known weight) |
| `accel_default` / `adc_default` | 1 / 1 | Record the accelerometer and temperatures by default |
| `max_file_mb`, `accel_rotate_mb`, `accel_max_mb`, `storage_reserve_mb` | 256, 32, 512, 64 | Storage limits |
| `startup_integration` | False | Deep Calibration's own print start. Leave it off: Auto Trim prepares prints |

In `[deep_calibration_approach]`: `approach_speed` (5 mm/s), `slow_clearance` (1 mm), `reference_max_age` (300 s).

## Limits

- **A development beta, used on one printer.** The knee search, the labels and the analysis are built on recordings from one AD5X, with PLA. The fitted knee, the noise-based threshold, the adaptive hold and the margin learning were checked against those recordings and in tests, not yet in a full search on the printer.
- **Labels are your judgement.** The automatic `GOOD` means "kept", not "confirmed"; a first layer can look right and still be too close.
- **The load cell reads in raw counts** unless `counts_per_gram` is set; the knee search's gram values assume about 43 counts per gram.
- **The guarded approach depends on Klipper's probe code** and can stop Klipper from starting after a zMod update (see above).
- **Nothing here replaces looking at the first layer.**

## Files

| File | What it is |
|---|---|
| `deep_calibration.cfg` | Settings, and the includes for the files below |
| `deep_calibration_start.cfg` | Strict soak calibration, and the optional print start (off) |
| `deep_calibration_auto_mesh.cfg` | The 9 x 9 saved mesh macro |
| `deep_calibration.py` | The recorder, labels and knee search |
| `deep_calibration_sensors.py` | Load cell, accelerometer and temperature capture |
| `deep_calibration_mesh.py` | Bed mesh diagnostics |
| `deep_calibration_approach.py` | The guarded approach |
| `install_deep_calibration.sh` | The installer |
| `analyze.py`, `vibration_analysis.py`, `export_acceleration.py`, `make_plan.py` | Analysis tools (run on a computer) |
| `tests/` | Automated tests (`python3 -m pytest tests`) |
| `CHANGELOG.md` | Release history |
| `AUDIT.md`, `SOURCE_AUDIT.md`, `NOTICE.md`, `LICENSE` | Development audits, notices and licence (GPL-3.0) |
