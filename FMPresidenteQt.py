"""FMPresidente Qt Widgets — entrada incremental; Tkinter preservado."""
import sys,time,json,os
from pathlib import Path
from PySide6.QtCore import Qt,QObject,Signal,Slot,QRunnable,QThreadPool,QTimer,QAbstractTableModel,QSortFilterProxyModel
from PySide6.QtGui import QIcon,QPixmap,QImage
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QFormLayout,QLabel,QPushButton,QListWidget,QStackedWidget,QScrollArea,QLineEdit,QComboBox,QDoubleSpinBox,QSpinBox,QTableView,QHeaderView,QMessageBox,QFileDialog,QFrame,QCheckBox)
import fm23 as native
import sincronizacao_hibrida as sync
import negociacao
from taticas_local import CentralTatica
from aplicacao_qt import Session

STYLE='''
QWidget {background:#101719;color:#e8efeb;font-family:"Segoe UI";font-size:13px;}
QListWidget {background:#162124;border:0;padding:14px;outline:0;}
QListWidget::item {padding:13px;border-radius:6px;margin:3px;}
QListWidget::item:selected {background:#285547;color:#ffffff;}
QLabel#heading {font-size:26px;font-weight:600;}
QLabel#muted {color:#a7b8b1;}
QLabel#card {background:#1b292b;border:1px solid #30403f;border-radius:8px;padding:18px;font-size:20px;}
QPushButton {background:#263c36;border:1px solid #3b5b4f;border-radius:5px;padding:9px 15px;}
QPushButton:hover {background:#335448;}
QPushButton:focus {border:2px solid #97d2af;}
QPushButton:disabled {color:#7d8c85;background:#1d2825;border-color:#283930;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox {background:#1c292a;border:1px solid #3a4d45;border-radius:4px;padding:7px;}
QTableView {background:#172224;alternate-background-color:#1c292b;gridline-color:#293c35;border:1px solid #30443a;selection-background-color:#315e4c;}
QHeaderView::section {background:#23372f;padding:9px;border:0;}
QScrollArea {border:0;}
'''
def money(value):return '£ '+f'{value:,.0f}'.replace(',','.')
class Rows(QAbstractTableModel):
 def __init__(self,headers):super().__init__();self.headers=headers;self.rows=[]
 def rowCount(self,parent=None):return len(self.rows)
 def columnCount(self,parent=None):return len(self.headers)
 def data(self,index,role=Qt.DisplayRole):
  if role==Qt.DisplayRole and index.isValid():return str(self.rows[index.row()][index.column()])
 def headerData(self,section,orientation,role=Qt.DisplayRole):
  if role==Qt.DisplayRole and orientation==Qt.Horizontal:return self.headers[section]
 def update(self,rows):
  if rows==self.rows:return
  if len(rows)==len(self.rows):
   self.rows=rows
   if rows:self.dataChanged.emit(self.index(0,0),self.index(len(rows)-1,len(self.headers)-1))
  else:self.beginResetModel();self.rows=rows;self.endResetModel()
class Signals(QObject):
 finished=Signal(object,object)
class Task(QRunnable):
 def __init__(self,fn):super().__init__();self.fn=fn;self.signals=Signals()
 def run(self):
  try:result=self.fn();error=None
  except Exception as exc:result=None;error=str(exc)
  self.signals.finished.emit(result,error)
class Controller(QObject):
 changed=Signal(str,object)
 def __init__(self,session=None):
  super().__init__();self.service=session or Session();self.coordinator=sync.Coordinator();self.pool=QThreadPool(self);self.pool.setMaxThreadCount(1);self.busy=False;self.pending=None;self.closed=False;self.active=None
 def request_sync(self,query='',full=False):
  epoch=self.coordinator.begin();self.changed.emit('invalidate',None)
  if self.busy:self.pending=(query,full,epoch);self.changed.emit('status','Sincronização recebida. Aguardando a tarefa atual…');return
  self.start_sync(query,full,epoch)
 def start_sync(self,query,full,epoch):
  self.submit('sync',lambda:self.service.discover(query,full),epoch)
 def submit(self,kind,fn,epoch=None):
  if self.closed or self.busy:return False
  if epoch is None:epoch=self.coordinator.epoch
  self.busy=True;self.changed.emit('busy',True);self.changed.emit('status',{'sync':'Localizando o FM e consultando candidatos…','approve':'Revalidando o clube selecionado…','monitor':'Atualizando o contexto…'}.get(kind,'Processando…'))
  task=Task(fn);self.active=task;task.signals.finished.connect(lambda result,error:self.complete(kind,epoch,result,error),Qt.QueuedConnection);self.pool.start(task);return True
 @Slot()
 def complete(self,kind,epoch,result,error):
  self.busy=False;self.active=None
  if self.closed:return
  if kind in ('sync','approve'):
   observation=result[0] if result else None
   if self.coordinator.finish(epoch,observation,error):self.changed.emit('error' if error else kind,error or result)
  elif kind=='monitor':
   if self.coordinator.inspect(epoch,result[0] if result else None,error):
    if error or self.coordinator.state==sync.State.CONTEXT_CHANGED:self.changed.emit('invalidate',None);self.changed.emit('error',error or 'Contexto alterado. Sincronize novamente.')
    else:self.changed.emit('monitor',result)
  elif kind not in ('offer','offer_new') or epoch==self.coordinator.epoch:
   self.changed.emit('error' if error else kind,error or result)
  self.changed.emit('busy',self.busy)
  if self.pending and not self.busy:
   query,full,epoch=self.pending;self.pending=None;self.start_sync(query,full,epoch)
 def approve(self,candidate):
  if not self.busy:
   epoch=self.coordinator.begin();self.submit('approve',lambda:self.service.approve(candidate),epoch)
 def monitor(self):
  if not self.busy and not self.pending and self.coordinator.state==sync.State.OBSERVED_UNVERIFIED:
   self.submit('monitor',self.service.monitor,self.coordinator.epoch)
 def close(self):
  if self.busy:return False
  self.closed=True;self.coordinator.close();self.service.close();return True

class MainWindow(QMainWindow):
 def __init__(self,controller=None,auto=True):
  super().__init__();self.setWindowTitle('FMPresidente • Gestão do clube');self.resize(1280,820);self.setMinimumSize(850,580)
  self.setWindowIcon(QIcon(str(native.ROOT/'assets/FMPresidente.ico')))
  self.controller=controller or Controller();self.controller.changed.connect(self.on_result);self.snapshot=None;self.options=[];self.records=[];self.entries=[];self.write_buttons=[];self.pages={};self.proposal=None;self.catalog_rows=[];self.sponsor_session=None;self.uniform_generated=None
  shell=QWidget();self.setCentralWidget(shell);layout=QHBoxLayout(shell);layout.setContentsMargins(0,0,0,0)
  self.nav=QListWidget();self.nav.setFixedWidth(205);layout.addWidget(self.nav)
  content=QWidget();body=QVBoxLayout(content);body.setContentsMargins(24,20,24,20);layout.addWidget(content,1)
  self.club=QLabel('FMPresidente');self.club.setObjectName('heading');body.addWidget(self.club)
  self.connection=QLabel('Clube ainda não aprovado');self.connection.setObjectName('muted');body.addWidget(self.connection)
  top=QHBoxLayout();self.query=QLineEdit();self.query.setMinimumWidth(200);self.query.setPlaceholderText('Nome ou ID do clube');top.addWidget(self.query)
  self.candidates=QComboBox();self.candidates.setMinimumContentsLength(18);top.addWidget(self.candidates,1)
  self.button(top,'Sincronizar',lambda:self.controller.request_sync(self.query.text().strip()))
  self.button(top,'Aprovar seleção',self.approve);body.addLayout(top)
  self.feedback=QLabel('Sincronize com o FM23 para começar.');self.feedback.setWordWrap(True);body.addWidget(self.feedback)
  self.stack=QStackedWidget();body.addWidget(self.stack,1)
  self.dashboard();self.finances();self.sponsors();self.facilities();self.debts();self.kits();self.history();self.recovery();self.settings()
  self.stack.addWidget(CentralTatica());self.nav.addItem('Central Tática')
  self.nav.currentRowChanged.connect(self.stack.setCurrentIndex);self.nav.setCurrentRow(0)
  self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(20000)
  if auto:QTimer.singleShot(300,lambda:self.controller.request_sync())
 def page(self,title,description):
  inner=QWidget();v=QVBoxLayout(inner);v.setSpacing(16);heading=QLabel(title);heading.setObjectName('heading');v.addWidget(heading);text=QLabel(description);text.setWordWrap(True);text.setObjectName('muted');v.addWidget(text)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(inner);self.stack.addWidget(scroll);self.nav.addItem(title);self.pages[title]=inner;return v
 def button(self,layout,text,fn,write=False):
  b=QPushButton(text);b.clicked.connect(lambda checked=False:fn());layout.addWidget(b)
  if write:self.write_buttons.append(b);b.setEnabled(False)
  return b
 def number(self,layout,label,maximum=1000000000,decimals=0):
  row=QFormLayout();field=QDoubleSpinBox() if decimals else QSpinBox()
  if decimals:field.setDecimals(decimals)
  field.setRange(0,maximum);field.setGroupSeparatorShown(True);row.addRow(label,field);layout.addLayout(row);return field
 def table(self,layout,headers):
  model=Rows(headers);view=QTableView();view.setModel(model);view.setAlternatingRowColors(True);view.setSelectionBehavior(QTableView.SelectRows);view.setSelectionMode(QTableView.SingleSelection);view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);view.setMinimumHeight(170);layout.addWidget(view,1);return view,model
 def dashboard(self):
  v=self.page('Visão Geral','A presidência do clube, em um só lugar.');self.cards={}
  for key,label in [('balance','Caixa'),('transfer','Transferências'),('wage','Folha semanal'),('date','Data da carreira')]:
   card=QLabel(label+'\n—');card.setObjectName('card');v.addWidget(card);self.cards[key]=(label,card)
  self.overview=QLabel('Sem dados atuais.');self.overview.setWordWrap(True);v.addWidget(self.overview);v.addStretch()
 def finances(self):
  v=self.page('Finanças','Valores em libras (£). As operações usam as mesmas regras e validações da versão anterior.')
  self.capital=self.number(v,'Aporte da presidência (£)');self.capital.setValue(1000000)
  self.button(v,'Confirmar aporte',lambda:self.execute('capital',self.capital.value()),True)
  self.transfer=self.number(v,'Orçamento de transferências (£)');self.wage=self.number(v,'Folha semanal (£)',20000000)
  self.button(v,'Aplicar orçamentos',lambda:self.execute('budgets',self.transfer.value(),self.wage.value()),True)
  self.ticket=self.number(v,'Ingresso médio (£)',100000,4);self.season=self.number(v,'Carnê de temporada (£)',100000,2)
  self.button(v,'Aplicar bilheteria',lambda:self.execute('prices',self.ticket.value(),self.season.value()),True);v.addStretch()
 def sponsors(self):
  v=self.page('Patrocínios','Catálogo local, negociação e contratos ativos. As regras comerciais continuam no serviço negociacao.py e as escritas seguem os guards do FM.')
  bar=QHBoxLayout();self.sponsor_filter=QLineEdit();self.sponsor_filter.setPlaceholderText('Buscar marca ou setor');bar.addWidget(self.sponsor_filter)
  self.sponsor_slot=QComboBox();bar.addWidget(self.sponsor_slot,1);self.sponsor_start=QLineEdit();self.sponsor_start.setPlaceholderText('Início AAAA-MM-DD');bar.addWidget(self.sponsor_start)
  self.button(bar,'Atualizar catálogo',self.load_sponsor_catalog);self.button(bar,'Abrir mesa',self.begin_sponsor,True);v.addLayout(bar)
  self.sponsor_filter.textChanged.connect(self.load_sponsor_catalog)
  self.sponsor_catalog_view,self.sponsor_catalog_model=self.table(v,['Marca','Setor','Reputação','Investimento'])
  self.sponsor_catalog_view.clicked.connect(lambda _:self.show_sponsor_selection())
  self.sponsor_info=QLabel('Sincronize e aprove um clube para consultar as receitas comerciais.');self.sponsor_info.setWordWrap(True);v.addWidget(self.sponsor_info)
  self.sponsor_offer=QLabel('Nenhuma mesa selecionada.');self.sponsor_offer.setWordWrap(True);v.addWidget(self.sponsor_offer)
  form=QHBoxLayout();self.sponsor_annual=self.number(form,'Valor anual (£)',500000000);self.sponsor_years=self.number(form,'Anos',5);self.sponsor_years.setRange(1,5);self.sponsor_penalty=self.number(form,'Multa (%)',100);self.sponsor_penalty.setValue(20);self.sponsor_exclusive=QCheckBox('Exclusividade');self.sponsor_renewal=QCheckBox('Preferência de renovação');form.addWidget(self.sponsor_exclusive);form.addWidget(self.sponsor_renewal);v.addLayout(form)
  actions=QHBoxLayout();self.button(actions,'Enviar contraproposta',self.counter_sponsor,True);self.button(actions,'Assinar proposta',self.sign_sponsor,True);self.button(actions,'Desistir da mesa',self.withdraw_sponsor);v.addLayout(actions)
  self.sponsor_view,self.sponsor_model=self.table(v,['Receita','Empresa','Total (£)','Vigência','Estado']);self.sponsor_view.clicked.connect(lambda _:self.show_contract())
  self.sponsor_contract=QLabel('Selecione um contrato para consultar cláusulas.');self.sponsor_contract.setWordWrap(True);v.addWidget(self.sponsor_contract)
  self.button(v,'Rescindir contrato selecionado',self.terminate_sponsor,True);v.addStretch()
 def facilities(self):
  v=self.page('Infraestrutura','Cada investimento sobe um nível e desconta o custo do caixa. Limite nativo: 20.')
  self.levels={}
  for name in native.FACILITIES:
   label=QLabel(name+' —');self.levels[name]=label;v.addWidget(label)
   self.button(v,'Investir em '+name,lambda name=name:self.execute('invest',name),True)
  v.addStretch()
 def debts(self):
  v=self.page('Empréstimos','Contrate crédito para o clube e administre os contratos existentes. A reserva nativa é revalidada antes de cada contratação.')
  self.debt_view,self.debt_model=self.table(v,['Contrato','Saldo original (£)','Parcela (£)','Juros (£)','Fim'])
  self.loan_contract_status=QLabel('Contratar empréstimo — sincronize e aprove um clube.');self.loan_contract_status.setWordWrap(True);self.loan_contract_status.setObjectName('muted');v.addWidget(self.loan_contract_status)
  self.principal=self.number(v,'Novo valor (£)',100000000);self.principal.setValue(1000000)
  self.loan_contract_button=self.button(v,'Contratar novo empréstimo',self.contract_loan,False);self.loan_contract_button.setEnabled(False)
  self.months=self.number(v,'Novo prazo (meses)',120);self.months.setMinimum(1);self.months.setValue(24);self.rate=self.number(v,'Taxa anual proposta (%)',100,2);self.rate.setValue(12)
  self.button(v,'Consultar renegociação',self.offer,True);self.button(v,'Quitar dívida selecionada',self.repay,True)
 def kits(self):
  v=self.page('Uniformes','Prévia, geração e instalação usam as rotinas Pillow/XML existentes. A alteração da flag nativa permanece uma operação separada e confirmada.')
  self.kit_status=QLabel('Modo indisponível');v.addWidget(self.kit_status)
  self.kit_brand=QComboBox();v.addWidget(self.kit_brand)
  kit_actions=QHBoxLayout();self.button(kit_actions,'Pré-visualizar camisa',self.preview_kit);self.button(kit_actions,'Gerar arquivos',self.generate_kits,True);self.button(kit_actions,'Instalar arquivos',self.install_kits,True);v.addLayout(kit_actions)
  self.kit_preview=QLabel('Nenhuma prévia gerada.');self.kit_preview.setMinimumSize(280,280);self.kit_preview.setAlignment(Qt.AlignCenter);v.addWidget(self.kit_preview)
  self.kit_result=QLabel('Arquivos gerados em diretório preparado aparecerão aqui.');self.kit_result.setWordWrap(True);v.addWidget(self.kit_result)
  self.button(v,'Usar estilo do editor',lambda:self.execute('set_licensed_kits',False,self.snapshot['date']),True)
  self.button(v,'Usar imagens licenciadas',lambda:self.execute('set_licensed_kits',True,self.snapshot['date']),True);v.addStretch()
 def history(self):
  v=self.page('Histórico','O desfazer continua sujeito à sessão, data, propriedade dos campos e estado da operação original.')
  self.history_view,self.history_model=self.table(v,['Data/hora','Operação','Resultado'])
  self.history_filter=QLineEdit();self.history_filter.setPlaceholderText('Filtrar histórico');v.insertWidget(2,self.history_filter)
  self.history_proxy=QSortFilterProxyModel(self);self.history_proxy.setSourceModel(self.history_model);self.history_proxy.setFilterKeyColumn(-1);self.history_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive);self.history_view.setModel(self.history_proxy);self.history_filter.textChanged.connect(self.history_proxy.setFilterFixedString)
  self.button(v,'Atualizar histórico',lambda:self.controller.submit('history',self.controller.service.history))
  self.button(v,'Desfazer selecionada',self.undo,True)
 def recovery(self):
  v=self.page('Recuperação','Consulta disponível sem conexão. Não repita operações incertas. Preserve o histórico e verifique a carreira e seus backups.')
  self.recovery_view,self.recovery_model=self.table(v,['Data','Operação','Estado','Recurso'])
  self.recovery_detail=QLabel('Selecione um registro para consultar as orientações.');self.recovery_detail.setWordWrap(True);v.addWidget(self.recovery_detail)
  self.recovery_view.clicked.connect(self.show_recovery)
  self.button(v,'Atualizar diagnóstico',lambda:self.controller.submit('recovery',self.controller.service.diagnostics))
  self.button(v,'Exportar diagnóstico',self.export)
 def settings(self):
  v=self.page('Configurações','A interface Qt está em migração. A versão Tkinter continua sendo a principal até a conclusão da paridade funcional.')
  self.button(v,'Abrir pasta do aplicativo',lambda:os.startfile(native.ROOT))
  self.button(v,'Criar backup do último save local',lambda:self.controller.submit('backup',native.backup_save));v.addStretch()
 def load_sponsor_catalog(self):
  if not self.snapshot:return
  self.catalog_rows=self.controller.service.catalog(self.sponsor_filter.text())
  self.sponsor_catalog_model.update([(c['name'],c.get('sector','Outros'),str(c.get('reputation','—'))+'/100',str(c.get('investment','—'))+'/100') for c in self.catalog_rows])
  self.sponsor_slot.clear()
  for row in self.snapshot.get('sponsors',[]):
   if row.get('kind') in negociacao.COMMERCIAL:self.sponsor_slot.addItem(f"{row['name']} • {money(row['total'])} • {row['start']} a {row['end']}",row['index'])
 def show_sponsor_selection(self):
  i=self.sponsor_catalog_view.currentIndex().row()
  if 0<=i<len(self.catalog_rows):
   c=self.catalog_rows[i];self.sponsor_info.setText(f"{c['name']} • {c.get('sector','Outros')}\nReputação: {c.get('reputation','—')}/100 • Investimento: {c.get('investment','—')}")
 def begin_sponsor(self):
  if not self.snapshot or self.controller.busy:return
  i=self.sponsor_catalog_view.currentIndex().row();row=self.sponsor_slot.currentData()
  if not (0<=i<len(self.catalog_rows)) or row is None:self.on_result('error','Selecione uma marca e uma receita comercial.');return
  start=self.sponsor_start.text().strip() or self.snapshot['date']
  company=self.catalog_rows[i]
  self.controller.submit('sponsor_begin',lambda:self.controller.service.sponsor_begin(company['id'],row,start))
 def current_terms(self):
  if not self.sponsor_session:raise ValueError('Abra uma mesa de negociação.')
  return {'annual':int(self.sponsor_annual.value()),'years':int(self.sponsor_years.value()),'start':self.sponsor_session['offer']['start'],'exclusive':self.sponsor_exclusive.isChecked(),'renewal':self.sponsor_renewal.isChecked(),'penalty':int(self.sponsor_penalty.value())}
 def counter_sponsor(self):
  try:terms=self.current_terms()
  except ValueError as exc:self.on_result('error',str(exc));return
  self.controller.submit('sponsor_counter',lambda:self.controller.service.sponsor_counter(self.sponsor_session['id'],terms,()))
 def sign_sponsor(self):
  if not self.sponsor_session:self.on_result('error','Abra uma mesa antes de assinar.');return
  if QMessageBox.question(self,'Assinar patrocínio','Aplicar a proposta ao clube aprovado? O resultado será persistido pelo serviço e a carreira deve ser salva no FM.')==QMessageBox.Yes:
   self.controller.submit('sponsor_sign',lambda:self.controller.service.sponsor_sign(self.sponsor_session['id']))
 def withdraw_sponsor(self):
  if self.sponsor_session:self.controller.submit('sponsor_withdraw',lambda:self.controller.service.sponsor_withdraw(self.sponsor_session['id']))
 def show_contract(self):
  i=self.sponsor_view.currentIndex().row()
  if self.snapshot and 0<=i<len(self.snapshot['sponsors']):
   row=self.snapshot['sponsors'][i];deal=next((c for c in reversed(self.controller.service.store.get('brands',[])) if c.get('kind')==row.get('kind') and c.get('start')==row.get('start') and c.get('end')==row.get('end') and c.get('total')==row.get('total')),None)
   self.sponsor_contract.setText((f"{deal['company']['name']} • {'Vigente' if row['total'] else 'Rescindido'}\nMulta estimada hoje: {money(negociacao.remaining_penalty(deal,self.snapshot['date']))}" if deal else 'Receita nativa sem cláusulas comerciais cadastradas no FMPresidente.'))
 def terminate_sponsor(self):
  i=self.sponsor_view.currentIndex().row()
  if not self.snapshot or not 0<=i<len(self.snapshot['sponsors']):self.on_result('error','Selecione um contrato.');return
  row=self.snapshot['sponsors'][i]
  if QMessageBox.question(self,'Rescindir patrocínio','Zerar a receita no FM e debitar a multa cadastrada?')==QMessageBox.Yes:self.controller.submit('sponsor_terminate',lambda:self.controller.service.sponsor_terminate(row['index']))
 def selected_brand_id(self):
  return self.kit_brand.currentData() if self.kit_brand.currentIndex()>=0 else None
 def preview_kit(self):
  if not self.snapshot:self.on_result('error','Aprove um clube antes de gerar a prévia.');return
  self.controller.submit('uniform_preview',lambda:self.controller.service.uniform_preview(self.selected_brand_id()))
 def generate_kits(self):
  if not self.snapshot:self.on_result('error','Aprove um clube antes de gerar arquivos.');return
  self.controller.submit('uniform_generate',lambda:self.controller.service.uniform_generate(self.selected_brand_id()))
 def install_kits(self):
  if not self.uniform_generated:self.on_result('error','Gere os arquivos antes de instalar.');return
  if QMessageBox.question(self,'Instalar uniformes','Substituir os arquivos preparados na pasta de gráficos do FM? Um backup local será criado quando houver arquivos anteriores.')==QMessageBox.Yes:
   item=self.uniform_generated;self.controller.submit('uniform_install',lambda:self.controller.service.uniform_install(item['folder'],item['signature']))
 def approve(self):
  i=self.candidates.currentIndex()
  if not 0<=i<len(self.options) or self.controller.busy:return
  c=self.options[i]
  if QMessageBox.question(self,'Aprovar clube',f'Administrar {c.club.name} (ID {c.club.uid}) nesta sessão? A identidade nativa do save não foi comprovada.')==QMessageBox.Yes:self.controller.approve(c)
 def execute(self,method,*args):
  if not self.snapshot or self.controller.busy:return
  labels={'capital':'Aporte: '+money(args[0]) if method=='capital' else '', 'budgets':'Atualizar orçamentos','prices':'Atualizar preços de bilheteria','invest':'Investir na infraestrutura','repay':'Quitar dívida selecionada','set_licensed_kits':'Alterar modo do uniforme','undo':'Desfazer operação selecionada'}
  if method=='budgets':labels[method]=f'Transferências: {money(args[0])}\nFolha semanal: {money(args[1])}'
  if method=='prices':labels[method]=f'Ingresso: £ {args[0]:.4f}\nCarnê: £ {args[1]:.2f}'
  if method=='invest':
   name=args[0];level=self.snapshot['facilities'][name];labels[method]=f'{name}: nível {level} → {level+1}\nCusto: {money(native.LEVEL_COST[name]*(level+1))}'
  if QMessageBox.question(self,'Confirmar operação',f"{labels.get(method,method)}\nAplicar no clube aprovado?\nSalve a carreira no FM para persistir.")==QMessageBox.Yes:
   self.controller.submit('applied',lambda:self.controller.service.execute(method,*args))
 def selected_debt(self):
  i=self.debt_view.currentIndex().row()
  if not self.snapshot or not 0<=i<len(self.snapshot['debts']):raise ValueError('Selecione uma dívida.')
  return self.snapshot['debts'][i]
 def offer(self):
  try:row=self.selected_debt()
  except ValueError as exc:self.on_result('error',str(exc));return
  index=row['index'];months=self.months.value();rate=self.rate.value();self.controller.submit('offer',lambda:self.controller.service.debt_offer(index,months,rate))
 def contract_loan(self):
  if not self.snapshot or self.controller.busy:return
  self.controller.submit('offer_new',lambda:self.controller.service.loan_contract_offer(self.principal.value(),self.months.value(),self.rate.value()))
 def repay(self):
  try:row=self.selected_debt()
  except ValueError as exc:self.on_result('error',str(exc));return
  self.execute('repay',row['index'],row['raw'])
 def undo(self):
  i=self.history_proxy.mapToSource(self.history_view.currentIndex()).row()
  if 0<=i<len(self.entries):self.execute('undo',self.entries[i])
 def show_recovery(self,index):
  if 0<=index.row()<len(self.records):
   r=self.records[index.row()];self.recovery_detail.setText(f'ID: {r.operation_id or "não identificado"}\n{r.reason}\nPara estado incerto, não repita a operação. Preserve o histórico e verifique uma cópia de backup.')
 def export(self):
  path,_=QFileDialog.getSaveFileName(self,'Exportar diagnóstico','','JSON (*.json)')
  if path:
   records=list(self.records);self.controller.submit('export',lambda:self.controller.service.export(path,records))
 def poll(self):
  if self.snapshot:self.controller.monitor()
 def on_result(self,kind,result):
  if kind=='busy':
   for button in self.write_buttons:button.setEnabled(bool(self.snapshot) and not result)
  elif kind=='status':self.feedback.setText(result)
  elif kind=='invalidate':
   self.snapshot=None;self.connection.setText('Contexto não aprovado. Sincronização solicitada.');self.club.setText('FMPresidente')
   if getattr(self,'loan_contract_button',None):self.loan_contract_button.setEnabled(False);self.loan_contract_status.setText('Contratar empréstimo — sincronize e aprove um clube.')
   self.options=[];self.candidates.clear()
   for label,card in self.cards.values():card.setText(label+'\n—')
   for b in self.write_buttons:b.setEnabled(False)
   self.sponsor_model.update([]);self.debt_model.update([])
  elif kind=='sync':
   observation,(self.options,limited)=result;self.candidates.clear()
   for c in self.options:self.candidates.addItem(f'{c.club.name} • ID {c.club.uid} • {c.source}')
   self.connection.setText('FM23 identificado • clube ainda não aprovado')
   self.feedback.setText(f'{len(self.options)} candidato(s) disponíveis. Selecione e aprove o clube.' if self.options else 'Nenhum candidato nesta busca. Verifique a carreira aberta e tente novamente.')
  elif kind=='approve':self.update_snapshot(result[1],True);self.feedback.setText('Clube aprovado manualmente para esta sessão.')
  elif kind=='monitor':self.update_snapshot(result[1]);self.feedback.setText('Dados atualizados. Contexto aprovado para esta sessão.')
  elif kind=='applied':
   self.update_snapshot(result['snapshot'])
   self.feedback.setText('Aplicado na memória. Salve a carreira no FM para persistir.' if not result['snapshot_error'] else 'Operação aplicada, mas não foi possível atualizar a leitura. Não repita. Consulte Recuperação.')
  elif kind=='offer':
   self.proposal=result
   if QMessageBox.question(self,'Renegociação',f"{result['months']} parcelas de {money(result['monthly'])}\nTaxa anual: {result['rate']}%\nTotal: {money(result['total'])}\nConfirmar estas condições?")==QMessageBox.Yes:
    proposal=dict(result);self.controller.submit('applied',lambda:self.controller.service.debt_sign(proposal))
  elif kind=='offer_new':
   self.proposal=result
   if QMessageBox.question(self,'Contratar empréstimo',f"{result['months']} parcelas de {money(result['monthly'])}\nTaxa anual: {result['rate']}%\nTotal: {money(result['total'])}\nCrédito no caixa: {money(result['principal'])}\n\nAplicar nesta sessão? Salve a carreira no FM para persistir.")==QMessageBox.Yes:
    proposal=dict(result);self.controller.submit('applied',lambda:self.controller.service.debt_sign(proposal))
  elif kind=='sponsor_begin':
   self.sponsor_session=result;self.sponsor_annual.setValue(result['offer']['annual']);self.sponsor_years.setValue(result['offer']['years']);self.sponsor_penalty.setValue(result['offer']['penalty']);self.sponsor_exclusive.setChecked(result['offer']['exclusive']);self.sponsor_renewal.setChecked(result['offer']['renewal']);self.sponsor_offer.setText(f"Mesa aberta: {result['company']['name']} • oferta {money(result['offer']['annual'])}/ano • {result['offer']['years']} ano(s) • estado {negociacao.STATES[result['status']]}");self.feedback.setText('Mesa de negociação aberta.')
  elif kind=='sponsor_counter':
   self.sponsor_session=result;self.sponsor_annual.setValue(result['offer']['annual']);self.sponsor_years.setValue(result['offer']['years']);self.sponsor_penalty.setValue(result['offer']['penalty']);self.sponsor_exclusive.setChecked(result['offer']['exclusive']);self.sponsor_renewal.setChecked(result['offer']['renewal']);self.sponsor_offer.setText(f"{result['company']['name']} respondeu: {money(result['offer']['annual'])}/ano • {result['offer']['years']} ano(s) • estado {negociacao.STATES[result['status']]}");self.feedback.setText('Contraproposta registrada localmente.')
  elif kind=='sponsor_withdraw':
   self.sponsor_session=result;self.sponsor_offer.setText('Mesa encerrada pelo clube.');self.feedback.setText('Negociação encerrada sem escrever no FM.')
  elif kind=='sponsor_sign':
   self.sponsor_session=result.get('session');self.update_snapshot(result.get('snapshot'));self.feedback.setText('Patrocínio aplicado, journal finalizado e leitura atualizada.');self.load_sponsor_catalog()
  elif kind=='sponsor_terminate':
   self.update_snapshot(result.get('snapshot'));self.feedback.setText(f"Contrato rescindido. Multa debitada: {money(result.get('fee',0))}.");self.load_sponsor_catalog()
  elif kind=='uniform_preview':
   image=result.convert('RGBA');raw=image.tobytes('raw','RGBA');qimage=QImage(raw,image.width,image.height,QImage.Format_RGBA8888);self.kit_preview.setPixmap(QPixmap.fromImage(qimage.copy()).scaled(300,300,Qt.KeepAspectRatio,Qt.SmoothTransformation));self.feedback.setText('Prévia gerada sem alterar arquivos do FM.')
  elif kind=='uniform_generate':
   self.uniform_generated=result;self.kit_result.setText(f"Arquivos gerados para {result['company']} em:\n{result['folder']}\nVerifique antes de instalar.");self.feedback.setText('Uniformes gerados em área preparada.')
  elif kind=='uniform_install':
   self.kit_result.setText(f"Arquivos instalados em {result['folder']}. Backup anterior preservado pelo serviço.");self.feedback.setText('Instalação concluída e conferida.')
  elif kind=='history':self.entries=result;self.history_model.update([(r.get('time','')[:19],r.get('title',''),r.get('status','')) for r in result])
  elif kind=='recovery':self.records=result;self.recovery_model.update([(r.time[:19],r.title,r.state,r.resource) for r in result]);self.feedback.setText('Diagnóstico atualizado. Nenhuma alteração no FM.')
  elif kind in ('export','backup'):self.feedback.setText('Arquivo salvo com sucesso.')
  elif kind=='error':
   self.feedback.setText(str(result))
   if self.controller.service.snapshot is None:self.on_result('invalidate',None)
  if kind!='busy':
   for button in self.write_buttons:button.setEnabled(bool(self.snapshot) and not self.controller.busy)
 def update_snapshot(self,snapshot,inputs=False):
  if snapshot is None:
   self.on_result('invalidate',None);return
  if snapshot==self.snapshot and not inputs:return
  self.snapshot=snapshot;name=self.options[self.candidates.currentIndex()].club.name if self.options and self.candidates.currentIndex()>=0 else snapshot['club']
  self.club.setText(name);self.connection.setText('Clube aprovado manualmente • identidade nativa da carreira não comprovada')
  for key,(label,card) in self.cards.items():
   value=snapshot[key] if key=='date' else money(snapshot[key]);card.setText(label+'\n'+value)
   if key=='balance':card.setStyleSheet('color:'+('#f28b82' if snapshot[key]<0 else '#90d5ae'))
  self.overview.setText(f"{len(snapshot['sponsors'])} receitas de patrocínio • {len(snapshot['debts'])} dívidas registradas")
  if inputs:
   for field,key in [(self.transfer,'transfer'),(self.wage,'wage'),(self.ticket,'ticket'),(self.season,'season_ticket')]:field.setValue(snapshot[key])
  for name,label in self.levels.items():
   level=snapshot['facilities'][name];label.setText(f'{name}: {level}/20 • '+('Máximo atingido' if level>=20 else 'Próximo nível: '+money(native.LEVEL_COST[name]*(level+1))))
   self.sponsor_model.update([(r['name'],(next((c.get('company',{}).get('name','') for c in reversed(self.controller.service.store.get('brands',[])) if c.get('kind')==r.get('kind') and c.get('start')==r.get('start') and c.get('end')==r.get('end') and c.get('total')==r.get('total')),'—')),money(r['total']),r['start']+' — '+r['end'],('Ativo' if r['total'] else 'Encerrado')) for r in snapshot['sponsors']])
   self.load_sponsor_catalog()
   self.kit_brand.clear()
   for company in self.controller.service.companies:self.kit_brand.addItem(company.get('name',''),company.get('id'))
  self.debt_model.update([(r['index']+1,money(r['original']),money(r['monthly']),money(r['interest']),r['end']) for r in snapshot['debts']])
  self.update_loan_status()
  self.kit_status.setText('Modo atual: '+('imagens licenciadas' if snapshot.get('licensed_kits') else 'estilo do editor'))
 def update_loan_status(self):
  if not getattr(self,'loan_contract_button',None):return
  if not self.snapshot or not self.controller.service.fm:
   self.loan_contract_status.setText('Contratar empréstimo — sincronize e aprove um clube.')
   self.loan_contract_button.setEnabled(False);return
  status=self.controller.service.loan_contract_status()
  prefix='disponível' if status['available'] else 'indisponível'
  self.loan_contract_status.setText(f'Contratar empréstimo — {prefix}.\n'+status['reason'])
  self.loan_contract_button.setEnabled(bool(status['available']) and not self.controller.busy)
 def closeEvent(self,event):
  if not self.controller.close():self.feedback.setText('Aguarde a tarefa terminar para fechar com segurança.');event.ignore()
  else:self.timer.stop();event.accept()

def main():
 app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
 if '--sync-self-check' in sys.argv:
  try:
   observation,(options,limited)=Session().discover();native.save_json(native.ROOT/'dados/autoteste-qt-sync.json',{'ok':True,'build':observation.process[2],'candidates':len(options),'limited':limited});return 0
  except Exception as error:
   native.save_json(native.ROOT/'dados/autoteste-qt-sync.json',{'ok':False,'error':str(error)});return 1
 if '--self-check' in sys.argv:
  window=MainWindow(auto=False);window.show();app.processEvents();assert window.stack.count()==10;window.close();native.save_json(native.ROOT/'dados/autoteste-qt.json',{'ok':True,'qt':True});return 0
 native.k.CreateMutexW.argtypes=[native.C.c_void_p,native.W.BOOL,native.W.LPCWSTR];native.k.CreateMutexW.restype=native.W.HANDLE
 mutex=native.k.CreateMutexW(None,False,'Local\\FMPresidenteFM23')
 if native.C.get_last_error()==183:
  native.k.CloseHandle(mutex);QMessageBox.information(None,'FMPresidente','Feche a outra janela do FMPresidente antes de iniciar a versão Qt.');return 0
 try:
  window=MainWindow();window.show();return app.exec()
 finally:
  if mutex:native.k.CloseHandle(mutex)
if __name__=='__main__':sys.exit(main())
