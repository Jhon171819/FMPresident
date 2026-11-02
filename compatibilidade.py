"""CP-01: identificação conservadora de build; nunca homologa automaticamente."""
from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import os
import struct
from contratos_dados import Evidence, ProcessIdentity, Source, Verification

class State(str, Enum):
    VERIFIED = 'VERIFIED'
    UNSUPPORTED = 'UNSUPPORTED'
    UNVERIFIED = 'UNVERIFIED'
    ERROR = 'ERROR'
    DISCONNECTED = 'DISCONNECTED'

@dataclass(frozen=True)
class Profile:
    name: str
    version: str
    image_size: int
    digest: str
    machine: int
    anchors: tuple
    homologated: bool = False

PROFILES = (Profile('fm23-23.2.0-1771058', '23.2.0+1771058', 356016128,
    'd0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1', 0x8664,
    ((0x3c38ba3, bytes.fromhex('ff100fb7054498820189c181e1ff010000410fb7969a0000006639152f988201')),
     (0x382bf20, bytes.fromhex('41574156565755534883ec4889d74889cee89aaaf9ff85ff0f84d20000008b05')),
     (0x2c3db90, bytes.fromhex('29ca4881fa001000007218488b41f84883c1f84829c14883f92073324883c227'))), homologated=True),)

@dataclass(frozen=True)
class Result:
    state: State
    process: ProcessIdentity | None = None
    profile: str | None = None
    reason: str = ''
    module_samples_match: bool = False
    unknown: tuple = ('equivalência integral da imagem carregada',)

    def diagnostic(self):
        # Explicit allowlist: no executable path, PID, raw exception or addresses.
        return {'status': self.state.value, 'versao': self.process.version if self.process else None,
                'perfil': self.profile, 'motivo': self.reason,
                'amostras_modulo_correspondem': self.module_samples_match,
                'desconhecido': list(self.unknown)}

    def diagnostic_json(self):
        try: return json.dumps(self.diagnostic(), ensure_ascii=False)
        except (TypeError, ValueError, OverflowError):
            return '{"status":"ERROR","motivo":"Falha ao serializar diagnóstico"}'

class CompatibilityError(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__(f'Build bloqueada [{result.state.value}] • FM {result.process.version if result.process else "desconhecido"} • perfil {result.profile or "não identificado"}: {result.reason} Reconecte após verificar a instalação.')

def stat_key(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)

def fingerprint(path):
    with open(path, 'rb') as f:
        before = stat_key(os.fstat(f.fileno()))
        header = f.read(4096)
        if len(header) < 64 or header[:2] != b'MZ': raise ValueError('PE inválido')
        off = struct.unpack_from('<I', header, 60)[0]
        if off + 6 > len(header) or header[off:off+4] != b'PE\0\0': raise ValueError('PE inválido')
        machine = struct.unpack_from('<H', header, off+4)[0]
        f.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024*1024), b''): digest.update(chunk)
        after = stat_key(os.fstat(f.fileno()))
    if before != after or after != stat_key(os.stat(path)): raise ValueError('Arquivo alterado durante identificação')
    return digest.hexdigest(), machine, after

def same_path(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))

class BuildGuard:
    def __init__(self, info, probe):
        self.info = dict(info)
        self.probe = probe
        self.result = Result(State.DISCONNECTED, reason='Ainda não identificado.')
        self.file_key = None
        self.profile = None
        self.verify()

    def fail(self, state, reason):
        self.result = replace(self.result, state=state, reason=reason)
        raise CompatibilityError(self.result)

    def instance(self):
        current = self.probe.identity()
        required = ('pid', 'started', 'path', 'base', 'size', 'version')
        if any(not self.info.get(k) for k in required): raise ValueError('Metadados incompletos')
        if any(current[k] != self.info[k] for k in ('pid', 'started', 'base', 'size')) or not same_path(current['path'], self.info['path']):
            raise ValueError('Identidade da instância ou módulo mudou')
        return current

    def verify(self):
        try:
            self.instance()
            digest, machine, key = fingerprint(self.info['path'])
            identity = ProcessIdentity(self.info['pid'], str(self.info['started']), self.info['version'], self.info['size'],
                self.info['path'], Evidence(digest, Source.LOCAL_STORAGE, Verification.VERIFIED, 'SHA-256 do arquivo em disco'), Verification.UNVERIFIED)
            self.result = Result(State.UNVERIFIED, identity, reason='Verificação em andamento.')
            self.instance()
            if stat_key(os.stat(self.info['path'])) != key: raise ValueError('Arquivo substituído')
            self.file_key = key
            matches = [p for p in PROFILES if p.digest == digest and p.version == self.info['version'] and p.image_size == self.info['size'] and p.machine == machine]
            if not matches: self.fail(State.UNSUPPORTED, 'Fingerprint ou metadados sem perfil correspondente.')
            self.profile = matches[0]
            self.result = replace(self.result, profile=self.profile.name)
            for rva, expected in self.profile.anchors:
                if self.probe.sample(self.info['base'] + rva, len(expected)) != expected:
                    self.fail(State.UNVERIFIED, 'Amostra do módulo carregado diverge do perfil.')
            self.instance()
            if stat_key(os.stat(self.info['path'])) != key: raise ValueError('Arquivo substituído')
            self.result = replace(self.result, module_samples_match=True)
            if not self.profile.homologated: self.fail(State.UNVERIFIED, 'Perfil identificado, mas homologação operacional pendente.')
            self.result = replace(self.result, state=State.VERIFIED, reason='Perfil homologado e verificações satisfeitas.', process=replace(identity, build_validation=Verification.VERIFIED))
        except CompatibilityError: raise
        except Exception:
            self.fail(State.ERROR, 'Não foi possível identificar o processo e seu arquivo com segurança.')

    def require_fast(self):
        if self.result.state is not State.VERIFIED: raise CompatibilityError(self.result)
        try:
            self.instance()
            if stat_key(os.stat(self.info['path'])) != self.file_key: raise ValueError('Arquivo alterado')
        except Exception:
            self.fail(State.ERROR, 'A identidade do processo ou do arquivo mudou; reconecte.')

    def require_full(self):
        self.require_fast()
        try:
            digest, machine, key = fingerprint(self.info['path'])
            if key != self.file_key or digest != self.profile.digest or machine != self.profile.machine: raise ValueError('Fingerprint alterado')
            for rva, expected in self.profile.anchors:
                if self.probe.sample(self.info['base'] + rva, len(expected)) != expected: raise ValueError('Módulo alterado')
            self.require_fast()
        except CompatibilityError: raise
        except Exception:
            self.fail(State.ERROR, 'A revalidação da build falhou; reconecte.')
