import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time,threading,unittest,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PySide6.QtCore import QThread
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMessageBox
import FMPresidenteQt as q
from aplicacao_qt import Session
app=QApplication.instance() or QApplication([])
from PySide6.QtGui import QFontDatabase,QFont
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf");app.setFont(QFont("Segoe UI",10));app.setStyleSheet(q.STYLE)
def snapshot():return {'club':'Clube de teste','date':'2032-05-26','uid':104749,'balance':-786933,'transfer':2204111,'wage':872443,'ticket':30.5,'season_ticket':500,'facilities':{n:10 for n in q.native.FACILITIES},'sponsors':[{'name':'Master','total':100000,'start':'2032-01-01','end':'2032-12-31'}],'debts':[{'index':0,'original':100000,'monthly':5000,'interest':400,'end':'2034-01-01','raw':'00'}],'licensed_kits':False}
class Tests(unittest.TestCase):
 def setUp(self):self.w=q.MainWindow(auto=False);self.addCleanup(self.w.close)
 def test_navigation(self):
  self.assertEqual(self.w.stack.count(),10)
  for i in range(10):self.w.nav.setCurrentRow(i);self.assertEqual(self.w.stack.currentIndex(),i)
 def test_no_approval_no_financial_actions(self):self.assertTrue(all(not b.isEnabled() for b in self.w.write_buttons))
 def test_snapshot_and_form_state(self):
  self.w.update_snapshot(snapshot(),True);self.w.transfer.setValue(123);self.w.update_snapshot(snapshot());self.assertEqual(self.w.transfer.value(),123)
 def test_model_updates_without_reset(self):
  m=q.Rows(['a']);m.update([('1',)]);reset=Mock();m.modelReset.connect(reset);m.update([('2',)]);reset.assert_not_called()
 def test_invalidated_context_clears_selection(self):
  self.w.update_snapshot(snapshot(),True);self.w.on_result('invalidate',None);self.assertIsNone(self.w.snapshot);self.assertEqual(self.w.candidates.count(),0)
 def test_delegates_to_engine(self):
  s=Session();s.fm=Mock();s.fm.capital.return_value={'status':'applied'};s.fm.snapshot.return_value=snapshot();r=s.execute('capital',1000);s.fm.capital.assert_called_once_with(1000);self.assertEqual(r['entry']['status'],'applied')
 def test_snapshot_failure_after_application_not_simple_failure(self):
  s=Session();s.fm=Mock();s.fm.capital.return_value={'status':'applied'};s.fm.snapshot.side_effect=OSError('read');r=s.execute('capital',1000);self.assertEqual(r['entry']['status'],'applied');self.assertIsNotNone(r['snapshot_error'])
 def test_recovery_disconnected(self):
  with patch('recuperacao.scan',return_value=[]) as scan:self.assertEqual(Session().diagnostics(),[]);scan.assert_called_once()
 def test_worker_callback_uses_gui_thread(self):
  c=q.Controller(Session());seen=[];c.changed.connect(lambda kind,value:seen.append(QThread.currentThread()==app.thread()))
  self.assertTrue(c.submit('test',lambda:123))
  deadline=time.monotonic()+5
  while c.busy and time.monotonic()<deadline:QTest.qWait(10)
  self.assertFalse(c.busy);self.assertTrue(all(seen));c.close()
 def test_worker_error_delivered(self):
  c=q.Controller(Session());seen=[];c.changed.connect(lambda kind,value:seen.append(kind))
  c.submit('test',lambda:1/0);deadline=time.monotonic()+5
  while c.busy and time.monotonic()<deadline:QTest.qWait(10)
  self.assertIn('error',seen);c.close()
 def test_pending_sync_coalesces(self):
  c=q.Controller(Session());c.busy=True;c.request_sync('one');c.request_sync('two');self.assertEqual(c.pending[:2],('two',False));self.assertEqual(c.coordinator.epoch,2);c.busy=False;c.close()
 def test_close_during_task_refused(self):
  c=q.Controller(Session());c.busy=True;self.assertFalse(c.close());c.busy=False;self.assertTrue(c.close())
 def test_all_available_service_operations_delegate(self):
  for method,args in [('budgets',(100,200)),('prices',(20.5,400)),('invest',('Treinamento',)),('repay',(0,'00')),('set_licensed_kits',(False,'2032-05-26')),('undo',({'id':'test'},))]:
   with self.subTest(method=method):
    s=Session();s.fm=Mock();s.fm.snapshot.return_value=snapshot();s.execute(method,*args);getattr(s.fm,method).assert_called_once_with(*args)
 def test_new_loan_not_exposed_by_service(self):
  s=Session();s.fm=Mock()
  with self.assertRaises(ValueError):s.execute('sign',{})
  s.fm.sign.assert_not_called()
 def test_approval_read_failure_closes_handle(self):
  fm=Mock();fm.snapshot.side_effect=OSError('read')
  with patch('fm23.FM.connect_manual',return_value=fm):
   with self.assertRaises(OSError):Session().approve(SimpleNamespace(address=1,club=SimpleNamespace(uid=104749)))
  fm.close.assert_called_once()
 def test_duplicate_task_refused(self):
  c=q.Controller(Session());c.busy=True;fn=Mock();self.assertFalse(c.submit('applied',fn));fn.assert_not_called();c.busy=False;c.close()
 def test_obsolete_sync_not_published(self):
  c=q.Controller(Session());epoch=c.coordinator.begin();c.coordinator.begin();events=[];c.changed.connect(lambda kind,value:events.append(kind));c.complete('sync',epoch,(None,([],False)),None);self.assertNotIn('sync',events);c.close()
 def test_obsolete_proposal_not_confirmed(self):
  c=q.Controller(Session());epoch=c.coordinator.begin();c.coordinator.begin();events=[];c.changed.connect(lambda kind,value:events.append(kind));c.complete('offer',epoch,{'proposal':'old'},None);self.assertNotIn('offer',events);c.close()
if __name__=='__main__':unittest.main(verbosity=2)
