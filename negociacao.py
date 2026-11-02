"""Motor de negociação de patrocínios. Regras de jogo do FMPresidente, sem rede."""
from copy import deepcopy
from datetime import date,timedelta
from pathlib import Path
import calendar
import hashlib
import json
import math
import uuid

COMMERCIAL={1,3,4,7,8,9,11,12,13,14,15,19}
SINGLE_SPACE={1,3,8,9,11,12,13,19}
STATES={'offered':'Proposta recebida','countered':'Contraproposta da empresa','agreed':'Termos acordados',
        'final':'Última proposta','rejected':'Empresa desistiu','withdrawn':'Clube desistiu',
        'expired':'Prazo encerrado','signed':'Assinado no FM','stale':'Contrato do FM mudou','reverted':'Assinatura desfeita'}
OPEN={'offered','countered','agreed','final'}
FAMILIES={'Bebidas':'bebidas','Bebidas energéticas':'bebidas','Alimentos e bebidas':'bebidas',
 'Banco':'finanças','Pagamentos':'finanças','Serviços financeiros':'finanças',
 'Tecnologia e games':'tecnologia','Tecnologia e varejo':'tecnologia','Tecnologia':'tecnologia',
 'Jogos eletrônicos':'games','Automotivo':'automotivo','Comércio eletrônico':'varejo',
 'Material esportivo':'material esportivo'}


def sector(company):return FAMILIES.get(company.get('sector',''),company.get('sector','Outros').casefold())
def iso(value):return date.fromisoformat(value)
def anniversary(start,years):
    return start.replace(year=start.year+years,day=min(start.day,calendar.monthrange(start.year+years,start.month)[1]))
def end_date(start,years):
    end=anniversary(start,years)
    return end if end.day<start.day else end-timedelta(days=1)
def round_money(value):return max(1000,int(round(value/1000))*1000)
def money(value):return '£ '+f'{value:,.0f}'.replace(',','.')


def validate_terms(terms,today=None):
    if not isinstance(terms,dict):raise ValueError('Condições inválidas.')
    annual=terms.get('annual');years=terms.get('years');penalty=terms.get('penalty')
    if type(annual) is not int or not 1000<=annual<=500_000_000:raise ValueError('Informe entre £1.000 e £500 milhões por ano.')
    if type(years) is not int or not 1<=years<=5:raise ValueError('A duração deve ser de um a cinco anos.')
    if annual*years>1_000_000_000:raise ValueError('O valor total deve ser de até £1 bilhão.')
    if type(penalty) is not int or not 0<=penalty<=100:raise ValueError('A multa deve ficar entre 0% e 100% do valor restante.')
    if type(terms.get('exclusive')) is not bool or type(terms.get('renewal')) is not bool:
        raise ValueError('Revise exclusividade e preferência de renovação.')
    start=iso(terms['start'])
    if today and start<today:raise ValueError('O início deve ser hoje ou uma data futura da carreira.')
    if today and start>today+timedelta(days=366*5):raise ValueError('O início deve estar nos próximos cinco anos da carreira.')
    if start.year+years>2199:raise ValueError('Vigência fora da faixa do jogo.')
    return deepcopy(terms)


def annual_reference(row):
    duration=(iso(row['end'])-iso(row['start'])).days+1
    return max(250_000,row['total']/max(1,duration/365.25))


def replacements(row,terms,rows):
    start=iso(terms['start']);end=end_date(start,terms['years'])
    return [r for r in rows if r['index']==row['index'] or
        (row['kind'] in SINGLE_SPACE and r['kind']==row['kind'] and r['total']>0 and iso(r['start'])<=end and iso(r['end'])>=start)]


def profile(company,row,context,start):
    # Mesma empresa, espaço e quinzena recebem o mesmo perfil; reabrir a janela
    # não sorteia um comprador novo nem reinicia uma negociação encerrada.
    period=iso(context['date']).toordinal()//14
    seed=int(hashlib.sha256(f"{context['uid']}|{company['id']}|{row['kind']}|{period}".encode()).hexdigest()[:12],16)
    reputation=max(0,min(100,int(company.get('reputation',70))))
    investment=max(0,min(100,int(company.get('investment',70))))
    preferred=1+seed%4
    strength=.72+investment/230+reputation/600
    if company.get('sector')=='Material esportivo' and row['kind']==8:strength*=1.12
    maximum=round_money(annual_reference(row)*strength*(.93+(seed%17)/100))
    return dict(seed=seed,max_annual=maximum,preferred_years=preferred,patience=3+seed%3,
                min_penalty=10+(seed%4)*10,deadline_days=5+seed%4,
                likes_exclusive=seed%5!=0,sector=sector(company),baseline=round_money(annual_reference(row)))


def budget(session,terms):
    p=session['profile']
    length=max(.72,1-.055*abs(terms['years']-p['preferred_years']))
    extras=(1.10 if terms['exclusive'] and p['likes_exclusive'] else 1)
    extras*=1.035 if terms['renewal'] else 1
    extras*=.88+.12*terms['penalty']/100
    return round_money(p['max_annual']*length*extras)


def log(session,who,message,terms=None):
    session['messages'].append(dict(who=who,text=message,terms=deepcopy(terms),round=session['round']))


def begin(company,row,context,start,previous=()):
    today=iso(context['date']);start=iso(start)
    if row['kind'] not in COMMERCIAL:raise ValueError('Selecione uma receita comercial negociável. TV e subvenções não são espaços de patrocínio.')
    if not today<=start<=today+timedelta(days=366*5):raise ValueError('O início deve estar entre hoje e os próximos cinco anos da carreira.')
    for s in previous:
        if s['company']['id']==company['id'] and s['row']['kind']==row['kind']:
            if s['status'] in OPEN:raise ValueError('Essa empresa já tem uma mesa aberta para esse espaço. Selecione-a na lista.')
            if s['status'] in {'rejected','withdrawn','expired'} and iso(s.get('cooldown_until',s['date']))>today:
                raise ValueError('Essa empresa só voltará a negociar em '+iso(s['cooldown_until']).strftime('%d/%m/%Y')+'.')
    p=profile(company,row,context,start)
    s=dict(id=uuid.uuid4().hex,version=1,club=context['uid'],date=str(today),last_date=str(today),
        company=deepcopy(company),row=deepcopy(row),profile=p,status='offered',round=0,
        expires=str(min(start,today+timedelta(days=p['deadline_days']))),messages=[],locked=[],transaction=None)
    terms=dict(annual=1000,years=p['preferred_years'],start=str(start),exclusive=p['likes_exclusive'],
               renewal=True,penalty=max(20,p['min_penalty']))
    terms['annual']=round_money(budget(s,terms)*.80)
    s['offer']=validate_terms(terms,today)
    log(s,'Empresa',f"Gostaríamos de ocupar este espaço por {terms['years']} ano(s). Nossa proposta é de {money(terms['annual'])} por ano. Podemos discutir valores, duração e condições.",terms)
    return s


def tick(session,today):
    s=deepcopy(session);today=iso(str(today))
    if today<iso(s['last_date']):
        if s['status'] in OPEN:s['status']='stale';log(s,'Sistema','A carreira voltou no tempo. Abra uma nova mesa para essa data.')
        return s
    s['last_date']=str(today)
    if s['status'] in OPEN and (today>iso(s['expires']) or today>iso(s['offer']['start'])):
        s['status']='expired';s['cooldown_until']=str(today+timedelta(days=14))
        log(s,'Empresa','O prazo de resposta terminou. Vamos suspender esta negociação por duas semanas.')
    return s


def counter(session,terms,locks,today):
    s=tick(session,today)
    if s['status'] not in OPEN:raise ValueError('Essa mesa não aceita novas propostas.')
    today=iso(str(today));terms=validate_terms(terms,today)
    valid={'annual','years','exclusive','renewal','penalty','start'}
    if not isinstance(locks,(set,list,tuple)) or not set(locks)<=valid:raise ValueError('Termo não negociável inválido.')
    previous=s['offer'];s['round']+=1;s['locked']=list(locks)
    log(s,'Clube',f"Pedimos {money(terms['annual'])}/ano por {terms['years']} ano(s), com as condições abaixo."+(' Termos marcados são finais.' if locks else ''),terms)
    limit=budget(s,terms)
    acceptable=terms['annual']<=limit and (terms['penalty']>=s['profile']['min_penalty'] or not terms['exclusive'])
    if acceptable:
        s['offer']=terms;s['status']='agreed'
        log(s,'Empresa','Aceitamos as condições. O acordo está pronto para assinatura.',terms)
    else:
        final=s['round']>=s['profile']['patience']
        impossible=('annual' in locks and terms['annual']>limit) or ('penalty' in locks and terms['exclusive'] and terms['penalty']<s['profile']['min_penalty'])
        aggressive=terms['annual']>limit*1.65
        if s['status']=='final' or (impossible and (final or aggressive)):
            s['status']='rejected';s['cooldown_until']=str(today+timedelta(days=14))
            log(s,'Empresa','Não conseguimos atender às condições finais. Encerramos as conversas por enquanto.')
        else:
            reply=deepcopy(terms)
            if 'penalty' not in locks:reply['penalty']=max(reply['penalty'],s['profile']['min_penalty'])
            elif reply['exclusive'] and reply['penalty']<s['profile']['min_penalty']:
                if 'exclusive' in locks:
                    s['status']='rejected';s['cooldown_until']=str(today+timedelta(days=14))
                    log(s,'Empresa','Não aceitamos exclusividade com essa multa não negociável. Encerramos as conversas.')
                    return s
                reply['exclusive']=False
            if 'years' not in locks and abs(reply['years']-s['profile']['preferred_years'])>=2:reply['years']=s['profile']['preferred_years']
            if 'exclusive' not in locks and s['profile']['likes_exclusive'] and reply['penalty']>=s['profile']['min_penalty']:reply['exclusive']=True
            if 'renewal' not in locks:reply['renewal']=True
            ceiling=budget(s,reply)
            if 'annual' not in locks:
                concession=min(.98,.82+.035*s['round'])
                reply['annual']=min(terms['annual'],round_money(ceiling*concession))
                # Nunca obrigar a empresa a subir uma proposta só porque o clube pediu menos.
            elif terms['annual']>ceiling:
                s['status']='rejected';s['cooldown_until']=str(today+timedelta(days=14))
                log(s,'Empresa','O valor não negociável supera nosso orçamento para essas condições. Não há acordo possível.')
                return s
            s['offer']=validate_terms(reply,today)
            s['status']='final' if final else 'countered'
            log(s,'Empresa',('Esta é nossa última proposta.' if final else 'Podemos avançar com esta contraproposta.')+f" {money(reply['annual'])}/ano por {reply['years']} ano(s).",reply)
    s['expires']=str(min(iso(s['offer']['start']),today+timedelta(days=max(2,s['profile']['deadline_days']-s['round']//2))))
    return s


def withdraw(session,today):
    s=tick(session,today)
    if s['status'] not in OPEN:raise ValueError('A mesa já está encerrada.')
    s['status']='withdrawn';s['cooldown_until']=str(iso(str(today))+timedelta(days=14))
    log(s,'Clube','Encerramos as conversas. Poderemos retomar contato em duas semanas.')
    return s


def conflicts(company,terms,contracts,kind,exclude_transaction=None):
    start=iso(terms['start']);end=end_date(start,terms['years'])
    for c in contracts:
        if c.get('transaction')==exclude_transaction or c.get('status')=='terminated':continue
        if not c.get('sector'):continue
        if iso(c['end'])<start or iso(c['start'])>end:continue
        if sector(company)==c['sector'] and company['name'].casefold()!=c['company']['name'].casefold() and (terms['exclusive'] or c.get('exclusive')):
            raise ValueError(f"Conflito de exclusividade com {c['company']['name']} até {iso(c['end']).strftime('%d/%m/%Y')}.")


def renewal_priority(company,terms,kind,contracts,sessions,today):
    today=iso(str(today));start=iso(terms['start'])
    for c in contracts:
        if not c.get('renewal') or c.get('status')=='terminated' or c['kind']!=kind or c['company']['name']==company['name']:continue
        end=iso(c['end']);opening=end-timedelta(days=30);closing=end+timedelta(days=7)
        if not opening<=today<=closing or not end<start<=closing:continue
        released=any(s['company']['name']==c['company']['name'] and s['row']['kind']==kind and s['status'] in {'rejected','expired'} and iso(s['date'])>=opening for s in sessions)
        if not released:raise ValueError(f"{c['company']['name']} tem preferência de renovação até {closing.strftime('%d/%m/%Y')}. Negocie primeiro com a empresa ou programe o início depois dessa data.")


def signing(session,today,native_row,contracts):
    s=tick(session,today)
    if s['status'] not in OPEN:raise ValueError('Essa proposta não pode ser assinada.')
    if native_row['raw']!=s['row']['raw'] or native_row['kind']!=s['row']['kind']:
        raise ValueError('A receita do FM mudou desde a abertura da mesa. Abra uma nova negociação.')
    terms=validate_terms(s['offer'],iso(str(today)))
    # A proposta da empresa sempre precisa caber no orçamento, inclusive após locks.
    if terms['annual']>budget(s,terms):raise ValueError('Proposta inconsistente com o orçamento da empresa.')
    conflicts(s['company'],terms,contracts,s['row']['kind'])
    start=iso(terms['start']);end=end_date(start,terms['years'])
    return dict(company=deepcopy(s['company']),kind=native_row['kind'],start=str(start),end=str(end),
        annual=terms['annual'],years=terms['years'],total=terms['annual']*terms['years'],
        exclusive=terms['exclusive'],renewal=terms['renewal'],penalty=terms['penalty'],
        sector=sector(s['company']),negotiation=s['id'],status='active')


def remaining_penalty(contract,today):
    today=iso(str(today));start=iso(contract['start']);end=iso(contract['end'])
    if today>end:return 0
    remaining=(end-max(start,today)).days+1;whole=(end-start).days+1
    return int(round(contract['total']*remaining/whole*contract.get('penalty',0)/100))
