import ast
import json
from pathlib import Path
import queue
import collections
import logging
import sys
import tempfile
import types
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import test_capture as capture
from deep_calibration_sensors import AccelerationWriter, SensorExtension, read_acceleration

class NativeBulk:
    def __init__(self):self.client_cbs=[];self.is_started=False;self.starts=self.stops=0
    def add_client(self,callback):
        self.client_cbs.append(callback)
        if not self.is_started:self.starts+=1;self.is_started=True
    def _stop(self):self.stops+=1;self.client_cbs.clear();self.is_started=False
    def publish(self,rows,errors=0,overflows=0):
        for callback in list(self.client_cbs):
            if not callback(dict(data=rows,errors=errors,overflows=overflows)):
                self.client_cbs.remove(callback)
                if not self.client_cbs:self._stop()
class ADC:
    _sample_count=8
    def __init__(self,reactor):
        self.reactor=reactor;self.calls=[];self._callback=self.original
    def original(self,*args):self.calls.append(args);return 'native_return'
    def get_mcu(self):return types.SimpleNamespace(estimated_print_time=lambda t:t+100)

class ContinuousTests(unittest.TestCase):
    def setUp(self):
        self.base=capture.CaptureTests();self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.cell=self.base.cell;self.bulk=NativeBulk()
        self.adc=ADC(self.base.reactor)
        self.base.objects['lis2dw']=types.SimpleNamespace(batch_bulk=self.bulk,data_rate=1600)
        self.base.objects['query_adc']=types.SimpleNamespace(adc={'temperature_sensor filamentValue':self.adc})
        self.addCleanup(self.close_sensors)
    def close_sensors(self):
        self.cell.sensors.stop()
        if self.cell.sensors.writer:self.cell.sensors.writer.thread.join(3)
    def start(self,**kw):
        self.base.feed()
        self.cell.cmd_START(capture.Command(ACCEL=1,ADC=1,**kw))
    def adc_report(self):
        now=self.base.reactor.now
        self.adc._callback([(now+99.99,.25),(now+99.995,.26)])
    def rows(self,start,count=160):return [(100.+(start+i)/1600.,float(i),1.,9800.) for i in range(count)]
    def end_records(self):
        self.cell.cmd_STOP(capture.Command());self.close_sensors();self.base.close()
        return [json.loads(x) for x in Path(self.cell.writer.path).read_text().splitlines()]

    def test_continuous_batches_rotate_without_restarting_or_stopping_sensor(self):
        self.cell.sensors.rotate_bytes=1800
        self.start()
        for batch in range(10):
            self.bulk.publish(self.rows(batch*40,count=40));self.adc_report()
            self.base.feed()
        records=self.end_records();writer=self.cell.sensors.writer
        rows=list(read_acceleration(writer.paths))
        self.assertEqual(len(rows),400);self.assertGreater(len(writer.paths),1)
        self.assertEqual(self.bulk.starts,1);self.assertEqual(self.bulk.stops,1)
        self.assertEqual([r['t'] for r in rows],[100+i/1600 for i in range(400)])
        self.assertEqual(len([r for r in records if r['type']=='adc']),20)
        self.assertEqual(records[0]['sensor_capture']['acquisition'],'continuous_until_session_end_no_windows')
        self.assertEqual(records[-1]['sensor_capture']['frames_received'],400)
    def test_adc_reports_arriving_between_context_ticks_are_all_preserved(self):
        self.start();now=self.base.reactor.now
        original=self.adc._callback
        self.assertEqual(original([(now+99.97,.2),(now+99.98,.3),(now+99.99,.4)]),'native_return')
        records=self.end_records() # final drain must retain reports before next timer
        self.assertEqual([r['normalized_value'] for r in records if r['type']=='adc'],[.2,.3,.4])
        self.assertEqual(len(self.adc.calls),1)
        self.assertEqual(self.adc._callback,self.adc.original)
    def test_other_bulk_consumer_is_preserved_on_stop(self):
        other=lambda msg:True;self.bulk.add_client(other)
        self.start();self.end_records()
        self.assertEqual(self.bulk.client_cbs,[other]);self.assertEqual(self.bulk.stops,0)
    def test_native_adc_safety_exception_is_not_swallowed(self):
        def fault(*args):raise RuntimeError('native heater safety fault')
        self.adc._callback=fault;self.start()
        with self.assertRaisesRegex(RuntimeError,'heater safety'):self.adc._callback([(100.2,.2)])
    def test_scalar_adc_adapter_is_explicit_and_preserves_callback(self):
        original_get=self.base.config.get
        self.base.config.get=lambda key,default=None:'scalar' if key=='adc_callback_format' else original_get(key,default)
        self.cell.sensors=SensorExtension(self.cell,self.base.config)
        self.start()
        self.assertEqual(self.adc._callback(100.24,.35),'native_return')
        records=self.end_records();record=next(r for r in records if r['type']=='adc')
        self.assertEqual(record['callback_format'],'scalar');self.assertEqual(record['normalized_value'],.35)
    def test_unknown_hardware_or_fractional_flags_reject_before_subscription(self):
        self.base.feed()
        for kw in ({'ACCEL':.5,'ADC':0},{'ACCEL':0,'ADC':float('nan')}):
            with self.assertRaises(RuntimeError):self.cell.cmd_START(capture.Command(**kw))
        self.base.objects['lis2dw'].data_rate=1344
        with self.assertRaisesRegex(RuntimeError,'1600'):self.cell.cmd_START(capture.Command(ACCEL=1,ADC=0))
        self.assertFalse(self.cell.active);self.assertEqual(self.bulk.starts,0)
    def test_native_accel_overflow_ends_capture_and_marks_incomplete(self):
        self.start();self.bulk.publish(self.rows(0),overflows=1)
        self.base.feed()
        self.assertFalse(self.cell.active)
        records=self.end_records()
        self.assertIn('capture_error',[r.get('reason') for r in records])
        self.assertTrue(records[-1]['sensor_capture']['error'])
    def test_stale_stream_ends_capture_without_printer_commands(self):
        self.start();self.base.reactor.now+=3;self.cell._tick(self.base.reactor.now)
        self.assertFalse(self.cell.active);self.assertFalse(self.bulk.is_started)
    def test_adc_format_error_stops_recorder_but_native_callback_was_executed(self):
        self.start();self.adc._callback(100.24,.3)
        self.base.feed()
        self.assertFalse(self.cell.active);self.assertEqual(len(self.adc.calls),1)
    def test_new_outer_adc_observer_is_not_removed(self):
        self.start();inner=self.adc._callback
        outer=lambda *args:inner(*args)
        self.adc._callback=outer
        self.end_records();self.assertIs(self.adc._callback,outer)
    def test_adc_queue_overflow_is_explicit(self):
        self.start();self.cell.sensors.adc_pending=__import__('collections').deque(maxlen=1)
        self.adc._callback([(100.24,.2),(100.245,.3)])
        self.base.feed();self.assertFalse(self.cell.active)
    def test_acceleration_start_failure_closes_adc_and_log_without_printer_changes(self):
        def fail(callback):raise RuntimeError('simulated SPI startup failure')
        self.bulk.add_client=fail
        with self.assertRaisesRegex(RuntimeError,'SPI startup'):self.start()
        self.assertFalse(self.cell.active);self.assertEqual(self.adc._callback,self.adc.original)
    def test_actual_supplied_bulk_helper_keeps_other_client_and_stops_last_only(self):
        tree=ast.parse((ROOT/'reference/bulk_sensor.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BatchBulkHelper')
        namespace={'logging':logging,'BATCH_INTERVAL':.5}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'supplied_bulk_sensor','exec'),namespace)
        self.base.reactor.register_timer=lambda fn,*args:fn
        self.base.reactor.unregister_timer=lambda timer:None
        counts={'start':0,'stop':0}
        printer=types.SimpleNamespace(get_reactor=lambda:self.base.reactor,command_error=RuntimeError)
        helper=namespace[cls.name](printer,lambda now:dict(data=self.rows(0),errors=0,overflows=0),
                                   lambda:counts.update(start=counts['start']+1),
                                   lambda:counts.update(stop=counts['stop']+1),.1)
        other=lambda message:True;helper.add_client(other)
        self.base.objects['lis2dw'].batch_bulk=helper
        self.start();helper._proc_batch(self.base.reactor.now)
        self.end_records()
        self.assertEqual(helper.client_cbs,[other]);self.assertEqual(counts,{'start':1,'stop':0})
        helper._stop();self.assertEqual(counts['stop'],1)
    def test_actual_native_mcu_adc_handler_preserves_decoded_report(self):
        tree=ast.parse((ROOT/'reference/mcu.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MCU_adc')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_old_handle_analog_in_state')
        scope={};exec(compile(ast.Module(body=[method],type_ignores=[]),'supplied_mcu', 'exec'),scope)
        self.adc._inv_max_adc=1./65535.;self.adc._report_clock=300
        self.adc._mcu=types.SimpleNamespace(clock32_to_clock64=lambda v:v,clock_to_print_time=lambda v:v/1000.)
        self.start()
        scope[method.name](self.adc,{'value':12345,'next_clock':100540})
        records=self.end_records();record=next(v for v in records if v['type']=='adc')
        self.assertAlmostEqual(record['print_time'],100.24)
        self.assertAlmostEqual(record['normalized_value'],12345/65535.)
        self.assertEqual(len(self.adc.calls),1)
    def test_force_reply_pending_before_stop_is_not_lost(self):
        self.start()
        self.base.reactor.now+=.25
        self.base.reader.extract_last_value_before_g('command H7 ok. 8001234 19 g')
        records=self.end_records()
        self.assertIn(8001234,[r['raw'] for r in records if r['type']=='sample'])
    def test_repeated_adc_report_is_recorded_and_skipped_capture_continues(self):
        self.start();self.adc._callback([(100.24,.3),(100.24,.3)])
        self.base.feed();self.assertTrue(self.cell.active)
        records=self.end_records()
        self.assertEqual(len([r for r in records if r['type']=='adc']),1)
        skipped=[r for r in records if r.get('event')=='adc_report_skipped']
        self.assertEqual(skipped[0]['reason'],'repeated_or_reversed')
    def test_missing_native_adc_report_is_recorded_as_a_gap_capture_continues(self):
        self.adc._report_time=.01
        self.start();self.adc._callback([(100.22,.2),(100.24,.3)])
        self.base.feed();self.assertTrue(self.cell.active)
        self.assertFalse(any('capture stopped' in s for s in self.base.gcode.messages))
        records=self.end_records()
        gap=[r for r in records if r.get('event')=='adc_gap'][0]
        self.assertAlmostEqual(gap['gap_s'],.02);self.assertAlmostEqual(gap['expected_s'],.01)
        self.assertEqual(len([r for r in records if r['type']=='adc']),2)
    def test_silent_adc_channel_is_marked_lost_then_resumed_capture_continues(self):
        self.start()
        for _ in range(10):
            self.base.reactor.now+=.25
            self.cell.sensors.last_batch_time=self.base.reactor.now   # acceleration keeps arriving
            self.base.feed()
        self.assertTrue(self.cell.active)
        self.adc_report();self.base.feed()                # the channel reports again
        records=self.end_records()
        self.assertTrue(any(r.get('event')=='adc_channel_lost' for r in records))
        self.assertTrue(any(r.get('event')=='adc_channel_resumed' for r in records))
    def test_adc_log_write_failure_still_stops_capture(self):
        self.start();self.cell._write=lambda record:False
        self.adc._callback([(100.24,.3)])
        self.base.feed();self.assertFalse(self.cell.active)
    def test_native_mcu_batch_handler_delivers_every_report_to_observer(self):
        tree=ast.parse((ROOT/'reference/mcu.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MCU_adc')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_handle_analog_in_state')
        scope={};exec(compile(ast.Module(body=[method],type_ignores=[]),'supplied_mcu','exec'),scope)
        self.adc._unpack_from=lambda value:(10000,20000)
        self.adc._inv_max_adc=1./65535.;self.adc._report_clock=5
        self.adc._mcu=types.SimpleNamespace(clock32_to_clock64=lambda v:v,clock_to_print_time=lambda v:v/1000.)
        self.start();scope[method.name](self.adc,{'values':b'example','next_clock':100250})
        records=self.end_records();reports=[v for v in records if v['type']=='adc']
        self.assertEqual(len(reports),2)
        self.assertAlmostEqual(reports[0]['normalized_value'],10000/65535.)
        self.assertAlmostEqual(reports[1]['normalized_value'],20000/65535.)

class BinaryTests(unittest.TestCase):
    def test_exact_float64_samples_and_rotation_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer=AccelerationWriter(str(Path(tmp)/'sample'),dict(session='s'),rotate_bytes=1000,reserve_bytes=0)
            expected=[]
            for batch in range(5):
                rows=[(1.+(batch*16+i)/1600.,i*.123456789,-i*.2,9800.) for i in range(16)]
                expected.extend(rows);self.assertTrue(writer.put(rows,2.+batch*.01))
            writer.close();writer.thread.join(3)
            rows=list(read_acceleration(writer.paths))
            self.assertEqual([(r['t'],r['x'],r['y'],r['z']) for r in rows],expected)
            self.assertGreater(len(writer.paths),1)
    def test_truncation_missing_parts_and_mixed_session_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=AccelerationWriter(str(Path(tmp)/'sample'),dict(session='s'),rotate_bytes=100,reserve_bytes=0)
            for i in range(3):w.put([(1+i*.001,0,0,1)],1.)
            w.close();w.thread.join(3)
            with self.assertRaisesRegex(ValueError,'part'):list(read_acceleration(w.paths[1:]))
            path=Path(w.paths[-1]);path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError,'truncated'):list(read_acceleration(w.paths))
    def test_budget_and_low_disk_fail_visibly(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=AccelerationWriter(str(Path(tmp)/'sample'),dict(session='s'),max_bytes=1000,reserve_bytes=0)
            w.put([(1+i*.001,0,0,1) for i in range(100)],1.)
            w.close();w.thread.join(3)
            self.assertIn('budget',w.error)
            with mock.patch('deep_calibration_sensors.shutil.disk_usage',return_value=types.SimpleNamespace(free=0)):
                with self.assertRaisesRegex(OSError,'reserve'):
                    AccelerationWriter(str(Path(tmp)/'low'),dict(session='s'),reserve_bytes=1)
    def test_queue_overflow_never_silently_drops_a_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=AccelerationWriter(str(Path(tmp)/'sample'),dict(session='s'),reserve_bytes=0)
            with mock.patch.object(w.queue,'put_nowait',side_effect=queue.Full):
                self.assertFalse(w.put([(1.,0,0,1)],1.))
            w.thread.join(3);self.assertIn('Full',w.error)
    def test_timestamp_reversal_is_not_accepted_as_continuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=AccelerationWriter(str(Path(tmp)/'sample'),dict(session='s'),reserve_bytes=0)
            w.put([(1.,0,0,1),(.9,0,0,1)],1.)
            w.close();w.thread.join(3)
            self.assertIn('reversed',w.error)

if __name__=='__main__':unittest.main()
