# 10.3.4: flushing only matters for prints with more than one filament;
# print-wide reasons do not restart the settling run; POLL_PAUSE= per recording.
import unittest
import test_gcode_context as gate_fixture
import test_beta10_policy as policy


class FlushingAndSettlingTests(unittest.TestCase):
    def setUp(self):
        self.g = gate_fixture.GateTests(); self.g.setUp(); self.addCleanup(self.g.doCleanups)
        self.settings = self.g.source.snapshot['settings']

    def test_single_filament_print_with_flushing_profile_is_eligible(self):
        # an AD5X print: one filament, flush_into_infill = 1, every reading rejected
        self.settings['flush_into_infill'] = '1'
        self.g.source.snapshot['used_filaments'] = [self.g.segment['tool']]
        result = self.g.ready()
        self.assertNotIn('model_flushing_not_separated', result['reasons'])

    def test_unknown_filament_list_keeps_the_flushing_rule(self):
        self.settings['flush_into_infill'] = '1'
        self.g.source.snapshot['used_filaments'] = None
        for n in range(26): result = self.g.sample(n / 10.)
        self.assertIn('model_flushing_not_separated', result['reasons'])

    def test_multi_filament_print_stays_rejected(self):
        self.settings['flush_into_objects'] = '1'
        self.g.source.snapshot['used_filaments'] = [self.g.segment['tool'], self.g.segment['tool'] + 1]
        for n in range(26): result = self.g.sample(n / 10.)
        self.assertIn('model_flushing_not_separated', result['reasons'])
        self.assertIn('tool_mapping_changed', result['reasons'])

    def test_print_wide_reason_does_not_restart_settling(self):
        self.g.ready()
        self.settings['raft_layers'] = '2'
        held = self.g.sample(2.7)
        self.assertIn('raft_first_layer', held['reasons'])
        self.assertNotIn('segment_settling', held['reasons'])
        self.settings['raft_layers'] = '0'
        self.assertTrue(self.g.sample(2.8)['eligible'])      # steady run was not restarted

    def test_moment_reasons_still_restart_settling(self):
        self.g.ready()
        self.g.motion['live_extruder_velocity'] = -1               # a retraction
        self.g.sample(2.7)
        self.g.motion['live_extruder_velocity'] = 1
        self.assertIn('segment_settling', self.g.sample(2.8)['reasons'])




class RecordingPollPauseTests(unittest.TestCase):
    def setUp(self):
        cls = next(v for v in vars(policy).values() if isinstance(v, type) and issubclass(v, unittest.TestCase) and hasattr(v, 'start'))
        self.p = cls(); self.p.setUp(); self.addCleanup(self.p.doCleanups)

    def test_poll_pause_applies_to_its_own_recording_only(self):
        c = self.p.c
        self.p.f.feed()
        c.cmd_START(policy.Command(RUN='idle_fast', ACCEL=0, ADC=0, POLL_PAUSE=0))
        self.assertEqual(c.reader.poll_time, 0.)
        c.cmd_STOP(policy.Command())
        self.assertAlmostEqual(c.reader.poll_time, .07)
        self.assertIsNone(c.run_poll_pause)
        c.writer.thread.join(5)                                    # previous file finished
        self.p.f.feed()
        c.cmd_START(policy.Command(RUN='next', ACCEL=0, ADC=0))
        self.assertAlmostEqual(c.reader.poll_time, .05)            # back to poll_pause
        c.cmd_STOP(policy.Command())


if __name__ == '__main__':
    unittest.main()
