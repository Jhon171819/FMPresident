<div align="center">
  <img src="assets/fmpresidente-logo.png" alt="Brasão do FMPresidente" width="300">

# FMPresidente

**Assuma a presidência e acompanhe as decisões do seu clube no Football Manager 2023.**

Aplicativo desktop para Windows com interface PySide6, gestão financeira, patrocínios, infraestrutura, empréstimos e planejamento tático local.
</div>

## O que você pode fazer

- Acompanhar caixa, orçamentos, folha salarial e data da carreira.
- Administrar aportes, orçamentos, ingressos e investimentos em infraestrutura.
- Negociar patrocínios e gerenciar a aparência dos uniformes.
- Simular condições de empréstimos, renegociar e quitar contratos; contratar quando as validações da sessão e da reserva nativa permitirem.
- Consultar o histórico das decisões e desfazer operações compatíveis com a sessão atual.
- Consultar diagnósticos e registros de recuperação de operações.
- Montar e salvar planos táticos locais com sete formações, onze titulares e nove reservas.

## Estado atual da pesquisa

A infraestrutura **ER-01** oferece SQLite, cache incremental, índices de classes/funções, grafos, checkpoints, métricas e CLI. O [Storybook de Engenharia Reversa](docs/engenharia-reversa/storybook/README.md) reúne onze histórias com fontes, evidências, hipóteses, histórico e bloqueadores. Consulte o [catálogo](docs/engenharia-reversa/storybook/catalogo.md) e as [oportunidades de melhoria](docs/engenharia-reversa/storybook/ER-01-opportunities.md).

A investigação TC-01.1C recuperou dois casos fortes de nome/nascimento e demonstrou relações RTTI entre ACTUAL_PLAYER, PLAYER e PERSON. O leitor genérico de nomes, UID persistente e a ligação entre linha tática e objeto do jogador **ainda não foram homologados**. Os nomes da Central Tática continuam manuais, e o plano local não é aplicado ao FM.

A contratação de empréstimos teve ensaio na memória do jogo; a persistência após salvar/reabrir continua pendente. A [situação da TC-01.1C](docs/taticas/TC-01.1C-pendencias.md) e os [relatórios de testes](docs/testes/) distinguem fixtures, observações reais e limitações.

## Compatibilidade e funcionamento

O projeto foi desenvolvido para **Windows**, Football Manager 2023 **23.2.0+1771058** e o **Ceará**. O aplicativo procura uma build específica e verifica sua compatibilidade antes de acessar os dados do jogo. Outros clubes e versões ainda não foram homologados.

A seleção manual aprova o clube escolhido para a sessão, mas não comprova a identidade do save. Ao trocar de carreira, sincronize e selecione o clube novamente. Algumas alterações são aplicadas diretamente à memória do jogo: mantenha um backup da carreira antes de usá-las.

## Como começar

1. Abra o Football Manager 2023 e carregue sua carreira.
2. Abra o FMPresidente e clique em **Sincronizar com FM23**.
3. Selecione o candidato correspondente ao clube e clique em **Aprovar seleção**.
4. Use a navegação lateral para acompanhar os dados e tomar decisões.

Consulte [EMPRESTIMOS.txt](EMPRESTIMOS.txt) e [PATROCINIOS.md](PATROCINIOS.md) para mais detalhes sobre essas funcionalidades.

## Desenvolvimento

Requer Windows e Python. Instale as dependências com:

```powershell
python -m pip install -r requirements.txt -r requirements-qt.txt
```

Para executar o aplicativo a partir do código:

```powershell
python FMPresidenteQt.py
```

Para compilar a distribuição local:

```powershell
python construir_qt.py
```

A distribuição Qt é criada em `build/qt-distrib`; instalar ou trocar um atalho é uma etapa separada. A entrada histórica Tkinter continua em `FMPresidente.pyw`, com compilação por `construir.py`. Os avisos de licença Qt estão em [avisos-qt](avisos-qt/LEIA-ME.txt).

Para executar os testes offline:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m unittest discover -s . -p 'testar_*.py'
python testar_emprestimos.py
python testar_patrocinios.py
python verificar.py
python testar_uniformes.py
```

As opções `--live` podem acessar ou modificar a memória do jogo conforme o script. Consulte cada ferramenta antes de executá-las; testes operacionais usam somente save descartável autorizado.

Para consultar a pesquisa sem abrir o FM:

```powershell
python engenharia_reversa/cli.py storybook seed
python engenharia_reversa/cli.py storybook list
python engenharia_reversa/cli.py storybook search ACTUAL_PLAYER
python engenharia_reversa/cli.py storybook show ST-03
```

`seed` importa as dez histórias históricas iniciais e preserva registros existentes. O estado exportado das onze histórias, com histórico, está em [snapshot.json](docs/engenharia-reversa/storybook/snapshot.json); o banco de trabalho fica localmente em `dados/er01.sqlite3`.

## Dados locais

Saves, backups, dados de conexão, negociações, executáveis compilados, dependências locais e resultados brutos de investigação não são incluídos no repositório. Alguns relatórios históricos permanecem apenas localmente enquanto aguardam revisão de privacidade.
