"""AU-02: contratos e adaptadores puros; não importa nem acessa o FM.

Unidades são explícitas nos nomes. Valores de memória não comprovam semântica,
persistência em save ou identidade do clube controlado.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import json
import math
from typing import Any, Generic, Mapping, Optional, TypeVar


class Source(str, Enum):
    FM_MEMORY = 'FM_MEMORY'
    LOCAL_STORAGE = 'LOCAL_STORAGE'
    CALCULATED = 'CALCULATED'
    FALLBACK = 'FALLBACK'
    UNKNOWN = 'UNKNOWN'


class Verification(str, Enum):
    VERIFIED = 'VERIFIED'
    UNVERIFIED = 'UNVERIFIED'
    UNKNOWN = 'UNKNOWN'


class ExecutionState(str, Enum):
    PROPOSED = 'PROPOSED'
    REJECTED = 'REJECTED'
    PREPARED = 'PREPARED'
    APPLIED = 'APPLIED'
    FAILED = 'FAILED'
    UNKNOWN = 'UNKNOWN'


T = TypeVar('T')


@dataclass(frozen=True)
class Evidence(Generic[T]):
    value: Optional[T]
    source: Source
    validation: Verification = Verification.UNVERIFIED
    note: str = ''

    def __post_init__(self):
        if not isinstance(self.source, Source) or not isinstance(self.validation, Verification):
            raise ValueError('Origem e validação devem ser estados conhecidos.')
        if self.value is None and self.validation is Verification.VERIFIED:
            raise ValueError('Um valor desconhecido não pode estar verificado.')


def integer(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name}: inteiro esperado entre {low} e {high}.')
    return value


def number(value: Any, name: str, low: float, high: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name}: número finito esperado entre {low} e {high}.')
    return float(value)


def text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name}: texto obrigatório.')
    return value


def day(value: Any, name: str) -> date:
    try:
        if type(value) is date:
            return value
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError()
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise ValueError(f'{name}: data ISO AAAA-MM-DD inválida.') from None


def boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f'{name}: booleano obrigatório.')
    return value


def mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise ValueError(f'{name}: objeto com chaves textuais esperado.')
    return value


def required(value: Mapping[str, Any], key: str) -> Any:
    if key not in value:
        raise ValueError(f'Campo obrigatório ausente: {key}.')
    return value[key]


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    started: str
    version: Optional[str]
    image_size: Optional[int]
    executable: Optional[str] = None
    sha256: Evidence[str] = field(default_factory=lambda: Evidence(None, Source.UNKNOWN, Verification.UNKNOWN))
    build_validation: Verification = Verification.UNKNOWN

    def __post_init__(self):
        integer(self.pid, 'pid', 1, 2**32-1)
        text(self.started, 'início do processo')
        if self.version is not None: text(self.version, 'versão')
        if self.image_size is not None: integer(self.image_size, 'tamanho da imagem', 1, 2**64-1)
        if self.executable is not None: text(self.executable, 'executável')
        if not isinstance(self.sha256, Evidence) or not isinstance(self.build_validation, Verification):
            raise ValueError('Fingerprint ou validação de build inválido.')
        if self.sha256.value is not None:
            s = self.sha256.value
            if not isinstance(s, str) or len(s) != 64 or any(c not in '0123456789abcdefABCDEF' for c in s):
                raise ValueError('SHA-256 inválido.')


@dataclass(frozen=True)
class ClubIdentity:
    uid: int
    name: str

    def __post_init__(self):
        integer(self.uid, 'UID do clube', 1, 2**32-1)
        text(self.name, 'nome do clube')


@dataclass(frozen=True)
class CareerIdentity:
    process: ProcessIdentity
    identified_club: ClubIdentity
    game_date: date
    career_id: Evidence[str] = field(default_factory=lambda: Evidence(None, Source.UNKNOWN, Verification.UNKNOWN))
    controlled_club: Evidence[ClubIdentity] = field(default_factory=lambda: Evidence(None, Source.UNKNOWN, Verification.UNKNOWN))
    origin: Source = Source.FM_MEMORY
    identity_validation: Verification = Verification.UNKNOWN

    def __post_init__(self):
        if not isinstance(self.process, ProcessIdentity) or not isinstance(self.identified_club, ClubIdentity) or type(self.game_date) is not date:
            raise ValueError('Identidade de carreira inconsistente.')
        if not isinstance(self.career_id, Evidence) or not isinstance(self.controlled_club, Evidence):
            raise ValueError('Identidades opcionais precisam de proveniência.')
        if self.career_id.value is not None: text(self.career_id.value, 'identificador de carreira')
        if self.controlled_club.value is not None and not isinstance(self.controlled_club.value, ClubIdentity):
            raise ValueError('Clube controlado inválido.')
        if not isinstance(self.origin, Source) or not isinstance(self.identity_validation, Verification):
            raise ValueError('Origem ou verificação de identidade inválida.')


@dataclass(frozen=True)
class Sponsor:
    kind: int
    start: date
    end: date
    total_gbp: int
    origin: Source
    brand: Optional[str] = None
    record_id: Optional[str] = None
    annual_gbp: Optional[int] = None
    years: Optional[int] = None
    exclusive: Optional[bool] = None
    renewal_preference: Optional[bool] = None
    penalty_percent: Optional[int] = None
    negotiation_state: Optional[str] = None
    fm_match: Verification = Verification.UNKNOWN
    sector: Optional[str] = None

    def __post_init__(self):
        integer(self.kind, 'espaço comercial', 1, 19)
        if type(self.start) is not date or type(self.end) is not date or self.end < self.start:
            raise ValueError('Datas de patrocínio inválidas ou invertidas.')
        integer(self.total_gbp, 'total GBP', 0, 2_000_000_000)
        if not isinstance(self.origin, Source) or not isinstance(self.fm_match, Verification): raise ValueError('Proveniência inválida.')
        if self.brand is not None: text(self.brand, 'marca')
        if self.sector is not None: text(self.sector, 'setor')
        if self.record_id is not None: text(self.record_id, 'identificador')
        if self.negotiation_state is not None: text(self.negotiation_state, 'estado da negociação')
        if self.annual_gbp is not None: integer(self.annual_gbp, 'anual GBP', 1000, 500_000_000)
        if self.years is not None: integer(self.years, 'duração em anos', 1, 5)
        if (self.annual_gbp is None) != (self.years is None): raise ValueError('Valor anual e duração devem ser informados juntos.')
        if self.annual_gbp is not None and (self.annual_gbp * self.years != self.total_gbp or self.total_gbp > 1_000_000_000):
            raise ValueError('Total incompatível com o valor anual e a duração.')
        for name, value in [('exclusividade',self.exclusive), ('preferência',self.renewal_preference)]:
            if value is not None: boolean(value, name)
        if self.penalty_percent is not None: integer(self.penalty_percent, 'multa percentual', 0, 100)


@dataclass(frozen=True)
class Loan:
    principal_gbp: int
    monthly_gbp: int
    interest_component_gbp: int
    start: date
    end: date
    kind: int
    interest_only: bool
    conditional_gbp: int
    origin: Source
    annual_rate_percent: Evidence[float] = field(default_factory=lambda: Evidence(None, Source.UNKNOWN, Verification.UNKNOWN))
    remaining_gbp: Evidence[int] = field(default_factory=lambda: Evidence(None, Source.UNKNOWN, Verification.UNKNOWN))
    months: Optional[int] = None
    operation_state: ExecutionState = ExecutionState.UNKNOWN

    def __post_init__(self):
        for name, value in [('principal',self.principal_gbp),('parcela',self.monthly_gbp),('juros',self.interest_component_gbp),('condicional',self.conditional_gbp)]:
            integer(value, name, 0, 2_000_000_000)
        integer(self.kind, 'tipo de empréstimo', 0, 255)
        boolean(self.interest_only, 'somente juros')
        if type(self.start) is not date or type(self.end) is not date or self.end < self.start: raise ValueError('Datas de empréstimo inválidas ou invertidas.')
        if not isinstance(self.origin, Source) or not isinstance(self.operation_state, ExecutionState): raise ValueError('Origem ou estado inválido.')
        for name, item in [('taxa',self.annual_rate_percent), ('saldo',self.remaining_gbp)]:
            if not isinstance(item, Evidence): raise ValueError(f'{name}: proveniência obrigatória.')
        if self.annual_rate_percent.value is not None: number(self.annual_rate_percent.value, 'taxa anual', 0, 100)
        if self.remaining_gbp.value is not None: integer(self.remaining_gbp.value, 'saldo remanescente GBP', 0, 2_000_000_000)
        if self.months is not None: integer(self.months, 'prazo em meses', 6, 120)


@dataclass(frozen=True)
class FinancialSnapshot:
    career: CareerIdentity
    balance_gbp: int
    transfer_budget_gbp: int
    season_transfer_gbp: int
    weekly_wage_budget_gbp: int
    weekly_wage_spend_gbp: int
    ticket_price_gbp: float
    season_ticket_price_gbp: float
    facilities: Mapping[str, int]
    revenues: tuple[Sponsor, ...]
    obligations: tuple[Loan, ...]
    credit_rate: Evidence[float]
    reputation: Evidence[int]
    licensed_kits: bool
    attendance: int

    def __post_init__(self):
        if not isinstance(self.career, CareerIdentity): raise ValueError('Carreira obrigatória.')
        integer(self.balance_gbp, 'caixa GBP', -1_999_999_999, 1_999_999_999)
        for name in ('transfer_budget_gbp','season_transfer_gbp','weekly_wage_budget_gbp','weekly_wage_spend_gbp'):
            integer(getattr(self,name), name, -2_000_000_000, 2_000_000_000)
        number(self.ticket_price_gbp, 'ingresso GBP', 0, 100_000)
        number(self.season_ticket_price_gbp, 'carnê GBP', 0, 100_000)
        for key, value in mapping(self.facilities, 'instalações').items():
            text(key, 'instalação'); integer(value, key, 0, 20)
        if not isinstance(self.revenues, tuple) or not all(isinstance(v, Sponsor) for v in self.revenues): raise ValueError('Receitas inválidas.')
        if not isinstance(self.obligations, tuple) or not all(isinstance(v, Loan) for v in self.obligations): raise ValueError('Obrigações inválidas.')
        if not isinstance(self.credit_rate, Evidence) or not isinstance(self.reputation, Evidence): raise ValueError('Proveniência de crédito ausente.')
        if self.credit_rate.value is not None: number(self.credit_rate.value, 'parâmetro de crédito', 0, 100)
        if self.reputation.value is not None: integer(self.reputation.value, 'reputação', 0, 65535)
        boolean(self.licensed_kits, 'modo de uniforme')
        integer(self.attendance, 'público', 0, 2_000_000_000)


@dataclass(frozen=True)
class OperationRequest:
    kind: str
    parameters: Mapping[str, Any]
    context: Optional[CareerIdentity] = None
    preconditions: tuple[str, ...] = ()
    request_id: Optional[str] = None

    def __post_init__(self):
        text(self.kind, 'tipo de operação'); mapping(self.parameters, 'parâmetros')
        if self.context is not None and not isinstance(self.context, CareerIdentity): raise ValueError('Contexto inválido.')
        if not isinstance(self.preconditions, tuple) or any(not isinstance(x,str) or not x for x in self.preconditions): raise ValueError('Pré-condições inválidas.')
        if self.request_id is not None: text(self.request_id, 'identificador')


@dataclass(frozen=True)
class OperationValidation:
    request: OperationRequest
    validation: Verification
    blocking_errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    satisfied: tuple[str, ...] = ()
    pending: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.request, OperationRequest) or not isinstance(self.validation, Verification): raise ValueError('Validação de operação inválida.')
        for group in (self.blocking_errors,self.warnings,self.satisfied,self.pending):
            if not isinstance(group,tuple) or any(not isinstance(v,str) or not v for v in group): raise ValueError('Itens de validação inválidos.')
        if self.validation is Verification.VERIFIED and (self.blocking_errors or self.pending): raise ValueError('Validação verificada não pode ter erros ou verificações pendentes.')


@dataclass(frozen=True)
class OperationResult:
    operation_id: str
    state: ExecutionState
    confirmed: tuple[str, ...] = ()
    journal: Optional[str] = None
    errors: tuple[str, ...] = ()
    recovery_needed: Optional[bool] = None

    def __post_init__(self):
        text(self.operation_id, 'operação')
        if not isinstance(self.state, ExecutionState): raise ValueError('Estado de operação inválido.')
        for group in (self.confirmed,self.errors):
            if not isinstance(group,tuple) or any(not isinstance(v,str) or not v for v in group): raise ValueError('Detalhes de resultado inválidos.')
        if self.journal is not None: text(self.journal, 'journal')
        if self.recovery_needed is not None: boolean(self.recovery_needed, 'recuperação')


def process_from_legacy(data: Mapping[str, Any]) -> ProcessIdentity:
    d = mapping(data, 'processo')
    # started é string de ticks no formato existente, não é data de carreira.
    started = text(required(d,'started'), 'início do processo')
    return ProcessIdentity(integer(required(d,'pid'),'pid',1,2**32-1), started,
        d.get('version'), d.get('size'), d.get('path'))


def sponsor_from_memory(data: Mapping[str, Any]) -> Sponsor:
    d = mapping(data,'receita')
    return Sponsor(integer(required(d,'kind'),'tipo',1,19), day(required(d,'start'),'início'),
        day(required(d,'end'),'fim'), integer(required(d,'total'),'total GBP',0,2_000_000_000),
        Source.FM_MEMORY)


def sponsor_from_local(data: Mapping[str, Any]) -> Sponsor:
    d = mapping(data,'patrocínio local')
    company = mapping(required(d,'company'),'empresa')
    return Sponsor(integer(required(d,'kind'),'tipo',1,19), day(required(d,'start'),'início'),
        day(required(d,'end'),'fim'), integer(required(d,'total'),'total GBP',0,2_000_000_000),
        Source.LOCAL_STORAGE, brand=text(required(company,'name'),'marca'), record_id=d.get('transaction'),
        annual_gbp=d.get('annual'), years=d.get('years'), exclusive=d.get('exclusive'),
        renewal_preference=d.get('renewal'), penalty_percent=d.get('penalty'), negotiation_state=d.get('status'),sector=d.get('sector'))


def validate_exclusivity(contracts: tuple[Sponsor, ...]) -> None:
    """Conflito apenas quando marca, setor, vigência e exclusividade são conhecidos."""
    if not isinstance(contracts,tuple) or not all(isinstance(c,Sponsor) for c in contracts): raise ValueError('Lista de patrocínios inválida.')
    for index, current in enumerate(contracts):
        for other in contracts[index+1:]:
            if not current.brand or not other.brand or not current.sector or not other.sector: continue
            if current.negotiation_state == 'terminated' or other.negotiation_state == 'terminated': continue
            if (current.sector.casefold()==other.sector.casefold() and current.brand.casefold()!=other.brand.casefold()
                    and current.start<=other.end and other.start<=current.end and (current.exclusive is True or other.exclusive is True)):
                raise ValueError('Conflito de exclusividade entre marcas do mesmo setor.')


def sponsor_proposal_from_legacy(data: Mapping[str, Any]) -> Sponsor:
    d = mapping(data,'mesa de negociação')
    terms = mapping(required(d,'offer'),'oferta')
    company = mapping(required(d,'company'),'empresa')
    row = mapping(required(d,'row'),'receita')
    annual = integer(required(terms,'annual'),'anual GBP',1000,500_000_000)
    years = integer(required(terms,'years'),'duração',1,5)
    start = day(required(terms,'start'),'início')
    import calendar
    if start.year + years > 2199: raise ValueError('Duração fora da faixa do jogo.')
    anniversary = start.replace(year=start.year+years, day=min(start.day,calendar.monthrange(start.year+years,start.month)[1]))
    from datetime import timedelta
    end = anniversary if anniversary.day < start.day else anniversary-timedelta(days=1)
    return Sponsor(integer(required(row,'kind'),'tipo',1,19),start,end,annual*years,Source.LOCAL_STORAGE,
        brand=text(required(company,'name'),'marca'),record_id=text(required(d,'id'),'mesa'),annual_gbp=annual,years=years,
        exclusive=boolean(required(terms,'exclusive'),'exclusividade'),renewal_preference=boolean(required(terms,'renewal'),'renovação'),
        penalty_percent=integer(required(terms,'penalty'),'multa',0,100),negotiation_state=text(required(d,'status'),'estado'))


def loan_from_memory(data: Mapping[str, Any]) -> Loan:
    d = mapping(data,'dívida')
    return Loan(integer(required(d,'original'),'principal',0,2_000_000_000),
        integer(required(d,'monthly'),'parcela',0,2_000_000_000),integer(required(d,'interest'),'juros',0,2_000_000_000),
        day(required(d,'start'),'início'),day(required(d,'end'),'vencimento'),integer(required(d,'source'),'tipo',0,255),
        boolean(required(d,'interest_only'),'somente juros'),integer(required(d,'conditional'),'condicional',0,2_000_000_000),Source.FM_MEMORY)


def loan_offer_from_legacy(data: Mapping[str, Any]) -> Loan:
    d = mapping(data,'proposta de empréstimo')
    monthly = integer(required(d,'monthly'),'parcela',1,2_000_000_000)
    interest = integer(required(d,'interest'),'juros',0,2_000_000_000)
    months = integer(required(d,'months'),'meses',6,120)
    if interest > monthly or monthly * months > 2_000_000_000:
        raise ValueError('Parcela ou total da proposta incompatível.')
    if 'total' in d and integer(d['total'],'total GBP',0,2_000_000_000) != monthly * months:
        raise ValueError('Total da proposta não corresponde às parcelas.')
    return Loan(integer(required(d,'principal'),'principal',1000,100_000_000),
        monthly,interest,
        day(required(d,'first'),'primeira parcela'),day(required(d,'end'),'última parcela'),1,False,0,Source.CALCULATED,
        annual_rate_percent=Evidence(number(required(d,'rate'),'taxa',0,100),Source.CALCULATED,Verification.UNVERIFIED,'Oferta do app; não é taxa lida da memória.'),
        months=months,operation_state=ExecutionState.PROPOSED)


def credit_from_offer_context(snapshot: Mapping[str, Any]) -> tuple[Evidence[float], Evidence[int]]:
    """Representa os valores efetivamente selecionados por emprestimos.offer."""
    credit = mapping(mapping(snapshot,'snapshot').get('credit',{}),'crédito')
    rate = (Evidence(number(credit['rate'],'parâmetro nacional',0,100),Source.UNKNOWN,Verification.UNVERIFIED,
                     'Snapshot legado: memória ou fallback 3.5 indistinguíveis; semântica não confirmada.')
            if 'rate' in credit else Evidence(13.75,Source.FALLBACK,Verification.UNVERIFIED,'Fallback da oferta.'))
    rep = (Evidence(integer(credit['reputation'],'reputação',0,65535),Source.FM_MEMORY,Verification.UNVERIFIED)
           if 'reputation' in credit else Evidence(5000,Source.FALLBACK,Verification.UNVERIFIED,'Fallback da oferta.'))
    return rate, rep


def financial_from_legacy(snapshot: Mapping[str, Any], process: Mapping[str, Any]) -> FinancialSnapshot:
    d = mapping(snapshot,'snapshot')
    career = CareerIdentity(process_from_legacy(process), ClubIdentity(integer(required(d,'uid'),'UID',1,2**32-1),text(required(d,'club'),'clube')),day(required(d,'date'),'data'))
    credit = mapping(d.get('credit',{}),'crédito')
    # A estrutura legada não registra se 3.5 veio de memória ou fallback.
    rate = Evidence(number(credit['rate'],'parâmetro nacional',0,100),Source.UNKNOWN,Verification.UNVERIFIED,
        'Snapshot legado: memória ou fallback 3.5 indistinguíveis; semântica não confirmada.') if 'rate' in credit else Evidence(None,Source.UNKNOWN,Verification.UNKNOWN)
    rep = Evidence(integer(credit['reputation'],'reputação',0,65535),Source.FM_MEMORY,Verification.UNVERIFIED) if 'reputation' in credit else Evidence(None,Source.UNKNOWN,Verification.UNKNOWN)
    revenues = required(d,'sponsors'); debts = required(d,'debts')
    if not isinstance(revenues,list) or not isinstance(debts,list): raise ValueError('Listas de receitas e dívidas obrigatórias.')
    facilities = dict(mapping(required(d,'facilities'),'instalações'))
    return FinancialSnapshot(career,integer(required(d,'balance'),'caixa',-1_999_999_999,1_999_999_999),
        integer(required(d,'transfer'),'transferências',-2_000_000_000,2_000_000_000),integer(required(d,'season_transfer'),'temporada',-2_000_000_000,2_000_000_000),
        integer(required(d,'wage'),'folha',-2_000_000_000,2_000_000_000),integer(required(d,'wage_spend'),'folha gasta',-2_000_000_000,2_000_000_000),
        number(required(d,'ticket'),'ingresso',0,100_000),number(required(d,'season_ticket'),'carnê',0,100_000), facilities,
        tuple(sponsor_from_memory(x) for x in revenues),tuple(loan_from_memory(x) for x in debts),rate,rep,
        boolean(required(d,'licensed_kits'),'uniforme'),integer(required(d,'attendance'),'público',0,2_000_000_000))


def operation_from_journal(data: Mapping[str, Any], journal: Optional[str] = None) -> OperationResult:
    d = mapping(data,'journal')
    states = {'prepared':ExecutionState.PREPARED,'applied':ExecutionState.APPLIED,'failed':ExecutionState.FAILED}
    state = states.get(d.get('status'),ExecutionState.UNKNOWN)
    error = d.get('error')
    if error is not None: text(error,'erro')
    # applied é o estado do journal; não confirma interface nem persistência do save.
    return OperationResult(text(required(d,'id'),'operação'),state,
        confirmed=('journal indica bytes aplicados',) if state is ExecutionState.APPLIED else (),journal=journal,
        errors=(error,) if error else (),recovery_needed=None)


ADAPTERS = {'process':process_from_legacy,'sponsor_memory':sponsor_from_memory,'sponsor_local':sponsor_from_local,
            'sponsor_proposal':sponsor_proposal_from_legacy,'loan_memory':loan_from_memory,'loan_offer':loan_offer_from_legacy,
            'journal':operation_from_journal,'financial_snapshot':lambda d:financial_from_legacy(required(d,'snapshot'),required(d,'process'))}


def serialize_legacy(kind: str, data: Mapping[str, Any]) -> str:
    """Envelope versionado com cópia integral do legado, inclusive campos futuros."""
    if kind not in ADAPTERS: raise ValueError('Tipo de contrato não suportado.')
    payload = deepcopy(dict(mapping(data,'dados')))
    ADAPTERS[kind](payload)
    try:
        return json.dumps({'schema_version':1,'kind':kind,'legacy':payload},sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError) as exc:
        raise ValueError('Dados incompatíveis com JSON.') from exc


def deserialize_legacy(serialized: str) -> tuple[Any, dict[str, Any]]:
    try:
        envelope = json.loads(serialized, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Número não finito')))
    except (ValueError,TypeError) as exc:
        raise ValueError('JSON de contrato inválido.') from exc
    d = mapping(envelope,'envelope')
    if type(d.get('schema_version')) is not int or d['schema_version'] != 1: raise ValueError('Versão do esquema não suportada.')
    kind = d.get('kind')
    if not isinstance(kind,str) or kind not in ADAPTERS: raise ValueError('Tipo de contrato não suportado.')
    payload = deepcopy(dict(mapping(required(d,'legacy'),'legado')))
    return ADAPTERS[kind](payload), payload


_MODELS = {c.__name__: c for c in (Evidence,ProcessIdentity,ClubIdentity,CareerIdentity,Sponsor,Loan,FinancialSnapshot,OperationRequest,OperationValidation,OperationResult)}
_ENUMS = {c.__name__: c for c in (Source,Verification,ExecutionState)}


def model_to_json(model: Any) -> str:
    """Esquema novo fechado; não substitui nem grava os arquivos legados."""
    from dataclasses import fields, is_dataclass
    def encode(value):
        if isinstance(value, Enum): return {'$enum':type(value).__name__,'value':value.value}
        if type(value) is date: return {'$date':value.isoformat()}
        if is_dataclass(value) and type(value).__name__ in _MODELS:
            return {'$model':type(value).__name__,'fields':{f.name:encode(getattr(value,f.name)) for f in fields(value)}}
        if isinstance(value,tuple): return {'$tuple':[encode(v) for v in value]}
        if isinstance(value,list): return [encode(v) for v in value]
        if isinstance(value,Mapping): return {'$map':{k:encode(v) for k,v in mapping(value,'objeto').items()}}
        if value is None or type(value) in (str,int,float,bool): return value
        raise ValueError('Valor não serializável no contrato.')
    if type(model).__name__ not in _MODELS or not isinstance(model,tuple(_MODELS.values())):
        raise ValueError('Modelo não suportado.')
    try: return json.dumps({'schema_version':1,'model':encode(model)},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (TypeError,ValueError) as exc: raise ValueError('Modelo incompatível com JSON.') from exc


def model_from_json(serialized: str) -> Any:
    def decode(value):
        if isinstance(value,list): return [decode(v) for v in value]
        if not isinstance(value,dict): return value
        if set(value)=={'$date'}: return day(value['$date'],'data')
        if set(value)=={'$tuple'} and isinstance(value['$tuple'],list): return tuple(decode(v) for v in value['$tuple'])
        if set(value)=={'$map'}: return {k:decode(v) for k,v in mapping(value['$map'],'objeto').items()}
        if set(value)=={'$enum','value'} and value['$enum'] in _ENUMS: return _ENUMS[value['$enum']](value['value'])
        if set(value)=={'$model','fields'} and value['$model'] in _MODELS:
            cls = _MODELS[value['$model']]
            try: return cls(**{k:decode(v) for k,v in mapping(value['fields'],'campos').items()})
            except (TypeError,KeyError) as exc: raise ValueError('Campos do modelo incompatíveis.') from exc
        raise ValueError('Estrutura de modelo desconhecida.')
    try:
        envelope = json.loads(serialized,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Número não finito')))
        if not isinstance(envelope,dict) or set(envelope)!={'schema_version','model'} or type(envelope['schema_version']) is not int or envelope['schema_version']!=1:
            raise ValueError('Versão ou envelope de modelo não suportado.')
        result=decode(envelope['model'])
        if not isinstance(result,tuple(_MODELS.values())): raise ValueError('Modelo obrigatório.')
        return result
    except (TypeError,KeyError,ValueError) as exc:
        raise ValueError('Contrato serializado inválido: '+str(exc)) from exc
