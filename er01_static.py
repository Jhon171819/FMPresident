"""Adaptadores offline para os artefatos e analisadores históricos."""
import hashlib,inspect,json,sys,time,os
from pathlib import Path
from er01 import ROOT,Store,canonical,digest,fingerprint

def process_usage():
    """Mede apenas o próprio processo da ferramenta, nunca o FM."""
    if os.name!='nt':return {}
    import ctypes as c
    from ctypes import wintypes as w
    class Memory(c.Structure):
        _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(name,c.c_size_t) for name in ('peak_rss','rss','quota_peak_paged','quota_paged','quota_peak_nonpaged','quota_nonpaged','pagefile','peak_pagefile')]
    class IO(c.Structure):
        _fields_=[(name,c.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    k=c.WinDLL('kernel32');ps=c.WinDLL('psapi');k.GetCurrentProcess.restype=w.HANDLE
    handle=k.GetCurrentProcess();mem=Memory();mem.cb=c.sizeof(mem);io=IO();result={}
    ps.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.POINTER(Memory),w.DWORD]
    k.GetProcessIoCounters.argtypes=[w.HANDLE,c.POINTER(IO)]
    if ps.GetProcessMemoryInfo(handle,c.byref(mem),mem.cb):result.update(rss=mem.rss,peak_rss=mem.peak_rss)
    if k.GetProcessIoCounters(handle,c.byref(io)):result.update(logical_read_bytes=io.read_bytes,logical_write_bytes=io.write_bytes)
    return result

def imports():
    sys.path[:0]=[str(ROOT/'engenharia_reversa'),str(ROOT/'engenharia_reversa/ferramentas')]
    from analisar_executavel import PE
    from investigar_gestao import graph
    import capstone as cs
    return PE,graph,cs

def identity(exe):
    # Identificação streaming; warm cache não instancia o parser PE histórico.
    value=fingerprint(exe)
    import struct
    with Path(exe).open('rb') as stream:
        if stream.read(2)!=b'MZ':raise ValueError('Não é PE')
        stream.seek(0x3c);pe=struct.unpack('<I',stream.read(4))[0];stream.seek(pe)
        if stream.read(4)!=b'PE\0\0':raise ValueError('PE inválido')
        machine,sections=struct.unpack('<HH',stream.read(4));stream.seek(pe+24)
        magic=struct.unpack('<H',stream.read(2))[0]
        if machine!=0x8664 or magic!=0x20b:raise ValueError('Esperado PE Windows x64')
    return value|{'architecture':'x64','machine':machine,'sections':sections}

def analyze(store,exe,rvas,config=None,task_id=None,max_functions=None,force=False):
    config=config or {'instructions':400,'blocks':50}
    if set(config)!= {'instructions','blocks'} or any(type(n) is not int or not 1<=n<=100000 for n in config.values()):raise ValueError('Limites inválidos')
    if len(rvas)>10000 or any(type(r) is not int or r<0 for r in rvas):raise ValueError('RVAs inválidos')
    wall=time.perf_counter();cpu=time.process_time();usage_before=process_usage();ident=identity(exe);fingerprint_s=time.perf_counter()-wall;binary=store.binary(ident)
    PE,graph,cs=imports()
    algorithm=digest((inspect.getsource(graph)+inspect.getsource(PE)+cs.__version__).encode())
    spec={'binary':binary,'algorithm':algorithm,'params':config,'rvas':sorted(set(rvas))}
    identifier=task_id or digest(canonical(spec).encode())[:24]
    task=store.task(identifier,spec)
    if task['state'] in ('PAUSED','CANCELLED','IGNORED'):return {'task':identifier,'state':task['state']}
    checkpoint=json.loads(task['checkpoint']);done=[];all_rvas=spec['rvas'];pe=None
    stats={'task':identifier,'binary':binary,'hit':0,'computed':0,'partial':0,'bytes_written':0,'fingerprint_bytes':ident['size']}
    # Revalida também entradas já concluídas: conteúdo corrompido nunca vira checkpoint confiável.
    try:
        for position,rva in enumerate(all_rvas):
            if max_functions is not None and position>=max_functions:
                store.checkpoint(identifier,done,all_rvas[position:],'INTERRUPTED');break
            def compute():
                nonlocal pe
                if pe is None:
                    pe=PE(exe,mapped=True)
                    if digest(pe.data)!=binary:raise ValueError('Binário mudou entre fingerprint e análise')
                if not pe.section(rva) or not pe.section(rva)['flags']&0x20000000:raise ValueError('RVA fora de código')
                md=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64);md.detail=True
                g=graph(pe,md,cs,rva,config['instructions'],config['blocks'])
                interval=g['range'];end=interval[1] if interval else rva+4096
                g['input_bytes_sha256']=digest(pe.read(rva,end-rva));return g
            result,metric=store.cached(binary,'graph',rva,algorithm,config,compute,force)
            stats['hit']+=metric['hit'];stats['computed']+=metric['computed'];stats['bytes_written']+=metric['bytes_written'];stats['partial']+=int(metric['state']=='PARTIAL')
            with store.db:
                for call in result.get('calls',[]):
                    if call.get('target') is not None:store.db.execute('INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?,?)',(binary,str(rva),str(call['target']),'call','STATIC',metric['key']))
            done.append(rva);store.checkpoint(identifier,done,all_rvas[position+1:],'RUNNING')
        else:store.checkpoint(identifier,done,[],'COMPLETE')
    except BaseException:
        if pe is not None:pe.close()
        store.checkpoint(identifier,done,[r for r in all_rvas if r not in done],'INTERRUPTED');raise
    stats.update(wall_s=time.perf_counter()-wall,cpu_s=time.process_time()-cpu,
                 state=store.db.execute('SELECT state FROM tasks WHERE id=?',(identifier,)).fetchone()[0],
                 parser_loaded=pe is not None)
    after=process_usage();stats['process_usage']=after
    stats['logical_io_delta']={k:after[k]-usage_before[k] for k in ('logical_read_bytes','logical_write_bytes') if k in after and k in usage_before}
    stats['fingerprint_s']=fingerprint_s
    with store.db:store.db.execute('INSERT INTO runs(metrics) VALUES (?)',(canonical(stats),))
    if pe is not None:pe.close()
    return stats

def import_legacy(store,folder,binary):
    folder=Path(folder);counts={'classes':0,'vtables':0,'functions':0,'graphs':0,'partial':0,'evidence':0}
    for path in sorted(folder.glob('*.json')):
        if path.stat().st_size>32*1024*1024:continue
        try:data=json.loads(path.read_text(encoding='utf-8'))
        except (ValueError,UnicodeError):continue
        if not isinstance(data,list):continue
        filehash=fingerprint(path)['sha256']
        with store.db:
            for item in data:
                if not isinstance(item,dict):continue
                if 'class_name' in item and 'vtables' in item:
                    records=[('class',item['class_name'],item)];counts['classes']+=1
                    for vt in item['vtables']:
                        records.append(('vtable',vt['rva'],vt));counts['vtables']+=1
                        for f in vt.get('functions',[]):records.append(('function',f['rva'],f));counts['functions']+=1
                elif 'start' in item and 'instructions' in item:
                    records=[('graph',item['start'],item)];counts['graphs']+=1;counts['partial']+=bool(item.get('bounded'))
                elif 'id' in item and 'description' in item:
                    status=item.get('status','HYPOTHESIS')
                    if status not in ('HYPOTHESIS','OBSERVED','PARTIAL','VERIFIED','REFUTED','INCONCLUSIVE'):status='INCONCLUSIVE'
                    # Não efetua commit aninhado: mantém importação transacional por arquivo.
                    store.db.execute('INSERT OR REPLACE INTO evidence VALUES (?,?,?,?)',(item['id'],status,canonical(item),path.name+':'+filehash));counts['evidence']+=1;continue
                else:continue
                for kind,subject,value in records:
                    params={'source_hash':filehash,'source':path.name}
                    key=store.key(binary,'legacy_'+kind,subject,'legacy-import-v1',params)
                    store.put(key,binary,'legacy_'+kind,subject,'legacy-import-v1',params,'LEGACY_UNVERIFIED',value)
    return counts

def index_class(store,exe,name):
    """Extrai apenas RTTI e endereços; desmontagem de métodos usa analyze/cache."""
    import struct
    ident=identity(exe);binary=store.binary(ident);PE,_,_=imports()
    analyzer=digest((inspect.getsource(index_class)+inspect.getsource(PE)).encode())
    def compute():
        pe=PE(exe,mapped=True)
        try:
            if digest(pe.data)!=binary:raise ValueError('Binário mudou')
            target=name if name.startswith('.?') else '.?AV'+name+'@@'
            at=pe.data.find(target.encode()+b'\0')
            if at<0:return {'class_name':target,'vtables':[],'located':False}
            td=pe.rva_at(at)-16;section=pe.section(0x4fdcdf8)
            lo=section['raw_offset'];hi=lo+section['raw_size'];pos=pe.data.find(struct.pack('<I',td),lo,hi);locators=[]
            while pos>=0:
                col=pos-12
                if col>=lo:
                    sig,offset,ctor,t,h,self_rva=pe.unpack('IIIIII',col)
                    if sig==1 and t==td and pe.rva_at(col)==self_rva:locators.append((self_rva,offset))
                pos=pe.data.find(struct.pack('<I',td),pos+1,hi)
            tables=[]
            for locator,offset in locators:
                needle=struct.pack('<Q',pe.image_base+locator);pos=pe.data.find(needle,lo,hi)
                while pos>=0:
                    vt=pe.rva_at(pos)+8;rtti=pe.rtti(vt)
                    if rtti and rtti['class_name']==target:
                        methods=[]
                        for slot in range(512):
                            rva=struct.unpack('<Q',pe.read(vt+slot*8,8))[0]-pe.image_base;s=pe.section(rva)
                            if not s or not s['flags']&0x20000000:break
                            methods.append({'slot':slot,'rva':rva})
                        tables.append({'rva':vt,'object_offset':offset,'methods':methods,'bounded':len(methods)==512})
                    pos=pe.data.find(needle,pos+1,hi)
            return {'class_name':target,'vtables':tables,'located':True,'bounded':any(t['bounded'] for t in tables)}
        finally:pe.close()
    value,metrics=store.cached(binary,'rtti',name,analyzer,{'method_limit':512,'section_anchor':0x4fdcdf8},compute)
    return {'value':value,'metrics':metrics}


def read_hierarchy(pe,vtable,max_bases=64):
    """RTTI MSVC x64 relativo à imagem; segue somente o COL já localizado."""
    import struct
    locator=pe.rtti(vtable)
    if not locator:raise ValueError('COL inválido')
    signature,attributes,count,array=struct.unpack('<IIII',pe.read(locator['hierarchy_rva'],16))
    if signature!=0 or not 1<=count<=max_bases:raise ValueError('Hierarquia incompatível ou limite de bases')
    records=[]
    for descriptor in struct.unpack('<'+'I'*count,pe.read(array,count*4)):
        td,contained,mdisp,pdisp,vdisp,flags,chd=struct.unpack('<IIiiiII',pe.read(descriptor,28))
        name=pe.string(td+16)
        if not name.startswith('.?A'):raise ValueError('Tipo RTTI incompatível')
        records.append({'class_name':name,'descriptor_rva':descriptor,'contained':contained,
                        'mdisp':mdisp,'pdisp':pdisp,'vdisp':vdisp,'attributes':flags,'hierarchy_rva':chd})
    return {'locator':locator,'attributes':attributes,'bases':records,'bounded':False,
            'scope':'Descritores estáticos de herança; não prova ligação de uma linha da UI nem UID'}


def index_hierarchy(store,exe,vtable):
    ident=identity(exe);binary=store.binary(ident);PE,_,_=imports()
    analyzer=digest((inspect.getsource(read_hierarchy)+inspect.getsource(PE)).encode())
    def compute():
        pe=PE(exe,mapped=True)
        try:
            if digest(pe.data)!=binary:raise ValueError('Binário mudou')
            return read_hierarchy(pe,vtable)
        finally:pe.close()
    value,metric=store.cached(binary,'rtti_hierarchy',vtable,analyzer,{'max_bases':64},compute)
    return {'binary':binary,'value':value,'metrics':metric}

def benchmark(store,exe,rvas):
    # Destinado a uma base temporária vazia indicada pelo chamador.
    config={'instructions':80,'blocks':15};reports=[]
    reports.append(analyze(store,exe,rvas,config,task_id='demo-cold'))
    reports.append(analyze(store,exe,rvas,config,task_id='demo-warm'))
    reports.append(analyze(store,exe,rvas[:1],{'instructions':81,'blocks':15},task_id='demo-changed'))
    original_keys=[store.key(reports[0]['binary'],'graph',r,store.db.execute("SELECT analyzer FROM artifacts WHERE kind='graph' AND subject=? AND params=?",(str(r),canonical(config))).fetchone()[0],config) for r in sorted(set(rvas))]
    assert all(store.get(k) for k in original_keys),'Parâmetro de uma análise afetou resultados independentes'
    reports[-1]['original_artifacts_preserved']=len(original_keys)
    # Novo trabalho interrompido com limite explícito, sem simular sucesso.
    cfg={'instructions':82,'blocks':15}
    reports.append(analyze(store,exe,rvas,cfg,task_id='demo-resume',max_functions=1))
    reports.append(analyze(store,exe,rvas,cfg,task_id='demo-resume'))
    from er01 import SnapshotReads
    data=bytes(range(32));requests=[(0x10000,4),(0x10004,4),(0x10000,4)]
    source=lambda a,n:data[a-0x10000:a-0x10000+n]
    naive=[source(a,n) for a,n in requests]
    planned=SnapshotReads(source,('fixture',1),lambda c:True,[(0x10000,0x10020)])
    assert planned.batch(requests)==naive
    reports.append({'scenario':'simulated_reads','naive_calls':len(requests),'planned_calls':planned.calls,
                    'naive_bytes':sum(n for a,n in requests),'planned_bytes':planned.bytes,'equal':True})
    planned.close()
    return reports
