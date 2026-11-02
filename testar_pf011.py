import unittest
from unittest.mock import Mock,patch
import sincronizacao_hibrida as s
import testar_sincronizacao_interface as base
connect=base.connect
class Tests(base.Tests):
 def test_pending_sync_dispatches_after_result_callback(self):
  import ast,queue
  from types import SimpleNamespace
  method=next(n for n in base.app.body if isinstance(n,ast.FunctionDef) and n.name=='pump')
  ns={'queue':queue,'messagebox':Mock()}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'pump','exec'),ns)
  order=[];events=queue.Queue();events.put(('done','result',lambda result:order.append('result')))
  x=SimpleNamespace(closed=False,busy=True,pending_sync=True,events=events,fm=None,snap=None,
   connect=lambda:order.append('sync'),set_actions=Mock(),after=Mock(),pump=Mock())
  ns['pump'](x)
  self.assertEqual(order,['result','sync']);self.assertFalse(x.pending_sync)
 def test_closed_pump_does_not_dispatch(self):
  import ast,queue
  from types import SimpleNamespace
  method=next(n for n in base.app.body if isinstance(n,ast.FunctionDef) and n.name=='pump')
  ns={'queue':queue};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'pump','exec'),ns)
  x=SimpleNamespace(closed=True,connect=Mock());ns['pump'](x);x.connect.assert_not_called()
 def test_three_busy_clicks_coalesce(self):
  self.x.busy=True
  for _ in range(3):connect(self.x)
  self.assertIs(self.x.pending_sync,True);self.assertEqual(self.x.sync.begin.call_count,3)
 def test_worker_failure_reports_error(self):
  with patch.object(__import__('testar_sincronizacao_interface').namespace['sync'],'observe_and_candidates',side_effect=OSError('FM fechado')):
   connect(self.x);self.x.connection.set.assert_called_with('Observação indisponível • FM fechado')
 def test_one_discovery_and_two_independent_validations(self):
  with patch('fm23.process_info',return_value={'pid':1}) as discovery,patch.object(s,'observe',return_value='o') as observation,patch.object(s,'search_candidates',return_value=([],False)) as search:
   self.assertEqual(s.observe_and_candidates(),('o',([],False)))
   discovery.assert_called_once();observation.assert_called_once_with(info={'pid':1});search.assert_called_once_with(query='',info={'pid':1})
if __name__=='__main__':unittest.main(verbosity=2)
