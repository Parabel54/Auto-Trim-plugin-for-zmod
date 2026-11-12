import types
import unittest
import test_soak_popup as popup
import test_preparation as preparation
class TwoSpeedTests(unittest.TestCase):
    def test_two_actual_native_calls_have_requested_speeds(self):
        obj,events=popup.SoakPopupTests().fixture()
        self.assertEqual(obj._measure_soak_point(2,.02,0),-3.4)
        calls=[event[1] for event in events if event[0]=='run']
        self.assertEqual([float(c['PROBE_SPEED']) for c in calls],[1.,1.])
        self.assertEqual([c['SAMPLES'] for c in calls],['1','1'])
        self.assertEqual(sum(event[0]=='closed' for event in events),2)
    def test_macro_defaults_and_overrides(self):
        for opts,expected in (({},(1.,1.)),({'PROBE_SPEED':2,'SECOND_PROBE_SPEED':.75},(2.,.75))):
            r=preparation.Runtime();r.p['print_stats']['state']='standby'
            r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict({'BED':60},**opts))
            c=r.p['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE']
            self.assertEqual((c['probe_speed'],c['second_probe_speed']),expected)
    def test_invalid_speed_rejected_before_motion(self):
        for opts in ({'PROBE_SPEED':'nan'},{'SECOND_PROBE_SPEED':0},{'PROBE_SPEED':float('inf')}):
            r=preparation.Runtime();r.p['print_stats']['state']='standby'
            with self.assertRaises(RuntimeError):r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict({'BED':60},**opts))
            self.assertEqual(r.lines,[])
    def test_retract_keeps_native_distance_and_lift_speed(self):
        obj,events=popup.SoakPopupTests().fixture();moves=[]
        original=obj.printer.lookup_object
        th=types.SimpleNamespace(get_position=lambda:[12,13,5,0],manual_move=lambda p,s:moves.append((p,s)))
        obj.printer.lookup_object=lambda name:th if name=='toolhead' else original(name)
        obj._measure_soak_point(2,.02,0)
        self.assertEqual(moves,[([12,13,7],5)])
