"""Benchmark PF-01: modo real somente leitura; nenhum save ou campo do FM é alterado."""
import argparse, importlib.machinery, importlib.util, json, statistics, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import fm23, recuperacao, sincronizacao_hibrida as sync
loader=importlib.machinery.SourceFileLoader('app_pf01','FMPresidente.pyw')
spec=importlib.util.spec_from_loader(loader.name,loader);app=importlib.util.module_from_spec(spec);loader.exec_module(app)
def measure(fn,n):
 values=[]
 for _ in range(n):
  t=time.perf_counter();fn();values.append((time.perf_counter()-t)*1000)
 ordered=sorted(values)
 return {'n':n,'median_ms':round(statistics.median(values),3),'min_ms':round(min(values),3),'max_ms':round(max(values),3),'p95_ms':round(ordered[int((n-1)*.95)],3) if n>=20 else None,'first_ms':round(values[0],3)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--live',action='store_true');args=p.parse_args()
 data={};root=tk.Tk();root.withdraw();tree=ttk.Treeview(root,columns=['x'],show='headings');rows=[(str(i),(str(i),)) for i in range(500)]
 app.App.replace_rows(tree,rows)
 data['tabela_500_sem_alteracoes']=measure(lambda:app.App.replace_rows(tree,rows),20)
 root.destroy()
 data['journals']=measure(lambda:recuperacao.scan(fm23.DATA/'historico'),10)
 if args.live:
  data['observacao_real']=measure(sync.observe,3)
  data['candidatos_cache_real']=measure(sync.search_candidates,3)
  options,_=sync.search_candidates()
  if options:
   fm=fm23.FM.connect_manual(options[0].address,options[0].club.uid)
   try:data['snapshot_real']=measure(fm.snapshot,3)
   finally:fm.close()
 Path(args.output).write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data,indent=2))
if __name__=='__main__':main()
