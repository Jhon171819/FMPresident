# CP-02 — pendências

R01 P0: mitigado pelo bloqueio, não resolvido; carece de identidade nativa de carreira e treinador, testes de troca de save e vínculo. R02, R03 e R04 P0 permanecem para SG-01. R05 P1 parcialmente mitigado por descoberta diagnóstica dinâmica; caminhos de negócio, recursos e uniformes continuam específicos do Ceará e outros clubes não foram homologados. R10 P1 permanece para SG-02. R11 P1 mitigado por bloqueio, sem garantia de desfazer. R15 P2 mitigado por manter dados locais legados sem associação automática, sem migração. Demais riscos da AU-01 continuam conforme os registros anteriores.

AU-02 PEND-01: formatos históricos ainda requerem fixtures amplas. PEND-02: integração parcial por identidades e evidências. PEND-03: não foram feitos testes atuais de escrita/persistência. PEND-04: cache legado é recusado antes do uso, mas adaptadores completos faltam. PEND-05: nova estrutura usa dataclasses congeladas, sem resolver todos os modelos. PEND-06: regressões offline executadas nesta issue, cobertura individual de todos os caminhos ainda insuficiente.

CP-01: guard, perfil específico e hash preservados. Comparação integral da imagem, rollback, concorrência, save/reload e outros clubes permanecem pendentes. A instância anterior do aplicativo, enquanto aberta, não recebe o novo guard.

Antes do beta: investigar e validar identificação do save e do humano em estados diferentes; distinguir carregamento, múltiplos humanos e desemprego; testar mudança de save no mesmo processo com mesmo clube/data; implementar autorização ligada a evidências e revalidação; testar interface e cada caminho de escrita; executar SG-01 e SG-02. A identificação dinâmica implementada é apenas ferramenta diagnóstica, não foi validada como enumeração completa.
