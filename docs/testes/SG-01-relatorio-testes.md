# SG-01 — relatório de testes

Data: 02/11/2026. Windows 11 x64 e Python 3.14. Objetivo: verificar alterações incrementais de propriedade, rollback e mensagens, preservando aprovação manual. A issue anexada termina no item 14.3 com “Falha na primeira”, sem o restante dos critérios; a execução considera o texto disponível.

## Resultados reais

- `python testar_sg01.py`: 18 testes aprovados, incluindo proprietário financeiro alterado, índice de patrocínio ou dívida alterado, bytes iguais em proprietário diferente, falha parcial da primeira e segunda escritas, restauração silenciosamente incorreta, falha de rollback, retomada, journal final, bloqueio da mesma instância, avanço normal da data e estado local pendente.
- `python testar_sg01_interface.py`: teste de snapshot posterior à aplicação passou, confirmando que não repete a operação. A primeira execução falhou porque a fixture usava um snapshot vazio; após corrigir a fixture, passou. É teste de lógica isolada com mocks, não teste visual Tk.
- Regressões offline aprovadas: `testar_emprestimos.py`, `verificar.py`, `testar_sincronizacao_hibrida.py` (12), `testar_compatibilidade.py` (23), `testar_identidade.py` (15), `testar_contratos_dados.py` (26), `testar_patrocinios.py`, `testar_uniformes.py`, `testar_indice_clubes.py` (7) e `testar_sincronizacao_interface.py` (4). Pillow via PYTHONPATH=ferramentas/build-tools.
- Conexão real `FM.connect_manual` e snapshot: Ceará, UID 104749, data no jogo 2032-05-11; espião verificou que WriteProcessMemory não foi chamado. Nenhuma operação real foi aplicada.
- `python construir.py` concluído; executável `bin-sg01-revisado/FMPresidente.exe --self-check` retornou exit=0 e ok=true. Atalhos atualizados; janela anterior precisa ser fechada. Autoteste anterior preservado.

O teste da conexão real é apenas leitura; não valida escrita, rollback real, persistência em save ou impacto de desempenho. Não foram executados testes de falha exaustiva em cada fase dos pools, concorrência real, fechamento inesperado do FM, ciclo salvar/reabrir ou GUI visual. Sem medição de tempo real da seção crítica. O risco de associação à carreira e a segurança semântica dos alocadores permanecem abertos.

Arquivos de código e documentação estão locais, sem commit ou push nesta etapa; modificações locais existentes do relatório fora das issues foram preservadas.
