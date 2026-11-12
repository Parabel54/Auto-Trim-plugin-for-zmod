# Knee search (DEEP_CALIBRATION_KNEE): lower the nozzle during the first layer
# until the load cell shows the steep rise where the nozzle presses the line.
import json, unittest
from pathlib import Path
import test_capture as capture
from test_capture import Command
import test_first_print_auto as fpa

class ArmCommand(fpa.ArmCommand):
    def get_int(self, key, default=None, **limits):
        return int(self.get_float(key, default, **limits))

CPG = 43.0
BASE = 8288568

class KneeTests(unittest.TestCase):
    close = capture.CaptureTests.close
    feed = capture.CaptureTests.feed
    setUp_auto = fpa.FirstPrintAutoTests.setUp
    arm = fpa.FirstPrintAutoTests.arm

    def setUp(self):
        self.setUp_auto()
        self.gm = self.objects['gcode_move'].status
        self.gm['homing_origin'][2] = 0.0
        self.knee_at = -0.125; self.slope = 2500.; self.drift = 0.; self.spike = None; self.jump = 0.
        self.mr = self.objects['motion_report'].status
        self.mr['live_extruder_velocity'] = 1.0; self.mr['live_velocity'] = 40.
        self.scripts = []
        def run_script(script):
            self.scripts.append(script)
            dz = float(script.split('Z_ADJUST=')[1].split()[0])
            before = list(self.gm['homing_origin']); self.gm['homing_origin'][2] = round(self.gm['homing_origin'][2] + dz, 6)
            self.cell._label_adjustment(before, list(self.gm['homing_origin']))   # the observer, as in Klipper
        self.gcode.run_script = run_script

    def force(self):
        z = self.gm['homing_origin'][2]
        f = 0. if z > self.knee_at else self.slope * (self.knee_at - z) + self.jump
        if self.spike and abs(z - self.spike[0]) < 1e-6: f += self.spike[1]
        return f + self.drift * self.reactor.now / 60.

    def run_print(self, seconds, layer=1):
        self.ps['state'] = 'printing'; self.ps['info'] = {'current_layer': layer}
        self.gm['gcode_position'][2] = .2 if layer == 1 else .4
        for _ in range(int(seconds / .25)):
            self.feed(raw=int(BASE + CPG * self.force()))
            if self.cell.knee is None and self.cell.active is False: break

    def start_recording_and_knee(self, **opts):
        self.arm()
        self.run_print(1.0)                     # recording starts with the first layer
        self.assertTrue(self.cell.active)
        params = dict(HOLD='3'); params.update(opts)
        self.cell.cmd_KNEE(ArmCommand(**params))

    def events(self):
        self.close()
        return [json.loads(l) for l in Path(self.cell.writer.path).read_text().splitlines()]

    def test_finds_the_knee_and_sets_knee_plus_margin(self):
        self.start_recording_and_knee()
        self.run_print(250)
        self.assertIsNone(self.cell.knee)
        self.assertAlmostEqual(self.gm['homing_origin'][2], -0.13 + 0.025, places=4)
        r = self.events()
        res = [e for e in r if e.get('event') == 'knee_result'][0]
        self.assertEqual(res['reason'], 'knee'); self.assertAlmostEqual(res['knee'], -0.13); self.assertAlmostEqual(res['target'], -0.105)
        self.assertTrue(any('knee found at Z -0.130' in m for m in self.gcode.messages))

    def test_slow_drift_does_not_move_the_knee(self):
        self.drift = 2.3                          # g per minute, as measured
        self.start_recording_and_knee()
        self.run_print(250)
        r = self.events()
        res = [e for e in r if e.get('event') == 'knee_result'][0]
        self.assertEqual(res['reason'], 'knee'); self.assertAlmostEqual(res['knee'], -0.13)

    def test_a_single_spike_is_not_taken_for_the_knee(self):
        self.spike = (0.05, 15.)                   # one step reads 15 g high, the next is normal
        self.start_recording_and_knee()
        self.run_print(250)
        r = self.events()
        res = [e for e in r if e.get('event') == 'knee_result'][0]
        self.assertAlmostEqual(res['knee'], -0.13)

    def test_force_limit_stops_at_once(self):
        self.jump = 200.                           # pressing at once very hard
        self.start_recording_and_knee()
        self.run_print(250)
        r = self.events()
        res = [e for e in r if e.get('event') == 'knee_result'][0]
        self.assertEqual(res['reason'], 'force limit'); self.assertAlmostEqual(res['knee'], -0.13)
        self.assertAlmostEqual(self.gm['homing_origin'][2], -0.105, places=4)

    def test_no_knee_within_travel_restores_the_offset(self):
        self.knee_at = -5.
        self.start_recording_and_knee(TRAVEL='0.15')
        self.run_print(250)
        r = self.events()
        res = [e for e in r if e.get('event') == 'knee_result'][0]
        self.assertTrue(res['reason'].startswith('no knee within'))
        self.assertAlmostEqual(self.gm['homing_origin'][2], 0.0, places=4)

    def test_layer_2_before_a_knee_restores_the_offset(self):
        self.knee_at = -5.
        self.start_recording_and_knee()
        self.run_print(20)
        self.run_print(5, layer=2)
        self.assertIsNone(self.cell.knee)
        self.assertAlmostEqual(self.gm['homing_origin'][2], 0.0, places=4)

    def test_search_steps_are_not_labelled_as_your_babysteps(self):
        self.start_recording_and_knee()
        self.run_print(250)
        r = self.events()
        labels = [e for e in r if e.get('event') == 'adjustment_label' and e.get('label') in ('TOO_HIGH', 'TOO_LOW')]
        self.assertEqual(labels, [])
        self.assertGreater(len([e for e in r if e.get('event') == 'knee_step']), 10)

    def test_arm_waits_for_the_first_layer(self):
        self.cell.cmd_KNEE(ArmCommand(ARM='1', HOLD='3'))
        self.assertEqual(self.cell.knee['phase'], 'wait')
        self.arm(); self.run_print(1.0)
        self.assertEqual(self.cell.knee['phase'], 'wait')        # not before 3 s into the layer
        self.run_print(6.0)
        self.assertEqual(self.cell.knee['phase'], 'step')

    def test_abort_restores_the_offset(self):
        self.start_recording_and_knee()
        self.run_print(30)
        self.cell.cmd_KNEE_ABORT(Command())
        self.assertIsNone(self.cell.knee)
        self.assertAlmostEqual(self.gm['homing_origin'][2], 0.0, places=4)

    def test_refused_outside_the_first_layer(self):
        with self.assertRaises(RuntimeError):
            self.cell.cmd_KNEE(ArmCommand(HOLD='3'))

if __name__ == '__main__':
    unittest.main()
