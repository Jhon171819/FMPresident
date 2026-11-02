# CP-01 — relatório de testes

Data: 2026-11-01. Ambiente: Windows 11 x64, Python 3.14, PyInstaller 6.22.3; execução local no diretório FMPresidente. Objetivo: verificar identificação conservadora, bloqueio e regressões offline, sem alterar o FM ou saves.

## Resultados executados

| Comando | Resultado |
|---|---|
| `python testar_compatibilidade.py` | 23 testes aprovados, 0 falhas na execução final. Perfis e processo positivos são sintéticos; falhas incluem hash, perfil, processo, PID, reinício, arquivo, amostras, metadados, acesso, serialização e bloqueio. |
| `python testar_contratos_dados.py` | 26 testes aprovados, 0 falhas. |
| `python testar_patrocinios.py` | Aprovado: script offline reportou 50 marcas e 172 rodadas, entre outras verificações; não é contagem de testes unitários. |
| `python testar_uniformes.py` | Primeira execução falhou por ausência de Pillow no Python global; repetida com `PYTHONPATH=ferramentas/build-tools`, aprovada. |
| `python verificar.py` | Script offline aprovado: datas, transação simulada, rollback e dados desatualizados. Não foi usado `--live`. |
| `python testar_emprestimos.py` | Script offline aprovado: proposta, operações simuladas, quitação e rollback. Não foi usado `--live`. |
| `python construir.py` | Build PyInstaller concluída. |
| `bin-cp01/FMPresidente.exe --self-check` | Saída 0; autoteste do executável aprovado para os quatro scripts integrados, em modo simulado. |
| Identificação atual, somente leitura | A API de processo, SHA-256 do arquivo e três amostras do módulo coincidiram com o perfil candidato. Resultado proposital: UNVERIFIED, pois perfil não está homologado. |

Durante desenvolvimento, a primeira execução da suíte do guard apresentou falhas intermitentes na comparação de `ctime` entre `fstat` e `stat` do Windows. Foi ajustada a comparação para dispositivo, identificador do arquivo, tamanho e modificação; a execução final acima passou. Tais metadados não constituem prova criptográfica de identidade entre verificações.

## Cobertura e limites

Espiões confirmaram que chamadas bloqueadas em `Memory.write`, `FM.transaction`, contratação e quitação não chamaram escrita simulada. Leituras e suspensão sem guard foram bloqueadas. A matriz de operações demonstra por inspeção o roteamento das demais funções até a proteção central. Não foram executados testes independentes completos de cada entrada de escrita com build homologada, desconhecida, PID alterado e falha de validação. Os testes de operação existentes usam guard simulado apenas em fixtures offline; não constituem homologação real.

O FM estava aberto durante a verificação de identificação, porém não foi executada transação real, alteração de memória, teste `--live`, save/reload ou teste com outro clube. Não houve teste visual completo da interface nem comprovação de imagem carregada integral. As três amostras não provam o restante da imagem. Não houve comparação por diff Git: o diretório não é repositório Git. O perfil de produção permanece não homologado e o aplicativo atualizado bloqueia as operações dependentes da build.

Os atalhos foram direcionados à nova compilação em `bin-cp01`; a instância antiga, se ainda aberta, continua executando o binário anterior até ser fechada. O autoteste anterior foi preservado em `dados/autoteste-executavel-antes-cp01.json` quando existente.
