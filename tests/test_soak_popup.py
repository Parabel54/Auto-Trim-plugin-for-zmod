import types
import unittest
from deep_calibration_mesh import DeepCalibrationMesh
class SoakPopupTests(unittest.TestCase):
    def fixture(self,error=None):
        obj=DeepCalibrationMesh.__new__(DeepCalibrationMesh);events=[]
        def run(cmd):
            events.append(('run',cmd))
            if error:raise RuntimeError(error)
        session=types.SimpleNamespace(run_probe=run,pull_probed_results=lambda:[types.SimpleNamespace(bed_z=-3.4)],end_probe_session=lambda:events.append(('closed',True)))
        probe=types.SimpleNamespace(start_probe_session=lambda cmd:session,get_probe_params=lambda cmd:dict(sample_retract_dist=2,lift_speed=5))
        toolhead=types.SimpleNamespace(get_position=lambda:[0,0,5],manual_move=lambda *args:None)
        obj.printer=types.SimpleNamespace(lookup_object=lambda name:probe if name=='probe' else toolhead)
        obj.gcode=types.SimpleNamespace(create_gcode_command=lambda name,line,params:params)
        return obj,events
    def test_native_measurement_returns_contact_and_closes_without_dispatch(self):
        obj,events=self.fixture();self.assertEqual(obj._measure_soak_point(5,.01,3),-3.4)
        self.assertEqual(events[-1],('closed',True));self.assertEqual(events[0][1]['SAMPLES_RESULT'],'median')
    def test_spread_exception_closes_session_without_gcode_error_popup(self):
        obj,events=self.fixture('Probe samples exceed samples_tolerance')
        with self.assertRaisesRegex(RuntimeError,'samples_tolerance'):obj._measure_soak_point(5,.01,3)
        self.assertEqual(events[-1],('closed',True))
    def test_real_fault_also_closes_and_propagates(self):
        obj,events=self.fixture('No trigger on probe after full movement')
        with self.assertRaisesRegex(RuntimeError,'No trigger'):obj._measure_soak_point(5,.01,3)
        self.assertEqual(events[-1],('closed',True))
