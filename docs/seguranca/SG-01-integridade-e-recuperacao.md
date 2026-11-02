# SG-01 — integridade e recuperação (implementação parcial)

## Proteções adicionadas

A transação existente mantém BuildGuard, contexto manual, journal e suspensão. `change()` registra o proprietário observado para campos em finance/info; patrocínios e dívidas existentes registram índice e endereço. Dentro da pausa, o plano reconstrói os ponteiros/coleções correspondentes e compara propriedade e bytes antes da primeira escrita. A mesma prova, quando disponível, é repetida antes da restauração.

Uma escrita tentada é incluída no rollback mesmo que a chamada retorne erro, pois pode ter ocorrido escrita parcial. Cada restauração é relida. Se todas as restaurações forem conferidas, journal `rollback_verified`; se alguma falhar, `recovery_required`, com listas de campos restaurados e incertos. A autorização manual é revogada e novas transações na instância são bloqueadas quando existe journal preparado, recuperação necessária ou patrocínio aplicado com commit local pendente. Uma falha ao atualizar o journal após aplicação informa que foi aplicado e impede repetição na sessão. Falha de retomada produz recuperação necessária. Arquivo de journal ilegível não é reconhecido pela busca atual: essa é limitação aberta.

A preparação de patrocínio registra `local_commit=pending`; após persistir os arquivos locais, o estado passa para `committed`. A recuperação automática por simples coincidência de valores deixou de ser chamada durante refresh; não há ainda interface completa para reconciliar o estado pendente. Se o snapshot após transação aplicada falhar, a interface comunica a aplicação e não orienta repetir.

A data de jogo deixou de ser comparada como identidade de contexto pelo monitor. Planos individuais que dependem da data ainda podem exigir atualização, como propostas de empréstimo. A aprovação manual e a ausência de ID nativo do save permanecem; não se afirma identidade comprovada.

## Limitações importantes

A revalidação de propriedade é incremental, não cobre todos os endereços. Alocador, reservas de pool, flag de uniforme, expansão de vetores, transações antigas e mudanças sem ownership não estão integralmente protegidos. O rollback relido não prova consistência semântica dos pools ou atomicidade contra outro processo. Journal irrecuperável, queda do sistema, falha de escrita do disco e encerramento do FM podem deixar resultado desconhecido; `prepared` da mesma instância é tratado como pendente, mas a recuperação persistente e reconciliação após reinício pertencem também à SG-02. A verificação de journal é vinculada à instância, não identifica save. Arquivos gráficos e JSON não são transação distribuída; a verificação do registro local não substitui testes de cada falha de instalação.

Não foi medido o custo real adicional da pré-validação, o tempo de pausa ou o número real de leituras em operações; não se alegam metas de desempenho. Não foram realizadas escritas reais ou testes de concorrência com FM nesta issue.

## Situação

Parcialmente concluída. R01 permanece aberto; R02/R03/R04 mitigados parcialmente, não resolvidos. R09/R12 mitigados parcialmente; R05/R07/R08/R10/R11/R13–R16 permanecem conforme auditoria, com evolução de data corrigida apenas para o comparador do monitor. A continuação deve cobrir ownership de pools, vetores e flag, falhas de journal, reconciliação local, persistência e plano seguro SG-02.
