# Merchandising no FM23: evidências e limites

Análise de 27/10/2026, FM23 23.2.0+1771058, executável SHA-256
`d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1`.
Inspeção estática e leitura de ponteiros do processo. Nenhuma função interna
foi chamada; nenhum dado da carreira ou do executável foi alterado.

## O que foi localizado

| Elemento | RVA | Evidência |
|---|---|---|
| `CLUB_MERCHANDISE_INCREASE_NEWS` | vtable `0x4982bb8` | RTTI, construtor e referências |
| Construtor dessa notícia | `0x533af0` | Instala a vtable e inicializa seus campos |
| Preenchimento da notícia | `0x114bdf0` | Recebe referências e consulta campos financeiros |
| `COMMERCIAL_SUMMARY_NEWS` | vtable `0x4983938` | RTTI e referências |
| Despacho para cálculo financeiro | `0x388d970` | Encaminha argumentos a método virtual |
| Implementação selecionada na sessão | `0x529490` | Ponteiro global → `GAME_CLUB_FINANCE_BASE` → slot `+0x30` |
| Um chamador associado ao incremento | `0x6f08410` | Consulta o cálculo, pode atualizar campo e construir notícia |

O despacho lê o ponteiro global no RVA `0x55537e0`. Na sessão, a vtable do
objeto era `0x49fe9f8`, identificada pelo RTTI como `GAME_CLUB_FINANCE_BASE`.
O slot `+0x30` apontava para `0x529490`. Resolver esse ponteiro não executa
o método; apenas identifica a implementação usada nessa sessão.

## Comportamento observado no código

`0x529490` recebe um contexto financeiro, uma referência de pessoa e uma
saída de flags. Resolve objetos por métodos virtuais, compara referências
geográficas, percorre uma coleção do clube e verifica registros associados.
Lê campos de 16 bits com limites de milhares e campos de país de um byte.
Combina comparações, razões entre grandezas, multiplicadores e um termo cúbico,
com conversões para inteiro. Retorna um valor inteiro e flags de motivos.

A interpretação mais provável é um cálculo de contribuição comercial de um
jogador, condicionado ao mercado e à sua projeção em relação ao clube.
Ainda faltam validação dos getters, identificação completa dos campos e
comparação com relatórios de scouting e receitas em uma carreira controlada.
Não se pode chamar este resultado de total de camisas, preço de camisa ou
valor anual sem demonstrar as unidades e o calendário de aplicação.

Um chamador em `0x6f08410` recebe esse resultado. Em um ramo, compara
`resultado × 52` com um limite e pode adicionar o resultado ao campo `+0x7d4`
do contexto recebido. Sob outras condições, constrói a notícia de aumento
de merchandising. Em outro ramo reduz o mesmo campo com piso zero.
Isso é evidência de um incremento persistente condicionado, mas não demonstra
que o lançamento aconteça semanalmente nem qual receita contábil o consome.
Também há condições para emitir a notícia: não receber uma notícia não prova
que inexista influência comercial.

## Influências: separar certeza de interpretação

- **Afiliados comerciais em novos mercados:** documentados no manual oficial
  do FM23 como vínculo que beneficia as finanças. Não há percentual fixo
  publicado, e não demonstramos que cada vínculo acumula integralmente.
- **Reputação de clube e jogador:** fortes candidatos na rotina encontrada;
  há campos e escalas compatíveis, comparações e ajustes relativos. Os nomes
  semânticos de todos esses campos ainda precisam ser confirmados.
- **País/mercado:** o código distingue referências geográficas e campos do
  país. É evidência mais forte do que simplesmente presumir que qualquer
  jogador de uma nacionalidade específica aumenta as vendas.
- **Títulos e resultados:** o efeito comercial indireto por reputação e alcance
  é uma hipótese razoável; nenhum bônus fixo por Libertadores, Brasileirão
  ou Copa do Brasil foi identificado nesta análise.
- **Torcida, seguidores, excursões e amistosos:** não foi rastreada sua
  contribuição exata ao cálculo de produtos. Não atribuir percentuais.
- **Marca da fornecedora, royalties, lojas, estoque, preço unitário e desenhos
  PNG de uniforme:** nenhum vínculo com o cálculo de vendas foi demonstrado.
  Os arquivos de uniformes gerados pelo FMPresidente são gráficos.

## Três coisas diferentes

1. Patrocínio/fornecimento é uma receita contratual com vigência.
2. Merchandising é a receita de produtos apresentada nas finanças.
3. Camisas vendidas por jogador são uma medida comercial apresentada pelo jogo.

Não é seguro converter diretamente número de camisas em receita líquida,
nem equiparar o total de merchandising apenas às camisas. Compare períodos
e moedas iguais. O manual financeiro documenta relatórios mensais e sazonais,
mas não publica a fórmula nem a margem por produto.

## O que falta para reconstruir a engine

Identificar semanticamente os campos da rotina `0x529490`; rastrear quem
consome o incremento `+0x7d4`; mapear o lançamento contábil de merchandising;
e reproduzir períodos equivalentes em cópias do save, mudando um fator por vez.
Não foram feitos testes que avançam o calendário ou mudam jogadores nesta etapa.
Os grafos são limitados e saltos indiretos não são totalmente resolvidos.

Fontes oficiais:

- [Club Details and Board Performance — FM23](https://community.sports-interactive.com/sigames-manual/football-manager-2023/club-details-and-board-performance-r4733/)
- [Finances — FM23](https://community.sports-interactive.com/sigames-manual/football-manager-2023/finances-r4734/)

As duas páginas foram consultadas diretamente nesta análise.
