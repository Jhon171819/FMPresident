import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import compatibilidade as c
import fm23
import emprestimos

class Probe:
    def __init__(self, info): self.data=dict(info); self.bytes=b'ABCD'; self.error=None
    def identity(self):
        if self.error: raise self.error
        return dict(self.data)
    def sample(self, address, size): return self.bytes

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'fm.exe'
        data=bytearray(256); data[:2]=b'MZ'; data[60:64]=(128).to_bytes(4,'little');data[128:132]=b'PE\0\0';data[132:134]=(0x8664).to_bytes(2,'little');self.path.write_bytes(data)
        digest,_,_=c.fingerprint(self.path)
        self.info=dict(pid=123,started='1234',path=str(self.path),base=0x10000,size=999,version='test')
        self.probe=Probe(self.info)
        self.profile=c.Profile('teste','test',999,digest,0x8664,((0,b'ABCD'),),True)
        self.mock=patch.object(c,'PROFILES',(self.profile,));self.mock.start();self.addCleanup(self.mock.stop)
    def guard(self):return c.BuildGuard(self.info,self.probe)
    def rejected(self,state):
        with self.assertRaises(c.CompatibilityError) as ex:self.guard()
        self.assertEqual(ex.exception.result.state,state)
        return ex.exception.result
    def test_verified_and_contract(self):
        g=self.guard();self.assertEqual(g.result.state,c.State.VERIFIED);g.require_full();self.assertEqual(g.result.process.sha256.source,c.Source.LOCAL_STORAGE);self.assertNotIn(str(self.path),g.result.diagnostic_json())
    def test_pending_profile(self):
        with patch.object(c,'PROFILES',(c.replace(self.profile,homologated=False),)):
            self.assertTrue(self.rejected(c.State.UNVERIFIED).module_samples_match)
    def test_unknown_hash_same_version_size(self):
        self.path.write_bytes(self.path.read_bytes()[:-1]+b'x');self.rejected(c.State.UNSUPPORTED)
    def test_no_profile(self):
        with patch.object(c,'PROFILES',()):self.rejected(c.State.UNSUPPORTED)
    def test_sample_mismatch(self):
        self.probe.bytes=b'XXXX';self.rejected(c.State.UNVERIFIED)
    def test_access_denied(self):
        self.probe.error=PermissionError();self.rejected(c.State.ERROR)
    def test_no_process(self):
        self.probe.error=ProcessLookupError();self.rejected(c.State.ERROR)
    def test_missing_path(self):
        self.info['path']='';self.rejected(c.State.ERROR)
    def test_inaccessible_file(self):
        self.path.unlink();self.rejected(c.State.ERROR)
    def test_incomplete_metadata(self):
        self.info['version']='';self.rejected(c.State.ERROR)
    def test_pid_changed(self):
        self.probe.data['pid']=124;self.rejected(c.State.ERROR)
    def test_pid_reused(self):
        self.probe.data['started']='different';self.rejected(c.State.ERROR)
    def test_process_ends_during_verification(self):
        old=self.probe.identity; calls=[]
        def identity():
            calls.append(1)
            if len(calls)>1:raise ProcessLookupError()
            return old()
        self.probe.identity=identity;self.rejected(c.State.ERROR)
    def test_file_replaced(self):
        g=self.guard();self.path.unlink();self.path.write_bytes(b'new')
        with self.assertRaises(c.CompatibilityError):g.require_fast()
        self.assertEqual(g.result.state,c.State.ERROR)
    def test_context_change_after_verified(self):
        g=self.guard();self.probe.data['started']='other'
        with self.assertRaises(c.CompatibilityError):g.require_fast()
        self.probe.data['started']='1234'
        with self.assertRaises(c.CompatibilityError):g.require_fast()
    def test_hash_failure(self):
        with patch.object(c,'fingerprint',side_effect=OSError()):self.rejected(c.State.ERROR)
    def test_serialization_failure(self):
        g=self.guard()
        with patch.object(c.json,'dumps',side_effect=TypeError()):self.assertIn('ERROR',g.result.diagnostic_json())
    def test_full_checks_hash_and_samples_again(self):
        g=self.guard();self.probe.bytes=b'XXXX'
        with self.assertRaises(c.CompatibilityError):g.require_full()
    def test_full_rejects_changed_hash_with_restored_metadata(self):
        g=self.guard(); old=self.path.stat(); data=self.path.read_bytes()
        self.path.write_bytes(data[:-1]+b'x')
        import os
        os.utime(self.path, ns=(old.st_atime_ns,old.st_mtime_ns))
        with self.assertRaises(c.CompatibilityError):g.require_full()
    def test_guard_blocks_read_and_pause_without_authorization(self):
        m=fm23.Memory.__new__(fm23.Memory);m.guard=None
        with patch.object(fm23.k,'ReadProcessMemory') as read:
            with self.assertRaises(RuntimeError):m.read(0x10000,4)
            read.assert_not_called()
        with self.assertRaises(RuntimeError):
            with m.paused():pass
    def test_write_rejects_unverified_guard_before_windows_call(self):
        class Rejected:
            def require_fast(self): raise RuntimeError('blocked')
        m=fm23.Memory.__new__(fm23.Memory);m.guard=Rejected()
        with patch.object(fm23.k,'WriteProcessMemory') as write:
            with self.assertRaises(RuntimeError):m.write(100,b'x')
            write.assert_not_called()
    def test_low_level_write_blocked(self):
        m=fm23.Memory.__new__(fm23.Memory);m.guard=None
        with patch.object(fm23.k,'WriteProcessMemory') as write:
            with self.assertRaises(RuntimeError):m.write(100,b'x')
            write.assert_not_called()
    def test_transaction_and_loans_block_before_write(self):
        class Block:
            def require_full(self):raise RuntimeError('blocked')
        class Memory:
            writes=0
            def write(self,*args):self.writes+=1
        fm=fm23.FM.__new__(fm23.FM);fm.guard=Block();fm.mem=Memory()
        for call in (lambda:fm.transaction('x',[{}]),lambda:emprestimos.sign(fm,{}),lambda:emprestimos.repay(fm,0,'')):
            with self.assertRaisesRegex(RuntimeError,'blocked'):call()
        self.assertEqual(fm.mem.writes,0)

if __name__=='__main__':unittest.main(verbosity=2)
