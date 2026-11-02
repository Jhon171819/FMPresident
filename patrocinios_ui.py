"""Mercado, mesas de negociação e carteira de patrocínios do FMPresidente."""
from copy import deepcopy
from datetime import date,datetime
import hashlib
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from PIL import Image,ImageTk,ImageOps
import fm23 as native
import negociacao as engine
import uniformes

ROOT=native.ROOT
STATE=ROOT/'dados/negociacoes.json'


def date_text(value):return date.fromisoformat(value).strftime('%d/%m/%Y')
def parse_date(value):return datetime.strptime(value.strip(),'%d/%m/%Y').date().isoformat()
def amount(value):
    text=value.replace('£','').replace('.','').replace(' ','').strip()
    if not text.isdecimal():raise ValueError('Use um valor inteiro, como 4.500.000.')
    return int(text)


class SponsorsPanel:
    def __init__(self,app,parent):
        self.app=app;self.parent=parent;self.snap=None;self.current=None;self.photo=None;self.selected=None
        # A aprovação manual usa arquivo separado e preserva negociações legadas.
        self.manual_state=ROOT/'dados/negociacoes-manuais.json'
        self.state=native.read_json(self.manual_state,{'version':1,'sessions':[]})
        self.sessions=self.state['sessions'];self.rows={};self.native_choice=tk.StringVar()
        imported=native.read_json(ROOT/'assets/patrocinadores.json',[])
        known={c['name'].casefold() for c in imported}
        for c in app.companies:
            if c['name'].casefold() not in known:
                imported.append(dict(c,id='local-'+hashlib.sha256(c['name'].encode()).hexdigest()[:12],sector='Outros',reputation=75,investment=75))
                known.add(c['name'].casefold())
        self.companies=imported
        self.build();self.fill_market();self.fill_sessions()

    def save(self):native.save_json(self.manual_state,self.state)
    def label(self,parent,text,**kwargs):return self.app.label(parent,text,**kwargs)

    def build(self):
        self.book=ttk.Notebook(self.parent);self.book.pack(fill='both',expand=True)
        market=ttk.Frame(self.book,padding=10);desk=ttk.Frame(self.book,padding=10);portfolio=ttk.Frame(self.book,padding=10)
        for frame,title in [(market,'Mercado de marcas'),(desk,'Mesa de negociação'),(portfolio,'Contratos no FM')]:self.book.add(frame,text=title)
        kits=ttk.Frame(self.book,padding=15);self.book.add(kits,text='Uniformes')
        self.label(kits,'Uniformes e patrocinadores',font=('Segoe UI',17,'bold'))
        self.kit_mode=tk.StringVar(value='Conecte ao FM para consultar o modo atual.')
        self.label(kits,'',textvariable=self.kit_mode,style='Muted.TLabel')
        self.label(kits,'Use o estilo do editor para mudar as cores e o desenho no FM. Depois, aplique os patrocinadores quando quiser voltar às imagens patrocinadas.',wraplength=950)
        row=ttk.Frame(kits);row.pack(fill='x',pady=12)
        self.apply_kits_button=self.app.button(row,'Aplicar patrocinadores no FM',self.app.apply_kit_sponsors,True)
        self.editor_kits_button=self.app.button(row,'Usar estilo do editor',self.app.use_editor_kits,True)
        self.label(kits,'São dois modos de aparência: o FM usa o desenho do editor ou as imagens patrocinadas do aplicativo. As marcas ainda não são sobrepostas ao desenho dinâmico do editor.',wraplength=950,style='Muted.TLabel')
        self.label(kits,'O desenho editado fica preservado na carreira. As imagens 2D/3D são reinstaladas e conferidas ao aplicar. Reabra a página do clube ou recarregue a skin para atualizar a exibição; uma partida já carregada pode manter a textura anterior.',wraplength=950,style='Muted.TLabel')
        self.label(market,'Escolha o espaço comercial e a empresa para iniciar as conversas.',style='Muted.TLabel')
        self.slot_box=ttk.Combobox(market,textvariable=self.native_choice,state='readonly');self.slot_box.pack(fill='x',pady=6)
        columns=ttk.Frame(market);columns.pack(fill='both',expand=True)
        left=ttk.Frame(columns);left.pack(side='left',fill='both',expand=True,padx=(0,18))
        self.search=tk.StringVar();ttk.Entry(left,textvariable=self.search).pack(fill='x',pady=5)
        self.search.trace_add('write',lambda *_:self.fill_market())
        self.market_tree=self.app.table(left,[('name','Empresa',160),('sector','Setor',145),('rating','Investimento',85)],8)
        self.market_tree.bind('<<TreeviewSelect>>',self.select_company)
        right=ttk.Frame(columns,width=355);right.pack(side='right',fill='y');right.pack_propagate(False)
        self.logo=ttk.Label(right);self.logo.pack(pady=10)
        self.company_info=tk.StringVar(value='Selecione uma empresa.')
        self.label(right,'',textvariable=self.company_info,wraplength=340)
        self.start=tk.StringVar();self.label(right,'Início pretendido (dia/mês/ano)')
        ttk.Entry(right,textvariable=self.start,width=18).pack(anchor='w',pady=4)
        row=ttk.Frame(right);row.pack(fill='x');self.app.button(row,'Abordar empresa',self.approach,True)
        self.label(right,'Perfis de jogo importados do seu pacote. A conversa é uma simulação do FMPresidente.',style='Muted.TLabel',wraplength=340)

        self.session_choice=tk.StringVar();self.session_map={}
        self.session_box=ttk.Combobox(desk,textvariable=self.session_choice,state='readonly');self.session_box.pack(fill='x',pady=(0,8))
        self.session_box.bind('<<ComboboxSelected>>',self.select_session)
        content=ttk.Frame(desk);content.pack(fill='both',expand=True)
        chat=ttk.Frame(content);chat.pack(side='left',fill='both',expand=True,padx=(0,15))
        self.transcript=tk.Text(chat,bg='#192432',fg='#edf4fc',font=('Segoe UI',10),wrap='word',relief='flat',padx=12,pady=10,height=10,state='disabled')
        bar=ttk.Scrollbar(chat,command=self.transcript.yview);self.transcript.configure(yscrollcommand=bar.set)
        self.transcript.pack(side='left',fill='both',expand=True);bar.pack(side='right',fill='y')
        form_shell=ttk.Frame(content,width=375);form_shell.pack(side='right',fill='y');form_shell.pack_propagate(False)
        form_canvas=tk.Canvas(form_shell,bg='#101720',highlightthickness=0,width=360)
        form_bar=ttk.Scrollbar(form_shell,command=form_canvas.yview);form_canvas.configure(yscrollcommand=form_bar.set)
        form_bar.pack(side='right',fill='y');form_canvas.pack(side='left',fill='both',expand=True)
        form=ttk.Frame(form_canvas);form_window=form_canvas.create_window((0,0),window=form,anchor='nw')
        form.bind('<Configure>',lambda _:form_canvas.configure(scrollregion=form_canvas.bbox('all')))
        form_canvas.bind('<Configure>',lambda event:form_canvas.itemconfigure(form_window,width=event.width))
        self.label(form,'Sua contraproposta',font=('Segoe UI',12,'bold'))
        self.variables={};self.locks={}
        for key,title,default in [('annual','Valor anual (£)',''),('years','Duração (anos)','2'),('start','Início',''),('penalty','Multa sobre saldo (%)','20')]:
            row=ttk.Frame(form);row.pack(fill='x',pady=3)
            ttk.Label(row,text=title,width=20).pack(side='left')
            var=tk.StringVar(value=default);self.variables[key]=var
            if key=='years':ttk.Combobox(row,textvariable=var,values=['1','2','3','4','5'],state='readonly',width=5).pack(side='left')
            else:ttk.Entry(row,textvariable=var,width=14 if key=='annual' else 11).pack(side='left')
            lock=tk.BooleanVar();self.locks[key]=lock
            if key!='start':ttk.Checkbutton(row,text='Fixo',variable=lock).pack(side='right')
        self.exclusive=tk.BooleanVar();self.renewal=tk.BooleanVar()
        ttk.Checkbutton(form,text='Exclusividade de setor',variable=self.exclusive).pack(anchor='w',pady=4)
        ttk.Checkbutton(form,text='Preferência para renovação',variable=self.renewal).pack(anchor='w',pady=4)
        row=ttk.Frame(form);row.pack(fill='x')
        ttk.Button(row,text='Enviar contraproposta',command=self.counter).pack(side='left',pady=6)
        ttk.Button(row,text='Desistir',command=self.withdraw).pack(side='right',pady=6)
        self.offer_info=tk.StringVar(value='Nenhuma mesa selecionada.')
        self.label(form,'',textvariable=self.offer_info,wraplength=350)
        row=ttk.Frame(form);row.pack(fill='x');self.sign_button=self.app.button(row,'Assinar oferta no FM',self.sign,True)
        self.label(desk,'Fixo = não negociável. Assinar aplica a oferta da empresa; envie qualquer alteração antes de assinar.',style='Muted.TLabel')

        self.portfolio_tree=self.app.table(portfolio,[('space','Receita nativa',160),('brand','Empresa no app',150),('total','Total no FM',120),('dates','Vigência',210)],7)
        self.portfolio_tree.bind('<<TreeviewSelect>>',lambda _:self.portfolio_details())
        self.contract_info=tk.StringVar(value='Selecione um contrato para consultar as cláusulas.')
        self.label(portfolio,'',textvariable=self.contract_info,wraplength=1060)
        row=ttk.Frame(portfolio);row.pack(fill='x');self.app.button(row,'Rescindir contrato',self.terminate,True)
        self.label(portfolio,'O FM administra os recebimentos da receita fixa. Exclusividade, preferência e multa são regras do app.\nA multa é debitada do caixa pelo FMPresidente. Alterações permanecem quando a carreira é salva no FM.',style='Muted.TLabel',wraplength=1060)

    def fill_market(self):
        query=self.search.get().casefold()
        rows=[(c['id'],(c['name'],c['sector'],str(c['investment'])+'/100')) for c in self.companies if query in (c['name']+' '+c['sector']).casefold()]
        self.app.replace_rows(self.market_tree,rows)

    def select_company(self,_=None):
        choice=self.market_tree.selection()
        if not choice:return
        company=next(c for c in self.companies if c['id']==choice[0])
        self.selected=company
        self.company_info.set(f"{company['name']}\n{company['sector']}\nReputação: {company['reputation']}/100\nInvestimento: {company['investment']}/100")
        path=ROOT/'assets'/company['logo'] if company.get('logo') else None
        if path and path.is_file():
            with Image.open(path) as im:
                self.photo=ImageTk.PhotoImage(ImageOps.contain(im.convert('RGBA'),(335,125)))
            self.logo.configure(image=self.photo)
        else:self.logo.configure(image='')

    def selected_row(self):
        if not self.snap or self.native_choice.get() not in self.rows:raise ValueError('Conecte ao FM e selecione uma receita comercial.')
        return self.rows[self.native_choice.get()]

    def approach(self):
        def work():
            if not self.selected:raise ValueError('Selecione uma marca no catálogo.')
            row=self.selected_row()
            s=engine.begin(self.selected,row,self.snap,parse_date(self.start.get()),self.sessions)
            self.sessions.append(s);self.save();self.current=s['id'];self.fill_sessions();self.load_session();self.book.select(1)
        self.app.guard(work)

    def find_session(self):return next((s for s in self.sessions if s['id']==self.current),None)

    def fill_sessions(self):
        self.session_map={f"{s['company']['name']} • {s['row']['name']} • {engine.STATES[s['status']]} • {engine.money(s['offer']['annual'])}/ano • {s['id'][:6]}":s['id'] for s in reversed(self.sessions)}
        self.session_box.configure(values=list(self.session_map))
        if self.current:self.session_choice.set(next((key for key,value in self.session_map.items() if value==self.current),''))

    def select_session(self,_=None):
        selected=self.session_map.get(self.session_choice.get())
        if not selected:return
        if selected!=self.current:self.current=selected;self.load_session()

    def load_session(self,fields=True):
        s=self.find_session()
        if not s:return
        if fields:
            for k,v in self.variables.items():v.set(date_text(s['offer'][k]) if k=='start' else str(s['offer'][k]))
            self.exclusive.set(s['offer']['exclusive']);self.renewal.set(s['offer']['renewal'])
            for k,v in self.locks.items():v.set(k in s.get('locked',[]))
        self.transcript.configure(state='normal');self.transcript.delete('1.0','end')
        for msg in s['messages']:
            who=s['company']['name'] if msg['who']=='Empresa' else msg['who']
            self.transcript.insert('end',who+'\n'+msg['text']+'\n')
            if msg.get('terms'):
                t=msg['terms'];self.transcript.insert('end',f"{t['years']} ano(s) • Início {date_text(t['start'])} • Exclusivo: {'sim' if t['exclusive'] else 'não'} • Multa: {t['penalty']}% • Preferência: {'sim' if t['renewal'] else 'não'}\n")
            self.transcript.insert('end','\n')
        self.transcript.configure(state='disabled');self.transcript.see('end')
        t=s['offer']
        self.offer_info.set(f"Oferta da empresa: {engine.money(t['annual'])}/ano\nTotal: {engine.money(t['annual']*t['years'])} • {t['years']} ano(s)\n{engine.STATES[s['status']]} • Responder até {date_text(s['expires'])}")

    def terms(self):
        return engine.validate_terms(dict(annual=amount(self.variables['annual'].get()),years=int(self.variables['years'].get()),
            start=parse_date(self.variables['start'].get()),penalty=int(self.variables['penalty'].get()),
            exclusive=bool(self.exclusive.get()),renewal=bool(self.renewal.get())))

    def update(self,s):
        self.sessions[:]=[s if item['id']==s['id'] else item for item in self.sessions]
        self.save();self.fill_sessions();self.load_session()

    def counter(self):
        def work():
            s=self.find_session()
            if not s or not self.snap:raise ValueError('Selecione uma mesa com o FM conectado.')
            self.update(engine.counter(s,self.terms(),[k for k,v in self.locks.items() if v.get()],self.snap['date']))
        self.app.guard(work)

    def withdraw(self):
        def work():
            s=self.find_session()
            if not s or not self.snap:raise ValueError('Selecione uma mesa com o FM conectado.')
            self.update(engine.withdraw(s,self.snap['date']))
        self.app.guard(work)

    @staticmethod
    def matches(row,contract):
        return (row['kind'],row['start'],row['end'],row['total'])==(contract['kind'],contract['start'],contract['end'],contract['total'])

    def match_deal(self,row):
        if not row['total']:
            return next((c for c in reversed(self.app.store['brands']) if c.get('status')=='terminated' and c.get('native_index')==row['index'] and c.get('termination_date')==row['start'] and c['kind']==row['kind']),None)
        return next((c for c in reversed(self.app.store['brands']) if self.matches(row,c)),None)

    def active_brands(self,exclude=None,exclude_indices=()):
        result=[]
        for row in self.snap['sponsors']:
            if exclude and row['index']==exclude['index']:continue
            if row['index'] in exclude_indices:continue
            deal=self.match_deal(row)
            if deal and row['total'] and row['end']>=self.snap['date']:result.append(deal)
        return result

    def sign(self):
        def prepare():
            if self.app.busy:return
            s=self.find_session()
            if not s or not self.snap or not self.app.fm:raise ValueError('Selecione uma mesa e conecte ao FM.')
            if self.terms()!=s['offer']:raise ValueError('O formulário foi alterado. Envie sua contraproposta antes de assinar.')
            row=next((r for r in self.snap['sponsors'] if r['raw']==s['row']['raw'] and r['kind']==s['row']['kind']),None)
            if not row:raise ValueError('A receita do FM mudou. Abra uma nova mesa para esse espaço.')
            affected=engine.replacements(row,s['offer'],self.snap['sponsors'])
            engine.renewal_priority(s['company'],s['offer'],row['kind'],self.app.store['brands'],self.sessions,self.snap['date'])
            for old_row in affected:
                previous=self.match_deal(old_row)
                if previous and previous.get('negotiation') and previous['end']>=self.snap['date'] and previous['company']['name']!=s['company']['name']:
                    raise ValueError('Esse espaço tem um contrato negociado com '+previous['company']['name']+'. Rescinda-o em Contratos no FM antes de trocar a empresa.')
            today=self.snap['date'];deal=engine.signing(s,today,row,self.active_brands(exclude_indices=[r['index'] for r in affected]))
            summary=(f"{deal['company']['name']} • {row['name']}\n\n{engine.money(deal['annual'])} por ano\n"
                f"{engine.money(deal['total'])} no total\n{date_text(deal['start'])} a {date_text(deal['end'])}\n"
                f"Exclusividade: {'sim' if deal['exclusive'] else 'não'} • Multa: {deal['penalty']}% do saldo restante\n\n"
                f"Substitui {len(affected)} receita(s) desse espaço, incluindo a selecionada de {engine.money(row['total'])}.\n"
                'O FM fará os recebimentos regulares do contrato. Aplicar agora?')
            if not messagebox.askyesno('Assinar patrocínio no FM',summary,parent=self.app):return
            fm=self.app.fm
            def work():
                if row['kind'] in {1,8,9,11,12,13,19}:
                    uniformes.export_kits(deal['company'],ROOT/'dados/preparados'/s['id'])
                return fm.update_sponsor(row['index'],deal['total'],engine.iso(deal['start']),engine.iso(deal['end']),row['raw'],deal['company']['name'],
                    expected_day=today,metadata={'sponsor_contract':deal,'negotiation_id':s['id']},replace_overlaps=True)
            def done(entry):
                self.commit(entry,deal,s)
                self.app.status.set('Patrocínio aplicado no FM: '+deal['company']['name']+' • '+engine.money(deal['total'])+' no total.')
            self.app.run(work,done,'Assinando e verificando o contrato real no FM…')
        self.app.guard(prepare)

    def commit(self,entry,deal,session):
        deal=dict(deal,transaction=entry['id']);self.app.store['brands'].append(deal)
        session['status']='signed';session['transaction']=entry['id']
        engine.log(session,'Sistema','Contrato assinado e verificado no FM. Os recebimentos regulares pertencem ao calendário do jogo.',session['offer'])
        # O journal nativo já contém os termos; uma falha de arquivo pode ser
        # recuperada depois, conferindo os dados efetivamente existentes no FM.
        native.save_json(self.app_state_path(),self.app.store);self.save();native.finalize_local_commit(entry);self.app.refresh_history()
        try:self.app.snap=self.app.fm.snapshot();self.app.render();self.app.check_kit()
        except (ValueError,OSError):self.app.status.set('O contrato foi gravado. Reconecte para atualizar a leitura do FM.')
        self.fill_sessions();self.load_session()

    @staticmethod
    def app_state_path():return ROOT/'dados/presidencia.json'

    def recover(self):
        entries=[]
        for file in sorted((ROOT/'dados/historico').glob('*.json')):
            entry=native.read_json(file,{})
            if entry.get('status')=='applied':entries.append(entry)
        undone={e.get('meta',{}).get('undoes') for e in entries}
        known={c.get('transaction') for c in self.app.store['brands']}
        changed=False
        for s in self.sessions:
            if s.get('transaction') in undone and s['status']=='signed':
                s['status']='reverted';engine.log(s,'Sistema','A assinatura foi desfeita pelo histórico de alterações do FM.');changed=True
        for entry in entries:
            deal=entry.get('meta',{}).get('sponsor_contract')
            if not deal or entry['id'] in undone:continue
            if not any(self.matches(r,deal) for r in self.snap['sponsors']):continue
            if entry['id'] not in known:
                self.app.store['brands'].append(dict(deal,transaction=entry['id']));known.add(entry['id']);changed=True
            for s in self.sessions:
                if s['id']==deal['negotiation'] and s['status']!='signed':s['status']='signed';s['transaction']=entry['id'];changed=True
        if changed:native.save_json(self.app_state_path(),self.app.store);self.save()

    def refresh(self,snapshot,inputs=False):
        self.snap=snapshot
        mode=snapshot.get('licensed_kits')
        self.kit_mode.set('Modo no FM: '+('imagens patrocinadas' if mode else 'estilo do editor') if mode is not None else 'Modo do uniforme indisponível nesta leitura.')
        # A coincidência de valores não prova associação à carreira atual.
        restored=False
        for row in snapshot['sponsors']:
            deal=self.match_deal(row)
            if deal and row['total'] and deal.get('status')=='terminated':deal['status']='active';restored=True
        if restored:native.save_json(self.app_state_path(),self.app.store)
        old_index=self.rows.get(self.native_choice.get(),{}).get('index')
        self.rows={f"{r['index']+1}. {r['name']} • {engine.money(r['total'])} no total • até {date_text(r['end'])}":r for r in snapshot['sponsors'] if r['kind'] in engine.COMMERCIAL}
        self.slot_box.configure(values=list(self.rows))
        selected=next((key for key,r in self.rows.items() if r['index']==old_index),None)
        if not selected:selected=next((key for key,r in self.rows.items() if r['kind']==1 and r['start']<=snapshot['date']<=r['end']),next((key for key,r in self.rows.items() if r['kind']==1),next(iter(self.rows),'')))
        self.native_choice.set(selected)
        if not self.start.get():self.start.set(date_text(snapshot['date']))
        changed=False
        for index,s in enumerate(self.sessions):
            t=engine.tick(s,snapshot['date'])
            if t['status'] in engine.OPEN and not any(r['raw']==s['row']['raw'] and r['kind']==s['row']['kind'] for r in snapshot['sponsors']):
                t['status']='stale';engine.log(t,'Sistema','A receita foi alterada no FM ou por outra assinatura. Abra uma nova mesa.')
            if t!=s:self.sessions[index]=t;changed=True
        if changed:self.save();self.fill_sessions();self.load_session(fields=False)
        rows=[(str(r['index']),(r['name'],(self.match_deal(r) or {}).get('company',{}).get('name','Sem marca cadastrada'),engine.money(r['total']),date_text(r['start'])+' — '+date_text(r['end']))) for r in snapshot['sponsors']]
        self.app.replace_rows(self.portfolio_tree,rows)
        self.portfolio_details()

    def portfolio_details(self):
        if not self.snap or not self.portfolio_tree.selection():return
        row=next((r for r in self.snap['sponsors'] if r['index']==int(self.portfolio_tree.selection()[0])),None)
        if not row:return
        c=self.match_deal(row)
        if not c:self.contract_info.set('Receita real do FM. Sem cláusulas comerciais cadastradas no FMPresidente.');return
        fee=engine.remaining_penalty(c,self.snap['date'])
        state='Rescindido' if not row['total'] else 'Agendado' if row['start']>self.snap['date'] else 'Encerrado' if row['end']<self.snap['date'] else 'Vigente'
        if not row['total']:fee=0
        self.contract_info.set(f"{c['company']['name']} • {state} • Exclusividade: {'sim' if c.get('exclusive') else 'não'} • Preferência de renovação: {'sim' if c.get('renewal') else 'não'}\nMulta para rescindir hoje: {engine.money(fee)}. A receita fixa e as datas estão no FM; as cláusulas ficam no app.")

    def terminate(self):
        def prepare():
            if self.app.busy:return
            if not self.snap or not self.app.fm or not self.portfolio_tree.selection():raise ValueError('Selecione um contrato com o FM conectado.')
            row=next(r for r in self.snap['sponsors'] if r['index']==int(self.portfolio_tree.selection()[0]))
            c=self.match_deal(row)
            if not c:raise ValueError('Esse contrato não tem termos de rescisão cadastrados no FMPresidente.')
            if not row['total']:raise ValueError('Esse contrato já foi encerrado.')
            today=self.snap['date'];fee=engine.remaining_penalty(c,today)
            if not messagebox.askyesno('Rescindir contrato',f"Encerrar o patrocínio de {c['company']['name']}?\n\nA receita será zerada no FM e a multa de {engine.money(fee)} será descontada do caixa.\nO app também atualizará os uniformes associados.",parent=self.app):return
            fm=self.app.fm
            def done(entry):
                c['status']='terminated';c['termination']=entry['id'];c['termination_date']=today;c['native_index']=row['index'];native.save_json(self.app_state_path(),self.app.store);native.finalize_local_commit(entry)
                self.app.refresh_history();self.app.snap=fm.snapshot();self.app.render();self.app.check_kit()
                self.app.status.set('Contrato encerrado no FM. Multa debitada: '+engine.money(fee)+'.')
            self.app.run(lambda:fm.terminate_sponsor(row['index'],row['raw'],fee,today,{'sponsor_termination':c.get('transaction'),'company':c['company']['name']}),done,'Encerrando receita e aplicando a multa no caixa…')
        self.app.guard(prepare)
