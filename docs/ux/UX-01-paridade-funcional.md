# UX-01 — Paridade funcional

Inventário criado antes da implementação e atualizado em 02/11/2026. Tkinter permanece principal; presença de página não significa paridade.

| Funcionalidade | Serviço | Qt | Evidência/limite |
|---|---|---|---|
| Sincronização e candidatos | observe_and_candidates | integrada | worker e épocas; homologação completa pendente |
| Aprovação manual | FM.connect_manual | integrada | confirmação e revalidação; não aprova automaticamente |
| Dashboard | FM.snapshot | integrado | renderização sintética e testes de estado |
| Aporte/orçamentos/bilheteria | FM.capital/budgets/prices | integrados | serviço único, confirmação; nenhuma escrita real de teste |
| Infraestrutura | FM.invest | integrada | mostra nível/custo; regras nativas preservadas |
| Contratos de patrocínio | snapshot.sponsors | integrada em UX-01.1 | catálogo, negociação, rescisão e commit local reutilizam `negociacao.py`/FM; homologação de escrita pendente |
| Renegociação e quitação | emprestimos.offer/sign; FM.repay | integradas | sem reescrever cálculos; homologação de fluxo pendente |
| Novo empréstimo | guarda existente | restrito | não liberado |
| Modo do uniforme | FM.set_licensed_kits | integrado em UX-01.1 | prévia, geração e instalação gráfica reutilizam `uniformes.py`; homologação de instalação pendente |
| Histórico/desfazer | journals; FM.undo | integrados | filtro; guardas existentes; legado sem ownership recusado |
| Recuperação | recuperacao.scan | integrada | desconectada, orientação e exportação; sem bypass |
| Pasta/backup | os.startfile; backup_save | integrados | nenhuma cópia de save real executada em teste |

Não há promoção do atalho principal nem homologação operacional de escrita. Ver `UX-01.1-paridade.md`, `UX-01.1-patrocinios.md` e `UX-01.1-uniformes.md` para a integração nova e suas limitações.
