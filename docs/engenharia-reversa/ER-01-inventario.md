# Inventário

| Componente | Entrada/saída e duplicação | Migração |
|---|---|---|
| analisar_executavel.PE | lê PE, RTTI, .pdata; antes carregava binário inteiro e string copiava o restante da seção | mmap opcional e strings limitadas a 4 KiB; API anterior preservada |
| mapear_classes | nomes → classes/vtables/ASM; repete desmontagem por slot | fonte histórica preservada; novo class indexa metadados sem desmontagem |
| investigar_gestao.graph | RVA/limites → blocos/arestas/chamadas | reutilizado por cache determinístico |
| tc011b_estatica | quatro classes/189 métodos reprocessados sempre | entrada explícita --exe, cache por função no fluxo padrão |
| tc011_sondar_equipe | candidato validado → sondagens limitadas de coleções; stdout | não executado nesta issue; nenhuma migração operacional de ponteiros |
| tc011_sondar_tela | ~1 GB/30 s + RTTI extra por busca | preservado como diagnóstico caro; não acionado pelo motor |
| tc011b_nomes | coleta dirigida e classificação heurística | evidências importadas, não leitor operacional |
| evidencias_taticas | validadores puros, sem persistência | complementado pelo registro SQLite sem promoção automática |
| indice_clubes | SQLite por PID/início/hash/endereço | não substituído; não é identidade de save |

Capstone local é necessário para análise estática nova. Consultas ao índice, evidências e planejamento não precisam dele nem do executável. Artefatos antigos não contêm identidade suficiente do algoritmo; permanecem LEGACY_UNVERIFIED. Riscos principais: executar análise pesada sem orçamento e confundir cache com validade de ponteiros; o modo padrão novo é offline.
