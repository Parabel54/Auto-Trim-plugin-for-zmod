# 0.1.0-beta.10.1 — current continuation (2026-11-14)

Official continuation of the existing Deep Calibration beta, superseding beta 9. Beta 10 was an intermediate local checkpoint; beta 10.1 is the current working baseline. Published as the continuation on the GitHub `beta` branch.

- Temporarily use zero post-reading pause during captures when the patched native driver supports it; preserve WAIT and restore the previous pause on exit/failure.
- Key learned margins by material, layer height, line width, print speed, filament diameter and nominal volumetric flow. Equal-flow recipes with different dimensions stay separate. Legacy entries remain saved but are not reused automatically.
- Require explicit or learned margins for new recipes by default; withdraw the universal 0.125 mm claim.
- Select the descending knee fit; retain ascending fit and hysteresis as diagnostics with longer upward settling/holds.
- Permit shorter downward holds only with sufficient observed sample rate and precision. Reject invalid margins and recipe/override changes during search.
- Retain recorder, labels, continuous acquisition, relabel analysis, guarded probing and soak tools. No bundled Auto Trim or new tuning pattern.
- 264 software tests plus 28 subtests passed, including the extracted runtime package. Hardware validation remains pending. Publication also updates the mesh status and start-config version labels; probe behavior is unchanged.

# 0.1.0-beta.8

- Knee search, more precise:
  - Fitted knee: a flat-then-rising line is fitted through all the steps, so the knee is found between steps (to 0.0005 mm), not only on the first step over the threshold. On the real 0.2 mm search: -0.136 instead of -0.150, the same whichever step passed the threshold.
  - Threshold from the noise: once four flat steps exist, the rise needed is 4 times their step-to-step noise (`knee_noise_k`), measured from differences between neighbouring steps so drift does not count, and at least 6 g (`knee_rise_min_g`). On the real 0.2 mm search, a 13 g recovery from a dip is no longer a candidate.
  - Adaptive hold: each step lasts at least 6 s (`knee_hold`), then ends when its median is within 2 g (`knee_se_g`), or at 20 s (`knee_hold_max`).
  - Confirmation from both directions (`knee_confirm`, `CONFIRM=`): after the knee going down, the search steps back up until the force is flat again, and reports the difference between the two sides as the repeatability (a warning above two steps).
  - Steps record whether they were a candidate or confirmed it, their precision, the noise and the rise needed.
- Learned margin: after a search, a babystep during the same first layer teaches the margin above the knee for that filament and first-layer height (`knee_margins.json` beside the recordings; `knee_learn_rate`). `DEEP_CALIBRATION_KNEE_MARGIN` shows, sets, adjusts or resets them; `MARGIN=` on the search line is used once and not learned.

# 0.1.0-beta.7

- Knee search, `DEEP_CALIBRATION_KNEE` (`ARM=1` on the start G-code): during the first layer, the nozzle is lowered in 0.01 mm steps from 0.10 mm above Auto Trim's offset until the median load cell force rises steeply (12 g above the recent level, confirmed by the next step), then set 0.025 mm above that point; Auto Trim learns it. Compared step to step, so slow load cell drift does not matter; a single high step is ignored. Stops at once at 80 g above the recent level, never goes more than 0.35 mm down, and puts the offset back when no knee is found, the first layer ends first, or on `DEEP_CALIBRATION_KNEE_ABORT`. Its steps are recorded as `knee_step` and `knee_result` events, not as babystep labels. The rest of Deep Calibration still does not change the print.
- The README is rewritten as one complete guide (installation, slicer setup, recording, labels, knee search, guarded approach, strict soak, analysis, commands and settings). `PATCH_README.md`, `QUICK_START.md` and the outdated `README.html` are removed.

# 0.1.0-beta.6.1

- A gap or an irregular report on a temperature channel (toolhead, filament, cutter, bed, extruder) no longer stops the capture. A single late report of the toolhead sensor (`ADC report gap detected: temperature_sensor head`) ended a first-layer recording after three minutes. Gaps are recorded as `adc_gap` events, irregular reports are skipped and recorded (`adc_report_skipped`), and a channel silent for 2 s is recorded as `adc_channel_lost` (and `adc_channel_resumed` when it reports again). The load cell and the accelerometer stay strict, and a failure to write the log still stops the capture.

# 0.1.0-beta.6

- Works with the official Auto Trim (3.9.9 or later) instead of a bundled copy. The bundled Auto Trim 3.9.6 is removed: it set Z homing and all probing to 1 mm/s from inside its config. Auto Trim 3.9.9 probes meshes, KAMP and its own checks at 1 mm/s without changing endstop homing, uses the strict soak calibration of this package for `SOAK=AUTO` (slowest of the five points), and still accepts `DC_SOAK=` and `DC_MESH=`.
- First print test without console input: `DEEP_CALIBRATION_ARM` on the start G-code takes the recipe from the slicer. Recording starts with the first layer (after Auto Trim has finished preparing), babysteps label the previous offset too high or too close, and when the second layer starts the offset kept is labelled GOOD (inferred, unless labelled by hand) and recording stops. `DEEP_CALIBRATION_DISARM`; `auto_capture` and `auto_stop_layer` in `[deep_calibration]`.
- The analyser uses the automatic GOOD label, and treats the automatic stop as a complete session.
- Physical timing: the first-layer start, the automatic stop and every babystep label are placed when they happen at the nozzle, using the time Klipper's queued moves run ahead of it. Recording no longer stops before the queued end of layer 1 has printed.
- The installer no longer requires the bundled Auto Trim. The beta 5.8 guarded approach is kept unchanged.

# 0.1.0-beta.5.8

- Restore the beta 5.5 guarded approach helper in the full development build: monitored 5 mm/s to 1 mm above a recent reference, 1 mm/s native measuring contacts. Unknown-height probing and Z homing remain entirely 1 mm/s.
- Add approach state/counters to recording contexts and DEEP_CALIBRATION_STATUS; retain DC_APPROACH_STATUS/RESET.
- Installer links the fourth module; no change to the standalone config-only GitHub Auto Trim release.
- Preserve all beta 5.7 recorder/labels and beta 5.6 Auto Trim integration. No pattern generator. Hardware validation pending.

# 0.1.0-beta.5.7

- Observe first-layer relative Z babysteps during recording. Infer TOO_HIGH/TOO_LOW for the preceding offset interval; reset the new setting to UNLABELLED. Ignore absolute startup/cleanup offsets, idle/paused adjustments and later layers.
- Preserve native commands/errors; no automatic motion. Add clickable DC_MARK_GOOD for explicit visual confirmation.
- Export retrospective inferred labels with source/flag; preserve explicit labels and all data-validity filters.
- 192 offline tests plus 16 integration check groups pass; hardware validation pending.

# 0.1.0-beta.5.6

- Bundle Auto Trim 3.9.6 with retained knocking and gentle wipes. Disable Deep Calibration startup takeover, preserving recording and calibration tools.
- Default to saved auto mesh; add conservative saved-soak wait before Auto Trim mesh/checks, optional DC_SOAK=OFF/seconds.
- Retain cold soak + 230/60 9x9 auto mesh command, no tuning pattern. Default calibration touches to 1 mm/s.
- 184 software tests and 16 integration check groups pass. Physical combined-build validation pending.

# 0.1.0-beta.5.4

- Add TEMP_GRACE=300, BED_BAND_START=3 and BED_BAND_FINAL=1: linearly narrowing cold-start collection band. Warm-up-only measurements retained separately, never certified as final-band stability.
- Normal thermal excursions wait/recheck instead of aborting, including after grace; MAX still limits the run. Target changes and genuine faults still abort. Native heater protections unchanged.
- Expose actual temperature/band/phase state and retain raw point rows in RAM. Preserve independent histories and two-speed probing.
- 184 offline checks pass; physical beta 5.4 test pending.

# 0.1.0-beta.5.3

- Keep valid readings independently for every soak location; retain invalid point entries explicitly. Recheck all locations and require all to pass together over bounded recent windows with sufficient observations, current valid points and two confirmations.
- Expose per-location evidence; reject old anchors and excessive valid-observation gaps. Use a common observed baseline for saved drift/warp metadata.
- Handle expected MAX without an error popup and skip remaining measurements after expiry. Preserve previous accepted calibration.
- Retain two-touch 2.5/1 mm/s soak speeds and global probe settings unchanged. 173 offline checks; no physical beta 5.3 test.

# 0.1.0-beta.5.2

- Two-touch soak defaults: first PROBE_SPEED=2.5 mm/s, second SECOND_PROBE_SPEED=1 mm/s. Native single-touch sessions with explicit retract and cleanup. Global homing/mesh configuration unchanged.
- Add speed validation, default/override tests, distinct approach-speed checks and unchanged native retract/lift checks. 166 offline checks; physical validation pending.

# 0.1.0-beta.5.1

- Minimal beta 5 patch: permit two touches and default SAMPLES to 2. Both must agree; no MATCHES parameter. Native median of two is midpoint. Preserve all beta 5 continuation/window/error-handling behavior.
- See PATCH_README.md for installation and command. Offline validation only.

# 0.1.0-beta.5

- Use native probe sessions directly for soak measurements, closing them explicitly in finally. Expected sample-spread rejection stays a normal informational message instead of passing through the G-code error dispatcher and generating a popup. Other faults still abort.
- Keep beta 4 continuation/window rules. 160 offline checks pass; no beta 5 physical test.

# 0.1.0-beta.4

- Correct soak calibration's early termination: native sample-spread failures reject a round and continue measurement instead of ending the entire settling experiment. Keep REPEAT and final STABLE at 0.01 mm.
- Mark failed points invalid rather than reading a stale previous probe result. Retain rejected-round timestamps/point validity and reset confirmations. No rejected round may lie inside an accepted observation window.
- Continue to MAX if repeatability never settles. Preserve previous accepted results on timeout. Other probe, thermal, homing and communication faults remain fatal.
- Add regression simulations for large early drift followed by stability, a rejected point with remaining point measurements, clean-window recovery, persistent rejection timeout and nonrecoverable faults.
- 157 offline checks pass. No beta 4 physical printer test performed.

# 0.1.0-beta.3

- Bundle the reviewed AD5X cooling-wipe, heat-soak calibration and mesh-preparation adapter into the Deep Calibration package; no separate Live Z Mesh installation is required.
- Add an internal namespaced mesh helper and DEEP_CALIBRATION_MESH_* status, trace and explicit travel-test commands while keeping capture commands distinct.
- Enable startup integration through the one project cfg. Preserve native START_PRINT/conditional homing, defer native pre-clean and require saved flags that avoid duplicate native leveling/check/prime paths.
- Retain one custom cooling cycle, one credited soak and one FULL/KAMP mesh build. Restore print temperature and counted hot-wipe/probe retractions; avoid cold extrusion.
- Replace retrospective smoothed soak estimates with strict five-point calibration: 90 s interval, unsmoothed 0.01 mm range, full 600 s window/minimum soak, 0.001 mm/min trend, five-touch native median/repeatability checks and two confirmations; MAX 2700 s. Save actual confirmation time, not an inferred earlier settling time.
- Reject legacy/centre-only calibration for AUTO; retain the full verified wait with eligible cleaning-time credit and no warm-start reduction or clipping. Turn heaters off before saving and commit strict validity last. Native failures/timeouts preserve earlier accepted results.
- Replay the supplied unstable 920 s field sequence and verify rejection. Guard temperature drift, print interruption and failed repeatability.
- Reject duplicate input paths/filenames and inconsistent force scales in analysis. Counterbalance repeat offset trials to expose drift and deposited-material-weight confounding.
- Guard old startup conflicts, duplicate preparation, active calibration/capture and invalid soak parameters. Preserve native probe/global-offset behavior; no force-based controller or automatic offset learning.
- Update fresh-install, single-include and slicer instructions, with a separate quick-start guide. Development macro checks require Jinja2; offline analysis remains standard-library-only.
- 151 software checks pass; no physical printer preparation or timing test performed.

# 0.1.0-beta.2

- Rewrite the README as a numbered plain-language operator/coworker guide, with command locations, examples, parameter/configuration tables, troubleshooting and a self-contained browser/print copy.

- Add continuous LIS2DW acquisition and native ADC report observers for the full recording session; no burst/pause cycle.
- Keep a single native acceleration subscription across bounded background binary file rotation. Preserve other consumers and original ADC temperature/safety callbacks.
- Record exposed mapped/scaled XYZ as timestamped float64 batches with native error/overflow fields; retain normalized aggregated ADC reports without extra hardware polls.
- Add explicit Klipper-13 batch / legacy scalar ADC adapters, source-stale/gap checks, queue/file/disk limits, callback timing and final force/ADC drains.
- Preserve overload raw force replies with quality flags instead of silently discarding them; exclude them from calibration fitting.
- Stream post-print acceleration validation, force-interval RMS/peak/shaper-tone features and optional CSV export. Compare vibration-augmented and baseline fits on the same segments and held-out run.
- Default ACCEL=1 ADC=1; allow explicitly disabled-stream comparison runs. Update installer to link both Python modules.
- Preserve probe reference, native motion/flow, homing, wipes, soak and collision protection. No physical timing/print validation performed.

# 0.1.0-beta.1

- Create separate Deep Calibration Development Beta extra for AD5X/zMod.
- Observe each native signed raw H7 reply without taking over serial polling, collision protection or other load-cell observers.
- Record receipt timestamps, native requested motion at that clock, labelled cache fallback, coherent planned mesh diagnostics and commanded Z counts.
- Capture offset changes, fan commands/RPM, print recipe/layers, temperatures, input-shaper settings and native probe reference.
- Preserve raw readings; add causal median/EMA filtering, measured source-rate/Nyquist reporting, software zero validity and explicit transition labels.
- Add bounded asynchronous JSONL recording, incomplete-file detection, per-install printer identity and metadata-only recipe commands.
- Add offline CSV/segment analysis, paired GOOD-reference targets, experimental per-printer/material ridge fits with whole-run holdout, and observed material-offset tables.
- Include one-factor experiment plan and 205/215 mm square STL coupons, both 2 mm thick.
- Preserve -0.25 probe reference and existing startup/wipe/soak/motion/flow behavior. No automatic corrections or physical printer validation in beta 1.
