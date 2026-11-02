# Leituras simuladas

SnapshotReads mantém bytes somente na instância da observação. Valida contexto antes/depois da fonte, região e tamanho, bytes, chamadas, falhas e tempo; regiões declaradas são limitadas a 256. Não possui write. batch agrupa pedidos contíguos/sobrepostos apenas na mesma região e preserva ordem/duplicados da resposta. Pedidos separados por lacuna não são agrupados. Leituras contidas reutilizam bytes, reduzindo chamadas. follow limita profundidade/objetos e rejeita ciclos.

fresh=True faz revalidação real e compara interseções com bytes anteriores; divergência fecha/invalida a observação. Contexto inválido limpa o cache. A fonte e as regiões devem vir de um Reader e identidade/época aprovados pelo chamador: não se presume atomicidade nem continuidade de proteção. close encerra apenas o cache; o dono do Reader fecha o handle. Nenhuma persistência de ponteiros ou resultado negativo dinâmico. Nenhum teste no processo real nesta issue.

Atualização: ensaio adicional solicitado pelo usuário utilizou Reader real com handle somente leitura e âncora de código da build. Agrupamento, respostas, fresh e rejeição controlada de época passaram. Não envolve dados de carreira mutáveis. Métricas e escopo: `docs/testes/ER-01-validacao-adicional.md`.
