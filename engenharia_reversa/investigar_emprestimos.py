"""Mapa estático de dívidas bancárias do FM23, sem executar ou modificar o jogo.

Reutiliza o leitor PE, RTTI e grafo existentes. Exemplos no relatório EMPRESTIMOS.md.
As referências por padrão de bytes são candidatas até validar a instrução.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from analisar_executavel import PE, dump
from investigar_gestao import graph
from mapear_classes import main as map_classes


NAMES = [
    '.?AVSTARTING_CLUB_DEBT@db@@',
    '.?AVPROCESS_CLUB_LOANS_AND_DEBTS@@',
    '.?AVPOST_PROCESS_CLUB_LOANS@@',
    '.?AVCLUB_RESTRUCTURES_DEBT@@',
    '.?AVCLUB_REQUIRED_TO_START_PAYING_CLUB_LOAN_NEWS@@',
    '.?AVLOAN_REPAYMENT_NEWS@@',
    '.?AVFINANCES_DEBT_LOAN_PANEL@@',
    '.?AVGAME_CLUB_FINANCE_BASE@@',
]
FOCUS = re.compile(
    r'bank.?loan|club.?debt|club.?loan|loans.and.debts|repay|refinanc|'
    r'restructur.{0,30}debt|debt.{0,30}restructur|interest.rate|'
    r'interest.only|loan.interest|debt.interest|monthly.repayment', re.I)


def xrefs(pe, targets):
    """RIP-relative MOV/LEA: cobertura limitada e registrada no relatório."""
    result = []
    pattern = re.compile(rb'[\x48\x4c][\x8b\x8d\x89][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....', re.S)
    for sec in pe.sections:
        if not sec['flags'] & 0x20000000:
            continue
        raw = pe.data[sec['raw_offset']:sec['raw_offset'] + sec['raw_size']]
        for m in pattern.finditer(raw):
            rva = sec['rva'] + m.start()
            target = rva + 7 + struct.unpack_from('<i', m.group(), 3)[0]
            if target in targets:
                result.append(dict(rva=rva, target=target, name=targets[target],
                                   range=pe.function(rva), candidate=True))
    return result


def save_graphs(pe, md, cs, chosen, out, stem):
    graphs = []
    asm = []
    for rva, labels in sorted(chosen.items()):
        g = graph(pe, md, cs, rva, max_instructions=6000, max_blocks=600)
        g['labels'] = labels
        graphs.append(g)
        asm.append(f'\n; RVA 0x{rva:x}: ' + ' / '.join(labels))
        asm.extend(f"{pe.image_base+i['rva']:016x} {i['bytes']:30} {i['mnemonic']:9} {i['operands']}"
                   for i in g['instructions'])
    dump(out / (stem + '.json'), graphs)
    (out / (stem + '.asm')).write_text('\n'.join(asm), encoding='utf-8')
    return graphs


def main(exe, out, capstone):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pe = PE(exe)
    names = list(NAMES)
    strings = []
    for m in re.finditer(rb'[\x20-\x7e]{4,600}\x00', pe.data):
        value = m.group()[:-1].decode('ascii')
        if FOCUS.search(value):
            rva = pe.rva_at(m.start())
            if rva is not None:
                strings.append(dict(rva=rva, text=value))
            if value.startswith('.?AV') and value not in names:
                names.append(value)
    dump(out / 'catalogo-strings.json', strings)
    map_classes(exe, out, capstone, names, 'classes')
    sys.path.insert(0, capstone)
    import capstone as cs
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    md.detail = True
    classes = json.loads((out / 'classes.json').read_text(encoding='utf-8'))
    targets = {s['rva']: s['text'] for s in strings if not s['text'].startswith('.?')}
    chosen = {}
    for c in classes:
        for table in c['vtables']:
            targets[table['rva']] = 'vtable:' + c['class_name']
            if table['object_offset'] == 0:
                for f in table['functions']:
                    # UI e motor financeiro são grandes: começar pelas referências.
                    if c['class_name'] in NAMES[:6] or 'PROCESS_CLUB_LOANS' in c['class_name']:
                        chosen.setdefault(f['rva'], []).append(c['class_name'] + f":slot{f['slot']}")
    refs = xrefs(pe, targets)
    for ref in refs:
        if ref['range']:
            chosen.setdefault(ref['range'][0], []).append('xref:' + ref['name'])
    graphs = save_graphs(pe, md, cs, chosen, out, 'fluxos')
    reached = {i['rva'] for g in graphs for i in g['instructions']}
    for ref in refs:
        ref['boundary_reached'] = ref['rva'] in reached
    dump(out / 'referencias.json', refs)
    manifest = dict(file=str(pe.path.resolve()), sha256=hashlib.sha256(pe.data).hexdigest(),
                    size=len(pe.data), image_base=hex(pe.image_base), classes=len(classes),
                    strings=len(strings), references=len(refs), graphs=len(graphs),
                    bounded_graphs=sum(g['bounded'] for g in graphs),
                    mode='static-read-only', capstone=cs.__version__)
    dump(out / 'manifesto.json', manifest)
    print(json.dumps(manifest, indent=2), flush=True)


def trace(exe, out, capstone, addresses, stem, callers=False):
    sys.path.insert(0, capstone)
    import capstone as cs
    pe = PE(exe)
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    md.detail = True
    chosen = {rva: ['alvo explícito'] for rva in addresses}
    refs = []
    if callers:
        for sec in pe.sections:
            if not sec['flags'] & 0x20000000:
                continue
            raw = pe.data[sec['raw_offset']:sec['raw_offset'] + sec['raw_size']]
            for m in re.finditer(rb'[\xe8\xe9]....', raw, re.S):
                rva = sec['rva'] + m.start()
                target = rva + 5 + struct.unpack_from('<i', m.group(), 1)[0]
                if target in addresses:
                    interval = pe.function(rva)
                    refs.append(dict(rva=rva, target=target, range=interval, candidate=True))
                    if interval:
                        chosen.setdefault(interval[0], []).append(f'caller:0x{target:x}')
    graphs = save_graphs(pe, md, cs, chosen, Path(out), stem)
    reached = {i['rva']: i for g in graphs for i in g['instructions']}
    for ref in refs:
        ins = reached.get(ref['rva'])
        ref['boundary_reached'] = bool(ins and ins['mnemonic'] in ('call', 'jmp'))
    dump(Path(out) / (stem + '-referencias.json'), refs)
    print(json.dumps(dict(graphs=len(graphs), references=len(refs),
                          reached=sum(r['boundary_reached'] for r in refs),
                          bounded=sum(g['bounded'] for g in graphs)), indent=2))


def live(out):
    """Amostras de contratos existentes; handle sem permissão de escrita."""
    from collections import Counter
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from fm23 import FM, Memory, k, process_info, read_json, fm_date, VTABLE_RVA
    fm = FM.__new__(FM)
    fm.process = process_info()
    fm.base = fm.process['base']
    fm.mem = Memory.__new__(Memory)
    fm.mem.handle = k.OpenProcess(0x410, False, fm.process['pid'])
    if not fm.mem.handle:
        raise OSError('Não foi possível abrir o processo para leitura.')
    root = Path(__file__).resolve().parent.parent
    fm.club = read_json(root / 'dados/conexao.json', {}).get('club', 0)
    try:
        try:
            fm.validate()
        except (ValueError, OSError):
            fm.club = fm.find_club()
            fm.validate()
        result = dict(process=fm.process, club=hex(fm.club), info=hex(fm.info),
                      finance=hex(fm.finance), date=fm.date().isoformat(),
                      debts=fm.debt_rows(), balance=fm.mem.number(fm.finance + 20),
                      vector=fm.mem.read(fm.info + 80, 24).hex(),
                      mode='OpenProcess(0x410): read-only; no writes, calls or suspension')
        dump(Path(out) / 'sessao-leitura.json', result)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        types = Counter()
        examples = []
        seen = set()
        clubs = 0
        needle = struct.pack('<Q', fm.base + VTABLE_RVA)
        for base, size in fm.mem.regions():
            for off in range(0, size, 4 * 1024 * 1024):
                try:
                    data = fm.mem.read(base + off, min(4 * 1024 * 1024, size - off))
                except OSError:
                    continue
                pos = data.find(needle)
                while pos >= 0:
                    addr = base + off + pos
                    pos = data.find(needle, pos + 1)
                    if addr % 8:
                        continue
                    try:
                        header = fm.mem.read(addr, 336)
                        uid = struct.unpack_from('<I', header, 12)[0]
                        info = struct.unpack_from('<Q', header, 248)[0]
                        finance = struct.unpack_from('<Q', header, 328)[0]
                        if not uid or fm.mem.pointer(finance + 8) != addr:
                            continue
                        if fm.mem.pointer(finance) != fm.base + 0x4a56998:
                            continue
                        loans = fm.vector(info + 80, 100)
                        if loans:
                            clubs += 1
                        for loan in loans:
                            if loan in seen:
                                continue
                            raw = fm.mem.read(loan, 28)
                            original, monthly, interest, conditional = struct.unpack_from('<iiii', raw)
                            start, end = fm_date(raw[20:24]), fm_date(raw[16:20])
                            if any(not 0 <= v <= 2_000_000_000 for v in (original, monthly, interest, conditional)):
                                continue
                            if end < start or raw[24] > 14 or raw[26] > 1:
                                continue
                            seen.add(loan)
                            key = f'type={raw[24]},flag25={raw[25]},interest_only={raw[26]}'
                            types[key] += 1
                            if types[key] <= 3:
                                examples.append(dict(club_uid=uid, addr=hex(loan), raw=raw.hex(),
                                    original=original, monthly=monthly, interest=interest,
                                    conditional=conditional, start=start.isoformat(), end=end.isoformat(),
                                    kind=raw[24], flag25=raw[25], interest_only=raw[26]))
                    except (ValueError, OSError, struct.error):
                        continue
        census = dict(process=fm.process, date=result['date'], mode=result['mode'],
                      clubs_with_loans=clubs, distinct_records=len(seen), types=dict(types), samples=examples,
                      limitation='Aligned club vtables and backlink filters; no exhaustive identity proof or calendar advance.')
        dump(Path(out) / 'amostras-carreira.json', census)
        print(json.dumps(dict(clubs=clubs, contracts=len(seen), types=dict(types)), indent=2), flush=True)
    finally:
        fm.mem.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('exe')
    p.add_argument('--out', required=True)
    p.add_argument('--capstone', required=True)
    p.add_argument('--trace', nargs='+', type=lambda v: int(v, 0))
    p.add_argument('--stem', default='auxiliares')
    p.add_argument('--callers', action='store_true')
    p.add_argument('--live', action='store_true')
    a = p.parse_args()
    if a.live:
        live(a.out)
    elif a.trace:
        trace(a.exe, a.out, a.capstone, a.trace, a.stem, a.callers)
    else:
        main(a.exe, a.out, a.capstone)
