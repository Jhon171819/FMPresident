from contextlib import contextmanager
from datetime import date
from pathlib import Path
import json,struct,tempfile,unittest
import fm23 as f
import sincronizacao_hibrida as sh
class Guard:
 def require(self):pass
 def require_full(self):pass
 def revoke(self):self.revoked=True
class Memory:
 def __init__(self):self.data={100:b'aaaa',200:b'bbbb',f.DATE_RVA:f.pack_date(date(2032,1,1))};self.calls=[];self.fail_at=None;self.rollback_failure=False;self.resume_failure=False
 def read(self,a,n):return self.data[a]
 def write(self,a,b):
  self.calls.append((a,b))
  if self.fail_at==a and b==b'dddd':self.data[a]=b'xxxx';raise OSError('falha parcial')
  if self.rollback_failure and a==100 and b==b'aaaa':raise OSError('rollback falhou')
  self.data[a]=b
 @contextmanager
 def paused(self):
  try:yield
  finally:
   if self.resume_failure:raise f.ResumeError('retomada falhou')
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.old=f.DATA;f.DATA=Path(self.tmp.name);self.addCleanup(setattr,f,'DATA',self.old)
  self.fm=f.FM.__new__(f.FM);self.fm.mem=Memory();self.fm.base=0;self.fm.club=1;self.fm.process={'pid':1,'started':'x'};self.fm.guard=Guard();self.fm.career_guard=Guard();self.fm.validate=lambda:None
  self.changes=[dict(label='A',addr=100,before=b'aaaa'.hex(),after=b'cccc'.hex()),dict(label='B',addr=200,before=b'bbbb'.hex(),after=b'dddd'.hex())]
 def journal(self):return json.loads(next((f.DATA/'historico').glob('*.json')).read_text(encoding='utf-8'))
 def test_success(self):
  entry=self.fm.transaction('ok',self.changes);self.assertEqual(entry['status'],'applied');self.assertEqual(self.fm.mem.data[100],b'cccc')
 def test_failed_partial_write_verified_rollback(self):
  self.fm.mem.fail_at=200
  with self.assertRaisesRegex(OSError,'restauradas e verificadas'):self.fm.transaction('x',self.changes)
  self.assertEqual(self.fm.mem.data[100],b'aaaa');self.assertEqual(self.fm.mem.data[200],b'bbbb');self.assertEqual(self.journal()['status'],'rollback_verified')
 def test_rollback_failure_quarantines(self):
  self.fm.mem.fail_at=200;self.fm.mem.rollback_failure=True
  with self.assertRaises(f.RecoveryError):self.fm.transaction('x',self.changes)
  self.assertTrue(self.fm.recovery_required);self.assertEqual(self.journal()['status'],'recovery_required')
  with self.assertRaises(f.RecoveryError):self.fm.transaction('x',self.changes)
 def test_resume_failure_quarantines(self):
  self.fm.mem.resume_failure=True
  with self.assertRaises(f.RecoveryError):self.fm.transaction('x',self.changes)
  self.assertEqual(self.journal()['status'],'recovery_required')
 def test_changed_owner_rejected_before_write(self):
  self.fm.finance=0x2000;self.changes[0]['ownership']=dict(kind='finance',base=0x1000,offset=100-0x1000)
  with self.assertRaisesRegex(ValueError,'proprietário'):self.fm.transaction('x',self.changes)
  self.assertEqual(self.fm.mem.calls,[])
 def test_equal_bytes_with_new_owner_are_rejected(self):
  self.fm.finance=0x2000;self.changes[0]['ownership']=dict(kind='finance',base=0x1000,offset=0)
  self.changes[0]['addr']=0x1000;self.fm.mem.data[0x1000]=b'aaaa'
  with self.assertRaises(ValueError):self.fm.transaction('x',self.changes)
  self.assertEqual(self.fm.mem.calls,[])
 def test_partial_first_write_is_restored(self):
  m=self.fm.mem;original=m.write
  def fail(a,b):
   if a==100 and b==b'cccc':m.data[a]=b'xxxx';raise OSError('falha parcial')
   return original(a,b)
  m.write=fail
  with self.assertRaisesRegex(OSError,'restauradas e verificadas'):self.fm.transaction('x',self.changes)
  self.assertEqual(m.data[100],b'aaaa');self.assertEqual(self.journal()['status'],'rollback_verified')
 def test_final_journal_failure_reports_applied_and_quarantines(self):
  from unittest.mock import patch
  original=f.save_json;calls=[]
  def save(path,data):
   calls.append(1)
   if len(calls)>1:raise OSError('disco indisponível')
   return original(path,data)
  with patch.object(f,'save_json',side_effect=save):
   with self.assertRaisesRegex(f.RecoveryError,'Alteração aplicada'):self.fm.transaction('x',self.changes)
  self.assertEqual(self.fm.mem.data[100],b'cccc');self.assertTrue(self.fm.recovery_required)
  self.assertIsNotNone(f.pending_recovery(self.fm.process))
 def test_change_records_current_finance_owner(self):
  self.fm.finance=0x1000;self.fm.mem.data[0x1014]=struct.pack('<i',10)
  item=self.fm.change('Caixa',0x1014,'i',20)
  self.assertEqual(item['ownership'],dict(kind='finance',base=0x1000,offset=20))
 def test_changed_bytes_before_first_write(self):
  self.fm.mem.data[100]=b'zzzz'
  with self.assertRaises(ValueError):self.fm.transaction('x',self.changes)
  self.assertEqual(self.fm.mem.calls,[]);self.assertEqual(self.journal()['status'],'failed')
 def test_silent_rollback_corruption_is_uncertain(self):
  m=self.fm.mem;m.fail_at=200;original=m.write
  def corrupt(a,b):
   if a==100 and b==b'aaaa':m.data[a]=b'zzzz';return
   original(a,b)
  m.write=corrupt
  with self.assertRaises(f.RecoveryError):self.fm.transaction('x',self.changes)
  self.assertIn('A',self.journal()['recovery']['uncertain'])
 def test_sponsor_moved_to_other_index_blocks_even_with_same_bytes(self):
  self.fm.mem.pointer=lambda a:0x5000
  self.fm.vector=lambda a,limit:[0x9999,0x7000]
  self.fm.mem.data[0x7000]=b'a'*24
  change=dict(label='Patrocínio',addr=0x7000,before=(b'a'*24).hex(),after=(b'b'*24).hex(),ownership=dict(kind='sponsor',index=0,base=0x7000))
  with self.assertRaisesRegex(ValueError,'proprietário'):self.fm.transaction('x',[change])
  self.assertEqual(self.fm.mem.calls,[])
 def test_debt_removed_blocks_even_with_same_bytes(self):
  self.fm.info=0x3000;self.fm.vector=lambda a,limit:[]
  self.fm.mem.data[0x7000]=b'a'*28
  change=dict(label='Dívida',addr=0x7000,before=(b'a'*28).hex(),after=(b'b'*28).hex(),ownership=dict(kind='debt',index=0,base=0x7000))
  with self.assertRaisesRegex(ValueError,'proprietário'):self.fm.transaction('x',[change])
  self.assertEqual(self.fm.mem.calls,[])
 def test_unknown_journal_blocks_new_object_same_process(self):
  self.fm.mem.fail_at=200;self.fm.mem.rollback_failure=True
  with self.assertRaises(f.RecoveryError):self.fm.transaction('x',self.changes)
  other=f.FM.__new__(f.FM);other.mem=Memory();other.base=0;other.club=1;other.process={'pid':1,'started':'x'}
  other.guard=Guard();other.career_guard=Guard();other.validate=lambda:None
  with self.assertRaisesRegex(f.RecoveryError,'pendente'):other.transaction('novo',self.changes)
  self.assertEqual(other.mem.calls,[])
 def test_prior_recovery_blocks_when_save_cannot_be_excluded(self):
  self.fm.mem.fail_at=200;self.fm.mem.rollback_failure=True
  with self.assertRaises(f.RecoveryError):self.fm.transaction('x',self.changes)
  self.assertIsNotNone(f.pending_recovery({'pid':2,'started':'x'}))
 def test_local_commit_remains_pending_until_recorded(self):
  entry=self.fm.transaction('patrocínio',self.changes,{'sponsor_contract':{'brand':'Teste'}})
  self.assertEqual(self.journal()['local_commit'],'pending')
  self.assertEqual(f.pending_recovery(self.fm.process),entry['id'])
  f.finalize_local_commit(entry)
  self.assertEqual(self.journal()['local_commit'],'committed')
  self.assertIsNone(f.pending_recovery(self.fm.process))
 def test_local_commit_missing_journal_never_rewrites_game(self):
  entry={'id':'missing','local_commit':'pending'}
  with self.assertRaises(OSError):f.finalize_local_commit(entry)
  self.assertEqual(self.fm.mem.calls,[])
 def test_date_advance_does_not_revoke_approval(self):
  o=sh.Observation((1,'start'),'build','now',1,123,'2032-01-01');c=sh.Coordinator();e=c.begin();c.finish(e,o)
  from dataclasses import replace
  c.inspect(e,replace(o,game_date='2032-01-02'));self.assertEqual(c.state,sh.State.OBSERVED_UNVERIFIED)
if __name__=='__main__':unittest.main(verbosity=2)
