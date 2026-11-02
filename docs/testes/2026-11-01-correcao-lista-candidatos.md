# Correção da lista de candidatos — testes

Data local: 01/11/2026. Windows 11 x64, Python 3.14, FM23 aberto. A sincronização exibia um candidato do cache, mas a busca por vínculo não retornava esse registro. Agora a busca inclui o candidato do cache apenas quando PID/início coincidem e a estrutura é revalidada; o item informa que o vínculo não foi confirmado. Vínculos observados pela cadeia recebem etiqueta própria. Registros iguais são deduplicados; evidência de cadeia prevalece sobre cache.

- `python -m py_compile sincronizacao_hibrida.py FMPresidente.pyw`: aprovado.
- `python testar_sincronizacao_hibrida.py`: 12 testes aprovados, incluindo inclusão de candidato, deduplicação e precedência da proveniência.
- Busca real somente leitura `search_candidates(256*1024*1024,5)`: encontrou Ceará UID 104749 com origem cache; busca limitada. `observe` revalidou o candidato.
- `python construir.py`: compilação aprovada; `bin-candidatos-corrigido/FMPresidente.exe --self-check`: saída 0, ok=true. Os dois atalhos foram atualizados.

Não foi feito teste visual completo nem confirmado vínculo ao treinador. Os dados do cache não são identidade de carreira e a seleção não libera escrita; nenhum save ou memória do jogo foi alterado. A busca pode retornar poucos candidatos por limite de tempo e volume. O processo antigo do aplicativo permanece em execução até ser fechado. Autoteste anterior preservado.
