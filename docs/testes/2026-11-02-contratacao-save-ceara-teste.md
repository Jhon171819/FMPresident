# Homologação — contratação de empréstimo no save `ceará teste fmpresidente`

Data: 02/11/2026

Ambiente: Windows 11 x64, FM23 `23.2.0+1771058`, processo `fm.exe` PID 12620, Python 3.14, PyInstaller 6.22.3.

## Escopo

Teste restrito ao arquivo:

`C:\Users\User\Documents\Sports Interactive\Football Manager 2023\games\ceará teste fmpresidente.fm`

Nenhum save anterior foi aberto ou escrito. Antes do ensaio foi criada a cópia:

`ceará teste fmpresidente.fmpresidente-test-backup-20261102.fm`

Os dois arquivos tinham 231.875.141 bytes e SHA-256 `21C7728C6E3FAA063BA2A54FEB876EFC7D865E0F17209A8CC62EADD01D6D88C2`.

## Confirmação do contexto

O diálogo nativo “Save Game” do FM exibiu o nome `ceará teste fmpresidente`, com data 02/11/2026 07:26. A observação somente leitura encontrou build `23.2.0+1771058`, data da carreira `2032-06-17` e o candidato Ceará UID 104749 no endereço `0x2e754b60`.

## Ensaios executados

- Auditoria somente leitura de `_contract_block` e `_vector_block`: aprovada; reserva de contrato `0x381c77c8` e reserva de lista `0xa1570c90` disponíveis.
- Ensaio real controlado, com a guarda de alocação habilitada somente para este processo: contratação de £1.000 em 12 meses, taxa anual de 13,75%, parcela £89, total £1.068.
- Resultado em memória: caixa £119.033 → £120.033; uma dívida nativa foi criada, com início `2032-07-01` e fim `2033-06-01`.
- SHA-256 do arquivo em disco antes/depois do ensaio: inalterado. Portanto, o teste não persistiu automaticamente no arquivo.
- Regressões aprovadas: `testar_emprestimos.py`, `testar_ux012.py`, `testar_ux011.py`, `testar_ux01.py` (além de `py_compile`).
- Build `bin-ux013/FMPresidenteQt/FMPresidenteQt.exe`: `--self-check` e `--sync-self-check` aprovados; sincronização encontrou 1 candidato.
- Teste Qt real com sessão aprovada: botão “Contratar novo empréstimo” habilitado e status “Reserva nativa conferida para esta sessão.”

## Alterações implementadas

`emprestimos.py` deixou de usar um bloqueio permanente e passou a auditar dinamicamente as reservas nativas antes de cada contratação. `aplicacao_qt.py` expõe a oferta de novo crédito. `FMPresidenteQt.py` agora oferece valor, prazo, taxa, confirmação e chamada para a transação journalizada.

Os atalhos do Documentos e da Área de Trabalho apontam para `bin-ux013/FMPresidenteQt/FMPresidenteQt.exe`.

## Limitação atual

O controle nativo foi interrompido pela tecla Escape antes de clicar em “Save Game”. Assim, a dívida está comprovadamente aplicada na memória da instância do FM, mas ainda não foi confirmada após salvar/reabrir o arquivo. Para persistir o ensaio, use o próprio FM e salve manualmente o save `ceará teste fmpresidente`; o backup permanece disponível para restauração.
