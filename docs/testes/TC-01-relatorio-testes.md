# TC-01 — Relatório parcial de testes

Data: 02/11/2026. Ambiente: Windows 11, Python 3.14 e PySide6 em modo offscreen. Objetivo: verificar a primeira versão local da Central Tática.

- `python -m py_compile taticas_local.py FMPresidenteQt.py`: aprovado.
- `python testar_ux01.py`: inicialmente 17/18, devido à expectativa antiga de nove páginas; após atualizar a expectativa, 18/18 aprovados.
- `python FMPresidenteQt.py --self-check`: concluído sem erro no código-fonte.
- Verificação das sete formações: cada uma apresentou onze campos.
- `python construir_qt.py`: compilação concluída em `build/qt-distrib`. O executável compilado não foi submetido a self-check e o atalho não foi alterado.

Limitações: não foi validada a persistência via diálogo, nem teste visual, drag-and-drop, recomendação, leitura de elenco, FMF ou escrita nativa. Não houve teste em save nem escrita na memória do FM nesta issue. O trabalho é parcial; os demais critérios precisam ser conferidos separadamente.
