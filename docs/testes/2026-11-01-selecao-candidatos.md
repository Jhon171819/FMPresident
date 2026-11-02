# Seleção de clubes candidatos — relatório de testes

Data: 01/11/2026. Windows 11 x64, Python 3.14, FM23 aberto. Objetivo: permitir descoberta limitada e seleção diagnóstica de clube, sem autorização de escrita.

- `python -m py_compile sincronizacao_hibrida.py FMPresidente.pyw`: aprovado.
- `python testar_sincronizacao_hibrida.py`: 10 testes aprovados.
- `python testar_identidade.py`: 12 testes aprovados; inclui bloqueio antes da escrita.
- Busca real somente leitura com `search_candidates(256*1024*1024, 5)`: encontrou candidato UID 104749, Ceará Sporting Club; busca limitada. `observe` revalidou o mesmo candidato.
- `python construir.py`: compilação aprovada. `bin-candidatos/FMPresidente.exe --self-check`: saída 0, ok=true. Atalhos atualizados.

A interface oferece busca limitada a 1 GiB/20 segundos, lista com nome, UID e número de registro e seleção revalidada. Em mudança observável ou erro o monitor invalida seleção. A lista não é um censo completo; múltiplos registros podem representar objetos antigos. Apenas o cache da mesma instância é incluído como candidato inicial após inspeção estrutural. A busca não modifica memória e usa handle 0x410.

A seleção não comprova treinador ou save, não ativa operações e não preenche painel de dados administrativos. Não foram realizados teste visual completo da interface, seleção de outro clube real, troca de save, varredura integral nem escrita no FM. Os guards anteriores permanecem inalterados. O relatório de autoteste anterior foi preservado quando disponível.
