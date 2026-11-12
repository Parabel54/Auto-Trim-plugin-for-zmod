"""Changing/noisy early rounds must not abort or certify a stable window."""
import types
import unittest
import test_strict_soak as strict
C=strict.C
class SoakRecoveryTests(unittest.TestCase):
    def fixture(self,**kw):return strict.StrictSoakTests().fixture(**kw)
    def feed(self,r,t,values):return strict.StrictSoakTests().feed(r,t,values)
    def test_large_early_movement_then_stable_window_accepts_later(self):
        r=self.fixture()
        for i,t in enumerate(range(90,541,90)):
            self.feed(r,t,[-3.4-i*.04]*5)
            self.assertTrue(r.p[C]['running']);self.assertEqual(r.count('SAVE_VARIABLE'),0)
        for t in range(630,1441,90):
            self.feed(r,t,[-3.6]*5)
            if not r.p[C]['running']:break
        self.assertEqual(r.p[C]['last_result'],'ACCEPTED_STRICT')
        self.assertGreater(r.p['save_variables']['variables']['soak_t60'],1100)
    def test_tolerance_failure_is_recoverable_but_stale_probe_not_recorded(self):
        r=self.fixture();original=r.run_lines
        def fail(script):
            if script.startswith('LOAD_CELL_TARE'):raise RuntimeError('Probe samples exceed samples_tolerance')
            original(script)
        r.probe_helper.gcode.run_script_from_command=fail
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertTrue(r.p[C]['running']);self.assertFalse(r.p[C]['point_valid'])
        r.run('_DEEP_CALIBRATION_SOAK_REC')
        self.assertEqual(r.p[C]['cur'],[None]);self.assertEqual(r.p['heater_bed']['target'],60)
    def test_failed_round_finishes_remaining_points_and_schedules_next(self):
        r=self.fixture();original=r.run_lines;calls=[]
        def fail_once(script):
            if script.startswith('LOAD_CELL_TARE'):
                calls.append(script)
                if len(calls)==1:raise RuntimeError('Probe samples exceed samples_tolerance')
            original(script)
        r.probe_helper.gcode.run_script_from_command=fail_once
        r.run('_DEEP_CALIBRATION_SOAK_ROUND')
        self.assertEqual(len(calls),5);self.assertTrue(r.p[C]['running'])
        self.assertEqual(len(r.p[C]['rejected_rounds']),1)
        self.assertIsNone(r.p[C]['rejected_rounds'][0][1])
        self.assertEqual(len(r.p[C]['rows']),1)
        self.assertTrue(any('DURATION=0' not in x and x.startswith('UPDATE_DELAYED_GCODE') for x in r.lines))
        r.run('_DEEP_CALIBRATION_SOAK_ROUND')
        self.assertTrue(r.p[C]['running']);self.assertEqual(len(r.p[C]['rows']),2)
    def test_rejected_point_does_not_reset_other_locations(self):
        r=self.fixture()
        for t in range(90,721,90):self.feed(r,t,[-3.4]*5)
        self.feed(r,810,[None,-3.4,-3.4,-3.4,-3.4])
        self.assertEqual([p['valid'] for p in r.p[C]['point_status']],[False,True,True,True,True])
        self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.feed(r,900,[-3.4]*5);self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.feed(r,990,[-3.4]*5)
        self.assertEqual(r.p[C]['last_result'],'ACCEPTED_STRICT')
    def test_all_rounds_rejected_until_max_preserves_old_result(self):
        r=self.fixture(max=900);old=dict(r.p['save_variables']['variables'])
        for t in range(90,901,90):self.feed(r,t,[None]*5)
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['heater_bed']['target'],0)
        self.assertEqual(old,r.p['save_variables']['variables']);self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_other_probe_error_still_aborts(self):
        r=self.fixture();original=r.run_lines
        def fail(script):
            if script.startswith('LOAD_CELL_TARE'):raise RuntimeError('No trigger on probe after full movement')
            original(script)
        r.probe_helper.gcode.run_script_from_command=fail
        with self.assertRaisesRegex(RuntimeError,'No trigger'):r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['extruder']['target'],0)
if __name__=='__main__':unittest.main()
