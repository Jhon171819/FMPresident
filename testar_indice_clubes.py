import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from indice_clubes import ClubIndex
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.idx=ClubIndex(Path(self.tmp.name)/'index.sqlite3');self.addCleanup(self.idx.close)
  self.p={'pid':10,'started':'one'};self.digest='a'*64
  self.a=SimpleNamespace(address=123,club=SimpleNamespace(uid=104749,name='Ceará Sporting Club'))
  self.b=SimpleNamespace(address=456,club=SimpleNamespace(uid=42,name='Fortaleza'))
  self.idx.put(self.p,self.digest,[self.a,self.b])
 def test_prefix_accent_and_case(self):self.assertEqual(self.idx.find(self.p,self.digest,'CEARA')[0][1],104749)
 def test_uid(self):self.assertEqual(self.idx.find(self.p,self.digest,'42')[0][2],'Fortaleza')
 def test_no_cross_process(self):self.assertEqual(self.idx.find({'pid':10,'started':'two'},self.digest),[])
 def test_no_cross_build(self):self.assertEqual(self.idx.find(self.p,'b'*64),[])
 def test_large_numeric_query(self):self.assertEqual(self.idx.find(self.p,self.digest,'9'*100),[])
 def test_parameterized_search(self):self.assertEqual(self.idx.find(self.p,self.digest,"%' OR 1=1 --"),[])
 def test_replace(self):
  self.idx.put(self.p,self.digest,[self.a]);self.assertEqual(len(self.idx.find(self.p,self.digest)),2)
if __name__=='__main__':unittest.main(verbosity=2)
