"""Testes de paridade dos adaptadores Qt, sem escrita no FM ou nos arquivos do usuário."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import date

from PIL import Image
import aplicacao_qt as app
import negociacao


def snap():
    return {
        'club':'Fixture FC','date':'2032-05-26','uid':104749,'balance':1_000_000,
        'transfer':2_000_000,'wage':100_000,'ticket':30.0,'season_ticket':500.0,
        'facilities':{name:10 for name in app.native.FACILITIES},
        'sponsors':[{'index':0,'name':'Receita de camisa','kind':1,'total':100_000,
                     'start':'2032-01-01','end':'2032-12-31','raw':'00'}],
        'debts':[],'licensed_kits':False,
    }


class Tests(unittest.TestCase):
    def test_catalog_filter_and_empty_state(self):
        s=app.Session()
        self.assertGreater(len(s.catalog()),10)
        self.assertEqual(s.catalog('marca que não existe'),[])
        self.assertTrue(all('adidas' in c['name'].casefold() or 'material' in c.get('sector','').casefold() for c in s.catalog('adidas')))

    def test_begin_and_counter_use_negotiation_engine(self):
        s=app.Session();s.snapshot=snap()
        company=s.catalog('adidas')[0]
        with patch('aplicacao_qt.native.save_json'):
            session=s.sponsor_begin(company['id'],0,'2032-06-01')
            terms=dict(session['offer'],annual=session['offer']['annual']+1000)
            updated=s.sponsor_counter(session['id'],terms,())
        self.assertEqual(updated['id'],session['id']);self.assertIn(updated['status'],negociacao.OPEN|{'rejected'})

    def test_sponsor_sign_delegates_native_write_and_finalizes(self):
        s=app.Session();s.snapshot=snap();s.fm=Mock();s.fm.snapshot.return_value=s.snapshot
        company=s.catalog('adidas')[0]
        with patch('aplicacao_qt.native.save_json'),patch('aplicacao_qt.native.finalize_local_commit'),patch('aplicacao_qt.uniformes.export_kits'),patch('aplicacao_qt.negociacao.signing') as signing:
            session={'id':'session-1','row':s.snapshot['sponsors'][0],'company':company,'offer':{'annual':100000,'years':1,'start':'2032-05-26','exclusive':False,'renewal':False,'penalty':20},'status':'agreed','messages':[],'round':0}
            s.sessions.append(session)
            signing.return_value={'company':company,'kind':1,'start':'2032-05-26','end':'2033-05-25','annual':100000,'years':1,'total':100000,'exclusive':False,'renewal':False,'penalty':20,'sector':'material esportivo','negotiation':'session-1','status':'active'}
            s.fm.update_sponsor.return_value={'id':'entry-1','status':'applied'}
            result=s.sponsor_sign('session-1')
        s.fm.update_sponsor.assert_called_once();self.assertEqual(result['entry']['id'],'entry-1');self.assertEqual(result['session']['status'],'signed')

    def test_sponsor_termination_preserves_fee_and_native_guard(self):
        s=app.Session();s.snapshot=snap();s.fm=Mock();s.fm.snapshot.return_value=s.snapshot
        company=s.catalog('adidas')[0]
        s.store['brands']=[{'company':company,'kind':1,'start':'2032-01-01','end':'2032-12-31','total':100000,'penalty':20,'status':'active','transaction':'old'}]
        s.fm.terminate_sponsor.return_value={'id':'entry-2','status':'applied'}
        with patch('aplicacao_qt.native.save_json'),patch('aplicacao_qt.native.finalize_local_commit'):
            result=s.sponsor_terminate(0)
        s.fm.terminate_sponsor.assert_called_once();self.assertGreaterEqual(result['fee'],0);self.assertEqual(result['deal']['status'],'terminated')

    def test_uniform_preview_is_real_pillow_output(self):
        s=app.Session();company=s.catalog('adidas')[0]
        image=s.uniform_preview(company['id'])
        self.assertIsInstance(image,Image.Image);self.assertEqual(image.size,(512,512))

    def test_uniform_install_delegates_and_does_not_fake_rollback(self):
        s=app.Session()
        with patch('aplicacao_qt.uniformes.install_kits') as install:
            result=s.uniform_install('C:/temporary/kits','signature')
        install.assert_called_once_with(Path('C:/temporary/kits'),'signature');self.assertEqual(result['signature'],'signature')

    def test_new_loan_remains_unavailable(self):
        s=app.Session();s.fm=Mock()
        with self.assertRaises(ValueError):s.execute('loan',{})
        s.fm.loan.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
