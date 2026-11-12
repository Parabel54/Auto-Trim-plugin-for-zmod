import importlib.util, math, pathlib, types, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mesh_audit',ROOT/'deep_calibration_mesh.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Gcode:
 def __init__(self):self.messages=[];self.registered={}
 def register_command(self,name,fn):
  if fn is None:return self.registered.pop(name,None)
  if name in self.registered:raise RuntimeError('duplicate command')
  self.registered[name]=fn
 def get_status(self,t):return {'commands':dict(self.registered)}
 def respond_info(self,msg):self.messages.append(msg)
class Reactor:
 NEVER=1e99
 def __init__(self):self.now=0
 def register_timer(self,fn):return fn
 def update_timer(self,*args):pass
 def monotonic(self):return self.now
class ToolHead:
 def __init__(self):self.pos=[0,0,1,0]
 def move(self,*args):pass
 def get_position(self):return list(self.pos)
 def get_kinematics(self):return types.SimpleNamespace(get_steppers=lambda:[types.SimpleNamespace(get_name=lambda:'stepper_z',get_mcu_position=lambda:round(self.pos[2]*400))])
class Surface:
 def calc_z(self,x,y):return x*.001
 def get_profile_name(self):return 'default'
class BedMesh:
 fade_target=0.;fade_start=1.;fade_end=10.
 def __init__(self):self.last_position=[0,0,1,0];self.mesh=Surface();self.factor=1
 def move(self,*args):pass
 def get_mesh(self):return self.mesh
 def get_z_factor(self,z):return self.factor
class Wrapper:
 def move(self,*args):pass
 def __init__(self,next):self.next_transform=next
class Gcmd:
 error=RuntimeError
 def __init__(self,**kwargs):self.kw=kwargs;self.messages=[]
 def get(self,k,default=None):return self.kw.get(k,default)
 def get_float(self,k,default=None,**limits):
  if k not in self.kw and default is None:raise RuntimeError('missing '+k)
  v=float(self.kw.get(k,default))
  for name,limit in limits.items():
   if (name=='minval'and v<limit)or(name=='maxval'and v>limit)or(name=='above'and v<=limit):raise RuntimeError('limit')
  return v
 def respond_info(self,msg):self.messages.append(msg)
class Config:
 def __init__(self,objects,reactor):self.objects=objects;self.reactor=reactor
 def get_printer(self):return self
 def get_reactor(self):return self.reactor
 def lookup_object(self,name,default=None):return self.objects.get(name,default)
 def getfloat(self,name,default,**kwargs):return default
 def getboolean(self,name,default):return False
 def config_error(self,msg):return RuntimeError(msg)
class MeshAuditTests(unittest.TestCase):
 def fixture(self):
  gcode=Gcode();reactor=Reactor();th=ToolHead();bm=BedMesh();gm=types.SimpleNamespace(move_transform=bm,get_status=lambda t:{'gcode_position':[0,0,.2,0],'homing_origin':[0,0,.5]})
  gm.move_with_transform=bm.move
  objects={'gcode':gcode,'gcode_move':gm,'toolhead':th,'bed_mesh':bm,'motion_report':types.SimpleNamespace(get_status=lambda t:{'live_position':th.pos}),'probe':types.SimpleNamespace(get_offsets=lambda cmd:(0,0,-.25))}
  return mod.DeepCalibrationMesh(Config(objects,reactor)),objects,reactor
 def varied(self,a,o,wrong=False):
  for t,x in enumerate([10,80,150]):
   bm=o['bed_mesh'];bm.last_position=[x,10,1.,0];o['toolhead'].pos=[x,10,1.+(0 if wrong else x*.001),0];a.samples.append(a.snapshot(t))
  a._finish();return '\n'.join(o['gcode'].messages)
 def test_matching_varying_mesh_transform(self):
  a,o,r=self.fixture();text=self.varied(a,o);self.assertIn('VERIFIED',text);self.assertIn('range=0.140000',text)
 def test_unaligned_xy_is_not_a_compensation_failure(self):
  a,o,r=self.fixture();o['toolhead'].pos=[100,0,1.1,0]
  s=a.snapshot(0);self.assertFalse(s['comparable']);a.samples.append(s);a._finish()
  text='\n'.join(o['gcode'].messages);self.assertIn('NOT COMPARABLE',text);self.assertIn('no comparable endpoints',text);self.assertNotIn('does NOT MATCH',text)
 def test_final_split_pending_z_update_is_excluded(self):
  a,o,r=self.fixture();o['bed_mesh'].splitter=types.SimpleNamespace(traverse_complete=True,next_pos=[0,0,2,0]);o['toolhead'].pos=[0,0,2,0]
  self.assertFalse(a.snapshot(0)['comparable'])
 def test_split_submission_excluded_even_with_matching_xy(self):
  a,o,r=self.fixture();o['bed_mesh'].splitter=types.SimpleNamespace(traverse_complete=False)
  self.assertFalse(a.snapshot(0)['comparable'])
 def test_skipped_samples_do_not_hide_comparable_failure(self):
  a,o,r=self.fixture();o['toolhead'].pos=[100,0,1.1,0];a.samples.append(a.snapshot(0))
  text=self.varied(a,o,wrong=True);self.assertIn('excluded 1/4',text);self.assertIn('does NOT MATCH',text)
 def test_nominal_z_is_not_mistaken_for_transformed_z(self):
  a,o,r=self.fixture();o['bed_mesh'].last_position=[100,10,1.,0];o['toolhead'].pos=[100,10,1.1,0];s=a.snapshot(0)
  self.assertEqual(s['nominal_z'],.2);self.assertAlmostEqual(s['observed'],.1);self.assertAlmostEqual(s['error'],0)
 def test_known_wrapper_and_unknown_wrapper(self):
  a,o,r=self.fixture();o['gcode_move'].move_transform=Wrapper(Wrapper(o['bed_mesh']));o['gcode_move'].move_with_transform=o['gcode_move'].move_transform.move;self.assertTrue(a.snapshot(0)['in_chain'])
  o['gcode_move'].move_transform=object();self.assertIsNone(a.snapshot(0)['in_chain']);text=self.varied(a,o);self.assertIn('could not be verified',text);self.assertNotIn('VERIFIED',text)
 def test_mesh_loaded_but_bypassed(self):
  a,o,r=self.fixture();o['gcode_move'].move_transform=o['toolhead'];text=self.varied(a,o);self.assertIn('BYPASSED',text)
 def test_no_mesh_and_faded_mesh(self):
  a,o,r=self.fixture();o['bed_mesh'].mesh=None;a.samples.append(a.snapshot(0));a._finish();self.assertIn('NO ACTIVE MESH','\n'.join(o['gcode'].messages))
  a,o,r=self.fixture();o['bed_mesh'].factor=0;o['bed_mesh'].fade_target=.02;o['toolhead'].pos[2]=1.02;a.samples.append(a.snapshot(0));a._finish();self.assertIn('FADED OUT','\n'.join(o['gcode'].messages))
 def test_mesh_formula_honors_fade_target(self):
  a,o,r=self.fixture();bm=o['bed_mesh'];bm.factor=.5;bm.fade_target=.02;bm.last_position=[100,10,1,0];o['toolhead'].pos=[100,10,1.06,0];s=a.snapshot(0);self.assertAlmostEqual(s['expected'],.06);self.assertAlmostEqual(s['error'],0)
 def test_mismatch_and_insufficient_route(self):
  a,o,r=self.fixture();self.assertIn('NOT MATCH',self.varied(a,o,wrong=True))
  a,o,r=self.fixture();a.samples.append(a.snapshot(0));a._finish();self.assertIn('insufficient','\n'.join(o['gcode'].messages))
 def test_layer_changes_are_not_proof_of_mesh_following(self):
  a,o,r=self.fixture()
  for i in range(3):
   o['bed_mesh'].last_position=[i*50,0,1.+i,0];o['toolhead'].pos=[i*50,0,1.+i+i*.05,0];a.samples.append(a.snapshot(i))
  a._finish();self.assertNotIn('VERIFIED','\n'.join(o['gcode'].messages))
 def test_trace_bounded_read_only_no_motion_api_needed(self):
  a,o,r=self.fixture();a.cmd_DEEP_CALIBRATION_MESH_TRACE(Gcmd(SECONDS=1,INTERVAL=.25))
  for i in range(5):r.now=i*.25;a._tick(r.now)
  self.assertIsNone(a.until);self.assertEqual(len(a.samples),5);self.assertEqual(o['toolhead'].pos,[0,0,1,0])
  self.assertIn('not bed encoders','\n'.join(o['gcode'].messages))
 def test_stale_gcode_callback_is_detected(self):
  a,o,r=self.fixture();o['gcode_move'].move_with_transform=o['toolhead'].move
  self.assertIn('callback does NOT MATCH',self.varied(a,o))
 def test_mesh_replaced_during_trace_is_not_verified(self):
  a,o,r=self.fixture()
  for i in range(3):
   o['bed_mesh'].mesh=Surface();o['bed_mesh'].last_position=[i*50,0,1,0];o['toolhead'].pos=[i*50,0,1+i*.05,0];a.samples.append(a.snapshot(i))
  a._finish();text='\n'.join(o['gcode'].messages);self.assertIn('active mesh changed',text);self.assertNotIn('VERIFIED',text)
 def test_mesh_removed_during_trace_is_not_verified(self):
  a,o,r=self.fixture();a.samples.append(a.snapshot(0));o['bed_mesh'].mesh=None;a.samples.append(a.snapshot(1));a._finish()
  self.assertIn('active or inactive','\n'.join(o['gcode'].messages))
 def test_nonfinite_trace_arguments_rejected(self):
  a,o,r=self.fixture()
  with self.assertRaises(RuntimeError):a.cmd_DEEP_CALIBRATION_MESH_TRACE(Gcmd(SECONDS=float('nan')))
 def test_startup_requirement_checks_path_mesh_and_effective_first_layer(self):
  a,o,r=self.fixture();a.cmd_DEEP_CALIBRATION_MESH_REQUIRE(Gcmd())
  o['gcode_move'].move_with_transform=o['toolhead'].move
  with self.assertRaises(RuntimeError):a.cmd_DEEP_CALIBRATION_MESH_REQUIRE(Gcmd())
  o['gcode_move'].move_with_transform=o['bed_mesh'].move;o['bed_mesh'].mesh=None
  with self.assertRaises(RuntimeError):a.cmd_DEEP_CALIBRATION_MESH_REQUIRE(Gcmd())
  o['bed_mesh'].mesh=Surface();o['gcode_move'].base_position=[0,0,.5,0];o['bed_mesh'].get_z_factor=lambda z:1 if z<.6 else 0
  with self.assertRaises(RuntimeError):a.cmd_DEEP_CALIBRATION_MESH_REQUIRE(Gcmd())
 def test_startup_routing_preserves_original_macro_handlers(self):
  a,o,r=self.fixture();g=o['gcode'];calls=[]
  old_start=lambda cmd:calls.append('original start');old_clean=lambda cmd:calls.append('original clean')
  new_start=lambda cmd:calls.append('new start');new_clean=lambda cmd:calls.append('new clean')
  g.register_command('START_PRINT',old_start);g.register_command('_PRINT_CLEAR_NOZZLE',old_clean)
  o['gcode_macro DEEP_CALIBRATION_START_PRINT']=types.SimpleNamespace(cmd=new_start)
  o['gcode_macro _DEEP_CALIBRATION_PRECLEAN']=types.SimpleNamespace(cmd=new_clean)
  a._install_startup();a._install_startup()
  for name in ['START_PRINT','_DEEP_CALIBRATION_BASE_START_PRINT','_PRINT_CLEAR_NOZZLE','_DEEP_CALIBRATION_BASE_PRECLEAN']:g.registered[name](None)
  self.assertEqual(calls,['new start','original start','new clean','original clean'])
 def test_routing_preflight_failure_keeps_original_handlers(self):
  a,o,r=self.fixture();old=lambda cmd:None;o['gcode'].register_command('START_PRINT',old)
  with self.assertRaises(RuntimeError):a._install_startup()
  self.assertIs(o['gcode'].registered['START_PRINT'],old)
 def test_opt_in_registers_startup_ready_hook(self):
  a,o,r=self.fixture();events=[]
  cfg=Config(o,r);cfg.getboolean=lambda key,default:True;cfg.register_event_handler=lambda event,callback:events.append(event)
  # Use a new command registry because a second module instance must not coexist.
  o['gcode']=Gcode();obj=mod.DeepCalibrationMesh(cfg)
  self.assertEqual(events,['klippy:ready']);self.assertTrue(obj.startup_integration)
if __name__=='__main__':unittest.main(verbosity=2)
