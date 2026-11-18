# Beta 10.2.3 validation

Software validation, 18 November 2026. Physical validation pending.

## What changed

1. **Accelerometer overflows** (`deep_calibration_sensors.py`). A single FIFO overflow is an `accel_overflow` event; the batch is written with its overflow count, so the acceleration file marks the gap. More than `accel_overflow_limit` (3) overflows within 60 s, or any data error, end the recording as before. Cause: three first-layer recordings on the AD5X (zMod 1.7.5, 17–18 November) ended about one second in with `native acceleration errors/overflows: 0/1`, two to four load cell readings each, all just after the 10.2.2 poll policy switched to fast polling at first-layer start.
2. **Vibration gate** (`deep_calibration_approach.py`). Around every probe touch, the shaking measured by the LIS2DW (RMS of each axis' deviation from its mean, combined) is compared with `vibration_limit` (150 mm/s2): wait before the touch, redo the touch if it was shaken (the native result appended by `descend_until_trigger` is removed first), keep and mark if still shaken; homing waits but is not redone. Every touch is recorded. Cause: on the zMod 1.7.1 AD5X, eight strict soak calibrations (about 7.5 h) were rejected with the bed settled (trends within ±0.005 mm per 10 min) because probe scatter of 0.004–0.010 mm exceeded the 0.02 mm range rule; the noisiest point moved between runs, and the user found an AD5M printing on the same table.

## Native code checked

From `ghzserg/zmod_klipper` (main): `DescendToEndstopHelper.descend_until_trigger` appends one result per touch to `self.results`; `pull_trigger_positions` collects them. `BatchBulkHelper.add_client` starts the sensor when it has no clients; callbacks returning False are removed; batch rows are `(print_time, x, y, z)`. The recorder removes only its own client on stop, so the gate's listener survives a recording ending.

## Tests

343 passed, 37 subtests (10.2.2: 329). Full list: [tests/BETA10_2_3_VALIDATION.txt](tests/BETA10_2_3_VALIDATION.txt).

- `test_continuous_sensors.py`: one overflow continues with the event, the kept batch and the status count; four within 60 s end the recording; a data error ends it at once (replaces the 10.2.2 test that required one overflow to end it).
- `test_vibration_gate.py` (12), with a simulated accelerometer delivering batches on the printer clock: quiet touch measured once (quiet level 55–85 mm/s2, matching the idle checks); shaking before the touch waits until it settles; shaking during the touch discards that result, goes back up and redoes it; constant shaking keeps the last touch and marks it; homing waits but is not redone; no accelerometer and gate off behave as before; touches logged into a running recording; one listener for many touches, released after 5 s idle, re-attached if dropped; status.

## Not yet verified on a printer

- That the default limit (150 mm/s2) separates a quiet AD5X from one shaken by a neighbouring printer. `DC_APPROACH_STATUS` and the `probe_touch` events give the real levels for tuning.
- Whether the first-layer overflow recurs with fast polling; `poll_accelerate: False` isolates it.
- The extra time per touch: about 0.3 s before, plus the wait for the accelerometer's next batch (up to about 0.5 s).
