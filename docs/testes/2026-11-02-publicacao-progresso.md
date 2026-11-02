# Publicação do progresso — verificações locais

Data: 02/11/2026. Ambiente: Windows 11 x64, Python 3.14, PySide6 em modo offscreen. Objetivo: preparar a publicação do progresso acumulado de SG-01/01.1, PF-01/01.1/01.2, UX-01/01.1/01.2, Central Tática e ER-01/TC-01.1C no repositório Jhon171819/FMPresident e uma cópia versionada no Drive do proprietário.

## Escopo

Inclui código-fonte, assets existentes, interface Qt, testes, ferramentas de investigação, documentação, capturas de homologação, benchmarks e Storybook. O README foi atualizado para a entrada Qt e explicita as limitações nativas. A imagem original do brasão foi preservada.

Git exclui dados da sessão, saves, backups, SQLite local, executáveis, dependências instaladas e resultados brutos das pesquisas. A lista explícita de scripts e guias de engenharia reversa foi ampliada no .gitignore, mantendo ferramentas/dependências e artefatos volumosos ignorados.

O pacote privado de pesquisa no Drive deve preservar uma cópia consistente do SQLite ER-01 e os resultados brutos de investigação; não inclui o executável comercial do FM, saves ou credenciais. O arquivo de código deve corresponder a um commit identificado por SHA. Os manifests de publicação ficam em dados/publicacao e não são versionados.

Uma referência à pasta privada do Drive foi removida da cópia pública do relatório de atividades fora das issues. O original foi preservado em dados/publicacao/originais. Resultados e conclusões desse relatório não foram alterados. Não foram encontrados padrões selecionados de credenciais nos arquivos candidatos; essa varredura não constitui garantia absoluta de ausência de informação sensível. Duas capturas Qt foram inspecionadas: interface de teste, sem dados de conta ou autenticação.

O .gitattributes preserva os bytes das evidências táticas e das exportações do Storybook, evitando que normalização automática de quebras de linha invalide os SHA-256 registrados. Os hashes também são conferidos contra os blobs preparados para o commit, além dos arquivos locais.

## Testes executados nesta preparação

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='C:\Users\User\Documents\FMPresidente\ferramentas\qt-tools;C:\Users\User\Documents\FMPresidente\ferramentas\build-tools;C:\Users\User\Documents\FMPresidente'
$env:QT_QPA_PLATFORM='offscreen'
python -m unittest discover -s . -p 'testar_*.py'
python testar_emprestimos.py
python testar_patrocinios.py
python verificar.py
python testar_uniformes.py
```

Resultados reais: **281 testes em 6,233 s — OK**. Os quatro scripts adicionais também terminaram com sucesso: empréstimos (negociação, parcelas, reserva, crédito e rollback simulados), patrocínios (50 marcas e 172 rodadas), datas/transações e uniformes 2D/3D. Nenhuma opção --live foi usada. Nenhum save ou dado do processo do FM foi modificado nesta publicação.

Essas verificações ampliam a cobertura offline da preparação; não substituem homologação no jogo. A contratação de dívida ainda não tem persistência validada após salvar/reabrir, e o leitor tático genérico continua não homologado. Os relatórios anteriores foram preservados.

## Conferências de publicação

Antes do commit: revisão do diff, arquivos candidatos, padrões de credenciais, exclusões de arquivos locais, sintaxe Python e integridade da exportação Storybook. Os resultados do push e das transferências, incluindo commit remoto, tamanhos e checksums quando disponíveis, são registrados no recibo local em dados/publicacao após a conclusão. Este relatório registra as verificações locais; não presume resultado de upload ainda não executado.
