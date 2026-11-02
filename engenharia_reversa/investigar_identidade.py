"""CP-02.1: diagnóstico isolado. Não fornece autorização operacional."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
HUMAN_DETAILS=0x48b7c08

def chain(reader,base,address):
    result={'object':hex(address),'state':'UNAVAILABLE'}
    try:
        if not address or address%8: return result
        if reader.pointer(address)!=base+HUMAN_DETAILS:
            result['state']='WRONG_VTABLE';return result
        team=reader.pointer(address+0x40)
        if not team:return result
        if reader.pointer(team)!=base+0x5002398:
            result['state']='WRONG_TEAM_VTABLE';return result
        club=reader.pointer(team+0x30)
        if not club or reader.pointer(club)!=base+0x4fdcdf8:return result
        uid=reader.number(club+12,'I')
        result.update(state='OBSERVED_CHAIN',team=hex(team),club=hex(club),club_uid=uid,
                      human_control='UNKNOWN',active_session='UNKNOWN')
    except (OSError,ValueError,struct.error):pass
    return result

def compare(a,b):
    for x in (a,b):
        if not isinstance(x,dict) or x.get('schema')!=1 or not isinstance(x.get('objects'),list) or len(x['objects'])>64:raise ValueError('Observação inválida')
        if any(not isinstance(o,dict) or not isinstance(o.get('object'),str) for o in x['objects']):raise ValueError('Objeto inválido')
        if len({o['object'] for o in x['objects']})!=len(x['objects']):raise ValueError('Objetos duplicados')
    old={x['object']:x for x in a['objects']};new={x['object']:x for x in b['objects']}
    return {'appeared':sorted(new.keys()-old.keys()),'disappeared':sorted(old.keys()-new.keys()),
            'changed':sorted(k for k in old.keys()&new.keys() if old[k]!=new[k]),
            'unchanged':sorted(k for k in old.keys()&new.keys() if old[k]==new[k]),
            'interpretation':'Diferenças observadas; identidade da carreira não comprovada.'}

def collect(max_mb=512,seconds=20):
    if type(max_mb) is not int or not 1<=max_mb<=1024 or not 1<=seconds<=30:raise ValueError('Limites inválidos')
    import fm23 as native
    import compatibilidade as compat
    # Sem herdar write/paused: direitos PROCESS_QUERY_INFORMATION | PROCESS_VM_READ.
    class Reader:
        read=native.Memory.read
        _sample=native.Memory._sample
        number=native.Memory.number
        pointer=native.Memory.pointer
        regions=native.Memory.regions
        alive=native.Memory.alive
        close=native.Memory.close
        def __init__(self,pid):
            self.guard=None
            self.handle=native.k.OpenProcess(0x410,False,pid)
            if not self.handle:raise OSError('Acesso de leitura indisponível')
    info=native.process_info();r=Reader(info['pid'])
    try:
        guard=compat.BuildGuard(info,native.ProcessProbe(r,info['base']));r.guard=guard
        deadline=time.monotonic()+seconds;budget=max_mb*1024*1024;total=0;objects=[];seen=set();failures=0;limited=False
        needle=struct.pack('<Q',info['base']+HUMAN_DETAILS)
        for start,size in r.regions():
            for off in range(0,size,1024*1024):
                if time.monotonic()>=deadline or total>=budget or len(objects)>=64:
                    limited=True;break
                n=min(1024*1024+7,size-off,budget-total);total+=n
                try:data=r.read(start+off,n)
                except OSError:failures+=1;continue
                pos=data.find(needle)
                while pos>=0:
                    address=start+off+pos
                    if address%8==0 and address not in seen:
                        seen.add(address);objects.append(chain(r,info['base'],address))
                        if len(objects)>=64:break
                    pos=data.find(needle,pos+1)
            if limited:break
        guard.require_fast()
        return {'schema':1,'at':datetime.now(timezone.utc).isoformat(),'method':'read-only-0x410-bounded',
                'build':guard.result.diagnostic(),'process':{'pid':info['pid'],'started':info['started']},
                'bytes_attempted':total,'read_failures':failures,'limited':limited,
                'objects':sorted(objects,key=lambda x:x['object']),
                'identity':'UNVERIFIED','non_atomic':True}
    finally:r.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--compare',nargs=2,type=Path);p.add_argument('--max-mb',type=int,default=512);p.add_argument('--seconds',type=int,default=20);a=p.parse_args()
    data=compare(*(json.loads(x.read_text(encoding='utf-8')) for x in a.compare)) if a.compare else collect(a.max_mb,a.seconds)
    rendered=json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x',encoding='utf-8') as f:f.write(rendered)
    else:print(rendered)
if __name__=='__main__':main()
