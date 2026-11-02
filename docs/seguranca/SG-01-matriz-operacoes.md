# SG-01 — matriz de operações e limites

Auditoria do código em 02/11/2026. As escritas do app no processo passam por `Memory.write`, normalmente por `FM.transaction`; arquivos JSON e gráficos são caminhos separados.

| Operação | Objeto / campos | Pré-condições e escrita | Reversão / limites |
|---|---|---|---|
| Aporte | finance +20 | build, sessão aprovada, clube, saldo e propriedade finance, bytes | rollback relido; sem lançamento contábil completo comprovado |
| Orçamento | finance +1956 e +2024 | limites, finance atual e bytes | múltiplos campos; rollback relido |
| Bilheteria | finance +24 e +28 | limites, finance e bytes | múltiplos campos; rollback relido |
| Infraestrutura | finance +20, info +288/299/300/301 | recursos, nível, proprietários e bytes | débito e nível; sem garantias contábeis totais |
| Patrocínio / rescisão | registro da coleção e eventualmente finance +20 | coleção reconstituída por índice/endereço e bytes; validação financeira | journal `local_commit` pendente até escrita dos arquivos locais; gráficos separados |
| Dívida existente: renegociação/quitação | registro da coleção e campos financeiros | índice/endereço, bytes, data, saldo, build e pausa | rollback de bytes relido; resultado sem prova de persistência |
| Contratação / expansão | pool de contratos, allocator, vetor, registros e finanças | layout e verificações prévias existentes, reserva dentro da pausa | invariantes de cada bloco e alocador ainda não integralmente comprovadas; rollback de bytes não prova restauração semântica do alocador |
| Flag de uniforme | team +46 | team e bytes existentes | propriedade não registrada no plano; pendente |
| Desfazer | alterações históricas | PID/início, ponteiro, data e bytes; planos novos preservam ownership | journals legados não possuem provas de propriedade completas |
| Arquivos de uniformes | gráficos e XML | instalação de arquivos própria | não é transação única com FM ou JSON; SG-02 |
| JSON, journal e marcas | disco | gravação atômica de arquivo individual | nenhuma transação distribuída; local_commit pendente exige reconciliação segura |

A cobertura de propriedade é parcial: registros planejados sem `ownership`, pools/listas novas, conteúdo alocado, flag de equipe e entradas legadas mantêm verificações anteriores, sem propriedade comprovada. Faltam rastreabilidade para cada bloco, alinhamento e ciclo de vida completos. Permanece o risco de save diferente com as mesmas observações durante aprovação manual.
