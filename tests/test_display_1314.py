# 10.3.14: Fluidd display sensors from raw counts
import os
import unittest
import test_zero_and_time as zero_fixture
import test_plastic_1313 as plastic_fixture
from test_capture import Command

HERE = os.path.dirname(os.path.abspath(__file__))


class Recorder:
    def __init__(self, sensor):
        self.values = []; sensor.setup_minmax(-10000, 10000); sensor.setup_callback(lambda t, v: self.values.append(v))


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); self.z.setUp(); self.addCleanup(self.z.doCleanups)
        self.c = self.z.c
        self.grams = Recorder(self.c._display_sensor('grams')); self.nozzle = Recorder(self.c._display_sensor('nozzle'))

    def test_grams_from_raw_relative_to_the_tare_reading(self):
        self.z.f.feed()
        self.z.f.reader._command_id += 1; self.c._auto_trim_output('H1 > command H1 ok. 8000000')
        self.z.run_readings(1, 8000526, z=1.0, ev=0.)
        self.assertAlmostEqual(self.grams.values[-1], 526 / 52.56, places=6)       # 10.01 g, not a 19 g step
        self.z.run_readings(1, 7999474, z=1.0, ev=0.)
        self.assertAlmostEqual(self.grams.values[-1], -526 / 52.56, places=6)      # negative stays negative

    def test_without_a_tare_reply_the_first_reading_after_the_tare_is_the_reference(self):
        self.z.f.feed()
        self.z.f.reader._command_id += 1
        self.z.f.feed(8001000); self.z.f.feed(8001526)
        self.assertAlmostEqual(self.grams.values[-2], 0., places=6)
        self.assertAlmostEqual(self.grams.values[-1], 526 / 52.56, places=6)

    def test_nozzle_force_zero_outside_and_recorded_value_inside_a_recording(self):
        self.z.f.feed()
        self.assertEqual(self.nozzle.values[-1], 0.)
        p = plastic_fixture.PlasticTests('test_users_first_layer_scale'); p.z = self.z; p.c = self.c; p.e = 100.
        import types
        self.z.f.objects['motion_report'].dtrapqs['extruder'] = types.SimpleNamespace(get_trapq_position=lambda clock: ([p.e], self.z.m['ev']))
        before = len(self.nozzle.values)
        records, samples, events = p.print_layer()
        last = samples[-1]
        self.assertAlmostEqual(self.nozzle.values[-1], last['filtered_grams_nozzle'], places=6)
        recorded = len([r for r in samples if r['t'] > 0])
        self.assertLessEqual(len(self.nozzle.values) - before, len(samples) + 2)       # one value per reading, no flicker

    def test_shipped_config_declares_both_after_deep_calibration(self):
        text = open(os.path.join(HERE, '..', 'deep_calibration.cfg')).read()
        dc = text.index('[deep_calibration]'); g = text.index('[temperature_sensor load_cell_grams]'); n = text.index('[temperature_sensor nozzle_force]')
        self.assertTrue(dc < g < n)
        self.assertIn('sensor_type: deep_calibration_grams', text); self.assertIn('sensor_type: deep_calibration_nozzle', text)


class KlipperLimitsTests(unittest.TestCase):
    def test_shipped_sensor_sections_pass_klippers_option_checks(self):
        # Klipper's temperature_sensor: min_temp >= -273.15, max_temp above min_temp
        import configparser
        cp = configparser.RawConfigParser(strict=False, inline_comment_prefixes=('#', ';'))
        cp.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'deep_calibration.cfg'))
        sections = [s for s in cp.sections() if s.startswith('temperature_sensor ')]
        self.assertEqual(len(sections), 2)
        for s in sections:
            lo, hi = cp.getfloat(s, 'min_temp'), cp.getfloat(s, 'max_temp')
            self.assertGreaterEqual(lo, -273.15, s); self.assertGreater(hi, lo, s)

if __name__ == '__main__':
    unittest.main()
