from dataclasses import dataclass
from enum import Enum
import threading

class State(str, Enum):
    AWAITING_SYNC='AWAITING_SYNC'
    SYNCING='SYNCING'
    OBSERVED_UNVERIFIED='OBSERVED_UNVERIFIED'
    CONTEXT_CHANGED='CONTEXT_CHANGED'
    ERROR='ERROR'
    DISCONNECTED='DISCONNECTED'

@dataclass(frozen=True)
class Observation:
    process: object
    profile: str
    observed_at: str
    candidate_uid: int | None = None
    candidate_address: int | None = None
    game_date: str | None = None
    trainer: str = 'UNKNOWN'
    career: str = 'UNKNOWN'
    candidate_name: str | None = None
    balance: int | None = None
    transfer: int | None = None
    wage: int | None = None

    def comparable(self):
        return (self.process, self.profile, self.candidate_uid, self.candidate_address, self.game_date, self.trainer, self.career)

class Coordinator:
    """Gestão de épocas diagnósticas; não contém nem emite autorização."""
    def __init__(self):
        self._lock=threading.Lock();self.epoch=0;self.state=State.AWAITING_SYNC
        self.observation=None;self.reason='';self.closed=False

    def begin(self):
        with self._lock:
            if self.closed: raise RuntimeError('Coordenador encerrado')
            self.epoch+=1;self.observation=None;self.reason='';self.state=State.SYNCING
            return self.epoch

    def finish(self, epoch, observation=None, error=None):
        with self._lock:
            if self.closed or epoch!=self.epoch or self.state!=State.SYNCING:return False
            if error is not None or not isinstance(observation,Observation):
                self.observation=None;self.state=State.ERROR;self.reason='Falha ao observar o contexto.'
            else:
                self.observation=observation;self.state=State.OBSERVED_UNVERIFIED
                self.reason='Observação atualizada; identidade da carreira e treinador não comprovadas.'
            return True

    def inspect(self, epoch, observation=None, error=None):
        with self._lock:
            if self.closed or epoch!=self.epoch or self.state!=State.OBSERVED_UNVERIFIED:return False
            if error is not None or not isinstance(observation,Observation) or observation.comparable()!=self.observation.comparable():
                self.epoch+=1;self.observation=None;self.state=State.CONTEXT_CHANGED
                self.reason='Contexto alterado ou indisponível; sincronize novamente.'
            else:self.observation=observation
            return True

    def close(self):
        with self._lock:
            self.closed=True;self.epoch+=1;self.observation=None;self.state=State.DISCONNECTED


def observe(selected_address=None):
    """Uma observação diagnóstica, com handle exclusivamente de leitura."""
    from datetime import datetime, timezone
    import fm23 as native
    import compatibilidade as compat
    import identidade
    class Reader:
        read=native.Memory.read;_sample=native.Memory._sample
        number=native.Memory.number;pointer=native.Memory.pointer
        alive=native.Memory.alive;close=native.Memory.close
        def __init__(self,pid):
            self.guard=None;self.handle=native.k.OpenProcess(0x410,False,pid)
            if not self.handle:raise OSError('Acesso de leitura ao FM indisponível.')
    info=native.process_info();reader=Reader(info['pid'])
    try:
        guard=compat.BuildGuard(info,native.ProcessProbe(reader,info['base']))
        reader.guard=guard
        cache=native.read_json(native.DATA/'conexao.json',{})
        candidate=None
        if selected_address is not None:
            candidate=identidade.inspect_candidate(reader,info['base'],selected_address,native.VTABLE_RVA,native.FACILITIES)
            if candidate is None:raise ValueError('O clube selecionado não está mais disponível. Busque candidatos novamente.')
        elif (cache.get('pid'),cache.get('started'))==(info['pid'],info['started']):
            candidate=identidade.inspect_candidate(reader,info['base'],cache.get('club',0),native.VTABLE_RVA,native.FACILITIES)
        day=native.fm_date(reader.read(info['base']+native.DATE_RVA,4)).isoformat()
        values={}
        if selected_address is not None and candidate:
            finance=reader.pointer(candidate.address+328)
            if reader.pointer(finance+8)!=candidate.address:raise ValueError('A estrutura financeira do candidato mudou.')
            values=dict(candidate_name=candidate.club.name,balance=reader.number(finance+20),
                        transfer=reader.number(finance+1956),wage=reader.number(finance+2024))
            checked=identidade.inspect_candidate(reader,info['base'],selected_address,native.VTABLE_RVA,native.FACILITIES)
            if checked != candidate:raise ValueError('O clube candidato mudou durante a leitura.')
        guard.require_fast()
        return Observation((info['pid'],info['started'],info['version']),guard.result.profile,
            datetime.now(timezone.utc).isoformat(),candidate.club.uid if candidate else None,
            candidate.address if candidate else None,day,**values)
    finally:reader.close()



def club_from_details(reader, base, address, team_vtable):
    """Retorna apenas a referência observada, sem inferir controle humano."""
    try:
        if not address or address%8 or reader.pointer(address)!=base+0x48b7c08:return None
        team=reader.pointer(address+0x40)
        if not team or reader.pointer(team)!=base+team_vtable:return None
        return reader.pointer(team+0x30) or None
    except (OSError,ValueError):return None

@dataclass(frozen=True)
class CandidateOption:
    club: object
    address: int
    source: str


def include_candidate(found, candidate, source):
    """Preserva proveniência e privilegia uma cadeia observada sobre cache."""
    if candidate is None:return
    previous=found.get(candidate.address)
    if previous is None or source=='vinculo':
        found[candidate.address]=CandidateOption(candidate.club,candidate.address,source)


def search_candidates(max_bytes=1024*1024*1024, max_seconds=20, prefer_cache=True, query=''):
    """Busca limitada de candidatos; não concede autorização."""
    import struct, time
    import fm23 as native
    import compatibilidade as compat
    import identidade
    import indice_clubes
    class Reader:
        read=native.Memory.read;_sample=native.Memory._sample
        number=native.Memory.number;pointer=native.Memory.pointer
        regions=native.Memory.regions;alive=native.Memory.alive;close=native.Memory.close
        def __init__(self,pid):
            self.guard=None;self.handle=native.k.OpenProcess(0x410,False,pid)
            if not self.handle:raise OSError('Acesso de leitura ao FM indisponível.')
    info=native.process_info();reader=Reader(info['pid'])
    try:
        guard=compat.BuildGuard(info,native.ProcessProbe(reader,info['base']));reader.guard=guard
        found={}
        index=indice_clubes.ClubIndex(native.DATA/'indice-clubes.sqlite3')
        digest=guard.result.process.sha256.value
        def add(address,source):
            candidate=identidade.inspect_candidate(reader,info['base'],address,native.VTABLE_RVA,native.FACILITIES)
            include_candidate(found,candidate,source)
        for address,uid,name in index.find(info,digest,query):
            candidate=identidade.inspect_candidate(reader,info['base'],address,native.VTABLE_RVA,native.FACILITIES)
            if candidate and (candidate.club.uid,candidate.club.name)==(uid,name):include_candidate(found,candidate,'indice')
        cache=native.read_json(native.DATA/'conexao.json',{})
        if (cache.get('pid'),cache.get('started'))==(info['pid'],info['started']):
            add(cache.get('club',0),'cache')
        # Índice é apenas um endereço candidato da sessão; a estrutura é revalidada.
        def matches(option):
            key=indice_clubes.normalize(query)
            return not key or (str(option.club.uid)==key if key.isdecimal() else indice_clubes.normalize(option.club.name).startswith(key))
        filtered=[item for item in found.values() if matches(item)]
        if prefer_cache and filtered:
            guard.require_fast()
            index.put(info,digest,list(found.values()))
            return sorted(filtered,key=lambda c:(c.club.name.casefold(),c.club.uid,c.address)),True
        needle=struct.pack('<Q',info['base']+0x48b7c08);total=0;deadline=time.monotonic()+max_seconds;limited=False
        for base,size in reader.regions():
            for offset in range(0,size,1024*1024):
                if total>=max_bytes or time.monotonic()>=deadline or len(found)>=200:
                    limited=True;break
                n=min(1024*1024,size-offset,max_bytes-total);total+=n
                try:data=reader.read(base+offset,n)
                except OSError:continue
                pos=data.find(needle)
                while pos>=0:
                    address=base+offset+pos
                    club=club_from_details(reader,info['base'],address,native.TEAM_VTABLE_RVA)
                    if club:add(club,'vinculo')
                    pos=data.find(needle,pos+1)
            if limited:break
        guard.require_fast()
        index.put(info,digest,list(found.values()))
        return sorted((c for c in found.values() if matches(c)),key=lambda c:(c.club.name.casefold(),c.club.uid,c.address)),limited
    finally:
        if 'index' in locals():index.close()
        reader.close()
