import ast
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

source=Path(__file__).with_name('FMPresidente.pyw').read_text(encoding='utf-8')
tree=ast.parse(source);app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App')
method=next(n for n in app.body if isinstance(n,ast.FunctionDef) and n.name=='connect')
namespace={'time':time,'sync':SimpleNamespace(observe=lambda: 'observacao')}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'FMPresidente.pyw','exec'),namespace)
connect=namespace['connect']

class Tests(unittest.TestCase):
 def setUp(self):
  self.x=SimpleNamespace(busy=False,closed=False,fm=None,snap=None,selected_candidate=1,candidates=[1],
   candidate_choice=Mock(),candidate_filter=Mock(),candidate_box=Mock(),connection=Mock(),status=Mock(),
   sync=SimpleNamespace(epoch=1,begin=Mock(return_value=1),finish=Mock(return_value=True)),
   clear_candidate_cards=Mock(),set_actions=Mock(),show_observation=Mock(),search_candidates=Mock())
  self.callbacks=[];self.x.after=lambda delay,fn:self.callbacks.append(fn)
  self.x.run=lambda fn,done,text:done(fn())
 def test_sync_schedules_candidates_without_selecting(self):
  connect(self.x);self.assertEqual(len(self.callbacks),1);self.callbacks.pop()();self.x.search_candidates.assert_called_once_with();self.assertIsNone(self.x.selected_candidate);self.x.candidate_filter.set.assert_called_once_with('')
 def test_old_epoch_is_ignored(self):
  connect(self.x);self.x.sync.epoch=2;self.callbacks.pop()();self.x.search_candidates.assert_not_called()
 def test_failure_does_not_search(self):
  old=namespace['sync'];namespace['sync']=SimpleNamespace(observe=Mock(side_effect=OSError('sem FM')))
  try:connect(self.x);self.assertEqual(self.callbacks,[]);self.x.search_candidates.assert_not_called()
  finally:namespace['sync']=old
 def test_closed_window_does_not_search(self):
  connect(self.x);self.x.closed=True;self.callbacks.pop()();self.x.search_candidates.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
