#!/usr/bin/env python3
"""Offline paired calibration analysis; never sends commands to a printer."""
import argparse
import collections
import csv
import json
import math
from pathlib import Path
import statistics
from deep_calibration import finite

FIELDS = ['run','segment','t','print_time','label','label_source','label_inferred','material','layer','height','width','recipe_speed','recipe_fan',
          'live_speed','live_e_speed','volumetric_flow','fan','nozzle_temp','bed_temp','offset_z',
          'probe_offset','raw','filtered_raw','delta_counts','filtered_grams','baseline_valid',
          'rate_hz','nyquist_hz','shaper_resolvable','live_x','live_y','live_z','mesh_live',
          'planned_mesh_error','mesh_comparable','context_lag','motion_method','native_generation','cpg','board_overload','accel_rms','accel_shaper_power','eligible','rejection']
FEATURES = ['force_relative_good','live_speed','height','width','fan','layer',
            'volumetric_flow','nozzle_temp','bed_temp','force_x_flow']


def median(values):
    values = [x for x in values if finite(x)]
    return statistics.median(values) if values else None


def load_run(path, settle=5.):
    contexts = {}
    samples = []
    events = []
    metadata = None
    segment = 0
    changed = -1.e99
    previous = None
    end = None
    final_sensors = {}
    malformed = False
    with open(path) as stream:
        for line_number, line in enumerate(stream,1):
            if not line.strip(): continue
            try:
                item = json.loads(line)
            except ValueError:
                malformed = True
                events.append(dict(event='invalid_json',line=line_number))
                continue
            kind = item.get('type')
            if kind=='session':
                if metadata is not None: raise ValueError('multiple sessions in '+str(path))
                metadata = item
            elif kind=='context':
                contexts[item['id']] = item
                if len(contexts)>128:contexts.pop(next(iter(contexts)))
            elif kind=='event':
                events.append(item)
                if item.get('event') in ('conditions_changed','label','recipe','baseline'):
                    segment += 1
                    changed = item['t']
                if item.get('event')=='session_end':
                    end = item.get('reason');final_sensors=item.get('sensor_capture',{})
            elif kind=='sample':
                ctx = contexts.get(item.get('context_id'),{})
                recipe = ctx.get('recipe',{})
                motion = item.get('motion_at_receipt') or ctx.get('motion_requested',{})
                mesh = ctx.get('mesh',{})
                live = motion.get('live_position') or [None,None,None]
                info = ctx.get('print_stats',{}).get('info') or {}
                layer = info.get('current_layer') or recipe.get('layer')
                origin = ctx.get('gcode',{}).get('homing_origin') or [None,None,None]
                nozzle = ctx.get('heaters',{}).get('extruder',{}).get('temperature')
                bed = ctx.get('heaters',{}).get('heater_bed',{}).get('temperature')
                v,e = motion.get('live_velocity'),motion.get('live_extruder_velocity')
                diameter = recipe.get('filament')
                flow = e*math.pi*(diameter/2)**2 if finite(e) and finite(diameter) else None
                error = (mesh['observed_adjustment']-mesh['expected_adjustment']
                         if finite(mesh.get('observed_adjustment')) and finite(mesh.get('expected_adjustment')) else None)
                row = dict(run=str(path.name),segment=segment,t=item['t'],label=ctx.get('label','UNLABELLED'),
                           label_source='manual_or_context',label_inferred=False,
                           material=recipe.get('material'),layer=layer,height=recipe.get('height'),
                           width=recipe.get('width'),recipe_speed=recipe.get('speed'),recipe_fan=recipe.get('fan'),
                           live_speed=v,live_e_speed=e,volumetric_flow=flow,fan=ctx.get('part_fan',{}).get('speed'),
                           nozzle_temp=nozzle,bed_temp=bed,offset_z=origin[2],probe_offset=ctx.get('configured_probe_offset'),
                           raw=item.get('raw'),filtered_raw=item.get('filtered_raw'),
                           delta_counts=item.get('filtered_delta_counts'),filtered_grams=item.get('filtered_grams'),
                           baseline_valid=item.get('baseline_valid'),rate_hz=item.get('rate_hz'),
                           nyquist_hz=item.get('nyquist_hz'),shaper_resolvable=item.get('shaper_resolvable'),
                           live_x=live[0],live_y=live[1],live_z=live[2],mesh_live=mesh.get('live_xy_interpolation'),
                           planned_mesh_error=error,mesh_comparable=mesh.get('comparable'),context_lag=item.get('context_lag'))
                row.update(native_generation=item.get('native_command_generation'),cpg=item.get('counts_per_gram'))
                row['motion_method'] = motion.get('method','legacy_context_status')
                row['board_overload'] = item.get('board_overload',False)
                row['accel_rms']=row['accel_shaper_power']=None
                row['print_time'] = motion.get('print_time')
                if item.get('mesh_interpolation_at_receipt') is not None:
                    row['mesh_live'] = item['mesh_interpolation_at_receipt']
                reasons = []
                if row['board_overload']:reasons.append('board_overload_or_invalid_force')
                if row['label'] not in ('GOOD','TOO_HIGH','TOO_LOW'): reasons.append('unlabelled_or_transition')
                if ctx.get('print_stats',{}).get('state')!='printing': reasons.append('not_printing')
                if item['t']-changed<settle: reasons.append('settling_after_change')
                if not finite(v) or v<5 or not finite(e) or e<=0: reasons.append('travel_or_slow_or_retraction')
                if not finite(row['context_lag']) or not 0<=row['context_lag']<=.35: reasons.append('context_delay')
                if item.get('filter_warmup'): reasons.append('filter_warmup')
                if not mesh.get('comparable') or not mesh.get('in_chain') or not mesh.get('callback_matches'):
                    reasons.append('mesh_not_aligned_or_unverified')
                if error is None or abs(error)>.005: reasons.append('planned_mesh_mismatch')
                if previous is not None and finite(v) and finite(previous[1]):
                    dt = item['t']-previous[0]
                    if dt<=0 or abs(v-previous[1])/dt>100: reasons.append('speed_transition')
                previous = (item['t'],v)
                if not all(finite(row.get(key)) for key in ('offset_z','filtered_raw','layer','height','width',
                                                           'fan','nozzle_temp','bed_temp','volumetric_flow')):
                    reasons.append('missing_numeric_context')
                row['eligible'],row['rejection'] = not reasons,';'.join(reasons)
                samples.append(row)
    # Backward annotations label only the unchanged, previously unlabelled
    # setting. Never overwrite explicit GOOD/TOO_HIGH/TOO_LOW/TRAVEL labels.
    for event in events:
        if event.get('event') != 'adjustment_label' or event.get('label') not in ('TOO_HIGH','TOO_LOW','GOOD'):
            continue
        if not all(finite(event.get(k)) for k in ('start_t','end_t','from_z')):
            continue
        for row in samples:
            if (row['label']=='UNLABELLED' and row['layer']==1
                    and event['start_t'] <= row['t'] < event['end_t']
                    and finite(row['offset_z']) and abs(row['offset_z']-event['from_z']) < 0.000001):
                row['label']=event['label']
                row['label_source']=event.get('source','relative_babystep_direction')
                row['label_inferred']=True
                reasons=[v for v in row['rejection'].split(';') if v and v!='unlabelled_or_transition']
                row['eligible']=not reasons
                row['rejection']=';'.join(reasons)
    if metadata is None or metadata.get('schema')!=1: raise ValueError('unsupported/missing session schema in '+str(path))
    complete = (end in ('user_stop','print_complete','duration_limit','first_layer_done') and not malformed
                and not final_sensors.get('error') and not final_sensors.get('acceleration_writer_error'))
    if not complete:
        for row in samples:
            row['eligible']=False
            row['rejection']+=';incomplete_session'
    return dict(metadata=metadata,samples=samples,events=events,complete=complete,end=end,path=str(path))


def summarize(run):
    groups = collections.defaultdict(list)
    for row in run['samples']:
        if row['eligible']: groups[row['segment']].append(row)
    segments = []
    for segment, rows in groups.items():
        if len(rows)<8 or rows[-1]['t']-rows[0]['t']<10: continue
        entry = {key:median([row.get(key) for row in rows]) for key in FIELDS
                 if key not in ('run','material','label','rejection','motion_method')}
        entry.update(run=rows[0]['run'],material=rows[0]['material'],label=rows[0]['label'],n=len(rows),
                     printer_id=run['metadata'].get('printer_id'),
                     span=rows[-1]['t']-rows[0]['t'],segment=segment,
                     force_raw_sd=statistics.pstdev(row['raw'] for row in rows),
                     force_filtered_sd=statistics.pstdev(row['filtered_raw'] for row in rows))
        # A moving offset within a segment is not a valid fixed-condition label.
        if max(row['offset_z'] for row in rows)-min(row['offset_z'] for row in rows)>.0001: continue
        aligned=[row for row in rows if finite(row.get('accel_rms')) and finite(row.get('accel_shaper_power'))]
        if len(aligned)<8 or aligned[-1]['t']-aligned[0]['t']<10:
            entry['accel_rms']=entry['accel_shaper_power']=None
        segments.append(entry)
    return segments


def condition(s):
    # Pair only within a run and an unchanged declared recipe/layer/fan/temp.
    return (s['run'],s['material'],s['height'],s['width'],s['recipe_speed'],
            s['recipe_fan'],s['layer'],round(s['fan'],2),round(s['nozzle_temp']/5),round(s['bed_temp']/5),
            s['native_generation'],s['cpg'],s['probe_offset'])


def paired(segments):
    goods = collections.defaultdict(list)
    for s in segments:
        if s['label']=='GOOD': goods[condition(s)].append(s)
    output = []
    for s in segments:
        good = goods.get(condition(s),[])
        if not good or max(g['offset_z'] for g in good)-min(g['offset_z'] for g in good)>.02: continue
        ref_force = median([g['filtered_raw'] for g in good])
        ref_offset = median([g['offset_z'] for g in good])
        row = dict(s,force_relative_good=s['filtered_raw']-ref_force,
                   good_force_reference=ref_force,good_offset_reference=ref_offset,
                   target_offset_delta=ref_offset-s['offset_z'])
        row['force_x_flow']=row['force_relative_good']*row['volumetric_flow']
        # Reject unmeasured probe reference rather than assuming -0.25.
        if finite(row.get('probe_offset')) and all(finite(row.get(k)) for k in FEATURES): output.append(row)
    return output


def solve(matrix, vector):
    a = [list(row)+[v] for row,v in zip(matrix,vector)]
    for i in range(len(a)):
        pivot=max(range(i,len(a)),key=lambda j:abs(a[j][i]))
        a[i],a[pivot]=a[pivot],a[i]
        if abs(a[i][i])<1.e-12: raise ValueError('singular regression')
        divisor=a[i][i];a[i]=[x/divisor for x in a[i]]
        for j in range(len(a)):
            if i!=j:
                f=a[j][i];a[j]=[x-f*y for x,y in zip(a[j],a[i])]
    return [row[-1] for row in a]


def fit(pairs, extra_features=()):
    """Experimental regression; final run held out as a whole, never random rows."""
    feature_names=FEATURES+list(extra_features)
    models = {}
    identities = sorted(set((p.get('printer_id') or 'unknown',p['material']) for p in pairs))
    for printer_id, material in identities:
        subset=[p for p in pairs if p['material']==material and (p.get('printer_id') or 'unknown')==printer_id]
        runs=sorted(set(p['run'] for p in subset))
        result=dict(status='insufficient_data',required='>=4 runs, >=24 training segments, >=6 held-out segments',
                    automatic_application=False,
                    limitation='retrospective model requires a GOOD force reference for each matched recipe; not a standalone gap sensor')
        models[printer_id+':'+material]=result
        if printer_id=='unknown':
            result['status']='missing_printer_identity';continue
        if len(runs)<4: continue
        train=[p for p in subset if p['run']!=runs[-1]]
        test=[p for p in subset if p['run']==runs[-1]]
        if len(train)<24 or len(test)<6: continue
        if len(set(p['probe_offset'] for p in subset))!=1:
            result.update(status='inconsistent_probe_reference');continue
        if len(set(p.get('cpg') for p in subset))!=1:
            result.update(status='inconsistent_force_scale');continue
        if len(set(p['target_offset_delta'] for p in train))<3:
            result.update(status='insufficient_offset_variation');continue
        means=[statistics.mean(p[k] for p in train) for k in feature_names]
        scales=[statistics.pstdev(p[k] for p in train) or 1. for k in feature_names]
        def features(p): return [1.]+[(p[k]-m)/s for k,m,s in zip(feature_names,means,scales)]
        x=[features(p) for p in train];y=[p['target_offset_delta'] for p in train];n=len(feature_names)+1
        normal=[[sum(row[i]*row[j] for row in x)+(1. if i==j and i>0 else 0.) for j in range(n)] for i in range(n)]
        rhs=[sum(row[i]*target for row,target in zip(x,y)) for i in range(n)]
        coefficients=solve(normal,rhs)
        def predict(p): return sum(a*b for a,b in zip(coefficients,features(p)))
        errors=[predict(p)-p['target_offset_delta'] for p in test]
        domain={k:[min(p[k] for p in train),max(p[k] for p in train)] for k in feature_names}
        outside=sum(any(p[k]<domain[k][0]-1.e-9 or p[k]>domain[k][1]+1.e-9 for k in feature_names) for p in test)
        result.update(status='experimental_candidate',features=feature_names,means=means,scales=scales,
                      intercept=coefficients[0],coefficients=coefficients[1:],ridge_lambda=1.,
                      train_runs=runs[:-1],held_out_run=runs[-1],train_segments=len(train),test_segments=len(test),
                      held_out_mae_mm=statistics.mean(abs(v) for v in errors),
                      zero_correction_mae_mm=statistics.mean(abs(p['target_offset_delta']) for p in test),
                      held_out_max_error_mm=max(abs(v) for v in errors),
                      held_out_out_of_domain_segments=outside,
                      improves_zero_baseline=(statistics.mean(abs(v) for v in errors)
                                               < statistics.mean(abs(p['target_offset_delta']) for p in test)),
                      probe_offset=subset[0]['probe_offset'],
                      formula='delta_Z = intercept + sum(coeff_i * ((feature_i - mean_i) / scale_i))',
                      training_domain=domain)
    return models


LABELS = ('GOOD','TOO_HIGH','TOO_LOW')

def parse_relabel(items):
    """'-0.125=TOO_LOW' -> [(-0.125, 'TOO_LOW')]"""
    out=[]
    for item in items or []:
        try:
            z,label=item.split('=',1); z=float(z); label=label.strip().upper()
        except ValueError:
            raise ValueError('--relabel takes OFFSET=LABEL, for example -0.125=TOO_LOW: '+item)
        if not math.isfinite(z) or label not in LABELS:
            raise ValueError('--relabel label must be GOOD, TOO_HIGH or TOO_LOW: '+item)
        out.append((z,label))
    return out

def apply_relabel(runs, relabels):
    """A label judged after the print (a scrape on layer 2, a peel test)
    replaces the label recorded during it, for first-layer readings at that
    offset. Marked as such, never as a print-time label."""
    counts={}
    for z,label in relabels:
        for run in runs:
            for row in run['samples']:
                if (row.get('layer')==1 and finite(row.get('offset_z')) and abs(row['offset_z']-z)<0.0005
                        and row.get('label') in LABELS+('UNLABELLED',)):
                    row['label']=label
                    row['label_source']='relabelled_after_print'
                    row['label_inferred']=False
                    reasons=[v for v in row['rejection'].split(';') if v and v!='unlabelled_or_transition']
                    row['eligible']=not reasons
                    row['rejection']=';'.join(reasons)
                    counts['%+.4f=%s'%(z,label)]=counts.get('%+.4f=%s'%(z,label),0)+1
    return counts

def analyze(paths, output, settle=5., want_fit=False, vibration=True, relabel=None):
    paths=[Path(path) for path in paths]
    if len({path.resolve() for path in paths})!=len(paths):
        raise ValueError('duplicate input session: each capture must be analyzed once')
    if len({path.name for path in paths})!=len(paths):
        raise ValueError('session filenames must be unique: matching names would merge labels or leak into validation')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    runs=[load_run(Path(path),settle) for path in paths]
    relabelled=apply_relabel(runs, parse_relabel(relabel))
    vibration_reports={}
    if vibration:
        from vibration_analysis import analyze_vibration
        for run in runs:
            result=analyze_vibration(run,output)
            vibration_reports[run['path']]=result
            if result.get('valid') and result.get('csv'):
                with open(result['csv']) as stream:
                    aligned={float(row['force_print_time']):row for row in csv.DictReader(stream)}
                for row in run['samples']:
                    value=aligned.get(row.get('print_time'))
                    if value is not None:
                        row['accel_rms']=float(value['ac_rms_total'])
                        row['accel_shaper_power']=sum(json.loads(value['shaper_tone_projection_power']).values())
            if result.get('valid') is False:
                run['complete']=False
                for row in run['samples']:
                    row['eligible']=False;row['rejection']+=';acceleration_incomplete_or_gapped'
    if not vibration:
        for run in runs:
            if run['metadata'].get('sensor_capture',{}).get('acceleration'):
                vibration_reports[run['path']]=dict(status='validation_skipped',valid=False)
                run['complete']=False
                for row in run['samples']:
                    row['eligible']=False;row['rejection']+=';acceleration_validation_skipped'
    segments=[s for run in runs for s in summarize(run)]
    pairs=paired(segments)
    rows=[s for run in runs for s in run['samples']]
    with open(output/'samples.csv','w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    report=dict(schema=1,software_analysis_only=True,relabelled=relabelled,
                vibration=vibration_reports,
                limitations=['force does not uniquely identify gap','deposited material weight and label order can confound force; counterbalance offset trials',
                             'input-shaper frequencies can exceed native Nyquist limit',
                             'host receipt is not ADC acquisition time','manual labels and queued offsets are not physical gap measurements',
                             'raw and filtered readings can drift with temperature and native tare/calibration',
                             'GOOD references and material offsets are observations, not automatically applied calibrations'],
                runs=[dict(path=r['path'],complete=r['complete'],end=r['end'],samples=len(r['samples']),
                           accepted=sum(s['eligible'] for s in r['samples']),
                           rejection_counts=dict(collections.Counter(reason for s in r['samples'] for reason in s['rejection'].split(';') if reason)),
                           observed_rate_hz=median([s['rate_hz'] for s in r['samples']]),
                           shaper_resolvable_samples=sum(s['shaper_resolvable'] is True for s in r['samples'])) for r in runs],
                segments=segments,paired_segments=pairs,
                material_good_observations=[{k:s[k] for k in ('run','printer_id','material','probe_offset','height','width','recipe_speed','fan','layer','offset_z','n')}
                                            for s in segments if s['label']=='GOOD'])
    signal_groups=collections.defaultdict(list)
    for row in rows:
        if finite(row['raw']) and finite(row['filtered_raw']):
            signal_groups[(row['run'],row['label'],row['recipe_fan'],row['layer'])].append(row)
    report['signal_statistics']=[dict(run=key[0],label=key[1],recipe_fan=key[2],layer=key[3],n=len(values),
                                     raw_sd_counts=statistics.pstdev(v['raw'] for v in values),
                                     filtered_sd_counts=statistics.pstdev(v['filtered_raw'] for v in values),
                                     note='lower filtered noise is not proof of vibration isolation or gap accuracy')
                                  for key,values in signal_groups.items() if len(values)>=4]
    # ADC reports are streamed to their own CSV, not retained as large arrays.
    adc_counts=collections.Counter()
    with open(output/'adc.csv','w',newline='') as stream:
        fields=['run','channel','host_received','print_time','normalized_value','age','callback_format']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for path in paths:
            with open(path) as source:
                for line in source:
                    try:item=json.loads(line)
                    except ValueError:continue
                    if item.get('type')=='adc':
                        writer.writerow(dict(run=Path(path).name,channel=item.get('channel'),
                                             host_received=item.get('t'),print_time=item.get('print_time'),
                                             normalized_value=item.get('normalized_value'),age=item.get('age'),
                                             callback_format=item.get('callback_format')))
                        adc_counts[item.get('channel')]+=1
    report['adc_report_counts']=dict(adc_counts)
    if want_fit:
        report['models']=fit(pairs)
        vibration_pairs=[p for p in pairs if finite(p.get('accel_rms')) and finite(p.get('accel_shaper_power'))]
        report['models_matched_without_vibration']=fit(vibration_pairs)
        report['models_with_vibration']=fit(vibration_pairs,('accel_rms','accel_shaper_power'))
        report['model_comparison_note']='Compare held-out errors only between matched models trained on the same vibration-aligned segments; neither is automatically applied.'
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,default=Path('deep_calibration_analysis'))
    parser.add_argument('--settle',type=float,default=5.,help='exclude seconds after observed label/offset/recipe/fan change')
    parser.add_argument('--fit',action='store_true',help='attempt a retrospective model with whole-run holdout')
    parser.add_argument('--skip-vibration',action='store_true',help='export force/ADC only; does not certify missing acceleration files')
    parser.add_argument('--relabel',action='append',metavar='OFFSET=LABEL',help='correct the label of first-layer readings at an offset after the print, e.g. -0.125=TOO_LOW (repeatable)')
    args=parser.parse_args()
    if not math.isfinite(args.settle) or args.settle<2: parser.error('--settle must be >=2 seconds')
    try:
        parse_relabel(args.relabel)          # check before loading anything
    except ValueError as exc:
        parser.error(str(exc))
    try:
        report=analyze(args.logs,args.output,args.settle,args.fit,not args.skip_vibration,args.relabel)
    except ValueError as exc:
        parser.error(str(exc))
    if report.get('relabelled'):
        print('Relabelled after the print: '+', '.join('%s (%d readings)'%(k,v) for k,v in sorted(report['relabelled'].items())))
    print('Wrote samples.csv and report.json; %d stable segments, %d GOOD-paired segments.'%
          (len(report['segments']),len(report['paired_segments'])))
    print('Experimental offline analysis only. No printer settings were changed.')

if __name__=='__main__': main()
