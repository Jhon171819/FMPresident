"""Contratação, contraproposta, renegociação e quitação de crédito do clube."""
from copy import deepcopy
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

import emprestimos as engine


def money(value):
    return '£ ' + f'{value:,.0f}'.replace(',', '.')


def day(value):
    return date.fromisoformat(value).strftime('%d/%m/%Y')


class LoansPanel:
    def __init__(self, app, parent):
        self.app = app
        self.snapshot = None
        self.forms = {}
        self.selected = None
        self.book = ttk.Notebook(parent)
        self.book.pack(fill='both', expand=True)
        new = ttk.Frame(self.book, padding=10)
        current = ttk.Frame(self.book, padding=10)
        self.book.add(new, text='Contratar empréstimo')
        self.book.add(current, text='Contratos e renegociação')
        app.label(new, 'Crédito para o clube', font=('Segoe UI', 17, 'bold'))
        app.label(new, 'Negocie valor, taxa anual e prazo. Ao assinar, o dinheiro entra no caixa e o contrato aparece no FM.', wraplength=1000)
        self.form(new, 'new')
        app.label(new, 'As propostas são regras do FMPresidente. O FM administra os pagamentos mensais do contrato registrado.', style='Muted.TLabel', wraplength=1000)
        self.tree = app.table(current, [('principal','Principal original',140),('monthly','Parcela mensal',130),('interest','Juros na parcela',130),('end','Último pagamento',140),('type','Modalidade',180)], 4)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        row = ttk.Frame(current)
        row.pack(fill='x')
        self.pay_button = app.button(row, 'Quitar saldo da dívida', self.pay, True)
        self.selected_info = tk.StringVar(value='Selecione um contrato para renegociar ou quitar.')
        app.label(current, '', textvariable=self.selected_info, style='Muted.TLabel', wraplength=1000)
        self.form(current, 'refinance')
        app.label(current, 'Renegociar troca taxa e prazo do saldo remanescente. A quitação antecipada desconta esse saldo do caixa.', style='Muted.TLabel', wraplength=1000)

    def form(self, parent, key):
        f = dict(principal=tk.StringVar(value='1.000.000' if key == 'new' else ''),
                 months=tk.StringVar(value='24'), rate=tk.StringVar(), proposal=None)
        self.forms[key] = f
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=8)
        for name, title, width in [('principal','Valor (£)' if key=='new' else 'Saldo a renegociar (£)',20), ('months','Parcelas mensais',9), ('rate','Taxa anual desejada (%)',12)]:
            field = ttk.Frame(row)
            field.pack(side='left', padx=(0,20))
            ttk.Label(field, text=title).pack(anchor='w', pady=(0,4))
            ttk.Entry(field, textvariable=f[name], width=width, state='readonly' if key=='refinance' and name=='principal' else 'normal').pack(anchor='w')
            f[name].trace_add('write', lambda *_, k=key: self.invalidate(k))
        buttons = ttk.Frame(parent)
        buttons.pack(fill='x')
        f['request'] = self.app.button(buttons, 'Solicitar / negociar condições', lambda: self.request(key), True)
        f['sign'] = self.app.button(buttons, 'Aceitar e contratar no FM' if key=='new' else 'Aceitar e renegociar no FM', lambda: self.sign(key), True)
        f['details'] = tk.StringVar(value='Deixe a taxa em branco para receber a proposta inicial.')
        self.app.label(parent, '', textvariable=f['details'], wraplength=1000)

    def invalidate(self, key):
        f = self.forms[key]
        f['proposal'] = None
        if 'sign' in f:
            f['sign'].state(['disabled'])
        if 'details' in f:
            f['details'].set('Solicite as condições para conferir a parcela, o custo total e as datas.')

    def selected_row(self):
        choice = self.tree.selection()
        if not self.snapshot or not choice:
            raise ValueError('Selecione um empréstimo na lista.')
        return next(r for r in self.snapshot['debts'] if str(r['index']) == choice[0])

    def select(self, _=None):
        try:
            row = self.selected_row()
            self.selected = row['raw']
            amount = engine.outstanding(row, date.fromisoformat(self.snapshot['date']))
            self.forms['refinance']['principal'].set(f'{amount:,}'.replace(',', '.'))
            self.selected_info.set(f'Saldo para quitação ou renegociação: {money(amount)}. Escolha o novo prazo e a taxa desejada.')
        except (ValueError, StopIteration) as exc:
            self.selected = None
            self.forms['refinance']['principal'].set('')
            self.selected_info.set(str(exc) or 'Selecione um contrato vigente.')
        self.set_enabled(self.app.fm is not None and not self.app.busy)

    def refresh(self, snapshot, inputs=False):
        previous = self.snapshot['date'] if self.snapshot else None
        self.snapshot = snapshot
        if previous != snapshot['date'] or inputs:
            for key in self.forms:
                self.invalidate(key)
        self.app.replace_rows(self.tree, [(str(r['index']), (money(r['original']),money(r['monthly']),money(r['interest']),day(r['end']),'Somente juros' if r['interest_only'] else 'Parcelas fixas')) for r in snapshot['debts']])
        if self.tree.selection():
            try:
                if self.selected_row()['raw'] != self.selected or inputs:
                    self.select()
            except (ValueError, StopIteration):
                self.selected = None
        self.set_enabled(not self.app.busy)

    def set_enabled(self, enabled):
        for key, f in self.forms.items():
            active = enabled and self.snapshot is not None and (key=='new' or self.selected is not None)
            f['request'].state(['!disabled'] if active else ['disabled'])
            f['sign'].state(['!disabled'] if active and f['proposal'] is not None else ['disabled'])
        self.pay_button.state(['!disabled'] if enabled and self.selected else ['disabled'])

    def request(self, key):
        def prepare():
            if self.app.busy or not self.snapshot:
                raise ValueError('Conecte à carreira e aguarde a atualização.')
            f = self.forms[key]
            text = f['principal'].get().strip().replace('£','').replace('.','').replace(' ','')
            if not text.isdecimal():
                raise ValueError('Informe o valor inteiro do empréstimo.')
            rate = f['rate'].get().strip().replace(',','.')
            proposal = engine.offer(self.snapshot, int(text), int(f['months'].get()), float(rate) if rate else None,
                                    self.selected_row() if key=='refinance' else None)
            f['proposal'] = proposal
            response = 'Contraproposta: a menor taxa disponível é' if proposal['counter'] else 'Condições aprovadas: taxa anual de'
            f['details'].set(f"{response} {proposal['rate']:.2f}%.\n"
                f"{proposal['months']} parcelas de {money(proposal['monthly'])} • Total: {money(proposal['total'])}\n"
                f"Primeiro pagamento: {day(proposal['first'])} • Último: {day(proposal['end'])}")
            self.set_enabled(True)
        self.app.guard(prepare)

    def sign(self, key):
        def prepare():
            proposal = self.forms[key]['proposal']
            if proposal is None:
                raise ValueError('Solicite as condições antes de assinar.')
            proposal = deepcopy(proposal)
            operation = 'Contratar' if key=='new' else 'Renegociar'
            effect = f"Crédito no caixa: {money(proposal['principal'])}." if key=='new' else 'O contrato existente será substituído pelas novas condições, sem novo crédito no caixa.'
            summary = (f"{operation} {money(proposal['principal'])} a {proposal['rate']:.2f}% ao ano?\n\n"
                f"{proposal['months']} parcelas de {money(proposal['monthly'])}.\nTotal: {money(proposal['total'])}.\n"
                f"Primeiro pagamento: {day(proposal['first'])}.\nÚltimo pagamento: {day(proposal['end'])}.\n\n{effect}")
            if messagebox.askyesno(operation+' empréstimo financeiro', summary, parent=self.app):
                self.app.apply(lambda: engine.sign(self.app.fm, proposal))
        self.app.guard(prepare)

    def pay(self):
        def prepare():
            row = self.selected_row()
            cost = engine.outstanding(row, date.fromisoformat(self.snapshot['date']))
            if messagebox.askyesno('Quitar empréstimo', f'Descontar {money(cost)} do caixa e encerrar esta dívida?', parent=self.app):
                self.app.apply(lambda: self.app.fm.repay(row['index'], row['raw']))
        self.app.guard(prepare)
