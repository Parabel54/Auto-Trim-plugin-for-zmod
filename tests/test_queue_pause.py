import unittest
from types import SimpleNamespace
from unittest import mock

import test_beta102_review as review
from test_first_print_auto import ArmCommand


def phase(t, duration, x, length):
    return SimpleNamespace(print_time=t, move_t=duration, start_x=x, start_y=0.,
                           x_r=1., y_r=0., start_v=length/duration, accel=0.)


class MotionHistoryTests(unittest.TestCase):
    setUp = review.AuditRegressions.setUp
    observe = review.AuditRegressions.observe

    def install(self):
        gcode = self.f.gcode
        self.s.handlers.clear()
        def register(name, fn):
            old = gcode.commands.pop(name, None)
            if fn is not None:
                gcode.commands[name] = fn
            return old
        gcode.register_command = register
        self.native.cmd_G1_alias = self.native.cmd_G1
        register('G1', self.native.cmd_G1)
        tool = self.f.objects['toolhead']
        tool.register_lookahead_callback = mock.Mock(side_effect=AssertionError('unexpected callback'))
        def add_move(move):
            self.assertFalse(move.timing_callbacks)
            return 'native-queue-result'
        tool.lookahead = SimpleNamespace(add_move=add_move)
        self.f.objects['mcu'] = self.s.mcu
        self.report = mock.Mock()
        self.report.extract_trapq.return_value = ([], [])
        self.f.objects['motion_report'].dtrapqs = {'toolhead': self.report}
        self.s.install()
        self.f.reactor.now = 9.
        self.assertIs(tool.lookahead.add_move, add_move)

    def test_split_moves_and_one_history_read_for_two_samples(self):
        self.install()
        first = phase(10., .10, 0., 40.)
        second = phase(10.10, .15, 40., 60.)
        sentinel = object()
        def native_moves(pos, speed):
            for row in (first, second):
                self.assertEqual(self.f.objects['toolhead'].lookahead.add_move(
                    SimpleNamespace(timing_callbacks=[])), 'native-queue-result')
            # A tick while native is paused sees no unverified incomplete
            # observation. Later receipt samples can match the same motion.
            self.s.batch([10.05], dict(t=10.05))
            self.assertFalse(self.s.timeline)
            return sentinel
        self.native.move_with_transform = native_moves
        self.f.gcode.commands['G1'](ArmCommand(X='100', E='2.5', F='2400'))
        self.report.extract_trapq.return_value = ([first, second], [])
        self.s.batch([10.05, 10.12], dict(t=10.20))
        self.report.extract_trapq.assert_called_once()
        self.assertEqual([(r['start'], r['end']) for r in self.s.timeline],
                         [(10., 10.10), (10.10, 10.25)])
        self.assertTrue(all(r['segment'] is self.segment for r in self.s.timeline))
        self.f.objects['toolhead'].register_lookahead_callback.assert_not_called()

    def test_native_error_propagates_once_without_partial_annotation(self):
        self.install()
        self.native.move_with_transform = mock.Mock(side_effect=RuntimeError('native queue failure'))
        with self.assertRaisesRegex(RuntimeError, 'native queue failure'):
            self.f.gcode.commands['G1'](ArmCommand(X='100', E='2.5', F='2400'))
        self.native.move_with_transform.assert_called_once()
        self.assertFalse(self.s.commands)

    def test_ambiguous_or_rewritten_native_motion_is_unattributed(self):
        self.install()
        self.observe()
        row = phase(10., .20, 0., 100.)
        self.report.extract_trapq.return_value = ([row], [])
        self.s.batch([10.1], dict(t=10.2))
        self.assertTrue(self.s.timeline)
        self.s.recent.append(self.s.recent[-1])
        self.s.batch([10.1], dict(t=10.2))
        self.assertFalse(self.s.timeline)
        self.s.recent.pop()
        self.report.extract_trapq.return_value = ([phase(10., .20, 0., 103.)], [])
        self.s.batch([10.1], dict(t=10.2))
        self.assertFalse(self.s.timeline)

    def test_changed_conditions_and_queue_overflow_fail_closed(self):
        self.install()
        self.observe()
        self.report.extract_trapq.return_value = ([phase(10., .20, 0., 100.)], [])
        self.s.batch([10.1], dict(t=10.2, extruder_state={'pressure_advance': .06}))
        self.assertFalse(self.s.timeline)
        item = (0, 'G1', {}, 1., None, (), (), 0)
        self.s.commands.extend([item] * 129)
        self.s.batch([10.1], dict(t=10.2))
        self.assertEqual(self.s.observation_drops, 129)
        self.assertFalse(self.s.recent)
