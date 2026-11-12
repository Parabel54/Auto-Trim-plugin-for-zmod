# Guarded fast approach for the reviewed Klipper 13 native probe helper.
# GPLv3. Final trigger detection, result creation and sample handling stay native.
import math


class DeepCalibrationApproach:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.fast_speed = config.getfloat('approach_speed', 5., minval=1., maxval=5.)
        self.clearance = config.getfloat('slow_clearance', 1., minval=1., maxval=5.)
        self.max_age = config.getfloat('reference_max_age', 300., minval=1., maxval=600.)
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

    def reset(self, *args):
        self.references.clear()
        self.last_mode = 'reference_cleared'

    def cmd_reset(self, gcmd):
        self.reset()
        gcmd.respond_info('Approach references cleared; next touch uses 1 mm/s throughout.')

    def cmd_status(self, gcmd):
        gcmd.respond_info('DEEP CALIBRATION approach: %s' % self.get_status(self.reactor.monotonic()))

    def get_status(self, eventtime):
        return dict(installed=self.installed, approach_speed=self.fast_speed,
                    contact_speed=1., slow_clearance=self.clearance,
                    reference_max_age=self.max_age, references=len(self.references),
                    fast_moves=self.fast_moves, slow_only=self.slow_only,
                    early_contacts=self.early_contacts, last_mode=self.last_mode)

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
            self.original(command)
            if not is_home:
                measured = list(toolhead.get_position())
                if not all(math.isfinite(v) for v in measured[:3]):
                    raise self.printer.command_error('Non-finite native probe position')
                self.references[(round(measured[0], 3), round(measured[1], 3))] = (
                    self.reactor.monotonic(), measured[2])
        except Exception:
            self.reset()
            raise


def load_config(config):
    return DeepCalibrationApproach(config)
