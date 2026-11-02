# ER-01 — Relatório de testes e entrega

02/11/2026, Windows 11 x64, Python 3.14, Capstone local. Base Git 2e9a103e8dd089d3f087f351c56f90edc4cf1cc8; árvore previamente modificada preservada. Nenhum acesso ao processo FM, varredura de memória real, alteração de save ou módulos administrativos.

## Implementação

er01.py: cache/SQLite, dependências, fila, checkpoints, evidências, grafos e leitura simulada. er01_static.py: fingerprint streaming, mmap PE, cache de RTTI/grafos, importação histórica e benchmarks. CLI em engenharia_reversa/cli.py. tc011b_estatica.py agora usa análise incremental offline por padrão e exige --exe; modo antigo por --legacy-rebuild. Parser PE mantém API anterior, com mmap opcional e strings limitadas. .gitignore inclui somente CLI adicional; banco/cache/dumps permanecem ignorados.

## Testes

`python -m unittest testar_er01 testar_tc011b testar_ux01 testar_ux011 testar_ux012 testar_pf01 testar_pf011 testar_pf012 testar_compatibilidade testar_identidade testar_sincronizacao_hibrida testar_contratos_dados`: **176 testes aprovados em 3,228 s**, incluindo 31 ER-01. PYTHONPATH: ferramentas/qt-tools, ferramentas/build-tools e raiz. Testes ER-01 usam SQLite temporário e memória simulada; não dependem do FM aberto.

A primeira execução ER-01 revelou erro de quantidade de placeholders no INSERT; corrigido e toda a suíte reexecutada. Também foi corrigida a revalidação fresh de intervalos sobrepostos, agora testada. Cobertura: cache frio/quente, parcial, corrupção, mudanças de chave/configuração/algoritmo/binário, invalidação seletiva, concorrência entre conexões, rollback por KeyboardInterrupt, checkpoint, legado idempotente, hipóteses, dependências, ciclos/profundidade/fronteira/retomada, texto não envolvido, contexto inválido, regiões, truncamento, orçamento de leitura, agrupamento e incoerência. Parser mmap inválido fecha o arquivo, verificado por exclusão da fixture após a falha.

`python -m py_compile er01.py er01_static.py engenharia_reversa/cli.py engenharia_reversa/tc011b_estatica.py`: aprovado. `git diff --check`: sem erros, avisos anteriores de LF/CRLF em arquivos não relacionados. Consulta `index --query TACTIC_PLAYER_LIST_TABLE` executada de C:\Windows\Temp: aprovada, sem identificação de processo.

## Importação real offline

`cli.py import engenharia_reversa/tc011b --exe FM.EXE` importou 4 registros de classes, 9 vtables, 262 métodos recebidos, 189 grafos e quatro bounded. Importação de tc011 adicionou fontes históricas. Totais de símbolos distintos: **22 classes, 45 vtables, 1.178 funções e 189 grafos**; proveniências múltiplas são preservadas, não chamadas de novos símbolos. Sete hipóteses/evidências importadas de docs/engenharia-reversa/ER-01-evidencias.json; estados não promovidos. Cache local em dados/er01.sqlite3, sem versionar banco.

## Demonstração obrigatória

`python engenharia_reversa/cli.py benchmark --exe FM.EXE --rva 0x3a88400 --rva 0x3a87f50 --rva 0x1de14d0` usa banco temporário vazio. Fria: três chamadas de construção de grafo; quente: zero chamadas e três hits; mudança de parâmetro de um RVA: uma chamada, três artefatos originais preservados; interrupção: uma função publicada e tarefa INTERRUPTED; retomada: duas funções calculadas e uma reutilizada. Duas respostas base permanecem PARTIAL. Esta demonstração não reprocessou os 189 grafos históricos.

RTTI solicitado duas vezes para TACTIC_PLAYER_LIST_TABLE: computed=1 na primeira, hit=1/computed=0 na segunda. Fixture de leitura: respostas idênticas, três chamadas/12 bytes viraram uma chamada/8 bytes. Cenários e métricas reais em ER-01-benchmarks.md. CPU/RSS/I/O lógico da ferramenta foram medidos em rodada adicional; I/O físico não foi medido.

## Limitações verificáveis

Não houve SIGKILL/pane elétrica, banco real corrompido, migração destrutiva, teste multiprocessos nativos ou integração de SnapshotReads ao FM. Concorrência foi testada com duas conexões SQLite em threads. Os checkpoints retomam por função; aprofundar um grafo parcial ainda reanalisa essa função. O custo do hash integral permanece nas consultas de análise novas/quentes. Mapeamento pode tornar páginas do PE residentes; pico Working Set observado ~414 MB. RTTI novo é específico à seção da build-alvo. Evidências semânticas permanecem hipóteses/parciais quando apropriado.

## Estado

Infraestrutura incremental funcional entregue e demonstração central aprovada. Consultas e importação são offline, cache evita remontagem determinística válida, invalidação é seletiva por chave/dependências, e retomada preserva funções já publicadas. Recursos avançados de recuperação e as limitações de desempenho estão documentados, sem homologação do leitor nativo de atletas. Nenhuma build Qt, atalho, commit ou push foi produzido nesta issue.

Atualização: ensaios adicionais solicitados pelo usuário confirmaram leitura real de código pelo planejador, o comportamento ao aprofundar um grafo e recuperação por TerminateProcess em três fases. Resultados em [ER-01-validacao-adicional.md](ER-01-validacao-adicional.md); preservam-se acima as condições do ensaio original.
