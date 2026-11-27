# 1.2.0: hills and valleys finer than the probe grid come from a dense base mesh
import math
import os
import random
import sys
import unittest
sys.path.insert(0, os.path.dirname(__file__))
import shutil
shutil.copy(os.path.join(os.path.dirname(__file__), '..', 'auto_trim_shape_mesh.py'), os.path.join(os.path.dirname(__file__), 'kextras', 'auto_trim_shape_mesh.py'))
from test_shape_mesh import Fixture, full_profile, bed_shape
from kextras import auto_trim_shape_mesh as sm, probe as fakeprobe

def bump(x, y, cx, cy, height, width):
    return height * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * width ** 2))

def plate(x, y):        # hills and valleys about 7 mm across, between probe points
    return bed_shape(x, y) + bump(x, y, 75, 75, .05, 6.) + bump(x, y, 98, 58, -.04, 6.) + bump(x, y, 60, 112, .03, 5.)

def today(x, y):
    return plate(x, y) + .03 + .0002 * x - .0001 * y

PART = [(40., 40.), (130., 40.), (130., 130.), (40., 130.)]

def error_under_part(mesh, truth):
    worst = 0.
    for i in range(46):
        for j in range(46):
            x, y = 40 + 90 * i / 45., 40 + 90 * j / 45.
            worst = max(worst, abs(mesh.calc_z(x, y) - truth(x, y)))
    return worst


class DenseBaseTests(unittest.TestCase):
    def run_mesh(self, truth, dense=True, base_counts=(21, 21), noise=.002):
        rng = random.Random(3)
        f = Fixture([PART], dict(auto=full_profile(plate, counts=base_counts)))
        if not dense:
            f.module.dense_output = 'off'
        f.run(lambda x, y: truth(x, y) + rng.gauss(0, noise))
        return f

    def test_dense_base_captures_hills_and_valleys(self):
        f = self.run_mesh(today)
        g = self.run_mesh(today, dense=False)
        dense_err, legacy_err = error_under_part(f.active, today), error_under_part(g.active, today)
        # the base mesh's own limit: how well 21 x 21 points describe the plate
        from kextras import bed_mesh
        prof = full_profile(plate, counts=(21, 21)); base = bed_mesh.ZMesh(dict(prof['mesh_params']), 'b'); base.build_mesh(prof['points'])
        base_err = error_under_part(base, plate)
        print("\n    under the part: dense-base mesh %.4f mm, previous shape mesh %.4f mm, the base's own limit %.4f mm" % (dense_err, legacy_err, base_err))
        self.assertTrue(f.module.last['dense_output'])
        self.assertLess(dense_err, base_err + .006)              # as good as the base allows, plus probe noise
        self.assertGreater(legacy_err, 2.5 * dense_err)
        self.assertIn('saved mesh', f.messages[-1]); self.assertIn('grid', f.messages[-1])

    def test_new_local_change_near_probes_is_picked_up(self):
        f0 = self.run_mesh(today, noise=0.)
        probes = fakeprobe.SURFACE['log'][0]['points']
        px, py = min(probes, key=lambda p: (p[0] - 85) ** 2 + (p[1] - 85) ** 2)
        changed = lambda x, y: today(x, y) + bump(x, y, px, py, .02, 15.)
        f = self.run_mesh(changed, noise=0.)
        self.assertLess(abs(f.active.calc_z(px, py) - changed(px, py)), .006)

    def test_base_not_denser_keeps_the_previous_behaviour(self):
        f = self.run_mesh(today, base_counts=(9, 9))
        self.assertFalse(f.module.last['dense_output'])

    def test_final_grid_covers_the_part_on_base_points(self):
        f = self.run_mesh(today)
        params = f.active.get_mesh_params()
        self.assertLessEqual(params['min_x'], 40.); self.assertGreaterEqual(params['max_x'], 130.)
        step = 215. / 20
        self.assertAlmostEqual(params['min_x'] / step, round(params['min_x'] / step), places=6)  # on base grid points
        self.assertEqual(params['algo'], 'bicubic')


    def test_interpolation_capped_at_41_points_per_axis(self):
        # zMod's mesh_pps 5 on a 21 x 21 dense grid would be 121 x 121 points;
        # large interpolations have stopped AD5X printers ("Timer too close")
        rng = random.Random(5)
        whole = [(5., 5.), (210., 5.), (210., 210.), (5., 210.)]
        f = Fixture([whole], dict(auto=full_profile(plate, counts=(21, 21))))
        f.bed_mesh.bmc.mesh_config.update(mesh_x_pps=5, mesh_y_pps=5)
        f.run(lambda x, y: today(x, y) + rng.gauss(0, .002))
        self.assertTrue(f.module.last['dense_output'])
        self.assertEqual(f.module.last['grid'], [21, 21])
        self.assertLessEqual(f.active.mesh_x_count, 41); self.assertLessEqual(f.active.mesh_y_count, 41)

    def test_pps_rule(self):
        for configured, count, expected in ((5, 21, 1), (5, 41, 0), (2, 21, 1), (5, 9, 4), (2, 9, 2), (5, 7, 5), (5, 11, 3)):
            self.assertEqual(sm.dense_pps(configured, count), expected, (configured, count))
            if expected:
                self.assertLessEqual((count - 1) * (expected + 1) + 1, 41)


if __name__ == '__main__':
    unittest.main()
