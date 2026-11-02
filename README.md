<div align="center">
  <img src="assets/fmpresidente-logo.png" alt="Brasão do FMPresidente" width="300">

# FMPresidente

**Assuma a presidência e acompanhe as decisões do seu clube no Football Manager 2023.**

Aplicativo desktop para Windows com gestão financeira, patrocínios, infraestrutura e empréstimos.
</div>

## O que você pode fazer

- Acompanhar caixa, orçamentos, folha salarial e data da carreira.
- Administrar aportes, orçamentos, ingressos e investimentos em infraestrutura.
- Negociar patrocínios e gerenciar a aparência dos uniformes.
- Simular condições, contratar, renegociar e quitar empréstimos financeiros.
- Consultar o histórico das decisões e desfazer operações compatíveis com a sessão atual.

## Compatibilidade e funcionamento

O projeto foi desenvolvido para **Windows**, Football Manager 2023 **23.2.0+1771058** e o **Ceará**. O aplicativo procura uma build específica e verifica sua compatibilidade antes de acessar os dados do jogo. Outros clubes e versões ainda não foram homologados.

A seleção manual aprova o clube escolhido para a sessão, mas não comprova a identidade do save. Ao trocar de carreira, sincronize e selecione o clube novamente. Algumas alterações são aplicadas diretamente à memória do jogo: mantenha um backup da carreira antes de usá-las.

## Como começar

1. Abra o Football Manager 2023 e carregue sua carreira.
2. Abra o FMPresidente e clique em **Sincronizar com FM23**.
3. Selecione o candidato correspondente ao clube e clique em **Selecionar candidato**.
4. Use as abas para acompanhar os dados e tomar decisões.

Consulte [EMPRESTIMOS.txt](EMPRESTIMOS.txt) e [PATROCINIOS.md](PATROCINIOS.md) para mais detalhes sobre essas funcionalidades.

## Desenvolvimento

Requer Windows e Python. Instale as dependências com:

```powershell
python -m pip install -r requirements.txt
```

Para executar o aplicativo a partir do código:

```powershell
python FMPresidente.pyw
```

Para compilar a distribuição local:

```powershell
python construir.py
```

A compilação é criada em `build/distrib`; instalá-la é uma etapa separada. Para executar os testes offline, rode os scripts `testar_*.py`. As opções `--live` de scripts de teste podem modificar a memória do jogo e devem ser usadas somente em ambiente controlado.

## Dados locais

Saves, backups, dados de conexão, negociações, executáveis compilados, dependências locais e resultados brutos de investigação não são incluídos no repositório. Alguns relatórios históricos permanecem apenas localmente enquanto aguardam revisão de privacidade.
