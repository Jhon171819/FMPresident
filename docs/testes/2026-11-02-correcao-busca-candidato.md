# Correção da busca de candidatos — 02/11/2026

O FM estava aberto e a build foi identificada; a busca de candidatos percorria apenas o primeiro GiB e não encontrou uma cadeia de detalhes nesta sessão, apresentando lista vazia. Foi acrescentada busca limitada pelo registro do único clube atualmente suportado (Ceará), com validação estrutural existente e seleção manual preservada. Isso identifica candidato, não treinador nem save. O limite de busca passou a 2 GiB/30 s em blocos de 4 MiB; não garante encontrar candidato em todos os jogos.

Ambiente: Windows 11, Python 3.14, FM 23.2.0+1771058 aberto. Busca real somente leitura: Ceará Sporting Club, ID 104749; 16,0 s; candidato indexado. Nenhuma escrita no processo do jogo nem no save.

Testes: `python testar_sincronizacao_hibrida.py` (13 aprovados), `python testar_sincronizacao_interface.py` (4 aprovados), `python testar_indice_clubes.py` (7 aprovados). A consulta real valida a localização, mas não comprova identidade da carreira nem testes de operações administrativas reais. A primeira busca pode continuar lenta, e os resultados são revalidados na seleção.

Compilação com `python construir.py` concluída; autoteste do executável aprovado. Atalho da área de trabalho atualizado para `bin-sg011-sincronizacao`. A seleção manual na interface não foi executada neste diagnóstico.

Verificação adicional na interface: o FM foi reconhecido, o Ceará apareceu na lista, foi selecionado e conectado manualmente. A tela exibiu data 26/05/2032, caixa e orçamentos, com botões administrativos habilitados. Nenhuma operação financeira ou escrita no FM foi realizada. O aplicativo aberto já está conectado; a identidade persistente do save continua não comprovada.
