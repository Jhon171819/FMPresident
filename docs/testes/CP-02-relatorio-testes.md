# CP-02 — relatório de testes

Data: 2026-11-01. Ambiente: Windows 11 x64, Python 3.14, PyInstaller 6.22.3; FM23 aberto. Objetivo: exercitar o bloqueio de identidade, preservar o Build Guard e testar regressões sem alterar o jogo ou saves.

| Comando / verificação | Resultado |
|---|---|
| `python testar_identidade.py` | 12 testes aprovados: candidato sintético de outro clube, múltiplos candidatos, nenhum candidato, finanças inválidas, ponteiro desatualizado, identidade desconhecida, mesmo clube/data, mudança de build, bloqueio de transação/empréstimo e ausência de FM simulada. Não identifica treinador real nem prova suporte a outros clubes. |
| `python testar_compatibilidade.py` | 23 testes aprovados, incluindo rejeição de build desconhecida e mudança de contexto da CP-01. |
| `python testar_contratos_dados.py` | 26 testes aprovados. |
| `python testar_patrocinios.py` | Script offline aprovado. |
| `PYTHONPATH=ferramentas/build-tools; python testar_uniformes.py` | Script offline aprovado. |
| `python verificar.py` | Script offline aprovado, com guard de identidade simulado para preservar o teste financeiro de transação. |
| `python testar_emprestimos.py` | Script offline aprovado, com guard de identidade simulado; sem `--live`. |
| `python engenharia_reversa/gestao/verificar_investigacao.py <executável>` | Aprovado: hash, classes RTTI, instruções e consistência das capturas históricas. Não demonstra vínculo humano ativo. |
| Inspeção real somente leitura | CP-01 `VERIFIED`; candidato do cache inspecionado como estrutura e não como autorização: UID 104749, Ceará Sporting Club. Carreira `UNVERIFIED`; treinador e identificador de save `UNKNOWN`; autorização rejeitada. |
| Duas tentativas reais de conexão com diretório de dados temporário | Ambas rejeitadas por identidade; espião na API de escrita não registrou chamadas; nenhum arquivo de cache criado no diretório temporário. |
| `python construir.py` e `bin-cp02/FMPresidente.exe --self-check` | Compilação concluída; autoteste do executável, somente offline, saída 0. |
| Atalhos | Alvos da área de trabalho e de Documentos conferidos como `bin-cp02/FMPresidente.exe`. |

Os testes atuais não incluem avanço de data, troca de save ou clube, carregamento, treinador desempregado, IA, múltiplos humanos, vínculo verdadeiro de treinador, suporte multiclubes, teste visual completo da interface nem escrita real. A detecção desses cenários ainda não é possível com a evidência existente: todos permanecem bloqueados, e não foram representados como comprovados. Não foi executado `--live`, não foram modificadas estruturas do FM nem saves; testes antigos de transação usam memória sintética. O cache real foi lido apenas para diagnóstico estrutural, não para autorização ou seleção.

A identificação dinâmica não foi comparada com uma lista completa de clubes e pode omitir objetos; os testes de múltiplos candidatos são sintéticos. Histórico e mesas legadas foram ocultados da associação à carreira atual, preservando os arquivos, mas não houve teste visual abrangente ou comparação de todos os arquivos históricos. Não há teste separado para cada entrada de escrita e cenário; a proteção central e caminhos especiais foram testados com espiões.

A instância antiga do FMPresidente estava aberta ao final: ela usa o binário anterior e não recebe o novo guard até ser fechada. O autoteste anterior foi preservado em `dados/autoteste-executavel-antes-cp02.json`.
