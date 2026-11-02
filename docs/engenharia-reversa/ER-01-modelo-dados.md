# Modelo SQLite

Esquema v1: binaries; artifacts (tipo, sujeito, analisador, parâmetros, estado, payload zlib, hash); dependencies (pai/filho); edges (origem, alvo, relação, confiança e proveniência); tasks e task_priority; evidence; runs. Chaves/índices permitem lookup de artefato, classe, função e origem/alvo de arestas. Métodos compartilhados deduplicam por RVA/chave; vínculos classe/slot permanecem no payload da classe.

foreign_keys ativo, WAL e timeout 30 s. Criar o esquema e gravar resultados usa transações; versões desconhecidas são recusadas. quick_check detecta corrupção estrutural e aborta preservando o arquivo. Não houve migração destrutiva implementada: uma futura migração assim exige backup SQLite antes de mudar versão. Nenhum reparo automático ou exclusão de banco corrompido.

Importação atual: 29 registros de proveniência de classes (22 distintas), 58 registros de vtable (45 distintas), 1.655 registros de funções (1.178 RVAs distintos), 189 grafos; quatro grafos bounded. Os contadores do importador contam registros recebidos, não símbolos distintos. Sete evidências preservam estados de observação/parcial/refutação/inconclusivo.
