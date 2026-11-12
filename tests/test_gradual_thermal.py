import unittest
import types
import test_strict_soak as strict
C=strict.C
class GradualThermalTests(unittest.TestCase):
    def fixture(self):return strict.StrictSoakTests().fixture()
    def thermal(self,r,t):
        r.p['toolhead']['estimated_print_time']=r.p[C]['t0']+t
        return r.probe_helper._soak_thermal_state(r.p[C])
    def test_band_tapers_from_three_to_one_over_five_minutes(self):
        r=self.fixture()
        self.assertEqual([self.thermal(r,t)['band'] for t in (0,150,300,600)],[3.,2.,1.,1.])
    def test_warmup_reading_can_be_measured_but_is_not_stability_evidence(self):
        r=self.fixture();r.p[C]['npts']=1;r.p['heater_bed']['temperature']=62.5
        s=self.thermal(r,0);self.assertTrue(s['collect']);self.assertFalse(s['eligible'])
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertTrue(r.p[C]['running']);self.assertTrue(r.p[C]['point_measured']);self.assertFalse(r.p[C]['point_valid'])
        r.run('_DEEP_CALIBRATION_SOAK_REC');r.run('_DEEP_CALIBRATION_SOAK_EVAL',dict(T=1))
        self.assertIsNone(r.p[C]['rows'][0][1]);self.assertEqual(r.p[C]['raw_rows'][0][1],-2.)
        self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_outside_current_band_waits_without_probing_or_switching_heaters_off(self):
        r=self.fixture();r.p['heater_bed']['temperature']=64
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertEqual(r.count('PROBE'),0);self.assertTrue(r.p[C]['running'])
        self.assertEqual(r.p['heater_bed']['target'],60)
    def test_overshoot_after_grace_also_waits_and_can_recover(self):
        r=self.fixture();self.thermal(r,400);r.p['heater_bed']['temperature']=61.5
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertEqual(r.count('PROBE'),0);self.assertTrue(r.p[C]['running'])
        r.p['heater_bed']['temperature']=60.3
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertEqual(r.count('PROBE'),1);self.assertTrue(r.p[C]['point_valid'])
    def test_temperature_leaving_final_band_during_touch_excludes_result(self):
        r=self.fixture();measure=r.probe_helper._measure_soak_point
        def drift(*args):
            value=measure(*args);r.p['heater_bed']['temperature']=62.;return value
        r.probe_helper._measure_soak_point=drift
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertTrue(r.p[C]['point_measured']);self.assertFalse(r.p[C]['point_valid'])
    def test_target_change_still_aborts_and_reports_actual_target(self):
        r=self.fixture();r.p['heater_bed']['target']=0
        with self.assertRaisesRegex(RuntimeError,'target changed: 0.00 C'):
            r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['extruder']['target'],0)
    def test_nonfinite_sensor_still_aborts(self):
        r=self.fixture();r.p['heater_bed']['temperature']=float('nan')
        with self.assertRaisesRegex(RuntimeError,'invalid temperature'):
            r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertFalse(r.p[C]['running'])
    def test_nozzle_outside_band_waits_and_is_not_accepted(self):
        r=self.fixture();r.p['extruder']['temperature']=125
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertEqual(r.count('PROBE'),0);self.assertTrue(r.p[C]['running'])
    def test_repeated_temperature_exclusions_cannot_save(self):
        r=self.fixture();old=dict(r.p['save_variables']['variables'])
        for t in range(90,1081,90):strict.StrictSoakTests().feed(r,t,[None]*5)
        self.assertEqual(r.count('SAVE_VARIABLE'),0);self.assertEqual(old,r.p['save_variables']['variables'])
    def test_zero_grace_selects_final_band_immediately(self):
        r=self.fixture();r.p[C]['temp_grace']=0
        self.assertEqual(self.thermal(r,0)['band'],1.)
    def test_invalid_macro_guard_parameters_rejected_before_actions(self):
        for opts in ({'BED_BAND_START':.5},{'BED_BAND_FINAL':'nan'},{'TEMP_GRACE':-1},{'TEMP_GRACE':float('inf')}):
            r=self.fixture();r.p[C]['running']=False;r.p['heater_bed']['temperature']=20
            with self.assertRaises(RuntimeError):r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict({'BED':60},**opts))
            self.assertEqual(r.lines,[])
