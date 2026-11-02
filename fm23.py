"""Integração local verificada para FM23 23.2.0+1771058, Windows x64.

Somente dados: não injeta código nem altera fm.exe. Os endereços são reencontrados
em cada processo e todos os campos são validados antes de escrever.
"""
import calendar
import ctypes as C
from ctypes import wintypes as W
from contextlib import contextmanager
from datetime import date, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import threading
import uuid
import compatibilidade as compat
import identidade

ROOT = Path(sys.executable).resolve().parent.parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
DATA = ROOT / 'dados'
DATA.mkdir(exist_ok=True)
GAME = Path.home() / 'Documents/Sports Interactive/Football Manager 2023'
UID = 104749
VTABLE_RVA = 0x4FDCDF8
TEAM_VTABLE_RVA = 0x5002398
DATE_RVA = 0x54623F0
IMAGE_SIZE = 356016128
VERSION = '23.2.0+1771058'
SPONSORS = {1:'Master', 2:'Subvenção pública', 3:'Estádio', 4:'Patrocínio geral',
 5:'Direitos de TV', 6:'Outras receitas', 7:'Sócio-torcedor', 8:'Patrocínio secundário',
 9:'Outro uniforme', 10:'Parachute', 11:'Costas da camisa', 12:'Calção',
 13:'Uniforme de treino', 14:'Equipe de base', 15:'Centro de treinamento',
 16:'Competição continental', 17:'Investimento societário', 18:'Comercial total', 19:'Manga'}
FACILITIES = {'Treinamento':288, 'Instalações de base':299,
              'Formação de jovens':300, 'Recrutamento de jovens':301}
LEVEL_COST = {'Treinamento':350000, 'Instalações de base':300000,
              'Formação de jovens':120000, 'Recrutamento de jovens':150000}
LOCK = threading.RLock()


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def fm_date(raw):
    day, year = struct.unpack('<HH', raw)
    day &= 511
    if not 1900 <= year <= 2199 or not 1 <= day <= (366 if calendar.isleap(year) else 365):
        raise ValueError('Data do FM inválida. Recarregue a conexão com a carreira aberta.')
    return date(year, 1, 1) + timedelta(days=day-1)


def pack_date(value, old=b'\0'*4):
    if not isinstance(value, date) or not 1900 <= value.year <= 2199:
        raise ValueError('Data fora da faixa suportada.')
    flags = int.from_bytes(old[:2], 'little') & 0xFE00
    return struct.pack('<HH', flags | value.timetuple().tm_yday, value.year)


def contract_end(start, years):
    last = calendar.monthrange(start.year+years, start.month)[1]
    end=start.replace(year=start.year+years,day=min(start.day,last))
    return end if start.day>last else end-timedelta(days=1)


k = C.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD]; k.OpenProcess.restype=W.HANDLE
k.CloseHandle.argtypes=[W.HANDLE]
k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
k.ReadProcessMemory.restype=W.BOOL
k.WriteProcessMemory.argtypes=k.ReadProcessMemory.argtypes; k.WriteProcessMemory.restype=W.BOOL
k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t]; k.VirtualQueryEx.restype=C.c_size_t
k.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(W.DWORD)]; k.GetExitCodeProcess.restype=W.BOOL
k.GetProcessId.argtypes=[W.HANDLE]; k.GetProcessId.restype=W.DWORD
k.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)]; k.GetProcessTimes.restype=W.BOOL
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]; k.QueryFullProcessImageNameW.restype=W.BOOL
psapi=C.WinDLL('psapi',use_last_error=True)
class ModuleInfo(C.Structure):
    _fields_=[('base',C.c_void_p),('size',W.DWORD),('entry',C.c_void_p)]
psapi.GetModuleInformation.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(ModuleInfo),W.DWORD]; psapi.GetModuleInformation.restype=W.BOOL
nt = C.WinDLL('ntdll')
nt.NtSuspendProcess.argtypes=[W.HANDLE]; nt.NtSuspendProcess.restype=C.c_long
nt.NtResumeProcess.argtypes=[W.HANDLE]; nt.NtResumeProcess.restype=C.c_long


class MBI(C.Structure):
    _fields_=[('base',C.c_void_p),('allocation',C.c_void_p),('allocation_protect',W.DWORD),
              ('partition',W.WORD),('size',C.c_size_t),('state',W.DWORD),('protect',W.DWORD),('type',W.DWORD)]


class Memory:
    def __init__(self, pid):
        self.handle = k.OpenProcess(0xC38, False, pid)
        self.guard = None
        self.career_guard = None
        if not self.handle:
            raise OSError('Não consegui acessar o FM. Abra os dois programas com o mesmo nível de permissão.')

    def read(self, addr, size):
        if self.guard is None: raise RuntimeError('Build não verificada.')
        self.guard.require_fast()
        return self._sample(addr, size)

    def _sample(self, addr, size):
        if not 0x10000 <= addr < 0x7FFFFFFFFFFF or not 0 < size <= 8*1024*1024:
            raise ValueError('Endereço ou tamanho inválido.')
        data=C.create_string_buffer(size); got=C.c_size_t()
        if not k.ReadProcessMemory(self.handle,addr,data,size,C.byref(got)) or got.value != size:
            raise OSError('A memória mudou ou a carreira foi fechada. Reconecte ao FM.')
        return data.raw

    def write(self, addr, raw):
        if self.guard is None: raise RuntimeError('Build não verificada.')
        self.guard.require_fast()
        if getattr(self,'career_guard',None) is None: raise identidade.IdentityError('Identidade da carreira não verificada.')
        self.career_guard.require()
        done=C.c_size_t(); buf=C.create_string_buffer(raw)
        if not k.WriteProcessMemory(self.handle,addr,buf,len(raw),C.byref(done)) or done.value != len(raw):
            raise OSError('O Windows recusou a escrita no FM.')

    def number(self, addr, fmt='i'):
        return struct.unpack('<'+fmt,self.read(addr,struct.calcsize('<'+fmt)))[0]

    def pointer(self, addr):
        return self.number(addr,'Q')

    def regions(self):
        if self.guard is None: raise RuntimeError('Build não verificada.')
        self.guard.require_fast()
        address=0
        while address<0x7FFFFFFFFFFF:
            info=MBI()
            if not k.VirtualQueryEx(self.handle,address,C.byref(info),C.sizeof(info)): break
            base=info.base or 0
            if info.state==0x1000 and info.type==0x20000 and not info.protect&0x101:
                yield base,info.size
            address=base+info.size

    @contextmanager
    def paused(self):
        if self.guard is None: raise RuntimeError('Build não verificada.')
        self.guard.require_fast()
        # A pausa dura a transação. Contratos reservam blocos antes do commit
        # no mesmo congelamento, incluindo a gravação durável do journal.
        if nt.NtSuspendProcess(self.handle)<0: raise OSError('Não foi possível pausar a escrita com segurança.')
        try: yield
        finally:
            if nt.NtResumeProcess(self.handle)<0:
                raise OSError('Falha ao retomar o processo do FM.')

    def alive(self):
        code=W.DWORD()
        return bool(k.GetExitCodeProcess(self.handle,C.byref(code)) and code.value==259)

    def close(self):
        if self.handle: k.CloseHandle(self.handle); self.handle=None


class ProcessProbe:
    def __init__(self, memory, base): self.memory=memory; self.base=base
    def identity(self):
        h=self.memory.handle
        if not h or not self.memory.alive(): raise OSError('Processo encerrado')
        pid=k.GetProcessId(h)
        created=W.FILETIME(); end=W.FILETIME(); kernel=W.FILETIME(); user=W.FILETIME()
        if not pid or not k.GetProcessTimes(h,C.byref(created),C.byref(end),C.byref(kernel),C.byref(user)): raise OSError('Identidade indisponível')
        started=str(((created.dwHighDateTime << 32) | created.dwLowDateTime)+504911232000000000)
        size=W.DWORD(32768); path=C.create_unicode_buffer(size.value)
        if not k.QueryFullProcessImageNameW(h,0,path,C.byref(size)): raise OSError('Caminho indisponível')
        module=ModuleInfo()
        if not psapi.GetModuleInformation(h,self.base,C.byref(module),C.sizeof(module)): raise OSError('Módulo indisponível')
        return dict(pid=pid,started=started,path=path.value,base=module.base,size=module.size)
    def sample(self,address,size): return self.memory._sample(address,size)


def process_info():
    script = "$ErrorActionPreference='Stop'; $p=@(Get-Process -Name fm -ErrorAction SilentlyContinue); if($p.Count -ne 1){throw 'Abra uma única instância do FM23 com sua carreira carregada.'}; $p=$p[0]; @{pid=$p.Id; started=$p.StartTime.ToUniversalTime().Ticks.ToString(); version=$p.MainModule.FileVersionInfo.ProductVersion; base=$p.MainModule.BaseAddress.ToInt64(); size=$p.MainModule.ModuleMemorySize; path=$p.Path}|ConvertTo-Json -Compress"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,creationflags=0x08000000,timeout=20)
    if result.returncode: raise RuntimeError('Abra uma única instância do FM23 com sua carreira carregada.')
    info=json.loads(result.stdout)
    return info


class FM:
    def __init__(self, progress=lambda message:None):
        self.process=process_info()
        self.mem=Memory(self.process['pid'])
        self.base=self.process['base']; self.club=0
        try:
            progress('Identificando a build do FM23 e verificando o executável…')
            self.guard=compat.BuildGuard(self.process,ProcessProbe(self.mem,self.base))
            self.mem.guard=self.guard
            self.career_guard=identidade.CareerGuard(self.guard)
            self.mem.career_guard=self.career_guard
            self.career_guard.require()
            cache=read_json(DATA/'conexao.json',{})
            if cache.get('pid')==self.process['pid'] and cache.get('started')==self.process['started']:
                self.club=cache.get('club',0)
                try: self.validate()
                except (ValueError,OSError): self.club=0
            if not self.club:
                progress('Localizando o Ceará na carreira…')
                self.club=self.find_club()
            self.validate()
            save_json(DATA/'conexao.json',dict(pid=self.process['pid'],started=self.process['started'],club=self.club))
        except Exception:
            self.mem.close()
            raise

    @classmethod
    def connect_manual(cls, candidate_address, candidate_uid):
        # A implementação de finanças e uniformes atual é homologada apenas para Ceará.
        if candidate_uid != UID:raise ValueError('Este clube ainda não é suportado pelas operações. O suporte atual é o Ceará.')
        self=cls.__new__(cls)
        self.process=process_info();self.mem=Memory(self.process['pid'])
        self.base=self.process['base'];self.club=candidate_address
        try:
            self.guard=compat.BuildGuard(self.process,ProcessProbe(self.mem,self.base))
            self.mem.guard=self.guard
            self.validate()
            self.career_guard=identidade.ManualCareerGuard(self.guard,self.validate)
            self.mem.career_guard=self.career_guard
            self.career_guard.require()
            return self
        except Exception:
            self.mem.close();raise

    def find_club(self):
        needle=struct.pack('<Q',self.base+VTABLE_RVA)
        matches=[]
        for base,size in self.mem.regions():
            for off in range(0,size,4*1024*1024):
                try: data=self.mem.read(base+off,min(4*1024*1024,size-off))
                except OSError: continue
                pos=data.find(needle)
                while pos>=0:
                    candidate=base+off+pos
                    if candidate%8==0:
                        self.club=candidate
                        try:
                            self.validate()
                            matches.append(candidate)
                        except (ValueError,OSError): pass
                    pos=data.find(needle,pos+1)
        self.club=0
        if len(matches)!=1: raise RuntimeError('Não encontrei um registro único e válido do Ceará. Carregue sua carreira e reconecte.')
        return matches[0]

    def validate(self):
        m=self.mem
        if not m.alive() or not self.club: raise ValueError('FM desconectado.')
        if m.pointer(self.club)!=self.base+VTABLE_RVA or m.number(self.club+12,'I')!=UID:
            raise ValueError('O registro do clube mudou. Reconecte.')
        name=m.read(m.pointer(self.club+184)+4,32).split(b'\0',1)[0].decode('utf-8','replace')
        if name!='CEA' and not name.casefold().startswith(('ceará','ceara')):
            raise ValueError('O nome do clube não corresponde ao Ceará.')
        f=m.pointer(self.club+328); i=m.pointer(self.club+248)
        if m.pointer(f+8)!=self.club: raise ValueError('Estrutura financeira não corresponde ao clube.')
        if not -2_000_000_000<m.number(f+20)<2_000_000_000: raise ValueError('Saldo fora da faixa suportada.')
        if any(not 0<=m.number(i+o,'B')<=20 for o in FACILITIES.values()): raise ValueError('Níveis de infraestrutura inválidos.')
        fm_date(m.read(self.base+DATE_RVA,4))
        self.finance=f; self.info=i

    def date(self):
        self.validate()
        return fm_date(self.mem.read(self.base+DATE_RVA,4))

    def kit_team(self):
        self.validate()
        start,end=struct.unpack('<QQ',self.mem.read(self.club+24,16))
        if not start or end<=start or (end-start)%8 or end-start>128:
            raise ValueError('Lista de equipes do clube incompatível.')
        team=self.mem.pointer(start)
        if self.mem.pointer(team)!=self.base+TEAM_VTABLE_RVA or self.mem.pointer(team+48)!=self.club:
            raise ValueError('Equipe principal não corresponde ao clube conectado.')
        return team

    def licensed_kits(self):
        return not bool(self.mem.number(self.kit_team()+46,'B')&8)

    def set_licensed_kits(self,enabled,expected_day=None):
        if type(enabled) is not bool:raise ValueError('Modo de uniforme inválido.')
        address=self.kit_team()+46
        before=self.mem.number(address,'B')
        after=before&~8 if enabled else before|8
        if before==after:return None
        return self.transaction('Uniformes: '+('usar imagens patrocinadas' if enabled else 'usar estilo do editor'),
            [dict(label='Permitir uniformes licenciados',addr=address,before=bytes([before]).hex(),after=bytes([after]).hex())],
            dict(expected_day=expected_day,licensed_kits=enabled))

    def vector(self, addr, limit=100):
        start,end,cap=struct.unpack('<QQQ',self.mem.read(addr,24))
        if not start and not end: return []
        if start>end or end>cap or (end-start)%8 or end-start>limit*8:
            raise ValueError('Lista de dados do jogo inválida.')
        return [self.mem.pointer(a) for a in range(start,end,8)]

    def sponsor_rows(self):
        rows=[]
        for index,addr in enumerate(self.vector(self.mem.pointer(self.club+296))):
            raw=self.mem.read(addr,24); total=struct.unpack_from('<i',raw,8)[0]
            if raw[18] not in SPONSORS or not 0<=total<=2_000_000_000 or raw[19]>1 or raw[20]>1:
                raise ValueError('Contrato incompatível; operação bloqueada.')
            start,end=fm_date(raw[:4]),fm_date(raw[4:8])
            if end<start: raise ValueError('Contrato com datas inconsistentes.')
            rows.append(dict(index=index,addr=addr,raw=raw.hex(),kind=raw[18],name=SPONSORS[raw[18]],
                total=total,start=start.isoformat(),end=end.isoformat(),renew=bool(raw[19]),fixed=bool(raw[20])))
        return rows

    def debt_rows(self):
        rows=[]
        for index,addr in enumerate(self.vector(self.info+80,100)):
            raw=self.mem.read(addr,28)
            original,monthly,interest,conditional=struct.unpack('<iiii',raw[:16])
            if any(not 0<=v<=2_000_000_000 for v in (original,monthly,interest,conditional)):
                raise ValueError('Empréstimo incompatível.')
            if raw[25]>1 or raw[26]>1:raise ValueError('Flags do empréstimo incompatíveis.')
            start,end=fm_date(raw[20:24]),fm_date(raw[16:20])
            rows.append(dict(index=index,addr=addr,raw=raw.hex(),original=original,monthly=monthly,interest=interest,
                conditional=conditional,start=start.isoformat(),end=end.isoformat(),source=raw[24],
                interest_only=raw[26]==1,can_repay=conditional==0 and original>0 and end>=self.date() and (raw[24]==1 or raw[26]==1)))
        return rows

    def snapshot(self):
        with LOCK:
            self.validate();m=self.mem;f=self.finance;i=self.info
            return dict(date=self.date().isoformat(),club='Ceará',uid=UID,
                licensed_kits=self.licensed_kits(),
                balance=m.number(f+20),transfer=m.number(f+1956),season_transfer=m.number(f+1960),
                wage=m.number(f+2024),wage_spend=m.number(f+2036),ticket=m.number(f+24,'f'),
                season_ticket=m.number(f+28,'f'),attendance=m.number(m.pointer(self.club+176)+104),
                facilities={name:m.number(i+o,'B') for name,o in FACILITIES.items()},
                sponsors=self.sponsor_rows(),debts=self.debt_rows(),credit=self.credit_terms())

    def credit_terms(self):
        self.validate()
        nation=self.mem.pointer(self.club+0xd0)
        rate=self.mem.number(nation+0x24c,'f') if nation else 3.5
        if not math.isfinite(rate) or not 0<rate<=100:rate=3.5
        return dict(rate=rate,reputation=self.mem.number(self.kit_team()+0xa8,'H'))

    def change(self, label, address, fmt, value):
        if fmt=='i' and not -2_000_000_000<=value<=2_000_000_000: raise ValueError('Valor fora da faixa permitida.')
        if fmt=='f' and (not math.isfinite(value) or not 0<=value<=100000): raise ValueError('Preço inválido.')
        return dict(label=label,addr=address,before=self.mem.read(address,struct.calcsize('<'+fmt)).hex(),after=struct.pack('<'+fmt,value).hex())

    def transaction(self, title, changes, meta=None):
        if not changes: raise ValueError('Nenhuma alteração selecionada.')
        with LOCK:
            self.guard.require_full()
            self.career_guard.require()
            self.validate()
            stamp=self.mem.read(self.base+DATE_RVA,4)
            if meta and meta.get('expected_day') and fm_date(stamp).isoformat()!=meta['expected_day']:
                raise ValueError('O dia do jogo mudou antes da aplicação. Atualize o painel.')
            entry=dict(id=uuid.uuid4().hex,title=title,status='prepared',time=datetime.now().isoformat(),
                date=fm_date(stamp).isoformat(),process=self.process,club=self.club,uid=UID,changes=changes,meta=meta or {})
            journal=DATA/'historico'/f"{datetime.now():%Y%m%d-%H%M%S-%f}-{entry['id']}.json"
            save_json(journal,entry) # durable intent before the first write
            applied=[]
            try:
                with self.mem.paused():
                    try:
                        self.validate()
                        if self.mem.read(self.base+DATE_RVA,4)!=stamp: raise ValueError('A data do jogo mudou; repita a operação com o FM parado.')
                        for change in changes:
                            before=bytes.fromhex(change['before']);after=bytes.fromhex(change['after'])
                            if len(before)!=len(after) or not before: raise ValueError('Transação inválida.')
                            if self.mem.read(change['addr'],len(before))!=before:
                                raise ValueError('Os dados mudaram desde a leitura; atualize antes de aplicar.')
                        for change in changes:
                            applied.append(change)
                            raw=bytes.fromhex(change['after']);self.mem.write(change['addr'],raw)
                            if self.mem.read(change['addr'],len(raw))!=raw: raise OSError('A verificação da escrita falhou.')
                    except Exception:
                        for change in reversed(applied):
                            self.mem.write(change['addr'],bytes.fromhex(change['before']))
                        raise
                entry['status']='applied'
            except Exception as exc:
                entry['status']='failed';entry['error']=str(exc);save_json(journal,entry);raise
            save_json(journal,entry)
            return entry

    def budgets(self, transfer, wage):
        self.validate()
        if not 0<=transfer<=1_000_000_000 or not 0<=wage<=20_000_000: raise ValueError('Orçamento inválido.')
        # Allocating budget is not spending cash; player payments remain managed by FM.
        return self.transaction('Redistribuição dos orçamentos',[
            self.change('Transferências disponíveis',self.finance+1956,'i',transfer),
            self.change('Folha semanal',self.finance+2024,'i',wage)])

    def capital(self, amount):
        if not isinstance(amount,int) or not 1<=amount<=1_000_000_000: raise ValueError('Aporte inválido.')
        self.validate();balance=self.mem.number(self.finance+20)
        return self.transaction('Aporte da presidência', [self.change('Caixa',self.finance+20,'i',balance+amount)])

    def prices(self, ticket, season):
        self.validate()
        return self.transaction('Preços da bilheteria',[
            self.change('Ingresso médio',self.finance+24,'f',ticket),
            self.change('Carnê de temporada',self.finance+28,'f',season)])

    def invest(self, name):
        self.validate()
        if name not in FACILITIES: raise ValueError('Investimento inválido.')
        level=self.mem.number(self.info+FACILITIES[name],'B')
        if level>=20: raise ValueError('O nível máximo já foi atingido.')
        cost=LEVEL_COST[name]*(level+1);balance=self.mem.number(self.finance+20)
        if balance<cost: raise ValueError('Caixa insuficiente para esse investimento.')
        return self.transaction('Investimento: '+name,[
            self.change('Caixa',self.finance+20,'i',balance-cost),
            self.change(name,self.info+FACILITIES[name],'B',level+1)],dict(cost=cost,previous=level,target=level+1))

    def update_sponsor(self, index, total, start, end, expected, brand='', expected_day=None, metadata=None, replace_overlaps=False):
        self.validate();rows=self.sponsor_rows()
        if not 0<=index<len(rows): raise ValueError('Contrato não encontrado.')
        row=rows[index]
        if expected_day and self.date().isoformat()!=expected_day:raise ValueError('O dia da carreira mudou. Atualize a mesa antes de assinar.')
        if row['raw']!=expected: raise ValueError('O contrato mudou. Selecione-o novamente.')
        if end<=start or not 1<=total<=1_000_000_000: raise ValueError('Revise o valor total e a vigência.')
        before=bytes.fromhex(row['raw']);after=bytearray(before)
        after[:4]=pack_date(start,before[:4]);after[4:8]=pack_date(end,before[4:8])
        struct.pack_into('<ii',after,8,total,0);after[19]=0;after[20]=1
        changes=[dict(label=row['name'],addr=row['addr'],before=before.hex(),after=after.hex())]
        replaced=[]
        if replace_overlaps and row['kind'] in {1,3,8,9,11,12,13,19}:
            today=self.date()
            for other in rows:
                if other['index']==index or other['kind']!=row['kind'] or not other['total']:continue
                if date.fromisoformat(other['end'])<start or date.fromisoformat(other['start'])>end:continue
                old=bytes.fromhex(other['raw']);new=bytearray(old)
                new[:4]=pack_date(today,old[:4]);new[4:8]=pack_date(today,old[4:8])
                new[8:16]=b'\0'*8;new[19]=0;new[20]=1
                changes.append(dict(label='Substituição de receita sobreposta',addr=other['addr'],before=old.hex(),after=new.hex()))
                replaced.append(dict(index=other['index'],kind=other['kind'],total=other['total'],start=other['start'],end=other['end']))
        return self.transaction('Patrocínio: '+(brand or row['name']),changes,
            dict(kind=row['kind'],total=total,start=start.isoformat(),end=end.isoformat(),brand=brand,expected_day=expected_day,replaced=replaced,**(metadata or {})))

    def terminate_sponsor(self,index,expected,penalty,expected_day,metadata=None):
        self.validate();rows=self.sponsor_rows()
        if type(penalty) is not int or not 0<=penalty<=1_000_000_000:raise ValueError('Multa inválida.')
        if not 0<=index<len(rows):raise ValueError('Contrato não encontrado.')
        row=rows[index]
        if row['kind'] not in {1,3,4,7,8,9,11,12,13,14,15,19}:raise ValueError('Esta receita não é um contrato comercial negociável.')
        if row['raw']!=expected or self.date().isoformat()!=expected_day:raise ValueError('O contrato ou a data mudaram. Atualize antes de rescindir.')
        balance=self.mem.number(self.finance+20)
        if balance<penalty:raise ValueError('Caixa insuficiente para a multa rescisória.')
        before=bytes.fromhex(row['raw']);after=bytearray(before);today=self.date()
        after[:4]=pack_date(today,before[:4]);after[4:8]=pack_date(today,before[4:8])
        after[8:16]=b'\0'*8;after[19]=0;after[20]=1
        changes=[dict(label='Encerramento do contrato',addr=row['addr'],before=before.hex(),after=after.hex())]
        if penalty:changes.append(self.change('Multa debitada do caixa',self.finance+20,'i',balance-penalty))
        return self.transaction('Rescisão de patrocínio',changes,dict(penalty=penalty,expected_day=expected_day,**(metadata or {})))

    def repay(self, index, expected):
        from emprestimos import repay
        return repay(self,index,expected)

    def undo(self, entry):
        self.validate()
        if entry['status']!='applied' or entry['process']['started']!=self.process['started'] or entry['process']['pid']!=self.process['pid'] or entry['club']!=self.club:
            raise ValueError('Desfazer exige a mesma sessão do FM e uma operação aplicada.')
        if entry['date']!=self.date().isoformat(): raise ValueError('A data avançou. Use o backup do save para voltar a outro dia.')
        return self.transaction('Desfazer: '+entry['title'],[dict(label=c['label'],addr=c['addr'],before=c['after'],after=c['before']) for c in reversed(entry['changes'])],dict(undoes=entry['id']))

    def close(self):
        if hasattr(self,'career_guard') and hasattr(self.career_guard,'revoke'):self.career_guard.revoke()
        self.mem.close()


def backup_save():
    saves=list((GAME/'games').glob('*.fm'))
    if not saves: raise ValueError('Nenhum save local encontrado para backup.')
    source=max(saves,key=lambda p:p.stat().st_mtime)
    dest=DATA/'backups'/f'{source.stem}-{datetime.now():%Y%m%d-%H%M%S}.fm'
    dest.parent.mkdir(parents=True,exist_ok=True)
    before=source.stat()
    shutil.copy2(source,dest)
    after=source.stat()
    if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns or dest.stat().st_size!=before.st_size:
        raise OSError('O save estava sendo gravado. Repita o backup quando a gravação terminar.')
    save_json(dest.with_suffix('.json'),dict(source=str(source),size=before.st_size,mtime=before.st_mtime_ns))
    return dest
