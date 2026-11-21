> **OrcaSlicer factor review:** the full 378-setting audit for OrcaSlicer 2.5.0-dev 606b50f1 is in [the factor review](reference/orca_606b50f1/ORCA_FACTOR_REVIEW.md). Beta 10.2 captures exported settings and applies the segment gates described below. Unexported scoped settings remain unknown.

# Deep Calibration

A first-layer research suite for the Flashforge AD5X running zMod: it records what the printer measures during the first layer, labels it with what you judged by eye, finds the first-layer offset automatically with the load cell, and measures how long the bed takes to settle.

Version 0.1.0-beta.10.3.4 (2026-11-21). **Development continuation of beta 10.3.3.** Used together with [Auto Trim for zMod](https://github.com/Parabel54/Auto-Trim-plugin-for-zmod) 3.9.12 or newer.

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
It links the five Python modules (`deep_calibration.py`, `deep_calibration_sensors.py`, `deep_calibration_mesh.py`, `deep_calibration_approach.py`, `deep_calibration_gcode.py`) into Klipper's extras folder. It never writes `user.cfg` or zMod's files, and refuses to overwrite a file of the same name that is not its own link. Run it again after every update.

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

## Beta 10.3.4: slicer eligibility fixes, POLL_PAUSE per recording

Current continuation: **0.1.0-beta.10.3.4**. Replace the full folder, rerun the installer and reboot while idle.

In the 10.3.2 AD5X recording, none of the 1303 load cell readings was eligible for slicer-based analysis. Two rules were wrong:

- **Flushing on a single-filament print.** `model_flushing_not_separated` rejected every reading because the profile had `flush_into_infill = 1`, but the print used one filament and never flushed. It now applies only when the print uses more than one filament, or the filament list is unknown. Prints with more than one filament are still rejected (`tool_mapping_changed`).
- **Print-wide reasons restarted the settling run.** Any reason, including print-wide settings (flushing, raft, spiral mode, scarf seams, tool mapping, snapshot issues), restarted the 0.5 s settling run, so every reading was also `segment_settling`. Print-wide reasons still make a reading ineligible but no longer restart the run; conditions of the moment (speed or extrusion changes, retractions, no matched command) still do.

Replayed on that recording, with the 10.3.3 guard fix as well, about 10% of the readings would qualify; the rest are speed changes on a curved part made of 0.75 mm segments at 100 mm/s. Slower first layers and straight-line test pads give more.

- **`POLL_PAUSE=` on `DEEP_CALIBRATION_START`**, 0 to 1 s, for that recording only, e.g. `POLL_PAUSE=0` for about 10 load cell readings per second in an idle test. Prints keep `poll_pause` (0.1 s); the override is cleared when the recording ends.

Software tests: 381 pass with 37 subtests (6 new).

## Beta 10.3.3: the load guard judges the tick's share of its interval

Current continuation: **0.1.0-beta.10.3.3**. Replace the full folder, rerun the installer and reboot while idle.

The first AD5X recording with the slicer data loaded through the first layer (10.3.2, `SOAK=AUTO`) ran the whole layer: 77,905 objects frozen out of garbage collection, no shutdown. But the load guard climbed to level 6 within 43 s and stayed there: 80% of the acceleration frames thinned, the load cell slowed to 3.4 readings per second, while Klipper was never behind (timer lag under 0.03 s, queues empty). It escalated on a fixed limit of 0.05 s of tick work, and the tick's slicer batch matching takes 0.05–0.09 s at every interval (each tick matches the commands since the last one).

- A tick now counts as overloaded when the lag is high, the tick takes more than half its interval, or the queues fill. 0.08 s every 0.1 s is 80%; every 0.2 s it is 40%.
- One level down only when the work would stay under 35% even at the lower level's shorter interval, with little lag, for 5 s: no bouncing between levels.
- Replayed on that recording: level 1 (printer state every 0.2 s) and nothing further; full acceleration and the normal load cell rate.

Software tests: 375 pass with 37 subtests (5 new, from the recording).

Also seen in that recording, not changed here: none of the 1303 load cell readings was eligible for slicer-based analysis (43% `missing_or_ambiguous_queue`, 36% `model_flushing_not_separate`, 21% `extrusion_history_settling`).

## Beta 10.3.2: slicer data kept out of garbage collection

Current continuation: **0.1.0-beta.10.3.2**. Replace the full folder, rerun the installer and reboot while idle.

On the AD5X, a print with `SOAK=AUTO` read its 5.8 MB G-code file during the soak (17.7 s, as designed), then shut down with `Timer too close` four minutes into the shape mesh. Klipper's log shows zMod's garbage collector starting a full collection (estimated at 0.5 s) 0.1 s before the shutdown, with no other large stall. The parsed file is millions of small Python objects kept for the whole print, and a full collection walks them all. The previous print, without a soak, did not read the file and ran through, first layer recording included.

Now, as soon as the slicer data is loaded (during the soak, while the printer only waits), `gc.freeze()` moves everything alive into Python's permanent generation, which garbage collections skip. Memory is still freed by reference counting when the data is released. `DEEP_CALIBRATION_STATUS` shows the number of frozen objects (`gc_frozen_objects`).

Software tests: 370 pass with 37 subtests (2 new).

## Beta 10.3.1: the load guard records less, never stops

Current continuation: **0.1.0-beta.10.3.1**. Replace the full folder, rerun the installer and reboot while idle.

10.3's first recording on the AD5X ran the whole first layer (386 s, about 4.8 load cell readings per second, one accelerometer overflow kept as a gap) with the load guard never above level 0. 10.3.1 changes how the guard reacts when it is needed: it reduces how much is recorded, one level at a time, and never stops a stream, never stops the knee search and never ends the recording.

| Level | Recorded less |
|---|---|
| 1 | Printer state every 0.2 s |
| 2 | Acceleration every 2nd frame (800 per second), every batch kept |
| 3 | Printer state every 0.5 s |
| 4 | Acceleration every 4th frame |
| 5 | Load cell at the driver's own pace; ADC every 2nd report |
| 6 | Acceleration every 8th frame, printer state every 1 s, ADC every 4th report; stays here under sustained load |

One level up after two late ticks (three from level 3), one level down after 5 s of headroom, as in 10.3. Each change is a `recording_load_guard` event with its description. The knee search continues at every level; at level 5 its steps lengthen with the slower load cell.

- **Acceleration file format:** each batch now stores its thinning factor (`batch_format` `<IdIIH`); files from earlier betas still read. The analysis checks spacing and frame count against the factor, keeps thinned stretches out of the 1600 Hz vibration windows, and no longer marks a thinned recording invalid. 10.3's dropped or suspended batches still count as holes.
- Software tests: 368 pass with 37 subtests (the guard tests rewritten for the new rules; an older-format file test added).
## Beta 10.3: recording load guard and native motion history

The slicer snapshot and live recipe matching remain active. During recording with a ready snapshot, the motion command wrapper stores the virtual SD file position, command parameters and compact native coordinate checkpoints. Parameter matching and native trapezoid timing are resolved in the recorder tick. A tick reads the native toolhead history once for its recent force receipts. Separate motion phases can match the same indexed line when bed mesh splits the move. Missing history, overlapping candidates, unsupported motion or disagreeing native checkpoints leave the force sample unattributed and ineligible for knee fitting.

By default, `load_guard: True` monitors timer lateness, recorder tick time and writer queue pressure:

| Level | Recording behavior |
| --- | --- |
| 0 | Full requested capture |
| 1 | Write alternating acceleration batches and keep batches with reported overflow |
| 2 | Suspend this recorder's acceleration subscription and space context ticks at least 0.3 s apart |
| 3 | Use the driver's original load-cell polling, skip ADC output and end an active knee search using its normal offset restoration |
| 4 | End recording if pressure persists and report the size of any unwritten force tail |

Five seconds of headroom reduce the guard by one level. The existing acceleration writer is kept open during a pause. The JSONL records each transition and the final data-loss counters. Acceleration gap and overflow validation still applies. Native ADC/temperature callbacks and other accelerometer clients continue to run. STATUS exposes the level, timer lateness and previous tick time. These are software guardrails and need a physical AD5X timing test.

Keep the existing slicer start G-code. With the default soak policy, preparation reuses a snapshot loaded during the soak. A print that skipped the soak can still record force without starting a new slicer-file read at the first layer. The `arm` policy still explicitly permits an earlier read at arming. Shape mesh 1.0.1 and the 10.2.7 load-cell polling defaults are retained.

## Beta 10.2.7: lighter first layer, vibration gate removed

Previous baseline: **0.1.0-beta.10.2.7**.

Two more AD5X prints (10.2.5 and 10.2.6 era) shut down with `Timer too close` 2.7 and 4.3 s into the first layer: from the recording start, Klipper's reactor was busy essentially 100% of the time (stall time equal to elapsed time), with soak off, so the G-code context file was never read.

- **The G-code observer does nothing without slicer context.** Armed or recording, every `G0`/`G1` went through an observer that read the motion state two or three times and collected the printing conditions, about 68 times per second on this first layer, even when there was no slicer context to match: the most likely main load, and new since beta 10 (beta 6–8 recorded first layers on this printer). Without context it now passes each command straight to Klipper. With context, conditions are read at most every 0.1 s instead of per command.
- **Vibration gate removed** (added in 10.2.3): its accelerometer stream ran through every mesh, and its levels needed per-printer tuning. The guarded approach is exactly 10.2.2's again. `vibration_*` settings are gone; remove them from your config if you set them.
- **Polling while recording:** `poll_pause` 0.1 s and `poll_wait` 0.05 s (about 5 readings per second), both set on the patched driver at the start of a recording and restored afterwards. `poll_rate` (10.2.6) is replaced.

Software tests: 362 pass with 37 subtests (2 new for the observer load). The review's two gate regression tests were removed with the gate.

## Beta 10.2.6: 6 load cell readings per second while recording

Current continuation: **0.1.0-beta.10.2.6**. Replace the full folder, rerun the installer and reboot while idle.

On the AD5X, a 10.2.5 recording shut the printer down with `Timer too close` 2.7 s into the first layer: from the recording start Klipper's reactor was blocked for 0.15–0.47 s every few tenths of a second, each time with Deep Calibration's `_tick`, while the G-code context reader was not running (no soak, so the file was not read). The recording's own load at the first layer (10 load cell readings per second, the context, the acceleration stream, the writer threads competing through the GIL) was more than the printer could keep up with.

- **`poll_rate`** (new, default **6**): load cell readings per second while recording, 3.3–10. The driver pause is set to `1/poll_rate - 0.10` s (each reading takes about 0.10 s plus the pause: pause 0 measured 9.8/s, 0.02 measured 7.9/s, 0.2 measured 3.3/s); at 6/s that is 0.067 s. The board converts every 0.1 s, so the rate averages out near the target. The `poll_policy` event records the target and the pause.
- **Knee search steps:** with fast polling, the minimum step is the time for about 20 readings (3.3 s at 6/s, 2 s at 10/s, never below `knee_fast_hold`); its precision check is unchanged. It used to need 8 readings per second for the short steps.

Whether 6/s is light enough is the next print's question: if the first layer still stalls, `context_interval` and the acceleration stream are the next settings to try (see the logs' `Reactor ... busy` lines).

Software tests: 375 pass with 37 subtests.

## Beta 10.2.5: review fixes and shape mesh timing

Current continuation: **0.1.0-beta.10.2.5**. Replace the full folder, rerun the installer and reboot while idle. Fixes for an independent review of 10.2.3 (archive note 31), whose four regression tests now pass, and for the shape mesh:

- **Accelerometer counters are running totals.** The native reader reports errors and overflows as totals since the stream started, repeated in every batch. 10.2.3 and 10.2.4 counted each report as new, so one overflow still stopped a recording after four batches. Now only increases count, with the first batch as baseline when the recording joins a stream already running (the vibration gate may have started it). The acceleration file records the per-batch increase.
- **The vibration gate keeps its listener for the whole wait.** It let go 5 s after the last touch even during a 10 s wait, which then ended without data and kept the touch unmarked.
- **Unreliable data is never quiet.** Rows from a batch whose error or overflow total rose are not trusted; a measurement counts only for a window fully covered by valid, finite samples without gaps. Every touch has a quality, `quiet`, `shaken` or `unknown`; unknown is marked disturbed like shaken.
- **Analysis** excludes any window touching a driver-marked batch, even without a timestamp gap.
- **Shape mesh 1.0.1:** the mesh is built after probing and all moves have finished, not inside Klipper's probing finalize step. Building there took 0.4 s on an AD5X right after Klipper had timed the next move, and the printer shut down with `Timer too close`.

Software tests: 369 pass with 37 subtests, and the review's 4 regression tests pass. Physical validation pending.

## Beta 10.2.4: G-code context read during the soak, vibration limit 400, shape mesh

Current continuation: **0.1.0-beta.10.2.4**. Replace the full folder, rerun the installer and reboot while idle.

### Why: a print shut down three seconds into the first layer

On the AD5X (zMod 1.7.5), a print with 10.2.3 shut down with `MCU 'mcu' shutdown: Timer too close` three seconds after the first layer started. Klipper's log showed its reactor stalling from the moment the recording began (0.11, 0.14, 0.10, 0.46 and 0.38 s), with Deep Calibration's `_tick` taking about 0.1 s on its own. Garbage collection was not involved (its last full pass was four minutes earlier, none deferred).

The G-code context reader (10.2) parses the whole print file in a background thread, started when Deep Calibration is armed, here three seconds before the first layer. Python runs one thread at a time (the GIL), so while the parse runs, Klipper's reactor gets only a share of the processor. The print's 4.4 MB file took 3.8 s of CPU on a 2.1 GHz server core, far longer on the printer. The three 10.2.2 first-layer recordings that stopped about a second in on an accelerometer overflow (17–18 November) fit the same cause: a starved reactor reads the accelerometer late.

### What changes

- **`gcode_context_start: soak`** (default): the file is read when Auto Trim announces its bed heat soak wait (`AUTO TRIM: bed heat soak ... waiting`), seen on the console with no change to Auto Trim. The read finishes during the soak; arming later finds it done (or still loading) and does not read again. The console says how long the read took (`G-code context read in ... s`): it must fit inside the soak.
- **No soak wait, no read:** with `SOAK=OFF`, or a soak already covered by the nozzle clean, the file is not read at all. The recording runs without slicer context (the 10.1 eligibility policy) and says so once (`G-code context not read`, `slicer_context_skipped` event). A previous print's context is never reused.
- **`gcode_context_start: arm`** keeps the 10.2.2 behaviour; `gcode_context: False` still turns the reader off.
- **`vibration_limit` 400 mm/s²** (was 150). During probing the AD5X reads 150–170 with fans and heaters on (the idle checks, 60–85, were taken with them off): at 150, a KAMP mesh of 81 points made 248 waits and 75 redos on ordinary noise and took 63 minutes. Real disturbances measured 184–357.

### Shape mesh built in

10.2.4 includes the Auto Trim shape mesh: with Auto Trim 3.9.14 or later, `MESH=SHAPE` on the `AUTO_TRIM_PREPARE` line probes only the bed mesh grid points near the printed objects (Orca's object outlines) and fills the rest from the saved full-bed mesh (`auto`), aligned to the fresh points by a plane fit. For a side panel running diagonally across the bed: 48 of 81 points, with the same accuracy under the part as a full KAMP mesh. The installer links `auto_trim_shape_mesh.py` with the other modules and `deep_calibration.cfg` contains its `[auto_trim_shape_mesh]` section, so the separate Auto Trim addon is not needed (installing both is harmless: the same file). Every touch still goes through the guarded approach and the vibration gate. What it does in detail: the Auto Trim README, *Shape mesh addon (optional)*.

Software tests: 367 pass with 37 subtests (24 new: 11 for the G-code read timing and the vibration default, 13 for the shape mesh, which builds meshes with Klipper's own `ZMesh`). Physical validation pending: the next print shows the read time and whether the first layer runs clean.

## Beta 10.2.3: vibration gate and accelerometer overflows

Current continuation: **0.1.0-beta.10.2.3**. Orca start G-code stays unchanged. Replace the full folder, rerun the installer and reboot while idle (a reboot loads changed Python; `RESTART` does not).

### First-layer recordings no longer stop on one accelerometer overflow

On the AD5X, 10.2.2 recordings stopped about a second into the first layer with `native acceleration errors/overflows: 0/1`: the accelerometer chip's buffer overflowed once, and any overflow ended the recording. Now:

- A single overflow is recorded as an `accel_overflow` event, and the batch keeps its overflow mark in the acceleration file, so the analyser treats that stretch as gapped, as it already does for gaps. The load cell and everything else keep recording.
- More than 3 overflows within 60 seconds (`accel_overflow_limit`) still stop the recording: by then the data is unreliable.
- An accelerometer data error (not an overflow) still stops it at once.

The overflow happened where 10.2.2 starts the recording, the accelerometer and fast load cell polling at the same moment, at the start of a print. If overflows keep appearing there, `poll_accelerate: False` shows whether fast polling at print start is the trigger.

### Vibration gate: clean probe touches on a shaking table

**Removed in 10.2.7.** Kept here as the 10.2.3 release notes.

The load cell feels the touch, so shaking from outside, such as another printer running on the same table, moves the moment it triggers. On one AD5X with an AD5M printing next to it, that scatter was what kept every strict soak calibration from passing.

The toolhead accelerometer measures exactly that shaking. Around every probe touch (meshes, KAMP, `PROBE`, soak rounds, homing with the probe):

1. **Before the touch,** with the nozzle still after any fast approach, the shaking is measured for 0.3 s (`vibration_window`). Above 150 mm/s² (`vibration_limit`) the touch waits until it settles, up to 10 s (`vibration_max_wait`).
2. **During the touch,** the shaking is measured again (the limit was 400 mm/s² in 10.2.4–10.2.6). If the touch itself was shaken, its result is discarded, the nozzle goes back up, and the touch is made again, up to 2 times (`vibration_retries`). Homing touches wait but are never redone: Klipper re-zeroes Z on each homing touch.
3. **If it is still shaken after that,** the last touch is kept and marked as disturbed, so a mesh is not failed halfway.

Shaking is the RMS of each axis' deviation from its own mean, combined, in mm/s²: gravity and the board's tilt drop out. A quiet AD5X reads about 60–85 (the idle checks), so 150 is about twice the quiet level; raise it if touches wait on a printer that is simply noisier.

Every touch is recorded: position, shaking before and during, the wait, the attempt, and whether it was redone or disturbed. `DC_APPROACH_STATUS` shows the counts and the last touch; during a recording, each touch is also a `probe_touch` event. The console says when a touch waits, is redone, or is kept while shaken.

One listener on the accelerometer serves all touches, so a 9 x 9 mesh does not restart the chip 81 times; it is released 5 seconds after the last touch, and attached again if Klipper dropped it. Without the accelerometer (`vibration_gate: False`, or a printer without one) touches are made as before.

Software tests: 343 pass (10.2.2's 329, the old overflow test replaced by three, and 11 for the gate) with 37 subtests. Physical validation pending: the default limit is a starting point.

## Beta 10.2.2: repeated validation and filament-profile scan

Current continuation: **0.1.0-beta.10.2.2**. Orca start G-code stays unchanged. Replace the full folder, rerun the installer and restart while idle. There are still five runtime modules.

Repeated source validation found that a long/split move can be processed while its G1 handler is still paused in native queue backpressure. Registering its end timing only after that handler returns is too late. Timing callbacks now attach to native lookahead moves at insertion, before processing/pausing. Split moves get separate clock intervals, with the same verified parent command. Native return values/errors are preserved; annotation failure blocks fitting. Unsupported queue APIs remain unsupported rather than guessed. Tests use the unmodified supplied native planner/movement methods with in-memory I/O sinks; hardware validation is pending.

### Scan the filament used by the selected print

Run in Fluidd/Mainsail:

```gcode
DEEP_CALIBRATION_FILAMENT
DEEP_CALIBRATION_FILAMENT SHOW=HIDDEN
DEEP_CALIBRATION_FILAMENT SHOW=ALL
```

These are read-only console commands. They do not heat, home, tare, change offsets or apply a filament preset. The first gives a summary; HIDDEN lists potentially mode/dependency-hidden settings; ALL lists the complete catalog. If scanning is needed, a background scan starts and its result appears automatically. The scanner reads the selected virtual-SD/current recording file, or retains the last verified snapshot after a print; selecting a new file changes the source. The report includes the source path/hash, exported filament preset identity and a separately labelled live-printer-now snapshot of PA, targets, fans and overrides. An uploaded file that has not been selected is not silently treated as the current print.

All exported config values are still archived automatically when recording; the scan commands are optional and add nothing to slicer startup. They inspect file metadata, not Orca's currently open editor on another computer. No Orca MCP connection is required by the printer plugin.

### Full filament option inventory, including hidden controls

The pinned OrcaSlicer 2.5.0-dev 606b50f1 filament inventory has **152 options**. It includes the explicit filament preset key list, filament-page bindings, dynamic override controls and the developer key set. No mode or feature-condition filtering is applied. Modes/dependencies overlap: 83 advanced, 1 expert, 18 developer; 45 have dependency controls and 31 lack an explicit binding in the scanned filament builders. The potentially hidden union is 130. Lack of an explicit binding is not proof that a generic dialog cannot expose a key. Actual visibility depends on your printer, selected variant and enabled features.

- [All 152 filament options](reference/orca_606b50f1/ALL_FILAMENT_OPTIONS.md)
- [Potentially hidden/mode/dependency options](reference/orca_606b50f1/HIDDEN_FILAMENT_OPTIONS.md)
- [Machine-readable registry](reference/orca_606b50f1/filament_registry_606b50f1.json)

The availability inventory is not your actual preset values. Missing fields remain unknown. Disabled/nil overrides remain explicit; they are not replaced with inherited/default values. Unverified active-filament and variant mappings keep the raw arrays and say unresolved. Exported file values are not proof that the firmware currently applies them.

### Scan an exported preset, including its supplied parents

On a computer, from this folder:

```sh
python scan_filament_profile.py print.gcode --output filament-scan.json
python scan_filament_profile.py MyPLA.json --parent GenericPLA.json --parent BasePLA.json --output filament-scan.json
```

Use one command appropriate to your input and a fresh output filename. The tool writes JSON plus a Markdown report, preserves each value's origin and reports missing parents. It never imports catalog defaults. Multiple variant values remain unresolved rather than choosing one arbitrarily. Custom additional filament metadata is retained. Preset JSON/parent exports or a project are needed to recover values deliberately omitted from G-code; the plugin cannot read your laptop's Orca editor remotely.

Validation: **329 tests +37 subtests pass** in source; extracted-package results are recorded separately. See `BETA10_2_2_VALIDATION.md`. Existing recording, labels, continuous sensors, 1 mm/s guarded contact, soak tools and Auto Trim integration remain. Physical validation is pending.

## Beta 10.2.1: reviewed corrections

Use **0.1.0-beta.10.2.1** in preference to 10.2. The start G-code remains unchanged. Replace the complete folder, rerun its installer and restart while idle.

The independent review found and fixed native modal/coordinate attribution, G91/M82 and relative-E-after-tool-selection parsing, truncated long queue timing, and force-limit relief being classed as a learnable result. It also fixed valid Orca duplicate wipe-tower coordinates and comma-separated numeric arrays, retained queued attribution after file EOF, and made missing eligibility flags explicit rather than assuming disabled. Filament profile identity now stays in the physics fingerprint. Legacy margin entries remain on disk; changed identities need a matching seed or explicit one-off margin.

Native handlers still run once and retain their errors/return values. Attribution verifies native pre/post coordinates, extrusion mode/delta and inherited feed against the indexed command. Force-limit relief remains a stop/retreat, with `accepted: false`; it is not a fitted knee or a margin-learning reference. Full queue lead is used for offset/label settling rather than a five-second cap.

See [the review report](BETA10_2_REVIEW.md). **314 tests and 37 subtests pass**, including regressions against the supplied unmodified Klipper movement class. Software tests do not establish physical printer validation.

## Beta 10.2: slicer context without longer start G-code

Keep your existing `DEEP_CALIBRATION_ARM MATERIAL=... HEIGHT=... WIDTH=... SPEED=... FILAMENT=...` line, Auto Trim preparation and layer hooks. No new slicer placeholders or per-setting G-code commands are required. Replace the complete package folder, rerun the installer, and restart while idle; it now links a fifth module. Check `DEEP_CALIBRATION_STATUS` for **0.1.0-beta.10.2.1**.

### Automatic file capture

With `gcode_context: True` (default), the plugin reads the selected virtual-SD file on a separate handle in a background thread. Since 10.2.4 it does so while Auto Trim's bed heat soak waits (`gcode_context_start: soak`), and not at all without a soak wait; `gcode_context_start: arm` reads it at arming, as before. It hashes the complete UTF-8 G-code, reads Orca's header/footer config block and retains all exported keys verbatim, including percentages, arrays, disabled options and future unknown keys. Coverage against the pinned 378-key process registry lists exported and missing keys. Missing values are not filled from defaults. Cached parsed contents are keyed by file/settings hashes; replacement files and changed sidecars invalidate the active snapshot.

The full settings snapshot is stored once as a `slicer_snapshot` event. Each force sample contains `slicer_context`: emitted role, local height/width, feed, E/mm, tool/object identity, selected material/filament/nozzle dimensions, physics fingerprint and eligibility reasons. Live heater readings/targets, fan commands, pressure advance, overrides and mesh identity are recorded. The existing ARM recipe remains as declared metadata; emitted dimensions and actual extrusion velocity are used by the new analysis where available.

### Which readings can feed a knee search

Native G0/G1/G2/G3 handlers retain their normal behavior and errors. Batched trap-queue history associates indexed linear moves with native print-clock intervals. Samples use requested motion at host receipt. Cached motion status, nested macro motion, modified command parameters and ambiguous or missing timing do not qualify. ADC acquisition and serial latency remain unknown.

Eligible samples require verified first-layer model extrusion, emitted geometry, settled temperatures, known live PA/fan/override/mesh conditions, and sufficiently steady commanded speed/extrusion. Supports, skirt/brim, tower/purge, bridge, ironing, unknown roles, Z-moving paths, arcs, raft, mixed-color layers, spiral mode, model flushing and scarf walls are excluded as applicable. Relevant settings and selected material dimensions remain in the identity. Multi-material/remapped tool variants are excluded unless a single used-filament mapping can be established from the exported file; a plain single-material file needs no additional hook.

Default `segment_settle: 0.5` seconds discards settling after speed/travel transitions. Retractions and a changed extrusion recipe also impose at least 2 seconds of history settling. This is a conservative software policy, not a physically validated pressure-decay model. Only accepted sample time counts toward a knee hold; travel does not count and does not cause the search to step down. Accepted same-recipe samples can accumulate across rejected transitions after settling. An insufficient measurement window or prolonged absence of suitable extrusion stops the search and restores its original offset. Changes to the eligible role/geometry/flow recipe or live PA/thermal/fan/mesh conditions abort it. Descending fit selection and longer ascending diagnostics remain.

Recording remains available when source context is missing or unsupported. Automatic fitting waits/refuses and reports why; it does not silently fall back. `gcode_context: False` explicitly restores the older beta10.1 eligibility policy and unscoped margin keys.

### Learned margins and analysis

New automatic margins append the full segment/physics fingerprint to the existing material/height/width/speed/filament/nominal-flow key. Old entries remain saved and are not reused automatically. Filename/output-name/notes-only changes do not change the physics identity; unknown settings and custom G-code bodies stay in it. Offline summaries, GOOD pairing and experimental models also keep fingerprints separate. Source exclusions remain after manual relabelling.

An explicit `MARGIN=` still permits a one-off search and is not learned. To initialize a learnable entry, run the existing `DEEP_CALIBRATION_KNEE_MARGIN` command with the same ARM recipe dimensions during an eligible recording; it binds to the current fingerprint. Alternatively provide `FINGERPRINT=<64-character fingerprint from the recording/status>`. The existing start G-code needs no additional parameters. User-adjustment learning requires matching recent eligible context and unchanged live conditions.

### Optional project snapshot

The emitted global config does not reveal every inherited object/modifier or filament-variant setting. To archive an Orca project alongside it, run on your computer after the final G-code has been produced:

```sh
python export_slicer_snapshot.py print.gcode --project project.3mf
```

Upload both `print.gcode` and `print.gcode.dc.json` into the same printer directory. No exporter is run on the printer and no start-G-code command is added. The sidecar archives the project's metadata settings parts, including scoped XML/JSON, and is bound to the exact G-code SHA-256. It never promotes a modifier to a global setting or guesses inheritance. Raw and physics settings hashes are separate; stale/tampered sidecars cannot silently supply settings. An existing sidecar is not overwritten. This is optional provenance capture, not a claim that all 378 settings are independently resolved into physical model features.

See `BETA10_2_IMPLEMENTATION.md` for limits and validation. Physical printer validation remains pending.

## Beta 10.1: flow-aware knee search and temporary fast polling

Beta 10.1 is the official continuation of the existing Deep Calibration development beta and supersedes beta 9. It is the current working baseline, not a separate experimental fork. This version is published on the repository's `beta` branch; the stable `main` branch is separate. Keep official Auto Trim 3.9.13 separate; there is no bundled Auto Trim. Replace the complete Deep Calibration folder, rerun its existing installer, and restart while idle. The beta10.1 changes below are retained in beta10.2. If updating Python does not load the new version on your zMod setup, use a full printer reboot. Publishing this source does not install it on your printer.

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

`DC_APPROACH_STATUS` shows its state, including the vibration gate's counts and the last touch; `DC_APPROACH_RESET` forgets the recent touches, so the next probe is slow all the way. Run it after turning a bed levelling knob: the bed is then no longer where the last touch found it.

(10.2.3–10.2.6 added a vibration gate to the approach; it was removed in 10.2.7.)

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

The load cell and the accelerometer are the measurements: if either fails, or the load cell is silent for 1.5 seconds or the accelerometer for 2 seconds, the recording stops, because the data would be incomplete. An accelerometer buffer overflow is the exception: a single one is recorded as an `accel_overflow` gap and recording continues; more than 3 within 60 seconds (`accel_overflow_limit`) stop it.

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
| `load_guard` | True | Shed optional recorder data in stages and restore it after host timing recovers |
| `filter_tau` | 0.5 | Smoothing of the live load cell value (s) |
| `counts_per_gram` | 0 | Load cell scale; 0 keeps raw counts (set only after calibrating with a known weight) |
| `accel_default` / `adc_default` | 1 / 1 | Record the accelerometer and temperatures by default |
| `max_file_mb`, `accel_rotate_mb`, `accel_max_mb`, `storage_reserve_mb` | 256, 32, 512, 64 | Storage limits |
| `startup_integration` | False | Deep Calibration's own print start. Leave it off: Auto Trim prepares prints |

In `[deep_calibration_approach]`: `approach_speed` (5 mm/s), `slow_clearance` (1 mm), `reference_max_age` (300 s). In `[deep_calibration]`: `accel_overflow_limit` (3 within 60 s).

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
