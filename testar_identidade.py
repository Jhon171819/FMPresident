from datetime import date
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import compatibilidade as compat
import identidade as identity
import contratos_dados as contracts
import fm23
import emprestimos

class Build:
    def __init__(self):
        self.ok=True
        self.result=SimpleNamespace(process=contracts.ProcessIdentity(12,'start','test',100))
    def require_fast(self):
        if not self.ok: raise RuntimeError('build changed')
    def require_full(self): self.require_fast()

class FakeMemory:
    def __init__(self):self.data={}
    def put(self,a,raw):self.data.update({a+i:b for i,b in enumerate(raw)})
    def read(self,a,n):return bytes(self.data.get(a+i,0) for i in range(n))
    def number(self,a,fmt='i'):return struct.unpack('<'+fmt,self.read(a,struct.calcsize(fmt)))[0]
    def pointer(self,a):return self.number(a,'Q')
    def regions(self):return [(0x10000,0x5000)]

def fixture(uid=11,name=b'Clube A'):
    m=FakeMemory();base=0x100000;club=0x11000
    m.put(club,struct.pack('<Q',base+0x100));m.put(club+12,struct.pack('<I',uid))
    m.put(club+184,struct.pack('<Q',0x12000));m.put(0x12004,name+b'\0')
    m.put(club+328,struct.pack('<Q',0x13000));m.put(club+248,struct.pack('<Q',0x14000))
    m.put(0x13008,struct.pack('<Q',club));m.put(0x13014,struct.pack('<i',100))
    return m,base,club

class IdentityTests(unittest.TestCase):
    def setUp(self):self.build=Build();self.m,self.base,self.addr=fixture()
    def candidate(self):return identity.inspect_candidate(self.m,self.base,self.addr,0x100,{'treino':0})
    def test_candidate_dynamic_not_ceara(self):
        c=self.candidate();self.assertEqual((c.club.uid,c.club.name),(11,'Clube A'))
    def test_discovery_multiple_never_selects(self):
        m,base,addr=fixture();other,_,_=fixture(22,b'Clube B')
        for a,b in other.data.items():
            target=a+0x5000 if 0x11000<=a<0x15000 else a
            m.data[target]=b
        # Independently validated candidates supplied to discovery; no automatic selection.
        with patch.object(identity,'inspect_candidate',side_effect=[identity.Candidate(contracts.ClubIdentity(11,'A'),0x11000),identity.Candidate(contracts.ClubIdentity(22,'B'),0x16000)]):
            m.put(0x16000,struct.pack('<Q',base+0x100));m.regions=lambda:[(0x10000,0x7000)]
            self.assertEqual(len(list(identity.discover_candidates(m,base,0x100,{}))),2)
    def test_no_clubs(self):
        self.m.put(self.addr,b'\0'*8);self.assertIsNone(self.candidate())
    def test_broken_financial_link(self):
        self.m.put(0x13008,struct.pack('<Q',0x22222));self.assertIsNone(self.candidate())
    def test_stale_pointer(self):
        self.m.put(self.addr,b'\0'*8);self.assertIsNone(self.candidate())
    def test_club_and_date_do_not_prove_career_or_human(self):
        g=identity.CareerGuard(self.build,self.candidate(),date(2032,4,20))
        self.assertEqual(g.result.state,identity.State.UNVERIFIED)
        self.assertEqual(g.result.career.career_id.validation,contracts.Verification.UNKNOWN)
        self.assertEqual(g.result.career.controlled_club.validation,contracts.Verification.UNKNOWN)
        with self.assertRaises(identity.IdentityError):g.require()
    def test_same_club_and_date_different_saves_remain_unknown(self):
        a=identity.CareerGuard(self.build,self.candidate(),date(2032,4,20))
        b=identity.CareerGuard(self.build,self.candidate(),date(2032,4,20))
        for g in (a,b):
            with self.assertRaises(identity.IdentityError):g.require()
    def test_build_change_invalidates(self):
        g=identity.CareerGuard(self.build);self.build.ok=False
        with self.assertRaisesRegex(RuntimeError,'build changed'):g.require()
    def test_missing_career_manager_and_club(self):
        g=identity.CareerGuard(self.build)
        self.assertIsNone(g.result.candidate);self.assertIsNone(g.result.career)
        with self.assertRaises(identity.IdentityError):g.require()
    def test_no_native_write_from_unverified_context(self):
        m=fm23.Memory.__new__(fm23.Memory);m.guard=self.build;m.career_guard=identity.CareerGuard(self.build)
        with patch.object(fm23.k,'WriteProcessMemory') as write:
            with self.assertRaises(identity.IdentityError):m.write(0x10000,b'x')
            write.assert_not_called()
    def test_transaction_loans_and_repay_stop_before_pause_or_write(self):
        fm=fm23.FM.__new__(fm23.FM);fm.guard=self.build;fm.career_guard=identity.CareerGuard(self.build)
        fm.mem=SimpleNamespace(write=unittest.mock.Mock(),paused=unittest.mock.Mock())
        for fn in (lambda:fm.transaction('x',[{}]),lambda:emprestimos.sign(fm,{}),lambda:emprestimos.repay(fm,0,'')):
            with self.assertRaises(identity.IdentityError):fn()
        fm.mem.paused.assert_not_called();fm.mem.write.assert_not_called()
    def test_missing_fm(self):
        with patch('processos_windows.enumerate_processes',return_value=[]):
            with self.assertRaises(RuntimeError):fm23.process_info()

class ManualTests(unittest.TestCase):
    def test_manual_approval_revalidates_and_revokes(self):
        build=Build();calls=[];guard=identity.ManualCareerGuard(build,lambda:calls.append(1))
        guard.require();self.assertEqual(calls,[1]);guard.revoke()
        with self.assertRaises(identity.IdentityError):guard.require()
    def test_manual_failure_permanently_invalidates(self):
        build=Build();guard=identity.ManualCareerGuard(build,lambda:(_ for _ in ()).throw(ValueError('mudou')))
        with self.assertRaises(ValueError):guard.require()
        with self.assertRaises(identity.IdentityError):guard.require()
    def test_manual_build_failure_invalidates(self):
        build=Build();guard=identity.ManualCareerGuard(build,lambda:None);build.ok=False
        with self.assertRaises(RuntimeError):guard.require()
        build.ok=True
        with self.assertRaises(identity.IdentityError):guard.require()

if __name__=='__main__':unittest.main(verbosity=2)
