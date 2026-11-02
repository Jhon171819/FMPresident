import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'engenharia_reversa'))
from investigar_identidade import chain,compare,HUMAN_DETAILS
class Reader:
 def __init__(self):self.data={1000:HUMAN_DETAILS+100,1064:2000,2000:100+0x5002398,2048:3000,3000:100+0x4fdcdf8,3012:104749}
 def pointer(self,a):
  if a not in self.data:raise OSError()
  return self.data[a]
 def number(self,a,fmt):return self.pointer(a)
class Tests(unittest.TestCase):
 def test_chain_observed_not_human_proof(self):
  self.assertEqual(chain(Reader(),100,1000)['human_control'],'UNKNOWN')
 def test_null(self):self.assertEqual(chain(Reader(),100,0)['state'],'UNAVAILABLE')
 def test_inaccessible(self):self.assertEqual(chain(Reader(),100,4000)['state'],'UNAVAILABLE')
 def test_wrong_vtable(self):
  r=Reader();r.data[1000]=12;self.assertEqual(chain(r,100,1000)['state'],'WRONG_VTABLE')
 def test_missing_team(self):
  r=Reader();r.data[1064]=0;self.assertEqual(chain(r,100,1000)['state'],'UNAVAILABLE')
 def test_changed_relation(self):
  a=chain(Reader(),100,1000);r=Reader();r.data[3012]=42;b=chain(r,100,1000)
  self.assertEqual(compare({'schema':1,'objects':[a]},{'schema':1,'objects':[b]})['changed'],['0x3e8'])
 def test_empty(self):self.assertEqual(compare({'schema':1,'objects':[]},{'schema':1,'objects':[]})['changed'],[])
 def test_disappeared_and_appeared(self):
  d=compare({'schema':1,'objects':[{'object':'a'}]},{'schema':1,'objects':[{'object':'b'}]});self.assertEqual(d['appeared'],['b']);self.assertEqual(d['disappeared'],['a'])
 def test_invalid_report(self):
  with self.assertRaises(ValueError):compare({}, {})
 def test_unchanged_not_save_proof(self):
  x={'schema':1,'objects':[{'object':'same','club_uid':1}]};self.assertIn('não comprovada',compare(x,x)['interpretation'])
if __name__=='__main__':unittest.main()
