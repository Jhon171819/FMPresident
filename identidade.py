"""CP-02: evidência observada não é autorização de carreira ou treinador."""
from dataclasses import dataclass
from enum import Enum
from contratos_dados import ClubIdentity, CareerIdentity, Evidence, Source, Verification

class State(str, Enum):
    UNVERIFIED='UNVERIFIED'
    AMBIGUOUS='AMBIGUOUS'
    CHANGED='CHANGED'
    ERROR='ERROR'

@dataclass(frozen=True)
class Candidate:
    club: ClubIdentity
    address: int

@dataclass(frozen=True)
class IdentityResult:
    state: State
    process: object
    candidate: Candidate | None
    career: CareerIdentity | None
    reason: str
    human_manager: Evidence

class IdentityError(RuntimeError):
    pass

class CareerGuard:
    def __init__(self, build_guard, candidate=None, game_date=None):
        self.build_guard=build_guard
        self.build_guard.require_fast()
        process=build_guard.result.process
        career=None
        if candidate is not None and game_date is not None:
            career=CareerIdentity(process,candidate.club,game_date,
                career_id=Evidence(None,Source.UNKNOWN,Verification.UNKNOWN),
                controlled_club=Evidence(None,Source.UNKNOWN,Verification.UNKNOWN))
        self.result=IdentityResult(State.UNVERIFIED,process,candidate,career,
            'Não foi possível confirmar a identidade da carreira e o vínculo do treinador humano com o clube.',
            Evidence(None,Source.UNKNOWN,Verification.UNKNOWN))

    def require(self):
        self.build_guard.require_fast()
        # Nenhuma cadeia de identificação homologada existe ainda; não há bypass.
        raise IdentityError('Identidade não verificada • Build '+str(self.result.process.version)+' validada. '+self.result.reason+' Operações administrativas indisponíveis.')



class ManualCareerGuard:
    """Autorização expressa do usuário para um clube nesta instância.

    Não prova identidade de save ou que o treinador controla o clube.
    """
    def __init__(self, build_guard, revalidate):
        self.build_guard=build_guard;self.revalidate=revalidate;self.active=True
    def require(self):
        if not self.active:raise IdentityError('Seleção manual invalidada. Sincronize novamente.')
        try:
            self.build_guard.require_fast()
            self.revalidate()
        except Exception:
            self.active=False
            raise
    def revoke(self):self.active=False

def inspect_candidate(memory, base, address, vtable_rva, facilities):
    """Candidato estrutural; não comprova controle humano, carreira ou suporte."""
    try:
        if not address or address % 8 or memory.pointer(address)!=base+vtable_rva: return None
        uid=memory.number(address+12,'I')
        name=memory.read(memory.pointer(address+184)+4,32).split(b'\0',1)[0].decode('utf-8','strict')
        finance=memory.pointer(address+328);info=memory.pointer(address+248)
        if not 0 < uid < 2**32 or not name.strip() or memory.pointer(finance+8)!=address: return None
        if not -2_000_000_000 < memory.number(finance+20) < 2_000_000_000: return None
        if any(not 0 <= memory.number(info+o,'B') <= 20 for o in facilities.values()): return None
        return Candidate(ClubIdentity(uid,name),address)
    except (OSError,ValueError,UnicodeError,OverflowError): return None


def discover_candidates(memory, base, vtable_rva, facilities):
    """Busca diagnóstica: sem escolher clube, sem assumir contagem completa."""
    import struct
    needle=struct.pack('<Q',base+vtable_rva)
    found=set()
    for start,size in memory.regions():
        for off in range(0,size,4*1024*1024):
            try: data=memory.read(start+off,min(4*1024*1024,size-off))
            except OSError: continue
            pos=data.find(needle)
            while pos>=0:
                address=start+off+pos
                if address not in found:
                    found.add(address)
                    candidate=inspect_candidate(memory,base,address,vtable_rva,facilities)
                    if candidate: yield candidate
                pos=data.find(needle,pos+1)
