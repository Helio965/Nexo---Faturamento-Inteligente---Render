# NEXO-SEC-004 — restauração segura de empresas e usuários

Data: 23/10/2026 (America/Sao_Paulo). Registro técnico pré-publicação da
implementação validada localmente. Os resultados posteriores de GitHub/CI
serão consolidados no relatório final de entrega e na descrição da PR.
Nenhum teste utiliza clientes, Supabase, banco existente ou credenciais reais.

## A. Identificação

| Item | Valor |
| --- | --- |
| Projeto | NEXO: Faturamento Inteligente |
| Repositório | Helio965/Nexo---Faturamento-Inteligente---Render |
| Branch exclusiva | `security/sec-004-safe-company-restore` |
| Base remota verificada | `2e18c506c90ae2e9fe9f0231912c50d84bd004d8` |
| Python local | 3.12.14, virtualenv de validação isolada |
| PostgreSQL local | 17.11, clusters privados via socket Unix, sem TCP |
| Escopo | SEC-004; preservação das SEC-001/002/003/006/006B |
| Produção | Não acessada nem modificada por esta tarefa |

O checkout estava limpo antes da implementação, na branch SEC-006B. A `main`
remota foi conferida por fetch e API; a branch SEC-004 foi criada dessa base.
Não havia PR ou implementação SEC-004 nessa base. As dependências, instalador
verificado, código PDF, ETL, NexoBot, vídeo e identidade visual foram preservados.

## B. Diagnóstico

O cadastro administrativo cria uma empresa e seu CLIENTE inicial ativo, com
primeiro acesso pendente, senha aleatória e link de ativação. ADMIN global
não possui empresa: a constraint de papel/vínculo continua obrigatória.

A exclusão reversível antiga gravava `Empresa.deletado_em` e sobrescrevia
`Usuario.ativo=False` em todos os vinculados. A restauração removia a data e
sobrescrevia `ativo=True`, perdendo a distinção entre bloqueio administrativo
anterior e bloqueio da lixeira. Não existia snapshot confiável para registros
antigos. O estado comercial ATIVA/SUSPENSA/CANCELADA é outro eixo e não foi
transformado em nova regra de autenticação.

A impressão criptográfica de sessão/token dependia do ID e da senha. Uma
exclusão/restauração sem troca de senha permitia reutilizar cookies e links
antigos. Os endpoints também não serializavam exclusão, restauração, edição e
exclusão permanente da mesma empresa. Capturavam apenas parte das falhas SQL.

## C. Solução

Foi escolhida a alternativa A: `Usuario.ativo` mantém exclusivamente a decisão
administrativa e a empresa na lixeira bloqueia autorização. A restauração não
precisa reconstituir nem sobrescrever estados individuais.

O helper `usuario_pode_acessar` consulta o estado atual da empresa no banco,
sem confiar no relacionamento ORM possivelmente carregado antes. É utilizado
por sessões HTTP, login, emissão/leitura/consumo de tokens, Socket.IO e entrega
de notificações. CLIENTE sem empresa existente é recusado; ADMIN precisa ter
vínculo nulo. Primeiro acesso mantém seus controles anteriores.

A geração persistente por usuário complementa a credencial criptográfica. Ela
avança em cada exclusão efetiva e jamais retrocede durante restauração. Não
há redefinição de senha, papel ou permissão para revogar acesso.

Snapshot (alternativa B) exigiria resolver histórico ausente e alterações
administrativas posteriores, com risco de sobrescrevê-las. Um estado desejado
já existe em `ativo`; preservá-lo elimina essa ambiguidade. Mecanismos apenas
em memória ou sem geração persistente não impediriam a reutilização dos cookies
após restauração/reinício, por isso foram descartados.

## D. Modelo de dados

Único campo novo: `usuario.geracao_autorizacao`, INTEGER NOT NULL, default
Python/servidor 0 e CHECK `geracao_autorizacao >= 0`, nomeado
`ck_usuario_geracao_autorizacao`.
Sem nova tabela, snapshot auxiliar, serviço externo ou registro órfão.

Revisão Alembic `e4c004a26b01`, sucessora do head `b7c4e2a9f031`. A coluna é
adicionada com CHECK inline, sem reconstrução de `usuario`. PKs, FKs, uniques,
checks, dados comerciais e relacionamentos preexistentes são preservados.

No upgrade, todos os CLIENTE vinculados a empresas já na lixeira ficam
`ativo=False`, geração 1, inclusive inconsistências anteriormente ativas.
Demais usuários mantêm `ativo`, papel, senha e empresa, com geração 0. Nenhuma
data ou flag atual foi usada para inventar seu estado anterior à lixeira.

A atualização real a partir do esquema anterior foi testada com a cadeia
Alembic e dados sintéticos, incluindo histórico dependente, nos dois bancos.
A migração não foi aplicada ao Supabase nem adicionada ao build do Render.

## E. Exclusão reversível

`company_security.excluir_empresa` não confirma a transação: o endpoint é
responsável por commit/rollback. Adquire primeiro `Empresa FOR UPDATE`, lê
novamente o estado, depois bloqueia todos os CLIENTE da empresa em ordem de
PK com `FOR UPDATE`. Marca a exclusão e avança todas as gerações na mesma
transação. `ativo`, senha, primeiro acesso, papel, vínculo e status comercial
permanecem intactos. Exclusão repetida não avança outra geração.

O lock da empresa também serializa inserções que precisam validar sua FK.
Edição cadastral POST, restauração e exclusão permanente utilizam a mesma
trava inicial. Falhas SQLAlchemy durante leitura, alteração ou confirmação
revertem a operação e produzem mensagens genéricas, sem SQL/credenciais.

Após commit, conexões locais da impressão anterior são desconectadas em
melhor esforço. Uma falha de transporte não desfaz o negócio confirmado nem
concede autorização: geração, banco e salas protegem também outros processos.

## F. Restauração

`restaurar_empresa` adquire os mesmos locks e remove apenas o bloqueio da
empresa. Nunca escreve `Usuario.ativo` nem reduz sua geração. Usuários antes
ativos podem fazer novo login; previamente bloqueados continuam bloqueados.
Uma desativação administrativa posterior durante a lixeira não é sobrescrita.
Repetições ou ciclos sucessivos não concedem permissões adicionais.

O administrador recebe confirmação e orientação de novo login. Se houver
contas inativas, uma mensagem genérica solicita revisão administrativa antes
de qualquer reativação. Somente a frase explicativa da lixeira foi ajustada;
layout, CSS, responsividade, formulários e CSRF permanecem preservados.

O histórico de análises, relatórios, chamados e notificações não é removido
pelas operações reversíveis. Exclusão permanente mantém sua remoção explícita
de dependências, agora serializada com restauração; nenhuma tabela auxiliar
nova exige limpeza. Remoção de arquivos continua seguindo o comportamento
preexistente do storage; não se promete rollback de efeitos externos ao banco.

## G. Empresas antigas

Sem prova confiável, nenhum CLIENTE legado de empresa atualmente na lixeira
é reativado. O bloqueio persistido e a mensagem ao restaurar registram a
necessidade de revisão. Não existe tela preexistente de edição de `ativo` no
projeto; não foi criado atalho web de reativação sem autorização ou CSRF.

Uma reativação legítima posterior exige revisão explícita por administrador
responsável: verificar titularidade, motivo do bloqueio e política aplicável,
registrar a decisão e autorizar procedimento próprio de manutenção. O operador
com acesso autorizado deve usar transação que bloqueie empresa e usuário na
mesma ordem, recuse empresa ainda na lixeira, altere somente a conta aprovada
e avance sua geração. Deve preservar senha, papel e vínculo, registrar a
revisão e exigir novo login/link adequado. Esse procedimento não foi executado
nesta tarefa nem concede permissão para atuar no banco real. Uma futura tela
precisa manter ADMIN, POST, CSRF e essa mesma disciplina transacional.

Limite histórico: restaurações indevidas já concluídas antes da correção não
podem ser identificadas pela coluna `deletado_em` agora nula. Não se inventa
histórico nem se bloqueiam indiscriminadamente todas as empresas ativas.
Casos conhecidos exigem revisão administrativa separada.

## H. Sessões e WebSocket

As HMACs das SEC-002/003 foram preservadas. Geração zero produz exatamente a
impressão anterior, evitando revogar terceiros sem motivo. Gerações posteriores
entram com domínio inequívoco na mensagem HMAC, separado entre sessão e token.
O cookie antigo não volta a valer após restauração, mesmo sem tentativa de
uso durante a exclusão. Cookies legados sem fingerprint continuam recusados.
BOOT_ID permanece como defesa adicional de reinício; a revogação da SEC-004 é
persistida no banco e não depende dele.

Tokens mantêm finalidade, payload v2, expiração e consumo único. Geração e
vínculo entram no snapshot imutável e no CAS, juntamente com credencial, papel,
primeiro acesso, `ativo` e EXISTS da empresa fora da lixeira. Links anteriores
à exclusão não revivem. Login/renovação após troca de senha usam a impressão
do snapshot verificado, sem adotar geração concorrente mais recente.

Eventos autenticados, handshake e notificações mantêm `Usuario FOR SHARE`
até autorizar/enfileirar. A empresa é consultada por SELECT MVCC sem lock,
na mesma Session dos leitores independentes; não há conexão extra nem
inversão Empresa→Usuario/Usuario→Empresa. A exclusão precisa bloquear/atualizar
todos os usuários antes de confirmar, então espera emissões anteriores.

Requisições HTTP já autorizadas e em curso não são canceladas retroativamente.
Mensagens autorizadas e enfileiradas antes do commit da exclusão podem chegar
ao transporte depois dele; isso não é nova autorização. Novas emissões após
commit consultam o banco e não entregam à sala da geração revogada. Após
restauração, somente uma sessão nova entra na geração atual. Varredura e
handlers removem conexões inválidas, sem usar o registro de SIDs como autoridade.

Falha na consulta de autorização HTTP retorna 503 sanitizado e limpa sessão;
Socket.IO e entrega falham de forma fechada. Notificações continuam isoladas
por usuário/empresa, inclusive com pool de uma conexão.

## I. Testes

Resultados reais desta tarefa, sem reutilizar totais históricos:

| Execução | Testes aprovados | Falhas/erros/ignorados | Tempo |
| --- | ---: | --- | ---: |
| SEC-004 funcional SQLite/HTTP/Socket.IO | 32 | 0/0/0 | 5,695 s |
| Migração SQLite desde esquema anterior | 5 | 0/0/0 | 0,407 s |
| SEC-004 concorrência PostgreSQL | 15 | 0/0/0 | 2,705 s |
| Migração PostgreSQL desde esquema anterior | 6 | 0/0/0 | 1,542 s |
| Suíte geral completa, navegador e backup habilitados | **398** | **0/0/0** | **90,108 s** |
| PostgreSQL combinado SEC-002/003/004 e migração | **99** | **0/0/0** | **19,509 s** |

**Total da regressão final: 497 testes aprovados (398 + 99), sem falhas,
erros ou ignorados.** Os focados já estão incluídos nesses totais.
O comando combinado PostgreSQL contém 37 testes de tokens, 41 de sessões,
15 de empresas e 6 de migração.

Os 32 casos específicos inspecionam o banco e exercitam estados mistos,
usuários externos/ADMIN, legado, repetição, ciclos, rollback, CSRF, não ADMIN,
cookies antigos, novo login, tokens, primeiro acesso, sockets, notificações,
histórico da exclusão permanente e os três estados comerciais. As cinco
verificações de migração SQLite usam esquema anterior real com dados.

A suíte completa habilita Chromium, ensaio de backup privado, WSGI/Gunicorn e
as regressões SEC-001/002/003/006/006B, autenticação, ETL, dashboards, uploads,
NexoBot e notificações. Testes focados já incluídos na suíte geral não devem
ser somados outra vez. Falhas de tentativas preliminares durante implementação
não foram apresentadas como aprovação; os números são das execuções concluídas.

Comandos efetivamente utilizados, a partir da raiz:

```bash
/tmp/nexo-sec006b-validation/bin/python -B -m unittest tests.test_company_restore_security -v
/tmp/nexo-sec006b-validation/bin/python -B -m unittest tests.test_company_restore_migration -v
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest discover -s tests -t . -v
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest \
  tests.postgresql_auth_tokens tests.postgresql_session_revocation \
  tests.postgresql_company_restore_security tests.postgresql_company_restore_migration -v
git -c core.whitespace=cr-at-eol diff --check
```

A virtualenv de validação SEC-006B foi reutilizada sem atualizar dependências;
pip 26.2.2 e dotenv 1.2.4 permanecem verificados pelas regressões do instalador.

## J. PostgreSQL

O helper `PrivatePostgreSQL` inicia clusters novos, usuário aleatório, diretório
0700, socket Unix exclusivo e nenhuma interface TCP; não aceita DSN ou servidor
existente. As credenciais/configurações libpq do ambiente são excluídas. Cada
teste recebe banco próprio, removido ao final. PostgreSQL local 17.11.

Quinze casos SEC-004 verificam locks reais observados por `pg_blocking_pids`,
exclusões/restaurações simultâneas, ambas as ordens de operações, edição de
usuário antes/depois, rollback real do servidor, fronteira FOR SHARE de evento
e notificação, corrida de login/primeiro acesso/CAS, inserção por FK, exclusão
permanente versus restauração, persistência e isolamento entre empresas.

Seis casos de migração PostgreSQL partem da revisão anterior com dados e
constraints reais. Incluem erro de servidor depois de ADD COLUMN e antes do
UPDATE legado: coluna, dados e revisão são revertidos atomicamente; nova
tentativa integral aprova. Downgrade/re-upgrade foram ensaiados exclusivamente
em bancos descartáveis. O job de CI contém ambos os módulos explicitamente e
falha se os binários privados obrigatórios faltarem, sem skip silencioso.

## K. Arquivos modificados

| Arquivo | Finalidade |
| --- | --- |
| `company_security.py` | Operações transacionais e locks da lixeira, sem commit implícito. |
| `blueprints/admin.py` | Exclusão/restauração seguras, locks de edição/permanente, rollback e mensagens. |
| `models.py` | Geração persistente de autorização e constraint. |
| `session_security.py` | Elegibilidade por empresa e vínculo de geração ao fingerprint existente. |
| `blueprints/auth.py` | Login, tokens e CAS com estado da empresa/geração e snapshots imutáveis. |
| `notifications.py` | Autorizar entrega na Session independente e excluir empresa na lixeira. |
| `realtime.py` | Revalidação na Session correta, preservando FOR SHARE/salas. |
| `app.py` | Falha de consulta de autorização retorna 503 genérico e limpa cookie. |
| `migrations/versions/e4c004a26b01_company_authorization_generation.py` | Migração aditiva e bloqueio conservador legado. |
| `templates/admin/lixeira.html` | Somente frase sobre preservação de bloqueios. |
| `tests/test_company_restore_security.py` | 32 casos específicos SQLite/HTTP/Socket.IO. |
| `tests/postgresql_company_restore_security.py` | 15 casos reais de concorrência/autorização. |
| `tests/test_company_restore_migration.py` | 5 casos de upgrade legado real em SQLite. |
| `tests/postgresql_company_restore_migration.py` | 6 casos de upgrade legado/rollback PostgreSQL. |
| `tests/test_security_deploy.py` | Adaptar somente fixture isolada de sigilo dos logs ao novo helper. |
| `.github/workflows/nexo-security-ci.yml` | Acrescentar duas etapas PostgreSQL obrigatórias; proteções anteriores preservadas. |
| `Docs/CI_SEGURANCA.md` | Comandos das duas novas suítes e escopo do job. |
| `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md` | SEC-004 implementada para revisão; SEC-005 continua pendente. |
| `Docs/RELATORIO_NEXO_SEC004_RESTAURACAO_SEGURA.md` | Diagnóstico, arquitetura, evidências e implantação/rollback. |

Nenhum arquivo preexistente foi excluído. Dependências, build/start do Render,
ETL, NexoBot, PDF, vídeo, CSS, identidade visual e regras comerciais não foram
modificados. Bancos, virtualenvs, .env, dados reais e logs ficam fora do Git.

## L. GitHub

Este documento é um snapshot anterior ao commit/push da branch exclusiva e à
abertura da PR. Não afirma que publicação ou CI remota já ocorreram nesse
instante. A entrega final registra SHA, URL e estado real por API/CLI.

A PR deve permanecer em rascunho para revisão. Não foi autorizado merge,
auto-merge, push na `main`, force push, exclusão de branch ou deploy.
Os checks esperados são `security-sqlite-browser` e `security-postgresql`.
Aprovação de CI não autoriza integração ou implantação.

## M. Render e Supabase

Sem acesso, alteração, migração, deploy ou troca de credenciais em produção
por esta tarefa. O proprietário informou Auto-Deploy ativado; o YAML não
comprova o estado atual do painel. Publicar em branch exclusiva não valida nem
implanta produção. A PR precisa ficar aberta para revisão/homologação.

Procedimento FUTURO, mediante autorização própria e acesso do operador:

1. Homologar a PR e a migração, conferir backup e restauração, versões e schema
   reais. Confirmar Auto-Deploy no painel; pausar integrações/implantações
   automáticas pelo operador autorizado antes de qualquer merge.
2. Abrir janela controlada e suspender tráfego, sockets, jobs e escritores
   antigos. Não manter versões antigas e novas atendendo simultaneamente:
   o código antigo ignora a geração e ainda pode reativar contas indevidamente.
3. Em conexão apropriada para DDL, confirmar revisão anterior e aplicar somente
   a revisão aprovada `e4c004a26b01`, com backup verificado. A migração não
   pertence ao build e não se presume aplicada pelo deploy automático.
4. Conferir coluna, default, CHECK, revisão e bloqueio conservador das contas
   legadas; implantar o código aprovado enquanto o tráfego continua suspenso.
5. Homologar login/novo login, bloqueados, lixeira legada, primeiro acesso,
   cookies/links anteriores, sockets/notificações, isolamento e estados de
   negócio; só reabrir tráfego após aprovação explícita do operador.
6. Registrar versão ativa, migração, testes e resultado real do Render. Nenhum
   desses passos de produção foi executado nesta entrega.

Rollback: interromper tráfego e investigar; preferir correção adiante mantendo
o esquema aditivo e os bloqueios. Voltar ao código antigo reintroduz a falha e
ignora a geração. Downgrade remove o histórico persistente de revogação e pode
reviver cookies/tokens se o operador não executar invalidação abrangente e
procedimento coordenado. Não automatizar downgrade, não reativar usuários
legados e não restaurar dados reais indiscriminadamente. Um rollback de código
não restaura estado de banco/arquivos nem equivale a rollback de segurança.

## N. Riscos residuais

- Produção, versão PostgreSQL real, configuração do Render, PgBouncer e carga
  comercial não foram acessados nem homologados; isso exige janela própria.
- Código novo exige migração; a aplicação não aplica schema automaticamente.
- Revogação é baseada no banco e não pode recolher mensagens autorizadas e
  enfileiradas antes do commit. A desconexão de transporte é complementar.
- Operações SQL/scripts externos que contornem os serviços, mudem vínculo ou
  reativem contas sem avançar geração não são um fluxo seguro suportado.
- Usuários já reativados indevidamente antes da SEC-004 precisam de evidência
  externa e revisão; a migração não reconstrói história desconhecida.
- SQLite valida funcionalidade e migração, mas concorrência PostgreSQL foi
  testada separadamente em READ COMMITTED; outras configurações precisam de
  avaliação. Locks em empresas com muitos usuários podem aumentar espera.
- A suíte não mede carga comercial nem prova ausência de toda vulnerabilidade.
  Nenhuma SEC-005 foi implementada; seus riscos de recursos ETL permanecem.

## O. Resultado final

**CORRIGIDO COM RESSALVAS neste snapshot pré-publicação:** implementação e
497 testes locais aprovados; publicação da branch, abertura da PR e aprovação
da CI remota ainda serão verificadas na sequência autorizada da tarefa.

A arquitetura preserva decisões administrativas, trata legado de forma
conservadora, revoga autorização persistentemente e mantém a lixeira e o
histórico. Integração, migração e homologação de produção são etapas separadas
que dependem de revisão e autorização; não são inferidas dos testes locais.

## P. Resumo para ChatGPT

**RESUMO PARA CHATGPT: NEXO-SEC-004**

- Base: `2e18c506c90ae2e9fe9f0231912c50d84bd004d8`.
- Falha: restauração sobrescrevia `ativo=True` em contas antes bloqueadas;
  cookies e links anteriores podiam voltar a valer sem mudança de senha.
- Solução A: preservar `ativo`, bloquear empresa na lixeira pelo banco,
  geração persistente por usuário nas HMACs, CAS e salas existentes.
- Banco: revisão `e4c004a26b01` após `b7c4e2a9f031`; coluna
  `geracao_autorizacao` NOT NULL/default0/CHECK não negativo.
- Legado: todos os CLIENTE de empresas já na lixeira ficam inativos/gen1;
  restauração não ativa contas desconhecidas; revisão explícita necessária.
- Sessões/tokens antigos não revivem; primeiro acesso, expiração/finalidade,
  consumo único, fingerprints e FOR SHARE das SEC anteriores preservados.
- Testes e resultados desta tarefa: seções I/J; arquivos: seção K.
- Branch: `security/sec-004-safe-company-restore`; publicação/CI reais serão
  registrados no relatório final e na descrição da PR, sem alegação antecipada.
- Riscos: rollout coordenado, histórico desconhecido, mensagens anteriores
  já enfileiradas e ausência de homologação/carga real em produção.
- Render/Supabase: não modificados; migração/implantação futuras com janela,
  operadores autorizados e sem escritores antigos. Sem merge/auto-merge.
- SEC-005: **PENDENTE, NÃO IMPLEMENTADA**.
- Próxima etapa: revisão da PR e homologação isolada. Antes de eventual
  integração autorizada, preparar migração e impedir deploy automático sem
  coordenação; não executar esses passos de produção nesta tarefa.
