import unittest
import test_preparation as prep
import test_strict_soak as strict
class TwoTouchTests(unittest.TestCase):
    def test_public_macro_accepts_two_and_rejects_one(self):
        r=prep.Runtime();r.p['print_stats']['state']='standby'
        r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict(BED=60,SAMPLES=2,RETRIES=0))
        self.assertEqual(r.p['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE']['samples'],2)
        r=prep.Runtime();r.p['print_stats']['state']='standby'
        with self.assertRaises(RuntimeError):r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict(BED=60,SAMPLES=1))
    def test_supplied_native_two_touch_median_and_tolerance(self):
        run,obj,moves=strict.SuppliedProbeTests().native([0,.005])
        original=obj.param_helper.get_probe_params
        obj.param_helper.get_probe_params=lambda cmd:dict(original(cmd),samples=2,samples_tolerance_retries=0)
        run();self.assertAlmostEqual(obj.results[0].bed_z,.0025);self.assertEqual(len(moves),1)
        run,obj,moves=strict.SuppliedProbeTests().native([0,.02])
        original=obj.param_helper.get_probe_params
        obj.param_helper.get_probe_params=lambda cmd:dict(original(cmd),samples=2,samples_tolerance_retries=0)
        with self.assertRaisesRegex(RuntimeError,'exceed'):run()
