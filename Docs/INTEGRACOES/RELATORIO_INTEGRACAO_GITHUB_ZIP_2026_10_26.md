# Relatório de integração: GitHub × ZIP local do NEXO (26/10/2026)

Conciliação das duas linhas de desenvolvimento do **NEXO: Faturamento Inteligente**: a `main` do repositório oficial e o projeto local recebido em ZIP. Inventário arquivo a arquivo no anexo [INVENTARIO_COMPARATIVO_ZIP_MAIN_2026_10_26.md](INVENTARIO_COMPARATIVO_ZIP_MAIN_2026_10_26.md).

**Classificação final: INTEGRADA À MAIN E VALIDADA** (pelo CI; não homologada nem confirmada em produção). Ao publicar os commits, a classificação era "commits publicados, merge pendente"; o proprietário fez o merge do PR #24 em seguida (seção 18.3). Justificativa na seção 19.10.

---

## 19.1 Identificação

| Item | Valor |
|---|---|
| Projeto | NEXO: Faturamento Inteligente (Flask, SQLAlchemy, Flask-Migrate/Alembic, PostgreSQL/Supabase, Render) |
| Data | 26/10/2026 |
| Repositório | `https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render` |
| Branch inicial | `main` |
| SHA inicial da `main` | `94e9b6ae4e2fb3d6582301cdfc3dd4397b4fdbb2` (merge do PR #23), **confirmado** com `git ls-remote` e pela API do GitHub; igual ao SHA da auditoria anterior. CI "NEXO Security CI" verde nesse commit (run `40314704876`) |
| Branch de integração | `claude/awesome-pascal-0ho42m`. O nome sugerido (`integracao/nexo-zip-atualizado-20261026`) não foi usado porque esta sessão só tem autorização de push para a branch designada pelo ambiente; o conteúdo e o PR são os mesmos |
| Arquivo ZIP | `Nexo - Faturamento Inteligente(4).zip` (19.189.840 bytes, SHA-256 `bfbd2dadc0e3cc1ac42ad6cf5b9161e11b7ea274d9a7b5253562cbae619436eb`), pasta raiz `Nexo - Faturamento Inteligente/`, 272 arquivos, sem `.git` |
| Base real do ZIP | Commit `ff8c2d8` da `main` (merge do PR #20), comprovado por conteúdo: 241 arquivos iguais (167 idênticos + 74 só EOL) e nenhum ausente. O commit `faa59d9` citado no comentário do ZIP não aparece em nenhuma branch nem PR deste repositório |
| Executor | Claude Code (sessão em nuvem) |

## 19.2 Inventário comparativo

Comparação de **conteúdo**, normalizando CRLF/LF, entre a `main` atual e o ZIP (método e lista completa no anexo).

| Classificação | Arquivos |
|---|---:|
| Idênticos | 167 |
| Equivalentes (diferença somente de quebra de linha: `main` CRLF × ZIP LF) | 74 |
| Modificados (todos "alterado no ZIP"; 0 alterados no GitHub ou nas duas linhas desde a base) | 17 |
| Exclusivos do ZIP | 14 |
| Exclusivos do GitHub (`main`) | 1 (`RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`) |
| Exclusivos de outras branches | 0 caminhos novos. A única branch com conteúdo fora da `main` é `feature/reestruturacao-comercial-nexo` (PR #22), que altera `.gitignore` e cria um `00_02_PROTECAO_BANCO_MIGRACOES.md` **diferente** do que está no ZIP |

Os números coincidem com a referência da auditoria anterior (167 / 74 / 17 / 14 / 1), agora recalculados. **Total: 273 caminhos; 31 com diferença real de conteúdo** (17 modificados + 14 exclusivos do ZIP), mais o arquivo exclusivo do GitHub e as 2 divergências do PR #22.

Os 74 arquivos equivalentes **não foram tocados**: a `main` usa CRLF neles e a cópia local foi convertida para LF. Nos arquivos modificados que usam CRLF no repositório (`blueprints/auth.py`, `notifications.py`, `templates/admin/empresa_form.html`), a alteração foi aplicada preservando CRLF, para o diff mostrar só as linhas realmente mudadas.

## 19.3 Funcionalidades integradas

### O que existia no GitHub e não no ZIP

- `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md` (PR #23): diagnóstico do HTTP 500 no login. **Preservado sem alteração.**
- Etapa 0.2 do PR #22 (`feature/reestruturacao-comercial-nexo`, não integrada à `main`): documento `00_02_PROTECAO_BANCO_MIGRACOES.md` (versão GitHub) e regras de `.gitignore` para dumps e chaves. **Trazida para a linha da `main` por merge** (commits originais `49b07d0` e `33881a8` preservados).
- Todo o restante do GitHub (NexoBot Advanced 2.0, landing COM-001, vídeo, SEC-001 a SEC-006B, backup do PR #6) já estava na base do ZIP e continua igual.

### O que existia no ZIP e não no GitHub

| Funcionalidade | Situação |
|---|---|
| **NEXO-AJ-06.1**: bloqueio de empresas CANCELADAS | Integrada (Grupo A) |
| **Etapa 0.2A**: verificador de backup, testes e documentação de operação | Integrada e conciliada com o PR #22 (Grupo B) |
| **NEXO-AJ-00** e controle dos prompts (`Docs/AJUSTES_NEXO_2026/`), mapa de prompts | Integrados como registro histórico, com nota de integração (Grupo C) |
| Insumos de identidade visual e regras comerciais de 25/10/2026 | Integrados; a captura de tela 03 só na versão redigida (Grupo C) |

### O que foi preservado, modificado, acrescentado e não integrado

- **Preservado:** toda a `main` (nenhum arquivo removido; os 74 equivalentes intactos), o relatório do incidente, os commits do PR #22, o workflow de CI (comando protegido inalterado), dependências e migrações.
- **Modificado:** os 17 arquivos alterados no ZIP receberam exatamente o conteúdo do ZIP (diferenças conferidas linha a linha), com a convenção de quebra de linha do repositório. Depois da revisão adversarial, um commit próprio (`b37e4d5`) fez ajustes pequenos: o rótulo de log "cancelamento" passou a "troca de status" em `empresa_editar` (a revogação também ocorre na reativação); três registros do NexoBot passaram a citar em `fontes` os arquivos que implementam o bloqueio (regra editorial de `nexobot/saber/modelo.py`); e foram acrescentadas notas de remissão em documentos que ficariam desatualizados (`Docs/NEXOBOT_ADVANCED.md`, `PREPARACAO_RENDER.md`, `OPERACAO_BACKUP_RESTAURACAO.md`, os dois `00_02`, os documentos AJ e o README dos insumos).
- **Acrescentado:** 14 arquivos exclusivos do ZIP (13 com o mesmo conteúdo, ou com nota de integração e anonimização nos documentos; o `03` só como versão redigida), o `00_02` do PR #22 com nome próprio e este relatório com seu anexo.
- **Conciliado:** `.gitignore` = união exata das regras do ZIP e do PR #22 (nenhum arquivo versionado passou a ser ignorado: `git ls-files -ci --exclude-standard` vazio). O `00_02` virou dois arquivos: a versão 0.2A (ZIP) ficou no caminho canônico, porque é a citada por seção (B.1, E15, G, G.10, H, K) em `OPERACAO_BACKUP_RESTAURACAO.md`, `PREPARACAO_RENDER.md` e `Docs/AJUSTES_NEXO_2026/`; a versão 0.2 do PR #22 foi preservada com conteúdo original em `00_02_PROTECAO_BANCO_MIGRACOES_ETAPA_0_2_PR22.md`. As duas receberam nota de remissão.
- **Não integrado:** a captura original `03_telas_atuais_marca_portal_admin_login.png` (mostra razão social, CNPJ, nomes de arquivos, valores financeiros, totais do painel ADMIN e uma URL; o próprio relatório AJ-00 pede confirmação antes de compartilhá-la). Os pontos de reversão e evidências citados nos relatórios AJ (`C:\ADS\...\Backups_NEXO\`, `evidencias\`) não estavam no ZIP. Nenhuma funcionalidade futura foi desenvolvida.

## 19.4 Arquivos modificados

| Arquivo | Origem | Alteração | Justificativa | Teste |
|---|---|---|---|---|
| `session_security.py` | ZIP (AJ-06.1) | `STATUS_CONTA_SEM_ACESSO` e `condicoes_empresa_acessivel()`; `usuario_pode_acessar` passa a negar CANCELADA | Critério único para todas as vias de acesso | `test_cancelled_company_security`, `test_session_revocation_security` |
| `company_security.py` | ZIP (AJ-06.1) | `STATUS_CONTA` e `aplicar_status_conta()` (revoga ao entrar ou sair de CANCELADA) | Revogação transacional com a ordem de locks da lixeira | `test_cancelled_company_security`, `test_cancelled_company_postgresql` |
| `blueprints/admin.py` | ZIP (AJ-06.1) | Edição valida o status, recusa formulário desatualizado, revoga e desconecta após o COMMIT; empresa nova CANCELADA sem token; aviso na restauração; helpers de revogação extraídos da lixeira | Impedir reativação silenciosa e aplicar a revogação | `test_cancelled_company_security`, `test_company_restore_security` |
| `blueprints/auth.py` (CRLF) | ZIP (AJ-06.1) | CAS da troca de senha usa o critério único | Fechar a corrida token → cancelamento | `test_cancelled_company_security`, `test_auth_tokens_security` |
| `notifications.py` (CRLF) | ZIP (AJ-06.1) | Notificações por empresa não criadas para CANCELADA | Mesma regra da lixeira | `test_cancelled_company_security` |
| `templates/admin/empresa_form.html` (CRLF) | ZIP (AJ-06.1) | Campo oculto `status_conta_exibido` (sem mudança visual) | Detectar formulário desatualizado | `test_cancelled_company_security` |
| `nexobot/saber/administracao.py`, `empresas_planos.py`, `uploads.py` | ZIP (AJ-06.1) | Textos sobre conta cancelada | A base afirmava que CANCELADA mantinha acesso | Suítes `test_nexobot_*` |
| `tests/test_company_restore_security.py` | ZIP (AJ-06.1) | CANCELADA passa a esperar acesso negado | O teste antigo travava a falha | Próprio |
| `tests/test_cancelled_company_security.py` | ZIP (novo) | 30 testes (login, sessão, URL, API, Socket.IO, tokens, notificações, formulário) | Cobertura da AJ-06.1 | Próprio |
| `tests/test_cancelled_company_postgresql.py` | ZIP (novo) | Ensaio em PostgreSQL descartável (20 checagens; opt-in por `NEXO_TEST_POSTGRES_BIN`) | Locks reais e rollback | Próprio |
| `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_06_1_PARA_CHATGPT.md` | ZIP (novo) | Relatório da AJ-06.1 + nota de integração | Documentação correspondente | — |
| `.gitignore` | ZIP + PR #22 | União: SQLite WAL/journal (ZIP) + dumps e chaves (PR #22) | Prevenção de vazamento | `git ls-files -ci --exclude-standard` vazio |
| `scripts/verificar_prontidao_backup.py` | ZIP (0.2A) | `locate_tool` (só diretórios absolutos do PATH; no Windows só `.exe`); `pg_restore --list` pela entrada padrão; falha em `--version` = indisponível | Evitar executável plantado e caminho ANSI | `test_backup_readiness`, `test_backup_restore` |
| `tests/test_backup_readiness.py`, `tests/test_backup_restore.py` | ZIP (0.2A) | Cobertura das regras acima; `not_executed` só por recusa de plataforma e reprovado no Linux | Não contar verificação pulada como aprovada | Próprios |
| `Docs/OPERACAO_BACKUP_RESTAURACAO.md`, `Docs/PLANO_PUBLICACAO_SEGURA.md`, `Docs/PREPARACAO_RENDER.md` | ZIP (0.2A) | Head `e4c004a26b01`, limites do migrador de arquivos, ACL no Windows, RLS no restore, `DIRECT_URL` via Session pooler, roteiro com Auto-Deploy bloqueado antes de migrar; caminho local anonimizado | Atualização operacional | Revisão documental |
| `Docs/REESTRUTURACAO_COMERCIAL/00_02_PROTECAO_BANCO_MIGRACOES.md` | ZIP (0.2A) | Conteúdo da Etapa 0.2A + nota de remissão | Versão citada pelos demais documentos | — |
| `Docs/REESTRUTURACAO_COMERCIAL/00_02_PROTECAO_BANCO_MIGRACOES_ETAPA_0_2_PR22.md` | PR #22 | Conteúdo original da Etapa 0.2 + nota de remissão | Preservar o trabalho do GitHub | — |
| `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md` | ZIP | Mudança de metodologia, situação por ambiente, histórico v4; caminhos anonimizados | Pedido do proprietário (Etapa 8) | — |
| `Docs/AJUSTES_NEXO_2026/NEXO_AJ_00_BASELINE.md`, `RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` | ZIP | Nota de integração (origem da indicação do repositório oficial, correção de CANCELADA pela AJ-06.1, captura 03 só redigida); caminhos com o nome do usuário anonimizados; conta GitHub de terceiro e projetos sem relação generalizados | Registro histórico com minimização de dados pessoais | — |
| `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md` | ZIP | Sem alteração (SHA-256 `b59e9d72…`) | Referência citada por hash | — |
| `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/` (01, 02, 04, 05, README, 03 redigido) | ZIP | Imagens sem alteração; 03 só redigido; README com nota | Referências do proprietário | Inspeção visual e de metadados |
| `Docs/INTEGRACOES/*` | Integração | Este relatório e o inventário | Etapa 15 | — |
| `blueprints/admin.py` (ajuste) | Revisão | Rótulo do aviso de desconexão: "troca de status" | A revogação ocorre ao entrar e ao sair de CANCELADA | `test_cancelled_company_security` |
| `nexobot/saber/*.py` (ajuste) | Revisão | `fontes` incluem `session_security.py`, `company_security.py` e `notifications.py` | Regra editorial "todo registro cita em `fontes` os arquivos que o embasam" | `test_nexobot_saber` e demais `test_nexobot_*` |
| `Docs/NEXOBOT_ADVANCED.md` | Revisão | Atualização da observação "CANCELADA continua entrando no portal" | Afirmação ficou falsa com a AJ-06.1 | — |
| `Docs/PREPARACAO_RENDER.md`, `Docs/OPERACAO_BACKUP_RESTAURACAO.md` (ajuste) | Revisão | Remissão ao relatório do PR #23 para a migração `e4c004a26b01` | O roteiro genérico da 0.2A é anterior ao incidente | — |

## 19.5 Regras de negócio

| Regra | Situação após a integração | Evidência |
|---|---|---|
| ADMIN | Mantém todas as permissões; inclusive lista, edita e consulta empresas CANCELADAS | `usuario_pode_acessar` retorna antes de consultar a empresa para ADMIN; `bloquear_usuarios_empresa` filtra `role = 'CLIENTE'`; testes `test_j_*` e checagem `admin_kept` no PostgreSQL |
| CLIENTE | Acessa somente a própria empresa | Testes de isolamento existentes e `other_company_kept` |
| ATIVA | Comportamento inalterado | `active_login` (PostgreSQL); suíte completa |
| SUSPENSA | Comportamento inalterado (acesso mantido; só novas análises bloqueadas). Nenhuma regra futura (14 dias, 3 meses, histórico pago) foi antecipada | `suspended_keeps_generation`, `suspended_keeps_session`; teste de restauração com SUSPENSA = 200 |
| CANCELADA | CLIENTE negado em login, sessão antiga, URL direta, APIs, Socket.IO, tokens de senha, notificações, uploads, PDFs e dashboards; entrar ou sair de CANCELADA revoga sessões | `test_cancelled_company_security` (30), `test_cancelled_company_postgresql` (20 checagens) |
| Lixeira | Continua independente: CANCELADA não grava `deletado_em`; restaurar uma empresa CANCELADA mantém o bloqueio | `test_k_*`; aviso em `empresa_restaurar` |
| Isolamento entre empresas | Preservado | `company_isolation` no ensaio de backup; testes de IDOR existentes |
| Autorizações e sessões | `geracao_autorizacao` (SEC-004) continua a base da revogação; nenhuma coluna nova | Sem migração nova; `alembic heads` = `e4c004a26b01` |

## 19.6 Testes

Ambiente local: contêiner Linux, Python 3.12 (mesma versão do CI) com `requirements-dev.txt`, PostgreSQL 16 local usado só por clusters descartáveis criados pelos próprios testes, Chromium do Playwright para os testes de navegador, as mesmas variáveis sintéticas do workflow (`DATABASE_URL=sqlite:///:memory:`, chaves vazias), usuário sem privilégios (o `initdb` recusa root) e nenhuma credencial real.

| Execução | Comando | Testes | Aprovados | Falhas | Erros | Ignorados |
|---|---|---:|---:|---:|---:|---:|
| `main` `94e9b6a` (linha de base) | `python -B -m unittest discover -s tests -t . -v` | 599 | 599 | 0 | 0* | 0 |
| Integração `6326999` (local) | mesmo comando (protegido do CI), com navegador e `NEXO_TEST_POSTGRES_BIN` | **638** | **638** | 0 | 0 | 0 |
| Integração `6326999` (local), job PostgreSQL | `tests.postgresql_auth_tokens` / `_session_revocation` / `_company_restore_security` / `_company_restore_migration` / `_etl_resource_security` | 37 / 41 / 15 / 6 / 9 = **108** | 108 | 0 | 0 | 0 |
| Grupo A isolado | AJ-06.1 + restauração + revogação + tokens + ensaio PostgreSQL AJ-06.1 | 135 | 135 | 0 | 0 | 0 |
| Grupo B isolado | `tests.test_backup_readiness` + `tests.test_backup_restore` (com o ensaio PostgreSQL) | 26 | 26 | 0 | 0 | 0 |
| Ajustes da revisão `b37e4d5` | todas as `tests.test_nexobot_*` (com navegador) + segurança de empresas + ensaio PostgreSQL AJ-06.1 | 242 | 242 | 0 | 0 | 0 |
| **CI do GitHub** no PR, commit `6326999` (run `40321393139`) | workflow "NEXO Security CI" | `security-sqlite-browser`: 638 OK; `security-postgresql`: OK | — | 0 | 0 | — |

\* Na primeira execução da linha de base, 6 erros em `tests.test_nexobot_api.ProvedorHttpRealTests` vieram do ambiente: `SSL_CERT_FILE` apontava para um certificado do proxy ilegível pelo usuário de teste. Sem essa variável, o módulo passou (46 OK), e a integração já rodou sem ela. Não é falha de código.

Os 39 testes a mais na integração são os 30 de `test_cancelled_company_security`, o ensaio `test_cancelled_company_postgresql` e os 8 novos dos dois arquivos de backup. Os 599 testes da `main` continuam existindo e passando.

**Ensaios PostgreSQL** (local e CI): o de backup e restauração aprovou 17 verificações (`migrations`, `custom_dump`, `sha256`, `pg_restore_list` pela entrada padrão, `readiness_cli`, `invalid_archive_rejected`, `restore`, `all_rows`, `relationships`, `binary_files`, `sequences`, `foreign_keys`, `etl`, `health`, `csrf_login`, `dashboard`, `company_isolation`), com `not_executed: []`, 15 tabelas, 4 uploads, 5 arquivos e `production_access: false`. O da AJ-06.1 aprovou 20 verificações (login ativo, SUSPENSA mantém geração e sessão, rollback, locks `FOR SHARE`, geração incrementada, login e sessão antiga de CANCELADA negados, outra empresa e ADMIN preservados, reativação revoga de novo e novo login funciona), com `production_access: false`.

**Autenticação (16.3):** login ADMIN e CLIENTE, acesso de ATIVA e SUSPENSA, bloqueio de CANCELADA, sessão antiga, tokens de senha, revogação, URL direta, Socket.IO e isolamento entre empresas estão cobertos pelas suítes acima.

**Regressão (16.4):** NexoBot (incluindo navegador e as 1.023 perguntas de roteamento conferidas pela revisão), landing e vídeo (navegador), uploads, ETL (incluindo limites e equivalência financeira), PDF, notificações, chamados e administração de empresas passaram na suíte completa.

**Validação de código (16.5):** `py_compile` dos arquivos alterados; nenhum import novo de terceiros; `alembic` com cadeia linear de 8 revisões e head única `e4c004a26b01` (nenhuma migração alterada ou criada); `requirements*.txt` e o workflow sem alteração; diffs conferidos linha a linha contra o ZIP; varredura de segredos (19.8).

**Não executado:** nada contra Supabase ou Render; nenhum teste de carga; nenhum teste em Windows. A CI dos commits posteriores a `6326999` (ajustes da revisão e este relatório) aparece no PR.

## Revisão adversarial

Antes da publicação, cinco revisores independentes analisaram as alterações do ZIP, cada um com um foco. Um verificador adversarial reexaminou cada achado de severidade média ou maior. No total foram 8 agentes, nenhum com erro.

| Foco | Resultado |
|---|---|
| Cobertura de acesso da AJ-06.1 (todas as vias) | Nenhum achado crítico, alto ou médio. Todas as rotas, APIs, Socket.IO, tokens e notificações passam pelo critério central; ADMIN, SUSPENSA, lixeira e isolamento preservados |
| Transações e concorrência da AJ-06.1 | Nenhum defeito. Ordem de locks Empresa → Usuario igual à da lixeira; rollback não revoga; lógica de formulário desatualizado correta em todas as combinações; nenhuma dependência nova de schema; 5 mutantes detectados |
| Regressões sobre a `main` | Nenhuma regressão funcional. Landing, vídeo, NexoBot 2.0 e SEC-002 a SEC-006 idênticos; 1.023 perguntas do NexoBot com o mesmo roteamento |
| Backup 0.2A | Nenhum achado crítico, alto ou médio. `locate_tool` funciona com o wrapper do Debian/Ubuntu; `pg_restore --list` pela entrada padrão validado; nenhuma asserção de segurança enfraquecida |
| Documentação e `.gitignore` | A 0.2A deve ficar no caminho canônico (cerca de 20 referências por seção ou linha). União do `.gitignore` correta e sem ignorar arquivos versionados. Os 3 achados médios (origem da indicação do repositório oficial, links para este relatório ainda não commitado, divergências de procedimento de backup real) foram **confirmados e rebaixados a baixo** pelos verificadores, e todos foram tratados em `b37e4d5` ou neste commit |

Achados tratados nesta integração: preservar o CRLF dos 3 arquivos (feito desde o início), preservar o relatório do PR #23, anonimizar o nome de usuário, as notas de remissão, as `fontes` do NexoBot, o rótulo do log, a posição das notas (para não deslocar as referências de linha) e a remissão ao procedimento do PR #23. Os achados que não foram corrigidos são comportamento anterior ou pertencem a etapas futuras; estão em 19.9.

## 19.7 GitHub

| Item | Valor |
|---|---|
| Branch publicada | `claude/awesome-pascal-0ho42m`, criada a partir de `94e9b6a`, sem force push |
| Commit 1 | `9435ec952f6b12b01726db6defa3f7f731ac9831`: fix(auth): integrar bloqueio de empresas canceladas NEXO-AJ-06.1 |
| Merge do PR #22 | `59f3de113ac5fef9e7fa0b1b50738418e54d3135`: traz os commits originais `49b07d0` e `33881a8` |
| Commit 2 | `52afb75d8e6bc06150299f55b7f69a2106547287`: chore(backup): conciliar verificacoes de backup e documentacao 0.2A |
| Commit 3 | `6326999e036b3a1c0eeac9fe7be20f11a3f83e89`: docs(nexo): integrar planejamento local e referencias do projeto |
| Commit 4 | `b37e4d507f684766f72a12a23b523af96e5e3363`: fix(integracao): aplicar ajustes da revisão adversarial |
| Commit 5 | Este relatório e o inventário (commit seguinte a `b37e4d5`; um documento não consegue citar o SHA do próprio commit) |
| Pull Request | [Helio965/Nexo---Faturamento-Inteligente---Render#24](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/24), base `main`, aberto como rascunho |
| Estado | **Integrado (merged)** pelo proprietário (`Helio965`) em 26/10/2026 às 09:38:56 (UTC−3) |
| Merge | `d7eb7e471d938948a23915036960670cd5609bc7` ("Merge pull request #24"), árvore idêntica a `2cf0269` |
| SHA final da `main` | `d7eb7e471d938948a23915036960670cd5609bc7` |

**Organização dos commits.** Os três commits sugeridos foram mantidos, com dois acréscimos justificados:

- o merge do PR #22 entra como commit próprio, porque preserva o histórico original do PR em vez de copiar o conteúdo;
- os ajustes da revisão ficaram separados, para deixar rastreável o que veio do ZIP e o que foi corrigido na integração.

O relatório vai num commit final porque cita os SHAs dos anteriores.

## Implantação: verificação da Etapa 14

| Verificação | Resultado |
|---|---|
| Render ligado à `main` | `render.yaml`: `branch: main`. Estado real do painel **não verificável** daqui (sem acesso ao Render). Também não foi possível verificar **qual repositório** o serviço publica: os documentos locais do ZIP citam `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente`, e o `faa59d9` do comentário do ZIP não existe neste repositório |
| Auto-Deploy | `render.yaml` declara `autoDeployTrigger: 'off'`, mas `Docs/PREPARACAO_RENDER.md:83` e `Docs/RELATORIO_NEXO_SEC006_DEPENDENCIAS.md:162` registram que o proprietário informou Auto-Deploy **ativado** no painel. O próprio `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md` (seção 1.3) atribui o incidente atual a um deploy automático da SEC-004 sem a migração |
| Outro workflow de deploy | Não há: o único workflow é `.github/workflows/nexo-security-ci.yml`, que só testa (`permissions: contents: read`) |
| Alteração de banco automática | Nenhuma: o build (`tools/install_dependencies.py`) não migra; esta integração não cria migração |
| Checks do PR | Run `40321393139` (commit `6326999`): `security-sqlite-browser` **success** (638 testes OK) e `security-postgresql` **success**. A CI dos commits seguintes aparece no PR |

**Conclusão:** não foi possível comprovar que um merge na `main` não provocaria deploy de produção não autorizado, e há registro do proprietário em sentido contrário. Por isso o executor **não fez o merge** (condição 18.2). O merge foi feito depois pelo próprio proprietário (seção 18.3); o estado do Auto-Deploy continua não verificado daqui, e o Render pode ter publicado `d7eb7e4` se ele estiver ativo. Mesmo sem nova dependência de schema, publicar esta versão com o Supabase em `b7c4e2a9f031` manteria o login em HTTP 500.

## 19.8 Segurança

- **Nenhum segredo publicado.** Varredura dos arquivos acrescentados ou alterados (e-mails, URLs, chaves, tokens, strings de conexão, caminhos de usuário): só endereços `@example.invalid` de testes, placeholders de documentação e URLs de documentação oficial. Caminhos `C:\Users\<usuário>` dos relatórios AJ foram anonimizados como `%USERPROFILE%`. A varredura final do diff `94e9b6a..b37e4d5` (33 arquivos) e deste relatório não encontrou chaves (`sk-ant`, `xkeysib`, AWS, GitHub), JWT, chave privada, string de conexão com senha, project ref do Supabase ou domínio do Render. `git grep` não encontra o nome do usuário do Windows em nenhum arquivo do repositório.
- **Nenhum dado real publicado:** a captura de tela com dados de empresa e totais do painel só entrou redigida; o ZIP não tinha `.env`, banco, dump, log nem ambiente virtual.
- **Nenhum dado de produção alterado.** Nenhuma conexão com o Supabase; os testes usaram apenas SQLite temporário e clusters PostgreSQL 16 descartáveis (socket privado ou loopback), com dados fictícios.
- **Nenhuma migração executada** em banco existente (`flask db upgrade/downgrade/stamp` não foram usados contra nenhum banco real).
- **Nenhum deploy:** nenhum acesso ao Render; o merge na `main` não foi feito.
- **Nenhum histórico apagado:** sem force push, rebase ou reescrita; o PR #22 entrou por merge com os commits originais; nenhuma branch ou PR foi removido.
- **Arquivos do ZIP tratados como não confiáveis:** inspecionados antes de executar; nenhum script do ZIP foi executado a partir da pasta extraída.

## 19.9 Pendências

**Técnicas**
- Migração `e4c004a26b01` no Supabase (incidente HTTP 500) — **não resolvida**, tratada à parte conforme `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`. O funcionamento da AJ-06.1 em produção depende dela.
- Tela própria de conta cancelada (NEXO-AJ-06.3) e transição automática SUSPENSA → CANCELADA (06.2).
- Escritas HTTP já em andamento no instante do cancelamento (registrado na AJ-06.1, seção 14.11, como 07.4).
- E-mails transacionais (`emails._emails_da_empresa`: chamado resolvido, análise publicada) continuam sendo enviados ao contato e aos CLIENTE de empresa CANCELADA ou na lixeira. Isso já ocorria na `main`; a decisão é da 06.4/07.x.
- Reativação feita direto no banco, fora da rota do ADMIN, não incrementa a geração. A 06.2 e os scripts operacionais devem usar `bloquear_empresa` + `aplicar_status_conta`.
- A proteção contra formulário desatualizado depende do campo `status_conta_exibido`. Um POST montado à mão sem esse campo se comporta como na `main`.
- Verificador de backup: reabrir o arquivo para o `--list` pode travar sem timeout se o arquivo for trocado por um FIFO depois do hash. É um endurecimento opcional.
- O teste PostgreSQL da AJ-06.1 roda pelo `discover` no job `security-sqlite-browser`. O workflow protegido não foi alterado para lhe dar um passo próprio.
- O relatório do PR #23 expõe o project ref do Supabase, contra a regra G.14 da 0.2A; isso já estava na `main`. Ele também cita `Docs/PREPARACAO_RENDER.md:81`, frase que após a 0.2A está na linha 83. O relatório foi preservado sem alteração.
- Antes do deploy, contar em produção, somente leitura, as empresas CANCELADAS: os CLIENTE delas perdem o acesso assim que a AJ-06.1 for publicada (comportamento desejado).

**Comerciais**
- Preços Bronze R$ 150, Prata R$ 300, Ouro R$ 650: **não aplicados**; `seed.py` continua com 600/1000/1400 e o valor do banco de produção não foi conferido.
- Contratos (vigência, renovação, histórico) — não implementados.
- SUSPENSA: histórico do período pago, janela de 14 dias para PDFs e prazo de até 3 meses com prorrogação — não implementados (o status SUSPENSA existente não os cumpre).
- Avisos de renovação 7 a 14 dias antes do vencimento — não implementados.
- COM-002 (avaliações e depoimentos) — não desenvolvido; componentes visuais preparados não equivalem à funcionalidade.
- Identidade visual com o cubo NEXO — insumos preservados; substituição da marca é atividade própria.

**Segurança**
- Revisão LGPD completa (NEXO-AJ-07.x).
- Confirmar com o proprietário se a captura 03 original pode ser versionada.

**Infraestrutura**
- Confirmar no painel do Render o estado real do Auto-Deploy e o commit implantado antes de qualquer merge na `main`.
- Backup real do Supabase e restauração isolada (Etapa 0.2A, seção G) — não executados.
- Domínio próprio e DNS — dependem de decisão de infraestrutura.

**Homologação**
- AJ-06.1 em ambiente de homologação com PostgreSQL na revisão `e4c004a26b01`.
- Aprovação humana das entregas NEXO-AJ-00 e NEXO-AJ-06.1 (`CONTROLE_PROMPTS.md`).
- Merge do PR de integração pelo responsável, depois das confirmações acima.

## 18.3 Registro do merge

| Item | Valor |
|---|---|
| Pull Request | [Helio965/Nexo---Faturamento-Inteligente---Render#24](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/24) |
| Quem fez o merge | O proprietário (`Helio965`), depois de marcar o PR como pronto para revisão. O executor não fez o merge |
| Data | 26/10/2026, 09:38:56 (UTC−3) |
| SHA do merge | `d7eb7e471d938948a23915036960670cd5609bc7` (pais `94e9b6a` e `2cf0269`; árvore idêntica ao head `2cf0269`) |
| CI do PR no head final | Run `40324126061` (`2cf0269`): **success**; as runs anteriores do mesmo head foram substituídas pelo `cancel-in-progress` do workflow |
| CI da `main` após o merge | Run `40324156855` (`d7eb7e4`): **success**, com `security-sqlite-browser` (suíte completa, navegador e ensaios PostgreSQL) e `security-postgresql` (os 5 módulos) aprovados |
| Revisão automática do Codex | Concluída no head `2cf0269`, sem achados |
| Arquivos integrados | 35 arquivos (5.854 inclusões, 78 remoções), listados nas seções 19.4 e no anexo |
| Deploy e banco | O executor não fez deploy nem migração. O estado do Render (Auto-Deploy, repositório e commit publicados) não foi verificado. O Supabase continua sem a `e4c004a26b01`, segundo o relatório do PR #23 |

## 19.10 Conclusão

**INTEGRADA À MAIN E VALIDADA** (pelo CI; não homologada nem confirmada em produção).

- As duas linhas de desenvolvimento foram conciliadas sem perda: a `main` foi preservada integralmente, o ZIP foi integrado (AJ-06.1, Etapa 0.2A, documentação e insumos seguros) e o PR #22 entrou com o histórico original.
- O bloqueio de empresas CANCELADAS está integrado e testado: localmente em SQLite e PostgreSQL descartável, e no CI.
- A suíte completa passou localmente (638) e no CI do PR (638), sem regressão conhecida; a revisão adversarial não encontrou defeito bloqueante.
- O executor não fez o merge porque a condição 18.2 de não haver deploy não autorizado não pôde ser comprovada (painel do Render inacessível daqui; registro do proprietário de Auto-Deploy ativado). O proprietário fez o merge em seguida (`d7eb7e4`), e o CI da `main` passou.
- O incidente HTTP 500 do Supabase continua aberto e é tratado à parte. O funcionamento em produção depende da migração `e4c004a26b01`.
- Próximo passo do responsável: conferir no Render se `d7eb7e4` foi publicado (Auto-Deploy) e qual repositório o serviço usa, e conduzir a migração `e4c004a26b01` pelo procedimento do PR #23. Até lá o login em produção continua sujeito ao HTTP 500, e a AJ-06.1 só vale em produção depois disso.
