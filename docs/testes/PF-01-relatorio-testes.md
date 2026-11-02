# PF-01 — Relatório de testes

Data: 2026-11-02. Windows 11 x64, Python 3.14.0, PyInstaller 6.22.3. FM23 aberto para medições somente leitura; nenhuma escrita de teste no jogo ou save. Comandos Python utilizaram `PYTHONPATH=ferramentas/build-tools;ferramentas`.

| Comando | Resultado |
|---|---|
| `python testar_pf01.py` | 6 testes aprovados: thread, renderização, resultado obsoleto, seleção e single-flight |
| `python testar_sg01.py` | 18 aprovados |
| `python testar_sg01_interface.py` | 1 aprovado |
| `python testar_sg011.py` | 20 aprovados |
| `python testar_sg011_interface.py` | 1 aprovado |
| `python testar_sincronizacao_hibrida.py` | 13 aprovados |
| `python testar_compatibilidade.py` | 23 aprovados |
| `python testar_identidade.py` | 15 aprovados |
| `python testar_contratos_dados.py` | 26 aprovados |
| `python testar_indice_clubes.py` | 7 aprovados |
| `python testar_sincronizacao_interface.py` | 4 aprovados |
| `python testar_emprestimos.py` | aprovado; script com fixture simulada |
| `python testar_patrocinios.py` | aprovado; script de verificações |
| `python testar_uniformes.py` | aprovado; script de verificações |
| `python verificar.py` | aprovado; script de verificações |
| `python medir_pf01.py --live --output ...` | baseline e depois registrados em JSON |
| `python construir.py` | compilação PyInstaller; assets copiados automaticamente |

Inicialmente o benchmark falhou por falta de PIL no PYTHONPATH; corrigido apontando para as ferramentas existentes. Quatro dos primeiros testes PF-01 falharam devido à ausência do método `poll` no mock; fixture corrigida, 6 testes passaram. O teste de seleção/filtro foi repetido após a alteração. As demais regressões passaram antes da última alteração localizada de interface; o teste correspondente foi reexecutado depois. Não foram executadas operações administrativas reais, cenários completos de inicialização ou homologação visual completa do executável. Ver `PF-01-benchmarks.md` para números, limitações e comparação.

Autoteste compilado: executável iniciado com diretório de trabalho temporário, retorno 0 e JSON indicando ok=true/frozen=true. Assets copiados automaticamente durante a construção. Compilação instalada em bin-pf01 e atalho atualizado; a versão anterior foi preservada. A janela compilada nova não foi aberta durante a sessão existente, para não encerrá-la e perder a aprovação atual.
