"""Compila o app em build/distrib; a instalação é uma etapa separada."""
import os
from pathlib import Path
import sys
import shutil

root = Path(__file__).resolve().parent
toolroot = root/'ferramentas/build-tools'
sys.path.insert(0,str(toolroot))
os.environ['PYTHONPATH'] = str(toolroot)
import PyInstaller.__main__

PyInstaller.__main__.run([
    str(root/'FMPresidente.pyw'), '--name','FMPresidente','--onedir','--noconsole','--noconfirm',
    '--distpath',str(root/'build/distrib'), '--workpath',str(root/'build/pyinstaller'),
    '--specpath',str(root/'build'), '--paths',str(root),
    '--icon',str(root/'assets/FMPresidente.ico'),
    '--exclude-module','numpy','--exclude-module','matplotlib','--exclude-module','scipy',
    '--exclude-module','pandas','--exclude-module','IPython','--exclude-module','pytest'
])
shutil.copytree(root/'assets',root/'build/distrib/assets',dirs_exist_ok=True)
