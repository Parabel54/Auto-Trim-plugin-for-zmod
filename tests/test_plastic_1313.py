# 10.3.13: the weight of the plastic laid on the bed is subtracted
import math
import types
import unittest
import test_zero_and_time as zero_fixture
from test_capture import Command

AREA = math.pi * (1.75 / 2) ** 2


class PlasticTests(unittest.TestCase):
    def setUp(self):
        self.z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); self.z.setUp(); self.addCleanup(self.z.doCleanups)
        self.c = self.z.c
        self.e = 100.
        dt = self.z.f.objects['motion_report'].dtrapqs
        dt['extruder'] = types.SimpleNamespace(get_trapq_position=lambda clock: ([self.e], self.z.m['ev']))

    def print_layer(self, material='PLA', feed_mm=(10., 20., 30.), retract=0.):
        self.z.f.feed(); self.c.cmd_START(Command(RUN='first', MATERIAL=material))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.)                  # zero at e = 100
        for mm in feed_mm:
            self.e = 100. + mm; self.z.run_readings(1, 8000526, z=.2, ev=1.)
        if retract:
            self.e -= retract; self.z.run_readings(1, 8000526, z=.6, ev=0.)
        return self.z.log()

    def test_plastic_weight_from_filament_fed(self):
        records, samples, events = self.print_layer()
        self.assertEqual([e for e in events if e['event'] == 'baseline'][0]['baseline']['e'], 100.)
        self.assertAlmostEqual(samples[-1]['plastic_weight_g'], 30. * AREA * 1.24 / 1000., places=9)

    def test_material_density(self):
        records, samples, events = self.print_layer(material='PETG')
        self.assertAlmostEqual(samples[-1]['plastic_weight_g'], 30. * AREA * 1.27 / 1000., places=9)

    def test_density_override(self):
        self.c.plastic_density = 1.5
        records, samples, events = self.print_layer()
        self.assertAlmostEqual(samples[-1]['plastic_weight_g'], 30. * AREA * 1.5 / 1000., places=9)

    def test_retraction_nets_out(self):
        records, samples, events = self.print_layer(retract=2.)
        self.assertAlmostEqual(samples[-1]['plastic_weight_g'], 28. * AREA * 1.24 / 1000., places=9)

    def test_nozzle_force_is_force_minus_creep_and_plastic(self):
        records, samples, events = self.print_layer()
        last = samples[-1]
        self.assertAlmostEqual(last['filtered_grams_nozzle'],
                               last['filtered_grams'] - (last['creep_correction_g'] or 0.) - last['plastic_weight_g'], places=9)

    def test_users_first_layer_scale(self):
        # 1920 mm of 1.75 mm PLA, as on the 26 November print: about 5.7 g
        self.assertAlmostEqual(1920 * AREA * 1.24 / 1000., 5.73, places=2)


if __name__ == '__main__':
    unittest.main()
