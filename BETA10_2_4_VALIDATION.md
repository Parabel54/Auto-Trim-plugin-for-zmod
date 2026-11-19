# Beta 10.2.4 validation

Software validation, 19 November 2026. Physical validation pending.

## Evidence for the change

A 10.2.3 print on the AD5X (zMod 1.7.5, `console_4.log`, `printer_4_1.log`) shut down with `MCU 'mcu' shutdown: Timer too close` at 13:39:09, three seconds after Deep Calibration armed and the first layer began. From `LIS2DW starting measurements` and the recording start to the shutdown, the reactor stall reports were 0.109 s (`_tick` alone), 0.139, 0.103 (`_tick` alone), 0.464, 0.379, 0.144 and 0.122 s. The garbage collector's last full pass was 260 s before (no deferrals). The G-code context parse starts at arming in a background thread; on the print's 4.4 MB file (96,731 lines, 16,292 segments) `parse_file` takes 3.84 s CPU on a 2.1 GHz Xeon core and keeps 24 MB, and through the GIL it shares the processor with the reactor.

The same print's KAMP mesh (81 points) took 63 minutes with `vibration_limit` 150: 248 waits (shaking 150–357, median 167), 75 redos (151–173) and 22 touches kept and marked (143–166). At 250 the replay gives 16 waits and no redo; the user chose 400.

## Tests

367 passed, 37 subtests (10.2.3: 343). Full list: [tests/BETA10_2_4_VALIDATION.txt](tests/BETA10_2_4_VALIDATION.txt).

`test_context_start.py` (11): soak is the default and the console listener attaches once; Auto Trim's soak announcement reads the file before arming and reports the read time; arming after the soak, or while the read is still loading, does not read again; no soak wait means no read, the state is `skipped` and it is said once; a soak already covered by the nozzle clean is not a wait; a previous print's snapshot is never reused; `arm` keeps the 10.2.2 behaviour; the soak message is ignored with `arm` or the context off; status reports the policy; the vibration default is 400.

`test_shape_mesh.py` (13), with Klipper's own `ZMesh` (zMod `bed_mesh.py`, unchanged) and the outline of a real diagonal part: the grid matches KAMP's for the same print (within KAMP's 3 mm point fuzzing); 48 of 81 points probed, all within one grid spacing of the part; with the bed shifted and tilted since the saved mesh, the shape mesh under the part is as accurate as probing all 81 points (largest error 0.0049 mm against 0.0056 mm); probed values enter the matrix unchanged in Klipper's order; without a saved mesh the rest is filled within the probed range; a saved mesh off under the part is reported, ordinary probe scatter (0.008 mm) is not; probe speed reaches the probe; serpentine order; a small part gets a 3 x 3 grid with lagrange; no outlines and a zero reference are refused; plane fit. `test_installer.py` links the module with the others; the bundling guard allows `[auto_trim_shape_mesh]` and no other Auto Trim section or macro.

## Not yet verified on a printer

- The read time on the printer (now reported) against the soak length.
- A `MESH=SHAPE` mesh on the printer (Klipper's probing helper with the real probe and Deep Calibration's guarded approach).
- That the first layer then runs without reactor stalls; if stalls remain without the parse, the next suspect is the work in `_tick` itself.
