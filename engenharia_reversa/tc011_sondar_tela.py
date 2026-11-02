"""Busca diagnóstica limitada por instâncias de painéis táticos, sem escrita no FM."""
import struct
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import fm23 as n
import compatibilidade as compat

class Reader:
    read=n.Memory.read; _sample=n.Memory._sample; number=n.Memory.number
    pointer=n.Memory.pointer; alive=n.Memory.alive; close=n.Memory.close; regions=n.Memory.regions
    def __init__(self,pid):
        self.guard=None;self.handle=n.k.OpenProcess(0x410,False,pid)
        if not self.handle:raise OSError('Acesso de leitura recusado')

CLASSES={'tactics_overview':0x4ccd2f8,'team_tactics_overview':0x4cd2058,
         'squad_tactics':0x4ceef18,'selector':0x4ceb3c8,'pitch':0x4cc83b8,
         'slot':0x4ccb588,'player_policy':0x4ccb258,'squad_selection':0x4cee808,
         'selection_edit':0x48b9ab8,'client_tactic':0x4a57ad8}

def scan(max_bytes=2*1024**3,seconds=30):
    info=n.process_info();reader=Reader(info['pid']);start=time.monotonic()
    try:
        guard=compat.BuildGuard(info,n.ProcessProbe(reader,info['base']));reader.guard=guard
        signatures={name:struct.pack('<Q',info['base']+rva) for name,rva in CLASSES.items()}
        found={name:[] for name in CLASSES};total=0;failures=0;limited=False;deadline=time.monotonic()+seconds
        for base,size in reader.regions():
            for off in range(0,size,8*1024*1024):
                if total>=max_bytes or time.monotonic()>=deadline:limited=True;break
                length=min(8*1024*1024,size-off,max_bytes-total);total+=length
                try:data=reader.read(base+off,length)
                except OSError:failures+=1;continue
                for name,needle in signatures.items():
                    pos=data.find(needle)
                    while pos>=0 and len(found[name])<200:
                        addr=base+off+pos
                        if addr%8==0:found[name].append(addr)
                        pos=data.find(needle,pos+1)
            if limited:break
        guard.require_fast()
        # Endereços são usados apenas no processo corrente; nunca são gravados.
        print('build',info['version'],'bytes',total,'tempo',round(time.monotonic()-start,3),'limitado',limited,'falhas',failures)
        print('instancias_candidatas',{name:len(values) for name,values in found.items()})
        for name in ('tactics_overview','team_tactics_overview','squad_tactics','selector','pitch','squad_selection'):
            references={}
            for address in found[name][:16]:
                try:raw=reader.read(address,2048)
                except (OSError,ValueError):continue
                words=struct.unpack('<256Q',raw)
                for target,items in found.items():
                    count=sum(1 for word in words if word in items)
                    if count:references[target]=references.get(target,0)+count
            print('referencias_diretas',name,references)
        # Resolve apenas RTTI já mapeado no arquivo; ponteiros continuam efêmeros.
        from analisar_executavel import PE
        pe=PE(info['path'])
        if len(found['team_tactics_overview'])==1:
            found['tactic_from_panel']=[reader.pointer(found['team_tactics_overview'][0]+0x1b8)]
        for name in ('team_tactics_overview','squad_tactics','slot','player_policy','tactic_from_panel'):
            observed={}
            for address in found[name][:4]:
                try:raw=reader.read(address,512)
                except (OSError,ValueError):continue
                for offset in range(8,512,8):
                    pointer=struct.unpack_from('<Q',raw,offset)[0]
                    if pointer<0x10000 or pointer%8:continue
                    try:
                        rva=reader.pointer(pointer)-info['base']
                        if not 0<=rva<info['size']:continue
                        rtti=pe.rtti(rva)
                        if rtti:
                            key=hex(offset)+':'+rtti['class_name'];observed[key]=observed.get(key,0)+1
                    except (OSError,ValueError,struct.error):continue
            print('campos_com_rtti',name,observed)
        if len(found['team_tactics_overview'])==len(found['squad_tactics'])==len(found['player_policy'])==1:
            a=reader.pointer(found['team_tactics_overview'][0]+0x1b8)
            b=reader.pointer(found['player_policy'][0]+0x58)
            table1=reader.pointer(found['squad_tactics'][0]+0x1b8)
            table2=reader.pointer(found['player_policy'][0]+0x38)
            slot_links=sum(reader.pointer(p+0x168)==a for p in found['slot'][:16])
            print('correlacao_paineis',{'taticas_mesmo_objeto':a==b,'tabela_mesmo_objeto':table1==table2,'botoes_mesma_tatica':slot_links,'botoes_observados':len(found['slot'])})
    finally:reader.close()
if __name__=='__main__':scan()
