"""Testes offline TC-01.1C; --benchmark gera medições com 2.000 histórias."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import time
import unittest
from datetime import date
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'engenharia_reversa'))
from tc011c_sondar import sample_player
from er01 import Store,SnapshotReads,digest
from er01_storybook import Storybook,seed_stories
from er01_static import process_usage,import_legacy,read_hierarchy
from evidencias_taticas import text_candidate,vector_bounds
from sincronizacao_hibrida import Coordinator,Observation


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'test.sqlite3');self.addCleanup(self.store.close)
        self.book=Storybook(self.store);self.body=next(seed_stories())

    def put(self,body=None):
        return self.book.put(body or self.body,reason='ensaio explícito',tool='unittest',context={'fixture':True})

    def test_create_persistence_and_evidence(self):
        self.put();self.assertEqual(self.book.show('ST-01')['evidence'],self.body['evidence'])
        with Store(self.store.path) as store:self.assertEqual(Storybook(store).show('ST-01')['revision'],1)

    def test_idempotent_and_equivalence(self):
        self.put();self.assertFalse(self.put()['changed'])
        another=self.body|{'id':'DUPLICATE'}
        with self.assertRaises(ValueError):self.put(another)
        self.assertEqual(len(self.book.show('ST-01')['history']),1)

    def test_search_index_migration_preserves_history(self):
        self.put()
        with self.store.db:
            self.store.db.execute('UPDATE storybook_meta SET version=1')
            self.store.db.execute('DELETE FROM story_search')
            self.store.db.execute('INSERT INTO story_search(rowid,id,build,body) VALUES (99,?,?,?)',('ST-01',self.body['build'],json.dumps(self.body)))
        migrated=Storybook(self.store)
        self.assertEqual(len(migrated.search('0x38')),1)
        self.assertEqual(len(migrated.show('ST-01')['history']),1)

    def test_update_refute_reopen_history(self):
        self.put()
        for status in ('REFUTED','HYPOTHESIS','PARTIAL'):
            self.body['status']=status;self.put()
        h=self.book.show('ST-01')['history']
        self.assertEqual([x['new_status'] for x in h],['PARTIAL','REFUTED','HYPOTHESIS','PARTIAL'])
        self.assertEqual(h[2]['previous_status'],'REFUTED')
        self.assertEqual(h[0]['body']['status'],'PARTIAL')
        self.assertTrue(all(x['reason'] and x['tool'] and x['timestamp'] and x['context'] and x['evidence'] for x in h))

    def test_search_filters_literal_and_index(self):
        for body in seed_stories():self.put(body)
        self.assertEqual(len(self.book.search(category='collections')),1)
        self.assertIn('ST-03',[x['id'] for x in self.book.search('0x2B8')])
        self.assertEqual(len(self.book.search(object='ACTUAL_PLAYER')),2)
        self.assertIn('ST-07',[x['id'] for x in self.book.search('0x3A88400')])
        self.assertEqual(len(self.book.search(status='UNMAPPED')),1)
        self.assertEqual(self.book.search(build='different'),[])
        self.assertEqual(self.book.search('" OR *'),[])
        self.assertEqual(len(self.book.search(limit=3,offset=3)),3)

    def test_unmapped_excludes_closed(self):
        self.put();self.assertEqual(len(self.book.search(unmapped=True)),1)
        self.body['status']='REFUTED';self.put();self.assertEqual(self.book.search(unmapped=True),[])

    def test_new_build_not_promoted(self):
        self.put();self.assertEqual(self.book.show('ST-01',target_build='new')['applicability'],'UNVERIFIED_OTHER_BUILD')
        self.put(self.body|{'build':'new'})
        with self.assertRaises(ValueError):self.book.show('ST-01')
        self.assertEqual(len(self.book.search()),2)

    def test_description_required(self):
        for value in ('',None,42):
            with self.subTest(value=value),self.assertRaises(ValueError):self.put(self.body|{'functional_description':value})

    def test_hypothesis_never_auto_verified(self):
        self.body['functional_description']='Hipótese: carrega todos os jogadores, ainda sem prova.'
        self.put();self.assertEqual(self.book.show('ST-01')['status'],'PARTIAL')
        with self.assertRaises(ValueError):self.put(self.body|{'status':'VERIFIED'})

    def test_explicit_scoped_verification(self):
        body=copy.deepcopy(self.body);body['status']='VERIFIED';body['verified_scope']='Somente formato de vetor em fixture'
        body['evidence'][0]['status']='VERIFIED';self.put(body)
        self.assertEqual(self.book.show('ST-01')['verified_scope'],body['verified_scope'])

    def test_source_link_required(self):
        body=copy.deepcopy(self.body);body['sources']=[]
        with self.assertRaises(ValueError):self.put(body)

    def test_relation_without_evidence_rejected(self):
        with self.assertRaises(ValueError):self.put(self.body|{'evidence':[]})
        body=copy.deepcopy(self.body);body['evidence'][0]['source']='unknown'
        with self.assertRaises(ValueError):self.put(body)

    def test_history_requires_context(self):
        with self.assertRaises(ValueError):self.book.put(self.body,reason='',tool='x',context={})

    def test_export_and_manifest(self):
        for body in seed_stories():self.put(body)
        folder=Path(self.temp.name)/'export';result=self.book.export(folder)
        self.assertEqual(result['stories'],10)
        for name,sha in result['manifest']['files'].items():self.assertEqual(digest((folder/name).read_bytes()),sha)
        snapshot=json.loads((folder/'snapshot.json').read_text(encoding='utf8'))
        self.assertEqual(snapshot[0]['history'][0]['body']['status'],'PARTIAL')
        self.assertIn('ST-10',(folder/'catalogo.md').read_text(encoding='utf8'))
        old=result['manifest'];self.assertEqual(self.book.export(folder)['manifest'],old)

    def test_export_consistent_during_concurrent_update(self):
        from unittest.mock import patch
        self.put();folder=Path(self.temp.name)/'snapshot'
        original=self.book.show
        with Store(self.store.path) as other:
            book2=Storybook(other);updated=[False]
            def show(*args,**kwargs):
                if not updated[0]:
                    book2.put(self.body|{'status':'REFUTED'},reason='Nova evidência',tool='writer2',context={'fixture':True})
                    updated[0]=True
                return original(*args,**kwargs)
            with patch.object(self.book,'show',side_effect=show):self.book.export(folder)
        snapshot=json.loads((folder/'snapshot.json').read_text(encoding='utf8'))
        self.assertEqual(snapshot[0]['revision'],1)
        self.assertEqual(snapshot[0]['status'],'PARTIAL')
        self.assertEqual(self.book.show('ST-01')['status'],'REFUTED')

    def test_cli_offline(self):
        import subprocess
        cli=Path(__file__).resolve().parent/'engenharia_reversa/cli.py'
        def run(*args):
            p=subprocess.run([sys.executable,str(cli),'--db',str(self.store.path),'storybook',*args],capture_output=True,text=True,encoding='utf8',check=True)
            return json.loads(p.stdout)
        self.assertEqual(len(run('seed')),10)
        self.assertTrue(all(not r['changed'] for r in run('seed')))
        self.assertEqual(run('show','ST-03')['status'],'PARTIAL')
        self.assertTrue(any(r['id']=='ST-03' for r in run('search','0x2B8')))
        self.assertEqual(len(run('unmapped')),10)
        self.assertEqual(run('export','--folder',str(Path(self.temp.name)/'cli'))['stories'],10)

    def test_opportunity_actual_counts_and_resolution(self):
        for body in seed_stories():self.put(body)
        p=self.book.opportunities()['priorities'][0]
        self.assertEqual(p['count'],len(p['stories']))
        self.assertEqual(p['blocker'],'UNVERIFIED_POINTER_CHAIN');self.assertEqual(p['count'],5)
        body=self.book.show('ST-04');body['status']='DEPRECATED';self.put(body)
        self.assertEqual(self.book.opportunities()['priorities'][0]['count'],4)

    def test_unsafe_id_and_blocker(self):
        with self.assertRaises(ValueError):self.put(self.body|{'id':'../escape'})
        with self.assertRaises(ValueError):self.put(self.body|{'blockers':['invented']})

    def test_cache_complete_partial_legacy_and_import(self):
        binary=self.store.binary({'sha256':'fixture'})
        for partial in (False,True):
            params={'partial':partial}
            _,first=self.store.cached(binary,'graph',123,'v1',params,lambda:{'bounded':partial})
            _,second=self.store.cached(binary,'graph',123,'v1',params,lambda:1/0)
            self.assertEqual((first['computed'],second['hit']),(1,1))
            self.assertEqual(second['state'],'PARTIAL' if partial else 'COMPLETE')
        legacy=Path(self.temp.name)/'legacy';legacy.mkdir()
        (legacy/'grafos.json').write_text(json.dumps([{'start':42,'instructions':[],'bounded':True}]))
        self.assertEqual(import_legacy(self.store,legacy,binary)['graphs'],1)
        self.assertEqual(self.store.db.execute("SELECT state FROM artifacts WHERE kind='legacy_graph'").fetchone()[0],'LEGACY_UNVERIFIED')


class DiagnosticTests(unittest.TestCase):
    def snapshot(self,source=lambda a,n:bytes(n),validate=lambda c:True):
        s=SnapshotReads(source,{'fixture':True},validate,[(0x10000,0x20000)])
        self.addCleanup(s.close);return s

    def test_names_valid_invalid_utf8_absent(self):
        self.assertEqual(text_candidate('Claudio Jeremías Echeverri'.encode())['status'],'HYPOTHESIS')
        for raw in (b'',b'1234',b'\xff',b'\0',b'a'*81):
            with self.subTest(raw=raw),self.assertRaises((ValueError,UnicodeError)):text_candidate(raw)

    def test_no_uid_without_independent_proof(self):
        story=[s for s in seed_stories() if s['id']=='ST-10'][0]
        self.assertEqual(story['status'],'INCONCLUSIVE')
        self.assertIn('MISSING_UID',story['blockers'])
        self.assertFalse(any(e['status']=='VERIFIED' for e in story['evidence']))

    def test_duplicate_uid_not_identity(self):
        # Dos enteros repetidos no se deriva identidad; el catálogo registra la excepción.
        with tempfile.TemporaryDirectory() as folder,Store(Path(folder)/'s.sqlite3') as store:
            book=Storybook(store);body=list(seed_stories())[-1]
            body['observed_behavior']='Fixture: dos objetos comparten candidato entero 42; UID descartado en esta fixture.'
            book.put(body,reason='Candidato duplicado',tool='fixture',context={'uid_candidates':[42,42]})
            self.assertEqual(book.show('ST-10')['status'],'INCONCLUSIVE')

    def test_other_team_not_universal(self):
        body=list(seed_stories())[1]
        self.assertIn('refutada',body['hypothesis']);self.assertNotEqual(body['status'],'VERIFIED')

    def sample(self,ptr=0x10000,text=b'Fernando Nava\0',team=0x20000):
        raw=bytearray(0x2c0);struct.pack_into('<Q',raw,0x2b8,ptr);struct.pack_into('<Q',raw,0x130,team)
        return sample_player(raw,lambda a,n:(bytes(4)+text).ljust(n,b'\0'),lambda b:date(2004,6,8),expected_team=0x20000)

    def test_diagnostic_statuses_and_team(self):
        self.assertEqual(self.sample()['name'],'Fernando Nava');self.assertIsNone(self.sample()['uid'])
        self.assertEqual(self.sample(ptr=0)['name_status'],'ABSENT_TEXT')
        self.assertEqual(self.sample(ptr=1)['name_status'],'INVALID_POINTER')
        self.assertEqual(self.sample(text=b'\xff')['name_status'],'INVALID_UTF8')
        self.assertEqual(self.sample(text=b'1234')['name_status'],'UNRESOLVED_STRING')
        self.assertFalse(self.sample(team=0x30000)['team_130_matches'])
        self.assertEqual(self.sample(team=0x30000)['confidence'],'HYPOTHESIS')

    def test_diagnostic_partial_and_context_propagated(self):
        with self.assertRaisesRegex(ValueError,'parcial'):sample_player(bytes(10),None,None,expected_team=0)
        raw=bytearray(0x2c0);struct.pack_into('<Q',raw,0x2b8,0x10000)
        def invalid(a,n):raise ValueError('Contexto mudou')
        with self.assertRaisesRegex(ValueError,'Contexto'):sample_player(raw,invalid,lambda b:date(2000,1,1),expected_team=0)
        self.assertEqual(sample_player(raw,lambda a,n:b'abc',lambda b:date(2000,1,1),expected_team=0)['name_status'],'PARTIAL_READ')

    def test_rtti_directed_fixture_and_bound(self):
        class PE:
            def rtti(self,v):return {'hierarchy_rva':100}
            def string(self,r):return '.?AVPERSON@db@@'
            def read(self,r,n):return {100:struct.pack('<IIII',0,3,1,200),200:struct.pack('<I',300),300:struct.pack('<IIiiiII',400,0,0,8,4,80,500)}[r]
        result=read_hierarchy(PE(),123)
        self.assertEqual(result['bases'][0]['pdisp'],8);self.assertEqual(result['bases'][0]['vdisp'],4)
        with self.assertRaises(ValueError):read_hierarchy(PE(),123,max_bases=0)

    def test_cycle(self):
        s=self.snapshot(lambda a,n:struct.pack('<Q',0x10000))
        with self.assertRaisesRegex(ValueError,'Ciclo'):s.follow(0x10000,[0])

    def test_invalid_pointer(self):
        with self.assertRaises(ValueError):self.snapshot().read(1,8)

    def test_closed_context(self):
        s=self.snapshot();s.close()
        with self.assertRaises(ValueError):s.read(0x10000,8)

    def test_partial_read(self):
        s=self.snapshot(lambda a,n:b'x')
        with self.assertRaisesRegex(ValueError,'truncada'):s.read(0x10000,8)
        self.assertEqual(s.failures,1)

    def test_stale_result(self):
        valid=[True];s=self.snapshot(validate=lambda c:valid[0]);s.read(0x10000,8);valid[0]=False
        with self.assertRaises(ValueError):s.read(0x10000,8)
        self.assertFalse(s.cache)
        c=Coordinator();epoch=c.begin();new=c.begin()
        self.assertFalse(c.finish(epoch,Observation(None,'fixture','now')))
        self.assertTrue(c.finish(new,Observation(None,'fixture','now')))

    def test_deduplicated_and_inconsistent(self):
        source=[b'abcdefgh'];s=self.snapshot(lambda a,n:source[0][:n])
        self.assertEqual(s.batch([(0x10000,8),(0x10000,4)]),[b'abcdefgh',b'abcd'])
        self.assertEqual(s.calls,1);source[0]=b'12345678'
        with self.assertRaisesRegex(ValueError,'inconsistente'):s.read(0x10000,8,fresh=True)
        self.assertTrue(s.closed)


def benchmark(output):
    result={'fixture':True,'count':2000,'evidence_per_story':6,'phases':{}}
    with tempfile.TemporaryDirectory(prefix='tc011c-') as folder,Store(Path(folder)/'fixture.sqlite3') as store:
        book=Storybook(store);template=next(seed_stories());wall=time.perf_counter();cpu=time.process_time()
        def measure(name,fn):
            t=time.perf_counter();c=time.process_time();value=fn()
            result['phases'][name]={'wall_s':time.perf_counter()-t,'cpu_s':time.process_time()-c}
            return value
        def load():
            for i in range(result['count']):
                body=copy.deepcopy(template);body.update(id=f'FIX-{i:05}',hypothesis=f'Hipótese fixture {i}',object=f'TEAM_{i%20}')
                body['evidence']*=6;book.put(body,reason='Fixture',tool='benchmark',context={'fixture':True})
        measure('import',load)
        for name,kwargs in [('list',{}),('text',{'query':'0x38'}),('class',{'object':'TEAM_1'}),('category',{'category':'collections'})]:
            values=measure(name,lambda:book.search(limit=10000,**kwargs));result['phases'][name]['matches']=len(values)
        body=book.show('FIX-00001');body['observed_behavior']+=' Atualização medida.'
        measure('incremental_update',lambda:book.put(body,reason='Nova observação fixture',tool='benchmark',context={'fixture':True}))
        export=measure('export',lambda:book.export(Path(folder)/'export'))
        result.update(wall_s=time.perf_counter()-wall,cpu_s=time.process_time()-cpu,process_usage=process_usage(),
                      database_bytes=store.path.stat().st_size,exported_stories=export['stories'],status_counts=[dict(r) for r in store.db.execute('SELECT status,count(*) AS count FROM stories GROUP BY status')])
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import sys
    if '--benchmark' in sys.argv:benchmark(sys.argv[sys.argv.index('--benchmark')+1])
    else:unittest.main()
