# Vibration gate (10.2.3): before and during every probe touch, the toolhead
# accelerometer measures shaking from outside (e.g. another printer on the
# same table). A shaken touch waits, or is discarded and redone; every touch
# is recorded with its vibration levels.
import importlib.util, math, random
from pathlib import Path
import unittest
from types import SimpleNamespace as S

spec=importlib.util.spec_from_file_location('approach_gate',Path(__file__).resolve().parents[1]/'deep_calibration_approach.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Command:
    def __init__(self,name='PROBE',params=None): self.name=name;self.params=params or {'PROBE_SPEED':'5'}
    def get_command_parameters(self): return self.params
    def get_command(self): return self.name
    def get_commandline(self): return self.name

RATE=400.   # samples per second in the simulation (the chip runs at 1600)

class GateTests(unittest.TestCase):
    def fixture(self, shake=lambda t:0., accelerometer=True, recording=False):
        o=m.DeepCalibrationApproach.__new__(m.DeepCalibrationApproach)
        o.fast_speed=5.;o.clearance=1.;o.max_age=300.;o.references={}
        o.fast_moves=o.slow_only=o.early_contacts=0;o.last_mode='ready';o.installed=True
        o.vib_gate=True;o.vib_limit=150.;o.vib_window=.3;o.vib_max_wait=10.;o.vib_retries=2;o.accel_name='lis2dw'
        o._vib_init()
        o.clock=100.;o.pos=[50.,60.,5.,0.];o.homed='xyz';o.messages=[];o.moves=[]
        o.shake=shake;o.generated=o.clock;o.rng=random.Random(3)
        bulk=S(clients=[])
        def add_client(cb): bulk.clients.append(cb)
        bulk.add_client=add_client
        def deliver():
            # samples up to the current clock, as one batch, like zMod's bulk helper
            rows=[]
            while o.generated < o.clock:
                t=o.generated;a=o.shake(t)*math.sqrt(2)   # RMS of a sine is amplitude/sqrt(2)
                rows.append((t, 40*o.rng.gauss(0,1)+a*math.sin(2*math.pi*31*t), 40*o.rng.gauss(0,1), 9800+40*o.rng.gauss(0,1)))
                o.generated+=1./RATE
            for cb in list(bulk.clients):
                if not cb(dict(data=rows,errors=0,overflows=0)): bulk.clients.remove(cb)
        def pause(until):
            o.clock=max(o.clock,until);deliver();return o.clock
        o.reactor=S(monotonic=lambda:o.clock,pause=pause)
        o.helper=S(mcu_probe=S(query_endstop=lambda t:False),results=[])
        def measured(c):
            pause(o.clock+1.0)                      # the touch takes about a second
            o.pos[2]=-3.5;o.helper.results.append(((o.pos[0],o.pos[1],-3.5),(0,0,-.25)))
        o.original=measured
        th=S(get_position=lambda:list(o.pos),get_status=lambda t:dict(homed_axes=o.homed),
             get_last_move_time=lambda:o.clock,wait_moves=lambda:None,
             manual_move=lambda goal,speed:(o.moves.append((list(goal),speed)),o.pos.__setitem__(2,goal[2])))
        o.dc=S(active=recording,events=[])
        o.dc._event=lambda name,**v:o.dc.events.append((name,v))
        def fast(toolhead,endstops,goal,speed,**k):
            o.pos[:]=list(goal);return list(goal)
        objects={'toolhead':th,'homing':S(manual_home=fast),
                 'mcu':S(estimated_print_time=lambda t:t),'deep_calibration':o.dc}
        if accelerometer: objects['lis2dw']=S(batch_bulk=bulk)
        o.bulk=bulk
        o.printer=S(lookup_object=lambda n,d=KeyError:objects.get(n,None) if d is not KeyError else objects[n],
                    command_error=RuntimeError,config_error=RuntimeError)
        o.gcode=S(create_gcode_command=lambda name,line,p:Command(name,p),respond_info=o.messages.append)
        return o

    def test_quiet_touch_is_measured_once_and_recorded(self):
        o=self.fixture()
        o.descend(Command())
        self.assertEqual(len(o.helper.results),1)
        t=o.touches[-1]
        self.assertLess(t['vibration_before'],150);self.assertLess(t['vibration_during'],150)
        self.assertFalse(t['shaken']);self.assertNotIn('redone',t);self.assertEqual(t['attempt'],1)
        self.assertEqual(o.vib_waited+o.vib_redone+o.vib_disturbed,0);self.assertEqual(o.messages,[])

    def test_quiet_level_matches_the_idle_checks(self):
        o=self.fixture();o.descend(Command())
        # three axes of 40 mm/s2 noise: about 69 mm/s2, like the AD5X idle checks (60-85)
        self.assertTrue(55<o.touches[-1]['vibration_during']<85, o.touches[-1])

    def test_shaking_before_the_touch_waits_until_it_settles(self):
        o=self.fixture(shake=lambda t:400. if t<103. else 0.)    # neighbour busy for 3 s
        o.descend(Command())
        t=o.touches[-1]
        self.assertGreaterEqual(t['waited_s'],2.5);self.assertLess(t['vibration_before'],150)
        self.assertEqual(len(o.helper.results),1);self.assertEqual(o.vib_waited,1)
        self.assertTrue(any('waiting for it to settle' in s for s in o.messages))

    def test_touch_shaken_during_the_touch_is_redone_and_the_shaken_result_discarded(self):
        o=self.fixture()
        start=o.clock
        # quiet while waiting, shaken during the first touch only
        o.shake=lambda t:400. if start+.4<=t<start+1.5 else 0.
        o.descend(Command())
        self.assertEqual(len(o.helper.results),1)               # only the good touch remains
        self.assertEqual(o.vib_redone,1)
        self.assertEqual(o.moves[0][0][2],5.)                    # went back up before touching again
        redone=[t for t in o.touches if t.get('redone')];kept=o.touches[-1]
        self.assertEqual(len(redone),1);self.assertGreater(redone[0]['vibration_during'],150)
        self.assertEqual(kept['attempt'],2);self.assertFalse(kept['shaken'])

    def test_constant_shaking_keeps_the_last_touch_and_marks_it(self):
        o=self.fixture(shake=lambda t:400.);o.vib_max_wait=2.
        o.descend(Command())
        self.assertEqual(len(o.helper.results),1)
        self.assertEqual(o.vib_redone,2);self.assertEqual(o.vib_disturbed,1)
        self.assertTrue(o.touches[-1].get('disturbed'));self.assertEqual(o.touches[-1]['attempt'],3)
        self.assertTrue(any('kept and marked' in s for s in o.messages))

    def test_homing_waits_but_is_never_redone(self):
        o=self.fixture(shake=lambda t:400.);o.vib_max_wait=1.
        o.descend(Command('G28'))
        self.assertEqual(len(o.helper.results),1);self.assertEqual(o.vib_redone,0)
        self.assertTrue(o.touches[-1]['homing']);self.assertTrue(o.touches[-1].get('disturbed'))

    def test_no_accelerometer_means_no_gate(self):
        o=self.fixture(accelerometer=False)
        o.descend(Command())
        self.assertEqual(len(o.helper.results),1);self.assertEqual(len(o.touches),0)
        self.assertEqual(o.vib_mode,'no_accelerometer')

    def test_gate_switched_off(self):
        o=self.fixture(shake=lambda t:400.);o.vib_gate=False
        o.descend(Command())
        self.assertEqual(len(o.helper.results),1);self.assertEqual(len(o.touches),0);self.assertEqual(o.bulk.clients,[])

    def test_touches_are_logged_into_a_running_recording(self):
        o=self.fixture(recording=True)
        o.descend(Command())
        ev=[v for n,v in o.dc.events if n=='probe_touch']
        self.assertEqual(len(ev),1);self.assertIn('vibration_during',ev[0])

    def test_one_listener_for_many_touches_released_when_idle(self):
        o=self.fixture()
        for i in range(3):
            o.pos[:]=[10.*i,20.,5.,0.];o.descend(Command())
        self.assertEqual(len(o.bulk.clients),1)                 # never added twice
        o.reactor.pause(o.clock+6.)                              # 6 s without a touch
        self.assertEqual(o.bulk.clients,[]);self.assertFalse(o.vib_listening)

    def test_listener_dropped_by_klipper_is_attached_again(self):
        o=self.fixture();o.bulk.client_cbs=o.bulk.clients
        o.descend(Command())
        o.bulk.clients.clear()                                   # e.g. Klipper stopped the stream
        o.pos[:]=[80.,20.,5.,0.];o.descend(Command())
        self.assertEqual(len(o.bulk.clients),1)
        self.assertIsNotNone(o.touches[-1]['vibration_during'])

    def test_status_reports_the_gate(self):
        o=self.fixture(shake=lambda t:400. if t<101.5 else 0.)
        o.descend(Command())
        st=o.get_status(0)
        self.assertTrue(st['vibration_gate']);self.assertEqual(st['vibration_limit'],150.)
        self.assertEqual(st['touches_recorded'],1);self.assertEqual(st['touches_waited'],1)
        self.assertIsNotNone(st['last_touch'])

if __name__=='__main__':
    unittest.main()
