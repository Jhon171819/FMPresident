"""Localiza tabelas virtuais de classes de gestão por RTTI e desmonta seus slots."""
from pathlib import Path
import argparse
import json
import struct
import sys
from analisar_executavel import PE,dump

WANTED=['.?AVCLUB@db@@','.?AVCLUB_FINANCE@db@@','.?AVFACILITY_UPGRADE@db@@',
 '.?AVFINANCES_SPONSORS_PANEL@@','.?AVFINANCES_DEBT_LOAN_PANEL@@',
 '.?AVSPONSORSHIP_DEAL_NEWS@@','.?AVCOMMERCIAL_NEWS_ITEM@db@@',
 '.?AVCLUB_AFFILIATE_CLUB_PROPOSAL_PANEL@@','.?AVCLUB_AFFILIATED_CLUBS_PANEL@@',
 '.?AVCLUB_BUDGET_ADJUSTMENT_LINK_ACTION@@','.?AVCLUB_FINANCE_LINK_ACTION@@',
 '.?AVSTADIUM_SPONSOR_LABEL@@','.?AVSTARTING_LOAN@db@@',
 '.?AVPROCESS_CLUB_LOANS_AND_DEBTS@@','.?AVPOST_PROCESS_CLUB_LOANS@@']


def main(exe,out,capstone,wanted=None,stem='classes-gestao-funcoes'):
    sys.path.insert(0,capstone)
    import capstone as cs
    md=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64)
    pe=PE(exe);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    # As tabelas e locators confirmados ficam na seção que contém a vtable do clube.
    section=pe.section(0x4FDCDF8)
    start=section['raw_offset'];end=start+section['raw_size'];region=pe.data[start:end]
    result=[];assembly=[]
    for name in (wanted or WANTED):
        nameoff=pe.data.find(name.encode()+b'\0')
        if nameoff<0:continue
        td=pe.rva_at(nameoff)-16;pos=region.find(struct.pack('<I',td));locators=[]
        while pos>=0:
            coloff=start+pos-12
            if coloff>=start:
                sig,objoff,ctor,t,rtti,self_rva=pe.unpack('IIIIII',coloff)
                if sig==1 and t==td and pe.rva_at(coloff)==self_rva:locators.append((self_rva,objoff))
            pos=region.find(struct.pack('<I',td),pos+1)
        entry=dict(class_name=name,type_rva=td,vtables=[])
        for locator,objoff in locators:
            needle=struct.pack('<Q',pe.image_base+locator);pos=region.find(needle)
            while pos>=0:
                vtable=pe.rva_at(start+pos)+8;valid=pe.rtti(vtable)
                if valid and valid['class_name']==name:
                    funcs=[]
                    for i in range(96):
                        frva=struct.unpack('<Q',pe.read(vtable+8*i,8))[0]-pe.image_base
                        section_fn=pe.section(frva)
                        if not section_fn or not section_fn['flags']&0x20000000:break
                        interval=pe.function(frva)
                        # Sem unwind, limitar a primeira RET: getters folha não têm .pdata.
                        count=min(512,(interval[1]-frva) if interval else 128)
                        raw=pe.read(frva,max(1,count))
                        instructions=[]
                        for ins in md.disasm(raw,pe.image_base+frva):
                            instructions.append(dict(rva=ins.address-pe.image_base,bytes=ins.bytes.hex(),mnemonic=ins.mnemonic,operands=ins.op_str))
                            if ins.mnemonic in ('ret','jmp'):break
                        funcs.append(dict(slot=i,rva=frva,function_range=interval,instructions=instructions))
                        assembly.append(f'\n; {name} / objeto +0x{objoff:x} / slot {i} / RVA 0x{frva:x}')
                        assembly.extend(f"{pe.image_base+ins['rva']:016x}  {ins['bytes']:30} {ins['mnemonic']:9} {ins['operands']}" for ins in instructions)
                    entry['vtables'].append(dict(rva=vtable,locator_rva=locator,object_offset=objoff,functions=funcs,capped_at_96=len(funcs)==96))
                pos=region.find(needle,pos+1)
        result.append(entry)
    dump(out/(stem+'.json'),result)
    (out/(stem+'.asm')).write_text('\n'.join(assembly),encoding='utf-8')
    print(json.dumps([dict(classe=c['class_name'],vtables=[hex(v['rva']) for v in c['vtables']],slots=sum(len(v['functions']) for v in c['vtables'])) for c in result],ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe');p.add_argument('--out',required=True);p.add_argument('--capstone',required=True);p.add_argument('--classes');p.add_argument('--stem',default='classes-gestao-funcoes')
    a=p.parse_args();main(a.exe,a.out,a.capstone,json.loads(Path(a.classes).read_text(encoding='utf-8')) if a.classes else None,a.stem)
