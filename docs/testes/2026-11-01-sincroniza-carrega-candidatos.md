# Sincronização carrega candidatos — relatório de testes

Data local: 01/11/2026. Windows 11 x64, Python 3.14. Objetivo: iniciar automaticamente a busca de candidatos após sincronização bem-sucedida.

Ao sincronizar, a seleção e o filtro antigos são limpos; uma busca de candidatos é agendada na thread da interface somente após observação bem-sucedida. A tarefa respeita época e fechamento, e usa a busca existente com índice SQLite. O usuário ainda escolhe e aprova manualmente o clube; a sincronização não seleciona ou autoriza automaticamente. Se não houver candidato indexado, a busca existente pode executar varredura limitada.

- `python -m py_compile FMPresidente.pyw`: aprovado.
- `python testar_sincronizacao_interface.py`: 4 aprovados; busca agendada após sucesso, nenhuma seleção automática, falha, época antiga e janela fechada.
- `python testar_indice_clubes.py`: 7 aprovados.
- `python testar_sincronizacao_hibrida.py`: 12 aprovados.
- `python testar_compatibilidade.py`: 23 aprovados.
- `python construir.py`: compilação concluída. `bin-sincroniza-candidatos/FMPresidente.exe --self-check`: saída 0 e ok=true. Atalhos atualizados; autoteste anterior preservado.

Os testes de interface isolam a lógica de connect com mocks, não substituem teste visual ou uma sincronização interativa completa. Não foram realizadas escritas no FM ou alteração de saves. A janela antiga precisa ser fechada para iniciar a nova versão. Busca ampliada continua manual em Buscar mais.
