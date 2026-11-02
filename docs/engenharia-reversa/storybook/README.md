# Reverse Engineering Storybook

Catálogo offline integrado ao SQLite da ER-01 em `dados/er01.sqlite3`. Implementação: `er01_storybook.py`, CLI: `engenharia_reversa/cli.py`. Usa somente a biblioteca padrão de Python e SQLite com FTS5. Não é Storybook.js.

Comece por [catálogo](catalogo.md), [esquema](esquema.md), [guia](guia.md) e [oportunidades](ER-01-opportunities.md). Os documentos individuais, `snapshot.json` e `manifest.json` são gerados do banco; não edite os documentos gerados manualmente.

```powershell
python engenharia_reversa/cli.py storybook seed
python engenharia_reversa/cli.py storybook list
python engenharia_reversa/cli.py storybook search ACTUAL_PLAYER
python engenharia_reversa/cli.py storybook search 0x2B8
python engenharia_reversa/cli.py storybook show ST-03 --build 23.2.0+1771058
python engenharia_reversa/cli.py storybook unmapped
python engenharia_reversa/cli.py storybook opportunities
python engenharia_reversa/cli.py storybook export
```

`seed` importa apenas histórias históricas ausentes. Não sobrescreve descobertas posteriores. As fontes originais permanecem registradas com SHA-256; atualizar uma história preserva integralmente todas as revisões anteriores. Banco e observações dinâmicas têm papéis distintos: consultar histórias não exige processo do FM ou ponteiros válidos. Endereços dinâmicos não são exportados pela sondagem.

O catálogo inicial tem dez histórias; TC-01.1C acrescentou ST-11 para Fernando Nava. A principal correção estrutural está em ST-01: os intervalos anteriormente atribuídos a um TEAM incluem objetos TEAM vizinhos de Fortaleza e Bangu. Consulte o histórico para distinguir a hipótese antiga da evidência nova.
