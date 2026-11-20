# 10.2.4: the G-code file is read while Auto Trim's bed heat soak waits, never
# at the first layer (a long parse slowed Klipper's reactor through the GIL and
# ended a print with "Timer too close").
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_capture as capture
from test_first_print_auto import ArmCommand
from test_gcode_context import gcode

SOAK = 'info AUTO TRIM: bed heat soak 971 s (calibrated at 60 C, slowest point, bed started at 20 C), 93 s covered by the nozzle clean, waiting 878 s'
COVERED = 'info AUTO TRIM: bed heat soak 60 s (calibrated at 60 C, slowest point, bed started at 55 C) already covered by the 93 s nozzle clean'

class ContextStartTests(unittest.TestCase):
    def setUp(self):
        self.f = capture.CaptureTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.owner = self.f.cell; self.source = self.owner.slicer
        self.source.enabled = True
        self.path = Path(self.f.temp.name) / 'print.gcode'; self.path.write_text(gcode())
        self.f.objects['virtual_sdcard'] = SimpleNamespace(file_path=lambda: str(self.path))
        self.handlers = []
        self.owner.gcode.register_output_handler = self.handlers.append
        self.messages = self.owner.gcode.messages = []
        self.owner.gcode.respond_info = self.messages.append

    def finish(self):
        if self.source.worker is not None: self.source.worker.join(5)
        self.source.poll()

    def announce(self, msg):
        for h in self.handlers: h(msg)

    def test_default_is_soak(self):
        self.assertEqual(self.source.start_policy, 'soak')
        self.source.poll(); self.assertEqual(len(self.handlers), 1)          # listener attached once
        self.source.poll(); self.assertEqual(len(self.handlers), 1)

    def test_soak_announcement_reads_the_file_before_arming(self):
        self.source.poll()
        self.assertIsNone(self.owner.armed)
        self.announce(SOAK)
        self.assertIn(self.source.state, ('loading', 'ready'))
        self.finish()
        self.assertEqual(self.source.state, 'ready'); self.assertIsNotNone(self.source.snapshot)
        self.assertEqual(len([m for m in self.messages if 'G-code context read in' in m]), 1)

    def test_arming_after_the_soak_does_not_read_again(self):
        self.source.poll(); self.announce(SOAK); self.finish()
        generation = self.source.generation; snapshot = self.source.snapshot
        self.owner.armed = dict(material='PLA')
        for _ in range(3): self.source.poll()
        self.assertEqual(self.source.generation, generation)
        self.assertIs(self.source.snapshot, snapshot); self.assertEqual(self.source.state, 'ready')
        self.assertFalse(any('not read' in m for m in self.messages))

    def test_arming_while_still_loading_waits_for_that_read(self):
        self.source.poll(); self.announce(SOAK)
        generation = self.source.generation
        self.owner.armed = dict(material='PLA'); self.source.poll()
        self.assertEqual(self.source.generation, generation)
        self.finish(); self.assertEqual(self.source.state, 'ready')

    def test_no_soak_wait_means_the_file_is_not_read(self):
        self.source.poll()
        self.owner.armed = dict(material='PLA')
        for _ in range(3): self.source.poll()
        self.assertEqual(self.source.state, 'skipped'); self.assertIsNone(self.source.snapshot)
        self.assertIsNone(self.source.worker)
        said = [m for m in self.messages if 'G-code context not read' in m]
        self.assertEqual(len(said), 1)                                        # said once

    def test_actual_arm_and_start_do_not_scan_when_soak_was_skipped(self):
        self.f.feed()
        self.owner.auto_capture = True
        self.owner.cmd_ARM(ArmCommand())
        self.assertIsNone(self.source.worker)
        self.owner.cmd_START(capture.Command())
        self.source.poll()
        self.assertIsNone(self.source.worker)
        self.assertTrue(self.owner.active)
        self.assertEqual(self.source.state, 'skipped')

    def test_soak_already_covered_is_not_a_wait(self):
        self.source.poll(); self.announce(COVERED)
        self.assertIsNone(self.source.worker)
        self.owner.armed = dict(material='PLA'); self.source.poll()
        self.assertEqual(self.source.state, 'skipped')

    def test_previous_print_snapshot_is_not_reused_without_a_soak(self):
        self.source.poll(); self.announce(SOAK); self.finish()
        self.assertEqual(self.source.state, 'ready')
        other = Path(self.f.temp.name) / 'next.gcode'; other.write_text(gcode())
        self.f.objects['virtual_sdcard'] = SimpleNamespace(file_path=lambda: str(other))
        self.owner.armed = dict(material='PLA'); self.source.poll()
        self.assertEqual(self.source.state, 'skipped'); self.assertIsNone(self.source.snapshot)

    def test_arm_policy_keeps_the_old_behaviour(self):
        self.source.start_policy = 'arm'
        self.owner.armed = dict(material='PLA'); self.source.poll()
        self.assertIn(self.source.state, ('loading', 'ready')); self.finish()
        self.assertEqual(self.source.state, 'ready')

    def test_soak_message_ignored_with_arm_policy_or_context_off(self):
        self.source.start_policy = 'arm'; self.source.poll(); self.announce(SOAK)
        self.assertIsNone(self.source.worker)
        self.source.enabled = False; self.source.start_policy = 'soak'; self.announce(SOAK)
        self.assertIsNone(self.source.worker)

    def test_loaded_slicer_data_is_frozen_out_of_garbage_collection(self):
        # 10.3.2: a full collection over the parsed file shut a print down
        import gc
        from unittest import mock
        with mock.patch.object(gc, 'freeze') as freeze:
            self.source.poll(); self.announce(SOAK); self.finish()
        self.assertEqual(self.source.state, 'ready')
        freeze.assert_called_once()

    def test_parsed_file_survives_freezing_for_real(self):
        import gc
        self.source.poll(); self.announce(SOAK); self.finish()
        self.assertEqual(self.source.state, 'ready'); self.assertGreater(gc.get_freeze_count(), 0)
        gc.unfreeze()

    def test_status_reports_the_policy(self):
        self.assertEqual(self.source.status()['start_policy'], 'soak')


if __name__ == '__main__':
    unittest.main()
