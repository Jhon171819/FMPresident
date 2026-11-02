"""Verificações reproduzíveis do motor, sem modificar uma carreira real."""
from copy import deepcopy
from datetime import date,timedelta
import json
from pathlib import Path
import random
import negociacao as n
from fm23 import ROOT


def check():
    rows=json.loads((ROOT/'assets/patrocinadores.json').read_text(encoding='utf-8'))
    assert len(rows)==50 and len({r['id'] for r in rows})==50
    row=dict(index=2,kind=1,total=7631000,start='2031-12-24',end='2033-12-23',raw='native-signature')
    ctx=dict(uid=104749,date='2031-11-25')
    a=n.begin(rows[0],row,ctx,ctx['date']);b=n.begin(rows[0],row,ctx,ctx['date'])
    assert a['profile']==b['profile'] and a['offer']==b['offer']
    c=n.signing(a,ctx['date'],row,[])
    assert c['total']==a['offer']['annual']*a['offer']['years']
    assert c['end']==str(n.end_date(n.iso(c['start']),c['years']))
    assert n.end_date(date(2031,12,24),2)==date(2033,12,23)
    assert n.end_date(date(2032,2,29),1)==date(2033,2,28)
    # Pedido razoável fecha; pedido impossível e fixo encerra sem falsa aceitação.
    terms=deepcopy(a['offer']);terms['annual']=1000;terms['exclusive']=False
    agreed=n.counter(a,terms,[],ctx['date']);assert agreed['status']=='agreed'
    impossible=deepcopy(a['offer']);impossible['annual']=min(500_000_000,int(a['profile']['max_annual']*4))
    impossible['years']=1
    rejected=n.counter(a,impossible,['annual'],ctx['date']);assert rejected['status']=='rejected'
    assert n.tick(a,'2031-12-10')['status']=='expired'
    try:n.begin(rows[0],row,ctx,ctx['date'],[rejected])
    except ValueError:pass
    else:raise AssertionError('Cooldown não aplicado')
    try:n.signing(a,ctx['date'],dict(row,raw='changed'),[])
    except ValueError:pass
    else:raise AssertionError('Contrato alterado aceito')
    existing=dict(c,company=dict(rows[0],name='Empresa concorrente'),sector=n.sector(rows[0]),exclusive=True,transaction='old')
    try:n.signing(a,ctx['date'],row,[existing])
    except ValueError:pass
    else:raise AssertionError('Exclusividade ignorada')
    half=dict(c,total=100000,penalty=20,start='2031-01-01',end='2031-12-31')
    assert n.remaining_penalty(half,'2030-12-31')==20000 and n.remaining_penalty(half,'2032-01-01')==0
    assert n.tick(a,'2031-11-20')['status']=='stale'
    priority=dict(c,end='2031-11-30',renewal=True,status='active')
    later=dict(a['offer'],start='2031-12-01')
    try:n.renewal_priority(dict(rows[0],name='Outra empresa'),later,1,[priority],[],'2031-11-25')
    except ValueError:pass
    else:raise AssertionError('Preferência de renovação ignorada')
    n.renewal_priority(dict(rows[0],name='Outra empresa'),dict(later,start='2031-12-08'),1,[priority],[],'2031-11-25')
    conflicting=dict(row,index=8,start='2031-12-01',end='2034-12-01')
    assert len(n.replacements(row,a['offer'],[row,conflicting]))==2
    assert len(n.replacements(dict(row,kind=4),a['offer'],[dict(row,kind=4),dict(conflicting,kind=4)]))==1
    # Explorar empresas/termos: toda oferta emitida pela empresa deve poder ser assinada.
    cases=0
    rng=random.Random(42)
    for company in rows:
        s=n.begin(company,row,ctx,'2031-12-01')
        for _ in range(6):
            if s['status'] not in n.OPEN:break
            t=deepcopy(s['offer']);t.update(years=rng.randint(1,5),penalty=rng.choice([0,10,20,50,100]),exclusive=rng.choice([True,False]))
            t['annual']=n.round_money(n.budget(s,t)*rng.choice([.7,1.1,1.4,1.9]))
            locks=rng.choice([[],['annual'],['penalty'],['penalty','exclusive']])
            s=n.counter(s,t,locks,ctx['date']);cases+=1
            if s['status'] in n.OPEN:
                signed=n.signing(s,ctx['date'],row,[])
                assert signed['total']==signed['annual']*signed['years']
                if 'annual' in locks:assert s['offer']['annual']==t['annual']
                if 'penalty' in locks:assert s['offer']['penalty']==t['penalty']
    print(f'OK: 50 marcas, negociação, {cases} rodadas, locks, prazo, cooldown, exclusividade, vigência, multa e conflitos nativos.')


if __name__=='__main__':check()
