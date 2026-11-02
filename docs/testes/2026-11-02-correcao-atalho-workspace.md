# Correção do atalho do workspace

Data: 02/11/2026. Objetivo: corrigir o atalho `Abrir FMPresidente.lnk` que ainda iniciava a interface Tkinter antiga.

## Verificação

O destino anterior era:

`C:\Users\User\Documents\FMPresidente\bin-sg01-revisado\FMPresidente.exe`

O destino atualizado é:

`C:\Users\User\Documents\FMPresidente\bin-ux011\FMPresidenteQt.exe`

Também foram atualizados o diretório de trabalho e o ícone para a build Qt. A build existe e o destino foi relido pelo `WScript.Shell` após salvar o `.lnk`.

Após a verificação do usuário, o atalho da área de trabalho (`Desktop\FMPresidente.lnk`) também foi alinhado para a mesma build Qt, evitando que o usuário abrisse acidentalmente a versão Tkinter antiga.
