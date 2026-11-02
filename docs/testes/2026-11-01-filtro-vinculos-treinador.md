# Filtro de possíveis vínculos com treinador — relatório

Data local: 01/11/2026. Windows 11 x64, Python 3.14, FM23 aberto. A busca anterior listava clubes cuja estrutura financeira parecia válida, sem evidência de ligação a treinador. Foi substituída por procura limitada da vtable CLUB_HUMAN_MANAGER_DETAILS e validação da cadeia +0x40 → TEAM, +0x30 → CLUB, seguida da inspeção estrutural do clube. O cache de clube isolado não é mais incluído. A relação é hipótese observacional, não comprovação de controle humano ativo nem de carreira.

Resultados: `python testar_sincronizacao_hibrida.py`: 11 aprovados, incluindo cadeia válida, vtable incorreta e ponteiro inacessível. Busca real somente leitura `search_candidates(1024*1024*1024,20)`: zero vínculos no intervalo e limite atingido. Isso não comprova ausência do treinador; ele pode estar fora da região verificada. `python construir.py`: aprovado; `bin-vinculos/FMPresidente.exe --self-check`: saída 0, ok=true. Atalhos atualizados para bin-vinculos.

Não houve teste visual completo nem comparação real com humano/IA, troca de save ou lista completa de objetos. Não houve escrita de memória ou alteração de save. A seleção segue diagnóstica e operações permanecem bloqueadas. A janela antiga deve ser fechada para iniciar a versão atualizada.
