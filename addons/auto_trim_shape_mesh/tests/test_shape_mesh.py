import math, os, re, random, sys, unittest
from types import SimpleNamespace as S
sys.path.insert(0, os.path.dirname(__file__))
import shutil
shutil.copy(os.path.join(os.path.dirname(__file__), '..', 'auto_trim_shape_mesh.py'), os.path.join(os.path.dirname(__file__), 'kextras', 'auto_trim_shape_mesh.py'))
from kextras import auto_trim_shape_mesh as sm, bed_mesh, probe as fakeprobe

# A real part: Orca's outline of a side panel that runs diagonally across an
# AD5X bed (EXCLUDE_OBJECT_DEFINE POLYGON from the print file)
POLYGON = [[7.31325,89.8349],[7.75021,88.3667],[61.0775,9.56183],[62.2827,8.60942],[63.8013,8.3784],[65.2352,8.92936],[70.4287,12.7385],[90.4517,28.5331],[109.978,45.8163],[128.65,64.3637],[146.388,84.1588],[162.655,104.573],[177.588,125.679],[191.181,147.398],[204.067,170.891],[215.002,193.862],[216.005,196.147],[216.242,197.623],[215.601,199.23],[213.736,200.48],[180.74,207.345],[178.891,206.67],[8.69493,92.4552],[7.65814,91.3275]]
def user_polygon():
    return [tuple(p) for p in POLYGON]

def bed_shape(x, y):         # the plate: a dome and a slight tilt (mm)
    return -3.24 + 0.06 * math.exp(-((x - 110) ** 2 + (y - 105) ** 2) / 6000.) + 0.0004 * x - 0.0002 * y

def full_profile(fn, counts=(9, 9), lo=(0., 0.), hi=(215., 215.)):
    nodes = sm.grid_nodes(lo, hi, *counts)
    pts = [[fn(*nodes[j * counts[0] + i]) for i in range(counts[0])] for j in range(counts[1])]
    return dict(points=pts, mesh_params=dict(min_x=lo[0], max_x=hi[0], min_y=lo[1], max_y=hi[1], x_count=counts[0], y_count=counts[1],
                                             mesh_x_pps=2, mesh_y_pps=2, algo='bicubic', tension=.2))

class Cmd:
    def __init__(self, **p): self.params = {k.upper(): str(v) for k, v in p.items()}; self.out = []
    def get(self, k, d=None): return self.params.get(k, d)
    def get_float(self, k, d=None, **kw): return float(self.params[k]) if k in self.params else d
    def respond_info(self, m): self.out.append(m)
    def error(self, m): return RuntimeError(m)

class Fixture:
    def __init__(self, polygons, profiles=None, mesh_min=(0., 0.), mesh_max=(215., 215.), counts=(9, 9)):
        self.messages = []; self.active = None; self.commands = {}; self.events = []
        cfg = dict(x_count=counts[0], y_count=counts[1], mesh_x_pps=2, mesh_y_pps=2, algo='bicubic', tension=.2)
        bmc = S(mesh_config=dict(cfg), orig_config=dict(cfg, mesh_min=mesh_min, mesh_max=mesh_max),
                probe_mgr=S(get_zero_ref_mode=lambda: bed_mesh.ZrefMode.DISABLED))
        self.bed_mesh = S(bmc=bmc, pmgr=S(get_profiles=lambda: profiles or {}), set_mesh=self._set)
        objects = dict(gcode=S(register_command=lambda n, f, desc=None: self.commands.__setitem__(n, f),
                               respond_info=self.messages.append, error=RuntimeError),
                       bed_mesh=self.bed_mesh,
                       toolhead=S(wait_moves=lambda: self.events.append('wait_moves')),
                       exclude_object=S(get_status=lambda t: dict(objects=[dict(name='o%d' % i, polygon=[list(p) for p in poly]) for i, poly in enumerate(polygons)])))
        printer = S(lookup_object=lambda n, d=None: objects.get(n, d), get_reactor=lambda: S(monotonic=lambda: 0.))
        config = S(get_printer=lambda: printer, getfloat=lambda n, d, **k: d, get=lambda n, d=None: d,
                   getsection=lambda n: S(getfloat=lambda o, d, **k: d), get_name=lambda: 'auto_trim_shape_mesh')
        self.module = sm.ShapeMesh(config)
    def _set(self, mesh): self.active = mesh; self.events.append('set_mesh')
    def run(self, surface, **params):
        fakeprobe.SURFACE['fn'] = surface; fakeprobe.SURFACE['log'] = []
        cmd = Cmd(**params); self.commands['AUTO_TRIM_SHAPE_MESH'](cmd)
        return cmd

class ShapeMeshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.poly = user_polygon()

    def test_grid_matches_the_kamp_mesh_of_the_print(self):
        lo, hi, nx, ny = sm.adaptive_grid([self.poly], (0., 0.), (215., 215.), (9, 9), 3.)
        # the console showed KAMP's (3.6633, 4.5984) - (215.0, 211.585), 9 x 9;
        # zMod's KAMP also jitters its edges by up to 3 mm ("points fuzzed")
        self.assertEqual((nx, ny), (9, 9))
        for got, kamp in ((lo[0], 3.6633), (lo[1], 4.5984), (hi[0], 215.0), (hi[1], 211.585)):
            self.assertLessEqual(abs(got - kamp), 3.)

    def test_probes_only_the_points_near_the_part(self):
        f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
        f.run(lambda x, y: bed_shape(x, y))
        pts = fakeprobe.SURFACE['log'][0]['points']
        self.assertTrue(30 <= len(pts) <= 50, len(pts))
        self.assertEqual(len(set(pts)), len(pts))
        for x, y in pts:   # every probed point within one grid spacing of the part
            self.assertLessEqual(sm.polygon_distance(x, y, self.poly), (215 - 3.6633) / 8 + 1e-6)
        print("\n    your part: %d of 81 points probed" % len(pts))

    def test_mesh_under_the_part_matches_the_true_bed(self):
        # The bed has moved since the saved mesh: shifted 0.04 mm and tilted
        rng = random.Random(1)
        now = lambda x, y: bed_shape(x, y) + 0.04 + 0.0001 * x - 0.00005 * y
        f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
        f.run(lambda x, y: now(x, y) + rng.gauss(0, .002))
        shape = f.active
        g = Fixture([self.poly])                       # reference: probe all 81 points
        g.module.reach_factor = 99.
        g.run(lambda x, y: now(x, y) + rng.gauss(0, .002))
        full = g.active
        xs = [p[0] for p in self.poly]; ys = [p[1] for p in self.poly]
        err_shape = err_full = 0.
        for i in range(60):
            for j in range(60):
                x = min(xs) + (max(xs) - min(xs)) * i / 59; y = min(ys) + (max(ys) - min(ys)) * j / 59
                if sm.polygon_distance(x, y, self.poly) == 0.:
                    err_shape = max(err_shape, abs(shape.calc_z(x, y) - now(x, y)))
                    err_full = max(err_full, abs(full.calc_z(x, y) - now(x, y)))
        print("\n    under the part: shape mesh max error %.4f mm, full 81-point mesh %.4f mm" % (err_shape, err_full))
        self.assertLess(err_shape, 0.012)
        self.assertLess(err_shape, err_full + 0.006)
        self.assertEqual(shape.get_profile_name(), 'shape')
        self.assertIn('filled', f.messages[-1]); self.assertIn("saved mesh 'auto'", f.messages[-1])

    def test_probed_points_go_into_the_matrix_unchanged_and_in_klipper_order(self):
        f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
        f.run(lambda x, y: round(x, 3) * 1000 + round(y, 3) / 1000)    # z encodes the position
        m = f.active.get_probed_matrix(); p = f.module.last
        nodes = sm.grid_nodes(*sm.adaptive_grid([self.poly], (0., 0.), (215., 215.), (9, 9), 3.))
        for x, y in fakeprobe.SURFACE['log'][0]['points']:
            k = nodes.index((x, y)); j, i = divmod(k, 9)
            self.assertAlmostEqual(m[j][i], round(round(x, 3) * 1000 + round(y, 3) / 1000, 6), 4)
        self.assertEqual(p['probed'] + p['filled'], 81)

    def test_without_a_saved_mesh_the_rest_is_filled_from_the_probed_points(self):
        f = Fixture([self.poly])
        f.run(bed_shape)
        self.assertIn('from the probed points', f.messages[-1])
        # far corner, nothing printed: a value within the probed range, no wild extrapolation
        probed = [bed_shape(x, y) for x, y in fakeprobe.SURFACE['log'][0]['points']]
        z = f.active.get_probed_matrix()[-1][0]
        self.assertTrue(min(probed) - 1e-6 <= z <= max(probed) + 1e-6, (z, min(probed), max(probed)))

    def test_warns_when_the_saved_mesh_no_longer_matches(self):
        # the plate has changed under the part since the saved mesh
        warped = lambda x, y: bed_shape(x, y) + (0.12 if 90 < x < 160 and 60 < y < 140 else 0.)
        f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
        f.run(warped)
        self.assertTrue(any('no longer matches' in m for m in f.messages), f.messages)

    def test_no_false_alarm_from_ordinary_probe_scatter(self):
        # scatter like the noisier AD5X's (0.008 mm), saved mesh still right
        for seed in range(5):
            rng = random.Random(seed)
            f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
            f.run(lambda x, y: bed_shape(x, y) + 0.02 + rng.gauss(0, .008))
            self.assertFalse(any('no longer matches' in m for m in f.messages), (seed, f.messages))

    def test_probe_speed_and_other_parameters_reach_the_probe(self):
        f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
        f.run(bed_shape, PROBE_SPEED=1.0, PROFILE='auto')
        self.assertEqual(fakeprobe.SURFACE['log'][0]['params']['PROBE_SPEED'], '1.0')

    def test_mesh_is_built_after_the_moves_not_inside_finalize(self):
        # On the printer, building inside Klipper's finalize callback (with
        # the next move already timed) shut it down with "Timer too close"
        f = Fixture([self.poly], dict(auto=full_profile(bed_shape)))
        built_in_finalize = []
        orig = f.module._finalize
        def spy(results):
            r = orig(results); built_in_finalize.append(f.active is not None); return r
        f.module._finalize = spy
        f.module.helper.finalize_callback = spy
        f.run(bed_shape)
        self.assertEqual(built_in_finalize, [False])
        self.assertEqual(f.events, ['wait_moves', 'set_mesh'])
        self.assertIsNotNone(f.active)

    def test_serpentine_order(self):
        order = sm.serpentine([0, 1, 2, 3, 4, 5, 6, 7, 8], 3)
        self.assertEqual(order, [0, 1, 2, 5, 4, 3, 6, 7, 8])

    def test_small_part_gets_a_small_grid_like_kamp(self):
        sq = [(100., 100.), (130., 100.), (130., 120.), (100., 120.)]
        lo, hi, nx, ny = sm.adaptive_grid([sq], (0., 0.), (215., 215.), (9, 9), 3.)
        self.assertEqual((nx, ny), (3, 3))
        f = Fixture([sq], dict(auto=full_profile(bed_shape)))
        f.run(bed_shape)
        self.assertEqual(f.active.get_mesh_params()['algo'], 'lagrange')     # bicubic needs 4 points
        self.assertEqual(len(fakeprobe.SURFACE['log'][0]['points']), 9)

    def test_no_labelled_objects_is_an_error(self):
        f = Fixture([])
        with self.assertRaises(RuntimeError): f.run(bed_shape)

    def test_zero_reference_is_refused(self):
        f = Fixture([self.poly])
        f.bed_mesh.bmc.probe_mgr = S(get_zero_ref_mode=lambda: bed_mesh.ZrefMode.IN_MESH)
        with self.assertRaises(RuntimeError): f.run(bed_shape)

    def test_plane_fit(self):
        pts = [(x, y, 0.1 + 0.002 * x - 0.001 * y) for x in (0, 50, 100) for y in (0, 70)]
        a, b, c = sm.fit_plane(pts)
        self.assertAlmostEqual(a, .1, 6); self.assertAlmostEqual(b, .002, 6); self.assertAlmostEqual(c, -.001, 6)

if __name__ == '__main__':
    unittest.main()
