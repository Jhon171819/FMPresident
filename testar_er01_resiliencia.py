"""Ensaios controlados: falha abrupta de Python auxiliar, grafo parcial e leitura opt-in.

Nunca encerra o FM nem escreve em sua memória. Bancos de ensaio são temporários.
"""
import argparse,json,queue,subprocess,sys,tempfile,threading,time
from pathlib import Path
from er01 import Store,SnapshotReads

def ready():
    print('READY',flush=True)
    threading.Event().wait(30)
    raise RuntimeError('O controlador não encerrou o auxiliar no prazo')

def child(path,stage):
    with Store(path) as s:
        b=s.binary({'sha256':'crash-fixture','size':1})
        s.task('crash',{'rvas':[1,2]})
        def compute():
            if stage=='during-compute':ready()
            return {'fixture':1}
        s.cached(b,'graph',1,'fixture-v1',{},compute)
        if stage=='after-checkpoint':s.checkpoint('crash',[1],[2],'RUNNING')
        ready()

def crash_tests():
    result=[]
    for stage in ('during-compute','after-publish','after-checkpoint'):
        with tempfile.TemporaryDirectory(prefix='er01-crash-') as tmp:
            path=Path(tmp)/'cache.sqlite3'
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--child',str(path),stage],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            lines=queue.Queue();thread=threading.Thread(target=lambda:lines.put(proc.stdout.readline()),daemon=True);thread.start()
            try:
                line=lines.get(timeout=10)
                if line.strip()!='READY':raise AssertionError('Auxiliar não alcançou o ponto de falha: '+line)
                # Windows: TerminateProcess apenas neste auxiliar criado pelo teste.
                proc.kill();stdout,stderr=proc.communicate(timeout=10)
                assert proc.returncode!=0, 'Auxiliar terminou normalmente'
                with Store(path) as s:
                    integrity=s.db.execute('PRAGMA integrity_check').fetchone()[0]
                    assert integrity=='ok'
                    b='crash-fixture';published=s.db.execute('SELECT count(*) FROM artifacts').fetchone()[0]
                    checkpoint=json.loads(s.db.execute("SELECT checkpoint FROM tasks WHERE id='crash'").fetchone()[0])
                    calls=[]
                    def compute():calls.append(1);return {'fixture':1}
                    _,one=s.cached(b,'graph',1,'fixture-v1',{},compute)
                    _,two=s.cached(b,'graph',2,'fixture-v1',{},compute)
                    assert published==(0 if stage=='during-compute' else 1)
                    assert one['computed']==int(stage=='during-compute')
                    assert len(calls)==(2 if stage=='during-compute' else 1)
                    s.checkpoint('crash',[1,2],[],'COMPLETE')
                    result.append({'stage':stage,'forced_exit':proc.returncode,'integrity':integrity,
                                   'published_after_crash':published,'checkpoint_done_before_resume':checkpoint['done'],
                                   'computed_during_resume':len(calls),'reused_first':one['hit'],'state':'COMPLETE'})
            finally:
                if proc.poll() is None:proc.kill();proc.communicate(timeout=10)
                thread.join(timeout=1)
    return result

def partial_graph(exe):
    from er01_static import analyze
    with tempfile.TemporaryDirectory(prefix='er01-depth-') as tmp:
        with Store(Path(tmp)/'cache.sqlite3') as s:
            rva=0x3a88400
            shallow=analyze(s,exe,[rva],{'instructions':5,'blocks':2})
            repeated=analyze(s,exe,[rva],{'instructions':5,'blocks':2})
            deep=analyze(s,exe,[rva],{'instructions':800,'blocks':100})
            deep_repeat=analyze(s,exe,[rva],{'instructions':800,'blocks':100})
            assert shallow['partial']==1 and shallow['computed']==1
            assert repeated['computed']==0 and deep['computed']==1 and deep_repeat['computed']==0
            return {'rva':hex(rva),'shallow':shallow,'same_limits':repeated,'deeper':deep,'deeper_repeated':deep_repeat}

def real_reads():
    import fm23 as n
    import compatibilidade as compat
    class Reader:
        read=n.Memory.read;_sample=n.Memory._sample;alive=n.Memory.alive;close=n.Memory.close
        def __init__(self,pid):
            self.guard=None;self.handle=n.k.OpenProcess(0x410,False,pid)
            if not self.handle:raise OSError('Leitura do FM recusada')
    info=n.process_info();reader=Reader(info['pid']);planned=None
    try:
        start=time.perf_counter();guard=compat.BuildGuard(info,n.ProcessProbe(reader,info['base']));reader.guard=guard
        guard_s=time.perf_counter()-start
        # Código já utilizado pelo próprio perfil BuildGuard: independente do save aberto.
        rva,expected=guard.profile.anchors[0]
        assert len(expected)>=8
        address=info['base']+rva
        region=n.MBI()
        assert n.k.VirtualQueryEx(reader.handle,address,n.C.byref(region),n.C.sizeof(region))
        assert region.state==0x1000 and not region.protect&0x101
        lo=region.base;hi=lo+region.size
        context=(info['pid'],info['started'],info['base'],info['version'],1)
        current=[context]
        def validate(value):
            guard.require_fast()
            return value==current[0] and reader.alive()
        requests=[(address,4),(address+4,4),(address,4)]
        before=time.perf_counter();naive=[reader.read(a,z) for a,z in requests];naive_s=time.perf_counter()-before
        planned=SnapshotReads(reader.read,context,validate,[(lo,hi)],byte_limit=32,call_limit=3,seconds=5)
        before=time.perf_counter();values=planned.batch(requests);planned_s=time.perf_counter()-before
        assert values==naive and planned.calls==1 and planned.bytes==8
        assert b''.join(values[:2])==expected[:8]
        planned.read(address,8,fresh=True)
        assert planned.calls==2
        current[0]=context[:-1]+(2,)
        try:planned.read(address,4)
        except ValueError:invalidated=True
        else:raise AssertionError('Época divergente aceita')
        after=n.process_info()
        assert (after['pid'],after['started'],after['base'])==context[:3]
        return {'build':info['version'],'guard_s':guard_s,'naive_s':naive_s,'planned_s':planned_s,
                'equal':True,'naive_requests':3,'naive_requested_bytes':12,'planned_source_calls_initial':1,
                'planned_requested_bytes_initial':8,'source_calls_with_revalidation':planned.calls,
                'epoch_rejected':invalidated,'note':'Contagens da fonte excluem amostras internas do BuildGuard; bytes de código, não elenco.'}
    finally:
        if planned is not None:planned.close()
        reader.close()
        assert reader.handle is None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe');p.add_argument('--live',action='store_true');p.add_argument('--output',type=Path)
    p.add_argument('--child',nargs=2,metavar=('DATABASE','STAGE'));a=p.parse_args()
    if a.child:child(*a.child);return
    result={'crashes':crash_tests()}
    if a.exe:result['partial_graph']=partial_graph(a.exe)
    if a.live:result['real_reads']=real_reads()
    rendered=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered,encoding='utf8')
    print(rendered)
if __name__=='__main__':main()
