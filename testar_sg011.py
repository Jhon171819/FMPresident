import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import recuperacao as r
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.dir=Path(self.t.name);self.process={'pid':1,'started':'start'}
  self.entry=dict(schema_version=1,id='a'*32,title='Teste',time='2026-11-02',status='prepared',process=self.process,changes=[dict(label='x',addr=1,before='00',after='01')],meta={})
 def write(self,name='x.json',entry=None):
  (self.dir/name).write_text(json.dumps(self.entry if entry is None else entry),encoding='utf-8')
 def test_prepared_unknown_and_blocks(self):
  self.write();rows=r.scan(self.dir);self.assertEqual(rows[0].state,'STATE_UNKNOWN');self.assertIsNotNone(r.blocking(rows,self.process))
 def test_applied_not_pending(self):
  self.entry['status']='applied';self.write();self.assertEqual(r.scan(self.dir)[0].state,'MEMORY_APPLIED');self.assertIsNone(r.blocking(r.scan(self.dir),self.process))
 def test_local_pending_only_ticket_independent(self):
  self.entry.update(status='applied',local_commit='pending',meta={'sponsor_contract':{}});self.write();rows=r.scan(self.dir)
  self.assertEqual(rows[0].state,'LOCAL_COMMIT_PENDING');self.assertIsNone(r.blocking(rows,self.process,'ticket'));self.assertIsNotNone(r.blocking(rows,self.process))
 def test_corrupted_empty_truncated_or_nonobject_blocks(self):
  for content in ('','{','[]','null'):
   (self.dir/'x.json').write_text(content);rows=r.scan(self.dir);self.assertEqual(rows[0].state,'JOURNAL_UNREADABLE');self.assertIsNotNone(r.blocking(rows,self.process,'ticket'))
 def test_unknown_version(self):
  self.entry['schema_version']=999;self.write();self.assertEqual(r.scan(self.dir)[0].state,'JOURNAL_UNREADABLE')
 def test_missing_required(self):
  del self.entry['changes'];self.write();self.assertEqual(r.scan(self.dir)[0].state,'JOURNAL_UNREADABLE')
 def test_duplicate_is_unknown(self):
  self.write('a.json');self.write('b.json');self.assertTrue(all(x.state=='JOURNAL_UNREADABLE' for x in r.scan(self.dir)))
 def test_old_process_visible_but_not_attributed(self):
  self.write();rows=r.scan(self.dir);self.assertIsNotNone(r.blocking(rows,{'pid':2,'started':'different'}));self.assertIn('não o save',rows[0].reason)
 def test_rollback_verified(self):
  self.entry['status']='rollback_verified';self.write();self.assertEqual(r.scan(self.dir)[0].state,'ROLLBACK_VERIFIED');self.assertIsNone(r.blocking(r.scan(self.dir),self.process))
 def test_interrupted_temp_file_blocks(self):
  (self.dir/'operation.tmp').write_text('partial')
  rows=r.scan(self.dir);self.assertEqual(rows[0].state,'JOURNAL_UNREADABLE');self.assertIsNotNone(r.blocking(rows,self.process))
 def test_unreadable_file(self):
  self.write()
  with patch('pathlib.Path.open',side_effect=PermissionError()):self.assertEqual(r.scan(self.dir)[0].state,'JOURNAL_UNREADABLE')
 def test_pending_without_sponsor_evidence_blocks_ticket(self):
  self.entry.update(status='applied',local_commit='pending');self.write()
  self.assertIsNotNone(r.blocking(r.scan(self.dir),self.process,'ticket'))
 def test_unavailable_directory_is_unreadable(self):
  with patch('pathlib.Path.iterdir',side_effect=PermissionError()):
   self.assertEqual(r.scan(self.dir)[0].state,'JOURNAL_UNREADABLE')
 def test_invalid_id_blocks(self):
  self.entry['id']='not-valid';self.write();self.assertEqual(r.scan(self.dir)[0].state,'JOURNAL_UNREADABLE')
 def test_independent_prices_allow_only_with_local_pending(self):
  import fm23 as f
  from testar_sg01 import Guard,Memory
  history=self.dir/'historico';history.mkdir()
  self.entry.update(status='applied',local_commit='pending',meta={'sponsor_contract':{}})
  (history/'pending.json').write_text(json.dumps(self.entry),encoding='utf-8')
  old=f.DATA;f.DATA=self.dir
  try:
   fm=f.FM.__new__(f.FM);fm.mem=Memory();fm.base=0;fm.club=1;fm.process=self.process
   fm.guard=Guard();fm.career_guard=Guard();fm.validate=lambda:None;fm.finance=0x1000
   fm.mem.data[0x1018]=b'aaaa';fm.mem.data[0x1014]=b'aaaa'
   ticket=dict(label='Ingresso',addr=0x1018,before=b'aaaa'.hex(),after=b'bbbb'.hex(),ownership=dict(kind='finance',base=0x1000,offset=24))
   self.assertEqual(fm.transaction('Bilheteria',[ticket])['status'],'applied')
   cash=dict(label='Caixa',addr=0x1014,before=b'aaaa'.hex(),after=b'bbbb'.hex(),ownership=dict(kind='finance',base=0x1000,offset=20))
   with self.assertRaises(f.RecoveryError):fm.transaction('Caixa',[cash])
   self.assertEqual(fm.mem.data[0x1014],b'aaaa')
  finally:f.DATA=old
 def test_team_flag_requires_current_team(self):
  import fm23 as f
  fm=f.FM.__new__(f.FM);fm.kit_team=lambda:0x1000
  change={'addr':0x1000+46,'ownership':{'kind':'team_flag','base':0x1000,'offset':46}}
  fm.validate_change_owner(change,1)
  fm.kit_team=lambda:0x2000
  with self.assertRaises(ValueError):fm.validate_change_owner(change,1)
 def test_legacy_undo_rejected(self):
  import fm23 as f
  from datetime import date
  fm=f.FM.__new__(f.FM);fm.validate=lambda:None;fm.date=lambda:date(2032,1,1);fm.process={'pid':1,'started':'start'};fm.club=100
  entry={'status':'applied','process':fm.process,'club':100,'date':'2032-01-01','changes':[{'label':'x','addr':5,'before':'00','after':'01'}]}
  with self.assertRaisesRegex(ValueError,'propriedade'):fm.undo(entry)
 def test_missing_directory(self):self.assertEqual(r.scan(self.dir/'absente'),[])
 def test_legacy_failed_unknown(self):
  self.entry.pop('schema_version');self.entry['status']='failed';self.write();self.assertEqual(r.scan(self.dir)[0].state,'STATE_UNKNOWN')
 def test_public_report_omits_pid(self):
  self.write();self.assertNotIn('process_pid',r.scan(self.dir)[0].public())
if __name__=='__main__':unittest.main(verbosity=2)
