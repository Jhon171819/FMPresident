# PF-01 — Benchmarks

Valores em ms; fonte: `PF-01-baseline.json` e `PF-01-depois.json`. Primeiro valor é primeira amostra do processo; p95 disponível apenas com 20 amostras. Condições semelhantes, medições sequenciais, sem controle do cache do SO.

| Cenário | n | Mediana antes | Mediana depois | Primeira antes/depois | p95 antes/depois |
|---|---:|---:|---:|---:|---:|
| Treeview 500 linhas inalteradas | 20 | 4,703 | 2,533 | 4,145 / 2,416 | 19,272 / 4,645 |
| 42 journals | 10 | 537,253 | 243,079 | 1399,133 / 357,783 | não calculado |
| Observação real FM | 3 | 1703,599 | 1720,486 | 3608,133 / 2282,130 | não calculado |
| Candidatos indexados reais | 3 | 1816,503 | 1780,550 | 1755,918 / 1829,308 | não calculado |
| Snapshot real | 3 | 103,765 | 112,948 | 92,384 / 92,873 | não calculado |

A mediana da tabela caiu 46,1% neste cenário isolado; a mudança elimina escritas Tk redundantes. A variação dos journals não é atribuída à mudança, pois o leitor não foi alterado; cache e carga podem influenciar. O snapshot não ficou mais rápido: foi retirado da thread gráfica. Outros fluxos estão dentro de variação não demonstrada; não declarar ganhos. P95 usa a 19ª posição ordenada para n=20. Inicialização, primeira pintura, busca fria ampliada e latência fim a fim com seleção humana não foram medidos.
