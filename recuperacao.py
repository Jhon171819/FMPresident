"""Diagnóstico conservador de journals existentes, sem escrita no FM."""
from dataclasses import dataclass, replace
from pathlib import Path
import json
import re

@dataclass(frozen=True)
class Record:
    operation_id: str
    title: str
    time: str
    state: str
    resource: str
    process_pid: int | None
    process_started: str | None
    reason: str

    def public(self):
        return dict(id=self.operation_id,title=self.title,time=self.time,state=self.state,
                    resource=self.resource,reason=self.reason)

VALID={'prepared','applied','failed','rollback_verified','recovery_required'}

def read_record(path):
    if path.suffix.lower()=='.tmp':
        return Record('', 'Registro temporário incompleto', '', 'JOURNAL_UNREADABLE','Indeterminado',None,None, 'Escrita de journal possivelmente interrompida; preserve o arquivo.')
    try:
        with path.open('r',encoding='utf-8-sig') as f:
            raw=f.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise ValueError('arquivo excede limite')
        entry=json.loads(raw)
        if not isinstance(entry,dict):raise ValueError('registro não é objeto')
        version=entry.get('schema_version',0)
        if type(version) is not int or version not in (0,1):raise ValueError('versão não reconhecida')
        opid=entry.get('id');process=entry.get('process');status=entry.get('status')
        if not isinstance(opid,str) or not re.fullmatch('[0-9a-f]{32}',opid):raise ValueError('ID inválido')
        if not isinstance(process,dict) or type(process.get('pid')) is not int or not isinstance(process.get('started'),str):raise ValueError('processo ausente')
        if status not in VALID or not isinstance(entry.get('changes'),list) or not entry['changes']:raise ValueError('estado ou alterações inválidas')
        if any(not isinstance(c,dict) or not all(k in c for k in ('label','addr','before','after')) for c in entry['changes']):raise ValueError('alteração incompleta')
        for c in entry['changes']:
            if not isinstance(c['label'],str) or type(c['addr']) is not int or c['addr']<=0:raise ValueError('alteração inválida')
            if not isinstance(c['before'],str) or not isinstance(c['after'],str):raise ValueError('bytes inválidos')
            before=bytes.fromhex(c['before']);after=bytes.fromhex(c['after'])
            if not before or len(before)!=len(after) or len(before)>8*1024*1024:raise ValueError('tamanho inconsistente')
        if not isinstance(entry.get('title'),str) or not isinstance(entry.get('time'),str):raise ValueError('metadados ausentes')
        local=entry.get('local_commit')
        if local not in (None,'pending','committed'):raise ValueError('commit local inválido')
        if status=='applied' and local=='pending':state='LOCAL_COMMIT_PENDING'
        elif status=='applied':state='MEMORY_APPLIED'
        elif status=='prepared':state='STATE_UNKNOWN'
        elif status=='recovery_required':state='RECOVERY_REQUIRED'
        elif status=='rollback_verified':state='ROLLBACK_VERIFIED'
        elif version==0:state='STATE_UNKNOWN'
        else:state='NOT_APPLIED'
        meta=entry.get('meta',{})
        if not isinstance(meta,dict):raise ValueError('metadados inválidos')
        resource='Patrocínio / dados locais' if 'sponsor_contract' in meta or 'sponsor_termination' in meta else 'Memória do clube'
        return Record(opid,entry['title'][:120],entry['time'][:40],state,resource,process['pid'],process['started'],
                      'PID e início identificam o processo, não o save.')
    except (OSError,ValueError,TypeError,UnicodeError,RecursionError):
        return Record('', 'Registro ilegível', '', 'JOURNAL_UNREADABLE','Indeterminado',None,None,
                      'Não foi possível determinar a operação ou seu contexto; preserve o arquivo e consulte os logs.')

def scan(directory):
    path=Path(directory)
    try:files=sorted(p for p in path.iterdir() if p.suffix.lower() in ('.json','.tmp'))
    except FileNotFoundError:return []
    except OSError:return [Record('','Histórico indisponível','','JOURNAL_UNREADABLE','Indeterminado',None,None,'Não foi possível ler o histórico.')]
    records=[read_record(p) for p in files]
    counts={}
    for r in records:
        if r.operation_id:counts[r.operation_id]=counts.get(r.operation_id,0)+1
    return [replace(r,state='JOURNAL_UNREADABLE',reason='Identificador duplicado; associação incerta.') if r.operation_id and counts[r.operation_id]>1 else r for r in records]

def blocking(records,process,resource=None):
    for r in records:
        if r.state=='JOURNAL_UNREADABLE':return r
        if r.state in ('STATE_UNKNOWN','RECOVERY_REQUIRED','LOCAL_COMMIT_PENDING'):
            # Somente bilheteria (dois campos de preço) é tratada como independente
            # de metadados locais após confirmação da escrita de patrocínio.
            if r.state=='LOCAL_COMMIT_PENDING' and r.resource=='Patrocínio / dados locais' and resource=='ticket':continue
            return r
    return None
