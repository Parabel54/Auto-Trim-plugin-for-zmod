# Deep Calibration integrated mesh diagnostics and AD5X preparation routing.
# Adapted from the reviewed Live Z Mesh Compensation development source.
# GPLv3, like the Klipper code whose public objects are inspected here.
import collections
import math
import statistics


def transform_path(root, mesh, toolhead):
    """Follow the next_transform chain used by Klipper skew/exclude wrappers."""
    seen, names = set(), []
    while root is not None and id(root) not in seen and len(names) < 16:
        seen.add(id(root))
        names.append(type(root).__name__)
        if root is mesh:
            return True, names
        if root is toolhead:
            return False, names
        root = getattr(root, 'next_transform', None)
    return None, names  # Unknown third-party wrapper is not proof of bypass.



class SoakTimeLimit(Exception):
    pass


def evaluate_soak_points(rows,npts,interval,window,min_rounds,stable,drift_limit):
    """Independent point windows; invalid touches never erase another point."""
    end=rows[-1][0];cutoff=end-window
    ordered=all(math.isfinite(row[0]) for row in rows) and all(
        rows[i][0]>rows[i-1][0] for i in range(1,len(rows)))
    result=[]
    for j in range(1,npts+1):
        valid=[(row[0],row[j]) for row in rows if row[j] is not None
               and isinstance(row[j],(int,float)) and math.isfinite(row[j])]
        anchors=[i for i,row in enumerate(valid) if row[0]<=cutoff]
        chosen=valid[anchors[-1]:] if anchors else valid
        status=dict(valid=False,count=len(chosen),span=0.,range=None,slope=None,reason='insufficient_coverage')
        if chosen:
            times=[row[0] for row in chosen];zs=[row[1] for row in chosen]
            status['span']=times[-1]-times[0];status['range']=max(zs)-min(zs)
            mt=statistics.mean(times);mz=statistics.mean(zs)
            den=sum((t-mt)**2 for t in times)
            slope=sum((t-mt)*(z-mz) for t,z in chosen)/den*60 if den else None
            status['slope']=slope
            gaps=[times[i]-times[i-1] for i in range(1,len(times))]
            covered=(ordered and bool(anchors) and len(chosen)>=min_rounds
                     and end-times[0]>=window-1.e-6
                     and cutoff-times[0]<=2*interval+1.e-6
                     and times[-1]==end and rows[-1][j] is not None
                     and gaps and min(gaps)>0 and max(gaps)<=2*interval+1.e-6)
            status['valid']=bool(covered and status['range']<=stable+1.e-7
                                 and slope is not None and abs(slope)<=drift_limit)
            status['reason']=('stable' if status['valid'] else
                              'current_touch_rejected' if rows[-1][j] is None else
                              'range_or_trend' if covered else 'insufficient_coverage')
        result.append(status)
    return result


class DeepCalibrationMesh:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.startup_integration = config.getboolean('startup_integration', True)
        self.startup_installed = False
        self.travel_running = False
        if self.startup_integration:
            self.printer.register_event_handler('klippy:ready', self._install_startup)
        self.tolerance = config.getfloat('tolerance', .005, above=0.)
        self.samples = collections.deque(maxlen=512)
        self.until = None
        self.interval = .5
        self.timer = self.reactor.register_timer(self._tick)
        for command in ('DEEP_CALIBRATION_MESH_STATUS', 'DEEP_CALIBRATION_MESH_TRACE',
                        'DEEP_CALIBRATION_MESH_TRACE_STOP', 'DEEP_CALIBRATION_MESH_REQUIRE',
                        'DEEP_CALIBRATION_MESH_TRAVEL_TEST'):
            self.gcode.register_command(command, getattr(self, 'cmd_' + command))
        self.gcode.register_command('_DEEP_CALIBRATION_SOAK_PROBE',self.cmd_soak_probe)
        self.gcode.register_command('_DEEP_CALIBRATION_SOAK_EVALUATE',self.cmd_soak_evaluate)

    def cmd_soak_probe(self,gcmd):
        """Use native bounded repeatability checks, with calibration cleanup."""
        macro=self.printer.lookup_object('gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE',None)
        c=macro.get_status(self.reactor.monotonic()) if macro else {}
        if not c.get('running'):
            raise gcmd.error('DEEP CALIBRATION: no active soak calibration')
        self.gcode.run_script_from_command('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=point_valid VALUE=False\nSET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=point_measured VALUE=False')
        try:
            if self.printer.lookup_object('print_stats').get_status(self.reactor.monotonic())['state'] in ('printing','paused'):
                raise ValueError('calibration interrupted by a print')
            def thermal_check():
                state=self._soak_thermal_state(c)
                self.gcode.run_script_from_command('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=thermal_status VALUE="%s"' % state)
                return state
            before=thermal_check()
            if not before['collect']:
                self.gcode.run_script_from_command('RESPOND PREFIX="info" MSG="DEEP CALIBRATION: temperature settling; bed %.2f C, target %.2f C, current band +/-%.2f C; nozzle %.2f C / %.2f C. Keeping targets; this point will be checked again."' % (before['bed'],c['bed'],before['band'],before['nozzle'],c['nozzle']))
                return
            samples=int(c['samples']);repeat=float(c['repeat']);retries=int(c['retries'])
            if samples<2 or samples>15 or not math.isfinite(repeat) or not 0<repeat<=.1 or not 0<=retries<=10:
                raise ValueError('invalid repeatability parameters')
            try:
                self.gcode.run_script_from_command('LOAD_CELL_TARE')
                point_z=self._measure_soak_point(samples,repeat,retries,float(c['probe_speed']),float(c['second_probe_speed']))
            except Exception as exc:
                # Only the native, bounded sample-spread failure is recoverable.
                # The direct native session is closed in finally, without
                # emitting a recoverable G-code fault through the UI dispatcher.
                # Never swallow homing, communication, heater or other faults.
                if str(exc).strip() != 'Probe samples exceed samples_tolerance':
                    raise
                thermal_check()
                self.gcode.run_script_from_command(
                    'RESPOND PREFIX="info" MSG="DEEP CALIBRATION: probe spread exceeded REPEAT; '
                    'this round cannot count as stable. Continuing until settled or MAX."')
                return
            after=thermal_check()
            if not math.isfinite(point_z):raise ValueError('non-finite probe position')
            self.gcode.run_script_from_command('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=point_z VALUE=%.9f' % point_z)
            self.gcode.run_script_from_command('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=point_measured VALUE=True')
            eligible=before['eligible'] and after['eligible']
            self.gcode.run_script_from_command('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=point_valid VALUE=%s' % eligible)
            if not eligible:
                self.gcode.run_script_from_command('RESPOND PREFIX="info" MSG="DEEP CALIBRATION: warm-up measurement recorded; outside final temperature band, excluded from stability. Continuing."')
        except SoakTimeLimit:
            state=self.printer.lookup_object('print_stats').get_status(self.reactor.monotonic())['state']
            lines=['SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=running VALUE=False',
                   'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=last_good VALUE=False',
                   'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=confirm_count VALUE=0',
                   'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=last_result VALUE=\'"TIMEOUT_OR_UNVERIFIED"\'',
                   'UPDATE_DELAYED_GCODE ID=_DEEP_CALIBRATION_SOAK_TICK DURATION=0']
            if state not in ('printing','paused'):lines+=['M140 S0','M104 S0']
            lines.append('RESPOND PREFIX="info" MSG="DEEP CALIBRATION: MAX reached; calibration not accepted, previous saved result preserved."')
            self.gcode.run_script_from_command('\n'.join(lines))
        except Exception as exc:
            state=self.printer.lookup_object('print_stats').get_status(self.reactor.monotonic())['state']
            cleanup=('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=running VALUE=False\n'
                     'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=last_result VALUE=\'"MEASUREMENT_FAILED"\'\n'
                     'UPDATE_DELAYED_GCODE ID=_DEEP_CALIBRATION_SOAK_TICK DURATION=0')
            # Do not turn off a newly started print's heaters. Idle calibration
            # failures otherwise shut both calibration heaters down.
            if state not in ('printing','paused'):cleanup+='\nM140 S0\nM104 S0'
            self.gcode.run_script_from_command(cleanup)
            raise gcmd.error('DEEP CALIBRATION: measurement rejected; nothing saved: '+str(exc))

    def _soak_thermal_state(self,c):
        now=self.reactor.monotonic();elapsed=now-float(c['t0'])
        if elapsed>float(c['max']):raise SoakTimeLimit('MAX measurement time reached')
        initial=float(c['bed_band_start']);final=float(c['bed_band_final']);grace=float(c['temp_grace'])
        if (not all(math.isfinite(v) for v in (initial,final,grace))
                or not .1<=final<=3 or not final<=initial<=10 or not 0<=grace<=1800):
            raise ValueError('invalid thermal guard parameters')
        fraction=max(0.,min(1.,1.-max(0.,elapsed)/grace)) if grace else 0.
        band=final+(initial-final)*fraction
        statuses={}
        for name,target in (('heater_bed',float(c['bed'])),('extruder',float(c['nozzle']))):
            status=self.printer.lookup_object(name).get_status(now)
            current=float(status['temperature']);actual_target=float(status['target'])
            if not all(math.isfinite(v) for v in (current,actual_target)):
                raise ValueError(name+' has an invalid temperature reading')
            if abs(actual_target-target)>.05:
                raise ValueError('%s target changed: %.2f C, expected %.2f C' % (name,actual_target,target))
            statuses[name]=current
        bed=statuses['heater_bed'];nozzle=statuses['extruder']
        return dict(elapsed=elapsed,band=band,bed=bed,nozzle=nozzle,
                    collect=abs(bed-float(c['bed']))<=band+1.e-7 and abs(nozzle-float(c['nozzle']))<=2.+1.e-7,
                    eligible=abs(bed-float(c['bed']))<=final+1.e-7 and abs(nozzle-float(c['nozzle']))<=2.+1.e-7,
                    phase='warming' if grace and elapsed<grace else 'final_band')

    def cmd_soak_evaluate(self,gcmd):
        c=self.printer.lookup_object('gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE').get_status(self.reactor.monotonic())
        if not c['running']:return
        t=gcmd.get_float('T')
        if len(c['cur'])!=int(c['npts']):raise gcmd.error('incomplete probing round')
        rows=c['rows']+[[round(t,6)]+list(c['cur'])]
        raw_cur=c.get('raw_cur',[])
        if len(raw_cur)!=int(c['npts']):raw_cur=c['cur']
        raw_rows=c.get('raw_rows',[])+[[round(t,6)]+list(raw_cur)]
        states=evaluate_soak_points(rows,int(c['npts']),float(c['interval']),float(c['window']),
                                    int(c['min_rounds']),float(c['stable']),float(c['drift_limit']))
        good=(float(c['min_soak'])<=t<=float(c['max']) and all(p['valid'] for p in states))
        passes=int(c['confirm_count'])+1 if good else 0
        lines=['SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=raw_rows VALUE="%s"' % raw_rows,
               'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=rows VALUE="%s"' % rows,
               'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=point_status VALUE="%s"' % states,
               'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=confirm_count VALUE=%d' % passes,
               'SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=last_good VALUE=%s' % good]
        if None in c['cur']:
            lines.append('SET_GCODE_VARIABLE MACRO=DEEP_CALIBRATION_SOAK_CALIBRATE VARIABLE=rejected_rounds VALUE="%s"' % (c['rejected_rounds']+[rows[-1]]))
        lines.append('RESPOND PREFIX="info" MSG="DEEP CALIBRATION: %d s; stable locations %d/%d; valid counts %s; point ranges %s; confirmations %d/%d. Good readings retained independently."' %
                     (t,sum(p['valid'] for p in states),c['npts'],[p['count'] for p in states],
                      [None if p['range'] is None else round(p['range'],6) for p in states],passes,c['confirm']))
        if good and passes>=int(c['confirm']):
            lines.append('_DEEP_CALIBRATION_SOAK_FINISH SETTLED=1 ELAPSED=%s' % t)
        elif t>=float(c['max']):
            lines.append('_DEEP_CALIBRATION_SOAK_FINISH SETTLED=0 ELAPSED=%s' % t)
        elif int(gcmd.get('TEST_ONLY',0))==0:
            delay=max(1.,float(c['round_started'])+float(c['interval'])-self.reactor.monotonic())
            lines.append('UPDATE_DELAYED_GCODE ID=_DEEP_CALIBRATION_SOAK_TICK DURATION=%s' % delay)
        self.gcode.run_script_from_command('\n'.join(lines))

    def _measure_soak_point(self,samples,repeat,retries,first_speed=1.,second_speed=1.):
        """Native single touches; both measuring touches default to 1 mm/s."""
        if not all(math.isfinite(v) and 0<v<=10 for v in (first_speed,second_speed)):
            raise ValueError('probe speeds must be finite and in (0,10] mm/s')
        probe=self.printer.lookup_object('probe')
        toolhead=self.printer.lookup_object('toolhead')
        for attempt in range(retries+1):
            touches=[];retract=None
            for i in range(samples):
                speed=first_speed if i==0 else second_speed
                params={'SAMPLES':'1','SAMPLES_RESULT':'median',
                        'PROBE_SPEED':str(speed),'SAMPLES_TOLERANCE_RETRIES':'0'}
                command=self.gcode.create_gcode_command('PROBE','PROBE',params)
                native=probe.get_probe_params(command)
                def retract():
                    pos=list(toolhead.get_position()[:3])
                    pos[2]+=native['sample_retract_dist']
                    toolhead.manual_move(pos,native['lift_speed'])
                session=probe.start_probe_session(command)
                try:
                    session.run_probe(command)
                    z=float(session.pull_probed_results()[0].bed_z)
                    if not math.isfinite(z):raise ValueError('non-finite probe position')
                    touches.append(z)
                finally:
                    session.end_probe_session()
                if i+1<samples:retract()
            if max(touches)-min(touches)<=repeat+1.e-7:
                return statistics.median(touches)
            if attempt<retries:retract()
        raise ValueError('Probe samples exceed samples_tolerance')

    def get_status(self, eventtime):
        return {'tracing': self.until is not None, 'samples': len(self.samples),
                'diagnostics_read_only': True, 'version': '0.1.0-beta.7',
                'travel_test_running': self.travel_running,
                'last_sample': self.samples[-1] if self.samples else None,
                'startup_installed': self.startup_installed}

    def _install_startup(self):
        # Existing START_PRINT and pre-clean are themselves macros. Defining
        # their sections again with rename_existing would erase their original
        # definitions during config merging, so preserve the registered handlers.
        if self.startup_installed:
            return
        if (self.printer.lookup_object('live_z_mesh', None) is not None
                or self.printer.lookup_object('gcode_macro LIVE_Z_MESH_PREPARE', None) is not None
                or self.printer.lookup_object('gcode_macro AUTO_TRIM_PREPARE', None) is not None):
            raise self.printer.config_error('DEEP CALIBRATION: remove the older startup includes before enabling integrated preparation')
        routes = [('START_PRINT', '_DEEP_CALIBRATION_BASE_START_PRINT',
                   'gcode_macro DEEP_CALIBRATION_START_PRINT'),
                  ('_PRINT_CLEAR_NOZZLE', '_DEEP_CALIBRATION_BASE_PRECLEAN',
                   'gcode_macro _DEEP_CALIBRATION_PRECLEAN')]
        commands = self.gcode.get_status(self.reactor.monotonic())['commands']
        targets = []
        for original, saved, target in routes:
            macro = self.printer.lookup_object(target, None)
            if original not in commands or saved in commands or macro is None:
                raise self.printer.config_error(
                    'DEEP CALIBRATION: missing startup macro or conflicting saved handler: '
                    + original)
            targets.append(macro.cmd)
        for (original, saved, target), callback in zip(routes, targets):
            previous = self.gcode.register_command(original, None)
            self.gcode.register_command(saved, previous)
            self.gcode.register_command(original, callback)
        self.startup_installed = True

    def snapshot(self, eventtime):
        gm = self.printer.lookup_object('gcode_move')
        th = self.printer.lookup_object('toolhead')
        bm = self.printer.lookup_object('bed_mesh', None)
        gstatus = gm.get_status(eventtime)
        actual = list(th.get_position())
        result = {'time': eventtime, 'profile': None, 'chain': [],
                  'in_chain': None, 'planned_z': actual[2],
                  'nominal_z': gstatus['gcode_position'][2],
                  'offset': gstatus['homing_origin'][2],
                  'input_z': None, 'expected': None, 'observed': None,
                  'error': None, 'factor': None, 'live_z': None, 'steps': {},
                  'mesh_id': None, 'callback_matches': None,
                  'comparable': True, 'sample_note': None}
        motion = self.printer.lookup_object('motion_report', None)
        if motion is not None:
            position = motion.get_status(eventtime).get('live_position')
            if position is not None and len(position) >= 3:
                result['live_z'] = position[2]
        for stepper in th.get_kinematics().get_steppers():
            if stepper.get_name().startswith('stepper_z'):
                # Klipper derives these from commanded position, not encoders.
                result['steps'][stepper.get_name()] = stepper.get_mcu_position()
        if bm is None:
            return result
        result['in_chain'], result['chain'] = transform_path(
            gm.move_transform, bm, th)
        callback = getattr(gm, 'move_with_transform', None)
        expected_callback = getattr(gm.move_transform, 'move', None)
        if callback is not None and expected_callback is not None:
            result['callback_matches'] = callback == expected_callback
        mesh = bm.get_mesh()
        if mesh is None:
            return result
        pos = list(bm.last_position)  # non-transformed planned mesh input
        factor = bm.get_z_factor(pos[2])
        # Toolhead.move may yield to reactor timers while BedMesh.move is
        # submitting split segments. BedMesh updates last_position only after
        # all segments return, so comparing it to an intermediate output is
        # invalid. Do not call get_position on the transform to 'repair' this:
        # it mutates last_position and algebraically inverts the very formula
        # this diagnostic is supposed to test independently.
        splitter = getattr(bm, 'splitter', None)
        splitting = factor and getattr(splitter, 'traverse_complete', True) is False
        endpoint = getattr(splitter, 'next_pos', None)
        pending_endpoint = factor and endpoint is not None and any(
            abs(endpoint[i] - pos[i]) > 1.e-7 for i in range(3))
        xy_mismatch = any(abs(actual[i] - pos[i]) > 1.e-7 for i in range(2))
        if splitting or pending_endpoint or xy_mismatch:
            result['comparable'] = False
            result['sample_note'] = 'input/output endpoints differ or split submission is in progress'
        result['output_xy'] = actual[:2]
        correction = factor * (mesh.calc_z(pos[0], pos[1]) - bm.fade_target)
        correction += bm.fade_target
        observed = actual[2] - pos[2]
        result.update(profile=mesh.get_profile_name(), xy=pos[:2], mesh_id=id(mesh),
                      input_z=pos[2], factor=factor, expected=correction,
                      observed=observed, error=observed-correction,
                      fade_start=bm.fade_start, fade_end=bm.fade_end)
        return result

    def _describe(self, s):
        self.gcode.respond_info(
            'DEEP CALIBRATION: profile=%s, transform_path=%s, mesh_in_path=%s, '
            'gcode_callback_matches_root=%s'
            % (s['profile'], ' -> '.join(s['chain']), s['in_chain'],
               s['callback_matches']))
        self.gcode.respond_info(
            'DEEP CALIBRATION: nominal layer Z=%.6f, global offset=%.6f, '
            'planned output Z=%.6f, live requested Z=%s'
            % (s['nominal_z'], s['offset'], s['planned_z'], s['live_z']))
        if s['expected'] is not None:
            self.gcode.respond_info(
                'DEEP CALIBRATION: XY=%s, mesh input Z=%.6f, fade factor=%.4f, '
                'expected adjustment=%+.6f, observed planned adjustment=%+.6f, '
                'difference=%+.6f mm' % (s['xy'], s['input_z'], s['factor'],
                                       s['expected'], s['observed'], s['error']))
            if not s.get('comparable', True):
                self.gcode.respond_info(
                    'DEEP CALIBRATION: sample NOT COMPARABLE: %s; output XY=%s. '
                    'Difference excluded from the correction verdict.'
                    % (s['sample_note'], s['output_xy']))
        self.gcode.respond_info(
            'DEEP CALIBRATION: commanded Z-step counts=%s. '
            'These and live requested Z are software commands, not bed encoders.'
            % s['steps'])

    def cmd_DEEP_CALIBRATION_MESH_STATUS(self, gcmd):
        self._describe(self.snapshot(self.reactor.monotonic()))

    def cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(self, gcmd):
        """Explicit idle-only A-B-A motion test through the normal G1 path."""
        fail = lambda message: gcmd.error('DEEP CALIBRATION: ' + message)
        if self.travel_running or self.until is not None:
            raise fail('stop the trace/test before starting a travel test')
        stats = self.printer.lookup_object('print_stats')
        if stats.get_status(self.reactor.monotonic())['state'] in ('printing', 'paused'):
            raise fail('travel test is idle-only; finish/cancel the print first')
        for name in ('DEEP_CALIBRATION_SOAK_CALIBRATE', 'AUTO_TRIM_SOAK_CALIBRATE'):
            macro = self.printer.lookup_object('gcode_macro ' + name, None)
            if macro and macro.get_status(self.reactor.monotonic()).get('running', False):
                raise fail('finish or abort soak calibration first')
        th = self.printer.lookup_object('toolhead')
        ts = th.get_status(self.reactor.monotonic())
        if not all(axis in ts['homed_axes'] for axis in 'xyz'):
            raise fail('home XYZ normally before the test; the test does not home')
        gm = self.printer.lookup_object('gcode_move')
        bm = self.printer.lookup_object('bed_mesh', None)
        if bm is None or bm.get_mesh() is None:
            raise fail('load or generate a mesh before the test')
        mesh = bm.get_mesh()
        root = gm.move_transform
        # No assumptions about unknown downstream transforms or active skew:
        # selected mesh XY must equal toolhead XY for independent comparison.
        if root is not bm:
            if (type(root).__name__ != 'PrinterSkew'
                    or getattr(root, 'next_transform', None) is not bm
                    or any(getattr(root, key, None) != 0. for key in
                           ('xy_factor', 'xz_factor', 'yz_factor'))):
                raise fail('travel test requires BedMesh directly, or zero-skew PrinterSkew -> BedMesh')
        if getattr(gm, 'move_with_transform', None) != root.move:
            raise fail('G-code motion callback does not match the transform root')
        height = gcmd.get_float('HEIGHT', 10., minval=5., maxval=30.)
        speed = gcmd.get_float('SPEED', 30., minval=1., maxval=60.)
        if not all(math.isfinite(v) for v in (height, speed, gm.speed_factor)) or gm.speed_factor <= 0:
            raise fail('height, speed and speed factor must be finite and valid')
        factor = bm.get_z_factor(height)
        if not math.isfinite(factor) or abs(factor - 1.) > 1.e-7:
            raise fail('full mesh correction must be active at test HEIGHT; current fade prevents this test')
        params = mesh.get_mesh_params()
        lower, upper = ts['axis_minimum'], ts['axis_maximum']
        xlo, xhi = max(params['min_x'], lower[0]) + 10., min(params['max_x'], upper[0]) - 10.
        ylo, yhi = max(params['min_y'], lower[1]) + 10., min(params['max_y'], upper[1]) - 10.
        if not all(math.isfinite(v) for v in (xlo, xhi, ylo, yhi)) or xhi <= xlo or yhi <= ylo:
            raise fail('mesh/axis intersection is too small for the 10 mm test margin')
        supplied = [gcmd.get(key, None) for key in ('X1', 'Y1', 'X2', 'Y2')]
        if any(v is not None for v in supplied):
            if any(v is None for v in supplied):
                raise fail('supply all of X1 Y1 X2 Y2, or omit all for automatic points')
            coordinates = [gcmd.get_float(key) for key in ('X1', 'Y1', 'X2', 'Y2')]
            points = [coordinates[:2], coordinates[2:]]
        else:
            grid = [(xlo+(xhi-xlo)*i/8., ylo+(yhi-ylo)*j/8.)
                    for i in range(9) for j in range(9)]
            values = [(mesh.calc_z(x, y), (x, y)) for x, y in grid]
            if not all(math.isfinite(value) for value, xy in values):
                raise fail('mesh contains non-finite corrections')
            points = [min(values)[1], max(values)[1]]
        if any(not all(math.isfinite(v) for v in xy)
               or not xlo <= xy[0] <= xhi or not ylo <= xy[1] <= yhi for xy in points):
            raise fail('test points must be inside the mesh/axis bounds with a 10 mm margin')
        if math.dist(points[0], points[1]) < 1.:
            raise fail('test points must be at least 1 mm apart')
        base = list(gm.base_position)
        if not all(math.isfinite(v) for v in base[:3]):
            raise fail('G-code base position must be finite')
        steppers = [s for s in th.get_kinematics().get_steppers()
                    if s.get_name().startswith('stepper_z')]
        distances = {s.get_name(): s.get_step_dist() for s in steppers}
        if not distances or any(not math.isfinite(v) or v <= 0. for v in distances.values()):
            raise fail('Z step distances are unavailable or invalid')
        mesh_range = mesh.get_z_range()
        if (not all(math.isfinite(z) for z in mesh_range)
                or height+min(mesh_range) < max(lower[2], 2.)
                or height+max(mesh_range) > upper[2]):
            raise fail('mesh-wide predicted Z is outside the 2 mm clearance / axis limits')
        # Validate both predicted endpoints before any move. Native G1 checks
        # every submitted segment against kinematic limits as usual.
        for x, y in points + [list(th.get_position()[:2])]:
            z = height + mesh.calc_z(x, y)
            if not math.isfinite(z) or not max(lower[2], 2.) <= z <= upper[2]:
                raise fail('predicted test Z is outside the 2 mm clearance / axis limits')
        correction = [mesh.calc_z(*xy) for xy in points]
        gcmd.respond_info('DEEP CALIBRATION: explicit A-B-A travel test; mesh-input Z=%.3f mm, '
                          'A=(%.3f,%.3f), B=(%.3f,%.3f), predicted A->B Z change=%+.6f mm. '
                          'No extrusion; bed must be clear. Software counts are not encoders.'
                          % (height, *points[0], *points[1], correction[1]-correction[0]))
        if abs(correction[1]-correction[0]) < .01:
            gcmd.respond_info('DEEP CALIBRATION: selected route has less than 0.01 mm endpoint variation; '
                              'small movement is expected, and this route cannot strongly test compensation')
        state_name = '_DEEP_CALIBRATION_TRAVEL_STATE'
        self.travel_running = True
        saved = False
        records = []
        try:
            th.wait_moves()
            self.gcode.run_script_from_command('SAVE_GCODE_STATE NAME=' + state_name)
            saved = True
            # Use ordinary G1, including its real transform callback. HEIGHT is
            # mesh-input Z; subtract base offsets to express it in G-code space.
            self.gcode.run_script_from_command('G90\nG1 Z%.9f F%.9f' %
                                               (height-base[2], 5./gm.speed_factor))
            th.wait_moves()
            for label, xy in (('A', points[0]), ('B', points[1]), ('A-return', points[0])):
                if bm.get_mesh() is not mesh or list(gm.base_position) != base:
                    raise fail('mesh or base offset changed during the test; result invalid')
                self.gcode.run_script_from_command('G1 X%.9f Y%.9f F%.9f' %
                                                   (xy[0]-base[0], xy[1]-base[1], speed/gm.speed_factor))
                th.wait_moves()
                sample = self.snapshot(self.reactor.monotonic())
                if (not sample['comparable'] or sample['in_chain'] is not True
                        or sample['callback_matches'] is not True
                        or sample['mesh_id'] != id(mesh)
                        or abs(sample['input_z']-height) > 1.e-6
                        or math.dist(sample['xy'], xy) > 1.e-6
                        or math.dist(sample['output_xy'], xy) > 1.e-6):
                    raise fail('completed endpoint could not be independently aligned; result invalid')
                if not all(math.isfinite(sample[key]) for key in ('planned_z', 'expected', 'error')):
                    raise fail('non-finite endpoint data; result invalid')
                records.append(sample)
                gcmd.respond_info('DEEP CALIBRATION: %s mesh XY=(%.3f,%.3f), predicted Z=%.6f, '
                                  'planned Z=%.6f, error=%+.6f mm, commanded Z counts=%s'
                                  % (label, *xy, height+mesh.calc_z(*xy), sample['planned_z'],
                                     sample['error'], sample['steps']))
                if abs(sample['error']) > self.tolerance:
                    raise fail('planned endpoint does NOT MATCH the mesh; stopped at ' + label)
            for i, label in ((1, 'A->B'), (2, 'B->A')):
                previous, current = records[i-1], records[i]
                expected = current['expected']-previous['expected']
                planned = current['planned_z']-previous['planned_z']
                gcmd.respond_info('DEEP CALIBRATION: %s predicted delta=%+.6f mm, planned delta=%+.6f mm'
                                  % (label, expected, planned))
                for name, distance in distances.items():
                    delta = current['steps'][name]-previous['steps'][name]
                    commanded = delta*distance
                    # MCU position counts are commanded steps; allow endpoint
                    # rounding by one step at each end, not a free mismatch.
                    error = commanded-expected
                    gcmd.respond_info('DEEP CALIBRATION: %s %s commanded delta=%+d steps (%+.6f mm), '
                                      'difference=%+.6f mm' % (label, name, delta, commanded, error))
                    if abs(planned-expected) > self.tolerance or abs(error) > 2.*distance + 1.e-6:
                        raise fail('commanded Z travel does NOT MATCH the predicted delta')
            gcmd.respond_info('DEEP CALIBRATION: A-B-A mesh endpoint and commanded-step comparison PASSED. '
                              'Physical bed travel is not measured; test ends at A at the test height.')
        finally:
            self.travel_running = False
            if saved:
                # Restore modes, feed and offsets without returning through the
                # old XY/Z or extruding. Retain the actual final test position.
                self.gcode.run_script_from_command('RESTORE_GCODE_STATE NAME=' + state_name + ' MOVE=0')

    def cmd_DEEP_CALIBRATION_MESH_REQUIRE(self, gcmd):
        """Fail startup if the standard compensation path is unavailable."""
        sample = self.snapshot(self.reactor.monotonic())
        bm = self.printer.lookup_object('bed_mesh', None)
        if sample['expected'] is None:
            raise gcmd.error('DEEP CALIBRATION: preparation did not leave an active mesh')
        if sample['in_chain'] is not True or sample['callback_matches'] is not True:
            raise gcmd.error('DEEP CALIBRATION: mesh motion path is bypassed or unknown')
        gm = self.printer.lookup_object('gcode_move')
        first_layer_input = .2 + getattr(gm, 'base_position', [0., 0., 0.])[2]
        if bm.get_z_factor(first_layer_input) <= 0.:
            raise gcmd.error('DEEP CALIBRATION: compensation is faded out at first-layer Z')
        gcmd.respond_info('DEEP CALIBRATION: active mesh and standard G-code transform '
                          'path found; dynamic and physical verification still required')

    def cmd_DEEP_CALIBRATION_MESH_TRACE(self, gcmd):
        seconds = gcmd.get_float('SECONDS', 20., minval=1., maxval=120.)
        self.interval = gcmd.get_float('INTERVAL', .5, minval=.25, maxval=5.)
        if not all(math.isfinite(v) for v in (seconds, self.interval)):
            raise gcmd.error('Trace duration and interval must be finite')
        self.samples.clear()
        now = self.reactor.monotonic()
        self.until = now + seconds
        self.reactor.update_timer(self.timer, now)
        gcmd.respond_info('DEEP CALIBRATION: read-only trace started for %.1f s. '
                          'Continue the normal first layer; no diagnostic moves '
                          'or configuration changes will be issued.' % seconds)

    def _tick(self, eventtime):
        if self.until is None:
            return self.reactor.NEVER
        try:
            self.samples.append(self.snapshot(eventtime))
        except Exception as error:
            self.until = None
            self.gcode.respond_info('DEEP CALIBRATION: trace unavailable: %s' % error)
            return self.reactor.NEVER
        if eventtime >= self.until:
            self.until = None
            self._finish()
            return self.reactor.NEVER
        return eventtime + self.interval

    def cmd_DEEP_CALIBRATION_MESH_TRACE_STOP(self, gcmd):
        self.until = None
        self.reactor.update_timer(self.timer, self.reactor.NEVER)
        self._finish()

    def _finish(self):
        if not self.samples:
            self.gcode.respond_info('DEEP CALIBRATION: no trace samples')
            return
        self._describe(self.samples[-1])
        applicable = [s for s in self.samples if s['expected'] is not None]
        comparable = [s for s in applicable if s.get('comparable', True)]
        skipped = len(applicable) - len(comparable)
        if skipped:
            self.gcode.respond_info(
                'DEEP CALIBRATION: excluded %d/%d samples with unaligned endpoints; '
                '%d comparable samples remain' % (skipped, len(applicable), len(comparable)))
        if not applicable:
            verdict = 'NO ACTIVE MESH observed'
        elif len(applicable) != len(self.samples):
            verdict = 'mesh became active or inactive during trace; repeat with stable setup'
        elif len(set(s['mesh_id'] for s in applicable)) > 1:
            verdict = 'active mesh changed during trace; repeat with stable setup'
        elif any(s['in_chain'] is False for s in applicable):
            verdict = 'mesh is loaded but BYPASSED in the known transform path'
        elif any(s['callback_matches'] is False for s in applicable):
            verdict = 'G-code motion callback does NOT MATCH the declared transform root'
        elif any(s['callback_matches'] is None for s in applicable):
            verdict = 'G-code motion callback could not be verified'
        elif any(s['in_chain'] is None for s in applicable):
            verdict = 'transform path contains an unknown wrapper; not verified'
        elif all(s['factor'] == 0 for s in applicable):
            verdict = 'mesh shape compensation FADED OUT at sampled Z'
        elif not comparable:
            verdict = 'no comparable endpoints captured; correction not verified, repeat trace'
        elif not all(math.isfinite(s[k]) for s in comparable for k in
                     ('input_z', 'expected', 'observed', 'error', 'factor')):
            verdict = 'non-finite mesh or position data; not verified'
        elif max(abs(s['error']) for s in comparable) > self.tolerance:
            verdict = 'mesh output does NOT MATCH the expected planned correction'
        else:
            # Compare only groups with the same mesh input Z. A layer change or
            # babystep is not evidence of mesh compensation.
            groups = collections.defaultdict(list)
            for s in comparable:
                groups[round(s['input_z'] / self.tolerance)].append(s)
            candidates = [g for g in groups.values() if len(g) >= 3 and
                          len(set((round(s['xy'][0], 1), round(s['xy'][1], 1))
                                  for s in g)) >= 3]
            varied = [g for g in candidates if
                      max(s['expected'] for s in g) -
                      min(s['expected'] for s in g) >= .01]
            if varied:
                best = max(varied, key=len)
                expected_range = max(s['expected'] for s in best) - min(
                    s['expected'] for s in best)
                planned_range = max(s['observed'] for s in best) - min(
                    s['observed'] for s in best)
                self.gcode.respond_info(
                    'DEEP CALIBRATION: at stable mesh input Z, expected adjustment '
                    'range=%.6f mm, observed planned range=%.6f mm'
                    % (expected_range, planned_range))
                verdict = 'varying mesh correction VERIFIED in the planned Z path'
            else:
                verdict = 'mesh output matches, but insufficient fixed-Z XY variation to prove dynamic compensation'
        live = [s['live_z'] for s in self.samples if s['live_z'] is not None]
        self.gcode.respond_info('DEEP CALIBRATION: %s (%d snapshots)' %
                               (verdict, len(self.samples)))
        if live:
            self.gcode.respond_info('DEEP CALIBRATION: live requested Z range '
                                   '%.6f..%.6f mm' % (min(live), max(live)))
        counts = collections.defaultdict(list)
        for s in self.samples:
            for name, value in s['steps'].items():
                counts[name].append(value)
        self.gcode.respond_info('DEEP CALIBRATION: commanded step-count ranges %s. '
                               'Physical bed movement still requires observation.'
                               % {name: (min(v), max(v)) for name, v in counts.items()})


