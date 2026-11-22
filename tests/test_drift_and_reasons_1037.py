# 10.3.7: steady drift checks with confirmation, the reason for each
# unverified command, and the shipped settings (one counts_per_gram line).
import collections
import configparser
import os
import unittest
import test_gcode_context as gate_fixture
import test_zero_and_time as zero_fixture
from test_capture import Command
from deep_calibration_gcode import GcodeContext

HERE = os.path.dirname(os.path.abspath(__file__))


class ShippedConfigTests(unittest.TestCase):
    def test_one_counts_per_gram_and_the_poll_pause(self):
        text = open(os.path.join(HERE, '..', 'deep_calibration.cfg')).read()
        section, active = None, collections.Counter()
        values = {}
        for line in text.splitlines():
            if line.startswith('['):
                section = line.strip()
            elif section == '[deep_calibration]' and ':' in line and not line.startswith(('#', ' ')):
                key, value = line.split(':', 1); active[key.strip()] += 1; values[key.strip()] = value.strip()
        self.assertEqual(active['counts_per_gram'], 1)          # a second line would silently win
        self.assertEqual(float(values['counts_per_gram']), 52.56)
        self.assertEqual(float(values['poll_pause']), .05)


class VerifyReasonTests(unittest.TestCase):
    def setUp(self):
        self.seg = dict(absolute_coordinates=True, absolute_extrude=False, feed=15., delta_e=.1,
                        before={'X': 0., 'Y': 0., 'Z': .2, 'E': 0.}, after={'X': 10., 'Y': 0., 'Z': .2, 'E': .1})
        self.before = ([0., 0., .2, 0.], [0., 0., 0., 0.], True, False, 900., 1., 1.)
        self.after = ([10., 0., .2, .1], [0., 0., 0., 0.], True, False, 900., 1., 1.)

    def test_verified(self):
        self.assertIsNone(GcodeContext.verify_reason(self.seg, self.before, self.after))
        self.assertTrue(GcodeContext.verified_command(self.seg, self.before, self.after))

    def test_each_failure_is_named(self):
        self.seg['feed'] = 20.
        self.assertEqual(GcodeContext.verify_reason(self.seg, self.before, self.after), 'feed')
        self.seg['feed'] = 15.
        after = ([10.5, 0., .2, .1],) + self.after[1:]
        self.assertEqual(GcodeContext.verify_reason(self.seg, self.before, after), 'position_after_X')
        after = self.after[:2] + (False,) + self.after[3:]
        self.assertEqual(GcodeContext.verify_reason(self.seg, self.before, after), 'coordinate_modes')
        self.seg['delta_e'] = .2
        self.assertEqual(GcodeContext.verify_reason(self.seg, self.before, self.after), 'delta_e')

    def test_blocked_reading_says_which_check(self):
        g = gate_fixture.GateTests(); g.setUp(); self.addCleanup(g.doCleanups)
        src = g.source
        a, b = (0., 0., 0., 0.), (100., 0., 0., 0.)
        src.recent = collections.deque([(9., None, a, b)])
        src.block_reasons = {(9., a, b): 'feed'}
        import types
        phase = types.SimpleNamespace(print_time=10., move_t=1., start_v=15., accel=0., x_r=1., y_r=0., start_x=0., start_y=0.)
        src.last_miss = None
        self.assertIsNone(src.match_phase(phase, {}))
        self.assertEqual(src.last_miss, 'blocked_by_unverified_command:feed')


class SteadyDriftTests(unittest.TestCase):
    def setUp(self):
        self.z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); self.z.setUp(); self.addCleanup(self.z.doCleanups)
        self.z.f.feed(); self.z.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(8, 8000000, z=1.0, ev=0.)        # zero
        self.z.run_readings(6, 8000500, z=.2, ev=1.)         # printing height known

    def events(self):
        return [e for e in self.z.log()[2] if e['event'] in ('zero_drift', 'zero_drift_rejected')]

    def test_single_reading_is_not_a_check(self):
        self.z.run_readings(1, 8004000, z=.6, ev=0.); self.z.run_readings(2, 8000500, z=.2, ev=1.)
        self.assertEqual([(e['event'], e.get('reason')) for e in self.events()], [('zero_drift_rejected', 'too_few_readings')])

    def test_changing_height_is_not_a_check(self):
        self.z.run_readings(2, 8000300, z=.6, ev=0.); self.z.run_readings(2, 8000300, z=.9, ev=0.)
        self.z.run_readings(2, 8000500, z=.2, ev=1.)
        self.assertEqual(self.events()[0]['reason'], 'height_changing')

    def test_scattered_readings_are_not_a_check(self):
        for raw in (8000000, 8003000, 7997000, 8002000):
            self.z.run_readings(1, raw, z=.6, ev=0.)
        self.z.run_readings(2, 8000500, z=.2, ev=1.)
        self.assertEqual(self.events()[0]['reason'], 'scatter')

    def test_large_jump_needs_confirmation(self):
        self.z.run_readings(4, 8004000, z=.6, ev=0.); self.z.run_readings(2, 8000500, z=.2, ev=1.)
        self.z.run_readings(4, 8004000, z=.6, ev=0.); self.z.run_readings(2, 8000500, z=.2, ev=1.)
        ev = self.events()
        self.assertEqual((ev[0]['event'], ev[0].get('reason')), ('zero_drift_rejected', 'jump_unconfirmed'))
        self.assertEqual(ev[1]['event'], 'zero_drift')
        self.assertAlmostEqual(ev[1]['counts'], 4000, delta=40)

    def test_small_steady_drift_is_accepted(self):
        self.z.run_readings(4, 8000300, z=.6, ev=0.); self.z.run_readings(2, 8000500, z=.2, ev=1.)
        ev = self.events()
        self.assertEqual(ev[0]['event'], 'zero_drift'); self.assertAlmostEqual(ev[0]['counts'], 300, delta=40)


if __name__ == '__main__':
    unittest.main()
