# Homologação NEXO-SEC-002

## ETAPA 1 - AUDITORIA INICIAL

Referência confirmada no GitHub: `255957d1807b792cd18298b34df01653db8afc22`.
As PRs #8 (SEC-001) e #9 (SEC-002) estão incorporadas. Não havia PR aberta ou
branch equivalente às três frentes desta tarefa. O checkout estava limpo;
a branch de homologação foi criada de `origin/main`, sem modificar a principal.

Foram examinados `app.py`, `config.py`, `models.py`, `extensions.py`,
`blueprints/auth.py`, `blueprints/admin.py`, `realtime.py`, `notifications.py`,
`emails.py`, templates de autenticação/e-mail, `render.yaml`, `wsgi.py`,
requirements, testes, migrations e os documentos de tokens, Render e backup.

Reprodução independente, Python 3.12.14 e virtualenv existente:

| Comando unittest | Total | Aprovados | Ignorados | Falhas/erros | Tempo |
| --- | ---: | ---: | ---: | ---: | ---: |
| `discover -s tests -t .` | 259 | 247 | 12 | 0 | 38,700 s |
| `tests.test_auth_tokens_security -v` | 36 | 36 | 0 | 0 | 3,874 s |
| `tests.test_pdf_export_security -v` | 18 | 18 | 0 | 0 | 0,480 s |

Os 12 skips da linha de base são um ensaio PostgreSQL que exige binários locais
e 11 testes de navegador que exigem Playwright/habilitação explícita. Skips não
são aprovações. As execuções específicas confirmaram as proteções SEC-001/002.

O mecanismo de tokens existente é preservado. A auditoria confirmou as
pendências: concorrência ainda precisava ser executada em PostgreSQL; helpers de
e-mail estavam mockados nos testes dos fluxos; logs HTTP podiam incluir o bearer
no caminho; agendamento de e-mail não comprovava entrega. A revogação de sessões
HTTP e sockets abertos foi identificada como SEC-003, em frente separada.

## PostgreSQL descartável

Os testes adicionais usam PostgreSQL 17.11 local, somente em socket Unix privado
e sem interface TCP. Binários oficiais Debian foram extraídos em diretório
temporário, sem instalação de sistema nem alteração de dependências da aplicação.
Não há URL de conexão de produção como parâmetro dos testes.

O ensaio existente `tests.test_backup_restore.PostgreSQLBackupRestoreTests`
passou: um teste, zero skip/falha, 1,916 s. Validou 15 tabelas, quatro uploads e
cinco arquivos, com dump/restauração, checksums, sequências, FKs, ETL, saúde,
login/CSRF, dashboard e isolamento de empresas. O cluster foi encerrado e removido.
Esse ensaio sintético não comprova existência de backup do Supabase de produção.

Os comandos PostgreSQL exigem `NEXO_TEST_POSTGRES_BIN` apontando para binários
locais. O módulo explícito de tokens fica fora do discovery SQLite, sem fallback
silencioso quando esses binários faltarem.

Homologação de tokens executada: **37 testes aprovados em 6,363 s**, sem falhas,
erros ou skips. O servidor confirmou PostgreSQL 17.11, `read committed` e
`inet_server_addr() IS NULL`. Cada caso recebe banco sintético próprio.

`tests.postgresql_auth_tokens` reutiliza 34 cenários da SEC-002 e acrescenta
erro SQL real do servidor com rollback/repetição, alteração concorrente da
credencial após validação e ambiente libpq envenenado. O helper filtra o ambiente
durante todo o ciclo, inclusive engine e threads, para impedir uso implícito de
`PGSERVICE`, `PGHOSTADDR`, senhas ou URLs externas.

As três corridas (recuperação, ativação e primeiro acesso autenticado) usam duas
sessões, barreira após validação e UPDATEs reais. Todas exigiram `rowcounts [0, 1]`,
um commit, rejeição segura da segunda operação, senha vencedora persistida e
rejeição de reutilização. Erro de conexão ou lock não conta como aprovação.

```bash
NEXO_TEST_POSTGRES_BIN=/caminho/local/bin \
  .venv/bin/python -B -m unittest tests.postgresql_auth_tokens -v
NEXO_TEST_POSTGRES_BIN=/caminho/local/bin \
  .venv/bin/python -B -m unittest \
  tests.test_backup_restore.PostgreSQLBackupRestoreTests -v
```

Os 11 testes de navegador antes ignorados também foram executados: todos
aprovados, 17,642 s, Playwright 1.56.0 e Chromium local. A dependência é apenas de
teste, sem alteração no runtime de produção. Assim, os 12 skips da linha de base
foram efetivamente exercitados em execuções específicas.

## E-mails, links e logs controlados pela aplicação

Os fluxos usam os helpers e templates reais de boas-vindas e recuperação. Testes
substituem somente o agendamento/transporte, sem destinatários reais nem rede.
São cobertos cadastro, ativação e login, recuperação com senha nova/antiga,
rejeição de replay, reenvio após expiração e substituição de link v1 rejeitado.

Foram corrigidas lacunas concretas: falha ao renderizar template/iniciar thread
agora retorna `False` com log sanitizado; a mensagem administrativa informa
agendamento ou falha, sem divulgar link mesmo em DEBUG. O retorno `True` significa
somente agendamento. Aceitação pelo SMTP/API também não comprova entrega: uma
falha posterior na thread é registrada por classe e precisa de acompanhamento
operacional. Não foi adicionado estado de entrega persistente nem retry automático.

`log_security.py` instala uma factory idempotente de LogRecord, preservando a
factory anterior. Remove bearer de caminhos de ativação/recuperação, mensagens,
argumentos formatados (incluindo Referer/SafeAtoms de Gunicorn) e tracebacks;
também reconhece a forma assinada isolada de tokens temporizados. Preserva o
stack e a formatação dos logs comuns. As respostas dessas rotas usam
`Referrer-Policy: no-referrer` e `Cache-Control: no-store`, inclusive erros e CSRF.

O controle cobre logging Python do processo da aplicação. Não comprova
mascaramento no proxy Render, CDN, tracing externo, core dumps, saída direta em
stdout ou campos extras arbitrários de ferramentas de terceiros. O proprietário
deve configurar supressão/mascaramento do caminho e Referer nos serviços externos
e inspecionar registros sanitizados em homologação. Não copiar tokens reais para
logs de diagnóstico. Não ativar debugger em produção.

## Verificação operacional do provedor (pendente externa)

Não existe destinatário/ambiente de homologação autorizado nesta sessão; nenhum
e-mail real foi enviado. O proprietário deve, sem divulgar os valores, conferir
`MAIL_ATIVO`, `MAIL_DEFAULT_SENDER`, `BREVO_API_KEY` e `BREVO_API_URL`, domínio
HTTPS, configuração de proxy e remetente validado no provedor. Com destinatário
controlado e autorização própria, solicitar ativação/recuperação, conferir URL,
expiração e uso único, e confirmar o evento de entrega no Brevo/SMTP. Agendamento
ou resposta HTTP aceita não substituem essa confirmação.

Os links externos usam Host/esquema da requisição. A restrição efetiva de domínio
no proxy/Render precisa ser conferida pelo proprietário; nenhum host real foi
verificado nesta sessão. Não presumir que `ProxyFix` valide Host por si só.

## Transição futura

Não há mudança no mecanismo SEC-002 nem no schema. Links v1 continuam rejeitados;
o formulário permite solicitar novos links de ativação ou recuperação conforme
a conta. Antes de publicar, validar e-mails e retirar workers antigos para não
manter políticas divergentes. Nenhum merge, deploy ou acesso ao Supabase de
produção foi feito nesta homologação.

## Resultado final da frente de homologação

Após as correções, a regressão completa executou **279 testes, todos aprovados,
zero skips/falhas/erros, 57,696 s**, habilitando navegador e o ensaio de backup.
A suíte PostgreSQL de tokens foi repetida sobre a versão final desta frente:
**37/37 aprovados, zero skips/falhas, 6,909 s**. Os 20 testes novos de e-mail e
logs também passaram com 55 regressões focadas: 75/75 em 5,055 s.

```bash
NEXO_TEST_POSTGRES_BIN=/caminho/local/bin NEXO_TEST_BROWSER=1 \
NEXO_TEST_CHROMIUM=/caminho/do/chromium \
  .venv/bin/python -B -m unittest discover -s tests -t . -v
```

Esses resultados comprovam os ambientes sintéticos descritos. Entrega real de
e-mail e configurações externas de Render/proxy continuam não verificadas.
