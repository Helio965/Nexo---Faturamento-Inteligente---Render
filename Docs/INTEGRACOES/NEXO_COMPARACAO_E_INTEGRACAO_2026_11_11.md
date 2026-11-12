# Auditoria comparativa e integração seletiva — NEXO

Data da auditoria: 11/11/2026, America/Sao_Paulo. A implementação usa o estado atual do repositório de Hélio e preserva sua landing page. Não houve clone, merge, deploy, envio real de e-mail ou alteração de produção.

## Parte A — Comparação dos projetos

| Fonte | Commit examinado | Arquivos | ZIP × GitHub |
|---|---|---:|---|
| `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente` | `91e5fb06fe0c56f9a4d0bc272a07f9d8c2501e22` | 431 | 431 blobs idênticos |
| `Helio965/Nexo---Faturamento-Inteligente---Render` | `46a342066ef73408a794fd5abb75f177aa380ed2` | 370 | 370 blobs idênticos |

A comparação confirmou 366 caminhos compartilhados: 267 idênticos e 99 diferentes; 65 exclusivos da referência e quatro exclusivos do destino. O inventário por arquivo e sua decisão estão em [nexo-integracao-inventario.csv](nexo-integracao-inventario.csv). Os relatos históricos anexos e em `Docs/` foram usados como contexto; os resultados abaixo se baseiam nos arquivos e testes desta execução.

Tipos: A funcionalidade exclusiva da referência; B implementação compartilhada; C implementação do destino preservada; D segurança/estabilidade; E interface; F banco; G documentação/infraestrutura.

| Tipo | Função e arquivos principais | Referência × destino | Risco / decisão | Estado e validação |
|---|---|---|---|---|
| B/C | Ativação, recuperação e tokens: `contas_email.py`, `origem_publica.py`, auth | A base já tem normalização, tokens de uso único, origem HTTPS confiável e anti-enumeração | Preservar infraestrutura do destino; combinar hardening de redirecionamento e credenciais | Integrado; suítes auth/tokens/e-mail |
| A/D | E-mail alterado, BCC de chamado e preferências: `emails.py`, `configuracoes_conta.py`, `notifications.py` | Recursos adicionais na referência | Integrar após commit, com reautenticação para configurar a caixa e sem expor BCC | Integrado; mocks, falha pós-commit, opt-out |
| B/D | Brevo, SMTP e diagnóstico: `config.py`, `extensions.py`, diagnóstico admin | Transporte HTTPS já existente; referência amplia diagnóstico SMTP local | Conservar alias `NEXO_RENDER`, bloquear SMTP centralmente e também no diagnóstico quando hospedagem o impede | Integrado; nenhuma conexão/envio real |
| A/D | Renovação e lembrete de aceite: conta, contratos, CLI, templates e-mail | Ausentes no destino | Sem cron; simulação padrão; resultados incertos preservam deduplicação e exigem conferir o provedor antes de reenvio | Integrado com correção adicional à referência |
| A/D/F | Configurações de conta: auth, preferências e telas cliente/admin | Troca de senha/e-mail, revogação de sessões, perfil e exportação presentes só na referência | Integrar CAS, confirmação e escopo da sessão; pedido de exclusão abre chamado, sem apagar dados | Integrado; SQLite/PostgreSQL/navegador |
| A/D/F/E | Documentos legais e aceites: `termos_legais.py`, modelos e telas | Versionamento e aceite explícito ausentes no destino | Sem texto jurídico automático; sem documento publicado não há bloqueio; preservar saídas de privacidade | Integrado; autorização, CSRF, concorrência, esquema ausente |
| B/C | Contratos: `contract_policy.py`, `contract_admin.py`, `plan_catalog.py` | Idênticos | Preservar preços, cadência, contratos e coberturas existentes | Preservado byte a byte |
| A/F/E | Novos planos/entitlements, onboarding e Raio-X | Catálogo e diagnóstico novos; condições de atendimento diferem da landing oficial | Preparar pacote completo com `NEXO_NOVOS_PLANOS_HABILITADOS=0`; endpoints 404 e menus ocultos até revisão comercial | Implementado, desativado por padrão; testes opt-in |
| A/F | Leads de Avaliação de Cenário: modelos, migração e CLI | Referência contém infraestrutura e expurgo, sem captação pública | Integrar infraestrutura explicitamente delimitada; nenhum formulário público nem agenda inventados | Preparado; TTL, UUID, RLS e concorrência em PG |
| A incompleto | Avaliações de clientes: `avaliacoes.py`, blueprint e templates | Importam quatro modelos e cinco constantes inexistentes; migração citada ausente; blueprint não registrado nem na referência | Não copiar código órfão que causaria ImportError; conclusão exige esquema e regras próprios revisados | Adiado integralmente |
| A/D | Segurança de uploads: `security_gatekeeper.py`, `etl_*` | Referência tem assinaturas de conteúdo, triagem XLSX ativa e neutralização CSV/Excel | Integrar conservando subprocessos, limites, autorização e motor financeiro do destino | Integrado; arquivos maliciosos, portal, worker e limites |
| B/C | Parser financeiro, status de vendas e ABC: `etl_processor.py`, fixtures | Referência muda milhares/decimais, cancelamentos/devoluções e top20 para ranking completo | Preservar regras/fixtures do destino; única correção: sinal de negativo escapado com apóstrofo, necessária à neutralização | Equivalência do corpus original e regressão negativa específica |
| A/F | Trava total PDV: `validacao_pdv.py`, rotas e publicação | Exige nova semântica bruto/devoluções; bloqueia publicação se esquema ausente | Não integrar bloqueio nem telas isoladas. A tabela da migração ancestral é reservada, sem uso operacional | Adiado com a revisão financeira |
| B/C | Indicadores, PDF, API, armazenamento e IA | Módulos centrais idênticos | Preservar conceitos financeiros e controle contratual | Preservado; regressões existentes |
| B/C | Horário: `horario.py`, suporte e notificações | Correção UTC/Brasília já existe nos dois | Preservar; não converter registros históricos por estimativa | Testes existentes e navegador |
| A/D/E | Suporte | Referência adiciona cards, preferências e cópia de novo chamado | Combinar com fluxo pós-commit; reabrir chamado limpa data de fechamento; eager loading evita N+1 | Integrado; isolamento, horário, idempotência e regressão |
| A/B | NexoBot | Referência descreve também PDV/ABC/planos diferentes | Incorporar apenas orientações e navegação de Configurações; preservar conhecimento financeiro/comercial legado | Seleção testada pelo corpus |
| E/C | Landing oficial, vídeo e identidade de Hélio | Destino tem redesign próprio recente | Não copiar landing/CSS/JS/vídeos da referência | Hashes protegidos idênticos |
| A/E | Tema do portal e acessibilidade | Referência adiciona tema claro opcional, persistência e cores dos gráficos | Aplicar apenas ao portal autenticado; landing independente permanece intacta | Integrado; testes CSS/HTML e navegador |
| F/G | Alembic e banco | Head destino `b6935e8de9d4`; referência `f4c2a8e1d9b6` | Cadeia linear aditiva testada em banco descartável; nenhuma migração de produção | Preparado para revisão |
| D/G | Workflow bootstrap exclusivo de Hélio | URI aceita não funcionava com SQLAlchemy 2.1; esquema existente com Alembic era aceito | Forçar psycopg2; abortar se qualquer tabela já existir em `public`; manter workflow manual e confirmação | Corrigido; teste executa sonda real em PG privado |
| G/C | Render e dependências | `render.yaml` e requirements iguais | Preservar infra, versões fixadas, build sem migração/seed e processo Gunicorn | Sem dependência de produção nova |

## Parte B — Melhorias implementadas

O fluxo de credenciais usa senha atual, confirmação, limites por usuário, atualização condicional e revogação das demais sessões. Os avisos de segurança continuam obrigatórios. Preferências opcionais afetam chamados e renovação. O administrador pode corrigir o acesso de um cliente, mediante sua própria senha, invalidando a senha/sessões antigas e emitindo convite seguro.

O diagnóstico separa transporte desativado, destinatário inválido/ausente, agendamento, aceitação pelo provedor, falha conhecida e resultado incerto. Aceitação pelo Brevo não é comprovação de entrega. O bloqueio SMTP agora também ocorre antes de iniciar a tarefa de envio; não depende de a rota consultar o diagnóstico. Recuperação, cadastro e demais fluxos compartilham a guarda. Credenciais e destinatários não são registrados em logs técnicos.

Os lembretes de renovação são manuais. Uma resposta de rede incerta mantém o marcador já persistido e informa a incerteza ao operador, impedindo repetição automática. Não foi criada cobrança, renovação financeira ou agendador.

O filtro de uploads rejeita conteúdo incompatível com a extensão, executáveis/disfarces e conteúdo ativo de XLSX; quando necessário, produz cópia passiva e neutraliza células perigosas. O parser legado conserva o sinal de números negativos escapados por apóstrofo. Essa correção específica pode mudar o resultado de um arquivo que antes interpretava `'-10,00` como positivo; ela está coberta por regressão explícita, sem trocar a fixture financeira histórica.

O Raio-X novo utiliza `raio_x_entradas.py`, separado do motor dos relatórios mensais. Não altera os KPIs existentes. A ativação exige revisão das condições comerciais documentadas em [PLANOS_E_RAIO_X.md](../PLANOS_E_RAIO_X.md). O escopo e as limitações da infraestrutura de leads estão em [LEADS_INTEGRACAO.md](../LEADS_INTEGRACAO.md).

## Parte C — Funcionalidades preservadas

`templates/landing.html`, `static/css/landing.css`, `static/js/landing.js`, `static/js/landing-video.js`, `static/video/` e `Docs/landing-redesign/` têm os mesmos bytes do commit-base. A evidência individual está em [nexo-preservacao.json](nexo-preservacao.json).

Foram preservados autenticação/tokens existentes, Socket.IO, sessões vinculadas ao servidor, políticas contratuais, preços, cadências, indicadores/PDF, isolamento de empresas, limites de recursos e configurações Render. Nenhum seed foi executado contra produção. Não foram inventados documentos legais ou presumidos aceites.

## Parte D — Testes realizados

Resultados exatos, duração, falhas e skips das execuções completas constam em [nexo-validacao.json](nexo-validacao.json). Execuções intermediárias com falhas de integração foram corrigidas; não são contadas como aprovações. Resultados de subtestes PostgreSQL são discriminados dos métodos `unittest`, sem inflar contagens ou somar suítes sobrepostas.

Resultados consolidados (métodos `unittest`; suites focadas não devem ser somadas):

| Execução | Métodos | Aprovados | Falhos | Ignorados |
|---|---:|---:|---:|---:|
| Base Hélio, descoberta completa com navegador | 1140 | 1140 | 0 | 0 |
| Integração, descoberta sem navegador | 1574 | 1454 | 1 | 119 |
| Reteste PostgreSQL da asserção de reabertura, quatro fusos | 1 | 1 | 0 | 0 |
| Integração, segurança PostgreSQL | 143 | 143 | 0 | 0 |
| Integração, conta PostgreSQL | 19 | 19 | 0 | 0 |
| Integração, três ensaios PostgreSQL de migrações | 3 | 3 | 0 | 0 |
| Navegador, configurações de conta | 17 | 17 | 0 | 0 |
| Navegador, planos e tema | 31 | 31 | 0 | 0 |
| Navegador, CSP/Socket.IO/horário | 5 | 5 | 0 | 0 |
| Navegador, layout/overflow do portal | 21 | 21 | 0 | 0 |
| Navegador, landing/identidade | 12 | 12 | 0 | 0 |

A descoberta integrada executou 1.455 métodos e ignorou 119 testes de navegador por configuração. Um método falhou em quatro subcasos porque ainda esperava a data de fechamento anterior depois de reabrir o chamado. A correção do produto já limpava essa data; a expectativa legada foi atualizada para NULL e o reteste passou nos quatro fusos. O restante da descoberta passou. Não se declara que a descoberta inteira foi repetida depois desse ajuste de teste. As execuções dedicadas cobrem 86 testes de navegador da versão integrada; os demais permanecem para a execução completa no CI.

Comandos reproduzíveis, em Python 3.12, dependências fixadas de `requirements-dev.txt` e provedores desativados:

```sh
python -I tools/install_dependencies.py --requirements requirements-dev.txt
python -B -m unittest discover -s tests -t . -v
python -B -m unittest tests.postgresql_auth_tokens tests.postgresql_session_revocation tests.postgresql_company_restore_security tests.postgresql_company_restore_migration tests.postgresql_etl_resource_security -v
python -B -m unittest tests.postgresql_configuracoes -v
python -B -m unittest tests.test_planos_postgresql tests.test_leads_postgresql tests.test_contratos_postgresql -v
python -B -m unittest tests.test_bootstrap_guard tests.test_integracao_seletiva -v
python -I tools/varredura_segredos.py
```

Os testes PostgreSQL recebem somente `NEXO_TEST_POSTGRES_BIN`, caminho local de binários, e criam seu próprio cluster privado com ambiente filtrado. Não recebem URLs existentes. O ensaio de backup/restauração verificou 32 tabelas, relacionamentos, sequências, arquivos, isolamento e ETL com dados fictícios.

Para navegador: `NEXO_TEST_BROWSER=1`, `NEXO_TEST_CHROMIUM` apontando para Chromium e `NEXO_TEST_CDN_DIR` para cópias locais com SRI conferido. A execução de descoberta sem navegador registra seus skips; execuções dedicadas verificam as telas modificadas. Não houve mensagem real a clientes.

No CI do commit de implementação, `pip-audit` informou não encontrar vulnerabilidades conhecidas nas dependências consultadas. O Bandit apontou dois B310 em `emails.py` (as chamadas `urlopen` de envio/consulta Brevo). A revisão confirmou validação prévia de esquema HTTPS/hostname e cabeçalho de chave não redirecionável; os testes cobrem URL sem HTTPS e redirecionamento. Os alertas ficam documentados, sem suprimir o scanner nem tratar o job consultivo como comprovação de ausência de falhas.

## Parte E — GitHub

Destino exclusivo: `Helio965/Nexo---Faturamento-Inteligente---Render`. Branch: `feature/nexo-integracao-melhorias-coder`, baseada em `46a342066ef73408a794fd5abb75f177aa380ed2`. Commit de implementação: `773e594b963765b123d624e56dd88d0881b29c54` (114 arquivos). Pull Request: [#45](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/45). A documentação final é um commit separado no histórico da branch. O repositório da NEXO Coder permaneceu somente leitura.

O estado do CI é informado separadamente dos testes locais. Nem PR aberto nem workflow iniciado significam aprovação de testes ou publicação. Não foi feito merge ou habilitado auto-merge.

## Parte F — Produção, pendências e implantação

Consulta somente leitura ao Render confirmou o serviço `srv-dbb21fgn74is73bvnej0` no workspace confirmado pelo proprietário. **Configuração real: Auto-Deploy ativo (`commit`) na branch `main`; prévias de PR desativadas.** Isso diverge de `autoDeployTrigger: off` no YAML. Abrir esta branch/PR não atualiza a branch observada pelo serviço. Um merge pode publicar automaticamente e precisa de preparação prévia pelo proprietário. O build efetivo consultado também era `pip install -r requirements.txt`, e a rota de health check configurada estava vazia; o YAML sozinho não comprova aplicação dessas opções.

O Supabase oficial continua `wuipygscavreoikzrqnv`; o projeto alternativo não foi utilizado. A tentativa de consulta somente leitura a `public.alembic_version` pelo conector foi negada por falta de permissão. Assim, a revisão instalada, o papel SQL efetivo e as permissões/RLS das tabelas históricas permanecem desconhecidos. Compatibilidade em PostgreSQL descartável não substitui esse diagnóstico de produção.

Migrações preparadas:

```text
b6935e8de9d4
  -> c7d41e9a2b60  conta/preferências/documentos
  -> e2f7a94c1d35  tabela PDV reservada, sem funcionalidade ativada
  -> a8d3f6b91c24  IP/rótulos de aceites
  -> b3e9d6c1f7a2  catálogo/Raio-X
  -> f4c2a8e1d9b6  infraestrutura de leads
```

O ancestral PDV é mantido para preservar os IDs e a cadeia Alembic da referência. Não existe bloqueio de publicação PDV nesta integração. Upgrades acrescentam estruturas e catálogo técnico sem alterar preços/contratos/clientes; não são uma autorização para execução no banco original. As tabelas novas habilitam RLS. As de conta/PDV pressupõem conexão de dono ou BYPASSRLS; planos/leads também restringem papéis da Data API. Confirmar o papel real antes da implantação.

Variáveis a verificar pelo proprietário: `BREVO_API_KEY` (API HTTPS), remetente verificado em `MAIL_DEFAULT_SENDER`, origem HTTPS canônica `NEXO_PUBLIC_URL`/`RENDER_EXTERNAL_URL`, `NEXO_EMAIL_TIMEOUT` e `NEXO_EMAIL_ALERTA_ADMIN`. Confirmar autorização dos IPs de saída no Brevo e SPF/DKIM/DMARC do domínio quando aplicável. O estado real dessas credenciais e a entrega em caixa postal não foram comprovados nesta execução. Não é necessário nem adequado tentar SMTP no Render Free. Não alterar automaticamente `DATABASE_URL`, `DIRECT_URL`, `SECRET_KEY`, `FLASK_ENV` ou `PYTHON_VERSION`.

Procedimento de implantação posterior, sob autorização explícita:

1. Confirmar CI, revisão do PR, configuração efetiva de Auto-Deploy e janela de manutenção antes de qualquer merge.
2. Diagnosticar somente leitura a revisão Alembic, papel SQL/RLS e compatibilidade do esquema original. Resolver divergências; não usar `stamp`, `create_all` ou bootstrap para escondê-las.
3. Obter backup verificável e ensaiar restauração/upgrade em cópia descartável. Revisar as cinco migrações e os catálogos.
4. Executar apenas as migrações necessárias na janela autorizada, verificar esquema/contagens e manter novos planos desativados.
5. Publicar somente o commit aprovado, validar `/healthz`, `/healthz/db`, login, permissões, painéis, uploads e Socket.IO. Teste real de e-mail depende de autorização e destinatário controlado.
6. Para rollback, retornar ao commit de aplicação anterior e manter o esquema expandido enquanto compatível. Não executar downgrades destrutivos; restauração de dados exige plano próprio, pois rollback de código não desfaz banco/envios.

Pendências delimitadas: avaliações de clientes completas; revisão de regras financeiras/PDV; decisão comercial antes de ativar planos/Raio-X; retenção de contatos/resumos e eventual agenda de expurgo de leads; diagnóstico do banco original; configuração/entrega Brevo; decisão de merge/deploy. Nada disso foi ativado silenciosamente.
