"""Compila a entrada Qt separadamente; não troca o atalho principal."""
import os,sys,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ['PATH']=os.pathsep.join([str(root/'ferramentas/qt-tools/PySide6'),str(root/'ferramentas/qt-tools/shiboken6'),str(Path(sys.executable).parent),str(Path(sys.executable).parent/'DLLs'),str(Path(os.environ['WINDIR'])/'System32'),os.environ['WINDIR']])
for folder in ('ferramentas/qt-tools','ferramentas/build-tools'):sys.path.insert(0,str(root/folder))
os.environ['PYTHONPATH']=os.pathsep.join([str(root/'ferramentas/qt-tools'),str(root/'ferramentas/build-tools')])
import PyInstaller.__main__
PyInstaller.__main__.run([str(root/'FMPresidenteQt.py'),'--name','FMPresidenteQt','--onedir','--noconsole','--noconfirm','--distpath',str(root/'build/qt-distrib'),'--workpath',str(root/'build/qt-pyinstaller'),'--specpath',str(root/'build'),'--paths',str(root),'--icon',str(root/'assets/FMPresidente.ico'),'--exclude-module','tkinter','--exclude-module','PySide6.QtWebEngineCore','--exclude-module','PySide6.QtQml','--exclude-module','PySide6.QtQuick','--exclude-module','numpy','--exclude-module','pytest'])
shutil.copytree(root/'assets',root/'build/qt-distrib/assets',dirs_exist_ok=True)

shutil.copytree(root/'avisos-qt',root/'build/qt-distrib/avisos-qt',dirs_exist_ok=True)
