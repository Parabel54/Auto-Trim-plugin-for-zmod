import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import test_capture as capture
from test_first_print_auto import ArmCommand
from test_gcode_context import gcode
from deep_calibration_gcode import parse_file, filament_profile_scan
from scan_filament_profile import scan, markdown
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=json.loads((ROOT/'reference/orca_606b50f1/filament_registry_606b50f1.json').read_text())

class FilamentScanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def write(self,name,data):
        p=self.root/name;p.write_text(json.dumps(data));return p
    def test_inventory_includes_all_modes_backend_and_conditional_options(self):
        rows=REGISTRY['settings'];self.assertEqual(len(rows),152)
        self.assertEqual(sum('developer' in r['hidden_categories'] for r in rows),18)
        self.assertEqual(sum(bool(r['hidden_categories']) for r in rows),130)
        self.assertTrue(any('advanced_mode' in r['hidden_categories'] for r in rows))
        self.assertTrue(all(r['type']!='unresolved' for r in rows))
        self.assertIn('filament_dev_ams_drying_time',{r['key'] for r in rows})
        self.assertIn('filament_retract_length_nc',{r['key'] for r in rows})
    def test_missing_settings_never_use_inventory_defaults(self):
        p=self.write('PLA.json',{'name':'My PLA','filament_type':['PLA']})
        report=scan(p);r={v['key']:v for v in report['settings']}
        self.assertEqual(report['profile'],'My PLA')
        self.assertEqual(r['pressure_advance']['status'],'missing_unknown')
        self.assertIsNone(r['pressure_advance']['selected_value'])
        self.assertNotIn('definition_default_reference',r['pressure_advance'])
    def test_parent_values_and_child_nil_are_preserved_with_origins(self):
        parent=self.write('base.json',{'name':'Base','filament_type':['PLA'],'pressure_advance':['0.04'],'filament_retraction_length':['1.0']})
        child=self.write('mine.json',{'name':'Mine','inherits':'Base','filament_retraction_length':['nil']})
        report=scan(child,[parent]);r={v['key']:v for v in report['settings']}
        self.assertEqual(report['unresolved_parents'],[])
        self.assertEqual(r['pressure_advance']['selected_value'],'0.04');self.assertEqual(r['pressure_advance']['origin'],'Base')
        self.assertEqual(r['filament_retraction_length']['selected_value'],'nil')
        self.assertEqual(r['filament_retraction_length']['status'],'explicit_nil_override')
        self.assertEqual(r['filament_retraction_length']['origin'],'Mine')
    def test_unavailable_parent_is_reported_and_not_fabricated(self):
        p=self.write('mine.json',{'name':'Mine','inherits':'Missing'})
        self.assertEqual(scan(p)['unresolved_parents'],['Missing'])
    def test_inheritance_cycle_rejected(self):
        a=self.write('a.json',{'name':'A','inherits':'B'});b=self.write('b.json',{'name':'B','inherits':'A'})
        with self.assertRaisesRegex(ValueError,'cyclic'):scan(a,[b])
    def test_used_profile_selected_and_hidden_values_captured_from_gcode(self):
        p=self.root/'print.gcode';p.write_text(gcode(header='; filament: 2\n',settings={
            'filament_type':'PLA;PETG','filament_diameter':'1.75,2.85','filament_flow_ratio':'1,0.98',
            'filament_settings_id':'Brand PLA;Brand PETG','filament_preheat_temperature_delta':'5'}))
        report=scan(p);r={v['key']:v for v in report['settings']}
        self.assertEqual(report['profile'],'Brand PETG');self.assertEqual(report['used_filament_index'],1)
        self.assertEqual(r['filament_diameter']['selected_value'],'2.85')
        self.assertEqual(r['filament_preheat_temperature_delta']['selected_value'],'5')
        self.assertIn('filament_preheat_temperature_delta',markdown(report))
    def test_multiple_variant_values_are_not_guessed(self):
        report=filament_profile_scan({'filament_type':['PLA'],'pressure_advance':['0.04','0.08']},REGISTRY,scope='preset')
        row=next(r for r in report['settings'] if r['key']=='pressure_advance')
        self.assertEqual(row['status'],'present_variant_mapping_unknown');self.assertIsNone(row['selected_value'])
        self.assertEqual(row['raw'],['0.04','0.08'])
    def test_unknown_active_profile_keeps_all_identity_values(self):
        report=filament_profile_scan({'filament_type':'PLA','filament_settings_id':'A;B'},REGISTRY)
        self.assertEqual(report['profile'],['A','B']);self.assertIsNone(report['used_filament_index'])
    def test_one_console_command_reports_background_scan_when_ready(self):
        f=capture.CaptureTests();f.setUp();self.addCleanup(f.doCleanups)
        p=Path(f.temp.name)/'print.gcode';p.write_text(gcode(settings={'filament_settings_id':'My PLA'}))
        f.cell.slicer.enabled=True
        f.objects['virtual_sdcard']=SimpleNamespace(file_path=lambda:str(p))
        command=ArmCommand(SHOW='HIDDEN');f.cell.cmd_FILAMENT(command)
        if f.cell.slicer.worker:f.cell.slicer.worker.join(3)
        f.cell.slicer.poll()
        messages=command.messages+f.gcode.messages
        self.assertTrue(any('DEEP CALIBRATION FILAMENT:' in text and 'My PLA' in text for text in messages))
        self.assertFalse(f.cell.filament_reports_pending)
        self.assertFalse(f.cell.active);self.assertEqual(f.reader.calls,[])

    def test_console_scan_is_read_only_and_hidden_listing_is_available(self):
        f=capture.CaptureTests();f.setUp();self.addCleanup(f.doCleanups)
        p=Path(f.temp.name)/'print.gcode';p.write_text(gcode(settings={'filament_settings_id':'My PLA'}))
        f.cell.slicer.enabled=True;f.cell.slicer.path=str(p);f.cell.slicer.state='ready';f.cell.slicer.snapshot=parse_file(str(p))
        f.objects['virtual_sdcard']=SimpleNamespace(file_path=lambda:str(p))
        c=ArmCommand(SHOW='HIDDEN');f.cell.cmd_FILAMENT(c)
        self.assertIn('My PLA',c.messages[0]);self.assertIn('filament_dev_ams_drying_time',c.messages[0])
        f.objects['virtual_sdcard']=SimpleNamespace(file_path=lambda:None)
        previous=f.cell.slicer.snapshot
        last=ArmCommand();f.cell.cmd_FILAMENT(last)
        self.assertIs(f.cell.slicer.snapshot,previous)
        self.assertIn('My PLA',last.messages[0])
        self.assertFalse(f.cell.active)
        self.assertEqual(f.reader.calls,[])
        self.assertIn('DEEP_CALIBRATION_FILAMENT',f.gcode.commands)
