"""Sondagem dirigida TC-01.1C. --live explícito, somente leitura, sem varredura.

Usa apenas candidato da sessão atual já armazenado; nunca procura a memória inteira.
Endereços existem apenas durante esta operação e não são exportados.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from er01 import SnapshotReads,ROOT
from er01_static import process_usage
from evidencias_taticas import text_candidate,vector_bounds


def sample_player(raw, read_text, decode_date, *, expected_team):
    """Interpretação diagnóstica dos candidatos; não produz identidade nem UID."""
    if len(raw)!=0x2c0:raise ValueError('Objeto parcial')
    ptr=struct.unpack_from('<Q',raw,0x2b8)[0]
    result={'name_status':'ABSENT_TEXT','name':None,'birth_candidate':None,'uid':None,'confidence':'INCONCLUSIVE',
            'team_130_matches':struct.unpack_from('<Q',raw,0x130)[0]==expected_team,
            'team_138_matches':struct.unpack_from('<Q',raw,0x138)[0]==expected_team}
    if ptr:
        if not 0x10000<=ptr<0x7fffffffffff:result['name_status']='INVALID_POINTER'
        else:
            try:
                data=read_text(ptr,84)
            except OSError:result['name_status']='PARTIAL_READ'
            else:
                if len(data)!=84:result['name_status']='PARTIAL_READ'
                else:
                    try:
                        result['name']=text_candidate(data[4:],max_bytes=80)['text']
                        result['name_status']='TEXT_CANDIDATE';result['confidence']='HYPOTHESIS'
                    except UnicodeError:result['name_status']='INVALID_UTF8'
                    except ValueError:result['name_status']='UNRESOLVED_STRING'
    try:result['birth_candidate']=decode_date(raw[0x2b4:0x2b8]).isoformat()
    except (ValueError,OverflowError):pass
    return result


def collect(owners_only=False):
    import ctypes as c
    import fm23 as n
    import compatibilidade as compat
    import identidade
    import indice_clubes
    from tc011b_nomes import MeasuredReader
    from sincronizacao_hibrida import Coordinator,Observation
    start=time.perf_counter();cpu=time.process_time();info=n.process_info();r=MeasuredReader(info['pid'])
    snapshot=None;coordinator=Coordinator();epoch=coordinator.begin();phases={}
    result={'issue':'TC-01.1C','read_only':True,'mode':'owners_only' if owners_only else 'identities','save_identity':'UNVERIFIED; nenhum save aberto/trocado pelo script',
            'limits':{'bytes':131072,'calls':256,'seconds':25,'primary_players':32,'other_collection_samples':4},
            'observed_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
    try:
        guard=compat.BuildGuard(info,n.ProcessProbe(r,info['base']));r.guard=guard
        phases['buildguard_s']=time.perf_counter()-start
        index=indice_clubes.ClubIndex(n.DATA/'indice-clubes.sqlite3')
        try:choices=index.find(info,guard.result.process.sha256.value,str(n.UID))
        finally:index.close()
        addresses={address for address,uid,name in choices if uid==n.UID}
        cache=n.read_json(n.DATA/'conexao.json',{})
        if (cache.get('pid'),cache.get('started'))==(info['pid'],info['started']) and cache.get('club'):addresses.add(cache['club'])
        candidates=[x for a in addresses if (x:=identidade.inspect_candidate(r,info['base'],a,n.VTABLE_RVA,n.FACILITIES)) and x.club.uid==n.UID]
        if len(candidates)!=1:raise ValueError('Candidato Ceará da sessão ausente ou ambíguo; nenhuma varredura realizada')
        club=candidates[0].address
        game_date=n.fm_date(r.read(info['base']+n.DATE_RVA,4));day=game_date.isoformat()
        career=identidade.CareerGuard(guard,candidates[0],game_date)
        result.update(build=info['version'],fingerprint=guard.result.process.sha256.value,
                      context={'pid':info['pid'],'started':info['started'],'date':day,'club_uid':n.UID,
                               'career_state':career.result.state.value,'manual_approval':'Não solicitada: somente diagnóstico; nenhuma autorização operacional emitida','epoch':epoch})
        context=(info['pid'],info['started'],day,epoch)
        def validate(current):
            guard.require_fast()
            return current==context and not coordinator.closed and epoch==coordinator.epoch and r.alive()
        regions=[]
        snapshot=SnapshotReads(r.read,context,validate,regions,byte_limit=131072,call_limit=256,seconds=25,failure_limit=3)
        def read(address,size,fresh=False):
            if not any(a<=address and address+size<=b for a,b in regions):
                if len(regions)>=256:raise ValueError('Região: limite atingido')
                mbi=n.MBI()
                if not n.k.VirtualQueryEx(r.handle,address,c.byref(mbi),c.sizeof(mbi)):raise OSError('VirtualQueryEx falhou')
                base=mbi.base or 0
                if mbi.state!=0x1000 or mbi.protect&0x101 or not(base<=address and address+size<=base+mbi.size):raise OSError('Região não legível')
                regions.append((base,base+mbi.size))
            return snapshot.read(address,size,fresh)
        def pointer(address):return struct.unpack('<Q',read(address,8))[0]
        team=pointer(pointer(club+24))
        if pointer(team)!=info['base']+n.TEAM_VTABLE_RVA or pointer(team+48)!=club:raise ValueError('Equipe incompatível')
        headers={};collections=[];samples=[];sets=[]
        for off in (0x38,0xf0,0x1a8):
            header=read(team+off,24);headers[off]=header;a,count=vector_bounds(header)
            owner={'relative_base':hex(off-0x38),'vtable_rva':hex(pointer(team+off-0x38)-info['base'])}
            if owner['vtable_rva']==hex(n.TEAM_VTABLE_RVA):
                owner_club=pointer(team+off-0x38+48)
                if pointer(owner_club)==info['base']+n.VTABLE_RVA:
                    owner['club_uid']=struct.unpack('<I',read(owner_club+12,4))[0]
                    owner['club_name']=read(pointer(owner_club+184)+4,32).split(b'\0',1)[0].decode('utf8','strict')
            values=struct.unpack('<'+'Q'*count,read(a,count*8)) if count and not owners_only else []
            types={};players=[]
            for p in values:
                vt=pointer(p)-info['base'];types[hex(vt)]=types.get(hex(vt),0)+1
                if vt==0x4fd7a28:players.append(p)
            sets.append(set(players));collections.append({'offset':hex(off),'entries':count,'types':types,'actual_players':len(players) if not owners_only else None,'owner_candidate':owner})
            for i,p in enumerate(players[:32 if off==0x38 else 4]):
                raw=read(p,0x2c0);item=sample_player(raw,read,n.fm_date,expected_team=team)
                item.update(collection=hex(off),index=i,subobject_words={hex(o):hex(struct.unpack_from('<Q',raw,o)[0]-info['base']) if info['base']<=struct.unpack_from('<Q',raw,o)[0]<info['base']+info['size'] else 'NOT_MODULE_POINTER' for o in (0x270,0x298)})
                vb=struct.unpack_from('<Q',raw,8)[0]
                item['vbtable_candidate']=list(struct.unpack('<4i',read(vb,16)))
                if not item['team_130_matches']:
                    other=struct.unpack_from('<Q',raw,0x130)[0];item['other_team_club_uid']=None
                    if other>=0x10000 and pointer(other)==info['base']+n.TEAM_VTABLE_RVA:
                        owner=pointer(other+48)
                        if pointer(owner)==info['base']+n.VTABLE_RVA:item['other_team_club_uid']=struct.unpack('<I',read(owner+12,4))[0]
                samples.append(item)
        # Igualdade nas pontas detecta algumas mudanças; não torna a observação atômica.
        for off,header in headers.items():
            if read(team+off,24,fresh=True)!=header:raise ValueError('Observação mudou')
        if identidade.inspect_candidate(r,info['base'],club,n.VTABLE_RVA,n.FACILITIES)!=candidates[0]:raise ValueError('Clube mudou')
        if n.fm_date(r.read(info['base']+n.DATE_RVA,4)).isoformat()!=day:raise ValueError('Data mudou')
        guard.require_fast()
        if not coordinator.finish(epoch,Observation(context,guard.result.profile,result['observed_at_utc'])):raise ValueError('Resultado obsoleto')
        result.update(state='OBSERVED_UNVERIFIED',collections=collections,samples=samples,
                      overlaps=None if owners_only else [{'a':hex((0x38,0xf0,0x1a8)[a]),'b':hex((0x38,0xf0,0x1a8)[b]),'count':len(sets[a]&sets[b])} for a in range(3) for b in range(a+1,3)])
    except Exception as exc:
        result.update(state='INCONCLUSIVE',error=type(exc).__name__+': '+str(exc))
    finally:
        if snapshot:
            result['snapshot_metrics']={k:getattr(snapshot,k) for k in ('calls','bytes','failures','hits')};snapshot.close()
        coordinator.close();r.close()
        result.update(wall_s=time.perf_counter()-start,cpu_s=time.process_time()-cpu,phases=phases,
                      reader_metrics={'calls':r.calls,'bytes':r.bytes,'failures':r.failures},process_usage=process_usage())
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--owners-only',action='store_true',help='verifica apenas bases e clubes dos três cabeçalhos; não repete amostra de atletas')
    a=p.parse_args();result=collect(a.owners_only);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
