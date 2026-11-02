# Pendências e limites

- O parser de PE usa mmap no novo motor; scripts históricos continuam com comportamento antigo salvo strings limitadas. O índice RTTI novo está restrito ao perfil/seção desta build.
- Não há cache validado retroativo dos 189 grafos sem versão/entrada originais; são consultáveis como LEGACY_UNVERIFIED. Para análises novas, calcular somente RVAs explicitamente solicitados.
- Integração dinâmica real não foi feita: SnapshotReads foi validado apenas em memória simulada. Requer contexto aprovado, Reader/BuildGuard e orçamento antes de usar em TC-01.1C.
- Aprofundar um grafo parcial reprocessa essa função com novos limites; não retoma bloco interno do Capstone. SQLite serializa cálculos escritores; medir necessidade antes de criar leases por artefato.
- Medidos RSS/pico Working Set e I/O lógico do próprio processo em uma rodada adicional. I/O físico e recuperação por desligamento abrupto real permanecem não testados. Banco estruturalmente corrompido é recusado/preservado, sem recuperação assistida implementada.
- Migrações destrutivas futuras exigem backup; esta versão apenas cria/adiciona tabelas idempotentes do esquema v1 e recusa versões desconhecidas.
- Planejamento é fila auditável acionada explicitamente; não executa automaticamente hipóteses nem estima probabilidade de descoberta. Não há painel Qt ou nova build, pois esta é infraestrutura CLI.

Atualização após solicitação de testes: SnapshotReads passou em uma âncora de código do FM real, e recuperação após TerminateProcess passou em três auxiliares descartáveis. Integração com objetos mutáveis e queda de energia continuam pendentes. O detalhamento e os limites da validação estão em docs/testes/ER-01-validacao-adicional.md.
