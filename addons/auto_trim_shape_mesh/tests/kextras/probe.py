# Test stand-in for Klipper's probe module: ProbePointsHelper probes the points
# on a simulated bed and hands the results to the finalize callback, as Klipper does.
import collections
Result = collections.namedtuple('Result', 'bed_x bed_y bed_z test_x test_y test_z')
SURFACE = {'fn': None, 'log': []}
class ProbePointsHelper:
    def __init__(self, config, finalize_callback, default_points=None):
        self.finalize_callback = finalize_callback; self.probe_points = default_points or []
        self.default_horizontal_move_z = 5.; self.speed = self.lift_speed = 50.; self.use_offsets = False
    def update_probe_points(self, points, min_points): self.probe_points = points
    def use_xy_offsets(self, v): self.use_offsets = v
    def start_probe(self, gcmd):
        SURFACE['log'].append(dict(points=[tuple(p) for p in self.probe_points], params=dict(gcmd.params)))
        res = [Result(x, y, SURFACE['fn'](x, y), x, y, 0.) for x, y in self.probe_points]
        self.finalize_callback(res)
