import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from deep_calibration_sensors import AccelerationWriter
from vibration_analysis import features, analyze_vibration
from analyze import analyze
import test_analysis as fixtures

class VibrationTests(unittest.TestCase):
    def rows(self,n=1600):
        return [dict(t=100+i/1600.,x=10*math.sin(2*math.pi*50*i/1600.),y=0.,z=9800.,
                     host_received=2.,errors=0,overflows=0) for i in range(n)]
    def test_dc_gravity_is_removed_and_known_tone_is_detected(self):
        result=features(self.rows(400),[50,10000])
        self.assertAlmostEqual(result['ac_rms_total'],10/math.sqrt(2),delta=.1)
        self.assertAlmostEqual(result['shaper_tone_projection_power']['50.000'],50.,delta=.2)
        self.assertEqual(result['ac_rms_z'],0.)
        self.assertNotIn('10000.000',result['shaper_tone_projection_power'])
    def run_fixture(self,tmp,drop=False):
        path=Path(tmp)/'capture.jsonl';path.write_text('placeholder')
        w=AccelerationWriter(str(path.with_suffix(''))+'.accel',dict(session='capture'),rotate_bytes=10000,reserve_bytes=0)
        rows=self.rows()
        if drop:rows.pop(800)
        for i in range(0,len(rows),160):
            w.put([(r['t'],r['x'],r['y'],r['z']) for r in rows[i:i+160]],2.)
        w.close();w.thread.join(3)
        run=dict(path=str(path),complete=True,metadata=dict(sensor_capture={'acceleration':True},shaper={'x':{'shaper_freq':'50'}}),
                 samples=[dict(print_time=100.5,raw=8000000,filtered_raw=8000000,label='GOOD',offset_z=.6),
                          dict(print_time=100.75,raw=8000001,filtered_raw=8000001,label='GOOD',offset_z=.6)],
                 events=[dict(event='session_end',sensor_capture=dict(frames_received=len(rows)))])
        return run,w
    def test_streamed_alignment_checks_rotated_files_and_complete_frame_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,w=self.run_fixture(tmp);report=analyze_vibration(run,tmp)
            self.assertTrue(report['valid']);self.assertEqual(report['count'],1600)
            self.assertEqual(report['matched_force_intervals'],2)
            self.assertGreater(len(report['files']),1)
            self.assertTrue(Path(report['csv']).exists())
    def test_single_missing_frame_is_reported_as_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,w=self.run_fixture(tmp,drop=True);report=analyze_vibration(run,tmp)
            self.assertFalse(report['valid']);self.assertEqual(report['gaps'],1)
            self.assertEqual(report['status'],'incomplete_or_gapped')
    def test_missing_last_part_or_truncated_tail_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,w=self.run_fixture(tmp)
            Path(w.paths[-1]).unlink()
            report=analyze_vibration(run,tmp);self.assertFalse(report['valid'])
            self.assertNotEqual(report['count'],report['expected_frames'])
        with tempfile.TemporaryDirectory() as tmp:
            run,w=self.run_fixture(tmp);p=Path(w.paths[-1]);p.write_bytes(p.read_bytes()[:-2])
            report=analyze_vibration(run,tmp);self.assertFalse(report['valid'])
            self.assertEqual(report['status'],'invalid_or_truncated_acceleration')
    def test_missing_motion_clock_is_not_invented_for_force_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,w=self.run_fixture(tmp)
            for s in run['samples']:s['print_time']=None
            report=analyze_vibration(run,tmp)
            self.assertEqual(report['matched_force_intervals'],0)
            self.assertEqual(report['force_samples_without_print_clock'],2)
    def test_missing_requested_accel_blocks_fitting_and_adc_export_is_streamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'capture.jsonl';fixtures.write_run(path)
            records=[json.loads(line) for line in path.read_text().splitlines()]
            records[0]['sensor_capture']={'acceleration':True,'adc':True}
            records.insert(1,dict(type='adc',channel='filament',t=1.,print_time=100.,normalized_value=.3,age=.1,callback_format='batch'))
            path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            result=analyze([path],Path(tmp)/'out',want_fit=True)
            self.assertEqual(result['paired_segments'],[])
            self.assertEqual(result['vibration'][str(path)]['status'],'missing_acceleration_files')
            self.assertEqual(result['adc_report_counts']['filament'],1)
            self.assertTrue((Path(tmp)/'out/adc.csv').exists())
            result=analyze([path],Path(tmp)/'skip',want_fit=True,vibration=False)
            self.assertEqual(result['paired_segments'],[])

if __name__=='__main__':unittest.main()
