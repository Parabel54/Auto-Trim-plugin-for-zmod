# Post-print analysis of continuous acceleration files. GPL-3.0-only.
# Streaming reader; no FFTs, projection calculations or file decoding on printer.
import collections
import csv
import math
from pathlib import Path
import statistics
import struct
from deep_calibration_sensors import read_acceleration


def features(rows, frequencies):
    if len(rows)<8:return None
    span=rows[-1]['t']-rows[0]['t']
    if span<=0:return None
    axes=[[row[k] for row in rows] for k in ('x','y','z')]
    means=[statistics.mean(v) for v in axes]
    ac=[[v-mean for v in values] for values,mean in zip(axes,means)]
    rms=[math.sqrt(sum(v*v for v in values)/len(values)) for values in ac]
    output=dict(n=len(rows),span_s=span,rate_hz=(len(rows)-1)/span,
                ac_rms_x=rms[0],ac_rms_y=rms[1],ac_rms_z=rms[2],
                ac_rms_total=math.sqrt(sum(v*v for v in rms)),
                ac_peak_total=max(math.sqrt(sum(ac[j][i]**2 for j in range(3))) for i in range(len(rows))))
    # Hann-windowed tone projections, not total band energy or force subtraction.
    weights=[.5-.5*math.cos(2*math.pi*i/(len(rows)-1)) for i in range(len(rows))]
    total_weight=sum(weights)
    projections={}
    for hz in frequencies:
        if hz<=0 or hz>=output['rate_hz']/2:continue
        power=0.
        for values in ac:
            c=sum(v*w*math.cos(2*math.pi*hz*(r['t']-rows[0]['t'])) for v,w,r in zip(values,weights,rows))
            s=sum(v*w*math.sin(2*math.pi*hz*(r['t']-rows[0]['t'])) for v,w,r in zip(values,weights,rows))
            power+=2*(c*c+s*s)/(total_weight*total_weight)
        projections['%.3f'%hz]=power
    output['shaper_tone_projection_power']=projections
    return output


def analyze_vibration(run, output, window=.25):
    import json
    metadata=run['metadata']
    requested=metadata.get('sensor_capture',{}).get('acceleration',False)
    if not requested:return dict(status='not_requested')
    path=Path(run['path']);parts=sorted(path.parent.glob(path.stem+'.accel.*.dca'))
    if not parts:return dict(status='missing_acceleration_files',valid=False)
    freqs=sorted({float(axis['shaper_freq']) for axis in metadata.get('shaper',{}).values()
                  if axis.get('shaper_freq') is not None and float(axis['shaper_freq'])>0})
    state=dict(count=0,first=None,last=None,gaps=0,max_gap=0.,driver_errors=0,driver_overflows=0)
    buffer=collections.deque(maxlen=8192)
    source=iter(read_acceleration(parts));pending=None
    def advance():
        nonlocal pending
        try:pending=next(source)
        except StopIteration:pending=None;return
        t=pending['t']
        if state['last'] is not None:
            dt=t-state['last'];state['max_gap']=max(state['max_gap'],dt)
            if dt>1.5/1600.:state['gaps']+=1
        state['first']=state['first'] if state['first'] is not None else t
        state['last']=t;state['count']+=1
        state['driver_errors']=max(state['driver_errors'],pending['errors'])
        state['driver_overflows']=max(state['driver_overflows'],pending['overflows'])
    target=Path(output)/(path.stem+'.vibration.csv')
    fields=['force_print_time','force_raw','force_filtered_raw','label','offset_z','n','span_s','rate_hz',
            'ac_rms_x','ac_rms_y','ac_rms_z','ac_rms_total','ac_peak_total','shaper_tone_projection_power']
    matched=0;unmatched=0
    try:
        advance()
        with target.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            points=sorted((row for row in run['samples'] if isinstance(row.get('print_time'),(int,float))),key=lambda r:r['print_time'])
            for row in points:
                clock=row['print_time']
                while pending is not None and pending['t']<=clock:
                    buffer.append(pending)
                    while buffer and pending['t']-buffer[0]['t']>window:buffer.popleft()
                    advance()
                selected=[r for r in buffer if clock-window<=r['t']<=clock]
                result=features(selected,freqs)
                # Require the whole requested window and no significant gaps;
                # do not mistake a short fragment for aligned continuous data.
                if (result is None or result['span_s']<window*.9
                        or clock-selected[-1]['t']>.005
                        or any(b['t']-a['t']>1.5/1600. for a,b in zip(selected,selected[1:]))):
                    unmatched+=1;continue
                matched+=1
                writer.writerow(dict(force_print_time=clock,force_raw=row['raw'],force_filtered_raw=row['filtered_raw'],
                                      label=row['label'],offset_z=row['offset_z'],
                                      **dict(result,shaper_tone_projection_power=json.dumps(result['shaper_tone_projection_power']))))
            # Validate all remaining frames and final counts without retaining
            # the entire acceleration stream or silently ignoring its tail.
            while pending is not None:advance()
    except (OSError,ValueError,struct.error) as exc:
        return dict(status='invalid_or_truncated_acceleration',valid=False,error=str(exc),
                    partial_csv=str(target),**state)
    end=next((e for e in reversed(run['events']) if e.get('event')=='session_end'),{})
    final=end.get('sensor_capture',{})
    expected=final.get('frames_received')
    valid=(run['complete'] and expected==state['count'] and state['count']>0 and not state['gaps']
           and not state['driver_errors'] and not state['driver_overflows']
           and not final.get('error') and not final.get('acceleration_writer_error'))
    return dict(status='complete' if valid else 'incomplete_or_gapped',valid=valid,files=[str(p) for p in parts],
                expected_frames=expected,matched_force_intervals=matched,unmatched_force_intervals=unmatched,
                force_samples_without_print_clock=sum(row.get('print_time') is None for row in run['samples']),
                window_seconds=window,shaper_frequencies_hz=freqs,csv=str(target),**state,
                limitation='acceleration aligned to force host-receipt print clock; ADC latency/force transfer remain unknown; no vibration subtraction or automatic correction')

