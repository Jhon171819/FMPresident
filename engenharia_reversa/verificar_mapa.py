"""Confere as descobertas diretamente nos bytes do arquivo, sem executar o FM."""
from pathlib import Path
import hashlib
import json
import struct
import sys
from analisar_executavel import PE

exe=Path(sys.argv[1])
root=Path(__file__).resolve().parent/'mapa'
pe=PE(exe)
report=json.loads((root/'executavel.json').read_text(encoding='utf-8'))
assert hashlib.sha256(pe.data).hexdigest()==report['sha256'],'O executável mudou.'
assert pe.machine==0x8664 and pe.image_size==356016128
for section in pe.sections:
    if section['raw_size']:
        rva=section['rva'];off=section['raw_offset']
        assert pe.offset(rva)==off and pe.rva_at(off)==rva
assert pe.rtti(0x4fdcdf8)['class_name']=='.?AVCLUB@db@@'
assert pe.rtti(0x4a56998)['class_name']=='.?AVCLUB_FINANCE@db@@'
assert pe.rtti(0x4a0fa28)['class_name']=='.?AVFACILITY_UPGRADE@db@@'
signatures=json.loads((root/'assinatura-data.json').read_text())
assert len(signatures)==1
s=signatures[0];ins=s['instruction_rva'];raw=pe.read(ins,13)
assert raw[:5]==bytes.fromhex('ff100fb705') and raw[9:]==bytes.fromhex('89c181e1')
assert ins+9+struct.unpack_from('<i',raw,5)[0]==s['date_rva']==0x54623f0
# Funções curtas cujo efeito foi verificado instrução por instrução.
assert pe.read(0xffa3b0,13)==bytes.fromhex('0191a40700000191a8070000c3')
expected=bytes.fromhex('89d0f7d80f4cc2014114018130030000018150050000c3')
assert pe.read(0x38810c0,len(expected))==expected
print('OK: hash, tradução RVA/arquivo, três RTTIs, assinatura de data e dois métodos financeiros.')
