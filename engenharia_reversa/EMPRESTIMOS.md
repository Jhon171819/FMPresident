# Empréstimos, juros e refinanciamento no FMPresidente

**Atualização de implementação — 01/11/2026:** a contratação, contraproposta,
renegociação e quitação foram integradas à aba **Empréstimos**. A implementação
reserva blocos livres dos pools nativos com o processo suspenso, sem executar
código remoto. Criação, crédito, renegociação e quitação passaram no teste real
reversível, com restauração completa. O teste não avançou o calendário nem
salvou/reabriu a carreira. Veja o [guia da funcionalidade](../EMPRESTIMOS.txt).
O texto a seguir preserva o relatório de pesquisa anterior à implementação.

Investigação local de **01/11/2026**, FM23 **23.2.0+1771058**, Windows x64.
Arquivo: `C:\Games\Football.Manager.2023\Football.Manager.2023\Football Manager 2023\fm.exe`.
SHA-256: `d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1`.

## Resultado

**Existe base concreta para desenvolver contratação de empréstimos e renegociação
no FMPresidente.** Foram localizados o construtor do contrato, o cálculo da
prestação, a inclusão na lista do clube, o débito periódico, o crédito financeiro
e um fluxo de reestruturação de dívida. A investigação chegou às instruções,
não apenas aos nomes de classes.

Ainda não foi validada a execução dessas operações pelo aplicativo. Nesta etapa
não houve escrita no processo, chamada de função interna, suspensão do jogo,
avanço do calendário pelo agente ou alteração de save/executável. A inspeção
dinâmica usou `OpenProcess(0x410)`, sem direitos de escrita ou criação de threads.
O jogo continuou em execução e a data mudou durante o trabalho.

A futura mesa de negociação com bancos pode usar regras próprias do
FMPresidente, como ocorre com patrocinadores. A pesquisa encontrou seleção
nativa de condições de crédito e reestruturação automática; **não encontrou um
fluxo validado de propostas e contrapropostas com uma entidade bancária**.
Isso não prova que tal fluxo inexista em todo o binário.

## Evidência na carreira

Na leitura de **09/04/2032** dentro do jogo, a lista de dívidas do Ceará estava
vazia. Por isso, não seria possível desenvolver a contratação apenas reaproveitando
um empréstimo existente do Ceará.

A busca por objetos de clube com tabela virtual e vínculo financeiro coerentes
encontrou **419 registros distintos de dívida em 292 estruturas de clubes**.
Foram preservadas **31 amostras**, até três por combinação de tipo/flags, além
das contagens. Há registros vencidos na amostra; esses números **não são uma
contagem de empréstimos ativos**. A busca é uma amostragem da memória com filtros,
não uma auditoria completa da identidade e do estado de todos os clubes.

Arquivos: `emprestimos/sessao-leitura.json`, `amostras-carreira.json`.

## 1. Contrato de execução: 28 bytes

O construtor em **RVA `0x3ba0e80`** grava os campos abaixo. A função de criação
solicita explicitamente **`0x1c` bytes** em `0xae5988`.

| Offset | Tipo | Interpretação e grau de confirmação |
|---|---|---|
| `+0x00` | int32 | Principal/valor original: argumento da criação e uso no cálculo de saldo |
| `+0x04` | int32 | Prestação de referência: calculada pela rotina de criação |
| `+0x08` | int32 | Componente monetário de juros; **não é a taxa percentual anual** |
| `+0x0c` | int32 | Valor auxiliar associado a liquidação condicional; todos os exemplos coletados eram zero; semântica completa pendente |
| `+0x10` | 4 bytes | Data de vencimento no formato compacto do FM |
| `+0x14` | 4 bytes | Data inicial |
| `+0x18` | uint8 | Modalidade/origem; influencia cálculo e tratamento. Não é um ID de banco confirmado |
| `+0x19` | uint8 | Flag repassada ao débito: muda atualização de um par de acumuladores; significado de negócio pendente |
| `+0x1a` | uint8 | Seleciona prestação (`0`) ou juros (`1`) no débito periódico dos tipos comuns |
| `+0x1b` | byte | Padding, não escrito pelo construtor examinado |

O seletor de pagamento aparece literalmente em `0xae2ac8..0xae2ad5`:

```text
indice = contrato[0x1a]
valor = int32(contrato + 4 + indice * 4)
debitar(financeiro, valor, contrato[0x19])
```

Tipos especiais têm regras adicionais. Não se deve aplicar a interpretação
dos contratos comuns indiscriminadamente aos códigos de modalidade.

O vetor proprietário fica em **`*(clube+0xf8) + 0x50`**. É o mesmo caminho já
usado pelo aplicativo: `info = *(clube+248)`, vetor em `info+80`.
Os campos são início, fim e capacidade, com ponteiros de 8 bytes para contratos.

### Não confundir com o registro do banco de dados inicial

`db::STARTING_CLUB_DEBT` tem RTTI e tabela virtual em `0x4fdeef8`, além de campos
maiores, incluindo ponteiro de clube em `+0x18` e valores em `+0x28` em diante.
Ele é processado na preparação da carreira. **Não é o contrato de 28 bytes**
da lista em execução. O nome `STARTING_LOAN` também não basta para identificar
crédito financeiro: existem estruturas de empréstimo de jogadores no executável.

## 2. Criação e fórmula dos juros

**RVA `0xae5150`** recebe clube, principal, prazo e modalidade, além de taxa e
condições na pilha. O fluxo inclui ajuste automático de prazo, modalidades
especiais e tratamento de datas; não foi convertido integralmente em código Python.

O ramo de prazo/taxa explícitos usa:

```text
r = taxa_anual / 100 / 12
prestacao = trunc(principal * r / (1 - (1+r)^(-meses)))
se taxa == 0: prestacao = principal // meses
```

As divisões por **100**, **12**, a constante **1**, a potência e a truncagem
foram confirmadas nos bytes. O cálculo está em `0xae56f4..0xae5762`.
A separação contábil ordinária dos juros usa:

```text
juros_medios = prestacao - trunc(float32(principal) / float32(meses))
```

O cálculo da prestação usa double; a divisão final da parcela de principal
usa float32. Em outro ramo, com pagamento somente de juros, observa-se
`trunc((principal // 12) * (taxa_anual / 100))`. Há diferenças de arredondamento:
não substituir tudo por uma única fórmula com centavos.

**A taxa anual não aparece como um float dedicado no contrato de 28 bytes.**
Uma taxa negociada pelo FMPresidente deverá ser persistida no histórico do app;
o jogo receberá os valores e datas derivados. Alterar somente `+0x08` não é
uma renegociação coerente de uma dívida amortizada.

### Seleção automática das condições

**RVA `0xafe1b0`** seleciona condições com base em valores obtidos do clube,
modalidade, prazo e contexto. Há tabelas de saltos indiretos nesta rotina;
o grafo automático não resolve todos esses ramos.

- `0x3f8c250` lê a reputação da primeira equipe (`equipe+0xa8`), com valor
  padrão de 1500 quando não encontra equipe.
- Em `0xafe412..0xafe443`, um parâmetro float de `*(clube+0xd0)+0x24c`
  modifica a taxa pela razão `max(parametro, 1.0) / 3.5`, quando positivo.
- A leitura de memória confirmou RTTI **`db::NATION`** para esse objeto e
  valor **13,75** no campo da nação vinculada ao Ceará. Interpretar o campo
  como parâmetro nacional de juros é uma inferência forte do seu uso; não foi
  conferido contra um editor ou uma tela identificada. Não é uma consulta à
  taxa de juros do mundo real.

Isso oferece base para uma política de crédito influenciada por reputação,
montante e contexto nacional. Não fornece, por si, paciência de gerente de banco,
rating de bancos ou uma engine de contrapropostas.

## 3. Ciclo de vida e lançamento financeiro

| Parte | RVA | O que o código examinado faz |
|---|---|---|
| Criar condições e contrato | `0xae5150` | Calcula valores, aloca, constrói e anexa o contrato |
| Alocador de contratos | `0xafe720` | Acessa pool específico e termina em `0x2c38c20` |
| Inicializar contrato | `0x3ba0e80` | Grava os campos de 28 bytes |
| Anexar ao clube | `0x37e0770` → `0x126fcb90` | Acrescenta ponteiro e avança fim do vetor; chama expansão se necessário |
| Expandir vetor | `0xb000c0` | Aloca/move/libera armazenamento da lista |
| Obter lista filtrada | `0x37e07c0` | Filtra início e, opcionalmente, modalidade |
| Remover contrato | `0x37e08d0` | Compacta a lista e encaminha liberação ao pool |
| Processamento periódico | `0xae21e0` | Tem ramo condicionado ao primeiro dia do mês que debita parcela/juros, avalia vencimento e reestruturação |
| Débito | `0x387f5a0` → `0x128c3bf0` | Diminui caixa e atualiza acumuladores financeiros |
| Crédito | `0x3879110` → virtual `+0x188` → `0x53e610` → `0x6f2dc90` | Caminho separado de entrada de dinheiro, com guarda e chamada auxiliar |
| Saldo da dívida | `0x3ba0ee0` | Calcula valores por modalidade, prazo restante e flags |
| Juros restantes | `0x3ba14c0` | No ramo comum, multiplica juros monetários pelo prazo restante aproximado |

A identidade do objeto de despacho financeiro foi confirmada por leitura:
global **`0x55537d8`** → **`GAME_CLUB_FINANCE`**, tabela virtual **`0x49fe648`**.
O slot **41 / `+0x148`**, RVA `0x52b510`, trata o registro inicial e chama a
criação. Esse método também altera outros campos de orçamento; não deve ser
usado como comando universal de contratar empréstimo.

### Caixa não é a única gravação

O crédito em `0x6f2dc90` chama antes `0x3881460` e depois soma o valor absoluto a:

```text
financeiro+0x014  caixa
financeiro+0x324  acumulador A
financeiro+0x544  acumulador B
```

Há uma guarda que retorna sem creditar se `financeiro+8` corresponde a um clube
guardado em outro contexto global. Na sessão lida, esse clube era nulo e não
correspondia ao Ceará. O propósito do contexto e os efeitos completos de
`0x3881460` continuam pendentes. O fluxo não foi executado nesta pesquisa.

O débito usado no processamento de dívidas subtrai do caixa e soma a
`+0x284` e `+0x4a4`. Quando o argumento vindo de `contrato+0x19` é zero,
também subtrai de `+0x33c` e `+0x55c`. A vinculação ao pagamento de dívida
é demonstrada pelo chamador; os rótulos de todas as categorias contábeis
ainda não foram associados à interface.

A criação do contrato e o crédito são caminhos separados. Um comando futuro
precisa tratar os dois, com verificação e recuperação de falhas. Apenas anexar
o contrato não demonstra que o dinheiro será depositado.

### Reestruturação e somente juros

Em `0xae2b0c..0xae2b5b`, o processamento de vencimento de contratos com a flag
de juros cria outra dívida a partir do principal. Há decisões de modalidade
e de situação do clube no caminho. Logo, **não se pode presumir que o principal
será automaticamente quitado em dinheiro no vencimento**: o jogo pode refinanciar.

O mesmo fluxo produz uma notícia **`CLUB_RESTRUCTURES_DEBT`**, identificada por
RTTI, cujo construtor fica em `0x1156410`. A existência dessa notícia não
transforma seu construtor num comando de refinanciamento.

## 4. O que já serve ao desenvolvimento

| Funcionalidade | Base encontrada | Trabalho que ainda falta |
|---|---|---|
| Simular principal, prazo, taxa e prestação | Fórmula e tipos numéricos confirmados | Conferir arredondamentos e datas na interface do jogo |
| Negociar taxa, prazo e modalidade no app | Taxa explícita aceita pela criação; condições nacionais/reputação identificadas | Implementar regras próprias de proposta/contraproposta e histórico |
| Contrair um novo empréstimo | Alocador, construtor, anexação e crédito localizados | Validar execução com contexto correto, ciclo de vida, contabilidade e persistência |
| Renegociar dívida existente | Campos e leitura de saldo identificados | Validar saldo a refinanciar, datas, valores recalculados e substituição sem duplicidade |
| Refinanciar/consolidar dívidas | Fluxo nativo de reestruturação localizado | Demonstrar transação que encerra antigas e cria nova sem crédito duplicado |
| Pagamento periódico pelo FM | Débito, seleção parcela/juros e retirada de contratos encontrados | Teste controlado atravessando vencimento e salvando/reabrindo a carreira |

O app atual escreve dados com transações verificadas; não chama funções do
jogo. Chamar o alocador e os métodos internos seria uma mudança dessa
arquitetura. Um bloco criado com alocador externo não é automaticamente
compatível com o pool que o FM usará para liberar o contrato.

Para manter o motor nativo responsável pelo calendário, o caminho recomendado
é validar a inclusão pelo ciclo de vida nativo em uma cópia da carreira.
Uma agenda de cobranças feita só pelo aplicativo exigiria resolver cobranças
com o app fechado, recarga de saves e duplicidade, portanto não foi implementada.

Antes de disponibilizar o comando, o teste de integração deve demonstrar:
crédito exato uma vez, contrato visível no FM, débito na data correta, saldo
coerente, salvamento/reabertura, resgate de falha e ausência de dívidas antigas
duplicadas num refinanciamento. Isso é trabalho pendente, não resultado desta etapa.

## 5. Protótipo e verificações entregues

`emprestimos/modelo.py` é um **simulador offline**, sem acesso ao processo,
para o ramo comum com taxa e prazo explícitos. Não implementa aprovação de
crédito, carência, modalidades especiais, ajuste automático de prazo/taxa nem
gravação do contrato. Recusa limites incompatíveis em vez de imitar os ajustes
internos de overflow do FM.

Exemplo na moeda interna usada pelo app, GBP:
**£1.000.000 a 12% anuais, em 24 meses → parcela £47.073**,
campo médio de juros **£5.407**, total nominal **£1.129.752**.
São valores do protótipo reconstruído, não uma proposta aceita dentro do jogo.
Na modalidade somente juros, o principal exibido no vencimento é a obrigação
remanescente; o protótipo não prevê a decisão nativa de refinanciá-la.

`verificar_emprestimos.py` passou: hash do executável, dois RTTIs, campos do
construtor, constantes, instruções dos caminhos principais, consistência das
31 amostras e exemplos/limites do simulador. As verificações são estáticas
e offline; não substituem um teste de empréstimo novo dentro do FM.

## Reprodução e arquivos

Partindo desta pasta, em PowerShell, usando a instalação já existente de Capstone:

```powershell
$fmExe = 'C:\Games\Football.Manager.2023\Football.Manager.2023\Football Manager 2023\fm.exe'
$capstoneDir = '.\ferramentas'
py .\investigar_emprestimos.py $fmExe --out .\emprestimos --capstone $capstoneDir
py .\verificar_emprestimos.py $fmExe --capstone $capstoneDir
py .\emprestimos\modelo.py
```

O script também aceita `--trace 0xae5150 0xafe1b0 --stem revisao`, com
`--callers` opcional para pesquisar chamadores diretos, e `--live` para repetir
a amostragem somente leitura com uma carreira aberta. As evidências da sessão
serão substituídas por novas leituras nesses arquivos.

Principais artefatos em `emprestimos/`:

- `manifesto.json`: hash, escopo inicial e versão do desmontador.
- `classes.json`, `referencias.json`, `fluxos.json/.asm`: RTTI, referências e grafos iniciais.
- `rotinas`, `estrutura`, `integracao`, `cobranca`, `ciclo`, `ciclo-auxiliares`,
  `parametros`, `acesso-lista` (`.json/.asm`): aprofundamentos pelos RVAs descritos.
- `motor-financeiro.json/.asm`, `motor-fluxos.json/.asm`: tabela e 74 grafos de
  métodos/encaminhamentos do motor financeiro selecionados nesta investigação.
- `constantes-formula.json`, `despacho-financeiro.json`, `parametro-nacao.json`,
  `guarda-credito.json`: verificações específicas.

Os grafos seguem chamadas e saltos de forma limitada; referências por padrão
de bytes começam como candidatas. `boundary_reached` identifica coincidência
com uma instrução alcançada. `bounded=false` significa apenas que o limite de
instruções/blocos não foi atingido; **não** significa cobertura de saltos
indiretos, callbacks, todas as exceções ou todos os estados possíveis.
