"""Profiling PF-01.1 somente leitura; wrappers restaurados ao terminar."""
import time,json,uuid,argparse
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import fm23 as n,compatibilidade as c,sincronizacao_hibrida as s,indice_clubes as ix
rows=[]
def run(output, samples=3):
 def wrap(fn,phase):
  def call(*a,**k):
   t=time.perf_counter_ns();ok=False
   try:r=fn(*a,**k);ok=True;return r
   finally:rows.append(dict(operation=op,phase=phase,ns=time.perf_counter_ns()-t,ok=ok,origin='diagnostic'))
  return call
 with patch.object(n,'process_info',wrap(n.process_info,'process_discovery')),patch.object(c,'fingerprint',wrap(c.fingerprint,'fingerprint')),patch.object(c.BuildGuard,'verify',wrap(c.BuildGuard.verify,'build_validation')),patch.object(n.Memory,'read',wrap(n.Memory.read,'memory_read')),patch.object(ix.ClubIndex,'find',wrap(ix.ClubIndex.find,'sqlite_query')):
  for _ in range(samples):
   op=uuid.uuid4().hex;t=time.perf_counter_ns()
   if hasattr(s,'observe_and_candidates'):s.observe_and_candidates()
   else:s.observe();s.search_candidates()
   rows.append(dict(operation=op,phase='pipeline',ns=time.perf_counter_ns()-t,ok=True,origin='diagnostic'))
 Path(output).write_text(json.dumps(rows,indent=2),encoding='utf-8')
 for phase in sorted({r['phase'] for r in rows}):
  v=[r['ns']/1e6 for r in rows if r['phase']==phase];import statistics
  print(phase,len(v),round(statistics.median(v),3))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)
