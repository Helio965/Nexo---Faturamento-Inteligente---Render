# Relatório — disparador de e-mails: projeto original (ZIP) × versão atual

Data: 01/11/2026. Base: `main` em `7585df7` (merge do PR #39). Branch de trabalho:
`claude/amazing-cannon-05671a` (designada pelo ambiente desta sessão). Referência: o pacote
`NEXO_MVP_compacto_para_Claude.zip` (pasta `nexo_mvp`), analisado fora do repositório. O ZIP não
contém `.env` (removido na higienização); do `.env.example` foram lidos apenas os **nomes** das
variáveis. Nenhum arquivo do ZIP foi copiado para o repositório. Nenhum deploy, migração, acesso
ao Supabase/Render/Brevo ou envio de e-mail real foi feito.

## Resumo

- **O código atual envia.** Rodando o NEXO de ponta a ponta contra servidores falsos locais
  (SMTP e uma API "Brevo" em HTTPS com TLS verificado, sem rede externa), cadastro de empresa,
  ativação e recuperação de senha chegam ao transporte, com links `https` na origem pública e
  sem token no log. Uma auditoria independente chegou à mesma conclusão: com o Brevo bem
  configurado, nenhum defeito de código impede o envio.
- **Por que o ZIP "funcionava":** ele envia pelo **Gmail SMTP** (porta 587). Onde a porta está
  aberta, envia; o **Render Free bloqueia as portas SMTP desde 26/09/2025** e, com a porta
  bloqueada, o código do ZIP não envia nada e ainda diz ao admin "Enviamos ao cliente um link".
- **O que impede a entrega em produção é configuração externa** (não verificável daqui): chave de
  API do Brevo no Render, IPs autorizados no Brevo, remetente/domínio e o deploy manual da versão
  atual (o deploy automático está desligado).
- **Esta entrega corrige** o que o código ainda fazia de errado ou de forma inadequada ao pedido:
  mensagens técnicas nas telas de operação e faixa técnica no dashboard; recuperação que dizia
  "enviamos" com o envio desligado; códigos de erro documentados do Brevo (DMARC, chave)
  tratados como genéricos; espera do limite 429 ignorando o cabeçalho do Brevo; STARTTLS sobre
  SSL e recusas sem código no Gmail SMTP; `NEXO_PUBLIC_URL` em branco impedindo o boot. E prepara
  o **teste real controlado** com confirmação da entrega no próprio NEXO.
- Uma **revisão adversarial independente** (correção, segurança e requisitos, com cada achado
  reproduzido) encontrou 2 problemas médios e vários baixos no próprio diff; todos foram
  corrigidos e cobertos por testes (seção 5.1).

## 1. Como o disparador funciona no ZIP original

| Aspecto | ZIP (`nexo_mvp`) |
|---|---|
| Transporte | Só Flask-Mail/SMTP. `config.py`: `MAIL_SERVER=smtp.gmail.com` (padrão), `MAIL_PORT=587`, `MAIL_USE_TLS` = texto `"true"`, `MAIL_USE_SSL=false`, `MAIL_USERNAME`/`MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` (padrão: `MAIL_USERNAME`), `MAIL_ATIVO` = usuário e senha preenchidos, `MAIL_DEBUG=False`. O `.env.example` higienizado cita `BREVO_API_KEY`/`BREVO_API_URL`, mas nenhum código do ZIP os lê. |
| Inicialização | `mail = Mail()` em `extensions.py` e `mail.init_app(app)` em `app.py`. Conexão padrão do Flask-Mail 0.10: sem prazo e STARTTLS sem verificação de certificado. |
| Mensagens | `Message(subject, recipients, html)` com `templates/emails/*.html`; remetente padrão. |
| Disparo | `enviar_email` inicia uma thread daemon (`_enviar_async`, com `app_context`) e devolve `True` só por ter agendado. Falha vira `logger.warning` com o texto da exceção. O log de sucesso registra assunto e destinatários. |
| Cadastro de empresa | Grava o e-mail como digitado; após o commit gera o token (e-mail assinado, 15 min), monta o link com `url_for(..., _external=True)` (host da requisição), **registra o link com o token no log**, agenda o envio e mostra "Enviamos ao cliente um link para definir a senha" sem saber o resultado. |
| Recuperação | Procura `email == e-mail digitado em minúsculas` (conta gravada com maiúsculas não é encontrada); **registra o link com o token no log**; resposta genérica; em DEBUG sem SMTP, mostra o link na tela. |

**Comportamento efetivo verificado** (o ZIP não traz testes de e-mail; o código dele foi executado
isolado, com SMTP falso em `127.0.0.1`, credenciais fictícias e qualquer outra conexão bloqueada):

| Cenário | Resultado |
|---|---|
| SMTP alcançável | Recuperação e boas-vindas chegam ao servidor SMTP, autenticadas. A conta com maiúsculas **não** recebe nada. Links em `http://localhost/...` (host da requisição). Log com link + token e destinatários. |
| SMTP bloqueado (como no Render Free) | Nenhuma mensagem; log "Connection refused"; a tela do admin diz "Enviamos ao cliente um link". |
| Sem credenciais | Nada enviado; em DEBUG, o link com token aparece na tela de quem pediu. |

**Reaproveitável:** a configuração do Gmail SMTP (todos os nomes e formatos de variáveis do ZIP
continuam lidos pela versão atual) e o modelo de envio em segundo plano com `app_context` (a
versão atual já o usa, com prazo e estados). **Não reaproveitável:** token e destinatário no log,
link montado pelo cabeçalho `Host`, confirmação falsa e busca de conta por grafia exata.

## 2. Como funciona na versão atual (`main` 7585df7)

- `emails.py`: `enviar_email` devolve um `EnvioEmail` com estado (`DESATIVADO`,
  `SEM_DESTINATARIO`, `AGENDADO`, `ACEITO_PELO_PROVEDOR`, `FALHA_NO_ENVIO`) e categoria do erro.
  Transporte: **API HTTPS do Brevo** quando há `BREVO_API_KEY`; senão **SMTP** (Flask-Mail com
  prazo e certificado verificado); sem credenciais, desativado. Uma linha de log estruturada por
  desfecho, sem destinatário, link, token ou chave.
- Cadastro: e-mail normalizado e validado; ativação enviada de forma **síncrona** após o commit,
  com mensagem ao admin conforme o resultado e referência do log; botão "Reenviar link de
  ativação".
- Recuperação: conta encontrada sem diferenciar maiúsculas; resposta pública genérica; envio em
  segundo plano; link na origem pública (`NEXO_PUBLIC_URL` ou `RENDER_EXTERNAL_URL`).
- Admin → Diagnóstico de e-mail: configuração sem segredos, pendências, envios recentes e envio
  de teste para o próprio admin.

**Verificação de ponta a ponta** (aplicação real, servidores falsos locais, TLS real):

| Cenário | Resultado |
|---|---|
| Brevo aceita (201) | POST `https://…/v3/smtp/email` com `api-key`, JSON (sender, to, subject, htmlContent, textContent, replyTo, tags, headers); estado `ACEITO_PELO_PROVEDOR` com `messageId`; 3 e-mails (2 recuperações, inclusive a conta com maiúsculas, e a ativação). |
| SMTP alcançável | As mesmas 3 mensagens, autenticadas, links `https://<origem pública>/auth/...`. |
| SMTP bloqueado | `FALHA_NO_ENVIO` / `smtp_conexao`; nada é dado como enviado. |
| Brevo recusa o IP (401) | `FALHA_NO_ENVIO` / `ip_nao_autorizado`; a mensagem do provedor não vai ao log. |
| Sem credenciais | `DESATIVADO`. |

## 3. Diferenças que causavam problemas

| # | Diferença / causa | Efeito | Situação |
|---|---|---|---|
| 1 | ZIP usa Gmail SMTP; o Render Free bloqueia SMTP desde 26/09/2025 | Nada sai; o ZIP ainda dizia "Enviamos" | Configuração: usar o Brevo (HTTPS) no Render; Gmail SMTP só fora do Render Free |
| 2 | `BREVO_API_KEY` com `sync: false` no `render.yaml` | Sem valor no painel, o envio fica `DESATIVADO` | Configuração manual (seção 8) |
| 3 | Remetente `@gmail.com` pelo Brevo | O Brevo troca o endereço por um domínio dele; favorece o spam | Configuração (domínio próprio) |
| 4 | Bloqueio de IP do Brevo × faixas compartilhadas do Render | HTTP 401 `ip_nao_autorizado` | Configuração (seção 8) |
| 5 | Deploy automático desligado | A versão no ar pode não ser a `main` | Conferir `/healthz` → `versao` |
| 6 | Telas de operação com jargão técnico e faixa vermelha no dashboard (PR #39) | Contra a apresentação profissional pedida | **Corrigido** |
| 7 | Recuperação dizia "enviamos" mesmo com o envio desligado | Confirmação falsa | **Corrigido** |
| 8 | Códigos de erro do Brevo em texto livre (ex.: `DMARC policy requires domain authentication`, `api-key not found`) descartados | Causa real (domínio, chave) virava erro genérico | **Corrigido** |
| 9 | 429 sem `Retry-After`: o Brevo documenta `x-sib-ratelimit-reset` | Nova tentativa cega ou espera errada | **Corrigido** |
| 10 | Gmail SMTP: SSL + TLS ligados faziam STARTTLS sobre SSL; recusas sem código | Envio na 465 falhava; "senha de app" e "cota diária" indistinguíveis | **Corrigido** |
| 11 | `NEXO_PUBLIC_URL` só com espaços escondia a `RENDER_EXTERNAL_URL` | Produção não subia | **Corrigido** |

## 4. Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `emails.py` | Códigos de erro do Brevo em texto livre (lista oficial, normalizados no log) e categoria `dominio_nao_autenticado` (DMARC); espera do 429 por `x-sib-ratelimit-reset`; código numérico das recusas SMTP (`534/5.7.9`) e categorias `smtp_senha_de_app` e `limite_excedido` (Gmail `5.4.5`); `consultar_entrega_brevo` (eventos de entrega por `messageId`, somente leitura); diagnóstico: SSL+TLS não bloqueia, porta × modo do Gmail, credenciais SMTP sem uso com o Brevo, remetente gratuito por transporte. |
| `extensions.py` | STARTTLS só sem SSL. |
| `config.py` | `PUBLIC_URL`/`PUBLIC_URL_PLATAFORMA` com `_env_texto` (em branco = ausente); `SMTP_PERMITIDO` (`NEXO_SMTP_PERMITIDO`, instância paga do Render). |
| `blueprints/auth.py` | Recuperação: quando a configuração impede qualquer envio (sem transporte ou com pendência bloqueante), mensagem neutra igual para qualquer endereço, sem consulta ao banco, com registro no histórico e aviso aos admins; mensagem genérica no futuro ("enviaremos"). |
| `blueprints/admin.py` | Mensagens das telas de operação verdadeiras e profissionais (causa técnica no Diagnóstico); dashboard sem a faixa técnica; rota `POST /admin/diagnostico-email/entrega/<correlacao>`. |
| `templates/admin/dashboard.html` | Remoção da faixa técnica de e-mail. |
| `templates/admin/diagnostico_email.html` | Etapas do teste controlado; ID no Brevo, eventos e botão "Consultar entrega". |
| `tests/test_disparador_emails.py` (novo) | Casos desta correção (seção 6). |
| `tests/test_emails_transacionais.py`, `tests/test_auth_tokens_security.py`, `tests/postgresql_auth_tokens.py`, `tests/test_contratos_portal.py`, `tests/test_security_deploy.py`, `tests/test_auth_email_flows.py` | Expectativas atualizadas para as mensagens novas; nos testes que substituem os gatilhos de e-mail, o transporte também é substituído. |
| `Docs/EMAILS_TRANSACIONAIS.md`, `README.md`, `.env.example` | Bloqueio de IP do Brevo conforme a documentação oficial; remetente gratuito; teste real em 4 etapas; Gmail SMTP fora do Render; avaliação da API do Gmail; conferência do deploy. |
| `Docs/INTEGRACOES/evidencias_disparador_emails/` (novo) | Capturas (dados fictícios): Diagnóstico com eventos de entrega (celular e desktop), dashboard sem faixa técnica e recuperação com envio desativado. Nenhuma rola na horizontal. |

Sem mudança de esquema do banco, sem dependência nova, sem alteração no `render.yaml`.

## 5. Correções realizadas

1. **Telas de operação** (cadastro de empresa, reenvio de ativação): mensagens continuam
   verdadeiras — aceito pelo serviço de e-mail, na fila, envio indisponível, resultado incerto
   ou falha (endereço do destinatário, instabilidade ou ajuste de configuração) — sempre com a
   referência, sem variáveis de ambiente, nome do provedor ou chave. A causa técnica da mesma
   referência fica no Diagnóstico de e-mail e no log (e, em produção, no sininho dos admins quando
   o provedor recusa ou o envio está desativado). O dashboard não tem mais a faixa técnica (o atalho
   "Diagnóstico de e-mail" continua no topo).
2. **Recuperação de senha**: com o envio de e-mail desligado no sistema todo, a página diz
   "No momento não é possível enviar o link de redefinição por e-mail…" para **qualquer**
   endereço, sem consultar o banco (não revela contas); com o envio ligado, a resposta genérica
   passou a "enviaremos" (no instante da resposta o envio está só agendado). Validade de 15
   minutos, assinatura, uso único, limites de tentativas, CSRF e anti-enumeração preservados.
3. **Brevo**: códigos oficiais em texto livre reconhecidos (`dominio_nao_autenticado` para DMARC;
   `api-key not found`/`Authentication failed` → chave recusada; `Insufficient credits`); só
   valores da lista oficial entram no log; 429 espera o `x-sib-ratelimit-reset` (até 5 s; acima
   disso não repete).
4. **Gmail SMTP** (fora do Render Free): STARTTLS nunca sobre SSL (porta 465 com o padrão
   `MAIL_USE_TLS=true` voltou a funcionar); recusas com código numérico no log (`534/5.7.9` →
   "senha de app"; `550/5.4.5` → cota diária), sem o texto do servidor; o Diagnóstico aponta
   porta × modo trocados.
5. **Teste controlado**: no Diagnóstico, cada envio aceito pelo Brevo mostra o ID da mensagem e
   o botão **Consultar entrega** (somente leitura, só para envios recentes deste processo, 20
   consultas/hora por admin), que mostra os eventos do Brevo (recebido, entregue, devolvido,
   bloqueado…) com horário — nunca destinatário, motivo, IP ou assunto.
6. **Configuração**: `NEXO_PUBLIC_URL` em branco vale como ausente. `NEXO_SMTP_PERMITIDO=1`
   (só em instância paga do Render) faz o SMTP no Render deixar de ser tratado como bloqueado.

### 5.1 Revisão adversarial do diff

Três leituras independentes (correção, segurança e requisitos), com verificadores que tentaram
refutar cada achado médio por reprodução. Todos os achados abaixo foram reproduzidos, corrigidos
e ganharam teste (`tests/test_disparador_emails.py`, classes `Revisao*`; os 15 testes novos
falham no código anterior às correções):

| Achado | Correção |
|---|---|
| (médio) Consulta de entrega que falhava aparecia depois como "Nenhum evento registrado" | A linha diz "A última consulta ao Brevo não foi concluída"; eventos já obtidos não são apagados |
| (médio) Destinatário recusado pelo Brevo (`email is not valid in to`) virava "ajuste de configuração" | Vira `destinatario_invalido` ("endereço do destinatário inválido ou não aceito", sem sugerir reenvio); causa desconhecida tem texto neutro |
| (médio) Recuperação prometia link com configuração que bloqueia todo envio (chave SMTP, URL sem https, remetente inválido, SMTP no Render) | Mesma mensagem neutra do envio desativado, para qualquer endereço; `NEXO_SMTP_PERMITIDO=1` para instância paga |
| (baixo) Abertura, clique e descadastro do cliente apareciam na consulta e no log | Só eventos de entrega são guardados, mostrados e registrados |
| (baixo) Data extrema ou JSON malformado do provedor derrubava a página/rota | Leitura à prova de falhas; data fora de 2000–2100 é descartada |
| (baixo) Status estendido SMTP lido em qualquer ponto do texto (dígitos de IP/endereço) | Só no início da resposta e da mesma classe do código |
| (baixo) "DMARC" num 429/5xx tirava a nova tentativa | Palavras de DMARC só valem na resposta 400 |
| (baixo) Cota diária pedia "tente em alguns minutos"; falha da consulta usava textos do envio | Texto próprio ("tente mais tarde"); a consulta tem mensagens próprias |
| (baixo) Sem a faixa do dashboard, o envio desativado ficou sem aviso proativo | Aviso no sininho dos admins (máx. 1 por categoria a cada 30 min, sem dados de conta) |
| (baixo) Diagnóstico dizia que `MAIL_USERNAME` ficava sem uso, mas ela pode ser o remetente; docs davam o deploy automático como desligado | Texto corrigido; docs mandam confirmar o Auto-Deploy no painel (o `render.yaml` declara desligado, o painel pode diferir) |

**Avaliada e não implementada — API do Gmail por HTTPS.** Funcionaria no Render Free e manteria o
remetente `@gmail.com` autenticado, mas exige OAuth 2.0 com refresh token da conta pessoal (que
deixa de valer com troca de senha, revogação, 6 meses sem uso ou 7 dias em modo de teste),
escopo sensível `gmail.send` (verificação do Google para uso não pessoal) e limite de ~500
envios/dia. O Brevo já contorna o bloqueio de SMTP; a alternativa ficou documentada no guia
(seção 11) para o caso de o dono preferir não ter domínio próprio.

## 6. Testes realizados

Ambiente: Python 3.12, dependências fixas do projeto, SQLite temporário, PostgreSQL 16 local
descartável e Chromium; rede bloqueada nos testes; nenhum envio real.

| Teste | Resultado | Evidência | Observação |
|---|---|---|---|
| T01 Cadastro de empresa com usuário válido | Aprovado | `CadastroEmpresaTests.test_t01_*` (SQLite e PostgreSQL); ponta a ponta com transportes reais | Empresa e usuário gravados; e-mail normalizado; ativação aceita; mensagem sem jargão |
| T02 Preparação e envio da ativação | Aprovado | `test_t02_*`; ponta a ponta (HTTPS real contra servidor falso) | Requisição completa ao Brevo; `messageId`; link `https` de 15 min; sem senha no e-mail |
| T03 Recuperação por e-mail | Aprovado | `RecuperacaoSenhaTests` (SQLite e PostgreSQL); `test_t03_com_envio_ativo_*` | Token válido, link na origem pública, envio agendado, resposta no futuro |
| T04 Link de redefinição | Aprovado | `TokensDoEmailTests` (expirado, já usado, HTTPS/CSRF) | Validade, uso único e CSRF preservados |
| T05 Gmail SMTP em ambiente compatível | Aprovado | `GmailSMTPTests` | Variáveis do ZIP selecionam o Gmail; STARTTLS com certificado verificado; SSL 465 sem STARTTLS; recusas `534/5.7.9`, `535/5.7.8`, `550/5.4.5`; Render marca SMTP como bloqueante |
| T06 API HTTPS do Brevo | Aprovado | `BrevoErrosTests`, `FalhasDoProvedorTests`, ponta a ponta | DMARC → `dominio_nao_autenticado`; chave SMTP/IP/remetente identificados |
| T07 Credenciais ausentes ou inválidas | Aprovado | `test_t05_*`, `test_t06_*`, `test_t07_codigos_em_texto_livre_*`, `test_t04_com_envio_desativado_*` | Sem credenciais: nada sai e nada é prometido, igual para qualquer endereço |
| T08 Falhas de conexão e erros do provedor | Aprovado | `test_t07_*`, `test_t08_429_*`, gateway/timeout | Nova tentativa só quando seguro; resultado incerto sinalizado |
| T09 Envios duplicados | Aprovado | `test_t09_cadastro_repetido_*`, `test_t13_*`, `test_t11_destinatarios_*` | Cadastro repetido não gera 2ª ativação; chamado resolvido não duplica; destinatários deduplicados |
| T10 PostgreSQL/Supabase | Aprovado | 5 suítes no PostgreSQL 16: 54 + 59 + 15 + 6 + 9 = **143 OK** | Inclui as variantes PostgreSQL de cadastro, recuperação e maiúsculas |
| T11 Segurança | Aprovado | `test_t15_*`, consulta de entrega sem dados pessoais, varredura de segredos | Nenhum token, senha, chave, destinatário ou texto do provedor em log, tela ou aviso |
| T12 Regressão | Aprovado | `discover` completo com navegador e cópias da CDN conferidas por SRI: **1138 testes OK** | 5 ignorados por exigirem os binários do PostgreSQL, rodados à parte no PostgreSQL 16: OK. Suítes afetadas: 326 OK; `test_disparador_emails`: 32 OK |
| Testes novos contra o código anterior | Aprovado | 15 dos 17 primeiros testes de `test_disparador_emails` falham na `main` anterior; os 15 testes da revisão falham no código anterior às correções | Passam nos dois o T09 e o STARTTLS na 587 (protegem comportamentos que já existiam) |
| Capturas no Chromium (390 px e 1440 px) | Aprovado | `Docs/INTEGRACOES/evidencias_disparador_emails/` | Sem rolagem horizontal |
| Integração real (Render/Brevo/caixa) | **Não executado** | — | Sem acesso aos painéis e sem autorização de envio real (seção 7) |

## 7. A integração real foi testada?

**Não.** Não houve acesso ao Render nem ao Brevo, nem autorização para enviar a endereços reais.
O teste controlado está preparado (guia, seção 7): depois do deploy e da configuração, o admin
usa *Diagnóstico de e-mail → Enviar e-mail de teste para mim* e registra cada etapa
separadamente:

| Etapa | Evidência | Situação |
|---|---|---|
| A aplicação iniciou o envio | Linha em "Envios recentes" e `correlacao=` no log | Pendente |
| O provedor aceitou | "Aceito pelo provedor" e ID no Brevo | Pendente |
| O provedor registrou a entrega | "Consultar entrega" → "Entregue ao servidor do destinatário" | Pendente |
| O destinatário recebeu | O próprio destinatário confirma na caixa de entrada (ou spam) | Pendente |

## 8. Configuração manual necessária

**Render** (*serviço → Environment*), sem inventar valores:

- `BREVO_API_KEY`: chave **de API** do Brevo (`xkeysib-…`), não a SMTP.
- `MAIL_DEFAULT_SENDER`: exatamente o remetente verificado no Brevo.
- `NEXO_PUBLIC_URL`: só se houver domínio próprio (`https://dominio`, sem caminho); sem ele,
  vale a `RENDER_EXTERNAL_URL`.
- `BREVO_API_URL`: deixar vazio (padrão `https://api.brevo.com/v3/smtp/email`).
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`:
  **não** usar no Render Free (portas bloqueadas). Junto com a chave do Brevo, `MAIL_PASSWORD`
  fica sem uso; com `MAIL_DEFAULT_SENDER` vazio, `MAIL_USERNAME` continua sendo o remetente.
  `NEXO_SMTP_PERMITIDO` fica vazio no plano Free.
- Depois de salvar: confirmar o deploy — o `render.yaml` declara o deploy automático desligado,
  mas o painel pode diferir (ver `Docs/PREPARACAO_RENDER.md`) — e conferir `GET /healthz` →
  `versao` igual ao commit da `main`. Se houver domínio próprio verificado no Render, incluí-lo em
  `NEXO_PUBLIC_URL` ou `NEXO_TRUSTED_HOSTS` (o health check usa esse domínio).

**Brevo:**

1. *SMTP & API → API keys*: gerar a chave de API (aparece uma vez).
2. *Senders*: adicionar e verificar o remetente (código de 6 dígitos). Recomendado: domínio
   próprio autenticado (código Brevo, DKIM e DMARC) em *Domains*.
3. *Settings → Security → Authorized IPs*: autorizar de uma vez todas as faixas de saída do
   serviço (*Render → serviço → Connect → Outbound*) ou desativar o bloqueio para a API.
4. Se o primeiro envio vier com 402/403 ou conta em validação: pedir ao suporte do Brevo a
   ativação do envio transacional.

## 9. Pull Request

[Helio965/Nexo---Faturamento-Inteligente---Render#40](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/40) — rascunho, da branch `claude/amazing-cannon-05671a` para a `main`. Commits: `a1ad40e` (código e testes), `2da9b7b` (documentação e evidências), `cd57cf8` (correções da revisão adversarial) e o commit que completa este relatório. Nenhum force push; nenhum deploy.

## Situação final

```text
CÓDIGO DO DISPARADOR:     CORRIGIDO E TESTADO
CADASTRO DE EMPRESA:      CORRIGIDO, AGUARDANDO CONFIGURAÇÃO
RECUPERAÇÃO DE SENHA:     CORRIGIDO, AGUARDANDO CONFIGURAÇÃO
INTEGRAÇÃO COM PROVEDOR:  CORRIGIDO, AGUARDANDO CONFIGURAÇÃO
CONFIGURAÇÃO DO RENDER:   PENDENTE DE VALIDAÇÃO REAL
ENTREGA REAL DE E-MAIL:   NÃO TESTADO
TESTES DE REGRESSÃO:      CORRIGIDO E TESTADO
```

Cadastro, recuperação e integração estão corrigidos e testados no código (com transporte
simulado e de ponta a ponta contra servidores falsos), mas o objetivo — o e-mail chegar ao
destinatário — depende da configuração externa da seção 8. A configuração do Render não pôde ser
vista: o `render.yaml` está correto, e os valores do painel e o deploy precisam ser confirmados.

## Fontes oficiais consultadas

- Render: [bloqueio de SMTP no plano Free](https://render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports), [IPs de saída](https://render.com/docs/outbound-ip-addresses), [plano Free](https://render.com/docs/free).
- Brevo: [envio transacional](https://developers.brevo.com/reference/sendtransacemail), [cabeçalhos de limite](https://developers.brevo.com/docs/limit-headers), [eventos por messageId](https://developers.brevo.com/reference/getemaileventreport-1), [segurança por IP](https://developers.brevo.com/docs/ip-security). Trechos da central de ajuda do Brevo (fase de aprendizado de IPs, troca do remetente gratuito) vieram de resumos de busca: a central recusa leitura automática.
- Google: [messages.send](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send), [escopos do Gmail](https://developers.google.com/gmail/api/auth/scopes), [OAuth 2.0 e expiração de refresh token](https://developers.google.com/identity/protocols/oauth2), [limites do Gmail](https://support.google.com/mail/answer/22839), [senhas de app](https://support.google.com/accounts/answer/185833).

## Observações fora do escopo (não alteradas)

- **Limite por IP no Render:** relatos públicos indicam que o `X-Forwarded-For` do Render tem
  dois saltos (cliente e borda do Cloudflare); com `PROXY_FIX_HOPS=1`, os limites por IP podem
  contar o IP da borda. Não foi observado no serviço real; confirmar contando as entradas do
  cabeçalho antes de mudar (e separar `x_for` de `x_proto`).
- **Health check × domínio próprio:** detalhado na seção 8 e no guia (seção 12).
- **Link de ativação manual:** sem provedor funcionando, o admin não tem como obter o link para
  repassar por outro canal (o ZIP o expunha no log). Criar essa função é uma decisão de
  segurança do dono (daria ao admin um meio de definir a senha do cliente).
- **Desenvolvimento:** sem `NEXO_PUBLIC_URL`, os links apontam para `http://127.0.0.1:5000`
  mesmo com outra porta; defina `NEXO_PUBLIC_URL` localmente.
