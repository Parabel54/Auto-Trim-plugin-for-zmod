import unittest
import types
from deep_calibration_mesh import evaluate_soak_points
import test_strict_soak as strict
C=strict.C
class IndependentSoakTests(unittest.TestCase):
    def fixture(self):return strict.StrictSoakTests().fixture()
    def feed(self,r,t,values):strict.StrictSoakTests().feed(r,t,values)
    def test_rejected_point_retains_all_other_raw_observations(self):
        r=self.fixture()
        for t in range(90,721,90):self.feed(r,t,[-3.4]*4+[None])
        self.assertEqual(len(r.p[C]['rows']),8)
        self.assertTrue(all(p['valid'] for p in r.p[C]['point_status'][:4]))
        self.assertFalse(r.p[C]['point_status'][4]['valid']);self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_alternating_bad_locations_can_build_independent_windows(self):
        r=self.fixture()
        for i,t in enumerate(range(90,901,90)):
            values=[-3.4]*5;values[i%5]=None;self.feed(r,t,values)
        self.assertEqual(len(r.p[C]['rows']),10);self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.feed(r,990,[-3.4]*5);self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.feed(r,1080,[-3.4]*5)
        self.assertEqual(r.p[C]['last_result'],'ACCEPTED_STRICT')
    def test_long_gap_at_one_point_does_not_invalidate_other_point(self):
        rows=[[t,-3.4,(-3.4 if t in (90,810) else None)] for t in range(90,811,90)]
        p=evaluate_soak_points(rows,2,90,600,6,.02,.001)
        self.assertTrue(p[0]['valid']);self.assertFalse(p[1]['valid'])
    def test_old_anchor_cannot_fake_recent_coverage(self):
        rows=[[90,-3.4]]+[[t,-3.4] for t in range(900,1441,90)]
        self.assertFalse(evaluate_soak_points(rows,1,90,600,6,.02,.001)[0]['valid'])
    def test_current_rejected_touch_cannot_use_stale_success(self):
        rows=[[t,-3.4] for t in range(90,721,90)]+[[810,None]]
        self.assertFalse(evaluate_soak_points(rows,1,90,600,6,.02,.001)[0]['valid'])
    def test_timeout_has_no_error_and_preserves_old_result(self):
        r=self.fixture();before=dict(r.p['save_variables']['variables'])
        r.p[C]['t0']=-3000
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['heater_bed']['target'],0)
        self.assertEqual(r.p['save_variables']['variables'],before)
        self.assertEqual(r.p[C]['last_result'],'TIMEOUT_OR_UNVERIFIED')
        self.assertTrue(any('MAX reached' in line for line in r.lines))
        n=r.count('PROBE');r.run('_DEEP_CALIBRATION_SOAK_POINT',dict(X=30,Y=30));self.assertEqual(r.count('PROBE'),n)
    def test_normal_round_schedules_next_with_string_gcode_parameters(self):
        r=self.fixture();r.run('_DEEP_CALIBRATION_SOAK_ROUND')
        self.assertTrue(any(line.startswith('UPDATE_DELAYED_GCODE') and 'DURATION=0' not in line for line in r.lines))
