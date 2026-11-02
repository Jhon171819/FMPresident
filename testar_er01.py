import json,struct,tempfile,threading,time,unittest
from pathlib import Path
from er01 import Store,SnapshotReads
from er01_static import import_legacy

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'cache.sqlite3';self.s=Store(self.path);self.addCleanup(self.s.close)
        self.binary=self.s.binary({'sha256':'fixture','size':3});self.calls=0
    def compute(self):self.calls+=1;return {'value':42}
    def get(self,**kw):return self.s.cached(self.binary,'graph','123','v1',kw,self.compute)
    def test_cold_warm(self):
        self.assertEqual(self.get()[1]['computed'],1);self.assertEqual(self.get()[1]['hit'],1);self.assertEqual(self.calls,1)
    def test_partial_not_complete(self):
        v,m=self.s.cached(self.binary,'g',1,'v',{},lambda:{'bounded':True});self.assertEqual(m['state'],'PARTIAL')
        self.assertEqual(self.s.cached(self.binary,'g',1,'v',{},lambda: self.fail())[1]['hit'],1)
    def test_config_changes(self):self.get(a=1);self.get(a=2);self.assertEqual(self.calls,2)
    def test_algorithm_changes(self):
        self.get();self.s.cached(self.binary,'graph','123','v2',{},self.compute);self.assertEqual(self.calls,2)
    def test_binary_changes(self):
        self.get();b=self.s.binary({'sha256':'other'});self.s.cached(b,'graph','123','v1',{},self.compute);self.assertEqual(self.calls,2)
    def test_corruption(self):
        _,m=self.get()
        with self.s.db:self.s.db.execute('UPDATE artifacts SET payload=? WHERE key=?',(b'bad',m['key']))
        self.get();self.assertEqual(self.calls,2)
    def test_force(self):
        self.get();self.s.cached(self.binary,'graph','123','v1',{},self.compute,True);self.assertEqual(self.calls,2)
    def test_selective_invalidation(self):
        _,a=self.get(a=1);_,b=self.get(a=2);_,c=self.get(a=3)
        with self.s.db:self.s.db.execute('INSERT INTO dependencies VALUES (?,?)',(a['key'],b['key']))
        self.assertEqual(len(self.s.invalidate([a['key']])),2);self.assertIsNotNone(self.s.get(a['key']))
        self.s.invalidate([a['key']],False);self.assertIsNone(self.s.get(b['key']));self.assertIsNotNone(self.s.get(c['key']))
    def test_interrupted_compute_rollback(self):
        with self.assertRaises(KeyboardInterrupt):self.s.cached(self.binary,'g',1,'v',{},lambda:(_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM artifacts').fetchone()[0],0)
    def test_task_input_changes(self):
        self.s.task('t',{'rvas':[1]})
        with self.assertRaises(ValueError):self.s.task('t',{'rvas':[2]})
    def test_invalid_mapped_pe_releases_file(self):
        import sys
        sys.path.insert(0,str(Path(__file__).parent/'engenharia_reversa'))
        from analisar_executavel import PE
        path=Path(self.tmp.name)/'invalid.exe';path.write_bytes(b'not a PE')
        with self.assertRaises(ValueError):PE(path,mapped=True)
        path.unlink();self.assertFalse(path.exists())
    def test_checkpoint(self):
        self.s.task('t',{'rvas':[1,2]});self.s.checkpoint('t',[1],[2],'INTERRUPTED')
        self.assertEqual(json.loads(self.s.task('t',{'rvas':[1,2]})['checkpoint'])['frontier'],[2])
    def test_evidence_no_promotion(self):
        self.s.evidence('h','PARTIAL',{'observations':100},'fixture');self.assertEqual(self.s.db.execute('SELECT status FROM evidence').fetchone()[0],'PARTIAL')
    def test_provenance_required(self):
        with self.assertRaises(ValueError):self.s.evidence('h','OBSERVED',{},'')
    def test_graph_cycle_depth(self):
        with self.s.db:
            for a,b in [('a','b'),('b','a'),('b','c')]:self.s.db.execute('INSERT INTO edges VALUES (?,?,?,?,?,?)',(self.binary,a,b,'call','STATIC','fixture'))
        r=self.s.walk(self.binary,'a');self.assertEqual(r['nodes'],['a','b','c'])
        self.assertEqual(self.s.walk(self.binary,'a',depth=1)['nodes'],['a','b'])
    def test_refuted_edges(self):
        with self.s.db:self.s.db.execute('INSERT INTO edges VALUES (?,?,?,?,?,?)',(self.binary,'a','b','x','REFUTED','fixture'))
        self.assertEqual(self.s.walk(self.binary,'a')['edges'],[])
    def test_graph_resume_frontier(self):
        with self.s.db:
            for a,b in [('a','b'),('b','c')]:self.s.db.execute('INSERT INTO edges VALUES (?,?,?,?,?,?)',(self.binary,a,b,'call','STATIC','fixture'))
        first=self.s.walk(self.binary,'a',nodes=1)
        second=self.s.walk(self.binary,'a',nodes=10,checkpoint=first)
        self.assertEqual(second['nodes'],['a','b','c']);self.assertEqual(len(second['edges']),2)
    def test_legacy_idempotent(self):
        p=Path(self.tmp.name)/'grafos.json';p.write_text(json.dumps([{'start':1,'instructions':[],'bounded':True}]))
        import_legacy(self.s,p.parent,self.binary);import_legacy(self.s,p.parent,self.binary)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM artifacts').fetchone()[0],1)
        self.assertEqual(self.s.db.execute('SELECT state FROM artifacts').fetchone()[0],'LEGACY_UNVERIFIED')
    def test_planner_dependencies(self):
        self.s.task('b',{'dependencies':['a'],'priority':99});self.s.task('a',{})
        self.assertEqual(self.s.plan()[0]['id'],'a');self.s.checkpoint('a',[],[],'COMPLETE');self.assertTrue(self.s.plan()[0]['ready'])
    def test_concurrent_single_compute(self):
        errors=[];counter=[]
        def work():
            try:
                with Store(self.path) as s:
                    def fn():counter.append(1);time.sleep(.03);return {'x':1}
                    s.cached(self.binary,'g',1,'v',{},fn)
            except Exception as e:errors.append(e)
        ts=[threading.Thread(target=work) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertFalse(errors);self.assertEqual(len(counter),1)

class Reads(unittest.TestCase):
    def make(self,source=None,**limits):return SnapshotReads(source or (lambda a,n:bytes((a-0x10000+i)%256 for i in range(n))),('pid','started','epoch'),lambda c:True,[(0x10000,0x10100)],**limits)
    def test_repeat_and_group(self):
        r=self.make();out=r.batch([(0x10000,4),(0x10004,4),(0x10000,4)]);self.assertEqual(r.calls,1);self.assertEqual(out,[bytes(range(4)),bytes(range(4,8)),bytes(range(4))]);self.assertEqual(r.bytes,8)
    def test_non_groupable(self):
        r=self.make();r.batch([(0x10000,4),(0x10010,4)]);self.assertEqual(r.calls,2)
    def test_no_cross_region(self):
        with self.assertRaises(ValueError):self.make().read(0x100fe,4)
    def test_invalid_pointer(self):
        with self.assertRaises(ValueError):self.make().read(0,1)
    def test_context(self):
        r=self.make();r.validate=lambda c:False
        with self.assertRaises(ValueError):r.read(0x10000,4)
    def test_budget(self):
        with self.assertRaises(ValueError):self.make(byte_limit=2).read(0x10000,4)
    def test_truncated_failure(self):
        r=self.make(lambda a,n:b'')
        with self.assertRaises(ValueError):r.read(0x10000,4)
        self.assertEqual(r.failures,1)
    def test_inconsistent(self):
        values=iter([b'aaaa',b'bbbb']);r=self.make(lambda a,n:next(values));r.read(0x10000,4)
        with self.assertRaises(ValueError):r.read(0x10000,4,fresh=True)
        self.assertTrue(r.closed)
    def test_cycle(self):
        with self.assertRaises(ValueError):self.make(lambda a,n:struct.pack('<Q',a)).follow(0x10000,[0])
    def test_overlap_inconsistency(self):
        values=iter([b'abcdefgh',b'zzzz']);r=self.make(lambda a,n:next(values));r.read(0x10000,8)
        with self.assertRaises(ValueError):r.read(0x10004,4,fresh=True)
    def test_close(self):
        r=self.make();r.close()
        with self.assertRaises(ValueError):r.read(0x10000,4)

if __name__=='__main__':unittest.main(verbosity=2)
