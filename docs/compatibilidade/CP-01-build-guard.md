> **Atualização em 2026-11-01:** o perfil exato `fm23-23.2.0-1771058` foi homologado explicitamente com base na identidade verificada, testes de leitura atuais e registros históricos. As referências abaixo ao perfil pendente refletem o estado anterior e foram preservadas como histórico. Isso não comprova persistência, propriedade de endereços nem segurança de todas as operações. Consulte [o relatório de homologação](../testes/2026-11-01-homologacao-build.md).

# CP-01 — identificação e proteção da build

Data: 2026-11-01. Estado: implementação parcial; homologação operacional pendente.

## Fluxo

`process_info` exige uma instância; `ProcessProbe` usa o mesmo handle do processo para PID, horário de criação, caminho, base e tamanho do módulo. O guard calcula SHA-256 do arquivo associado e confere arquitetura PE, metadados do arquivo aberto antes/depois, identidade e três amostras da imagem. O resultado integra `ProcessIdentity` e `Evidence` da AU-02. É criada uma autorização por instância; `Memory.read`, `regions`, `paused` e `write` exigem essa autorização, e a transação, contratação e quitação refazem hash e amostras. Alteração detectada invalida a autorização até nova conexão. Não há interface de bypass.

O registro contém um perfil candidato explícito, não homologado. O executável local apresentou versão 23.2.0+1771058, imagem 356016128 bytes, arquitetura x64 e SHA-256 `d0c9fb1a66248ee6ae2febf086dbc50b3ad4100ee7ee8d6ec0ee31015ff6b8c1`, igual ao hash em `emprestimos.py` e ao mapa de pesquisa. Uma verificação nesta sessão encontrou o processo e confirmou as três amostras documentadas em `engenharia_reversa/mapa/sessao-leitura.json`. Isso é observação somente de leitura, não homologação de todas as operações ou persistência.

Estados: VERIFIED exige perfil homologado e todas as verificações; UNSUPPORTED indica ausência de correspondência; UNVERIFIED representa evidência incompleta ou perfil pendente; ERROR representa falha técnica; DISCONNECTED é o estado inicial. A interface apresenta motivo, versão e perfil ao bloquear; o diagnóstico estruturado não inclui caminho pessoal.

## Limitações

Comparar hash em disco e três amostras de código não prova equivalência integral de imagem, nem garante que o arquivo corrente seja aquele originalmente mapeado em todas as páginas. Metadados e amostras não eliminam todas as corridas ou modificações com metadados restaurados entre verificações. Revalidação completa ocorre antes da transação, e a rápida antes de cada escrita; existe janela entre verificação e chamada do Windows. A checagem não identifica carreira, controla propriedade de endereços nem garante rollback; se a identidade mudar durante rollback, o guard pode bloquear a restauração. Esses riscos pertencem também a CP-02 e SG-01.

A leitura de amostras conhecidas ocorre apenas após a correspondência do hash e metadados do perfil candidato e antes de qualquer leitura de estruturas da carreira. Não há hash ingênuo da imagem inteira, sujeita a relocations e alterações legítimas. `club` no cache continua sendo ponteiro, nunca UID; o guard antecede a utilização do cache e este segue limitado ao PID e início.

## Roteiro para homologação futura

1. Em ambiente controlado, confirmar procedência da instalação, processo e assinatura do arquivo; reproduzir fingerprint e amostras, registrando versão e máquina sem divulgar caminho pessoal.
2. Validar os layouts e caminhos específicos com cópia de save, incluindo leituras, cenários de mudança de instância, falhas, concorrência, retomada e verificação de rollback.
3. Sob procedimento controlado e autorização adequada, testar operações em cópia, conferir interface do FM, salvar e reabrir; registrar evidências e limitações. Não usar a carreira principal.
4. Revisar os resultados para cada perfil, atualizar evidências e só então mudar explicitamente o estado de homologação. Adicionar um hash isolado nunca homologa automaticamente.

CP-02 deve identificar carreira e clube controlado; SG-01 precisa tratar propriedade de endereços, ciclo dos pools, estado parcial e restauração.
