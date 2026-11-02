import ast,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
source=Path('FMPresidente.pyw').read_text(encoding='utf-8');tree=ast.parse(source)
app=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='App')
method=next(x for x in app.body if isinstance(x,ast.FunctionDef) and x.name=='apply')
box=SimpleNamespace(showwarning=Mock());ns={'messagebox':box};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'FMPresidente.pyw','exec'),ns)
class Tests(unittest.TestCase):
 def test_applied_but_snapshot_failure_never_retries(self):
  operation=Mock(return_value={'id':'abc','title':'teste','status':'applied'})
  status=Mock();status.get.return_value='Alteração aplicada; não repita'
  app=SimpleNamespace(fm=SimpleNamespace(snapshot=Mock(side_effect=OSError('indisponível'))),snap={"date":"2032-01-01"},status=status,set_actions=Mock(),render=Mock(),refresh_history=Mock())
  app.run=lambda work,done:done(work())
  ns['apply'](app,operation)
  operation.assert_called_once();self.assertIsNone(app.snap);box.showwarning.assert_called_once();app.set_actions.assert_called_once_with(False)
if __name__=='__main__':unittest.main(verbosity=2)
