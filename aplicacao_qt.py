"""Serviços da interface Qt, sem dependência do framework gráfico."""
from datetime import date
from pathlib import Path
import hashlib
import json
import fm23 as native
import sincronizacao_hibrida as sync
import emprestimos
import negociacao
import recuperacao
import uniformes
class Session:
 def __init__(self):
  self.fm=None;self.snapshot=None
  self.manual_state=native.ROOT/'dados/negociacoes-manuais.json'
  self.state=native.read_json(self.manual_state,{'version':1,'sessions':[]})
  self.sessions=self.state.setdefault('sessions',[])
  self.store=native.read_json(native.ROOT/'dados/presidencia.json',{'brands':[],'custom':[],'quotes':{},'installed':None})
  imported=native.read_json(native.ROOT/'assets/patrocinadores.json',[])
  known={c.get('name','').casefold() for c in imported}
  for company in self.store.get('custom',[]):
   if company.get('name','').casefold() not in known:
    imported.append(dict(company,id='local-'+hashlib.sha256(company['name'].encode()).hexdigest()[:12],sector=company.get('sector','Outros'),reputation=75,investment=75));known.add(company['name'].casefold())
  self.companies=imported
 def close(self):
  if self.fm:self.fm.close()
  self.fm=None;self.snapshot=None
 def _save_sessions(self):
  native.save_json(self.manual_state,self.state)
 def catalog(self,query=''):
  query=(query or '').casefold().strip()
  return [c for c in self.companies if not query or query in (c.get('name','')+' '+c.get('sector','')).casefold()]
 def sponsor_slots(self):
  if not self.snapshot:raise ValueError('Conecte ao clube antes de consultar o catálogo.')
  return [r for r in self.snapshot.get('sponsors',[]) if r.get('kind') in negociacao.COMMERCIAL]
 def _session(self,session_id):
  return next((s for s in self.sessions if s.get('id')==session_id),None)
 def sponsor_begin(self,company_id,row_index,start):
  if not self.snapshot:raise ValueError('Conecte ao clube antes de abrir uma negociação.')
  company=next((c for c in self.companies if c.get('id')==company_id),None)
  row=next((r for r in self.sponsor_slots() if r.get('index')==int(row_index)),None)
  if not company or not row:raise ValueError('Selecione uma marca e uma receita comercial.')
  start=date.fromisoformat(start).isoformat()
  session=negociacao.begin(company,row,self.snapshot,start,self.sessions)
  self.sessions.append(session);self._save_sessions();return session
 def sponsor_counter(self,session_id,terms,locks=()):
  session=self._session(session_id)
  if not session or not self.snapshot:raise ValueError('Selecione uma mesa de negociação ativa.')
  updated=negociacao.counter(session,terms,locks,self.snapshot['date'])
  self.sessions[:]=[updated if item.get('id')==session_id else item for item in self.sessions];self._save_sessions();return updated
 def sponsor_withdraw(self,session_id):
  session=self._session(session_id)
  if not session or not self.snapshot:raise ValueError('Selecione uma mesa de negociação ativa.')
  updated=negociacao.withdraw(session,self.snapshot['date']);self.sessions[:]=[updated if item.get('id')==session_id else item for item in self.sessions];self._save_sessions();return updated
 def sponsor_sign(self,session_id):
  if not self.fm or not self.snapshot:raise ValueError('Conecte e aprove um clube antes de assinar.')
  session=self._session(session_id)
  if not session:raise ValueError('Mesa de negociação não encontrada.')
  row=next((r for r in self.snapshot['sponsors'] if r['raw']==session['row']['raw'] and r['kind']==session['row']['kind']),None)
  if not row:raise ValueError('A receita do FM mudou. Abra uma nova mesa.')
  affected=negociacao.replacements(row,session['offer'],self.snapshot['sponsors'])
  negociacao.renewal_priority(session['company'],session['offer'],row['kind'],self.store.get('brands',[]),self.sessions,self.snapshot['date'])
  for old in affected:
   previous=next((c for c in self.store.get('brands',[]) if c.get('kind')==old.get('kind') and c.get('start')==old.get('start') and c.get('end')==old.get('end') and c.get('total')==old.get('total')),None)
   if previous and previous.get('status')!='terminated' and previous.get('company',{}).get('name')!=session['company'].get('name'):
    raise ValueError('Esse espaço já tem contrato negociado; rescinda-o antes de trocar a empresa.')
  deal=negociacao.signing(session,self.snapshot['date'],row,[c for c in self.store.get('brands',[]) if c.get('status')!='terminated'])
  if row['kind'] in {1,8,9,11,12,13,19}:
   uniformes.export_kits(deal['company'],native.ROOT/'dados/preparados'/session['id'])
  entry=self.fm.update_sponsor(row['index'],deal['total'],deal['start'],deal['end'],row['raw'],deal['company']['name'],expected_day=self.snapshot['date'],metadata={'sponsor_contract':deal,'negotiation_id':session['id']},replace_overlaps=True)
  deal=dict(deal,transaction=entry['id']);self.store.setdefault('brands',[]).append(deal)
  session['status']='signed';session['transaction']=entry['id'];negociacao.log(session,'Sistema','Contrato assinado e verificado no FM.',session['offer'])
  native.save_json(native.ROOT/'dados/presidencia.json',self.store);self._save_sessions();native.finalize_local_commit(entry)
  return self.applied(entry)|{'deal':deal,'session':session}
 def sponsor_terminate(self,index):
  if not self.fm or not self.snapshot:raise ValueError('Conecte e aprove um clube antes de rescindir.')
  row=next((r for r in self.snapshot['sponsors'] if r['index']==int(index)),None)
  if not row or not row.get('total'):raise ValueError('Selecione um contrato ativo.')
  deal=next((c for c in reversed(self.store.get('brands',[])) if c.get('kind')==row.get('kind') and c.get('start')==row.get('start') and c.get('end')==row.get('end') and c.get('total')==row.get('total') and c.get('status')!='terminated'),None)
  if not deal:raise ValueError('Esse contrato não tem termos de rescisão cadastrados no FMPresidente.')
  fee=negociacao.remaining_penalty(deal,self.snapshot['date'])
  entry=self.fm.terminate_sponsor(row['index'],row['raw'],fee,self.snapshot['date'],{'sponsor_termination':deal.get('transaction'),'company':deal['company']['name']})
  deal['status']='terminated';deal['termination']=entry['id'];deal['termination_date']=self.snapshot['date'];deal['native_index']=row['index']
  native.save_json(native.ROOT/'dados/presidencia.json',self.store);native.finalize_local_commit(entry)
  return self.applied(entry)|{'deal':deal,'fee':fee}
 def uniform_preview(self,company_id=None):
  company=next((c for c in self.companies if c.get('id')==company_id),None) if company_id else None
  if not company and self.snapshot:
   bundle=uniformes.active_sponsors(self.snapshot,self.store.get('brands',[]));company=bundle.get(1)
  return uniformes.make_kit(company,'home')
 def uniform_generate(self,company_id=None):
  company=next((c for c in self.companies if c.get('id')==company_id),None) if company_id else None
  if not company:raise ValueError('Selecione uma marca para gerar o uniforme.')
  signature=uniformes.kit_signature({1:company})
  folder=native.ROOT/'dados/preparados'/'qt-uniformes'/signature
  if not (folder/'config.xml').is_file():uniformes.export_kits(company,folder)
  return {'folder':str(folder),'signature':signature,'company':company['name']}
 def uniform_install(self,folder,signature):
  uniformes.install_kits(Path(folder),signature);return {'folder':str(folder),'signature':signature}
 def discover(self,query='',full=False):
  self.close()
  if full:return sync.observe(),sync.search_candidates(query=query,prefer_cache=False)
  return sync.observe_and_candidates(query=query)
 def approve(self,candidate):
  self.close();fm=native.FM.connect_manual(candidate.address,candidate.club.uid)
  try:snapshot=fm.snapshot();observation=sync.observe(fm.club)
  except Exception:fm.close();raise
  self.fm=fm;self.snapshot=snapshot;return observation,snapshot
 def monitor(self):
  if not self.fm:return None,None
  try:
   observation=sync.observe(self.fm.club);snapshot=self.fm.snapshot()
   if observation.candidate_address!=self.fm.club or observation.process[:2]!=(self.fm.process['pid'],self.fm.process['started']):raise ValueError('O contexto mudou. Sincronize novamente.')
   self.snapshot=snapshot;return observation,snapshot
  except Exception:self.close();raise
 def execute(self,method,*args):
  if not self.fm:raise ValueError('Selecione e aprove um clube antes de aplicar.')
  if method not in ('capital','budgets','prices','invest','repay','set_licensed_kits','undo'):raise ValueError('Operação indisponível.')
  entry=getattr(self.fm,method)(*args)
  return self.applied(entry)
 def applied(self,entry):
  try:self.snapshot=self.fm.snapshot();return {'entry':entry,'snapshot':self.snapshot,'snapshot_error':None}
  except Exception as error:
   self.snapshot=None
   return {'entry':entry,'snapshot':None,'snapshot_error':str(error)}
 def debt_offer(self,index,months,rate):
  if not self.fm or not self.snapshot:raise ValueError('Conecte ao clube.')
  row=next(r for r in self.snapshot['debts'] if r['index']==index)
  return emprestimos.offer(self.snapshot,0,months,rate,row)
 def debt_sign(self,proposal):
  if not self.fm:raise ValueError('Conecte ao clube.')
  return self.applied(emprestimos.sign(self.fm,proposal))
 def loan_contract_status(self):
  if not self.fm:return {'available':False,'reason':'Aprove um clube antes de contratar.'}
  return emprestimos.allocation_status(self.fm)
 def loan_contract_offer(self,principal,months,rate):
  if not self.fm or not self.snapshot:raise ValueError('Conecte ao clube antes de contratar.')
  status=self.loan_contract_status()
  if not status['available']:raise ValueError(status['reason'])
  return emprestimos.offer(self.snapshot,principal,months,rate)
 def diagnostics(self):return recuperacao.scan(native.DATA/'historico')
 def export(self,path,records):
  native.save_json(path,{'aviso':'Diagnóstico local; não identifica a carreira.','operacoes':[r.public() for r in records]})
 def history(self):
  entries=[]
  for path in sorted((native.DATA/'historico').glob('*.json'),reverse=True)[:500]:
   try:
    entry=native.read_json(path,{})
    if isinstance(entry,dict):entries.append(entry)
   except (OSError,ValueError):continue
  return entries
