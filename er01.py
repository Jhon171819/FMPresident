"""Infraestrutura de pesquisa offline. Não importa fm23 nem abre processos."""
import hashlib
import inspect
import json
import sqlite3
import time
import zlib
from collections import deque
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATES={'COMPLETE','PARTIAL','INTERRUPTED','INVALID','LEGACY_UNVERIFIED'}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(data):return hashlib.sha256(data).hexdigest()
def fingerprint(path):
    path=Path(path)
    before=path.stat()
    with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Entrada mudou durante fingerprint')
    return {'sha256':sha,'size':after.st_size}

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=30)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA journal_mode=WAL')
        version=self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0,1):self.db.close();raise ValueError('Versão do banco não suportada; banco preservado')
        with self.db:
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS binaries(id TEXT PRIMARY KEY, meta TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts(key TEXT PRIMARY KEY, binary TEXT REFERENCES binaries(id), kind TEXT NOT NULL,
              subject TEXT NOT NULL, analyzer TEXT NOT NULL, params TEXT NOT NULL, state TEXT NOT NULL,
              content_hash TEXT NOT NULL, payload BLOB NOT NULL, created REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS artifact_lookup ON artifacts(binary,kind,subject,state);
            CREATE TABLE IF NOT EXISTS dependencies(parent TEXT REFERENCES artifacts(key),child TEXT REFERENCES artifacts(key),PRIMARY KEY(parent,child));
            CREATE TABLE IF NOT EXISTS edges(binary TEXT REFERENCES binaries(id),source TEXT,target TEXT,relation TEXT,confidence TEXT,provenance TEXT,
              PRIMARY KEY(binary,source,target,relation,confidence,provenance));
            CREATE INDEX IF NOT EXISTS edge_source ON edges(binary,source);
            CREATE INDEX IF NOT EXISTS edge_target ON edges(binary,target);
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,spec TEXT NOT NULL,state TEXT NOT NULL,checkpoint TEXT NOT NULL,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS task_priority(id TEXT PRIMARY KEY REFERENCES tasks(id),value REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,status TEXT NOT NULL,body TEXT NOT NULL,provenance TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,metrics TEXT NOT NULL);
            PRAGMA user_version=1;
            ''')
        check=self.db.execute('PRAGMA quick_check').fetchone()[0]
        if check!='ok':self.db.close();raise ValueError('Banco corrompido; preserve para recuperação')
    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def binary(self,identity):
        key=identity['sha256']
        with self.db:self.db.execute('INSERT OR IGNORE INTO binaries VALUES (?,?)',(key,canonical(identity)))
        return key
    @staticmethod
    def key(binary,kind,subject,analyzer,params):
        return digest(canonical([binary,kind,str(subject),analyzer,params]).encode())
    def get(self,key):
        row=self.db.execute('SELECT * FROM artifacts WHERE key=?',(key,)).fetchone()
        if not row or row['state']=='INVALID':return None
        try:
            raw=zlib.decompress(row['payload'])
            if digest(raw)!=row['content_hash']:raise ValueError('Hash do conteúdo divergente')
            return dict(row)|{'value':json.loads(raw)}
        except (ValueError,zlib.error,UnicodeError):
            self.db.execute("UPDATE artifacts SET state='INVALID' WHERE key=?",(key,));return None
    def put(self,key,binary,kind,subject,analyzer,params,state,value,dependencies=()):
        if state not in STATES:raise ValueError('Estado inválido')
        raw=canonical(value).encode();blob=zlib.compress(raw)
        self.db.execute('''INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET
            state=excluded.state,content_hash=excluded.content_hash,payload=excluded.payload,created=excluded.created''',
                        (key,binary,kind,str(subject),analyzer,canonical(params),state,digest(raw),blob,time.time()))
        for parent in dependencies:self.db.execute('INSERT OR IGNORE INTO dependencies VALUES (?,?)',(parent,key))
        return len(blob)
    def cached(self,binary,kind,subject,analyzer,params,compute,force=False):
        key=self.key(binary,kind,subject,analyzer,params)
        # ponytail: um escritor por banco durante compute; separar leases se análises longas exigirem paralelismo.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=None if force else self.get(key)
            if old and old['state'] in ('COMPLETE','PARTIAL'):
                self.db.commit();return old['value'],{'hit':1,'computed':0,'state':old['state'],'key':key,'bytes_written':0}
            value=compute();state='PARTIAL' if value.get('bounded',False) else 'COMPLETE'
            written=self.put(key,binary,kind,subject,analyzer,params,state,value)
            self.db.commit();return value,{'hit':0,'computed':1,'state':state,'key':key,'bytes_written':written}
        except BaseException:self.db.rollback();raise
    def invalidate(self,keys,dry_run=True):
        found=set(keys);pending=list(keys)
        while pending:
            for row in self.db.execute('SELECT child FROM dependencies WHERE parent=?',(pending.pop(),)):
                if row[0] not in found:found.add(row[0]);pending.append(row[0])
        if not dry_run:
            with self.db:self.db.executemany("UPDATE artifacts SET state='INVALID' WHERE key=?",[(k,) for k in found])
        return sorted(found)
    def task(self,identifier,spec):
        text=canonical(spec);old=self.db.execute('SELECT * FROM tasks WHERE id=?',(identifier,)).fetchone()
        if old and old['spec']!=text:raise ValueError('Entradas/configuração da tarefa mudaram; use novo ID')
        if not old:
            with self.db:self.db.execute('INSERT INTO tasks VALUES (?,?,?,?,?)',(identifier,text,'PENDING',canonical({'done':[],'frontier':spec.get('rvas',[])}),time.time()))
        return self.db.execute('SELECT * FROM tasks WHERE id=?',(identifier,)).fetchone()
    def checkpoint(self,identifier,done,frontier,state):
        with self.db:self.db.execute('UPDATE tasks SET state=?,checkpoint=?,updated=? WHERE id=?',
          (state,canonical({'done':done,'frontier':frontier}),time.time(),identifier))
    def evidence(self,identifier,status,body,provenance):
        if status not in ('HYPOTHESIS','OBSERVED','PARTIAL','VERIFIED','REFUTED','INCONCLUSIVE'):raise ValueError('Estado de evidência inválido')
        if not provenance:raise ValueError('Proveniência obrigatória')
        with self.db:self.db.execute('INSERT OR REPLACE INTO evidence VALUES (?,?,?,?)',(identifier,status,canonical(body),provenance))
    def plan(self):
        result=[]
        for row in self.db.execute("SELECT * FROM tasks WHERE state NOT IN ('COMPLETE','CANCELLED','PAUSED','IGNORED')"):
            spec=json.loads(row['spec']);missing=[]
            for dep in spec.get('dependencies',[]):
                d=self.db.execute('SELECT state FROM tasks WHERE id=?',(dep,)).fetchone()
                if not d or d[0]!='COMPLETE':missing.append(dep)
            override=self.db.execute('SELECT value FROM task_priority WHERE id=?',(row['id'],)).fetchone()
            score=(override[0] if override else spec.get('priority',0))+spec.get('novelty',0)-spec.get('cost',1)-spec.get('risk',0)
            result.append({'id':row['id'],'score':score,'ready':not missing,'reason':f'priority + novelty - cost - risk; missing={missing}'})
        return sorted(result,key=lambda r:(not r['ready'],-r['score'],r['id']))
    def walk(self,binary,start,depth=3,nodes=100,edges=500,seconds=1,checkpoint=None):
        previous=checkpoint or {}
        pending=deque(previous.get('frontier',[(start,0)]));seen=set(previous.get('nodes',[]));out=list(previous.get('edges',[]));deadline=time.monotonic()+seconds
        while pending and len(seen)<nodes and len(out)<edges and time.monotonic()<deadline:
            node,d=pending.popleft()
            if node in seen:continue
            seen.add(node)
            if d>=depth:continue
            adjacent=list(self.db.execute("SELECT * FROM edges WHERE binary=? AND source=? AND confidence!='REFUTED' LIMIT ?",(binary,node,edges-len(out)+1)))
            if len(adjacent)>edges-len(out):
                seen.remove(node);pending.appendleft((node,d));break
            for row in adjacent:
                out.append(dict(row));pending.append((row['target'],d+1))
        return {'nodes':sorted(seen),'edges':out,'frontier':list(pending),'bounded':bool(pending)}

class SnapshotReads:
    """Cache efêmero de UMA observação não atômica; fonte deve ser Reader validado."""
    def __init__(self,read,context,validate,regions,byte_limit=65536,call_limit=100,seconds=2,failure_limit=3):
        if len(regions)>256 or any(a>=b for a,b in regions):raise ValueError('Limite ou formato de regiões')
        self.source=read;self.context=context;self.validate=validate;self.regions=regions
        self.byte_limit=byte_limit;self.call_limit=call_limit;self.deadline=time.monotonic()+seconds;self.failure_limit=failure_limit
        self.cache={};self.bytes=0;self.calls=0;self.failures=0;self.hits=0;self.closed=False
    def read(self,address,size,fresh=False):
        if self.closed or not self.validate(self.context):self.cache.clear();raise ValueError('Contexto inválido')
        if type(address) is not int or type(size) is not int or address<0x10000 or size<=0:raise ValueError('Pedido inválido')
        if not any(a<=address and address+size<=b for a,b in self.regions):raise ValueError('Região não permitida')
        if time.monotonic()>self.deadline:raise ValueError('Orçamento de tempo')
        if not fresh:
            for (a,n),raw in self.cache.items():
                if a<=address and address+size<=a+n:self.hits+=1;return raw[address-a:address-a+size]
        if self.calls>=self.call_limit or self.bytes+size>self.byte_limit or self.failures>=self.failure_limit:raise ValueError('Orçamento de leitura')
        self.calls+=1;self.bytes+=size
        try:
            raw=self.source(address,size)
            if len(raw)!=size:raise ValueError('Leitura truncada')
        except Exception:self.failures+=1;raise
        if not self.validate(self.context):self.cache.clear();raise ValueError('Contexto mudou durante leitura')
        if fresh:
            for (a,n),old in self.cache.items():
                lo=max(a,address);hi=min(a+n,address+size)
                if lo<hi and old[lo-a:hi-a]!=raw[lo-address:hi-address]:
                    self.close();raise ValueError('Observação inconsistente')
        self.cache[address,size]=raw;return raw
    def batch(self,requests):
        # Agrupa apenas pedidos contíguos na mesma região declarada legível.
        groups=[]
        for a,n in sorted(set(requests)):
            if n<=0 or not any(lo<=a and a+n<=hi for lo,hi in self.regions):raise ValueError('Pedido fora da região')
            if groups and a<=groups[-1][1] and any(lo<=groups[-1][0] and a+n<=hi for lo,hi in self.regions):groups[-1][1]=max(groups[-1][1],a+n)
            else:groups.append([a,a+n])
        for a,b in groups:self.read(a,b-a)
        return [self.read(a,n) for a,n in requests]
    def close(self):self.cache.clear();self.closed=True
    def follow(self,address,offsets,max_depth=8,max_objects=64):
        import struct
        if len(offsets)>max_depth:raise ValueError('Profundidade excedida')
        seen={address}
        for offset in offsets:
            address=struct.unpack('<Q',self.read(address+offset,8))[0]
            if address in seen:raise ValueError('Ciclo de ponteiros')
            seen.add(address)
            if len(seen)>max_objects:raise ValueError('Limite de objetos')
        return address
