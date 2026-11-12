"""Execute unchanged classes from the supplied Klipper source, without hardware."""
import ast
import collections
import logging
import math
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]

def source_classes(filename, names):
    path = ROOT / 'reference' / filename
    tree = ast.parse(path.read_text(), filename=str(path))
    selected = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))
                and n.name in names]
    if {n.name for n in selected} != set(names):
        raise AssertionError('Reference source is missing required definitions')
    scope = dict(math=math, logging=logging, collections=collections)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), scope)
    return scope

BM = source_classes('bed_mesh.py', ['BedMesh', 'MoveSplitter', 'ZMesh',
                                    'isclose', 'constrain', 'lerp'])
GM = source_classes('gcode_move.py', ['GCodeMove'])['GCodeMove']

class Toolhead:
    def __init__(self):
        self.positions = []
        self.position = [0., 0., 1., 0.]
    def move(self, pos, speed):
        self.position = list(pos)
        self.positions.append((list(pos), speed))
    def get_position(self):
        return list(self.position)

class Config:
    def getfloat(self, name, default, **limits):
        return default

class Command:
    error = RuntimeError
    def __init__(self, **params):
        self.params = params
    def get_command_parameters(self):
        return self.params

class SuppliedKlipperTests(unittest.TestCase):
    def fixture(self, points=3, algo='direct'):
        params = dict(min_x=0., max_x=200., min_y=0., max_y=200.,
                      x_count=points, y_count=points,
                      mesh_x_pps=0 if algo=='direct' else 2,
                      mesh_y_pps=0 if algo=='direct' else 2,
                      algo=algo, tension=.2)
        mesh = BM['ZMesh'](params, 'software-test')
        # A 0.2 mm sloped surface, sampled at nodes.
        mesh.build_mesh([[.2*x/(points-1) for x in range(points)]
                         for y in range(points)])
        th = Toolhead()
        bm = BM['BedMesh'].__new__(BM['BedMesh'])
        bm.toolhead = th
        bm.gcode = types.SimpleNamespace(error=RuntimeError)
        bm.z_mesh = mesh
        bm.last_position = [0., 0., 1., 0.]
        bm.fade_start = bm.fade_end = bm.FADE_DISABLE
        bm.fade_dist = -1.
        bm.fade_target = bm.tool_offset = 0.
        bm.log_fade_complete = False
        bm.splitter = BM['MoveSplitter'](Config(), bm.gcode)
        bm.splitter.initialize(mesh, 0.)
        gm = GM.__new__(GM)
        gm.printer = types.SimpleNamespace(lookup_object=lambda name, default=None: th)
        gm.move_transform = None
        gm.axis_map = dict(X=0, Y=1, Z=2, E=3)
        gm.absolute_coord = gm.allow_absolute_extrude = True
        gm.extrude_factor = 1.
        gm.speed_factor = 1./60.
        gm.speed = 50.
        gm.base_position = [0., 0., 0., 0.]
        gm.last_position = [0., 0., 1., 0.]
        gm.set_move_transform(bm)
        return gm, bm, th

    def test_actual_g1_dispatch_to_mesh_and_toolhead(self):
        gm, bm, th = self.fixture()
        gm.cmd_G1(Command(X=200, Y=0, Z=1, E=5, F=3000))
        self.assertEqual(gm.last_position[2], 1.)
        self.assertAlmostEqual(th.position[2], 1.2)
        self.assertGreater(len(th.positions), 2)
        self.assertEqual(th.position[3], 5.)
        self.assertTrue(all(speed == 50 for pos, speed in th.positions))

    def test_native_mesh_follows_08_mm_variation_without_clipping(self):
        gm, bm, th = self.fixture()
        bm.z_mesh.build_mesh([[-3.6 + .4*x for x in range(3)]
                              for y in range(3)])
        gm.cmd_G1(Command(X=0, Y=0, Z=10))
        low = th.position[2]
        gm.cmd_G1(Command(X=200, Y=200, Z=10))
        high = th.position[2]
        self.assertAlmostEqual(low, 6.4)
        self.assertAlmostEqual(high, 7.2)
        self.assertAlmostEqual(high-low, .8)
        gm.cmd_G1(Command(X=0, Y=0, Z=10))
        self.assertAlmostEqual(th.position[2], low)

    def test_timer_during_native_split_submission_does_not_report_false_failure(self):
        from test_mesh_diagnostics import MeshAuditTests
        audit, objects, reactor = MeshAuditTests().fixture()
        gm, bm, th = self.fixture()
        th.get_kinematics = objects['toolhead'].get_kinematics
        objects['toolhead'], objects['bed_mesh'] = th, bm
        objects['gcode_move'].move_transform = bm
        objects['gcode_move'].move_with_transform = bm.move
        native_move = th.move
        def timer_inside_submission(pos, speed):
            native_move(pos, speed)
            # Model a reactor timer at the yield in Toolhead.move, before
            # BedMesh.move returns and advances its last_position.
            audit.samples.append(audit.snapshot(0))
        th.move = timer_inside_submission
        for x in (60, 120, 200):
            gm.cmd_G1(Command(X=x, Z=1))
            audit.samples.append(audit.snapshot(0))
        stale = [s for s in audit.samples if not s['comparable']]
        self.assertTrue(stale)
        self.assertGreater(max(abs(s['error']) for s in stale), .005)
        self.assertEqual(len([s for s in audit.samples if s['comparable']]), 3)
        audit._finish()
        text = '\n'.join(objects['gcode'].messages)
        self.assertIn('VERIFIED', text)
        self.assertNotIn('does NOT MATCH', text)

    def test_cleared_mesh_suppresses_correction(self):
        gm, bm, th = self.fixture()
        bm.z_mesh = None
        gm.cmd_G1(Command(X=200, Z=1))
        self.assertEqual(th.position[2], 1.)

    def test_disabled_fade_keeps_full_compensation_at_high_z(self):
        gm, bm, th = self.fixture()
        gm.cmd_G1(Command(X=200, Z=25))
        self.assertAlmostEqual(th.position[2], 25.2)

    def test_explicit_fade_removes_shape_above_end(self):
        gm, bm, th = self.fixture()
        bm.fade_start, bm.fade_end, bm.fade_dist = 1., 10., 9.
        bm.fade_target = .1
        gm.cmd_G1(Command(X=200, Z=11))
        self.assertAlmostEqual(th.position[2], 11.1)

    def test_actual_nine_by_nine_bicubic_mesh(self):
        gm, bm, th = self.fixture(9, 'bicubic')
        gm.cmd_G1(Command(X=112.5, Y=87.5, Z=.2))
        self.assertAlmostEqual(th.position[2], .3125)

    def test_splitter_commands_hill_inside_move_with_equal_end_heights(self):
        gm, bm, th = self.fixture()
        bm.z_mesh.build_mesh([[0., .2, 0.] for y in range(3)])
        gm.cmd_G1(Command(X=200, Y=0, Z=1))
        self.assertAlmostEqual(th.position[2], 1.)
        self.assertGreater(max(pos[2] for pos, speed in th.positions), 1.17)

    def test_bypassed_callback_leaves_loaded_mesh_unused(self):
        gm, bm, th = self.fixture()
        gm.move_with_transform = th.move
        gm.cmd_G1(Command(X=200, Z=1))
        self.assertIsNotNone(bm.z_mesh)
        self.assertEqual(th.position[2], 1.)

if __name__ == '__main__':
    unittest.main(verbosity=2)
