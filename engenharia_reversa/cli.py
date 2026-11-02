"""CLI ER-01; offline, sem importação de fm23 ou abertura do processo."""
import argparse,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from er01 import ROOT,Store,canonical
from er01_static import analyze,identity,import_legacy,benchmark,index_class,index_hierarchy
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,default=ROOT/'dados/er01.sqlite3')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('status','plan','evidence','stats','report'):sub.add_parser(name)
    q=sub.add_parser('import');q.add_argument('folder',type=Path);q.add_argument('--exe',required=True)
    q=sub.add_parser('analyze');q.add_argument('--exe',required=True);q.add_argument('--rva',action='append',required=True,type=lambda x:int(x,0));q.add_argument('--instructions',type=int,default=400);q.add_argument('--blocks',type=int,default=50);q.add_argument('--task');q.add_argument('--max-functions',type=int);q.add_argument('--force',action='store_true')
    q=sub.add_parser('resume');q.add_argument('task');q.add_argument('--exe',required=True)
    q=sub.add_parser('task');q.add_argument('id');q.add_argument('--state',choices=['PENDING','PAUSED','CANCELLED','IGNORED']);q.add_argument('--priority',type=int)
    q=sub.add_parser('invalidate');q.add_argument('key',nargs='+');q.add_argument('--apply',action='store_true',help='sem esta opção apenas simula')
    q=sub.add_parser('graph');q.add_argument('binary');q.add_argument('source');q.add_argument('--depth',type=int,default=3)
    q=sub.add_parser('benchmark');q.add_argument('--exe',required=True);q.add_argument('--rva',type=lambda x:int(x,0),action='append',required=True)
    q=sub.add_parser('cache-explain');q.add_argument('key')
    q=sub.add_parser('clean');q.add_argument('--apply',action='store_true')
    q=sub.add_parser('index');q.add_argument('--query',default='');q.add_argument('--kind',default='legacy_class')
    q=sub.add_parser('queue');q.add_argument('id');q.add_argument('spec',type=Path)
    q=sub.add_parser('class');q.add_argument('name');q.add_argument('--exe',required=True)
    q=sub.add_parser('hierarchy');q.add_argument('--exe',required=True);q.add_argument('--vtable',required=True,type=lambda x:int(x,0))
    q=sub.add_parser('storybook',help='catálogo persistente; consultas inteiramente offline')
    sb=q.add_subparsers(dest='action',required=True)
    for name in ('list','search','unmapped','blockers','opportunities','show','export','seed','put'):
        s=sb.add_parser(name)
        s.add_argument('--build')
        if name=='show':
            s.add_argument('id');s.add_argument('--target-build')
        if name in ('list','search','unmapped'):
            if name=='search':s.add_argument('query')
            s.add_argument('--category');s.add_argument('--status');s.add_argument('--object')
            s.add_argument('--limit',type=int,default=100);s.add_argument('--offset',type=int,default=0)
        if name=='export':s.add_argument('--folder',type=Path,default=ROOT/'docs/engenharia-reversa/storybook')
        if name=='put':
            s.add_argument('file',type=Path);s.add_argument('--reason',required=True)
            s.add_argument('--context',required=True,help='JSON do contexto original');s.add_argument('--tool',required=True)
    a=p.parse_args()
    if a.command=='benchmark':
        with tempfile.TemporaryDirectory(prefix='er01-') as folder:
            with Store(Path(folder)/'benchmark.sqlite3') as store:result=benchmark(store,a.exe,a.rva)
    else:
        with Store(a.db) as store:
            if a.command=='storybook':
                from er01_storybook import Storybook,seed_stories
                book=Storybook(store)
                if a.action=='seed':
                    result=[]
                    for body in seed_stories():
                        if a.build and a.build!=body['build']:continue
                        if store.db.execute('SELECT 1 FROM stories WHERE id=? AND build=?',(body['id'],body['build'])).fetchone():
                            result.append({'id':body['id'],'changed':False,'reason':'história existente preservada'})
                        else:result.append(book.put(body,reason='Importação histórica TC-01.1/TC-01.1B',tool='cli.seed',context={'issue':'TC-01.1C','origin':'historical'}))
                elif a.action=='show':result=book.show(a.id,a.build,a.target_build)
                elif a.action=='put':
                    body=json.loads(a.file.read_text(encoding='utf8'))
                    if a.build and body['build']!=a.build:raise ValueError('Build do arquivo divergente')
                    result=book.put(body,reason=a.reason,tool=a.tool,context=json.loads(a.context))
                elif a.action=='export':result=book.export(a.folder,a.build)
                elif a.action in ('blockers','opportunities'):
                    result=book.opportunities(a.build)
                    if a.action=='blockers':result=result['priorities']
                else:result=book.search(getattr(a,'query',''),category=a.category,status=a.status,build=a.build,object=a.object,unmapped=a.action=='unmapped',limit=a.limit,offset=a.offset)
            elif a.command in ('status','stats'):
                result={'artifacts':[dict(r) for r in store.db.execute('SELECT kind,state,count(*) AS count FROM artifacts GROUP BY kind,state')],
                        'tasks':[dict(r) for r in store.db.execute('SELECT id,state FROM tasks')],
                        'database_bytes':store.path.stat().st_size,'orphans':store.db.execute('SELECT count(*) FROM dependencies d LEFT JOIN artifacts a ON a.key=d.child WHERE a.key IS NULL').fetchone()[0]}
            elif a.command=='import':result=import_legacy(store,a.folder,store.binary(identity(a.exe)))
            elif a.command=='analyze':result=analyze(store,a.exe,a.rva,{'instructions':a.instructions,'blocks':a.blocks},a.task,a.max_functions,a.force)
            elif a.command=='resume':
                row=store.db.execute('SELECT * FROM tasks WHERE id=?',(a.task,)).fetchone()
                if not row:raise ValueError('Tarefa inexistente')
                spec=json.loads(row['spec']);result=analyze(store,a.exe,spec['rvas'],spec['params'],a.task)
            elif a.command=='plan':result=store.plan()
            elif a.command=='class':result=index_class(store,a.exe,a.name)
            elif a.command=='hierarchy':result=index_hierarchy(store,a.exe,a.vtable)
            elif a.command=='index':result=[dict(r) for r in store.db.execute('SELECT kind,subject,state,count(*) AS provenance_records FROM artifacts WHERE kind=? AND subject LIKE ? GROUP BY kind,subject,state LIMIT 200',(a.kind,'%'+a.query+'%'))]
            elif a.command=='queue':result=dict(store.task(a.id,json.loads(a.spec.read_text(encoding='utf8'))))
            elif a.command=='task':
                with store.db:
                    if a.state:store.db.execute('UPDATE tasks SET state=? WHERE id=?',(a.state,a.id))
                    # Prioridade administrativa não altera o fingerprint de entrada da tarefa.
                    if a.priority is not None:store.db.execute('INSERT OR REPLACE INTO task_priority VALUES (?,?)',(a.id,a.priority))
                result=dict(store.db.execute('SELECT * FROM tasks WHERE id=?',(a.id,)).fetchone())
            elif a.command=='invalidate':result={'dry_run':not a.apply,'affected':store.invalidate(a.key,not a.apply)}
            elif a.command=='graph':result=store.walk(a.binary,a.source,depth=a.depth)
            elif a.command=='evidence':result=[dict(r) for r in store.db.execute('SELECT * FROM evidence ORDER BY id')]
            elif a.command=='report':result=[json.loads(r[0]) for r in store.db.execute('SELECT metrics FROM runs ORDER BY id')]
            elif a.command=='cache-explain':
                row=store.get(a.key);store.db.commit()
                result={'found':bool(row),'state':row['state'] if row else 'ABSENT_OR_INVALID','reason':'identidade, algoritmo e parâmetros fazem parte da chave; LEGACY não é cache validado'}
            elif a.command=='clean':
                keys=[r[0] for r in store.db.execute("SELECT key FROM artifacts WHERE state='INVALID'")]
                result={'dry_run':not a.apply,'invalid_artifacts':keys}
                if a.apply:
                    with store.db:
                        for key in keys:
                            store.db.execute('DELETE FROM dependencies WHERE parent=? OR child=?',(key,key))
                            store.db.execute('DELETE FROM artifacts WHERE key=?',(key,))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
