import ast,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import recuperacao
source=Path('FMPresidente.pyw').read_text(encoding='utf-8');tree=ast.parse(source);app=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='App')
method=next(x for x in app.body if isinstance(x,ast.FunctionDef) and x.name=='open_recovery')
window=Mock();window.winfo_exists.return_value=True
widget=Mock();table=Mock();table.selection.return_value=()
namespace={'tk':SimpleNamespace(Toplevel=lambda _:window,StringVar=lambda **_:Mock()),'ttk':SimpleNamespace(Frame=lambda _:widget,Button=lambda *a,**k:Mock()),'native':SimpleNamespace(DATA=Path('.')),'recuperacao':recuperacao,'filedialog':Mock()}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'FMPresidente.pyw','exec'),namespace)
class Tests(unittest.TestCase):
 def test_center_reads_when_disconnected(self):
  app=SimpleNamespace(busy=False,fm=None,label=Mock(),table=Mock(return_value=table),replace_rows=Mock())
  app.after=lambda delay,fn:fn()
  app.run=lambda work,done,text:done(work())
  record=recuperacao.Record('a'*32,'Teste','2026','STATE_UNKNOWN','Indeterminado',None,None,'Incerto')
  original=recuperacao.scan;recuperacao.scan=lambda _: [record]
  try:namespace['open_recovery'](app)
  finally:recuperacao.scan=original
  self.assertTrue(app.replace_rows.called);self.assertEqual(app.replace_rows.call_args.args[1][0][1][2],'STATE_UNKNOWN')
if __name__=='__main__':unittest.main(verbosity=2)
