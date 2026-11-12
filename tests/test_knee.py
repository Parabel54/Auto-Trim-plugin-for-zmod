# Knee search (DEEP_CALIBRATION_KNEE): lower the nozzle during the first layer
# until the load cell shows the steep rise where the nozzle presses the line;
# fitted knee, noise-based threshold, adaptive hold, confirmation going back
# up, and the margin learned from what you keep.
import json, random, unittest
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
        self.noise = 0.; self.rng = random.Random(7)
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
        f += self.drift * self.reactor.now / 60.
        if self.noise: f += self.rng.gauss(0., self.noise)
        return f

    def run_print(self, seconds, layer=1):
        self.ps['state'] = 'printing'; self.ps['info'] = {'current_layer': layer}
        self.gm['gcode_position'][2] = .2 if layer == 1 else .4
        for _ in range(int(seconds / .25)):
            self.feed(raw=int(BASE + CPG * self.force()))
            if self.cell.knee is None and self.cell.active is False: break

    def start_recording_and_knee(self, **opts):
        self.arm()
        self.run_print(1.0)
        self.assertTrue(self.cell.active)
        # CONFIRM=1 is the printer's default (the fixture config answers every boolean False)
        params = dict(HOLD='3', HOLD_MAX='12', CONFIRM='1'); params.update(opts)
        self.cell.cmd_KNEE(ArmCommand(**params))

    def events(self):
        self.close()
        return [json.loads(l) for l in Path(self.cell.writer.path).read_text().splitlines()]

    def result(self, r):
        return [e for e in r if e.get('event') == 'knee_result'][0]

    # ---- the knee itself
    def test_finds_the_knee_by_fitting_and_sets_knee_plus_margin(self):
        self.start_recording_and_knee()
        self.run_print(400)
        self.assertIsNone(self.cell.knee)
        res = self.result(self.events())
        self.assertEqual(res['reason'], 'knee')
        self.assertAlmostEqual(res['knee_threshold'], -0.13)          # the old rule: first step over the threshold
        self.assertAlmostEqual(res['knee'], -0.125, places=3)         # the fit: where pressing really starts
        self.assertAlmostEqual(self.gm['homing_origin'][2], res['knee'] + 0.025, places=4)
        self.assertTrue(res['fitted'])

    def test_a_knee_between_two_steps_is_found_between_them(self):
        self.knee_at = -0.1263
        self.start_recording_and_knee()
        self.run_print(400)
        res = self.result(self.events())
        self.assertAlmostEqual(res['knee'], -0.1263, delta=0.0015)
        self.assertAlmostEqual(res['knee_threshold'], -0.13)

    def test_confirmed_going_back_up_with_a_repeatability(self):
        self.start_recording_and_knee()
        self.run_print(400)
        r = self.events(); res = self.result(r)
        ups = [e for e in r if e.get('event') == 'knee_step' and e.get('direction') == 'up' and not e.get('skipped')]
        self.assertGreaterEqual(len(ups), 2)
        self.assertLess(max(e['offset'] for e in ups), -0.125 + 0.05)    # it does not climb far
        self.assertIsNotNone(res['knee_up'])
        self.assertLessEqual(res['repeatability'], 0.002)

    def test_confirm_can_be_switched_off(self):
        self.start_recording_and_knee(CONFIRM='0')
        self.run_print(400)
        r = self.events(); res = self.result(r)
        self.assertFalse(any(e.get('direction') == 'up' for e in r if e.get('event') == 'knee_step'))
        self.assertAlmostEqual(res['knee'], -0.125, places=3)

    # ---- noise and drift
    def test_slow_drift_does_not_move_the_knee(self):
        self.drift = 2.3
        self.start_recording_and_knee()
        self.run_print(400)
        res = self.result(self.events())
        self.assertAlmostEqual(res['knee'], -0.125, delta=0.002)

    def test_noisy_load_cell_threshold_follows_the_noise(self):
        # 6 g of noise per reading: single steps wander enough that a fixed
        # 12 g rule could fire early; the threshold is set from the noise
        self.noise = 6.
        self.start_recording_and_knee(HOLD_MAX='30')
        self.run_print(900)
        r = self.events(); res = self.result(r)
        self.assertEqual(res['reason'], 'knee')
        self.assertAlmostEqual(res['knee'], -0.125, delta=0.006)
        rises = [e['rise'] for e in r if e.get('event') == 'knee_step' and e.get('noise') is not None]
        self.assertTrue(rises and min(rises) >= 6.)

    def test_quiet_steps_are_short_noisy_steps_are_longer(self):
        def step_lengths(noise):
            self.setUp(); self.noise = noise
            self.start_recording_and_knee(HOLD_MAX='40')
            self.run_print(1200)
            r = self.events()
            return [e.get('readings') for e in r if e.get('event') == 'knee_step' and e.get('readings') and not e.get('skipped')]
        quiet = step_lengths(0.); noisy = step_lengths(15.)
        self.assertLess(sum(quiet) / len(quiet), sum(noisy) / len(noisy))

    def test_a_single_spike_is_not_taken_for_the_knee(self):
        self.spike = (0.05, 15.)
        self.start_recording_and_knee()
        self.run_print(400)
        self.assertAlmostEqual(self.result(self.events())['knee'], -0.125, delta=0.001)

    # ---- safety
    def test_force_limit_stops_at_once(self):
        self.jump = 200.
        self.start_recording_and_knee()
        self.run_print(400)
        res = self.result(self.events())
        self.assertEqual(res['reason'], 'force limit'); self.assertAlmostEqual(res['knee'], -0.13)
        self.assertAlmostEqual(self.gm['homing_origin'][2], -0.105, places=4)

    def test_no_knee_within_travel_restores_the_offset(self):
        self.knee_at = -5.
        self.start_recording_and_knee(TRAVEL='0.15')
        self.run_print(400)
        self.assertTrue(self.result(self.events())['reason'].startswith('no knee within'))
        self.assertAlmostEqual(self.gm['homing_origin'][2], 0.0, places=4)

    def test_layer_2_before_a_knee_restores_the_offset(self):
        self.knee_at = -5.
        self.start_recording_and_knee()
        self.run_print(20)
        self.run_print(5, layer=2)
        self.assertIsNone(self.cell.knee)
        self.assertAlmostEqual(self.gm['homing_origin'][2], 0.0, places=4)

    def test_abort_restores_the_offset(self):
        self.start_recording_and_knee()
        self.run_print(30)
        self.cell.cmd_KNEE_ABORT(Command())
        self.assertIsNone(self.cell.knee)
        self.assertAlmostEqual(self.gm['homing_origin'][2], 0.0, places=4)

    def test_refused_outside_the_first_layer(self):
        with self.assertRaises(RuntimeError):
            self.cell.cmd_KNEE(ArmCommand(HOLD='3'))

    def test_search_steps_are_not_labelled_as_your_babysteps(self):
        self.start_recording_and_knee()
        self.run_print(400)
        r = self.events()
        self.assertEqual([e for e in r if e.get('event') == 'adjustment_label' and e.get('label') in ('TOO_HIGH', 'TOO_LOW')], [])

    def test_arm_waits_for_the_first_layer(self):
        self.cell.cmd_KNEE(ArmCommand(ARM='1', HOLD='3'))
        self.assertEqual(self.cell.knee['phase'], 'wait')
        self.arm(); self.run_print(1.0)
        self.assertEqual(self.cell.knee['phase'], 'wait')
        self.run_print(6.0)
        self.assertEqual(self.cell.knee['phase'], 'down')

    # ---- margin learning
    def finish_layer_with(self, babystep):
        if babystep:
            before = list(self.gm['homing_origin']); self.gm['homing_origin'][2] = round(self.gm['homing_origin'][2] + babystep, 6)
            self.cell._label_adjustment(before, list(self.gm['homing_origin']))
        self.run_print(10)
        self.run_print(5, layer=2)          # layer 2: recording ends, the margin is learned

    def margins(self):
        p = Path(self.cell.knee_margin_file)
        return json.loads(p.read_text()) if p.exists() else {}

    def test_margin_learned_from_what_you_keep(self):
        self.start_recording_and_knee()
        self.run_print(400)
        self.assertIsNone(self.cell.knee)
        self.finish_layer_with(+0.02)        # the first layer looked too close: 0.02 up
        m = self.margins()['pla_0.20']
        self.assertEqual(m['n'], 1)
        self.assertAlmostEqual(m['last_observed'], 0.045, places=3)          # kept 0.045 above the knee
        self.assertAlmostEqual(m['margin'], 0.025 + 0.5 * (0.045 - 0.025), places=3)

    def test_no_babystep_after_the_search_learns_nothing(self):
        self.start_recording_and_knee()
        self.run_print(400)
        self.finish_layer_with(None)
        self.assertEqual(self.margins(), {})

    def test_the_next_search_uses_the_learned_margin(self):
        Path(self.cell.knee_margin_file).write_text(json.dumps({'pla_0.20': {'margin': 0.04, 'n': 3}}))
        self.start_recording_and_knee()
        self.run_print(400)
        res = self.result(self.events())
        self.assertAlmostEqual(res['margin'], 0.04)
        self.assertIn('learned from 3 prints', res['margin_source'])
        self.assertAlmostEqual(self.gm['homing_origin'][2], res['knee'] + 0.04, places=4)

    def test_margin_on_the_command_is_used_and_not_learned(self):
        self.start_recording_and_knee(MARGIN='0.05')
        self.run_print(400)
        self.finish_layer_with(+0.02)
        self.assertEqual(self.margins(), {})

    def test_margin_command_shows_sets_adjusts_and_resets(self):
        c = Command(); self.cell.cmd_KNEE_MARGIN(c)
        self.assertIn('no learned knee margins yet', c.messages[-1])
        self.cell.cmd_KNEE_MARGIN(ArmCommand(MATERIAL='PETG', HEIGHT='0.2', MARGIN='0.03'))
        self.assertAlmostEqual(self.margins()['petg_0.20']['margin'], 0.03)
        self.cell.cmd_KNEE_MARGIN(ArmCommand(MATERIAL='PETG', HEIGHT='0.2', ADJUST='0.01'))
        self.assertAlmostEqual(self.margins()['petg_0.20']['margin'], 0.04)
        c = Command(); self.cell.cmd_KNEE_MARGIN(c)
        self.assertIn('PETG 0.20: 0.0400', c.messages[-1])
        self.cell.cmd_KNEE_MARGIN(ArmCommand(MATERIAL='PETG', HEIGHT='0.2', RESET='1'))
        self.assertNotIn('petg_0.20', self.margins())

if __name__ == '__main__':
    unittest.main()
