# Controle nativo da aparência dos uniformes

Validado em 28/10/2026, FM23 23.2.0+1771058, Ceará ID 104749.

O editor expõe **Allow Licensed Kits**. Na equipe principal (`db::TEAM`,
vtable RVA `0x5002398`), o bit `0x08` no byte `+0x2e` impede o uso de
uniformes licenciados quando está ligado.

Na comparação controlada pelo editor, os bytes do clube e das instalações
não mudaram. O byte da equipe mudou de `5` para `13` ao desabilitar imagens,
e voltou a `5` ao habilitá-las. A inspeção estática encontrou testes desse bit,
incluindo o RVA `0x3d06d57`: `test byte ptr [rcx + 0x2e], 8`.

O backend resolve a primeira equipe da coleção em `CLUB +0x18`, confere
limites, vtable e o ponteiro de retorno `TEAM +0x30 → CLUB`. Altera somente
esse bit, preservando os demais. A escrita usa o journal e as verificações
de sessão/data/CAS existentes. Se o modo já está escolhido, não escreve.

O teste real desabilitou o modo e o restaurou pelo histórico. O byte original
e o snapshot da carreira foram iguais ao final. Os testes isolados também
conferem que os outros bits são preservados e a operação repetida não escreve.

Esse controle seleciona a fonte visual. Não incorpora o patrocinador à imagem
procedural produzida pelo editor. O estilo do editor fica guardado; o modo
patrocinado usa os PNGs 2D/3D do aplicativo. A recarga de uma textura já usada
por uma partida e a sobreposição sobre o novo estilo do editor continuam
fora do que foi validado nesta mudança.
