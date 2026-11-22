# 10.3.6: the matcher works at the gate's times, says why a phase found no
# line, and the automatic zero needs 6 readings over 1 s.
import collections
import types
import unittest
import test_capture as capture
import test_gcode_context as gate_fixture
import test_zero_and_time as zero_fixture
from test_capture import Command


def phase(start=10., dt=1., x=0., y=0., vx=1., speed=15.):
    return types.SimpleNamespace(print_time=start, move_t=dt, start_v=speed, accel=0.,
                                 x_r=vx, y_r=0., start_x=x, start_y=y)


class MissKindTests(unittest.TestCase):
    def setUp(self):
        self.g = gate_fixture.GateTests(); self.g.setUp(); self.addCleanup(self.g.doCleanups)
        self.src = self.g.source
        self.src.recent = collections.deque()
        self.seg = {'code': 'G1'}

    def kind(self, recent):
        self.src.recent = collections.deque(recent)
        self.src.last_miss = None
        result = self.src.match_phase(phase(), {})
        return result, self.src.last_miss

    def test_unique_line_matches(self):
        result, miss = self.kind([(9., self.seg, (0., 0., 0., 0.), (100., 0., 0., 0.))])
        self.assertIsNotNone(result); self.assertIsNone(miss)

    def test_no_line(self):
        self.assertEqual(self.kind([(9., self.seg, (0., 5., 0., 0.), (100., 5., 0., 0.))])[1], 'no_queue_segment')

    def test_two_lines(self):
        line = (9., self.seg, (0., 0., 0., 0.), (100., 0., 0., 0.))
        self.assertEqual(self.kind([line, line])[1], 'ambiguous_queue_segment')

    def test_unverified_command(self):
        self.assertEqual(self.kind([(9., None, (0., 0., 0., 0.), (100., 0., 0., 0.))])[1], 'blocked_by_unverified_command')

    def test_reading_carries_the_kind(self):
        self.src.timeline.clear()
        self.src.misses = [(10., 11., 'ambiguous_queue_segment')]
        motion = dict(self.g.motion); motion['print_time'] = 10.5
        result = self.src.sample(20., motion, self.g.context)
        self.assertIn('missing_or_ambiguous_queue_segment', result['reasons'])
        self.assertEqual(result['queue_miss'], 'ambiguous_queue_segment')


class GateTimesTests(unittest.TestCase):
    def test_matcher_gets_measurement_and_arrival_times(self):
        f = capture.CaptureTests(); f.setUp(); self.addCleanup(f.doCleanups)
        seen = []
        f.cell.slicer.batch = lambda stamps, context: seen.append(list(stamps))
        f.feed(); f.cell.cmd_START(Command(RUN='first'))
        f.feed(t=f.reactor.now + .25); f.feed(t=f.reactor.now + .25)
        stamps = [s for batch in seen for s in batch]
        arrival = f.reactor.now
        self.assertIn(arrival, stamps)
        self.assertTrue(any(abs(s - (arrival - .051)) < 1e-6 for s in stamps))


class ZeroThresholdTests(unittest.TestCase):
    def test_seven_readings_over_one_and_a_half_seconds_are_enough(self):
        z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); z.setUp(); self.addCleanup(z.doCleanups)
        z.f.feed(); z.c.cmd_START(Command(RUN='first'))
        z.run_readings(7, 8000000, z=1.0, ev=0.)                  # 7 readings over 1.5 s: missed before 10.3.6
        z.run_readings(3, 8000526, z=.2, ev=1.)
        records, samples, events = z.log()
        self.assertTrue(any(e['event'] == 'baseline' for e in events))
        self.assertTrue(samples[-1]['baseline_valid'])

    def test_session_end_carries_matching_counters(self):
        z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); z.setUp(); self.addCleanup(z.doCleanups)
        z.f.feed(); z.c.cmd_START(Command(RUN='first')); z.f.feed()
        records, samples, events = z.log()
        end = next(e for e in events if e['event'] == 'session_end')
        self.assertIn('phase_misses', end['slicer_matching'])


if __name__ == '__main__':
    unittest.main()
