# NEXO - Faturamento Inteligente | Baseline GitHub para a Reestruturação Comercial

**Etapa 0.1 — Registro da versão atual e preparação do repositório**

Este documento registra o estado do repositório no momento em que a reestruturação
comercial e funcional do NEXO foi iniciada. Ele é a referência contra a qual todas as
etapas seguintes (E1 a E9 e a Etapa 0.2) serão comparadas.

A análise foi exclusivamente documental: leitura do código versionado, dos arquivos de
configuração e da documentação existente, mais comandos Git de consulta. Nenhum arquivo
operacional foi alterado, nenhuma dependência foi instalada, a aplicação não foi
executada, a suíte de testes não foi rodada, nenhum banco foi acessado e nenhum deploy
foi iniciado. Afirmações que dependeriam de execução estão marcadas como tal.

Convenção usada neste documento:

- **Comprovado**: verificado diretamente no código ou no Git, com referência
  `arquivo:linha` ou comando.
- **Requer execução**: comportamento esperado pela leitura do código, mas que só um teste
  de execução, acesso ao banco ou ao painel do Render confirmaria.
- **Documental**: afirmação que consta apenas na documentação do repositório (não foi
  verificada de forma independente nesta etapa).

Nenhum valor de segredo, credencial, e-mail pessoal, telefone ou nome de pessoa é
reproduzido aqui. Quando um dado sensível existe no repositório, registra-se apenas a sua
localização.

---

## A. Identificação

| Item | Valor |
|---|---|
| Projeto | NEXO - Faturamento Inteligente |
| Repositório | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Visibilidade do repositório | Privado (consulta à API do GitHub em 2026-10-24) |
| Branch principal | `main` |
| Branch de desenvolvimento | `feature/reestruturacao-comercial-nexo` |
| Data da verificação | 2026-10-24 |
| Commit de referência (`origin/main`) | `8233c5bddbd1f6c67a4d95c7b0a2a470724738c8` |
| Descrição do commit de referência | `Merge pull request #18` (branch `security/sec-005-etl-resource-limits`), 2026-10-24, 09:02 -03:00 |
| Branch de desenvolvimento criada a partir de | `origin/main` em `8233c5bddbd1f6c67a4d95c7b0a2a470724738c8` |
| Stack principal | Python 3.12 (Render fixa 3.12.10), Flask 3.1.3, SQLAlchemy 2.x (via Flask-SQLAlchemy 3.1.1), Flask-Migrate/Alembic, PostgreSQL (Supabase) em produção e SQLite em desenvolvimento, Gunicorn 23, Bootstrap 5.3.3, Plotly.js 2.35.2, Pandas 3.0.3, ReportLab, Flask-SocketIO |

---

## B. Estado inicial

### B.1 Situação do repositório local (Comprovado)

- O diretório de trabalho corresponde ao repositório oficial: `git remote -v` mostra
  `origin` com fetch e push para o repositório indicado na seção A.
- Git configurado e funcional (`git version 2.43.0`).
- Árvore de trabalho limpa antes da preparação: `git status` sem alterações, sem
  arquivos não rastreados, sem stash (`git stash list` vazio) e sem worktrees adicionais
  (`git worktree list` só mostra o diretório principal). Nenhuma modificação local
  precisou ser preservada ou isolada.
- Após `git fetch origin --prune`, `main`, `origin/main` e `HEAD` apontavam para o mesmo
  commit `8233c5bddbd1f6c67a4d95c7b0a2a470724738c8`. Não há commits locais à frente da
  `main`.
- Não existem tags no remoto (`git ls-remote --tags origin` vazio).
- 210 arquivos rastreados; aproximadamente 12.100 linhas em todos os `.py` rastreados fora
  de `tests/` (inclui `migrations/`, `tools/`, `scripts/` e `test_etl.py` da raiz; só o código
  da aplicação soma cerca de 10.800) e 10.400 linhas de Python em `tests/`
  (`git ls-files` + `wc -l`).

### B.2 Situação das branches (Comprovado)

- `main` é a branch de integração principal (a `security/sec-002-homologacao` serviu,
  pontualmente, de branch intermediária para as PRs #11 e #12 antes de ser mesclada pela
  PR #10). No remoto existem 18 branches além dela, todas já integradas via Pull Request
  (PRs #1 a #18, todas com merge commit na história da `main` entre 2026-10-19 e
  2026-10-24; a ausência de PR aberta foi verificada por consulta à API do GitHub em
  2026-10-24, não pelo Git local). Há ainda 1 branch apenas local (ver abaixo):
  - `security/*` (8): `fix-pdf-reportlab-sec001`, `sec-002-password-tokens`,
    `sec-002-homologacao`, `sec-003-session-revocation`, `sec-004-safe-company-restore`,
    `sec-005-etl-resource-limits`, `sec-006-dependency-updates`,
    `sec-006b-supply-chain-hardening`;
  - `seguranca/01-backup-restauracao` (1);
  - `docs/*` (2): `security-integration-evidence`, `sec-006-publication-evidence`;
  - `feature/*` (2): `video-demo-loop-sem-download`,
    `video-audio-visibilidade-tela-cheia`;
  - `fix/player-demo-loop-audio-visibilidade` (1);
  - `infra/nexo-security-ci` (1);
  - `claude/*` (3 remotas): `blissful-keller-72pucy`, `busy-davinci-dwcngt`,
    `epic-galileo-klfd53` (todas mescladas). Além delas existe a branch **apenas local**
    `claude/serene-mendel-nhd2jn` (branch de sessão da ferramenta de apoio, criada a
    partir de `HEAD`, apontando para o próprio commit de referência, sem commits próprios
    e sem correspondente em `origin` após `git fetch --prune`).
- **Não existia** nenhuma branch, local ou remota, destinada à reestruturação comercial
  (nenhuma com `reestrutura`, `comercial` ou equivalente). Por isso a branch
  `feature/reestruturacao-comercial-nexo` foi criada nova, a partir de `origin/main`,
  sem conflito com trabalho anterior e sem necessidade de sufixo identificador.
- A branch foi criada sem vínculo de rastreamento com `main`
  (`git switch --no-track -c ...`), para que um `git push` sem destino explícito não
  atinja a branch principal.

### B.3 Modificações locais (Comprovado)

Nenhuma. Nada foi descartado, sobrescrito, incluído em stash ou movido para worktree.

### B.4 Histórico recente relevante (Comprovado via `git log`)

49 commits ao todo. Marcos pelo histórico de primeiro pai da `main`:

| Data | Commit | Evento |
|---|---|---|
| 2026-10-18 | `3024891` | Initial commit |
| 2026-10-19 | `fc63708` | Publicação do NEXO preparado para hospedagem no Render |
| 2026-10-19 | PR #1 | Correção do roteiro de migração e deploy manual |
| 2026-10-20 | PRs #2 a #5 | Vídeo promocional e player de demonstração na landing |
| 2026-10-21 | PR #6 | Backup, restauração e plano de recuperação (Security 01/25) |
| 2026-10-21 | PR #7 | NexoBot Advanced (NLP local, navegação segura, busca no Guia) |
| 2026-10-21 | PR #8 | SEC-001: marcação não confiável nos PDFs |
| 2026-10-21 | PRs #9 e #10 (a #10 traz as PRs #11 e #12, mescladas antes em `security/sec-002-homologacao`) | SEC-002 (tokens de senha e homologação), SEC-003 (revogação de sessões), CI de segurança |
| 2026-10-23 | PRs #13 a #16 | Evidências de integração; SEC-006/006B (dependências e cadeia de suprimentos) |
| 2026-10-23 | PR #17 | SEC-004: restauração segura de empresas (inclui migração `e4c004a26b01`) |
| 2026-10-24 | PR #18 | SEC-005: limites de recursos do ETL — **commit de referência** |

Observações sobre o histórico:

- Dos últimos nove merges de primeiro pai (PRs #8 a #18), sete são correções de segurança
  (SEC-001, SEC-002, SEC-004, SEC-005, SEC-006 e SEC-006B; SEC-003 e o CI de segurança
  entraram pela PR #10) e dois são apenas de documentação (PRs #13 e #15). A última
  mudança de schema integrada à `main` é a migração `e4c004a26b01` (PR #17), cuja
  aplicação em produção **não está confirmada** pela documentação
  (`Docs/RELATORIO_NEXO_SEC005_ETL_SEGURO.md:16-17`,
  `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md`).
- Nenhum arquivo `.env`, banco `.db`/`.sqlite` ou dump foi adicionado em qualquer ponto do
  histórico (`git log --all --diff-filter=A --name-only`). O único arquivo de ambiente
  versionado é `.env.example`, cujos campos de segredo estão vazios em todo o histórico.

---

## C. Arquitetura identificada

### C.1 Inventário dos principais componentes

| Caminho | Papel | Observação |
|---|---|---|
| `app.py` | Application factory `create_app()`; entrypoint de desenvolvimento (`python app.py`) | Registra 5 blueprints, 5 rotas diretas (`/`, `/como-aderir`, `/healthz`, `/healthz/db`, `/midia/<chave>`), 3 `before_request`, 1 `after_request`, 2 `errorhandler`, 1 `context_processor`, ProxyFix condicional |
| `wsgi.py` | Entrypoint de produção (`gunicorn ... wsgi:app`) | `create_app(os.environ.get("FLASK_ENV", "production"))` |
| `config.py` | Classes `Config`, `DevelopmentConfig`, `ProductionConfig`; resolução das URIs de banco | Só existem os ambientes `development` e `production` (`config.py:209-212`) |
| `extensions.py` | Instâncias compartilhadas: `db`, `login_manager`, `migrate`, `mail`, `socketio`, `csrf`, `limiter` | `Base` declarativa sem `naming_convention` |
| `models.py` | 14 modelos SQLAlchemy 2.x | Ver C.4 |
| `migrations/` | Flask-Migrate/Alembic: `env.py`, `alembic.ini`, `script.py.mako`, 8 revisões em `versions/` | Ver C.5 |
| `blueprints/auth.py` | Autenticação (`/auth`, 6 rotas) | Ver C.6 |
| `blueprints/admin.py` | Painel administrativo (`/admin`, 20 rotas) | Ver C.7 |
| `blueprints/cliente.py` | Portal do cliente (`/cliente`, 8 rotas) | Ver C.8 |
| `blueprints/notificacoes.py` | Sininho de notificações (`/notificacoes`, 2 rotas) | |
| `blueprints/api.py` | API JSON (`/api`, 1 rota: `POST /api/suporte-bot`) | Única rota de API |
| `session_security.py`, `company_security.py`, `log_security.py` | Revalidação de sessão por request, lixeira transacional de empresas, redação de tokens em logs | Resultado das SEC-002/003/004 |
| `etl_processor.py`, `etl_inputs.py`, `etl_limits.py`, `etl_runtime.py`, `etl_uploads.py`, `etl_worker.py` | Motor ETL e seu isolamento em subprocesso | Ver C.9 |
| `insights.py`, `ai_devolutiva.py`, `pdf_export.py` | Semáforos de risco, devolutiva por IA (Anthropic) com fallback local, exportação PDF (ReportLab) | |
| `notifications.py`, `realtime.py`, `emails.py` | Notificações in-app após commit, Socket.IO autenticado, e-mails transacionais (Brevo HTTPS ou SMTP) | |
| `storage.py` | Armazenamento de arquivos no banco (`arquivo_armazenado`, BYTEA) com cache temporário em disco | Referências `db:<chave>` |
| `nexobot/` (14 módulos) + `suporte_bot.py` | Assistente de navegação e suporte, local, sem rede por padrão | Ver C.10 |
| `templates/` (38 arquivos) | Jinja2: `landing.html`, `como_aderir.html`, `base.html`, `_macros.html`, `_auditoria.html`, `_chat.html`, `erro_simples.html`, `auth/` (6), `admin/` (13), `cliente/` (7), `emails/` (5) | |
| `static/` | `css/landing.css`, `css/nexo.css`, `js/landing.js`, `js/landing-video.js`, `js/nexobot.js`, `js/nexo.js` (vazio, 0 bytes, não referenciado), `img/nexo-logo.jpeg`, `video/` (MP4 de ~12 MB, poster JPG/PNG, GIF) | |
| `seed.py`, `seed_guia.py`, `init_db.py`, `criar_cliente_demo.py`, `migrar_arquivos_para_db.py` | Scripts operacionais | Ver riscos em F |
| `schema_nexo_mvp_v4.sql`, `Docs/schema_nexo_mvp_v4 (1).sql` | DDL SQLite históricos, **divergentes** dos modelos atuais | Ver C.5 |
| `tests/` (41 arquivos) | Suíte `unittest` | Ver C.11 |
| `.github/workflows/nexo-security-ci.yml` | CI de segurança | Ver C.11 |
| `render.yaml`, `tools/install_dependencies.py` | Blueprint do Render e instalador verificado de dependências | Ver D |
| `tools/nexo-motion/` | Projeto Remotion (React/TypeScript) que gerou o vídeo demo | Não entra no build do Render |
| `tools/measure_etl_resources.py`, `scripts/verificar_prontidao_backup.py` | Ferramentas de medição do ETL e de prontidão de backup | Não tocam a aplicação nem o banco |
| `Docs/` (26 arquivos) | Relatórios de segurança, operação de backup, preparação do Render, CI, NexoBot, DER (`.docx`) | Vários estão desatualizados quanto à head de migração e ao comando de build (ver F) |
| `README.md`, `NEXO_RENDER_PROGRESS.md`, `RELATORIO_FINAL_PARA_CHATGPT.md`, `LICENSE` | Documentação de raiz | README com identidade acadêmica; LICENSE MIT |
| `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore` | Dependências (18 diretas fixadas com `==`), nomes de variáveis, exclusões | |

### C.2 Backend (Comprovado)

- Padrão Application Factory. `create_app(config_name)` (`app.py:60-348`) carrega a classe
  de configuração, valida produção, gera um `BOOT_ID` aleatório por processo, inicializa
  as extensões, registra blueprints e hooks e aplica `ProxyFix` quando `PROXY_FIX_HOPS > 0`.
- Validações de produção (`app.py:76-102`): `SECRET_KEY` obrigatória e diferente do
  placeholder de desenvolvimento; `DATABASE_URL` obrigatória; `DIRECT_URL` obrigatória
  quando `NEXO_DB_DIRECT=1`; backend obrigatoriamente `postgresql`. Há testes para isso
  (`tests/test_configuration_deploy.py`).
- Segurança transversal: CSRF global (Flask-WTF, sem `csrf.exempt` no código da
  aplicação); rate limit explícito só em `POST /auth/login` (10/min),
  `POST /auth/recuperar-senha` (5/min) e `POST /api/suporte-bot` (30/min por usuário),
  armazenamento padrão `memory://`; guard de caractere NUL; guard de primeiro acesso;
  cabeçalhos pontuais (`no-referrer`/`no-store` nas rotas de token, CSP `sandbox` em
  `/midia`, `no-store`/`nosniff` em `/api`). **Não há** CSP, HSTS ou
  `X-Frame-Options` globais (`app.py:133-139, 271-276`; `blueprints/api.py:42-47`).
- Rotas por módulo: `auth` 6, `admin` 20, `cliente` 8, `notificacoes` 2, `api` 1, `app.py`
  5 — total de 42 regras de URL.

### C.3 Frontend (Comprovado)

- Landing pública `templates/landing.html`, servida por `GET /` sem contexto e sem acesso
  ao banco (`app.py:282-284`). Documento autônomo (não estende `base.html`) com
  `static/css/landing.css`, Bootstrap 5.3.3 (com SRI), Google Fonts, Plotly 2.35.2 via
  `cdn.plot.ly` (sem SRI), `landing.js` (3 gráficos com dados fictícios) e
  `landing-video.js` (player do vídeo demo). Seções: header, hero, problema, solução
  (com um único depoimento estático marcado como exemplo), indicadores, demonstração em
  vídeo e dashboard simulado, método, planos (Bronze/Prata/Ouro, todos "Sob consulta",
  botões para o login), CTA final e rodapé sem canal de contato real. Não há FAQ,
  carrossel, favicon, Open Graph ou link para WhatsApp na landing.
- `templates/como_aderir.html` (`GET /como-aderir`): onboarding em 3 passos com botões de
  WhatsApp (`wa.me`) e e-mail cujos valores são **placeholders** declarados em comentário
  Jinja (`templates/como_aderir.html:58-72`). Linkada apenas pela tela de login; a landing
  não a referencia, ao contrário do que diz o comentário em `app.py:286-287`.
- Layout autenticado `templates/base.html`: Bootstrap 5.3.3 e Bootstrap Icons 1.11.3
  (jsdelivr, sem SRI), `nexo.css`, Plotly 2.35.2 (jsdelivr, sem SRI), helpers
  `NEXO.plot/plotParetoAbc/plotLinhaTemporal` inline, cliente Socket.IO 4.7.5
  (`cdn.socket.io`, só autenticado) e widget do NexoBot (só cliente).
- Identidade acadêmica **visível ao usuário** concentra-se na landing:
  `templates/landing.html:90` (tag do hero), `:720-723` (selo do rodapé com classe
  `.academic-tag`, `static/css/landing.css:768-773`) e os termos "MVP" em `:305` e
  `:329`. E-mails, PDF, telas de auth, admin e cliente não exibem identidade acadêmica.
  Ocorrências não renderizadas (comentários Jinja/HTML/CSS/docstrings/saídas de script)
  existem em `landing.html:323`, `base.html:27-36`, `_macros.html:1-12`, `landing.css:393`,
  `models.py:4-12, 412`, `etl_processor.py:22, 238`, `init_db.py:4, 56`, `seed.py:15-16`,
  `requirements.txt:1, 12`, `test_etl.py:2`, `criar_cliente_demo.py:3`,
  `schema_nexo_mvp_v4.sql` e em documentação (`README.md:12, 16, 323, 394, 401`,
  `Docs/RELATORIO_COBERTURA_ETL.md:3, 107`, `Docs/RELATORIO_TECNICO.md:116, 188`).
  Atenção operacional: em locale não UTF-8 (POSIX/C), `grep` com classes de caracteres ou
  `-i` sobre letras acentuadas (ex.: `grep -iE 'acad[eê]mic'`) pode deixar passar
  `README.md:401` e uma das ocorrências de `landing.html`; usar `LC_ALL=C.UTF-8` em todos
  os greps da E1. O comentário HTML `landing.html:2-20` é um cabeçalho obsoleto de "preview
  standalone", sem referência acadêmica (candidato à E2, não à E1).
- Finais de linha: 82 dos 210 arquivos rastreados usam CRLF — todos os 38 templates,
  `landing.css`, `nexo.css`, `landing.js`, 29 arquivos `.py` (entre eles `app.py`,
  `config.py`, `models.py`, `extensions.py`, `blueprints/api.py`, `blueprints/auth.py`,
  `blueprints/cliente.py`, `blueprints/notificacoes.py`, `seed.py`), 10 arquivos de
  `migrations/` (incl. `env.py`, `alembic.ini` e 6 das 8 revisões), `requirements.txt` e
  `README.md` — e não há `.gitattributes` (`git ls-files --eol`). Edições nesses arquivos e
  novas revisões Alembic devem preservar o final de linha existente para não gerar diffs
  de arquivo inteiro.

### C.4 Persistência (Comprovado)

14 modelos em `models.py`, todos cobertos pelas migrações:

| Modelo | Tabela | Notas |
|---|---|---|
| `Plano` | `plano` | `nome_plano` com CHECK em (`BRONZE`, `PRATA`, `OURO`); `valor_mensal`; `qtd_analises_mes`; `tipo_analise_permitida` (MENSAL/QUINZENAL); `nivel_entrega_analise`, `nivel_dashboard`, `nivel_atendimento`; `ativo` |
| `Segmento` | `segmento` | |
| `Empresa` | `empresa` | FKs `id_segmento`, `id_plano_atual`; `status_conta` (ATIVA/SUSPENSA/CANCELADA); `deletado_em` (soft delete/lixeira); `telefone_contato`, `email_contato`, `data_contratacao` |
| `Usuario` | `usuario` | `role` (ADMIN/CLIENTE) com CHECK que amarra ADMIN a `id_empresa IS NULL` e CLIENTE a `id_empresa IS NOT NULL`; `primeiro_acesso`; `geracao_autorizacao` (SEC-004); `UserMixin` |
| `Analise` | `analise` | FKs `id_empresa`, `id_plano_referencia` (snapshot do plano na criação), `id_usuario_admin_responsavel`; `tipo_analise` MENSAL/QUINZENAL; `status_analise` (AGUARDANDO_RELATORIO/RELATORIO_RECEBIDO/EM_ANALISE/CONCLUIDO) |
| `UploadRelatorio` | `upload_relatorio` | `caminho_arquivo` como `db:<chave>` (sem FK para `arquivo_armazenado`); `hash_arquivo` SHA-256 |
| `IndicadorAnalise` | `indicador_analise` | 1:1 com análise; KPIs numéricos; `periodo_base_inicio/fim`; `versao_processamento` |
| `RelatorioAnalise` | `relatorio_analise` | 1:1; `publicado`; `gerado_por_ia` |
| `ProdutoCurvaABC` | `produto_curva_abc` | Top 20 persistido; `classe_abc` A/B/C |
| `ChamadoSuporte`, `MensagemSuporte` | `chamado_suporte`, `mensagem_suporte` | Tickets por empresa; categorias FINANCEIRO/DUVIDA_TECNICA/ERRO_INTEGRACAO; status ABERTO/EM_ATENDIMENTO/RESOLVIDO |
| `Notificacao` | `notificacao` | Sininho por usuário |
| `GuiaTopico` | `guia_topico` | CMS da Base de Conhecimento; fonte do NexoBot |
| `ArquivoArmazenado` | `arquivo_armazenado` | `conteudo` `LargeBinary` (BYTEA); planilhas dos clientes e imagens do Guia ficam no banco |

Pontos relevantes para as próximas etapas:

- **Não existe** modelo, migração ou tabela para avaliações, sugestões, depoimentos,
  assinatura/contrato ou WhatsApp. A tabela `avaliacao_analise` (nota 1-5, 1 por
  análise) e `fatura_cobranca` existem **apenas** no DDL histórico
  `schema_nexo_mvp_v4.sql:351-387`, fora do ORM e das migrações.
- Os campos de nível do `Plano` (`qtd_analises_mes`, `tipo_analise_permitida`,
  `nivel_entrega_analise`, `nivel_dashboard`, `nivel_atendimento`) são persistidos e
  semeados, mas **nenhum código de aplicação os lê** (grep em `blueprints/` e
  `templates/` sem ocorrências). A única regra de negócio por plano é "análise QUINZENAL
  somente para empresa cujo plano se chama `OURO`", comparando o nome
  (`blueprints/admin.py:240-244`; duplicada em JS e texto em
  `templates/admin/analise_form.html:57, 122-140`).
- `Empresa.status_conta` SUSPENSA/CANCELADA só bloqueia a criação de novas análises no
  admin (`blueprints/admin.py:230-231`); não restringe login, upload, tickets ou
  Socket.IO (`session_security.py:33-57` verifica `ativo`, papel válido, vínculo com a
  empresa e `deletado_em`, mas não `status_conta`).
- Nenhuma FK declara `ondelete`; o apagamento em cascata existe só no ORM
  (`Analise` → uploads, indicador, relatório, curva ABC). A exclusão permanente de
  empresa enumera manualmente as tabelas filhas (`blueprints/admin.py:523-612`).
- `Base` sem `naming_convention` (`extensions.py:20-26`): as CHECKs de `plano`,
  `empresa.status_conta`, `usuario.role`, `analise` (`mes_referencia`, `tipo_analise`,
  `status_analise`), `upload_relatorio`, `produto_curva_abc.classe_abc` e
  `chamado_suporte` têm nome gerado pelo banco; só
  `ck_usuario_role_empresa`, `ck_usuario_geracao_autorizacao`,
  `ck_analise_tipo_quinzena`, `uq_upload_analise_tipo` e `uq_abc_analise_posicao` têm
  nome explícito.

### C.5 Migrações (Comprovado)

Cadeia Alembic **linear, com head única**, 8 revisões (lidas em
`migrations/versions/*.py`, campos `revision`/`down_revision`):

```
d87a6fbc2fbe (raiz: schema inicial, 12 tabelas)
└─ c7189696a9cd (indicador_analise.periodo_base_inicio/fim)
   └─ f958d38a7f19 (relatorio_analise.gerado_por_ia)
      └─ 91a2ecf56a41 (usuario.primeiro_acesso)
         └─ d61b5e68082c (guia_topico)
            └─ a3f1c9b27d04 (empresa.deletado_em)
               └─ b7c4e2a9f031 (arquivo_armazenado)
                  └─ e4c004a26b01 (usuario.geracao_autorizacao + UPDATE de dados)  ← HEAD
```

- `migrations/env.py` usa a engine da app atual; com `NEXO_DB_DIRECT=1` a factory troca a
  URI para `DIRECT_URL` antes (`app.py:93-97`). O build do Render **não** executa
  migrações (`render.yaml:15-17`).
- A head `e4c004a26b01` inclui `UPDATE` de dados (desativa clientes de empresas na
  lixeira) e o seu `downgrade` não restaura esse estado; o `downgrade` da raiz faz `drop`
  de todas as tabelas.
- `tests/test_deploy.py:40-54` aplica as migrações em SQLite vazio e exige
  `compare_metadata == []` (paridade modelos × migrações);
  `tests/test_company_restore_migration.py` fixa `OLD_HEAD=b7c4e2a9f031` e
  `NEW_HEAD=e4c004a26b01`.
- Os dois arquivos `.sql` avulsos são DDL SQLite históricos e **divergem** dos modelos:
  faltam `guia_topico` e `arquivo_armazenado` e as colunas `empresa.deletado_em`,
  `usuario.geracao_autorizacao`, `usuario.primeiro_acesso`,
  `indicador_analise.periodo_base_*`, `relatorio_analise.gerado_por_ia`; trazem
  `avaliacao_analise` e `fatura_cobranca`, que não existem no ORM. O de `Docs/` é ainda
  mais antigo (12 tabelas). Não devem ser usados para criar ou restaurar banco.
- A documentação operacional ainda cita "7 revisões / head `b7c4e2a9f031`"
  (`Docs/AUDITORIA_RENDER.md:76`, `Docs/OPERACAO_BACKUP_RESTAURACAO.md:16`).

**Requer execução**: `flask db heads` e `flask db current` contra o banco autorizado para
confirmar a head e a revisão efetivamente aplicada em produção (ver H).

### C.6 Autenticação (Comprovado)

- Flask-Login com `user_loader` que relê o usuário do banco a cada request
  (`session_security.carregar_usuario`). Um `before_request` global revalida a sessão:
  conta ativa, papel válido, empresa fora da lixeira, `_user_id`, `BOOT_ID` do processo e
  impressão HMAC-SHA256 da credencial (`SECRET_KEY` + id + `senha_hash` +
  `geracao_autorizacao`). Falha → logout e `session.clear()`; falha de banco → 503
  (`app.py:159-197`; `session_security.py:33-115`).
- Rotas `/auth`: `login` (GET/POST, 10/min no POST), `logout` (GET), `primeiro-acesso`
  (logado), `recuperar-senha` (GET/POST, 5/min no POST, resposta anti-enumeração),
  `resetar-senha/<token>`, `primeiro-acesso/<token>`. Tokens v2 assinados com
  `SECRET_KEY` por finalidade, validade de 900 s, ligados ao hash da senha e à geração de
  autorização; consumo por `UPDATE` condicional (`blueprints/auth.py:48-234`).
- Dois papéis: `ADMIN` (sem empresa) e `CLIENTE` (com empresa). Decorators
  `admin_required` (`blueprints/admin.py:45-53`) e `cliente_required`
  (`blueprints/cliente.py:61-69`). **Não existe** decorator ou helper de autorização por
  plano; a única checagem por plano em todo o código é a regra QUINZENAL → `OURO` em
  `blueprints/admin.py:240-244` (ver C.4).
- Sessão: `SESSION_PERMANENT=False`, 8 h, `HttpOnly`, `SameSite=Lax`, `Secure` só em
  produção; `remember=False`. `BOOT_ID` novo a cada processo invalida todas as sessões em
  cada restart/deploy.
- Isolamento entre empresas é feito rota a rota na aplicação (`id_empresa ==
  current_user.empresa.id_empresa`, senão 404); não há RLS nem filtro centralizado.

**Requer execução**: entrega real de e-mails de ativação/recuperação; eficácia do rate
limit por IP atrás do proxy do Render; revogação ponta a ponta de sessões e sockets
(coberta por testes PostgreSQL que não foram executados nesta etapa).

### C.7 Área administrativa (Comprovado)

20 rotas em `/admin`, todas com `@admin_required`:

- Dashboard com KPIs e 3 gráficos Plotly (empresas por status, por plano com rótulos
  fixos `BRONZE/PRATA/OURO`, análises por status) e fila de homologação de uploads.
- Empresas: listagem, criação (seleção de `id_plano_atual`, criação do usuário CLIENTE
  inicial com link de ativação por e-mail), edição (CNPJ imutável; troca de plano não
  altera análises antigas), exclusão para a lixeira (soft delete com revogação de
  sessões), lixeira, restauração, exclusão permanente (hard delete manual em ordem
  topológica).
- Análises: listagem, criação (exige `status_conta` ATIVA; regra QUINZENAL → OURO),
  upload (`@limitar_upload`), processamento ETL (`@limitar_processamento`), editor de
  relatório (rascunho, gerar por IA, publicar, despublicar), exclusão física.
- Tickets: listagem global e detalhe (responder, alterar status).
- Guia/Base de Conhecimento: CRUD de `GuiaTopico` com imagens validadas por PIL e
  armazenadas no banco.
- **Não existe** gestão de planos (CRUD), gestão de usuários (ativar/desativar, usuários
  adicionais) nem qualquer tela de avaliações, depoimentos ou sugestões.

### C.8 Área do cliente (Comprovado)

8 rotas em `/cliente`, todas com `@cliente_required`:

- `dashboard`: última análise concluída, KPIs, 4 gráficos Plotly (Compras × Vendas,
  Pressão de Estoque, Pareto ABC Top 10, histórico temporal com ≥ 2 análises), cards de
  semáforo, barra de auditoria e um card "Contato NEXO" com os textos literais
  "WhatsApp: preencher depois" e "E-mail: preencher depois"
  (`templates/cliente/dashboard.html:219-223`).
- `historico`, `analise/<id>` (detalhe com 2 gráficos, tabela ABC, semáforos, devolutiva
  com banner de IA quando `gerado_por_ia`), `analise/<id>/pdf` (ReportLab).
- `upload` (self-service de CSV/XLSX com validação em subprocesso; notifica admins).
- `tickets` e `tickets/<id>` (chamados por empresa, visíveis a todos os CLIENTE da
  empresa; reabertura ao responder).
- `guia` (tópicos ativos do CMS).
- O plano aparece apenas como badge (`templates/cliente/dashboard.html:39-41`,
  `templates/_macros.html:65-72`). **Nenhum recurso do portal é condicionado ao plano.**
- Notificações: `POST /notificacoes/marcar-lidas`, `GET /notificacoes/<id>/abrir`; a
  linha de `notificacao` é criada e `flush`ada na mesma transação do evento que a origina
  (`notifications.py:146-155`) e a emissão em tempo real pelo evento `nova_notificacao`,
  em sala `user_<id>_<impressao>` (`realtime.py:41-42`), só ocorre após o `commit`
  (`notifications.py:80-99, 136-143`). Varredura em segundo plano a cada 1 s revalida
  cada SID no banco (`realtime.py:69-105`).
- E-mails transacionais (4): análise publicada, chamado resolvido, recuperação de senha,
  boas-vindas. Transporte Brevo HTTPS quando há `BREVO_API_KEY`, senão SMTP; envio em
  thread daemon; suprimidos quando não há credencial.

**Requer execução**: renderização dos gráficos em navegador; handshake WebSocket atrás do
proxy do Render; impacto da varredura de 1 s no pooler do Supabase; entrega de e-mails.

### C.9 Processamento ETL (Comprovado)

- Formatos: `csv` e `xlsx` (`.xls` recusado). Limites padrão em `etl_limits.py`
  (20 MiB/arquivo, 100.000 linhas, 128 colunas, 16 abas, 60 s, 384 MiB, saída 2 MiB),
  sobrescrevíveis por variáveis `ETL_*` dentro de tetos rígidos.
- Execução **síncrona na requisição**, porém em subprocesso Python isolado
  (`etl_runtime.py` → `python -I -B etl_worker.py`) com `RLIMIT_AS`, `RLIMIT_CPU`,
  ambiente sem segredos, audit hook bloqueando rede e subprocessos, SIGKILL no timeout.
  Admissão com um único slot por processo, em duas camadas, ambas `BoundedSemaphore(1)`:
  `etl_uploads.py:17` (compartilhado por `@limitar_upload` e `@limitar_processamento`) e
  `etl_runtime.py:17` (em torno do subprocesso de validação e de cálculo).
- Pipeline (`etl_processor.py`): detecção de cabeçalho por aliases (1 ou 2 linhas),
  limpeza de rodapés e não-produtos, conversão numérica pt-BR/en-US, KPIs (faturamento,
  total comprado, Pressão de Estoque, produto mais vendido, maior faturamento, maior saldo
  parado, período da base) e Curva ABC (80/95%, top 20 persistido). Persistência em
  `IndicadorAnalise` (upsert) e `ProdutoCurvaABC` (apaga e reinsere), dentro de SAVEPOINT;
  telemetria e alertas **não** são persistidos.
- `insights.py`: até 3 cards-semáforo a partir dos KPIs. `ai_devolutiva.py`: chamada ao
  SDK Anthropic (modelo em `ANTHROPIC_MODEL`) com fallback determinístico local sem chave
  ou em erro. `pdf_export.py`: ReportLab com escape de todo texto externo (SEC-001).
- Nenhuma lógica desta área depende do plano comercial.

**Requer execução**: tempo e memória reais no Render Free (0,1 CPU / 512 MB); aceitação
dos parâmetros `output_config`/`thinking` pela versão `anthropic==0.109.1`.

### C.10 Integrações (Comprovado)

| Integração | Mecanismo | Variáveis (nomes) | Estado no `render.yaml` |
|---|---|---|---|
| PostgreSQL/Supabase | `psycopg2-binary`; `DATABASE_URL` (pooler) para a app, `DIRECT_URL` (direta) para migrações com `NEXO_DB_DIRECT=1`; `_limpar_url_pg` remove parâmetros `pgbouncer`, `connection_limit`, `pool_timeout`, `schema` e força `postgresql+psycopg2`; `pool_pre_ping`, `pool_recycle=280`; `sslmode` não é forçado pelo código | `DATABASE_URL`, `DIRECT_URL`, `NEXO_DB_DIRECT` | `DATABASE_URL` e `DIRECT_URL` com `sync: false` |
| E-mail | Brevo API HTTPS (`BREVO_API_KEY`, `BREVO_API_URL`) ou SMTP via Flask-Mail (`MAIL_*`) | `BREVO_API_KEY`, `BREVO_API_URL`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | `BREVO_API_KEY` (`sync: false`), `MAIL_DEFAULT_SENDER` (valor fixo com endereço de e-mail) |
| IA (devolutiva) | SDK `anthropic==0.109.1`; fallback local sem chave | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | **Não declaradas** |
| NexoBot/Hugging Face (opcional) | `httpx` (transitivo do SDK Anthropic) ao roteador HF; desligado sem token; saída validada | `HF_API_TOKEN`, `HF_MODEL` | **Não declaradas** |
| Tempo real | Flask-SocketIO 5.6.1 `threading` + `simple-websocket`, sem `message_queue` | `SOCKETIO_CORS_ORIGINS`, `RENDER_EXTERNAL_URL` | `SOCKETIO_CORS_ORIGINS` não declarada |
| Rate limit | Flask-Limiter 3.8.0 | `RATELIMIT_STORAGE_URI` (padrão `memory://`) | Não declarada |
| WhatsApp | **Nenhuma integração.** Apenas um link `wa.me` fixo com número placeholder em `templates/como_aderir.html:63` e texto placeholder em `templates/cliente/dashboard.html:221`; nenhuma variável de configuração | — | — |

NexoBot (`nexobot/`, `suporte_bot.py`, `static/js/nexobot.js`): roda localmente em cinco
camadas (normalização, classificação por evidências com 22 intenções, conhecimento BM25F
sobre `guia_topico` + 11 fatos fixos, contexto sem estado no servidor, decisão); única
leitura no banco é em `GuiaTopico`; navegação restrita a um catálogo fechado de 5
destinos do portal do cliente via `url_for()`; o widget recusa URLs externas. Exposto só
por `POST /api/suporte-bot` para CLIENTE autenticado. Não há menção a planos, preços,
WhatsApp ou identidade acadêmica no código do bot.

### C.11 Testes e CI (Comprovado)

- Framework: `unittest` da biblioteca padrão (sem pytest). `tests/` tem 41 arquivos
  (30 `test_*.py` descobertos por `unittest discover`, 5 módulos `postgresql_*.py`
  executados explicitamente, suportes `deploy_support.py`, `postgresql_support.py`,
  `etl_equivalence_support.py`, `nexobot_corpus.py`, `__init__.py` — que chama
  `ensure_test_environment()` na carga do pacote — e 1 fixture JSON). 564 ocorrências de
  `def test_` (531 em `test_*.py`, 33 em `postgresql_*.py`); por herança de classes, o
  total executado pode diferir. Último total **documental**: 531 + 108 aprovados
  localmente (`Docs/RELATORIO_NEXO_SEC005_ETL_SEGURO.md:245-253`).
- Isolamento: SQLite temporário com migrações reais (`DeployTestCase`) ou `create_all`
  (`_TokenCase`); rede bloqueada por patch de socket; `.env` nunca lido; PostgreSQL
  descartável criado pelo próprio teste via `initdb`/`pg_ctl` em socket Unix privado
  (`tests/postgresql_support.py`), recusando qualquer URL externa; navegador Chromium via
  Playwright opt-in (`NEXO_TEST_BROWSER=1`).
- Cobertura relevante para a reestruturação: `test_deploy.py` exige 200 em `/`,
  `/como-aderir` e `/auth/login`, existência de todos os assets `static` referenciados,
  seed com exatamente 3 planos/3 segmentos/1 usuário e `compare_metadata == []`;
  `test_backup_restore.py` exige exatamente 15 tabelas; `test_supply_chain_install.py`
  fixa campos do `render.yaml` e a estrutura do CI; `test_nexobot_interface.py` casa
  strings literais de `base.html` e `nexo.css`. **Não há** testes de diferenciação de
  planos PRATA/OURO (fixtures criam só BRONZE), avaliações, depoimentos, WhatsApp ou
  conteúdo textual da landing.
- CI `.github/workflows/nexo-security-ci.yml` ("NEXO Security CI"): gatilhos
  `pull_request` (opened, synchronize, reopened, ready_for_review), `push` em `main`,
  `workflow_dispatch`; `permissions: contents: read`; dois jobs em `ubuntu-24.04` /
  Python 3.12 — `security-sqlite-browser` (suíte completa + Chromium + ensaio de backup
  PostgreSQL) e `security-postgresql` (5 módulos PostgreSQL). Actions fixadas por SHA.
  Instalação pelo mesmo `tools/install_dependencies.py` do Render.
- Os testes **não foram executados** nesta etapa. A aprovação do CI no commit de
  referência não está documentada no repositório (runs documentados:
  `Docs/CI_SEGURANCA.md:108-117`).

---

## D. Hospedagem

### D.1 `render.yaml` (Comprovado — configuração **versionada**)

| Campo | Valor versionado |
|---|---|
| `type` / `runtime` / `plan` | `web` / `python` / `free` |
| `name` | `nexo-faturamento-inteligente` |
| `region` | `oregon` |
| `branch` | `main` |
| `buildCommand` | `python -I tools/install_dependencies.py --requirements requirements.txt` |
| `startCommand` | `gunicorn -w 1 --threads 50 --timeout 180 -b 0.0.0.0:$PORT wsgi:app` |
| `healthCheckPath` | `/healthz` (não consulta o banco; `/healthz/db` faz `SELECT 1`) |
| `autoDeployTrigger` | `'off'` |
| `envVars` com valor fixo | `PYTHON_VERSION=3.12.10`, `FLASK_ENV=production`, `PROXY_FIX_HOPS="1"`, `MAIL_DEFAULT_SENDER` (contém endereço de e-mail; valor não reproduzido) |
| `envVars` geradas | `SECRET_KEY` (`generateValue: true`) |
| `envVars` pedidas na criação (`sync: false`) | `DATABASE_URL`, `DIRECT_URL`, `BREVO_API_KEY` |
| Não declarados | disco persistente, `preDeployCommand`, escala/instâncias, previews, `RATELIMIT_STORAGE_URI`, `SOCKETIO_CORS_ORIGINS`, `ANTHROPIC_API_KEY`, `HF_API_TOKEN`, `ETL_*` |

O comentário do próprio arquivo registra que o build não altera o banco e que as
migrações devem ser aplicadas separadamente antes de liberar o tráfego.

### D.2 `wsgi.py` e `config.py` (Comprovado)

- `wsgi.py` instancia `create_app(FLASK_ENV ou "production")`. A docstring explica o
  worker único: salas Socket.IO e rate limit `memory://` vivem na memória do processo
  (`wsgi.py:8-12`); o `BOOT_ID`, também por processo, é descrito em `app.py:86-91`.
- `config.py` lê, do ambiente, os seguintes **nomes** de variáveis: `SECRET_KEY`,
  `DATABASE_URL`, `DIRECT_URL`, `RATELIMIT_STORAGE_URI`, `SOCKETIO_CORS_ORIGINS`,
  `RENDER_EXTERNAL_URL`, `PROXY_FIX_HOPS`, `ADMIN_EMAIL`, `ADMIN_NOME`, `ADMIN_SENHA`,
  `UPLOAD_FOLDER`, `MAX_CONTENT_LENGTH_MB`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`,
  `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`,
  `BREVO_API_KEY`, `BREVO_API_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`,
  `HF_API_TOKEN`, `HF_MODEL` e `ETL_*` (via `etl_limits.limits_from_environment`).
  `app.py`/`wsgi.py` leem ainda `FLASK_ENV`, `NEXO_DB_DIRECT`, `HOST`, `PORT`.
  `load_dotenv()` é chamado em `config.py:23` sem `override`.
- Sem `DATABASE_URL`, o padrão é SQLite em `instance/nexo_mvp.db`. Para Postgres, a URL é
  normalizada (`_limpar_url_pg`) e `SQLALCHEMY_ENGINE_OPTIONS` define apenas
  `pool_pre_ping=True` e `pool_recycle=280`.
- `.env.example` lista os mesmos nomes (todos os segredos vazios) e **não** lista
  `ETL_*`, `ANTHROPIC_MODEL`, `BREVO_API_URL`, `HOST`, `PORT`, `RENDER_EXTERNAL_URL`.

### D.3 Dependências relacionadas ao deploy (Comprovado)

- `gunicorn==23.0.0`, `psycopg2-binary==2.9.9`, `Flask-Migrate==4.0.7`,
  `Flask-SocketIO==5.6.1`, `simple-websocket==1.1.0`. SQLAlchemy, Alembic e NumPy não têm
  pin direto (chegam como transitivos). Não há lockfile nem `--require-hashes`.
- `tools/install_dependencies.py` (SEC-006B): só stdlib; baixa o wheel do `pip 26.2.2`
  verificando SHA256 fixo, executa esse pip isolado e instala `requirements(.txt|-dev.txt)`
  do PyPI oficial com ambiente filtrado e `pip check`. Os pacotes da aplicação **não** têm
  hash verificado.

### D.4 Procedimento de migração e deploy documentado (Documental)

`Docs/PREPARACAO_RENDER.md:52-88`, `README.md:271-289`: exportar `FLASK_ENV=production`,
`NEXO_DB_DIRECT=1`, `DATABASE_URL`, `DIRECT_URL`, `SECRET_KEY`; `flask db upgrade`;
`python seed.py` na primeira instalação; nas atualizações, backup autorizado e restauração
isolada validados antes, `flask db upgrade` quando houver novas revisões e só então
"Manual Deploy → Deploy latest commit". O build/instalador não executa migração nem seed
(`render.yaml:15-16`, `Docs/PREPARACAO_RENDER.md:36`); `downgrade` e `stamp` não devem
ser usados como rollback (`Docs/OPERACAO_BACKUP_RESTAURACAO.md:229, 240`;
`Docs/AUDITORIA_RENDER.md:109`).

### D.5 Estado do serviço ativo no Render — **PENDENTE**

Nesta etapa **não houve acesso ao painel do Render nem a qualquer URL do serviço**. O
`render.yaml` representa a configuração versionada, não o estado real. Em particular:

- A documentação registra que o proprietário informou **Auto-Deploy ATIVADO** no painel
  (`Docs/PREPARACAO_RENDER.md:81`; `Docs/RELATORIO_NEXO_SEC006_DEPENDENCIAS.md:162, 204`),
  divergindo do `autoDeployTrigger: 'off'` versionado.
- Commit atualmente implantado, URL pública, comandos efetivos, estado de Pull Request
  Previews, versão do PostgreSQL no Supabase e valores efetivos de variáveis não
  declaradas no YAML são **desconhecidos**.
- A verificação do ambiente ativo fica registrada como pendente para a Etapa 0.2/E9.

---

## E. Componentes previstos para alteração futura

Nenhum destes arquivos foi modificado nesta etapa. A lista indica onde cada etapa
provavelmente atuará, com base no código lido.

| Etapa | Arquivos/módulos prováveis | Motivo (evidência) |
|---|---|---|
| **E1** Remoção da identidade acadêmica | `templates/landing.html` (90, 305, 323, 329, 720-723); `static/css/landing.css` (393, 768-773); comentários/saídas não renderizados em `templates/base.html`, `templates/_macros.html`, `models.py` (4-12, 412), `etl_processor.py`, `init_db.py` (4, 56), `seed.py`, `requirements.txt`, `test_etl.py`, `criar_cliente_demo.py`; `README.md` (12, 16, 323, 394, 401); `Docs/RELATORIO_COBERTURA_ETL.md`, `Docs/RELATORIO_TECNICO.md`, `schema_nexo_mvp_v4.sql`, `Docs/schema_nexo_mvp_v4 (1).sql`; conteúdo da tabela `guia_topico` (dado, não código) | Ocorrências levantadas em C.3. Decidir se documentos históricos entram no escopo. Não renomear `instance/nexo_mvp.db` (`config.py:57`) |
| **E2** Landing comercial | `templates/landing.html` (incl. comentário HTML obsoleto de "preview standalone" em 2-20); `static/css/landing.css`; `static/js/landing.js`; `templates/como_aderir.html`; `templates/auth/login.html`, `templates/auth/_layout.html`; `app.py:279-290` (comentário e eventual contexto) | Hero, navegação mobile ausente (`landing.css:779, 789`), CTA final sem canal, jargão técnico, planos "Sob consulta" vs `seed.py:33-60` |
| **E3** Demonstração e indicadores | `templates/cliente/dashboard.html`, `templates/cliente/analise.html`, `templates/base.html` (helpers Plotly inline), `static/js/nexo.js` (vazio), `blueprints/cliente.py:75-197`, `insights.py`, `etl_processor.py` (resumo ABC/telemetria não persistidos), `pdf_export.py`, `templates/admin/processar_resultado.html`, `templates/emails/analise_publicada.html` ("Top 5" vs Top 10), `static/video/*`, `static/js/landing-video.js`, `tools/nexo-motion/` | Divergências de dados fictícios entre vídeo e landing; rótulo "Maior faturamento" (regra do 2º colocado em `etl_processor.py:655-669`) |
| **E4** Planos Bronze/Prata/Ouro | `models.py:37-61` (campos `nivel_*` não usados); `seed.py:29-71`; `blueprints/admin.py:240-244, 113-116`; `templates/admin/analise_form.html`; `templates/_macros.html:65-72`; `blueprints/cliente.py` (dashboard, análise, PDF, upload); `session_security.py:33-57` (portão central; preferir helper separado); `ai_devolutiva.py`; `nexobot/navegacao.py`, `nexobot/portal.py`, `nexobot/respostas.py` (textos afirmam PDF/e-mail para todos); `tests/deploy_support.py`, `tests/test_auth_tokens_security.py` (fixtures só com BRONZE); `templates/landing.html:538-652` | Decidir plano atual (`empresa.plano_atual`) vs snapshot (`analise.plano_referencia`); semântica de SUSPENSA/CANCELADA |
| **E5** Avaliações e sugestões | `models.py` (novo modelo); nova revisão Alembic com `down_revision='e4c004a26b01'`; `blueprints/cliente.py`; `templates/cliente/analise.html`, `templates/cliente/dashboard.html`; `notifications.py` (`classificar_notificacao` por palavra-chave); `extensions.py`/`limiter` (novos POST precisam de limite explícito); `nexobot/navegacao.py`, `nexobot/lexico.py` (novo destino); `templates/base.html` (menu); `tests/test_deploy.py`, `tests/test_backup_restore.py:97` (15 tabelas) | Referência histórica: `schema_nexo_mvp_v4.sql:351-360` (`avaliacao_analise`) |
| **E6** Administração de avaliações | `blueprints/admin.py` (novas rotas; incluir novas tabelas na enumeração manual do hard delete `523-612`; a exclusão de análise `961-1010` depende do `cascade` ORM dos relationships de `Analise` em `models.py:219-241`, que precisará cobrir as novas tabelas); `templates/admin/*`; `templates/base.html:52-71` (menu); `company_security.py` (destino das avaliações de empresas na lixeira); `nexobot/seguranca.py` (área admin bloqueada no bot) | Falta de `ondelete` no banco faz o hard delete falhar se as novas FKs não forem tratadas |
| **E7** Carrossel de depoimentos | `templates/landing.html:309-319`; `static/css/landing.css:364-390`; `app.py:282-284` (rota `/` passaria dados; hoje não acessa o banco); `storage.py`/`app.py:261-276` (se houver imagens públicas: `/midia` exige login e só aceita prefixo `guia/`); `tests/test_deploy.py:67-73` (assets devem existir) | Consentimento e origem real dos depoimentos; dependência da landing em relação ao Supabase |
| **E8** WhatsApp Business e rodapé | `templates/como_aderir.html:58-72`; `templates/cliente/dashboard.html:215-225`; `templates/landing.html:654-726`; `config.py` (não há variável para contato comercial); `app.py:247-259` (context processor/globais Jinja); `.env.example`; `render.yaml`; `static/css/nexo.css:653-705`; `nexobot/respostas.py`, `nexobot/seguranca.py`, `static/js/nexobot.js:89-97` (modelo de segurança recusa URLs externas); `pdf_export.py`, `templates/emails/_base.html` (rodapés) | Link `wa.me` hoje fixo em template |
| **E9** Homologação e implantação | `render.yaml`; `.env.example`; `config.py` (`SOCKETIO_CORS_ORIGINS`, `RATELIMIT_STORAGE_URI`, só `development`/`production`); `app.py` (CSP/HSTS inexistentes; CDNs sem SRI em `base.html`, `auth/_layout.html`, `erro_simples.html`, Plotly da landing); `etl_limits.py` (ajuste ao Render Free após medição); `Docs/PREPARACAO_RENDER.md`, `Docs/PLANO_PUBLICACAO_SEGURA.md`, `Docs/CI_SEGURANCA.md`; `tests/test_supply_chain_install.py:257-300` | |
| **0.2** Banco e migrações | `migrations/versions/` (encadear na head `e4c004a26b01`); `extensions.py:20-26` (`Base` sem `naming_convention`); `models.py`; `seed.py` (não atualiza linhas existentes); `criar_cliente_demo.py`; `schema_nexo_mvp_v4.sql` e cópia em `Docs/`; `Docs/OPERACAO_BACKUP_RESTAURACAO.md`, `Docs/AUDITORIA_RENDER.md` (head desatualizada); `tests/test_company_restore_migration.py`; `requirements.txt` (SQLAlchemy/Alembic sem pin) | Ver H |

---

## F. Riscos identificados

Classificação: **Comprovado** (observado diretamente no código) ou **Potencial** (depende
de condição externa, de execução ou de decisão de produto). Severidade estimada para a
reestruturação: alta / média / baixa.

### F.1 Banco de dados e migrações

| # | Risco | Tipo | Sev. | Evidência |
|---|---|---|---|---|
| F1.1 | Revisão aplicada em produção desconhecida: o código atual mapeia `usuario.geracao_autorizacao` (criada pela head `e4c004a26b01`), e a documentação diz que essa migração **não foi confirmada** em produção. Se o banco estiver em `b7c4e2a9f031`, consultas a `Usuario` falham com o código atual | Potencial | Alta | `models.py:135-137`; `Docs/RELATORIO_NEXO_SEC005_ETL_SEGURO.md:16-17`; `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md` |
| F1.2 | Novas tabelas (E5/E6/E7) exigem migração sobre banco de produção com dados; o build do Render não migra e o procedimento depende de passo manual | Comprovado | Alta | `render.yaml:15-17`; `Docs/PREPARACAO_RENDER.md:79-88` |
| F1.3 | CHECK constraints sem nome explícito (`plano`, `status_conta`, enums de análise/upload/chamado): alterar valores permitidos (novos níveis em E4, status em E5/E6) exige descobrir o nome gerado no Postgres e usar `batch` no SQLite; migração pode funcionar num banco e falhar no outro | Potencial | Média | `extensions.py:20-22`; `models.py:56-60, 113, 153, 245-249, 289-291, 399, 443-449` |
| F1.4 | Downgrades destrutivos: a raiz faz `drop` de todas as tabelas; a head tem `UPDATE` de dados sem restauração no downgrade. Rollback de código não reverte o banco | Comprovado | Média | `migrations/versions/d87a6fbc2fbe_*.py:238-263`; `e4c004a26b01_*.py:56-73` |
| F1.5 | `.sql` avulsos divergentes dos modelos (2 tabelas a mais, 2 a menos, 6 colunas ausentes, dialeto SQLite, sem `alembic_version`); uso indevido geraria schema incorreto | Comprovado | Média | `schema_nexo_mvp_v4.sql`; `Docs/schema_nexo_mvp_v4 (1).sql` |
| F1.6 | Arquivos dos clientes como BYTEA no Postgres sem FK entre `caminho_arquivo`/`imagem_url` e `arquivo_armazenado.chave`; crescimento do banco e possíveis órfãos | Potencial | Média | `models.py:273, 523, 538-557`; `storage.py` |
| F1.7 | Pool de conexões no padrão da biblioteca com 50 threads do gunicorn e PgBouncer; varredura Socket.IO consulta o banco a cada 1 s por SID; lock `FOR UPDATE` mantido durante o subprocesso do ETL (até 60 s) | Potencial | Média | `config.py:136`; `render.yaml:21`; `realtime.py:102-115`; `blueprints/admin.py:889-930` |
| F1.8 | `/healthz` (health check do Render) não consulta o banco: serviço parece saudável com banco indisponível ou schema divergente | Comprovado | Média | `render.yaml:22`; `app.py:293-310` |
| F1.9 | RLS do Supabase não verificada (segundo a própria auditoria); o estado da Data API/PostgREST sobre o schema `public` não consta em nenhum documento do repositório; tabelas com `senha_hash` e BYTEA no schema `public` | Potencial | Média | `Docs/AUDITORIA_RENDER.md:75` |
| F1.10 | SQLAlchemy e Alembic sem pin direto: comportamento de `autogenerate`/migração pode variar entre desenvolvedor, CI e Render | Potencial | Baixa | `requirements.txt` |
| F1.11 | `migrations/env.py` renderiza a URL com senha em memória (`hide_password=False`); traceback verboso poderia expor credencial | Potencial | Baixa | `migrations/env.py:27-32, 39` |
| F1.12 | Documentação operacional cita 7 revisões / head `b7c4e2a9f031` (hoje 8 / `e4c004a26b01`) | Comprovado | Baixa | `Docs/AUDITORIA_RENDER.md:76`; `Docs/OPERACAO_BACKUP_RESTAURACAO.md:16` |

### F.2 Permissões dos planos comerciais

| # | Risco | Tipo | Sev. | Evidência |
|---|---|---|---|---|
| F2.1 | Diferenciação de planos praticamente inexistente: campos `nivel_*`, `qtd_analises_mes`, `tipo_analise_permitida` não são lidos por nenhuma rota ou template; única regra é QUINZENAL → nome `OURO`. A landing promete diferenças ("devolutiva premium", "indicadores principais") que o código não implementa | Comprovado | Média | `blueprints/admin.py:240-244`; grep sem uso de `nivel_*`; `templates/landing.html:552-650` |
| F2.2 | `status_conta` SUSPENSA/CANCELADA não restringe login, upload, tickets ou Socket.IO; só bloqueia novas análises no admin | Comprovado | Média | `session_security.py:33-57`; `blueprints/admin.py:230-231`; `blueprints/cliente.py:312-351` |
| F2.3 | Rótulos de plano fixos no código (gráfico do admin, badge, JS do formulário) | Comprovado | Baixa | `blueprints/admin.py:113-116`; `templates/_macros.html:65-72`; `templates/admin/analise_form.html:57, 122-140` |
| F2.4 | NexoBot afirma PDF/e-mail para todos os clientes e não conhece o plano; restrições da E4 tornariam as respostas incorretas | Potencial | Média | `nexobot/portal.py:60-78`; `nexobot/navegacao.py:42-46`; `blueprints/api.py:77-82` |

### F.3 Compatibilidade com clientes existentes

| # | Risco | Tipo | Sev. | Evidência |
|---|---|---|---|---|
| F3.1 | Ao aplicar restrições por plano, clientes existentes podem perder recursos que já usam; decidir entre `empresa.plano_atual` e `analise.plano_referencia` | Potencial | Média | `models.py:88, 108, 197, 217`; `blueprints/admin.py:279` |
| F3.2 | `seed.py` é idempotente só para inserção: mudar a definição dos planos no seed não altera linhas existentes em produção; exige migração de dados | Comprovado | Média | `seed.py:63-71, 82-89` |
| F3.3 | Rotacionar `SECRET_KEY` (inclusive recriar o serviço via Blueprint com `generateValue`) invalida sessões, impressões de credencial e tokens já enviados | Comprovado | Média | `session_security.py:70-80`; `blueprints/auth.py:74-86`; `render.yaml:28-29` |
| F3.4 | Normalização de e-mail inconsistente (login `strip()`, recuperação `strip().lower()`, cadastro `strip()` sem `lower()`, preservando maiúsculas): usuário cadastrado com maiúsculas pode não conseguir recuperar senha | Comprovado | Média | `blueprints/auth.py:259, 347-350`; `blueprints/admin.py:355-357` |
| F3.5 | Referências legadas fora do formato `db:` caem em `UPLOAD_FOLDER` local, inexistente no Render (disco efêmero) | Potencial | Baixa | `storage.py:84-92`; `migrar_arquivos_para_db.py` |
| F3.6 | Clientes veem placeholders "WhatsApp: preencher depois" e "E-mail: preencher depois" no dashboard | Comprovado | Baixa | `templates/cliente/dashboard.html:219-223` |
| F3.7 | KPI "Maior faturamento" exibe o 2º colocado quando coincide com o mais vendido; parse numérico trata `1.500` como 1,5 | Comprovado | Média | `etl_processor.py:655-669, 162-165`; `templates/cliente/dashboard.html:93` |

### F.4 Segurança e isolamento de dados

| # | Risco | Tipo | Sev. | Evidência |
|---|---|---|---|---|
| F4.1 | **Credencial de demonstração versionada**: `criar_cliente_demo.py` contém e-mail e senha temporária fixos de um CLIENTE, executa ao ser importado (sem guarda `__main__`), usa `create_app("development")` (sem as travas de produção), vincula a conta à **primeira empresa** do banco, imprime a senha no stdout e o uso documentado é `NEXO_DB_DIRECT=1`. O repositório é privado, o que reduz a exposição, mas a credencial está no histórico Git. Não se sabe se a conta existe em produção | Comprovado (credencial) / Potencial (conta em produção) | Alta | `criar_cliente_demo.py:1-7, 17-19, 21-25, 33-55`; `config.py:194-196`; `app.py:76-85` |
| F4.2 | Ausência de CSP, HSTS e `X-Frame-Options`/`frame-ancestors` globais; CDNs sem SRI em `base.html`, `auth/_layout.html`, `erro_simples.html` e Plotly da landing | Comprovado | Média | `app.py:133-139, 271-276`; `templates/base.html:16-17, 192-194, 368`; `templates/landing.html:41` |
| F4.3 | Isolamento entre empresas depende só de filtros na aplicação (sem RLS); toda rota nova (E5) precisa repetir o padrão. Há teste HTTP de acesso cruzado para `/cliente/analise/<id>` e `/pdf` (`tests/test_deploy.py:123-128`; `tests/test_backup_restore.py:368-369`) e para upload (`tests/test_etl_upload_security.py:201-207`), mas **não** para `/cliente/tickets/<id>` | Potencial | Média | `blueprints/cliente.py:251-259, 276-284, 465-467`; `tests/test_deploy.py:123-128`; `tests/test_backup_restore.py:368-369`; `tests/test_etl_upload_security.py:201-207` |
| F4.4 | Página pública `/como-aderir` publica `wa.me` e `mailto` com valores placeholder; prospects podem enviar dados a destinatário errado | Comprovado | Média | `templates/como_aderir.html:58-72` |
| F4.5 | Dados comerciais (empresa, produtos, KPIs) são enviados à Anthropic quando há chave; o NexoBot envia ao Hugging Face (opcional) apenas até 3 trechos do Guia e a pergunta do cliente redigida (sem KPIs do banco). Precisa constar em termos de uso/privacidade para operação comercial | Comprovado | Baixa | `ai_devolutiva.py:63-108`; `nexobot/providers.py:55-65` |
| F4.6 | Dados de empresas na lixeira continuam visíveis em contagens/listas do admin; `analise_nova` não verifica `deletado_em` no backend | Comprovado | Baixa | `blueprints/admin.py:101-141, 188-190, 211-232` |
| F4.7 | Abertura de chamado e mensagens sem rate limit nem limite de comprimento por campo (`assunto` `String` sem tamanho, `mensagem` `Text`; vale só o `MAX_CONTENT_LENGTH` global de 20 MB); logout por GET sem CSRF; conversões `int(form[...])` sem tratamento em formulários de empresa | Comprovado | Baixa | `blueprints/cliente.py:403-490`; `config.py:145-146`; `models.py:424, 464`; `blueprints/auth.py:299-305`; `blueprints/admin.py:343-354, 425-433` |
| F4.8 | `.gitignore:34` descreve o repositório como público, mas a API do GitHub o registra como privado; divergência documental que pode levar a decisões erradas sobre exposição | Comprovado | Baixa | `.gitignore:33-35`; consulta à API em 2026-10-24 |

### F.5 Deploy e operação

| # | Risco | Tipo | Sev. | Evidência |
|---|---|---|---|---|
| F5.1 | **Auto-Deploy possivelmente ativo** no painel apesar de `autoDeployTrigger: 'off'` no YAML, com `main` sem proteção de branch (estado lido em 22-23/10). Um merge das etapas E1-E8 (sobretudo E5/E6, com novas tabelas) pode implantar código antes do `flask db upgrade` manual | Potencial | Alta | `render.yaml:18`; `Docs/PREPARACAO_RENDER.md:81`; `Docs/PLANO_PUBLICACAO_SEGURA.md:9-17, 30` |
| F5.2 | Memória e CPU no Render Free (0,1 CPU / 512 MB): processo pai já carrega pandas/openpyxl e o filho pode usar até 384 MiB; prazo de 60 s inclui criação do interpretador e leituras repetidas. Medição existente (4,31 s para XLSX de 4 abas) foi em ambiente de desenvolvimento | Potencial | Alta | `etl_limits.py:22-23`; `etl_runtime.py:62-71`; `Docs/RELATORIO_NEXO_SEC005_ETL_SEGURO.md:88, 229-232, 365-375` |
| F5.3 | Processo único obrigatório: `BOOT_ID`, salas Socket.IO e rate limit `memory://` por processo. Escalar workers/instâncias quebraria sessões, notificações e limites; cada restart desloga todos | Comprovado | Média | `app.py:86-91`; `wsgi.py:8-13`; `extensions.py:37`; `config.py:99-102` |
| F5.4 | Pull Request Previews, se ativas no painel, copiariam `DATABASE_URL` de produção para a instância de prévia desta branch | Potencial | Média | `Docs/VALIDACAO_VIDEO_RENDER.md:157-160` |
| F5.5 | Vídeo MP4 de ~12 MB servido pelo Flask/Gunicorn; estimativa documental de ~447 reproduções/mês para 5 GiB de saída | Potencial | Média | `templates/landing.html:417`; `Docs/VALIDACAO_VIDEO_RENDER.md:138-151` |
| F5.6 | Se a landing passar a consultar o banco (E7), `/` passa a depender do Supabase, que pausa no plano free após 7 dias sem consultas | Potencial | Média | `app.py:282-284, 301-310` |
| F5.7 | `SOCKETIO_CORS_ORIGINS` não declarada no YAML: em produção a única origem aceita além das de localhost vem de `RENDER_EXTERNAL_URL` (`config.py:117-118`); um domínio próprio (E9) recusará o handshake WebSocket se essa variável não o refletir e ele não for adicionado | Potencial | Baixa | `config.py:109-118`; `render.yaml:23-42` |
| F5.8 | Só `development` e `production` existem; `FLASK_ENV=staging` gera `KeyError` | Comprovado | Baixa | `app.py:70`; `config.py:209-212` |
| F5.9 | IA possivelmente inoperante em produção: `ANTHROPIC_API_KEY` não declarada no YAML; compatibilidade de `output_config` com `anthropic==0.109.1` não verificada; chamada síncrona sem timeout explícito; fallback sinalizado apenas por `flash` ao admin e `warning` em log, sem alerta operacional nem indicação ao cliente | Potencial | Média | `render.yaml`; `ai_devolutiva.py:123-159`; `blueprints/admin.py:740-765` |
| F5.10 | Dependências sem `--require-hashes`/lockfile; transitivos não fixados; Python do CI `3.12` flutuante vs `3.12.10` no Render; PostgreSQL do CI (APT) vs versão do Supabase desconhecida | Comprovado | Média | `tools/install_dependencies.py`; `.github/workflows/nexo-security-ci.yml:42-44`; `render.yaml:24-25` |
| F5.11 | Documentação operacional desatualizada (build `pip install`, "deploy automático desabilitado", links `docs/` minúsculo quebrados, "13 modelos"/"13 entidades"; `Docs/PLANO_PUBLICACAO_SEGURA.md:55` condiciona a publicação à ausência de migração nova, condição que a SEC-004 já desfez) | Comprovado | Média | `Docs/PLANO_PUBLICACAO_SEGURA.md:44, 55`; `RELATORIO_FINAL_PARA_CHATGPT.md:53`; `README.md:72, 122, 142, 337, 394-395` |
| F5.12 | Scripts operacionais sem trava contra Postgres: `criar_cliente_demo.py` usa `create_app("development")`; `seed.py`, `seed_guia.py` e `migrar_arquivos_para_db.py` usam `create_app()` sem argumento (cai em `development` quando `FLASK_ENV` não está definida, `app.py:66-67`). Todos funcionam contra Postgres se as variáveis apontarem para produção; `SQLALCHEMY_ECHO=True` em development registra SQL com parâmetros | Comprovado | Média | `criar_cliente_demo.py:21`; `seed.py:126`; `seed_guia.py:61`; `migrar_arquivos_para_db.py:41`; `app.py:66-67`; `config.py:194-196`; `init_db.py:32, 44-51` (único com trava própria) |

### F.6 Dependências das funcionalidades já implementadas

| # | Risco | Tipo | Sev. | Evidência |
|---|---|---|---|---|
| F6.1 | Testes com contratos rígidos quebrarão com as mudanças planejadas se não forem ajustados junto: 15 tabelas no ensaio de backup, exatamente 3 planos no seed, `compare_metadata == []`, campos fixos do `render.yaml`, marcadores literais em `base.html`/`nexo.css`, textos de e-mail | Comprovado | Média | `tests/test_backup_restore.py:97`; `tests/test_deploy.py:37, 40-54`; `tests/test_supply_chain_install.py:291-300`; `tests/test_nexobot_interface.py:14-15, 88-90`; `tests/test_auth_email_flows.py:104-125` |
| F6.2 | Hard delete de empresa enumera tabelas manualmente e a exclusão de análise depende do `cascade` ORM dos relationships de `Analise`; novas FKs sem tratamento (enumeração ou relationship/cascade) causam `IntegrityError`/rollback, pois não há `ondelete` no banco | Potencial | Média | `blueprints/admin.py:523-612, 961-1010`; `models.py:219-241` |
| F6.3 | NexoBot: catálogo fechado de 5 destinos e saudação fixa em JS; novas páginas exigem novo destino, léxico e corpus; listeners globais de `Session` registrados na importação; falha de banco ao carregar `guia_topico` (p. ex. schema alterado) degrada a base para "somente fatos do portal", com aviso em log e na resposta | Potencial | Média | `nexobot/navegacao.py:28-60`; `static/js/nexobot.js:186-189`; `nexobot/conhecimento.py:71-93, 297-309, 320-342` |
| F6.4 | `classificar_notificacao` classifica badge por palavra-chave do texto; textos novos (avaliação, sugestão) podem receber badge errado | Potencial | Baixa | `notifications.py:30-45` |
| F6.5 | Curva ABC persistida só no top 20; card "Classe A" e prompt da IA subestimam concentração com mais de 20 produtos A | Comprovado | Média | `etl_processor.py:61, 608-617`; `insights.py:100-112`; `ai_devolutiva.py:67-69` |
| F6.6 | E-mail de chamado resolvido é disparado antes do `commit` (padrão diferente da publicação, que dispara depois) | Comprovado | Baixa | `blueprints/admin.py:1085-1096` vs `853-867` |
| F6.7 | Licença ambígua para comercialização: `LICENSE` é MIT, README diz "direitos reservados aos autores" | Comprovado | Baixa | `LICENSE:1-3`; `README.md:401` |

---

## G. Limites desta etapa

Declarações sobre o que **não** foi feito nesta subetapa, verificadas em `git status`,
`git diff --stat origin/main` e `git diff --check`:

- **Nenhuma funcionalidade foi modificada.** Nenhum arquivo `.py`, `.html`, `.css`,
  `.js`, `.yaml`, `.txt`, `.sql` ou de configuração existente foi alterado.
- **Nenhuma migration foi executada.** Não houve `flask db upgrade`, `downgrade`,
  `stamp`, `heads` ou `current`; o diretório `migrations/` não foi tocado.
- **Nenhuma alteração foi realizada no banco.** Nenhuma conexão foi aberta a banco algum
  (produção, homologação ou local); nenhum seed ou script operacional foi executado.
- **Nenhum deploy foi iniciado.** Não houve acesso ao painel do Render, a URLs do
  serviço, nem alteração de `render.yaml`.
- **Nenhum arquivo operacional precisou ser alterado.** A única adição é este documento
  em `Docs/REESTRUTURACAO_COMERCIAL/00_01_BASELINE_GITHUB.md`.
- **Nenhuma dependência foi instalada ou alterada.** A aplicação e a suíte de testes não
  foram executadas.
- **Nenhum segredo ou dado pessoal foi reproduzido.** Localizações sensíveis conhecidas
  (apenas para referência das próximas etapas, sem valores): `criar_cliente_demo.py:17-19`
  (credencial de demonstração), `config.py:82, 139, 158` (placeholders/defaults de
  desenvolvimento), `render.yaml:41-42` e `README.md:336, 341` (endereço de remetente),
  `templates/como_aderir.html:63, 68` (telefone e e-mail placeholder), `LICENSE:3` (nome do
  titular), caminhos locais de máquina em `Docs/AUDITORIA_RENDER.md:5, 9`,
  `NEXO_RENDER_PROGRESS.md:9-10`, `RELATORIO_FINAL_PARA_CHATGPT.md:5`,
  `Docs/OPERACAO_BACKUP_RESTAURACAO.md:259`. `Docs/DER_NEXO_MVP_V4_Completo_Com_Roadmap.docx`
  (binário) não foi inspecionado.
- **A branch `main` não foi alterada.** Nenhum commit, merge ou push atingiu `main`;
  `origin/main` permanece em `8233c5bddbd1f6c67a4d95c7b0a2a470724738c8`.
- **Nenhum comando destrutivo do Git foi usado** (`push --force`, `reset --hard`,
  `rebase`, `amend`, `clean`).

Divergências: nenhuma em relação às condições acima.

---

## H. Preparação para a próxima etapa

**Próxima subetapa: ETAPA 0.2 — Proteção do banco de dados e preparação das migrações.**

Verificações que a Etapa 0.2 precisará realizar (listadas aqui, **não executadas**
nesta etapa). Todas as que tocam o banco exigem autorização explícita, backup verificado
e, preferencialmente, execução contra uma restauração isolada antes de qualquer contato
com produção:

1. **Backup e restauração**: obter backup autorizado do Supabase e validar a restauração
   isolada conforme `Docs/OPERACAO_BACKUP_RESTAURACAO.md`, antes de qualquer DDL.
   `scripts/verificar_prontidao_backup.py` pode conferir ferramentas e dump local sem
   conectar a banco.
2. **Revisão aplicada**: `flask db current` (com `NEXO_DB_DIRECT=1`, `DIRECT_URL`,
   somente leitura) para confirmar se `alembic_version` está em `e4c004a26b01` ou
   `b7c4e2a9f031`; `flask db heads` para confirmar head única (leitura indica
   `e4c004a26b01`).
3. **Paridade schema × modelos** no Postgres real (`compare_metadata`), incluindo
   verificação de que tabelas/índices só do `.sql` avulso (`avaliacao_analise`,
   `fatura_cobranca`, `idx_*`) **não** existem fisicamente.
4. **Nomes reais das constraints** CHECK/UNIQUE/índices gerados pelo Postgres (sem
   `naming_convention`), necessários para alterar enums de plano/status em E4/E5/E6; decidir
   a convenção de nomes para as novas constraints.
5. **Inventário de dados**: linhas da tabela `plano` (valores, níveis, `ativo`),
   empresas por plano e por `status_conta`, existência da conta de demonstração de
   `criar_cliente_demo.py`, referências legadas (fora do formato `db:`) em
   `upload_relatorio.caminho_arquivo` e `guia_topico.imagem_url`, órfãos em
   `arquivo_armazenado`, volume total de BYTEA vs limite do plano Supabase, conteúdo dos
   tópicos de `guia_topico` (identidade acadêmica, planos, contato).
6. **Configuração do serviço no Render** (painel): estado real do Auto-Deploy, Pull
   Request Previews, commit implantado, URL pública, comandos efetivos, variáveis não
   declaradas no YAML (`ANTHROPIC_API_KEY`, `HF_API_TOKEN`, `RATELIMIT_STORAGE_URI`,
   `SOCKETIO_CORS_ORIGINS`), presença de `sslmode` nas URLs de banco. Definir a ordem
   "migrar → liberar código" com Auto-Deploy controlado e proteção da `main`.
7. **Supabase**: versão do PostgreSQL, estado da RLS e da Data API para o schema
   `public`, limites do plano.
8. **Scripts perigosos**: decidir o destino de `criar_cliente_demo.py` (remoção ou
   endurecimento com guarda `__main__`, trava contra Postgres e remoção da credencial) e
   dos `.sql` avulsos (regenerar a partir das migrações ou marcar como histórico).
9. **Plano de novas revisões**: encadear a partir de `e4c004a26b01`; `upgrade`/`downgrade`
   testados em SQLite e PostgreSQL privado (`tests/postgresql_support.py`); incluir novas
   tabelas em `tests/test_backup_restore.py` e nas rotinas de hard delete; considerar pin
   direto de SQLAlchemy/Alembic.
10. **Suíte de testes** no commit de referência (não executada nesta etapa) para
    estabelecer a linha de base de aprovação antes de qualquer mudança.

---

*Documento gerado na Etapa 0.1 da reestruturação comercial do NEXO. Referência:
`origin/main` = `8233c5bddbd1f6c67a4d95c7b0a2a470724738c8`, 2026-10-24.*
