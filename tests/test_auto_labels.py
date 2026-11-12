import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as S
from deep_calibration import DeepCalibration
from analyze import load_run
from test_analysis import write_run

class AutoLabelTests(unittest.TestCase):
 def fixture(self):
  c=DeepCalibration.__new__(DeepCalibration);c.active=True;c.auto_adjust_labels=True;c.offset_original=None;c.started=0.;c.adjustment_since=0.;c.label='UNLABELLED'
  c.reactor=S(monotonic=lambda:20.);c.events=[];c.messages=[];c.calls=[];c.origin=[0,0,.6,0]
  c.status={'print_stats':{'state':'printing','info':{'current_layer':1}},'gcode_macro AUTO_TRIM':{'prepared':True}}
  c._status=lambda n,t:{'homing_origin':list(c.origin)} if n=='gcode_move' else c.status.get(n,{})
  c._flush_force_tail=lambda:None;c._event=lambda name,**kw:c.events.append(dict(event=name,**kw))
  def native(g):
   c.calls.append(g)
   if g.get('Z_ADJUST') is not None:c.origin[2]+=float(g.get('Z_ADJUST'))
   elif g.get('Z') is not None:c.origin[2]=float(g.get('Z'))
  commands={'SET_GCODE_OFFSET':native}
  def register(name,fn):
   if fn is None:return commands.pop(name,None)
   commands[name]=fn
  c.gcode=S(register_command=register,respond_info=c.messages.append)
  c._install_adjustment_observer();c._install_adjustment_observer()
  return c,commands
 def test_lowering_marks_old_interval_too_high_and_new_unknown(self):
  c,commands=self.fixture();commands['SET_GCODE_OFFSET']({'Z_ADJUST':'-.02'})
  event=c.events[0];self.assertEqual(event['label'],'TOO_HIGH');self.assertEqual(event['start_t'],0.)
  self.assertAlmostEqual(event['from_z'],.6);self.assertAlmostEqual(event['to_z'],.58)
  self.assertEqual(len(c.calls),1);self.assertEqual(c.label,'UNLABELLED')
 def test_raising_means_old_interval_too_low(self):
  c,cmd=self.fixture();cmd['SET_GCODE_OFFSET']({'Z_ADJUST':'.02'});self.assertEqual(c.events[0]['label'],'TOO_LOW')
 def test_absolute_auto_trim_offsets_and_zero_adjust_are_not_labels(self):
  c,cmd=self.fixture();cmd['SET_GCODE_OFFSET']({'Z':'.25'});cmd['SET_GCODE_OFFSET']({'Z_ADJUST':'0'})
  self.assertEqual(c.events,[]);self.assertEqual(len(c.calls),2)
 def test_inactive_paused_later_layer_and_startup_are_not_labelled(self):
  for change in ('inactive','paused','layer','startup'):
   c,cmd=self.fixture()
   if change=='inactive':c.active=False
   if change=='paused':c.status['print_stats']['state']='paused'
   if change=='layer':c.status['print_stats']['info']['current_layer']=2
   if change=='startup':c.status['gcode_macro AUTO_TRIM']['prepared']=False
   cmd['SET_GCODE_OFFSET']({'Z_ADJUST':'.02'});self.assertEqual(c.events,[],change)
 def test_native_failure_is_preserved_and_never_annotated(self):
  c,cmd=self.fixture()
  def error(g):raise RuntimeError('native error')
  c.offset_original=error
  with self.assertRaisesRegex(RuntimeError,'native error'):cmd['SET_GCODE_OFFSET']({'Z_ADJUST':'.02'})
  self.assertEqual(c.events,[])
 def records(self,path):
  write_run(path);r=[json.loads(l) for l in path.read_text().splitlines()]
  for item in r:
   if item['type']=='context' and item['label']=='TOO_HIGH':item['label']='UNLABELLED'
  r.append(dict(type='event',event='adjustment_label',t=40,start_t=0,end_t=30,from_z=.7,label='TOO_HIGH'))
  return r
 def test_offline_labels_preceding_unlabelled_interval_only(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.jsonl';r=self.records(p);p.write_text(''.join(json.dumps(x)+'\n' for x in r));s=load_run(p)['samples']
   self.assertTrue(all(x['label']=='TOO_HIGH' and x['label_inferred'] for x in s if x['t']<30))
   self.assertTrue(all(x['label']=='GOOD' and not x['label_inferred'] for x in s if x['t']>=80))
   self.assertTrue(any(x['eligible'] for x in s if x['t']<30))
 def test_wrong_offset_and_manual_label_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.jsonl';r=self.records(p)
   for x in r:
    if x['type']=='context' and x['t']<30:x['label']='GOOD'
   p.write_text(''.join(json.dumps(x)+'\n' for x in r));s=load_run(p)['samples']
   self.assertTrue(all(x['label']=='GOOD' for x in s if x['t']<30))
   for x in r:
    if x.get('event')=='adjustment_label':x['from_z']=99.
    if x['type']=='context' and x['t']<30:x['label']='UNLABELLED'
   p.write_text(''.join(json.dumps(x)+'\n' for x in r));s=load_run(p)['samples']
   self.assertTrue(all(x['label']=='UNLABELLED' for x in s if x['t']<30))
 def test_automatic_labels_do_not_remove_force_or_motion_rejections(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.jsonl';r=self.records(p)
   for x in r:
    if x['type']=='sample':x['board_overload']=True
   p.write_text(''.join(json.dumps(x)+'\n' for x in r));s=load_run(p)['samples']
   self.assertTrue(all(not x['eligible'] for x in s))
   self.assertTrue(all('board_overload' in x['rejection'] for x in s))
