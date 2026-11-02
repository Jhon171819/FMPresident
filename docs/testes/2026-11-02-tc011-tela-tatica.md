# TC-01.1 — Investigação a partir da tela de tática

Data: 02/11/2026. Windows 11 x64; FM23 build 23.2.0+1771058. Investigação exclusivamente de leitura. O nome do save corrente não foi verificado nesta rodada; não houve escrita em memória ou save.

## Tela e análise estática

A tela Tactics → Overview exibiu Ceará, formação Positive 4-1-1-3-1 DM Wide, titulares e reservas. A tela foi aberta pela navegação do jogo, sem mudar tática ou seleção.

`mapear_classes.main` extraiu RTTI, tabelas virtuais e desmontagem para os painéis de visão geral e elenco, seletor, campo, botão de slot, política de recuperação de jogadores, sessão de edição e `CLIENT_TACTIC`. Arquivos: `engenharia_reversa/tc011/tela_tatica.json` e `.asm`.

## Memória

`python engenharia_reversa/tc011_sondar_tela.py` usa handle de consulta/leitura e BuildGuard, com teto de 2 GiB e 30 s para descoberta. Três varreduras leram aproximadamente 1,04–1,27 GB e atingiram o limite de tempo, sem falhas de leitura informadas. Encontraram um `TEAM_TACTICS_OVERVIEW_PANEL`, um `TEAM_SQUAD_TACTICS_PANEL`, quatro `TACTIC_SLOT_BUTTON` e, nas duas últimas, uma `TACTIC_PLAYER_DATA_RETRIEVAL_POLICY`. Ausências não são prova de inexistência, pois a busca foi limitada.

Com RTTI estático aplicado às referências em memória, foram observadas as seguintes relações, na sessão atual:

- `TEAM_TACTICS_OVERVIEW_PANEL + 0x1b8` → `CLIENT_TACTIC`.
- `TACTIC_PLAYER_DATA_RETRIEVAL_POLICY + 0x58` → o mesmo `CLIENT_TACTIC`.
- Quatro `TACTIC_SLOT_BUTTON + 0x168` → o mesmo `CLIENT_TACTIC`.
- `TEAM_SQUAD_TACTICS_PANEL + 0x1b8` e `TACTIC_PLAYER_DATA_RETRIEVAL_POLICY + 0x38` → a mesma `TACTIC_PLAYER_LIST_TABLE`.

As igualdades foram conferidas duas vezes. O objeto é associado à tela observada, mas ainda não foi demonstrado se representa tática ativa, edição ou escalação confirmada. Não há nomes, funções, posição ou formação decodificados. Nenhum endereço de processo foi persistido neste relatório.

## Testes e limites

`python -m py_compile engenharia_reversa/tc011_sondar_tela.py`: aprovado. `git diff --check`: sem erro, apenas avisos de normalização de fim de linha anteriores. O tempo de 31 s inclui a varredura, mas o rastreamento de RTTI executa depois e aumenta o tempo total; não é apropriado para monitoramento periódico. Não foi feita comparação antes/depois de mudanças, nem homologação entre sessões ou integração à interface.
