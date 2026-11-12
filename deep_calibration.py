# Deep Calibration Development Beta, AD5X/zMod. GPL-3.0-only.
# Observes native replies; never owns the serial port or changes motion.
import collections
import datetime
import json
import logging
import math
import os
import queue
import re
import shutil
import statistics
import threading
import time
import uuid
try:
    from .deep_calibration_sensors import SensorExtension
    from .deep_calibration_mesh import DeepCalibrationMesh
except ImportError:
    from deep_calibration_sensors import SensorExtension
    from deep_calibration_mesh import DeepCalibrationMesh

VERSION = '0.1.0-beta.8'
REPLY = re.compile(r'command\s+H7\s+ok\.\s*(-?\d+)\s+(-?\d+(?:\.\d+)?)\s*g\b', re.I)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def safe(value):
    """JSON-safe status snapshot, copied before it reaches the writer thread."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe(v) for v in value]
    return str(value)


def parse_reply(response):
    match = REPLY.search(response or '')
    if match is None:
        return None
    raw, grams = int(match.group(1)), float(match.group(2))
    return (raw, grams) if finite(grams) else None


class SignalFilter:
    """Causal median-3 followed by time-aware EMA; not a shaper notch."""
    def __init__(self, tau=.5):
        self.tau = tau
        self.reset()

    def reset(self):
        self.values = collections.deque(maxlen=3)
        self.times = collections.deque(maxlen=40)
        self.last = self.ema = None

    def feed(self, stamp, raw, generation):
        if self.last is not None and (generation != self.generation
                or stamp <= self.last or stamp-self.last > 1.5):
            self.reset()
        self.values.append(raw)
        self.times.append(stamp)
        median = statistics.median(self.values)
        alpha = 1. if self.last is None else -math.expm1(-(stamp-self.last)/self.tau)
        self.ema = median if self.ema is None else self.ema+alpha*(median-self.ema)
        self.last, self.generation = stamp, generation
        span = self.times[-1]-self.times[0]
        rate = (len(self.times)-1)/span if span > 0 else None
        return dict(median_raw=median, filtered_raw=self.ema, rate_hz=rate,
                    nyquist_hz=rate/2 if rate else None,
                    filter='causal_median3_then_ema', filter_tau=self.tau,
                    filter_warmup=len(self.values)<3)


class JsonWriter:
    """Bounded queue; disk I/O is performed only in a background thread."""
    def __init__(self, path, max_bytes=100*1024*1024, queue_size=2048, reserve_bytes=0):
        self.path, self.max_bytes = path, max_bytes
        self.queue = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()
        self.error = None
        self.rows = self.bytes = 0
        self.reserve_bytes=reserve_bytes
        # Open exclusively before starting, so start fails visibly on bad paths.
        self.stream = open(path, 'x', buffering=65536)
        self.thread = threading.Thread(target=self._run, name='deep-calibration-writer', daemon=True)
        self.thread.start()

    def put(self, record):
        if self.error or self.stop_event.is_set():
            return False
        try:
            self.queue.put_nowait(safe(record))
            return True
        except queue.Full:
            self.error = 'writer queue overflow; session incomplete'
            self.stop_event.set()
            return False

    def close(self):
        self.stop_event.set()

    def _run(self):
        try:
            while not self.stop_event.is_set() or not self.queue.empty():
                try:
                    record = self.queue.get(timeout=.2)
                except queue.Empty:
                    self.stream.flush()
                    continue
                line = json.dumps(record, allow_nan=False, separators=(',', ':'))+'\n'
                size = len(line.encode('utf-8'))
                if self.bytes+size > self.max_bytes:
                    self.error = 'file size limit reached; session incomplete'
                    break
                self.stream.write(line)
                self.rows += 1
                self.bytes += size
                if self.rows % 50 == 0:
                    if self.reserve_bytes and shutil.disk_usage(os.path.dirname(self.path)).free<self.reserve_bytes:
                        raise OSError('free storage below configured reserve')
                    self.stream.flush()
        except Exception as exc:
            self.error = 'writer failure: '+str(exc)
        finally:
            self.stop_event.set()
            try:
                self.stream.flush()
                self.stream.close()
            except Exception as exc:
                self.error = 'writer close failure: '+str(exc)


class DeepCalibration:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.directory = config.get('log_directory', '/usr/data/config/mod_data/deep_calibration_data')
        if not os.path.isabs(self.directory):
            raise config.error('deep_calibration: log_directory must be absolute')
        self.interval = config.getfloat('context_interval', .1, minval=.1, maxval=1.)
        self.tau = config.getfloat('filter_tau', .5, minval=.1, maxval=5.)
        if not finite(self.interval) or not finite(self.tau):
            raise config.error('deep_calibration: context_interval and filter_tau must be finite')
        self.cpg = config.getfloat('counts_per_gram', 0.)
        if not finite(self.cpg):
            raise config.error('deep_calibration: counts_per_gram must be finite')
        self.part_fan = config.get('part_fan', 'fan_generic fanM106')
        self.max_bytes = config.getint('max_file_mb', 256, minval=1, maxval=512)*1024*1024
        self.lock = threading.Lock()
        self.pending = collections.deque(maxlen=2048)
        self.history = collections.deque(maxlen=80)
        self.sequence = self.dropped = 0
        self.reader = self.original = self.wrapper = None
        self.source = None
        self.writer = None
        self.active = False
        self.ending = False
        self.started = self.deadline = 0.
        self.recipe = {}
        self.label = 'UNLABELLED'
        self.adjustment_since = None
        self.offset_original = None
        self.auto_adjust_labels = config.getboolean('auto_adjust_labels', True)
        # First print test without console input: DEEP_CALIBRATION_ARM on the
        # start G-code; recording starts with the first layer, and when layer
        # auto_stop_layer starts the offset kept last is labelled GOOD (unless
        # labelled by hand) and recording stops.
        self.auto_capture = config.getboolean('auto_capture', True)
        self.auto_stop_layer = config.getint('auto_stop_layer', 2, minval=2, maxval=100)
        self.armed = None
        self.auto_session = False
        self.manual_since_adjust = False
        self.z_above_since = None
        # Physical timing: Klipper runs ahead of the nozzle by the queued
        # moves. Layer markers and babysteps are placed at the time they
        # take effect, not when the command is read.
        self.first_layer_t = None
        self.stop_at = None
        # Knee search (DEEP_CALIBRATION_KNEE): the only part of Deep
        # Calibration that changes the print. During the first layer it lowers
        # the nozzle in small steps until the load cell shows the steep rise
        # where the nozzle starts pressing the line, then backs off by a margin.
        self.knee_cfg = dict(
            start=config.getfloat('knee_start', .10, minval=0., maxval=.5),
            step=config.getfloat('knee_step', .01, minval=.002, maxval=.05),
            hold=config.getfloat('knee_hold', 6., minval=2., maxval=60.),
            hold_max=config.getfloat('knee_hold_max', 20., minval=2., maxval=120.),
            se=config.getfloat('knee_se_g', 2., minval=.1, maxval=50.),
            rise=config.getfloat('knee_rise_g', 12., minval=1., maxval=500.),
            rise_min=config.getfloat('knee_rise_min_g', 6., minval=1., maxval=500.),
            noise_k=config.getfloat('knee_noise_k', 4., minval=1., maxval=20.),
            margin=config.getfloat('knee_margin', .025, minval=0., maxval=.2),
            max_force=config.getfloat('knee_max_force_g', 80., minval=5., maxval=2000.),
            travel=config.getfloat('knee_max_travel', .35, minval=.02, maxval=1.),
            min_readings=config.getint('knee_min_readings', 8, minval=3, maxval=200),
            confirm=config.getboolean('knee_confirm', True),
            learn_rate=config.getfloat('knee_learn_rate', .5, minval=0., maxval=1.))
        # Learned margins per material and first-layer height
        self.knee_margin_file = os.path.join(self.directory, 'knee_margins.json')
        self.knee_last = None
        self.knee = None
        self.context_id = 0
        self.last_signature = None
        self.last_context = None
        self.baseline = None
        self.signal = SignalFilter(self.tau)
        self.fans = []
        self.settings = {}
        self.seen_printing = False
        self.last_sample = None
        self.sensors = SensorExtension(self, config)
        self.mesh = DeepCalibrationMesh(config)
        self.printer.register_event_handler('klippy:connect', self._connect)
        self.printer.register_event_handler('klippy:ready', self._install_adjustment_observer)
        self.printer.register_event_handler('klippy:shutdown', self._shutdown)
        self.printer.register_event_handler('klippy:disconnect', self._disconnect)
        self.timer = self.reactor.register_timer(self._tick)
        for name in ('START','STOP','STATUS','MARK','SET','ZERO','ARM','DISARM','KNEE','KNEE_ABORT','KNEE_MARGIN'):
            self.gcode.register_command('DEEP_CALIBRATION_'+name, getattr(self, 'cmd_'+name))

    def _install_adjustment_observer(self):
        if not self.auto_adjust_labels or self.offset_original is not None:
            return
        original = self.gcode.register_command('SET_GCODE_OFFSET', None)
        if original is None:
            self.gcode.respond_info('DEEP CALIBRATION: automatic labels unavailable: no SET_GCODE_OFFSET handler')
            return
        self.offset_original = original
        self.gcode.register_command('SET_GCODE_OFFSET', self._offset_observer)

    def _offset_observer(self, gcmd):
        # Observe only user-style relative babysteps. Absolute startup/cleanup
        # offsets (including Auto Trim) must never become training labels.
        before = self._status('gcode_move', self.reactor.monotonic()).get('homing_origin')
        if self.active and gcmd.get('Z_ADJUST', None) is not None:
            try:
                self._flush_force_tail()
            except Exception:
                logging.exception('deep_calibration: adjustment tail flush failed')
        result = self.offset_original(gcmd)  # preserve native command and errors
        after = self._status('gcode_move', self.reactor.monotonic()).get('homing_origin')
        if self.active and gcmd.get('Z_ADJUST', None) is not None:
            try:
                self._label_adjustment(before, after)
            except Exception:
                # An observer must never turn a successful native motion
                # command into an error or execute a second motion.
                logging.exception('deep_calibration: adjustment annotation failed')
        return result

    def _queue_lead(self, now):
        # Seconds of moves queued ahead of the nozzle (0 to 5)
        th = self._status('toolhead', now)
        try:
            lead = float(th.get('print_time')) - float(th.get('estimated_print_time'))
        except (TypeError, ValueError):
            return 0.
        return min(max(lead, 0.), 5.) if finite(lead) else 0.

    def _label_adjustment(self, before, after):
        now = self.reactor.monotonic()
        effect = now + self._queue_lead(now)
        if not before or not after or not finite(before[2]) or not finite(after[2]):
            return
        delta = after[2]-before[2]
        if abs(delta) < 0.000001:
            return
        ps = self._status('print_stats', now)
        at = self._status('gcode_macro AUTO_TRIM', now)
        layer = (ps.get('info') or {}).get('current_layer')
        knee = getattr(self, 'knee', None)
        if knee is not None and knee['phase'] in ('wait', 'down', 'up') and knee.get('own_move'):
            # The knee search's own step: recorded as a search step, not a label
            knee['own_move'] = False
            self.adjustment_since = effect
            return
        if knee is None and getattr(self, 'knee_last', None) is not None and not self.knee_last.get('user_adjusted'):
            self.knee_last['user_adjusted'] = True
        # Commands are read in order: a babystep read after layer 2 was
        # announced changes layer 2 moves, so it belongs to layer 2. Its
        # effect starts when the moves queued before it have printed.
        if ps.get('state') != 'printing' or (layer is not None and layer != 1) or (at and not at.get('prepared')):
            self.adjustment_since = effect
            return
        start = self.adjustment_since if self.adjustment_since is not None else self.started
        label = 'TOO_HIGH' if delta < 0 else 'TOO_LOW'
        self._event('adjustment_label', label=label, start_t=start, end_t=effect,
                    queue_lead=effect-now,
                    from_z=before[2], to_z=after[2], delta_z=delta,
                    inferred=True, source='relative_babystep_direction',
                    applies_to='preceding_interval', physical_settle_time_unknown=True)
        # New setting remains unknown. Explicit manual GOOD/other labels in
        # preceding rows remain authoritative in offline annotation.
        self.label = 'UNLABELLED'
        self.adjustment_since = effect
        self._event('label', label='UNLABELLED', source='after_adjustment', offset=after)
        self.manual_since_adjust = False
        self.gcode.respond_info('DEEP CALIBRATION: Z %.3f was %s (%s, from your babystep); new offset Z %.3f being recorded'
                                % (before[2], 'too high' if label == 'TOO_HIGH' else 'too close',
                                   label, after[2]))

    def _connect(self):
        if self.reader is not None:
            return
        for name, obj in self.printer.lookup_objects():
            if name.startswith('temperature_load') and hasattr(obj, 'extract_last_value_before_g'):
                self.source, self.reader = name, obj
                break
        if self.reader is None:
            logging.warning('deep_calibration: no compatible native AD5X zmod_tenz parser; recording disabled')
            return
        self.original = self.reader.extract_last_value_before_g
        config_status = self.printer.lookup_object('configfile').get_status(self.reactor.monotonic())
        self.settings = safe({name:config_status.get('settings',{}).get(name,{})
                              for name in ('probe','extruder','input_shaper','bed_mesh')})
        def wrapper(response):
            try:
                parsed = parse_reply(response)
                if parsed is not None:
                    stamp = self.reactor.monotonic()
                    with self.lock:
                        self.sequence += 1
                        if len(self.pending) == self.pending.maxlen:
                            self.dropped += 1
                        self.pending.append((self.sequence, stamp, *parsed,
                                             getattr(self.reader, '_command_id', None)))
            except Exception:
                logging.exception('deep_calibration: reply observer failed')
            return self.original(response)
        self.wrapper = wrapper
        self.reader.extract_last_value_before_g = wrapper
        self.fans = [(name, obj) for name, obj in self.printer.lookup_objects()
                     if name == 'fan' or name.startswith(('fan_generic ', 'heater_fan ', 'controller_fan ', 'temperature_fan '))]
        self.reactor.update_timer(self.timer, self.reactor.monotonic())

    def _shutdown(self):
        if self.active:
            self._end('printer_shutdown')

    def _disconnect(self):
        self._shutdown()
        if self.reader is not None and self.reader.extract_last_value_before_g is self.wrapper:
            self.reader.extract_last_value_before_g = self.original
        self.reactor.update_timer(self.timer, self.reactor.NEVER)

    def _status(self, name, now):
        obj = self.printer.lookup_object(name, None)
        return safe(obj.get_status(now)) if obj is not None else {}

    def _motion_at(self, stamp):
        """Read native trap queues at the receipt clock, avoiding status cache.

        Mirrors supplied motion_report.get_status without changing its cache.
        Receipt is still later than the unknown ADC acquisition time.
        """
        report = self.printer.lookup_object('motion_report', None)
        mcu = self.printer.lookup_object('mcu', None)
        th = self.printer.lookup_object('toolhead')
        queues = getattr(report, 'dtrapqs', {})
        if mcu is not None and 'toolhead' in queues and hasattr(th,'get_extra_axes'):
            clock = mcu.estimated_print_time(stamp)
            pos, velocity = queues['toolhead'].get_trapq_position(clock)
            if pos is not None:
                axes = th.get_extra_axes()
                live = [None]*max(4,len(axes))
                live[:3] = pos[:3]
                evelocity = None
                for index, axis in enumerate(axes):
                    if axis is None: continue
                    handler = queues.get(axis.get_name())
                    if handler is None: continue
                    epos, ev = handler.get_trapq_position(clock)
                    if epos is not None:
                        live[index] = epos[0]
                        if index==3: evelocity = ev
                return safe(dict(live_position=live,live_velocity=velocity,
                                 live_extruder_velocity=evelocity, print_time=clock,
                                 sample_time=stamp,method='native_trapq_at_host_receipt',
                                 adc_latency_unknown=True))
        cached = self._status('motion_report',self.reactor.monotonic())
        cached.update(method='cached_status_fallback',sample_time=None,adc_latency_unknown=True)
        return cached

    def _shaper(self):
        obj = self.printer.lookup_object('input_shaper', None)
        values = {}
        for shaper in getattr(obj, 'shapers', ()):
            params = getattr(shaper, 'params', None)
            if params is not None and hasattr(params, 'get_status'):
                values[shaper.get_name()] = safe(params.get_status())
        return values

    def _context(self, now):
        gm = self._status('gcode_move', now)
        th = self.printer.lookup_object('toolhead')
        ts = safe(th.get_status(now))
        motion = self._motion_at(now)
        ps = self._status('print_stats', now)
        settings = self.settings
        position = list(th.get_position())
        data = dict(t=now, id=self.context_id, gcode=gm,
                    toolhead_planned=position, toolhead=ts,
                    motion_requested=motion, print_stats=ps,
                    fans={name:self._status(name, now) for name, obj in self.fans},
                    part_fan=self._status(self.part_fan, now),
                    heaters={name:self._status(name, now) for name in ('extruder','heater_bed')},
                    configured_probe_offset=settings.get('probe', {}).get('z_offset'),
                    shaper=self._shaper(), recipe=dict(self.recipe), label=self.label,
                    native_command_generation=getattr(self.reader, '_command_id', None),
                    cell_age=now-self.last_sample['t'] if self.last_sample else None,
                    auto_trim_cell=self._status('auto_trim_cell', now),
                    probe_status=self._status('probe', now),
                    clock_note='host monotonic receipt/context times; requested motion is software, not an encoder')
        reported = data['probe_status'].get('last_z_result')
        configured = data['configured_probe_offset']
        if finite(reported) and finite(configured):
            data['last_probe_contact_estimate'] = dict(
                z=reported-configured,
                note='last_z_result minus configured probe offset; latest completed probe, not live printing gap')
        bm = self.printer.lookup_object('bed_mesh', None)
        mesh = bm.get_mesh() if bm is not None else None
        if mesh is not None:
            pos = list(bm.last_position)
            factor = bm.get_z_factor(pos[2])
            expected = factor*(mesh.calc_z(pos[0],pos[1])-bm.fade_target)+bm.fade_target
            splitter = getattr(bm, 'splitter', None)
            endpoint = getattr(splitter, 'next_pos', None)
            coherent = (all(abs(position[i]-pos[i]) < 1.e-7 for i in range(2))
                        and not (factor and getattr(splitter,'traverse_complete',True) is False)
                        and not (factor and endpoint is not None and
                                 any(abs(endpoint[i]-pos[i]) > 1.e-7 for i in range(3))))
            root = self.printer.lookup_object('gcode_move').move_transform
            chain = []
            seen = set()
            while root is not None and id(root) not in seen and len(chain)<16:
                seen.add(id(root)); chain.append(type(root).__name__)
                if root is bm: break
                root = getattr(root,'next_transform',None)
            callback = self.printer.lookup_object('gcode_move').move_with_transform
            declared = self.printer.lookup_object('gcode_move').move_transform
            live = motion.get('live_position')
            data['mesh'] = dict(profile=bm.get_status(now).get('profile_name'), input=pos,
                                factor=factor, expected_adjustment=expected,
                                observed_adjustment=position[2]-pos[2],
                                comparable=coherent, chain=chain, in_chain=root is bm,
                                callback_matches=callback==getattr(declared,'move',None),
                                live_xy_interpolation=mesh.calc_z(live[0],live[1]) if live and len(live)>=2 else None)
        data['probe_approach'] = self._status('deep_calibration_approach', now)
        data['z_command_counts'] = {s.get_name():s.get_mcu_position()
                                   for s in th.get_kinematics().get_steppers()
                                   if s.get_name().startswith('stepper_z')}
        return safe(data)

    def _write(self, record):
        if self.writer and not self.writer.put(record):
            self.active = False
            self.gcode.respond_info('DEEP CALIBRATION: recording stopped: '+str(self.writer.error))
            self.writer.close()
            self.sensors.stop()
            return False
        return True

    def _event(self, name, **values):
        return self._write(dict(type='event', event=name, t=self.reactor.monotonic(), **values))

    def _tick(self, now):
        try:
            with self.lock:
                pending = list(self.pending)
                self.pending.clear()
                dropped = self.dropped
            context = self._context(now)
            self.context_id += 1
            self.last_context = context
            signature = safe([context['gcode'].get('homing_origin'),
                              context['gcode'].get('speed_factor'), context['gcode'].get('extrude_factor'),
                              {name:value.get('speed') for name,value in context['fans'].items()},
                              context['shaper'], context['native_command_generation'],
                              context['print_stats'].get('info'), self.recipe])
            if self.active:
                self.sensors.tick(now)
                if self.writer.error:
                    self.active = False
                    self.writer.close()
                    self.sensors.stop()
                    self.gcode.respond_info('DEEP CALIBRATION: '+str(self.writer.error))
                elif dropped != self.session_dropped:
                    self._event('data_loss', dropped=dropped-self.session_dropped)
                    self._end('raw_queue_overflow')
                else:
                    if signature != self.last_signature:
                        self._event('conditions_changed', signature=signature)
                    self._write(dict(type='context', **context))
            self.last_signature = signature
            self._drain_force(pending,now,context)
            if self.active and self.last_sample and now-self.last_sample['t']>1.5:
                raise RuntimeError('native force stream stale for more than 1.5 s')
            state = context['print_stats'].get('state')
            if self.knee is not None:
                try:
                    self._knee_tick(now, context)
                except Exception as exc:
                    logging.exception('deep_calibration: knee search')
                    self._knee_stop(now, context, 'error: '+str(exc), restore=True)
            if self.auto_capture:
                try:
                    self._auto(now, context)
                except Exception as exc:
                    logging.exception('deep_calibration: automatic capture')
                    self.armed = None
                    self.gcode.respond_info('DEEP CALIBRATION: automatic capture stopped: '+str(exc))
            self.seen_printing = self.seen_printing or (self.active and state=='printing')
            if self.active and now>=self.deadline:
                self._end('duration_limit')
            elif self.active and self.seen_printing and state in ('complete','cancelled','error'):
                self._end('print_'+state)
        except Exception as exc:
            logging.exception('deep_calibration: capture error')
            if self.active:
                self._event('capture_error', error=str(exc))
                self._end('capture_error')
                self.gcode.respond_info('DEEP CALIBRATION: capture stopped: '+str(exc))
        return now+self.interval

    def _drain_force(self,pending,now,context):
        for sequence, stamp, raw, grams, generation in pending:
            # Keep raw data exact. Context is taken on the reactor thread
            # and deliberately has a separate timestamp/id and lag field.
            filtered = self.signal.feed(stamp, raw, generation)
            velocity = context['motion_requested'].get('live_velocity')
            ev = context['motion_requested'].get('live_extruder_velocity')
            self.history.append((stamp, raw, generation,
                                 0<=now-stamp<=.35 and finite(velocity) and abs(velocity)<.05
                                 and finite(ev) and abs(ev)<.01 and abs(grams)<=5120))
            k = self.knee
            if k is not None and k['phase'] in ('down', 'up') and stamp >= k['window'][0]:
                mot = self._motion_at(stamp)
                kev = mot.get('live_extruder_velocity'); kv = mot.get('live_velocity')
                if finite(kev) and finite(kv) and kev > .2 and kv > 10 and abs(grams) <= 5120:
                    k['readings'].append(raw)
            self.last_sample = dict(t=stamp, raw=raw, board_grams=grams, sequence=sequence,
                                    native_command_generation=generation, board_overload=abs(grams)>5120, **filtered)
            if self.active and stamp >= self.started:
                baseline_ok = self.baseline is not None and self.baseline['generation'] == generation and abs(grams)<=5120
                delta = filtered['filtered_raw']-self.baseline['raw'] if baseline_ok else None
                shaper_frequencies = [float(v['shaper_freq']) for v in context['shaper'].values()
                                      if v.get('shaper_freq') is not None and float(v['shaper_freq'])>0]
                motion_at_receipt = self._motion_at(stamp)
                live = motion_at_receipt.get('live_position')
                bed = self.printer.lookup_object('bed_mesh',None)
                current_mesh = bed.get_mesh() if bed else None
                interpolation = (current_mesh.calc_z(live[0],live[1])
                                 if current_mesh and live and all(finite(v) for v in live[:2]) else None)
                self._write(dict(type='sample', t=stamp, sequence=sequence, raw=raw, board_grams=grams,
                                 context_id=context['id'], context_t=now, context_lag=now-stamp,
                                 board_overload=abs(grams)>5120,
                                 native_command_generation=generation, baseline_valid=baseline_ok,
                                 baseline_raw=self.baseline['raw'] if baseline_ok else None,
                                 filtered_delta_counts=delta,
                                 filtered_grams=delta/self.cpg if delta is not None and self.cpg else None,
                                 counts_per_gram=self.cpg or None,
                                 motion_at_receipt=motion_at_receipt,
                                 mesh_interpolation_at_receipt=interpolation,
                                 shaper_resolvable=bool(shaper_frequencies and filtered['nyquist_hz']
                                     and max(shaper_frequencies)<.4*(filtered['rate_hz'] or 0)),
                                 **filtered))

    def _flush_force_tail(self):
        if not self.active:return
        with self.lock:
            pending=list(self.pending);self.pending.clear()
        if not pending:return
        now=self.reactor.monotonic()
        context=self._context(now);self.context_id+=1;self.last_context=context
        self._write(dict(type='context',**context))
        self._drain_force(pending,now,context)

    def _recipe(self, gcmd, previous=None):
        data = dict(previous or {})
        for key, default, low, high in (('HEIGHT',.2,.04,1.),('WIDTH',.45,.1,2.),
                                      ('SPEED',40.,1.,600.),('FAN',0.,0.,100.),
                                      ('LAYER',1,1,100000),('FILAMENT',1.75,1.,3.)):
            value = gcmd.get_float(key, data.get(key.lower(),default), minval=low,maxval=high)
            if not finite(value): raise gcmd.error('DEEP CALIBRATION: '+key+' must be finite')
            if key=='LAYER' and value!=int(value): raise gcmd.error('DEEP CALIBRATION: LAYER must be an integer')
            data[key.lower()] = value
        material = str(gcmd.get('MATERIAL',data.get('material','PLA'))).strip()
        if not re.fullmatch(r'[A-Za-z0-9_.+-]{1,48}',material):
            raise gcmd.error('DEEP CALIBRATION: MATERIAL must be a short identifier')
        data['material'] = material
        return data

    def _first_layer_state(self, context):
        ps = context['print_stats']
        layer = (ps.get('info') or {}).get('current_layer')
        layer = int(layer) if isinstance(layer, (int, float)) and layer > 0 else None
        pos = context['gcode'].get('gcode_position') or [0., 0., 99., 0.]
        return ps.get('state'), layer, float(pos[2])

    def _auto(self, now, context):
        state, layer, z = self._first_layer_state(context)
        if self.armed is not None and not self.active:
            if state in ('complete', 'cancelled', 'error') or (state == 'standby' and self.armed['seen']):
                self.armed = None
                self.gcode.respond_info('DEEP CALIBRATION: print ended before its first layer, nothing recorded')
                return
            if state != 'printing':
                return
            self.armed['seen'] = True
            at = self._status('gcode_macro AUTO_TRIM', now)
            if at and not at.get('prepared', True):
                return
            height = self.armed['recipe']['height']
            if layer == 1 or (layer is None and 0. < z <= height + 0.1):
                params = dict(self.armed['params'])
                params.setdefault('RUN', self.armed['recipe']['material'] + '_firstlayer')
                params['LAYER'] = '1'
                line = 'DEEP_CALIBRATION_START ' + ' '.join('%s=%s' % kv for kv in sorted(params.items()))
                self.armed = None
                self.cmd_START(self.gcode.create_gcode_command('DEEP_CALIBRATION_START', line, params))
                self.auto_session = True
                self.manual_since_adjust = False
                self.z_above_since = None
                self.stop_at = None
                # The first layer starts when its first queued move runs
                self.first_layer_t = now + self._queue_lead(now)
                self.adjustment_since = self.first_layer_t
                self._event('first_layer_start', t_physical=self.first_layer_t, queue_lead=self.first_layer_t-now,
                            source='layer_number' if layer == 1 else 'nozzle_height')
            return
        if not (self.active and self.auto_session and (state == 'printing' or self.stop_at is not None)):
            return
        stop_layer = self.auto_stop_layer
        done = False
        if layer is not None:
            done = layer >= stop_layer
        else:
            # No layer numbers: the nozzle stays at the height of layer
            # auto_stop_layer for 3 s (a Z-hop does not)
            if z >= self.recipe['height'] * stop_layer - 0.01:
                if self.z_above_since is None:
                    self.z_above_since = now
                done = now - self.z_above_since >= 3.
            else:
                self.z_above_since = None
        if done and self.stop_at is None:
            # Layer 2 is announced while the end of layer 1 is still queued:
            # keep recording until it has printed
            self.stop_at = now + self._queue_lead(now)
            self._event('first_layer_end', t_physical=self.stop_at, queue_lead=self.stop_at-now,
                        source='layer_number' if layer is not None else 'nozzle_height')
        if self.stop_at is None or now < self.stop_at:
            return
        end = self.stop_at
        offset = (context['gcode'].get('homing_origin') or [0., 0., 0.])[2]
        if not self.manual_since_adjust:
            start = self.adjustment_since if self.adjustment_since is not None else self.started
            if self.first_layer_t is not None:
                start = max(start, self.first_layer_t)
            self._event('adjustment_label', label='GOOD', start_t=start, end_t=end,
                        from_z=offset, to_z=offset, delta_z=0., inferred=True,
                        source='held_through_first_layer', applies_to='preceding_interval',
                        physical_settle_time_unknown=True)
            self.gcode.respond_info('DEEP CALIBRATION: first layer done: Z %.3f, the offset you kept, labelled GOOD'
                                    % offset)
        self._end('first_layer_done')
        self.gcode.respond_info('DEEP CALIBRATION: recording stopped after the first layer; '
                                'the files finish writing in the background (DEEP_CALIBRATION_STATUS)')

    # ------------------------------------------------------------------
    # Knee search
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Knee search helpers
    # ------------------------------------------------------------------
    def _knee_offset(self, context):
        # Read live: a step moved since the last snapshot must not be missed
        live = self._status('gcode_move', self.reactor.monotonic()).get('homing_origin')
        if live:
            return float(live[2])
        return float((context['gcode'].get('homing_origin') or [0., 0., 0.])[2])

    def _knee_move(self, dz):
        dz = round(dz, 4)
        if abs(dz) < 1e-6:
            return
        self.knee['own_move'] = True
        self.gcode.run_script('SET_GCODE_OFFSET Z_ADJUST=%.4f MOVE=1' % dz)

    def _knee_next_window(self, now):
        k = self.knee
        begin = now + self._queue_lead(now) + 1.5
        k['window'] = [begin, begin + k['cfg']['hold_max']]
        k['readings'] = []

    @staticmethod
    def _median(vals):
        v = sorted(vals); n = len(v)
        return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.

    @staticmethod
    def _hinge_fit(points, lo, hi, res=.0005):
        """Fit force = b for z >= zk, b + s*(zk - z) below it (s > 0).
        points: (z, g, weight). Returns (zk, b, s, sse) or None."""
        if len(points) < 3:
            return None
        best = None
        n = int(round((hi - lo) / res))
        for i in range(n + 1):
            zk = lo + i * res
            sw = swx = swy = swxx = swxy = 0.
            for z, g, w in points:
                x = max(0., zk - z)
                sw += w; swx += w * x; swy += w * g; swxx += w * x * x; swxy += w * x * g
            det = sw * swxx - swx * swx
            if det <= 1e-12:
                continue
            slope = (sw * swxy - swx * swy) / det
            if slope <= 0:
                continue
            b = (swy - slope * swx) / sw
            sse = sum(w * (g - b - slope * max(0., zk - z)) ** 2 for z, g, w in points)
            if best is None or sse < best[3] - 1e-12:
                best = (round(zk, 4), b, slope, sse)
        return best

    def _knee_noise(self, flat):
        """Step-to-step noise of the flat steps, robust to slow drift:
        consecutive differences, median absolute value, scaled to a standard
        deviation (1.4826 / sqrt(2))."""
        if len(flat) < 4:
            return None
        diffs = [abs(flat[i] - flat[i - 1]) for i in range(1, len(flat))]
        return 1.4826 * self._median(diffs) / 2 ** .5

    def _knee_key(self):
        r = self.recipe or {}
        return '%s_%.2f' % (str(r.get('material', 'PLA')).lower().replace('-', '_').replace(' ', '_'), float(r.get('height', .2)))

    def _knee_margins(self):
        try:
            with open(self.knee_margin_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def _knee_save_margins(self, data):
        tmp = self.knee_margin_file + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.knee_margin_file)

    # ------------------------------------------------------------------
    # Knee search
    # ------------------------------------------------------------------
    def _knee_begin(self, now, context):
        k = self.knee
        k['original'] = self._knee_offset(context)
        k['offset'] = round(k['original'] + k['cfg']['start'], 4)
        k['floor'] = round(k['offset'] - k['cfg']['travel'], 4)
        k['phase'] = 'down'
        k['steps'] = []
        k['candidate'] = None
        k['key'] = self._knee_key()
        if k.get('margin_fixed') is None:
            m = self._knee_margins().get(k['key'])
            k['margin'] = float(m['margin']) if m else k['cfg']['margin']
            k['margin_src'] = ('learned from %d print%s' % (m['n'], '' if m['n'] == 1 else 's')) if m else 'default'
        else:
            k['margin'] = k['margin_fixed']; k['margin_src'] = 'set on the command'
        self._knee_move(k['cfg']['start'])
        self._knee_next_window(now)
        self._event('knee_start', original=k['original'], start=k['offset'], floor=k['floor'], cfg=k['cfg'],
                    key=k['key'], margin=k['margin'], margin_source=k['margin_src'])
        self.gcode.respond_info('DEEP CALIBRATION: knee search started at Z %.3f (%.3f above Z %.3f), stepping down %.3f mm; margin %.3f (%s)'
                                % (k['offset'], k['cfg']['start'], k['original'], k['cfg']['step'], k['margin'], k['margin_src']))

    def _knee_stop(self, now, context, reason, restore=False, target=None, knee=None, extra=None):
        k = self.knee
        if k is None:
            return
        current = self._knee_offset(context)
        if target is not None:
            self._knee_move(target - current)
        elif restore and k.get('original') is not None:
            self._knee_move(k['original'] - current)
        k['phase'] = 'done'
        result = dict(reason=reason, knee=knee, target=target, original=k.get('original'), steps=k.get('steps', []),
                      key=k.get('key'), margin=k.get('margin'), margin_source=k.get('margin_src'))
        result.update(extra or {})
        self._event('knee_result', **result)
        if target is not None:
            self.knee_last = dict(knee=knee, target=target, margin=k['margin'], key=k['key'],
                                  fixed=k.get('margin_fixed') is not None, user_adjusted=False)
            rep = (extra or {}).get('repeatability')
            self.gcode.respond_info('DEEP CALIBRATION: knee found at Z %.4f%s: the nozzle starts pressing the line there. '
                                    'Offset set to Z %.4f (knee + %.3f, %s); Auto Trim learns it when layer 3 starts.'
                                    % (knee, (' (down %.4f, up %.4f, repeatability %.4f mm)' % (extra['knee_down'], extra['knee_up'], rep)) if rep is not None else '',
                                       target, k['margin'], k['margin_src']))
            if rep is not None and rep > 2 * k['cfg']['step']:
                self.gcode.respond_info('DEEP CALIBRATION: !! the knee going down and going up differ by %.4f mm: this result is less certain. Check the first layer.' % rep)
        else:
            self.gcode.respond_info('DEEP CALIBRATION: knee search stopped (%s)%s' % (
                reason, ', offset back to Z %.3f' % k['original'] if restore and k.get('original') is not None else ''))
        self.knee = None

    def _knee_measure(self, now):
        """The current step's median force in grams once it is precise enough:
        at least HOLD seconds, then until its standard error is within knee_se_g
        or HOLD_MAX is reached. Returns (g, n, se), 'wait', or 'skip'."""
        k = self.knee
        w0 = k['window'][0]
        if now < w0 + k['cfg']['hold']:
            return 'wait'
        vals = k['readings']; n = len(vals)
        cpg = self.cpg or 43.
        if n >= k['cfg']['min_readings']:
            med = self._median(vals)
            sd = statistics.pstdev(vals) / cpg
            se = 1.2533 * sd / n ** .5
            if se <= k['cfg']['se'] or now >= w0 + k['cfg']['hold_max']:
                if k.get('ref') is None:
                    k['ref'] = med
                return ((med - k['ref']) / cpg, n, se)
            return 'wait'
        return 'skip' if now >= w0 + k['cfg']['hold_max'] else 'wait'

    def _knee_tick(self, now, context):
        k = self.knee
        state, layer, z = self._first_layer_state(context)
        if k['phase'] == 'wait':
            if self.active and self.auto_session and self.first_layer_t is not None and now >= self.first_layer_t + 3.:
                self._knee_begin(now, context)
            elif state in ('complete', 'cancelled', 'error'):
                self._knee_stop(now, context, 'print ended before the first layer')
            return
        if k['phase'] not in ('down', 'up'):
            return
        if not self.active:
            return self._knee_stop(now, context, 'recording stopped', restore=True)
        if state != 'printing':
            return self._knee_stop(now, context, 'print not running', restore=True)
        if layer is not None and layer >= 2:
            return self._knee_stop(now, context, 'the first layer ended before a knee was found', restore=True)
        m = self._knee_measure(now)
        if m == 'wait':
            return
        if m == 'skip':
            self._event('knee_step', offset=k['offset'], direction=k['phase'], readings=len(k['readings']), skipped=True)
            return self._knee_advance(now, context)
        g, n, se = m
        flat = [st['g'] for st in k['steps'] if st['direction'] == 'down' and st.get('flat')]
        base = self._median(flat[-3:]) if flat else g
        noise = self._knee_noise(flat)
        rise = max(k['cfg']['rise_min'], k['cfg']['noise_k'] * noise) if noise is not None else k['cfg']['rise']
        k['rise_now'] = rise
        step = dict(offset=k['offset'], direction=k['phase'], g=round(g, 2), se=round(se, 2), base=round(base, 2),
                    rise=round(rise, 2), noise=None if noise is None else round(noise, 2), readings=n)
        k['steps'].append(step)
        if k['phase'] == 'up':
            return self._knee_up_step(now, context, step, base, rise)
        cand = k['candidate']
        if flat and g - base >= k['cfg']['max_force']:
            step['candidate'] = False
            self._event('knee_step', **step)
            knee = cand['offset'] if cand else k['offset']
            return self._knee_stop(now, context, 'force limit', target=round(knee + k['margin'], 4), knee=knee)
        if cand is not None:
            if g >= cand['g'] + rise / 2.:
                step['confirms'] = True
                self._event('knee_step', **step)
                return self._knee_found_down(now, context, cand)
            cand['flat'] = True                  # not confirmed: noise, keep going
            k['candidate'] = None
        if len(flat) >= 2 and g - base >= rise:
            step['candidate'] = True
            k['candidate'] = step
        else:
            step['flat'] = True
        self._event('knee_step', **step)
        self.gcode.respond_info('DEEP CALIBRATION: knee search Z %.3f: %.1f g (recent level %.1f g, rise needed %.1f g, +/-%.1f g, %d readings)'
                                % (k['offset'], g, base, rise, se, n))
        self._knee_advance(now, context)

    def _knee_points(self, steps):
        return [(st['offset'], st['g'], 1. / max(st.get('se') or 1., .5) ** 2) for st in steps]

    def _knee_fit(self, steps, cand_offset):
        k = self.knee; stp = k['cfg']['step']
        # The rise can start up to two steps above the first step that passed
        # the threshold (a gentle rise, or a threshold raised by noise)
        lo = cand_offset - .5 * stp; hi = cand_offset + 2.5 * stp
        fit = self._hinge_fit(self._knee_points(steps), lo, hi)
        return fit

    def _knee_found_down(self, now, context, cand):
        k = self.knee
        down = [st for st in k['steps'] if st['direction'] == 'down']
        fit = self._knee_fit(down, cand['offset'])
        k['knee_threshold'] = cand['offset']
        k['knee_down'] = fit[0] if fit else cand['offset']
        if not k['cfg']['confirm']:
            knee = k['knee_down']
            return self._knee_stop(now, context, 'knee', target=round(knee + k['margin'], 4), knee=knee,
                                   extra=dict(knee_threshold=cand['offset'], knee_down=k['knee_down'], fitted=fit is not None))
        # Confirm from the other side: step back up until the force is flat again
        k['phase'] = 'up'; k['up_flat'] = 0
        self.gcode.respond_info('DEEP CALIBRATION: knee going down at Z %.4f; stepping back up to confirm it' % k['knee_down'])
        k['offset'] = round(k['offset'] + k['cfg']['step'], 4)
        self._knee_move(k['cfg']['step'])
        self._knee_next_window(now)

    def _knee_up_step(self, now, context, step, base, rise):
        k = self.knee
        flat_now = step['g'] - base < rise / 2.
        step['flat'] = flat_now
        self._event('knee_step', **step)
        self.gcode.respond_info('DEEP CALIBRATION: knee check going up Z %.3f: %.1f g (%s)' % (k['offset'], step['g'], 'flat' if flat_now else 'still pressing'))
        k['up_flat'] = k['up_flat'] + 1 if flat_now else 0
        if k['up_flat'] < 2 and k['offset'] < k['knee_threshold'] + 4 * k['cfg']['step']:
            k['offset'] = round(k['offset'] + k['cfg']['step'], 4)
            self._knee_move(k['cfg']['step'])
            self._knee_next_window(now)
            return
        down_flat = [st for st in k['steps'] if st['direction'] == 'down' and st.get('flat')]
        rising_down = [st for st in k['steps'] if st['direction'] == 'down' and not st.get('flat')]
        ups = [st for st in k['steps'] if st['direction'] == 'up']
        # The deepest step, where the search turned, is the start of the way
        # up: with it the upward fit has at least two pressing points
        turn = [min(rising_down, key=lambda st: st['offset'])] if rising_down else []
        fit_up = self._knee_fit(down_flat + turn + ups, k['knee_threshold'])
        knee_up = fit_up[0] if fit_up else None
        fit_all = self._knee_fit(down_flat + rising_down + ups, k['knee_threshold'])
        knee = fit_all[0] if fit_all else k['knee_down']
        rep = round(abs(knee_up - k['knee_down']), 4) if knee_up is not None else None
        return self._knee_stop(now, context, 'knee', target=round(knee + k['margin'], 4), knee=knee,
                               extra=dict(knee_threshold=k['knee_threshold'], knee_down=k['knee_down'],
                                          knee_up=knee_up, repeatability=rep, fitted=fit_all is not None))

    def _knee_advance(self, now, context):
        k = self.knee
        if k['phase'] == 'up':
            k['offset'] = round(k['offset'] + k['cfg']['step'], 4)
            self._knee_move(k['cfg']['step'])
            self._knee_next_window(now)
            return
        nxt = round(k['offset'] - k['cfg']['step'], 4)
        if nxt < k['floor'] - 1e-9:
            return self._knee_stop(now, context, 'no knee within %.2f mm' % k['cfg']['travel'], restore=True)
        k['offset'] = nxt
        self._knee_move(-k['cfg']['step'])
        self._knee_next_window(now)

    def _knee_learn(self):
        """Learn the margin above the knee from the offset kept to the end of
        the first layer, when you babystepped after a knee search."""
        last = self.knee_last
        if last is None or last.get('fixed') or not last.get('user_adjusted'):
            return
        kept = float(self._status('gcode_move', self.reactor.monotonic()).get('homing_origin', [0, 0, 0])[2])
        obs = kept - last['knee']
        data = self._knee_margins()
        old = data.get(last['key'], {'margin': last['margin'], 'n': 0})
        rate = self.knee_cfg['learn_rate']
        new = round(min(max(old['margin'] + rate * (obs - old['margin']), 0.), .2), 4)
        data[last['key']] = {'margin': new, 'n': int(old['n']) + 1, 'last_observed': round(obs, 4)}
        self._knee_save_margins(data)
        self._event('knee_margin_learned', key=last['key'], observed=round(obs, 4), old=old['margin'], new=new, n=data[last['key']]['n'])
        self.gcode.respond_info('DEEP CALIBRATION: knee margin for %s learned: you kept Z %.4f, %.4f above the knee; margin %.4f -> %.4f'
                                % (last['key'].replace('_', ' ').upper(), kept, obs, old['margin'], new))

    cmd_KNEE_help = 'Knee search: lower the nozzle during the first layer until the load cell shows the nozzle pressing, then back off by a margin. ARM=1 waits for the first layer of an armed recording'
    def cmd_KNEE(self, gcmd):
        if self.knee is not None:
            raise gcmd.error('DEEP CALIBRATION: a knee search is already running (DEEP_CALIBRATION_KNEE_ABORT)')
        cfg = dict(self.knee_cfg)
        for key, name in (('start', 'START'), ('step', 'STEP'), ('hold', 'HOLD'), ('hold_max', 'HOLD_MAX'), ('se', 'SE'),
                          ('rise', 'RISE'), ('rise_min', 'RISE_MIN'), ('noise_k', 'NOISE_K'),
                          ('max_force', 'MAX_FORCE'), ('travel', 'TRAVEL')):
            cfg[key] = gcmd.get_float(name, cfg[key], minval=0.)
        cfg['confirm'] = bool(gcmd.get_int('CONFIRM', 1 if cfg['confirm'] else 0))
        margin = gcmd.get('MARGIN', None)
        if not (0 < cfg['step'] <= .05 and cfg['hold'] >= 2 and cfg['hold_max'] >= cfg['hold'] and cfg['travel'] >= cfg['step']):
            raise gcmd.error('DEEP CALIBRATION: STEP 0 to 0.05 mm, HOLD at least 2 s, HOLD_MAX at least HOLD, TRAVEL at least one STEP')
        self.knee = dict(cfg=cfg, phase='wait', own_move=False, readings=[], window=[0., 0.], ref=None,
                         margin_fixed=None if margin is None else float(margin))
        self.knee_last = None
        if gcmd.get_int('ARM', 0):
            if not self.auto_capture:
                self.knee = None
                raise gcmd.error('DEEP CALIBRATION: ARM=1 needs auto_capture and DEEP_CALIBRATION_ARM')
            gcmd.respond_info('DEEP CALIBRATION: knee search armed: it starts 3 s into the first layer of this print')
            return
        now = self.reactor.monotonic(); context = self.last_context or self._context(now)
        state, layer, z = self._first_layer_state(context)
        if not self.active or state != 'printing' or (layer is not None and layer != 1):
            self.knee = None
            raise gcmd.error('DEEP CALIBRATION: the knee search runs during the first layer of a recording (or use ARM=1 on the start G-code)')
        self._knee_begin(now, context)

    cmd_KNEE_ABORT_help = 'Stop a running knee search and put the offset back'
    def cmd_KNEE_ABORT(self, gcmd):
        if self.knee is None:
            gcmd.respond_info('DEEP CALIBRATION: no knee search running'); return
        now = self.reactor.monotonic()
        self._knee_stop(now, self.last_context or self._context(now), 'stopped by you', restore=True)

    cmd_KNEE_MARGIN_help = 'Show the learned knee margins; MATERIAL= HEIGHT= with MARGIN=, ADJUST= or RESET=1 changes one'
    def cmd_KNEE_MARGIN(self, gcmd):
        data = self._knee_margins()
        mat = gcmd.get('MATERIAL', None)
        if mat is None:
            if not data:
                gcmd.respond_info('DEEP CALIBRATION: no learned knee margins yet (default %.3f)' % self.knee_cfg['margin']); return
            lines = ['%s: %.4f (%d print%s)' % (k.replace('_', ' ').upper(), v['margin'], v['n'], '' if v['n'] == 1 else 's') for k, v in sorted(data.items())]
            gcmd.respond_info('DEEP CALIBRATION: knee margins: ' + '; '.join(lines)); return
        key = '%s_%.2f' % (str(mat).lower().replace('-', '_').replace(' ', '_'), gcmd.get_float('HEIGHT', .2, minval=.02, maxval=1.))
        old = data.get(key, {'margin': self.knee_cfg['margin'], 'n': 0})
        if gcmd.get_int('RESET', 0):
            data.pop(key, None); self._knee_save_margins(data)
            gcmd.respond_info('DEEP CALIBRATION: knee margin for %s reset to the default %.3f' % (key.replace('_', ' ').upper(), self.knee_cfg['margin'])); return
        if gcmd.get('MARGIN', None) is not None:
            new = gcmd.get_float('MARGIN', minval=0., maxval=.2)
        elif gcmd.get('ADJUST', None) is not None:
            new = min(max(old['margin'] + gcmd.get_float('ADJUST'), 0.), .2)
        else:
            gcmd.respond_info('DEEP CALIBRATION: knee margin for %s: %.4f (%d print%s)' % (key.replace('_', ' ').upper(), old['margin'], old['n'], '' if old['n'] == 1 else 's')); return
        data[key] = {'margin': round(new, 4), 'n': int(old['n']), 'set_by_hand': True}
        self._knee_save_margins(data)
        gcmd.respond_info('DEEP CALIBRATION: knee margin for %s set to %.4f' % (key.replace('_', ' ').upper(), new))

    def cmd_ARM(self, gcmd):
        if not self.auto_capture:
            raise gcmd.error('DEEP CALIBRATION: auto_capture is off in [deep_calibration]')
        if self.active:
            raise gcmd.error('DEEP CALIBRATION: recording already active')
        recipe = self._recipe(gcmd)
        params = {k: v for k, v in gcmd.get_command_parameters().items()
                  if k in ('RUN', 'MATERIAL', 'HEIGHT', 'WIDTH', 'SPEED', 'FAN', 'FILAMENT', 'ACCEL', 'ADC', 'MAX')}
        params['MATERIAL'] = recipe['material']
        if 'RUN' in params and not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', str(params['RUN'])):
            raise gcmd.error('DEEP CALIBRATION: invalid RUN identifier')
        self.armed = dict(params=params, recipe=recipe, seen=False)
        gcmd.respond_info('DEEP CALIBRATION: armed for this print (%s, first layer %.2f mm): recording starts with '
                          'the first layer, babysteps label the offsets, and it stops when layer %d starts'
                          % (recipe['material'], recipe['height'], self.auto_stop_layer))

    def cmd_DISARM(self, gcmd):
        self.armed = None
        gcmd.respond_info('DEEP CALIBRATION: not armed')

    def cmd_START(self, gcmd):
        if self.active or (self.writer and self.writer.thread.is_alive()):
            raise gcmd.error('DEEP CALIBRATION: recording active or previous writer still finishing')
        calibration = self.printer.lookup_object('gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE',None)
        if calibration is not None and calibration.get_status(self.reactor.monotonic()).get('running',False):
            raise gcmd.error('DEEP CALIBRATION: finish or abort soak calibration before starting capture')
        if self.reader is None:
            raise gcmd.error('DEEP CALIBRATION: native AD5X raw reader not found')
        if self.printer.lookup_object(self.part_fan, None) is None:
            raise gcmd.error('DEEP CALIBRATION: configured part_fan object not found: '+self.part_fan)
        now = self.reactor.monotonic()
        if self.last_sample is None or now-self.last_sample['t']>1.5:
            raise gcmd.error('DEEP CALIBRATION: fresh native load-cell samples unavailable')
        seconds = gcmd.get_float('MAX',3600.,minval=30.,maxval=21600.)
        if not finite(seconds): raise gcmd.error('DEEP CALIBRATION: MAX must be finite')
        run = str(gcmd.get('RUN','capture'))
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',run):
            raise gcmd.error('DEEP CALIBRATION: invalid RUN identifier')
        recipe = self._recipe(gcmd)
        sensor_settings = self.sensors.configure(gcmd)
        try:
            os.makedirs(self.directory, exist_ok=True)
            identity = os.path.join(self.directory, '.printer_id')
            try:
                with open(identity, 'x') as stream:
                    stream.write(uuid.uuid4().hex+'\n')
            except FileExistsError:
                pass
            with open(identity) as stream:
                printer_id = stream.read().strip()
        except OSError as exc:
            raise gcmd.error('DEEP CALIBRATION: cannot access log directory: '+str(exc))
        if not re.fullmatch(r'[a-f0-9]{32}',printer_id):
            raise gcmd.error('DEEP CALIBRATION: invalid data-directory .printer_id; preserve it and repair before recording')
        name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+run+'_'+uuid.uuid4().hex[:8]+'.jsonl'
        try:
            self.writer = JsonWriter(os.path.join(self.directory,name), self.max_bytes,
                                     reserve_bytes=self.sensors.reserve_bytes)
        except OSError as exc:
            raise gcmd.error('DEEP CALIBRATION: cannot open log: '+str(exc))
        self.recipe, self.label = recipe, 'UNLABELLED'
        self.adjustment_since = now
        self.started, self.deadline = now, now+seconds
        self.seen_printing = False
        self.session_dropped = self.dropped
        self.active = True
        self.last_signature = None
        self.signal.reset()
        config = self.settings
        bm = self.printer.lookup_object('bed_mesh',None)
        self._write(dict(type='session',schema=1,version=VERSION,t=now,run=run,
                         printer_id=printer_id,
                         utc=time.time(),recipe=recipe,source=self.source,
                         baseline=self.baseline,counts_per_gram=self.cpg or None,
                         configured_probe=config.get('probe'),
                         bed_mesh=bm.get_status(now) if bm else None,
                         shaper=self._shaper(), filter_tau=self.tau,
                         context_interval=self.interval,
                         sensor_capture=sensor_settings,
                         limitations=['native reply rate limits bandwidth','receipt clock is not ADC clock',
                                      'live motion is requested motion, not encoder feedback',
                                      'queued offset/layer markers may lead physical execution',
                                      'no automatic offset or flow control']))
        try:
            self.sensors.start(self.writer.path[:-6])
        except Exception as exc:
            self._event('sensor_start_error',error=str(exc))
            self._end('sensor_start_error')
            raise gcmd.error('DEEP CALIBRATION: continuous sensor startup failed: '+str(exc))
        gcmd.respond_info('DEEP CALIBRATION: live recording started: '+self.writer.path+
                          '. MARK labels/SET record metadata; they do not move or change printing.')

    def _end(self, reason):
        if not self.active or self.ending:return
        self.ending=True
        try:
            try:self._flush_force_tail()
            except Exception as exc:
                reason='capture_end_error';self._event('capture_error',error=str(exc))
            self.sensors.stop()
            try:self._flush_force_tail()
            except Exception as exc:
                reason='capture_end_error';self._event('capture_error',error=str(exc))
            self.auto_session = False
            self.stop_at = None
            self.first_layer_t = None
            if reason == 'first_layer_done':
                try:
                    self._knee_learn()
                except Exception:
                    logging.exception('deep_calibration: knee margin learning')
            self.knee_last = None
            if self.active:
                self._event('session_end',reason=reason,raw_dropped=self.dropped-self.session_dropped,
                            sensor_capture=self.sensors.status())
                self.active=False
                self.writer.close()
        finally:
            self.ending=False

    def cmd_STOP(self, gcmd):
        self._end('user_stop')
        gcmd.respond_info('DEEP CALIBRATION: stopped; writer drains asynchronously. Use STATUS before downloading.')

    def cmd_MARK(self, gcmd):
        if not self.active: raise gcmd.error('DEEP CALIBRATION: start recording first')
        label = str(gcmd.get('LABEL','UNLABELLED')).upper()
        if label not in ('UNLABELLED','TOO_HIGH','TOO_LOW','GOOD','TRAVEL','TRANSITION'):
            raise gcmd.error('DEEP CALIBRATION: LABEL is UNLABELLED, TOO_HIGH, TOO_LOW, GOOD, TRAVEL or TRANSITION')
        self.label = label
        self.adjustment_since = self.reactor.monotonic()
        self.manual_since_adjust = True
        self._event('label',label=label,note=str(gcmd.get('NOTE',''))[:256],
                    offset=self._status('gcode_move',self.reactor.monotonic()).get('homing_origin'))
        gcmd.respond_info('DEEP CALIBRATION: label='+label+'; allow the queue and force filter to settle before judging it')

    def cmd_SET(self, gcmd):
        if not self.active: raise gcmd.error('DEEP CALIBRATION: start recording first')
        self.recipe = self._recipe(gcmd,self.recipe)
        self._event('recipe',recipe=self.recipe)
        gcmd.respond_info('DEEP CALIBRATION: metadata updated; printer speed/fan/extrusion were not changed')

    def cmd_ZERO(self, gcmd):
        now = self.reactor.monotonic()
        motion = self._status('motion_report',now)
        if (self._status('print_stats',now).get('state') in ('printing','paused')
                or not finite(motion.get('live_velocity')) or abs(motion['live_velocity'])>=.05
                or not finite(motion.get('live_extruder_velocity')) or abs(motion['live_extruder_velocity'])>=.01):
            raise gcmd.error('DEEP CALIBRATION: ZERO requires idle, stationary, non-extruding conditions with nozzle clear')
        samples = [s for s in self.history if now-5.<=s[0]<=now]
        if (len(samples)<10 or now-samples[-1][0]>1.5 or samples[-1][0]-samples[0][0]<2.
                or not all(s[3] for s in samples) or len(set(s[2] for s in samples))!=1):
            raise gcmd.error('DEEP CALIBRATION: need at least ten fresh, quiet samples over two seconds')
        self.baseline = dict(t=now,raw=statistics.median(s[1] for s in samples),
                             generation=samples[-1][2],kind='software_idle_reference_not_board_tare')
        if self.active: self._event('baseline',baseline=self.baseline)
        gcmd.respond_info('DEEP CALIBRATION: software reference recorded; no H1/tare sent. Native special commands invalidate it conservatively.')

    def _auto_status(self):
        return dict(knee=None if self.knee is None else dict(phase=self.knee['phase'], offset=self.knee.get('offset'),
                                                             steps=len(self.knee.get('steps', [])), rise=self.knee.get('rise_now')),
                    armed=self.armed is not None, auto_session=self.auto_session,
                    auto_capture=self.auto_capture, auto_stop_layer=self.auto_stop_layer)

    def get_status(self, eventtime):
        context = self.last_context or {}
        valid = bool(self.last_sample and self.baseline
                     and self.last_sample['native_command_generation']==self.baseline['generation']
                     and eventtime-self.last_sample['t']<=1.5 and not self.last_sample.get('board_overload'))
        delta = self.last_sample['filtered_raw']-self.baseline['raw'] if valid else None
        return dict(self._auto_status(),host_time=eventtime,version=VERSION,recording=self.active,connected=self.reader is not None,
                    source=self.source,last_sample=self.last_sample,
                    probe_approach=self._status('deep_calibration_approach',eventtime),
                    age=eventtime-self.last_sample['t'] if self.last_sample else None,
                    baseline=self.baseline,recipe=self.recipe,label=self.label,
                    auto_adjust_labels=self.auto_adjust_labels, adjustment_observer_installed=self.offset_original is not None,
                    raw_dropped=self.dropped,path=self.writer.path if self.writer else None,
                    writer_alive=self.writer.thread.is_alive() if self.writer else False,
                    writer_error=self.writer.error if self.writer else None,
                    rows_written=self.writer.rows if self.writer else 0,
                    bytes_written=self.writer.bytes if self.writer else 0,
                    sensor_capture=self.sensors.status(),
                    preparation=self.mesh.get_status(eventtime),
                    force_reference_valid=valid,filtered_delta_counts=delta,
                    filtered_grams=delta/self.cpg if delta is not None and self.cpg else None,
                    live_diagnostics=dict(t=context.get('t'),mesh=context.get('mesh'),
                                          requested_motion=context.get('motion_requested'),
                                          global_origin=context.get('gcode',{}).get('homing_origin'),
                                          part_fan=context.get('part_fan'),fans=context.get('fans'),
                                          probe_reference=context.get('configured_probe_offset')),
                    automatic_corrections=False)

    def cmd_STATUS(self, gcmd):
        gcmd.respond_info('DEEP CALIBRATION: '+json.dumps(safe(self.get_status(self.reactor.monotonic())),allow_nan=False))


def load_config(config):
    return DeepCalibration(config)
