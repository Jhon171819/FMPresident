"""Verificação de datas e transações; --live testa e restaura dados reais no FM."""
from datetime import date
from contextlib import contextmanager
import json
import struct
import tempfile
from pathlib import Path
import sys
import fm23 as f


def selfcheck():
    for day in (date(2031,11,18),date(2031,12,24),date(2032,2,29),date(2032,12,31)):
        old=bytes.fromhex('00800000')
        raw=f.pack_date(day,old)
        assert f.fm_date(raw)==day
        assert int.from_bytes(raw[:2],'little')&0xFE00==0x8000
    assert f.contract_end(date(2031,12,24),2)==date(2033,12,23)
    for raw in (b'\0'*4,struct.pack('<HH',366,2031)):
        try:f.fm_date(raw)
        except ValueError:pass
        else:raise AssertionError('Data inválida aceita')

    class Fake:
        def __init__(self):self.data={100:b'aaaa',200:b'bbbb',f.DATE_RVA:f.pack_date(date(2031,11,18))};self.fail=False;self.pauses=0
        def read(self,a,n):return self.data[a]
        def write(self,a,b):
            if self.fail and a==200:self.fail=False;raise OSError('falha de escrita simulada')
            self.data[a]=b
        @contextmanager
        def paused(self):
            self.pauses+=1
            try:yield
            finally:self.pauses-=1
    fm=object.__new__(f.FM);fm.mem=Fake();fm.club=123;fm.base=0
    fm.process={'pid':1,'started':'test'};fm.validate=lambda:None
    fm.guard=type('GuardSimulado',(),{'require_full':lambda self:None})()
    fm.career_guard=type('ContextoSimulado',(),{'require':lambda self:None})()
    changes=[dict(label='A',addr=100,before=b'aaaa'.hex(),after=b'cccc'.hex()),dict(label='B',addr=200,before=b'bbbb'.hex(),after=b'dddd'.hex())]
    original=f.DATA
    with tempfile.TemporaryDirectory() as folder:
        f.DATA=Path(folder)
        try:
            fm.mem.fail=True
            try:fm.transaction('falha de duas escritas',changes)
            except OSError:pass
            else:raise AssertionError('Falha não propagada')
            assert fm.mem.data[100]==b'aaaa' and fm.mem.data[200]==b'bbbb' and fm.mem.pauses==0
            entry=fm.transaction('sucesso',changes)
            assert entry['status']=='applied' and fm.mem.data[100]==b'cccc'
            try:fm.transaction('dados antigos',changes)
            except ValueError:pass
            else:raise AssertionError('Escrita sobre dado modificado')
            assert fm.mem.data[100]==b'cccc' and fm.mem.pauses==0
        finally:f.DATA=original
    print('OK: datas, flags, vigência, rollback e bloqueio de dados desatualizados.')


def live():
    fm=f.FM(print)
    try:
        baseline=fm.snapshot();results=[]
        operations=[('Aporte +1000',lambda:fm.capital(1000)),
            ('Orçamentos',lambda:fm.budgets(baseline['transfer']+1000,baseline['wage']+10)),
            ('Preços',lambda:fm.prices(baseline['ticket']+.25,baseline['season_ticket']+1)),
            ('Treinamento +1',lambda:fm.invest('Treinamento'))]
        for title,op in operations:
            entry=op()
            try:
                for change in entry['changes']:
                    raw=bytes.fromhex(change['after']);assert fm.mem.read(change['addr'],len(raw))==raw
                results.append(dict(test=title,verified=True,entry=entry['id']))
            finally:fm.undo(entry)
        sponsor=next(r for r in baseline['sponsors'] if r['kind']==1)
        entry=fm.update_sponsor(sponsor['index'],sponsor['total']+1000,date.fromisoformat(sponsor['start']),date.fromisoformat(sponsor['end']),sponsor['raw'],'Teste reversível')
        try:assert fm.sponsor_rows()[sponsor['index']]['total']==sponsor['total']+1000
        finally:fm.undo(entry)
        results.append(dict(test='Patrocínio nativo',verified=True,entry=entry['id']))
        debt=next(r for r in baseline['debts'] if r['can_repay'])
        entry=fm.repay(debt['index'],debt['raw'])
        try:
            after=fm.snapshot();row=after['debts'][debt['index']]
            assert row['original']==row['monthly']==row['interest']==0
            assert after['balance']==baseline['balance']-debt['original']
        finally:fm.undo(entry)
        results.append(dict(test='Quitação do empréstimo',verified=True,entry=entry['id']))
        assert fm.snapshot()==baseline,'O FM não voltou ao estado inicial'
        report=dict(process=fm.process,date=baseline['date'],tests=results,restored=True)
        f.save_json(f.DATA/'validacao-integracao.json',report)
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:fm.close()


if __name__=='__main__':
    selfcheck()
    if '--live' in sys.argv:live()
