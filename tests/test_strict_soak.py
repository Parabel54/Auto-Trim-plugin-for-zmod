"""Real-log replay and strict acceptance/cleanup checks; no printer hardware."""
import ast
import collections
from pathlib import Path
import types
import unittest
from test_preparation import Runtime, T

C='gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE'
class StrictSoakTests(unittest.TestCase):
    def fixture(self,**kw):
        r=Runtime();r.p['print_stats']['state']='standby'
        r.p['heater_bed'].update(target=60,temperature=60)
        r.p['extruder'].update(target=121,temperature=121)
        r.p[C].update(running=True,bed=60,nozzle=121,t0=10,**kw)
        return r
    def feed(self,r,t,values):
        r.p[C]['cur']=values
        r.run('_DEEP_CALIBRATION_SOAK_EVAL',{'T':t})
    def test_previous_920_second_field_run_is_not_accepted(self):
        r=self.fixture()
        times=[55,200,289,380,470,560,650,740,830,920]
        points=[[-3.405833,-3.414167,-3.4125,-3.413333,-3.409167,-3.4175,-3.410833,-3.415,-3.41,-3.414167],
                [-3.455,-3.471667,-3.464167,-3.4675,-3.458333,-3.4725,-3.4625,-3.463333,-3.465,-3.473333],
                [-3.223333,-3.235,-3.233333,-3.229167,-3.2325,-3.230833,-3.254167,-3.2375,-3.235833,-3.243333],
                [-3.3775,-3.384167,-3.390833,-3.381667,-3.404167,-3.3825,-3.388333,-3.385,-3.389167,-3.375833],
                [-3.591667,-3.5925,-3.580833,-3.573333,-3.571667,-3.5675,-3.58,-3.5725,-3.5825,-3.575]]
        for t,values in zip(times,zip(*points)):self.feed(r,t,list(values))
        self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.assertFalse(r.p[C]['last_good']);self.assertEqual(r.p[C]['confirm_count'],0)
    def test_constant_points_save_actual_confirmation_time_not_earliest_time(self):
        r=self.fixture()
        for t in range(90,721,90):self.feed(r,t,[-3.4]*5)
        self.assertEqual(r.p[C]['confirm_count'],1);self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.feed(r,810.2,[-3.4]*5)
        v=r.p['save_variables']['variables']
        self.assertEqual(v['soak_t60'],811);self.assertEqual(v['soak_t60_corners'],811)
        self.assertEqual(v['soak_t60_method'],2);self.assertEqual(v['soak_t60_points'],5)
        self.assertFalse(r.p[C]['running'])
        saves=[s for s in r.lines if s.startswith('SAVE_VARIABLE')]
        self.assertIn('_method VALUE=0',saves[0]);self.assertIn('_method VALUE=2',saves[-1])
        self.assertLess(r.lines.index('M140 S0'),r.lines.index(saves[0]))
    def test_slow_trend_rejected_even_inside_range_limit(self):
        r=self.fixture(drift_limit=.0002)
        for i,t in enumerate(range(90,901,90)):self.feed(r,t,[-3.4+i*.0006]*5)
        self.assertEqual(r.count('SAVE_VARIABLE'),0);self.assertFalse(r.p[C]['last_good'])
    def test_outlier_resets_confirmation_without_smoothing_it_away(self):
        r=self.fixture()
        for t in range(90,721,90):self.feed(r,t,[-3.4]*5)
        self.assertEqual(r.p[C]['confirm_count'],1)
        self.feed(r,810,[-3.4,-3.4,-3.38,-3.4,-3.4])
        self.assertEqual(r.p[C]['confirm_count'],0);self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_missing_rounds_and_reversed_time_cannot_pass(self):
        for times in ([90,180,270,630,720,810],[900,810,720,630,540,450,360,270,180,90]):
            r=self.fixture()
            for t in times:self.feed(r,t,[-3.4]*5)
            self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_timeout_preserves_prior_accepted_result(self):
        r=self.fixture(max=700)
        old=dict(r.p['save_variables']['variables'])
        for t in range(90,721,90):self.feed(r,t,[-3.4]*5)
        self.assertEqual(r.p['save_variables']['variables'],old)
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['heater_bed']['target'],0)
    def test_auto_rejects_legacy_or_missing_calibration_before_actions(self):
        for key in ('soak_t60_method','soak_t60_points','soak_t60'):
            r=Runtime();r.p['save_variables']['variables'].pop(key)
            with self.assertRaises(RuntimeError):r.start()
            self.assertEqual(r.lines,[])
    def test_elapsed_time_uses_host_clock_not_planner_clock(self):
        r=self.fixture();r.p['deep_calibration']['host_time']=650
        r.p['toolhead']['estimated_print_time']=999999
        r.p[C]['cur']=[-3.4]*5
        script=T['gcode_macro _DEEP_CALIBRATION_SOAK_EVAL'].render(printer=r.p,params={})
        self.assertIn('640.0',script);self.assertNotIn('999989',script)
    def test_native_probe_receives_median_and_repeatability_parameters(self):
        r=self.fixture();r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        command=next(s for s in r.lines if s.startswith('PROBE '))
        self.assertIn('SAMPLES=2',command);self.assertIn('SAMPLES_RESULT=median',command)
        self.assertIn('SAMPLES_TOLERANCE=0.010000100',command)
        self.assertIn('SAMPLES_TOLERANCE_RETRIES=3',command)
    def test_probe_failure_stops_calibration_and_turns_off_heaters(self):
        r=self.fixture();original=r.run_lines
        def fail(script):
            if script.startswith('LOAD_CELL_TARE'):raise RuntimeError('native tolerance failed')
            original(script)
        r.probe_helper.gcode.run_script_from_command=fail
        with self.assertRaisesRegex(RuntimeError,'nothing saved'):r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['heater_bed']['target'],0)
        self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_bad_temperature_pauses_measurement_without_heater_shutdown(self):
        r=self.fixture();r.p['heater_bed']['temperature']=55
        r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertEqual(r.count('PROBE'),0);self.assertEqual(r.p['extruder']['target'],121)
        self.assertTrue(r.p[C]['running']);self.assertFalse(r.p[C]['point_valid'])
    def test_print_interruption_does_not_turn_off_print_heaters(self):
        r=self.fixture();r.p['print_stats']['state']='printing'
        with self.assertRaises(RuntimeError):r.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
        self.assertFalse(r.p[C]['running']);self.assertEqual(r.p['heater_bed']['target'],60)
        self.assertEqual(r.p['extruder']['target'],121)

class SuppliedProbeTests(unittest.TestCase):
    def native(self,values):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'reference/probe.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='calc_probe_z_average')
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SampleAveragingHelper')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run_probe')
        result_type=collections.namedtuple('ProbeResult','bed_x bed_y bed_z')
        ns={'manual_probe':types.SimpleNamespace(ProbeResult=result_type)}
        exec(compile(ast.Module(body=[fn,method],type_ignores=[]),'supplied_probe','exec'),ns)
        moves=[];toolhead=types.SimpleNamespace(get_position=lambda:[0,0,5],manual_move=lambda *args:moves.append(args))
        it=iter(values)
        obj=types.SimpleNamespace(hw_probe_session=True,results=[],
            printer=types.SimpleNamespace(lookup_object=lambda name:toolhead),
            param_helper=types.SimpleNamespace(get_probe_params=lambda cmd:dict(samples=5,samples_result='median',samples_tolerance=.0100001,samples_tolerance_retries=3,sample_retract_dist=2,lift_speed=5)),
            _probe=lambda cmd:result_type(0,0,next(it)))
        cmd=types.SimpleNamespace(error=RuntimeError,respond_info=lambda m:None)
        return lambda:ns['run_probe'](obj,cmd),obj,moves
    def test_real_native_helper_rejects_noisy_probe_and_bounds_retries(self):
        run,obj,moves=self.native([0,.02]*20)
        with self.assertRaisesRegex(RuntimeError,'exceed'):run()
        self.assertEqual(obj.results,[]);self.assertLessEqual(len(moves),8)
    def test_real_native_helper_accepts_repeatable_median(self):
        run,obj,moves=self.native([-.003,.001,0,.004,.002]);run()
        self.assertAlmostEqual(obj.results[0].bed_z,.001);self.assertEqual(len(moves),4)

if __name__=='__main__':unittest.main()
