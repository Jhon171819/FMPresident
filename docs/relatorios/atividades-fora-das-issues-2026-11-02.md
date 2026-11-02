# FMPresidente — relatório das atividades fora das issues

**Data de elaboração:** 02/11/2026

**Período recuperável:** 27/10/2026 a 02/11/2026

**Escopo:** solicitações, implementações, pesquisas, correções e organização feitas fora das issues formais AU-01, AU-02, CP-01, CP-02, CP-02.1 e CP-02.1B.

## Critério e limites

Este relatório reúne a conversa disponível e os arquivos locais. Alguns trabalhos começaram antes das issues, e seus registros históricos não identificam uma solicitação formal de origem; são descritos como antecedentes do projeto, sem presumir toda a sequência. Atividades iniciadas em uma issue e retomadas depois a pedido do usuário aparecem somente na parte retomada. As issues em si não são reproduzidas aqui.

As datas são as registradas nos documentos e no horário local. Testes sintéticos, leitura real do processo e intervenções reais históricas são distinguidos. Nenhuma atividade não documentada é tratada como comprovada. O estado mais recente prevalece sobre descrições históricas que foram posteriormente modificadas.

## 1. Projeto existente e mudança para Documentos

O FMPresidente já existia como aplicativo Windows/Python/Tkinter para a carreira do Ceará no Football Manager 2023. O usuário indicou a cópia que estava em uma pasta de trabalho do Codex e pediu uma localização permanente. O projeto foi colocado em `Documentos/FMPresidente`, e o atalho da área de trabalho passou a apontar para a instalação nessa pasta. Os atalhos foram atualizados novamente ao longo das compilações seguintes.

As funcionalidades documentadas do aplicativo incluem acompanhamento de caixa e orçamentos, aportes, infraestrutura, bilheteria, patrocínios, uniformes, empréstimos e histórico. Isso descreve o que o aplicativo oferece; não significa que cada operação tenha sido homologada para outras builds ou clubes.

**Evidências:** [guia local do aplicativo](../../LEIA-ME.txt), [README](../../README.md) e `dados/relocacao.json` local. O guia local contém referências históricas de instalação; o atalho atual foi verificado durante a organização de 01/11.

## 2. Investigação técnica e desenvolvimento de empréstimos

O usuário pediu contratos de empréstimo financeiro — contratação de crédito, juros e negociação — para o FMPresidente. Foi investigado o executável do FM23 por análise estática e leituras de memória. A pesquisa identificou estruturas e fluxos candidatos relacionados a empréstimos, incluindo um registro nativo de 28 bytes, parcelas, crédito, lista e pools. Foram analisadas amostras de dívidas de outras estruturas de clubes; a amostragem não foi uma auditoria de todas as dívidas ativas.

A aba **Empréstimos** passou a oferecer proposta e contraproposta, escolha de valor e prazo, juros, contratação, renegociação e quitação. A negociação apresentada é uma regra implementada no FMPresidente; a pesquisa não comprovou um fluxo nativo de negociação bancária equivalente no FM.

O registro histórico de `dados/validacao-emprestimos.json` relata testes reais reversíveis de criação, crédito/lista, renegociação e quitação, com restauração. Os testes offline cobrem cálculo, reserva simulada, operações e rollback. **Não foram comprovados nessa validação o avanço até o vencimento, o processamento de todas as parcelas ou a persistência após salvar e reabrir.** Os riscos de pools, propriedade de endereços e rollback continuam relevantes.

**Evidências:** [guia de empréstimos](../../EMPRESTIMOS.txt), [pesquisa local de empréstimos](../../engenharia_reversa/EMPRESTIMOS.md), [teste offline](../../testar_emprestimos.py) e `dados/validacao-emprestimos.json` local.

## 3. Patrocínios, uniformes e pesquisa anterior

Os registros anteriores às issues documentam um mercado de patrocínios com catálogo de marcas, propostas, contrapropostas, prazos, cláusulas e contratos. O guia descreve o tratamento do valor anual e da vigência na aplicação ao contrato nativo. Os perfis e negociações do aplicativo não representam propostas reais das empresas.

Também foram documentados ajustes de vinculação e aplicação de patrocinadores aos uniformes 2D/3D, verificação de arquivos e opção de voltar ao estilo do editor. O registro histórico de uniformes informa verificação de imagens 2D no FM, mas **não** confirma a visualização dos arquivos 3D em partida. Há registros históricos de testes reversíveis de patrocínio; eles não substituem homologação de todos os cenários.

A pesquisa local anterior também analisou estruturas e hipóteses de finanças, instalações, gestão, scouting, responsabilidades e merchandising. Parte dos resultados consiste em nomes de classes, acesso a campos ou ligações observadas, e não em semântica ou comandos completos comprovados.

**Evidências:** [guia de patrocínios](../../PATROCINIOS.md), [pesquisa inicial](../../engenharia_reversa/LEIA-ME.md), [gestão e responsabilidades](../../engenharia_reversa/gestao/MOTORES-E-PRESIDENCIA.md), [merchandising](../../engenharia_reversa/MERCHANDISING.md), `dados/validacao-patrocinios-v2.json` e `dados/validacao-uniformes.json` locais.

## 4. Relatórios de testes como prática

Depois que o usuário perguntou onde estavam os relatórios e pediu que fossem gerados e mantidos como prática, foi registrada em [AGENTS.md](../../AGENTS.md) a orientação de criar relatório em `docs/testes/` para alterações futuras que incluam verificações ou testes. A orientação pede data, objetivo, comandos, resultados reais, ambiente e limitações, distinguindo testes executados dos não realizados e preservando relatórios anteriores.

Os relatórios posteriores registram, entre outros, validações offline, verificações de leitura real, compilações, organização e publicação. Testes que usam dados sintéticos ou mocks não demonstram, por si, funcionamento no save real.

## 5. Homologação solicitada após a CP-01

Após a implementação da CP-01, o usuário solicitou que a homologação da build fosse executada. Foram confrontados o SHA-256 do executável local, a versão, a arquitetura e amostras do módulo em memória, além de registros históricos. O perfil específico `23.2.0+1771058`, x64, foi marcado como homologado para o mecanismo de reconhecimento de build. Uma leitura real posterior produziu `VERIFIED` no BuildGuard e um snapshot do Ceará; o executável compilado passou no autoteste com leitura real.

A homologação identifica o perfil binário conforme as evidências disponíveis. **Ela não prova equivalência de toda a imagem em memória, segurança universal das operações, identidade do save ou persistência após reabrir.** O executável local consultado não possuía assinatura digital, segundo o relatório.

**Evidência:** [relatório de homologação](../testes/2026-11-01-homologacao-build.md).

## 6. Ideias de sincronização e validação de viabilidade

Fora das issues, o usuário propôs usar o processo aberto do FM, um monitor externo e o botão de sincronização para atualizar o contexto. Foi desenvolvido um protótipo diagnóstico com época local de sincronização e comparação de observações. Doze testes sintéticos passaram; três leituras reais próximas no tempo encontraram o mesmo candidato do Ceará, endereço e data.

O teste com dois saves hipotéticos contendo os mesmos valores observáveis mostrou que esses campos não bastam para distingui-los. A pesquisa não executou troca real de save naquele teste. Assim, sincronização e monitoramento são viáveis como mecanismos de observação e invalidação, mas não comprovam por si a identidade da carreira.

**Evidência:** [relatório de viabilidade](../testes/2026-11-01-viabilidade-sincronizacao.md).

## 7. Integração de sincronização e escolha de candidatos

Depois da CP-02.1B parcial, o usuário relatou a mensagem de identidade não verificada e pediu um aplicativo funcional. Foi integrada à interface uma sincronização diagnóstica em segundo plano, usando leitura externa e validação da build. Um monitor passou a repetir observações periodicamente; mudanças observáveis ou falhas invalidam a observação. O monitor não garante perceber toda troca de save entre verificações.

A pedido do usuário, foram adicionados busca, lista e seleção de clubes candidatos. Houve duas correções após os testes de uso:

1. A primeira busca listava clubes estruturalmente válidos demais; foi alterada para procurar a cadeia relacionada à estrutura de treinador.
2. A busca seguinte não mostrava o candidato já indicado pelo cache. O registro anterior passou a aparecer com identificação de procedência e vínculo não confirmado, após revalidação estrutural.

A presença de um clube candidato ou de uma cadeia observada não comprova, isoladamente, que o treinador humano o controla. A busca é limitada em tempo e volume e não é uma lista completa de clubes.

**Evidências:** [integração da sincronização](../testes/2026-11-01-integracao-sincronizacao.md), [seleção de candidatos](../testes/2026-11-01-selecao-candidatos.md), [filtro de vínculos](../testes/2026-11-01-filtro-vinculos-treinador.md) e [correção da lista](../testes/2026-11-01-correcao-lista-candidatos.md).

## 8. Aprovação manual expressamente solicitada

Após selecionar um candidato sem ver as operações serem aplicadas, o usuário esclareceu que a seleção manual deveria aprovar a identidade. Em resposta, foi implementada uma **autorização manual de clube** para a instância atual do FM. A aplicação abre o Ceará escolhido e habilita operações, mantendo verificações da build e da estrutura observada. O suporte operacional permanece específico do Ceará; outros clubes não estão homologados.

Essa decisão posterior substituiu a política conservadora anterior de bloqueio integral para o caso de aprovação manual. Ela **não comprova a identidade do save ou do treinador**. Uma troca de save que mantenha os valores e referências observados pode não ser detectada; há também janela de concorrência. Ao trocar de carreira, a orientação atual é sincronizar e selecionar novamente. As negociações manuais usam arquivo local separado, cuja associação automática a um save específico não foi comprovada.

Foram executados testes offline e uma conexão real em leitura. **Não houve teste real novo de escrita, contratação ou salvar/reabrir nessa etapa.**

**Evidência:** [relatório de aprovação manual](../testes/2026-11-01-aprovacao-manual.md).

## 9. Desempenho, SQLite e carregamento automático

O usuário relatou lentidão na procura e seleção. A busca passou a reutilizar um candidato conhecido da mesma instância após validação, mantendo a opção **Buscar mais** para uma pesquisa ampliada. A seleção deixou de repetir uma identificação completa da build. Em medições pontuais com o FM aberto, a busca passou de **10,301 s para 2,235 s** e a seleção de **3,749 s para 2,281 s**. Não são médias nem garantia de desempenho.

Depois, por solicitação do usuário, foi adicionado um índice SQLite local para candidatos já encontrados, com busca por prefixo de nome ou UID. Os registros são separados por PID, início do processo e hash da build; o endereço e a estrutura são revalidados antes de uso. O índice **não é um catálogo completo de todos os clubes do FM** e não prova identidade de carreira. A consulta real medida por UID levou **1,627 s**, em medição pontual.

Por fim, a sincronização passou a iniciar automaticamente a busca de candidatos e preencher o seletor. O usuário continua selecionando manualmente o clube. Os testes de interface dessa mudança usaram mocks; não substituem uma validação visual abrangente.

**Evidências:** [busca rápida](../testes/2026-11-01-busca-rapida.md), [índice SQLite](../testes/2026-11-01-indice-sqlite-clubes.md) e [carregamento automático de candidatos](../testes/2026-11-01-sincroniza-carrega-candidatos.md).

## 10. Google Drive, backups e redução da pasta

Ao investigar o tamanho do projeto, foram encontrados cerca de **661 MiB em backups de saves**, além de múltiplas compilações antigas, arquivos de build, pesquisa e ferramentas. A integração Google Drive foi conectada a pedido do usuário, e foi criada a pasta privada “FMPresidente — backups e versões”. O endereço privado foi omitido desta cópia para publicação; o relatório original foi preservado localmente.

Foram enviados três backups de save em nove partes, devido ao limite de tamanho por transferência, com manifesto de SHA-256 e script de restauração. Foram enviadas 11 compilações antigas em ZIP e um ZIP de outros arquivos históricos. Inicialmente, foi possível conferir apenas nomes e tamanhos remotos; depois, as **nove partes remotas dos saves foram lidas em fluxo e seus hashes coincidiram com o manifesto**. A abertura dos saves restaurados no jogo e os hashes remotos dos ZIPs de versões não foram verificados.

Ao organizar o projeto, as 11 compilações antigas, o build e os três saves antigos foram movidos para uma área de arquivo em Documentos. Os saves originais foram preservados em `FMPresidente-transferencia-drive-20261101/saves-originais`. A pasta do projeto passou de aproximadamente **1,4 GiB para 181 MiB**. Como os arquivos foram movidos dentro do mesmo disco, isso **não liberou espaço equivalente no disco**. A remoção das cópias temporárias de transferência foi bloqueada por política e elas permaneceram no local. O envio automático de atualizações futuras ao Drive não foi configurado.

**Evidências:** [envio ao Drive](../testes/2026-11-01-backup-google-drive.md) e [organização e conferência posterior](../testes/2026-11-01-organizacao-repositorio.md).

## 11. Preparação e publicação no GitHub

Para preparar um repositório, foi inicializado Git local, criado `.gitignore`, README e `requirements.txt`. Saves, dados de conexão, negociações, SQLite local, executáveis gerados, dependências locais e material bruto de pesquisa foram excluídos do controle de versão. Alguns relatórios locais com caminhos ou links privados também ficaram fora; dois scripts de diagnóstico necessários aos testes foram incluídos.

Após o usuário fornecer o endereço e a imagem, o README foi refeito com o brasão enviado, funcionalidades, compatibilidade, instruções e limites. O projeto foi publicado em [Jhon171819/FMPresident](https://github.com/Jhon171819/FMPresident), branch `main`, commit inicial `2e9a103e8dd089d3f087f351c56f90edc4cf1cc8`. O commit remoto foi conferido por `git ls-remote` e correspondia ao local.

Na preparação da publicação passaram, em modo offline, os testes de índice, sincronização, compatibilidade, identidade, interface isolada e contratos, além dos scripts de empréstimos, patrocínios, datas/transações e uniformes. A varredura de padrões comuns não encontrou caminhos pessoais, links de pasta Drive ou padrões selecionados de credenciais nos arquivos preparados; isso não garante ausência de toda informação sensível. Não houve teste visual do README no GitHub registrado nessa etapa.

**Evidência:** [relatório de publicação](../testes/2026-11-02-publicacao-repositorio.md).

## 12. Situação consolidada e pendências

- **Clube e build:** o fluxo operacional disponível continua voltado ao Ceará e à build específica do FM23 registrada no projeto.
- **Identidade:** o usuário pode aprovar manualmente o clube; a identidade nativa do save e o vínculo do treinador não estão comprovados.
- **Troca de save:** o monitor observa alterações, mas pode não distinguir saves com observações idênticas ou mudanças entre verificações.
- **Empréstimos:** contratação, renegociação e quitação estão implementadas; a validação histórica reversível não comprova o ciclo completo de parcelas e persistência após reabrir.
- **Segurança de memória:** propriedade dos endereços, concorrência, pools e confirmação integral do rollback continuam pendentes de trabalho específico.
- **Índice:** SQLite contém candidatos já encontrados, não toda a base de clubes.
- **Drive:** cópia disponível e partes dos saves verificadas por hash; atualização automática futura não configurada. ZIPs de versões ainda não tiveram hashes remotos conferidos.
- **Armazenamento:** a pasta do projeto ficou menor por movimentação, sem ganho equivalente de espaço no disco; a área de transferência local ainda contém arquivos arquivados e cópias temporárias.
- **Repositório:** versão inicial publicada. Este relatório foi criado localmente após a publicação; não está incluído no commit inicial.

## Índice dos relatórios relacionados

- [Homologação da build](../testes/2026-11-01-homologacao-build.md)
- [Viabilidade da sincronização](../testes/2026-11-01-viabilidade-sincronizacao.md)
- [Integração da sincronização](../testes/2026-11-01-integracao-sincronizacao.md)
- [Seleção de candidatos](../testes/2026-11-01-selecao-candidatos.md)
- [Filtro de vínculos](../testes/2026-11-01-filtro-vinculos-treinador.md)
- [Correção da lista](../testes/2026-11-01-correcao-lista-candidatos.md)
- [Aprovação manual](../testes/2026-11-01-aprovacao-manual.md)
- [Busca rápida](../testes/2026-11-01-busca-rapida.md)
- [Índice SQLite](../testes/2026-11-01-indice-sqlite-clubes.md)
- [Candidatos carregados ao sincronizar](../testes/2026-11-01-sincroniza-carrega-candidatos.md)
- [Backup no Google Drive](../testes/2026-11-01-backup-google-drive.md)
- [Organização e preparo do repositório](../testes/2026-11-01-organizacao-repositorio.md)
- [Publicação no GitHub](../testes/2026-11-02-publicacao-repositorio.md)
