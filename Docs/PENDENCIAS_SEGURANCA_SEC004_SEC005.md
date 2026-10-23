# Pendências futuras de segurança — SEC-004 e SEC-005

Registro iniciado na SEC-006B e atualizado na tarefa específica SEC-004.
A SEC-004 possui implementação própria para revisão; a SEC-005 continua
exclusivamente documental. Os estados de integração e produção não são
inferidos a partir da implementação local.

## NEXO-SEC-004: Restauração de empresas e usuários

**Status: IMPLEMENTADA NA BRANCH SEC-004; validação e publicação registradas no relatório próprio.**

A vulnerabilidade original estava em `blueprints/admin.py`: exclusão reversível
sobrescrevia `Usuario.ativo=False` e restauração sobrescrevia `ativo=True` em
todas as contas vinculadas. Uma conta previamente bloqueada recuperava acesso.
Além disso, a mesma senha permitia que cookies anteriores voltassem a valer
após o ciclo de exclusão/restauração.

A SEC-004 preserva `ativo` como estado administrativo. A empresa na lixeira
bloqueia login, sessões, tokens e Socket.IO pelo estado atual do banco. A exclusão
avança `Usuario.geracao_autorizacao` na mesma transação, revogando cookies,
links de senha e salas anteriores, sem alterar senhas, papéis ou estados
comerciais. A restauração nunca escreve `ativo` nem reduz a geração.

A migração `e4c004a26b01`, após `b7c4e2a9f031`, adiciona a geração persistente.
Para empresas que já estavam na lixeira, fixa todos os CLIENTE como inativos e
geração 1: não existe histórico confiável que autorize reativação automática.
Os bloqueios permanecem após restauração e a interface solicita revisão
administrativa. O procedimento de revisão está no relatório; não existe tela
preexistente de reativação de usuários e nenhum atalho sem autorização foi criado.

A implantação exige janela controlada e migração antes do novo código, sem
tráfego ou escritores antigos durante a transição. Não incluir migração no
build. Esta entrega não aplica migrações no Supabase nem executa deploy.
A informação confiável está em
[`RELATORIO_NEXO_SEC004_RESTAURACAO_SEGURA.md`](RELATORIO_NEXO_SEC004_RESTAURACAO_SEGURA.md),
que distingue implementação, testes, branch, PR, integração e produção.

**Limite histórico:** usuários indevidamente reativados por restaurações
concluídas antes desta correção não podem ser identificados sem evidência
externa. Não foi inventado histórico nem aplicado bloqueio indiscriminado às
empresas ativas; casos suspeitos exigem revisão administrativa própria.

## NEXO-SEC-005: Limites de processamento ETL

**Status: PENDENTE, NÃO IMPLEMENTADA. Não implementar nesta tarefa.**

### Problema identificado

O processamento de planilhas pode consumir recursos excessivos ao carregar
arquivos grandes ou com muitas abas, linhas e colunas. Na base deste registro,
[`etl_processor.py`](../etl_processor.py#L191), função `_ler_bruto`, contém nas
linhas 203–204 a leitura de todas as abas XLSX antes de selecionar a matriz com
mais células preenchidas:

```python
pd.read_excel(
    caminho_arquivo,
    dtype=str,
    header=None,
    engine="openpyxl",
    sheet_name=None,
)
```

Os limites de requisição e de formulários multipart exercitados na SEC-006 não
equivalem a limites de expansão de XLSX, quantidade de células ou recursos do
processamento ETL. A leitura CSV também precisa de orçamento próprio. Nenhum
desses limites de processamento foi implementado nesta etapa documental.

### Objetivo da correção futura

Estabelecer limites adequados de processamento sem comprometer os relatórios
comerciais legítimos, os cálculos de faturamento, os indicadores e a Curva ABC.
Os valores dos limites devem ser definidos com critérios operacionais e testes;
este registro não inventa limites nem altera o processamento atual.

### Itens para futura análise

- Tamanho máximo do arquivo e orçamento para conteúdo descompactado.
- Quantidade máxima de abas, linhas, colunas e células processadas, por aba e no
  conjunto do documento.
- Consumo de memória e tempo máximo de processamento, incluindo tratamento de
  interrupção e limpeza de recursos.
- Arquivos XLSX excessivamente complexos ou malformados e proteção contra
  expansão excessiva de arquivos compactados.
- Limites próprios para CSV, validação de codificações, linhas irregulares e
  campos extensos, sem modificar as regras comerciais de interpretação.
- Tratamento seguro de erros, sem exposição de detalhes internos ou dados de
  clientes e sem persistência parcial de resultados inválidos.
- Preservação dos formatos legítimos suportados, das regras de faturamento,
  dos indicadores e da Curva ABC.

Dependências técnicas a avaliar: estratégias de leitura de pandas/openpyxl,
inspeção segura da estrutura ZIP do XLSX, orçamento de recursos e integração
com os pontos que chamam o ETL. Não é uma autorização para substituir essas
bibliotecas, criar serviços externos ou modificar banco/infraestrutura.

Arquivo principal: `etl_processor.py`. Rotas de upload/processamento e testes
correspondentes deverão ser avaliados somente na futura correção e conforme a
necessidade demonstrada.

### Critérios de aceitação futuros

1. Limites de bytes, expansão, abas, linhas, colunas, células, memória e tempo
   possuem política documentada e comportamento definido ao excedê-los.
2. Arquivos XLSX/CSV legítimos usados nas regressões mantêm os resultados de
   faturamento, indicadores e Curva ABC dentro dos limites aceitos.
3. Entradas malformadas ou acima do orçamento são rejeitadas de forma controlada,
   sem persistência parcial, exposição de dados ou consumo sem limite definido.
4. Os testes incluem limites, valores imediatamente abaixo/acima e expansão de
   conteúdo com amostras sintéticas pequenas; não realizam negação de serviço
   contra sistemas reais nem utilizam arquivos de clientes.
5. A rejeição e a limpeza de recursos são verificadas no fluxo de integração,
   preservando autenticação, CSRF, isolamento entre empresas e as proteções das
   SEC-001, SEC-002, SEC-003 e SEC-006.
6. A solução é validada em ambiente descartável, com evidências de desempenho e
   regressão antes de qualquer proposta de implantação.

**Gravidade preliminar:** média, por risco de indisponibilidade decorrente de
consumo de recursos. A avaliação final depende da capacidade de processamento,
dos controles de acesso e da exposição do fluxo; não houve teste de exploração
ou medição contra o ambiente de produção.

## Registro original da SEC-006B e atualização SEC-004

| Item | Valor |
| --- | --- |
| Data do registro | 23/10/2026, referência de calendário America/Sao_Paulo. |
| Commit de referência desta base | `5eb352403d4df7659602047472ab0afcd9540b28`. |
| Referência conhecida no pedido | `415466ef2c89fb3e1fbae6dec4ce575a6688923e`; a base atual inclui o avanço documental posterior. |
| Tarefa que inclui este registro | NEXO-SEC-006B, segurança das dependências e do processo de instalação. |
| SEC-004 | Implementada na branch exclusiva; testes, publicação e pendências de produção no relatório específico. |
| SEC-005 | PENDENTE, NÃO IMPLEMENTADA; gravidade preliminar média; arquivo principal `etl_processor.py` preservado. |
| Dependências futuras | Política de restauração de acessos, eventual persistência/migração planejada, orçamentos ETL e testes isolados de regressão. |
| Alterações funcionais neste registro | O documento registra a SEC-004 implementada em arquivos próprios. SEC-005 sem implementação. |
| Produção | Nenhum acesso a dados reais, deploy, migração ou alteração de configuração é realizado por este documento. |

Os critérios de aceitação de cada pendência estão registrados acima para
planejamento futuro. Sua execução e qualquer integração ou implantação exigem
uma tarefa posterior com escopo e autorização próprios.

Atualização SEC-004: 23/10/2026 (America/Sao_Paulo), base `2e18c506c90ae2e9fe9f0231912c50d84bd004d8`; sem merge, deploy ou migração de produção pelo assistente.
