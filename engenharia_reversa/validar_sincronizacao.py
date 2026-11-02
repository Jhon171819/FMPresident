"""Protótipo diagnóstico de sincronização; nunca autoriza operações."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Observation:
    pid: int
    started: str
    build: str
    club_uid: int
    club_address: int
    game_date: str

class Monitor:
    def __init__(self):self.epoch=0;self.observation=None
    def synchronize(self, discover):
        # Invalidar ANTES da descoberta, inclusive em caso de falha.
        self.epoch+=1;self.observation=None
        self.observation=discover()
        if not isinstance(self.observation,Observation):
            self.observation=None;raise ValueError('Observação inválida')
        return self.epoch
    def inspect(self, ticket, discover):
        if ticket!=self.epoch or self.observation is None:return 'STALE'
        try:current=discover()
        except Exception:
            self.epoch+=1;self.observation=None;return 'UNAVAILABLE'
        if not isinstance(current,Observation) or current!=self.observation:
            self.epoch+=1;self.observation=None;return 'CHANGED'
        return 'SAME_OBSERVATION_IDENTITY_UNPROVEN'
    def authorize(self):raise RuntimeError('Protótipo diagnóstico sem autorização de escrita')

if __name__=='__main__':
    import sys,json,time
    from datetime import datetime,timezone
    ROOT=__import__('pathlib').Path(__file__).resolve().parent.parent
    sys.path.insert(0,str(ROOT))
    import fm23 as native
    import compatibilidade as compat
    import identidade
    class Reader:
        read=native.Memory.read;_sample=native.Memory._sample
        number=native.Memory.number;pointer=native.Memory.pointer
        alive=native.Memory.alive;close=native.Memory.close
        def __init__(self,pid):
            self.guard=None;self.handle=native.k.OpenProcess(0x410,False,pid)
            if not self.handle:raise OSError('Leitura indisponível')
    info=native.process_info();r=Reader(info['pid'])
    try:
        g=compat.BuildGuard(info,native.ProcessProbe(r,info['base']));r.guard=g
        cache=native.read_json(native.DATA/'conexao.json',{})
        if (cache.get('pid'),cache.get('started'))!=(info['pid'],info['started']):raise ValueError('Cache de outra instância')
        samples=[]
        for _ in range(3):
            g.require_fast()
            c=identidade.inspect_candidate(r,info['base'],cache['club'],native.VTABLE_RVA,native.FACILITIES)
            samples.append({'at':datetime.now(timezone.utc).isoformat(),'candidate_uid':c.club.uid if c else None,
                'candidate_address':hex(c.address) if c else None,'date':native.fm_date(r.read(info['base']+native.DATE_RVA,4)).isoformat()})
            time.sleep(0.25)
        result={'method':'0x410-read-only','build':g.result.diagnostic(),'observations':samples,
                'conclusion':'Observações estruturais; treinador, save e continuidade não comprovados.'}
        output=ROOT/'engenharia_reversa/identidade/teste-sincronizacao.json'
        with output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
        print(json.dumps(result,ensure_ascii=False))
    finally:r.close()
