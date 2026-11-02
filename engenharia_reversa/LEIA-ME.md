# Engenharia reversa inicial do FM23

Análise iniciada em 27/10/2026 sobre o executável instalado na sua máquina,
versão **23.2.0+1771058**, Windows x64. Esta etapa apenas leu o arquivo e a
memória do processo. O executável e os dados da carreira não foram modificados.

SHA-256 do arquivo analisado:
`d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1`.

Investigação de **01/11/2026**: [Empréstimos, juros e refinanciamento](EMPRESTIMOS.md)
documenta o contrato de 28 bytes, criação, parcelas, contabilidade, processamento
e pendências da integração, com simulador offline e evidências verificáveis.

## O que foi encontrado

O arquivo preserva RTTI, que identifica classes C++, e a tabela de unwind do
Windows, que ajuda a delimitar funções. Foram catalogados **1.215 nomes de
classes relevantes para gestão**, **4.588 strings relacionadas ao domínio**
e **141.731 intervalos de funções da tabela de unwind**. Um intervalo pode
ser somente parte de uma função; esses números não representam funções cujo
comportamento já foi compreendido.

As tabelas virtuais de `db::CLUB` e `db::CLUB_FINANCE` confirmam a identidade
das estruturas usadas pelo FMPresidente. Também foram localizadas tabelas de
`FACILITY_UPGRADE`, `FINANCES_SPONSORS_PANEL`, `FINANCES_DEBT_LOAN_PANEL`,
`SPONSORSHIP_DEAL_NEWS`, painéis de clubes afiliados e ações de orçamento.

| Objeto | RVA da tabela virtual principal | Evidência |
|---|---|---|
| `db::CLUB` | `0x4fdcdf8` | RTTI e objeto real na memória |
| `db::CLUB_FINANCE` | `0x4a56998` | RTTI e objeto real na memória |
| `db::FACILITY_UPGRADE` | `0x4a0fa28` | RTTI e acesso a propriedades no assembly |
| `FINANCES_SPONSORS_PANEL` | `0x4cb6b68` | RTTI |
| `FINANCES_DEBT_LOAN_PANEL` | `0x4cb4d78` | RTTI |
| `SPONSORSHIP_DEAL_NEWS` | `0x4a77d58` | RTTI |

RVA é um endereço relativo ao início do módulo carregado. Não reutilize
endereços absolutos dos objetos: eles mudam a cada execução.

## Descoberta financeira importante

A rotina em **RVA `0x38810c0`**, presente no slot 83 da tabela de finanças,
recebe um valor inteiro no registrador EDX e soma seu valor absoluto a três
campos do objeto:

```text
finance +0x014  saldo
finance +0x330  acumulador de entrada A — categoria ainda não identificada
finance +0x550  acumulador de entrada B — categoria ainda não identificada
```

As rotinas em `0x3881f00` e `0x387afb0` fazem movimentos de saída e atualizam
outros pares de acumuladores. Isso demonstra por que aumentar somente o saldo
não equivale necessariamente a lançar uma receita contábil completa no FM.
O aporte atual do FMPresidente continua sendo um ajuste direto do caixa.

Também foi identificada a rotina `0xffa3b0`, que soma o mesmo valor aos campos
de orçamento em `+0x7a4` e `+0x7a8`, e o getter `0xffa410`, que lê o orçamento
salarial em `+0x7e8`.

Essas rotinas foram desmontadas, mas **não foram chamadas**. Ainda é preciso
identificar os chamadores, a categoria de cada lançamento, as condições e
demais efeitos do fluxo nativo antes de usá-las no aplicativo.

## Obras e infraestrutura

`db::FACILITY_UPGRADE` possui acesso por propriedades de quatro caracteres:

| Propriedade | Campo | Interpretação atual |
|---|---|---|
| `fuda` | `+0x10`, 4 bytes | Data compactada; sentido exato da data pendente |
| `fuyl` | `+0x14`, 1 byte | Candidato a nível de instalações de base |
| `futl` | `+0x15`, 1 byte | Candidato a nível de treinamento |

Os getters e setters confirmam os offsets. Os nomes semânticos dos níveis
ainda são inferências das propriedades. O próximo passo é localizar a
coleção proprietária das obras e as rotinas que criam e concluem esses registros.
Isso pode permitir obras com conclusão administrada pelo calendário do FM.

## Patrocínios

A estrutura de receitas já utilizada pelo app foi documentada em
`descobertas.json`. A localização do painel financeiro e da classe de notícia
de patrocínio fornece pontos para rastrear inserção de contratos, recebimentos
e avisos comerciais. A existência dessas classes não comprova um sistema de
negociação de patrocinadores disponível para ser ativado.

A criação de novos registros ainda precisa usar corretamente o alocador e o
ciclo de vida do jogo. Esta etapa não alocou registros nem instalou hooks.

## Verificação na nova sessão

Na sessão observada, o objeto do Ceará foi reencontrado em outro endereço,
preservando as tabelas virtuais esperadas. A data foi lida como **23/11/2031**.
Os bytes comparados entre disco e memória coincidiram. A leitura também
confirmou os nomes **Ceará Sporting Club** e **Ceará** após a instalação do
pacote de nomes reais. Essa observação confirma o Ceará nessa sessão; não
é uma auditoria de todos os clubes do save.

## Arquivos e reprodução

- `descobertas.json`: offsets e métodos com evidência e pendências.
- `mapa/executavel.json`: identificação, seções e imports.
- `mapa/classes-gestao-funcoes.json` e `.asm`: tabelas e blocos iniciais dos
  métodos das classes selecionadas. A tabela financeira foi limitada aos
  primeiros 96 slots; os trechos são parciais.
- `mapa/assinatura-data.json`: assinatura e resolução do endereço da data.
- `mapa/sessao-leitura.json`: evidência da leitura da sessão atual.
- `mapa/referencias-candidatas.json`: referências candidatas por padrão de
  instrução, sem garantia de alinhamento ou cobertura completa.

`analisar_executavel.py` e `mapear_classes.py` reproduzem a análise. Usam
Python e Capstone para desmontagem; a instalação de análise está em
`work/re-tools` da pasta deste trabalho. Nenhuma dependência foi instalada
globalmente. `verificar_mapa.py caminho/fm.exe` confere hash, RTTI, tradução
de endereços, assinatura e dois métodos diretamente nos bytes do arquivo.

Os offsets de dados anteriores vieram de leitura e testes no FM e de uma
tabela comunitária de tgd6661 para uma versão anterior. Foram tratados como
hipóteses e conferidos na versão local. RTTI, métodos e assinaturas descritos
nesta etapa foram extraídos do executável instalado. Os materiais externos
de referência não foram executados.
