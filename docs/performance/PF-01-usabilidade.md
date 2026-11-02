# PF-01 — Usabilidade

O texto de progresso e erro passou acima das abas, onde permanece visível em janela menor. A sincronização preserva o filtro digitado; atualizar a busca mantém o candidato visual selecionado se o mesmo endereço permanecer válido. Não existe aprovação automática; o botão de seleção continua necessário. Atualizações de tabelas conservam itens e seleção existentes quando possível.

O monitor lê a memória no worker e a fila publica na thread Tk. A verificação de época impede que resultado antigo seja aplicado. O bloqueio `busy` ainda impede ações durante o monitor em andamento; sincronização concorrente e cancelamento físico não foram implementados. Painéis e carregamento inicial ainda possuem caminhos síncronos e exigem avaliação na UX-01. A janela e seus componentes permanecem Tkinter.
