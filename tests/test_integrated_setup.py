"""Integrated package guards and calibration parameters, without printer hardware."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import test_capture as capture
import test_preparation as preparation
import test_mesh_diagnostics as diagnostics

class IntegratedSetupTests(unittest.TestCase):
    def test_single_main_section_bundles_its_macros_and_not_the_legacy_extra(self):
        cfg=(ROOT/'deep_calibration.cfg').read_text()
        self.assertEqual(cfg.count('[deep_calibration]'),1)
        self.assertIn('startup_integration: False',cfg)
        # Auto Trim is installed separately (3.9.9 or later), never bundled
        self.assertNotIn('[include auto_trim/',cfg)
        self.assertFalse((ROOT/'auto_trim').exists())
        self.assertIn('auto_capture: True',cfg)
        self.assertIn('[include deep_calibration_start.cfg]',cfg)
        self.assertNotIn('[live_z_mesh]',cfg)
        self.assertNotIn('[auto_trim',cfg)
    def test_main_module_registers_capture_and_mesh_commands_without_collision(self):
        f=capture.CaptureTests();f.setUp()
        try:
            commands=f.gcode.commands
            for name in ('START','STATUS','STOP','ZERO','MARK','SET','MESH_STATUS','MESH_TRACE','MESH_REQUIRE','MESH_TRAVEL_TEST'):
                self.assertIn('DEEP_CALIBRATION_'+name,commands)
            self.assertIsNot(commands['DEEP_CALIBRATION_STATUS'],commands['DEEP_CALIBRATION_MESH_STATUS'])
        finally:f.doCleanups()
    def test_recording_cannot_start_during_soak_calibration(self):
        f=capture.CaptureTests();f.setUp()
        try:
            f.feed();f.objects['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE']=capture.Status(running=True)
            with self.assertRaisesRegex(RuntimeError,'soak calibration'):f.cell.cmd_START(capture.Command())
            self.assertIsNone(f.cell.writer)
        finally:f.doCleanups()
    def test_ready_routing_rejects_old_startup_modules_before_any_mutation(self):
        for legacy in ('live_z_mesh','gcode_macro LIVE_Z_MESH_PREPARE','gcode_macro AUTO_TRIM_PREPARE'):
            with self.subTest(legacy=legacy):
                audit,objects,reactor=diagnostics.MeshAuditTests().fixture()
                objects[legacy]=object()
                native=lambda cmd:None;objects['gcode'].register_command('START_PRINT',native)
                with self.assertRaisesRegex(RuntimeError,'older startup'):audit._install_startup()
                self.assertIs(objects['gcode'].registered['START_PRINT'],native)
    def test_invalid_soak_values_fail_before_heating_or_motion(self):
        for options in ({'STABLE':'nan'},{'NOZZLE':'400'},{'NOZZLE_SOAK':'-1'},{'MAX':'9000'},{'BED':'60.5'},{'SAMPLES':'5.5'},{'POINTS':'5.5'},{'CONFIRM':'2.5'}):
            with self.subTest(options=options):
                r=preparation.Runtime();r.p['print_stats']['state']='standby'
                with self.assertRaises(RuntimeError):r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict({'BED':60},**options))
                self.assertEqual(r.lines,[])
    def test_calibration_defaults_use_strict_001mm_check(self):
        r=preparation.Runtime();r.p['print_stats']['state']='standby'
        r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict(BED=60))
        c=r.p['gcode_macro DEEP_CALIBRATION_SOAK_CALIBRATE']
        self.assertEqual(c['interval'],90.)
        self.assertEqual(c['stable'],.01)
        self.assertEqual(c['window'],600.)
        self.assertEqual(c['min_soak'],600.)
        self.assertEqual(c['samples'],2)
        self.assertEqual(c['repeat'],.01)
        self.assertEqual(c['confirm'],2)
        self.assertEqual(r.count('_G28'),1)
    def test_soak_calibration_rejects_active_recording_before_actions(self):
        r=preparation.Runtime();r.p['print_stats']['state']='standby';r.p['deep_calibration']['recording']=True
        with self.assertRaisesRegex(RuntimeError,'no capture'):r.run('DEEP_CALIBRATION_SOAK_CALIBRATE',dict(BED=60))
        self.assertEqual(r.lines,[])
    def test_fixed_560s_soak_counts_cleaning_time_and_builds_one_mesh(self):
        r=preparation.Runtime();r.start(DC_SOAK='560')
        self.assertEqual(r.meshes,1);self.assertEqual(r.homes,1)
        self.assertGreater(r.dwells,400);self.assertLess(r.dwells,560)
        self.assertTrue(any('SOAK=560' in line for line in r.lines))
    def test_saved_soak_status_is_read_only(self):
        r=preparation.Runtime();r.p['save_variables']['variables'].update(soak_t60=55,soak_t60_corners=560,soak_t60_from=24)
        r.run('DEEP_CALIBRATION_SOAK_STATUS',dict(BED=60))
        self.assertEqual(r.count('SAVE_VARIABLE'),0)
        self.assertTrue(any('560.0 s' in line for line in r.lines))
        self.assertFalse(any(line.startswith(('G1 ','M104 ','M140 ')) for line in r.lines))
    def test_original_preparation_call_count_remains_one(self):
        r=preparation.Runtime();r.start()
        self.assertEqual(r.count('_DEEP_CALIBRATION_BASE_START_PRINT'),1)
        self.assertEqual(r.count('_DEEP_CALIBRATION_TRASH_CLEAN'),1)
        self.assertEqual(r.count('_DEEP_CALIBRATION_SOAK'),1)
        self.assertEqual(r.count('_DEEP_CALIBRATION_BASE_PRECLEAN'),0)
        self.assertEqual(r.meshes,1)

if __name__=='__main__':unittest.main()
