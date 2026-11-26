# 10.3.12: contact-band vibration with stepper tones and frame resonances removed
import json
import math
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import contact_vibration as cv
import deep_calibration_sensors as dcs


class ToneTests(unittest.TestCase):
    def test_corexy_step_tones_for_the_users_lines(self):
        # 50 mm/s at 80 degrees, 0.2 mm per full step: the 289 Hz peak measured
        a, b = cv.motor_step_hz(50 * math.cos(math.radians(80)), 50 * math.sin(math.radians(80)), .2)
        self.assertAlmostEqual(a, 289.6, delta=.5); self.assertAlmostEqual(b, 202.8, delta=.5)

    def test_buried_contact_signal_is_recovered(self):
        t = np.arange(1024) / 1600.
        contact = 20. * np.sin(2 * math.pi * 12. * t)                   # 20 mm/s2 at 12 Hz
        tone = 2000. * np.sin(2 * math.pi * 289.6 * t)                 # stepper tone, 100x larger
        harmonic = 500. * np.sin(2 * math.pi * 579.2 * t)
        resonance = 800. * np.sin(2 * math.pi * 57.6 * t)              # frame resonance
        win = np.stack([contact + tone + resonance, tone + harmonic, contact + tone + harmonic + resonance], axis=1)
        cx, cy, cz = cv.contact_band(win, (289.6, 202.8), (57.6, 61.0), (2., 40.), 6.)
        self.assertAlmostEqual(cz, 20. / math.sqrt(2), delta=.5)        # the contact signal's RMS, despite tones 100x larger
        self.assertLess(cy, 1.)                                          # pure tones: nothing left
        self.assertAlmostEqual(cx, 20. / math.sqrt(2), delta=.5)

    def test_without_filtering_the_tone_would_dominate(self):
        t = np.arange(1024) / 1600.
        win = np.stack([2000. * np.sin(2 * math.pi * 30. * t)] * 3, axis=1)   # a tone inside the band, not notched
        self.assertGreater(cv.contact_band(win, (), (), (2., 40.), 6.)[2], 1000.)
        self.assertLess(cv.contact_band(win, (30.,), (), (2., 40.), 6.)[2], 5.)  # notched as a stepper tone


class FileTests(unittest.TestCase):
    def test_reads_the_recorders_format(self):
        d = tempfile.mkdtemp(); path = os.path.join(d, 'r_accel_0000.dca')
        header = json.dumps(dict(session='s', part=0, format='<dddd', batch_format='<IdIIH')).encode()
        with open(path, 'wb') as f:
            f.write(dcs.MAGIC + struct.pack('<I', len(header)) + header)
            f.write(dcs.BATCH2.pack(2, 1., 0, 0, 1)); f.write(dcs.FRAME.pack(1., 1., 2., 3.)); f.write(dcs.FRAME.pack(1.000625, 4., 5., 6.))
        a = cv.read_acceleration([path])
        self.assertEqual(a.shape, (2, 4)); self.assertEqual(list(a[1]), [1.000625, 4., 5., 6.])
        self.assertEqual(cv.MAGIC, dcs.MAGIC)


if __name__ == '__main__':
    unittest.main()
