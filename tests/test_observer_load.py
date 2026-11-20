import unittest
from unittest import mock
import test_beta102_review as review


class ObserverLoadTests(unittest.TestCase):
    setUp = review.AuditRegressions.setUp
    observe = review.AuditRegressions.observe

    def test_armed_only_and_missing_snapshot_do_no_observer_work(self):
        self.s.checkpoint = mock.Mock(side_effect=AssertionError('checkpoint'))
        self.c.armed, self.c.active = {'test': True}, False
        self.observe()
        self.c.active, self.s.snapshot = True, None
        self.observe()
        self.s.checkpoint.assert_not_called()
        self.assertFalse(self.s.commands)

    def test_dispatch_only_buffers_and_batch_checks_native_state(self):
        self.c._status = mock.Mock(side_effect=AssertionError('per-command status'))
        self.s.verified_command = mock.Mock(return_value=True)
        self.observe()
        self.c._status.assert_not_called()
        self.s.verified_command.assert_not_called()
        self.assertEqual(len(self.s.commands), 1)
        self.s.batch([], self.context)
        self.s.verified_command.assert_called_once()
        self.assertFalse(self.s.commands)
