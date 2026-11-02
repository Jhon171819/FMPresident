# Checkpoints e retomada

Cada função é publicada atomicamente no cache antes de avançar checkpoint. Tarefa mantém spec, configuração, lista concluída, fronteira e estado. Interrupção entre publicação e checkpoint é recuperável pelo cache; interrupção durante compute não publica parcial falso. Na retomada, fingerprint e hash de algoritmo precisam corresponder ao spec anterior.

resume TASK --exe FILE recupera o trabalho; resultados concluídos são revalidados pelo hash de payload e reutilizados. Não confia apenas na lista done: cache corrompido pode exigir refazer aquela função. --max-functions cria interrupção controlada por quantidade de RVAs percorridos nesta chamada; é ferramenta de demonstração, não limite de novas computações. PAUSED/CANCELLED/IGNORED não executam análise até controle explícito.

A retomada de um grafo de blocos não continua internamente a desmontagem histórica: mudar limites de um grafo parcial reanalisa somente a função solicitada. A API walk retoma a fronteira de relações do índice separadamente. Falha de máquina/SIGKILL real não foi injetada; testes cobrem exceção/KeyboardInterrupt, rollback e checkpoint persistido.

Atualização: testes adicionais de TerminateProcess passaram durante compute, após publicação e após checkpoint. Os publicados foram preservados e os não publicados não apareceram como concluídos. Cobertura ampliada para término abrupto de processo, sem testar queda de energia. O aprofundamento também foi ensaiado e confirmou a reanálise da função solicitada. Consulte ER-01-validacao-adicional.md em docs/testes.
