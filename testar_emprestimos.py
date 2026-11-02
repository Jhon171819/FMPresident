"""Verificações financeiras offline. --live faz criação e rollback no FM parado."""
from datetime import date
from pathlib import Path
import json
import struct
import tempfile

import fm23 as native
import emprestimos as e


def check():
    assert e.payment(1_000_000, 12, 24) == (47073, 5407)
    assert e.payment(1_000_000, 0, 24) == (41666, 0)
    assert e.month(date(2032, 1, 31), 1) == date(2032, 2, 29)
    for args in [(0, 12, 24), (True, 12, 24), (10000, float('nan'), 24), (10000, 12, 0)]:
        try:
            e.payment(*args)
        except ValueError:
            pass
        else:
            raise AssertionError('Valor inválido aceito')
    e._slist_layout()
    class Memory:
        def __init__(self):
            self.data = {}
            self.fail = None
            self.depth = 0
        def put(self, address, value):
            self.data.update({address+i: b for i,b in enumerate(value)})
        def read(self, address, size):
            return bytes(self.data.get(address+i, 0) for i in range(size))
        def write(self, address, value):
            assert self.depth, 'Escrita sem suspensão'
            if address == self.fail:
                self.fail = None
                raise OSError('Falha de escrita simulada')
            self.put(address, value)
        def number(self, address, fmt='i'):
            return struct.unpack('<'+fmt, self.read(address, struct.calcsize('<'+fmt)))[0]
        def pointer(self, address):
            return self.number(address, 'Q')
        def paused(self):
            from contextlib import contextmanager
            @contextmanager
            def pause():
                self.depth += 1
                try:
                    yield
                finally:
                    self.depth -= 1
            return pause()
    fm = native.FM.__new__(native.FM)
    fm.mem = m = Memory()
    fm.base, fm.club, fm.finance, fm.info = 0, 0x5000, 0x1000, 0x3000
    fm.process = dict(pid=1, started='test')
    fm.guard = type('GuardSimulado', (), {'require_full': lambda self: None})()
    fm.career_guard=type('ContextoSimulado',(),{'require':lambda self:None})()
    fm._loans_verified = True
    fm.validate = lambda: None
    m.put(native.DATE_RVA, native.pack_date(date(2032,4,12)))
    for address, size in ((0x1000, 2200), (0x3000, 512), (0x6000, 8), (e.LOAN_POOL, 80),
                          (0x8000, 128), (0x9000, 4096), (0xa000, 128), (0x20000, 192), (0x10000, 28*128)):
        m.put(address, b'\0'*size)
    m.put(0x1014, struct.pack('<i', 2_000_000))
    m.put(e.LOAN_POOL+16, struct.pack('<QQQ',0x6000,0x6008,0x6008))
    m.put(e.LOAN_POOL+40, struct.pack('<QIIIII',0x10000,128,0,28,128,128))
    m.put(0x6000, struct.pack('<Q',0x10000))
    for i in range(128):
        m.put(0x10000+i*28, struct.pack('<Q',0x10000+(i+1)*28 if i<127 else 0))
    m.put(e.ALLOCATOR, struct.pack('<Q',0x8000))
    m.put(0x8018, struct.pack('<QQ',0x9000,0xa000))
    m.put(0x8034, b'\1')
    m.put(0x9000+64*8, struct.pack('<Q',0xa000))
    m.put(0xa020, struct.pack('<QQ',3 | (6<<16),0x20000))
    m.put(0xa050, struct.pack('<I',64))
    m.put(0x20000, struct.pack('<Q',0x20040))
    m.put(0x20040, struct.pack('<Q',0x20080))
    original_idle, original_data = e._ensure_idle, native.DATA
    e._ensure_idle = lambda fm: None
    snapshot = dict(date='2032-04-12', credit=dict(rate=13.75,reputation=6500))
    with tempfile.TemporaryDirectory() as folder:
        native.DATA = Path(folder)
        try:
            baseline = dict(m.data)
            q = e.offer(snapshot,100_000,24,1)
            assert q['counter'] and q['rate'] == q['minimum_rate']
            assert (q['first'],q['end']) == ('2032-05-01','2034-04-01')
            m.fail = fm.finance+0x544
            try:
                e.sign(fm,q)
            except OSError:
                pass
            else:
                raise AssertionError('Falha de escrita não propagada')
            assert m.data == baseline, 'Rollback não restaurou caixa ou reservas'
            entry = e.sign(fm,q)
            assert fm.debt_rows()[0]['original'] == 100_000
            assert m.number(fm.finance+20) == 2_100_000
            for offset in (0x324,0x544,0x7e4):
                assert m.number(fm.finance+offset) == 100_000
            assert m.number(e.LOAN_POOL+48,'I') == 127
            row = fm.debt_rows()[0]
            r = e.offer(snapshot,0,12,12,row)
            refinanced = e.sign(fm,r)
            assert len(fm.debt_rows()) == 1 and m.number(fm.finance+20) == 2_100_000
            assert fm.debt_rows()[0]['monthly'] == r['monthly']
            fm.undo(refinanced)
            second = e.sign(fm,q)
            assert len(fm.debt_rows()) == 2
            assert len({r['addr'] for r in fm.debt_rows()}) == 2
            fm.undo(second)
            repaid = fm.repay(0, fm.debt_rows()[0]['raw'])
            assert fm.debt_rows()[0]['original'] == 0
            assert m.number(fm.finance+20) == 2_000_000
            assert m.number(fm.finance+0x284) == 100_000
            fm.undo(repaid)
            fm.undo(entry)
            assert m.data == baseline and m.depth == 0
            changed = dict(q,date='2032-04-11')
            try:
                e.sign(fm,changed)
            except ValueError:
                pass
            else:
                raise AssertionError('Proposta de outro dia aceita')
        finally:
            e._ensure_idle, native.DATA = original_idle, original_data
    print('OK: proposta e contraproposta, parcelas, reserva nativa, criação, crédito contábil, renegociação, quitação, undo, rollback e proposta vencida.')


def live():
    fm = native.FM(print)
    try:
        e._build(fm)
        # Toda a sequência é revertida antes de retomar o calendário do jogo.
        with native.LOCK, fm.mem.paused():
            snapshot = fm.snapshot()
            proposal = e.offer(snapshot, 1000, 12)
            entry = e.sign(fm, proposal)
            try:
                after = fm.snapshot()
                assert after['balance'] == snapshot['balance'] + 1000
                assert len(after['debts']) == len(snapshot['debts']) + 1
                loan = after['debts'][-1]
                assert loan['original'] == 1000 and loan['monthly'] == proposal['monthly']
                renegotiation = e.offer(after, 0, 6, debt=loan)
                renamed = e.sign(fm, renegotiation)
                try:
                    assert len(fm.debt_rows()) == len(after['debts'])
                    assert fm.debt_rows()[-1]['monthly'] == renegotiation['monthly']
                finally:
                    fm.undo(renamed)
                paid = fm.repay(loan['index'], fm.debt_rows()[-1]['raw'])
                try:
                    assert fm.mem.number(fm.finance+20) == snapshot['balance']
                    assert fm.debt_rows()[-1]['original'] == 0
                finally:
                    fm.undo(paid)
            finally:
                fm.undo(entry)
            assert fm.snapshot() == snapshot, 'A carreira não voltou ao estado anterior'
        native.save_json(native.DATA/'validacao-emprestimos.json', dict(ok=True,process=fm.process,
            date=snapshot['date'],restored=True,tests=['criar contrato','crédito e lista nativa','renegociar','quitar','rollback completo'],proposal=proposal))
        print('OK: contrato criado na memória real, renegociado, quitado e totalmente desfeito; carreira restaurada.')
    finally:
        fm.close()


if __name__ == '__main__':
    import sys
    check()
    if '--live' in sys.argv:
        live()
