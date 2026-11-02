from dataclasses import replace
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent/'engenharia_reversa'))
from validar_sincronizacao import Monitor,Observation
class Tests(unittest.TestCase):
 def setUp(self):
  self.a=Observation(1,'start','hash',104749,1000,'2032-05-01');self.m=Monitor();self.ticket=self.m.synchronize(lambda:self.a)
 def test_sync_invalidates_old_ticket_even_when_same_values(self):
  self.m.synchronize(lambda:self.a);self.assertEqual(self.m.inspect(self.ticket,lambda:self.a),'STALE')
 def test_failure_invalidates_previous_context(self):
  with self.assertRaises(OSError):self.m.synchronize(lambda:(_ for _ in ()).throw(OSError()))
  self.assertIsNone(self.m.observation);self.assertEqual(self.m.inspect(self.ticket,lambda:self.a),'STALE')
 def test_process_restart(self):self.assertEqual(self.m.inspect(self.ticket,lambda:replace(self.a,started='new')),'CHANGED')
 def test_pid_change(self):self.assertEqual(self.m.inspect(self.ticket,lambda:replace(self.a,pid=2)),'CHANGED')
 def test_build_change(self):self.assertEqual(self.m.inspect(self.ticket,lambda:replace(self.a,build='other')),'CHANGED')
 def test_club_change(self):self.assertEqual(self.m.inspect(self.ticket,lambda:replace(self.a,club_uid=42)),'CHANGED')
 def test_pointer_change(self):self.assertEqual(self.m.inspect(self.ticket,lambda:replace(self.a,club_address=2000)),'CHANGED')
 def test_date_change_is_not_proof_of_save_change(self):self.assertEqual(self.m.inspect(self.ticket,lambda:replace(self.a,game_date='2032-05-02')),'CHANGED')
 def test_same_values_other_save_undetectable(self):
  different_save_same_observables=replace(self.a)
  self.assertEqual(self.m.inspect(self.ticket,lambda:different_save_same_observables),'SAME_OBSERVATION_IDENTITY_UNPROVEN')
 def test_disappeared_context(self):
  self.assertEqual(self.m.inspect(self.ticket,lambda:(_ for _ in ()).throw(OSError())),'UNAVAILABLE');self.assertIsNone(self.m.observation)
 def test_invalid_discovery(self):
  with self.assertRaises(ValueError):self.m.synchronize(lambda:{})
  self.assertIsNone(self.m.observation)
 def test_never_authorizes(self):
  with self.assertRaises(RuntimeError):self.m.authorize()
if __name__=='__main__':unittest.main(verbosity=2)
