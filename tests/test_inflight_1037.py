# 10.3.7+: a command whose handler is still waiting in Klipper's move queue
# (a long line, already printing) is checked like a finished one.
import types
import unittest
import test_beta102_review as review
from test_beta102_review import ArmCommand


class InProgressTests(unittest.TestCase):
    setUp = review.AuditRegressions.setUp

    def run_in_handler(self, check):
        # Klipper's tick runs while the G1 handler waits in the move queue
        seen = {}
        def waiting_handler(gcmd):
            self.native.cmd_G1(gcmd)                      # position and speed already set
            seen.update(check())
        self.s.observe('G1', waiting_handler, ArmCommand(X='100', E='2.5', F='2400'))
        return seen

    def inflight(self):
        return dict(entries=self.s._inflight(False, self.s.live_conditions[0]))

    def test_trusted_command_in_progress_is_a_candidate(self):
        entries = self.run_in_handler(self.inflight)['entries']
        self.assertEqual(len(entries), 1)
        self.assertIs(entries[0][1], self.segment)

    def test_its_phase_matches_while_it_prints(self):
        def match():
            entries = self.s._inflight(False, self.s.live_conditions[0])
            phase = types.SimpleNamespace(print_time=5., move_t=1., start_v=40., accel=0.,
                                          x_r=1., y_r=0., start_x=20., start_y=0.)
            self.s.last_miss = None
            return dict(record=self.s.match_phase(phase, self.s.live_conditions[0], entries), miss=self.s.last_miss)
        seen = self.run_in_handler(match)
        self.assertIsNotNone(seen['record'], seen['miss'])
        self.assertIs(seen['record']['segment'], self.segment)

    def test_tampered_command_in_progress_blocks_with_its_reason(self):
        self.native.last_position[0] = 20.                # a hidden macro moved X
        entries = self.run_in_handler(self.inflight)['entries']
        self.assertIsNone(entries[0][1])
        self.assertEqual(self.s.unverified_counts, {'in_progress:position_before_X': 1})


if __name__ == '__main__':
    unittest.main()
