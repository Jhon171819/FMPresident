# Planejamento

Store.task registra spec, dependências, fila e checkpoint; IDs não podem ser reutilizados para outra entrada/configuração. plan ordena tarefas prontas primeiro, depois prioridade + novidade - custo - risco, desempate pelo ID. A justificativa e dependências faltantes são retornadas. A heurística é determinística; não estima probabilidade estatística de sucesso.

queue ID spec.json cria tarefa pelo CLI. task ID --priority N ajusta prioridade separada do fingerprint. --state PAUSED/PENDING/CANCELLED/IGNORED controla a fila. Hipóteses são consultáveis; reabertura é explícita via Store.evidence com nova proveniência. O planejador não dispara investigação nem reabre hipóteses sozinho. plan não executa tarefas; analyze/resume são ações explícitas.
