# PF-01 — Profiling

Windows 11, Python 3.14, FM23 23.2.0+1771058 aberto com Ceará. Com `PYTHONPATH=ferramentas/build-tools;ferramentas`, executar `python medir_pf01.py --live --output <arquivo.json>`. O script usa `perf_counter`, Tk real oculto com 500 linhas, histórico local e leituras reais do FM. A primeira amostra é registrada separadamente, mas não corresponde a cache do sistema operacional necessariamente frio. Baseline foi produzido antes das mudanças críticas; depois, repetiu-se o mesmo procedimento.

Gargalos medidos: observação real mediana 1703,599 ms (3 amostras); candidatos indexados 1816,503 ms (3); snapshot 103,765 ms (3), anteriormente na thread Tk; 42 journals mediana 537,253 ms (10, sujeita a disco); atualização redundante de 500 linhas 4,703 ms (20). Processamento visual usa worker para memória após a mudança. A validação da build inclui fingerprint, e não foi enfraquecida para reduzir tempos.

Fases internas de hash, leituras individuais, CPU, memória, contagem de consultas, criação de janela, primeira pintura, troca de abas, abertura de modais e medições por operação administrativa não foram instrumentadas. Os tempos reais totais não substituem profiling detalhado, e 3 amostras não permitem inferência estatística robusta. Não houve escrita real no FM.
