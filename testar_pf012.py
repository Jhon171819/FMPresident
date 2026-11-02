import ctypes as C,unittest
from unittest.mock import patch,Mock
import fm23 as n,processos_windows as p
class Tests(unittest.TestCase):
 def test_unique(self):self.assertEqual(p.unique_pid([(1,'other.exe'),(2,'FM.EXE')]),2)
 def test_absent(self):
  with self.assertRaises(RuntimeError):p.unique_pid([])
 def test_multiple(self):
  with self.assertRaises(RuntimeError):p.unique_pid([(1,'fm.exe'),(2,'fm.exe')])
 def test_similar_name(self):
  with self.assertRaises(RuntimeError):p.unique_pid([(1,'fm23.exe')])
 def call(self,identities=None,version_error=False,module_ok=True):
  self.closed=Mock();info={'pid':1,'started':'time','path':'C:/game/fm.exe','base':100,'size':200}
  probe=Mock();probe.identity.side_effect=identities or [dict(info),dict(info)]
  def modules(h,ptr,size,needed):C.cast(ptr,C.POINTER(C.c_void_p))[0]=100;return module_ok
  with patch.object(p,'enumerate_processes',return_value=[(1,'fm.exe')]),patch.object(n.k,'OpenProcess',return_value=5),patch.object(n.k,'CloseHandle',self.closed),patch.object(n.psapi,'EnumProcessModules',Mock(side_effect=modules)),patch.object(n,'ProcessProbe',return_value=probe),patch.object(p,'product_version',side_effect=OSError('version') if version_error else None,return_value='v'):
   return p.process_info()
 def test_identity_and_close(self):
  self.assertEqual(self.call()['version'],'v');self.closed.assert_called_once_with(5)
 def test_module_error_closes(self):
  with self.assertRaises(OSError):self.call(module_ok=False)
  self.closed.assert_called_once_with(5)
 def test_version_error_closes(self):
  with self.assertRaises(OSError):self.call(version_error=True)
  self.closed.assert_called_once_with(5)
 def test_changed_instance_rejected(self):
  a={'pid':1,'started':'a','path':'C:/fm.exe','base':100,'size':200};b=dict(a,started='b')
  with self.assertRaises(OSError):self.call([a,b])
  self.closed.assert_called_once_with(5)
 def test_wrong_executable_rejected(self):
  a={'pid':1,'started':'a','path':'C:/wrong.exe','base':100,'size':200}
  with self.assertRaises(OSError):self.call([a,a])
  self.closed.assert_called_once_with(5)
 def test_access_denied(self):
  with patch.object(p,'enumerate_processes',return_value=[(1,'fm.exe')]),patch.object(n.k,'OpenProcess',return_value=0):
   with self.assertRaises(OSError):p.process_info()
if __name__=='__main__':unittest.main(verbosity=2)
