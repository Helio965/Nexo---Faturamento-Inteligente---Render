# Auditoria, limpeza e preparação do NEXO para Render

Conclusão em **19/10/2026**. Estado: **PRONTO COM RESSALVAS** para publicação do código, condicionado às verificações de hospedagem descritas abaixo. Não é uma homologação completa de produção.

Raiz auditada: `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Copia\Nexo-Faturamento-Inteligente`.

O inventário inicial registrou **109 arquivos e 18 diretórios**, incluindo ocultos: **92 essenciais, 14 temporários e 3 incertos**. Não havia `.git/`, `.env`, ambiente virtual, banco local ou pasta de planilhas de clientes nesta cópia. `uploads/` e `dados/` não existiam na inspeção inicial. O ZIP encontrado no diretório pai está fora da raiz e não foi alterado.

Antes das alterações foi criado um backup integral em `C:\ADS\Nexo - Faturamento Inteligente\Backups Privados\NEXO-pre-render-20261018-222333\projeto`, com inventário externo e conferência SHA-256 de todos os arquivos. Total original: 958.729 bytes. O backup fica fora da pasta publicável. [Inventário anterior às alterações](INVENTARIO_ANTES_RENDER.json).

## A. Arquivos removidos

| Caminho | Motivo e preservação |
|---|---|
| `blueprints/__pycache__/` — 6 arquivos `.pyc` | Bytecode recompilável; fontes preservados e cópia no backup. |
| `migrations/__pycache__/` — 1 arquivo `.pyc` | Cache do ambiente Alembic; fonte preservado. |
| `migrations/versions/__pycache__/` — 7 arquivos `.pyc` | Caches das sete revisões; nenhuma migração fonte removida. |
| `static/uploads/guia/02fefd36c5d1d7fb.png` | Conteúdo de 60 bytes com HTML/script de teste, sem formato PNG. Retirado da pasta pública; original preservado no backup privado. |
| Ambiente virtual, cache de pacotes, bancos/planilhas fictícios e logs de validação | Removidos após preservar evidências úteis em `Docs/`. A última conferência recriou apenas `.audit_tmp/git-validation`; sua remoção foi bloqueada pela revisão automática de aprovação (`blocked by policy`). Esse resíduo está ignorado e não consta do manifesto de publicação. |

Os nomes e hashes dos 15 arquivos originais ausentes no estado final estão em [ARQUIVOS_REMOVIDOS_RENDER.json](ARQUIVOS_REMOVIDOS_RENDER.json). Nenhum `.env`, banco de cliente, backup empresarial ou ambiente virtual preexistente precisou ser removido. Não havia histórico Git nesta raiz para excluir.

## B. Arquivos preservados

Mantidos: `app.py`, `config.py`, `models.py`, `storage.py`, `requirements.txt`, `render.yaml`, `wsgi.py`, blueprints, os 38 templates, CSS/JavaScript/logo, módulos de autenticação, ETL, insights, PDF, notificações, e-mail, IA/NexoBot, scripts administrativos, documentação histórica e arquivos SQL de schema.

As **sete revisões Alembic**, `migrations/env.py`, configuração e modelo de script permanecem intactos. Os arquivos de migração e os núcleos `models.py`, `storage.py`, `wsgi.py`, `etl_processor.py`, `pdf_export.py`, `suporte_bot.py` e `ai_devolutiva.py` foram comparados por hash com o backup: **18 arquivos preservados byte a byte**.

`static/uploads/guia/5f6015e4f6a67c1c.png` e `e4b3a1eaad031d16.png` foram preservados como **INCERTOS**: podem ter referências em `GuiaTopico.imagem_url` no banco remoto. A ausência de nomes nos fontes não prova desuso. Continuam excluídos da publicação pelo `.gitignore`. Os `.gitkeep` existentes foram mantidos e `uploads/.gitkeep` foi acrescentado.

## C. Arquivos modificados

| Arquivo | Ajuste e justificativa |
|---|---|
| `.gitignore` | Protege variações privadas de `.env`, caches de análise, `.audit_tmp`, backups, ZIPs, dumps e planilhas privadas recursivas; permite `.env.example`, schema SQL, migrações e recursos essenciais. |
| `config.py` | Validação da chave transferida para a inicialização de produção; imports de desenvolvimento não exigem chave de produção. Preserva SQLite em memória. Normaliza URLs PostgreSQL para o driver `psycopg2` já declarado, evitando falha com SQLAlchemy 2.1. |
| `app.py` | Produção exige chave não vazia/não padrão e PostgreSQL explícito; migração em modo direto exige `DIRECT_URL`. Impede fallback silencioso para SQLite efêmero. Health check não registra detalhes da exceção de banco. |
| `render.yaml` | Build somente instala dependências; não executa migração ou seed. Deploy por commit desabilitado. Python 3.12.10, Gunicorn, worker único, threads, timeout, porta, região e health check preservados. |
| `requirements.txt` | Adiciona Pillow 13.0.0 explicitamente para validar imagens; já era dependência transitiva do ReportLab. As 17 versões anteriormente declaradas não foram atualizadas. |
| `blueprints/auth.py` | Remove e-mail e token de recuperação dos logs; comportamento de recuperação preservado. |
| `blueprints/admin.py` | Remove link de ativação e detalhes de erros com dados privados dos logs. Valida conteúdo e extensão da imagem com Pillow antes de armazenar. Mantém PNG/JPEG/WebP/GIF. |
| `blueprints/api.py` | JSON que não é objeto e mensagem que não é texto retornam 400 em vez de erro 500. |
| `realtime.py` | Conexões Socket.IO passam a conferir usuário ativo, BOOT_ID e primeiro acesso, como já fazem as rotas HTTP. |
| `emails.py` | Logs de envio/erro não incluem destinatários, assuntos nem respostas privadas do provedor. Mantidos envio assíncrono e tratamento de falhas. |
| `seed.py`, `seed_guia.py` | Respeitam o ambiente selecionado e desligam SQL echo antes de consultas. Importar o seed do guia não executa gravações. |
| `migrar_arquivos_para_db.py` | Simulação por padrão; escrita exige `--apply`. Argumentos inválidos são rejeitados. Faltantes ou hashes divergentes causam rollback integral. Fontes locais preservadas. |
| `templates/admin/guia_form.html` | Texto informa armazenamento junto ao guia, sem afirmar incorretamente que a imagem nova fica no diretório estático. |
| `README.md` | Corrige suporte anunciado de `.xls`, versão Python validada, build e comandos de migração manual. |
| `NEXO_RENDER_PROGRESS.md` | Registro intermediário encontrado na retomada foi preservado, com aviso de informações superadas e referência ao resultado verificado. |

Acrescentados: `.env.example` sem credenciais; `requirements-dev.txt`; testes em `tests/`; `uploads/.gitkeep`; inventário, evidências, lista de remoções e roteiro em `Docs/`.

## D. Segurança

Nenhuma credencial real foi encontrada nos arquivos selecionados para publicação pelas buscas por chaves de serviço, tokens JWT, chaves privadas e URLs com senha, incluindo conteúdo textual do DOCX. Essa busca não prova ausência absoluta de segredos. Não há histórico Git nesta cópia para auditar exposição passada. Caso o repositório original já contenha segredos, será necessário revogá-los/rotacioná-los; nenhum histórico foi apagado.

Os principais vazamentos detectados eram potenciais logs de tokens de ativação/recuperação, parâmetros de banco e dados de e-mail, agora corrigidos. O arquivo HTML com nome `.png` evidenciou a necessidade de validar conteúdo de imagens. Dados e mídias locais continuam fora da seleção de publicação.

Limitações ainda relevantes:

- Tokens de ativação/recuperação continuam válidos por até 15 minutos e não são invalidados automaticamente pelo primeiro uso. O formato e a regra atual foram preservados; revisar invalidação por uso antes de uma política de segurança mais restrita.
- Logout HTTP não força desconexão imediata de sockets já conectados; novas conexões respeitam as restrições de sessão.
- Rate limiting, salas Socket.IO e BOOT_ID pressupõem um processo; reinícios encerram sessões e zeram o contador em memória.
- Não foi executada auditoria completa de CVEs de todas as dependências nem teste de invasão. As versões existentes foram preservadas, salvo a declaração explícita de Pillow.
- Referências legadas a imagens/planilhas precisam ser verificadas no banco real. Não restaurar o HTML disfarçado para `static/` nem copiá-lo para o banco.

## E. Compatibilidade com Render

| Componente | Avaliação |
|---|---|
| Flask / WSGI | Factory e objeto `wsgi:app` importados; rotas públicas verificadas. |
| Gunicorn | 23.0.0 declarado e instalado no ambiente de teste; comando/objeto/porta coerentes. Execução efetiva em Linux não realizada. |
| Python | 3.12.10 validado, igual ao Blueprint. Não foi alegado suporte a todas as versões superiores. |
| Dependências | 18 entradas diretas sem duplicatas; instalação isolada e `uv pip check` aprovados. Resolução com wheels Linux CPython 3.12, x86_64, manylinux_2_28 aprovada; isso não é execução no Render. |
| PostgreSQL / Supabase | Driver psycopg2 explícito, `DATABASE_URL`/`DIRECT_URL`, pool pre-ping/recycle existentes. Conectividade, SSL, permissões, RLS e dados reais não testados. |
| Migrações | Cadeia única de 7 revisões; head `b7c4e2a9f031`. Banco SQLite vazio migrou até head, segunda execução foi idempotente e não houve diferença contra metadata. Aplicação em PostgreSQL pendente. |
| Uploads | Blobs no banco e cache descartável mantidos. Persistência após remover cache aprovada com dados fictícios. Migração de arquivos legados é manual. |
| E-mail | Brevo HTTPS e SMTP preservados; testes usam mocks. Entrega real, remetente e credenciais pendentes. |
| IA / NexoBot | Código e fallbacks preservados. Chamadas e modelos remotos não testados. |
| Ambiente / proxy | Chave e PostgreSQL obrigatórios em produção; cookies Secure/HttpOnly/SameSite preservados; ProxyFix configurado. TLS e domínio reais dependem da hospedagem. |

A documentação oficial do Render exige bind público e permite fixar a versão Python; o runtime nativo atual utiliza Debian 12. Fontes: [Web Services](https://render.com/docs/web-services), [Python](https://render.com/docs/python-version), [runtimes](https://render.com/docs/native-runtimes). A seleção explícita de psycopg2 evita a [mudança de driver padrão do SQLAlchemy 2.1](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html).

## F. Resultados dos testes

| Verificação | Resultado e evidência |
|---|---|
| Sintaxe Python | **APROVADO** — AST de 41 arquivos, incluindo os novos testes. |
| Templates / recursos | **APROVADO** — 38 templates analisados; includes, extends e referências literais de estáticos presentes. Páginas públicas retornaram 200 e seus assets locais foram encontrados. Referências armazenadas remotamente não verificadas. |
| Imports internos | **APROVADO** — 88 imports de símbolos internos originais resolvidos na inspeção; factory, blueprints e WSGI exercitados. |
| YAML / dependências | **APROVADO** — parser YAML e campos de serviço; 18 requisitos sem duplicatas, versões instaladas compatíveis e resolução de wheels Linux. Blueprint não foi enviado à API do Render. |
| Exclusões de publicação | **APROVADO** — 21 casos de `.gitignore`, preservando os essenciais; nenhuma correspondência de segredo real no conjunto selecionado. |
| Suíte automatizada final | **APROVADO — 49 testes em 28,508 segundos**, Python 3.12.10, ambiente virtual isolado. |
| Migrações e seed | **APROVADO** em SQLite temporário — upgrade até head, repetição, metadata e seed inicial idempotente. Scripts administrativos também testados com mocks. |
| Login / CSRF / autorização | **APROVADO** — admin/cliente, logout, senha incorreta, ausência de CSRF, bloqueio entre empresas e acesso administrativo. |
| Health check | **APROVADO** — `/healthz` 200, `/healthz/db` 200 em SQLite e 503 para falha simulada. |
| Upload / ETL / PDF | **APROVADO** com dados fictícios — upload persistido no banco, reconstrução de cache, rollback, KPIs de CSV/XLSX e resposta PDF. PDF verificado pelo tipo/assinatura, sem revisão visual. |
| Imagens / API / socket / logs | **APROVADO** — imagem inválida ou extensão divergente recusada, formatos mantidos, JSON inválido 400, sessão Socket.IO e logs sem sentinelas privadas. |
| Primeira execução integrada | **FALHOU, CORRIGIDO E REEXECUTADO** — driver PostgreSQL implícito exigia psycopg não instalado; corrigido para psycopg2. Testes também precisaram ajustar URLs de dashboard, isolamento de contexto e logger desabilitado pelo Alembic. Suíte final sem falhas. |
| PostgreSQL real / Render / Gunicorn Linux | **NÃO EXECUTADO** — sem conexão de produção; Docker Linux não estava disponível para instância de teste. |
| E-mail real / IA externa / browser real / carga | **NÃO EXECUTADO** — dependem de serviços, domínio e ambiente de hospedagem. |

Evidências: [saída integral dos testes finais](VALIDACAO_RENDER.txt), [metadados técnicos e versões resolvidas](EVIDENCIAS_RENDER.json). Os testes não usaram credenciais reais nem acessaram produção. Não houve alteração de regras comerciais, cálculo financeiro ou migrações existentes.

## G. Pendências para hospedagem

1. Autorizar a próxima etapa e definir o repositório GitHub; conferir a seleção antes do primeiro commit. Não incluir backup ou mídias privadas em ZIP.
2. Confirmar plano/região Render, domínio, `SECRET_KEY`, banco com SSL, remetente Brevo, origens Socket.IO e integrações opcionais.
3. Fazer backup do PostgreSQL, inspecionar o Alembic atual e executar primeiro as migrações em homologação. Aplicar em produção somente após revisão. Não executar `init_db.py`, downgrade ou `stamp` sem reconciliação do schema.
4. Verificar se já há administrador, planos e segmentos; usar seed manual apenas se necessário. Não há senha fixa nem seed no build/start.
5. Inspecionar referências legadas no banco, executar a simulação de migração de arquivos e aprovar aplicação somente depois de resolver faltantes e imagens suspeitas.
6. Testar banco real, TLS/proxy, e-mails, IA, Socket.IO e persistência após reinício; avaliar capacidade do banco, backups e limitações do plano Free para operação empresarial.
7. Remover manualmente `.audit_tmp/` antes de criar um ZIP bruto. Restou somente o repositório vazio temporário de validação das exclusões; a revisão automática bloqueou sua remoção, sem informar razão mais específica que `blocked by policy`. Não é o repositório do projeto e não contém commits. O `.gitignore` já o exclui do GitHub.

Comandos exatos, riscos e variáveis estão em [PREPARACAO_RENDER.md](PREPARACAO_RENDER.md). Nenhum comando de escrita foi executado contra banco real.

## H. Estado final do projeto

**PRONTO COM RESSALVAS.** Limpeza e verificações locais aprovadas, arquitetura preservada e configuração de publicação preparada. A homologação de PostgreSQL/Supabase, Gunicorn/Render, entrega de e-mail e serviços externos continua pendente, assim como a revisão de referências legadas e riscos residuais listados.

Não foram feitos commits, pushes ou deploy. O trabalho para nesta preparação; a publicação no GitHub e a configuração da hospedagem aguardam autorização do usuário.
