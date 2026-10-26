# NEXO-AJ-00: baseline do projeto

> **Nota de integração (26/10/2026).** Documento produzido na pasta local (sem `.git`) e publicado em `Helio965/Nexo---Faturamento-Inteligente---Render`, indicado pelo proprietário como repositório oficial no pedido de integração de 26/10/2026 (os documentos locais citavam também `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente`; qual repositório o Render publica não foi verificado). A base do ZIP foi confirmada por comparação de conteúdo: o commit `ff8c2d8` da `main` (o `faa59d9` do comentário do ZIP não aparece em nenhuma branch nem PR deste repositório). Afirmações como "sem `.git`", "sem acesso ao remoto" e "VERSÃO NÃO VERIFICADA" descrevem a execução original e foram superadas pelo [relatório da integração](../INTEGRACOES/RELATORIO_INTEGRACAO_GITHUB_ZIP_2026_10_26.md). Caminhos locais com o nome do usuário do Windows foram anonimizados como `%USERPROFILE%`, e o nome de uma conta GitHub de terceiro e de projetos sem relação foram generalizados; o restante do conteúdo foi preservado. As constatações de que o CLIENTE de empresa `CANCELADA` mantém acesso foram corrigidas pela NEXO-AJ-06.1, integrada junto; `SUSPENSA` e a lixeira mantêm o comportamento.

**Etapa 00 (subetapas 0.1 e 0.2): preparação, baseline e proteção do projeto NEXO: Faturamento Inteligente.**

Esta é a referência técnica do estado do projeto antes dos ajustes NEXO-AJ. **Nenhum código, template, CSS, migração, banco, upload ou configuração de deploy foi alterado.** Não houve acesso a Supabase, Render, DNS, GitHub nem a qualquer serviço externo, e nenhum comando Git foi executado na pasta de trabalho.

Legenda usada em todo o documento:

| Classificação | Significado |
|---|---|
| **COMPROVADO NO CÓDIGO** | Lido em código, configuração, migração, template ou teste, com `arquivo:linha` |
| **TESTADO LOCALMENTE** | Confirmado por execução nesta máquina, em cópia isolada, com dados fictícios |
| **DOCUMENTAL** | Só aparece em documentação |
| **PENDENTE DE TESTE** | Só uma execução, ou um acesso autorizado, comprovaria |
| **HIPÓTESE** | Inferência plausível, não comprovada |

---

## 1. Identificação

| Item | Valor |
|---|---|
| Data e hora local | 25/10/2026, das 10:51 às 11:25 (UTC−3, fuso `E. South America Standard Time`) |
| Executor | Claude Code (Claude Opus 5.5), a pedido do responsável pelo projeto |
| Sistema operacional | Windows 11 Pro 10.0.26200, 64 bits |
| Python usado nas verificações | 3.12.10 do usuário, sem ambiente virtual. `pytest` não está instalado; a suíte do projeto usa `unittest` |
| Raiz do projeto | `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente` |
| Sinais que confirmam a raiz | `app.py`, `models.py`, `blueprints/`, `templates/`, `migrations/`, `render.yaml` e `requirements.txt` presentes |
| Git | **A pasta não é um repositório Git**: não há `.git` nela nem em pastas acima. Nenhum branch ou commit é atribuído a ela. `git init` não foi executado |
| Arquivos na pasta antes desta etapa | 265 (inventário SHA-256 completo no checkpoint, seção 8) |

### 1.1 ZIP de origem

| Item | Valor |
|---|---|
| Arquivo | `%USERPROFILE%\Downloads\Nexo-Faturamento-Inteligente-main.zip` |
| Tamanho | 18.417.690 bytes |
| Data de modificação | 24/10/2026 16:55:03 |
| SHA-256 | `C308B3A0C6954D7CB0DC704783E94A8BBD870E03924D0646793BC991984D1A33` |
| Entradas | 293: 258 arquivos e 35 diretórios, sob o prefixo `Nexo-Faturamento-Inteligente-main/` |
| Comentário do ZIP | `faa59d98a6352c4e076ba11d4469c81486e13474`. O `git archive`, usado pelo GitHub para gerar ZIPs, grava ali o commit arquivado. **Não foi possível confirmar esse commit em repositório**, porque não há Git nem rede autorizada |

### 1.2 Pasta de trabalho comparada com o ZIP (COMPROVADO, por hash)

| Situação | Qtde | Arquivos |
|---|---|---|
| Idênticos ao ZIP | 251 | — |
| Modificados pela Etapa 0.2A (24/10/2026) | 7 | `.gitignore`, `Docs/OPERACAO_BACKUP_RESTAURACAO.md`, `Docs/PLANO_PUBLICACAO_SEGURA.md`, `Docs/PREPARACAO_RENDER.md`, `scripts/verificar_prontidao_backup.py`, `tests/test_backup_readiness.py`, `tests/test_backup_restore.py` (relação e motivos em `Docs/REESTRUTURACAO_COMERCIAL/00_02_PROTECAO_BANCO_MIGRACOES.md:375-386`) |
| Acrescentados | 7 | `Docs/REESTRUTURACAO_COMERCIAL/00_02_PROTECAO_BANCO_MIGRACOES.md` (Etapa 0.2A) e os 6 arquivos de `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/` (imagens e README do responsável, salvos nesta mesma sessão de 25/10, **antes** da NEXO-AJ-00) |
| Ausentes | 0 | — |

Não há `.env`, `instance/`, banco (`*.db`, `*.sqlite*`), `__pycache__`, `.venv` nem upload real na pasta. `uploads/` e `static/uploads/guia/` contêm só `.gitkeep`.

### 1.3 Outras cópias e fontes encontradas (nenhuma foi alterada)

| Caminho | O que é | Observação |
|---|---|---|
| `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente.zip` (24/10/2026 21:36, 18.468.287 bytes) | 259 arquivos, **idênticos por hash** aos da pasta atual | Estado pós-0.2A, sem os insumos de 25/10. É um ponto de reversão anterior, criado pelo responsável. **[Complemento de 25/10/2026]** Regravado às 11:28, fora desta execução: agora tem 19.137.330 bytes e os 268 arquivos pós-AJ-00 (SHA-256 `1C359F29…DBBB95720`), e não é mais o estado pós-0.2A |
| `C:\ADS\Nexo - Faturamento Inteligente\Nexo.zip` (24/10/2026 16:58, 88.242.414 bytes, 15.229 entradas) | Cópia da pasta antiga `Nexo/` | **Contém, pelos nomes das entradas, arquivos `.env`, um backup de `.env` e um banco SQLite com arquivos WAL/SHM.** O conteúdo não foi aberto. **Não compartilhar** |
| `C:\ADS\Nexo - Faturamento Inteligente\Nexo\Nexo-Faturamento-Inteligente\` | Clone Git antigo. Remoto `<conta de terceiro>/Nexo-Faturamento-Inteligente`, HEAD `2152781` (20/06/2026), 19 alterações locais | Não contém nenhum dos commits de referência (`faa59d9`, `c919b1d`, `8233c5b`, `ff8c2d8`). Tem `.env` e `instance/` locais, que não foram abertos. **Não é a pasta alvo** |
| `C:\ADS\Nexo - Faturamento Inteligente\Documentos\` | Documentos acadêmicos (PI) de 8, 10 e 13 tabelas e planilhas de base | Histórico; não representam a versão atual |
| `%USERPROFILE%\Downloads\NEXO_DOCUMENTO_MESTRE_ETAPAS_SUBETAPAS_E_STATUS.docx` (634.977 bytes, 24/10/2026 14:43) | Documento Mestre v1.0 | Base `c919b1d`, corte das evidências às 14h40 de 24/10/2026. Usa as Etapas 1 a 8, não os IDs `NEXO-AJ` |
| `%USERPROFILE%\Downloads\nexo_cubo_centralizado.png` (260.224 bytes, 640×641) | Nova arte da logo (só o cubo) | SHA-256 `FF29A45F…2B16B6D`, **idêntico** a `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/01_logo_cubo_sem_texto.png` |
| `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md` | Mapa dos 27 prompts | Primeira entrega: **não encontrado nesta máquina**. **[Complemento de 25/10/2026]** Recebido em `Downloads\NEXO_MAPA_27_PROMPTS_PARA_CLAUDE_CODE.zip` e copiado sem alteração para a raiz do projeto (364 linhas, SHA-256 `B59E9D72…EFDEED67`). Controle completado em `CONTROLE_PROMPTS.md`. As buscas da primeira entrega estão registradas no histórico de `CONTROLE_PROMPTS.md` |

---

## 2. Arquitetura atual (COMPROVADO NO CÓDIGO)

| Camada | Componente | Evidência |
|---|---|---|
| Aplicação | Flask com fábrica `create_app()`. O ambiente vem de `FLASK_ENV`. Em produção há travas para `SECRET_KEY`, `DATABASE_URL`, `DIRECT_URL` e PostgreSQL. `BOOT_ID` muda a cada boot e invalida sessões | `app.py:60-102` |
| Extensões | SQLAlchemy 2.x, Flask-Login, Flask-Migrate, Flask-Mail, Flask-SocketIO (`threading`), CSRFProtect, Flask-Limiter (por IP, memória) | `extensions.py:26-44`; `app.py:110-124` |
| Guardas globais | Revalidação da sessão a cada requisição, bloqueio de NUL e primeiro acesso | `app.py:159-229` |
| Rotas | 42 rotas HTTP: admin 20, cliente 8, auth 6, notificações 2, api 1 e raiz 5 (`/midia/<chave>`, `/`, `/como-aderir`, `/healthz`, `/healthz/db`); mais 4 handlers Socket.IO | `app.py:238-242,261-301`; `realtime.py:147-190` |
| ETL | Pandas e openpyxl num **subprocesso isolado** com limites de recursos e bloqueio de rede. Exige o módulo POSIX `resource`: no Windows recusa com `code="platform"` | `etl_runtime.py:62-66`; `etl_worker.py:19-33` |
| Arquivos | Planilhas guardadas inteiras no banco (`arquivo_armazenado`, BYTEA), com cache temporário em `%TEMP%/nexo_arquivos` | `storage.py:8-11,41,52-64` |
| PDF | ReportLab, `gerar_pdf_analise` | `pdf_export.py:231` |
| IA | Devolutiva pela Anthropic (síncrona, dentro da requisição do admin), com fallback local | `ai_devolutiva.py:110-147`; `blueprints/admin.py:744-756` |
| NexoBot | `suporte_bot.py` e pacote `nexobot/` (32 módulos). Redação opcional pelo roteador Hugging Face | `nexobot/providers.py:26` |
| Tempo real | Salas `user_<id>_<impressão>`, varredura de 1 s | `realtime.py:41-42,102-105` |
| Notificações e e-mail | Notificações após o COMMIT; e-mail em thread por Brevo (HTTPS) ou SMTP | `notifications.py:80-143`; `emails.py:64-101` |

### 2.1 Mapa de pastas

| Pasta | Conteúdo (sem abrir dados privados) |
|---|---|
| `blueprints/` | `auth`, `admin`, `cliente`, `notificacoes`, `api` |
| `templates/` | 38 HTML: raiz 7, `admin/` 13, `auth/` 6, `cliente/` 7, `emails/` 5 |
| `static/` | `css/` 2, `js/` 4 (`nexo.js` com 0 byte), `img/` 1 (`nexo-logo.jpeg`), `video/` 4 (MP4 de 11,9 MB), `uploads/guia/.gitkeep` |
| `tests/` | 33 `test_*.py`, 4 módulos de apoio, 5 suítes `postgresql_*` (só POSIX) e 1 fixture JSON |
| `migrations/` | Alembic com 8 revisões em cadeia linear |
| `Docs/` | 59 arquivos antes desta etapa: relatórios SEC, Render, backup, NexoBot e as pastas `REESTRUTURACAO_COMERCIAL/` e `nexobot/evidencias/` |
| `scripts/`, `tools/` | `verificar_prontidao_backup.py`; `install_dependencies.py`, `auditar_guia.py`, `measure_etl_resources.py` e `nexo-motion/` (vídeo em Remotion) |
| `uploads/` | Só `.gitkeep` |

### 2.2 Infraestrutura: local × produção

| Aspecto | Local (verificado) | Produção (só **configuração declarada**, não verificada) |
|---|---|---|
| Banco | Sem `DATABASE_URL`, SQLite em `instance/nexo_mvp.db` (`config.py:54-57`). Nenhum banco na pasta hoje | PostgreSQL no Supabase: pooled para a aplicação e `DIRECT_URL` para migrações (`config.py:127-136`). SSL não é forçado pelo código (`config.py:29-45`) |
| `.env` | `config.py:23` lê só `<raiz>/.env`, que não existe | Variáveis no painel do Render |
| Servidor | `python app.py` em 127.0.0.1:5000 (`app.py:368-369`) | `render.yaml:8-22`: um Web Service, `plan: free`, `region: oregon`, `branch: main`, `autoDeployTrigger: 'off'`, gunicorn 1 worker e 50 threads, healthcheck `/healthz` |
| Variáveis declaradas | — | `PYTHON_VERSION`, `FLASK_ENV`, `SECRET_KEY`, `PROXY_FIX_HOPS`, `DATABASE_URL`, `DIRECT_URL`, `BREVO_API_KEY`, `MAIL_DEFAULT_SENDER` (`render.yaml:23-42`). **Não declaradas:** `ANTHROPIC_API_KEY`, `HF_API_TOKEN`, `SOCKETIO_CORS_ORIGINS` |
| Agendamento | — | **Inexistente**: sem cron, worker, APScheduler ou Celery (`render.yaml:8`; `requirements.txt`) |
| CI | — | `.github/workflows/nexo-security-ci.yml`: jobs `sqlite-browser` e `postgresql-security` em ubuntu-24.04, com `PYTHONUTF8=1` |

O estado real do painel do Render, do Supabase, do DNS e do provedor de e-mail **não foi verificado** (PENDENTE DE TESTE, depende de acesso autorizado).

---

## 3. Modelos e banco

### 3.1 Modelos (COMPROVADO NO CÓDIGO: 14 modelos, 14 tabelas; 15 com `alembic_version`)

| # | Modelo (linha) | Tabela (linha) |
|---|---|---|
| 1 | `Plano` (`models.py:37`) | `plano` (`:38`) |
| 2 | `Segmento` (`:67`) | `segmento` (`:68`) |
| 3 | `Empresa` (`:83`) | `empresa` (`:84`) |
| 4 | `Usuario` (`:120`) | `usuario` (`:125`) |
| 5 | `Analise` (`:192`) | `analise` (`:193`) |
| 6 | `UploadRelatorio` (`:262`) | `upload_relatorio` (`:263`) |
| 7 | `IndicadorAnalise` (`:305`) | `indicador_analise` (`:306`) |
| 8 | `RelatorioAnalise` (`:336`) | `relatorio_analise` (`:337`) |
| 9 | `ProdutoCurvaABC` (`:365`) | `produto_curva_abc` (`:381`) |
| 10 | `ChamadoSuporte` (`:408`) | `chamado_suporte` (`:419`) |
| 11 | `MensagemSuporte` (`:457`) | `mensagem_suporte` (`:459`) |
| 12 | `Notificacao` (`:481`) | `notificacao` (`:487`) |
| 13 | `GuiaTopico` (`:508`) | `guia_topico` (`:517`) |
| 14 | `ArquivoArmazenado` (`:538`) | `arquivo_armazenado` (`:549`) |

O teste de backup exige 15 tabelas no banco migrado (`tests/test_backup_restore.py:118`). Divergências documentais estão na seção 5.

### 3.2 Migrações (COMPROVADO NO CÓDIGO)

Cadeia linear, sem ramificação: `d87a6fbc2fbe` (12 tabelas) → `c7189696a9cd` (período-base) → `f958d38a7f19` (`gerado_por_ia`) → `91a2ecf56a41` (`primeiro_acesso`) → `d61b5e68082c` (`guia_topico`) → `a3f1c9b27d04` (`deletado_em`) → `b7c4e2a9f031` (`arquivo_armazenado`) → **`e4c004a26b01`** (head: `geracao_autorizacao` e um UPDATE que desativa clientes de empresas na lixeira; o downgrade não restaura esse estado, `e4c004a26b01_company_authorization_generation.py:10-13,56-67`).

**Estado dos bancos:** não há banco local na pasta. A revisão aplicada em produção **não é conhecida** (PENDENTE DE TESTE; `Docs/PREPARACAO_RENDER.md:89`; `00_02`, seção C.4). Nenhuma migração foi executada.

---

## 4. Testes

| Item | Situação |
|---|---|
| Framework | `unittest`. Não há `pytest.ini`, `conftest.py` nem `pyproject.toml`, e pytest não está em `requirements-dev.txt` |
| Isolamento | `tests/__init__.py:3-5` → `ensure_test_environment()` redefine 23 variáveis, com SQLite em `.audit_tmp` e chaves vazias (`tests/deploy_support.py:24-39`). Rede bloqueada por patch de socket (`:53-55`) e `dotenv.load_dotenv` neutralizado (`:57`) |
| Opt-ins | `NEXO_TEST_BROWSER=1` + Playwright; `NEXO_TEST_POSTGRES_BIN` (ensaio de backup; suítes PG só em POSIX) |
| Gravações na raiz | `.audit_tmp/` e `instance/` (ambos no `.gitignore`). Por isso, nesta etapa a suíte rodou numa **cópia** do checkpoint, fora da pasta |
| Resultado nesta etapa | **569 testes: 13 falhas, 12 erros, 42 ignorados**, em duas execuções idênticas. É o mesmo total da linha de base pós-0.2A (`00_02`, E15). Todas as falhas são de ambiente; detalhes no relatório desta etapa, seção 9 |

---

## 5. Divergências entre ZIP, Documento Mestre, documentos e regras pedidas

| # | Tema | O que diverge | Evidência | Classificação |
|---|---|---|---|---|
| D1 | Commit de base | O Documento Mestre usa `c919b1d` (24/10, 10:46, merge da PR #19). O ZIP traz `faa59d9` no comentário. `00_01` usa `8233c5b` e `00_02` cita `ff8c2d8` como histórico | Documento Mestre, "Identificação do projeto"; comentário do ZIP; `00_01_BASELINE_GITHUB.md:40`; `00_02_PROTECAO_BANCO_MIGRACOES.md:40` | COMPROVADO (valores); relação entre os commits NÃO VERIFICADA |
| D2 | Conteúdo do ZIP posterior ao Documento Mestre | O Documento Mestre (corte às 14h40) diz que as PRs #20 (NexoBot Advanced) e #21 (landing COM-001) **não estavam integradas**, mas o ZIP (16:55) contém seus artefatos: `Docs/NEXOBOT_ADVANCED.md`, `Docs/PLANO_ACAO_COMERCIAL_LANDING_NEXO.md`, `Docs/RELATORIO_NEXO_COM001_LANDING_COMERCIAL.md`, `Docs/PENDENCIAS_NEXO_COM002_AVALIACOES.md`, `tests/test_landing_commercial.py`, `tests/test_landing_video_commercial.py` | Documento Mestre, seções A (PRs abertas) e Etapa 6; presença dos arquivos no ZIP | COMPROVADO (presença). HIPÓTESE: `faa59d9` integra as PRs #20 e #21 depois de `c919b1d` |
| D3 | Repositório | Documento Mestre: `Helio965/Nexo---Faturamento-Inteligente---Render`. `00_02:40-41`: esse mesmo como referência e `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente` como destino oficial. O prefixo do ZIP (`Nexo-Faturamento-Inteligente-main/`) indica um repositório chamado `Nexo-Faturamento-Inteligente` | Documento Mestre, "Identificação do projeto"; `00_02:40-41`; prefixo do ZIP | HIPÓTESE: o ZIP veio do repositório de destino oficial |
| D4 | Quantidade de tabelas | Código: 14. `models.py:4` diz 8 e `models.py:9-11` diz que chamado/mensagem não têm Model. `README.md:142` e `Docs/RELATORIO_TECNICO.md:13` dizem 13. `schema_nexo_mvp_v4.sql` tem 14 `CREATE TABLE`, mas outro conjunto (`avaliacao_analise` `:351` e `fatura_cobranca` `:368`, sem `guia_topico` e `arquivo_armazenado`). `Docs/schema_nexo_mvp_v4 (1).sql` tem 12. Os documentos acadêmicos de 8, 10 e 12 tabelas são históricos | Linhas citadas | COMPROVADO. **Os documentos de 12 tabelas não representam a versão atual** |
| D5 | Migrações documentadas | `Docs/RELATORIO_TECNICO.md:49` fala em "6 migrações" reversíveis e `Docs/AUDITORIA_RENDER.md:76` em 7 com head `b7c4e2a9f031`. Existem 8, com head `e4c004a26b01` não reversível | Linhas citadas | COMPROVADO |
| D6 | Preços | O seed grava Bronze 600, Prata 1000 e Ouro 1400 (`seed.py:35,45,55`). Pedido: 150, 300 e 650. A landing mostra "Sob consulta" (`templates/landing.html:383,396,410`), exigido por `tests/test_landing_commercial.py:132`. O NexoBot proíbe preços (`nexobot/saber/empresas_planos.py:220`; `tests/test_nexobot_saber.py:29-30`) | Linhas citadas | COMPROVADO. Valor em produção: PENDENTE DE TESTE |
| D7 | Conta cancelada | Pedido: tela bloqueada ou desfocada. Código: empresa CANCELADA entra, mantém a sessão e acessa tudo (seção 6). Um teste **trava** esse comportamento (`tests/test_company_restore_security.py:431-444`) e o NexoBot o descreve (`nexobot/saber/empresas_planos.py:135-137,165-167`) | Linhas citadas | COMPROVADO NO CÓDIGO e TESTADO LOCALMENTE |
| D8 | Suspensão | Pedido: consulta só do período pago e PDF por 14 dias. Código: consulta e PDF sem status nem prazo (`blueprints/cliente.py:240-292`) | Linhas citadas | COMPROVADO |
| D9 | Contrato | Pedido: tudo por contrato, com vigência e prorrogação. Código: só `Empresa.data_contratacao` (`models.py:94`), sem uso em cálculos. `fatura_cobranca` existe só no SQL avulso (`schema_nexo_mvp_v4.sql:364-387`) | Linhas citadas | COMPROVADO |
| D10 | Aviso de renovação | Pedido: 7 a 14 dias antes do vencimento. Código: sem vencimento modelado e sem agendador (`render.yaml:8`; `requirements.txt`) | Linhas citadas | COMPROVADO |
| D11 | Logo | Pedido: só o cubo. Código: `nexo-logo.jpeg` (com texto e marca ✦) em 7 templates; a landing usa um quadrado com "N" (`templates/landing.html:23,448`) | Seção 7 | COMPROVADO |
| D12 | Domínio | Pedido: "nome em vez de IP". O repositório não tem IP público nem domínio próprio. Falta URL canônica (`SERVER_NAME`) e `SOCKETIO_CORS_ORIGINS` não está no `render.yaml` | `config.py:109-118`; `blueprints/auth.py:355,359` | COMPROVADO (código); DNS real: PENDENTE |
| D13 | LGPD | Pedido: revisão. A landing declara que privacidade e termos "ainda não foram publicados" (`templates/landing.html:464-465`) | Linha citada | COMPROVADO |
| D14 | Versões locais × fixadas | Local: Flask 3.0.3, Werkzeug 3.0.4, Flask-SocketIO 5.4.1, python-dotenv 1.0.1, Pillow 12.2.0. Fixadas: 3.1.3, 3.1.9, 5.6.1, 1.2.4, 13.0.0 (`requirements.txt:6,9,10,23,26`). Ausentes no ambiente: `gunicorn` (`:34`) e `PyYAML` (`requirements-dev.txt:2`). O Documento Mestre cita Flask 3.1 | `pip list` local | COMPROVADO. Explica 7 falhas (Werkzeug 2, Flask 4 subtestes, python-dotenv 1) e os 2 erros de importação |
| D15 | Auto-Deploy | `render.yaml:18` declara `'off'`, mas `Docs/PREPARACAO_RENDER.md:83` registra que o responsável informou Auto-Deploy **ativado** | Linhas citadas | DOCUMENTAL; painel: PENDENTE |
| D16 | Numeração das etapas | Documento Mestre: Etapas 1 a 8. `Docs/REESTRUTURACAO_COMERCIAL/`: Etapas 0.1 e 0.2A. Prompt atual: `NEXO-AJ-00` a `NEXO-AJ-xx` (27 prompts). Sem o mapa, não há tabela de correspondência. **[Complemento de 25/10/2026]** O mapa define as etapas NEXO-AJ 00 a 09 como plano complementar, que não substitui as 8 etapas nem os códigos COM/SEC do Documento Mestre (mapa:17). A correspondência dos 27 IDs está em `CONTROLE_PROMPTS.md` | Mapa:17,22-33 | DOCUMENTAL |

---

## 6. Controle de acesso por status da conta (achado prioritário)

**Confirmado:** `usuario_pode_acessar()` não bloqueia `status_conta = CANCELADA` nem `SUSPENSA`.

| Linha | O que a função verifica |
|---|---|
| `session_security.py:43-45` | Usuário inexistente, inativo ou com papel inválido → nega |
| `:46-47` | ADMIN: exige não ter empresa |
| `:48-49` | CLIENTE sem empresa → nega |
| `:53-57` | Empresa existe com `deletado_em IS NULL`. É **a única condição sobre a empresa**: a lixeira |

Consequências, todas COMPROVADAS NO CÓDIGO:

- Login de empresa CANCELADA é aceito (`blueprints/auth.py:268-280`).
- Uma sessão já aberta continua válida depois da troca de status. A edição do admin (`blueprints/admin.py:433-435`) não incrementa `geracao_autorizacao`; a lixeira incrementa (`company_security.py:58-59`).
- Socket.IO conecta e recebe notificações (`realtime.py:147-152`; `notifications.py:70`).
- Tokens de ativação e recuperação de senha são aceitos (`blueprints/auth.py:110,153,352-360`).
- Consulta, histórico e PDF funcionam sem status nem prazo (`blueprints/cliente.py:139-292`).
- Upload em análise aberta continua aceito (`blueprints/cliente.py:307-351`).
- E-mails continuam sendo enviados à empresa cancelada (`emails.py:104-112`).

**TESTADO LOCALMENTE:** `tests/test_company_restore_security.py:431-444` faz login como cliente de empresa SUSPENSA e CANCELADA e espera 200 numa rota protegida. O teste **passou** nas duas execuções desta etapa.

**Cancelamento não é lixeira:** `deletado_em` (`models.py:101-104`) bloqueia o acesso e revoga sessões; `status_conta` (`models.py:96,113`) é só um rótulo editado à mão, sem efeito de autorização. A única guarda de status no servidor é a abertura de análise (`blueprints/admin.py:230-232`). O risco já estava registrado como F2.2 em `00_01_BASELINE_GITHUB.md:603`. **Nada foi corrigido nesta etapa.**

---

## 7. Pontos dos futuros ajustes (localizados, não implementados)

| Tema | Onde está hoje |
|---|---|
| Logo | `static/img/nexo-logo.jpeg` (1024×1024, com texto e marca ✦) em `templates/base.html:42-43` (`.brand-logo`, 42×42 px, `static/css/nexo.css:251-260`) e em 6 telas com `.auth-logo` (88×88 px, `nexo.css:158-166`): `templates/auth/login.html:11-12`, `auth/primeiro_acesso.html:7`, `auth/primeiro_acesso_token.html:7`, `auth/recuperar_senha.html:7`, `auth/resetar_senha.html:7`, `como_aderir.html:7`. A landing usa "N" em `.brand-mark` (`templates/landing.html:23,448`; `static/css/landing.css:135-142,967`). E-mails e PDF escrevem "NEXO" em texto (`templates/emails/_base.html:10-12`; `pdf_export.py:92`). Não há favicon nem `og:image`. A arte nova é `nexo_cubo_centralizado.png` (640×641, com anel branco e fundo escuro) |
| Preços | `seed.py:35,45,55`; `plano.valor_mensal` (`models.py:43`), uma linha por plano (`models.py:41,56`); receita estimada `SUM(valor_mensal)` de empresas ATIVAS fora da lixeira (`blueprints/admin.py:72-79`); rótulo do formulário (`templates/admin/empresa_form.html:92`). Não há tela para editar planos |
| Contratos | Só `Empresa.data_contratacao` (`models.py:94`). Sem vigência, histórico, prorrogação nem datas de suspensão e cancelamento. A troca de plano sobrescreve `id_plano_atual` (`blueprints/admin.py:426`); a análise guarda só a chave do plano (`models.py:197`) |
| Renovação | Notificações (`notifications.py:146,158,168`) e e-mails (`emails.py:77,118-149`) só disparados em requisições HTTP. Sem agendador. `Notificacao` sem tipo nem deduplicação (`models.py:489-496`). Links absolutos dependem do Host da requisição (`blueprints/admin.py:868`) |
| Suspensão e cancelamento | Seção 6 |
| LGPD | Dados pessoais em `empresa` (`models.py:89-95`), `usuario` (`:129-144`), textos livres (`:424,464,491`) e planilhas inteiras (`:552`). Terceiros: Anthropic (`ai_devolutiva.py:63-147`), Hugging Face (`nexobot/providers.py:26,55-65`), Brevo/SMTP (`emails.py:33-61`), Render (Oregon, EUA) e Supabase (`render.yaml:11-13`), além de Google Fonts, jsDelivr e cdn.socket.io em todas as páginas (`templates/base.html:13,16-17,192,194,368`). Sem política de privacidade, termos, aviso de cookies nem encarregado (`templates/landing.html:464-465`). Sem rotina de retenção. A exclusão permanente deixa notificações de ADMIN com dados da empresa (`blueprints/admin.py:588-594`; `00_02`, B4.1). Inventário inicial: **não conclui conformidade** |
| Domínio | `render.yaml` sem `domains:`. Sem `SERVER_NAME`, `PREFERRED_URL_SCHEME` ou `TRUSTED_HOSTS`. Links de e-mail com `url_for(..., _external=True)` (`blueprints/auth.py:355,359`; `blueprints/admin.py:386,868,1092`). CORS do Socket.IO por `SOCKETIO_CORS_ORIGINS` + `RENDER_EXTERNAL_URL` (`config.py:109-118`). Cookie Secure só em produção (`config.py:205`); sem HSTS nem CSP global. Remetente Gmail fixo por padrão (`config.py:156-159`) |

---

## 8. Ponto de reversão

| Item | Valor |
|---|---|
| Checkpoint | `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\NEXO_checkpoint_pre-AJ-00_2026-10-25.zip` |
| Conteúdo | 265 arquivos (estado anterior aos documentos desta etapa), conferidos **265 de 265 idênticos** por SHA-256 |
| SHA-256 | `56886D00074010C39172310E83A50306DE75D0C4623E3C5E3B6BD0B04AD9C8FA` (19.080.971 bytes) |
| Manifesto | `MANIFESTO_SHA256_pre-AJ-00.json`, SHA-256 `30F077C5…548B1EC2` |
| Exclusões aplicadas | `.env*` (exceto `.env.example`), bancos, dumps, logs, chaves, caches, ambientes virtuais, `instance/`, `.audit_tmp/` e uploads que não sejam `.gitkeep`. **Nenhum arquivo se enquadrou** |
| Como restaurar | `LEIA-ME.txt` na mesma pasta |

---

## 9. Premissas verificadas × hipóteses

**Verificadas:**

- A pasta alvo é `C:\ADS\…\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente`, sem Git.
- A pasta contém o ZIP `faa59d9` mais as alterações da 0.2A e os insumos de 25/10.
- O projeto tem 14 modelos e 8 migrações, com head `e4c004a26b01`.
- Não há `.env` nem banco na pasta, e o processo de teste não tinha credenciais.
- CANCELADA e SUSPENSA não restringem o acesso (código e teste executado).
- Os preços do seed são 600, 1000 e 1400.
- Não existe agendador.
- Não há política de privacidade publicada.
- A suíte dá 569 testes com 13 falhas, 12 erros e 42 ignorados, todos de ambiente.

**Hipóteses e pendências:**

- `faa59d9` é posterior a `c919b1d` e integra as PRs #20 e #21.
- O ZIP veio do repositório `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente`.
- Não se sabe:
  - qual revisão está aplicada em produção;
  - qual `valor_mensal` está em produção e quantas empresas há por plano;
  - qual é a configuração real do Auto-Deploy;
  - se existe domínio próprio registrado.
- As falhas da suíte local tendem a não ocorrer em Linux/CI, com as versões fixadas e `PYTHONUTF8=1`. Isso não foi verificado nesta etapa.

---

## 10. Riscos e dependências para os próximos IDs

Sem o mapa, a lista está organizada por tema, não por ID. **[Complemento de 25/10/2026]** Correspondência com o mapa oficial:

| Tema | Prompts |
|---|---|
| Logo | `NEXO-AJ-01` |
| Preços | `02` |
| Contratos | `03.1` a `03.4` |
| Renovação | `04.1` a `04.3` |
| Suspensão | `05.1` a `05.5` |
| Cancelamento | `06.1` a `06.4` (`06.1` é o próximo) |
| LGPD | `07.1` a `07.4` |
| Domínio | `08` |
| Ambiente local e validação | `09.1` a `09.3` |

A pendência "Mapa ausente" da linha "Todos" foi resolvida.

| Tema | Dependência ou risco | Antes de começar |
|---|---|---|
| Todos | Mapa ausente; commit-base não confirmado no GitHub; dúvidas do responsável em aberto (`Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/README.md:62-70`) | Colocar o mapa na pasta; confirmar se `faa59d9` é a `main` oficial |
| Cancelamento e suspensão (o prompt indica `NEXO-AJ-06.1` como próximo) | Reescrever `tests/test_company_restore_security.py:431-444`; revogar sessões e sockets na troca de status, como a lixeira já faz; tokens, e-mails e textos do NexoBot. Prazos de 14 dias e 3 meses exigem datas que ainda não existem | Decidir se a conta cancelada ainda entra (tela desfocada) ou se o login é bloqueado |
| Contratos | Nova migração (9ª revisão) com CHECKs sem nome (`00_02`, B.1). A revisão de produção é desconhecida e o Auto-Deploy pode estar ativo | Seguir `00_02`, seções G, H e K; backup real autorizado antes de migrar a produção |
| Renovação | Depende de vencimento modelado. O Render Free hiberna, então um agendador dentro do processo não é confiável. Links fora de requisição precisam de URL canônica. `Notificacao` não tem deduplicação | Escolher o mecanismo de disparo (cron externo, Render Cron, etc.) |
| Preços | É atualização de dados, não só do seed. Uma linha por plano faz a mudança valer retroativamente; não há tela de edição; landing, teste e NexoBot mudam se os preços forem publicados | Responder se contratos vigentes mantêm o preço antigo |
| Logo | 7 templates, 2 tamanhos de CSS e a marca "N" da landing. A arte nova tem anel e fundo escuro, ruins em 42 px | Decidir onde trocar e se haverá recorte transparente |
| LGPD | Política, termos, encarregado, retenção, terceiros e transferência internacional | Definir se a revisão é documento, sistema ou ambos |
| Domínio | `SOCKETIO_CORS_ORIGINS`, URL canônica, remetente de e-mail, HSTS. A configuração do DNS e do painel é externa | Autorização expressa para mexer em Render e DNS |
| Ambiente local | ETL recusado no Windows; versões locais diferentes das fixadas; `gunicorn` e `PyYAML` ausentes | Validar entregas que mexem em ETL, upload ou dependências em Linux/CI |
