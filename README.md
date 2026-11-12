# Deep Calibration

A first-layer research suite for the Flashforge AD5X running zMod: it records what the printer measures during the first layer, labels it with what you judged by eye, finds the first-layer offset automatically with the load cell, and measures how long the bed takes to settle.

Version 0.1.0-beta.8 (2026-11-12). **Development beta.** Used together with [Auto Trim for zMod](https://github.com/Parabel54/Auto-Trim-plugin-for-zmod) 3.9.12 or newer.

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

Download the `beta` branch (Code > Download ZIP), unzip it, and rename the folder to `deep_calibration_development_beta`. Copy that whole folder into `mod_data` (Fluidd or Mainsail: Configuration > `mod_data`). When updating, replace the whole folder. Your recordings (`deep_calibration_data`) and saved soak calibrations are separate and are kept.

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

## Knee search: finding the offset automatically

Recordings show a clear pattern. Above a certain offset, the nozzle lays the line without pressing on it, and the load cell reads almost nothing. Below it, the force rises steeply. That point, the knee, is where the nozzle starts pressing the line into the bed. A good first layer sits just above it, by a small margin.

`DEEP_CALIBRATION_KNEE` finds the knee during the first layer, then sets the offset the margin above it. Auto Trim learns that offset when layer 3 starts, like a babystep.

### How it searches

1. It raises the nozzle 0.10 mm above the offset Auto Trim set (`START`), where the force reads near zero.
2. It lowers the nozzle 0.01 mm at a time (`STEP`). Each step is measured once the change has reached the nozzle (see [Timing](#timing)), using only the readings taken while printing.
3. When a step rises clearly above the steps before it, and the next step rises further, the knee is between them.
4. It steps back up until the force is flat again, to measure the knee from the other side.
5. It fits the knee through all the steps, and sets the offset the margin above it.

The console shows every step, for example:
```
DEEP CALIBRATION: knee search started at Z 0.110 (0.100 above Z 0.010), stepping down 0.010 mm; margin 0.025 (default)
DEEP CALIBRATION: knee search Z -0.120: 1.4 g (recent level -5.7 g, rise needed 15.9 g, +/-1.8 g, 26 readings)
DEEP CALIBRATION: knee going down at Z -0.1365; stepping back up to confirm it
DEEP CALIBRATION: knee check going up Z -0.130: 2.1 g (flat)
DEEP CALIBRATION: knee found at Z -0.1362 (down -0.1365, up -0.1358, repeatability 0.0007 mm): the nozzle starts pressing the line there. Offset set to Z -0.1112 (knee + 0.025, default); Auto Trim learns it when layer 3 starts.
```

### How long each step takes (adaptive hold)

The load cell reports about 3 times a second, and each reading is noisy, so one step needs many readings. Each step lasts at least 6 seconds (`HOLD`). After that it ends as soon as its median force is known to within 2 g (`SE`), or at 20 seconds at most (`HOLD_MAX`). A quiet load cell gives short steps; a noisy one gets the time it needs. The console shows the precision of each step (`+/-1.8 g`).

### When a rise counts (threshold from the noise)

A step is compared with the median of the three flat steps before it, never with a fixed value: the load cell drifts slowly (about 2 g per minute in recordings), and comparing neighbouring steps makes that irrelevant.

How big the rise must be is measured, not guessed. From the first flat steps, the search measures how much the step results jump from one step to the next, using the differences between neighbouring steps (so slow drift does not count as noise). The rise must then be 4 times that noise (`NOISE_K`), and at least 6 g (`RISE_MIN`). Until four flat steps exist, it uses 12 g (`RISE`).

Example from a real 0.2 mm first layer: the step results wandered by about 4 g, so the rise needed was about 16 g. A step that recovered from a dip (from -15.5 g back to -2.2 g, a jump of 13 g) is no longer mistaken for a rise.

A step that passes is a candidate. It only counts if the next step rises further (by half the threshold); a single high step that does not continue is ignored.

### Where the knee is (fitted, not stepped)

The step that first passes the threshold is not the knee itself: the rise starts somewhere above it, between steps, and with a gentle rise or a noisy load cell, the threshold may only be passed a step or two later. So the search fits a line through all its steps: flat down to the knee, then rising steadily below it. The knee is where the two meet, found to 0.0005 mm, anywhere from half a step below the candidate to two and a half steps above it. Steps with a more precise median count more.

On the real 0.2 mm recording, the old rule put the knee at -0.150 (the first step over the threshold); the fit puts it at -0.136, and gives the same answer whichever step the threshold was passed at.

### Measured from both directions (confirmation)

After finding the knee going down, the search steps back up 0.01 mm at a time until two steps in a row are flat again (at most 4 steps above the knee). It fits the knee again from that side, using the deepest step as the start of the way up. The difference between the two is the repeatability of this search, shown in the console. If it is more than two steps, the console says the result is less certain. The knee used is the fit through all the steps, down and up.

On the real 0.08 mm recording, where the nozzle went down and back up by hand, the knee was -0.1380 going down and -0.1325 going up: a repeatability of 0.0055 mm. `CONFIRM=0` skips the way up.

### The margin above the knee (learned)

The knee is where pressing starts; how far above it a good first layer sits depends on the filament, the first-layer height and your taste. The search uses a margin per filament and first-layer height (for example `PLA 0.20`), and learns it from you:

- After a search, look at the first layer. If it is right, do nothing: nothing is learned, the margin stays.
- If it is not, babystep it during the same first layer. When layer 2 starts, the offset you kept, minus the knee, is what this print wanted. The margin moves halfway towards it (`knee_learn_rate`).

```
DEEP CALIBRATION: knee margin for PLA 0.20 learned: you kept Z -0.0912, 0.0450 above the knee; margin 0.0250 -> 0.0350
```

The next search for that filament and height uses the learned margin (the console says `learned from 2 prints`). The margins are kept in `knee_margins.json` beside the recordings.

`DEEP_CALIBRATION_KNEE_MARGIN` shows them. To change one by hand, for example when layer 2 scraped and the first layer should be higher:
```gcode
DEEP_CALIBRATION_KNEE_MARGIN MATERIAL=PLA HEIGHT=0.2 ADJUST=0.01
DEEP_CALIBRATION_KNEE_MARGIN MATERIAL=PLA HEIGHT=0.2 MARGIN=0.03
DEEP_CALIBRATION_KNEE_MARGIN MATERIAL=PLA HEIGHT=0.2 RESET=1
```
A `MARGIN=` on the knee search line is used for that search only, and nothing is learned from it.

### Safety

| If... | Then |
|---|---|
| A step is 80 g above the recent level (`MAX_FORCE`) | The search stops at once and sets the offset the margin above the knee found so far |
| It has gone 0.35 mm down without a knee (`TRAVEL`) | It stops and puts the offset back where Auto Trim set it |
| The first layer ends first | It stops and puts the offset back |
| You run `DEEP_CALIBRATION_KNEE_ABORT` | It stops and puts the offset back |

Its own steps are recorded as `knee_step` events and the result as `knee_result`, not as your too high or too close labels. Babysteps you make after the search are labelled normally.

### Using it

`DEEP_CALIBRATION_KNEE ARM=1` on the start G-code, after `DEEP_CALIBRATION_ARM`. It starts 3 seconds into the first layer. A search takes about 25 to 30 steps of 6 to 20 seconds, so the first layer needs to last several minutes: a large flat square works well. Search at the first-layer height you print: the knee moves a little with it (about -0.13 at 0.08 mm and -0.14 at 0.2 mm on the first printer tested).

| Option | Default | What it does |
|---|---|---|
| `START` | 0.10 | How far above Auto Trim's offset it starts (mm) |
| `STEP` | 0.01 | Step size (mm) |
| `HOLD` / `HOLD_MAX` | 6 / 20 | Shortest and longest step (s) |
| `SE` | 2 | Precision a step aims for (g) |
| `RISE` | 12 | Rise needed until the noise is known (g) |
| `NOISE_K` / `RISE_MIN` | 4 / 6 | Rise needed: this many times the noise, and at least this (g) |
| `MARGIN` | learned, or 0.025 | Offset set this far above the knee (mm); on the line, used once and not learned |
| `CONFIRM` | 1 | Step back up to measure the knee from both sides |
| `MAX_FORCE` | 80 | Rise that stops the search at once (g) |
| `TRAVEL` | 0.35 | Furthest it goes below its start (mm) |

During a first layer that is already recording, `DEEP_CALIBRATION_KNEE` without `ARM` starts it at once.

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

From one AD5X, PLA, first layers of 0.08 and 0.2 mm:

- **The knee can be measured to a fraction of a step.** Fitted through all the steps, the knee of a real 0.2 mm search came out at -0.136, whichever step the threshold was passed at; measured going down and back up on a 0.08 mm first layer, the two sides agreed to 0.0055 mm.
- **The load cell sees the nozzle pressing.** The force stays near zero until the nozzle starts pressing the line, then rises steeply: about 100 g over 0.04 mm at a 0.08 mm first layer, about 22 g over 0.02 mm at 0.2 mm. Moving back up brings the force back down, so it is the height, not time.
- **It cannot tell "right" from "too high".** Both read near zero. That is why the knee search looks for the start of the rise and backs off by a margin, instead of aiming for a force.
- **The load cell drifts slowly,** about 2 g per minute at a fixed offset. Steps compared with each other are not affected; an absolute force target would be.
- **A first layer that looks perfect can still be too close.** At -0.13 mm a 0.08 mm first layer looked smooth, but the next layer scraped.

## Commands

| Command | What it does |
|---|---|
| `DEEP_CALIBRATION_ARM` | Records the first layer of this print (start G-code) |
| `DEEP_CALIBRATION_DISARM` | Cancels `ARM` before the first layer starts |
| `DEEP_CALIBRATION_KNEE` | Knee search; `ARM=1` waits for the first layer |
| `DEEP_CALIBRATION_KNEE_ABORT` | Stops the knee search and puts the offset back |
| `DEEP_CALIBRATION_KNEE_MARGIN` | Shows the learned knee margins; with `MATERIAL=` and `HEIGHT=`, `MARGIN=`, `ADJUST=` or `RESET=1` changes one |
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
| `knee_margin` | 0.025 | Margin above the knee until one is learned (mm) |
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
