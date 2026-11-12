import json
import math
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import ast
import logging
import re
import queue
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from deep_calibration import DeepCalibration, JsonWriter, SignalFilter, parse_reply

class Command:
    def __init__(self,**params): self.params=params;self.messages=[]
    def get(self,key,default=None): return self.params.get(key,default)
    def get_float(self,key,default=None,**limits):
        if key not in self.params and default is None: raise RuntimeError('missing '+key)
        v=float(self.params.get(key,default))
        if 'minval' in limits and v<limits['minval']: raise RuntimeError('low '+key)
        if 'maxval' in limits and v>limits['maxval']: raise RuntimeError('high '+key)
        return v
    error=RuntimeError
    def respond_info(self,text): self.messages.append(text)
class Status:
    def __init__(self,**status): self.status=status
    def get_status(self,t): return self.status
class Reactor:
    NEVER=1.e99
    def __init__(self): self.now=0.;self.timers=[]
    def monotonic(self): return self.now
    def register_timer(self,fn): self.timers.append(fn);return fn
    def update_timer(self,*args): pass
class Reader:
    _command_id=0
    def __init__(self): self.calls=[]
    def extract_last_value_before_g(self,response): self.calls.append(response);return 19.
class Gcode:
    def __init__(self): self.commands={};self.messages=[]
    def register_command(self,name,fn):
        if name in self.commands: raise RuntimeError('duplicate')
        self.commands[name]=fn
    def respond_info(self,text): self.messages.append(text)
    def run_script_from_command(self,script): raise AssertionError('Recorder must not execute printer commands: '+script)
class Config:
    def __init__(self,objects,reactor,directory): self.objects=objects;self.reactor=reactor;self.directory=directory;self.events={}
    def get_printer(self): return self
    def get_reactor(self): return self.reactor
    def lookup_object(self,name,default=None): return self.objects.get(name,default)
    def lookup_objects(self): return list(self.objects.items())
    def register_event_handler(self,name,fn): self.events[name]=fn
    def get(self,name,default=None): return self.directory if name=='log_directory' else default
    def getfloat(self,name,default,**kw): return default
    def getint(self,name,default,**kw): return 0 if name in ('accel_default','adc_default') else default
    error=RuntimeError
    config_error=RuntimeError
    def getboolean(self,name,default):return False

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.reactor=Reactor();self.reader=Reader();self.gcode=Gcode()
        gm=Status(gcode_position=[10,20,.2,0],homing_origin=[0,0,.6,0],speed_factor=1.,extrude_factor=1.)
        class Mesh:
            def calc_z(self,x,y): return -3.4
        class Bed(Status):
            last_position=[10,20,.8,0];fade_target=0.
            def get_mesh(self): return Mesh()
            def get_z_factor(self,z): return 1.
            def move(self,*args): raise AssertionError('no motion')
        bm=Bed(profile_name='auto');gm.move_transform=bm;gm.move_with_transform=bm.move
        class Tool(Status):
            def get_position(self): return [10,20,-2.6,0]
            def get_kinematics(self): return types.SimpleNamespace(get_steppers=lambda:[types.SimpleNamespace(get_name=lambda:'stepper_z',get_mcu_position=lambda:100)])
        tool=Tool(homed_axes='xyz',print_time=1.,estimated_print_time=.5)
        self.objects={'gcode':self.gcode,'temperature_load weightValue':self.reader,
                      'toolhead':tool,'gcode_move':gm,'bed_mesh':bm,
                      'configfile':Status(settings={'probe':{'z_offset':-.25},'extruder':{'nozzle_diameter':.4}}),
                      'motion_report':Status(live_position=[10,20,-2.6,0],live_velocity=0.,live_extruder_velocity=0.),
                      'print_stats':Status(state='standby',info={'current_layer':None}),
                      'fan':Status(speed=0.,rpm=3000),
                      'extruder':Status(temperature=230.,target=230.),'heater_bed':Status(temperature=60.,target=60.),
                      'input_shaper':types.SimpleNamespace(shapers=[types.SimpleNamespace(get_name=lambda:'shaper_x',params=types.SimpleNamespace(get_status=lambda:dict(shaper_freq='50.000',shaper_type='mzv')))])}
        self.objects['fan_generic fanM106']=self.objects['fan']
        self.config=Config(self.objects,self.reactor,self.temp.name)
        self.cell=DeepCalibration(self.config);self.cell._connect()
        self.addCleanup(self.close)
    def close(self):
        if self.cell.writer:
            self.cell.sensors.stop()
            self.cell.writer.close();self.cell.writer.thread.join(3)
            if self.cell.sensors.writer:self.cell.sensors.writer.thread.join(3)
    def feed(self,raw=8000000,grams=-19,t=None):
        self.reactor.now=self.reactor.now+.25 if t is None else t
        response='command H7 ok. %d %s g'%(raw,grams)
        result=self.reader.extract_last_value_before_g(response)
        self.cell._tick(self.reactor.now)
        return result
    def read_log(self):
        self.cell.cmd_STOP(Command());self.close()
        return [json.loads(line) for line in Path(self.cell.writer.path).read_text().splitlines()]

    def test_parser_preserves_signed_overload_and_rejects_non_h7(self):
        self.assertEqual(parse_reply('command H7 ok. 12345 -19.5 g'),(12345,-19.5))
        self.assertIsNone(parse_reply('command H1 ok. 12345 19 g'))
        self.assertEqual(parse_reply('command H7 ok. 12345 99999 g'),(12345,99999.))
        self.assertIsNone(parse_reply('garbage'))
    def test_native_parser_return_is_preserved_and_raw_logged_once(self):
        self.assertEqual(self.feed(),19.)
        self.cell.cmd_START(Command(RUN='first',MATERIAL='PLA'))
        for i in range(5): self.feed(8000000+i)
        self.cell._tick(self.reactor.now+.1)
        records=self.read_log();samples=[v for v in records if v['type']=='sample']
        self.assertEqual(len(samples),5)
        self.assertEqual(len(set(s['sequence'] for s in samples)),5)
        self.assertEqual(samples[0]['board_grams'],-19.)
        self.assertIsNone(samples[0]['filtered_grams'])
        self.assertEqual(records[0]['configured_probe']['z_offset'],-.25)
        self.assertTrue(all('context_id' in s and 'context_lag' in s for s in samples))
        self.assertTrue(any(v.get('event')=='session_end' for v in records))
        self.assertEqual(len(self.reader.calls),6)
    def test_offset_changes_marked_while_fan_rpm_noise_is_not_a_setting_change(self):
        self.feed();self.cell.cmd_START(Command());self.feed()
        self.objects['fan'].status['rpm']=3010;self.feed()
        self.objects['gcode_move'].status['homing_origin'][2]=.65;self.feed()
        self.objects['fan'].status['speed']=.5;self.feed()
        records=self.read_log();changes=[x for x in records if x.get('event')=='conditions_changed']
        self.assertEqual(len(changes),3) # initial snapshot, offset, fan command
    def test_labels_and_recipe_updates_do_not_execute_gcode(self):
        self.feed();self.cell.cmd_START(Command());self.cell.cmd_MARK(Command(LABEL='TOO_HIGH'))
        self.cell.cmd_SET(Command(FAN=50,HEIGHT=.15,WIDTH=.5,LAYER=2));self.feed()
        records=self.read_log();contexts=[v for v in records if v['type']=='context']
        self.assertEqual(contexts[-1]['recipe']['fan'],50)
        self.assertEqual(contexts[-1]['fans']['fan']['speed'],0.)
        self.assertEqual(contexts[-1]['label'],'TOO_HIGH')
        self.assertFalse(self.cell.get_status(self.reactor.now)['automatic_corrections'])
    def test_stale_data_and_invalid_parameters_rejected(self):
        with self.assertRaises(RuntimeError): self.cell.cmd_START(Command())
        self.feed();self.reactor.now+=2
        with self.assertRaises(RuntimeError): self.cell.cmd_START(Command())
        self.feed()
        for params in ({'RUN':'../bad'},{'HEIGHT':math.nan},{'MAX':math.inf},{'LAYER':1.5},{'MATERIAL':'bad name'}):
            with self.subTest(params=params),self.assertRaises(RuntimeError): self.cell.cmd_START(Command(**params))
    def test_software_zero_does_not_tare_board_and_native_generation_invalidates_it(self):
        for i in range(15): self.feed(8000000)
        self.cell.cmd_ZERO(Command());self.assertEqual(self.cell.baseline['raw'],8000000)
        self.cell.cmd_START(Command());self.feed(8000010)
        self.reader._command_id+=1;self.feed(8000020)
        samples=[v for v in self.read_log() if v['type']=='sample']
        self.assertTrue(samples[0]['baseline_valid']);self.assertFalse(samples[-1]['baseline_valid'])
        self.assertIsNone(samples[-1]['filtered_delta_counts'])
    def test_zero_rejects_motion_or_printing_or_insufficient_data(self):
        with self.assertRaises(RuntimeError): self.cell.cmd_ZERO(Command())
        for i in range(15): self.feed()
        self.objects['print_stats'].status['state']='printing'
        with self.assertRaises(RuntimeError): self.cell.cmd_ZERO(Command())
        self.objects['print_stats'].status['state']='standby'
        self.objects['motion_report'].status['live_velocity']=10
        with self.assertRaises(RuntimeError): self.cell.cmd_ZERO(Command())
    def test_low_sample_rate_cannot_resolve_shaper_frequency(self):
        self.feed();self.cell.cmd_START(Command())
        for i in range(20): self.feed(8000000+i)
        samples=[v for v in self.read_log() if v['type']=='sample']
        self.assertAlmostEqual(samples[-1]['rate_hz'],4.)
        self.assertEqual(samples[-1]['nyquist_hz'],2.)
        self.assertFalse(samples[-1]['shaper_resolvable'])
    def test_overload_raw_reply_is_retained_and_flagged(self):
        self.feed();self.cell.cmd_START(Command());self.feed(9000000,99999)
        sample=next(s for s in self.read_log() if s['type']=='sample')
        self.assertEqual(sample['raw'],9000000);self.assertTrue(sample['board_overload'])
        self.assertFalse(sample['baseline_valid'])
    def test_print_completion_and_timeout_close_capture(self):
        self.feed();self.cell.cmd_START(Command(MAX=30))
        self.objects['print_stats'].status['state']='printing';self.feed()
        self.objects['print_stats'].status['state']='complete';self.feed()
        self.assertFalse(self.cell.active);records=self.read_log()
        self.assertIn('print_complete',[v.get('reason') for v in records])
    def test_disconnect_preserves_an_outer_observer(self):
        inner=self.reader.extract_last_value_before_g
        outer=lambda response:inner(response)
        self.reader.extract_last_value_before_g=outer
        self.cell._disconnect()
        self.assertIs(self.reader.extract_last_value_before_g,outer)
    def test_missing_reader_disables_start_without_blocking_native_printer(self):
        self.cell._disconnect();self.objects.pop('temperature_load weightValue')
        cell=DeepCalibration(Config(dict(self.objects,gcode=Gcode()),self.reactor,self.temp.name));cell._connect()
        with self.assertRaises(RuntimeError): cell.cmd_START(Command())
        self.assertIsNone(cell.reader)
    def test_context_records_split_endpoints_as_unaligned(self):
        self.feed();self.cell.cmd_START(Command())
        self.objects['bed_mesh'].splitter=types.SimpleNamespace(traverse_complete=False)
        self.feed();contexts=[v for v in self.read_log() if v['type']=='context']
        self.assertFalse(contexts[-1]['mesh']['comparable'])
    def test_native_trapq_is_queried_at_each_receipt_not_cached_future_endpoint(self):
        self.objects['mcu']=types.SimpleNamespace(estimated_print_time=lambda t:t+100.)
        self.objects['toolhead'].get_extra_axes=lambda:[None,None,None,types.SimpleNamespace(get_name=lambda:'extruder')]
        requested=[]
        def position(clock): requested.append(clock);return ([clock,20.,-2.6],40.)
        self.objects['motion_report'].dtrapqs={
            'toolhead':types.SimpleNamespace(get_trapq_position=position),
            'extruder':types.SimpleNamespace(get_trapq_position=lambda clock:([clock*.1],1.5))}
        self.feed();self.cell.cmd_START(Command());self.feed(t=1.)
        records=self.read_log();sample=next(v for v in records if v['type']=='sample')
        self.assertEqual(sample['motion_at_receipt']['method'],'native_trapq_at_host_receipt')
        self.assertEqual(sample['motion_at_receipt']['live_position'][0],101.)
        self.assertEqual(sample['motion_at_receipt']['live_extruder_velocity'],1.5)
        self.assertEqual(sample['motion_at_receipt']['sample_time'],1.)
        self.assertIn(101.,requested)
    def test_fallback_motion_cache_is_explicitly_labelled(self):
        self.feed();self.cell.cmd_START(Command());self.feed()
        sample=next(v for v in self.read_log() if v['type']=='sample')
        self.assertEqual(sample['motion_at_receipt']['method'],'cached_status_fallback')
        self.assertIsNone(sample['motion_at_receipt']['sample_time'])
    def test_observer_compatible_with_actual_supplied_native_parser(self):
        tree=ast.parse((ROOT/'reference/zmod_tenz.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='zmod_tenz')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='extract_last_value_before_g')
        namespace={'re':re,'logging':logging}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'supplied_zmod_tenz','exec'),namespace)
        self.cell.original=types.MethodType(namespace[method.name],self.reader)
        self.assertEqual(self.feed(8000123,-19),19.)
        self.assertEqual(self.cell.last_sample['raw'],8000123)
    def test_raw_queue_loss_ends_session_with_explicit_incomplete_reason(self):
        self.feed();self.cell.cmd_START(Command())
        self.cell.dropped+=1;self.feed()
        self.assertFalse(self.cell.active)
        records=self.read_log()
        self.assertIn('raw_queue_overflow',[r.get('reason') for r in records])
    def test_writer_error_is_reported_without_printer_actions(self):
        self.feed();self.cell.cmd_START(Command())
        self.cell.writer.error='simulated disk failure';self.feed()
        self.assertFalse(self.cell.active)
        self.assertTrue(any('disk failure' in s for s in self.gcode.messages))
    def test_printer_identity_is_persistent_per_data_directory(self):
        self.feed();self.cell.cmd_START(Command())
        first=self.read_log()[0]['printer_id']
        self.cell.cmd_START(Command());second=self.read_log()[0]['printer_id']
        self.assertEqual(first,second);self.assertEqual(len(first),32)
    def test_start_reports_bad_directory_as_command_error(self):
        self.feed();self.cell.directory=str(Path(self.temp.name)/'not_directory')
        Path(self.cell.directory).write_text('file')
        with self.assertRaisesRegex(RuntimeError,'log directory'): self.cell.cmd_START(Command())
    def test_capture_error_stops_recording_not_printing(self):
        self.feed();self.cell.cmd_START(Command())
        self.objects['toolhead'].get_position=lambda:(_ for _ in ()).throw(RuntimeError('bad status'))
        self.cell._tick(self.reactor.now+.1)
        self.assertFalse(self.cell.active)
        self.assertTrue(any('capture stopped' in s for s in self.gcode.messages))

class FilterWriterTests(unittest.TestCase):
    def test_median_rejects_isolated_spike_and_gap_resets(self):
        signal=SignalFilter()
        for t,v in ((0,100),(.25,100),(.5,1000000),(.75,100)):
            out=signal.feed(t,v,1)
        self.assertEqual(out['filtered_raw'],100)
        self.assertEqual(signal.feed(3,200,1)['filtered_raw'],200)
        self.assertEqual(signal.feed(3.25,300,2)['filtered_raw'],300)
    def test_ema_uses_actual_time(self):
        signal=SignalFilter(tau=.5)
        signal.feed(0,0,1);signal.feed(.25,10,1);out=signal.feed(.5,10,1)
        expected=(1-math.exp(-.5))*5+(1-math.exp(-.5))*(10-(1-math.exp(-.5))*5)
        self.assertAlmostEqual(out['filtered_raw'],expected)
    def test_writer_is_exclusive_and_bounds_file_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'log.jsonl';writer=JsonWriter(path,max_bytes=100)
            writer.put(dict(data='x'*200));writer.close();writer.thread.join(3)
            self.assertIn('size limit',writer.error)
            self.assertLessEqual(path.stat().st_size,100)
            with self.assertRaises(FileExistsError): JsonWriter(path)
    def test_writer_sanitizes_nonfinite_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'log.jsonl';writer=JsonWriter(path)
            writer.put(dict(value=math.nan));writer.close();writer.thread.join(3)
            self.assertIsNone(json.loads(path.read_text())['value'])
    def test_writer_queue_overflow_is_bounded_and_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer=JsonWriter(Path(tmp)/'overflow.jsonl')
            with mock.patch.object(writer.queue,'put_nowait',side_effect=queue.Full):
                self.assertFalse(writer.put({'row':1}))
            writer.thread.join(3)
            self.assertIn('queue overflow',writer.error)

if __name__=='__main__': unittest.main()
