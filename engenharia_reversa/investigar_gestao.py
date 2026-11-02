"""Rastreia referências e blocos de código de negociação, scouting e diretoria.

Não executa o binário nem escreve no jogo. Os grafos têm limites explícitos.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from analisar_executavel import PE,dump

STRING_KEYS=[
 'make_transfer_decision_for_player',
 'db::TC_SHORTLIST::make_transfer_decision - failed to setup transfer offer, set next statement to just before switch and step though, find out why?',
 'db::TC_SHORTLIST::make_transfer_decision - no transfer rules',
 'make_transfer_offer_non_player','send_responsibility_change_event','responsibility_id',
 'SCOUT_MANAGER_patch_dupe_and_negative_focus_ids','SCOUT_MANAGER_patch_fix_person_search_counts',
 'SCOUTED_PERSON','RECRUITMENT_FOCUS','KNOWLEDGE_ARRAY',
 'allow_takeover_of_managed_teams','use_cut_down_club_vision','Providing Financial Resources',
 'Assigning Scouts','Negotiating Player Signings','Finalising Player Signings',
 'Hiring and Firing the Manager','Building the Club']


def graph(pe,md,cs,start,max_instructions=800,max_blocks=100):
    interval=pe.function(start)
    low,high=(interval[0],interval[1]) if interval else (start,start+4096)
    pending=[start];visited=set();instructions={};edges=[];calls=[]
    while pending and len(instructions)<max_instructions and len(visited)<max_blocks:
        block=pending.pop()
        if block in visited:continue
        visited.add(block)
        try:body=pe.read(block,min(high-block,4096))
        except ValueError:continue
        if not body:continue
        for ins in md.disasm(body,pe.image_base+block):
            rva=ins.address-pe.image_base
            if rva in instructions:break
            refs=[]
            for op in ins.operands:
                if op.type==cs.x86.X86_OP_MEM:
                    refs.append(dict(base=ins.reg_name(op.mem.base),index=ins.reg_name(op.mem.index),disp=op.mem.disp,size=op.size))
            instructions[rva]=dict(rva=rva,bytes=ins.bytes.hex(),mnemonic=ins.mnemonic,operands=ins.op_str,memory=refs)
            if len(instructions)>=max_instructions:break
            if ins.group(cs.CS_GRP_CALL):
                target=ins.operands[0].imm-pe.image_base if ins.operands and ins.operands[0].type==cs.x86.X86_OP_IMM else None
                calls.append(dict(at=rva,target=target,operand=ins.op_str))
            if ins.group(cs.CS_GRP_JUMP):
                target=ins.operands[0].imm-pe.image_base if ins.operands and ins.operands[0].type==cs.x86.X86_OP_IMM else None
                edges.append(dict(source=rva,target=target,condition=ins.mnemonic,within=target is not None and low<=target<high))
                if target is not None and low<=target<high:pending.append(target)
                if ins.mnemonic=='jmp':break
            if ins.group(cs.CS_GRP_RET) or ins.mnemonic in ('int3','ud2'):break
    return dict(start=start,range=interval,limit_instructions=max_instructions,
        bounded=len(instructions)>=max_instructions or len(visited)>=max_blocks,
        instructions=sorted(instructions.values(),key=lambda i:i['rva']),edges=edges,calls=calls)


def analyze(exe,out,capstone):
    sys.path.insert(0,capstone)
    import capstone as cs
    md=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64);md.detail=True
    pe=PE(exe);out=Path(out);out.mkdir(exist_ok=True)
    classes=json.loads((out/'motores-funcoes.json').read_text(encoding='utf-8'))
    strings=json.loads((out/'catalogo-strings.json').read_text(encoding='utf-8'))
    targets={}
    for s in strings:
        if any(key.casefold() in s['text'].casefold() for key in STRING_KEYS) and not s['text'].startswith('.?'):
            targets[s['rva']]=s['text']
    for c in classes:
        for t in c['vtables']:
            if t['object_offset']==0:targets[t['rva']]='vtable:'+c['class_name']
    dump(out/'alvos-referencias.json',[dict(rva=r,text=t) for r,t in targets.items()])
    pattern=re.compile(rb'[\x48\x4c][\x8b\x8d\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....',re.DOTALL)
    xrefs=[]
    for sec in pe.sections:
        if not sec['flags']&0x20000000:continue
        raw=pe.data[sec['raw_offset']:sec['raw_offset']+sec['raw_size']]
        for m in pattern.finditer(raw):
            rva=sec['rva']+m.start();target=rva+7+struct.unpack_from('<i',m.group(),3)[0]
            if target not in targets:continue
            interval=pe.function(rva)
            xrefs.append(dict(rva=rva,target=target,name=targets[target],range=interval,candidate=True))
    dump(out/'referencias-motores.json',xrefs)
    print('Referências candidatas:',len(xrefs),flush=True)
    chosen={}
    def choose(rva,label):
        chosen.setdefault(rva,[]).append(label)
    rules=['IS_TRANSFER_OFFER_NEGOTIABLE','PLAYER_AGENT_DEMANDS_CAN_CONTEST_WAGE_RULE','CLUB_HAS_OR_CAN_ACCEPT_TRANSFER_OFFER_FOR_PLAYER']
    for c in classes:
        for t in c['vtables']:
            if t['object_offset']!=0:continue
            for f in t['functions']:
                if any(r in c['class_name'] for r in rules) and f['slot']==1:choose(f['rva'],c['class_name']+':test')
                if c['class_name'] in ('.?AVSCOUT_MANAGER@@','.?AVBOARD_TAKEOVER_MANAGER@@'):
                    choose(f['rva'],c['class_name']+f":slot{f['slot']}")
    for x in xrefs:
        if x['range']:choose(x['range'][0],'xref:'+x['name'])
    graphs=[];asm=[]
    for rva,labels in sorted(chosen.items()):
        g=graph(pe,md,cs,rva)
        g['labels']=labels
        # Uma única cadeia de trampolins diretos, sem emulação nem execução.
        g['tail_chain']=[];seen={rva};current=g
        for _ in range(3):
            ins=current['instructions']
            if len(ins)!=1 or ins[0]['mnemonic']!='jmp' or not current['edges']:break
            target=current['edges'][0]['target']
            if target is None or target in seen or not pe.section(target):break
            seen.add(target);current=graph(pe,md,cs,target,160,30)
            g['tail_chain'].append(current)
        graphs.append(g)
        asm.append(f'\n; RVA 0x{rva:x} '+ ' / '.join(labels))
        for part in [g]+g['tail_chain']:
            if part is not g:asm.append(f"; salto para RVA 0x{part['start']:x}")
            asm.extend(f"{pe.image_base+i['rva']:016x} {i['bytes']:30} {i['mnemonic']:9} {i['operands']}" for i in part['instructions'])
    dump(out/'fluxos.json',graphs)
    (out/'fluxos.asm').write_text('\n'.join(asm),encoding='utf-8')
    # Confirma candidatos que coincidem com instrução alcançada a partir de entrada.
    reached={i['rva'] for g in graphs for part in [g]+g['tail_chain'] for i in part['instructions']}
    for x in xrefs:x['boundary_reached']=x['rva'] in reached
    dump(out/'referencias-motores.json',xrefs)
    print(json.dumps(dict(functions=len(graphs),references=len(xrefs),reached_references=sum(x['boundary_reached'] for x in xrefs),sha256=hashlib.sha256(pe.data).hexdigest()),indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe');p.add_argument('--out',required=True);p.add_argument('--capstone',required=True)
    a=p.parse_args();analyze(a.exe,a.out,a.capstone)
