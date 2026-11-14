import unittest
from types import SimpleNamespace
import test_beta102_review as review_tests
from test_first_print_auto import ArmCommand

class QueuePauseTests(unittest.TestCase):
    setUp = review_tests.AuditRegressions.setUp

    def install(self, add=None):
        gcode=self.f.gcode
        def register(name,fn):
            old=gcode.commands.pop(name,None)
            if fn is not None:gcode.commands[name]=fn
            return old
        gcode.register_command=register
        register('G1',self.native.cmd_G1)
        self.add_calls=[]
        def native_add(move):
            self.add_calls.append(move)
            if add: return add(move)
            return 'native-queue-result'
        self.f.objects['toolhead'].lookahead=SimpleNamespace(add_move=native_add)
        self.s.install()
        self.assertIsNotNone(self.s.queue_hook)

    def test_timing_exists_while_native_g1_is_still_running(self):
        self.install();during=[]
        def physical_move(pos,speed):
            move=SimpleNamespace(timing_callbacks=[],accel_t=.1,cruise_t=9.8,decel_t=.1)
            result=self.f.objects['toolhead'].lookahead.add_move(move)
            self.assertEqual(result,'native-queue-result')
            # Mirrors native _process_lookahead before _check_pause yields.
            for callback in move.timing_callbacks:callback(20.)
            during.append((self.s.timeline[-1]['start'],self.s.timeline[-1]['end'],self.s.timeline[-1]['source_valid']))
        self.native.move_with_transform=physical_move
        self.f.gcode.commands['G1'](ArmCommand(X='100',E='2.5',F='2400'))
        self.assertEqual(during,[(10.,20.,True)])
        self.assertEqual(len(self.add_calls),1)
        self.assertEqual(self.s.inflight,[])

    def test_split_native_moves_keep_separate_intervals(self):
        self.install()
        def split(pos,speed):
            for end in (15.,20.):
                move=SimpleNamespace(timing_callbacks=[],accel_t=1.,cruise_t=3.,decel_t=1.)
                self.f.objects['toolhead'].lookahead.add_move(move)
                for callback in move.timing_callbacks:callback(end)
        self.native.move_with_transform=split
        self.f.gcode.commands['G1'](ArmCommand(X='100',E='2.5',F='2400'))
        self.assertEqual([(r['start'],r['end']) for r in self.s.timeline],[(10.,15.),(15.,20.)])

    def test_native_queue_error_is_preserved_once(self):
        def error(move):raise RuntimeError('native queue failure')
        self.install(error)
        self.native.move_with_transform=lambda pos,speed:self.f.objects['toolhead'].lookahead.add_move(SimpleNamespace())
        with self.assertRaisesRegex(RuntimeError,'native queue failure'):
            self.f.gcode.commands['G1'](ArmCommand(X='100',E='2.5',F='2400'))
        self.assertEqual(len(self.add_calls),1);self.assertEqual(self.s.inflight,[])

    def test_annotation_failure_cannot_fail_native_queue(self):
        self.install()
        self.native.move_with_transform=lambda pos,speed:self.f.objects['toolhead'].lookahead.add_move(SimpleNamespace())
        self.f.gcode.commands['G1'](ArmCommand(X='100',E='2.5',F='2400'))
        self.assertEqual(len(self.add_calls),1)
        self.assertEqual(self.s.state,'unsupported')

class NativePlannerPauseTests(unittest.TestCase):
    setUp = review_tests.AuditRegressions.setUp
    install = QueuePauseTests.install
    def test_native_split_move_planning_has_timing_during_actual_check_pause(self):
        import ast, contextlib, math, logging, importlib
        from pathlib import Path
        tree=ast.parse((Path(__file__).parent/'native_reference/toolhead.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.Assign) or isinstance(n,ast.ClassDef) and n.name in ('Move','LookAheadQueue','ToolHead')]
        namespace=dict(math=math,logging=logging,importlib=importlib)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'unmodified_native_toolhead','exec'),namespace)
        ToolHead=namespace['ToolHead'];tool=ToolHead.__new__(ToolHead)
        tool.max_accel=500.;tool.max_velocity=100.;tool.junction_deviation=.02;tool.mcr_pseudo_accel=250.
        tool.commanded_pos=[0.,0.,.2,0.];tool.extra_axes=[]
        tool.kin=SimpleNamespace(check_move=lambda m:None)
        tool.lookahead=namespace['LookAheadQueue']();tool.lookahead.set_flush_time(0.)
        tool.print_time=10.;tool.need_check_pause=-1.;tool.special_queuing_state='';tool.can_pause=True
        tool.trapq=None;tool.trapq_append=lambda *args:None
        tool.motion_queuing=SimpleNamespace(note_mcu_movequeue_activity=lambda t:None)
        tool._advance_move_time=lambda t:setattr(tool,'print_time',t)
        tool.get_last_move_time=lambda:tool.print_time
        clock=[10.];during=[]
        def pause(t):
            if t==0.:return clock[0]
            clock[0]=t
            during.append((len(self.s.inflight),any(r.get('end') is not None for r in self.s.timeline)))
            return t
        tool.flush_timer=None
        tool.reactor=SimpleNamespace(NOW=0.,update_timer=lambda *args:None,monotonic=lambda:clock[0],pause=pause,assert_no_pause=contextlib.nullcontext)
        tool.mcu=SimpleNamespace(estimated_print_time=lambda t:t)
        self.f.objects['toolhead']=tool
        self.install()
        # install() supplies a simple queue for other tests; restore a native
        # LookAheadQueue and install a fresh observer around its actual method.
        self.s.handlers={};self.s.queue_hook=None
        self.f.gcode.commands.clear();self.f.gcode.commands['G1']=self.native.cmd_G1
        tool.lookahead=namespace['LookAheadQueue']();tool.lookahead.set_flush_time(0.)
        self.s.install()
        def split(pos,speed):
            for i in range(1,11):tool.move([i*10.,0.,.2,i*.25],speed)
        self.native.move_with_transform=split
        self.f.gcode.commands['G1'](ArmCommand(X='100',E='2.5',F='2400'))
        self.assertTrue(during,'native planner did not exercise its pause path')
        self.assertTrue(all(active and known for active,known in during),during)
