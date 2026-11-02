# CLI offline

Na raiz do projeto: python engenharia_reversa/cli.py --help. --db CAMINHO é opção global anterior ao comando; padrão dados/er01.sqlite3.

- status / stats: estados, contagens e tamanho do arquivo principal.
- import PASTA --exe FM.EXE: JSONs legados, sem desmontagem.
- index --query ACTUAL_PLAYER --kind legacy_class: histórico agrupado por sujeito.
- class TACTIC_PLAYER_LIST_TABLE --exe FM.EXE: RTTI incremental novo.
- analyze --exe FM.EXE --rva 0x3a88400 --rva 0x3a87f50 --task pesquisa: grafos incrementais.
- analyze ... --instructions 800 --blocks 100: aprofundar especificamente RVAs pedidos.
- analyze ... --force: recalcular explicitamente.
- resume pesquisa --exe FM.EXE: retomar após interrupção.
- queue pesquisa spec.json / plan / task pesquisa --state PAUSED / task pesquisa --state PENDING.
- task pesquisa --priority 20: prioridade manual.
- graph HASH SOURCE_RVA_DECIMAL --depth 3: relações conhecidas.
- evidence / report: JSON de evidências/execuções; stdout pode ser capturado pelo usuário.
- cache-explain CHAVE: estado e motivo de validade.
- invalidate CHAVE: dry-run; --apply confirma mutação do cache.
- clean: dry-run de INVALID; --apply efetiva, sem tocar em originais.
- benchmark --exe FM.EXE --rva 0x3a88400 --rva 0x3a87f50 --rva 0x1de14d0: base temporária fria, quente, mudança localizada, interrupção/retomada e fixture de leitura.

Fonte incremental anterior: python engenharia_reversa/tc011b_estatica.py --exe FM.EXE mostra plano e quatro RVAs parciais, sem reconstruir grafos. Acrescente --rva para solicitar um método ou --refresh-all para solicitar todos explicitamente. Modo antigo explícito: --legacy-rebuild. Consultas não exigem FM aberto. Não há modo real de memória exposto nesta CLI.
