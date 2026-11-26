#!/usr/bin/env python3
"""Contact-band vibration from a Deep Calibration first-layer recording.

The toolhead accelerometer is dominated by the motors' stepping tones (each
CoreXY motor's belt speed divided by the full-step length, 0.2 mm on an AD5X:
a line at 50 mm/s and 80 degrees runs one motor at about 289 steps/s) and by
the frame resonances the input shaper is tuned to. Neither says anything
about the nozzle. This tool removes both, per reading, and reports what is
left in a low band (2-40 Hz by default), where nozzle drag or contact would
show, alongside the force.

Runs on a computer (needs numpy), not on the printer:
    python3 contact_vibration.py RECORDING.jsonl [--full-step-mm 0.2]
        [--notch-hz 6] [--band 2 40] [--window 1024] [--csv out.csv]
The .dca acceleration files are found next to the .jsonl.
"""
import argparse
import collections
import glob
import json
import math
import os
import struct
import sys

import numpy as np

RATE = 1600.

MAGIC = b'DCA2'


def read_acceleration(paths):
    """All frames as an array of (t, x, y, z), any batch format."""
    chunks = []
    for path in paths:
        data = open(path, 'rb').read()
        if not data.startswith(MAGIC):
            raise ValueError('not a Deep Calibration acceleration file: %s' % path)
        pos = len(MAGIC)
        (length,) = struct.unpack_from('<I', data, pos); pos += 4
        meta = json.loads(data[pos:pos + length]); pos += length
        batch = struct.Struct(meta.get('batch_format') or '<IdII')
        while pos < len(data):
            n = batch.unpack_from(data, pos)[0]; pos += batch.size
            chunks.append(np.frombuffer(data, dtype='<f8', count=n * 4, offset=pos).reshape(n, 4)); pos += n * 32
    return np.concatenate(chunks) if chunks else np.zeros((0, 4))


def motor_step_hz(vx, vy, full_step_mm):
    """Full-step frequencies of the two CoreXY motors for a toolhead velocity."""
    return abs(vx + vy) / full_step_mm, abs(vx - vy) / full_step_mm


def blackman_harris(n):
    # 4-term Blackman-Harris: side-lobes about -92 dB, so the stepper tones
    # and resonances (100x the contact signal) do not leak into the band
    k = np.arange(n) / (n - 1.)
    return (.35875 - .48829 * np.cos(2 * np.pi * k) + .14128 * np.cos(4 * np.pi * k)
            - .01168 * np.cos(6 * np.pi * k))


def contact_band(window, tones, resonances, band, notch_hz, rate=RATE):
    """RMS per axis (x, y, z) in `band` after removing `tones` (and their
    second harmonics) and `resonances`, each +-notch_hz but never narrower
    than the window's main lobe (4 frequency steps)."""
    n = len(window)
    freqs = np.fft.rfftfreq(n, 1. / rate)
    notch = max(notch_hz, 4.5 * rate / n)
    keep = (freqs >= band[0]) & (freqs <= band[1])
    for f in list(tones) + [2 * f for f in tones] + list(resonances):
        if f and f > 0:
            keep &= np.abs(freqs - f) > notch
    taper = blackman_harris(n)
    norm = np.sum(taper ** 2)
    out = []
    for axis in range(3):
        x = window[:, axis] - window[:, axis].mean()
        spectrum = np.abs(np.fft.rfft(x * taper)) ** 2
        out.append(math.sqrt(2. * spectrum[keep].sum() / (norm * n)))
    return tuple(out)


def shaper_frequencies(records):
    for r in records:
        sh = r.get('shaper') if r.get('type') in ('context', 'session') else None
        if not sh and r.get('type') == 'event' and r.get('event') == 'conditions_changed':
            sig = r.get('signature') or []
            sh = next((s for s in sig if isinstance(s, dict) and 'shaper_x' in s), None)
        if isinstance(sh, dict) and 'shaper_x' in sh:
            try:
                return float(sh['shaper_x']['shaper_freq']), float(sh['shaper_y']['shaper_freq'])
            except (KeyError, TypeError, ValueError):
                pass
    return None, None


def analyse(jsonl, full_step_mm=.2, notch_hz=6., band=(2., 40.), window=1024, extra_resonances=()):
    records = [json.loads(line) for line in open(jsonl)]
    base = jsonl[:-len('.jsonl')]
    paths = sorted(glob.glob(base + '_accel_*.dca'))
    if not paths:
        raise SystemExit('no acceleration files next to %s' % jsonl)
    accel = read_acceleration(paths)
    times = accel[:, 0]
    fx, fy = shaper_frequencies(records)
    resonances = [f for f in (fx, fy) if f] + list(extra_resonances)
    labels = sorted((r for r in records if r.get('type') == 'event' and r.get('event') == 'adjustment_label'),
                    key=lambda r: r['t'])
    rows = []
    half = window // 2
    for r in records:
        if r.get('type') != 'sample' or not r.get('slicer_context', {}).get('eligible'):
            continue
        seg = r['slicer_context'].get('segment') or {}
        motion = r.get('motion_at_acquisition') or {}
        pt = motion.get('print_time')
        if pt is None or not seg.get('before') or not seg.get('after'):
            continue
        dx = seg['after']['X'] - seg['before']['X']; dy = seg['after']['Y'] - seg['before']['Y']
        length = math.hypot(dx, dy)
        if length <= 0:
            continue
        speed = seg.get('feed') or motion.get('live_velocity') or 0.
        vx, vy = speed * dx / length, speed * dy / length
        tones = motor_step_hz(vx, vy, full_step_mm)
        i = int(np.searchsorted(times, pt))
        if i - half < 0 or i + half > len(times):
            continue
        win = accel[i - half:i + half, 1:4]
        if times[i + half - 1] - times[i - half] > 1.5 * window / RATE:
            continue                                  # a gap in the window
        offset = None
        for e in labels:
            if e['t'] <= r['t']:
                offset = e['to_z']
        if offset is None and labels:
            offset = labels[0]['from_z']
        cx, cy, cz = contact_band(win, tones, resonances, band, notch_hz)
        rows.append(dict(t=r['t'], print_time=pt, x=(motion.get('live_position') or [None])[0],
                         offset=offset, grams=r.get('filtered_grams'), step_hz_a=tones[0], step_hz_b=tones[1],
                         contact_x=cx, contact_y=cy, contact_z=cz))
    return rows, dict(shaper_x=fx, shaper_y=fy, frames=len(accel), files=len(paths))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('jsonl')
    ap.add_argument('--full-step-mm', type=float, default=.2)
    ap.add_argument('--notch-hz', type=float, default=6.)
    ap.add_argument('--band', type=float, nargs=2, default=(2., 40.))
    ap.add_argument('--window', type=int, default=1024)
    ap.add_argument('--csv')
    a = ap.parse_args(argv)
    rows, info = analyse(a.jsonl, a.full_step_mm, a.notch_hz, tuple(a.band), a.window)
    print('%d frames in %d files; resonances removed: X %s Hz, Y %s Hz; %d readings analysed'
          % (info['frames'], info['files'], info['shaper_x'], info['shaper_y'], len(rows)))
    by = collections.OrderedDict()
    for r in rows:
        by.setdefault(r['offset'], []).append(r)
    for off, rs in by.items():
        med = lambda k: float(np.median([r[k] for r in rs if r[k] is not None])) if any(r[k] is not None for r in rs) else float('nan')
        print('offset %s: %d readings, contact band X %.0f Y %.0f Z %.0f mm/s2, force %.1f g'
              % (off, len(rs), med('contact_x'), med('contact_y'), med('contact_z'), med('grams')))
    if a.csv:
        keys = list(rows[0].keys()) if rows else []
        with open(a.csv, 'w') as f:
            f.write(','.join(keys) + '\n')
            for r in rows:
                f.write(','.join('' if r[k] is None else str(r[k]) for k in keys) + '\n')
        print('wrote', a.csv)


if __name__ == '__main__':
    main()
