"""Validações diagnósticas puras; não autorizam leitura nem operações no FM."""
import struct

def vector_bounds(raw,limit=100):
    if len(raw)!=24:raise ValueError('Vetor truncado')
    a,b,c=struct.unpack('<QQQ',raw)
    if a==b==c==0:return 0,0
    if not 0x10000<=a<=b<=c<0x7fffffffffff or any(x%8 for x in (a,b,c)) or (c-a)//8>limit:
        raise ValueError('Vetor incompatível')
    return a,(b-a)//8

def text_candidate(raw,max_bytes=80):
    if len(raw)>max_bytes:raise ValueError('Limite de texto excedido')
    text=raw.split(b'\0',1)[0].decode('utf-8',errors='strict')
    if not 2<=len(text)<=48 or any(not(c.isalpha() or c in " -.'") for c in text):raise ValueError('Texto incompatível')
    # Texto bem formado é candidato, nunca identidade comprovada.
    return {'text':text,'status':'HYPOTHESIS'}

def evidence(identifier,description,observations=0,matches=0,divergences=0):
    if not identifier or not description or any(type(n) is not int or n<0 for n in (observations,matches,divergences)):
        raise ValueError('Evidência inválida')
    return dict(id=identifier,description=description,observations=observations,matches=matches,
                divergences=divergences,status='OBSERVED' if observations else 'HYPOTHESIS')
