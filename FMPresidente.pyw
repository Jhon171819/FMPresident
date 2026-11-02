"""FMPresidente — gestão externa aplicada diretamente ao FM23."""
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import fm23 as native
import uniformes
import patrocinios_ui
import emprestimos_ui
import sincronizacao_hibrida as sync
import recuperacao
import time

native.C.windll.shell32.SetCurrentProcessExplicitAppUserModelID('FMPresidente.FM23.Local')

ROOT=native.ROOT
STATE=ROOT/'dados/presidencia.json'
BG='#101720';PANEL='#192432';FG='#edf4fc';MUTED='#9eafc2';ACCENT='#52dec2'


def money(value): return '£ '+f'{value:,.0f}'.replace(',','.')
def dt(value): return date.fromisoformat(value).strftime('%d/%m/%Y')
def parse_date(value): return datetime.strptime(value.strip(),'%d/%m/%Y').date()
def integer(text):
    text=text.strip().replace('£','').replace(' ','').replace('.','')
    if not text.isdecimal(): raise ValueError('Informe um número inteiro positivo; pontos separam milhares.')
    return int(text)
def price(text): return float(text.strip().replace('£','').replace(' ','').replace(',','.'))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('FMPresidente — FM23')
        self.geometry('1190x805');self.minsize(1060,740);self.configure(bg=BG)
        self.fm=None;self.snap=None;self.busy=False;self.closed=False;self.events=queue.Queue()
        self.sync=sync.Coordinator();self.last_monitor=0;self.selected_candidate=None;self.candidates=[]
        self.recovery_running=False
        self.pending_sync=False
        self.store=native.read_json(STATE,{'brands':[],'custom':[],'quotes':{},'installed':None})
        self.companies=[{'name':'Samsung','logo':'samsung.png'},{'name':'Spotify','logo':'spotify.png'}]+self.store.get('custom',[])
        self.quote=None;self.selected_sponsor=None;self.history_entries=[]
        self.style();self.build();self.protocol('WM_DELETE_WINDOW',self.close)
        self.after(150,self.pump);self.after(300,self.connect);self.after(500,self.update_recovery_indicator);self.after(4000,self.poll)

    def style(self):
        s=ttk.Style(self);s.theme_use('clam')
        s.configure('.',font=('Segoe UI',10),background=PANEL,foreground=FG)
        s.configure('TFrame',background=BG);s.configure('TLabel',background=BG,foreground=FG)
        s.configure('Title.TLabel',font=('Segoe UI',25,'bold'))
        s.configure('Muted.TLabel',foreground=MUTED)
        s.configure('TButton',padding=(14,9),background='#254354',foreground=FG)
        s.map('TButton',background=[('active','#326070'),('disabled','#202b37')],foreground=[('disabled','#718294')])
        s.configure('Accent.TButton',background='#197b6b')
        s.configure('TEntry',fieldbackground='#263545',foreground=FG,insertcolor=FG,padding=7)
        s.configure('TCombobox',fieldbackground='#263545',foreground=FG,padding=6)
        s.map('TCombobox',fieldbackground=[('readonly','#263545')],foreground=[('readonly',FG)])
        s.configure('TNotebook',background=BG,borderwidth=0)
        s.configure('TNotebook.Tab',padding=(15,10),background=PANEL)
        s.map('TNotebook.Tab',background=[('selected','#254758')])
        s.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,rowheight=31,borderwidth=0)
        s.configure('Treeview.Heading',background='#253749',foreground=FG,padding=7)
        s.map('Treeview',background=[('selected','#285b64')])

    def label(self,parent,text,**kw):
        obj=ttk.Label(parent,text=text,**kw);obj.pack(anchor='w',pady=5);return obj

    def button(self,parent,text,command,write=False):
        b=ttk.Button(parent,text=text,command=command,style='Accent.TButton' if write else 'TButton')
        b.pack(side='left',padx=(0,10),pady=8)
        if write:self.actions.append(b);b.state(['disabled'])
        return b

    def entry(self,parent,label,value,width=24):
        row=ttk.Frame(parent);row.pack(fill='x',pady=6)
        ttk.Label(row,text=label,width=29).pack(side='left')
        v=tk.StringVar(value=str(value));ttk.Entry(row,textvariable=v,width=width).pack(side='left')
        return v

    def table(self,parent,columns,heights=8):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True,pady=8)
        tree=ttk.Treeview(frame,columns=[c[0] for c in columns],show='headings',height=heights,selectmode='browse')
        for key,title,width in columns:tree.heading(key,text=title);tree.column(key,width=width,minwidth=65)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set)
        tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        return tree

    def build(self):
        self.actions=[]
        outer=ttk.Frame(self,padding=22);outer.pack(fill='both',expand=True)
        top=ttk.Frame(outer);top.pack(fill='x')
        ttk.Label(top,text='FMPresidente',style='Title.TLabel').pack(side='left')
        ttk.Label(top,text='GESTÃO DO CLUBE  /  IDENTIDADE PENDENTE',style='Muted.TLabel').pack(side='left',padx=22)
        ttk.Button(top,text='Sincronizar com FM23',command=self.connect).pack(side='right')
        ttk.Button(top,text='Aplicar patrocinadores',command=self.apply_kit_sponsors).pack(side='right',padx=8)
        self.connection=tk.StringVar(value='Preparando conexão…')
        self.label(outer,'',textvariable=self.connection,style='Muted.TLabel')
        self.recovery_summary=tk.StringVar(value='Recuperação: verificando histórico…')
        self.label(outer,'',textvariable=self.recovery_summary,style='Muted.TLabel')
        self.status=tk.StringVar(value='Iniciando…');self.label(outer,'',textvariable=self.status,style='Muted.TLabel',wraplength=1120)
        candidate_row=ttk.Frame(outer);candidate_row.pack(fill='x')
        ttk.Button(candidate_row,text='Buscar candidatos',command=self.search_candidates).pack(side='left',padx=(0,8))
        ttk.Button(candidate_row,text='Buscar mais',command=lambda:self.search_candidates(full=True)).pack(side='left',padx=(0,8))
        self.candidate_filter=tk.StringVar()
        ttk.Label(candidate_row,text='Nome ou ID:').pack(side='left',padx=(0,4))
        ttk.Entry(candidate_row,textvariable=self.candidate_filter,width=18).pack(side='left',padx=(0,8))
        self.candidate_choice=tk.StringVar()
        self.candidate_box=ttk.Combobox(candidate_row,textvariable=self.candidate_choice,state='readonly',width=55)
        self.candidate_box.pack(side='left',padx=(0,8))
        ttk.Button(candidate_row,text='Selecionar candidato',command=self.select_candidate).pack(side='left')
        cards=ttk.Frame(outer);cards.pack(fill='x',pady=(8,14))
        self.cards={}
        for key,label in [('balance','CAIXA'),('transfer','TRANSFERÊNCIAS'),('wage','FOLHA / SEMANA'),('date','DATA DA CARREIRA')]:
            f=tk.Frame(cards,bg=PANEL,padx=18,pady=12);f.pack(side='left',fill='x',expand=True,padx=(0,9))
            tk.Label(f,text=label,bg=PANEL,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w')
            v=tk.StringVar(value='—');tk.Label(f,textvariable=v,bg=PANEL,fg=ACCENT,font=('Segoe UI',18,'bold')).pack(anchor='w')
            self.cards[key]=v
        self.tabs=ttk.Notebook(outer);self.tabs.pack(fill='both',expand=True)
        pages={}
        for name in ['Presidência','Patrocínios','Infraestrutura','Bilheteria','Empréstimos','Histórico']:
            p=ttk.Frame(self.tabs,padding=16);self.tabs.add(p,text=name);pages[name]=p

        p=pages['Presidência']
        self.label(p,'Decisões de diretoria',font=('Segoe UI',17,'bold'))
        self.label(p,'Os valores abaixo vêm do FM. As decisões são gravadas diretamente na carreira aberta.',style='Muted.TLabel')
        self.transfer=self.entry(p,'Orçamento de transferências (£)','0')
        self.wage=self.entry(p,'Orçamento salarial / semana (£)','0')
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'Aplicar orçamentos',self.apply_budgets,True)
        self.label(p,'Definir um orçamento autoriza gastos; não retira dinheiro do caixa imediatamente.',style='Muted.TLabel')
        self.capital=self.entry(p,'Aporte da presidência (£)','1.000.000')
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'Investir capital no clube',self.apply_capital,True)
        self.label(p,'O aporte é uma regra do FMPresidente: credita o caixa sem criar uma dívida ou um acionista no FM.',style='Muted.TLabel')
        row=ttk.Frame(p);row.pack(fill='x',pady=15)
        self.button(row,'Criar backup do save',self.backup)
        self.button(row,'Abrir pasta do aplicativo',lambda:os.startfile(ROOT))
        self.label(p,'Use com o FM parado, fora de partidas, processamento e telas do editor.\nAs alterações ficam permanentes quando o próprio FM salva a carreira.',style='Muted.TLabel')

        p=pages['Patrocínios']
        self.sponsors_panel=patrocinios_ui.SponsorsPanel(self,p)

        p=pages['Infraestrutura']
        self.label(p,'Investir na estrutura do clube',font=('Segoe UI',17,'bold'))
        self.label(p,'Cada investimento sobe um nível e desconta o custo do caixa na mesma operação.\nOs custos são regras do FMPresidente e a melhoria é aplicada imediatamente.',style='Muted.TLabel')
        self.facility_labels={}
        for name in native.FACILITIES:
            row=ttk.Frame(p);row.pack(fill='x',pady=14)
            v=tk.StringVar(value=name+' —');self.facility_labels[name]=v
            ttk.Label(row,textvariable=v,width=72).pack(side='left')
            self.button(row,'Investir +1 nível',lambda n=name:self.invest(n),True)
        self.label(p,'O limite nativo é 20. O FM continua usando seus próprios cálculos para treino, formação e recrutamento.',style='Muted.TLabel',wraplength=1040)

        p=pages['Bilheteria']
        self.label(p,'Preços do clube',font=('Segoe UI',17,'bold'))
        self.label(p,'Altera o ingresso médio e o preço médio do carnê nos dados financeiros reais do clube.',style='Muted.TLabel')
        self.ticket=self.entry(p,'Ingresso médio (£)','0')
        self.season=self.entry(p,'Carnê de temporada (£)','0')
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'Aplicar preços',self.apply_prices,True)
        self.attendance=tk.StringVar(value='Público de referência: —');self.label(p,'',textvariable=self.attendance)
        self.label(p,'O FM calcula as receitas conforme a competição e seus calendários de venda.\nDefinir o preço do carnê não cria sócios ou vendas de carnês automaticamente.',style='Muted.TLabel')

        p=pages['Empréstimos']
        self.loans_panel=emprestimos_ui.LoansPanel(self,p)
        if '--emprestimos' in sys.argv:self.tabs.select(p)

        p=pages['Histórico']
        self.history_tree=self.table(p,[('time','Aplicado em',145),('date','Dia no FM',100),('title','Decisão',390),('status','Estado',100)],9)
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'Desfazer decisão selecionada',self.undo,True)
        self.button(row,'Atualizar histórico',self.refresh_history)
        self.button(row,'Central de Recuperação',self.open_recovery)
        self.label(p,'Desfazer exige a mesma sessão e data, com os campos ainda iguais aos gravados.\nPara voltar a outro dia ou depois de reabrir o jogo, use o backup da carreira.',style='Muted.TLabel')
        self.refresh_history()

    def run(self,fn,done=None,text='Aplicando…'):
        if self.busy:return
        self.busy=True;self.status.set(text);self.set_actions(False)
        def worker():
            try:self.events.put(('done',fn(),done))
            except Exception as exc:
                self.events.put(('error',str(exc),None))
                with (ROOT/'dados/erros.log').open('a',encoding='utf-8') as f:f.write(datetime.now().isoformat()+'\n'+traceback.format_exc()+'\n')
        threading.Thread(target=worker,daemon=True).start()

    def pump(self):
        if self.closed:return
        try:
            while True:
                kind,result,callback=self.events.get_nowait()
                if kind=='progress':self.status.set(result);continue
                if kind=='recovery_indicator':
                    self.recovery_running=False
                    count=sum(r.state in ('STATE_UNKNOWN','RECOVERY_REQUIRED','LOCAL_COMMIT_PENDING','JOURNAL_UNREADABLE') for r in result)
                    self.recovery_summary.set(f'Recuperação: {count} registro(s) pendente(s); consulte a aba Histórico.' if count else 'Recuperação: nenhuma pendência identificada.')
                    continue
                self.busy=False
                if kind=='error':
                    self.status.set(result)
                    self.update_recovery_indicator()
                    if result.startswith(('Build bloqueada','Identidade não verificada')):
                        self.snap=None;self.connection.set(result)
                    elif self.fm is None:self.connection.set('Desconectado • '+result)
                    messagebox.showerror('Operação não concluída',result,parent=self)
                elif callback:
                    try:callback(result)
                    except Exception as exc:
                        self.update_recovery_indicator()
                        if isinstance(result,dict) and result.get('status')=='applied':
                            self.snap=None;self.set_actions(False)
                            self.status.set('Alteração aplicada na memória, mas a atualização local falhou. Não repita; operação '+result.get('id','desconhecida'))
                            messagebox.showwarning('Alteração aplicada',self.status.get(),parent=self)
                        else:self.status.set(str(exc));messagebox.showerror('Atualização do painel',str(exc),parent=self)
                self.set_actions(self.fm is not None and self.snap is not None)
                if getattr(self,'pending_sync',False) and not self.busy:
                    self.pending_sync=False
                    self.connect()
        except queue.Empty:pass
        self.after(150,self.pump)

    def set_actions(self,enabled):
        for b in self.actions:b.state(['!disabled'] if enabled and not self.busy else ['disabled'])
        self.loans_panel.set_enabled(enabled and not self.busy)

    def connect(self):
        if self.busy:
            self.pending_sync=True
            self.sync.begin()
            self.status.set('Sincronização recebida; aguardando a tarefa atual terminar…')
            self.set_actions(False)
            return
        epoch=self.sync.begin()
        self.selected_candidate=None;self.candidates=[];self.candidate_choice.set('');self.candidate_box.configure(values=[])
        if self.fm:self.fm.close();self.fm=None
        self.snap=None;self.clear_candidate_cards();self.set_actions(False)
        self.connection.set('Sincronizando • identidade da carreira ainda não comprovada')
        def work():
            try:return sync.observe_and_candidates(query=self.candidate_filter_value),None
            except Exception as exc:return None,str(exc)
        def ready(result):
            payload,error=result
            observation=payload[0] if payload else None
            if not self.sync.finish(epoch,observation,error):return
            self.last_monitor=time.monotonic()
            if error:
                self.connection.set('Observação indisponível • '+error)
                self.status.set('Sincronização falhou. Verifique o FM e tente novamente.')
            else:
                self.show_observation(observation)
                self.update_recovery_indicator()
                # Agendado após liberar a fila do Tkinter; descarta épocas antigas.
                self.candidates,limited=payload[1]
                self.candidate_box.configure(values=[f'{c.club.name} • ID {c.club.uid} • candidato {i+1}' for i,c in enumerate(self.candidates)])
                self.status.set(f'{len(self.candidates)} candidato(s). Escolha na lista e clique em Selecionar candidato.' if self.candidates else 'Nenhum candidato encontrado nesta busca. Tente Buscar mais.')
        self.candidate_filter_value=self.candidate_filter.get().strip()
        self.run(work,ready,'Observando FM23…')

    def search_candidates(self,full=False):
        if self.busy:return
        epoch=self.sync.epoch;query=self.candidate_filter.get().strip()
        def ready(result):
            if epoch!=self.sync.epoch:return
            previous=self.candidate_box.current()
            address=self.candidates[previous].address if 0<=previous<len(self.candidates) else None
            self.candidates,limited=result
            self.candidate_box.configure(values=[f"{c.club.name} • ID {c.club.uid} • {'vínculo observado' if c.source=='vinculo' else 'registro anterior: vínculo não confirmado'} • {i+1}" for i,c in enumerate(self.candidates)])
            selected=next((i for i,c in enumerate(self.candidates) if c.address==address),None)
            if selected is None:self.candidate_choice.set('')
            else:self.candidate_box.current(selected)
            self.status.set(f'{len(self.candidates)} registros disponíveis'+(' (busca limitada).' if limited else '.')+' A relação com o treinador ativo ainda não foi comprovada.')
        self.run(lambda:sync.search_candidates(prefer_cache=not full,query=query),ready,'Buscando clubes candidatos…')

    def select_candidate(self):
        if self.busy:return
        index=self.candidate_box.current()
        if not 0<=index<len(self.candidates):
            self.status.set('Selecione um clube candidato na lista.');return
        candidate=self.candidates[index];epoch=self.sync.begin()
        self.selected_candidate=None;self.snap=None;self.clear_candidate_cards();self.set_actions(False)
        if self.fm:self.fm.close();self.fm=None
        def work():
            fm=None
            try:
                fm=native.FM.connect_manual(candidate.address,candidate.club.uid)
                snapshot=fm.snapshot()
                fm.guard.require_fast()
                observation=sync.Observation((fm.process['pid'],fm.process['started'],fm.process['version']),
                    fm.guard.result.profile,datetime.now().astimezone().isoformat(),candidate.club.uid,
                    candidate.address,snapshot['date'],candidate_name=candidate.club.name,
                    balance=snapshot['balance'],transfer=snapshot['transfer'],wage=snapshot['wage'])
                return observation,fm,snapshot,None
            except Exception as exc:
                if fm:fm.close()
                return None,None,None,str(exc)
        def ready(result):
            observation,fm,snapshot,error=result
            if not self.sync.finish(epoch,observation,error):
                if fm:fm.close()
                return
            self.last_monitor=time.monotonic()
            if error:self.connection.set('Candidato indisponível • '+error);self.status.set('Busque candidatos novamente.')
            else:
                self.selected_candidate=candidate.address;self.fm=fm;self.snap=snapshot
                self.render(True)
                self.status.set('Clube selecionado e aprovado manualmente. A identidade do save não foi comprovada.')
        self.run(work,ready,'Verificando candidato…')

    def clear_candidate_cards(self):
        for value in self.cards.values():value.set('—')

    def show_observation(self, observation):
        if self.selected_candidate is not None and observation.balance is not None:
            for key in ('balance','transfer','wage'):self.cards[key].set(money(getattr(observation,key)))
            self.cards['date'].set(dt(observation.game_date))
        club=(' • clube candidato ID '+str(observation.candidate_uid)) if observation.candidate_uid else ''
        self.connection.set('FM '+observation.process[2]+' • build validada • '+('candidato selecionado: '+observation.candidate_name+' • dados somente leitura' if self.selected_candidate is not None and observation.candidate_name else 'observação não verificada'+club))
        self.status.set('Observação atualizada. Carreira e treinador não comprovados; operações indisponíveis. Última leitura: '+observation.observed_at)

    def import_previous(self):
        if self.store.get('imported'):return
        old=native.read_json(ROOT.parent/'Patrocinios FM23/dados/contratos.json',{})
        for c in old.get('contracts',[]):
            start=parse_date(c['start']).isoformat();end=parse_date(c['end']).isoformat()
            for r in self.snap['sponsors']:
                if r['kind']==1 and r['start']==start and r['end']==end:
                    self.store['brands'].append(dict(company=c['company'],kind=1,start=start,end=end,total=r['total']))
        self.store['imported']=True;native.save_json(STATE,self.store)

    def brand_for(self,row):
        for b in reversed(self.store['brands']):
            if (b['kind'],b['start'],b['end'],b['total'])==(row['kind'],row['start'],row['end'],row['total']):return b['company']['name']
        return '—'

    def render(self,inputs=False):
        s=self.snap
        for key in self.cards:self.cards[key].set(dt(s[key]) if key=='date' else money(s[key]))
        self.connection.set(f"Clube aprovado manualmente • FM {self.fm.process['version']} • Ceará (ID {native.UID}) • identidade do save não comprovada")
        if inputs:
            self.transfer.set(f"{s['transfer']:,}".replace(',','.'));self.wage.set(str(s['wage']))
            self.ticket.set(f"{s['ticket']:.4f}");self.season.set(f"{s['season_ticket']:.2f}")
        for name,level in s['facilities'].items():
            cost='Máximo atingido' if level>=20 else 'Próximo nível: '+money(native.LEVEL_COST[name]*(level+1))
            self.facility_labels[name].set(f'{name}   {level}/20   •   {cost}')
        self.attendance.set(f"Público de referência do clube: {s['attendance']:,}".replace(',','.'))
        self.sponsors_panel.refresh(s,inputs)
        self.loans_panel.refresh(s,inputs)

    @staticmethod
    def replace_rows(tree,rows):
        wanted={i for i,_ in rows}
        for i in tree.get_children():
            if i not in wanted:tree.delete(i)
        for i,values in rows:
            if tree.exists(i):
                if tuple(map(str,tree.item(i,'values')))!=tuple(map(str,values)):tree.item(i,values=values)
            else:tree.insert('','end',iid=i,values=values)

    def poll(self):
        if self.closed:return
        if not self.busy and self.sync.state==sync.State.OBSERVED_UNVERIFIED and time.monotonic()-self.last_monitor>=20:
            epoch=self.sync.epoch;self.last_monitor=time.monotonic()
            active_fm=self.fm;selected=self.selected_candidate
            def work():
                try:
                    observation=sync.observe(selected)
                    snapshot=active_fm.snapshot() if active_fm else None
                    return observation,None,snapshot,None
                except Exception as exc:return None,str(exc),None,None
            def ready(result):
                observation,error,snapshot,_=result
                if not self.sync.inspect(epoch,observation,error):return
                if self.sync.state==sync.State.CONTEXT_CHANGED:
                    if self.fm:self.fm.close();self.fm=None
                    self.snap=None;self.clear_candidate_cards();self.selected_candidate=None;self.candidates=[];self.candidate_choice.set('');self.candidate_box.configure(values=[]);self.connection.set('Contexto alterado ou indisponível • sincronize novamente')
                    self.status.set('A observação anterior foi invalidada; identidade não comprovada.')
                elif self.fm:
                    try:
                        changed=snapshot!=self.snap;self.snap=snapshot
                        if changed:self.render()
                    except Exception as exc:
                        self.fm.close();self.fm=None;self.snap=None;self.clear_candidate_cards();self.set_actions(False);self.connection.set('Contexto inválido • '+str(exc))
                else:self.show_observation(observation)
            self.run(work,ready,'Verificando conexão…')
        self.after(4000,self.poll)

    def apply(self,fn):
        if not self.fm or not self.snap:raise ValueError('Conecte à carreira primeiro.')
        def work():
            result=fn()
            try:return result,self.fm.snapshot(),None
            except Exception as exc:return result,None,str(exc)
        def done(result):
            entry,self.snap,error=result
            if error:
                self.set_actions(False)
                self.status.set('Alteração aplicada na memória, mas a atualização do painel falhou. Não repita; operação '+entry['id'])
                messagebox.showwarning('Alteração aplicada',self.status.get(),parent=self)
                return
            self.render(True);self.refresh_history()
            self.status.set('Aplicado na memória do FM. Salve a carreira no jogo para persistir.')
        self.run(work,done)

    def guard(self,fn):
        try:fn()
        except Exception as exc:messagebox.showerror('Revise os dados',str(exc),parent=self)

    def apply_budgets(self):self.guard(lambda:self.apply(lambda:self.fm.budgets(integer(self.transfer.get()),integer(self.wage.get()))))
    def apply_capital(self):self.guard(lambda:self.apply(lambda:self.fm.capital(integer(self.capital.get()))))
    def apply_prices(self):self.guard(lambda:self.apply(lambda:self.fm.prices(price(self.ticket.get()),price(self.season.get()))))
    def invest(self,name):self.guard(lambda:self.apply(lambda:self.fm.invest(name)))

    def apply_kit_sponsors(self):
        def prepare():
            if not self.fm or not self.snap:raise ValueError('Conecte ao FM primeiro.')
            self.check_kit(force=True,enable=True)
        self.guard(prepare)

    def use_editor_kits(self):
        def prepare():
            if not self.fm or not self.snap:raise ValueError('Conecte ao FM primeiro.')
            def done(entry):
                self.refresh_history();self.snap=self.fm.snapshot();self.render()
                self.status.set('Estilo do editor habilitado. Reabra a página do clube no FM para atualizar. As imagens patrocinadas ficaram guardadas.')
            self.run(lambda:self.fm.set_licensed_kits(False,self.snap['date']),done,'Habilitando o estilo do editor…')
        self.guard(prepare)

    def check_kit(self,force=False,enable=False):
        if self.busy or not self.snap:return
        bundle=uniformes.active_sponsors(self.snap,self.store['brands'])
        if not bundle and self.store.get('installed') is None:
            if force:self.status.set('Não há patrocinador de camisa vigente vinculado aos contratos do FM.')
            return
        key=uniformes.kit_signature(bundle)
        if not force and self.store.get('installed')==key and uniformes.installation_ok(key):return
        def work():
            folder=ROOT/'dados/uniforme-atual'
            uniformes.export_kits(bundle.get(1),folder,bundle.get(8));uniformes.install_kits(folder,key)
            if enable:self.fm.set_licensed_kits(True,self.snap['date'])
            self.store['installed']=key;native.save_json(STATE,self.store)
            return ', '.join(company['name'] for company in bundle.values()) or 'sem patrocínio cadastrado vigente'
        def done(names):
            if enable:
                self.refresh_history();self.snap=self.fm.snapshot();self.render()
            self.status.set('Uniformes patrocinados '+('habilitados no FM' if enable else 'instalados')+': '+names+'. Reabra o clube ou recarregue a skin no FM.')
        self.run(work,done,'Aplicando os patrocinadores e verificando os uniformes…')

    def update_recovery_indicator(self):
        if self.closed or self.recovery_running:return
        self.recovery_running=True
        def work():
            try:result=recuperacao.scan(native.DATA/'historico')
            except Exception:
                result=[recuperacao.Record('','Histórico indisponível','','JOURNAL_UNREADABLE','Indeterminado',None,None,'Falha ao consultar histórico.')]
            self.events.put(('recovery_indicator',result,None))
        threading.Thread(target=work,daemon=True).start()

    def open_recovery(self):
        window=tk.Toplevel(self);window.title('Central de Recuperação')
        window.geometry('1050x520')
        self.label(window,'Diagnóstico de operações e arquivos locais',font=('Segoe UI',14,'bold'))
        self.label(window,'PID não identifica o save. Estados incertos exigem verificação; não repita a operação.',wraplength=980)
        table=self.table(window,[('time','Data',145),('title','Operação',270),('state','Estado',190),('resource','Recurso',200)],10)
        status=tk.StringVar(value='Aguardando leitura…');self.label(window,'',textvariable=status,wraplength=980)
        records=[]
        def update():
            if self.busy:
                status.set('Aguarde a operação atual terminar e atualize o diagnóstico.');return
            def done(result):
                if not window.winfo_exists():return
                records[:]=result
                self.replace_rows(table,[(str(i),(r.time[:19].replace('T',' '),r.title,r.state,r.resource)) for i,r in enumerate(records)])
                status.set(f'{len(records)} registros. Selecione um para ver orientações. Nenhuma alteração no FM.')
            self.run(lambda:recuperacao.scan(native.DATA/'historico'),done,'Lendo diagnóstico de recuperação…')
        def selected(_event=None):
            chosen=table.selection()
            if not chosen:return
            r=records[int(chosen[0])]
            status.set((f'Operação {r.operation_id or "não identificada"} • {r.reason} '
                'Para estado incerto, não repita a operação; verifique a carreira e um backup.'))
        def export():
            if self.busy:return
            path=filedialog.asksaveasfilename(parent=window,title='Exportar diagnóstico',defaultextension='.json',filetypes=[('JSON','*.json')])
            if not path:return
            payload={'aviso':'Diagnóstico local; não identifica o save.','operacoes':[r.public() for r in records]}
            def done(_):
                if window.winfo_exists():status.set('Diagnóstico exportado.')
            self.run(lambda:native.save_json(path,payload),done,'Exportando diagnóstico…')
        table.bind('<<TreeviewSelect>>',selected)
        row=ttk.Frame(window);row.pack(fill='x',padx=10)
        ttk.Button(row,text='Atualizar diagnóstico',command=update).pack(side='left',padx=5,pady=8)
        ttk.Button(row,text='Exportar relatório',command=export).pack(side='left',padx=5,pady=8)
        self.after(0,update)

    def refresh_history(self):
        # Histórico legado não está associado com segurança à carreira atual.
        files=[]
        self.history_entries=[native.read_json(p,{}) for p in files[:200]]
        self.replace_rows(self.history_tree,[(str(i),(e.get('time','')[:19].replace('T',' '),dt(e['date']),e.get('title',''),{'applied':'Aplicado','failed':'Falhou','prepared':'Pendente'}.get(e.get('status'),e.get('status')))) for i,e in enumerate(self.history_entries)])

    def undo(self):
        def prepare():
            if not self.history_tree.selection():raise ValueError('Selecione a decisão que deseja desfazer.')
            entry=self.history_entries[int(self.history_tree.selection()[0])]
            self.apply(lambda:self.fm.undo(entry))
        self.guard(prepare)

    def backup(self):
        self.run(native.backup_save,lambda p:self.status.set('Backup criado: '+p.name),'Copiando o último save local…')

    def close(self):
        if self.busy:
            self.status.set('Aguarde a operação terminar antes de fechar.');return
        self.closed=True
        self.sync.close()
        if self.fm:self.fm.close()
        self.destroy()


if __name__=='__main__':
    if '--self-check' in sys.argv:
        import io
        from contextlib import redirect_stdout
        from testar_patrocinios import check
        from testar_uniformes import check as check_kits
        from verificar import selfcheck
        from testar_emprestimos import check as check_loans
        capture=io.StringIO()
        try:
            with redirect_stdout(capture):check();selfcheck();check_kits();check_loans()
            diagnostic={'ok':True,'root':str(ROOT),'frozen':bool(getattr(sys,'frozen',False)),'checks':capture.getvalue()}
            if '--live-read' in sys.argv:
                fm=native.FM()
                try:
                    snapshot=fm.snapshot();diagnostic['fm']={'date':snapshot['date'],'uid':snapshot['uid'],'sponsors':len(snapshot['sponsors'])}
                finally:fm.close()
            native.save_json(ROOT/'dados/autoteste-executavel.json',diagnostic)
        except Exception:
            native.save_json(ROOT/'dados/autoteste-executavel.json',{'ok':False,'error':traceback.format_exc(),'checks':capture.getvalue()})
            sys.exit(1)
        sys.exit(0)
    native.k.CreateMutexW.argtypes=[native.C.c_void_p,native.W.BOOL,native.W.LPCWSTR]
    native.k.CreateMutexW.restype=native.W.HANDLE
    instance_mutex=native.k.CreateMutexW(None,False,'Local\\FMPresidenteFM23')
    if native.C.get_last_error()==183:sys.exit(0)
    try:App().mainloop()
    except Exception:
        (ROOT/'dados/falha-inicializacao.log').write_text(traceback.format_exc(),encoding='utf-8')
        messagebox.showerror('FMPresidente','Falha ao iniciar. Veja dados/falha-inicializacao.log na pasta do aplicativo.')
