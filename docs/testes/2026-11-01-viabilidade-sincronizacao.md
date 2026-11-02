# Viabilidade da sincronização e do monitoramento externo do FM23

Data local: 01/11/2026. Captura: 02/11/2026 01:45 UTC. Ambiente: Windows 11 x64, Python 3.14, FM23 23.2.0+1771058 aberto.

## Parecer

É tecnicamente viável usar Sincronizar como gatilho de invalidação e redescoberta, e manter um monitor externo no FMPresidente. Os testes validam essa mecânica em protótipo. Ainda não foi validado identificar o save carregado nem detectar toda troca de save no mesmo processo. Portanto essas ideias são componentes úteis, mas não bastam, com os campos hoje conhecidos, para liberar operações administrativas.

O botão pode resolver uma parte real do problema: qualquer clique inicia uma nova época local de sincronização, elimina referências anteriores antes da descoberta e rejeita propostas ligadas à época anterior, inclusive se a descoberta falhar. Essa época é do aplicativo; não representa identificador nativo do FM ou prova de identidade do save.

O monitor é uma tarefa externa de leitura, sem necessidade de injeção ou processo dentro do FM. Deve detectar contradições, falhas e alterações e invalidar o contexto. Uma observação igual significa apenas que os campos consultados coincidiram. Não demonstra que o save permaneceu o mesmo. O intervalo de monitoramento também deixa uma janela entre verificações: não existe detecção imediata garantida. Uma validação antes de escrever reduz a janela, mas não elimina concorrência entre validação e escrita.

## Testes executados

`python testar_sincronizacao.py`: 12 testes aprovados, zero falhas. Abrangem nova sincronização com mesmos valores, falha na descoberta, PID, reinício do processo, build, clube, endereço, data, contexto inacessível, entrada inválida, dois saves com observações iguais e recusa permanente de autorização. São fixtures sintéticas; não comprovam semântica nativa nem troca real de save.

O teste decisivo simula A e B com mesmo processo, build, UID, endereço e data. O protótipo retorna SAME_OBSERVATION_IDENTITY_UNPROVEN. Isso demonstra a insuficiência desse conjunto de informações para distinguir os saves; não demonstra impossibilidade de encontrar outra evidência nativa no FM.

`python engenharia_reversa/validar_sincronizacao.py`: três observações reais em cerca de meio segundo, separadas por aproximadamente 250 ms. Handle aberto com direitos 0x410 (consulta e leitura), sem métodos de suspensão ou escrita no leitor. Build validada pela CP-01. O cache foi usado exclusivamente como endereço candidato a inspecionar, após conferir PID e início; não foi tratado como identidade de save. Cada leitura revalidou a estrutura candidata.

Resultados: UID 104749, endereço 0x2fc2ebd0 e data 2032-05-01 nas três observações; identidade de treinador, vínculo ativo e save continuam desconhecidos. Não houve troca manual de save durante o teste. Artefato: engenharia_reversa/identidade/teste-sincronizacao.json. A ferramenta recusa sobrescrever esse arquivo existente.

Regressões executadas: `python testar_identidade.py` (12 aprovados) e `python testar_compatibilidade.py` (23 aprovados). Não foram repetidos motores financeiros, porque os acréscimos são protótipos isolados e não alteram os módulos operacionais.

## Arquitetura possível

1. Sincronizar invalida a época anterior, propostas, ponteiros e associações pendentes antes de qualquer tentativa de descoberta.
2. CP-01 confirma build e instância do processo.
3. Descoberta procura contexto ativo e treinador humano por cadeia ainda a validar, sem escolher objeto arbitrariamente.
4. Uma ligação comprovada entre treinador e equipe/clube define o alvo; sem prova, apenas diagnóstico.
5. Monitor observa referências e sinais nativos de recarregamento, quando descobertos. Falhas e ambiguidades invalidam o contexto.
6. Cada operação precisa validar época local, contexto atual, vínculo e suas próprias pré-condições; SG-01 tratará propriedade de endereços e concorrência.

A sincronização manual não identifica automaticamente a mesma carreira depois de reiniciar o jogo. Histórico, marcas e negociações precisam de associação persistente própria e comprovada, ou devem permanecer pendentes. Seleção visual ou confirmação do usuário é complemento, não prova nativa isolada.

## Próximos experimentos necessários

Em cópias preparadas de saves: capturar antes, durante e depois de carregar B no mesmo PID; repetir A/B com mesmo clube e data, e com treinador desempregado ou transferido. Registrar estado conhecido por fonte independente. Comparar a pessoa HUMAN_NON_PLAYER e seu proprietário/coleção ativa, o vínculo com TEAM e possíveis sinais nativos de geração de mundo. Demonstrar que uma referência muda obrigatoriamente ou que um estado de carregamento invalida o contexto, inclusive quando o monitor começa tarde ou perde uma transição.

Não foram executados: troca real de save, clique na interface do aplicativo, monitor prolongado, mudança real de emprego, múltiplos humanos, salvar/reabrir, escrita de memória ou testes de atomicidade. Nenhuma carreira foi alterada, nenhum botão novo foi integrado e os guards de produção continuam bloqueando operações.

## Conclusão

Sincronização como gatilho: viabilidade demonstrada em protótipo. Monitor externo: leitura real demonstrada e comparação testada sinteticamente. Identificação do save e detecção garantida de sua substituição: ainda não comprovadas. Recomendação: incorporar esse ciclo apenas depois de validar uma fonte nativa de contexto ativo; não usar a estabilidade de UID, data e ponteiros como autorização.
