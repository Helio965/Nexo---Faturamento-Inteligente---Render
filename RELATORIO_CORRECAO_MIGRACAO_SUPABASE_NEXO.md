# RELATÓRIO: correção do HTTP 500 no login (migração Supabase `e4c004a26b01`)

| Item | Situação em 25/10/2026 |
|---|---|
| **Banco de produção (Supabase)** | **NENHUMA ALTERAÇÃO FOI REALIZADA.** Nenhuma conexão, consulta, backup, migração, `stamp` ou `downgrade` foi executada contra o Supabase. |
| Render | Nenhum acesso ao painel, nenhuma variável alterada, nenhum deploy. |
| Código da aplicação | Nenhuma alteração. A única mudança no repositório é este relatório. |
| Migração `e4c004a26b01` | **Não executada.** Aguarda autorização expressa, backup verificado e as confirmações da seção 9. |
| Causa do HTTP 500 | **Provável, com confiança alta**, para a produção. **Confirmada** em reprodução local fiel. |
| Executor da análise | Claude Code (sessão em nuvem), branch `claude/zen-johnson-e12c1z`, sobre `origin/main` = `ff8c2d8`. |

Este relatório não autoriza nenhuma operação. Ele prepara a decisão do responsável e documenta a evidência para auditoria independente.

---

## 0. Resumo executivo

1. O código em `main` (desde `cde2afc`, SEC-004, PR #17) mapeia a coluna `usuario.geracao_autorizacao`. Todo carregamento de `Usuario` pelo SQLAlchemy inclui essa coluna no `SELECT`.
2. Segundo a verificação independente do ChatGPT, o banco de produção está em `b7c4e2a9f031` e não tem essa coluna.
3. O `POST /auth/login` executa `SELECT ... usuario.geracao_autorizacao ... FROM usuario WHERE email = ...` (`blueprints/auth.py:263-265`). Esse SELECT não tem tratamento de erro. O PostgreSQL responde `UndefinedColumn` (SQLSTATE `42703`) e o Flask devolve **HTTP 500**, para qualquer e-mail, existente ou não, e com qualquer senha.
4. Reproduzi exatamente esse quadro num PostgreSQL local construído pelas migrações oficiais até `b7c4e2a9f031`:
   - GET `/auth/login`, `/healthz` e `/healthz/db`: 200;
   - todo POST de login: 500.
5. Depois de `flask db upgrade` no mesmo banco, com o mesmo processo gunicorn ainda no ar e sem restart nem redeploy, o login do administrador e o do cliente voltaram a funcionar.
6. A única diferença de schema entre `b7c4e2a9f031` e o código atual é a migração `e4c004a26b01`. Ela é a única pendente: adiciona a coluna (com CHECK) e bloqueia, de forma conservadora e irreversível pela migração, os usuários CLIENTE de empresas que estão na lixeira.
7. **Bloqueios para executar agora:**
   - não há autorização;
   - **não há backup confirmado**: o plano Free do Supabase não tem backup automático, e o repositório registra que nenhum backup real foi feito;
   - não consegui comprovar daqui o commit implantado no Render, nem que a `DATABASE_URL` do Render aponta para `wuipygscavreoikzrqnv`;
   - este ambiente não tem credenciais e não alcança o Supabase (TCP 5432 bloqueado). O Render Free não oferece Shell.

   A execução, portanto, cabe ao responsável, pelo procedimento da seção 10, depois da autorização.

---

## 1. Diagnóstico

### 1.1 Mecanismo do erro

| Passo | Evidência |
|---|---|
| A rota `POST /auth/login` procura o usuário pelo e-mail antes de verificar a senha. | `blueprints/auth.py:263-265` |
| `Usuario` mapeia `geracao_autorizacao` (Integer, NOT NULL, default 0), sem `deferred`. | `models.py:135-137` e CHECK em `models.py:154-156` |
| SQL emitido pelo SQLAlchemy 2.1.6 | `SELECT usuario.id_usuario, usuario.id_empresa, usuario.nome, usuario.email, usuario.senha_hash, usuario.role, usuario.ativo, usuario.geracao_autorizacao, usuario.primeiro_acesso, usuario.ultimo_acesso, usuario.data_criacao, usuario.data_atualizacao FROM usuario WHERE usuario.email = %(email_1)s` |
| Resposta do PostgreSQL com o schema `b7c4e2a9f031` | `psycopg2.errors.UndefinedColumn: column usuario.geracao_autorizacao does not exist` (SQLSTATE 42703), encapsulado em `sqlalchemy.exc.ProgrammingError` |
| Motivo de virar 500 | `login()` não tem `try/except`. O app só registra handlers para `CSRFError` e `429` (`app.py:319`, `app.py:329`). Com `DEBUG=False`, o Flask registra `Exception on /auth/login [POST]` e devolve `500 Internal Server Error`. |

### 1.2 Por que o resto parece saudável

- `/healthz` não acessa o banco, e `/healthz/db` só executa `SELECT 1` (`app.py:293-309`). Os dois respondem 200 com a coluna ausente. **Não servem como prova da correção.** O health check do Render usa `/healthz` (`render.yaml:22`), então o serviço continua "healthy".
- `GET /auth/login` sem cookie não consulta `usuario`. O SQL capturado durante a requisição confirmou que nenhuma consulta a `usuario` foi feita.
- Outros caminhos que leem `Usuario` tratam o erro sem 500:
  - requisição com cookie de sessão: 503 "Serviço indisponível", depois o cookie é limpo;
  - `/auth/recuperar-senha`: mostra a mensagem genérica de sucesso, **mas nenhum e-mail é enviado**;
  - links de token: redirecionam como "token inválido";
  - Socket.IO: recusa a conexão.

  Fica só um `WARNING` com `ProgrammingError` no log.

### 1.3 Classificação

- **Confirmada localmente.** O sintoma foi reproduzido de forma independente por 5 frentes, entre elas um gunicorn iniciado com o `startCommand` do `render.yaml`. A correção também foi reproduzida, sem restart.
- **Provável com confiança alta em produção.** Faltam dois fatos que só o painel mostra:
  1. o commit implantado descende de `cde2afc`;
  2. o log do Render mostra `UndefinedColumn ... geracao_autorizacao`.

  Contraprova feita: o código anterior à SEC-004 (`2e18c50`) faz login normalmente sobre o mesmo banco `b7c4e2a9f031`. Portanto o 500 exige as duas condições ao mesmo tempo: código com SEC-004 e banco sem a migração.
- Sequência provável do incidente: a PR #17 foi integrada à `main` em 23/10/2026. Segundo `Docs/PREPARACAO_RENDER.md:81`, o proprietário informou Auto-Deploy **ativado**. O Render teria implantado o código, e a migração, que a SEC-004 exigia aplicar **antes** do novo código (`Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md:31-33`), não foi aplicada.

### 1.4 Hipóteses alternativas testadas localmente

| Hipótese | Sintoma que produziria | Compatível com o relato? |
|---|---|---|
| CSRF ausente ou inválido, ou `SECRET_KEY` trocada entre GET e POST | 400 com a mensagem "Sua sessão expirou" | Não |
| Rate limit | 429 a partir do 11º POST por minuto | Não |
| `SECRET_KEY` ausente, ou Redis de rate limit sem o pacote | O app nem sobe (GET também falharia) | Não |
| Banco inacessível | `/healthz/db` 503 e `OperationalError` | Não, se `/healthz/db` = 200 |
| Coluna criada à mão como nullable | 500 só com a senha certa (`ValueError`) | Não: o 500 ocorre com qualquer e-mail |
| `senha_hash` fora do formato werkzeug | 500 só para aquele usuário | Não |
| Timeout ou falta de memória no gunicorn | 502 do proxy do Render | Não |

**Assinatura no log do Render** (permite distinguir sem expor segredos):

- `[ERROR] app: Exception on /auth/login [POST]`;
- seguido de `psycopg2.errors.UndefinedColumn: column usuario.geracao_autorizacao does not exist`;
- e de `File ".../blueprints/auth.py", line 263, in login`.

O traceback não contém senha nem `SECRET_KEY`. Contém, porém, o e-mail digitado em `[parameters: {'email_1': ...}]`, que deve ser **redigido** antes de compartilhar.

---

## 2. Evidências

### 2.1 Fornecidas pelo ChatGPT (não reverificadas aqui, por falta de acesso)

Na tabela `public.usuario` existe; a coluna `geracao_autorizacao` não existe; `public.alembic_version` = `b7c4e2a9f031`. A próxima migração do repositório é `e4c004a26b01`. Essas três afirmações são **coerentes com todas as observações locais**. A seção 10 (P1-P3) as confirma de novo de forma somente leitura.

### 2.2 Reprodução local

Ambiente: PostgreSQL 16.15 local isolado (127.0.0.1), schema construído **somente** por `flask db upgrade` (migrações oficiais), dados 100% fictícios (`@example.invalid`), Python 3.12, Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.6, Flask-Migrate 4.0.7, Alembic 1.20.1, psycopg2-binary 2.9.9, `FLASK_ENV=production`.

| # | Cenário | Resultado |
|---|---|---|
| 1 | Banco em `b7c4e2a9f031`: GET `/auth/login`, `/healthz`, `/healthz/db` | 200, 200, 200 |
| 2 | Banco em `b7c4e2a9f031`: POST login (admin com senha certa, senha errada, cliente ativo, cliente pendente, e-mail inexistente) | **500** em todos, `UndefinedColumn` 42703 |
| 3 | Gunicorn com o `startCommand` do `render.yaml` + `PROXY_FIX_HOPS=1` + curl | POST 500. O log tem `Exception on /auth/login [POST]` e o traceback aponta `auth.py:263` |
| 4 | `flask db upgrade` com o **mesmo** gunicorn no ar (mesmo PID, mesma conexão do pool) | POST admin 302 → `/admin/dashboard` 200; cliente 302 → `/cliente/dashboard` 200; senha errada 200; cliente de empresa na lixeira 200 "Esta conta está desativada" |
| 5 | Crawl depois da migração: 51 páginas do admin, 48 de um segundo admin, 16 de um cliente, 7 de um cliente de empresa suspensa; mais os principais POSTs (empresa, análise, ETL, upload, tickets, guia, lixeira) | Nenhum 5xx; Socket.IO aceito |
| 6 | Código pré-SEC-004 (`2e18c50`) sobre banco `b7c4e2a9f031` | Login 200/302: o erro exige código novo + banco antigo |
| 7 | Simulação de RLS habilitado (não forçado), com papel dono NOSUPERUSER NOBYPASSRLS | Mesmo comportamento: 500 antes, OK depois |

### 2.3 Lacuna de schema

| Verificação | Em `b7c4e2a9f031` | Em `e4c004a26b01` |
|---|---|---|
| `alembic.autogenerate.compare_metadata` (`compare_type` e `compare_server_default`) | 1 diferença: `add_column usuario.geracao_autorizacao` | 0 diferenças |
| CHECKs dos models × banco | Falta `ck_usuario_geracao_autorizacao` (20 contra 19) | 20 contra 20 |
| `diff` do `pg_dump --schema-only` | Só 2 linhas: a coluna e o CHECK | n/a |
| Impressão digital (P9, Apêndice B, PG 16) | columns 141 `0a392cc115c56c534c6af068cc5dfb75` · constraints 57 `f3313f1685a4979e588325da9e8b7fe5` · indexes 27 `b45f24cbb56eb108a6395f934d55a6e9` | columns 142 `006bf355619a793573c4438f1e0e70d7` · constraints 58 `7a578489692205a9fb4c2c0c34bcddca` · indexes 27 `b45f24cbb56eb108a6395f934d55a6e9` |

O app não usa SQL textual que referencie colunas: os únicos `text()` são `SELECT 1` e um `PRAGMA` de SQLite. Isso significa que a comparação com os models cobre todo o runtime.

**Ressalva:** o PostgreSQL só acusa a primeira coluna inexistente. Por isso o P3 e o P9 conferem as demais colunas da produção antes da migração. Os hashes podem variar por formatação em PG 15/17 sem diferença real; nesse caso, compare a lista do P3.

---

## 3. Versão do GitHub

| Item | Valor |
|---|---|
| `origin/main` | `ff8c2d8009c4889648a357fb5488a2a004cb7fe8` (merge da PR #20, 24/10/2026), igual ao `HEAD` desta branch antes deste relatório |
| Commit que introduziu a coluna no modelo **e** a migração (no mesmo commit) | `cde2afcd0c872c55b687acd67ef8045b15c91de3` (SEC-004), integrado pelo merge `ff148796d9b579418b3782d472eb44fb0025fe6f` (PR #17, 23/10/2026) |
| Arquivo da migração | `migrations/versions/e4c004a26b01_company_authorization_generation.py`, blob git `cc3336b6242ab26fffe6dbec48857070a4de77a4`, SHA-256 `155e3ba0edd3b2d0d53bc30da18b187142fa9ace5e339f83485f18246c8c3115` |
| Estabilidade | O blob é idêntico nos 13 commits de `cde2afc` a `ff8c2d8`. `models.py`, `extensions.py` e `migrations/` não mudaram depois de `cde2afc`. Em 60 commits analisados, nenhum tem a coluna no modelo sem o arquivo da migração. |
| Cadeia Alembic | Linear, 8 revisões, base `d87a6fbc2fbe`, **head única** `e4c004a26b01`: `d87a6fbc2fbe → c7189696a9cd → f958d38a7f19 → 91a2ecf56a41 → d61b5e68082c → a3f1c9b27d04 → b7c4e2a9f031 → e4c004a26b01`. Não há branches nem merges. |

**Conclusão:** qualquer commit implantado que produza esse `UndefinedColumn` contém o arquivo da migração `e4c004a26b01`, idêntico ao revisado aqui.

## 4. Versão do Render (não verificada)

Não há acesso ao painel do Render nesta sessão, e o endereço público do serviço não consta no repositório. O subdomínio padrão `nexo-faturamento-inteligente.onrender.com` responde 404, como já registrado em `Docs/VALIDACAO_VIDEO_RENDER.md:204`.

Antes de migrar, o responsável deve conferir:

1. **Render → serviço → Events:** o SHA do último deploy "live". Depois, no clone local, `git merge-base --is-ancestor cde2afc <SHA> && echo CONTEM_SEC004`. Se **não** contiver, PARE: a causa seria outra, porque o código antigo funciona no schema `b7c4e2a9f031`.
2. **Render → Logs:** a assinatura da seção 1.4.
3. **Render → Environment** (só visualizar, sem copiar para lugar nenhum): `DATABASE_URL` e `DIRECT_URL` contêm `wuipygscavreoikzrqnv`. Ele aparece no usuário `postgres.wuipygscavreoikzrqnv` (pooler) ou no host `db.wuipygscavreoikzrqnv.supabase.co` (direta). Anotar se a `DATABASE_URL` usa a porta 6543 (Transaction pooler, esperado para o runtime).

## 5. Banco de produção: identidade e versão anterior

- **Projeto Supabase identificado (informado):** `wuipygscavreoikzrqnv`, região provável us-west-2 (`render.yaml:12-13`).
- **Identidade da `DATABASE_URL` do Render: NÃO COMPROVADA aqui.** O procedimento a comprova de três formas:
  - (a) inspeção visual no painel do Render (item 4.3);
  - (b) a URL usada na migração é copiada da página do próprio projeto (Supabase → Connect), e a sonda (Apêndice A) recusa um ref diferente;
  - (c) as contagens lidas pela sonda devem ser iguais às do SQL Editor do projeto.

  Depois da migração, o login funcionar no Render prova que o Render usa o banco migrado.
- **Versão anterior do banco (informada):** `b7c4e2a9f031`. Será confirmada pelo P1 e pela sonda, que **recusa** qualquer outro valor.
- **Migrações intermediárias pendentes:** nenhuma. Entre `b7c4e2a9f031` e a head existe só `e4c004a26b01`.

---

## 6. Migração identificada: `e4c004a26b01`

Arquivo lido integralmente: `migrations/versions/e4c004a26b01_company_authorization_generation.py` (73 linhas), junto com `migrations/env.py` e `migrations/alembic.ini`. **Nenhuma modificação é necessária nem foi feita.**

| # | Ponto | Resultado |
|---|---|---|
| 1 | Revisão anterior | `b7c4e2a9f031` (`down_revision`, linha 21) |
| 2 | Revisão aplicada | `e4c004a26b01` (linha 20). É a única aplicada a partir de `b7c4e2a9f031`. |
| 3 | Campos adicionados | `usuario.geracao_autorizacao INTEGER NOT NULL DEFAULT 0`, igual ao modelo |
| 4 | Restrições criadas | Só `ck_usuario_geracao_autorizacao CHECK (geracao_autorizacao >= 0)`, CHECK de coluna já validado. Não cria índice nem FK, e não altera as restrições existentes. |
| 5 | Registros atualizados | `UPDATE usuario SET ativo=false, geracao_autorizacao=1 WHERE role='CLIENTE' AND id_empresa IN (SELECT id_empresa FROM empresa WHERE deletado_em IS NOT NULL)`. Atinge **todo CLIENTE de empresa que está na lixeira**, inclusive quem hoje está `ativo=true` ou pendente de primeiro acesso. ADMIN nunca é atingido. Não altera `data_atualizacao`, então não deixa rastro. Nenhuma outra tabela muda (md5 de todas as tabelas antes e depois). |
| 6 | Compatibilidade PostgreSQL | DDL padrão, compatível com PG 11+ (o Supabase oferece 15 e 17). DEFAULT constante significa **sem reescrita da tabela** (relfilenode inalterado). O CHECK obriga **uma leitura completa** de `usuario` (95 ms com 1 milhão de linhas locais). O `ALTER` toma **ACCESS EXCLUSIVE** em `usuario` até o COMMIT. |
| 7 | Impacto em usuários | ADMIN e CLIENTE de empresas não excluídas: `geracao=0`, `ativo` inalterado. Login continua igual, porque a impressão de sessão e de token com geração 0 é idêntica à de antes da SEC-004. CLIENTE de empresas na lixeira: `ativo=false`, `geracao=1`. Eles já não conseguiam entrar com a empresa na lixeira, e **continuarão bloqueados se a empresa for restaurada**, até reativação administrativa individual (não existe tela para isso, `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md:24-29`). |
| 8 | Comportamento em falha | Uma única transação: `BEGIN; ALTER; UPDATE usuario; UPDATE alembic_version; COMMIT` (`env.py:99-107`, `transactional_ddl=True` no PostgreSQL, `transaction_per_migration=False`). Provado localmente: `lock_timeout` no ALTER, falha no último comando e SIGKILL do cliente terminam em **rollback total** (coluna ausente, dados e `alembic_version` intactos). Exceção: queda de rede **durante o COMMIT** deixa o resultado em dúvida, e o banco pode estar migrado (ver 10.F). |
| 9 | Limites do rollback | `downgrade()` só faz `DROP COLUMN`. **Não reativa** ninguém e apaga o histórico de revogação. Com o código atual no ar, **recriaria o HTTP 500**. Só backup desfaz o efeito de dados. Por instrução, **não usar downgrade**. |

SQL exato (gerado offline por `flask db upgrade b7c4e2a9f031:e4c004a26b01 --sql`, sem conectar a banco):

```sql
BEGIN;
-- Running upgrade b7c4e2a9f031 -> e4c004a26b01
ALTER TABLE usuario ADD COLUMN geracao_autorizacao INTEGER DEFAULT 0 NOT NULL CONSTRAINT ck_usuario_geracao_autorizacao CHECK (geracao_autorizacao >= 0);
UPDATE usuario SET ativo=false, geracao_autorizacao=1 WHERE usuario.role = 'CLIENTE' AND usuario.id_empresa IN (SELECT empresa.id_empresa
FROM empresa
WHERE empresa.deletado_em IS NOT NULL);
UPDATE alembic_version SET version_num='e4c004a26b01' WHERE alembic_version.version_num = 'b7c4e2a9f031';
COMMIT;
```

Classificação correta: **aditiva no schema, com bloqueio de dados intencional e irreversível pela própria migração.** Não deve ser descrita como "não destrutiva".

---

## 7. Backup e segurança

### 7.1 Resultado da verificação de backup: **NÃO CONFIRMADO. Execução interrompida.**

- Pela documentação oficial, o plano **Free** do Supabase não tem backup automático nem PITR. Só os planos Pro, Team e Enterprise têm backup diário, com retenção de 7, 14 e até 30 dias. Para o Free, a recomendação é exportar com `supabase db dump` / `pg_dump` e guardar a cópia fora do Supabase ([supabase.com/docs/guides/platform/backups](https://supabase.com/docs/guides/platform/backups)). O plano real do projeto não foi verificado.
- `Docs/OPERACAO_BACKUP_RESTAURACAO.md` (§1, §11) registra que **nenhum backup real do Supabase foi executado ou restaurado**. Os ensaios do repositório usaram só dados fictícios.
- Sem acesso, não consegui verificar a existência, a data ou a restaurabilidade de qualquer backup.

Pela regra deste trabalho, **a execução está interrompida** até o responsável produzir e testar um backup (Fase C da seção 10).

### 7.2 Demais itens de segurança

| Item | Situação |
|---|---|
| Versão atual do banco | Informada como `b7c4e2a9f031`; P1 e a sonda confirmam antes de migrar |
| Migração intermediária pendente | Nenhuma (seção 3) |
| Janela de manutenção | ~20-30 min com o backup já pronto. O lock dura milissegundos e o comando leva segundos. Ver Fase E. |
| Sessões existentes | Hoje **não existe sessão válida**: o login dá 500, cookies recebem 503 e são apagados, e o `BOOT_ID` invalida sessões de boots anteriores. A migração, por si só, não derruba ninguém, porque a geração 0 mantém a mesma impressão. Quem pediu redefinição de senha durante a pane não recebeu e-mail e precisa pedir de novo. |
| Escritores incompatíveis | Incompatível é **qualquer processo com código anterior a `cde2afc`** apontando para o banco de produção: checkout antigo local, "Rollback" no Render para deploy antigo, outro serviço ou preview, SQL manual, `criar_cliente_demo.py`. O código antigo funciona no schema `b7c4e2a9f031` e continuaria funcionando depois, mas reativaria em silêncio as contas bloqueadas ao restaurar uma empresa. O serviço Render atual (pós-SEC-004) é **compatível** e não precisa ser suspenso. O ETL não acessa o banco; notificações e Socket.IO só leem. |
| Render | O plano Free não tem Shell, one-off job nem pre-deploy. A migração roda na estação do responsável, como já previsto em `Docs/PREPARACAO_RENDER.md` §4. Não incluir no build. |
| Congelamento | Não fazer merge nem push na `main` durante a janela: pelo relato, o Auto-Deploy está ativo e a `main` não é protegida. |

---

## 8. Riscos identificados

| Risco | Probabilidade | Impacto | Mitigação no procedimento |
|---|---|---|---|
| Ausência de backup restaurável | Hoje: certo | Alto (o UPDATE é irreversível pela migração) | Fase C obrigatória, com teste de restauração e exportação da lista P4 |
| Bloqueio de CLIENTE de empresas na lixeira que deveriam continuar ativos | Depende dos dados (P4) | Médio | Revisar P4 antes. É o comportamento intencional da SEC-004. Reativação individual só com revisão e autorização (seção 16). |
| Fila de lock: uma transação aberta em `usuario` faz o ALTER esperar e bloqueia leituras de `usuario` | Baixa, com o P8 vazio | Médio (o login já está fora; a fila pode ocupar threads do gunicorn) | P8 imediatamente antes. `lock_timeout=5s` via `PGOPTIONS` vale **só na conexão direta**: o Supavisor ignora opções `-c` além de `search_path` e `log_level` ([supavisor#858](https://github.com/supabase/supavisor/pull/858)). A sonda mostra o valor efetivo. Contingência com `pg_cancel_backend` (10.F). O teto global do Supabase para o papel `postgres` é ~2 min ([timeouts](https://supabase.com/docs/guides/database/postgres/timeouts)). |
| Migrar o banco errado: `.env` local preenchendo variáveis, `NEXO_DB_DIRECT` ≠ `"1"` exato, Transaction pooler 6543, ref divergente, `?host=` na query, `search_path` desviado | Média, se feito à mão | Alto (falso sucesso) | Worktree limpo sem `.env`, `FLASK_SKIP_DOTENV=1`, `DATABASE_URL`=`DIRECT_URL` na sessão e **sonda** (Apêndice A), que recusa tudo isso antes de conectar e confere `to_regclass`, dono da tabela e revisão |
| Checkout errado ou revisão extra local | Baixa | Alto | Worktree do SHA implantado e alvo explícito `flask db upgrade e4c004a26b01` |
| Triggers, regras, publicações (Realtime/webhooks) ou RLS forçado em `usuario` ampliando ou anulando o efeito | Baixa (não verificado) | Médio | P7 (Apêndice B) |
| Queda de rede durante o COMMIT, com estado incerto | Muito baixa | Baixo | Conferir P1/P2 antes de repetir qualquer coisa (10.F) |
| Vazamento de credenciais (histórico, argv, logs, área de transferência) | Média, se feito à mão | Alto | `Read-Host -AsSecureString` / `read -rs`, só no escopo do processo; senha nunca no argv; sonda mascara a senha; limpar Win+V |
| `pg_dump` mais antigo que o servidor, ou falta de permissão em schemas gerenciados | Média | Bloqueia (seguro) | `pg_dump` com major ≥ servidor (P0). Se faltar permissão, `--schema=public` registrado como escopo limitado. |
| `downgrade`/`stamp` como "conserto" | n/a | Alto (recria o 500 ou mascara o estado) | Proibidos neste procedimento |

---

## 9. Autorização

**Status: NÃO RECEBIDA.** Nenhuma etapa que altere o banco foi ou será executada sem ela.

### 9.1 O que se pede ao responsável

| Item | Conteúdo |
|---|---|
| Diagnóstico | Seção 1: HTTP 500 por `UndefinedColumn usuario.geracao_autorizacao` (provável/alta em produção, confirmado localmente) |
| Projeto Supabase | `wuipygscavreoikzrqnv` (a confirmar no Render, item 4.3, e pela sonda) |
| Migração pendente | `b7c4e2a9f031 → e4c004a26b01` (única) |
| Alterações que serão executadas | `ALTER TABLE usuario ADD COLUMN geracao_autorizacao ... CHECK`; `UPDATE` que desativa os CLIENTE de empresas na lixeira (lista P4); `UPDATE alembic_version` |
| Backup | **Ainda inexistente/não verificado.** É condição para a execução (Fase C). |
| Riscos | Seção 8 |
| Reversão | Seção 16. Não existe reversão automática do efeito de dados; a recuperação total é por backup. |

**Pedido:** depois de concluir a Fase C (backup testado) e as confirmações das Fases A e B, o responsável responde, por escrito:

> "Autorizo a execução da migração `e4c004a26b01` no projeto Supabase `wuipygscavreoikzrqnv`, ciente de que N usuários CLIENTE (lista P4) ficarão bloqueados, com backup verificado em <data/hora>."

### 9.2 Quem executa

Este ambiente de IA não tem credenciais do banco, não alcança a porta 5432 do Supabase, e o Render Free não tem Shell. **Senhas ou URLs de conexão nunca devem ser enviadas por chat.** A execução cabe ao responsável, na sua estação, pelo procedimento abaixo. A IA pode revisar as saídas não sensíveis (resultados da sonda e dos blocos SQL), sempre sem credenciais.

---

## 10. Procedimento de execução (somente após a autorização)

O procedimento foi validado de ponta a ponta localmente, contra bancos `b7c4e2a9f031` fictícios, em Bash e em PowerShell 7.4.6 (pwsh). Resultados: sonda OK antes e depois, `upgrade` com código 0, revisão final `e4c004a26b01` e zero ocorrências de senha nas saídas. **O Windows PowerShell 5.1 não foi testado**; prefira o PowerShell 7 (`pwsh`).

### Fase A: confirmações nos painéis (somente leitura)

1. Render → Events: anotar o `<SHA>` implantado e conferir que contém `cde2afc` (seção 4).
2. Render → Logs: localizar a assinatura `UndefinedColumn ... geracao_autorizacao` (seção 1.4).
3. Render → Environment: conferir o ref `wuipygscavreoikzrqnv` nas duas URLs (seção 4).
4. Supabase: abrir o projeto `wuipygscavreoikzrqnv` (o ref aparece na URL do painel) e anotar o plano e o que existe em Database → Backups.
5. Confirmar que não há outra instância, script local ou serviço com código antigo usando o banco de produção. Congelar merges na `main` e pausar o Auto-Deploy durante a janela.

### Fase B: pré-verificações no SQL Editor do projeto (somente leitura)

Rodar os blocos **P0 a P7 e P9** do Apêndice B, **um por vez**. O P8 fica para o momento da execução. Esperado:

- P1 = `b7c4e2a9f031`;
- P2 = `0 | 0`;
- P3 = as 11 colunas listadas;
- P7 = nada além de `dono_usuario` e de event triggers gerenciados do Supabase (`pgrst_*`, `issue_*`).

**Exportar P4 (CSV), P5 e P6** para uma pasta privada fora do repositório. Se algo divergir, PARE e analise antes de seguir.

### Fase C: backup e teste de restauração (obrigatórios)

Seguir `Docs/OPERACAO_BACKUP_RESTAURACAO.md` §3, §4 e §8, que é o procedimento oficial do projeto, com estes pontos específicos:

- Conexão do backup: **Session pooler** (porta 5432, usuário `postgres.wuipygscavreoikzrqnv`, host copiado de Supabase → Connect) ou a conexão direta, se a rede tiver IPv6. **Nunca a 6543.** Credenciais em `pg_service.conf` (sem senha) + passfile privado, nunca no argv.
- `pg_dump` com versão principal **≥** à do servidor (P0). Exemplo PowerShell, com utilitários PostgreSQL 18 locais:

```powershell
$Bin = 'C:\Program Files\PostgreSQL\18\bin'
$env:PGSERVICEFILE = "$env:USERPROFILE\nexo-operacao\credenciais\pg_service.conf"
$env:PGPASSFILE    = "$env:USERPROFILE\nexo-operacao\credenciais\pgpass.conf"
$Dir = "$env:USERPROFILE\nexo-operacao\backups\" + (Get-Date -Format 'yyyyMMdd-HHmmss')
New-Item -ItemType Directory $Dir | Out-Null
& "$Bin\pg_dump.exe" --no-password --dbname='service=nexo_backup_autorizado' --format=custom --file="$Dir\nexo.dump" 2> "$Dir\pg_dump.log"
"pg_dump exit=$LASTEXITCODE"            # precisa ser 0; revisar pg_dump.log
(Get-FileHash -Algorithm SHA256 "$Dir\nexo.dump").Hash | Set-Content "$Dir\nexo.dump.sha256"
& "$Bin\pg_restore.exe" --list "$Dir\nexo.dump" | Select-String 'TABLE DATA public'   # 15 linhas, incl. usuario e alembic_version
```

- Se o dump completo falhar por permissão em schemas gerenciados do Supabase, repetir com `--schema=public` e registrar como **escopo limitado**. A migração só altera `public.usuario` e `public.alembic_version`.
- **Teste de restauração** num banco **novo e vazio**, num PostgreSQL local (nunca na produção):

```powershell
& "$Bin\createdb.exe" -h localhost -U postgres nexo_ensaio_restauracao
& "$Bin\pg_restore.exe" -h localhost -U postgres --dbname=nexo_ensaio_restauracao --schema=public --single-transaction --exit-on-error --no-owner --no-privileges "$Dir\nexo.dump"
"pg_restore exit=$LASTEXITCODE"         # precisa ser 0
```

  Depois, rodar o bloco P6 nesse banco local e comparar com o P6 da produção: contagens iguais e `alembic_version` = `b7c4e2a9f031`. Se o restore falhar por papéis inexistentes do Supabase (`anon`, `authenticated`, `service_role`), criá-los como `NOLOGIN` no PostgreSQL local de ensaio e repetir num banco novo.
- Criptografar o dump (`Docs/OPERACAO_BACKUP_RESTAURACAO.md` §5) e guardá-lo fora do repositório e do Render. **Só com o restore aprovado o backup conta como confirmado.**

### Fase D: preparar a estação (sem credenciais ainda)

1. Num **checkout limpo do `<SHA>` implantado**, que garante que não há `.env`:
   - com clone existente: `git fetch origin` e depois `git worktree add ..\nexo-migracao <SHA>`;
   - sem clone: `git clone https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render nexo-migracao` e depois `git -C nexo-migracao checkout <SHA>`.
2. Python **3.12 x64**: o `psycopg2-binary 2.9.9` não tem wheel Windows para 3.13+ nem para ARM64. Dentro de `nexo-migracao`:
   - `py -3.12 -m venv .venv`;
   - `.\.venv\Scripts\python.exe -I tools\install_dependencies.py --requirements requirements.txt` (instalador oficial do projeto).
3. Salvar a sonda (Apêndice A) **fora** do repositório, por exemplo em `%USERPROFILE%\nexo-operacao\sonda_migracao_nexo.py`.
4. Conferir que `migrations\versions\e4c004a26b01_company_authorization_generation.py` existe e que `Get-FileHash` dá `155E3BA0EDD3B2D0D53BC30DA18B187142FA9ACE5E339F83485F18246C8C3115`.

### Fase E: execução (PowerShell 7, na raiz de `nexo-migracao`)

```powershell
$Py    = (Resolve-Path .\.venv\Scripts\python.exe).Path
$Sonda = "$env:USERPROFILE\nexo-operacao\sonda_migracao_nexo.py"
'PGHOSTADDR','PGSERVICE','PGSERVICEFILE','PGPASSFILE','DATABASE_URL','DIRECT_URL','NEXO_SONDA_ENSAIO_LOCAL' |
  ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
$env:FLASK_APP = 'wsgi:app'; $env:FLASK_SKIP_DOTENV = '1'; $env:FLASK_ENV = 'production'; $env:NEXO_DB_DIRECT = '1'
$env:PGSSLMODE = 'require'; $env:PGOPTIONS = '-c lock_timeout=5s'      # efetivo só na conexão direta
$env:SECRET_KEY = & $Py -c "import secrets; print(secrets.token_hex(32))"   # descartável: a migração não usa
# URL copiada de Supabase > projeto wuipygscavreoikzrqnv > Connect > "Session pooler" (5432) ou "Direct".
# Senha com caracteres especiais deve estar percent-encoded. Nada aparece na tela nem no histórico.
$s = Read-Host 'DIRECT_URL' -AsSecureString
$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
try { $env:DIRECT_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
$env:DATABASE_URL = $env:DIRECT_URL; Remove-Variable s, b

& $Py $Sonda antes                                    # 1) precisa terminar "RESULTADO: OK"
& $Py -m flask db upgrade b7c4e2a9f031:e4c004a26b01 --sql 2>&1 | ForEach-Object { "$_" }   # 2) prévia = SQL da seção 6
& $Py -m flask db current 2>&1 | ForEach-Object { "$_" }  # 3) b7c4e2a9f031
& $Py -m flask db heads   2>&1 | ForEach-Object { "$_" }  # 4) e4c004a26b01 (head)
# 5) SQL Editor: rodar P8 AGORA. Só continuar com zero linhas.
& $Py -m flask db upgrade e4c004a26b01 2>&1 | ForEach-Object { "$_" }; "upgrade exit=$LASTEXITCODE"   # 6) MIGRAÇÃO
& $Py -m flask db current 2>&1 | ForEach-Object { "$_" }  # 7) e4c004a26b01 (head)
& $Py $Sonda depois                                   # 8) precisa terminar "RESULTADO: OK"
'DIRECT_URL','DATABASE_URL','SECRET_KEY','PGOPTIONS' | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
```

Notas:

- Na saída da sonda, comparar "usuários" e "alvo do UPDATE" com o P5 (soma) e o P4 (linhas) do SQL Editor. Iguais é a prova de que se trata do mesmo banco.
- `lock_timeout efetivo: 5s` indica proteção ativa; `0` indica que o pooler ignorou a opção. Nesse caso vale a contingência 10.F.
- As linhas `INFO [alembic...]` saem no stderr. É normal que apareçam, ou que fiquem em vermelho no PowerShell 5.1.
- A saída esperada do passo 6 inclui: `Running upgrade b7c4e2a9f031 -> e4c004a26b01, SEC-004: ...` e `upgrade exit=0`.

Equivalente em Bash (Linux/macOS/WSL; no Git Bash use `.venv/Scripts/python.exe`):

```bash
PY="$PWD/.venv/bin/python"; SONDA="$HOME/nexo-operacao/sonda_migracao_nexo.py"
unset PGHOSTADDR PGSERVICE PGSERVICEFILE PGPASSFILE DATABASE_URL DIRECT_URL NEXO_SONDA_ENSAIO_LOCAL
export FLASK_APP=wsgi:app FLASK_SKIP_DOTENV=1 FLASK_ENV=production NEXO_DB_DIRECT=1
export PGSSLMODE=require PGOPTIONS='-c lock_timeout=5s'
export SECRET_KEY="$("$PY" -c 'import secrets; print(secrets.token_hex(32))')"
read -rsp 'DIRECT_URL: ' DIRECT_URL; echo; export DIRECT_URL DATABASE_URL="$DIRECT_URL"
"$PY" "$SONDA" antes                                   # RESULTADO: OK
"$PY" -m flask db upgrade b7c4e2a9f031:e4c004a26b01 --sql
"$PY" -m flask db current                              # b7c4e2a9f031
"$PY" -m flask db heads                                # e4c004a26b01 (head)
# SQL Editor: P8 sem linhas
"$PY" -m flask db upgrade e4c004a26b01; echo "upgrade exit=$?"
"$PY" -m flask db current                              # e4c004a26b01 (head)
"$PY" "$SONDA" depois                                  # RESULTADO: OK
unset DIRECT_URL DATABASE_URL SECRET_KEY PGOPTIONS
```

**Proibido neste procedimento:** `flask db migrate`, `flask db stamp`, `flask db downgrade`, `db.create_all()`, `init_db.py`, `seed.py`, `criar_cliente_demo.py`, SQL manual de DDL, e qualquer `flask` executado fora do worktree e das variáveis acima. Se aparecer "Target database is not up to date", a resposta é este `upgrade` com alvo explícito, nunca `stamp`.

### Fase F: contingências

- **O upgrade não termina em ~15 s** (provável espera por lock). Ctrl+C **não** libera a fila. No SQL Editor:

  ```sql
  SELECT pid, state, wait_event_type, date_trunc('second', now() - query_start) AS espera
    FROM pg_stat_activity
   WHERE pid <> pg_backend_pid() AND query LIKE 'ALTER TABLE usuario ADD COLUMN geracao_autorizacao%';
  SELECT pg_cancel_backend(<pid>);   -- cancela só a migração: rollback total
  ```

  Depois, rodar P1 e P2 (devem continuar `b7c4e2a9f031` e `0 | 0`), identificar a sessão bloqueadora pelo P8 e só então repetir.
- **Qualquer erro ou queda de conexão:** **não repetir às cegas.** Rodar P1 e P2 no SQL Editor:
  - `b7c4e2a9f031` e `0 | 0` significa que nada mudou: corrigir a causa (a sonda mostra só a classe do erro e o SQLSTATE) e repetir;
  - `e4c004a26b01` com a coluna presente significa que a migração foi aplicada: seguir para a Fase G.
- **`InsufficientPrivilege` / `must be owner`:** nada mudou. O papel da URL não é dono de `public.usuario` (a sonda acusa isso antes). Usar a conexão do papel `postgres` do projeto.
- **`DuplicateColumn` / `DuplicateObject`:** alguém criou a coluna ou o CHECK à mão. Nada mudou. PARE e analise; não usar `stamp`.

### Fase G: pós-verificações (somente leitura)

Rodar Q1 a Q7 (Apêndice C) e repetir o P6. Esperado:

- Q1 = `e4c004a26b01`;
- Q2 = `integer | 0 | NO`;
- Q3 = `CHECK ((geracao_autorizacao >= 0)) | true`;
- Q4: totais por perfil iguais aos do P5, com CLIENTE `ativo=true` reduzido exatamente pelas linhas `ativo=true` do P4;
- Q5 = `0 | 0 | <ids do P4>`;
- Q6: `usuario` e `alembic_version` com o mesmo total. As demais tabelas podem crescer, porque o app volta a gravar; isso é informativo e **não é motivo para reverter**.
- Q7 sem lock pendente.

### Fase H: testes de aceite (sem compartilhar credenciais)

1. Navegador: `https://<serviço>.onrender.com/healthz` → `{"status":"ok"}`; `/healthz/db` → `{"db":"ok","status":"ok"}`; `/auth/login` carrega. Nenhum restart ou redeploy é necessário (provado localmente). O serviço Free pode levar ~1 min para acordar.
2. **Teste que distingue antes e depois:** login com e-mail fictício inexistente, por exemplo `teste.inexistente@example.invalid`, e qualquer senha. Antes da migração: página "500 Internal Server Error". Depois: "E-mail ou senha incorretos.".
3. **Login administrativo** real → `/admin/dashboard`. **Login de cliente** ativo de empresa não excluída → `/cliente/dashboard` (ou `/auth/primeiro-acesso`, se pendente). Clientes da lista P4 verão "Esta conta está desativada", e isso é esperado.
4. Render → Logs: nenhum novo `UndefinedColumn`, `Exception on /auth/login`, `Autenticação indisponível` ou `Autorizacao indisponivel`.
5. Limite: 10 POSTs de login por minuto (429 significa aguardar).

### Fase I: encerramento

- Remover as variáveis (último comando da Fase E), apagar o worktree (`git worktree remove ..\nexo-migracao`) e o banco local de ensaio, e limpar o histórico da área de transferência (Win+V).
- Manter o dump criptografado e a lista P4.
- Reativar o Auto-Deploy só depois de decidir sobre `main` e deploys.
- Avisar os usuários: precisam entrar de novo, e quem pediu redefinição de senha durante a pane deve pedir outra vez.

---

## 11. Comandos executados nesta sessão

**Nenhum comando foi executado contra o Supabase, o Render ou qualquer URL de produção.** Todos rodaram localmente, contra um cluster PostgreSQL 16 temporário em `127.0.0.1` e com dados fictícios.

- Leitura: `git log/show/merge-base/rev-parse/diff/worktree`, leitura integral da migração, de `env.py`, `models.py`, `blueprints/auth.py`, `session_security.py`, `config.py`, `app.py`, `render.yaml` e da documentação.
- Preparação: `uv venv -p python3.12` + `uv pip install -r requirements.txt`; `initdb`/`pg_ctl` de um cluster local descartável.
- Reprodução: `flask db upgrade b7c4e2a9f031` em bancos locais novos; inserção de dados fictícios; login via test client do Flask e via gunicorn + curl; `flask db upgrade` / `flask db upgrade e4c004a26b01` locais; `flask db upgrade b7c4e2a9f031:e4c004a26b01 --sql` (offline); `flask db current/heads/history`.
- Análise: `compare_metadata`, `pg_dump --schema-only` + `diff`, experimentos de lock e falha (`lock_timeout`, SIGKILL, SIGINT, falha no último comando), casos-limite (`search_path`, RLS forçado, coluna/CHECK duplicados, triggers, revisão extra), ensaio `pg_dump`/`pg_restore` local, e ensaio completo das Fases E/G em Bash e pwsh 7.4.6.
- Testes do repositório (seção 14).
- Consultas públicas: documentação do Supabase (backups, conexões, timeouts, pricing), do Render (Free, deploys, maintenance mode, logs), do PostgreSQL (ALTER TABLE, libpq) e a PR supavisor#858.
- Teste de alcance: conexão TCP sem autenticação para `aws-0-us-west-2.pooler.supabase.com:5432`, que foi **bloqueada** pelo ambiente.

Transparência: a suíte `tests.postgresql_company_restore_migration` do próprio repositório inclui um teste de `downgrade` **descartável**, executado no cluster temporário que o teste cria e destrói. Nenhum `downgrade` foi executado em qualquer outro lugar.

## 12. Alterações realizadas

| Alvo | Alteração |
|---|---|
| Banco Supabase de produção | **Nenhuma** |
| Render (serviço, variáveis, deploy) | **Nenhuma** |
| Código, migrações, dependências | **Nenhuma** |
| Repositório | Apenas este arquivo, na branch `claude/zen-johnson-e12c1z` (PR em rascunho). O merge na `main` pode disparar Auto-Deploy, embora a mudança seja só de documentação. |
| Ambiente local da sessão | Bancos fictícios num cluster temporário, descartado com o contêiner |

## 13. Verificações posteriores: **pendentes** (a migração não foi executada)

| # | Verificação | Como | Esperado |
|---|---|---|---|
| 1 | `geracao_autorizacao` existe | Q2 / sonda `depois` | 1 coluna |
| 2 | Tipo | Q2 | `integer` |
| 3 | Valor padrão | Q2 | `0`, `NOT NULL` |
| 4 | Restrição | Q3 | `ck_usuario_geracao_autorizacao`, `CHECK ((geracao_autorizacao >= 0))`, validada |
| 5 | Revisão Alembic | Q1 / `flask db current` | `e4c004a26b01 (head)` |
| 6 | Usuários preservados | Q4 × P5 | Mesmo total por perfil |
| 7 | Nenhuma perda de informação | Q6 × P6, Q5 × P4 | `usuario` e `alembic_version` com o mesmo total; só os ids do P4 alterados |
| 8 | Render respondendo | `/healthz` | 200 |
| 9 | `/healthz/db` | navegador | 200 `{"db":"ok"}` |
| 10 | Página de login | `/auth/login` | Carrega |
| 11 | POST de login sem 500 | Fase H, itens 2 e 3 | "E-mail ou senha incorretos." / dashboards |

## 14. Resultado dos testes (locais)

| Suíte ou ensaio | Resultado |
|---|---|
| `tests.postgresql_company_restore_migration`, `tests.postgresql_session_revocation`, `tests.postgresql_auth_tokens`, `tests.postgresql_company_restore_security` (PostgreSQL 16 real, `NEXO_TEST_POSTGRES_BIN`) | **99 testes, OK** (52 s). Inclui os 6 da transição SEC-004 com dados pré-existentes (atomicidade, bloqueio conservador, constraints, repetição). |
| `tests.test_deploy`, `tests.test_company_restore_migration`, `tests.test_session_revocation_security`, `tests.test_auth_email_flows`, `tests.test_configuration_deploy`, `tests.test_auth_tokens_security` (SQLite) | **110 testes, OK** (37 s) |
| Reprodução do 500 e da recuperação sem restart (seção 2.2) | Confirmados |
| Ensaio do procedimento (Fases B, E, G), em Bash e pwsh 7.4.6 | OK; sem vazamento de senha |
| Sonda: casos negativos (`.env` presente, `DATABASE_URL`≠`DIRECT_URL`, porta 6543, ref divergente, `NEXO_DB_DIRECT='1 '`, `?host=` na query, flag de ensaio com host remoto, host inalcançável) | Todos terminam em **PARE**, sem conectar quando o alvo está errado e sem imprimir senha |
| Testes manuais de login admin e cliente em produção | **Não realizados.** Dependem da migração. |

## 15. Possíveis problemas remanescentes (fora do escopo desta correção)

1. O login não tem tratamento de erro de banco: uma falha transitória vira 500 genérico. Os monitores (`/healthz`, `/healthz/db`) não detectam incompatibilidade de schema. Sugestão futura: um check que compare `alembic_version` com a head do código.
2. `/auth/recuperar-senha` engole falhas de banco e mostra sucesso sem enviar e-mail.
3. O README (`README.md:250-279`) orienta colocar as URLs do Supabase no `.env` e rodar `flask db upgrade` à mão. O `config.py:23` carrega o `.env` mesmo com `FLASK_SKIP_DOTENV=1`, preenchendo variáveis ausentes, o que pode levar a migrar o banco errado com aparência de sucesso. `NEXO_DB_DIRECT` precisa ser exatamente `"1"`.
4. `SQLAlchemy` e `alembic` não estão fixados em `requirements.txt` (vêm como dependências transitivas).
5. Documentos desatualizados: `Docs/OPERACAO_BACKUP_RESTAURACAO.md:16` e `Docs/AUDITORIA_RENDER.md` citam head `b7c4e2a9f031`.
6. Auto-Deploy possivelmente ativo e `main` sem proteção: um merge com migração implanta o código antes do schema, que foi a causa provável deste incidente.
7. Sem tela para reativar individualmente os clientes bloqueados (pendência já registrada na SEC-004).
8. A verificar no Supabase (Security Advisor): RLS e exposição do schema `public` pela Data API. O NEXO não usa a Data API, mas tabelas em `public` sem RLS ficam acessíveis por ela com a chave `anon`.
9. Plano Free do Supabase: sem backup automático e com pausa após 1 semana sem atividade. É preciso definir uma rotina de backup (RPO/RTO) conforme `Docs/OPERACAO_BACKUP_RESTAURACAO.md` §5.

## 16. Procedimento de recuperação

| Situação | Ação |
|---|---|
| Falha durante a migração | Transação única: rollback automático. Confirmar P1/P2 (10.F), corrigir a causa, repetir. **Sem downgrade.** |
| Resultado incerto (queda no COMMIT) | P1/P2 no SQL Editor são a fonte de verdade (10.F) |
| Migração aplicada, mas o login no Render continua com 500 | Ler a nova exceção no log. Se ainda for `UndefinedColumn`, a `DATABASE_URL` do Render aponta para **outro** banco: PARE e reporte. Não migrar outro banco sem nova autorização. Se for outra exceção, analisar antes de qualquer mudança. Nunca usar `downgrade` com o código atual no ar, porque recria o 500. |
| Cliente bloqueado que deveria continuar ativo | Decisão de negócio, depois de revisar a lista P4. Exige `UPDATE` individual revisado e **autorização própria**, mantendo `geracao_autorizacao` (nunca voltar para 0). Só tem efeito se a empresa sair da lixeira. |
| Necessidade de voltar ao estado anterior | Restaurar o dump da Fase C num banco **novo e separado**, validar e planejar a troca com reconciliação das gravações posteriores ao snapshot (`Docs/OPERACAO_BACKUP_RESTAURACAO.md` §8 e §10). Requer autorização própria. **Nunca** restaurar por cima da produção. |
| Reverter o código (alternativa sem migração) | Descartado por instrução (sem rollback do GitHub). Também reabriria a falha de segurança corrigida pela SEC-004. |

---

## Apêndice A: `sonda_migracao_nexo.py` (somente leitura)

Salvar fora do repositório. Ela usa o mesmo `create_app`/engine do `flask db upgrade`. Antes de conectar, recusa:

- `.env` presente;
- `NEXO_DB_DIRECT` diferente de `"1"`;
- `DATABASE_URL` diferente de `DIRECT_URL`;
- porta diferente de 5432;
- ref diferente de `wuipygscavreoikzrqnv`;
- parâmetros de alvo na query.

Depois de conectar, numa transação `READ ONLY`, confere TLS, `search_path`/`to_regclass`, dono da tabela, revisão e coluna. Imprime a URL com a senha oculta (`***`). Validada localmente com 9 casos.

```python
"""NEXO - sonda SOMENTE LEITURA para a migração e4c004a26b01.

Uso (na raiz do worktree do commit implantado, com as variáveis já definidas):
    <python do venv> CAMINHO/sonda_migracao_nexo.py antes
    <python do venv> CAMINHO/sonda_migracao_nexo.py depois

Usa o MESMO create_app/engine que o `flask db upgrade` usará (mesmo parser de URL,
mesmo .env, mesmas PGOPTIONS), abre uma transação READ ONLY e nunca imprime senha.
Saída 0 = tudo conforme o esperado; 1 = PARE.
"""

import os
import sys
from pathlib import Path

REF = "wuipygscavreoikzrqnv"
REV_ANTES, REV_DEPOIS = "b7c4e2a9f031", "e4c004a26b01"
MODO = sys.argv[1] if len(sys.argv) > 1 else ""
# Somente para o ensaio com PostgreSQL local fictício; nunca definir em produção.
ENSAIO_LOCAL = os.environ.get("NEXO_SONDA_ENSAIO_LOCAL") == "1"
falhas = []


def confere(ok, msg):
    print(("  ok   " if ok else "  PARE ") + msg)
    if not ok:
        falhas.append(msg)


def fim():
    print("RESULTADO:", "OK" if not falhas else f"PARE ({len(falhas)} problema(s))")
    sys.exit(0 if not falhas else 1)


if MODO not in ("antes", "depois"):
    sys.exit("uso: sonda_migracao_nexo.py antes|depois")

print(f"== Sonda NEXO ({MODO}){' - ENSAIO LOCAL, NÃO É PRODUÇÃO' if ENSAIO_LOCAL else ''}")
# 1. Ambiente: nada pode vir de .env nem cair na DATABASE_URL pooled (6543).
raiz = Path.cwd()
confere((raiz / "wsgi.py").is_file() and (raiz / "migrations").is_dir(), "executando na raiz do projeto")
confere(not (raiz / ".env").exists() and not (raiz / ".flaskenv").exists(), "sem .env/.flaskenv na raiz")
confere(os.environ.get("FLASK_ENV") == "production", "FLASK_ENV=production")
confere(os.environ.get("NEXO_DB_DIRECT") == "1", "NEXO_DB_DIRECT=1 (exatamente)")
confere(os.environ.get("FLASK_SKIP_DOTENV") == "1", "FLASK_SKIP_DOTENV=1")
direct = os.environ.get("DIRECT_URL", "")
confere(bool(direct.strip()), "DIRECT_URL definida")
confere(os.environ.get("DATABASE_URL", "") == direct, "DATABASE_URL igual à DIRECT_URL nesta sessão")
confere(not os.environ.get("PGHOSTADDR") and not os.environ.get("PGSERVICE"), "sem PGHOSTADDR/PGSERVICE herdados")
arq = raiz / "migrations" / "versions" / "e4c004a26b01_company_authorization_generation.py"
confere(arq.is_file(), "arquivo da migração e4c004a26b01 presente no checkout")
if falhas:
    fim()

sys.path.insert(0, str(raiz))
try:
    from sqlalchemy import text
    from wsgi import app
    from extensions import db
except Exception as erro:  # noqa: BLE001 - mensagem pode conter dados; só a classe
    confere(False, f"create_app falhou ({type(erro).__name__})")
    fim()

with app.app_context():
    url = db.engine.url
    query = {k.lower() for k in url.query}
    print("  alvo (senha oculta):", url.render_as_string(hide_password=True))
    usuario, host = url.username or "", (url.host or "").lower()
    confere(url.get_backend_name() == "postgresql", "backend PostgreSQL")
    confere(not query & {"host", "hostaddr", "port", "dbname", "user", "service", "options"},
            "query da URL sem parâmetros que mudem o alvo")
    if ENSAIO_LOCAL:
        confere(host in ("127.0.0.1", "localhost", "::1") and url.port != 6543,
                "ensaio local: somente loopback")
    else:
        confere((url.port or 5432) == 5432, "porta 5432 (direta ou Session pooler; nunca 6543)")
        ref_ok = usuario == f"postgres.{REF}" or host == f"db.{REF}.supabase.co"
        confere(ref_ok, f"URL pertence ao projeto {REF}")
        confere(host.endswith(".supabase.com") or host.endswith(".supabase.co"), "host Supabase")
    if falhas:  # alvo errado: não conectar
        fim()
    try:
        with db.engine.connect() as con:
            con.execute(text("SET TRANSACTION READ ONLY"))
            v = lambda sql: con.execute(text(sql)).scalar()  # noqa: E731
            print("  banco:", v("select current_database()"), "| papel:", v("select current_user"),
                  "| servidor:", v("show server_version"))
            ssl = v("select ssl from pg_stat_ssl where pid = pg_backend_pid()")
            confere(bool(ssl) or ENSAIO_LOCAL, "conexão com TLS")
            lock = v("show lock_timeout")
            print("  lock_timeout efetivo nesta sessão:", lock,
                  "(0 = PGOPTIONS ignorada: seguir a contingência de lock do relatório)")
            print("  search_path:", v("show search_path"))
            confere(v("select to_regclass('usuario') = to_regclass('public.usuario')"),
                    "'usuario' resolve para public.usuario")
            confere(v("select to_regclass('alembic_version') = to_regclass('public.alembic_version')"),
                    "'alembic_version' resolve para public.alembic_version")
            confere(v("select tableowner = current_user from pg_tables "
                      "where schemaname = 'public' and tablename = 'usuario'"),
                    "papel atual é dono de public.usuario (requisito do ALTER)")
            revs = [r[0] for r in con.execute(text("select version_num from public.alembic_version"))]
            esperada = REV_ANTES if MODO == "antes" else REV_DEPOIS
            confere(revs == [esperada], f"alembic_version = {esperada} (lido: {revs})")
            col = v("select count(*) from information_schema.columns where table_schema = 'public' "
                    "and table_name = 'usuario' and column_name = 'geracao_autorizacao'")
            ck = v("select count(*) from pg_constraint where conrelid = 'public.usuario'::regclass "
                   "and conname = 'ck_usuario_geracao_autorizacao'")
            alvo = v("select count(*) from public.usuario u where u.role = 'CLIENTE' and u.id_empresa in "
                     "(select e.id_empresa from public.empresa e where e.deletado_em is not null)")
            print("  usuários:", v("select count(*) from public.usuario"),
                  "| CLIENTE de empresas na lixeira (alvo do UPDATE):", alvo)
            if MODO == "antes":
                confere(col == 0 and ck == 0, "coluna e CHECK ainda ausentes")
            else:
                confere(col == 1 and ck == 1, "coluna e CHECK presentes")
                tipo = con.execute(text(
                    "select data_type, column_default, is_nullable from information_schema.columns "
                    "where table_schema = 'public' and table_name = 'usuario' "
                    "and column_name = 'geracao_autorizacao'")).one()
                confere(tuple(tipo) == ("integer", "0", "NO"), f"tipo/default/nulidade (lido: {tuple(tipo)})")
                incons = v("select count(*) from public.usuario u join public.empresa e "
                           "on e.id_empresa = u.id_empresa where u.role = 'CLIENTE' and "
                           "e.deletado_em is not null and (u.ativo or u.geracao_autorizacao <> 1)")
                confere(incons == 0, "todos os CLIENTE de empresas na lixeira com ativo=false e geração 1")
            con.rollback()
    except Exception as erro:  # noqa: BLE001 - sem mensagem: pode trazer host/usuário
        codigo = getattr(getattr(erro, "orig", None), "pgcode", None)
        confere(False, f"consulta falhou ({type(erro).__name__}, SQLSTATE {codigo})")
fim()
```

## Apêndice B: pré-verificações (SQL Editor, somente leitura, um bloco por vez)

```sql
-- [P0] Servidor e sessão
SELECT current_database() AS banco, current_user AS papel,
       current_setting('server_version') AS versao_servidor,
       current_setting('lock_timeout') AS lock_timeout,
       current_setting('statement_timeout') AS statement_timeout;

-- [P1] Revisão Alembic (esperado: 1 linha, b7c4e2a9f031)
SELECT version_num FROM public.alembic_version;

-- [P2] Coluna e CHECK ainda ausentes (esperado: 0 | 0)
SELECT (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'usuario'
           AND column_name = 'geracao_autorizacao') AS coluna_existe,
       (SELECT count(*) FROM pg_constraint
         WHERE conrelid = 'public.usuario'::regclass
           AND conname = 'ck_usuario_geracao_autorizacao') AS check_existe;

-- [P3] Colunas atuais de public.usuario (esperado: as 11 abaixo, sem geracao_autorizacao)
-- id_usuario, id_empresa, nome, email, senha_hash, role, ativo, ultimo_acesso,
-- data_criacao, data_atualizacao, primeiro_acesso
SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) AS colunas, count(*) AS total
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'usuario';

-- [P4] Usuários que o UPDATE da migração vai bloquear (ativo=false, geração 1).
-- EXPORTAR o resultado como CSV para local PRIVADO (sem e-mail; serve para reversão seletiva).
SELECT u.id_usuario, u.id_empresa, u.ativo, u.primeiro_acesso, e.deletado_em
  FROM public.usuario u
  JOIN public.empresa e ON e.id_empresa = u.id_empresa
 WHERE u.role = 'CLIENTE' AND e.deletado_em IS NOT NULL
 ORDER BY u.id_usuario;

-- [P5] Usuários por perfil/estado (guardar para comparar depois)
SELECT role, ativo, count(*) AS usuarios
  FROM public.usuario GROUP BY role, ativo ORDER BY role, ativo;

-- [P6] Linhas por tabela do schema public (guardar para comparar depois)
SELECT c.relname AS tabela,
       (xpath('/row/n/text()', query_to_xml(
           format('SELECT count(*) AS n FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text::bigint AS linhas
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
 ORDER BY c.relname;

-- [P7] Objetos que poderiam ampliar o efeito do UPDATE/ALTER (esperado: tudo vazio/false;
-- event triggers gerenciados do Supabase, como pgrst_* e issue_*, são normais)
SELECT 'trigger' AS tipo, tgname::text AS nome FROM pg_trigger
 WHERE tgrelid = 'public.usuario'::regclass AND NOT tgisinternal
UNION ALL SELECT 'rule', rulename::text FROM pg_rules WHERE schemaname = 'public' AND tablename = 'usuario'
UNION ALL SELECT 'publicacao', pubname::text FROM pg_publication_tables WHERE schemaname = 'public' AND tablename = 'usuario'
UNION ALL SELECT 'event_trigger', evtname::text FROM pg_event_trigger
UNION ALL SELECT 'rls_forcado', 'public.usuario' FROM pg_class
 WHERE oid = 'public.usuario'::regclass AND relforcerowsecurity
UNION ALL SELECT 'dono_usuario', tableowner::text FROM pg_tables WHERE schemaname = 'public' AND tablename = 'usuario';

-- [P8] IMEDIATAMENTE antes do upgrade: sessões longas/abertas e locks em public.usuario
-- (esperado: nenhuma linha; se houver, NÃO migrar até entender e encerrar a sessão)
SELECT a.pid, a.usename, a.application_name, a.state, l.mode, l.granted,
       date_trunc('second', now() - a.xact_start) AS idade_transacao
  FROM pg_stat_activity a
  LEFT JOIN pg_locks l ON l.pid = a.pid AND l.locktype = 'relation'
                      AND l.relation = 'public.usuario'::regclass
 WHERE a.datname = current_database() AND a.pid <> pg_backend_pid()
   AND (l.pid IS NOT NULL
        OR a.state IN ('idle in transaction', 'idle in transaction (aborted)')
        OR now() - a.xact_start > interval '60 seconds')
 ORDER BY a.xact_start NULLS LAST;

-- [P9] (opcional) Impressão digital do schema das 14 tabelas; comparar com a seção 2.3.
WITH t(n) AS (VALUES ('plano'),('segmento'),('empresa'),('usuario'),('analise'),('upload_relatorio'),
  ('arquivo_armazenado'),('indicador_analise'),('relatorio_analise'),('produto_curva_abc'),
  ('chamado_suporte'),('mensagem_suporte'),('notificacao'),('guia_topico')),
cols AS (SELECT c.table_name||'.'||c.column_name||':'||c.data_type||':'||c.is_nullable||':'||coalesce(c.column_default,'') AS s
           FROM information_schema.columns c JOIN t ON t.n = c.table_name WHERE c.table_schema = 'public'),
cons AS (SELECT r.relname||'.'||k.conname||':'||k.contype::text||':'||pg_get_constraintdef(k.oid) AS s
           FROM pg_constraint k JOIN pg_class r ON r.oid = k.conrelid
           JOIN pg_namespace ns ON ns.oid = r.relnamespace JOIN t ON t.n = r.relname WHERE ns.nspname = 'public'),
idx AS (SELECT i.indexdef AS s FROM pg_indexes i JOIN t ON t.n = i.tablename WHERE i.schemaname = 'public')
SELECT 'columns' AS kind, count(*) AS n, md5(string_agg(s, '|' ORDER BY s)) AS hash FROM cols
UNION ALL SELECT 'constraints', count(*), md5(string_agg(s, '|' ORDER BY s)) FROM cons
UNION ALL SELECT 'indexes', count(*), md5(string_agg(s, '|' ORDER BY s)) FROM idx;
```

## Apêndice C: pós-verificações (SQL Editor, somente leitura)

```sql
-- [Q1] Revisão Alembic (esperado: 1 linha, e4c004a26b01)
SELECT version_num FROM public.alembic_version;

-- [Q2] Coluna (esperado: integer | 0 | NO)
SELECT data_type, column_default, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'usuario' AND column_name = 'geracao_autorizacao';

-- [Q3] CHECK (esperado: CHECK ((geracao_autorizacao >= 0)) | true)
SELECT pg_get_constraintdef(oid) AS definicao, convalidated
  FROM pg_constraint
 WHERE conrelid = 'public.usuario'::regclass AND conname = 'ck_usuario_geracao_autorizacao';

-- [Q4] Usuários por perfil/estado: totais por role iguais ao [P5]; CLIENTE ativo=true
--      diminui exatamente o número de linhas ativo=true listadas no [P4]
SELECT role, ativo, count(*) AS usuarios
  FROM public.usuario GROUP BY role, ativo ORDER BY role, ativo;

-- [Q5] Consistência do UPDATE (esperado: 0 | 0 | ids iguais aos do [P4])
SELECT count(*) FILTER (WHERE u.role = 'CLIENTE' AND e.deletado_em IS NOT NULL
                          AND (u.ativo OR u.geracao_autorizacao <> 1)) AS inconsistentes_lixeira,
       count(*) FILTER (WHERE u.geracao_autorizacao <> 0
                          AND NOT (u.role = 'CLIENTE' AND e.deletado_em IS NOT NULL)) AS geracao_fora_do_alvo,
       array_agg(u.id_usuario ORDER BY u.id_usuario) FILTER (WHERE u.geracao_autorizacao = 1) AS ids_geracao_1
  FROM public.usuario u
  LEFT JOIN public.empresa e ON e.id_empresa = u.id_empresa;

-- [Q6] Linhas por tabela: repetir o bloco [P6] das pré-verificações e comparar.
--      usuario e alembic_version devem ter o MESMO total; as demais podem crescer
--      porque o app volta a gravar logo após o COMMIT (informativo, não reverter).

-- [Q7] Locks remanescentes em public.usuario (esperado: nenhuma linha com granted=false)
SELECT l.pid, l.mode, l.granted, a.state
  FROM pg_locks l JOIN pg_stat_activity a ON a.pid = l.pid
 WHERE l.locktype = 'relation' AND l.relation = 'public.usuario'::regclass
   AND l.pid <> pg_backend_pid();
```
