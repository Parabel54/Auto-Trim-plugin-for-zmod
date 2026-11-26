# 10.3.11: when the bed's warm-up was not seen, the warm-up time comes from
# Auto Trim's soak message (messages as printed by Auto Trim 3.9.16).
import unittest
import test_zero_and_time as zero_fixture
from test_capture import Command

FULL = ("info AUTO TRIM: bed heat soak 30 s (calibrated at 60 C, slowest point, full: bed history not known "
        "(Klipper restarted), bed started at -1 C), 0 s covered by the nozzle clean, waiting 30 s")
PART = ("info AUTO TRIM: bed heat soak 30 s (calibrated at 60 C, slowest point, bed hot for only 10 s, bed started "
        "at 60 C), 10 s covered by the time the bed was already hot, waiting 20 s")
COVERED = "info AUTO TRIM: bed heat soak 30 s (calibrated at 60 C, slowest point, bed started at 25 C) already covered: 45 s by the nozzle clean"
OLD = "info AUTO TRIM: bed heat soak 60 s (calibrated at 60 C, slowest point, bed started at 55 C) already covered by the 93 s nozzle clean"
LONG = "info AUTO TRIM: no bed heat soak (bed hot for 3600 s, longer than the 971 s soak)"


class SoakAnchorTests(unittest.TestCase):
    def setUp(self):
        self.z = zero_fixture.ZeroAndTimeTests('test_measurement_time_window'); self.z.setUp(); self.addCleanup(self.z.doCleanups)
        self.c = self.z.c
        self.c.creep_recovery, self.c.creep_tau, self.c.creep_rate, self.c.creep_slow_tau = 14.9, .5, .81, 120.
        self.z.f.feed()                                   # fixture bed already hot: warm-up not seen
        self.assertIsNone(self.c.bed_warm_t)

    def say(self, msg):
        self.c._auto_trim_output(msg)

    def test_each_message_form_gives_the_warm_up_time(self):
        for msg, hot in ((FULL, 0.), (PART, 10.), (COVERED, 45.), (OLD, 93.), (LONG, 3600.)):
            self.c.bed_warm_t = self.c.bed_warm_source = None
            now = self.z.f.reactor.now
            self.say(msg)
            self.assertAlmostEqual(self.c.bed_warm_t, now - hot, places=6, msg=msg)
            self.assertEqual(self.c.bed_warm_source, 'auto_trim_soak')

    def test_own_observation_wins(self):
        bed = self.z.f.objects['heater_bed'].status
        bed.update(temperature=25., target=60.); self.z.f.feed(); bed.update(temperature=60.); self.z.f.feed()
        seen = self.c.bed_warm_t
        self.say(LONG)
        self.assertEqual(self.c.bed_warm_t, seen); self.assertEqual(self.c.bed_warm_source, 'observed')

    def test_other_messages_are_ignored(self):
        self.say("info AUTO TRIM: no bed heat soak (off)")
        self.say("info AUTO TRIM: bed heat soak, 15 s left")
        self.assertIsNone(self.c.bed_warm_t)

    def test_correction_applies_from_the_soak(self):
        self.say(PART); warm = self.c.bed_warm_t
        self.c.cmd_START(Command(RUN='first'))
        self.z.run_readings(10, 8000000, z=1.0, ev=0.); self.z.run_readings(6, 8000526, z=.2, ev=1.)
        records, samples, events = self.z.log()
        last = samples[-1]
        self.assertEqual(last['bed_warm_source'], 'auto_trim_soak')
        zero_t = [e for e in events if e['event'] == 'baseline'][0]['baseline']['t']
        expected = self.c._creep_model((last['t'] - warm) / 60.) - self.c._creep_model((zero_t - warm) / 60.)
        self.assertAlmostEqual(last['creep_correction_g'], expected, places=6)


if __name__ == '__main__':
    unittest.main()
