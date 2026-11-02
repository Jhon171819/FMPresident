# Índices e grafos

import lê JSONs legados de até 32 MiB por arquivo, registra source_hash e nome de origem. Todos entram como LEGACY_UNVERIFIED; bounded continua no payload. A identidade do binário fornecido não constitui validação retroativa do algoritmo antigo. Arquivos JSON desconhecidos/incompatíveis não são convertidos.

class NAME --exe FILE extrai RTTI e métodos, cacheado por binário/nome/implementação/limites. Perfil inicial usa a seção que contém RVA 0x4fdcdf8, específico desta build; até 512 métodos por vtable. Não é indexador universal de todos os PE. Resultado negativo de classe é estático e específico do fingerprint. Capstone não é chamado na extração de RTTI; análise de métodos é separada.

analyze deduplica RVAs e registra chamadas diretas em edges. Chamadas virtuais não resolvidas permanecem no grafo, sem alvo inventado. walk permite ciclos, limites de nós/arestas/profundidade/tempo e retorno de fronteira; checkpoint retornado pode ser passado à API para continuar. Relações REFUTED não são percorridas. Se um nó exceder orçamento de arestas, permanece na fronteira para uma solicitação com orçamento maior. Arestas não são fatos semânticos por serem estáticas. Consultas públicas: index, graph e cache-explain; consultas por dependências de artefato via serviço Store.
