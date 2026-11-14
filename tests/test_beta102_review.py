"""Audit regressions, with the unmodified supplied native G-code move class."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import test_capture as capture
from test_first_print_auto import ArmCommand
from test_gcode_context import gcode
from deep_calibration_gcode import parse_file

spec = importlib.util.spec_from_file_location('native_gcode_move_reference',
    Path(__file__).parent/'native_reference/gcode_move.py')
native_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(native_module)


def native_move():
    m = native_module.GCodeMove.__new__(native_module.GCodeMove)
    m.absolute_coord = m.allow_absolute_extrude = True
    m.base_position = [0., 0., 0., 0.]; m.last_position = [0., 0., .2, 0.]
    m.homing_position = [0., 0., 0., 0.]; m.axis_map = {'X':0,'Y':1,'Z':2,'E':3}
    m.speed_factor = 1./60; m.extrude_factor = 1.; m.speed = 40.; m.Coord = list
    m.move_with_transform = lambda pos, speed: None
    return m


class AuditRegressions(unittest.TestCase):
    def setUp(self):
        self.f = capture.CaptureTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.c = self.f.cell; self.s = self.c.slicer; self.s.enabled = True
        self.path = Path(self.f.temp.name)/'print.gcode'; self.path.write_text(gcode())
        self.s.snapshot = parse_file(str(self.path)); self.s.state = 'ready'; self.s.path = str(self.path)
        self.segment = next(iter(self.s.snapshot['segments'].values()))
        self.c.armed = {'test':True}
        self.f.objects['virtual_sdcard'] = SimpleNamespace(cmd_from_sd=True,file_position=self.segment['offset'])
        self.f.objects['toolhead'].register_lookahead_callback = lambda cb: cb(10.)
        self.native = native_move(); self.native.allow_absolute_extrude = False
        self.f.objects['gcode_move'] = self.native

    def observe(self):
        return self.s.observe('G1', self.native.cmd_G1, ArmCommand(X='100', E='2.5', F='2400'))

    def test_relative_xyz_also_makes_e_relative_with_m82_in_native_klipper(self):
        text = gcode(extra='G92 E50\nM82\nG91\n')
        self.path.write_text(text); p = parse_file(str(self.path)); segment = next(iter(p['segments'].values()))
        self.native.last_position = [0.,0.,.2,50.]
        self.native.cmd_M82(ArmCommand()); self.native.cmd_G91(ArmCommand())
        self.native.cmd_G1(ArmCommand(X='100',E='2.5',F='2400'))
        self.assertAlmostEqual(segment['delta_e'], self.native.last_position[3]-50.)

    def test_modal_mismatch_is_excluded_without_changing_native_behavior(self):
        self.native.absolute_coord = False
        self.observe()
        self.assertEqual(self.native.last_position, [100.,0.,.2,2.5])
        self.assertFalse(self.s.timeline[-1]['source_valid'])

    def test_hidden_macro_coordinate_change_cannot_pass_attribution(self):
        self.native.last_position[0] = 20.
        self.observe()
        self.assertFalse(self.s.timeline[-1]['source_valid'])

    def test_matching_native_move_is_attributable(self):
        self.observe()
        self.assertTrue(self.s.timeline[-1]['source_valid'])

    def test_long_queued_move_is_not_truncated_to_five_seconds(self):
        self.f.objects['toolhead'].status.update(print_time=30.,estimated_print_time=10.)
        self.assertEqual(self.c._queue_lead(10.), 20.)

    def test_force_limit_relief_is_not_a_learnable_fitted_result(self):
        self.c.knee = dict(original=0.,offset=-.1,steps=[],key='test',margin=.01,
                           margin_src='test',margin_fixed=None,cfg={'step':.01})
        self.c._knee_move = lambda value: None
        self.c._knee_stop(0.,{'gcode':{}},'force limit',target=-.09,knee=-.1)
        self.assertIsNone(self.c.knee_last)

    def test_closed_sd_handle_does_not_drop_still_executing_queued_segments(self):
        self.c.active = True
        self.f.objects['virtual_sdcard'] = SimpleNamespace(file_path=lambda:None)
        self.s.timeline.append(dict(start=0.,end=20.))
        self.s.request()
        self.assertEqual(self.s.state, 'ready')
        self.assertIsNotNone(self.s.snapshot)
        self.assertEqual(len(self.s.timeline), 1)


    def test_relative_extrusion_after_tool_selection_does_not_need_absolute_e_origin(self):
        self.path.write_text(gcode(extra='T0\n'))
        parsed = parse_file(str(self.path)); seg = next(iter(parsed['segments'].values()))
        self.assertAlmostEqual(seg['delta_e'], 2.5)
        self.assertTrue(seg['eligible'])

    def test_missing_gate_flags_are_unknown_not_assumed_disabled(self):
        self.s.snapshot['settings'].pop('flush_into_objects')
        self.s.timeline.append(dict(start=0.,end=20.,source_valid=True,segment=self.segment))
        result = self.s.sample(1.,dict(method='native_trapq_at_host_receipt',print_time=1.),{})
        self.assertFalse(result['eligible'])
        self.assertIn('missing_eligibility_setting:flush_into_objects', result['reasons'])

    def test_post_move_coordinate_rewrite_cannot_be_attributed(self):
        def rewritten(gcmd):
            self.native.cmd_G1(gcmd)
            self.native.last_position[0] += 5.
        self.s.observe('G1', rewritten, ArmCommand(X='100',E='2.5',F='2400'))
        self.assertFalse(self.s.timeline[-1]['source_valid'])

    def test_inherited_feed_mismatch_cannot_be_attributed(self):
        self.path.write_text(gcode().replace('G1 X100 E2.5 F2400', 'G1 X100 E2.5'))
        self.s.snapshot = parse_file(str(self.path)); seg=next(iter(self.s.snapshot['segments'].values()))
        self.f.objects['virtual_sdcard'].file_position = seg['offset']
        self.native.speed = 20.
        self.s.observe('G1', self.native.cmd_G1, ArmCommand(X='100',E='2.5'))
        self.assertFalse(self.s.timeline[-1]['source_valid'])


    def test_pinned_orca_duplicate_plate_coordinates_are_valid_and_retained(self):
        text=gcode().replace('; CONFIG_BLOCK_END', '; wipe_tower_x = 165.000\n; wipe_tower_x = 165,170\n; wipe_tower_y = 175.000\n; wipe_tower_y = 175,180\n; CONFIG_BLOCK_END')
        self.path.write_text(text)
        parsed = parse_file(str(self.path))
        self.assertTrue(parsed['eligible'], parsed['issues'])
        self.assertEqual(parsed['settings']['wipe_tower_x'], '165,170')
        self.assertEqual(parsed['setting_variants']['wipe_tower_x'], ['165.000','165,170'])
        self.assertEqual(parsed['emitted_plate_coordinates']['wipe_tower_x'], 165.)

    def test_unrelated_duplicate_settings_remain_invalid(self):
        text=gcode().replace('; CONFIG_BLOCK_END', '; filament_flow_ratio = 0.9\n; CONFIG_BLOCK_END')
        self.path.write_text(text)
        self.assertIn('conflicting_setting:filament_flow_ratio', parse_file(str(self.path))['issues'])


    def test_actual_orca_numeric_vectors_use_commas_and_keep_selected_material(self):
        self.path.write_text(gcode(header='; filament: 2\n', settings={
            'filament_type':'PLA;PETG','filament_diameter':'1.75,2.85','filament_flow_ratio':'1,0.97'}))
        parsed = parse_file(str(self.path))
        self.assertTrue(parsed['eligible'], parsed['issues'])
        self.assertEqual(parsed['settings']['filament_diameter'], '1.75,2.85')
        self.s.snapshot=parsed
        seg=next(iter(parsed['segments'].values()))
        self.s.timeline.append(dict(start=0.,end=20.,segment=seg,source_valid=True))
        sample=self.s.sample(1.,dict(method='native_trapq_at_host_receipt',print_time=1.),{})
        self.assertEqual(sample['material'], 'PETG')
        self.assertEqual(sample['filament_diameter'], 2.85)

    def test_material_profile_identity_is_not_discarded_as_a_cosmetic_name(self):
        self.path.write_text(gcode(settings={'filament_settings_id':'Brand A PLA'}))
        a=parse_file(str(self.path))
        self.path.write_text(gcode(settings={'filament_settings_id':'Brand B PLA'}))
        b=parse_file(str(self.path))
        self.assertNotEqual(a['physics_sha256'],b['physics_sha256'])


if __name__ == '__main__': unittest.main()
