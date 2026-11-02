# AU-02 — Contratos de dados

## Escopo e arquitetura

`contratos_dados.py` é uma camada **independente** de `fm23`, Windows, jogo, GUI e arquivos reais. Utiliza `dataclasses`, `Enum`, `typing`, `datetime` e `json` da biblioteca padrão. Adaptadores recebem dicionários legados e devolvem modelos; não modificam as entradas. Os consumidores atuais continuam usando seus dicionários. Nenhum adaptador foi inserido no caminho operacional: `Memory.read`, `Memory.write`, `FM.transaction`, endereços, suspensão, rollback, motor de crédito e interface permanecem como antes.

```text
FM.snapshot/process_info ──> financial_from_legacy/process_from_legacy
receita nativa ────────────> sponsor_from_memory
marca ou mesa local ───────> sponsor_from_local/sponsor_proposal_from_legacy
dívida ou oferta ──────────> loan_from_memory/loan_offer_from_legacy
journal ───────────────────> operation_from_journal
                              ↓
 dataclasses + Evidence(value, source, validation, note)
```

Esta camada organiza dados e identifica incertezas; não valida endereços, propriedade de objetos ou segurança de memória. Uma data, UID e PID não identificam um save.

## Inventário e origem

Veja [matriz de fontes](AU-02-matriz-fontes.md) e [AU-01](../auditoria/AU-01-matriz-operacoes.md). `FM.snapshot` (`fm23.py:279-295`) reúne campos lidos em momentos potencialmente diferentes. `process_info` (`fm23.py:153-160`) fornece PID, string de ticks de início, caminho, versão, base e tamanho; versão/tamanho não são fingerprint. `negociacao.begin` (`negociacao.py:91-108`) produz mesa com ID, versão, empresa, receita, oferta, status, histórico, prazos e locks; `signing` (`:200-214`) produz contrato local e `total = annual * years`. Os tipos nativos `sponsor_rows` e `debt_rows` são descritos em `fm23.py:253-277`. `emprestimos.offer` (`emprestimos.py:132-153`) calcula oferta; `outstanding` (`:120-129`) é uma estimativa em ramos amortizados. `transaction` (`fm23.py:302-335`) cria journal com processo, clube, dados antes/depois e metadados.

`uniformes.active_sponsors` (`uniformes.py:123-148`) associa registros locais e receitas por atributos, sujeito a unicidade; não transforma essa associação em ID nativo comprovado. `dados/presidencia.json`, `negociacoes.json`, `conexao.json` e `historico/*.json` têm consumidores e estruturas próprios (`FMPresidente.pyw:22-23,194-216,308-318`; `patrocinios_ui.py:14-15,26-40,251-284`; `fm23.py:169-178,309-312`). O envelope AU-02 preserva o objeto original completo, incluindo campos que não são parte do modelo. Os adaptadores abrangem estruturas documentadas; não existe leitor/migrador universal de todos esses arquivos.

## Modelos e unidades

| Modelo | Significado e validação |
|---|---|
| `ProcessIdentity` | PID inteiro positivo; `started` string original; versão, tamanho e caminho opcionais; SHA-256 `Evidence` opcional e validação da build separada. `process_from_legacy` não afirma que a versão/tamanho identificam o binário. |
| `CareerIdentity`, `ClubIdentity` | Clube identificado, data de carreira ISO convertida a `date`, processo e origem; ID de carreira e clube controlado como `Evidence` desconhecido por padrão. UID 104749 não prova controle humano. |
| `FinancialSnapshot` | Caixa, orçamento de transferências, verba de temporada em GBP inteiros; folha e gasto em GBP/semana; preços de ingresso e carnê em GBP `float` finito; infraestrutura 0–20; receitas/obrigações tipadas; público e modo de uniforme. Caixa e orçamento não são somados. |
| `Sponsor` | Tipo, datas e total em GBP; marca/ID, anual em GBP/ano e duração em anos opcionais; cláusulas locais e estado separados da origem; `fm_match=UNKNOWN` enquanto não houver prova. Na proposta negociada, anual e anos aparecem juntos e total é o produto. A receita lida da memória não inventa anual ou duração. |
| `Loan` | Principal, parcela mensal, componente monetário de juros e condicional em GBP; datas, código e flag de pagamento só de juros; taxa anual percentual, saldo e prazo opcionais. Taxa e saldo não são deduzidos do registro nativo; saldo estimado deve usar `Source.CALCULATED`. `loan_offer_from_legacy` valida prazo 6–120, taxa 0–100%, principal £1.000–£100 milhões e parcela positiva, sem recalcular o motor. |
| `OperationRequest/Validation/Result` | Solicitação, validação com erros/avisos/checagens pendentes e resultado com estado/journal/recuperação opcional. Modelar não executa; estado `APPLIED` de journal não comprova UI atualizada ou save persistido. |

Fontes `FM_MEMORY`, `LOCAL_STORAGE`, `CALCULATED`, `FALLBACK`, `UNKNOWN` são independentes de `Verification` (`VERIFIED`, `UNVERIFIED`, `UNKNOWN`). `Evidence` aceita valor conhecido com origem desconhecida. O parâmetro nacional do snapshot legado tem origem **UNKNOWN** porque `fm23.credit_terms` já substituiu valor inválido por 3,5 antes de entregar o dicionário; não é possível recuperar a origem observando somente o valor, mesmo quando igual a 3,5. Sua semântica também é `UNVERIFIED`. Campo ausente no snapshot fica desconhecido; `credit_from_offer_context` representa separadamente os fallbacks 13,75 e 5000 aplicados pela oferta. Não confundir o componente monetário mensal de juros com taxa anual percentual.

## Exemplos

```python
from contratos_dados import financial_from_legacy, model_to_json, model_from_json

# `snapshot` e `process` são dicionários já obtidos por um chamador existente.
finance = financial_from_legacy(snapshot, process)
assert finance.career.career_id.value is None
assert finance.career.controlled_club.value is None
payload = model_to_json(finance)
assert model_from_json(payload) == finance
```

Para propostas, `sponsor_proposal_from_legacy(mesa)` preserva o status e representa como fonte local; `loan_offer_from_legacy(oferta)` representa operação `PROPOSED`. `validate_exclusivity` rejeita duas marcas distintas do mesmo setor em vigência sobreposta quando pelo menos uma exige exclusividade; se marca/setor for desconhecido, não afirma que há nem que não há conflito. A verificação completa das regras do motor existente continua em `negociacao.py`.

## Validação e compatibilidade

Validadores recusam booleanos como inteiros, ausências obrigatórias, tipos incorretos, datas ISO inválidas ou invertidas, números não finitos e faixas documentadas. O adaptador de snapshot é propositalmente mais estrito em alguns dados que `FM.snapshot`: por exemplo, rejeita preços negativos/não finitos, e datas de dívida invertidas. Isso é uma rejeição explícita de entrada, não mudança do aplicativo. Contratos locais sem `annual` e `years` permanecem representáveis; se apenas um estiver presente, a conversão recusa a ambiguidade. Exclusividade não é presumida quando ausente.

`serialize_legacy(kind, dicionario)` cria JSON determinístico com `schema_version=1`, `kind` e `legacy`; valida antes de codificar e preserva cópia profunda de campos extras. `deserialize_legacy` devolve `(modelo, copia_legada)`; versões e tipos não suportados são rejeitados. `model_to_json` e `model_from_json` codificam modelos, enums, datas, tuplas e mapas num envelope tipado fechado v1; JSON não finito é recusado. Não leem, migram ou sobrescrevem arquivos. O formato novo é separado dos JSON antigos; futuras migrações precisam de versão explícita, backup, adaptadores por versão e testes de ida e volta antes de qualquer gravação.

O inventário inclui processo, snapshot, receitas, patrocínios locais, mesas/propostas, dívidas, ofertas e journal. No caso de conexão (`pid`, `started`, `club` como endereço) e estado presidencial, a preservação integral por um adaptador específico ainda precisa ser implementada; não converter `club` do cache em UID. O adapter de journal preserva desconhecidos no envelope, mas interpreta apenas ID, status e erro. Resultados `FAILED` não comprovam rollback; `recovery_needed=None` explicita incerteza.

## Integração futura

- **CP-01:** usar `ProcessIdentity`, `Evidence` de SHA-256 e `build_validation`; associar fingerprint ao módulo efetivamente carregado com evidência, sem usar versão/tamanho como prova criptográfica.
- **CP-02:** preencher carreira e clube controlado somente quando houver fonte e comprovação; testar troca de save e clube.
- **SG-01/SG-02:** validar `OperationRequest` e produzir `OperationValidation`/`OperationResult`, sem interpretar `APPLIED` como persistência; integrar journal e recuperação em issue própria.
- **EC-01/EV-01:** consumir valores e origens explícitos, preservando distinção entre semanal/anual/total e inferências.

## Verificação e limitações

`py -B -m unittest -v testar_contratos_dados` executa fixtures sintéticas, sem import de `fm23`, handles ou dados reais. Nenhum teste desta issue confirma comportamento de gravação/persistência no jogo. A camada é aditiva e não é importada pelo aplicativo ou compilada no executável instalado nesta etapa. Compatibilidade foi testada para os formatos sintéticos abrangidos, não para todo arquivo histórico existente. `frozen=True` impede reatribuição dos campos, mas mapas internos continuam mutáveis; chamadores devem tratá-los como dados de leitura ou copiar. Identificadores, semântica de campos de memória e demais builds permanecem pendentes.
