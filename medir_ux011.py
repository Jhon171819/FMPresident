"""Benchmark sintético equivalente de inicialização das duas janelas."""
import importlib.machinery
import json
import os
import statistics
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
import FMPresidenteQt as qt


def stats(values):
    ordered=sorted(values)
    return {'n':len(values),'median_ms':round(statistics.median(values),3),
            'p95_ms':round(ordered[int(len(values)*.95)-1],3),
            'min_ms':round(min(values),3),'max_ms':round(max(values),3)}


def cancel_timers(window):
    for timer_id in window.tk.call('after','info'):
        window.after_cancel(timer_id)


def main():
    app=QApplication.instance() or QApplication([])
    qt_values=[]
    for _ in range(10):
        started=time.perf_counter();window=qt.MainWindow(auto=False);window.show();app.processEvents();qt_values.append((time.perf_counter()-started)*1000);window.close()
    loader=importlib.machinery.SourceFileLoader('legacy_app','FMPresidente.pyw');legacy=loader.load_module()
    tk_values=[]
    for _ in range(10):
        started=time.perf_counter();window=legacy.App();window.update_idletasks();window.update();tk_values.append((time.perf_counter()-started)*1000);cancel_timers(window);window.destroy()
    result={'environment':'Windows 11 x64 / Python 3.14 / synthetic no FM','qt':stats(qt_values),'tkinter':stats(tk_values),
            'note':'Janelas instanciadas sem conexão FM; não mede sincronização, leitura de memória, primeira pintura nativa, CPU ou memória de carreira.'}
    path=qt.native.ROOT/'docs/ux/UX-01.1-benchmarks.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__=='__main__':main()
