# CP-02 — matriz de identificadores

| Identificador | Origem | Estabilidade | Comprovação | Limitações |
|---|---|---|---|---|
| PID e criação | API Windows via CP-01 | Instância de processo | Confirmado para processo | Mesmo PID e início podem conter vários saves sucessivos |
| SHA-256 e perfil | Arquivo associado e amostras | Enquanto arquivo e instância forem validados | Build específica verificada | Não identifica save, autoria, todas as páginas ou treinador |
| UID do clube | `club+12`, build conhecida | Observado em sessões | Candidato estrutural | Um clube pode existir em diversas carreiras; outros clubes não homologados |
| Nome do clube | `club+184` e bytes da string | Pode mudar / ser repetido | Nome observado | Não identifica jogador, save ou controle humano |
| Endereço do clube | Vtable e memória | Pode mudar e ser reutilizado | Ponteiro observado numa sessão | Cache legado não é UID nem identidade de carreira |
| Data interna | `base+DATE_RVA` | Muda com tempo | Data decodificada no contexto observado | Vários saves podem ter mesma data; carregamento pode ser instável |
| `CLUB_HUMAN_MANAGER_DETAILS +0x40 -> TEAM +0x30 -> CLUB` | RTTI e captura histórica somente leitura | Desconhecida | Cadeia observada uma vez | Não prova treinador humano ativo, unicidade ou save atual |
| Identidade do treinador e vínculo | Desconhecido | Desconhecida | Não comprovada | Sem distinção confiável de IA, desemprego ou múltiplos humanos |
| ID do save/carreira | Desconhecido | Desconhecida | Não comprovada | UID, data, PID e endereço não suprem essa ausência |
| JSON local | Armazenamento do app | Não vinculado à carreira | Formato existente | Associação automática está bloqueada; arquivos preservados |
