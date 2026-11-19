# Guarded fast approach for the reviewed Klipper 13 native probe helper.
# GPLv3. Final trigger detection, result creation and sample handling stay native.
#
# Vibration gate (10.2.3): the load cell feels the touch, so shaking from
# outside (another printer on the same table) moves the trigger point. Before
# each touch the toolhead accelerometer measures the shaking; while it is above
# vibration_limit the touch waits (up to vibration_max_wait). The shaking
# during the touch is measured too: a shaken touch is discarded and redone (up
# to vibration_retries, not for homing). Every touch is recorded with its
# vibration levels.
import collections
import math


class DeepCalibrationApproach:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.fast_speed = config.getfloat('approach_speed', 5., minval=1., maxval=5.)
        self.clearance = config.getfloat('slow_clearance', 1., minval=1., maxval=5.)
        self.max_age = config.getfloat('reference_max_age', 300., minval=1., maxval=600.)
        self.vib_gate = config.getboolean('vibration_gate', True)
        self.vib_limit = config.getfloat('vibration_limit', 400., minval=10., maxval=5000.)
        self.vib_window = config.getfloat('vibration_window', .3, minval=.1, maxval=2.)
        self.vib_max_wait = config.getfloat('vibration_max_wait', 10., minval=0., maxval=120.)
        self.vib_retries = config.getint('vibration_retries', 2, minval=0, maxval=5)
        self.accel_name = config.get('accelerometer', 'lis2dw')
        self._vib_init()
        self.references = {}
        self.installed = False
        self.original = None
        self.fast_moves = self.slow_only = self.early_contacts = 0
        self.last_mode = 'not_connected'
        self.printer.register_event_handler('klippy:connect', self._connect)
        for event in ('homing:home_rails_begin', 'homing:home_rails_end',
                      'stepper_enable:motor_off', 'klippy:shutdown', 'klippy:disconnect'):
            self.printer.register_event_handler(event, self.reset)
        self.gcode.register_command('DC_APPROACH_STATUS', self.cmd_status)
        self.gcode.register_command('DC_APPROACH_RESET', self.cmd_reset)

    # ------------------------------------------------------------------
    # Vibration gate
    # ------------------------------------------------------------------
    def _vib_init(self):
        self.vib_samples = collections.deque(maxlen=1600 * 6)
        self.vib_listening = False
        self.vib_last_use = 0.
        self.vib_mode = 'off' if not self.vib_gate else 'not_started'
        self.touches = collections.deque(maxlen=200)
        self.vib_waited = self.vib_redone = self.vib_disturbed = 0
        # Running error/overflow totals of the stream (10.2.5): rows from a
        # batch where either increased are not trusted
        self.vib_counter_base = (0, 0)

    def _vib_helper(self):
        chip = self.printer.lookup_object(self.accel_name, None)
        helper = getattr(chip, 'batch_bulk', None)
        if helper is None or not callable(getattr(helper, 'add_client', None)):
            return None
        return helper

    def _vib_cb(self, msg):
        if not self.vib_listening:
            return False
        totals = (int(msg.get('errors', 0) or 0), int(msg.get('overflows', 0) or 0))
        if self.vib_counter_base is None:
            self.vib_counter_base = totals          # joined a running stream: baseline
        valid = all(t <= b for t, b in zip(totals, self.vib_counter_base)) or totals == self.vib_counter_base
        if any(t < b for t, b in zip(totals, self.vib_counter_base)):
            valid = totals == (0, 0)                # the stream restarted
        self.vib_counter_base = totals
        for row in msg.get('data', ()):
            if len(row) >= 4:
                self.vib_samples.append((row[0], row[1], row[2], row[3], valid))
        if self.reactor.monotonic() - self.vib_last_use > 5.:
            # Let go a few seconds after the last touch
            self.vib_listening = False
            return False
        return True

    def _vib_start(self):
        self.vib_last_use = self.reactor.monotonic()
        helper = self._vib_helper()
        if helper is None:
            self.vib_mode = 'no_accelerometer'
            return False
        clients = getattr(helper, 'client_cbs', None)
        if self.vib_listening and (not isinstance(clients, list) or self._vib_cb in clients):
            return True
        # Not listening, or Klipper dropped our listener (sensor error, stop):
        # attach (again). Joining a stream already running, its first batch
        # is the baseline for the running totals.
        self.vib_samples.clear()
        self.vib_counter_base = None if (isinstance(clients, list) and clients) else (0, 0)
        self.vib_listening = True
        helper.add_client(self._vib_cb)
        self.vib_mode = 'listening'
        return True

    def _print_time(self):
        mcu = self.printer.lookup_object('mcu')
        return mcu.estimated_print_time(self.reactor.monotonic())

    def _vib_rms(self, t0, t1, timeout=2.5):
        # Wait until samples cover t1 (they arrive in batches), then the RMS of
        # each axis' deviation from its own mean, combined: gravity and the
        # board's tilt drop out.
        give_up = self.reactor.monotonic() + timeout + max(0., t1 - self._print_time())
        while (not self.vib_samples or self.vib_samples[-1][0] < t1) and self.reactor.monotonic() < give_up:
            self.vib_last_use = self.reactor.monotonic()     # keep the listener while waiting
            self.reactor.pause(self.reactor.monotonic() + .05)
        self.vib_last_use = self.reactor.monotonic()
        rows = [r for r in self.vib_samples if t0 <= r[0] <= t1]
        # Only a fully covered window of valid, finite samples counts;
        # anything else is unknown, never quiet (10.2.5)
        span = t1 - t0
        if (len(rows) < 8 or not all(len(r) < 5 or r[4] for r in rows)
                or not all(math.isfinite(v) for r in rows for v in r[1:4])
                or rows[0][0] - t0 > .1 * span + .01 or t1 - rows[-1][0] > .1 * span + .01
                or any(b[0] - a[0] > .05 for a, b in zip(rows, rows[1:]))):
            return None
        total = 0.
        for axis in (1, 2, 3):
            vals = [r[axis] for r in rows]
            mean = sum(vals) / len(vals)
            total += sum((v - mean) ** 2 for v in vals) / len(vals)
        return math.sqrt(total)

    def _vib_quiet(self, toolhead, where):
        # Before a touch: measure with the nozzle still; wait while shaken
        toolhead.wait_moves()
        began = self.reactor.monotonic()
        told = False
        while True:
            self.vib_last_use = self.reactor.monotonic()
            t0 = self._print_time()
            level = self._vib_rms(t0, t0 + self.vib_window)
            if level is not None and level <= self.vib_limit:
                return level, self.reactor.monotonic() - began
            if self.reactor.monotonic() - began >= self.vib_max_wait:
                return level, self.reactor.monotonic() - began
            if level is None:
                continue                    # no usable data yet: measure again
            if not told:
                told = True
                self.vib_waited += 1
                self.gcode.respond_info(
                    'DEEP CALIBRATION: shaking %.0f mm/s2 before the touch at %s (limit %.0f), waiting for it to settle'
                    % (level, where, self.vib_limit))

    def _record_touch(self, info):
        self.touches.append(info)
        dc = self.printer.lookup_object('deep_calibration', None)
        if dc is not None and getattr(dc, 'active', False) and callable(getattr(dc, '_event', None)):
            try:
                dc._event('probe_touch', **info)
            except Exception:
                pass

    def reset(self, *args):
        self.references.clear()
        self.last_mode = 'reference_cleared'

    def cmd_reset(self, gcmd):
        self.reset()
        gcmd.respond_info('Approach references cleared; next touch uses 1 mm/s throughout.')

    def cmd_status(self, gcmd):
        gcmd.respond_info('DEEP CALIBRATION approach: %s' % self.get_status(self.reactor.monotonic()))

    def get_status(self, eventtime):
        touches = getattr(self, 'touches', ())
        last = touches[-1] if touches else None
        return dict(installed=self.installed, approach_speed=self.fast_speed,
                    contact_speed=1., slow_clearance=self.clearance,
                    reference_max_age=self.max_age, references=len(self.references),
                    fast_moves=self.fast_moves, slow_only=self.slow_only,
                    early_contacts=self.early_contacts, last_mode=self.last_mode,
                    vibration_gate=getattr(self, 'vib_gate', False),
                    vibration_limit=getattr(self, 'vib_limit', None),
                    vibration_mode=getattr(self, 'vib_mode', 'off'), touches_recorded=len(touches),
                    touches_waited=getattr(self, 'vib_waited', 0), touches_redone=getattr(self, 'vib_redone', 0),
                    touches_disturbed=getattr(self, 'vib_disturbed', 0), last_touch=last)

    def _connect(self):
        probe = self.printer.lookup_object('probe')
        wrapper = getattr(probe, 'mcu_probe', None)
        helper = getattr(wrapper, 'homing_helper', None)
        homing = self.printer.lookup_object('homing')
        if (helper is None or not callable(getattr(helper, 'descend_until_trigger', None))
                or not callable(getattr(homing, 'manual_home', None))
                or not hasattr(helper, 'mcu_probe')
                or not hasattr(getattr(probe, 'param_helper', None), 'speed')):
            raise self.printer.config_error(
                'deep_calibration_approach requires the reviewed Klipper 13 '
                'native probe DescendToEndstopHelper; no hook installed')
        if self.installed:
            return
        self.helper = helper
        self.original = helper.descend_until_trigger
        helper.descend_until_trigger = self.descend
        # Covers defaults reported by PROBE/mesh/accuracy helpers as well.
        probe.param_helper.speed = 1.
        self.installed = True
        self.last_mode = 'ready_no_reference'

    def _command_at_one(self, gcmd):
        params = dict(gcmd.get_command_parameters())
        params['PROBE_SPEED'] = '1'
        return self.gcode.create_gcode_command(
            gcmd.get_command(), gcmd.get_commandline(), params)

    def _reference(self, pos, now):
        self.references = {k: v for k, v in self.references.items()
                           if 0. <= now-v[0] <= self.max_age}
        if not self.references:
            return None
        # Use highest recent native trigger Z at all positions. This keeps the
        # slow boundary above every observed surface, including a higher corner.
        return max(v[1] for v in self.references.values())

    def descend(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        homing = self.printer.lookup_object('homing')
        command = self._command_at_one(gcmd)
        now = self.reactor.monotonic()
        pos = list(toolhead.get_position())
        is_home = gcmd.get_command().upper().startswith('G28')
        if is_home:
            # Native Z-via-probe homing does not emit home_rails_begin/end.
            # It rebases Z after each touch, so no prior reference survives.
            self.reset()
        try:
            homed = toolhead.get_status(now)['homed_axes']
            reference = None if is_home or 'z' not in homed else self._reference(pos, now)
            target = None if reference is None else reference+self.clearance
            if target is not None and math.isfinite(target) and pos[2]-target > 0.05:
                endstop = self.helper.mcu_probe
                if endstop.query_endstop(toolhead.get_last_move_time()):
                    raise self.printer.command_error('Probe already triggered before fast approach')
                goal = list(pos)
                goal[2] = target
                # Native monitored move; not a blind G1 toward the bed.
                reached = homing.manual_home(
                    toolhead, [(endstop, 'probe')], goal, self.fast_speed,
                    probe_pos=True, triggered=True, check_triggered=False)
                self.fast_moves += 1
                if (abs(reached[2]-target) > 0.01
                        or endstop.query_endstop(toolhead.get_last_move_time())):
                    self.early_contacts += 1
                    raise self.printer.command_error(
                        'Probe triggered during fast approach; measurement rejected. '
                        'Reference cleared; inspect bed/nozzle before retrying.')
                self.last_mode = 'guarded_fast_then_slow'
            else:
                self.slow_only += 1
                self.last_mode = 'homing_slow' if is_home else 'slow_only'
            # Original native function owns the actual measured trigger and
            # sample result. Only its speed parameter is changed to 1 mm/s.
            self._touch(command, toolhead, pos, is_home)
            if not is_home:
                measured = list(toolhead.get_position())
                if not all(math.isfinite(v) for v in measured[:3]):
                    raise self.printer.command_error('Non-finite native probe position')
                self.references[(round(measured[0], 3), round(measured[1], 3))] = (
                    self.reactor.monotonic(), measured[2])
        except Exception:
            self.reset()
            raise


    def _touch(self, command, toolhead, pos, is_home):
        gate = getattr(self, 'vib_gate', False) and self._vib_start()
        if not gate:
            self.original(command)
            return
        where = 'X%.1f Y%.1f' % (pos[0], pos[1])
        start_z = toolhead.get_position()[2]
        results = getattr(self.helper, 'results', None)
        attempts = 1 if is_home else self.vib_retries + 1
        for attempt in range(attempts):
            before, waited = self._vib_quiet(toolhead, where)
            t0 = self._print_time()
            count = len(results) if isinstance(results, list) else None
            self.original(command)
            t1 = toolhead.get_last_move_time()
            self.vib_last_use = self.reactor.monotonic()
            during = self._vib_rms(t0, t1)
            shaken = during is not None and during > self.vib_limit
            unknown = before is None or during is None
            quality = 'shaken' if shaken or (before is not None and before > self.vib_limit) else ('unknown' if unknown else 'quiet')
            info = dict(x=round(pos[0], 3), y=round(pos[1], 3), homing=is_home, quality=quality,
                        z=round(toolhead.get_position()[2], 5),
                        vibration_before=None if before is None else round(before, 1),
                        vibration_during=None if during is None else round(during, 1),
                        waited_s=round(waited, 1), attempt=attempt + 1,
                        limit=self.vib_limit, shaken=shaken)
            last = attempt == attempts - 1
            if shaken and not last and count is not None and len(results) == count + 1:
                # Discard this shaken result, go back up and touch again
                results.pop()
                info['redone'] = True
                self._record_touch(info)
                self.vib_redone += 1
                self.gcode.respond_info(
                    'DEEP CALIBRATION: touch at %s shaken during the touch (%.0f mm/s2, limit %.0f), redoing it (%d of %d)'
                    % (where, during, self.vib_limit, attempt + 1, attempts - 1))
                goal = list(toolhead.get_position())
                goal[2] = start_z
                toolhead.manual_move(goal, self.fast_speed)
                continue
            if quality != 'quiet':
                # shaken, or no usable vibration data: never a clean touch
                info['disturbed'] = True
                self.vib_disturbed += 1
                self.gcode.respond_info(
                    'DEEP CALIBRATION: touch at %s measured ' % where
                    + ('without usable vibration data' if quality == 'unknown' else 'while shaken')
                    + ' (before %s, during %s mm/s2, limit %.0f); kept and marked'
                    % ('-' if before is None else '%.0f' % before,
                       '-' if during is None else '%.0f' % during, self.vib_limit))
            self._record_touch(info)
            return


def load_config(config):
    return DeepCalibrationApproach(config)
