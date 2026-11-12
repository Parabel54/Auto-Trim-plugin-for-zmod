"""Controlled motion command tests using supplied native G1/BedMesh classes.
Hardware completion and MCU counts are simulated; no physical printer used.
"""
import math
import types
import unittest
import test_mesh_diagnostics as diagnostics
from test_mesh_diagnostics import Gcmd
import test_mesh_native as native

class Command(Gcmd):
    def get_command_parameters(self): return self.kw
    def get_int(self, key, default=0): return int(self.kw.get(key, default))

class TravelTests(unittest.TestCase):
    def fixture(self):
        audit, objects, reactor = diagnostics.MeshAuditTests().fixture()
        gm, bm, th = native.SuppliedKlipperTests().fixture()
        gm.saved_states = {}
        gm.homing_position = [.3, .7, .699, 0.]
        gm.base_position = [.3, .7, .699, 0.]
        gm.absolute_coord = False
        gm.allow_absolute_extrude = False
        gm.last_position[3] = bm.last_position[3] = th.position[3] = 8.
        gm.Coord = lambda pos: list(pos)
        objects.update(gcode_move=gm, bed_mesh=bm, toolhead=th,
                       print_stats=types.SimpleNamespace(get_status=lambda t:{'state':'standby'}))
        self.status = dict(homed_axes='xyz', axis_minimum=[0,0,-10], axis_maximum=[215,215,220])
        th.get_status = lambda t: self.status
        self.waits = []
        th.wait_moves = lambda: self.waits.append(True)
        self.steps_offset = 0
        stepper = types.SimpleNamespace(get_name=lambda:'stepper_z',get_step_dist=lambda:.0025,
                                        get_mcu_position=lambda:round(th.position[2]/.0025)+self.steps_offset)
        th.get_kinematics = lambda: types.SimpleNamespace(get_steppers=lambda:[stepper])
        objects['motion_report'] = types.SimpleNamespace(get_status=lambda t:{'live_position':th.position})
        self.scripts = []
        def run_script(script):
            for line in script.splitlines():
                self.scripts.append(line)
                words = line.split(); name = words[0]
                if name == 'G1': params = {v[0]:v[1:] for v in words[1:]}
                else: params = dict(v.split('=',1) for v in words[1:])
                getattr(gm, 'cmd_'+name)(Command(**params))
        objects['gcode'].run_script_from_command = run_script
        return audit, objects, gm, bm, th

    def test_auto_route_native_g1_and_steps_with_offset_state_preserved(self):
        a,o,gm,bm,th=self.fixture(); cmd=Command()
        a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
        text='\n'.join(cmd.messages)
        self.assertIn('comparison PASSED',text)
        self.assertIn('predicted delta=+0.180000',text)
        self.assertIn('commanded delta=+72 steps (+0.180000 mm)',text)
        self.assertIn('commanded delta=-72 steps (-0.180000 mm)',text)
        self.assertFalse(gm.absolute_coord); self.assertFalse(gm.allow_absolute_extrude)
        self.assertEqual(gm.base_position,[.3,.7,.699,0.]); self.assertEqual(gm.homing_position,[.3,.7,.699,0.])
        self.assertEqual(th.position[3],8.); self.assertEqual(gm.last_position[3],8.)
        self.assertAlmostEqual(th.position[0],10.); self.assertTrue(10. <= th.position[1] <= 190.)
        self.assertAlmostEqual(bm.last_position[2],10.)
        self.assertFalse(a.travel_running)
        self.assertEqual(len([line for line in self.scripts if line.startswith('G1 ')]),4)
        self.assertFalse(any(word.startswith('E') for line in self.scripts if line.startswith('G1 ') for word in line.split()[1:]))
        self.assertEqual(len(self.waits),5)

    def test_explicit_points_and_height(self):
        a,o,gm,bm,th=self.fixture(); cmd=Command(X1=20,Y1=40,X2=80,Y2=100,HEIGHT=8,SPEED=15)
        a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
        self.assertIn('predicted delta=+0.060000','\n'.join(cmd.messages))
        self.assertAlmostEqual(th.position[2],8.02)

    def test_travel_comparison_accepts_08_mm_and_larger_measured_variation(self):
        for delta in (.8, 1.2):
            with self.subTest(delta=delta):
                a,o,gm,bm,th=self.fixture()
                # Retain raw negative contact-reference values as in the
                # supplied AD5X mesh. Interior X=10..190 spans delta mm.
                bm.z_mesh.build_mesh([[-3.6+delta*x*100./180. for x in range(3)]
                                      for y in range(3)])
                cmd=Command(X1=10,Y1=10,X2=190,Y2=190)
                a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
                text='\n'.join(cmd.messages)
                self.assertIn('predicted delta=%+.6f' % delta,text)
                self.assertIn('commanded delta=%+d steps' % round(delta/.0025),text)
                self.assertIn('commanded delta=%+d steps' % -round(delta/.0025),text)
                self.assertIn('comparison PASSED',text)

    def test_rejects_printing_paused_unhomed_and_active_calibration_without_motion(self):
        for scenario in ('printing','paused','unhomed','calibrating','tracing'):
            with self.subTest(scenario=scenario):
                a,o,gm,bm,th=self.fixture()
                if scenario in ('printing','paused'): o['print_stats'].get_status=lambda t:{'state':scenario}
                elif scenario=='unhomed': self.status['homed_axes']='xy'
                elif scenario=='calibrating': o['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE']=types.SimpleNamespace(get_status=lambda t:{'running':True})
                else: a.until=5
                with self.assertRaises(RuntimeError): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(Command())
                self.assertEqual(self.scripts,[])

    def test_invalid_parameters_bounds_and_mesh_fail_before_motion(self):
        cases=[dict(HEIGHT=math.nan),dict(SPEED=math.inf),dict(X1=20),dict(X1=0,Y1=10,X2=190,Y2=190),dict(X1=10,Y1=10,X2=10,Y2=10)]
        for case in cases:
            with self.subTest(case=case):
                a,o,gm,bm,th=self.fixture()
                with self.assertRaises(RuntimeError): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(Command(**case))
                self.assertEqual(self.scripts,[])
        for condition in ('missing','faded','skew','callback','clearance'):
            a,o,gm,bm,th=self.fixture()
            if condition=='missing': bm.z_mesh=None
            elif condition=='faded': bm.get_z_factor=lambda z:0.
            elif condition=='skew': gm.move_transform=object()
            elif condition=='callback': gm.move_with_transform=th.move
            else: bm.z_mesh.mesh_matrix=[[-20. for value in row] for row in bm.z_mesh.mesh_matrix]
            with self.assertRaises(RuntimeError): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(Command())
            self.assertEqual(self.scripts,[])

    def test_zero_skew_wrapper_allowed_but_nonzero_skew_rejected(self):
        for factor in (0.,.001):
            a,o,gm,bm,th=self.fixture()
            def move(self,pos,speed): self.next_transform.move(pos,speed)
            root=type('PrinterSkew',(),dict(move=move))()
            root.next_transform=bm; root.xy_factor=factor; root.xz_factor=root.yz_factor=0.
            gm.move_transform=root; gm.move_with_transform=root.move
            if factor:
                with self.assertRaises(RuntimeError): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(Command())
                self.assertEqual(self.scripts,[])
            else: a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(Command())

    def test_motion_error_restores_modes_and_does_not_report_pass(self):
        a,o,gm,bm,th=self.fixture(); native=th.move
        def fail_move(pos,speed):
            if pos[0]>100: raise RuntimeError('simulated motion rejection')
            native(pos,speed)
        th.move=fail_move; cmd=Command()
        with self.assertRaisesRegex(RuntimeError,'motion rejection'): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
        self.assertFalse(a.travel_running); self.assertFalse(gm.absolute_coord)
        self.assertTrue(self.scripts[-1].startswith('RESTORE_GCODE_STATE'))
        self.assertNotIn('comparison PASSED','\n'.join(cmd.messages))

    def test_endpoint_mismatch_stops_at_first_endpoint(self):
        a,o,gm,bm,th=self.fixture(); native=th.move
        def wrong_move(pos,speed):
            native(pos,speed); th.position[2]+=.03
        th.move=wrong_move; cmd=Command()
        with self.assertRaisesRegex(RuntimeError,'does NOT MATCH'): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
        self.assertFalse(a.travel_running); self.assertFalse(gm.absolute_coord)
        self.assertNotIn('comparison PASSED','\n'.join(cmd.messages))

    def test_wrong_step_delta_is_reported_separately_from_mesh_endpoint_match(self):
        a,o,gm,bm,th=self.fixture(); native=th.wait_moves
        def wait():
            native()
            if len(self.waits)==4: self.steps_offset=20
        th.wait_moves=wait; cmd=Command()
        with self.assertRaisesRegex(RuntimeError,'commanded Z travel does NOT MATCH'): a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
        self.assertIn('difference=+0.050000','\n'.join(cmd.messages))
        self.assertFalse(a.travel_running); self.assertFalse(gm.absolute_coord)

    def test_flat_route_warns_without_claiming_large_movement(self):
        a,o,gm,bm,th=self.fixture(); cmd=Command(X1=20,Y1=20,X2=20,Y2=180)
        a.cmd_DEEP_CALIBRATION_MESH_TRAVEL_TEST(cmd)
        self.assertIn('less than 0.01 mm','\n'.join(cmd.messages))
        self.assertIn('Physical bed travel is not measured','\n'.join(cmd.messages))

if __name__=='__main__': unittest.main()
