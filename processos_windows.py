"""Descoberta somente leitura do FM por Toolhelp e identidade nativa x64."""
import ctypes as C
from ctypes import wintypes as W
class ProcessEntry(C.Structure):
 _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',C.c_size_t),('module',W.DWORD),('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),('flags',W.DWORD),('name',W.WCHAR*260)]
def unique_pid(entries):
 matches=[pid for pid,name in entries if name.casefold()=='fm.exe']
 if len(matches)!=1:raise RuntimeError('Abra uma única instância do FM23 com sua carreira carregada.')
 return matches[0]
def enumerate_processes():
 import fm23 as n
 k=n.k
 k.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];k.CreateToolhelp32Snapshot.restype=W.HANDLE
 k.Process32FirstW.argtypes=[W.HANDLE,C.POINTER(ProcessEntry)];k.Process32FirstW.restype=W.BOOL
 k.Process32NextW.argtypes=k.Process32FirstW.argtypes;k.Process32NextW.restype=W.BOOL
 h=k.CreateToolhelp32Snapshot(2,0)
 if h==C.c_void_p(-1).value:raise C.WinError(C.get_last_error())
 try:
  entry=ProcessEntry();entry.size=C.sizeof(entry);rows=[]
  ok=k.Process32FirstW(h,C.byref(entry))
  while ok:
   rows.append((entry.pid,entry.name));ok=k.Process32NextW(h,C.byref(entry))
  error=C.get_last_error()
  if error!=18:raise C.WinError(error)
  return rows
 finally:k.CloseHandle(h)
def product_version(path):
 v=C.WinDLL('version',use_last_error=True)
 v.GetFileVersionInfoSizeW.argtypes=[W.LPCWSTR,C.POINTER(W.DWORD)];v.GetFileVersionInfoSizeW.restype=W.DWORD
 v.GetFileVersionInfoW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p];v.GetFileVersionInfoW.restype=W.BOOL
 v.VerQueryValueW.argtypes=[C.c_void_p,W.LPCWSTR,C.POINTER(C.c_void_p),C.POINTER(W.UINT)];v.VerQueryValueW.restype=W.BOOL
 size=v.GetFileVersionInfoSizeW(path,None)
 if not size:raise C.WinError(C.get_last_error())
 data=C.create_string_buffer(size)
 if not v.GetFileVersionInfoW(path,0,size,data):raise C.WinError(C.get_last_error())
 ptr=C.c_void_p();length=W.UINT()
 if not v.VerQueryValueW(data,'\\VarFileInfo\\Translation',C.byref(ptr),C.byref(length)) or length.value<4:raise OSError('Tradução da versão indisponível.')
 words=C.cast(ptr,C.POINTER(W.WORD));translations=[(words[i],words[i+1]) for i in range(0,length.value//2-1,2)]
 for lang,code in translations:
  if v.VerQueryValueW(data,f'\\StringFileInfo\\{lang:04x}{code:04x}\\ProductVersion',C.byref(ptr),C.byref(length)) and length.value:
   return C.wstring_at(ptr,length.value).rstrip('\0')
 raise OSError('Versão do executável indisponível.')
def process_info():
 import fm23 as n
 pid=unique_pid(enumerate_processes());h=n.k.OpenProcess(0x410,False,pid)
 if not h:raise OSError('Acesso de leitura ao processo FM indisponível.')
 try:
  n.psapi.EnumProcessModules.argtypes=[W.HANDLE,C.POINTER(C.c_void_p),W.DWORD,C.POINTER(W.DWORD)];n.psapi.EnumProcessModules.restype=W.BOOL
  module=C.c_void_p();needed=W.DWORD()
  if not n.psapi.EnumProcessModules(h,C.byref(module),C.sizeof(module),C.byref(needed)) or not module.value:raise OSError('Módulo principal indisponível.')
  class Reader:
   handle=h
   def alive(self):
    code=W.DWORD();return bool(n.k.GetExitCodeProcess(self.handle,C.byref(code)) and code.value==259)
  probe=n.ProcessProbe(Reader(),module.value);info=probe.identity()
  info['version']=product_version(info['path'])
  if info['path'].replace('\\','/').rsplit('/',1)[-1].casefold()!='fm.exe':raise OSError('Executável mudou durante a descoberta.')
  if probe.identity()!={k:v for k,v in info.items() if k!='version'}:raise OSError('Instância mudou durante a descoberta.')
  return info
 finally:n.k.CloseHandle(h)
