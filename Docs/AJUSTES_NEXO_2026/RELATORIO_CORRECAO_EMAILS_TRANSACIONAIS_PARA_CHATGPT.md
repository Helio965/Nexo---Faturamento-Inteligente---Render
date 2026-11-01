# Relatório — correção dos e-mails transacionais do NEXO

Data: 01/11/2026. Base: `main` em `a48ee92` (merge do PR #38). Branch de trabalho:
`claude/amazing-cannon-05671a` (branch designada pelo ambiente desta sessão; o nome
sugerido `fix/correcao-emails-transacionais` não pôde ser usado). Nenhum deploy, migração
ou acesso ao Supabase/Render/Brevo de produção foi feito. Nenhum e-mail real foi enviado.

Guia operacional (configuração, diagnóstico e testes controlados):
[`Docs/EMAILS_TRANSACIONAIS.md`](../EMAILS_TRANSACIONAIS.md).

## A. Diagnóstico

Classificação: **[código]** confirmada pela leitura do código; **[teste]** reproduzida em
teste automatizado; **[hipótese]** depende de configuração externa que não pôde ser vista.
Nenhuma causa foi confirmada em produção (sem acesso ao Render/Brevo).

| # | Causa | Fluxo | Classificação |
|---|---|---|---|
| 1 | O cadastro gravava o e-mail do usuário como digitado (`Cliente@Empresa.com`), mas a recuperação buscava `lower(e-mail)` com igualdade exata: a conta não era encontrada, nada era enviado e a tela dizia que o link fora enviado. O login também exigia a grafia exata. | Recuperação (B) e reemissão da ativação | [código] [teste] |
| 2 | Em produção (HTTPS atrás do `ProxyFix`), as páginas de token respondiam `Referrer-Policy: no-referrer`; sob HTTPS o CSRF do Flask-WTF (`WTF_CSRF_SSL_STRICT`) exige o cabeçalho `Referer`, então o POST da nova senha era recusado (400). O cliente não conseguia ativar a conta nem redefinir a senha pelo link do e-mail. | Ativação (A) e recuperação (B) | [código] [teste] (mecanismo reproduzido com HTTPS simulado; o comportamento do navegador sob `no-referrer` é o padrão da especificação) |
| 3 | Falhas do provedor ficavam indistinguíveis: o log só dizia `Falha ao enviar e-mail (RuntimeError)`, sem status HTTP, código do Brevo, tipo de e-mail ou correlação. Uma chave inválida, um IP não autorizado ou um remetente recusado pareciam iguais. | Todos | [código] |
| 4 | O admin via "e-mail de ativação agendado" mesmo quando o provedor recusava tudo; o resultado real nunca chegava a ele. Envio desativado em produção era registrado só em INFO. | Cadastro (A) | [código] [teste] |
| 5 | Variáveis vazias ou com espaço: `MAIL_DEFAULT_SENDER=` (como no `.env.example`) virava remetente vazio; `BREVO_API_KEY` com espaço/quebra de linha ativava o envio com uma chave que o Brevo recusa; `BREVO_API_URL=` vazia não voltava ao padrão. | Transporte | [código] [teste] |
| 6 | O Render Free bloqueia SMTP (25/465/587) desde 26/09/2025; sem `BREVO_API_KEY`, com credenciais SMTP, o envio sairia por SMTP e falharia. O SMTP do Flask-Mail 0.10 abre a conexão **sem prazo** e o STARTTLS padrão **não verifica o certificado**. | Transporte | [código] (bloqueio do Render: documentação oficial) |
| 7 | Contas Brevo criadas após 16/05/2024 bloqueiam por padrão chamadas de API de IPs desconhecidos (HTTP 401); o IP de saída do Render precisa estar autorizado. Uma chave SMTP (`xsmtpsib-`) no lugar da de API (`xkeysib-`) também dá 401. | Transporte | [hipótese] — causa provável em produção, não verificável sem o painel |
| 8 | `BREVO_API_KEY` com `sync: false` no `render.yaml` não tem valor até ser preenchida no painel; sem ela o envio fica desativado. | Transporte | [hipótese] |
| 9 | O remetente é `@gmail.com`: domínios gratuitos não são autenticáveis no Brevo, que reescreve o remetente — risco de spam e de não entrega. | Entregabilidade | [hipótese] |
| 10 | Thread daemon: um envio em andamento morria sem rastro no encerramento do processo (deploy/reinício). | Todos | [código] [teste] |
| 11 | Exceções depois do COMMIT viravam HTTP 500 com a operação já confirmada (aviso de senha alterada, chamado resolvido, política consultada após publicar); um `ValueError` na emissão do token da recuperação geraria 500 só para contas existentes (oráculo de enumeração). | Recuperação, chamado, publicação | [código] [teste] |
| 12 | Duplicidade: destinatários repetidos por diferença de maiúsculas; salvar de novo como RESOLVIDO um chamado já resolvido reenviava aviso e e-mail. Chamado de conta sem vínculo contratual recebia e-mail (o sininho não). Contato da empresa igual ao de um usuário desativado continuava recebendo. | Gatilhos de empresa | [código] [teste] |
| 13 | As telas de nova senha e o NexoBot anunciavam "mínimo de 8 caracteres", mas a política exige 12. | Ativação/recuperação | [código] [teste] |
| 14 | A chave do limite por conta era um SHA-256 sem segredo do e-mail, e o Flask-Limiter a escreve no log quando o limite estoura (reversível por dicionário). | Login/recuperação (logs) | [código] [teste] |

## B. Arquivos analisados

`config.py`, `emails.py`, `app.py`, `wsgi.py`, `extensions.py`, `blueprints/auth.py`,
`blueprints/admin.py`, `blueprints/contratos.py`, `blueprints/cliente.py`, `models.py`,
`notifications.py`, `pos_commit.py`, `origem_publica.py`, `log_security.py`,
`session_security.py`, `contract_policy.py`, `company_security.py`, `politica_senha.py`,
`seguranca_http.py`, `seed.py`, `criar_cliente_demo.py`, `render.yaml`, `requirements*.txt`,
`.env.example`, `README.md`, `Docs/PREPARACAO_RENDER.md`, `Docs/HOMOLOGACAO_SEC002_POSTGRES_EMAIL.md`,
`.github/workflows/nexo-security-ci.yml`, `tools/varredura_segredos.py`,
`templates/emails/*`, `templates/auth/*`, `templates/admin/{empresa_form,empresa_detalhe,dashboard}.html`,
`templates/base.html`, `nexobot/saber/{notificacoes,acesso,primeiros_passos}.py`, o código do
Flask-Mail 0.10.0 e do Flask-WTF 1.2.1 instalados, e os testes de autenticação, tokens,
e-mail, logs, publicação, chamados, navegação e deploy.

## C. Arquivos modificados

| Arquivo | Propósito |
|---|---|
| `emails.py` | Reescrito: `EnvioEmail` com estados (DESATIVADO, SEM_DESTINATARIO, AGENDADO, ACEITO_PELO_PROVEDOR, FALHA_NO_ENVIO) e categoria do erro; classificação segura de 400/401/402/403/429/5xx, rede, prazo, TLS e SMTP; uma linha de log estruturada por desfecho com correlação; nova tentativa só quando o pedido comprovadamente não foi processado; modo síncrono para o admin; histórico em memória; aviso no sininho dos admins (produção, limitado); espera limitada no encerramento; versão em texto, `tags`, `replyTo` e cabeçalho de correlação no Brevo; validação de remetente/destinatários; diagnóstico de configuração sem segredos. |
| `contas_email.py` (novo) | Normalização e busca de conta por e-mail: texto exato e, se não houver, a única conta igual sem diferenciar maiúsculas; conflito legado não escolhe conta. |
| `config.py` | Variáveis vazias/espaços valem como ausentes; `NEXO_EMAIL_TIMEOUT`; `NEXO_EMAIL_ALERTA_ADMIN` (ligado em produção); booleanos tolerantes; detecção do Render. |
| `extensions.py` | SMTP com prazo e certificado TLS verificado; QUIT com falha não mascara o resultado; chave do limite por conta com HMAC (o Flask-Limiter a registra em log). |
| `app.py` | `Referrer-Policy: strict-origin` nas páginas de token; resumo do diagnóstico de e-mail no log de inicialização. |
| `blueprints/auth.py` | Login e recuperação com a busca de `contas_email.py`; resultado operacional em log interno (resposta pública genérica); nenhum erro 500 na recuperação; aviso de senha alterada à prova de falhas. |
| `blueprints/admin.py` | Cadastro: e-mails normalizados e validados, duplicata por caixa recusada, ativação síncrona com mensagem verdadeira e referência; edição normaliza o contato; reenvio de ativação; Diagnóstico de e-mail e envio de teste (só para o próprio admin, limitado); chamado: sem duplicar aviso e e-mail à prova de falhas; publicação: política após o commit protegida; alerta no dashboard. |
| `politica_senha.py` | `http.client.HTTPException` na checagem opcional de senhas vazadas não derruba a troca. |
| `notifications.py` | `classificar_notificacao` dá o selo "Aberto" ao aviso de e-mail recusado ("Falha no envio de e-mail…"), mesmo quando o texto fala em "resolvido" ou "indisponível". |
| `.github/workflows/nexo-security-ci.yml` | Tempo-limite do job `security-sqlite-browser` de 20 para 30 min: a suíte com navegador já levava ~18 min na `main` e passou do limite com os testes novos. |
| `templates/admin/diagnostico_email.html` (novo), `templates/admin/empresa_detalhe.html`, `templates/admin/dashboard.html` | Painel de diagnóstico; card "Acesso ao portal" com situação e reenvio; aviso de pendência. |
| `templates/emails/boas_vindas.html`, `templates/emails/teste_configuracao.html` (novo) | Empresa do cadastro e orientação de acesso ao portal; e-mail de teste sem token. |
| `templates/auth/{resetar_senha,primeiro_acesso_token,primeiro_acesso}.html`, `nexobot/saber/{acesso,primeiros_passos}.py` | Mínimo de 12 caracteres, igual à política. |
| `tools/varredura_segredos.py` | Detecta chaves de API e SMTP do Brevo versionadas. |
| `render.yaml`, `.env.example`, `README.md`, `Docs/PREPARACAO_RENDER.md`, `Docs/EMAILS_TRANSACIONAIS.md` (novo) | Configuração do Brevo, IPs autorizados, tipos de chave, novas variáveis, diagnóstico e testes controlados. `render.yaml`: só comentários. |
| `tests/test_emails_transacionais.py` (novo), `tests/postgresql_auth_tokens.py`, `tests/test_auth_email_flows.py`, `tests/test_sensitive_http_logs.py`, `tests/test_security_deploy.py` | T01–T17 e regressões; variantes em PostgreSQL real; testes antigos ajustados à nova semântica (cadastro síncrono; `strict-origin`; dublê de banco da busca única por e-mail). |
| `Docs/INTEGRACOES/evidencias_emails_transacionais/*.jpg` (novos) | Capturas no Chromium, com dados fictícios: Diagnóstico de e-mail (desktop e celular), detalhe da empresa com "Acesso ao portal" (celular) e dashboard com a faixa de pendência (desktop). Nenhuma rola na horizontal. |

## D. Correções realizadas

**Envio de e-mails.** Agendar não é mais tratado como enviar: o retorno é um `EnvioEmail`
com estado e categoria; o aceite do provedor (HTTP 201 com `messageId`) é registrado como
`ACEITO_PELO_PROVEDOR`, nunca como "entregue". Logs estruturados sem dados privados; a
mensagem de erro do provedor é usada só para classificar (ex.: `ip_nao_autorizado`) e nunca é
registrada. Prazo em toda tentativa (inclusive SMTP), uma nova tentativa para 429, 500, 503 e
falha de conexão antes do envio, e espera limitada no encerramento do processo com registro explícito
do que for interrompido. A fila persistente foi avaliada e não introduzida (justificativa em
`Docs/EMAILS_TRANSACIONAIS.md`).

**Cadastro de empresa.** E-mails gravados em minúsculas e validados; duplicata por caixa
recusada antes do insert; ativação enviada de forma síncrona após o commit, com mensagem que
distingue cadastro concluído, aceito pelo serviço, agendado, serviço desativado e falha (com a
causa), sempre com a referência do log; falha nunca desfaz o cadastro; e-mail com a empresa,
o e-mail de acesso, o link seguro de 15 minutos e o endereço do portal; reenvio pelo detalhe
da empresa. Empresa CANCELADA continua sem ativação.

**Recuperação de senha.** Conta encontrada com qualquer combinação de maiúsculas (texto exato
primeiro; conflito legado não escolhe conta); resposta pública sempre genérica; resultado
operacional em log interno (não encontrada, não elegível, agendado + correlação); nenhum 500;
links pela origem pública canônica; `strict-origin` nas páginas de token para o POST da nova
senha passar no CSRF sob HTTPS sem expor o token no `Referer`. Expiração, assinatura, uso
único, CSRF, limites e validação de senha preservados.

**Demais gatilhos.** Boas-vindas, recuperação, senha alterada, análise publicada e chamado
resolvido passam pela mesma infraestrutura; destinatários deduplicados sem diferenciar
maiúsculas; chamado só avisa na transição para RESOLVIDO e só para conta com acesso ao portal;
a republicação de análise continua avisando de novo (regra existente, coberta por teste).

**Ajustes vindos da revisão adversarial** (todos com teste): a busca de conta virou uma única
consulta (login com e sem conta fazem o mesmo número de consultas); a requisição pública de
recuperação não grava aviso no banco (sem oráculo de tempo) e os avisos aos admins saem de
thread própria, só para recusas do provedor; a `api-key` vai como cabeçalho não repassado em
redirecionamento e resposta diferente de 201/202 não conta como aceite; 502/504, prazo
esgotado e conexão caída depois do envio não são repetidos e aparecem ao admin como "pode não
ter sido enviado"; `Retry-After` acima do teto não é atropelado; a janela de 30 min do aviso só
conta quando ele foi gravado; o aviso tem selo "Aberto" no sininho.

**Segunda rodada da revisão** (compatibilidade e requisitos, todos com teste): prazo esgotado
ainda na conexão (o urllib o embrulha em `URLError`, antes de o pedido sair) passou a ser
`conexao_sem_resposta`, falha certa com uma nova tentativa; `tempo_esgotado` ficou só para o
prazo na leitura da resposta (incerto, sem repetição). Entre os 5xx, só 500 e 503 são repetidos:
outro status (501, 507…) não prova que nada foi processado. No SMTP, uma queda ou prazo já
dentro da transação (MAIL/RCPT/DATA) vira `conexao_interrompida` ("pode não ter sido enviado");
antes dela (conexão, STARTTLS, login) continua falha certa. Tempo-limite do job com navegador no
CI de 20 para 30 min; linha `PYTHON_VERSION` devolvida à tabela de `Docs/PREPARACAO_RENDER.md`.

## E. Testes realizados

Ambiente: Python 3.12, dependências fixas do projeto (`tools/install_dependencies.py`),
SQLite temporário, PostgreSQL 16 local descartável (socket Unix, usuário sem privilégios) e
Chromium do ambiente; rede bloqueada nos testes; nenhum envio real.

| Teste | Resultado | Evidência | Observação |
|---|---|---|---|
| Linha de base (antes das mudanças) | Aprovado | `discover`: 1042 testes, OK, 75 ignorados | Ignorados: navegador e PostgreSQL |
| T01 Cadastro de empresa | Aprovado | `CadastroEmpresaTests.test_t01_*` (SQLite e PostgreSQL) | Empresa e usuário persistidos, e-mail normalizado, ativação aceita, link válido até o login |
| T02 E-mail de ativação (Brevo simulado) | Aprovado | `test_t02_ativacao_pelo_brevo_*` | URL https, POST, `api-key`, JSON (sender, to, subject, htmlContent, textContent, tags, replyTo, headers), aceite com `messageId` |
| T03 Recuperação | Aprovado | `test_t03_*` (SQLite e PostgreSQL) | Token válido, URL na origem pública, transporte chamado, AGENDADO → ACEITO no log |
| T04 E-mail inexistente | Aprovado | `test_t04_*` | Resposta genérica idêntica, sem envio, log sem o endereço |
| T05 Sem chave Brevo e sem SMTP | Aprovado | `test_t05_*` (inclui subprocesso de configuração) | DESATIVADO, sem confirmação falsa; admin vê a pendência |
| T06 Chave inválida | Aprovado | `test_t06_*` | 401 → `credencial_rejeitada`/`ip_nao_autorizado`; chave e mensagem do provedor fora do log |
| T07 Falha de conexão | Aprovado | `test_t07_*`, `test_5xx_que_nao_garante_*`, `test_queda_na_transacao_smtp_*` | Uma nova tentativa só quando seguro (recusa de conexão, prazo na conexão, 429/500/503); prazo na resposta, 501/507 e queda na transação SMTP não são repetidos; dados intactos |
| T08 Remetente inválido | Aprovado | `test_t08_*` | 400 de remetente → orientação; remetente mal configurado falha antes da rede |
| T09 Token expirado | Aprovado | `test_t09_*` | Negado com orientação para pedir outro link |
| T10 Token já utilizado | Aprovado | `test_t10_*` | Rejeitado; aviso de senha alterada sem token |
| T11 Maiúsculas/minúsculas | Aprovado | `MaiusculasMinusculasTests` (SQLite e PostgreSQL) | Conta legada encontrada; sem duplicata; conflito não escolhe conta |
| T12 Publicação de análise | Aprovado | `test_t12_*` | Solicitado só após o commit; falha da política após o commit não vira 500 |
| T13 Chamado resolvido | Aprovado | `test_t13_*` | Só após o commit; sem duplicar; conta sem vínculo e cancelada não recebem |
| T14 Render Free | Aprovado | `RenderEConfiguracaoTests`, `test_t14_url_sem_https_*` | Brevo/HTTPS 443, links https; SMTP no Render e chave SMTP viram pendência bloqueante no log |
| T15 Segurança de logs | Aprovado | `test_t15_*` | Nenhum token, senha, chave, destinatário ou mensagem do provedor em logs e avisos |
| T16 Estabilidade (regressão) | Aprovado | `discover` completo com navegador e cópias da CDN conferidas por SRI: 1103 testes OK no `ae0f9fd` e **1106 OK** no `9d18675` (último commit de código), 5 ignorados em ambos; os 5 ignorados (dependem dos binários do PostgreSQL) rodados à parte no PostgreSQL 16: OK | Login, cadastro, recuperação, autenticação, sessões, contratos, ETL, PDF, NexoBot e telas sem regressão |
| T17 Thread/processo | Aprovado | `AgendamentoEEncerramentoTests` | Falha ao iniciar a thread = FALHA; encerramento aguarda ou registra "interrompido" |
| CSRF sob HTTPS nos links de token | Aprovado | `test_links_do_email_funcionam_sob_https_*` | Sem Referer → 400; com origem → nova senha aceita |
| Suítes PostgreSQL do CI | Aprovado | 5 módulos no commit final: `auth_tokens` 54 (inclui as variantes dos testes de e-mail), `session_revocation` 59, `company_restore_security` 15, `company_restore_migration` 6, `etl_resource_security` 9 — todos OK | PostgreSQL 16 local, ~2 min no total |
| Varredura de segredos | Aprovado | `tools/varredura_segredos.py` | Nenhum padrão encontrado; padrões do Brevo adicionados |
| Validação real no Render/Brevo | **Não executado** | — | Sem acesso autorizado; ver seção F |

## F. Infraestrutura

- **Transporte selecionado:** API HTTPS do Brevo (`https://api.brevo.com/v3/smtp/email`, porta
  443). SMTP só fora do Render Free.
- **Variáveis no Render (Environment):** `BREVO_API_KEY` (chave de API `xkeysib-…`, preenchida
  no painel), `MAIL_DEFAULT_SENDER` (remetente verificado), `NEXO_PUBLIC_URL` (opcional; sem ela
  vale `RENDER_EXTERNAL_URL`), `PROXY_FIX_HOPS=1` (já no blueprint). Opcionais:
  `NEXO_EMAIL_TIMEOUT`, `NEXO_EMAIL_ALERTA_ADMIN`.
- **Brevo (manual):** gerar chave de API; verificar o remetente (código de 6 dígitos);
  autorizar as faixas de IP de saída do serviço Render (*serviço → Connect → Outbound*) em
  *Configurações → Segurança → IPs autorizados*; recomendado autenticar um domínio próprio
  (SPF/DKIM/DMARC) e trocar o remetente `@gmail.com`.
- **Pendências de infraestrutura:** confirmar no painel do Render que `BREVO_API_KEY` tem valor;
  autorizar os IPs no Brevo; deploy desta branch (o `render.yaml` publica a `main` com deploy
  automático desligado); depois do deploy, abrir *Admin → Diagnóstico de e-mail* e usar o envio
  de teste; conferir os eventos no Brevo (*Transacional → Logs*, etiquetas `nexo-*`).
- **Testes reais:** **não executados** (sem acesso ao Render/Brevo e sem autorização de envio
  real). Roteiro em `Docs/EMAILS_TRANSACIONAIS.md`, seção 7.

## G. GitHub

- Branch: `claude/amazing-cannon-05671a`.
- Commits: `82ca010` (código e testes), `ae0f9fd` (documentação e evidências) e os ajustes
  posteriores listados no PR.
- Pull Request: [Helio965/Nexo---Faturamento-Inteligente---Render#39](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/39)
  (rascunho, base `main`).
- Verificações automáticas: workflow `NEXO Security CI`.
  - Primeiro push: `security-postgresql` e `security-sca-sast` aprovados;
    `security-sqlite-browser` cancelado com o `apt-get update` travado num espelho do Ubuntu,
    antes de qualquer teste (infraestrutura).
  - Push de `c1723ee`: `security-sqlite-browser` cancelado pelo tempo-limite de 20 min com os
    testes ainda rodando. A causa é o crescimento da suíte neste PR, e o limite passou para
    30 min. `security-postgresql` ficou preso no `apt-get update` (infraestrutura). Localmente,
    as cinco suítes PostgreSQL levam ~2 min.
  - O resultado do último commit está no PR.

## H. Situação final

```text
CADASTRO DE EMPRESA:        CORRIGIDO, AGUARDANDO VALIDAÇÃO REAL
RECUPERAÇÃO DE SENHA:       CORRIGIDO, AGUARDANDO VALIDAÇÃO REAL
AVISO DE SENHA ALTERADA:    CORRIGIDO, AGUARDANDO VALIDAÇÃO REAL
PUBLICAÇÃO DE ANÁLISE:      CORRIGIDO, AGUARDANDO VALIDAÇÃO REAL
RESOLUÇÃO DE TICKET:        CORRIGIDO, AGUARDANDO VALIDAÇÃO REAL
CONFIGURAÇÃO DO RENDER:     PENDENTE DE CONFIGURAÇÃO
INTEGRAÇÃO COM BREVO:       PENDENTE DE CONFIGURAÇÃO
ENTREGA REAL DE E-MAIL:     NÃO TESTADO
```

Os cinco fluxos foram corrigidos e testados com transporte simulado (SQLite e PostgreSQL);
como nenhum envio real foi possível, ficam como "aguardando validação real". Render e Brevo
dependem de ações no painel (chave, IPs autorizados, remetente/domínio) que não pude ver nem
executar. A entrega real só é comprovada pelos eventos do Brevo e pela caixa do destinatário.

## Observações fora do escopo (não alteradas)

- O limite por conta da recuperação (10/hora) pode ser esgotado de um único IP em ~2 minutos
  (5/min), bloqueando a recuperação de um alvo por até 1 hora; aumentar facilita bombardeio de
  e-mails. É um equilíbrio de segurança existente; mantido.
- O tratamento global de CSRF responde `redirect(...), 400` (o navegador mostra uma página
  "Redirecting…"); com a correção do `Referer` o fluxo de senha não passa mais por ele.
- Não há como o admin corrigir o e-mail de acesso de um usuário (ex.: digitado errado no
  cadastro); só o reenvio foi adicionado.
- A unicidade de `usuario.email` no banco diferencia maiúsculas; a aplicação passou a impedir
  novas duplicatas. Um índice único em `lower(email)` exigiria migração e a resolução prévia de
  conflitos (consulta somente leitura em `Docs/EMAILS_TRANSACIONAIS.md`, seção 9).
