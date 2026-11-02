"""Verifica evidências no fm.exe e o protótipo offline; nunca abre o jogo.

Uso: py verificar_emprestimos.py caminho/fm.exe --capstone caminho/re-tools
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from analisar_executavel import PE


def main(exe, capstone):
    sys.path.insert(0, capstone)
    import capstone as cs
    from emprestimos.modelo import simular
    out = Path(__file__).resolve().parent / 'emprestimos'
    pe = PE(exe)
    assert hashlib.sha256(pe.data).hexdigest() == 'd0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1'
    assert pe.rtti(0x49fe648)['class_name'] == '.?AVGAME_CLUB_FINANCE@@'
    assert pe.rtti(0x4fdeef8)['class_name'] == '.?AVSTARTING_CLUB_DEBT@db@@'
    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    md.detail = True
    constructor = list(md.disasm(pe.read(0x3ba0e80, 0x48), pe.image_base + 0x3ba0e80))
    writes = {o.mem.disp: o.size for ins in constructor if ins.mnemonic == 'mov'
              for o in ins.operands[:1] if o.type == cs.x86.X86_OP_MEM and o.mem.base == cs.x86.X86_REG_RAX}
    assert writes == {0: 4, 4: 4, 8: 4, 12: 4, 16: 4, 20: 4, 24: 1, 25: 1, 26: 1}
    for rva, value in ((0x48cbcc0, 100.0), (0x4981720, 12.0), (0x48cbf50, 1.0)):
        assert struct.unpack('<d', pe.read(rva, 8))[0] == value
    # Compara bytes de cada instrução citada no relatório com o binário atual.
    expected = {
        0xae5988: 'mov ecx, 0x1c',
        0xae59d2: 'call 0x143ba0e80',
        0xae59df: 'call 0x1437e0770',
        0xae2acc: 'mov edx, dword ptr [rax + rcx*4 + 4]',
        0xae2ad5: 'call 0x14387f5a0',
        0x6f2dcc2: 'add dword ptr [rsi + 0x14], edi',
        0x6f2dcc5: 'add dword ptr [rsi + 0x324], edi',
        0x6f2dccb: 'add dword ptr [rsi + 0x544], edi',
    }
    for rva, text in expected.items():
        i = next(md.disasm(pe.read(rva, 15), pe.image_base + rva))
        assert i.mnemonic + ' ' + i.op_str == text, (hex(rva), i.mnemonic, i.op_str)
    samples = json.loads((out / 'amostras-carreira.json').read_text(encoding='utf-8'))
    assert samples['mode'].startswith('OpenProcess(0x410)')
    assert sum(samples['types'].values()) == samples['distinct_records']
    for row in samples['samples']:
        raw = bytes.fromhex(row['raw'])
        assert len(raw) == 28
        assert struct.unpack_from('<iiii', raw) == tuple(row[k] for k in ('original', 'monthly', 'interest', 'conditional'))
        assert tuple(raw[24:27]) == (row['kind'], row['flag25'], row['interest_only'])
    amortizado = simular(1_000_000, 12, 24)
    assert (amortizado['campo_parcela'], amortizado['campo_juros']) == (47073, 5407)
    assert amortizado['total_nominal'] == 1_129_752
    assert simular(1_000_000, 0, 24)['campo_parcela'] == 41666
    balao = simular(1_000_000, 12, 24, True)
    assert balao['pagamento_periodico'] == 9999
    assert balao['principal_no_vencimento'] == 1_000_000
    for args in [(True, 12, 24), (0, 12, 24), (1000, float('nan'), 24),
                 (1000, float('inf'), 24), (1000, -1, 24), (1000, 12, 0),
                 (1000, 12, 651), (2_000_000_000, 100, 650)]:
        try:
            simular(*args)
        except ValueError:
            continue
        raise AssertionError(('Entrada deveria ser recusada', args))
    print(f"OK: hash, RTTI, layout de 28 bytes, constantes, chamadas e contabilidade; {len(samples['samples'])} amostras; simulação offline e limites.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe')
    parser.add_argument('--capstone', required=True)
    args = parser.parse_args()
    main(args.exe, args.capstone)
