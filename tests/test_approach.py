import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace as S

spec=importlib.util.spec_from_file_location('approach',Path(__file__).resolve().parents[1]/'deep_calibration_approach.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Command:
    def __init__(self, name='PROBE', params=None): self.name=name;self.params=params or {'PROBE_SPEED':'5','SAMPLES':'2'}
    def get_command_parameters(self): return self.params
    def get_command(self): return self.name
    def get_commandline(self): return self.name+' PROBE_SPEED=5'

class ApproachTests(unittest.TestCase):
    def fixture(self):
        o=m.DeepCalibrationApproach.__new__(m.DeepCalibrationApproach)
        o.fast_speed=5.;o.clearance=1.;o.max_age=300.;o.references={}
        o.fast_moves=o.slow_only=o.early_contacts=0;o.last_mode='ready';o.installed=False
        o.clock=10.;o.reactor=S(monotonic=lambda:o.clock)
        o.pos=[100.,100.,5.,0.];o.homed='xyz';o.trigger=False;o.events=[]
        th=S(get_position=lambda:list(o.pos),get_status=lambda t:dict(homed_axes=o.homed),get_last_move_time=lambda:100.)
        end=S(query_endstop=lambda t:o.trigger)
        def measured(c):
            o.events.append(('slow',c.get_command(),c.params))
            if o.trigger:raise RuntimeError('Probe triggered prior to movement')
            o.pos[2]=-3.5
        helper=S(mcu_probe=end,descend_until_trigger=measured)
        o.original=measured;o.helper=helper
        def fast(toolhead,endstops,goal,speed,**kwargs):
            o.events.append(('fast',goal,speed,kwargs));o.pos[:]=goal;return list(goal)
        homing=S(manual_home=fast)
        probe=S(mcu_probe=S(homing_helper=helper),param_helper=S(speed=5.))
        o.objects={'toolhead':th,'homing':homing,'probe':probe}
        o.printer=S(lookup_object=lambda n:o.objects[n],command_error=RuntimeError,config_error=RuntimeError)
        o.gcode=S(create_gcode_command=lambda name,line,p:Command(name,p))
        return o
    def test_unknown_reference_entirely_slow(self):
        o=self.fixture();o.descend(Command())
        self.assertEqual([e[0] for e in o.events],['slow'])
        self.assertEqual(o.events[0][2]['PROBE_SPEED'],'1')
        self.assertEqual(len(o.references),1)
    def test_fast_monitored_endpoint_then_measured_slow(self):
        o=self.fixture();o.references[(100,100)]=(5,-3.5);o.descend(Command())
        self.assertEqual([e[0] for e in o.events],['fast','slow'])
        self.assertEqual(o.events[0][1][2],-2.5)
        self.assertEqual(o.events[0][2],5.)
        self.assertEqual(o.events[0][3],dict(probe_pos=True,triggered=True,check_triggered=False))
        self.assertEqual(o.events[1][2]['PROBE_SPEED'],'1')
    def test_new_xy_uses_highest_observed_surface(self):
        o=self.fixture();o.references={(1,2):(5,-3.5),(3,4):(5,-3.1)}
        o.descend(Command());self.assertAlmostEqual(o.events[0][1][2],-2.1)
    def test_stale_reference_falls_back_slow(self):
        o=self.fixture();o.references[(1,2)]=(-400,-3.5);o.descend(Command())
        self.assertEqual([e[0] for e in o.events],['slow'])
    def test_future_reference_not_used(self):
        o=self.fixture();o.references[(1,2)]=(20,-3.5);o.descend(Command())
        self.assertEqual([e[0] for e in o.events],['slow'])
    def test_inside_clearance_never_moves_up_or_fast(self):
        o=self.fixture();o.references[(1,2)]=(5,-3.5);o.pos[2]=-3.
        o.descend(Command());self.assertEqual([e[0] for e in o.events],['slow'])
    def test_homing_always_slow_and_not_cached(self):
        for name in ('G28','G28.1'):
            o=self.fixture();o.references[(1,2)]=(5,-3.5);o.descend(Command(name))
            self.assertEqual([e[0] for e in o.events],['slow']);self.assertEqual(len(o.references),0)
    def test_unhomed_z_never_fast(self):
        o=self.fixture();o.homed='xy';o.references[(1,2)]=(5,-3.5)
        o.original=lambda c:(_ for _ in ()).throw(RuntimeError('Must home'))
        with self.assertRaises(RuntimeError):o.descend(Command())
        self.assertEqual(o.events,[]);self.assertEqual(o.references,{})
    def test_early_contact_aborts_without_native_result(self):
        o=self.fixture();o.references[(1,2)]=(5,-3.5)
        def fast(*a,**kw):return [100,100,-2.,0]
        o.objects['homing'].manual_home=fast
        with self.assertRaisesRegex(RuntimeError,'fast approach'):o.descend(Command())
        self.assertEqual(o.references,{});self.assertEqual(o.early_contacts,1);self.assertEqual(o.events,[])
    def test_pretrigger_rejected_before_fast(self):
        o=self.fixture();o.references[(1,2)]=(5,-3.5);o.trigger=True
        with self.assertRaisesRegex(RuntimeError,'already triggered'):o.descend(Command())
        self.assertEqual(o.events,[]);self.assertEqual(o.references,{})
    def test_endstop_at_boundary_aborts(self):
        o=self.fixture();o.references[(1,2)]=(5,-3.5)
        def fast(th,es,goal,speed,**kw):o.trigger=True;return goal
        o.objects['homing'].manual_home=fast
        with self.assertRaisesRegex(RuntimeError,'fast approach'):o.descend(Command())
        self.assertEqual(o.events,[])
    def test_probe_failure_invalidates_references(self):
        o=self.fixture();o.references[(1,2)]=(5,-3.5)
        o.original=lambda c:(_ for _ in ()).throw(RuntimeError('No trigger'))
        with self.assertRaises(RuntimeError):o.descend(Command())
        self.assertEqual(o.references,{})
    def test_connection_installs_instance_hook_and_default(self):
        o=self.fixture();o._connect();o._connect()
        self.assertTrue(o.installed);self.assertEqual(o.objects['probe'].param_helper.speed,1.)
        o.helper.descend_until_trigger(Command());self.assertEqual(o.events[0][2]['PROBE_SPEED'],'1')
    def test_unsupported_probe_rejected(self):
        o=self.fixture();o.objects['probe']=S()
        with self.assertRaisesRegex(RuntimeError,'requires the reviewed'):o._connect()
        self.assertFalse(o.installed)
    def test_reference_reset(self):
        o=self.fixture();o.references[(1,2)]=(5,-3.5);o.reset('event',[])
        self.assertEqual(o.references,{})
    def test_command_preserves_other_parameters(self):
        o=self.fixture();cmd=Command();o.descend(cmd)
        self.assertEqual(o.events[0][2]['SAMPLES'],'2');self.assertEqual(cmd.params['PROBE_SPEED'],'5')

class NativeHelperIntegrationTests(unittest.TestCase):
    fixture = ApproachTests.fixture
    # Exercise the hook with the unchanged, bundled native descent method.
    def test_native_result_is_created_only_by_slow_final_touch(self):
        import ast
        o=self.fixture()
        source=(Path(__file__).resolve().parents[1]/'reference/probe.py').read_text()
        cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='DescendToEndstopHelper')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='descend_until_trigger')
        ns={'manual_probe':S(create_probe_result=lambda p,offsets:(list(p),offsets))}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'native_probe.py','exec'),ns)
        helper=o.helper
        helper.printer=o.printer;helper.z_min_position=-10.;helper.always_check_movement=False
        helper.param_helper=S(get_probe_params=lambda c:dict(probe_speed=float(c.params['PROBE_SPEED'])))
        helper.probe_offsets=S(get_offsets=lambda:(0,0,-.25));helper.results=[]
        o.objects['homing'].check_probe_first_home=lambda c:False
        def probing(endstop,target,speed,check_movement):
            o.events.append(('native_final',speed,check_movement));o.pos[2]=-3.5
            return list(o.pos)
        o.objects['homing'].probing_move=probing
        o.original=lambda c:ns['descend_until_trigger'](helper,c)
        o.references[(1,2)]=(5,-3.5)
        o.descend(Command())
        self.assertEqual([e[0] for e in o.events],['fast','native_final'])
        self.assertEqual(o.events[-1][1],1.)
        self.assertEqual(len(helper.results),1)
        self.assertEqual(helper.results[0][0][2],-3.5)
        self.assertEqual(helper.results[0][1],(0,0,-.25))

if __name__=='__main__':unittest.main()
