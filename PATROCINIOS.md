# Patrocínios no FMPresidente

Abra o **FMPresidente** pelo atalho da área de trabalho, com a carreira do FM23
carregada. Em **Patrocínios**, use as três páginas:

1. **Mercado de marcas:** escolha uma receita comercial do clube, uma empresa
   e a data inicial. Clique em **Abordar empresa**.
2. **Mesa de negociação:** consulte a proposta, altere sua contraproposta e
   envie. Marcar **Fixo** torna aquele termo não negociável. A empresa pode
   aceitar, contrapropor, apresentar a última oferta ou desistir.
3. **Contratos no FM:** confira os valores reais, a vigência, as cláusulas
   registradas no app e o custo de eventual rescisão.

## Empresas e critérios

Foram importadas as **50 marcas do ZIP fornecido**, incluindo nome, setor,
reputação, poder de investimento e cartões PNG. Samsung foi preservada do
cadastro anterior, resultando em 51 empresas no catálogo atual.

Os perfis são parâmetros de jogo. A reputação e o investimento da marca,
a receita anterior desse espaço, a duração preferida e as cláusulas influenciam
o orçamento da empresa. Os perfis e as ofertas não representam propostas reais
dessas empresas. O aplicativo funciona offline.

Cada mesa mantém seu histórico. Há limite de paciência, prazo de resposta e
duas semanas de afastamento depois de uma desistência. A mesma empresa não
recebe um novo perfil ao reabrir a janela na mesma quinzena da carreira.
O prazo também respeita a data inicial: uma oferta para começar hoje precisa
ser concluída no mesmo dia do jogo. Para negociar ao longo de dias, escolha
uma data inicial futura.

## O que é aplicado ao FM

Na assinatura, o app mostra o resumo e confere novamente o contrato e a data
da carreira. O valor **anual × anos** é registrado como o valor **total** do
contrato nativo, com a vigência acordada, valor fixo e renovação automática
desligada. Os recebimentos regulares ficam a cargo do calendário do FM;
assinar não deposita de uma vez todo o dinheiro do contrato.

Em espaços individuais, como master e patrocínio secundário, receitas do
mesmo tipo com vigências sobrepostas são substituídas na mesma transação,
para não acumular dois pagamentos pelo mesmo espaço. O resumo informa
quantas receitas serão substituídas. Patrocínios gerais permitem várias
receitas e não recebem esse tratamento.

Esta versão utiliza receitas comerciais que já existem na carreira. A criação
de novos registros no alocador do jogo ainda não foi validada. Não é necessário
copiar números para o editor. Salve a carreira normalmente no FM para tornar
as mudanças permanentes.

## Cláusulas do aplicativo

As cláusulas abaixo pertencem ao motor próprio do FMPresidente:

- **Exclusividade de setor:** impede contratos sobrepostos com concorrentes
  do mesmo setor/família, quando um deles exige exclusividade.
- **Preferência para renovação:** no fim do contrato, o parceiro tem uma janela
  de preferência até sete dias depois do vencimento. Nos últimos trinta dias,
  negocie primeiro com ele; uma recusa ou expiração libera a preferência.
  Também é possível programar o novo início depois da janela.
- **Multa rescisória:** percentual do valor garantido ainda restante, calculado
  pelos dias de vigência. Ao rescindir, o app encerra a receita no FM e debita
  a multa do caixa na mesma operação. Esse débito é um ajuste de caixa do
  aplicativo; ainda não foi associado a uma categoria contábil de despesas
  do motor nativo.

Para trocar uma empresa que já possui contrato negociado nesta versão,
rescinda primeiro. Uma renegociação com a própria empresa pode substituir
o contrato por acordo mútuo. As cláusulas e as marcas são persistidas no app;
o save do FM guarda a receita financeira e a vigência.

## Uniformes

O master e o patrocinador secundário cadastrados são aplicados automaticamente
nos arquivos de uniformes 2D e 3D quando entram em vigência. A rescisão ou o
fim de vigência também atualiza os gráficos administrados pelo app.

As imagens do ZIP são cartões tipográficos, com legendas, e não logotipos
oficiais. São exibidas no mercado. Nas camisas, o gerador usa somente o nome
da empresa, sem inserir a legenda do cartão. O escudo do Ceará foi preservado.

Gráficos que o FM já mantém em cache aparecem atualizados ao recarregar a
skin ou reiniciar o jogo. Outros tipos de receita, como patrocínio geral ou
sócio-torcedor, não ganham uma posição de camisa por serem negociados.

Correção de 28/10/2026: o vínculo gráfico tolera a mudança da data inicial
do contrato pelo calendário do FM quando valor, fim e espaço identificam
uma única receita e uma única marca. O cadastro legado Samsung também é
reconhecido quando foi movido para outro uniforme. Esse reconhecimento
não modifica contratos ou dinheiro no jogo. A data inicial negociada continua
limitando quando a marca pode aparecer.

O aplicativo confere os sete arquivos instalados e os reinstala se faltarem
ou forem alterados. **Aplicar patrocinadores**, no topo da janela, reinstala
os gráficos e habilita diretamente **Allow Licensed Kits** no FM. A mesma
ação está em **Patrocínios → Uniformes**, junto de **Usar estilo do editor**.
Esse segundo botão volta à aparência dinâmica para editar cores e desenho.
Os dois modos preservam os dados de estilo da carreira; porém o modo patrocinado
usa as imagens do aplicativo, sem sobrepor marcas ao novo desenho do editor.
A atualização automática dos arquivos não altera o modo escolhido manualmente.
Reabra a página do clube ou recarregue a skin; com cache ativo, desative **Use caching
to decrease page loading times** nas preferências de interface antes de
recarregar. A textura de uma partida que já começou pode continuar carregada
até a próxima partida.

O modo é uma flag de um byte da equipe principal, validada pelo tipo `db::TEAM`
e pelo vínculo com o clube conectado. As mudanças registram histórico e podem
ser desfeitas como as outras decisões. O controle foi validado comparando o
liga/desliga do editor e testando aplicação/restauração pelo backend, sem
alterar os demais bits ou os dados financeiros. Salve a carreira normalmente
para manter a escolha após fechar o FM.

## Integração e recuperação

O motor de negociação foi criado no FMPresidente, inspirado no fluxo de
ofertas e contrapropostas de contratos. Ele não executa a engine de transferências
de jogadores com objetos de empresa, nem introduz menus novos dentro do FM.
O executável `fm.exe` permaneceu inalterado: a integração escreve nos dados
do contrato real, usando os campos já validados para esta versão.

Cada transação registra os bytes anteriores, os novos valores e os termos
acordados antes da aplicação, com conferência e restauração em caso de falha.
O histórico permite desfazer na mesma sessão/data se os campos continuarem
iguais. Os termos também podem ser recuperados do journal após uma falha
na persistência do painel, conferindo sua correspondência com os dados do FM.

Foram preservados um backup do aplicativo anterior e uma cópia do último
save local antes dos testes. Os testes de valor, vigência, substituição de
master e multa foram feitos no processo e restaurados. O relatório fica em
`dados/validacao-patrocinios-v2.json`. Eles não substituem uma verificação de
todos os ciclos futuros de recebimento e de todas as cláusulas durante anos
de calendário do FM.
