import struct,unittest
from evidencias_taticas import vector_bounds,text_candidate,evidence

class Tests(unittest.TestCase):
    def test_empty(self):self.assertEqual(vector_bounds(bytes(24)),(0,0))
    def test_vector(self):self.assertEqual(vector_bounds(struct.pack('<QQQ',0x10000,0x10010,0x10018)),(0x10000,2))
    def test_truncated(self):
        with self.assertRaises(ValueError):vector_bounds(bytes(16))
    def test_bad_pointer(self):
        with self.assertRaises(ValueError):vector_bounds(struct.pack('<QQQ',8,16,24))
    def test_misaligned(self):
        with self.assertRaises(ValueError):vector_bounds(struct.pack('<QQQ',0x10001,0x10009,0x10011))
    def test_reverse(self):
        with self.assertRaises(ValueError):vector_bounds(struct.pack('<QQQ',0x10010,0x10000,0x10018))
    def test_excessive(self):
        with self.assertRaises(ValueError):vector_bounds(struct.pack('<QQQ',0x10000,0x11000,0x11000))
    def test_utf8(self):self.assertEqual(text_candidate('João'.encode())['status'],'HYPOTHESIS')
    def test_invalid_text(self):
        with self.assertRaises(UnicodeError):text_candidate(b'\xff\xff')
    def test_empty_text(self):
        with self.assertRaises(ValueError):text_candidate(b'\0')
    def test_budget(self):
        with self.assertRaises(ValueError):text_candidate(b'A'*81)
    def test_no_automatic_verification(self):self.assertEqual(evidence('a','b',100,100)['status'],'OBSERVED')
    def test_invalid_evidence(self):
        with self.assertRaises(ValueError):evidence('a','b',-1)
if __name__=='__main__':unittest.main(verbosity=2)
