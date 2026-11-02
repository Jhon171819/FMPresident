# Demonstração ER-01

02/11/2026, Windows 11 x64, Python 3.14. Executável SHA-256 d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1, 352.687.104 bytes. Três RVAs: 0x3a88400, 0x3a87f50, 0x1de14d0. Banco temporário vazio, limites 80 instruções/15 blocos. Não envolve leitura do FM em execução.

| Cenário | Grafos calculados | Reutilizados | Tempo s | CPU s | Payload comprimido escrito |
|---|---:|---:|---:|---:|---:|
| Fria | 3 | 0 | 2,571 | 2,281 | 4.426 bytes |
| Quente | 0 | 3 | 1,037 | 0,984 | 0 bytes |
| Parâmetro de uma função: 81 instruções | 1 | 0 | 2,327 | 2,203 | 1.512 bytes |
| Interrupção após uma função, configuração 82 | 1 | 0 | 2,352 | 2,188 | 1.760 bytes |
| Retomada da mesma tarefa | 2 | 1 | 2,336 | 2,203 | 2.687 bytes |

Contador computed corresponde à chamada do construtor de grafo/Capstone no miss; quente não carregou parser. Os três artefatos da configuração original foram conferidos após a mudança localizada. Dois grafos da configuração base são PARTIAL. Não foram promovidos para completos.

Fixture idêntica: pedidos de 4 bytes em posições contíguas, com uma repetição. Ingênuo: 3 chamadas/12 bytes; planejado: 1 chamada/8 bytes, respostas idênticas. Isso mede deduplicação/agrupamento sob os mesmos dados, não velocidade do ReadProcessMemory.

SHA streaming lê logicamente 352.687.104 bytes em cada análise, inclusive quente. Miss carrega PE via mmap somente leitura; tamanhos de buffer/mapeamento não são RSS. Payload não mede páginas SQLite/WAL, portanto não é total físico escrito em disco. Banco legado principal observado ~2,95 MB antes da entrada RTTI nova. CPU por process_time; pico RSS, contadores físicos de disco e memória não foram medidos. Não extrapolar ganhos percentuais gerais.

RTTI TACTIC_PLAYER_LIST_TABLE: primeira solicitação computed=1, 615 bytes de payload; segunda hit=1/computed=0, três vtables, sem desmontagem. Importação reutilizou 189 grafos e seus quatro bounded sem analisá-los novamente.

Rodada adicional com instrumentação Windows do próprio processo: fria 3,433 s (CPU 2,422 s), quente 1,071 s (CPU 0,938 s), parâmetro 2,666 s, interrupção 2,604 s e retomada 2,211 s. Contadores de cálculo/hit mantiveram 3/0, 0/3, 1/0, 1/0 e 2/1. RSS capturado antes de fechar mmap: 414.023.680 bytes na fria, 34.144.256 na quente. Pico Working Set é acumulado do processo, ~414 MB; não interpretar como pico isolado da fase quente. Mapeamento somente leitura ainda torna páginas residentes durante verificação; não há promessa de RSS constante. Delta de I/O lógico na quente: 352.818.176 bytes lidos e 24.720 escritos, mesmo com payload novo zero (hash, consultas e checkpoints/SQLite). Esses contadores incluem a ferramenta e não representam I/O físico de disco. A persistência final da própria métrica fica fora da janela medida.
