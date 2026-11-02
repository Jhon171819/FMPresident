"""UX-01.2: contratação de crédito com auditoria dinâmica das reservas."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
import FMPresidenteQt as qt
from aplicacao_qt import Session
import emprestimos

app=QApplication.instance() or QApplication([])


class Tests(unittest.TestCase):
    def setUp(self):
        self.window=qt.MainWindow(auto=False);self.addCleanup(self.window.close)

    def test_new_loan_action_waits_for_approved_session(self):
        self.assertFalse(self.window.loan_contract_button.isEnabled())
        self.assertIn('sincronize',self.window.loan_contract_status.text())

    def test_service_exposes_restriction_reason(self):
        result=Session().loan_contract_status()
        self.assertFalse(result['available']);self.assertIn('Aprove',result['reason'])

    def test_pool_guard_requires_an_active_session(self):
        with self.assertRaisesRegex(ValueError,'sessão ativa'):
            emprestimos._require_pool_allocation_proven()

    def test_unknown_creation_method_never_reaches_fm(self):
        service=Session();service.fm=Mock()
        with self.assertRaises(ValueError):service.execute('loan',100000)
        service.fm.assert_not_called()

    def test_existing_debt_operations_are_not_disabled_by_restriction(self):
        service=Session();service.fm=Mock();service.snapshot={'date':'2032-05-26','credit':{'rate':12,'reputation':5000},'debts':[{'index':0,'addr':1,'raw':'00','conditional':0,'original':100000,'source':1,'interest_only':False,'start':'2032-01-01','end':'2034-01-01','monthly':5000,'interest':400}]}
        proposal=service.debt_offer(0,24,12)
        self.assertEqual(proposal['principal'],87400)


if __name__=='__main__':unittest.main(verbosity=2)
