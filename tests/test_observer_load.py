# 10.2.7: the G-code observer must cost nothing without slicer context, and
# read printing conditions at most every 0.1 s with it (it runs for every G1).
import unittest
from types import SimpleNamespace
import test_capture as capture

class Cmd:
    def __init__(self, **p): self.p = {k: str(v) for k, v in p.items()}
    def get_command_parameters(self): return dict(self.p)

class ObserverLoadTests(unittest.TestCase):
    def setUp(self):
        self.f = capture.CaptureTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.owner = self.f.cell; self.src = self.owner.slicer; self.src.enabled = True
        self.calls = {'status': 0, 'conditions': 0, 'native': 0}
        real_status = self.owner._status
        def status(name, t):
            self.calls['status'] += 1; return real_status(name, t)
        self.owner._status = status
        def conditions():
            self.calls['conditions'] += 1; return {}
        self.owner._context_conditions = conditions
        self.f.objects['virtual_sdcard'] = SimpleNamespace(cmd_from_sd=True, file_position=10)
        self.owner.armed = dict(material='PLA')
    def native(self, gcmd):
        self.calls['native'] += 1
    def test_no_slicer_context_no_work(self):
        self.src.state, self.src.snapshot = 'skipped', None
        for _ in range(50):
            self.src.observe('G1', self.native, Cmd(X=1, Y=2, E=.1))
        self.assertEqual(self.calls, {'status': 0, 'conditions': 0, 'native': 50})
    def test_conditions_read_at_most_every_tenth_second(self):
        self.src.state, self.src.snapshot = 'ready', {'segments': {}}
        for _ in range(30):            # a burst within the same 0.1 s
            self.src.observe('G1', self.native, Cmd(X=1, Y=2, E=.1))
        self.assertEqual(self.calls['native'], 30)
        self.assertEqual(self.calls['conditions'], 1)
if __name__ == '__main__':
    unittest.main()
