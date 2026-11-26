# 10.3.9/10.3.10: the load cell's own creep while the printer warms up,
# counted from when the bed reached its temperature, is subtracted.
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
        self.c.creep_recovery, self.c.creep_tau, self.c.creep_rate, self.c.creep_slow_tau = 14.9, .5, .81, 120.
        self.bed = self.z.f.objects['heater_bed'].status

    def heat_up(self):
        self.bed.update(temperature=25., target=60.); self.z.f.feed()
        self.bed.update(temperature=60.); self.z.f.feed()

    def tare(self):
        self.z.f.reader._command_id += 1

    def test_bed_warm_moment_seen_from_cold(self):
        self.bed.update(temperature=25., target=60.); self.z.f.feed()
        self.assertIsNone(self.c.bed_warm_t)
        self.bed.update(temperature=59.5); self.z.f.feed()
        self.assertIsNotNone(self.c.bed_warm_t)

    def test_bed_already_hot_when_first_seen_means_no_correction(self):
        self.z.f.feed()                                                   # fixture bed: 60 of 60 from the start
        self.assertIsNone(self.c.bed_warm_t)
        self.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.); self.z.run_readings(4, 8000526, z=.2, ev=1.)
        last = self.z.log()[1][-1]
        self.assertIsNotNone(last['filtered_grams']); self.assertIsNone(last['creep_correction_g'])

    def test_correction_counts_from_bed_warm_up_not_from_the_tare(self):
        self.heat_up(); warm = self.c.bed_warm_t
        self.z.run_readings(40, 8000000, z=1.0, ev=0., step=1.5)          # a minute warm before the tare
        self.tare(); self.z.run_readings(1, 8000000, z=1.0, ev=0.)
        self.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.); self.z.run_readings(12, 8000526, z=.2, ev=1.)
        records, samples, events = self.z.log()
        last = samples[-1]; zero_t = [e for e in events if e['event'] == 'baseline'][0]['baseline']['t']
        expected = self.c._creep_model((last['t'] - warm) / 60.) - self.c._creep_model((zero_t - warm) / 60.)
        self.assertAlmostEqual(last['creep_correction_g'], expected, places=6)
        self.assertAlmostEqual(last['filtered_grams_creep_corrected'], last['filtered_grams'] - expected, places=6)
        self.assertAlmostEqual(last['time_since_bed_warm_s'], last['t'] - warm, places=6)
        self.assertIsNotNone(last['time_since_tare_s'])

    def test_model_fades_on_a_warm_printer(self):
        m = self.c._creep_model
        self.assertAlmostEqual(m(0.), 0.)
        self.assertAlmostEqual(m(1.), 14.9 * (1 - math.exp(-2)) + .81 * 120 * (1 - math.exp(-1 / 120.)), places=9)
        rate_start = m(2.) - m(1.); rate_late = m(301.) - m(300.)
        self.assertGreater(rate_start, .7); self.assertLess(rate_late, .1)
        self.c.creep_slow_tau = 0.                                         # 0: the slow part never fades
        self.assertAlmostEqual(m(301.) - m(300.), .81, places=6)

    def test_target_change_restarts_the_clock(self):
        self.heat_up(); first = self.c.bed_warm_t
        self.bed.update(target=80., temperature=60.); self.z.f.feed()
        self.assertIsNone(self.c.bed_warm_t)
        self.bed.update(temperature=80.); self.z.f.feed()
        self.assertGreater(self.c.bed_warm_t, first)

    def test_tare_time_is_still_tracked(self):
        self.z.f.feed(); first = self.c.tare_t
        self.z.run_readings(4, 8000000, z=1.0, ev=0., step=1.)
        self.tare(); self.z.run_readings(1, 8000000, z=1.0, ev=0.)
        self.assertGreater(self.c.tare_t, first)

    def test_off_when_not_set(self):
        self.c.creep_recovery = self.c.creep_rate = 0.
        self.heat_up(); self.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.); self.z.run_readings(4, 8000526, z=.2, ev=1.)
        last = self.z.log()[1][-1]
        self.assertIsNone(last['creep_correction_g']); self.assertIsNone(last['filtered_grams_creep_corrected'])

    def test_shipped_config_values(self):
        values, section = {}, None
        for line in open(os.path.join(HERE, '..', 'deep_calibration.cfg')).read().splitlines():
            if line.startswith('['): section = line.strip()
            elif section == '[deep_calibration]' and ':' in line and not line.startswith(('#', ' ')):
                k, v = line.split(':', 1); values[k.strip()] = v.strip()
        self.assertEqual(tuple(float(values[k]) for k in ('creep_recovery_g', 'creep_tau', 'creep_rate', 'creep_slow_tau')),
                         (14.9, .5, .81, 120.))


if __name__ == '__main__':
    unittest.main()
