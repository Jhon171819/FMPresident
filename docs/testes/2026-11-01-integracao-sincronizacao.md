# Integração da sincronização — relatório de testes

Data: 01/11/2026. Windows 11 x64, Python 3.14, FM23 aberto. Objetivo: integrar observação somente de leitura à interface mantendo o bloqueio de escrita por identidade desconhecida.

Resultados: `python -m py_compile sincronizacao_hibrida.py FMPresidente.pyw` aprovado; `python testar_sincronizacao_hibrida.py` 10 aprovados; `python testar_identidade.py` 12 aprovados; `python testar_compatibilidade.py` 23 aprovados. `sync.observe()` no processo real confirmou o perfil fm23-23.2.0-1771058 e observou candidato UID 104749, data 2032-05-02 e carreira UNKNOWN. O handle utilizado possui direitos 0x410 de consulta/leitura, e é fechado ao terminar. Nenhuma transação ou alteração de memória foi executada.

`python construir.py` terminou com sucesso; `bin-sincronizacao/FMPresidente.exe --self-check` retornou 0 e ok=true. Atalhos da área de trabalho e da pasta do aplicativo apontam para bin-sincronizacao. A instância anterior continuou aberta e precisa ser fechada antes de abrir a nova.

Sincronização ocorre em thread do fluxo existente; o polling agenda observação quando não ocupado, com intervalo mínimo de 20 segundos, e valida novamente a build, incluindo hash do executável. Isto pode gerar uso de disco e não foi medido em operação prolongada. Comparação de dados iguais não comprova identidade ou continuidade; alteração da data também invalida de forma conservadora. O cache legado serve apenas para localizar candidato, nunca para autorização. CareerGuard permanece bloqueado.

Não foram executados testes visuais completos da interface, troca real de save A/B/A, teste de encerramento durante hash em andamento, monitoramento prolongado ou testes reais de empréstimo, escrita, save/reload e identidade do treinador. O usuário não pode realizar operações administrativas até que se demonstre uma identidade de contexto segura. A integração diagnóstica não conclui a CP-02.1B nem resolve o objetivo operacional solicitado.
