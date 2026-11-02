# CP-01 — matriz de operações

A inspeção estática encontrou uma única chamada `WriteProcessMemory`, em `Memory.write`. Todos os caminhos abaixo são protegidos por esse limite, por `Memory.read` e pela revalidação completa em `FM.transaction`; a assinatura e quitação também revalidam antes da suspensão especial. A proteção é adicional às validações anteriores.

| Operação / entrada | Método / caminho | Proteção |
|---|---|---|
| Aporte | `FM.capital` → `transaction` | Guard em leituras, transação e escrita |
| Orçamentos | `FM.budgets` → `transaction` | Idem |
| Preços | `FM.prices` → `transaction` | Idem |
| Infraestrutura | `FM.invest` → `transaction` | Idem |
| Assinatura, substituição, rescisão de patrocínio | `update_sponsor` / `terminate_sponsor` → `transaction` | Idem |
| Uniforme, flag de memória | `set_licensed_kits` → `transaction` | Idem |
| Contratação e renegociação de empréstimo; pools e listas | `emprestimos.sign` → `transaction` | Revalidação antes da pausa e central |
| Quitação | `emprestimos.repay` → `transaction` | Revalidação antes da pausa e central |
| Desfazer | `FM.undo` → `transaction` | Idem |
| Rollback | `transaction` → `Memory.write` | Requer guard válido, sem garantia de restauração |
| Arquivos de uniformes e XML | `uniformes.py` | Sistema de arquivos, não é escrita de memória; guard não substitui proteções próprias |
| JSON, journal e backup de save | `save_json`, `backup_save` | Armazenamento local; fora da proteção de memória |

A prova automatizada cobre explicitamente o limite de escrita, transação, assinatura e quitação com espiões; a associação dos demais caminhos à transação foi verificada por inspeção, não por testes independentes de cada entrada em todos os estados. Isso continua pendente.
