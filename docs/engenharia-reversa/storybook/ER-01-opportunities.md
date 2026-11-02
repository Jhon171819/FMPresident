# Oportunidades ER-01 — gerado do Storybook

Frequência mede alcance, não viabilidade. Custos de melhoria são estimativas qualitativas; medições históricas ausentes não são zero.

Ordenação: número decrescente de histórias abertas beneficiadas; empate por bloqueador.

| Bloqueador | Histórias | Grupo | Recomendação | Custo estimado |
|---|---|---|---|---|
| INSUFFICIENT_SAMPLES | 5: ST-01, ST-02, ST-03, ST-10, ST-11 | Observações dinâmicas | Repetir amostras limitadas com validação visual e contexto explícito. | baixo |
| UNVERIFIED_POINTER_CHAIN | 5: ST-04, ST-05, ST-06, ST-07, ST-08 | Metadados | Registrar segmentos e referências cruzadas sem unir lacunas por inferência. | médio |
| UNKNOWN_OBJECT_LAYOUT | 4: ST-01, ST-02, ST-04, ST-10 | Inferência de tipos | Comparar layouts e ajustes de subobjetos com proveniência por build. | médio |
| MISSING_UID | 3: ST-03, ST-10, ST-11 | Qualidade das evidências | Confrontar identificador candidato com fonte independente. | alto |
| UNRESOLVED_VIRTUAL_CALL | 3: ST-05, ST-06, ST-07 | Cobertura de análise | Resolver destinos virtuais apenas com vtable e tipo demonstrados. | alto |
| UNRESOLVED_STRING | 2: ST-03, ST-11 | Strings | Classificar representação e propriedade do texto em amostras dirigidas. | médio |
| DYNAMIC_OBJECT_LIFETIME | 1: ST-08 | Cache | Invalidar observações ao mudar processo, época ou âncoras. | médio |
| EXPENSIVE_SCAN | 1: ST-09 | Performance | Preferir caminhos tipados já conhecidos e medir orçamento por fase. | médio |
| PARTIAL_GRAPH | 1: ST-09 | Grafos | Investigar retomada dentro da função, preservando fronteira e parâmetros. | alto |

## Estruturas abertas

- ST-01 — TEAM: TEAM+0x38 contém um intervalo de jogadores. Os intervalos observados em +0xF0 e +0x1A8 a partir da primeira base pertencem a outros objetos TEAM nesta amostra, não a três grupos comprovados do Ceará.
- ST-02 — ACTUAL_PLAYER: Campos contêm referências a equipes; o vínculo contratual não está demonstrado.
- ST-03 — ACTUAL_PLAYER: Possível representação de nome e nascimento associada a um objeto de atleta.
- ST-04 — PLAYER / PERSON: RTTI vincula ACTUAL_PLAYER a PLAYER e às bases virtuais ACTUAL_PERSON e PERSON; estas estruturas participam do objeto, sem método genérico de identidade demonstrado.
- ST-05 — TACTIC_PLAYER_LIST_TABLE: Componente de apresentação de jogadores na tática; métodos percorrem intervalo interno, origem dos atletas não demonstrada.
- ST-06 — TACTIC_PLAYER_DATA_RETRIEVAL_POLICY: Converte e recupera metadados usados pela interface; retorno como identidade de atleta não demonstrado.
- ST-07 — 0x64726566: Chave usada por rotinas de transformação e busca em registros internos; semântica desconhecida.
- ST-08 — CLIENT_TACTIC: Objeto compartilhado por componentes da interface de táticas na sessão observada.
- ST-09 — CFG legado: Desmontagem limitada preserva fronteira, mas ainda não explica integralmente estas funções.
- ST-10 — Identificador do atleta: Identificador persistente seria necessário para vincular atletas entre reconstruções; campo ainda desconhecido.
- ST-11 — ACTUAL_PLAYER / Fernando Nava: Segundo caso dirigido de texto e nascimento compatíveis com perfil do jogo, em outro clube; não é membro comprovado do elenco do Ceará.

## Recursos e falhas medidos

Rankings decrescentes, deduplicados por measurement_id. Um lote não é custo isolado de cada função.

```json
{
  "wall_s": [
    {
      "measurement_id": "TC011C-static-helpers-cold",
      "stories": [
        "ST-07"
      ],
      "cost": {
        "cache_hits": 0,
        "cpu_s": 2.390625,
        "failures": 0,
        "functions": 2,
        "measured": true,
        "measurement_id": "TC011C-static-helpers-cold",
        "peak_rss": 414904320,
        "scope": "Lote de dois helpers; não medido por função",
        "wall_s": 2.748244699992938
      }
    },
    {
      "measurement_id": "TC011C-live-identities-1",
      "stories": [
        "ST-03",
        "ST-11"
      ],
      "cost": {
        "bytes": 28416,
        "calls": 192,
        "cpu_s": 1.59375,
        "failures": 0,
        "measured": true,
        "measurement_id": "TC011C-live-identities-1",
        "scope": "Amostra compartilhada de 37 objetos; BuildGuard incluído no tempo e excluído dos contadores SnapshotReads",
        "wall_s": 1.7511946999875363
      }
    }
  ],
  "cpu_s": [
    {
      "measurement_id": "TC011C-static-helpers-cold",
      "stories": [
        "ST-07"
      ],
      "cost": {
        "cache_hits": 0,
        "cpu_s": 2.390625,
        "failures": 0,
        "functions": 2,
        "measured": true,
        "measurement_id": "TC011C-static-helpers-cold",
        "peak_rss": 414904320,
        "scope": "Lote de dois helpers; não medido por função",
        "wall_s": 2.748244699992938
      }
    },
    {
      "measurement_id": "TC011C-live-identities-1",
      "stories": [
        "ST-03",
        "ST-11"
      ],
      "cost": {
        "bytes": 28416,
        "calls": 192,
        "cpu_s": 1.59375,
        "failures": 0,
        "measured": true,
        "measurement_id": "TC011C-live-identities-1",
        "scope": "Amostra compartilhada de 37 objetos; BuildGuard incluído no tempo e excluído dos contadores SnapshotReads",
        "wall_s": 1.7511946999875363
      }
    }
  ],
  "bytes": [
    {
      "measurement_id": "TC011C-live-identities-1",
      "stories": [
        "ST-03",
        "ST-11"
      ],
      "cost": {
        "bytes": 28416,
        "calls": 192,
        "cpu_s": 1.59375,
        "failures": 0,
        "measured": true,
        "measurement_id": "TC011C-live-identities-1",
        "scope": "Amostra compartilhada de 37 objetos; BuildGuard incluído no tempo e excluído dos contadores SnapshotReads",
        "wall_s": 1.7511946999875363
      }
    }
  ],
  "calls": [
    {
      "measurement_id": "TC011C-live-identities-1",
      "stories": [
        "ST-03",
        "ST-11"
      ],
      "cost": {
        "bytes": 28416,
        "calls": 192,
        "cpu_s": 1.59375,
        "failures": 0,
        "measured": true,
        "measurement_id": "TC011C-live-identities-1",
        "scope": "Amostra compartilhada de 37 objetos; BuildGuard incluído no tempo e excluído dos contadores SnapshotReads",
        "wall_s": 1.7511946999875363
      }
    }
  ],
  "failures": [
    {
      "measurement_id": "TC011C-live-identities-1",
      "stories": [
        "ST-03",
        "ST-11"
      ],
      "cost": {
        "bytes": 28416,
        "calls": 192,
        "cpu_s": 1.59375,
        "failures": 0,
        "measured": true,
        "measurement_id": "TC011C-live-identities-1",
        "scope": "Amostra compartilhada de 37 objetos; BuildGuard incluído no tempo e excluído dos contadores SnapshotReads",
        "wall_s": 1.7511946999875363
      }
    },
    {
      "measurement_id": "TC011C-static-helpers-cold",
      "stories": [
        "ST-07"
      ],
      "cost": {
        "cache_hits": 0,
        "cpu_s": 2.390625,
        "failures": 0,
        "functions": 2,
        "measured": true,
        "measurement_id": "TC011C-static-helpers-cold",
        "peak_rss": 414904320,
        "scope": "Lote de dois helpers; não medido por função",
        "wall_s": 2.748244699992938
      }
    }
  ]
}
```

Não há ranking comparável de CPU/erros por método quando as fontes não fornecem essas medições. Valores de uma mesma amostra não devem ser somados entre histórias.

## Automação e capacidades ausentes

Exportação, consultas, validação de esquema e deduplicação são offline. Nenhuma investigação é iniciada automaticamente.

Menor custo estimado: amostragem dirigida. Maior alcance: primeiros bloqueadores da tabela. Falta evidência para estimar horas ou garantia de resolução.

Categorias sem bloqueador ativo permanecem sem recomendação; nenhuma melhoria é implementada por este relatório.
