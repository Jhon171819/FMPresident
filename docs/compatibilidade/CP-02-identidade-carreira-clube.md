# CP-02 — identidade da carreira e clube

Estado: parcialmente concluída; identidade confiável do save e do treinador não demonstrada. A implementação segura bloqueia todas as alterações administrativas enquanto não houver essa evidência.

## Fronteiras e fluxo

`compatibilidade.BuildGuard` continua validando processo, hash e amostras. `identidade.CareerGuard` recebe a identidade de processo AU-02 já validada; representa candidato com `ClubIdentity`, identidade de carreira com `CareerIdentity`, evidências desconhecidas e estados próprios. O guard atual não possui caminho de autorização: a identidade da carreira e do treinador não foi comprovada. A conexão é interrompida antes da leitura ou reutilização do cache legado e antes do snapshot. `FM.transaction`, contratação e quitação exigem o guard; `Memory.write` também o exige antes da API do Windows. Revalidação de propriedade e rollback não são substituídos pela CP-02.

`inspect_candidate` verifica estrutura candidata conhecida da build sem filtrar UID ou nome do Ceará. `discover_candidates` percorre regiões e retorna candidatos sem selecionar qualquer um; é ferramenta diagnóstica, não está ligada a autorização e não prova exaustividade ou suporte multiclubes. Um candidato é apenas observação e pode ser objeto antigo, cache ou representar outro save. A descoberta não é executada automaticamente durante a conexão bloqueada.

A interface informa o bloqueio, não associa as mesas ou histórico legados e mantém os arquivos intactos. Patrocínios existentes não são migrados. O caminho de dados antigo permanece preservado; sua reutilização está atrás de um guard que sempre bloqueia. O título não afirma que o Ceará é o clube conectado. A interface não fornece ainda uma seleção ou exibição completa de candidato/treinador.

## Investigação e evidências

`engenharia_reversa/gestao/MOTORES-E-PRESIDENCIA.md` e `vinculos-sessao.json` documentam uma captura não atômica: classe RTTI `CLUB_HUMAN_MANAGER_DETAILS`, vtable RVA `0x48b7c08`, ponteiro `+0x40` para TEAM, ponteiro de TEAM `+0x30` para clube observado Ceará. O próprio estudo alerta que isso não identifica o jogador humano atual, nem prova estado ativo ou unicidade. Treinador humano, distinção de IA, vínculo de emprego, múltiplos humanos e identidade de save permanecem desconhecidos. Um nome de classe ou ponteiro não é prova de relação ativa.

Nesta sessão, após validar a build, o ponteiro guardado no cache foi inspecionado apenas como candidato diagnóstico, nunca para autorizar operação: foi observada uma estrutura com UID 104749 e nome Ceará Sporting Club. Não prova clube controlado nem identidade de carreira. A mesma data e o mesmo clube podem existir em saves diferentes. PID/início identificam apenas processo; o campo `club` do cache é endereço, não UID. Um endereço pode ser reaproveitado. Carregamento e mudança de save no mesmo processo não são detectáveis com as evidências atuais; por isso nenhuma autorização é emitida.

Não foram demonstradas identificação de treinador desempregado, controle por IA, múltiplos humanos, troca de emprego ou save. Não há suporte comprovado a outros clubes. O rastreamento em memória pode falhar ou omitir candidatos em fronteiras de bloco; não é enumeração autoritativa. Nomes, UID, data e pontas de referências não comprovam identidade persistente.

## Passos futuros

Em ambiente de leitura controlado, comparar múltiplas carreiras e treinadores, mesma data e clube, troca de clube/save sem reiniciar, desemprego, múltiplos humanos e carregamento; documentar uma cadeia nativa e identificador que sobrevivam ou mudem conforme demonstrado. Somente com evidências e testes será possível implementar autorização, revalidação e invalidação precisas. SG-01 deve tratar propriedade dos endereços, concorrência, restauração e recuperação; SG-02 deve vincular backup ao save correto.
