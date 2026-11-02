# Homologação do perfil de build FM23 23.2.0+1771058

Data: 2026-11-01. Ambiente: Windows 11 x64, Python 3.14, PyInstaller 6.22.3, FM23 aberto. Objetivo: homologar explicitamente o perfil específico com base nas evidências disponíveis, exercitar o guard e a conexão real sem realizar novas escritas no jogo.

## Decisão e evidências

Perfil `fm23-23.2.0-1771058`, x64, imagem 356016128 bytes, SHA-256 `d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1`: marcado explicitamente como homologado no registro. Não é homologação genérica de todas as instalações com a mesma versão.

- O arquivo da instalação atual corresponde ao SHA-256 registrado em `engenharia_reversa/mapa/executavel.json` em 27/10 e ao hash usado por `_build` em `emprestimos.py`.
- Na sessão atual, o guard verificou a instância por PID e momento de criação, arquivo associado, hash, arquitetura, base/tamanho do módulo e três amostras de código; resultado `VERIFIED`. Esse teste não demonstra equivalência integral da imagem carregada.
- `dados/validacao-emprestimos.json` registra testes históricos de criação de contrato, crédito/lista, renegociação e quitação, com restauração reportada. O PID e o instante de criação nesse registro coincidem com a instância atual, cujo hash foi conferido nesta execução. O registro é uma evidência histórica, não um novo teste de escrita.
- `dados/validacao-integracao.json` registra testes históricos reversíveis de aporte, orçamentos, preços, treinamento, patrocínio e quitação em outra instância; não contém hash, portanto não vincula criptograficamente aquela instância à build atual. Os registros de patrocínio e uniformes são evidências históricas adicionais, igualmente com escopo limitado.
- `Get-AuthenticodeSignature` retornou `NotSigned` para o executável atual. O hash identifica os bytes locais, mas não comprova autoria ou procedência oficial.

## Testes desta execução

| Comando / verificação | Resultado real |
|---|---|
| `python testar_compatibilidade.py` | 23 testes aprovados, incluindo recusa de perfil não homologado e contextos alterados. Os cenários positivos de unidade são sintéticos. |
| `python testar_contratos_dados.py` | 26 testes aprovados. |
| `python testar_patrocinios.py`, `python verificar.py`, `python testar_emprestimos.py` | Três scripts offline aprovados. |
| `PYTHONPATH=ferramentas/build-tools; python testar_uniformes.py` | Script offline aprovado. |
| Verificação `BuildGuard` e `snapshot` em processo real | `VERIFIED`; snapshot de leitura retornou UID 104749, 12 patrocínios e 0 empréstimos. A chamada de escrita foi substituída por falha no teste em Python, para detectar tentativa inesperada; nenhuma escrita foi chamada. |
| `python construir.py` | Compilação aprovada. |
| `bin-cp01-homologado/FMPresidente.exe --self-check --live-read` | Saída 0, autotestes offline aprovados e snapshot real de leitura do Ceará. |
| Atalhos de Documentos e área de trabalho | Atualizados para `bin-cp01-homologado/FMPresidente.exe`. |

## Limites

Nesta execução não houve escrita de memória no FM, teste real de contratação ou rollback, modificação de save nem ciclo salvar/reabrir. Os scripts offline e evidências históricas não provam esses comportamentos para todas as condições, nem a propriedade dos endereços ou identidade da carreira. Aprovar a identidade da build com base nessas evidências não resolve os riscos R01–R05 ou os demais riscos da AU-01; exige ainda validação controlada de persistência, troca de carreira, concorrência e falhas. O snapshot representa apenas a carreira e os campos lidos naquele instante. Resta cobertura automatizada independente por entrada de escrita e estado. A interface completa não foi testada visualmente nesta execução.

A homologação é uma decisão explícita baseada nas evidências disponíveis e não equivale a garantir que todas as operações sejam seguras; builds diferentes continuam bloqueadas. A instância antiga do FMPresidente, se aberta, precisa ser fechada para iniciar o novo executável pelo atalho.
