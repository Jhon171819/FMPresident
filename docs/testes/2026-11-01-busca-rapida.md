# Busca e seleção rápidas — relatório de testes

Data local 01/11/2026. Ambiente: Windows 11 x64, Python 3.14 e FM23 aberto. Objetivo: reduzir latência da busca e seleção sem escrever no FM.

A busca normal usa o registro de conexão já indexado apenas se PID e início corresponderem e a estrutura for revalidada; a build ainda é identificada pelo hash. Se não houver candidato válido, a busca limitada existente continua disponível automaticamente. O botão Buscar mais executa busca ampliada mesmo havendo cache. A seleção reutiliza o snapshot e a validação da conexão manual em vez de executar duas identificações completas de build consecutivas. Antes de gravar continuam as revalidações da transação e do guard. Cache não prova identidade do save nem treinador.

Medição real pontual com FM aberto: busca anterior 10,301 s, busca rápida 2,235 s; seleção anterior 3,749 s, nova 2,281 s. Testes em momentos diferentes, sem controle de cache de disco e concorrência, não são benchmark estatístico. A busca rápida retornou o candidato UID 104749 e o snapshot manual foi lido sem escrita. Não foi executada transação real, seleção visual ou alteração de save.

`python -m py_compile sincronizacao_hibrida.py FMPresidente.pyw`: aprovado; `python testar_sincronizacao_hibrida.py`: 12 aprovados; `python testar_compatibilidade.py`: 23 aprovados; `python testar_identidade.py`: 15 aprovados. `python construir.py` aprovado; `bin-busca-rapida/FMPresidente.exe --self-check` saída 0 e ok=true. Atalhos atualizados. Teste visual completo, busca ampliada após a alteração e benchmarks repetidos não foram executados. O autoteste anterior foi preservado.

A busca rápida pode retornar somente o candidato indexado; outras opções exigem Buscar mais. O índice não é migrado nem tratado como identidade permanente. Alterações no processo, arquivo ou clube ainda são verificadas; mesmo assim, a aprovação manual não prova que o save permaneceu o mesmo e há limitações de concorrência.
