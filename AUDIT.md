# Beta 5 review: what works in software and what remains unmeasured

This review targets the supplied **AD5X / zMod 1.7.5 / Klipper 13** implementation. It does not certify Forge-X, Kiln, another printer, or every future zMod update. Uploaded scripts and chat exports were read as reference material. No firmware installer or printer command was executed against your printer during this review.

## Corrections made

| Finding | Result in beta 5 | Evidence |
|---|---|---|
| Old smoothing could make a moving bed look settled, and report an earlier time | Check unsmoothed round results at every point; save actual confirmation time | Replay of your 920-second log is rejected; constant synthetic data saves the later confirmation time |
| Averages could conceal inconsistent individual probes | Native five-touch median, 0.01 mm max-minus-min tolerance and bounded retries | Tests execute the supplied Klipper probe helper itself |
| Planner time is ahead of physical execution | Use host monotonic elapsed time for calibration and cleaning credit | Clock-separation regression test; native Jinja status clock interface checked |
| One fortunate observation could end calibration | Full 600 s window, minimum 600 s soak, coverage/gap checks, residual trend limit, two successive passes | Trend, outlier, missing/reversed time and confirmation-reset simulations |
| Old 55/560 s estimates could be reused as trusted calibration | AUTO requires a strict five-point result for the requested whole-degree temperature | Legacy/missing calibration fails before startup actions |
| Warm bed readings could shorten an unverified wait | AUTO retains full verified time; cleaning credit remains; no silent clipping | Warm-start and credited-wait simulations |
| A failure could leave misleading accepted data | Fatal probe/thermal failure and timeout preserve prior results; sample-spread rejection continues measurement; heaters off on idle failure; save validity committed last | Cleanup, timeout, print-interruption and save-order checks |
| Removed older installs left missing preparation features | Bundle cooling wipes, credited soak, fresh mesh and diagnostics under one include | Integrated-module registration and macro simulations |
| Duplicate startup paths | Native START_PRINT owns conditional homing; pre-clean deferred; native flags gate duplicate mesh/check/prime paths | Source inspection plus cold/warm startup call-count simulation |
| Duplicate capture inputs could leak between training and validation | Reject duplicate paths and colliding session filenames | Offline analysis regression tests |
| Different force scales could be combined | Reject inconsistent counts-per-gram metadata within a candidate model | Cross-run scale-change regression test |
| Always improving the gap later could confuse time/material weight with gap | Repeat GOOD sections, vary order between repeats, keep GOOD offset fixed | Updated experiment CSV and operator instructions; this reduces a confound, not proves its elimination |
| Incomplete installation or conflicting Python files | Link all three modules; preflight both supported roots before writes; preserve regular-file conflicts | Actual shell installer executed with only filesystem roots redirected to temporary directories |

## Capability check against supplied source

| Component | Exposed data/control | Boundary |
|---|---|---|
| Native zmod_tenz load-cell interface | Each background H7 signed raw reply plus coarse grams, native command generation and receipt time | Roughly 4 Hz; no exposed high-rate force stream or proven ADC acquisition timestamp |
| LIS2DW | Native continuous 1600 Hz mapped/scaled XYZ batches | Floats after driver conversion, not original integer ADC words; SPI reliability under a long print still needs measurement |
| MCU ADC | Every configured callback report, including temperature-related ADC channels | Normalized/aggregated reports; not every underlying hardware conversion |
| Motion report/trap queues | Requested motion at the MCU clock corresponding to receipt time | No bed encoder; unknown force ADC/serial delay remains |
| Bed mesh | Active transform, interpolation, fade, endpoint coherence and commanded Z counts | Confirms software commands, not physical bed displacement |
| Probe | Native repeated contact probing with median and tolerance retries | Does not directly measure nozzle gap during extrusion; achievable repeatability depends on hardware |
| Fans | Requested speeds and RPM where a tachometer exists | Cannot invent missing physical airflow measurements |
| Input shaper | Frequency/type/damping settings, plus acquired acceleration | Settings alone do not supply a vibration-to-force transfer function |
| Native saved variables | Persistent accepted soak result and validity metadata | Multiple native writes are not a filesystem transaction; validity is committed last to reject partial results |

The previous A-B-A field log already showed a predicted 0.408583 mm change and 163 commanded steps (0.407500 mm). That supports an active mesh command path. It does not justify amplifying the mesh or adding flow changes. No extra compensation transform is added here.

The native probe reference, including the supplied -0.25 mm value, remains unchanged. Removing it during these experiments would change the measurement reference and invalidate comparisons.

## Resource and continuity check

Acquisition uses bounded queues; acceleration files rotate without restarting the sensor subscription. Disk packing and writes run in background workers. Native temperature/safety callbacks run unchanged before their observers, and their exceptions propagate. Removing this observer preserves other native consumers.

At 1600 XYZ frames/s and 32 bytes/frame, acceleration payload alone is approximately **184 MB per hour**. Default budgets are 512 MiB acceleration, 256 MiB JSONL and a 64 MiB free-storage reserve. Budgets limit files, not allocated RAM. Queue overflow, sensor staleness, timestamp/gap errors and disk failures mark recording incomplete instead of silently training on it. Final pending force/ADC reports are drained at normal stop. Native accelerometer start/stop buffering defines the available capture boundaries.

Your approximately 474 MiB RAM / 370 MiB available and 4.6 GB available storage snapshots do not rule out this design. They do not establish CPU headroom, SPI stability or real-time print performance. Callback timing and delivered counts are recorded so those can be evaluated. No stress-test result is invented from idle free memory.

## Validation performed

- **160 offline automated checks**: native parser/probe/bulk/ADC source definitions, macro rendering/control flow, mesh math and native split-move behavior, installer filesystem handling, queues/storage/failures and offline statistical analysis.
- Python compilation and shell syntax checks.
- Command-line analysis and acceleration export using synthetic capture data.
- Installation ZIP integrity, extraction and a test run from the extracted package; README HTML links checked.

The fixtures simulate clocks, transport, motion and heaters. They are not physical printer tests or a complete installed-firmware startup execution. The full test output is in tests/VALIDATION.txt. Supplied-source provenance/hashes are in SOURCE_AUDIT.md.

## Still needs a printer run

1. Confirm the installed firmware exposes the checked interfaces and the idle continuous capture completes without missing/error counters.
2. Run strict soak calibration from cold with a clean nozzle and clear bed. Early probe-spread rejections now keep measuring. Persistent variation may still reach MAX without acceptance; do not save a false result.
3. Confirm one real startup, cooling cycle, credited soak and mesh, with the requested print temperature before extrusion.
4. Compare a representative print with streams enabled/disabled, inspecting timing, sensor errors and print quality. Observe physical Z travel separately from software counts.
5. Collect labelled, counterbalanced repeat prints before judging a formula. Held-out error is retrospective evidence only; GOOD labels, force references and deposited-material weight remain limitations.

This is a data-acquisition and experiment package. It does not yet provide validated autonomous nozzle-gap calibration, force-based Z correction, exact vibration subtraction or a high-rate force sensor. Those require evidence from the collected data, not an enabling switch.

## Beta 5 follow-up

The first physical beta 3 soak log exposed an overly strict abort policy: X30/Y30 exhausted the 0.01 mm within-point repeatability retries during the first round. That is distinct from comparing all readings to the initial height. Beta 5 permits early movement and recovers this specific sample-spread failure by rejecting the round and measuring again. It requires a later full clean stable window before saving. The threshold has not been widened. Other failures remain fatal. New simulations verify this behavior; no beta 5 printer run has been performed.
