import importlib.machinery,importlib.util,threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import tkinter as tk
from tkinter import ttk
loader=importlib.machinery.SourceFileLoader('app_pf01_test','FMPresidente.pyw')
spec=importlib.util.spec_from_loader(loader.name,loader);mod=importlib.util.module_from_spec(spec);loader.exec_module(mod)
class Tests(unittest.TestCase):
 def setUp(self):
  self.main=threading.get_ident();self.worker_thread=None;self.obs=object();self.result={'balance':1}
  def snapshot():self.worker_thread=threading.get_ident();return self.result
  self.fm=SimpleNamespace(snapshot=snapshot,close=Mock())
  self.x=SimpleNamespace(closed=False,busy=False,last_monitor=0,selected_candidate=123,fm=self.fm,snap={'balance':1},
   sync=SimpleNamespace(state=mod.sync.State.OBSERVED_UNVERIFIED,epoch=3,inspect=Mock(return_value=True)),
   after=Mock(),poll=Mock(),render=Mock(),clear_candidate_cards=Mock(),set_actions=Mock(),connection=Mock(),status=Mock(),candidate_choice=Mock(),candidate_box=Mock())
  self.work=None;self.done=None
  def run(work,done,text):self.work=work;self.done=done
  self.x.run=run
 def poll(self):
  with patch.object(mod.sync,'observe',return_value=self.obs):
   mod.App.poll(self.x)
   result=[];t=threading.Thread(target=lambda:result.append(self.work()));t.start();t.join();self.done(result[0])
 def test_snapshot_is_off_ui_thread_and_unchanged_skips_render(self):
  self.poll();self.assertNotEqual(self.worker_thread,self.main);self.x.render.assert_not_called();self.x.sync.inspect.assert_called_once()
 def test_changed_snapshot_renders(self):
  self.result={'balance':2};self.poll();self.x.render.assert_called_once();self.assertEqual(self.x.snap,self.result)
 def test_obsolete_result_is_discarded(self):
  self.x.sync.inspect.return_value=False;self.result={'balance':2};self.poll();self.x.render.assert_not_called();self.assertEqual(self.x.snap,{'balance':1})
 def test_real_tree_preserves_selected_row(self):
  root=tk.Tk();root.withdraw();self.addCleanup(root.destroy);tree=ttk.Treeview(root,columns=['x'])
  mod.App.replace_rows(tree,[('1',('a',)),('2',('b',))]);tree.selection_set('1')
  mod.App.replace_rows(tree,[('1',('a',)),('2',('c',))]);self.assertEqual(tree.selection(),('1',));self.assertEqual(tree.item('2','values'),('c',))
 def test_busy_monitor_does_not_start(self):
  self.x.busy=True;mod.App.poll(self.x);self.assertIsNone(self.work);self.x.after.assert_called_once()
 def test_search_keeps_existing_selection(self):
  first=SimpleNamespace(address=9,club=SimpleNamespace(name='Ceará',uid=104749),source='registro')
  box=Mock();box.current.return_value=0
  x=SimpleNamespace(busy=False,sync=SimpleNamespace(epoch=1),candidate_filter=Mock(),candidate_box=box,
   candidates=[first],candidate_choice=Mock(),status=Mock())
  x.candidate_filter.get.return_value=''
  x.run=lambda work,done,text:done(([first],False))
  mod.App.search_candidates(x)
  box.current.assert_called_with(0);x.candidate_choice.set.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
