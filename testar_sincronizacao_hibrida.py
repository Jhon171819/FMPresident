import unittest
from dataclasses import replace
from sincronizacao_hibrida import Coordinator, Observation, State, club_from_details, include_candidate

class Tests(unittest.TestCase):
 def setUp(self):
  self.c=Coordinator();self.o=Observation((10,'start'),'profile','now',104749,100,'2032-05-01')
 def test_late_result_after_new_sync(self):
  a=self.c.begin();b=self.c.begin();self.assertFalse(self.c.finish(a,self.o));self.assertTrue(self.c.finish(b,self.o))
 def test_invalidate_before_discovery(self):
  a=self.c.begin();self.c.finish(a,self.o);b=self.c.begin();self.assertIsNone(self.c.observation);self.assertNotEqual(a,b)
 def test_failure_stays_unverified(self):
  a=self.c.begin();self.c.finish(a,error=OSError());self.assertEqual(self.c.state,State.ERROR);self.assertIsNone(self.c.observation)
 def test_same_observation_does_not_authorize(self):
  a=self.c.begin();self.c.finish(a,self.o);self.c.inspect(a,replace(self.o,observed_at='later'));self.assertEqual(self.c.state,State.OBSERVED_UNVERIFIED)
 def test_change_invalidates(self):
  a=self.c.begin();self.c.finish(a,self.o);self.c.inspect(a,replace(self.o,candidate_address=200));self.assertEqual(self.c.state,State.CONTEXT_CHANGED);self.assertIsNone(self.c.observation)
 def test_late_monitor_does_not_invalidate_new_epoch(self):
  a=self.c.begin();self.c.finish(a,self.o);b=self.c.begin();self.assertFalse(self.c.inspect(a,error=OSError()));self.assertEqual(self.c.state,State.SYNCING);self.c.finish(b,self.o)
 def test_close_discards_result(self):
  a=self.c.begin();self.c.close();self.assertFalse(self.c.finish(a,self.o));self.assertEqual(self.c.state,State.DISCONNECTED)
 def test_missing_identity_is_unknown(self):
  a=self.c.begin();self.c.finish(a,self.o);self.assertEqual(self.c.observation.career,'UNKNOWN');self.assertEqual(self.c.observation.trainer,'UNKNOWN')
 def test_failure_invalidates_monitor(self):
  a=self.c.begin();self.c.finish(a,self.o);self.c.inspect(a,error=OSError());self.assertEqual(self.c.state,State.CONTEXT_CHANGED)
 def test_concurrent_old_result_is_discarded(self):
  import threading
  started=threading.Event();release=threading.Event();results=[];a=self.c.begin()
  def worker():
   started.set();release.wait(5);results.append(self.c.finish(a,self.o))
  t=threading.Thread(target=worker);t.start();self.assertTrue(started.wait(5))
  b=self.c.begin();self.c.finish(b,self.o);release.set();t.join(5)
  self.assertFalse(t.is_alive());self.assertEqual(results,[False]);self.assertEqual(self.c.state,State.OBSERVED_UNVERIFIED)

class ChainTests(unittest.TestCase):
 def test_only_valid_chain(self):
  class Reader:
   def __init__(self):self.data={0x1000:0x48b7c08+0x100000,0x1040:0x2000,0x2000:0x100000+0x5002398,0x2030:0x3000}
   def pointer(self,a):
    if a not in self.data:raise OSError()
    return self.data[a]
  r=Reader();self.assertEqual(club_from_details(r,0x100000,0x1000,0x5002398),0x3000)
  r.data[0x2000]=0;self.assertIsNone(club_from_details(r,0x100000,0x1000,0x5002398))
  self.assertIsNone(club_from_details(r,0x100000,0x3000,0x5002398))
class CandidateTests(unittest.TestCase):
 def test_supported_club_record_is_candidate_only_with_correct_uid_and_alignment(self):
  import struct
  from sincronizacao_hibrida import matching_club_addresses
  data=bytearray(64);struct.pack_into('<Q',data,8,0x1234);struct.pack_into('<I',data,20,104749)
  self.assertEqual(list(matching_club_addresses(data,0x1000,0x1234,104749)),[0x1008])
  self.assertEqual(list(matching_club_addresses(data,0x1000,0x1234,1)),[])
  self.assertEqual(list(matching_club_addresses(data,0x1001,0x1234,104749)),[])
 def test_cache_candidate_and_link_upgrade(self):
  from types import SimpleNamespace
  c=SimpleNamespace(address=123,club=SimpleNamespace(uid=104749,name='Ceará'))
  found={};include_candidate(found,c,'cache');self.assertEqual(found[123].source,'cache')
  include_candidate(found,c,'vinculo');include_candidate(found,c,'cache');self.assertEqual(len(found),1);self.assertEqual(found[123].source,'vinculo')
  include_candidate(found,None,'cache');self.assertEqual(len(found),1)
if __name__=='__main__':unittest.main(verbosity=2)
