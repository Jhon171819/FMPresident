"""Renderização real Qt com dados sintéticos, sem conexão ou escrita no FM."""
import os,time,json,statistics
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from testar_ux01 import app,snapshot
import FMPresidenteQt as q
from PySide6.QtWidgets import QMessageBox
root=Path('docs/ux/capturas');root.mkdir(parents=True,exist_ok=True)
w=q.MainWindow(auto=False);w.resize(1366,768);w.show();app.processEvents();w.grab().save(str(root/'01-desconectado-1366.png'))
w.on_result('approve',(None,snapshot()))
for i,name in enumerate(('dashboard','financas','patrocinios','infraestrutura','emprestimos','uniformes','historico','recuperacao','configuracoes')):
 w.nav.setCurrentRow(i);app.processEvents();w.grab().save(str(root/f'{i+2:02d}-{name}-1366.png'))
w.resize(1600,900);w.nav.setCurrentRow(1);app.processEvents();w.grab().save(str(root/'11-financas-1600.png'))
dialog=QMessageBox(QMessageBox.Question,'Confirmar aporte','Aplicar aporte de £ 1.000.000 no clube aprovado?',QMessageBox.Yes|QMessageBox.No,w);dialog.show();app.processEvents();dialog.grab().save(str(root/'12-confirmacao.png'));dialog.close()
w.on_result('error','Não foi possível identificar o FM23. Verifique a carreira aberta.');app.processEvents();w.grab().save(str(root/'13-erro.png'))
values=[]
for _ in range(20):
 t=time.perf_counter();w.nav.setCurrentRow((w.nav.currentRow()+1)%9);app.processEvents();values.append((time.perf_counter()-t)*1000)
Path('docs/ux/UX-01-medicoes.json').write_text(json.dumps({'cenario':'Qt offscreen, snapshot sintético; não compara com Tk','troca_pagina_ms':{'n':20,'mediana':statistics.median(values),'min':min(values),'max':max(values),'p95':sorted(values)[18]}},indent=2))
w.close()
