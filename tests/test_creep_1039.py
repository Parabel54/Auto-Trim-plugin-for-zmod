# 10.3.9: the load cell's own creep after a tare is subtracted from the force.
import math
import os
import unittest
import test_zero_and_time as zero_fixture
from test_capture import Command

HERE = os.path.dirname(os.path.abspath(__file__))


class CreepTests(unittest.TestCase):
    def setUp(self):
        self.z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); self.z.setUp(); self.addCleanup(self.z.doCleanups)
        self.c = self.z.c
        self.c.creep_recovery, self.c.creep_tau, self.c.creep_rate = 14.9, .5, .81

    def tare(self):
        self.z.f.reader._command_id += 1

    def test_tare_before_the_recording_is_dated_and_used(self):
        self.z.f.feed()
        self.tare(); self.z.run_readings(1, 8000000, z=1.0, ev=0.)
        tare_t = self.c.tare_t
        self.z.run_readings(40, 8000000, z=1.0, ev=0., step=1.5)          # a minute of preparation, no recording
        self.assertEqual(self.c.tare_t, tare_t)                               # not re-dated by later readings
        self.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.)
        self.z.run_readings(12, 8000526, z=.2, ev=1.)
        records, samples, events = self.z.log()
        last = samples[-1]
        zero_t = [e for e in events if e['event'] == 'baseline'][0]['baseline']['t']
        expected = (self.c._creep_model((last['t'] - tare_t) / 60.) - self.c._creep_model((zero_t - tare_t) / 60.))
        self.assertAlmostEqual(last['creep_correction_g'], expected, places=6)
        self.assertAlmostEqual(last['filtered_grams_creep_corrected'], last['filtered_grams'] - expected, places=6)
        self.assertAlmostEqual(last['time_since_tare_s'], last['t'] - tare_t, places=6)

    def test_model_shape(self):
        m = self.c._creep_model
        self.assertAlmostEqual(m(0.), 0.)
        self.assertAlmostEqual(m(1.), 14.9 * (1 - math.exp(-2)) + .81, places=9)
        self.assertGreater(m(25.), m(10.))

    def test_new_tare_restarts_the_clock(self):
        self.z.f.feed(); first = self.c.tare_t
        self.z.run_readings(4, 8000000, z=1.0, ev=0., step=1.)
        self.tare(); self.z.run_readings(1, 8000000, z=1.0, ev=0.)
        self.assertGreater(self.c.tare_t, first)

    def test_off_when_not_set(self):
        self.c.creep_recovery = self.c.creep_rate = 0.
        self.z.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.)
        self.z.run_readings(4, 8000526, z=.2, ev=1.)
        last = self.z.log()[1][-1]
        self.assertIsNotNone(last['filtered_grams'])
        self.assertIsNone(last['creep_correction_g']); self.assertIsNone(last['filtered_grams_creep_corrected'])

    def test_shipped_config_values(self):
        text = open(os.path.join(HERE, '..', 'deep_calibration.cfg')).read()
        values = {}
        section = None
        for line in text.splitlines():
            if line.startswith('['): section = line.strip()
            elif section == '[deep_calibration]' and ':' in line and not line.startswith(('#', ' ')):
                k, v = line.split(':', 1); values[k.strip()] = v.strip()
        self.assertEqual((float(values['creep_recovery_g']), float(values['creep_tau']), float(values['creep_rate'])), (14.9, .5, .81))


if __name__ == '__main__':
    unittest.main()
