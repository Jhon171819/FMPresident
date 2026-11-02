"""Grafo estático limitado dos componentes táticos; não executa código do FM."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT.parent),str(ROOT),str(ROOT/'ferramentas')]
from evidencias_taticas import evidence
from analisar_executavel import PE,dump
from investigar_gestao import graph
from mapear_classes import main
import capstone as cs

def analyze(exe):
    out=ROOT/'tc011b';out.mkdir(exist_ok=True)
    names=['TACTIC_PLAYER_LIST_TABLE','TACTIC_PLAYER_DATA_RETRIEVAL_POLICY','TACTIC_SLOT_BUTTON','CLIENT_TACTIC']
    main(exe,out,str(ROOT/'ferramentas'),['.?AV'+n+'@@' for n in names],'componentes')
    pe=PE(exe);md=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64);md.detail=True
    classes=json.loads((out/'componentes.json').read_text(encoding='utf8'))
    graphs=[];seen=set()
    for c in classes:
        for vt in c['vtables']:
            if vt['object_offset']!=0:continue
            for f in vt['functions']:
                if f['rva'] in seen:continue
                seen.add(f['rva']);g=graph(pe,md,cs,f['rva'],400,50)
                g['class']=c['class_name'];g['slot']=f['slot'];graphs.append(g)
    dump(out/'grafos.json',graphs)
    print('grafos',len(graphs),'limitados',sum(g['bounded'] for g in graphs))
    # Retém chamadas diretas e alvos de trampolins; chamadas virtuais não são resolvidas por hipótese.
    edges=[{'class':g['class'],'slot':g['slot'],'source_rva':g['start'],'calls':g['calls'],'jumps':g['edges']} for g in graphs]
    dump(out/'chamadas.json',edges)
    dump(out/'hipoteses.json',[evidence('META-01','Política usa metadados intermediários; ligação ao atleta pendente',1),
                             evidence('UID-01','Identidade persistente não localizada')])
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Análise offline incremental; artefatos legados permanecem preservados')
    parser.add_argument('--exe',required=True);parser.add_argument('--legacy-rebuild',action='store_true')
    parser.add_argument('--rva',type=lambda x:int(x,0),action='append')
    parser.add_argument('--refresh-all',action='store_true',help='Solicita explicitamente análise de todos os métodos históricos')
    args=parser.parse_args()
    if args.legacy_rebuild:analyze(args.exe)
    else:
        from er01 import Store
        from er01_static import analyze as incremental
        source=ROOT/'tc011b/componentes.json'
        classes=json.loads(source.read_text(encoding='utf8'))
        rvas=sorted({f['rva'] for c in classes for vt in c['vtables'] if vt['object_offset']==0 for f in vt['functions']})
        if args.rva or args.refresh_all:
            with Store(ROOT.parent/'dados/er01.sqlite3') as store:
                print(json.dumps(incremental(store,args.exe,args.rva or rvas),indent=2))
        else:
            graphs=json.loads((ROOT/'tc011b/grafos.json').read_text(encoding='utf8'))
            print(json.dumps({'mode':'plan','methods':len(rvas),'legacy_partial_rvas':[hex(g['start']) for g in graphs if g.get('bounded')],
                              'reason':'Legados sem identidade do analisador são consultáveis; análise nova exige --rva ou --refresh-all'},indent=2))
