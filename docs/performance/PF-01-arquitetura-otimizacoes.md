# PF-01 — Arquitetura e otimizações

Data: 2026-11-02. Situação parcial. Antes, o monitor fazia observação em worker, mas chamava `fm.snapshot()` dentro do callback Tk, bloqueando a janela durante a leitura. Agora observação e snapshot ocorrem no worker já existente, e a época é verificada antes de publicar. Falhas continuam invalidando o contexto. Não foi criado polling adicional; o controle `busy` impede execução concorrente das tarefas usuais.

Com snapshot igual, o monitor não renderiza novamente os mesmos dados. `replace_rows` atualiza valores apenas quando mudam e preserva itens selecionados. O filtro de clube é mantido na sincronização e a seleção visual é mantida se o candidato continuar na lista. A apresentação não autoriza escrituras: a escolha manual, BuildGuard, validações, rollback, journals e a restrição do alocador permanecem.

O indicador de operação foi reposicionado para ficar visível acima das abas. O script de compilação copia assets à distribuição automaticamente. A construção da interface, carregamento do JSON inicial, processamento de imagens e eventual gravação de JSON na atualização do painel ainda têm trechos na thread principal. Não foi implantado cache de autorização.
