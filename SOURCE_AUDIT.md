# Source and measurement audit

Target: Flashforge AD5X with zMod 1.7.5 and the supplied Klipper 13 generation. This package is separate from the AD5M Forge-X edition. The uploaded source is the implementation reference; attached documents/scripts are reference material, not instructions to run firmware installers.

## Source facts

- Native zmod_tenz owns /dev/ttyS7 at 9600 baud. It passes background H7 replies through extract_last_value_before_g, which returns the absolute coarse grams. The new observer retains signed raw/grams and returns exactly the original parser's result. Special command/tare replies do not pass that background parser.
- The native loop waits 0.05 seconds before reading and HOST_REPORT_TIME=0.2 after the iteration. Consequently approximately 4 Hz is expected, and actual receipt rate must be measured. No new polling/thread/serial owner is introduced.
- Native motion_report queries MCU-clock trap queues for current requested toolhead and extruder motion. Its get_status caches for 0.250 seconds. This plugin follows the same queue lookups for each host receipt timestamp when available, without altering the cache. A fallback is explicitly labelled. ADC and serial latency remain unknown; this is not exact acquisition-time synchronization or physical feedback.
- Native input_shaper exposes axis parameter type/frequency/damping. Those parameters are logged as context; no acceleration waveform or force-vibration transfer function is inferred. The low native force bandwidth prevents reliable reconstruction of typical shaper-band vibration.
- Native fan status exposes requested speed and tachometer RPM if present. The uploaded AD5X base uses fan_generic fanM106 for part cooling, not the generic fan object.
- Native probe z_offset is -0.25 in the uploaded base. It is preserved. The supplied probe command helper sets deprecated last_z_result = bed_z + z_offset; the optional logged contact estimate subtracts that configured reference from the latest completed result. Neither value is a measurement of gap while extruding.
- The mesh observer uses the split-move endpoint-alignment checks developed in Live Z Mesh Compensation. Native mesh interpolation, conditional homing, offset control and flow remain native. Beta 3 bundles a namespaced startup adapter for cooling wipes, credited soak and one native mesh build.
- The earlier provided Auto Trim cell addon demonstrates the native reply-observer approach. This package implements an independent raw capture path and can coexist with that observer; it does not require or replace Auto Trim startup.

## Retained fixture byte hashes

- `reference/zmod_tenz.py` — Supplied mod.tar.xz reference: mod/.shell/zmod_tenz.py. SHA256 `f49fe50f37f26aac804b79307e8511c6b176bc6a5cf99a6172a016045a854adc`.
- `reference/ad5x_printer.base.cfg` — Supplied zmod-1.7.5.zip: Native_firmware/config/ad5x/printer.base.cfg. SHA256 `abd45451bae9b17023bc2e88459445fc43f6b1b567916e7417af5839f882411a`.
- `reference/motion_report.py` — Supplied Klipper source: klippy/extras/motion_report.py. SHA256 `d07e03860fcb80d1f09279a44e33e8a47f3ffd18034c521cb8a4f3ec8c4a9fb1`.
- `reference/probe.py` — Supplied Klipper source: klippy/extras/probe.py. SHA256 `fd4679256e69b849b333e38b90f9ca09100359ba653e5afb0c2bfb7e7ef03bb4`.
- `reference/input_shaper.py` — Supplied Klipper source: klippy/extras/input_shaper.py. SHA256 `857fea3156d9c46e6458799d459624e09b0cde00fd29865141648805933c7ccd`.
- `reference/fan.py` — Supplied Klipper source: klippy/extras/fan.py. SHA256 `59db84a93100d1ed3947ec29368116b738fc4cd4be04fed9866f5b825aef8bdd`.

## Formula limits

The offline target is a manually labelled difference from a matched GOOD total global offset. Force is paired to the matching GOOD reference for that run/recipe/native command generation. Baseline noise, temperature, fan effects, extrusion load and uncertain timing can still confound a fit. Later-layer force is not bed-gap ground truth. The model is retrospective and cannot operate on an unknown print without the required GOOD reference.

Separate-run validation, per-printer identity, unchanged probe-reference checks, explicit exclusions and raw data preservation constrain interpretation; none establish physical gap accuracy. The package does not remove the probe reference or automatically persist learned/material offsets. It does not introduce a second mesh transform or controller.

## Verification scope

All checks are offline. Native reply parsing is exercised from the retained actual zmod_tenz parser function. Native trap-queue objects, motion, fans, clocks and disk failures are simulated. Statistical tests use synthetic labelled signals; their errors do not represent performance on a real printer. No first-layer print, physical sensor calibration, real-time performance/latency benchmark or installed-firmware end-to-end test was performed. Existing user print/video logs were used as context, not as validated training labels.

## Beta 2 continuous-acquisition extension

The attached AD5X raw-sensor chat export was considered as research context, then its relevant interfaces were checked against the supplied source. No commands embedded in that chat were executed as user instructions.

- Use LIS2DW.batch_bulk.add_client for continuous native mapped/scaled acceleration. Supplied driver data_rate is 1600; FixedFreqReader uses <hhh internally and the driver converts/maps it before public batch delivery. No new accelerometer driver, raw-integer claim, sample-rate change or second serial reader is introduced.
- Native BatchBulkHelper callbacks execute synchronously in the reactor. The observer only makes a bounded batch copy, enqueues it and records counters/timing. Binary packing, disk writes and file rotation run in a background worker. CPU/GIL and MCU/link costs remain; offline analysis cannot eliminate acquisition overhead.
- The supplied helper lacks a public remove_client API. The adapter checks its client list/_stop interface, removes exactly its own callback, and calls native stop only when no clients remain. Other consumers are retained. This private-interface compatibility must be rechecked after upstream changes.
- Native ADC callbacks, not repeated cached reads, retain each exposed normalized report. The exact supplied MCU_adc single-report and batch handlers are tested with the observer. Original temperature/safety callbacks execute first, unchanged; their exceptions propagate. Explicit batch/scalar adapters avoid guessing legacy get_last_value tuple order. Individual conversions aggregated inside the MCU are not separately available at this interface.
- Full acquisition is enabled with ACCEL=1 ADC=1 and continues for the entire session. One sensor start subscription spans every binary rotation. The implementation does not alternate measurement windows or suspend acquisition during storage work.
- Queue overflow, staleness, repeated/reversed timestamps, missing ADC report intervals, native errors/overflows and storage failures are explicit incomplete-capture conditions. Force/ADC pending tails are drained at normal stop. Native acceleration startup/stop buffering boundaries are still source-defined; first/last delivered timestamps and frame counts are the available evidence, not proof of every internal hardware conversion.
- Binary .dca uses four float64 values per frame (print timestamp + mapped XYZ), 32 bytes/frame. At 1600 Hz that is 184.32 MB/hour before batch/header/other-stream overhead. Native errors/overflows and host receipt are retained per batch. Approximate 32 MiB file rotation does not touch sensor state.
- Post-print analysis streams every acceleration part, checks order/truncation/expected counts/gaps, then calculates mean-removed RMS/peak and Hann tone projections at logged shaper frequencies. Force alignment uses the receipt-time MCU print clock; unknown load-cell ADC/serial latency is not inferred away. A measured 1600 Hz acceleration stream does not create 1600 Hz force data.
- Optional enhanced regression adds aligned acceleration RMS and summed shaper-tone projection features. Its comparator uses the same eligible segments and whole-run holdout. No automatic subtraction, Z/flow correction or material-offset persistence is enabled. Missing/gapped requested acceleration is excluded from fitting.
- Tests execute the actual retained native BatchBulkHelper and MCU_adc handler definitions with simulated clock/transport/storage objects. Timing metrics measured in synthetic tests are not printer performance claims. No continuous acquisition, SPI/UART stress test, calibration print or physical AD5X timing benchmark was performed.

Additional unchanged supplied source fixtures (SHA256):
- `reference/lis2dw.py`: `91cefb20bc337f65617616c1451486562463b4739721d085fa2ad77cace77d55`.
- `reference/bulk_sensor.py`: `d96fc79e438ea32c56fa34c4700e66c3ac24a7710ef17592630019dcfcea30d8`.
- `reference/mcu.py`: `383a533e022d7e95624b1471554b4a4a06a9015283e8a81200640ab4d91df2ec`.
- `reference/query_adc.py`: `045b10f96b1b78e53fbfa5ad5681f2d2dc35624b32a0430e9573f98bccd72c1f`.

## Beta 3 integrated preparation and strict soak review

- One main config section loads its bundled preparation macros and namespaced mesh helper. No Auto Trim or older Live Z Mesh install is required. Startup conflicts are rejected before handler replacement.
- Native START_PRINT and _PRINT_CLEAR_NOZZLE handlers are retained; native conditional homing remains the owner of startup homing. Saved native flags prevent duplicate mesh/check/prime paths. Macro control-flow simulation checks one preparation, soak and mesh per startup. This is not a physical end-to-end startup test.
- Cold wipe XYZ/speeds match retained reference/stock_CLEAR_REZINA.cfg; cold extrusion is omitted. Counted hot wipe/probe retracts are restored after reheating. No new geometric compensation transform or force controller is installed.
- Supplied probe.py SampleAveragingHelper.run_probe checks SAMPLES_TOLERANCE using within-group max-minus-min, bounds retries, and uses calc_probe_z_average(..., median). Tests execute those actual source definitions. Five touches with a 0.01 mm range limit prevent an average alone from hiding poor repeatability.
- Calibration clocks use reactor host monotonic time exposed to Jinja, not the ahead-of-motion planner clock. Full unsmoothed per-point windows, minimum elapsed time, observation coverage, residual slope and repeated confirmation gate acceptance. Saved time is actual confirmation time rounded upward. Timeout/measurement failure cannot overwrite a previously accepted result. Save validity is invalidated before field writes and committed last.
- Thermal guards check bed/nozzle current values and targets around each native probe group. Native probe failures stop calibration and turn off idle calibration heaters. A newly started print is not shut down by the calibration cleanup helper.
- The user's supplied 920-second five-point log fails the strict range tests. This is a replay of logged readings, not a new hardware measurement. The source supports these stricter checks; physical repeatability at 0.01 mm is not established.
- AUTO requires method=2, points=5 at the requested integer temperature key. It uses the full saved wait, without warm-start scaling or clipping. A numeric wait/OFF is explicit. The configured probe reference remains unchanged.
- Analysis rejects duplicate session paths/names that could merge references or contaminate holdout, and changed force scale across model runs. Experiment order returns to GOOD and is counterbalanced. Deposited material weight remains a possible confound; no physical mass subtraction is assumed.

See AUDIT.md for the complete scope, validation matrix and unresolved physical checks.

## Beta 4 settling recovery

The supplied probe helper raises the exact message `Probe samples exceed samples_tolerance` after bounded retries. The supplied gcode dispatch sends gcode:command_error before propagating it, which invokes the native probe-session cleanup. Beta 4 catches only this specific recoverable failure, verifies thermal/time guards and keeps measuring. Other errors retain abort behavior. A rejected point is recorded as invalid, never as the previous successful probe position. Invalid rounds reset confirmations and prevent acceptance while inside the proposed window. Early valid drift likewise blocks acceptance until a later full stable window; it does not abort.

Regression tests cover continued point/round scheduling, large early movement that later settles, invalid-window exclusion, timeout with no accepted rounds, previous-result preservation and fatal probe errors. These are offline simulations, not physical proof that a noisy probe will eventually settle.

## Beta 5 popup handling

Soak measurements now use the supplied public start_probe_session/run_probe/pull_probed_results/end_probe_session interface directly, with explicit finally cleanup. This avoids error dispatch for the recognized recoverable sample-spread exception. Other exceptions propagate through the existing cleanup/error path. The source native probing/tolerance algorithm is unchanged. Tests cover cleanup and propagation; physical printer testing remains pending.

## Beta 5.3 correction

# Beta 5.3 — independent soak histories

This release fixes the whole-round data rejection in the beta 5.2 two-speed edition. It does not modify global mesh/homing speeds.

## What changed

Every round retains all five entries, including explicit None for a rejected point. The centre and each corner have an independent rolling history. A failed pair at one location does not remove valid measurements from any other location. All locations are physically rechecked every round; a previously stable location is never locked as permanently good.

Each location needs at least MIN_ROUNDS valid observations spanning WINDOW, a valid measurement in the current round, no gap between valid observations greater than twice INTERVAL, acceptable unsmoothed range and residual trend. An old point cannot substitute for a current failed pair. An isolated rejected observation may be bridged only when these coverage/gap requirements still pass. The anchor at/before the window must be within two intervals of its boundary; very old observations cannot fabricate recent coverage. This is evidence from sampled times, not proof of behavior between observations.

All five locations must pass together for CONFIRM successive rounds before saving. No smoothing or invented readings are added. Sparse data cannot certify stability. Final save time remains the actual confirmation time. Drift/warp metadata use the earliest complete common baseline, so locations are compared against the same observed round; that baseline may be later than the first failed rounds. It is not an extrapolated cold-start displacement.

Per-location status is shown after each round (counts, ranges and number passing). DEEP_CALIBRATION_SOAK_STATUS also shows each point's valid flag, count, span, range, slope and reason. Order: centre, front-left, front-right, rear-right, rear-left. The macro rows variable preserves accepted/invalid point entries in RAM; it is not a durable raw-data file and clears at a new calibration/restart. Console logs remain useful evidence.

MAX now ends normally without an error popup. Timer is cancelled, no calibration is saved, idle heaters turn off, and remaining queued point macros skip new measurements. Genuine probe/temperature/communication faults still abort. Timeout or rejected results preserve the previous saved calibration.

## Probe and mesh settings

Two soak touches: first PROBE_SPEED=2.5 mm/s, second SECOND_PROBE_SPEED=1 mm/s. Native retract distance/lift speed are retained. These are per-command overrides inside the soak helper. Global mesh settings and g28_tenz are unchanged. The supplied recommend plugin sets global probe speed to 2 mm/s and lift speed to 5 mm/s unless overridden elsewhere. The supplied base's 5 mm/s must not be assumed to be the active value when recommend is enabled.

## Install

Abort any running calibration first and wait for it to finish. Replace the complete deep_calibration_development_beta folder in mod_data, rerun its installer and reboot idle. Keep the existing single project include. Both DEEP_CALIBRATION_STATUS version fields should read 0.1.0-beta.5.3. Python and macro files must be updated together.

```sh
sh /usr/data/config/mod_data/deep_calibration_development_beta/install_deep_calibration.sh
```

From a cold bed, with clean nozzle, clear bed and capture stopped:

```gcode
DEEP_CALIBRATION_SOAK_CALIBRATE BED=60 POINTS=5 SAMPLES=2 PROBE_SPEED=2.5 SECOND_PROBE_SPEED=1 REPEAT=0.02 RETRIES=0 STABLE=0.02 INTERVAL=90 WINDOW=600 MIN_SOAK=600 MAX=2700 CONFIRM=2
```

The command explicitly selects 0.02 mm; omitted STABLE/REPEAT defaults remain 0.01 mm. Increasing tolerance is a trial acceptance choice, not a sensor-accuracy improvement. Do not infer a cold-start calibration from a warm FORCE=1 run. These algorithm changes do not guarantee a pass on hardware with inconsistent contact readings.

## Validation and history

173 offline checks pass, including independent histories, alternating failed locations, current-point freshness, long gaps, old anchors, timeout cleanup, two-speed native calls and existing capture/analysis/macro tests. Native source fixtures are retained. No physical beta 5.3 test performed.

The legacy full beta 5 README/HTML is retained for unchanged capture/install concepts. This patch guide supersedes its soak behavior. Earlier-source behavior in SOURCE_AUDIT is historical; the appended beta 5.3 section describes this release. No autonomous Z or flow controller is added.

## Beta 5.4 gradual guard

# Beta 5.4 — gradual cold-start temperature guard

This patch extends beta 5.3's independent per-location histories and two-speed soak probes. It changes the experiment guard, not native heater protection, PID, global probing or the physical sensor settings.

## Gradual guard

TEMP_GRACE=300 begins when the bed first reaches the calibration start temperature window, after nozzle pre-soak and bed heating. BED_BAND_START=3 narrows linearly to BED_BAND_FINAL=1 over those five minutes. At 0 s the collection band is +/-3 C; at 150 s it is +/-2 C; at 300 s and thereafter it is +/-1 C. These are degrees Celsius, separate from STABLE/REPEAT in millimetres. TEMP_GRACE=0 starts with the final band immediately.

Within the collection band, probe measurements can be taken. They are eligible for stability only if the bed was inside the FINAL band and the nozzle inside +/-2 C both before and after the touch group. Warm-up-only results are recorded in raw_rows and printed by the native probe, but have None in eligible rows. This prevents an early overshoot from aborting the experiment while also preventing that overshoot from certifying stability.

Outside the current collection band, probing at that location is skipped and the run continues to the next scheduled recheck. The same recovery applies to normal excursions after grace; the guard is not an automatic heater controller. It preserves heater targets and eventually reaches MAX normally if conditions never become suitable. Every point is still revisited; a currently invalid point cannot use an old result to pass. Only valid observations count toward the full final stability window, per-point observation count/gap limits and repeated confirmations.

Heater target changes still abort and report the actual/expected target. Invalid temperature readings, native heater faults, communication/homing/probe faults remain errors. Native heater safety checks and configured limits are not disabled or relaxed. An initial collection band is a proposed experimental default, not a physically validated overshoot bound for every AD5X.

The thermal_status macro variable and SOAK_STATUS expose the latest actual temperatures, effective band, phase, and collection/eligibility flags. raw_cur/raw_rows retain measured point results, including warm-up-only measurements, in RAM. They clear with a new calibration/restart and are not a durable recording file. Rejected sample pairs are still visible as individual native probe messages; no false median is fabricated for them.

## Install and run

Abort any calibration and wait for it to finish. Replace the complete extracted package folder in mod_data, rerun the installer and reboot while idle. Keep the single include. Both status version fields must show 0.1.0-beta.5.4. Python and cfg files change together.

```sh
sh /usr/data/config/mod_data/deep_calibration_development_beta/install_deep_calibration.sh
```

From a cold bed, with clean nozzle, clear bed and recorder stopped:

```gcode
DEEP_CALIBRATION_SOAK_CALIBRATE BED=60 POINTS=5 SAMPLES=2 PROBE_SPEED=2.5 SECOND_PROBE_SPEED=1 REPEAT=0.02 RETRIES=0 STABLE=0.02 INTERVAL=90 WINDOW=600 MIN_SOAK=600 MAX=2700 CONFIRM=2 TEMP_GRACE=300 BED_BAND_START=3 BED_BAND_FINAL=1
```

The command explicitly selects 0.02 mm; omitted REPEAT/STABLE still default to 0.01 mm. The two different approach speeds remain user-selected and can introduce speed-dependent trigger differences. This guard does not solve contact repeatability or guarantee acceptance. Global mesh/homing speeds remain unchanged.

## Validation

184 offline tests pass, including taper values, warm-up-only retention, no false stability acceptance, before/after temperature checks, excursions after grace, target changes, invalid sensors, timeout handling and all earlier per-point/capture/analysis/macro checks. Source compilation and shell syntax pass. No physical beta 5.4 printer test performed.

The base README and earlier audit sections describe historical versions. This guide and the appended current audit section supersede their thermal guard behavior. Earlier projects/artifacts are preserved.
