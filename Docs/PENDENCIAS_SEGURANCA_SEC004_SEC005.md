# Pendências futuras de segurança — SEC-004 e SEC-005

Registro iniciado na SEC-006B e atualizado na tarefa específica SEC-004.
A SEC-004 foi integrada externamente no GitHub; sua migração de produção
permanece não confirmada. A SEC-005 agora possui implementação e validação
próprias em branch exclusiva. Integração e produção não são inferidas dos testes.

## NEXO-SEC-004: Restauração de empresas e usuários

**Status: INTEGRADA NO GITHUB pela PR #17, main `ff148796d9b579418b3782d472eb44fb0025fe6f`; migração em produção NÃO CONFIRMADA.**

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

**Status: IMPLEMENTADA E VALIDADA LOCALMENTE na branch `security/sec-005-etl-resource-limits`; publicação/PR/CI a confirmar na entrega final. Produção não verificada.**

O leitor anterior carregava todas as abas XLSX simultaneamente e materializava
texto CSV e listas de candidatos sem orçamento completo. Uploads e recuperação
de BYTEA também precisavam de limites, e a falha transacional podia atingir
um upload substituído após soltar a trava da análise.

A implementação possui limites finitos de bytes, ZIP/expansão, abas, linhas,
colunas, células, campos e registros; leitura incremental e escolha equivalente
da aba/separador. Validação e cálculo executam em processo filho com prazo,
limite AS/CPU e protocolo JSON limitado, sem banco ou credenciais no filho.
Há admissão compartilhada por processo para upload/processamento, recuperação
limitada em cópia temporária própria, lock da análise respeitado pelos uploads
e SAVEPOINT para manter indicadores e Curva ABC anteriores na rejeição.

A equivalência financeira utiliza referência anterior preservada e fixtures
somente sintéticas, incluindo C1/C2/C3/C4, 22 pares e 47 matrizes cruas.
Resultados completos, medições de recursos, contagens atuais, limitações e
publicação estão em
[`RELATORIO_NEXO_SEC005_ETL_SEGURO.md`](RELATORIO_NEXO_SEC005_ETL_SEGURO.md).
O relatório versionado é um snapshot pré-publicação; evidências posteriores
serão consolidadas na descrição da PR e no relatório final externo.

Nenhuma fórmula, regra comercial, dependência, modelo ou migração foi alterada.
A SEC-005 não foi implantada nem modifica o Supabase real. Limites do filho não
constituem limite global RSS do Render; a homologação real permanece pendente.
Integridade do cache comum para outros consumidores pertence à SEC-007 e não
foi corrigida como uma refatoração geral nesta tarefa.

## Registro original da SEC-006B e atualização SEC-004

| Item | Valor |
| --- | --- |
| Data do registro | 23/10/2026, referência de calendário America/Sao_Paulo. |
| Commit de referência desta base | `5eb352403d4df7659602047472ab0afcd9540b28`. |
| Referência conhecida no pedido | `415466ef2c89fb3e1fbae6dec4ce575a6688923e`; a base atual inclui o avanço documental posterior. |
| Tarefa que inclui este registro | NEXO-SEC-006B, segurança das dependências e do processo de instalação. |
| SEC-004 | Integrada externamente pela PR #17; migração de produção não confirmada. |
| SEC-005 | Implementada e validada localmente em branch exclusiva; publicação/CI e produção distinguidas no relatório. |
| Dependências futuras | Política de restauração de acessos, eventual persistência/migração planejada, orçamentos ETL e testes isolados de regressão. |
| Alterações funcionais neste registro | Documento apenas registra as implementações em arquivos próprios. |
| Produção | Nenhum acesso a dados reais, deploy, migração ou alteração de configuração é realizado por este documento. |

Os critérios de aceitação de cada pendência estão registrados acima para
planejamento futuro. Sua execução e qualquer integração ou implantação exigem
uma tarefa posterior com escopo e autorização próprios.

Atualização SEC-004: 23/10/2026 (America/Sao_Paulo), base `2e18c506c90ae2e9fe9f0231912c50d84bd004d8`; sem merge, deploy ou migração de produção pelo assistente.

Atualização SEC-005: 24/10/2026 (America/Sao_Paulo), base `ff148796d9b579418b3782d472eb44fb0025fe6f`. Sem merge, deploy, acesso ao Supabase ou aplicação de migração de produção pelo assistente.
