"""Contratos de crédito do clube: proposta, parcelas e dados nativos do FM23.

Não executa código remoto. Reserva apenas blocos livres nos alocadores existentes,
com o jogo suspenso durante a transação e rollback dos bytes em caso de falha.
"""
import calendar
import hashlib
import math
import struct
from datetime import date

import fm23 as native

HASH = 'd0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1'
LOAN_POOL = 0x5497bd8
ALLOCATOR = 0x54753c8
MANAGED_KINDS = {1}


def _slist_layout():
    """Verifica o layout contra a API do próprio Windows, em memória local."""
    C = native.C
    for name, args, result in [('RtlInitializeSListHead', [C.c_void_p], None),
            ('RtlInterlockedPushEntrySList', [C.c_void_p, C.c_void_p], C.c_void_p),
            ('RtlInterlockedPopEntrySList', [C.c_void_p], C.c_void_p)]:
        fn = getattr(native.nt, name)
        fn.argtypes, fn.restype = args, result
    buffer = C.create_string_buffer(256)
    base = (C.addressof(buffer) + 15) & ~15
    native.nt.RtlInitializeSListHead(base)
    for offset in (32, 64, 96):
        native.nt.RtlInterlockedPushEntrySList(base, base + offset)
    for _ in range(3):
        lo, hi = struct.unpack('<QQ', C.string_at(base, 16))
        head = hi & ~15
        next_head = struct.unpack('<Q', C.string_at(head, 8))[0]
        expected = struct.pack('<QQ', lo - 1, (hi & 15) | next_head)
        if native.nt.RtlInterlockedPopEntrySList(base) != head or C.string_at(base, 16) != expected:
            raise ValueError('O alocador desta versão do Windows ainda não foi validado.')


def _ensure_idle(fm):
    """Recusa pausar no meio de uma operação nativa de dívida/alocação."""
    C, W, k = native.C, native.W, native.k
    class ThreadEntry(C.Structure):
        _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('tid', W.DWORD), ('pid', W.DWORD),
                    ('priority', W.LONG), ('delta', W.LONG), ('flags', W.DWORD)]
    k.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    k.CreateToolhelp32Snapshot.restype = W.HANDLE
    k.Thread32First.argtypes = [W.HANDLE, C.POINTER(ThreadEntry)]
    k.Thread32Next.argtypes = k.Thread32First.argtypes
    k.OpenThread.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    k.OpenThread.restype = W.HANDLE
    k.GetThreadContext.argtypes = [W.HANDLE, C.c_void_p]
    ranges = [(0xae21e0, 0xae4400), (0xae5150, 0xae5c80), (0x2c38c20, 0x2c38da6),
              (0x126fcb90, 0x126fcbcb), (0x37e08d0, 0x37e0946), (0x12847c50, 0x12847dbd)]
    def critical(address):
        return any(low <= address - fm.base < high for low, high in ranges)
    snapshot = k.CreateToolhelp32Snapshot(4, 0)
    if snapshot == C.c_void_p(-1).value:
        raise OSError('Não foi possível verificar o estado do FM.')
    try:
        entry = ThreadEntry()
        entry.size = C.sizeof(entry)
        available = k.Thread32First(snapshot, C.byref(entry))
        while available:
            if entry.pid == fm.process['pid']:
                thread = k.OpenThread(0x48, False, entry.tid)
                if not thread:
                    raise OSError('Não foi possível verificar um thread do FM. Tente novamente com o jogo parado.')
                try:
                    buffer = C.create_string_buffer(1248)
                    context = (C.addressof(buffer) + 15) & ~15
                    C.c_uint32.from_address(context + 48).value = 0x100001
                    if not k.GetThreadContext(thread, context):
                        raise OSError('Não foi possível consultar o processamento do FM.')
                    sp, ip = C.c_uint64.from_address(context + 152).value, C.c_uint64.from_address(context + 248).value
                    words = [ip]
                    if sp:
                        size = min(4096 - sp % 4096, 2048) // 8 * 8
                        stack = fm.mem.read(sp, size)
                        words.extend(struct.unpack('<' + 'Q' * (size // 8), stack))
                    if any(critical(word) for word in words):
                        raise ValueError('O FM está processando uma operação financeira. Pare o jogo e tente novamente.')
                finally:
                    k.CloseHandle(thread)
            available = k.Thread32Next(snapshot, C.byref(entry))
    finally:
        k.CloseHandle(snapshot)


def month(value, delta):
    y, m = divmod(value.year * 12 + value.month - 1 + delta, 12)
    return date(y, m + 1, min(value.day, calendar.monthrange(y, m + 1)[1]))


def payment(principal, rate, months):
    if type(principal) is not int or not 1000 <= principal <= 100_000_000:
        raise ValueError('Informe um empréstimo entre £1.000 e £100.000.000.')
    if type(months) is not int or not 6 <= months <= 120:
        raise ValueError('O prazo deve estar entre 6 e 120 parcelas mensais.')
    if type(rate) not in (int, float) or not math.isfinite(rate) or not 0 <= rate <= 100:
        raise ValueError('Informe uma taxa anual entre 0 e 100%.')
    f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
    rate = f32(rate)
    r = rate / 100 / 12
    if r and 1 + r == 1:
        raise ValueError('Taxa pequena demais. Use zero para crédito sem juros.')
    monthly = int(principal / ((1 - 1 / math.pow(1 + r, months)) / r)) if r else principal // months
    interest = monthly - int(f32(f32(principal) / f32(months)))
    if monthly * months > 2_000_000_000 or not 0 <= interest <= monthly:
        raise ValueError('O custo total excede a faixa de valores suportada.')
    return monthly, interest


def manageable(row):
    return row['conditional'] == 0 and row['original'] > 0 and (row['source'] in MANAGED_KINDS or row['interest_only'])


def outstanding(row, today):
    if not manageable(row):
        raise ValueError('Esta modalidade possui condições especiais e não pode ser renegociada pelo aplicativo.')
    if date.fromisoformat(row['end']) < today:
        raise ValueError('Este contrato já venceu. Atualize o painel depois do processamento do FM.')
    if row['interest_only'] or today < date.fromisoformat(row['start']):
        return row['original']
    # Mesmo ramo do getter nativo 0x3ba0ee0: meses aproximados de 30 dias.
    months = max(1, (date.fromisoformat(row['end']) - today).days // 30)
    return min(row['original'], max(0, row['monthly'] - row['interest']) * months)


def offer(snapshot, principal, months, requested_rate=None, debt=None):
    today = date.fromisoformat(snapshot['date'])
    credit = snapshot.get('credit', {})
    base = credit.get('rate', 13.75)
    reputation = credit.get('reputation', 5000)
    if debt:
        principal = outstanding(debt, today)
    risk = 1 + max(0, 6500 - reputation) / 10000 + max(0, months - 36) / 300
    initial = round(min(90, max(1, base * risk)), 2)
    floor = round(max(0.5, initial * .75), 2)
    desired = initial if requested_rate is None else requested_rate
    if type(desired) not in (int, float) or not math.isfinite(desired) or not 0 <= desired <= 100:
        raise ValueError('Revise a taxa anual desejada.')
    rate = round(max(floor, desired), 2)
    monthly, interest = payment(principal, rate, months)
    first = month(today.replace(day=1), 1)
    end = month(first, months - 1)
    return dict(uid=native.UID, date=today.isoformat(), principal=principal, months=months,
                rate=rate, requested_rate=desired, minimum_rate=floor, monthly=monthly,
                interest=interest, first=first.isoformat(), end=end.isoformat(),
                total=monthly * months, counter=rate > desired,
                debt=dict(index=debt['index'], addr=debt['addr'], raw=debt['raw']) if debt else None)


def _build(fm):
    if getattr(fm, '_loans_verified', False):
        return
    with open(fm.process['path'], 'rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != HASH:
        raise ValueError('Este executável do FM23 não corresponde à versão validada para empréstimos.')
    _slist_layout()
    fm._loans_verified = True


def _change(fm, label, addr, after):
    return dict(label=label, addr=addr, before=fm.mem.read(addr, len(after)).hex(), after=after.hex())


def _contract_block(fm, changes):
    m = fm.mem
    pool = fm.base + LOAN_POOL
    raw = m.read(pool, 80)
    head = struct.unpack_from('<Q', raw, 40)[0]
    free, used, stride, initial, growth = struct.unpack_from('<IIIII', raw, 48)
    if stride != 28 or initial != growth or not 1 <= growth <= 4096 or not head or not free:
        raise ValueError('O FM está sem reserva disponível para um novo contrato. Reabra a carreira e tente novamente.')
    start, end = struct.unpack_from('<QQ', raw, 16)
    if not start or not 0 < end - start <= 4096 or (end - start) % 8:
        raise ValueError('Reserva de contratos incompatível com a versão validada.')
    chunks = struct.unpack('<' + 'Q' * ((end - start) // 8), m.read(start, end - start))
    if not any(chunk <= head < chunk + stride * growth and (head - chunk) % stride == 0 for chunk in chunks):
        raise ValueError('O bloco de contrato não pertence à reserva nativa.')
    next_head = m.pointer(head)
    if next_head and not any(chunk <= next_head < chunk + stride * growth and (next_head - chunk) % stride == 0 for chunk in chunks):
        raise ValueError('Lista de reserva de contratos inconsistente.')
    changes.append(_change(fm, 'Reserva nativa de contrato', pool + 40, struct.pack('<QII', next_head, free - 1, used + 1)))
    return head


def _vector_block(fm, size, changes):
    m = fm.mem
    manager = m.pointer(fm.base + ALLOCATOR)
    if m.number(manager + 52, 'B') != 1:
        raise ValueError('O alocador do FM não está no modo validado para empréstimos.')
    start, end = struct.unpack('<QQ', m.read(manager + 24, 16))
    if not start or end - start <= size * 8:
        raise ValueError('Reserva da lista de dívidas indisponível.')
    pool = m.pointer(start + size * 8)
    raw = m.read(pool, 128)
    allocation = struct.unpack_from('<I', raw, 80)[0]
    prefix = struct.unpack_from('<I', raw, 120)[0]
    lo, hi = struct.unpack_from('<QQ', raw, 32)
    head = hi & ~15
    if prefix or allocation < size or allocation > 4096 or not lo & 65535 or not head:
        raise ValueError('O FM está sem reserva disponível para a lista de dívidas. Tente novamente depois de reabrir a carreira.')
    next_head = m.pointer(head)
    if next_head and (next_head < 0x10000 or next_head % 16):
        raise ValueError('Lista de memória livre incompatível.')
    # Layout x64 conferido contra RtlInterlockedPopEntrySList no Windows local.
    changes.append(_change(fm, 'Reserva nativa da lista', pool + 32, struct.pack('<QQ', lo - 1, (hi & 15) | next_head)))
    if raw[72]:
        changes.append(fm.change('Uso da reserva de listas', pool + 64, 'I', m.number(pool + 64, 'I') + 1))
    return head


def sign(fm, proposal):
    fm.guard.require_full()
    fm.career_guard.require()
    _build(fm)
    # O congelamento externo inclui a leitura das reservas e o journal durável.
    # Assim nenhum thread do FM pode disputar os blocos entre o plano e o commit.
    with native.LOCK, fm.mem.paused():
        fm.validate()
        _ensure_idle(fm)
        today = fm.date()
        if proposal['date'] != today.isoformat() or proposal['uid'] != native.UID:
            raise ValueError('A data da carreira mudou. Solicite uma nova proposta antes de assinar.')
        monthly, interest = payment(proposal['principal'], proposal['rate'], proposal['months'])
        if (monthly, interest) != (proposal['monthly'], proposal['interest']):
            raise ValueError('A proposta foi alterada. Solicite novamente as condições.')
        first = month(today.replace(day=1), 1)
        end = month(first, proposal['months'] - 1)
        if (first.isoformat(), end.isoformat()) != (proposal['first'], proposal['end']):
            raise ValueError('Calendário da proposta inconsistente.')
        changes = []
        raw = struct.pack('<iiii', proposal['principal'], monthly, interest, 0) + native.pack_date(end) + native.pack_date(first) + bytes([1, 1, 0, 0])
        rows = fm.debt_rows()
        debt = proposal.get('debt')
        if debt:
            row = next((r for r in rows if r['addr'] == debt['addr'] and r['index'] == debt['index']), None)
            if not row or row['raw'] != debt['raw'] or outstanding(row, today) != proposal['principal']:
                raise ValueError('O empréstimo mudou. Atualize a seleção e renegocie novamente.')
            address = row['addr']
            changes.append(_change(fm, 'Novas condições da dívida', address, raw))
            title = 'Renegociação de empréstimo financeiro'
        else:
            if len(rows) >= 100:
                raise ValueError('O limite de contratos suportado foi atingido.')
            address = _contract_block(fm, changes)
            changes.append(_change(fm, 'Novo contrato financeiro', address, raw))
            vector = fm.info + 80
            before = fm.mem.read(vector, 24)
            start, finish, cap = struct.unpack('<QQQ', before)
            if start and finish + 8 <= cap:
                changes.append(_change(fm, 'Inclusão do empréstimo na lista', finish, struct.pack('<Q', address)))
                after = struct.pack('<QQQ', start, finish + 8, cap)
            else:
                capacity = max(8, min(100, max(len(rows) + 1, (cap - start) // 4)))
                dest = _vector_block(fm, capacity * 8, changes)
                pointers = [r['addr'] for r in rows] + [address]
                content = struct.pack('<' + 'Q' * len(pointers), *pointers).ljust(capacity * 8, b'\0')
                changes.append(_change(fm, 'Conteúdo da nova lista de dívidas', dest, content))
                after = struct.pack('<QQQ', dest, dest + 8 * len(pointers), dest + capacity * 8)
                # ponytail: vetor anterior fica reservado para desfazer; menos de 2 KiB
                # nas expansões até 100 dívidas, recuperado com o encerramento do FM.
            changes.append(dict(label='Lista nativa de dívidas', addr=vector, before=before.hex(), after=after.hex()))
            for offset, label in ((20, 'Crédito no caixa'), (0x324, 'Entrada de empréstimos A'), (0x544, 'Entrada de empréstimos B')):
                changes.append(fm.change(label, fm.finance + offset, 'i', fm.mem.number(fm.finance + offset) + proposal['principal']))
            accumulated = fm.mem.number(fm.finance + 0x7e4) + proposal['principal']
            changes.append(fm.change('Financiamento acumulado', fm.finance + 0x7e4, 'i', accumulated if accumulated <= 0x7fffffff else 0x73333300))
            title = 'Contratação de empréstimo financeiro'
        return fm.transaction(title, changes, dict(expected_day=proposal['date'], loan=proposal, contract=raw.hex(), address=address))


def repay(fm, index, expected):
    fm.guard.require_full()
    fm.career_guard.require()
    with native.LOCK, fm.mem.paused():
        fm.validate()
        _ensure_idle(fm)
        row = next((r for r in fm.debt_rows() if r['index'] == index), None)
        if not row or row['raw'] != expected:
            raise ValueError('O contrato mudou. Atualize a seleção.')
        today = fm.date()
        cost = outstanding(row, today)
        balance = fm.mem.number(fm.finance + 20)
        if not cost or balance < cost:
            raise ValueError('Caixa insuficiente ou empréstimo sem saldo para quitar.')
        before = bytes.fromhex(row['raw'])
        after = bytearray(before)
        after[:16] = b'\0' * 16
        after[16:20] = native.pack_date(today, before[16:20])
        if date.fromisoformat(row['start']) > today:
            after[20:24] = native.pack_date(today, before[20:24])
        changes = [_change(fm, 'Encerramento da dívida', row['addr'], bytes(after)), fm.change('Quitação no caixa', fm.finance + 20, 'i', balance - cost)]
        for offset in (0x284, 0x4a4):
            changes.append(fm.change('Pagamento de dívida', fm.finance + offset, 'i', fm.mem.number(fm.finance + offset) + cost))
        if before[25] == 0:
            for offset in (0x33c, 0x55c):
                changes.append(fm.change('Ajuste contábil da quitação', fm.finance + offset, 'i', fm.mem.number(fm.finance + offset) - cost))
        return fm.transaction('Quitação antecipada de empréstimo', changes, dict(cost=cost, expected_day=today.isoformat()))
