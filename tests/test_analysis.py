import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from analyze import analyze, fit, load_run, paired, summarize

def write_run(path, complete=True):
    records=[dict(type='session',schema=1,version='test',run=path.stem,printer_id='a'*32)]
    n=0
    for segment,(label,offset,force) in enumerate([('TOO_HIGH',.7,7999000),('TOO_LOW',.5,8001000),('GOOD',.6,8000000)]):
        start=segment*40
        records.append(dict(type='event',event='label',t=start,label=label))
        for i in range(30):
            t=start+i
            ctx=dict(type='context',id=n,t=t+.05,label=label,
                     recipe=dict(material='PLA',height=.2,width=.45,speed=40,fan=50,layer=1,filament=1.75),
                     print_stats=dict(state='printing',info={'current_layer':1}),
                     gcode=dict(homing_origin=[0,0,offset,0]),configured_probe_offset=-.25,
                     part_fan={'speed':.5},heaters={'extruder':{'temperature':230},'heater_bed':{'temperature':60}},
                     motion_requested=dict(live_velocity=40,live_extruder_velocity=1.5,live_position=[i,10,1]),
                     mesh=dict(comparable=True,in_chain=True,callback_matches=True,
                               expected_adjustment=-3.4,observed_adjustment=-3.4,live_xy_interpolation=-3.4))
            records.extend([ctx,dict(type='sample',t=t,context_id=n,context_lag=.05,raw=force,filtered_raw=force,
                                     filter_warmup=False,rate_hz=4.,nyquist_hz=2.,shaper_resolvable=False,
                                     baseline_valid=False,native_command_generation=1,counts_per_gram=None)])
            n+=1
    if complete: records.append(dict(type='event',event='session_end',t=120,reason='user_stop'))
    path.write_text(''.join(json.dumps(v)+'\n' for v in records))

class AnalysisTests(unittest.TestCase):
    def test_full_log_exports_three_stable_segments_and_signed_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.jsonl';write_run(p)
            report=analyze([p],Path(tmp)/'out',want_fit=True)
            self.assertEqual(len(report['segments']),3)
            rows=report['paired_segments'];self.assertEqual(len(rows),3)
            self.assertAlmostEqual(rows[0]['target_offset_delta'],-.1)
            self.assertAlmostEqual(rows[1]['target_offset_delta'],.1)
            self.assertEqual(rows[0]['probe_offset'],-.25)
            self.assertTrue((Path(tmp)/'out/samples.csv').exists())
            self.assertEqual(report['models']['a'*32+':PLA']['status'],'insufficient_data')
    def test_incomplete_and_truncated_sessions_never_train(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.jsonl';write_run(p,complete=False)
            self.assertFalse(load_run(p)['complete']);self.assertEqual(summarize(load_run(p)),[])
            write_run(p)
            with p.open('a') as f: f.write('{truncated')
            self.assertFalse(load_run(p)['complete'])
    def test_context_lag_and_travel_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.jsonl';write_run(p)
            records=[json.loads(line) for line in p.read_text().splitlines()]
            for record in records:
                if record['type']=='sample': record['context_lag']=2.
                if record['type']=='context': record['motion_requested']['live_extruder_velocity']=0.
            p.write_text(''.join(json.dumps(v)+'\n' for v in records))
            run=load_run(p)
            self.assertTrue(all(not s['eligible'] for s in run['samples']))
            self.assertIn('context_delay',run['samples'][0]['rejection'])
            self.assertEqual(summarize(run),[])
    def test_ambiguous_good_offsets_are_not_training_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.jsonl';write_run(p);segments=summarize(load_run(p))
            good=dict(segments[-1],offset_z=.65)
            self.assertEqual(paired(segments+[good]),[])
    def test_native_tare_generation_separates_good_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.jsonl';write_run(p);segments=summarize(load_run(p))
            segments[-1]['native_generation']=2
            result=paired(segments)
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['label'],'GOOD')
    def test_whole_run_holdout_model_reports_error_and_never_auto_applies(self):
        rows=[]
        for run in range(4):
            for j in range(10):
                force=(j-4)*50.
                rows.append(dict(run='run%d'%run,printer_id='printer_a',material='PLA',probe_offset=-.25,
                                 force_relative_good=force,live_speed=40.,height=.2,width=.45,fan=.5,
                                 layer=1.,volumetric_flow=3.,nozzle_temp=230.,bed_temp=60.,
                                 force_x_flow=force*3.,target_offset_delta=force*.0001))
        model=fit(rows)['printer_a:PLA']
        self.assertEqual(model['status'],'experimental_candidate')
        self.assertEqual(model['held_out_run'],'run3');self.assertNotIn('run3',model['train_runs'])
        self.assertLess(model['held_out_mae_mm'],model['zero_correction_mae_mm'])
        self.assertFalse(model['automatic_application'])
    def test_inconsistent_probe_reference_and_separate_printers(self):
        rows=[]
        for run in range(4):
            for j in range(10):
                rows.append(dict(run='r%d'%run,printer_id='p',material='PLA',probe_offset=-.25 if run<3 else 0.,
                                 target_offset_delta=j*.01))
        self.assertEqual(fit(rows)['p:PLA']['status'],'inconsistent_probe_reference')
        rows[-1]['printer_id']='other'
        self.assertIn('other:PLA',fit(rows))
    def test_duplicate_inputs_or_names_cannot_leak_between_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run.jsonl';write_run(p)
            with self.assertRaisesRegex(ValueError,'duplicate input'):analyze([p,p],Path(tmp)/'out')
            folder=Path(tmp)/'other';folder.mkdir();q=folder/p.name;write_run(q)
            with self.assertRaisesRegex(ValueError,'filenames must be unique'):analyze([p,q],Path(tmp)/'out')
    def test_force_gain_change_blocks_cross_run_model(self):
        rows=[]
        for run in range(4):
            for j in range(10):
                rows.append(dict(run='r%d'%run,printer_id='p',material='PLA',probe_offset=-.25,
                                 cpg=100 if run<3 else 200,target_offset_delta=j*.01))
        self.assertEqual(fit(rows)['p:PLA']['status'],'inconsistent_force_scale')
    def test_optional_vibration_model_has_explicit_features_and_same_holdout(self):
        rows=[]
        for run in range(4):
            for j in range(10):
                rows.append(dict(run='r%d'%run,printer_id='p',material='PLA',probe_offset=-.25,
                                 force_relative_good=j*50.,live_speed=40.,height=.2,width=.45,fan=.5,layer=1.,
                                 volumetric_flow=3.,nozzle_temp=230.,bed_temp=60.,force_x_flow=j*150.,
                                 accel_rms=float(j),accel_shaper_power=float(j*j),target_offset_delta=j*.01))
        base=fit(rows)['p:PLA'];enhanced=fit(rows,('accel_rms','accel_shaper_power'))['p:PLA']
        self.assertEqual(base['held_out_run'],enhanced['held_out_run'])
        self.assertEqual(base['train_segments'],enhanced['train_segments'])
        self.assertIn('accel_rms',enhanced['features']);self.assertNotIn('accel_rms',base['features'])
        self.assertFalse(enhanced['automatic_application'])

if __name__=='__main__': unittest.main()
