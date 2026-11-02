# UX-01 — Benchmarks

Ver UX-01-medicoes.json: 20 trocas de página Qt offscreen, widgets reais, snapshot sintético. Mediana/p95/min/max registrados no JSON. Não comparar esse cenário com os benchmarks Tk de leitura real de FM: a equivalência funcional ainda não existe.

Não foram medidas de forma comparável inicialização fria Tk/Qt, primeira pintura nativa, CPU, memória ou latência durante sincronização. Qt não é declarado mais rápido pelo simples uso do framework. As páginas são persistentes; Rows evita reset se o número de linhas é igual e atualiza apenas dados. Não há leitura de memória ou escrita de arquivos no callback de renderização financeira. O backend continua com a descoberta nativa e os dois hashes completos.

Medição atual da troca de páginas: mediana 11,32 ms; p95 27,61 ms; mínimo 7,16 ms; máximo 36,28 ms, n=20 (Qt offscreen). Variações dependem do ambiente; não há baseline Tk equivalente nem inferência de ganho.
