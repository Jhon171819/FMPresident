# ER-01 — Arquitetura

Implementação offline, 02/11/2026. er01.py contém armazenamento SQLite transacional, cache, dependências, tarefas, evidências e cache efêmero de leituras. er01_static.py adapta o parser PE/Capstone e os grafos históricos. engenharia_reversa/cli.py expõe as operações sem importar fm23. Não existe acesso automático ao FM23.

Os módulos administrativos, BuildGuard e CareerGuard não foram alterados. A integração progressiva está em tc011b_estatica.py: agora exige --exe e usa o motor incremental por padrão. --legacy-rebuild conserva a rotina antiga explicitamente. No modo incremental, componentes.json fornece a lista histórica de RVAs; sua proveniência permanece legada e cada RVA solicitado é validado contra o PE. O comando class faz RTTI sem desmontar métodos.

Cache não confere autorização de memória. SnapshotReads recebe exclusivamente uma função de leitura já validada pelo chamador, contexto e regiões legíveis; nesta issue foi usado apenas com fixtures.
