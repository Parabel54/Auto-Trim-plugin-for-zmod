import json, unittest
from unittest import mock
from types import SimpleNamespace
import test_capture as capture
from test_capture import Command
import test_knee as knee_tests
ArmCommand = knee_tests.ArmCommand

class Beta10PolicyTests(unittest.TestCase):
    def setUp(self):
        self.f = capture.CaptureTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.c = self.f.cell
        self.c.poll_accelerate = True
        self.c.reader.poll_time = .07
        self.c.reader.poll_wait = .02
        self.c.reader.cmd_LOAD_CELL_POLL = lambda cmd: None

    def start(self):
        self.f.feed()
        self.c.cmd_START(Command(RUN='beta10', ACCEL=0, ADC=0))
        self.addCleanup(lambda: self.c._end('test_cleanup'))

    def test_poll_start_and_restore_previous_not_hardcoded(self):
        self.start()
        self.assertEqual(self.c.reader.poll_time, 0)
        self.assertEqual(self.c.reader.poll_wait, .02)
        self.c.cmd_STOP(Command())
        self.assertEqual(self.c.reader.poll_time, .07)
        self.assertEqual(self.c.reader.poll_wait, .02)

    def test_unpatched_reader_is_untouched(self):
        del self.c.reader.cmd_LOAD_CELL_POLL
        self.start()
        self.assertEqual(self.c.reader.poll_time, .07)
        self.assertIsNone(self.c.poll_saved)

    def test_poll_policy_opt_out(self):
        self.c.poll_accelerate = False
        self.start()
        self.assertEqual(self.c.reader.poll_time, .07)

    def test_sensor_start_error_does_not_change_pause(self):
        with mock.patch.object(self.c.sensors, 'start', side_effect=RuntimeError('sensor')):
            with self.assertRaises(RuntimeError): self.start()
        self.assertEqual(self.c.reader.poll_time, .07)

    def test_shutdown_restores(self):
        self.start(); self.c._shutdown()
        self.assertEqual(self.c.reader.poll_time, .07)

    def test_write_failure_restores(self):
        self.start()
        with mock.patch.object(self.c.writer, 'put', return_value=False): self.c._write({'type':'test'})
        self.assertEqual(self.c.reader.poll_time, .07)

    def test_stop_failure_still_restores_pause(self):
        self.start()
        with mock.patch.object(self.c.sensors, 'stop', side_effect=RuntimeError('stop')):
            with self.assertRaises(RuntimeError):self.c._end('test')
        self.assertEqual(self.c.reader.poll_time, .07)

    def test_recipe_key_separates_equal_flow_dimensions(self):
        self.c.recipe = dict(material='PLA',height=.2,width=.5,speed=40)
        key = self.c._knee_key()
        self.c.recipe.update(height=.1,speed=80)
        self.assertNotEqual(self.c._knee_key(),key)
        self.c.recipe.update(speed=40)
        self.assertNotEqual(self.c._knee_key(),key)
        self.assertNotEqual(self.c._knee_key('PETG'),key)
        self.c.recipe = dict(material='PLA',height=.2,width=.5,speed=40,filament=2.85)
        self.assertNotEqual(self.c._knee_key(),key)

    def knee_fixture(self):
        f=knee_tests.KneeTests();f.setUp();self.addCleanup(f.doCleanups)
        return f

    def test_legacy_height_margin_not_reused(self):
        f=self.knee_fixture();f.cell.knee_require_margin=True
        from pathlib import Path
        Path(f.cell.knee_margin_file).write_text(json.dumps({'pla_0.20':{'margin':.125,'n':9}}))
        with self.assertRaisesRegex(ValueError,'Uncalibrated flow'):
            f.start_recording_and_knee()
        self.assertIsNone(f.cell.knee)
        self.assertEqual(f.scripts,[])
        f.close()

    def test_explicit_margin_satisfies_new_policy(self):
        f=self.knee_fixture();f.cell.knee_require_margin=True
        f.start_recording_and_knee(MARGIN='.0075',CONFIRM='0');f.run_print(400)
        r=f.result(f.events())
        self.assertAlmostEqual(r['target']-r['knee'],.0075,places=4)

    def test_up_fit_cannot_move_down_estimate(self):
        f=self.knee_fixture();f.start_recording_and_knee();f.run_print(400)
        r=f.result(f.events())
        self.assertEqual(r['knee'],r['knee_down'])
        self.assertEqual(r['estimate_source'],'descending_only')

    def test_upward_settle_and_hold_are_longer(self):
        self.c.knee=dict(cfg=dict(self.c.knee_cfg),phase='up',readings=[],window=[0,20],ref=None)
        self.c._knee_next_window(0)
        self.assertGreaterEqual(self.c.knee['window'][0],6)
        self.c.knee['readings']=[0]*100
        self.assertEqual(self.c._knee_measure(10),'wait')

    def test_fast_hold_requires_actual_samples(self):
        self.c.poll_saved=(self.c.reader,.07)
        self.c.knee=dict(cfg=dict(self.c.knee_cfg),phase='down',readings=[0]*20,window=[0,20],ref=None)
        self.assertIsInstance(self.c._knee_measure(2),tuple)
        self.c.knee.update(readings=[0]*5,ref=None)
        self.assertEqual(self.c._knee_measure(2),'wait')

    def test_bad_explicit_margins_rejected_before_motion(self):
        for v in ['nan','inf','-0.01','.31']:
            with self.assertRaises(RuntimeError):self.c.cmd_KNEE(ArmCommand(MARGIN=v))

class RecipeDimensionsTests(unittest.TestCase):
    def setUp(self):
        self.f=capture.CaptureTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.c=self.f.cell

    def test_manual_key_matches_capture_recipe(self):
        self.c.recipe=dict(material='PLA',height=.2,width=.5,speed=110,filament=1.75)
        self.c.cmd_KNEE_MARGIN(ArmCommand(MATERIAL='PLA',HEIGHT=.2,WIDTH=.5,SPEED=110,FLOW=11,MARGIN=.0075))
        self.assertIn(self.c._knee_key(),self.c._knee_margins())

    def test_flow_only_input_refused_without_changing_saved_data(self):
        with self.assertRaises(RuntimeError):self.c.cmd_KNEE_MARGIN(ArmCommand(MATERIAL='PLA',FLOW=11,MARGIN=.0075))
        self.assertEqual(self.c._knee_margins(),{})

    def test_inconsistent_flow_refused(self):
        with self.assertRaises(RuntimeError):self.c.cmd_KNEE_MARGIN(ArmCommand(MATERIAL='PLA',HEIGHT=.2,WIDTH=.5,SPEED=110,FLOW=4,MARGIN=.0075))

if __name__=='__main__':unittest.main()
