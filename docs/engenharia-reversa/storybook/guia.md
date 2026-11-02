# Guia de manutenção

Todos os comandos aceitam `--db CAMINHO` antes do subcomando `storybook`. A importação inicial usa fontes históricas locais, sem abrir o jogo. Para outra máquina, `snapshot.json` conserva corpos, fontes e histórico exportado; `seed` sozinho restaura apenas o catálogo histórico inicial.

```powershell
python engenharia_reversa/cli.py storybook list --category player_identity --status PARTIAL
python engenharia_reversa/cli.py storybook list --object ACTUAL_PLAYER
python engenharia_reversa/cli.py storybook search 0x3A88400 --build 23.2.0+1771058
python engenharia_reversa/cli.py storybook show ST-04 --build 23.2.0+1771058 --target-build outra-build
python engenharia_reversa/cli.py storybook list --limit 50 --offset 50
```

`unmapped` lista histórias ainda abertas (exclui VERIFIED, REFUTED e DEPRECATED). `list --status UNMAPPED` seleciona apenas esse estado exato. `show` exige build quando há mais de uma versão do mesmo id.

Para atualizar, extraia o corpo de uma história, acrescente evidência com fonte e contexto, salve em JSON e use:

```powershell
python engenharia_reversa/cli.py storybook put historia.json --reason 'Nova observação dirigida' --tool 'sondagem explícita' --context '{"issue":"TC-01.1C","mode":"read_only"}'
python engenharia_reversa/cli.py storybook export --build 23.2.0+1771058
```

No PowerShell, preserve as aspas do argumento JSON. Alternativamente, invoque `Storybook.put` diretamente em Python. Registre a justificativa de refutações e reaberturas. Não apague uma evidência que contrariou a hipótese; explique a revisão. `cost.measured=false` significa custo desconhecido, não zero. Para medição compartilhada, use `measurement_id` e evite somá-la entre histórias.

`blockers` e `opportunities` agrupam códigos do vocabulário em `er01_storybook.BLOCKERS`. Ordenam por número de histórias abertas beneficiadas, com empate pelo código. A redução desse número após uma revisão permite acompanhar resolução de bloqueadores, mas frequência não demonstra viabilidade. Custos de melhorias são estimativas qualitativas, separadas das medições.

O Storybook nunca conecta ao FM ou executa tarefas. O planejador ER-01 pode receber uma tarefa apenas por comando explícito `queue`; `plan` somente ordena. Uma sugestão do catálogo não concede autorização de leitura operacional, escrita, reinício ou troca de save.
