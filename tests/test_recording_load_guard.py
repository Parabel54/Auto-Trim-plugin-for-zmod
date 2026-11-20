import unittest

import test_continuous_sensors as sensors
from deep_calibration import RecordingLoadGuard


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
        # Pass isolated timing measurements to the integrated guard. The
        # fixture's synthetic force cadence is intentionally unrelated.
        self.capture.start()

    def pressure(self, times):
        for n in range(times):
            self.guard.due = self.capture.base.reactor.now - .2
            self.cell._update_load_guard(self.capture.base.reactor.now)

    def recover_one_level(self):
        self.guard.work = .005
        self.guard.due = None
        self.cell._update_load_guard(self.capture.base.reactor.now)
        self.capture.base.reactor.now += 6.
        self.cell._update_load_guard(self.capture.base.reactor.now)

    def test_sheds_and_restores_native_acceleration_and_polling(self):
        self.pressure(2)
        self.assertEqual(self.guard.level, 1)
        self.capture.bulk.publish(self.capture.rows(0, 40))
        self.capture.bulk.publish(self.capture.rows(40, 40))
        self.assertEqual(self.cell.sensors.thinned_frames, 40)
        other = lambda msg: True
        self.capture.bulk.add_client(other)
        self.pressure(2)
        self.assertEqual(self.guard.level, 2)
        self.assertEqual(self.capture.bulk.client_cbs, [other])
        self.pressure(2)
        self.assertEqual(self.guard.level, 3)
        self.assertAlmostEqual(self.reader.poll_time, .2)
        self.capture.adc_report()
        self.cell.sensors.tick(self.capture.base.reactor.now)
        self.assertEqual(self.cell.sensors.thinned_adc, 2)
        for expected in (2, 1, 0):
            self.recover_one_level()
            self.assertEqual(self.guard.level, expected)
        self.assertIn(other, self.capture.bulk.client_cbs)
        self.assertIn(self.cell.sensors.callback, self.capture.bulk.client_cbs)
        self.assertAlmostEqual(self.reader.poll_time, .1)
        self.capture.bulk.publish(self.capture.rows(80, 40))
        records = self.capture.end_records()
        levels = [r['level'] for r in records if r.get('event') == 'recording_load_guard']
        self.assertEqual(levels, [1, 2, 3, 2, 1, 0])
        self.assertEqual(len(list(sensors.read_acceleration(self.cell.sensors.writer.paths))), 80)
        self.assertEqual(self.capture.bulk.client_cbs, [other])
        self.assertAlmostEqual(self.reader.poll_time, .2)

    def test_sustained_pressure_stops_only_recording_and_reports_tail(self):
        self.pressure(6)
        self.assertEqual(self.guard.level, 3)
        self.capture.base.reader.extract_last_value_before_g('command H7 ok. 8000000 19 g')
        self.pressure(4)
        self.assertFalse(self.cell.active)
        records = self.capture.end_records()
        end = next(r for r in records if r.get('event') == 'session_end')
        self.assertEqual(end['reason'], 'recording_load_guard')
        self.assertEqual(end['unwritten_force_tail'], 1)
        self.assertEqual(end['load_guard']['level'], 4)

    def test_queue_backpressure_and_hysteresis(self):
        guard = RecordingLoadGuard(True)
        self.assertEqual(guard.update(0., .1, .4), 0)
        self.assertEqual(guard.update(.1, .1, .4), 1)
        guard.level = 1
        self.assertEqual(guard.update(.2, .1, 0.), 1)
        self.assertEqual(guard.update(4., .1, 0.), 1)
        self.assertEqual(guard.update(5.3, .1, 0.), 0)
