"""Sondagem limitada, somente leitura, de possíveis vetores da equipe do Ceará.

As saídas são hipóteses estruturais, não um leitor de elenco homologado.
"""
import struct
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fm23 as n
import compatibilidade as compat
import identidade
import sincronizacao_hibrida as sync

class Reader:
    read=n.Memory.read; _sample=n.Memory._sample; number=n.Memory.number
    pointer=n.Memory.pointer; alive=n.Memory.alive; close=n.Memory.close
    def __init__(self,pid):
        self.guard=None; self.handle=n.k.OpenProcess(0x410,False,pid)
        if not self.handle: raise OSError('Acesso de leitura recusado')

def probe():
    info=n.process_info(); options,limited=sync.search_candidates(info=info)
    candidates=[c for c in options if c.club.uid==n.UID]
    if len(candidates)!=1: raise ValueError('Candidato Ceará não é único')
    reader=Reader(info['pid']); start=time.perf_counter()
    try:
        guard=compat.BuildGuard(info,n.ProcessProbe(reader,info['base']));reader.guard=guard
        club=candidates[0].address
        before=identidade.inspect_candidate(reader,info['base'],club,n.VTABLE_RVA,n.FACILITIES)
        if not before:raise ValueError('Candidato inválido')
        first,last=struct.unpack('<QQ',reader.read(club+24,16))
        if not first or last<=first or last-first>128 or (last-first)%8:raise ValueError('Lista de equipes incompatível')
        team=reader.pointer(first)
        if reader.pointer(team)!=info['base']+n.TEAM_VTABLE_RVA or reader.pointer(team+48)!=club:raise ValueError('Equipe incompatível')
        raw=reader.read(team,512); results=[]; sets={}
        for offset in range(0,512-24+1,8):
            a,b,c=struct.unpack_from('<QQQ',raw,offset)
            if not (0x10000<=a<=b<=c<0x7fffffffffff and 0<b-a<=800 and (b-a)%8==0 and c-a<=4096):continue
            try:
                values=struct.unpack('<'+'Q'*((b-a)//8),reader.read(a,b-a)); types={}
                for value in values[:100]:
                    if value<0x10000 or value%8:continue
                    try:vt=reader.pointer(value)-info['base']
                    except (OSError,ValueError):continue
                    if 0<=vt<info['size']:types[hex(vt)]=types.get(hex(vt),0)+1
                    if vt==0x4fd7a28:sets.setdefault(offset,set()).add(value)
                results.append((hex(offset),len(values),types))
            except (OSError,ValueError,struct.error):continue
        if reader.read(team,512)!=raw or identidade.inspect_candidate(reader,info['base'],club,n.VTABLE_RVA,n.FACILITIES)!=before:raise ValueError('Contexto mudou durante sondagem')
        guard.require_fast()
        overlap=[(hex(a),hex(b),len(sets[a]&sets[b])) for a in sets for b in sets if a<b]
        links={}
        for off,players in sets.items():
            counts={'total':len(players),'team_130':0,'team_138':0}
            for player in players:
                pair=reader.read(player+0x130,16)
                p1,p2=struct.unpack('<QQ',pair)
                counts['team_130']+=int(p1==team);counts['team_138']+=int(p2==team)
            links[hex(off)]=counts
        # Apenas descreve quantidade de ponteiros repetidos, sem rotulá-los como nomes.
        samples=[reader.read(p,0x298) for p in sorted(sets.get(0x38,set()))[:8]]
        shared=[]
        for off in range(8,0x298,8):
            pointers=[struct.unpack_from('<Q',sample,off)[0] for sample in samples]
            plausible=[p for p in pointers if 0x10000<=p<0x7fffffffffff and p%8==0]
            if len(plausible)>=6:shared.append(hex(off))
        text_counts={}
        reference_types={}
        for off in (0xf8,0x100,0x108,0x130,0x138,0x178):
            count=0
            for sample in samples:
                ptr=struct.unpack_from('<Q',sample,off)[0]
                try:
                    data=reader.read(ptr,64)
                    vtable=struct.unpack_from('<Q',data)[0]-info['base']
                    if 0<=vtable<info['size']:
                        bucket=reference_types.setdefault(hex(off),{})
                        bucket[hex(vtable)]=bucket.get(hex(vtable),0)+1
                    for pos in (0,4,8,16):
                        word=data[pos:].split(b'\0',1)[0]
                        if 3<=len(word)<=40 and all(32<=c<127 for c in word):count+=1;break
                except (ValueError,OSError):pass
            text_counts[hex(off)]=count
        print('build',info['version'],'candidatos_limitados',limited,'vetores_candidatos',results,'intersecoes',overlap,'tempo_s',round(time.perf_counter()-start,3))
        print('amostra_objetos',len(samples),'offsets_ponteiros_candidatos',shared)
        print('ponteiros_texto_ascii_candidatos',text_counts)
        print('tipos_referenciados',reference_types)
        print('vinculo_equipe_candidata',links)
        divergent=[]
        for player in sorted(sets.get(0x38,set())):
            other=reader.pointer(player+0x130)
            if other==team:continue
            item={'classe':'ACTUAL_PLAYER','referencia_130':'UNKNOWN','club_uid':None}
            try:
                if reader.pointer(other)==info['base']+n.TEAM_VTABLE_RVA:
                    item['referencia_130']='TEAM'
                    owner=reader.pointer(other+48)
                    if reader.pointer(owner)==info['base']+n.VTABLE_RVA:item['club_uid']=reader.number(owner+12,'I')
            except (OSError,ValueError):pass
            divergent.append(item)
        print('divergentes',divergent)
        print('RTTI tipos: 0x5006e68=VIRTUAL_PLAYER; 0x4fd9a18=ACTUAL_PLAYER_AND_NON_PLAYER; 0x4fd7a28=ACTUAL_PLAYER')
    finally:reader.close()

if __name__=='__main__':probe()
