# Cache e invalidação

Chave SHA-256 de [SHA-256 integral do binário, tipo, objeto/RVA, hash da implementação, parâmetros]. O analisador de grafos considera fonte de graph, parser PE e versão Capstone. Cada grafo novo retém hash dos bytes de entrada. O hash do PE carregado é confrontado com a identidade calculada antes da análise. Consultas quentes ainda fazem fingerprint integral streaming, sem parser nem desmontagem.

Estados: COMPLETE, PARTIAL, INTERRUPTED, INVALID, LEGACY_UNVERIFIED; ausência é retorno nulo. PARTIAL preserva bounded e limites: repetir os mesmos limites reutiliza o mesmo parcial; aprofundar exige outros parâmetros. COMPLETE de uma tarefa significa que os pedidos foram atendidos nos limites declarados, não que cada grafo foi exaurido.

Conteúdo JSON comprimido no SQLite tem hash validado ao recuperar. Corrupção do payload invalida somente a entrada. BEGIN IMMEDIATE coordena cálculo/publicação: dois solicitantes não calculam simultaneamente a mesma chave. A transação serializa escritores do banco; processos distintos foram simulados por conexões concorrentes em threads. Falhas durante cálculo fazem rollback.

invalidate retorna por padrão simulação e segue dependências registradas. --apply efetiva. clean remove somente INVALID com --apply; originais/legados não são apagados. Mudança de parâmetro cria nova chave, preservando resultados independentes. Não há reciclagem silenciosa de cache dinâmico persistente.
