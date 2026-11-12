# Infraestrutura de Avaliação de Cenário e retenção

A integração incorpora os modelos `LeadAvaliacao` e `BrainstormingDadosPdv`, a revisão Alembic `f4c2a8e1d9b6` e o comando `flask leads expurgar-pdv` presentes na referência. A referência não fornece um fluxo público completo de captação/processamento de leads. Não foi criada uma rota pública, seção na landing, tarefa agendada ou envio real de email.

## Estruturas e permissões

A revisão depende da cadeia `b6935e8de9d4 -> c7d41e9a2b60 -> e2f7a94c1d35 -> a8d3f6b91c24 -> b3e9d6c1f7a2 -> f4c2a8e1d9b6`. Ela cria duas tabelas e uma função de expurgo no PostgreSQL, sem modificar contratos, contas ou análises antigas. Os UUIDs têm geração no ORM e no banco. Restrições verificam status, nomes, email básico, valores, ano e integridade referencial.

RLS está habilitado. Quando os papéis da Data API existem, os privilégios de `anon` e `authenticated` são revogados e uma política restritiva nega acesso mesmo após um GRANT futuro. A função é `SECURITY INVOKER`, fixa `search_path` e revoga `EXECUTE` de `PUBLIC`, `anon` e `authenticated`. A aplicação deve usar o papel de servidor apropriado; nenhum cliente recebe chave privilegiada.

## Retenção e operação

`flask leads expurgar-pdv` simula e reverte a transação. `--aplicar` confirma a exclusão de linhas de PDV vencidas de leads não convertidos. O padrão é 30 dias; `--dias` aceita um inteiro positivo. Leads convertidos são preservados. O lead que fica sem qualquer linha recente é marcado expirado. Contatos e resumos permanecem na tabela de leads: isto não representa exclusão completa de dados pessoais.

Nenhum agendador está configurado. Antes de captar dados reais, o proprietário precisa definir fluxo/consentimento, política de retenção de contatos e resumos, autorização de uso, tratamento de solicitações dos titulares e operação do expurgo. Qualquer migração ou expurgo em produção depende de backup verificável e autorização explícita. Não executar os comandos de aplicação como parte de testes.

## Verificação isolada

Os testes `tests.test_leads_avaliacao` usam SQLite com dados sintéticos. `tests.test_leads_postgresql` cria seu próprio cluster temporário, com ambiente filtrado, quando `NEXO_TEST_POSTGRES_BIN` aponta para binários PostgreSQL locais. Esse teste cobre UUIDs, constraints, RLS, função, concorrência, simulação, CASCADE e proteção do downgrade, sem utilizar o Supabase original.

As avaliações voluntárias de clientes/prova social são outro módulo. Seus arquivos na referência dependem de modelos e de uma revisão inexistentes; ficaram fora desta integração para não introduzir rotas quebradas.
