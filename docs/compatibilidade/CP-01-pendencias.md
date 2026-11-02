> **Atualização em 2026-11-01:** o perfil exato `fm23-23.2.0-1771058` foi homologado explicitamente com base na identidade verificada, testes de leitura atuais e registros históricos. As referências abaixo ao perfil pendente refletem o estado anterior e foram preservadas como histórico. Isso não comprova persistência, propriedade de endereços nem segurança de todas as operações. Consulte [o relatório de homologação](../testes/2026-11-01-homologacao-build.md).

# CP-01 — pendências e riscos

| Pendência AU-02 | Estado | Próxima ação |
|---|---|---|
| PEND-01 | Parcial: formato real do cache inspecionado; não foi executado teste automatizado com cópia histórica de todos os formatos. | Fixtures históricas sem dados pessoais em issue futura. |
| PEND-02 | Parcial: `ProcessIdentity` e `Evidence` integrados ao guard; outros consumidores permanecem legados. | Migrar gradualmente nas issues de domínio. |
| PEND-03 | Parcial: identificação atual somente leitura realizada; nenhuma escrita, save/reload ou outro clube. | Homologação controlada e CP-02/SG-01. |
| PEND-04 | Parcial: guard executa antes de consultar cache; `club` permanece ponteiro, não UID; sem migração. | Adaptadores completos em issue futura. |
| PEND-05 | Parcial: resultado e perfil congelados e tuplas; guard guarda cópia rasa de metadados escalares. | Rever demais modelos AU-02. |
| PEND-06 | Parcial: 26 testes de contratos e quatro scripts offline executados; diff Git indisponível pois projeto não é repositório. | Cobertura adicional dos caminhos e comparação em repositório versionado. |

AU-01: R06 mitigado por bloqueio central e identificação criptográfica do arquivo; a equivalência integral do módulo ainda não é provada e nenhuma build está homologada. R03 parcialmente mitigado por bloquear builds incertas; risco de pools permanece. R01, R02 e R04 continuam P0 pendentes de CP-02/SG-01; R05, R07, R08, R09, R10, R11, R12, R13, R14 e R15 permanecem pendentes conforme AU-01. R16 parcialmente mitigado pelos novos relatórios, sem reescrever pesquisa histórica. Nenhum risco P0 foi considerado resolvido.

Homologação: a correspondência de hash e amostras na sessão atual não prova a segurança de escrita nem persistência. Falta validação controlada e revisão do perfil. Também faltam testes automatizados independentes por operação e estado, teste visual completo da interface e verificação de cenários concorrentes.
