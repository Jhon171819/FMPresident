# UX-01 — Arquitetura PySide6

02/11/2026. Entrada incremental FMPresidenteQt.py. MainWindow usa Qt Widgets/QSS, navegação lateral e QStackedWidget com páginas persistentes e scroll. Rows usa QAbstractTableModel, histórico com proxy de filtro. aplicacao_qt.Session é uma camada sem imports Qt; ela detém os handles, delega operações ao FM e fecha a sessão. O motor e seus offsets não foram alterados nesta issue.

Controller usa o Coordinator existente, pool com um único worker e Signals/Slots queued. Widgets são alterados na thread principal. Tarefas incompatíveis não rodam juntas; a sincronização pedida durante busy avança a época, invalida a exibição e consolida o pedido mais recente. O resultado administrativo não é descartado; uma falha de snapshot após aplicação retorna explicitamente aplicação confirmada e erro de leitura, evitando repetição. Fechamento durante tarefa é recusado até conclusão segura. Mesmo mutex da interface legada impede duas instâncias administrativas simultâneas na entrada normal.

A migração é parcial. Tkinter continua principal e não foi removido. Não há cache visual que conceda autorização, compartilhamento global de fingerprint ou liberação de alocação de empréstimos.
