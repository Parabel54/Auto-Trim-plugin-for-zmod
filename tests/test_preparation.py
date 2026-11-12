"""Stateful macro control-flow simulation; no printer or thermal model."""
import ast
import configparser
from pathlib import Path
import shlex
import re
import unittest
import jinja2
import types
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deep_calibration_mesh import DeepCalibrationMesh
ROOT=Path(__file__).resolve().parents[1]
CP=configparser.RawConfigParser()
CP.read(ROOT/'deep_calibration_start.cfg')
ENV=jinja2.Environment('{%','%}','{','}',undefined=jinja2.StrictUndefined)
T={k:ENV.from_string(CP[k]['gcode']) for k in CP if 'gcode' in CP[k]}

def literal(value):
    if value[:1] in ('"',"'") and value[-1:]==value[:1]:value=value[1:-1]
    return ast.literal_eval(value)

class Runtime:
    def __init__(self, homed=False, ext=230, minimum=170):
        self.lines=[];self.e=0.;self.homes=0;self.dwells=0.;self.meshes=0
        self.p={k:{n[9:]:ast.literal_eval(v) for n,v in CP[k].items() if n.startswith('variable_')} for k in CP if k.startswith('gcode_macro ')}
        self.p.update(deep_calibration={'recording':False,'host_time':10.},save_variables={'variables':dict(print_leveling=0,mesh_test=0,disable_priming=1,soak_t60=120,soak_t60_method=2,soak_t60_points=5)},
                      toolhead=dict(homed_axes='xyz' if homed else '',estimated_print_time=10.,max_velocity=300.,max_accel=5000.),
                      heater_bed=dict(target=0.,temperature=20.),extruder=dict(target=0.,temperature=20.,can_extrude=False),
                      print_stats=dict(state='printing'),gcode_move=dict(gcode_position=dict(z=5)),
                      gcode={'commands':dict(DEEP_CALIBRATION_MESH_REQUIRE=True,_KAMP_BED_MESH_CALIBRATE=True)},
                      configfile={'settings':dict(extruder=dict(min_extrude_temp=minimum,max_temp=300),heater_bed=dict(max_temp=120),bed_mesh=dict(mesh_min=[0,0],mesh_max=[215,215]))},
                      probe=dict(last_probe_position=dict(z=-2.),last_z_result=-2.))
        self.p['gcode_macro _CLIENT_VARIABLE']=dict(ad5x=True,custom_park_y=230.5,max_y=220)
        self.p['gcode_macro _SCREEN']=dict(screen=False)
        self.p['save_variables']['variables']['klipper13']=1
        self.ext=ext;self.minimum=minimum
        self.probe_helper=DeepCalibrationMesh.__new__(DeepCalibrationMesh)
        self.probe_helper.reactor=types.SimpleNamespace(monotonic=lambda:self.p['toolhead']['estimated_print_time'])
        self.probe_helper.printer=types.SimpleNamespace(lookup_object=lambda name,default=None:
            types.SimpleNamespace(get_status=lambda now:self.p[name]) if name in self.p else default)
        self.probe_helper.gcode=types.SimpleNamespace(run_script_from_command=self.run_lines)
        def measure(samples,repeat,retries,first_speed=2.5,second_speed=1.):
            self.run_lines('PROBE SAMPLES=%d SAMPLES_RESULT=median SAMPLES_TOLERANCE=%.9f SAMPLES_TOLERANCE_RETRIES=%d' % (samples,repeat+1.e-7,retries))
            return self.p['probe']['last_probe_position']['z']
        self.probe_helper._measure_soak_point=measure

    def run(self,name,params=None):
        self.p['deep_calibration']['host_time']=self.p['toolhead']['estimated_print_time']
        params=params or {};section=('delayed_gcode ' if name.startswith('delayed:') else 'gcode_macro ')+name.removeprefix('delayed:')
        ctx=dict(self.p.get(section,{}));ctx.update(printer=self.p,params=params,rawparams=' '.join(k+'='+str(v) for k,v in params.items()),action_raise_error=lambda m:(_ for _ in ()).throw(RuntimeError(m)))
        text=T[section].render(ctx)
        self.run_lines(text)
    def run_lines(self,text):
        for raw in text.splitlines():
            line=raw.strip()
            if not line or line.startswith('#'):continue
            self.lines.append(line);cmd=line.split()[0]
            if cmd=='_DEEP_CALIBRATION_SOAK_EVALUATE':
                args=dict(x.split('=',1) for x in shlex.split(line)[1:] if '=' in x)
                self.probe_helper.cmd_soak_evaluate(types.SimpleNamespace(
                    error=RuntimeError,get_float=lambda key:float(args[key]),
                    get=lambda key,default=None:args.get(key,default)))
                continue
            if cmd=='_DEEP_CALIBRATION_SOAK_PROBE':
                self.probe_helper.cmd_soak_probe(types.SimpleNamespace(error=RuntimeError))
                continue
            if cmd in ('SET_GCODE_VARIABLE','SAVE_VARIABLE'):
                left,val=line.split(' VALUE=',1);args=dict(x.split('=',1) for x in shlex.split(left)[1:]);value=literal(val)
                if cmd=='SAVE_VARIABLE':self.p['save_variables']['variables'][args['VARIABLE']]=value
                else:self.p['gcode_macro '+args['MACRO']][args['VARIABLE']]=value
                continue
            args=dict(x.split('=',1) for x in shlex.split(line)[1:] if '=' in x)
            if cmd=='_DEEP_CALIBRATION_BASE_START_PRINT':
                assert args['SKIP_LEVELING']=='True' and args['FORCE_KAMP']=='False' and args['FORCE_LEVELING']=='False' and args['MESH']==''
                # The supplied stock startup owns conditional _G28 and pre-clean.
                if self.p['toolhead']['homed_axes']!='xyz':self.homes+=1;self.p['toolhead']['homed_axes']='xyz'
                self.run('_DEEP_CALIBRATION_PRECLEAN')
                for name,key in [('extruder','EXTRUDER_TEMP'),('heater_bed','BED_TEMP')]:self.p[name].update(target=float(args[key]),temperature=float(args[key]))
                self.p['extruder']['can_extrude']=True
            elif 'gcode_macro '+cmd in T:self.run(cmd,args)
            elif cmd in ('_BED_MESH_CALIBRATE','_KAMP_BED_MESH_CALIBRATE'):self.meshes+=1
            elif cmd in ('M104','M109','M140','M190'):
                name='extruder' if cmd in ('M104','M109') else 'heater_bed';value=float(line.split(' S')[1].split()[0]);self.p[name]['target']=value
                if cmd in ('M109','M190'):self.p[name]['temperature']=value
                self.p['extruder']['can_extrude']=self.p['extruder']['temperature']>=self.minimum
            elif cmd=='TEMPERATURE_WAIT':
                sensor=self.p[args['SENSOR']];old=sensor['temperature'];sensor['temperature']=sensor['target'] if 'MINIMUM'in args else min(old,float(args['MAXIMUM']))
                self.p['toolhead']['estimated_print_time']+=abs(sensor['temperature']-old)
                self.p['extruder']['can_extrude']=self.p['extruder']['temperature']>=self.minimum
            elif cmd=='G4':
                seconds=float(line.split(' P')[1])/1000.;self.dwells+=seconds;self.p['toolhead']['estimated_print_time']+=seconds
            elif cmd=='_CLEAR_REZINA':self.e-=2.
            elif cmd=='G1':
                for part in line.split()[1:]:
                    if part.startswith('E'):self.e+=float(part[1:])
    def start(self,**kw):self.run('DEEP_CALIBRATION_START_PRINT',dict(EXTRUDER_TEMP=self.ext,BED_TEMP=60,**kw))
    def count(self,cmd):return sum(x.split()[0]==cmd for x in self.lines)

class StartupTests(unittest.TestCase):
    def test_all_templates_compile(self):self.assertGreater(len(T),15)
    def test_one_cold_start_no_duplicate_actions(self):
        r=Runtime();r.start();self.assertEqual(r.homes,1);self.assertEqual(r.meshes,1)
        for cmd in ('_DEEP_CALIBRATION_BASE_START_PRINT','DEEP_CALIBRATION_PREPARE','_DEEP_CALIBRATION_TRASH_CLEAN','_DEEP_CALIBRATION_SOAK','_DEEP_CALIBRATION_TRASH_FINISH','DEEP_CALIBRATION_MESH_REQUIRE'):self.assertEqual(r.count(cmd),1,cmd)
        self.assertEqual(r.count('_DEEP_CALIBRATION_BASE_PRECLEAN'),0);self.assertEqual(r.count('_G28'),0)
        self.assertEqual(r.p['extruder']['target'],230);self.assertAlmostEqual(r.e,10)
        self.assertNotIn('SET_GCODE_OFFSET','\n'.join(r.lines))
    def test_homed_start_does_not_home_again(self):
        r=Runtime(homed=True);r.start();self.assertEqual(r.homes,0)
    def test_periodic_cooling_wipes_retained_and_no_cold_e_moves(self):
        r=Runtime();r.start();self.assertEqual(r.count('_DEEP_CALIBRATION_COLD_WIPE'),5)
        self.assertEqual(r.count('_CLEAR_REZINA'),2);self.assertAlmostEqual(r.e,10)
        self.assertIn('G1 E7.0 F300',r.lines)
    def test_lower_extrusion_threshold_counts_every_actual_hot_wipe(self):
        r=Runtime(ext=240,minimum=130);r.start();self.assertEqual(r.count('_DEEP_CALIBRATION_COLD_WIPE'),0)
        self.assertEqual(r.count('_CLEAR_REZINA'),6);self.assertIn('G1 E15.0 F300',r.lines);self.assertAlmostEqual(r.e,10)
    def test_soak_reuses_cooling_time_and_slowest_corner(self):
        r=Runtime();r.p['save_variables']['variables'].update(soak_t60=10,soak_t60_from=20,soak_t60_corners=200)
        r.start();waits=[x for x in r.lines if x.startswith('G4 P')];self.assertGreater(r.dwells,80);self.assertLess(r.dwells,120)
        self.assertTrue(any('calibration at 60 C' in x for x in r.lines))
    def test_soak_already_covered_has_no_second_full_wait(self):
        r=Runtime();r.p['save_variables']['variables'].update(soak_t60=10,soak_t60_from=20);r.start();self.assertLess(r.dwells,10)
    def test_warm_bed_auto_soak_is_not_silently_shortened(self):
        r=Runtime();r.p['heater_bed']['temperature']=59;r.start();self.assertTrue(any('no warm-start reduction' in x for x in r.lines))
    def test_invalid_settings_rejected_before_startup_actions(self):
        for key,value in [('mesh_test',1),('print_leveling',1),('disable_priming',0)]:
            r=Runtime();r.p['save_variables']['variables'][key]=value
            with self.assertRaises(RuntimeError):r.start()
            self.assertEqual(r.lines,[])
    def test_duplicate_start_or_prepare_rejected(self):
        r=Runtime();r.start();n=len(r.lines)
        with self.assertRaises(RuntimeError):r.start()
        with self.assertRaises(RuntimeError):r.run('DEEP_CALIBRATION_PREPARE')
        self.assertEqual(len(r.lines),n)
    def test_kamp_only_one_mesh(self):
        r=Runtime();r.start(DC_MESH='KAMP');self.assertEqual(r.meshes,1);self.assertEqual(r.count('_BED_MESH_CALIBRATE'),0)
    def test_standalone_stock_preclean_preserved(self):
        r=Runtime();r.run('_DEEP_CALIBRATION_PRECLEAN');self.assertEqual(r.count('_DEEP_CALIBRATION_BASE_PRECLEAN'),1)
    def test_soak_calibration_probes_once_per_point_without_rehoming_round(self):
        r=Runtime();c=r.p['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE'];c.update(running=True,npts=5,t0=10,bed=60,nozzle=121)
        r.p['print_stats']['state']='standby';r.p['heater_bed'].update(temperature=60,target=60);r.p['extruder'].update(temperature=121,target=121);r.run('_DEEP_CALIBRATION_SOAK_ROUND')
        self.assertEqual(r.count('PROBE'),5);self.assertEqual(r.count('LOAD_CELL_TARE'),5);self.assertEqual(r.count('_G28'),0)
    def test_timeout_preserves_previous_soak_calibration(self):
        r=Runtime();r.p['save_variables']['variables']['soak_t60']=123
        r.p['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE'].update(bed=60,rows=[[0,0],[60,.02],[120,.03],[180,.04]])
        r.run('_DEEP_CALIBRATION_SOAK_FINISH',dict(SETTLED='0'))
        self.assertEqual(r.p['save_variables']['variables']['soak_t60'],123);self.assertEqual(r.count('SAVE_VARIABLE'),0)
    def test_reset_blocked_during_print(self):
        r=Runtime()
        with self.assertRaises(RuntimeError):r.run('DEEP_CALIBRATION_RESET')
        r.p['print_stats']['state']='complete';r.run('DEEP_CALIBRATION_RESET');self.assertFalse(r.p['gcode_macro DEEP_CALIBRATION_PREPARE']['prepared'])
    def test_successful_soak_calibration_saves_and_turns_heaters_off(self):
        r=Runtime();r.p['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE'].update(bed=60,npts=1,last_good=True,confirm_count=2,rows=[[0,0],[300,.001],[600,.002],[720,.002]])
        r.run('_DEEP_CALIBRATION_SOAK_FINISH',dict(SETTLED='1'))
        self.assertEqual(r.count('SAVE_VARIABLE'),11);self.assertEqual(r.p['heater_bed']['target'],0);self.assertEqual(r.p['extruder']['target'],0)
    def test_invalid_temperature_and_autotrim_conflict_fail_before_motion(self):
        for reason in ('temperature','autotrim'):
            r=Runtime(ext=121 if reason=='temperature' else 230)
            if reason=='autotrim':r.p['gcode_macro AUTO_TRIM_PREPARE']={}
            with self.assertRaises(RuntimeError):r.start()
            self.assertEqual(r.lines,[])
    def test_cold_wipe_xyz_moves_and_speeds_match_supplied_stock(self):
        source=(ROOT/'reference'/'stock_CLEAR_REZINA.cfg').read_text()
        def moves(text):
            return [line.split(';')[0].strip() for line in text.splitlines()
                    if re.match(r'^\s*G1\s',line) and not re.search(r'\bE[-+0-9{]',line)]
        self.assertEqual(moves(source),moves(CP['gcode_macro _DEEP_CALIBRATION_COLD_WIPE']['gcode']))
if __name__=='__main__':unittest.main(verbosity=2)
