# Auto Trim shape-aware bed mesh (optional addon). GPLv3.
#
# KAMP meshes the bounding rectangle of the print. A part that runs
# diagonally across the bed fills its rectangle only partly, yet every grid
# point of that rectangle is probed. This probes only the grid points near the
# printed objects (Orca's EXCLUDE_OBJECT polygons) and fills the others from
# the saved full-bed mesh, aligned to the freshly probed points by a plane
# (shift and tilt), so Klipper gets the complete rectangular mesh it needs.
# Nothing is printed at the filled points; where the part is, the mesh comes
# from fresh probing.
#
# The mesh is built after probing has ended and the toolhead has finished its
# moves (1.0.1). Klipper calls the probing helper's finalize callback right
# after committing the next move to a time a fraction of a second ahead;
# building the mesh inside that callback took 0.4 s on an AD5X, the move's
# steps were sent too late, and the printer shut down with "Timer too close".
#
# 1.2.0: when the saved base mesh is denser than the probe grid (e.g. a
# 21 x 21 full-bed mesh), the final mesh is built on the base's own grid over
# the print area: the base's measured height at each point (the plate's hills
# and valleys, finer than the probe grid can see), plus the plane fitted to
# today's probes (offset and tilt), plus a smooth local correction where
# today's probes differ from the base, fading out away from them.
#
# The grid (area and point count) is laid out as Klipper's adaptive mesh does
# for the same area, and the probing goes through Klipper's ProbePointsHelper,
# like a normal mesh: the probe's own speed, samples and retries apply, and
# hooks on the probe touch (Deep Calibration's guarded approach) still work.
import logging
import math

try:
    from . import bed_mesh as bed_mesh_module
    from . import probe as probe_module
except ImportError:          # imported outside Klipper (tests)
    bed_mesh_module = probe_module = None

VERSION = '1.2.0'


def _inside(px, py, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i][0], poly[i][1]
        xj, yj = poly[j][0], poly[j][1]
        if (yi > py) != (yj > py):
            if px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def _segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0. if length == 0. else max(0., min(1., ((px - ax) * dx + (py - ay) * dy) / length))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def polygon_distance(px, py, poly):
    """0 inside the polygon, otherwise the distance to its outline (mm)."""
    if len(poly) < 3:
        return min(math.hypot(px - p[0], py - p[1]) for p in poly)
    if _inside(px, py, poly):
        return 0.
    return min(_segment_distance(px, py, poly[i - 1][0], poly[i - 1][1], poly[i][0], poly[i][1])
               for i in range(len(poly)))


def adaptive_grid(polygons, mesh_min, mesh_max, counts, margin):
    """Klipper's adaptive mesh for the objects' area: bounds (objects plus
    margin, clipped to the configured mesh) and point counts scaled with the
    area, at least 3 (4 when the other axis has more than 6)."""
    xs = [p[0] for poly in polygons for p in poly]
    ys = [p[1] for poly in polygons for p in poly]
    lo = [max(mesh_min[0], min(xs) - margin), max(mesh_min[1], min(ys) - margin)]
    hi = [min(mesh_max[0], max(xs) + margin), min(mesh_max[1], max(ys) + margin)]
    ratio = [(hi[0] - lo[0]) / (mesh_max[0] - mesh_min[0]), (hi[1] - lo[1]) / (mesh_max[1] - mesh_min[1])]
    nx = int(math.ceil(counts[0] * ratio[0]))
    ny = int(math.ceil(counts[1] * ratio[1]))
    least = 4 if max(nx, ny) > 6 and min(nx, ny) < 4 else 3
    nx, ny = max(least, nx), max(least, ny)
    # a too-small area is widened to at least one mm per point, as Klipper does
    for axis, n in ((0, nx), (1, ny)):
        if hi[axis] - lo[axis] < n:
            hi[axis] = min(mesh_max[axis], lo[axis] + n)
    return lo, hi, nx, ny


def grid_nodes(lo, hi, nx, ny):
    """Row-major (y rows, x ascending), as Klipper's probed matrix."""
    return [(lo[0] + (hi[0] - lo[0]) * i / (nx - 1), lo[1] + (hi[1] - lo[1]) * j / (ny - 1))
            for j in range(ny) for i in range(nx)]


def select_nodes(nodes, polygons, reach):
    return [k for k, (x, y) in enumerate(nodes)
            if min(polygon_distance(x, y, poly) for poly in polygons) <= reach]


def serpentine(indexes, nx):
    """Probing order: rows ascending, alternate rows reversed (short travel)."""
    rows = {}
    for k in indexes:
        rows.setdefault(k // nx, []).append(k)
    order = []
    for n, row in enumerate(sorted(rows)):
        order.extend(sorted(rows[row], reverse=bool(n % 2)))
    return order


def fit_plane(points):
    """Least-squares z = a + b x + c y; a constant when the points do not span
    a plane."""
    n = len(points)
    mean = sum(p[2] for p in points) / n
    if n < 3:
        return mean, 0., 0.
    sx = sum(p[0] for p in points); sy = sum(p[1] for p in points)
    sxx = sum(p[0] * p[0] for p in points); syy = sum(p[1] * p[1] for p in points)
    sxy = sum(p[0] * p[1] for p in points)
    sz = sum(p[2] for p in points)
    sxz = sum(p[0] * p[2] for p in points); syz = sum(p[1] * p[2] for p in points)
    m = [[n, sx, sy], [sx, sxx, sxy], [sy, sxy, syy]]
    v = [sz, sxz, syz]

    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    scale = max(1., abs(sxx) + abs(syy)) ** 2 * n
    if abs(d) < 1e-9 * scale:
        return mean, 0., 0.
    out = []
    for col in range(3):
        mm = [row[:] for row in m]
        for r in range(3):
            mm[r][col] = v[r]
        out.append(det(mm) / d)
    return tuple(out)


def idw(x, y, probed):
    """Inverse-distance weighting from the probed points (no saved mesh)."""
    num = den = 0.
    for px, py, pz in probed:
        d2 = (x - px) ** 2 + (y - py) ** 2
        if d2 < 1e-12:
            return pz
        w = 1. / d2
        num += w * pz
        den += w
    return num / den


def dense_from_base(base_points, base_params, lo, hi, probed, base, reach, min_count):
    """The final mesh on the base's grid over [lo, hi]; None if the base is
    not denser than min_count points per axis there. probed: [(x, y, z)]."""
    xc, yc = int(base_params['x_count']), int(base_params['y_count'])
    bx = [base_params['min_x'] + (base_params['max_x'] - base_params['min_x']) * i / (xc - 1) for i in range(xc)]
    by = [base_params['min_y'] + (base_params['max_y'] - base_params['min_y']) * j / (yc - 1) for j in range(yc)]
    i0 = max([i for i in range(xc) if bx[i] <= lo[0] + 1e-6] or [0]); i1 = min([i for i in range(xc) if bx[i] >= hi[0] - 1e-6] or [xc - 1])
    j0 = max([j for j in range(yc) if by[j] <= lo[1] + 1e-6] or [0]); j1 = min([j for j in range(yc) if by[j] >= hi[1] - 1e-6] or [yc - 1])
    nx, ny = i1 - i0 + 1, j1 - j0 + 1
    if nx <= min_count[0] and ny <= min_count[1]:
        return None
    if nx < 3 or ny < 3:
        return None
    residuals = [(x, y, z - base(x, y)) for x, y, z in probed]
    a, b, c = fit_plane(residuals)
    local = [(x, y, r - (a + b * x + c * y)) for x, y, r in residuals]

    def correction(x, y):
        num = den = 0.
        for px, py, r in local:
            w = math.exp(-((x - px) ** 2 + (y - py) ** 2) / (reach * reach))
            num += w * r; den += w
        return num / max(den, 1.)               # fades to 0 away from the probes
    matrix = [[base_points[j][i] + a + b * bx[i] + c * by[j] + correction(bx[i], by[j])
               for i in range(i0, i1 + 1)] for j in range(j0, j1 + 1)]
    return dict(lo=(bx[i0], by[j0]), hi=(bx[i1], by[j1]), nx=nx, ny=ny, matrix=matrix,
                info=dict(shift=a + b * sum(p[0] for p in probed) / len(probed) + c * sum(p[1] for p in probed) / len(probed),
                          residual_sd=math.sqrt(sum(r * r for _, _, r in local) / len(local)),
                          residual_max=max(abs(r) for _, _, r in local), filled_from='saved mesh grid'))


def dense_pps(configured, count, limit=41):
    """Interpolation points between grid points, so that the interpolated
    mesh has at most `limit` points per axis (never more than configured)."""
    if count < 2:
        return int(configured)
    return max(0, min(int(configured), (limit - 1) // (count - 1) - 1))


def fill_matrix(nodes, nx, ny, measured, base=None):
    """measured: {node index: z}. base: callable(x, y) -> z of the saved mesh,
    or None. Returns (matrix rows, info)."""
    probed = [(nodes[k][0], nodes[k][1], z) for k, z in measured.items()]
    info = dict(filled_from='saved mesh' if base else 'probed points')
    if base is not None:
        residuals = [(x, y, z - base(x, y)) for x, y, z in probed]
        a, b, c = fit_plane(residuals)
        fit = [r - (a + b * x + c * y) for x, y, r in residuals]
        info.update(shift=a + b * sum(p[0] for p in probed) / len(probed) + c * sum(p[1] for p in probed) / len(probed),
                    tilt_x_mm_per_100mm=b * 100., tilt_y_mm_per_100mm=c * 100.,
                    residual_sd=math.sqrt(sum(f * f for f in fit) / len(fit)),
                    residual_max=max(abs(f) for f in fit))

        def value(x, y):
            return base(x, y) + a + b * x + c * y
    else:
        def value(x, y):
            return idw(x, y, probed)
    matrix = []
    for j in range(ny):
        row = []
        for i in range(nx):
            k = j * nx + i
            row.append(measured[k] if k in measured else value(*nodes[k]))
        matrix.append(row)
    return matrix, info


class ShapeMesh:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.reach_factor = config.getfloat('reach', 1., minval=.25, maxval=3.)
        self.margin = config.getfloat('margin', 3., minval=0., maxval=30.)
        self.base_profile = config.get('base_profile', 'auto')
        self.max_residual = config.getfloat('max_residual', .06, minval=.001, maxval=1.)
        self.profile_name = config.get('profile_name', 'shape')
        # 1.2.0: use the base mesh's grid when it is denser (auto/off), and how
        # far today's local differences reach (mm; 0: half a probe spacing)
        self.dense_output = config.get('dense_output', 'auto').strip().lower()
        self.local_reach = config.getfloat('local_reach', 0., minval=0., maxval=100.)
        self.helper = None
        if probe_module is not None:
            self.helper = probe_module.ProbePointsHelper(config, self._finalize, default_points=[])
            try:
                bm = config.getsection('bed_mesh')
                self.helper.default_horizontal_move_z = bm.getfloat('horizontal_move_z', 5.)
                self.helper.speed = self.helper.lift_speed = bm.getfloat('speed', 50., above=0.)
            except Exception:
                pass
        self.pending = None
        self.results = None
        self.last = None
        self.gcode.register_command('AUTO_TRIM_SHAPE_MESH', self.cmd_SHAPE_MESH,
                                    desc='Mesh probing only the grid points near the printed objects; the rest from the saved mesh')

    def _polygons(self, eventtime):
        ex = self.printer.lookup_object('exclude_object', None)
        if ex is None:
            return []
        objects = ex.get_status(eventtime).get('objects', [])
        return [[(float(p[0]), float(p[1])) for p in o['polygon']]
                for o in objects if o.get('polygon')]

    def _base(self, bed_mesh, name):
        profile = self._profile(bed_mesh, name)
        if not profile:
            return None
        zm = bed_mesh_module.ZMesh(dict(profile['mesh_params']), name)
        zm.build_mesh(profile['points'])
        return zm.calc_z

    def _profile(self, bed_mesh, name):
        profiles = bed_mesh.pmgr.get_profiles() if hasattr(bed_mesh.pmgr, 'get_profiles') else bed_mesh.pmgr.profiles
        return profiles.get(name)

    def cmd_SHAPE_MESH(self, gcmd):
        if self.helper is None:
            raise gcmd.error('AUTO_TRIM_SHAPE_MESH: Klipper probe support not available')
        now = self.printer.get_reactor().monotonic()
        polygons = self._polygons(now)
        if not polygons:
            raise gcmd.error('AUTO_TRIM_SHAPE_MESH: no object outlines. Turn on Label objects in Orca.')
        bed_mesh = self.printer.lookup_object('bed_mesh')
        bmc = bed_mesh.bmc
        zref = getattr(getattr(bmc, 'probe_mgr', None), 'get_zero_ref_mode', None)
        disabled = getattr(getattr(bed_mesh_module, 'ZrefMode', None), 'DISABLED', 0)
        if zref is not None and zref() != disabled:
            raise gcmd.error('AUTO_TRIM_SHAPE_MESH: zero_reference_position is set; use a KAMP mesh')
        orig = bmc.orig_config
        counts = (orig['x_count'], orig['y_count'])
        lo, hi, nx, ny = adaptive_grid(polygons, orig['mesh_min'], orig['mesh_max'], counts,
                                       gcmd.get_float('MARGIN', self.margin, minval=0.))
        nodes = grid_nodes(lo, hi, nx, ny)
        spacing = max((hi[0] - lo[0]) / (nx - 1), (hi[1] - lo[1]) / (ny - 1))
        reach = gcmd.get_float('REACH', self.reach_factor * spacing, minval=0.)
        chosen = select_nodes(nodes, polygons, reach)
        if len(chosen) < 3:
            chosen = list(range(len(nodes)))
        order = serpentine(chosen, nx)
        params = dict(bmc.mesh_config)
        params.update(min_x=lo[0], max_x=hi[0], min_y=lo[1], max_y=hi[1], x_count=nx, y_count=ny)
        if max(params.get('mesh_x_pps', 0), params.get('mesh_y_pps', 0)) == 0:
            params['algo'] = 'direct'
        elif params.get('algo') == 'bicubic' and min(nx, ny) < 4:
            params['algo'] = 'lagrange'
        elif params.get('algo') == 'lagrange' and max(nx, ny) > 6:
            params['algo'] = 'bicubic'
        self.pending = dict(nodes=nodes, nx=nx, ny=ny, order=order, params=params,
                            base=gcmd.get('PROFILE', self.base_profile), reach=reach, gcmd=gcmd)
        gcmd.respond_info('AUTO TRIM SHAPE MESH: %dx%d grid over X%.1f-%.1f Y%.1f-%.1f, probing %d of %d points (within %.0f mm of the print)'
                          % (nx, ny, lo[0], hi[0], lo[1], hi[1], len(order), len(nodes), reach))
        self.results = None
        self.helper.update_probe_points([list(nodes[k]) for k in order], 3)
        self.helper.use_xy_offsets(True)
        self.helper.start_probe(gcmd)
        # Probing has ended. Build the mesh only once nothing is moving:
        # a long calculation is then harmless.
        self.printer.lookup_object('toolhead').wait_moves()
        p, results = self.pending, self.results
        self.pending = self.results = None
        if p is not None and results is not None:
            self._build(p, results)

    def _finalize(self, results):
        # Called by Klipper's probing helper with the next move already timed:
        # keep this instant, only store the results.
        self.results = list(results)
        return None

    def _build(self, p, results):
        order = p['order']
        if len(results) != len(order):
            raise self.gcode.error('AUTO_TRIM_SHAPE_MESH: %d results for %d points' % (len(results), len(order)))
        measured = {}
        for k, r in zip(order, results):
            measured[k] = float(r.bed_z if hasattr(r, 'bed_z') else r[2])
        bed_mesh = self.printer.lookup_object('bed_mesh')
        base = None
        try:
            base = self._base(bed_mesh, p['base'])
        except Exception:
            logging.exception('auto_trim_shape_mesh: saved mesh %s', p['base'])
        params = p['params']
        dense = None
        if base is not None and self.dense_output != 'off':
            profile = self._profile(bed_mesh, p['base'])
            lo = (params['min_x'], params['min_y']); hi = (params['max_x'], params['max_y'])
            spacing = max((hi[0] - lo[0]) / (p['nx'] - 1), (hi[1] - lo[1]) / (p['ny'] - 1))
            probed = [(p['nodes'][k][0], p['nodes'][k][1], z) for k, z in measured.items()]
            dense = dense_from_base(profile['points'], profile['mesh_params'], lo, hi, probed, base,
                                    self.local_reach or .5 * spacing, (p['nx'], p['ny']))
        if dense is not None:
            matrix, info = dense['matrix'], dense['info']
            params = dict(params)
            params.update(min_x=dense['lo'][0], max_x=dense['hi'][0], min_y=dense['lo'][1], max_y=dense['hi'][1],
                          x_count=dense['nx'], y_count=dense['ny'])
            # keep Klipper's interpolation at most 41 points per axis: the
            # configured mesh_pps (5 on zMod) on a 21 x 21 grid would mean
            # 121 x 121 points, and large interpolations have stopped AD5X
            # printers with "Timer too close"
            params['mesh_x_pps'], params['mesh_y_pps'] = (
                dense_pps(params.get('mesh_x_pps', 2), dense['nx']), dense_pps(params.get('mesh_y_pps', 2), dense['ny']))
            if max(params['mesh_x_pps'], params['mesh_y_pps']) == 0:
                params['algo'] = 'direct'
            elif params.get('algo') in ('lagrange', 'direct') and max(dense['nx'], dense['ny']) > 6:
                params['algo'] = 'bicubic'
            info['grid'] = (dense['nx'], dense['ny'])
        else:
            matrix, info = fill_matrix(p['nodes'], p['nx'], p['ny'], measured, base)
        zmesh = bed_mesh_module.ZMesh(params, self.profile_name)
        zmesh.build_mesh(matrix)
        bed_mesh.set_mesh(zmesh)
        filled = (dense['nx'] * dense['ny'] - len(measured)) if dense is not None else len(p['nodes']) - len(measured)
        self.last = dict(version=VERSION, probed=len(measured), points=len(p['nodes']), filled=filled,
                         grid=list(info.pop('grid', (p['nx'], p['ny']))), reach=round(p['reach'], 1), base_profile=p['base'] if base else None,
                         dense_output=dense is not None,
                         **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items()})
        if base is not None:
            if dense is not None:
                self.gcode.respond_info(
                    "AUTO TRIM SHAPE MESH: probed %d points; final mesh %dx%d on the saved mesh '%s' grid (its hills and valleys), aligned by the probes (shift %+.3f mm, local differences %.3f mm, largest %.3f mm)"
                    % (len(measured), dense['nx'], dense['ny'], p['base'], info['shift'], info['residual_sd'], info['residual_max']))
            else:
                self.gcode.respond_info(
                    "AUTO TRIM SHAPE MESH: probed %d points, filled %d from the saved mesh '%s' (shift %+.3f mm, residual %.3f mm, largest %.3f mm)"
                    % (len(measured), filled, p['base'], info['shift'], info['residual_sd'], info['residual_max']))
            # The largest mismatch: one place where the saved mesh is clearly
            # off means it is out of date (probe scatter alone stays well below)
            if info['residual_max'] > self.max_residual:
                self.gcode.respond_info(
                    "!! AUTO TRIM SHAPE MESH: the saved mesh '%s' no longer matches the bed (off by up to %.3f mm, limit %.3f): refresh it with AUTO_TRIM_MESH_CALIBRATE"
                    % (p['base'], info['residual_max'], self.max_residual))
        else:
            self.gcode.respond_info(
                "AUTO TRIM SHAPE MESH: probed %d points, filled %d from the probed points (no saved mesh '%s'; AUTO_TRIM_MESH_CALIBRATE makes one)"
                % (len(measured), filled, p['base']))
        return None

    def get_status(self, eventtime):
        return dict(version=VERSION, last=self.last)


def load_config(config):
    return ShapeMesh(config)
