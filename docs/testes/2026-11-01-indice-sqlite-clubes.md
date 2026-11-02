# Índice SQLite de clubes — relatório de testes

Data local: 01/11/2026. Windows 11 x64, Python 3.14, FM23 aberto. Objetivo: indexar candidatos observados usando SQLite para localizar por prefixo do nome ou UID, preservando validação antes de usar os dados.

O arquivo descartável `dados/indice-clubes.sqlite3` contém índices B-tree por contexto (PID, início do processo e hash do executável), nome normalizado e UID. Indexa apenas registros candidatos efetivamente encontrados pelo aplicativo, não todos os clubes do banco do jogo. O campo de pesquisa aceita prefixo sem diferenciar acentos e caixa ou UID exato. A busca rápida consulta o índice; Buscar mais também varre a região limitada e acrescenta candidatos encontrados. Antes de usar qualquer endereço indexado, o aplicativo confirma build e revalida vtable, UID, nome e estrutura do clube. Uma entrada local não comprova identidade da carreira, controle humano ou validade após troca de save. A aprovação manual continua como implementada anteriormente.

- `python testar_indice_clubes.py`: 7 testes aprovados; consulta por prefixo e UID, isolamento por processo/build, parâmetros SQL, número grande e substituição.
- `python testar_sincronizacao_hibrida.py`: 12 testes aprovados.
- `python testar_compatibilidade.py`: 23 testes aprovados.
- `python testar_identidade.py`: 15 testes aprovados.
- `python -m py_compile indice_clubes.py sincronizacao_hibrida.py FMPresidente.pyw`: aprovado.
- Busca real por `ceara`: candidato UID 104749 retornado em 1,878 s; busca seguinte por UID consultando SQLite: 1,627 s. Medições pontuais, sem controle de cache do sistema; o hash do executável continua sendo calculado e domina o tempo. Não representam garantia de desempenho.
- Em diretório temporário, registro indexado com endereço real mas UID divergente foi rejeitado pela busca antes de seleção; teste somente leitura do FM.
- `python construir.py` aprovado. `bin-sqlite/FMPresidente.exe --self-check`: saída 0, ok=true; atalhos atualizados.

Nenhuma escrita em memória, transação, alteração de save, teste real de troca de save, busca ampliada completa, teste visual abrangente da interface ou medição repetida foi executada. O índice possui informações técnicas do processo local; não compartilhe o arquivo sem avaliação. SQLite é da biblioteca padrão; nenhum dado histórico foi migrado ou apagado. A instância anterior do aplicativo, se aberta, deve ser fechada para iniciar a nova versão. O autoteste anterior foi preservado.
