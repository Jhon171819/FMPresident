import ast,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
source=Path('FMPresidente.pyw').read_text(encoding='utf-8');tree=ast.parse(source)
app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='App')
method=next(n for n in app.body if isinstance(n,ast.FunctionDef) and n.name=='connect')
namespace={'time':time,'sync':SimpleNamespace(observe_and_candidates=lambda **kw:('observacao',([],False)))}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'FMPresidente.pyw','exec'),namespace)
connect=namespace['connect']
class Tests(unittest.TestCase):
 def setUp(self):
  self.x=SimpleNamespace(busy=False,closed=False,fm=None,snap=None,selected_candidate=1,candidates=[1],candidate_choice=Mock(),candidate_filter=Mock(),candidate_box=Mock(),connection=Mock(),status=Mock(),sync=SimpleNamespace(epoch=1,begin=Mock(return_value=1),finish=Mock(return_value=True)),clear_candidate_cards=Mock(),set_actions=Mock(),show_observation=Mock(),update_recovery_indicator=Mock())
  self.x.candidate_filter.get.return_value=''
  self.x.run=lambda fn,done,text:done(fn())
 def test_sync_populates_without_approval(self):
  connect(self.x);self.x.candidate_box.configure.assert_called_with(values=[]);self.assertIsNone(self.x.selected_candidate)
 def test_obsolete_result_ignored(self):
  self.x.sync.finish.return_value=False;connect(self.x);self.x.show_observation.assert_not_called()
 def test_busy_sync_is_queued_and_invalidates_epoch(self):
  self.x.busy=True;connect(self.x);self.assertTrue(self.x.pending_sync);self.x.sync.begin.assert_called_once();self.x.status.set.assert_called_once()
 def test_filter_preserved(self):
  connect(self.x);self.x.candidate_filter.set.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
