# First print test without console input (beta 6): DEEP_CALIBRATION_ARM on
# the start G-code, automatic start with the first layer, babystep labels,
# automatic GOOD for the offset kept, automatic stop.
import json, unittest
from pathlib import Path
import test_capture as capture
from test_capture import Command, Status

class ArmCommand(Command):
    def get_command_parameters(self): return dict(self.params)

ARM = dict(MATERIAL='PLA', HEIGHT='0.2', WIDTH='0.45', SPEED='40', FAN='0', FILAMENT='1.75')

class FirstPrintAutoTests(unittest.TestCase):
    # The recorder fixture of test_capture, without re-running its tests
    close = capture.CaptureTests.close
    feed = capture.CaptureTests.feed
    def setUp(self):
        capture.CaptureTests.setUp(self)
        self.cell.auto_capture = True
        self.cell.auto_stop_layer = 2
        self.gcode.create_gcode_command = lambda cmd, line, params: ArmCommand(**params)
        self.objects['gcode macro'] = None
        self.ps = self.objects['print_stats'].status
        self.gm = self.objects['gcode_move'].status
        self.feed()

    def arm(self, **extra):
        params = dict(ARM); params.update(extra)
        self.cell.cmd_ARM(ArmCommand(**params))

    def print_layer(self, layer, z=None, n=3):
        self.ps['state'] = 'printing'; self.ps['info'] = {'current_layer': layer}
        if z is not None: self.gm['gcode_position'][2] = z
        for _ in range(n): self.feed()

    def events(self):
        self.close()
        return [json.loads(l) for l in Path(self.cell.writer.path).read_text().splitlines()]

    def test_full_session_starts_labels_and_stops_by_itself(self):
        self.arm()
        self.assertTrue(self.cell.get_status(self.reactor.now)['armed'])
        self.print_layer(0, z=10.)
        self.assertFalse(self.cell.active, 'not before the first layer')
        self.print_layer(1, z=.2)
        self.assertTrue(self.cell.active and self.cell.auto_session)
        self.assertEqual(self.cell.recipe['material'], 'PLA'); self.assertEqual(self.cell.recipe['height'], .2)
        # babystep closer: the previous offset was too high
        self.cell._label_adjustment([0, 0, .60, 0], [0, 0, .58, 0])
        self.assertTrue(any('was too high' in m for m in self.gcode.messages))
        self.gm['homing_origin'][2] = .58
        self.print_layer(1, n=2)
        self.print_layer(2, z=.4)
        self.assertFalse(self.cell.active)
        r = self.events()
        good = [e for e in r if e.get('event') == 'adjustment_label' and e.get('label') == 'GOOD']
        self.assertEqual(len(good), 1); self.assertAlmostEqual(good[0]['from_z'], .58)
        self.assertTrue(good[0]['inferred']); self.assertEqual(good[0]['source'], 'held_through_first_layer')
        end = [e for e in r if e.get('event') == 'session_end']
        self.assertEqual(end[-1]['reason'], 'first_layer_done')
        self.assertTrue(any('labelled GOOD' in m for m in self.gcode.messages))

    def test_manual_label_after_the_last_change_is_kept(self):
        self.arm(); self.print_layer(1, z=.2)
        self.cell.cmd_MARK(Command(LABEL='TOO_LOW'))
        self.print_layer(2, z=.4)
        r = self.events()
        self.assertFalse(any(e.get('event') == 'adjustment_label' and e.get('label') == 'GOOD' for e in r))

    def test_waits_for_auto_trim_to_finish_preparing(self):
        self.objects['gcode_macro AUTO_TRIM'] = Status(prepared=False)
        self.arm(); self.print_layer(1, z=.2)
        self.assertFalse(self.cell.active)
        self.objects['gcode_macro AUTO_TRIM'].status['prepared'] = True
        self.print_layer(1, z=.2)
        self.assertTrue(self.cell.active)

    def test_without_layer_numbers_uses_height_and_ignores_a_short_z_hop(self):
        self.arm(); self.print_layer(None, z=.2)
        self.assertTrue(self.cell.active)
        self.print_layer(None, z=.45, n=4)       # 1 s above: a Z-hop, keeps recording
        self.print_layer(None, z=.2, n=2)
        self.assertTrue(self.cell.active)
        self.print_layer(None, z=.4, n=16)       # 4 s at layer 2 height
        self.assertFalse(self.cell.active)

    def test_print_cancelled_before_first_layer_disarms(self):
        self.arm(); self.print_layer(0, z=10.)
        self.ps['state'] = 'cancelled'; self.feed()
        self.assertFalse(self.cell.get_status(self.reactor.now)['armed'])
        self.assertTrue(any('nothing recorded' in m for m in self.gcode.messages))

    def test_arm_rejects_bad_recipe_and_works_only_with_auto_capture(self):
        with self.assertRaises(RuntimeError): self.cell.cmd_ARM(ArmCommand(MATERIAL='P L A!', HEIGHT='0.2'))
        self.cell.auto_capture = False
        with self.assertRaises(RuntimeError): self.arm()

class AnalyzerGoodTests(unittest.TestCase):
    def test_automatic_good_labels_rows_and_session_is_complete(self):
        import tempfile
        from analyze import load_run
        from test_analysis import write_run
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'r.jsonl'; write_run(p)
            r = [json.loads(l) for l in p.read_text().splitlines()]
            for item in r:
                if item['type'] == 'context': item['label'] = 'UNLABELLED'
            for item in r:
                if item.get('event') == 'session_end': item['reason'] = 'first_layer_done'
            z = next(i['gcode']['homing_origin'][2] for i in r if i['type'] == 'context' and i.get('gcode'))
            r.append(dict(type='event', event='adjustment_label', t=900, start_t=0, end_t=900, from_z=z, to_z=z,
                          label='GOOD', inferred=True, source='held_through_first_layer'))
            p.write_text(''.join(json.dumps(x) + '\n' for x in r))
            run = load_run(p)
            rows = [x for x in run['samples'] if x['label'] == 'GOOD']
            self.assertTrue(rows and all(x['label_inferred'] and x['label_source'] == 'held_through_first_layer' for x in rows))

if __name__ == '__main__':
    unittest.main()


class PhysicalTimingTests(unittest.TestCase):
    # Klipper reads G-code ahead of the nozzle. Start, stop and labels are
    # placed at the time they physically happen.
    close = capture.CaptureTests.close
    feed = capture.CaptureTests.feed
    setUp = FirstPrintAutoTests.setUp
    arm = FirstPrintAutoTests.arm
    print_layer = FirstPrintAutoTests.print_layer
    events = FirstPrintAutoTests.events

    def lead(self, seconds):
        tool = self.objects['toolhead'].status
        tool['print_time'] = tool['estimated_print_time'] + seconds

    def test_first_layer_starts_when_its_first_queued_move_runs(self):
        self.lead(2.0); self.arm(); self.print_layer(1, z=.2, n=1)
        self.assertTrue(self.cell.active)
        self.assertAlmostEqual(self.cell.first_layer_t, self.reactor.now + 2.0)
        r = self.events() if False else None

    def test_recording_continues_until_the_queued_end_of_layer_1_has_printed(self):
        self.lead(2.0); self.arm(); self.print_layer(1, z=.2, n=2)
        self.print_layer(2, z=.4, n=1)
        announced = self.reactor.now
        self.assertTrue(self.cell.active, 'still printing the end of layer 1')
        self.assertAlmostEqual(self.cell.stop_at, announced + 2.0)
        for _ in range(6): self.feed()                     # 1.5 s later
        self.assertTrue(self.cell.active)
        for _ in range(4): self.feed()                     # past 2 s
        self.assertFalse(self.cell.active)
        r = self.events()
        good = [e for e in r if e.get('event') == 'adjustment_label' and e.get('label') == 'GOOD'][0]
        self.assertAlmostEqual(good['end_t'], announced + 2.0)
        self.assertTrue(any(e.get('event') == 'first_layer_end' for e in r))
        self.assertTrue(any(e.get('event') == 'first_layer_start' for e in r))

    def test_babystep_label_is_timed_when_it_reaches_the_nozzle(self):
        self.lead(1.5); self.arm(); self.print_layer(1, z=.2, n=2)
        pressed = self.reactor.now
        self.cell._label_adjustment([0, 0, .60, 0], [0, 0, .58, 0])
        self.assertAlmostEqual(self.cell.adjustment_since, pressed + 1.5)
        self.print_layer(2, z=.4, n=10)
        r = self.events()
        lab = [e for e in r if e.get('event') == 'adjustment_label' and e.get('label') == 'TOO_HIGH'][0]
        self.assertAlmostEqual(lab['end_t'], pressed + 1.5); self.assertAlmostEqual(lab['queue_lead'], 1.5)
        good = [e for e in r if e.get('event') == 'adjustment_label' and e.get('label') == 'GOOD'][0]
        self.assertAlmostEqual(good['start_t'], pressed + 1.5)

    def test_babystep_read_after_layer_2_was_announced_belongs_to_layer_2(self):
        self.lead(2.0); self.arm(); self.print_layer(1, z=.2, n=2)
        self.print_layer(2, z=.4, n=1)
        self.cell._label_adjustment([0, 0, .60, 0], [0, 0, .62, 0])
        self.print_layer(2, n=10)
        r = self.events()
        self.assertFalse(any(e.get('event') == 'adjustment_label' and e.get('label') == 'TOO_LOW' for e in r))

    def test_no_queue_means_no_delay(self):
        self.lead(0.0); self.arm(); self.print_layer(1, z=.2, n=2)
        self.print_layer(2, z=.4, n=1)
        self.assertFalse(self.cell.active)
