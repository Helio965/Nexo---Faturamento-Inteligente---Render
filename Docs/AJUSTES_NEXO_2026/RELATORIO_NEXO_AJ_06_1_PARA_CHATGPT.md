# Relatório NEXO-AJ-06.1 para revisão

Correção prioritária do bloqueio de empresas CANCELADAS (Etapa 06, Contas Canceladas, subetapa 06.1). Controle dos prompts em [`CONTROLE_PROMPTS.md`](CONTROLE_PROMPTS.md). Escopo e aceite oficiais: mapa, linhas 199-205.

**Status final: CONCLUÍDO PARA REVISÃO.** A aprovação depende da revisão independente e do responsável. Nenhum status "APROVADO" foi registrado.

---

## 14.1 Identificação

| Item | Valor |
|---|---|
| Projeto | NEXO: Faturamento Inteligente |
| Subetapa | `NEXO-AJ-06.1`, Correção prioritária do bloqueio CANCELADA (SUBETAPA, depende de `00`) |
| Data da execução | 25/10/2026, das 13:49 às 14:38 (UTC−3). **[Complemento Linux]** das 15:10 às 15:18: suíte em Linux (WSL) com as dependências fixadas, autorizada pelo responsável |
| Pasta | `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente` (sem `.git`) |
| Versão identificada | Pasta local = ZIP `Nexo-Faturamento-Inteligente-main.zip` (comentário do ZIP: commit `faa59d98a6352c4e076ba11d4469c81486e13474`), mais as alterações documentadas da Etapa 0.2A, da NEXO-AJ-00 e desta subetapa. **Equivalência com o remoto: VERSÃO NÃO VERIFICADA** (seção 14.3) |
| Status final | **CONCLUÍDO PARA REVISÃO** |

## 14.2 Resumo executivo

**Problema.** `usuario_pode_acessar()` só considerava a lixeira (`Empresa.deletado_em`) e ignorava `status_conta`. Um CLIENTE de empresa CANCELADA:
- fazia login;
- mantinha sessões antigas;
- abria Socket.IO e recebia notificações;
- usava tokens de senha;
- consultava análises, exportava PDF, enviava arquivos e usava a API do NexoBot.

Um teste existente garantia esse comportamento (`tests/test_company_restore_security.py:443-444` na versão anterior). A troca de status pelo ADMIN também não revogava nenhuma sessão.

**Correção.**
- **Critério único:** "empresa acessível" passa a ser fora da lixeira **e** não CANCELADA. Ele é aplicado na autorização central, que já é consultada a cada requisição HTTP, no handshake e nos eventos Socket.IO, na varredura de sockets, no login, nos tokens de senha e na entrega e criação de notificações.
- **Revogação:** entrar em CANCELADA ou sair dela incrementa `geracao_autorizacao` dos CLIENTE, na mesma transação e com o mesmo protocolo de locks da lixeira. Sessões e cookies anteriores morrem, e a reativação exige novo login.
- **Formulário do ADMIN:** passou a ser protegido contra reativação silenciosa (formulário desatualizado ou sem o campo de status).

**Protegido para CANCELADA:**
- login;
- sessão já aberta;
- todas as rotas por URL direta (dashboard, histórico, análise, PDF, upload, suporte, guia, primeiro acesso);
- API do NexoBot;
- rotas de notificações;
- Socket.IO, tanto conexões novas quanto antigas e eventos autenticados;
- tokens de ativação e recuperação;
- troca de senha.

SUSPENSA e ADMIN mantêm exatamente o acesso anterior. A lixeira continua independente.

**Pendente** (seção 14.11):
- confirmar a versão no GitHub (não verificável sem acesso);
- rodar a CI. **[Complemento Linux]** A suíte em Linux com as dependências fixadas já passou no WSL (seção 14.7: 638 testes, 0 falhas). Faltam só o PostgreSQL real, o navegador e o `pdftotext`, que no Linux exigem `apt`;
- decisões de outras etapas: e-mails transacionais (06.4/07.x), escritas HTTP em andamento durante o cancelamento (07.4), tela de cancelamento (06.3) e transição automática (06.2).

## 14.3 Verificação da versão

| Item | Resultado | Evidência |
|---|---|---|
| Versão local | ZIP do GitHub `faa59d98…` (comentário do ZIP) com as alterações registradas da 0.2A e da AJ-00 | `NEXO_AJ_00_BASELINE.md`, seção 1; manifesto pré-06.1 (269 arquivos) |
| Git local | **Não há** `.git` na pasta nem acima dela. Nenhum branch ou commit pode ser atribuído à pasta, e `git init` não foi executado | Teste de existência de `.git` às 13:49 |
| Remoto `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente` | **Sem acesso**: `git ls-remote` respondeu `could not read Username` (repositório privado ou inexistente) | Execução às 13:49, com `GIT_TERMINAL_PROMPT=0` e `GCM_INTERACTIVE=never` |
| Remoto `Helio965/Nexo---Faturamento-Inteligente---Render` (citado no Documento Mestre) | **Sem acesso** (mesma resposta) | Idem |
| Remoto `Helio965/Nexo-Faturamento-Inteligente` (repositório original, público) | `main` = `015981e809d3c6cafa085edb42c59ccc9aa72604`. É a linha original de desenvolvimento, **não** a deste ZIP | `git ls-remote` somente leitura |
| Credenciais ou ferramentas | Sem `gh`, sem credenciais guardadas e com o conector do GitHub desta sessão fora do ar | — |
| **Classificação** | **VERSÃO NÃO VERIFICADA.** A pasta local está claramente identificada como alvo, então a correção foi feita localmente, conforme a regra 5.3 do prompt. Não há divergência comprovada nem sobrescrita de trabalho | — |

Para o responsável confirmar, com acesso ao repositório oficial: compare o resultado de `git ls-remote <repositório-oficial> refs/heads/main` com `faa59d98…`. Se forem diferentes, compare a pasta com o checkout dessa `main` antes de integrar esta correção.

## 14.4 Arquivos modificados

Comparação por SHA-256 com o checkpoint pré-06.1: **12 arquivos de código e teste** (10 modificados e 2 novos) e 2 documentos. **Nenhum arquivo foi excluído.**

*Artefato removido:* uma pasta **vazia** `.audit_tmp/` (ignorada pelo `.gitignore:16`) apareceu na raiz às 14:13. Foi criada pelos helpers de teste quando um script de sondagem da revisão adversarial importou o pacote `tests` com o projeto como diretório atual. Ela não existia no checkpoint e foi removida às 14:38, vazia como estava. Nenhum arquivo do projeto foi afetado. O diff completo está em `evidencias\diff_codigo_pre_vs_pos_AJ-06.1.patch` (seção 14.10).

| Arquivo | Alteração | Justificativa | Teste relacionado |
|---|---|---|---|
| `session_security.py` (+13 −2) | `STATUS_CONTA_SEM_ACESSO` e `condicoes_empresa_acessivel()` (`:16-27`); `usuario_pode_acessar` usa o critério (`:44`, `:67`) | Autorização central: uma só regra para todos os pontos de entrada | `test_c_*`, `test_d_*`, `test_e_*`, `test_n_*` |
| `company_security.py` (+25) | `STATUS_CONTA` (`:17`); `aplicar_status_conta` (`:80-97`): trava os CLIENTE depois da empresa e incrementa a geração ao entrar ou sair de CANCELADA | Revogação transacional de sessões, com o mesmo protocolo da lixeira | `test_d_*`, `test_h_*`, `test_m_*`, `test_failed_status_commit_*` |
| `blueprints/admin.py` (+54 −19) | Helpers `_revogacoes_socket` e `_desconectar_revogados` (`:319-340`), extraídos da lixeira sem mudar o comportamento. `empresa_editar` (`:435-492`): valida o status, preserva o atual se o campo faltar, recusa formulário desatualizado, aplica `aplicar_status_conta`, faz o COMMIT e só então desconecta. `empresa_excluir` (`:496-515`) usa os helpers. `empresa_nova` (`:403-408`): empresa criada CANCELADA não recebe token. `empresa_restaurar` (`:542`, `:551-552`): avisa que a empresa continua CANCELADA | Revogação ao cancelar; impedir reativação silenciosa; mensagens corretas ao ADMIN | `test_d_*`, `test_h_*`, `test_stale_*`, `test_company_created_*`, `test_k_*` |
| `blueprints/auth.py` (+4 −4) | Import (`:19`); CAS de troca de senha com o critério único (`:190`) | Fecha a corrida token → cancelamento | `test_password_change_cas_*`, `test_b_*_password_*` |
| `notifications.py` (+3 −3) | `notificar_clientes_empresa` usa o critério único (`:168-180`) | Não gravar notificações para CLIENTE de empresa cancelada (igual à lixeira) | `test_company_notifications_*` |
| `templates/admin/empresa_form.html` (+2) | Campo oculto `status_conta_exibido` só na edição (`:103-104`); **sem mudança visual** | Detectar formulário aberto antes de outra troca de status | `test_stale_or_incomplete_*` |
| `nexobot/saber/empresas_planos.py` (+9 −7), `nexobot/saber/administracao.py` (+3 −2), `nexobot/saber/uploads.py` (+3 −2) | Textos da base de conhecimento: CANCELADA bloqueia o portal; SUSPENSA mantém o histórico | A base afirmava que conta cancelada mantinha acesso, o que ficou falso depois da correção. Os IDs, as perguntas e os termos não mudaram | Suítes `test_nexobot_*` (dentro das 313 OK) |
| `tests/test_company_restore_security.py` (+7 −2) | `test_soft_delete_restore_preserves_existing_commercial_status_policy` (`:431-449`): CANCELADA passa a esperar acesso negado; ATIVA e SUSPENSA continuam com 200 | O teste antigo travava a falha de segurança. A finalidade original (lixeira e restauração preservam o status) foi mantida | O próprio teste |
| `tests/test_cancelled_company_security.py` (novo, 30 testes) | Cenários A–N, tokens, transação, formulário, cadastro e notificações | Exigência do prompt (9.2) | — |
| `tests/test_cancelled_company_postgresql.py` (novo, 1 teste opt-in com 20 checagens) | Cluster PostgreSQL descartável: locks reais, rollback e revogação | Compatibilidade com PostgreSQL versionada no repositório | — |
| `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md` | Linha 16, registro por ID e histórico (versão 3) | Regra permanente | — |
| `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_06_1_PARA_CHATGPT.md` | Novo (este relatório) | Fase 10 | — |

**Não alterados:**
- migrações e banco de dados (nenhuma migração nova, nenhum `upgrade`);
- CSS, JavaScript, landing e identidade visual;
- preços, contratos e vencimentos;
- `render.yaml`, `requirements*.txt` e a CI;
- `app.py`, `realtime.py`, `blueprints/cliente.py`, `blueprints/api.py` e `blueprints/notificacoes.py`. Esses passam a ser protegidos pelo critério central, sem mudança de código.

## 14.5 Correção da autorização

**Como era.** `usuario_pode_acessar` (versão anterior, `session_security.py:43-57`) verificava usuário existente, `ativo`, papel ADMIN/CLIENTE, vínculo com a empresa e `Empresa.deletado_em IS NULL`. Não verificava `status_conta`. O login (`blueprints/auth.py:268-280`), o `_guard_sessao` de cada requisição (`app.py:160-197`, via `sessao_valida`), o Socket.IO (`realtime.py:148-151`, `:128`, `:91`), os tokens (`auth.py:110`, `:153`, `:352`) e a entrega de notificações (`notifications.py:70`) dependiam só desse predicado. Assim, CANCELADA passava em todos. A edição do ADMIN (`empresa.status_conta = form.get("status_conta", "ATIVA")`) não revogava nada e, sem o campo, voltava a empresa para ATIVA.

**O que mudou.**

1. **Critério único** (`session_security.py:16-27`): `condicoes_empresa_acessivel()` = `deletado_em IS NULL` **e** `status_conta != 'CANCELADA'`. É usado por:
   - `usuario_pode_acessar` (`:67`);
   - o CAS de senha (`blueprints/auth.py:190`);
   - `notificar_clientes_empresa` (`notifications.py:177`).
   A coluna é NOT NULL, com CHECK nos três valores (`models.py:96,113`), então não há caso NULL.
2. **Revogação transacional** (`company_security.py:80-97`). Com a empresa já travada (`bloquear_empresa`, FOR UPDATE, `admin.py:438`), a entrada **ou saída** de CANCELADA:
   - trava os CLIENTE em ordem de PK (FOR UPDATE);
   - incrementa `geracao_autorizacao`.
   A ordem Empresa → Usuario é a mesma da lixeira, sem inversão de locks. No PostgreSQL, o UPDATE da geração espera qualquer `FOR SHARE` de entrega ou evento em andamento (comprovado, seção 14.9).
3. **Rota do ADMIN** (`blueprints/admin.py:463-482`):
   - status fora do domínio → recusa sem gravar;
   - campo ausente → preserva o status atual;
   - `status_conta_exibido` diferente do status atual com pedido de troca → recusa com aviso ("alterado por outra operação");
   - depois disso, `aplicar_status_conta`, cálculo das impressões, **COMMIT**, e só então `_desconectar_revogados`.
   Rollback não revoga nada (testado com falha injetada no meio da escrita, em SQLite e em PostgreSQL).

**Como o bloqueio funciona agora.**

| Ponto | Mecanismo | Evidência |
|---|---|---|
| Login | `usuario_pode_acessar` falha depois da senha e antes de `login_user`. A mensagem é a mesma de conta desativada, e a senha errada mantém a mensagem genérica (sem enumeração) | `auth.py:268-274`; `test_c_*` |
| Cada requisição HTTP | `_guard_sessao` → `sessao_valida` → `usuario_pode_acessar`. Se a sessão for inválida, faz `logout_user()` e limpa a sessão, e `login_required` redireciona | `app.py:177,193-195`; `test_e_*`, `test_f_*`, `test_g_*` |
| Sessão já aberta | Negada no request seguinte pelo status (mesmo com mudança fora da rota) e também pela geração (pela rota) | `test_d_existing_*`, `test_d_out_of_band_*` |
| Socket.IO novo | `_on_connect` → `sessao_valida` com FOR SHARE | `realtime.py:148-151`; `test_i_*` |
| Socket.IO antigo | A rota fecha os SIDs locais depois do COMMIT. Nos demais processos, a varredura de 1 s, as salas por impressão (geração) e a entrega que relê o banco sob FOR SHARE impedem o recebimento | `realtime.py:55-105`; `notifications.py:66-75`; `test_h_*` |
| Eventos autenticados | `guarded_socket_event` revalida antes do handler | `realtime.py:118-144`; `test_h_guarded_*` |
| Tokens de senha | Não emitidos nem aceitos; o CAS também recusa | `auth.py:110,153,190,352`; `test_password_*` |
| Notificações | Não são criadas nem entregues | `notifications.py:70,177`; `test_company_notifications_*` |

**Sessões antigas.** São invalidadas de duas formas independentes:
- **pelo status**, relido no banco a cada requisição e evento, o que vale até para cancelamento feito fora da rota;
- **pela geração**, que muda a impressão HMAC da sessão e a sala do Socket.IO.

Como a geração também sobe ao sair de CANCELADA, nenhum cookie ou token anterior ao cancelamento volta a valer depois da reativação, inclusive após um cancelamento gravado por script (`test_m_route_reactivation_after_out_of_band_*`). Os mecanismos de senha e de `BOOT_ID` continuam iguais.

**ADMIN.** `usuario_pode_acessar` retorna antes de consultar a empresa para ADMIN (`session_security.py:57-58`), e `bloquear_usuarios_empresa` filtra `role = 'CLIENTE'` (`company_security.py:48`). O ADMIN continua listando, editando e consultando empresas canceladas, com socket e notificações intactos (`test_j_*`). CANCELADA não grava `deletado_em`, e a lixeira segue igual (`test_k_*`).

## 14.6 Testes anteriores (histórico × reproduzido)

| Origem | Testes | Falhas | Erros | Ignorados | Observação |
|---|---|---|---|---|---|
| Histórico: NEXO-AJ-00 (25/10, cerca de 11:00) e 0.2A (E15) | 569 | 13 | 12 | 42 | Registrado nos relatórios anteriores |
| **Reproduzido nesta execução**, sobre o checkpoint pré-06.1 (cópia extraída do ZIP, isolada) | 569 | 13 | 12 | 42 | Às 14:34-14:37 (171 s de testes). Os 25 blocos FAIL/ERROR são **idênticos** aos da AJ-00 e aos da suíte final pós-06.1. Nessa versão, o teste antigo `test_soft_delete_restore_preserves_existing_commercial_status_policy` **passou**, o que comprova em execução que um CLIENTE de empresa CANCELADA obtinha 200 numa rota protegida. Log: `evidencias\suite_completa_pre_061_reproducao.log` |

| **[Complemento Linux]** Reproduzido em Linux (WSL Ubuntu 24.04, Python 3.12.3, dependências fixadas), sobre o mesmo checkpoint pré-06.1 | 607 | **0** | **0** | 38 | Às 15:14-15:16 (149 s). Em Linux todos passam, inclusive os módulos que nem importavam no Windows. O teste antigo que travava o acesso de CANCELADA também **passou**, o que confirma a vulnerabilidade em Linux. Log: `evidencias\linux_wsl\suite_pre061.log` |

Os 25 blocos FAIL/ERROR também foram reproduzidos **um a um** na investigação (seção 14.7), com experimentos dirigidos.

## 14.7 Testes posteriores

**Ambiente:**
- Windows 11, Python 3.12.10 do sistema;
- cópia isolada do projeto fora da pasta de trabalho;
- SQLite temporário;
- variáveis `ANTHROPIC_*`, `CLAUDE_CODE_*`, `SENTRY-TRACE`, `DATABASE_URL`, `DIRECT_URL` e `NEXO_TEST_POSTGRES_BIN` removidas do processo;
- sem `.env`;
- rede bloqueada pelos próprios testes.

| Grupo | Comando | Resultado |
|---|---|---|
| Suíte completa final | `python -B -m unittest discover -s tests -t . -v` | **600 testes; 13 falhas; 12 erros; 43 ignorados**; 187 s (197 s com a inicialização). Os 25 blocos FAIL/ERROR são **idênticos** aos da linha de base, sem nenhuma falha nova. Os 30 testes novos em SQLite e o teste antigo corrigido passaram. Os 43 ignorados são os 42 da linha de base mais o teste PostgreSQL opt-in |
| Segurança e NexoBot | `python -B -m unittest tests.test_cancelled_company_security tests.test_company_restore_security tests.test_session_revocation_security tests.test_auth_tokens_security tests.test_nexobot_*` | **313 testes OK** (18 ignorados: navegador opt-in do NexoBot); 102 s |
| PostgreSQL 18.1 (opt-in) | `NEXO_TEST_POSTGRES_BIN="C:\Program Files\PostgreSQL\18\bin" python -B -m unittest tests.test_cancelled_company_postgresql -v` | **OK, com as 20 checagens aprovadas**; 18 s |
| Mutação | `mutacao_061.py` (15 mutantes aplicados na cópia) | **15 de 15 detectados**, nenhum sobrevivente |
| **[Complemento Linux]** Suíte completa em Linux com as dependências fixadas | Detalhes abaixo | **638 testes; 0 falhas; 0 erros; 39 ignorados**; 170 s |

**[Complemento Linux] Como foi a execução em Linux** (autorizada pelo responsável na conversa; script `evidencias\linux_wsl\linux061.sh`):

- **Ambiente:** WSL Ubuntu 24.04.4, kernel 6.6.87.2, Python 3.12.3. Tudo ficou em `~/nexo_aj061_linux`, fora do projeto, com cópias do projeto pós-06.1 e do checkpoint pré-06.1. O projeto foi só lido: o manifesto SHA-256 deu 272 de 272 arquivos idênticos antes e depois.
- **Instalação:** `python3 -m venv --without-pip` e depois `python -I tools/install_dependencies.py --requirements requirements-dev.txt`, o instalador verificado do projeto. Ele baixou o wheel do pip 26.2.2 com SHA-256 conferido e depois só os requisitos, do PyPI. Sem `apt`, sem `sudo`. Versões instaladas: Flask 3.1.3, Werkzeug 3.1.9, python-dotenv 1.2.4, Flask-SocketIO 5.6.1, Pillow 13.0.0, gunicorn 23.0.0, PyYAML 6.0.3 e pip 26.2.2. `pip check` não acusou nenhum conflito. O relatório completo do pip está em `evidencias\linux_wsl\pip-report.json`.
- **Ambiente dos testes:** o mesmo da CI (`PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`, segredos vazios ou sintéticos, `DATABASE_URL` em memória), com ambiente limpo (`env -i`).
- **Ignorados (39):** 33 de navegador opt-in; 3 sem `pdftotext`; 2 do PostgreSQL opt-in (ensaio de backup e o novo `test_cancelled_company_postgresql`), porque não há PostgreSQL no WSL; 1 de gunicorn simulado, que exige os binários do PostgreSQL.
- **Resultado pós-06.1:** 638 testes = 607 da versão anterior + 31 novos. Os 30 testes novos em SQLite e o teste antigo corrigido passaram.
- **As 25 falhas do Windows passam todas em Linux**, módulo a módulo: equivalência financeira 15/15, `test_sensitive_http_logs` 10/10, `test_supply_chain_install` 15/15, `test_dependency_security_compat` 18/18, `test_dotenv_security_compat` 12/12, `test_etl_upload_security` 28/28, `test_etl_runtime_limits` 21/21, `test_etl_resource_limits` 68/68 e `test_deploy` 12/12. Isso **confirma por execução** a classificação de ambiente da tabela abaixo.

**Falhas e erros remanescentes.** Todos são pré-existentes, idênticos antes e depois e sem relação com a 06.1. Classificação com experimentos:

| # | Teste (arquivo:linha) | Blocos | Mensagem principal | Categoria | Causa comprovada e evidência |
|---|---|---|---|---|---|
| 1 | `test_deploy.DeployTests.test_etl_csv_and_xlsx_fictitious_data` (`tests/test_deploy.py:188`) | 2 E | `ETLValidationError`: plataforma sem isolamento | 2 | O worker ETL exige o módulo POSIX `resource` (`etl_worker.py:19-28`) e recusa com `code="platform"`. Recusa capturada no teste; com um `resource` simulado, passa; no WSL Ubuntu, o worker aplica os limites reais (AS=384 MiB, CPU=60 s) |
| 2 | `test_deploy.DeployTests.test_cliente_uploads_persist_in_database_and_survive_cache_removal` (`:151`) | 1 F | `0 != 2` | 2 | Upload recusado no preflight (`platform`), com flash "danger" capturado; com a validação simulada como aceita, passa |
| 3 | `test_etl_financial_equivalence.FinancialEquivalenceTests` setUpClass (`:28`) | 1 E | `UnicodeDecodeError 'charmap'` | 2 (portabilidade do teste) | `read_text()` sem `encoding` lê fixture UTF-8 como cp1252. Com `PYTHONUTF8=1` (como na CI) aparece a recusa `platform`; com `resource` simulado e UTF-8, 15 de 15 passam |
| 4 | `test_etl_resource_limits…test_csv_record_exact_limit_includes_line_ending` (`:127-128`) | 1 E | registro acima do limite | 2 (portabilidade do teste) | A fixture gravada em modo texto vira CRLF no Windows (5 caracteres > limite 4). O leitor de produção conta corretamente (`etl_inputs.py:92-105`). Bytes conferidos |
| 5 | `test_etl_runtime_limits…test_calculation_restores_dates_and_rejects_incomplete_payloads` (`:251`) | 1 E | interrompido pelo limite ou arquivo inválido | 2 (portabilidade do teste) | Script sintético gravado em cp1252 e lido como UTF-8 pelo filho (`SyntaxError`). Passa com `PYTHONUTF8=1` |
| 6 | `test_etl_runtime_limits…test_real_worker_validates_a_small_csv_inside_default_resource_limits` (`:231`) | 1 E | plataforma | 2 | `resource` ausente; passa com `resource` simulado |
| 7 | `test_etl_runtime_limits…test_real_worker_reports_applied_os_limits_and_no_database_modules` (`:278`) | 1 F | `2 != 0` | 2 | O worker sai com código 2 por plataforma; no WSL sai com 0 e os limites aplicados |
| 8 | `test_etl_upload_security…test_admin_and_client_valid_csv_xlsx_preserve_bytes_sha_and_status` (`:152`, `:158`) | 4 E + 1 F | `NoneType.hash_arquivo`; `AGUARDANDO_RELATORIO != RELATORIO_RECEBIDO` | 2 | Os 4 uploads recusados (`platform`); com a validação simulada, passa, inclusive a rota do admin já com a 06.1 |
| 9 | `test_etl_upload_security…test_busy_admission_rejects_post_without_validation_but_keeps_get_available` (`:242`) | 1 F | `0 != 1` | 2 | A admissão funciona (flash "warning" capturado); o upload final é recusado (`platform`) |
| 10 | `test_dependency_security_compat…test_multipart_part_limit_accepts_four_and_rejects_five_parts` (`:242`) | 1 F | `0 != 1` | 2 | Recusa `platform` e, por trás dela, o Flask 3.0.3 instalado ignora `MAX_FORM_PARTS` (o projeto fixa 3.1.3) |
| 11 | `test_dependency_security_compat…test_valid_csv_and_xlsx_uploads_preserve_stored_bytes_and_hashes` (`:193`) | 1 F | `0 != 2` | 2 | Recusa `platform`; passa com a validação simulada |
| 12 | `test_dependency_security_compat.MultipartMemoryCompatibilityTests.test_field_budget_is_cumulative_across_small_chunks` (`:111-117`) | 1 F | `RequestEntityTooLarge not raised` | 2 (versão instalada) | Werkzeug 3.0.4 instalado × 3.1.9 fixado: o limite vale só por bloco (código do pacote inspecionado); com o comportamento cumulativo simulado, passa |
| 13 | `test_dependency_security_compat…test_multipart_field_budget_rejects_large_field_without_overwriting_upload` (`:249-256`) | 1 F | `302 != 413` | 2 (versão instalada) | O Flask 3.0.3 não tem `MAX_FORM_MEMORY_SIZE`; por trás, também há a recusa `platform` |
| 14 | `SessionVaryCompatibilityTests.test_length_for_populated_and_empty_session_varies_on_cookie` (`:77-83`) | 2 F | `'Cookie' not found` | 2 (versão instalada) | Flask 3.0.3: `len(session)` não marca `accessed` (corrigido no 3.1.3); com o comportamento do 3.1.3 simulado, passa |
| 15 | `SessionVaryCompatibilityTests.test_membership_for_present_and_missing_keys_varies_on_cookie` (`:70-75`) | 2 F | idem | 2 (versão instalada) | Idem, para o operador `in` |
| 16 | `test_dotenv_security_compat…test_disable_flag_prevents_reading_even_an_explicit_file` (`:82-86`) | 1 F | `True is not false` | 2 (versão instalada) | python-dotenv 1.0.1 não implementa `PYTHON_DOTENV_DISABLED` (o projeto fixa 1.2.4); código do pacote inspecionado |
| 17 | `tests.test_sensitive_http_logs` (importação, `:7`) | 1 E | `No module named 'gunicorn'` | 3 (e 2) | `gunicorn` ausente. No `.venv` antigo, que tem `gunicorn`, falha em `import fcntl` (só POSIX). Com stubs POSIX, os 10 testes passam, inclusive os que exercitam `blueprints/auth.py` já com a 06.1 |
| 18 | `tests.test_supply_chain_install` (importação, `:23`) | 1 E | `No module named 'yaml'` | 3 | PyYAML ausente. Latente: o pip local (25.0.1) é diferente do exigido (26.2.2) |

Totais: **25 blocos**, sendo 23 na categoria 2 (incompatibilidade do ambiente: plataforma Windows, versão instalada diferente da fixada ou portabilidade do próprio teste) e 2 na categoria 3 (dependência ausente). Categorias 1 (defeito real de código), 4, 5, 6 (autorização) e 7: **nenhum bloco**.

Os 3 blocos marcados como "portabilidade do teste" também podem ser lidos como categoria 4 (configuração de teste): o defeito está no código do teste (falta de `encoding` ou `newline`), não na aplicação. Nenhum foi corrigido aqui, porque estão fora do escopo da 06.1 (regra 10.3).

**Limitação** (registro da execução das 14:38, mantido): "Não foi possível rodar a suíte em Linux com as dependências fixadas. O WSL Ubuntu-24.04 tem Python 3.12.3, mas não tem Flask, pandas nem pip, e instalar exigiria baixar pacotes, o que não foi autorizado."

**[Complemento Linux]** A limitação foi resolvida às 15:10, com a autorização do responsável: a suíte rodou em Linux com as dependências fixadas, e os 25 blocos passaram. Em Linux, ainda não foram executados o PostgreSQL real, o navegador e o `pdftotext`, que exigiriam `apt` e `sudo`, não autorizados. A CI (`.github/workflows/nexo-security-ci.yml`) cobre esses três.

## 14.8 Evidências de segurança

| Cenário | Resultado | Testes (`tests/test_cancelled_company_security.py`) |
|---|---|---|
| ATIVA | Login, dashboard e PDF OK | `test_a_*` (`:160`) |
| SUSPENSA | Login, sessão anterior, socket aberto antes, eventos, notificações, PDF, recuperação de senha, ativação e primeiro acesso: **tudo mantido**, sem mudança de geração | `test_b_*` (`:168`, `:183`, `:193`, `:210`) |
| CANCELADA: login | Negado (200 na página de login, sem sessão, sem redirecionar ao dashboard); senha errada mantém a mensagem genérica | `test_c_*` (`:222`, `:230`) |
| Sessão existente antes do cancelamento | Negada pela rota (geração +1 nos 3 CLIENTE, ADMIN e outra empresa intactos) e também fora da rota (status relido) | `test_d_*` (`:241`, `:257`, `:265`) |
| URL direta | Dashboard, histórico, análise, upload, suporte, guia e primeiro acesso: redirecionam ao login, sem dado privado | `test_e_*` (`:279`) |
| PDFs | Negados com cookie salvo (cancelamento pela rota e fora dela) | `test_f_*` (`:288`) |
| APIs | `/api/suporte-bot`, `/notificacoes/marcar-lidas` e `/notificacoes/<id>/abrir` negados; a notificação continua não lida | `test_g_*` (`:300`) |
| Socket.IO antigo | Nada recebido, mesmo sem o fechamento local (simulando outro processo); a varredura desconecta; a rota fecha o socket local depois do COMMIT; evento autenticado não executa | `test_h_*` (`:321`, `:341`, `:346`, `:360`) |
| Socket.IO novo | Recusado (cookie anterior; cancelamento pela rota e fora dela) | `test_i_*` (`:371`) |
| ADMIN | Listagem, edição, socket e notificações mantidos; análise e relatório preservados; sem `deletado_em` | `test_j_*` (`:380`) |
| Lixeira | Excluir e restaurar preservam CANCELADA, com aviso ao ADMIN; login continua negado | `test_k_*` (`:399`) e teste antigo corrigido |
| Isolamento entre empresas | Análise e PDF de outra empresa: 404; cancelar uma empresa não afeta a outra | `test_l_*` (`:411`) |
| Reativação | CANCELADA → ATIVA ou SUSPENSA: geração +1, cookie anterior inválido, novo login OK; vale também depois de cancelamento fora da rota | `test_m_*` (`:427`, `:445`) |
| Falha de banco | Consulta de status falhando: HTTP 503 com sessão limpa, socket recusado, notificação não entregue; falha no meio da escrita do cancelamento: nada revogado, socket preservado | `test_n_*` (`:454`); `test_failed_status_commit_*` (`:514`) |
| Tokens e CAS | Não emitidos nem aceitos para CANCELADA; CAS recusa | `:480`, `:504` |
| Formulário do ADMIN | Formulário desatualizado, campo ausente e valor inválido não mudam o status | `:541` |
| Cadastro já CANCELADO | Sem token nem e-mail de ativação; aviso claro | `:560` |
| Notificações | Não criadas para CANCELADA; criadas para SUSPENSA | `:577` |

**Teste dos testes (mutação).** Todos os 15 defeitos reintroduzidos foram detectados:
- sem o critério de status;
- sem incremento de geração;
- CAS sem o critério;
- sem fechar sockets locais;
- SUSPENSA revogando;
- status aplicado antes da comparação;
- SUSPENSA tratada como CANCELADA;
- sair de CANCELADA sem revogar;
- notificações para CANCELADA;
- formulário desatualizado aceito;
- campo ausente virando ATIVA;
- sockets fechados antes do COMMIT;
- CAS negando SUSPENSA;
- restauração sem aviso;
- cadastro CANCELADA sem tratamento.

O mutante "sem incremento" é detectado por erro (a rota calcularia a impressão de uma geração −1); o efeito "não revogar" é coberto pelo mutante "status aplicado antes da comparação", detectado por 8 testes.

**Revisão adversarial.** Três revisores independentes, somente leitura, analisaram desvios, transações e locks e regressões. Resultados:
- Confirmaram: ausência de desvio durante o cancelamento; ordem de locks sem deadlock; rollback sem efeitos; ADMIN, SUSPENSA e lixeira intactos (a refatoração da lixeira foi comparada linha a linha).
- Os apontamentos do escopo foram corrigidos: reativação silenciosa, revogação ao sair, notificações persistidas, testes fracos, PostgreSQL versionado, mensagens ao ADMIN e textos do NexoBot.
- Os de fora do escopo estão na seção 14.11.

## 14.9 Compatibilidade

| Banco | Resultado | Evidência |
|---|---|---|
| SQLite | **Testado**: suíte completa (600) e suítes de segurança (313) | Logs em `evidencias\` |
| SQLite em Linux, com as dependências fixadas | **[Complemento Linux] Testado**: 638 testes, 0 falhas e 0 erros (WSL Ubuntu 24.04, Flask 3.1.3, Werkzeug 3.1.9, SQLAlchemy 2.1.6) | `evidencias\linux_wsl\suite_pos061.log` |
| PostgreSQL 18.1 | **Testado**, em cluster descartável próprio (`initdb` em pasta temporária, porta aleatória em 127.0.0.1, sem socket Unix, scram com senha aleatória, migrações reais até `e4c004a26b01`). O serviço preexistente da porta 5432 não foi usado | `tests/test_cancelled_company_postgresql.py`: 20 checagens OK, entre elas o rollback real (a segunda escrita falha e status e geração ficam intactos) e o cancelamento esperando 1,5 s pelo `FOR SHARE` de uma entrega já autorizada, que termina antes do COMMIT. Antes, uma verificação ad hoc com 21 checagens também passou |
| PostgreSQL na CI (Linux) | **Não executado**: depende de push autorizado | O job `sqlite-browser` já define `NEXO_TEST_POSTGRES_BIN` (`.github/workflows/nexo-security-ci.yml:52`), então o teste opt-in deve rodar lá automaticamente |

Observação: no SQLite, `with_for_update` é ignorado, e por isso a serialização só é provada no PostgreSQL. A produção exige PostgreSQL (`app.py:99-102`).

## 14.10 Checkpoint e reversão

| Item | Valor |
|---|---|
| Localização | `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-06.1_2026-10-25\NEXO_checkpoint_pre-AJ-06.1_2026-10-25.zip` |
| Método | ZIP da pasta inteira às 13:50, **antes** de qualquer alteração, com as regras de exclusão de segredos (nenhum arquivo se enquadrou), conferido arquivo a arquivo (269/269) |
| Integridade | SHA-256 `6A568DF4C660811D0578601E61A99D3DE7AF459906A8AB3AEE61A3911F84FC7F` (19.127.086 bytes); manifesto `MANIFESTO_SHA256_pre-AJ-06.1.json` |
| Arquivos protegidos | Os 269 arquivos do estado final da AJ-00, inclusive todo o código, os testes, as migrações e os documentos |
| Checkpoint da AJ-00 | Intacto (hash conferido) |
| Evidências | `…\NEXO-AJ-06.1_2026-10-25\evidencias\`: logs das suítes, diff completo (`diff_codigo_pre_vs_pos_AJ-06.1.patch`), mutação, PostgreSQL, investigação das 25 falhas e revisão adversarial. **[Complemento Linux]** `evidencias\linux_wsl\`: script, log da instalação, `pip-list.txt`, `pip-report.json` (o único "token" que aparece é o de um selo público do codecov no README do pacote `chardet`, não é dado do projeto) e os logs das suítes pré e pós-06.1 |
| Como restaurar | Renomeie a pasta atual (não apague), extraia o ZIP em `C:\ADS\Nexo - Faturamento Inteligente\` e confira o manifesto. Para desfazer só a 06.1, aplique o patch ao contrário ou restaure os 12 arquivos listados na seção 14.4 |
| Limitações | Cópia local no mesmo disco, sem cópia externa. **Não é backup do banco de produção**, que não foi acessado |

## 14.11 Pendências

**Desta subetapa** (nenhuma impede a revisão):

- Confirmar a versão no GitHub (seção 14.3).
- Rodar a CI. Depende de push, que não foi feito. **[Complemento Linux]** A suíte em Linux com os pins já passou no WSL. Na CI ficam só o PostgreSQL real (inclusive `tests.test_cancelled_company_postgresql` e os 5 módulos `postgresql_*`), o navegador e o `pdftotext`.
- Registrar o checkpoint de versão depois da aprovação (mapa:360).

**Problemas anteriores** (fora do escopo, não corrigidos):

- Os 25 blocos da seção 14.7. Ajustes sugeridos para os testes rodarem localmente:
  - `encoding="utf-8"` em `read_text` e `write_text`;
  - fixture CSV gravada em bytes;
  - `skipUnless(os.name == "posix")` nos testes que usam o worker ETL real.
- Latentes:
  - com python-dotenv 1.0.1, `PYTHON_DOTENV_DISABLED` não isola dois testes do `.env` local;
  - o pip local é 25.0.1, e o instalador exige 26.2.2.

**Ambiente:**

- Python local com Flask 3.0.3, Werkzeug 3.0.4, python-dotenv 1.0.1 e Flask-SocketIO 5.4.1, abaixo das versões fixadas.
- `gunicorn` e `PyYAML` ausentes.
- Windows sem o módulo `resource`.
- ~~O WSL não tem as dependências. Montá-lo exigiria baixar pacotes do PyPI, o que precisa de autorização.~~ **[Complemento Linux]** Resolvido. O ambiente ficou em `~/nexo_aj061_linux`, dentro do WSL (472 MB, com a venv e as duas cópias), e pode ser apagado sem afetar o projeto.
- **[Complemento Linux] Achado de reprodutibilidade:** `SQLAlchemy` e `alembic` não têm versão fixada em `requirements.txt`; só `Flask-SQLAlchemy==3.1.1` (`requirements.txt:7`) está fixado. Por isso o pip instalou as versões mais recentes no Linux (SQLAlchemy 2.1.6, alembic 1.20.1), enquanto o Windows tem SQLAlchemy 2.0.51 e alembic 1.18.4. As duas combinações passaram, mas a versão resolvida muda com o tempo. Sugestão para a 09.2: fixar ou usar arquivo de restrições, com hashes, para as dependências transitivas.

**De outras etapas** (observações da revisão adversarial):

| Observação | Etapa sugerida |
|---|---|
| E-mails transacionais (análise publicada, chamado resolvido) continuam indo para a empresa cancelada (`emails.py:104-112`). Não dão acesso ao portal; é uma política a decidir | 06.4 / 07.x |
| Requisição HTTP de escrita que passou pela autorização antes do COMMIT do cancelamento (por exemplo, um upload de até 60 s) termina depois dele. A janela é curta, o comportamento já era igual na lixeira e o Socket.IO já é serializado | 07.4 (ou 05.1) |
| `analise_nova` lê o status sem lock e pode criar análise durante o cancelamento. O impacto é administrativo; o CLIENTE segue bloqueado | 05.1 |
| A transição automática SUSPENSA → CANCELADA precisa usar `bloquear_empresa` + `aplicar_status_conta` | 06.2 |
| Tela própria para conta cancelada (hoje vale a mensagem de conta desativada) | 06.3 |
| Notificações criadas **antes** desta correção para empresas já canceladas continuam no banco (só aparecem se a empresa for reativada) | 06.4 / 07.3 |
| Documento Mestre e documentação geral desatualizados quanto a CANCELADA | 09.3 |

## 14.12 Checklist de aceitação

| Critério | Situação | Evidência |
|---|---|---|
| Login de CANCELADA bloqueado | **OK** | `test_c_*`; PostgreSQL `cancelled_login_denied` |
| Sessão antiga invalidada | **OK** | `test_d_*`, `test_m_*`; PostgreSQL `old_session_denied`, `old_cookie_stays_invalid` |
| Dashboard protegido | **OK** | `test_e_*` (URL direta, cookie salvo) |
| PDF protegido | **OK** | `test_f_*` |
| API protegida | **OK** | `test_g_*` (NexoBot e notificações) |
| Socket.IO protegido | **OK** | `test_h_*` (4), `test_i_*`; PostgreSQL `cancel_waits_for_share_lock`, `later_delivery_denied` |
| ADMIN preservado | **OK** | `test_j_*`, `test_n_*`; PostgreSQL `admin_kept` |
| SUSPENSA preservada | **OK** | `test_b_*` (4); mutantes de SUSPENSA detectados |
| Teste antigo corrigido | **OK** | `tests/test_company_restore_security.py:441-449`; passou na suíte final |
| Testes novos criados | **OK** | 30 (SQLite) + 1 opt-in PostgreSQL com 20 checagens |
| Testes executados | **OK** | 600 (completa, Windows), 313 (segurança e NexoBot), PostgreSQL opt-in, mutação 15/15. **[Complemento Linux]** 638 em Linux com os pins: 0 falhas e 0 erros |
| Nenhuma alteração fora do escopo | **OK, com transparência** | Todas as mudanças tratam do acesso de empresa cancelada ou da consistência dele: textos do NexoBot que ficaram falsos, aviso ao ADMIN e campo oculto no formulário, sem mudança visual. Sem migração, preço, contrato, landing, identidade visual ou deploy (seção 14.4) |
| Checkpoint disponível | **OK** | Seção 14.10 |

## 14.13 Conclusão

**CONCLUÍDO PARA REVISÃO.** Motivos:
- O bloqueio de empresas CANCELADAS está implementado na autorização central e tem efeito sobre login, sessões existentes, todas as rotas, PDFs, APIs, notificações, tokens e Socket.IO.
- SUSPENSA e ADMIN foram preservados, e a lixeira continua independente.
- Os testes de segurança específicos passaram em SQLite e em PostgreSQL real, e a mutação mostra que eles detectam a regressão.
- As 25 falhas antigas foram investigadas uma a uma, com experimentos: nenhuma é defeito de código, nenhuma é relacionada à autorização e nenhuma é nova. **[Complemento Linux]** Em Linux com as dependências fixadas, todas passam (638 testes, 0 falhas, 0 erros).
- A versão de origem está identificada; a comparação com o remoto fica explicitamente pendente, como permite o prompt.

O status "APROVADO" não foi usado. A validação independente ainda não ocorreu. A NEXO-AJ-06.2, a 06.3, a 06.4 e as demais subetapas **não foram iniciadas**.
