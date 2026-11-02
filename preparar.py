"""Preparação local dos gráficos existentes; executar uma vez na instalação."""
from pathlib import Path
import shutil

root=Path(__file__).resolve().parent
old=root.parent/'Patrocinios FM23'
shutil.copytree(old/'assets',root/'assets',dirs_exist_ok=True)
source=(old/'painel.pyw').read_text(encoding='utf-8').split('\nclass App(tk.Tk):')[0]
source=source.replace('"""Negociação local de patrocínios para FM23. Não altera a memória nem o save."""',
    '"""Gráficos locais de uniformes, reutilizados do painel de patrocínios."""')
# Mantém somente o gerador de gráficos e seus auxiliares; elimina o roteiro manual.
source=source.split('\ndef financial_guide(c):')[0]
(root/'uniformes.py').write_text(source,encoding='utf-8')
