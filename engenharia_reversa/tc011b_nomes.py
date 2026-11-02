"""Pesquisa diagnóstica dirigida; nenhum campo é promovido a domínio operacional."""
import struct, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from tc011_sondar_equipe import Reader
import fm23 as n
import compatibilidade as compat
import sincronizacao_hibrida as sync
from evidencias_taticas import vector_bounds,text_candidate
sys.stdout.reconfigure(encoding='utf-8')

class MeasuredReader(Reader):
    def __init__(self,pid):
        self.calls=0;self.bytes=0;self.failures=0;super().__init__(pid)
    def _sample(self,addr,size):
        self.calls+=1;self.bytes+=size
        try:return super()._sample(addr,size)
        except Exception:self.failures+=1;raise

def collect():
    info=n.process_info(); options,_=sync.search_candidates(info=info)
    club=next(c.address for c in options if c.club.uid==n.UID)
    r=MeasuredReader(info['pid']);start=time.perf_counter()
    try:
        guard=compat.BuildGuard(info,n.ProcessProbe(r,info['base']));r.guard=guard
        print('buildguard_s',round(time.perf_counter()-start,3))
        if r.pointer(club)!=info['base']+n.VTABLE_RVA:raise ValueError('Clube mudou')
        team=r.pointer(r.pointer(club+24))
        if r.pointer(team)!=info['base']+n.TEAM_VTABLE_RVA or r.pointer(team+48)!=club:raise ValueError('Equipe mudou')
        header=r.read(team+0x38,24);a,count=vector_bounds(header);b=a+count*8
        if not count:raise ValueError('Coleção vazia')
        players=[p for p in struct.unpack('<'+'Q'*((b-a)//8),r.read(a,b-a)) if r.pointer(p)==info['base']+0x4fd7a28]
        for i,p in enumerate(players[:40]):
            raw=r.read(p,0x600);texts=[];adjust=[]
            for off in range(0x10,0x2e0,8):
                ptr=struct.unpack_from('<Q',raw,off)[0]
                if not 0x10000<=ptr<0x7fffffffffff:continue
                try:data=r.read(ptr,80)
                except (OSError,ValueError):continue
                for skip in (0,4,8,16):
                    word=data[skip:].split(b'\0',1)[0]
                    try:text=text_candidate(word)['text']
                    except (UnicodeError,ValueError):continue
                    texts.append((hex(off),skip,text));break
            vb=r.pointer(p+8)
            try:adjust=list(struct.unpack('<4i',r.read(vb,16)))
            except (OSError,ValueError):pass
            print(i,'vbtable',adjust,'textos',texts,flush=True)
            if any(t[0]=='0x2b8' for t in texts):
                try:print('data_candidata_2b4',n.fm_date(raw[0x2b4:0x2b8]).isoformat())
                except ValueError:print('data_candidata_invalida')
        if r.read(team+0x38,24)!=header:raise ValueError('Coleção mudou; descarte o resultado')
        guard.require_fast()
        print('tempo_total',round(time.perf_counter()-start,3),'chamadas',r.calls,'bytes',r.bytes,'falhas',r.failures)
    finally:r.close()
if __name__=='__main__':collect()
