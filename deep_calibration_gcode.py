"""Read-only Orca provenance and queue-timed first-layer segment attribution.

GPL-3.0-only. No G-code is executed by the parser. A separate file handle and
worker thread are used; virtual_sdcard's cursor is never read or changed here.
"""
import collections
import gc
import hashlib
import itertools
import json
import logging
import math
import os
import re
import threading
import time
import xml.etree.ElementTree as ET


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def file_stat(path):
    stat = os.stat(path)
    return [stat.st_size, stat.st_mtime_ns, stat.st_ino]


def project_sidecar(path, file_hash):
    name = path + '.dc.json'
    if not os.path.exists(name):
        return None, None
    if os.path.getsize(name) > 8 * 1024 * 1024:
        raise ValueError('project snapshot exceeds 8 MiB bound')
    before = file_stat(name)
    with open(name) as stream:
        data = json.load(stream, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite snapshot')))
    if (data.get('schema') != 1 or data.get('gcode_sha256') != file_hash
            or not isinstance(data.get('settings_parts'), dict)):
        raise ValueError('project snapshot is invalid or bound to another G-code file')
    if data.get('settings_sha256') != digest(data['settings_parts']):
        raise ValueError('project settings snapshot hash mismatch')
    if not all(isinstance(k, str) and isinstance(v, str) for k,v in data['settings_parts'].items()):
        raise ValueError('project settings parts must be strings')
    if data.get('physics_sha256') != project_physics(data['settings_parts']):
        raise ValueError('project physics snapshot hash mismatch')
    if before != file_stat(name): raise ValueError('project snapshot changed during scan')
    return data, before


PROVENANCE_ONLY = frozenset(('output_filename_format', 'notes', 'print_settings_id',
                            'printer_settings_id',
                            'compatible_printers',
                            'compatible_prints', 'inherits', 'version'))
ALLOWED_ROLES = frozenset(('outer wall', 'inner wall', 'external perimeter',
                          'perimeter', 'internal solid infill', 'solid infill',
                          'bottom surface'))
PARAM = re.compile(r'([A-Za-z])\s*([-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?)')
ASSIGN = re.compile(r'^([A-Za-z_][\w]*)\s*=\s*(.*)$')
NUMERIC_VECTORS = frozenset(('nozzle_diameter', 'filament_diameter', 'filament_flow_ratio'))


def setting_values(settings, key):
    value = settings.get(key, '')
    # ConfigOptionFloats uses commas; ConfigOptionStrings uses semicolons.
    # Accept the old numeric-semicolon spelling without changing raw metadata.
    return re.split('[,;]', value) if key in NUMERIC_VECTORS else value.split(';')


def serialized_strings(value):
    """Orca ConfigOptionStrings: semicolon delimiter, quoted/escaped values."""
    values, current, quoted, escape = [], [], False, False
    for char in value:
        if escape:
            current.append({'n':'\n','r':'\r','t':'\t'}.get(char,char)); escape=False
        elif char == '\\': escape=True
        elif char == '"': quoted=not quoted
        elif char == ';' and not quoted:
            values.append(''.join(current));current=[]
        else: current.append(char)
    if escape or quoted: raise ValueError('incomplete serialized string vector')
    values.append(''.join(current))
    return values


def filament_profile_scan(settings, registry, used=None, scope='gcode', origins=None, unresolved=None):
    """Inventory actual exported/preset values; never supply definition defaults."""
    def vector(key, value, kind):
        if isinstance(value,list):return value
        if not isinstance(value,str):return [value]
        if kind == 'coString':return [value]
        if kind == 'coStrings':return serialized_strings(value)
        return re.split('[,;]',value)
    types=serialized_strings(settings.get('filament_type','')) if scope=='gcode' else settings.get('filament_type',[])
    if not isinstance(types,list):types=[types]
    index = (used[0] if used and len(used)==1 else 0 if scope=='preset' or len(types)==1 else None)
    profile=settings.get('filament_settings_id',settings.get('name'))
    if isinstance(profile,str) and scope=='gcode':profile=serialized_strings(profile)
    if scope=='gcode' and not used and isinstance(profile,list) and len(profile)>1:
        index=None
    if isinstance(profile,list):profile=profile[index] if index is not None and index<len(profile) else profile
    rows=[]
    for definition in registry['settings']:
        key=definition['key'];row={k:v for k,v in definition.items() if k!='definition_default_reference'}
        row.update(raw=settings.get(key),selected_value=None,origin=(origins or {}).get(key,scope) if key in settings else 'unknown_not_supplied',status='missing_unknown')
        if key in settings:
            value=settings[key]
            try:
                values=vector(key,value,definition['type'])
                if len(values)==1:
                    row.update(selected_value=values[0],status='present')
                elif definition['variant_scoped']:
                    row['status']='present_variant_mapping_unknown'
                elif index is not None and index<len(values):
                    row.update(selected_value=values[index],status='present')
                else:row['status']='present_active_filament_unknown'
                if row['selected_value'] is None or row['selected_value']=='nil':
                    if value is None or row['status']=='present':
                        row['status']='explicit_nil_override' if definition['nullable'] else 'present_null_unknown'
            except (ValueError,TypeError):row['status']='present_serialization_unresolved'
        rows.append(row)
    known={r['key'] for r in rows}
    extras={k:v for k,v in settings.items() if k.startswith('filament_') and k not in known}
    return dict(schema=1,slicer_commit=registry['commit'],scope=scope,profile=profile,used_filament_index=index,
                counts=dict(catalog=len(rows),present=sum(r['status']!='missing_unknown' for r in rows),
                            missing=sum(r['status']=='missing_unknown' for r in rows),
                            hidden_or_conditional=sum(bool(r['hidden_categories']) for r in rows)),
                unresolved_parents=unresolved or [],settings=rows,additional_filament_metadata=extras,
                note='Raw and selected values are exported/preset metadata, not proof of active firmware settings; missing and variant mappings are not defaulted.')


def project_physics(parts):
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in PROVENANCE_ONLY}
        if isinstance(value, list): return [clean(v) for v in value]
        return value
    normalized = {}
    for name, text in parts.items():
        try:
            normalized[name] = clean(json.loads(text))
        except ValueError:
            try:
                root = ET.fromstring(text)
                for parent in root.iter():
                    for node in list(parent):
                        if node.tag == 'metadata' and node.get('key') in PROVENANCE_ONLY.union(('name', 'source_file')):
                            parent.remove(node)
                normalized[name] = ET.tostring(root, encoding='unicode')
            except ET.ParseError:
                normalized[name] = text
    return digest(normalized)


def parse_file(path, cancel=None):
    """Bounded streaming parse, including Orca's config footer and exact bytes.

    Settings stay serialized (percentages, lists, units, and disabled options
    are not guessed). Geometry tags describe emitted paths, not defaults.
    """
    initial = os.stat(path)
    if initial.st_size > 512 * 1024 * 1024:
        raise ValueError('G-code exceeds 512 MiB scan bound')
    settings, segments, issues = {}, {}, []
    variants, plate_values = {}, {}
    hasher = hashlib.sha256()
    offset = config_bytes = 0
    in_config = False
    complete = False
    slicer = None
    used_filaments = None
    layer = 0
    role = height = width = obj = None
    tool = 0
    pos = dict(X=None, Y=None, Z=None, E=0.)
    absolute, eabsolute, metric = True, True, True
    feed = None
    with open(path, 'rb') as stream:
        while True:
            if cancel is not None and cancel.is_set():
                raise ValueError('scan cancelled')
            raw = stream.readline(262145)
            if not raw:
                break
            if len(raw) > 262144:
                raise ValueError('G-code line exceeds scan bound')
            hasher.update(raw)
            text = raw.decode('utf-8', errors='strict').strip()
            start, offset = offset, offset + len(raw)
            if offset > 512 * 1024 * 1024:
                raise ValueError('G-code grew beyond 512 MiB scan bound')
            if 'generated by OrcaSlicer' in text:
                slicer = text.lstrip('; ').strip()
            if text.startswith(';'):
                comment = text[1:].strip()
                if comment in ('CONFIG_BLOCK_START', 'config = begin'):
                    in_config = True
                    complete = False
                    continue
                if comment in ('CONFIG_BLOCK_END', 'config = end'):
                    complete = in_config
                    in_config = False
                    continue
                if in_config:
                    match = ASSIGN.match(comment)
                    if match:
                        key, value = match.groups()
                        config_bytes += len(raw)
                        if config_bytes > 4 * 1024 * 1024 or len(settings) >= 8192:
                            raise ValueError('settings exceed scan bound')
                        variants.setdefault(key, []).append(value)
                        if key in settings and settings[key] != value:
                            # Pinned Orca append_full_config emits these twice:
                            # the selected plate coordinate, then its full array.
                            # Preserve both; unrelated conflicts still fail.
                            plate_duplicate = False
                            if key in ('wipe_tower_x', 'wipe_tower_y') and len(variants[key]) == 2:
                                try:
                                    selected = float(settings[key])
                                    values = [float(v) for v in value.split(',')]
                                    plate_duplicate = finite(selected) and all(finite(v) for v in values)
                                    if plate_duplicate: plate_values[key] = selected
                                except ValueError:
                                    pass
                            if not plate_duplicate: issues.append('conflicting_setting:' + key)
                        settings[key] = value
                    continue
                if comment == 'LAYER_CHANGE':
                    layer += 1
                    role = height = width = obj = None
                elif comment.startswith('filament:'):
                    try:
                        used_filaments = [int(v.strip()) - 1 for v in comment.split(':', 1)[1].split(',')]
                        if len(used_filaments) == 1 and used_filaments[0] >= 0:
                            tool = used_filaments[0]
                    except ValueError:
                        issues.append('invalid_used_filament_header')
                elif comment.lower().startswith('layer num/total_layer_count:'):
                    try:
                        layer = int(comment.split(':', 1)[1].split('/')[0])
                    except ValueError:
                        issues.append('invalid_layer_marker')
                elif comment.startswith(('FEATURE:', 'TYPE:')):
                    role = comment.split(':', 1)[1].strip().lower()
                elif comment.startswith(('HEIGHT:', 'LAYER_HEIGHT:')):
                    try:
                        height = float(comment.split(':', 1)[1])
                        if not finite(height): height = None
                    except ValueError:
                        height = None
                elif comment.startswith(('WIDTH:', 'LINE_WIDTH:')):
                    try:
                        width = float(comment.split(':', 1)[1])
                        if not finite(width): width = None
                    except ValueError:
                        width = None
                continue
            code_text = text.split(';', 1)[0].strip()
            if not code_text:
                continue
            if layer >= 2:
                continue  # Hash the whole file; only index its first layer.
            code = code_text.split()[0].upper()
            args = {k.upper(): float(v) for k, v in PARAM.findall(code_text[len(code):])}
            if not all(finite(v) for v in args.values()):
                raise ValueError('nonfinite G-code parameter')
            if code == 'G90': absolute = True
            elif code == 'G91': absolute = False
            elif code == 'M82': eabsolute = True
            elif code == 'M83': eabsolute = False
            elif code == 'G20': metric = False
            elif code == 'G21': metric = True
            elif code == 'G92':
                for axis in pos:
                    if axis in args: pos[axis] = args[axis]
            elif code == 'G28':
                # Unknown homing macros/offsets are never reconstructed.
                for axis in 'XYZ': pos[axis] = None
            elif code.startswith('T') and code[1:].isdigit():
                tool = int(code[1:])
                pos['E'] = None
            elif code == 'EXCLUDE_OBJECT_START':
                match = re.search(r'\bNAME=(\S+)', code_text)
                obj = match.group(1) if match else None
            elif code == 'EXCLUDE_OBJECT_END': obj = None
            elif code in ('G0', 'G1', 'G2', 'G3'):
                before = dict(pos)
                for axis in pos:
                    if axis not in args: continue
                    is_abs = (absolute and eabsolute) if axis == 'E' else absolute
                    pos[axis] = args[axis] if is_abs else (
                        pos[axis] + args[axis] if pos[axis] is not None else None)
                if 'F' in args: feed = args['F'] / 60.
                if layer != 1: continue
                if len(segments) >= 100000:
                    raise ValueError('first-layer command index exceeds scan bound')
                de = (args.get('E', 0.) if not (absolute and eabsolute) else
                      pos['E'] - before['E'] if pos['E'] is not None and before['E'] is not None else None)
                xy = (math.hypot(pos['X'] - before['X'], pos['Y'] - before['Y'])
                      if all(finite(v) for v in (pos['X'], pos['Y'], before['X'], before['Y'])) else None)
                dz = (pos['Z'] - before['Z'] if finite(pos['Z']) and finite(before['Z']) else None)
                reasons = []
                if not metric: reasons.append('unsupported_units')
                if code in ('G2', 'G3'): reasons.append('arc_not_indexed_as_linear')
                if role not in ALLOWED_ROLES: reasons.append('unknown_or_excluded_role')
                if not all(finite(v) and v > 0 for v in (height, width, feed)):
                    reasons.append('missing_emitted_geometry_or_feed')
                if not finite(de) or de <= 0 or not finite(xy) or xy <= 0:
                    reasons.append('travel_retraction_or_unknown_extrusion')
                if dz is None or abs(dz) > .0001: reasons.append('z_motion_or_unknown_height')
                segments[start] = dict(offset=start, end=offset, code=code, role=role,
                    height=height, width=width, feed=feed, layer=layer, tool=tool,
                    object=obj, delta_e=de, xy_length=xy,
                    before=before, after=dict(pos), absolute_coordinates=absolute,
                    absolute_extrude=eabsolute,
                    e_per_mm=de / xy if finite(de) and finite(xy) and xy > 0 else None,
                    parameters=args, eligible=not reasons, reasons=reasons)
    final = os.stat(path)
    if (initial.st_size, initial.st_mtime_ns, initial.st_ino) != (
            final.st_size, final.st_mtime_ns, final.st_ino):
        raise ValueError('G-code changed during scan')
    if not complete or in_config: issues.append('missing_complete_config_block')
    if slicer is None: issues.append('unidentified_slicer')
    required = ('nozzle_diameter', 'filament_diameter', 'filament_type', 'filament_flow_ratio')
    missing = [key for key in required if key not in settings]
    if missing: issues.append('missing_material_or_nozzle_settings')
    if not settings.get('filament_type', '').strip('\" '):
        issues.append('invalid_material_setting')
    for key in ('nozzle_diameter', 'filament_diameter', 'filament_flow_ratio'):
        try:
            values = [float(v) for v in setting_values(settings, key)]
            if not values or not all(finite(v) and v > 0 for v in values): raise ValueError()
        except ValueError:
            issues.append('invalid_numeric_setting:' + key)
    # Tool/filament variant remapping is not inferred from a single extruder's
    # status. Single-material files work without any extra slicer hooks.
    single_values = all(len(setting_values(settings, key)) == 1 for key in
                        ('filament_type', 'filament_diameter', 'filament_flow_ratio', 'nozzle_diameter'))
    single_used = used_filaments is not None and len(used_filaments) == 1 and used_filaments[0] >= 0
    if not single_values and not single_used:
        issues.append('multi_material_mapping_unverified')
    if single_used:
        for key in ('filament_type', 'filament_diameter', 'filament_flow_ratio'):
            values = setting_values(settings, key)
            if len(values) != 1 and used_filaments[0] >= len(values):
                issues.append('filament_index_out_of_range')
    if used_filaments is not None and len(used_filaments) != 1:
        issues.append('multi_material_mapping_unverified')
    # Keep script bodies and unknown keys in physics identity. Exclude only
    # explicitly nonphysical provenance; never discard all "other" settings.
    physics = {k: v for k, v in settings.items() if k not in PROVENANCE_ONLY}
    if plate_values: physics['emitted_plate_coordinates'] = plate_values
    file_hash = hasher.hexdigest()
    sidecar, sidecar_stat = project_sidecar(path, file_hash)
    if sidecar is not None: physics['project_settings_sha256'] = sidecar['physics_sha256']
    coverage = None
    registry_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
        'reference', 'orca_606b50f1', 'parameter_registry_606b50f1.json')
    try:
        with open(registry_path) as stream: registry = json.load(stream)
        expected = {row['key'] for row in registry['settings']}
        coverage = dict(expected_process_bindings=len(expected),
                        exported_process_bindings=len(expected.intersection(settings)),
                        missing_keys=sorted(expected.difference(settings)))
    except (OSError, ValueError, KeyError):
        pass  # Coverage catalog is documentation, never a source of defaults.
    result = dict(schema=1, file_sha256=hasher.hexdigest(), bytes=offset, slicer=slicer,
                settings=settings, settings_sha256=digest(settings),
                setting_variants={k:v for k,v in variants.items() if len(v)>1},
                emitted_plate_coordinates=plate_values,
                physics_sha256=digest(physics), segments=segments,
                complete_config=complete, missing_settings=missing,
                issues=sorted(set(issues)), eligible=not issues,
                file_stat=[final.st_size, final.st_mtime_ns, final.st_ino],
                used_filaments=used_filaments,
                project_snapshot=sidecar, sidecar_stat=sidecar_stat,
                process_coverage=coverage,
                scope='emitted_global_config_plus_emitted_segments; unexported object/modifier settings unknown')
    try:
        path=os.path.join(os.path.dirname(os.path.realpath(__file__)),'reference','orca_606b50f1','filament_registry_606b50f1.json')
        with open(path) as stream:filament_registry=json.load(stream)
        result['filament_profile']=filament_profile_scan(settings,filament_registry,used_filaments)
    except (OSError,ValueError,KeyError,TypeError):
        result['filament_profile']=None
    return result


def public_snapshot(snapshot):
    return {key: value for key, value in snapshot.items() if key != 'segments'}


class GcodeContext:
    def __init__(self, owner, config):
        self.owner = owner
        self.enabled = config.getboolean('gcode_context', True)
        # When to read the print file (10.2.4). Parsing a long G-code file on
        # the printer takes tens of seconds and, through Python's GIL, slows
        # Klipper's reactor while it runs; at the first layer that ended a
        # print with "Timer too close". 'soak' starts the read when Auto Trim
        # announces its bed heat soak wait, so it is done long before the
        # first layer; without a soak wait the file is not read. 'arm' reads
        # it when Deep Calibration is armed (10.2.2 behaviour).
        self.start_policy = config.get('gcode_context_start', 'soak').strip().lower()
        if self.start_policy not in ('soak', 'arm'):
            raise config.error('gcode_context_start must be soak or arm')
        self.listening = False
        self.skip_reported = False
        self.settle = config.getfloat('segment_settle', .5, minval=.2, maxval=30.)
        if not finite(self.settle): raise config.error('segment_settle must be finite')
        self.worker = None
        self.cancel = threading.Event()
        self.lock = threading.Lock()
        self.pending = None
        self.snapshot = None
        self.path = None
        self.state = 'disabled' if not self.enabled else 'unavailable'
        self.error = None
        self.cache = collections.OrderedDict()
        self.timeline = collections.deque(maxlen=8192)
        self.handlers = {}
        self.last_gate = None
        self.steady_since = None
        self.last_velocity = None
        self.last_stamp = None
        self.last_segment = None
        self.last_identity = None
        self.last_eligible = None
        self.emitted_hash = None
        self.generation = 0
        self.flow_reference = None
        self.pressure_until = 0.
        self.commands = collections.deque(maxlen=256)
        self.recent = collections.deque(maxlen=1024)
        self.epoch = None
        self.live_conditions = None
        self.history_drops = 0
        self.observation_drops = 0
        self.sd = self.gm = self.mcu = self.report = None
        self.in_progress = []
        self.last_check = None

    def install(self):
        if not self.enabled or self.handlers: return
        for attr, name in (('sd', 'virtual_sdcard'), ('gm', 'gcode_move'),
                           ('mcu', 'mcu'), ('report', 'motion_report')):
            setattr(self, attr, self.owner.printer.lookup_object(name, None))
        for name in ('G0', 'G1', 'G2', 'G3'):
            original = self.owner.gcode.register_command(name, None)
            if original is None: continue
            self.handlers[name] = original
            def observer(gcmd, name=name, original=original):
                return self.observe(name, original, gcmd)
            self.owner.gcode.register_command(name, observer)

    def _path(self):
        sd = self.owner.printer.lookup_object('virtual_sdcard', None)
        if sd is None: return None
        path_fn = getattr(sd, 'file_path', None)
        path = path_fn() if callable(path_fn) else None
        return os.path.realpath(path) if path and os.path.isabs(path) else None

    def request(self):
        if not self.enabled: return
        try:
            path = self._path()
        except Exception as exc:
            self.snapshot = None
            self.state, self.error = 'error', 'virtual-SD path unavailable: ' + str(exc)
            self.reset_gate()
            return
        if path is None and self.owner.active and self.path is not None:
            # virtual_sdcard closes the file at EOF while its final moves may
            # still be queued. Keep their immutable attribution until capture
            # ends; the native clock/velocity still controls sample eligibility.
            path = self.path
        if path == self.path and self.state in ('loading', 'ready', 'error', 'unsupported'):
            if self.state == 'ready' and self.snapshot:
                try:
                    stat = os.stat(path)
                    if [stat.st_size, stat.st_mtime_ns, stat.st_ino] != self.snapshot['file_stat']:
                        self.state, self.error = 'error', 'G-code changed after scan'
                        self.snapshot = None
                        self.clear_motion()
                        self.reset_gate()
                    elif (file_stat(path + '.dc.json') if os.path.exists(path + '.dc.json') else None) != self.snapshot['sidecar_stat']:
                        self.state, self.error = 'error', 'project snapshot changed after scan'
                        self.snapshot = None
                        self.clear_motion()
                        self.reset_gate()
                except OSError as exc:
                    self.state, self.error = 'error', str(exc)
                    self.snapshot = None
                    self.reset_gate()
            return
        self.generation += 1
        generation = self.generation
        self.cancel.set()
        cancel = self.cancel = threading.Event()
        self.path, self.snapshot, self.error = path, None, None
        self.clear_motion()
        self.reset_gate()
        self.emitted_hash = None
        if not path:
            self.state = 'unavailable'
            return
        self.state = 'loading'
        def scan():
            began = time.monotonic()
            try:
                snapshot = parse_file(path, cancel)
                self.read_seconds = time.monotonic() - began
                # Cache immutable results by actual file content, not filename.
                with self.lock:
                    if cancel.is_set(): return
                    key = (snapshot['file_sha256'],
                           (snapshot['project_snapshot'] or {}).get('settings_sha256'))
                    cached = self.cache.setdefault(key, snapshot)
                    # A renamed/reuploaded identical file has a different inode
                    # and timestamps. These belong to this scan, not the cache.
                    snapshot = dict(cached, file_stat=snapshot['file_stat'],
                                    sidecar_stat=snapshot['sidecar_stat'],
                                    project_snapshot=snapshot['project_snapshot'])
                    self.cache.move_to_end(key)
                    while len(self.cache) > 2: self.cache.popitem(last=False)
                    self.pending = (generation, snapshot, None)
            except Exception as exc:
                with self.lock:
                    if not cancel.is_set(): self.pending = (generation, None, str(exc))
        self.worker = threading.Thread(target=scan, name='deep-calibration-gcode', daemon=True)
        self.worker.start()

    def _listen(self):
        # Watch the console for Auto Trim's soak announcement (no change to
        # Auto Trim needed). Attached once; tolerated if unavailable.
        if self.listening: return
        self.listening = True
        register = getattr(self.owner.gcode, 'register_output_handler', None)
        if callable(register):
            register(self._on_output)

    def _on_output(self, msg):
        try:
            if (self.enabled and self.start_policy == 'soak' and isinstance(msg, str)
                    and 'AUTO TRIM: bed heat soak' in msg and 'waiting' in msg):
                self.request()          # the printer is only waiting now
        except Exception:
            logging.exception('deep_calibration: G-code context preload')

    def _requested_for_current_file(self):
        try:
            path = self._path()
        except Exception:
            return False
        return path is not None and path == self.path and self.state in ('loading', 'ready', 'error', 'unsupported')

    def poll(self):
        if not self.enabled: return
        self._listen()
        now = self.owner.reactor.monotonic()
        watching = self.owner.active or self.owner.armed is not None or self.owner.knee is not None
        if watching and (self.last_check is None or now - self.last_check >= 1. or not self.owner.active):
            self.last_check = now
            if (self._requested_for_current_file()
                    or (self.owner.active and self.path and self._path() is None)
                    or (self.start_policy == 'arm' and not self.owner.active)):
                self.request()
            elif self.state != 'skipped':
                # No soak wait before the first layer: reading the file now
                # would compete with it. Record without slicer context.
                self.state = 'skipped'
                self.error = ('no soak wait before the first layer: G-code context not read '
                              '(gcode_context_start: soak)')
                self.snapshot = None; self.path = None
                self.generation += 1
                self.cancel.set()
                self.clear_motion(); self.reset_gate()
                self.skip_reported = False
            if self.state == 'skipped' and not self.skip_reported and (self.owner.active or self.owner.armed is not None):
                self.skip_reported = True
                self.owner.gcode.respond_info('DEEP CALIBRATION: ' + self.error)
                if self.owner.active:
                    self.owner._event('slicer_context_skipped', reason=self.error)
        with self.lock:
            pending, self.pending = self.pending, None
        if pending and pending[0] == self.generation:
            self.snapshot, self.error = pending[1:]
            self.state = 'ready' if self.snapshot else 'error'
            if self.snapshot:
                # 10.3.2: the parsed file is millions of small objects kept
                # for the whole print. A full garbage collection walked them
                # all (about 0.5 s on an AD5X) and a print shut down with
                # "Timer too close" in the middle of the mesh. Freezing moves
                # everything alive now into the permanent generation, which
                # collections skip; memory is still freed by reference counts.
                freeze = getattr(gc, 'freeze', None)
                if callable(freeze):
                    freeze()
                    self.frozen = getattr(gc, 'get_freeze_count', lambda: None)()
            if self.snapshot and getattr(self, 'read_seconds', None) is not None:
                # How long the read took on this printer: it must fit in the soak
                self.owner.gcode.respond_info('DEEP CALIBRATION: G-code context read in %.1f s (%d bytes)'
                                              % (self.read_seconds, self.snapshot.get('bytes') or 0))
                self.read_seconds = None
        if self.owner.active and self.snapshot and self.emitted_hash != self.snapshot['file_sha256']:
            self.owner._event('slicer_snapshot', **public_snapshot(self.snapshot))
            self.emitted_hash = self.snapshot['file_sha256']

        requested=getattr(self.owner,'filament_reports_pending',set())
        if requested and self.state != 'loading':
            for show in sorted(requested):self.owner._filament_report(show,self.owner.gcode.respond_info)
            requested.clear()

    PRINT_WIDE = frozenset(('raft_first_layer', 'mixed_color_sublayer', 'spiral_mode',
                            'model_flushing_not_separated', 'scarf_wall_not_separated',
                            'tool_mapping_changed', 'unresolved_tool_material_dimensions'))

    def _print_wide(self, reason, snapshot):
        return (reason in self.PRINT_WIDE or reason.startswith(('missing_eligibility_setting:', 'slicer_snapshot_'))
                or reason in ((snapshot or {}).get('issues') or ()))

    def reset_gate(self):
        self.last_gate = self.steady_since = self.last_velocity = None
        self.last_stamp = self.last_segment = self.last_identity = None
        self.flow_reference = None
        self.last_eligible = None
        self.pressure_until = 0.

    def clear_motion(self):
        self.timeline.clear()
        self.misses = []
        self.commands.clear()
        self.recent.clear()
        self.live_conditions = None
        self.epoch = None

    def start_recording(self):
        self.clear_motion()
        self.observation_drops = self.history_drops = 0
        self.miss_counts = {}
        self.unverified_counts = {}

    def match_status(self):
        return dict(observation_drops=self.observation_drops, history_drops=self.history_drops,
                    phase_misses=dict(getattr(self, 'miss_counts', {})),
                    unverified_commands=dict(getattr(self, 'unverified_counts', {})))

    def _miss(self, start, end, kind):
        # 10.3.6: why a motion phase found no unique G-code line
        self.misses.append((start, end, kind))
        counts = getattr(self, 'miss_counts', None)
        if counts is None:
            counts = self.miss_counts = {}
        counts[kind] = counts.get(kind, 0) + 1
        self.last_check = None

    def observe(self, name, original, gcmd):
        """Keep only an SD command and cheap native checkpoints on the hot path."""
        if not (self.owner.active and self.state == 'ready' and self.snapshot):
            return original(gcmd)
        sd, gm = self.sd, self.gm
        if sd is None or gm is None or not getattr(sd, 'cmd_from_sd', False):
            return original(gcmd)
        try:
            offset = sd.file_position
            epoch = self.epoch
            before = self.checkpoint(gm)
            stamp = self.owner.reactor.monotonic()
            params = gcmd.get_command_parameters()
        except Exception:
            self.observation_drops += 1
            self.commands.clear()
            self.recent.clear()
            return original(gcmd)
        self.in_progress.append((stamp, before[0]))
        try:
            result = original(gcmd)
        except BaseException:
            self.commands.clear()
            self.recent.clear()
            raise
        finally:
            self.in_progress.pop()
        try:
            if self.owner.active and self.state == 'ready':
                if len(self.commands) == self.commands.maxlen:
                    self.observation_drops += 1
                    self.commands.clear()
                    self.recent.clear()
                self.commands.append((offset, name, params, stamp, epoch, before,
                                      self.checkpoint(gm), bool(self.in_progress)))
        except Exception:
            self.observation_drops += 1
            self.commands.clear()
            self.recent.clear()
        return result

    @staticmethod
    def checkpoint(gm):
        # Klipper stores these native arrays in place; copy only the four axes
        # and scalar modes. No status walks or parameter parsing in dispatch.
        return (tuple(gm.last_position[:4]), tuple(gm.base_position[:4]),
                gm.absolute_coord, gm.allow_absolute_extrude, gm.speed,
                gm.speed_factor, gm.extrude_factor)

    @staticmethod
    def verified_command(segment, before, after):
        return GcodeContext.verify_reason(segment, before, after) is None

    @staticmethod
    def verify_reason(segment, before, after):
        # 10.3.7: the same checks as before, naming the first that fails
        if before[2:4] != after[2:4] or before[2:4] != (segment['absolute_coordinates'], segment['absolute_extrude']):
            return 'coordinate_modes'
        if (not finite(after[5]) or after[5] <= 0 or not finite(after[6]) or after[6] <= 0
                or before[6] != after[6]):
            return 'speed_or_extrude_factor'
        if not finite(segment['feed']) or not finite(segment['delta_e']):
            return 'segment_values'
        if abs(after[4] / after[5] / 60. - segment['feed']) > 1.e-5:
            return 'feed'
        for step, key in ((before, 'before'), (after, 'after')):
            pos, base = step[:2]
            expected = segment[key]
            for axis in range(3):
                target = expected['XYZ'[axis]]
                if not finite(target) or abs(pos[axis] - base[axis] - target) > 1.e-5:
                    return 'position_%s_%s' % (key, 'XYZ'[axis])
            if step[2] and step[3]:
                target_e = expected['E']
                if not finite(target_e) or abs((pos[3] - base[3]) / step[6] - target_e) > 1.e-5:
                    return 'extrusion_%s' % key
        if abs((after[0][3] - before[0][3]) / after[6] - segment['delta_e']) > 1.e-5:
            return 'delta_e'
        return None

    def batch(self, stamps, context):
        """Match native motion phases at receipt times on the reactor tick."""
        if not (self.owner.active and self.handlers and self.state == 'ready' and self.snapshot):
            return
        self.timeline.clear()
        self.misses = []
        live = self.conditions(context)
        identity = (live, context.get('mesh_identity'))
        changed = identity != self.live_conditions
        if changed:
            self.epoch = object()
            self.live_conditions = identity
            self.recent.clear()
        if self.mcu is None:
            return
        if len(self.commands) > 128:
            self._miss(-1., -1., 'commands_overflow')
            self.observation_drops += len(self.commands)
            self.commands.clear()
            self.recent.clear()
            return
        for offset, name, params, stamp, epoch, before, after, nested in self.commands:
            segment = self.snapshot['segments'].get(offset)
            try:
                if changed: reason = 'conditions_changed'
                elif epoch is not self.epoch: reason = 'epoch_changed'
                elif nested: reason = 'nested_command'
                elif not segment: reason = 'not_indexed'
                elif name != segment['code'] or name not in ('G0', 'G1'): reason = 'command_code'
                elif not segment.get('xy_length'): reason = 'no_xy_length'
                elif live['speed_factor'] is not None and abs(after[5] * 60. - live['speed_factor']) > 1.e-5:
                    reason = 'speed_factor'
                elif live['extrude_factor'] is not None and abs(after[6] - live['extrude_factor']) > 1.e-5:
                    reason = 'extrude_factor'
                elif ({k: float(v) for k, v in params.items() if k in ('X','Y','Z','E','F','I','J','R','P')}
                      != segment['parameters']):
                    reason = 'parameters'
                else:
                    reason = self.verify_reason(segment, before, after)
            except (TypeError, ValueError, IndexError, KeyError):
                reason = 'unreadable_state'
            entry_segment = segment if reason is None else None
            # An unverified command (macro, rewrite, failed check) overlapping
            # an indexed path is kept as a blocker until it ages out.
            entry = (self.mcu.estimated_print_time(stamp), entry_segment, before[0], after[0])
            if reason is not None:
                counts = getattr(self, 'unverified_counts', None)
                if counts is None:
                    counts = self.unverified_counts = {}
                counts[reason] = counts.get(reason, 0) + 1
                reasons = getattr(self, 'block_reasons', None)
                if reasons is None or len(reasons) > 4096:
                    reasons = self.block_reasons = {}
                reasons[(entry[0], tuple(entry[2]), tuple(entry[3]))] = reason
            self.recent.append(entry)
        self.commands.clear()
        if not stamps or not self.recent:
            return
        clocks = [self.mcu.estimated_print_time(t) for t in stamps if 0 <= context['t'] - t <= .35]
        if not clocks:
            return
        oldest = min(clocks)
        while self.recent and self.recent[0][0] < oldest - 32.:
            self.recent.popleft()
        trapq = getattr(self.report, 'dtrapqs', {}).get('toolhead')
        extract = getattr(trapq, 'extract_trapq', None)
        if not callable(extract):
            return
        rows, backing = extract(oldest, max(clocks) + 1.e-6)
        if len(rows) > 256:
            self._miss(-1., -1., 'history_overflow')
            self.history_drops += 1
            return
        phases = iter(rows)
        phase = next(phases, None)
        inflight = [(self.mcu.estimated_print_time(t), None, a, self.gm.last_position[:4])
                    for t, a in self.in_progress]
        for clock in sorted(set(clocks)):
            while phase is not None and phase.print_time + phase.move_t <= clock:
                phase = next(phases, None)
            if phase is None or not phase.print_time <= clock < phase.print_time + phase.move_t:
                self._miss(clock, clock, 'no_motion_phase')
                continue
            if (any(r['start'] == phase.print_time for r in self.timeline)
                    or any(m[0] == phase.print_time for m in self.misses)):
                continue
            self.last_miss = None
            record = self.match_phase(phase, live, inflight)
            if record is not None:
                self.timeline.append(record)
            else:
                self._miss(phase.print_time, phase.print_time + phase.move_t, self.last_miss or 'no_candidate')

    def match_phase(self, phase, conditions, inflight=()):
        """Only a unique emitted path containing the whole native XY phase."""
        start = phase.print_time
        dt = phase.move_t
        distance = (phase.start_v + .5 * phase.accel * dt) * dt
        vx, vy = phase.x_r * distance, phase.y_r * distance
        if math.hypot(vx, vy) <= 1.e-9:
            self.last_miss = 'no_xy_motion'
            return None
        x, y = phase.start_x, phase.start_y
        candidates = []
        for observed, segment, a, b in itertools.chain(self.recent, inflight):
            if observed > start + .002:
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            if (x < min(a[0], b[0]) - 1.e-5 or x > max(a[0], b[0]) + 1.e-5
                    or y < min(a[1], b[1]) - 1.e-5 or y > max(a[1], b[1]) + 1.e-5):
                continue
            norm2 = dx * dx + dy * dy
            if norm2 <= 1.e-12 or vx * dx + vy * dy <= 0:
                continue
            u, v = x - a[0], y - a[1]
            if (abs(u * dy - v * dx) > 1.e-5 * math.sqrt(norm2)
                    or abs((u + vx) * dy - (v + vy) * dx) > 1.e-5 * math.sqrt(norm2)
                    or u * dx + v * dy < -1.e-5
                    or (u + vx) * dx + (v + vy) * dy > norm2 + 1.e-5):
                continue
            candidates.append((segment, a, b, observed))
            if len(candidates) > 1:
                self.last_miss = 'ambiguous_queue_segment'
                return None
        if not candidates:
            self.last_miss = 'no_queue_segment'
            return None
        segment, a, b, observed = candidates[0]
        if segment is None:
            why = getattr(self, 'block_reasons', {}).get((observed, tuple(a), tuple(b)))
            self.last_miss = 'blocked_by_unverified_command' + (':' + why if why else '')
            return None
        return dict(start=start, end=start + dt, segment=segment, source_valid=True,
                    conditions=conditions, native_start=a, native_end=b)

    def status(self):
        s = self.snapshot or {}
        return dict(enabled=self.enabled, state=self.state, error=self.error,
                    start_policy=self.start_policy, gc_frozen_objects=getattr(self, 'frozen', None),
                    file_sha256=s.get('file_sha256'), physics_sha256=s.get('physics_sha256'),
                    setting_count=len(s.get('settings', {})), indexed_commands=len(s.get('segments', {})),
                    issues=s.get('issues', []), timing_observer_installed=bool(self.handlers),
                    timing_source='native_trapq_history' if self.handlers else None,
                    timing_before_native_pause=False,
                    observation_drops=self.observation_drops, history_drops=self.history_drops)

    @staticmethod
    def conditions(context):
        gm = context.get('gcode', {})
        heaters = context.get('heaters', {})
        extruder = context.get('extruder_state', {})
        return dict(speed_factor=gm.get('speed_factor'), extrude_factor=gm.get('extrude_factor'),
                    pressure_advance=extruder.get('pressure_advance'),
                    smooth_time=extruder.get('smooth_time'),
                    nozzle_target=heaters.get('extruder', {}).get('target'),
                    bed_target=heaters.get('heater_bed', {}).get('target'),
                    fans={k: v.get('speed') for k, v in context.get('fans', {}).items()})

    def sample(self, stamp, motion, context):
        reasons, segment, record = [], None, None
        queue_miss = None
        if not self.enabled: return dict(eligible=True, reasons=[], mode='legacy_opt_out')
        snapshot = self.snapshot
        if self.state != 'ready' or not snapshot: reasons.append('slicer_snapshot_' + self.state)
        elif not snapshot['eligible']: reasons.extend(snapshot['issues'])
        clock = motion.get('print_time')
        if motion.get('method') != 'native_trapq_at_host_receipt' or not finite(clock):
            reasons.append('unverified_motion_clock')
        else:
            matches = [r for r in self.timeline if finite(r['start']) and finite(r['end'])
                       and r['start'] <= clock < r['end']]
            if len(matches) != 1:
                reasons.append('missing_or_ambiguous_queue_segment')
                # 10.3.6: which kind (kept under the same reason for compatibility)
                if matches:
                    queue_miss = 'overlapping_timeline_records'
                else:
                    kinds = [m[2] for m in getattr(self, 'misses', ()) if m[0] <= clock <= m[1]]
                    queue_miss = kinds[0] if kinds else 'not_examined'
            elif (not matches[0]['source_valid'] or
                  not matches[0].get('parent', {}).get('source_valid', True)):
                reasons.append('unindexed_or_macro_motion')
            else:
                record = matches[0]
                segment = record['segment']
                if 'native_start' in record:
                    a, b = record['native_start'], record['native_end']
                    pos = motion.get('live_position')
                    if not pos or len(pos) < 4 or not all(finite(v) for v in (pos[0], pos[1], pos[3])):
                        reasons.append('unverified_extrusion_position')
                    else:
                        dx, dy = b[0] - a[0], b[1] - a[1]
                        fraction = ((pos[0] - a[0]) * dx + (pos[1] - a[1]) * dy) / (dx*dx + dy*dy)
                        if abs(pos[3] - (a[3] + fraction * (b[3] - a[3]))) > .02:
                            reasons.append('native_extrusion_path_mismatch')
        gm = context.get('gcode', {})
        heaters = context.get('heaters', {})
        extruder = context.get('extruder_state', {})
        ps = context.get('print_stats', {})
        if ps.get('state') != 'printing': reasons.append('not_printing')
        if (ps.get('info') or {}).get('current_layer') != 1: reasons.append('unverified_first_layer')
        live = self.conditions(context)
        if record is not None and record.get('conditions') != live:
            reasons.append('queued_conditions_differ_from_live_context')
        live['mesh'] = context.get('mesh_identity')
        if not all(finite(live[k]) for k in ('speed_factor', 'extrude_factor', 'pressure_advance',
                                            'smooth_time', 'nozzle_target', 'bed_target')):
            reasons.append('missing_live_conditions')
        if live['mesh'] is None: reasons.append('unverified_mesh_identity')
        for name, band in (('extruder', 3.), ('heater_bed', 1.)):
            h = heaters.get(name, {})
            if not finite(h.get('temperature')) or not finite(h.get('target')) or h['target'] <= 0 or abs(h['temperature'] - h['target']) > band:
                reasons.append('temperature_not_settled:' + name)
        velocity, ev = motion.get('live_velocity'), motion.get('live_extruder_velocity')
        if not finite(velocity) or velocity <= 10 or not finite(ev) or ev <= .2:
            reasons.append('travel_retraction_or_slow')
        identity = None
        if not finite(context.get('t')) or not 0 <= context['t'] - stamp <= .35:
            reasons.append('stale_live_context')
        material, diameter, nozzle = None, None, None
        if segment:
            reasons.extend(segment['reasons'])
            settings = (snapshot or {}).get('settings', {})
            try:
                def selected(key):
                    values = setting_values(settings, key)
                    return values[segment['tool']] if len(values) > 1 else values[0]
                material = selected('filament_type').strip('" ')
                diameter = float(selected('filament_diameter'))
                nozzle_values = setting_values(settings, 'nozzle_diameter')
                if len(nozzle_values) != 1: raise ValueError('multi-extruder nozzle mapping')
                nozzle = float(nozzle_values[0])
            except (KeyError, ValueError, IndexError):
                reasons.append('unresolved_tool_material_dimensions')
            used = (snapshot or {}).get('used_filaments')
            if used is not None and used != [segment['tool']]: reasons.append('tool_mapping_changed')
            for key in ('raft_layers','enable_mixed_color_sublayer','spiral_mode','flush_into_infill','flush_into_objects'):
                if key not in settings: reasons.append('missing_eligibility_setting:' + key)
            if settings.get('raft_layers') not in ('0', '0.0'): reasons.append('raft_first_layer')
            if settings.get('enable_mixed_color_sublayer') not in ('0', 'false', 'False'):
                reasons.append('mixed_color_sublayer')
            if settings.get('spiral_mode') not in ('0', 'false', 'False'):
                reasons.append('spiral_mode')
            # 10.3.4: flushing only happens at a filament change. A print with
            # one filament never flushes, whatever the profile says (an AD5X
            # print was rejected entirely for flush_into_infill = 1); prints
            # with more than one are already rejected (tool_mapping_changed).
            if ((used is None or len(used) > 1) and
                    (settings.get('flush_into_infill') not in ('0', 'false', 'False')
                     or settings.get('flush_into_objects') not in ('0', 'false', 'False'))):
                reasons.append('model_flushing_not_separated')
            if (segment['role'] in ('outer wall', 'inner wall', 'perimeter', 'external perimeter')
                    and settings.get('seam_slope_type', '').lower() not in ('none', '0')):
                reasons.append('scarf_wall_not_separated')
            identity = dict(role=segment['role'], height=segment['height'], width=segment['width'],
                feed=segment['feed'], tool=segment['tool'], live=live,
                physics_sha256=(snapshot or {}).get('physics_sha256'))
            identity.update(material=material, filament_diameter=diameter, nozzle_diameter=nozzle)
            expected = (segment['feed'] * live['speed_factor']
                        if finite(segment['feed']) and finite(live['speed_factor']) else None)
            # Acceleration/short paths may not reach requested feed. Such force
            # samples cannot teach the same steady-flow recipe.
            if finite(expected) and finite(velocity) and abs(velocity - expected) > max(1., abs(expected) * .05):
                reasons.append('speed_not_at_commanded_feed')
            erate = segment['e_per_mm']
            if finite(erate) and finite(velocity) and finite(ev) and finite(live['extrude_factor']):
                target_e = erate * velocity * live['extrude_factor']
                if abs(ev - target_e) > max(.02, abs(target_e) * .10):
                    reasons.append('extrusion_rate_transition')
        fingerprint = digest(identity) if identity else None
        # E rounding on adjacent lines must not invent a new recipe each move.
        # Keep a stable reference only inside a 2% commanded E/mm band; record
        # the exact trajectory and include the representative band in the key.
        if segment and finite(segment['e_per_mm']) and segment['e_per_mm'] > 0:
            if (self.flow_reference is None or self.flow_reference[0] != fingerprint
                    or abs(segment['e_per_mm'] / self.flow_reference[1] - 1.) > .02):
                self.flow_reference = (fingerprint, segment['e_per_mm'])
                self.pressure_until = max(self.pressure_until, stamp + 2.)
            fingerprint = digest([fingerprint, round(self.flow_reference[1], 4)])
        if finite(ev) and ev < -.01:
            self.pressure_until = max(self.pressure_until, stamp + 2.)
        if stamp < self.pressure_until: reasons.append('extrusion_history_settling')
        if self.last_stamp is not None and stamp <= self.last_stamp:
            reasons.append('nonmonotonic_sample')
        if self.last_velocity is not None and self.last_stamp is not None and stamp > self.last_stamp:
            if finite(velocity) and abs(velocity - self.last_velocity) / (stamp - self.last_stamp) > 20.:
                reasons.append('speed_transition')
        # 10.3.4: only conditions of this moment restart the settling run.
        # Print-wide settings (flushing, raft, spiral, scarf, tool mapping,
        # snapshot issues) keep the reading ineligible but say nothing about
        # whether the flow is steady now; restarting on them made every
        # reading "settling" too.
        moment = [r for r in reasons if not self._print_wide(r, snapshot)]
        if moment or fingerprint != self.last_identity or (self.last_stamp is not None and stamp - self.last_stamp > .5):
            self.steady_since = stamp
        if self.steady_since is None: self.steady_since = stamp
        if stamp - self.steady_since < self.settle: reasons.append('segment_settling')
        self.last_velocity = velocity if finite(velocity) else None
        self.last_stamp, self.last_segment, self.last_identity = stamp, segment, fingerprint
        self.last_gate = dict(eligible=not reasons, reasons=sorted(set(reasons)),
            mode='trapq_matched_emitted_segment', segment=segment, fingerprint=fingerprint,
            physics_sha256=(snapshot or {}).get('physics_sha256'), file_sha256=(snapshot or {}).get('file_sha256'),
            print_time=clock, live=live, context_age=context['t'] - stamp if finite(context.get('t')) else None)
        self.last_gate.update(material=material, filament_diameter=diameter, nozzle_diameter=nozzle)
        if queue_miss is not None:
            self.last_gate['queue_miss'] = queue_miss
        if self.last_gate['eligible']:
            self.last_eligible = dict(self.last_gate, t=stamp)
        return self.last_gate

    def stop(self):
        self.cancel.set()
