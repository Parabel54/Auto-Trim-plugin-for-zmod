# 10.3.5: automatic force zero after the last tare (in-air drift removed in 10.3.8),
# and each reading's estimated measurement time with its uncertainty.
import types
import unittest
import test_capture as capture
from test_capture import Command


class ZeroAndTimeTests(unittest.TestCase):
    def setUp(self):
        self.f = capture.CaptureTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.c = self.f.cell; self.c.cpg = 52.56
        self.c.auto_zero = True          # the fixture config returns False for every boolean
        self.m = dict(z=1.0, ev=0.)
        o = self.f.objects
        o['mcu'] = types.SimpleNamespace(estimated_print_time=lambda t: t)
        o['toolhead'].get_extra_axes = lambda: [None, None, None, types.SimpleNamespace(get_name=lambda: 'extruder')]
        o['motion_report'].dtrapqs = {
            'toolhead': types.SimpleNamespace(get_trapq_position=lambda clock: ([10., 20., self.m['z']], 0.)),
            'extruder': types.SimpleNamespace(get_trapq_position=lambda clock: ([0.], self.m['ev']))}

    def run_readings(self, n, raw, z, ev, step=None):
        self.m.update(z=z, ev=ev)
        for i in range(n):
            self.f.feed(raw + (i % 3) * 20, t=None if step is None else self.f.reactor.now + step)

    def log(self):
        records = self.f.read_log()
        return records, [r for r in records if r['type'] == 'sample'], [r for r in records if r['type'] == 'event']

    def test_auto_zero_after_tare_gives_force_in_grams(self):
        self.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.run_readings(14, 8000000, z=1.0, ev=0.)                 # after the tare, nozzle clear
        self.run_readings(12, 8000526, z=.2, ev=1.)                  # printing: about +10 g
        records, samples, events = self.log()
        base = [e for e in events if e['event'] == 'baseline']
        self.assertEqual(base[0]['baseline']['kind'], 'auto_after_tare')
        self.assertAlmostEqual(base[0]['baseline']['raw'], 8000020, delta=25)
        late = samples[-1]
        self.assertTrue(late['baseline_valid']); self.assertEqual(late['baseline_kind'], 'auto_after_tare')
        self.assertGreater(late['filtered_grams'], 5.)

    def test_only_readings_after_the_last_tare_count(self):
        self.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.run_readings(14, 9000000, z=1.0, ev=0.)                 # before a tare
        self.f.reader._command_id += 1                               # Auto Trim re-tares
        self.run_readings(14, 8000000, z=1.0, ev=0.)
        self.run_readings(3, 8000000, z=.2, ev=1.)
        records, samples, events = self.log()
        base = [e for e in events if e['event'] == 'baseline'][0]['baseline']
        self.assertLess(abs(base['raw'] - 8000020), 25)

    def test_too_few_quiet_readings_means_no_zero_and_says_so(self):
        self.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.run_readings(4, 8000000, z=1.0, ev=0.)
        self.run_readings(3, 8000500, z=.2, ev=1.)
        records, samples, events = self.log()
        self.assertTrue(any(e['event'] == 'auto_zero_unavailable' for e in events))
        self.assertFalse(any(e['event'] == 'baseline' for e in events))
        self.assertIsNone(samples[-1]['filtered_grams'])

    def test_in_air_moments_no_longer_change_anything(self):
        # 10.3.8: drift checks from in-air moments were removed
        self.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.run_readings(14, 8000000, z=1.0, ev=0.)
        self.run_readings(8, 8000500, z=.2, ev=1.)
        self.run_readings(4, 8004000, z=.6, ev=0.)                   # Z-hop travel
        self.run_readings(6, 8000500, z=.2, ev=1.)
        records, samples, events = self.log()
        self.assertFalse(any(e['event'] in ('zero_drift', 'zero_drift_rejected') for e in events))
        self.assertFalse(any(k.startswith('zero_drift') or 'drift_corrected' in k for k in samples[-1]))
        self.assertEqual(samples[-1]['baseline_kind'], 'auto_after_tare')

    def test_extruding_or_moving_down_readings_never_become_the_zero(self):
        self.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.run_readings(14, 8000000, z=1.0, ev=0.)
        self.run_readings(8, 8000500, z=.2, ev=1.)
        self.run_readings(4, 8000500, z=.25, ev=0.)                 # pause at layer height: not "in air"
        self.run_readings(4, 8000500, z=.2, ev=1.)
        records, samples, events = self.log()
        self.assertFalse(any(e['event'] == 'zero_drift' for e in events))

    def test_manual_zero_takes_precedence(self):
        self.f.feed()
        self.c.baseline = dict(t=0., raw=7999000, generation=self.f.reader._command_id, kind='software_idle_reference_not_board_tare')
        self.c.cmd_START(Command(RUN='first'))
        self.run_readings(14, 8000000, z=1.0, ev=0.)
        self.run_readings(3, 8000500, z=.2, ev=1.)
        records, samples, events = self.log()
        self.assertEqual(samples[-1]['baseline_kind'], 'software_idle_reference_not_board_tare')

    def test_measurement_time_window(self):
        self.f.feed(); self.c.cmd_START(Command(RUN='first'))
        self.run_readings(3, 8000000, z=1.0, ev=0., step=.25)        # slower than the board: one period back
        self.run_readings(3, 8000000, z=1.0, ev=0., step=.05)        # faster: back to the previous reply
        records, samples, events = self.log()
        slow, fast = samples[1], samples[-1]
        self.assertAlmostEqual(slow['t'] - slow['acquisition_t'], .051, places=3)
        self.assertAlmostEqual(slow['acquisition_uncertainty_s'], .049, places=3)
        self.assertAlmostEqual(fast['t'] - fast['acquisition_t'], .026, places=3)
        self.assertAlmostEqual(fast['acquisition_uncertainty_s'], .024, places=3)
        self.assertEqual(fast['motion_at_acquisition']['sample_time'], fast['acquisition_t'])


if __name__ == '__main__':
    unittest.main()
