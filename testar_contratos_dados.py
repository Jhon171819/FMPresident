"""Testes AU-02 independentes do jogo e da pasta dados/."""
import copy
from datetime import date
import json
import unittest

import contratos_dados as c


PROCESS = dict(pid=123,started='123456789',version='23.2.0+1771058',size=356016128,path='C:/FM/fm.exe')
SPONSOR = dict(index=0,addr=1234,raw='00',kind=1,name='Master',total=20000,start='2032-01-01',end='2033-12-31',renew=False,fixed=True)
LOAN = dict(index=0,addr=2345,raw='00',original=100000,monthly=5000,interest=833,conditional=0,start='2032-01-01',end='2033-12-01',source=1,interest_only=False,can_repay=True)
SNAPSHOT = dict(date='2032-04-16',club='Ceará',uid=104749,licensed_kits=True,balance=-1,transfer=200,season_transfer=300,wage=400,wage_spend=500,ticket=1.5,season_ticket=30.0,attendance=15000,facilities={'Treinamento':14},sponsors=[SPONSOR],debts=[LOAN],credit={'rate':3.5,'reputation':6500})
LOCAL = dict(company={'name':'Marca'},kind=1,start='2032-01-01',end='2033-12-31',total=20000,annual=10000,years=2,exclusive=True,renewal=True,penalty=20,sector='Banco',status='active',transaction='abc')
SESSION = dict(id='mesa',company={'name':'Marca'},row={'kind':1},offer={'start':'2032-01-01','annual':10000,'years':2,'exclusive':True,'renewal':True,'penalty':20},status='offered')
OFFER = dict(principal=100000,monthly=5000,interest=833,first='2032-05-01',end='2034-04-01',rate=12.0,months=24)


class ContractsTest(unittest.TestCase):
    def test_process_and_unknown_build(self):
        p=c.process_from_legacy(PROCESS)
        self.assertEqual(p.pid,123); self.assertEqual(p.build_validation,c.Verification.UNKNOWN)
        self.assertIsNone(p.sha256.value); self.assertEqual(p.sha256.source,c.Source.UNKNOWN)
    def test_invalid_identity(self):
        for update in ({'pid':0},{'pid':True},{'started':''},{'size':-1}):
            with self.subTest(update=update), self.assertRaises(ValueError): c.process_from_legacy(dict(PROCESS,**update))
    def test_unknown_career_and_control(self):
        s=c.financial_from_legacy(SNAPSHOT,PROCESS)
        self.assertIsNone(s.career.career_id.value); self.assertIsNone(s.career.controlled_club.value)
        self.assertEqual(s.career.identity_validation,c.Verification.UNKNOWN)
        self.assertEqual(s.career.identified_club.uid,104749)
    def test_financial_distinct_units(self):
        s=c.financial_from_legacy(SNAPSHOT,PROCESS)
        self.assertEqual((s.balance_gbp,s.transfer_budget_gbp,s.weekly_wage_budget_gbp,s.ticket_price_gbp),(-1,200,400,1.5))
    def test_financial_bad_values(self):
        for key,value in [('balance',float('nan')),('ticket',float('inf')),('wage',True),('facilities',{'x':21}),('ticket',-1),('uid',0)]:
            with self.subTest(key=key), self.assertRaises(ValueError): c.financial_from_legacy(dict(SNAPSHOT,**{key:value}),PROCESS)
    def test_financial_missing(self):
        d=dict(SNAPSHOT); del d['balance']
        with self.assertRaises(ValueError): c.financial_from_legacy(d,PROCESS)
    def test_sponsor_observed(self):
        s=c.sponsor_from_memory(SPONSOR)
        self.assertEqual(s.origin,c.Source.FM_MEMORY); self.assertIsNone(s.annual_gbp); self.assertIsNone(s.brand)
    def test_local_sponsor_not_proven_in_fm(self):
        s=c.sponsor_from_local(LOCAL)
        self.assertEqual(s.fm_match,c.Verification.UNKNOWN); self.assertEqual(s.total_gbp,s.annual_gbp*s.years)
    def test_sponsor_proposal(self):
        s=c.sponsor_proposal_from_legacy(SESSION)
        self.assertEqual(s.total_gbp,20000); self.assertEqual(s.end,date(2033,12,31)); self.assertEqual(s.fm_match,c.Verification.UNKNOWN)
    def test_sponsor_leap_date(self):
        d=copy.deepcopy(SESSION);d['offer'].update(start='2032-02-29',years=1)
        self.assertEqual(c.sponsor_proposal_from_legacy(d).end,date(2033,2,28))
    def test_sponsor_invalid(self):
        for key,value in [('years',0),('years',6),('annual',999),('total',20001),('start','bad'),('end','2031-12-31'),('exclusive','sim')]:
            with self.subTest(key=key), self.assertRaises(ValueError): c.sponsor_from_local(dict(LOCAL,**{key:value}))
    def test_sponsor_limits(self):
        d=dict(LOCAL,annual=500_000_000,years=2,total=1_000_000_000,penalty=100)
        self.assertEqual(c.sponsor_from_local(d).total_gbp,1_000_000_000)
        with self.assertRaises(ValueError):c.sponsor_from_local(dict(d,years=3,total=1_500_000_000))
    def test_exclusivity(self):
        a=c.sponsor_from_local(LOCAL)
        b=c.sponsor_from_local(dict(LOCAL,company={'name':'Outra'}))
        with self.assertRaises(ValueError): c.validate_exclusivity((a,b))
        c.validate_exclusivity((a,c.sponsor_from_local(dict(LOCAL,company={'name':'Outra'},sector='Varejo'))))
    def test_loan_observed_not_rate(self):
        x=c.loan_from_memory(LOAN)
        self.assertEqual(x.interest_component_gbp,833); self.assertIsNone(x.annual_rate_percent.value); self.assertIsNone(x.remaining_gbp.value)
    def test_loan_estimated_balance(self):
        x=c.Loan(**{**c.loan_from_memory(LOAN).__dict__,'remaining_gbp':c.Evidence(50000,c.Source.CALCULATED,c.Verification.UNVERIFIED,'estimativa')})
        self.assertEqual(x.remaining_gbp.source,c.Source.CALCULATED)
    def test_loan_offer(self):
        x=c.loan_offer_from_legacy(OFFER)
        self.assertEqual(x.operation_state,c.ExecutionState.PROPOSED);self.assertEqual(x.annual_rate_percent.source,c.Source.CALCULATED)
    def test_loan_invalid(self):
        for key,value in [('principal',0),('monthly',0),('interest',5001),('total',1),('rate',101),('rate',float('nan')),('months',5),('end','2031-01-01')]:
            with self.subTest(key=key), self.assertRaises(ValueError):c.loan_offer_from_legacy(dict(OFFER,**{key:value}))
    def test_loan_missing(self):
        d=dict(LOAN);del d['monthly']
        with self.assertRaises(ValueError):c.loan_from_memory(d)
    def test_provenance(self):
        for origin in c.Source:
            item=c.Evidence(None if origin==c.Source.UNKNOWN else 3,origin,c.Verification.UNVERIFIED,'semântica não confirmada')
            self.assertEqual(c.model_from_json(c.model_to_json(item)),item)
        self.assertEqual(c.financial_from_legacy(SNAPSHOT,PROCESS).credit_rate.source,c.Source.UNKNOWN)
    def test_fallback(self):
        d=dict(SNAPSHOT,credit={});s=c.financial_from_legacy(d,PROCESS)
        self.assertIsNone(s.credit_rate.value);self.assertIsNone(s.reputation.value)
        rate,rep=c.credit_from_offer_context(d)
        self.assertEqual((rate.value,rate.source,rep.value),(13.75,c.Source.FALLBACK,5000))
    def test_operation_states(self):
        for state in ('prepared','applied','failed','unexpected'):
            r=c.operation_from_journal({'id':'id','status':state})
            self.assertEqual(r.state,{'prepared':c.ExecutionState.PREPARED,'applied':c.ExecutionState.APPLIED,'failed':c.ExecutionState.FAILED}.get(state,c.ExecutionState.UNKNOWN))
            self.assertIsNone(r.recovery_needed)
        request=c.OperationRequest('capital',{'amount_gbp':1000})
        with self.assertRaises(ValueError): c.OperationValidation(request,c.Verification.VERIFIED,pending=('identidade',))
    def test_legacy_roundtrip_no_mutation(self):
        for kind,item in [('process',PROCESS),('sponsor_memory',SPONSOR),('sponsor_local',LOCAL),('sponsor_proposal',SESSION),('loan_memory',LOAN),('loan_offer',OFFER),('financial_snapshot',{'snapshot':SNAPSHOT,'process':PROCESS}),('journal',{'id':'abc','status':'prepared'})]:
            with self.subTest(kind=kind):
                original=copy.deepcopy(item);envelope=c.serialize_legacy(kind,item); model,restored=c.deserialize_legacy(envelope)
                self.assertEqual(item,original);self.assertEqual(restored,original);self.assertEqual(envelope,c.serialize_legacy(kind,restored));self.assertIsNotNone(model)
    def test_unknown_legacy_fields(self):
        item=dict(LOCAL,extra={'future':[1,2,3]});_, restored=c.deserialize_legacy(c.serialize_legacy('sponsor_local',item))
        self.assertEqual(restored,item);restored['extra']['future'].append(4);self.assertEqual(item['extra']['future'],[1,2,3])
    def test_unsupported_envelope(self):
        for value in ('{}','{"schema_version":2,"kind":"process","legacy":{}}','{"schema_version":1,"kind":"bad","legacy":{}}','{"schema_version":1,"kind":"process","legacy":{"pid":NaN}}'):
            with self.subTest(value=value),self.assertRaises(ValueError):c.deserialize_legacy(value)
    def test_typed_roundtrip(self):
        request=c.OperationRequest('aporte',{'amount_gbp':1000},c.financial_from_legacy(SNAPSHOT,PROCESS).career,('validar identidade',),'req')
        for model in (c.financial_from_legacy(SNAPSHOT,PROCESS),c.sponsor_from_local(LOCAL),c.loan_from_memory(LOAN),request,c.OperationValidation(request,c.Verification.UNKNOWN,pending=('identidade',)),c.operation_from_journal({'id':'x','status':'applied'})):
            with self.subTest(model=type(model).__name__): self.assertEqual(c.model_from_json(c.model_to_json(model)),model)
    def test_reject_malformed_typed(self):
        for raw in ('{}','{"schema_version":2,"model":{}}','{"schema_version":1,"model":{"$model":"Bad","fields":{}}}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):c.model_from_json(raw)


if __name__ == '__main__': unittest.main()
