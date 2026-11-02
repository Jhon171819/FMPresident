"""Inspeção estática somente leitura do FM23; não modifica nem executa o binário.

Uso: python analisar_executavel.py caminho/fm.exe --out pasta --capstone pasta
Capstone é opcional e usado apenas para desmontar as funções selecionadas.
"""
import argparse
import bisect
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys


class PE:
    def __init__(self,path,mapped=False):
        self.path=Path(path);self._stream=None
        if mapped:
            import mmap
            self._stream=self.path.open('rb')
            try:self.data=mmap.mmap(self._stream.fileno(),0,access=mmap.ACCESS_READ)
            except BaseException:self._stream.close();raise
        else:self.data=self.path.read_bytes()
        try:self._parse()
        except BaseException:self.close();raise

    def _parse(self):
        if self.data[:2]!=b'MZ':raise ValueError('Não é um executável PE.')
        at=self.unpack('I',0x3c)[0]
        if self.data[at:at+4]!=b'PE\0\0':raise ValueError('Assinatura PE inválida.')
        self.machine,self.count,self.timestamp,_,_,optional,self.characteristics=self.unpack('HHIIIHH',at+4)
        opt=at+24
        if self.unpack('H',opt)[0]!=0x20b:raise ValueError('Esperado PE32+ de 64 bits.')
        self.image_base=self.unpack('Q',opt+24)[0]
        self.image_size=self.unpack('I',opt+56)[0]
        self.entry=self.unpack('I',opt+16)[0]
        self.dll_characteristics=self.unpack('H',opt+70)[0]
        self.directories=[self.unpack('II',opt+112+8*i) for i in range(min(self.unpack('I',opt+108)[0],16))]
        self.sections=[]
        for i in range(self.count):
            s=opt+optional+40*i
            name=self.data[s:s+8].split(b'\0')[0].decode('ascii','replace')
            virtual_size,rva,raw_size,raw_offset=self.unpack('IIII',s+8)
            flags=self.unpack('I',s+36)[0]
            self.sections.append(dict(name=name,rva=rva,virtual_size=virtual_size,raw_offset=raw_offset,raw_size=raw_size,flags=flags))
        self.functions=[]
        rva,size=self.directories[3]
        if rva:
            off=self.offset(rva)
            for i in range(size//12):
                begin,end,unwind=self.unpack('III',off+12*i)
                if begin<end and self.section(begin):self.functions.append((begin,end,unwind))
        self.functions.sort();self.starts=[x[0] for x in self.functions]

    def unpack(self,fmt,offset):return struct.unpack_from('<'+fmt,self.data,offset)
    def section(self,rva):return next((s for s in self.sections if s['rva']<=rva<s['rva']+max(s['virtual_size'],s['raw_size'])),None)
    def offset(self,rva):
        s=self.section(rva)
        if s is None or rva-s['rva']>=s['raw_size']:raise ValueError(f'RVA sem bytes no arquivo: {rva:x}')
        return s['raw_offset']+rva-s['rva']
    def rva_at(self,offset):
        s=next((s for s in self.sections if s['raw_offset']<=offset<s['raw_offset']+s['raw_size']),None)
        return s['rva']+offset-s['raw_offset'] if s else None
    def read(self,rva,n):return self.data[self.offset(rva):self.offset(rva)+n]
    def string(self,rva):
        at=self.offset(rva);end=self.data.find(b'\0',at,min(at+4096,len(self.data)))
        if end<0:raise ValueError('String PE sem terminador dentro do limite')
        return self.data[at:end].decode('ascii','replace')
    def close(self):
        if self._stream is not None:self.data.close();self._stream.close();self._stream=None
    def function(self,rva):
        at=bisect.bisect_right(self.starts,rva)-1
        if at>=0 and self.functions[at][0]<=rva<self.functions[at][1]:return self.functions[at]
        return None

    def imports(self):
        modules=[];rva,size=self.directories[1]
        if not rva:return modules
        at=self.offset(rva)
        for i in range(min(size//20+1,1024)):
            lookup,_,_,name,first=self.unpack('IIIII',at+i*20)
            if not name:break
            funcs=[];p=self.offset(lookup or first)
            for j in range(10000):
                value=self.unpack('Q',p+8*j)[0]
                if not value:break
                funcs.append({'name':f'ordinal:{value&0xffff}' if value>>63 else self.string(value+2),'iat_rva':first+8*j})
            modules.append(dict(module=self.string(name),functions=funcs))
        return modules

    def rtti(self,vtable):
        try:
            locator=self.unpack('Q',self.offset(vtable-8))[0]-self.image_base
            sig,offset,construction,td,hierarchy,self_rva=struct.unpack('<IIIIII',self.read(locator,24))
            if sig!=1 or self_rva!=locator:return None
            return dict(locator_rva=locator,type_rva=td,class_name=self.string(td+16),object_offset=offset,hierarchy_rva=hierarchy)
        except (ValueError,struct.error):return None


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def analyze(path,out,capstone=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);pe=PE(path)
    report=dict(file=str(pe.path.resolve()),size=len(pe.data),sha256=hashlib.sha256(pe.data).hexdigest(),
        analyzed_at=datetime.now(timezone.utc).isoformat(),machine=hex(pe.machine),image_base=hex(pe.image_base),
        image_size=pe.image_size,entry_rva=hex(pe.entry),pe_timestamp_raw=pe.timestamp,
        unwind_function_ranges=len(pe.functions),sections=pe.sections,imports=pe.imports())
    dump(out/'executavel.json',report)
    print('Cabeçalhos, hash, seções e imports extraídos.',flush=True)
    focus=re.compile(r'club|financ|sponsor|chairman|board|commercial|affiliat|stadium|loan|debt|ticket|facility',re.I)
    classes=[]
    for m in re.finditer(rb'\.\?A[UV][\x21-\x7e]{2,240}?@@\x00',pe.data):
        name=m.group()[:-1].decode('ascii')
        if focus.search(name):classes.append(dict(name=name,rva=pe.rva_at(m.start()),offset=m.start()))
    dump(out/'classes-relevantes.json',classes)
    targets={'club_vtable':0x4FDCDF8,'finance_vtable':0x4A56998,'game_date':0x54623F0}
    # RTTI de outras classes serve para achar construtores e tabelas virtuais.
    for c in classes:
        if any(s in c['name'].lower() for s in ('sponsor','affiliat','loan','chairman','club_financ')):
            targets[c['name'][:150]]=c['rva']-16 if c['rva'] is not None else 0
    tables={}
    for name,rva in [('club',0x4FDCDF8),('finance',0x4A56998)]:
        funcs=[]
        for i in range(64):
            addr=struct.unpack('<Q',pe.read(rva+8*i,8))[0];frva=addr-pe.image_base;s=pe.section(frva)
            if not s or not s['flags']&0x20000000:break
            interval=pe.function(frva)
            funcs.append(dict(slot=i,rva=frva,function_range=interval))
        tables[name]=dict(vtable_rva=rva,rtti=pe.rtti(rva),functions=funcs)
    dump(out/'tabelas-virtuais.json',tables)
    print(f'{len(classes)} nomes de classes relevantes; tabelas virtuais extraídas.',flush=True)
    # Apenas instruções RIP-relative de 7 bytes com MOV/LEA. Não é uma lista
    # exaustiva de referências; cada candidato é desmontado quando Capstone existe.
    xrefs=[];target_lookup={rva:name for name,rva in targets.items()}
    selected=set()
    pattern=re.compile(rb'[\x48\x4c][\x8b\x8d\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',re.DOTALL)
    datepattern=re.compile(rb'\xff\x10\x0f\xb7\x05....\x89\xc1\x81\xe1',re.DOTALL)
    signatures=[]
    for s in pe.sections:
        if not s['flags']&0x20000000:continue
        raw=pe.data[s['raw_offset']:s['raw_offset']+s['raw_size']]
        for m in pattern.finditer(raw):
            ins=s['rva']+m.start();target=ins+7+struct.unpack_from('<i',m.group(),3)[0]
            if target in target_lookup:
                fn=pe.function(ins)
                xrefs.append(dict(source_rva=ins,target_rva=target,target=target_lookup[target],bytes=m.group().hex(),function_range=fn))
                if fn and target_lookup[target] in ('club_vtable','finance_vtable'):selected.add(fn)
        for m in datepattern.finditer(raw):
            ins=s['rva']+m.start();target=ins+9+struct.unpack_from('<i',m.group(),5)[0];fn=pe.function(ins)
            signatures.append(dict(instruction_rva=ins,date_rva=target,function_range=fn,pattern='FF 10 0F B7 05 ?? ?? ?? ?? 89 C1 81 E1'))
            if fn:selected.add(fn)
    dump(out/'referencias-candidatas.json',xrefs);dump(out/'assinatura-data.json',signatures)
    for table in tables.values():
        for f in table['functions']:
            if f['function_range']:selected.add(tuple(f['function_range']))
    print(f'{len(xrefs)} referências candidatas e {len(signatures)} assinatura(s) de data.',flush=True)
    # Catálogo de strings de domínio, com posição exata, sem copiar textos de jogo inteiros.
    strings=[]
    for m in re.finditer(rb'[\x20-\x7e]{6,300}\x00',pe.data):
        value=m.group()[:-1].decode('ascii')
        if focus.search(value):
            rva=pe.rva_at(m.start())
            if rva is not None:strings.append(dict(rva=rva,text=value))
    dump(out/'strings-gestao.json',strings)
    if capstone:sys.path.insert(0,capstone)
    try:
        import capstone as cs
    except ImportError:
        print('Capstone ausente: mapa produzido sem desmontagem.',flush=True);return
    md=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64)
    listing=[];function_report=[]
    for begin,end,unwind in sorted(selected):
        if end-begin>100000:continue
        listing.append(f'\n; RVA 0x{begin:x}..0x{end:x} / unwind 0x{unwind:x}')
        body=pe.read(begin,end-begin)
        instructions=list(md.disasm(body,pe.image_base+begin))
        for ins in instructions:listing.append(f'{ins.address:016x}  {ins.bytes.hex():30} {ins.mnemonic:9} {ins.op_str}')
        function_report.append(dict(begin=begin,end=end,instructions=len(instructions),decoded_bytes=sum(i.size for i in instructions),total_bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
    (out/'funcoes-selecionadas.asm').write_text('\n'.join(listing),encoding='utf-8')
    dump(out/'funcoes-selecionadas.json',function_report)
    print(f'{len(function_report)} intervalos de funções desmontados; {len(strings)} strings catalogadas. Capstone {cs.__version__}.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable');parser.add_argument('--out',required=True);parser.add_argument('--capstone')
    args=parser.parse_args();analyze(args.executable,args.out,args.capstone)
