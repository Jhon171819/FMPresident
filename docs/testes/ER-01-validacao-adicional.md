# ER-01 — Validação adicional solicitada

02/11/2026. Windows 11 x64, Python 3.14. Objetivo: testar grafo parcial, planejador com memória real e recuperação por término abrupto de processo.

Comando: `python testar_er01_resiliencia.py --exe CAMINHO_DO_FM23/fm.exe --live --output dados/ER-01-validacao-adicional.json`. Executado com o caminho real da instalação homologada; saída **0**, todas as asserções aprovadas. JSON local preservado em `dados/ER-01-validacao-adicional.json`. Bancos de ensaio foram criados em pastas temporárias próprias; o banco de pesquisa não foi alterado.

## Grafo parcial

Função RVA 0x3a88400, executável SHA-256 d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1:

| Solicitação | Calculados | Hits | Parciais | Tempo |
|---|---:|---:|---:|---:|
| 5 instruções / 2 blocos | 1 | 0 | 1 | 2,718 s |
| Repetição | 0 | 1 | 1 | 0,978 s |
| 800 instruções / 100 blocos | 1 | 0 | 0 | 2,266 s |
| Repetição aprofundada | 0 | 1 | 0 | 0,983 s |

Confirmado: mudar limites reanalisa aquela função; não existe retomada interna do grafo. O resultado aprofundado não atingiu os limites nessa amostra. Repetir cada configuração utiliza seu cache. COMPLETE da tarefa não transforma artefato PARTIAL em completo.

## Planejador com memória real

Build FM23 23.2.0+1771058, identidade de processo igual antes/depois. Handle 0x410, somente consulta/leitura. BuildGuard: 1,104 s. Uma âncora de código do próprio perfil foi lida em região consultada com VirtualQueryEx, sem acessar estruturas da carreira.

Três pedidos (4 bytes, 4 bytes seguintes, repetição dos primeiros): método direto 3 pedidos/12 bytes; planejador 1 chamada à fonte/8 bytes. Respostas idênticas entre métodos e iguais aos bytes esperados da âncora. fresh acrescentou uma chamada e não detectou divergência. Uma época controlada diferente foi rejeitada. Contexto de processo conferido ao final, cache e handle fechados.

Direto: 1,686 ms; planejado: 3,067 ms. Não houve ganho de latência nessa amostra pequena; as validações adicionais têm custo. O benefício demonstrado é redução das chamadas à fonte. As contagens excluem amostras internas do BuildGuard. A troca de época foi controlada pelo harness, não pelo coordenador Qt nem por troca real de carreira.

Cobertura ampliada: Reader real e bytes de código estáveis. Não homologa objetos mutáveis, estruturas destruídas ou monitoramento de elenco.

## Encerramento abrupto

Três auxiliares Python descartáveis foram encerrados por Popen.kill(), que usa TerminateProcess no Windows, após handshake READY. Não executaram fechamento normal, finally ou fechamento voluntário do SQLite. Cada auxiliar retornou código de término forçado 1.

| Ponto da interrupção | Publicados ao reabrir | Calculados na recuperação | Primeira função reutilizada | integrity_check |
|---|---:|---:|---:|---|
| Durante compute, transação aberta | 0 | 2 | não | ok |
| Após publicação, antes do checkpoint | 1 | 1 | sim | ok |
| Após checkpoint | 1 | 1 | sim | ok |

Todas as recuperações terminaram COMPLETE. Durante compute não havia resultado publicado para preservar; portanto as duas funções precisaram ser calculadas. Nos demais cenários o cache preservou a primeira função mesmo com checkpoint desatualizado. A fixture usa a API Store/cached/checkpoint com duas funções sintéticas; não executa o analisador Capstone nos auxiliares.

Confirmado: recuperação após falha abrupta de processo nos três pontos. Não testados: desligamento da máquina, queda de energia, perda de cache do dispositivo ou corrupção física. TerminateProcess não equivale a esses eventos.

## Regressões e preservação

`python -m unittest testar_er01`: 31 aprovados em 0,852 s. `python -m py_compile testar_er01_resiliencia.py`: aprovado. `git diff --check`: sem erros, apenas avisos anteriores de LF/CRLF.

Nenhuma escrita na memória do FM, suspensão, depuração ou alteração de save. Somente os auxiliares criados pelo teste foram encerrados. Novo harness e documentação; módulos administrativos, proteções, atalhos e builds não foram alterados.
