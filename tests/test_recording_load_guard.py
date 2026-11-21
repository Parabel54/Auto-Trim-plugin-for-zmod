# 10.3.1: the load guard records less, one level at a time; it never stops a
# stream, never stops the knee search and never ends the recording.
import json
import struct
import unittest

import test_continuous_sensors as sensors
from deep_calibration import RecordingLoadGuard, GUARD_MAX_LEVEL
import deep_calibration_sensors as dcs


class LoadGuardTests(unittest.TestCase):
    def setUp(self):
        self.capture = sensors.ContinuousTests()
        self.capture.setUp()
        self.addCleanup(self.capture.doCleanups)
        self.cell = self.capture.cell
        self.guard = self.cell.load_guard
        self.guard.enabled = True
        self.cell.poll_accelerate = True
        reader = self.capture.base.reader
        reader.cmd_LOAD_CELL_POLL = lambda cmd: None
        reader.poll_time, reader.poll_wait = .2, .05
        self.reader = reader
        self.capture.start()

    def pressure(self, times):
        for n in range(times):
            self.guard.due = self.capture.base.reactor.now - 2.
            self.cell._update_load_guard(self.capture.base.reactor.now)

    def recover_one_level(self):
        self.guard.work = .005
        self.guard.due = None
        self.cell._update_load_guard(self.capture.base.reactor.now)
        self.capture.base.reactor.now += 6.
        self.cell._update_load_guard(self.capture.base.reactor.now)

    def to_level(self, level):
        for _ in range(60):
            if self.guard.level >= level:
                return
            self.pressure(1)
        self.fail('guard did not reach level %d (at %d)' % (level, self.guard.level))

    def test_acceleration_is_thinned_not_dropped_or_detached(self):
        self.to_level(2)
        self.assertEqual(self.guard.level, 2)
        self.assertIn(self.cell.sensors.callback, self.capture.bulk.client_cbs)     # still attached
        self.capture.bulk.publish(self.capture.rows(0, 40))
        self.capture.bulk.publish(self.capture.rows(40, 40))
        self.assertEqual(self.cell.sensors.thinned_frames, 40)                      # every 2nd of 80
        self.to_level(4)
        self.capture.bulk.publish(self.capture.rows(80, 40))                       # every 4th: 10 kept
        self.assertEqual(self.cell.sensors.thinned_frames, 70)
        self.assertTrue(self.cell.active)
        records = self.capture.end_records()
        frames = list(dcs.read_acceleration(self.cell.sensors.writer.paths))
        self.assertEqual(len(frames), 50)
        self.assertEqual({f['thinning'] for f in frames}, {2, 4})
        end = next(r for r in records if r.get('event') == 'session_end')
        self.assertEqual(end['sensor_capture']['acceleration_suspensions'], 0)

    def test_level_five_slows_the_load_cell_and_thins_adc_but_keeps_recording(self):
        self.assertAlmostEqual(self.reader.poll_time, .1)
        self.to_level(5)
        self.assertAlmostEqual(self.reader.poll_time, .2)                           # the driver's own pace
        self.capture.adc_report()
        self.capture.adc_report()
        self.cell.sensors.tick(self.capture.base.reactor.now)
        self.assertGreaterEqual(self.cell.sensors.thinned_adc, 1)
        self.assertTrue(self.cell.active)
        self.assertIn(self.cell.sensors.callback, self.capture.bulk.client_cbs)

    def test_sustained_pressure_stays_at_the_last_level_and_never_ends(self):
        self.pressure(40)
        self.assertEqual(self.guard.level, GUARD_MAX_LEVEL)
        self.assertTrue(self.cell.active)
        self.assertEqual(self.cell._tick_interval(), 1.)
        self.capture.bulk.publish(self.capture.rows(0, 40))
        self.assertEqual(self.cell.sensors.thinned_frames, 35)                     # every 8th kept
        records = self.capture.end_records()
        end = next(r for r in records if r.get('event') == 'session_end')
        self.assertNotEqual(end['reason'], 'recording_load_guard')

    def test_recovers_one_level_at_a_time_back_to_full(self):
        self.to_level(6)
        for expected in (5, 4, 3, 2, 1, 0):
            self.recover_one_level()
            self.assertEqual(self.guard.level, expected)
        self.assertAlmostEqual(self.reader.poll_time, .1)                           # recording pace again
        self.assertEqual(self.cell._tick_interval(), self.cell.interval)
        self.capture.bulk.publish(self.capture.rows(0, 40))
        records = self.capture.end_records()
        levels = [r['level'] for r in records if r.get('event') == 'recording_load_guard']
        self.assertEqual(levels, [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1, 0])
        self.assertAlmostEqual(self.reader.poll_time, .2)                           # restored after recording

    def test_knee_search_is_not_stopped_by_load(self):
        self.cell.knee = dict(phase='down', cfg=dict(self.cell.knee_cfg), readings=[], window=[0, 1], ref=None)
        self.to_level(6)
        self.assertIsNotNone(self.cell.knee)

    def test_hysteresis(self):
        guard = RecordingLoadGuard(True)
        self.assertEqual(guard.update(0., .1, .4), 0)
        self.assertEqual(guard.update(.1, .1, .4), 1)
        guard.level = 1
        self.assertEqual(guard.update(.2, .1, 0.), 1)
        self.assertEqual(guard.update(4., .1, 0.), 1)
        self.assertEqual(guard.update(5.3, .1, 0.), 0)
        guard.level = GUARD_MAX_LEVEL
        for _ in range(10):
            guard.update(6., .1, .9)
        self.assertEqual(guard.level, GUARD_MAX_LEVEL)


class GuardDutyTests(unittest.TestCase):
    # 10.3.3, from a real AD5X recording: tick work 0.05-0.09 s at every
    # interval, Klipper never behind (lag under 0.03 s)
    def run_ticks(self, works, start_level=0):
        g = RecordingLoadGuard(True); g.level = start_level; now = 0.
        intervals = (.1, .2, .2, .5, .5, .5, 1.)
        for w in works:
            interval = intervals[g.level]; lower = intervals[max(0, g.level - 1)]
            now += interval; g.due = now; g.work = w
            g.level = g.update(now + .001, interval, 0., lower)
        return g.level
    def test_heavy_tick_at_the_shortest_interval_takes_one_step(self):
        self.assertEqual(self.run_ticks([.077, .077]), 1)
    def test_same_work_at_level_one_stays_there_instead_of_climbing(self):
        self.assertEqual(self.run_ticks([.077, .077] + [.05, .09, .06, .08] * 60), 1)
    def test_no_bouncing_back_to_a_level_that_would_overload(self):
        self.assertEqual(self.run_ticks([.06] * 200, start_level=1), 1)
    def test_light_work_recovers_to_full(self):
        self.assertEqual(self.run_ticks([.005] * 300, start_level=6), 0)
    def test_real_lag_still_escalates(self):
        g = RecordingLoadGuard(True); levels = []
        for n in range(2):
            g.due = n * .5; g.work = .01
            levels.append(g.update(n * .5 + .4, .1, 0., .1))   # 0.4 s late, light work
        self.assertEqual(levels, [0, 1])


class AccelerationFormatTests(unittest.TestCase):
    def test_older_files_without_thinning_still_read(self):
        import tempfile, os
        d = tempfile.mkdtemp(); path = os.path.join(d, 'old.accel.0000.dca')
        header = json.dumps(dict(session='s', part=0, format='<dddd', batch_format='<IdII')).encode()
        with open(path, 'wb') as f:
            f.write(dcs.MAGIC + struct.pack('<I', len(header)) + header)
            f.write(dcs.BATCH.pack(2, 1., 0, 0)); f.write(dcs.FRAME.pack(1., 1., 2., 3.)); f.write(dcs.FRAME.pack(2., 1., 2., 3.))
        rows = list(dcs.read_acceleration([path]))
        self.assertEqual(len(rows), 2); self.assertEqual({r['thinning'] for r in rows}, {1})


if __name__ == '__main__':
    unittest.main()
