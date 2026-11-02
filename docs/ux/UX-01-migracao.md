# UX-01 — Migração e distribuição

Legado: FMPresidente.pyw ou bin-pf012/FMPresidente.exe pelo atalho principal. Qt: FMPresidenteQt.py ou bin-ux01/FMPresidenteQt.exe. Feche a outra interface antes de abrir Qt: o mutex é compartilhado. A versão Qt não substituiu o atalho principal. Retorno: feche Qt e use o atalho habitual.

Dependência de runtime escolhida: PySide6 Essentials 6.12.0 e Shiboken 6.12.0; os metadados declaram Python >=3.10,<3.16, incluindo 3.14, e foi testado aqui em Windows x64 com Python 3.14. A instalação de desenvolvimento incluiu o metapacote completo, mas requirements-qt.txt pede apenas Essentials. A aplicação usa QtCore/Gui/Widgets; não usa QML/WebEngine. Compilar com construir_qt.py e as ferramentas Qt/build-tools no PYTHONPATH. PyInstaller 6.22.3; plataformas Windows são coletadas por hooks. Assets e avisos são copiados separadamente.

Houve uma falha de importação QtCore causada pela inclusão de icuuc.dll de Poppler no PATH da ferramenta. O script de build passou a usar um PATH explícito de Qt/Python/Windows, evitando DLLs de outras ferramentas. A reprodução final precisa passar no self-check sem correções manuais.

Licenças: consultar avisos-qt/LEIA-ME.txt, [licenças oficiais](https://doc.qt.io/qtforpython-6/licenses.html) e [obrigações publicadas pelo Qt](https://www.qt.io/development/open-source-lgpl-obligations). Foram incluídos textos GPL/LGPL; os metadados do pacote declaram licenças abertas, mas seu License-File aponta para texto comercial. A correspondência de avisos/fontes e a possibilidade de substituição das bibliotecas precisam ser verificadas antes de distribuição pública. Não se declara conformidade completa, nem foi publicada release.
