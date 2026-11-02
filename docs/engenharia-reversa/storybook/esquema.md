# Esquema do Storybook

Versão própria: 2, em `storybook_meta`. A versão 1 do armazenamento ER-01 permanece intacta. Migração 1→2 reconstrói apenas o índice textual derivado e associa seu rowid ao da história; preserva corpos e histórico. Versões desconhecidas são rejeitadas.

`stories` tem chave `(id, build)`, equivalência única `(build, equivalence)`, objeto, categoria, estado, corpo JSON e revisão. Há índices B-tree por objeto/build, categoria/build/estado e estado/build. `story_search` usa FTS5, pesquisa por frase literal e junção por rowid. RVA e offset devem ser consultados na forma hexadecimal registrada, por exemplo `0x2B8`; a busca não converte decimal para hexadecimal. Busca textual inclui hipóteses e evidências. Não interpreta operadores FTS fornecidos pelo usuário.

O corpo exige id seguro, título, categoria, build, objeto, descrição funcional, comportamento observado, hipótese, evidências, lacunas, dependências, próximos experimentos, custo, fontes, bloqueadores, offsets e RVAs. Cada evidência exige descrição, estado e fonte vinculada. Cada fonte exige caminho e SHA-256. O hash identifica a versão da fonte consultada; não é automaticamente reescrito ao editar a fonte.

`story_history` mantém corpo anterior por revisão, estado anterior/novo, justificativa, evidências, instante UTC Unix, ferramenta e contexto original. Corpo e histórico são publicados na mesma transação SQLite `BEGIN IMMEDIATE`; a busca também é atualizada nessa transação. Repetir um corpo idêntico não cria revisão. Outro id com equivalência já existente é rejeitado; não há fusão por similaridade. Equivalência pode ser fornecida explicitamente, ou derivada de objeto e hipótese normalizados para caixa.

Estados: UNMAPPED, HYPOTHESIS, OBSERVED, PARTIAL, VERIFIED, REFUTED, INCONCLUSIVE e DEPRECATED. Mudanças de estado são explícitas; refutação e reabertura preservam o histórico. VERIFIED exige `verified_scope` e uma evidência marcada VERIFIED. Esse controle valida a presença da declaração; não julga automaticamente se a prova científica é suficiente. A decisão de homologar permanece humana e específica à propriedade descrita.

`show --target-build` retorna SAME_BUILD, UNVERIFIED_OTHER_BUILD ou NOT_ASSESSED. SAME_BUILD indica somente correspondência da build declarada, não homologação automática. Builds novas recebem registros separados; nenhuma descoberta antiga é apagada. Dependências entre histórias são referências de conhecimento, podem conter ciclos e não disparam execução.

Exportação: documentos por id e hash da build, catálogo, snapshot JSON completo com histórico e relatório de oportunidades. O manifesto identifica revisão de cada história e SHA-256 de cada arquivo gerado. Para conferir atualização, compare as revisões do manifesto com o SQLite e regenere explicitamente. O exportador não remove arquivos antigos; o catálogo e o manifesto delimitam os arquivos ativos dessa exportação.
