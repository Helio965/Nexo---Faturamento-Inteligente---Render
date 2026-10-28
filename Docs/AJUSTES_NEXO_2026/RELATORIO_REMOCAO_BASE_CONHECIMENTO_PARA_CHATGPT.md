# NEXO: Faturamento Inteligente — Relatório técnico para auditoria independente

## Remoção da aba "Base de Conhecimento" da navegação administrativa: auditoria de versão, verificação e diagnóstico

Documento preparado para auditoria independente (ChatGPT). Tudo o que está aqui foi lido no repositório oficial ou executado em cópia descartável do código com dados fictícios. Nenhuma ação foi feita contra Render, Supabase ou qualquer ambiente de produção além de requisições GET públicas e anônimas a um hostname padrão do Render (seção C). Fato verificado e hipótese estão sempre separados.

## A. Estado inicial

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| SHA da `main` no início desta tarefa | `101899968c380c7bab9503f50965013e01896d08` — "Merge pull request #33", feito por Hélio (Helio965) em 28/10/2026 08:02 (−03:00) = 11:02 UTC. Confere com o commit de referência informado pelo proprietário. |
| Pais do merge | `264f713` (main anterior, merge do PR #32) e `3a9a65d` (último commit da branch do PR #33). |
| Branch desta tarefa | `claude/awesome-pascal-0ho42m`, recriada sobre a `main` `1018999` (a versão anterior da branch já estava integrada pelo PR #33; nenhum commit antigo foi reaproveitado). |
| Situação da sidebar na imagem do proprietário | Sete itens: Dashboard, Empresas, Contratos, Lixeira, Análises, Suporte e **Base de Conhecimento**. |
| Situação da sidebar no código da `main` | Seis itens: Dashboard, Empresas, Contratos, Lixeira, Análises, Suporte (bloco `{% if current_user.is_admin %}` em `templates/base.html`, linhas 58–81). No lugar do item antigo há apenas um comentário Jinja (`{# A Base de Conhecimento (CMS do Guia) saiu do menu administrativo em 28/10/2026 … #}`), que não produz HTML. "Sair" continua no rodapé da sidebar (`.sidebar-foot`, linha 110). |
| Implementação existente | PR #33 (`feat/fix/refactor` de 28/10/2026), commit `635fb01 refactor(nav): remover Base de Conhecimento do menu administrativo` (01:57 UTC), que apagou de `base.html` as linhas `<a class="nav-item …" href="{{ url_for('admin.guia') }}"><i class="bi bi-journal-text"></i> Base de Conhecimento</a>` (linhas 78–80 da versão `264f713`). A mesma PR acrescentou o teste de navegador `test_menu_administrativo_sem_base_de_conhecimento` (`tests/test_overflow_navegador.py`), que afirma que o menu administrativo é exatamente a lista de seis rótulos. |

## B. Resultado da auditoria

**A aba ainda estava no código?** Não. Em `1018999` não existe nenhum caminho que renderize "Base de Conhecimento" como item de navegação para o administrador. Verificação feita por leitura e por renderização real das páginas (cliente de teste Flask e Chromium, administrador fictício):

- `templates/base.html` — único template que monta a sidebar (desktop e celular usam o mesmo `<aside id="sidebar">`; a gaveta do celular é o mesmo elemento aberto por `#navToggle`). Não há `include`/`extends` alternativo de sidebar; nenhum template filho sobrescreve o bloco de navegação (`templates/admin/guia.html` e `guia_form.html` só definem `title`, `page_title` e `content`).
- Navegação por JavaScript: `static/js/` não monta itens de menu; o script da sidebar em `base.html` (linhas 222–272) só abre/fecha a gaveta e marca `aria-current` no item ativo.
- CSS: `static/css/nexo.css` não injeta texto em `.sidebar-nav` (nenhum `content:` com esse texto).
- Histórico de `templates/base.html` na `main`: o item existe em todos os commits até `48c54f3` (28/10 00:28 UTC) e deixa de existir a partir de `635fb01` (28/10 01:57 UTC). Logo, **qualquer build feita a partir de um commit anterior a `635fb01` — por exemplo a `main` `264f713` (merge do PR #32, 00:47 UTC) ou qualquer versão de 27/10 — exibe a aba.**

**O PR #33 já havia removido a opção?** Sim, por completo: link, ícone (`bi-journal-text`) e participação no indicador de item ativo (`request.endpoint in ['admin.guia', …]`).

**Existiam outras referências visíveis?** As referências restantes ao texto "Base de Conhecimento" não são navegação e foram mantidas de propósito (o proprietário pediu para preservar o Guia do cliente e o NexoBot):

| Onde | O que é | Visível no menu? |
|---|---|---|
| `templates/admin/guia.html`, `guia_form.html` | Título e cabeçalho das páginas do CMS do Guia (`/admin/guia`, `/admin/guia/novo`, `/admin/guia/editar/<id>`), alcançáveis só por endereço digitado ou favorito antigo | Não — nessas páginas a sidebar também tem seis itens e nenhum ativo (coberto por teste). |
| `blueprints/admin.py` (1292–1439), `models.py` (533–537), `seed_guia.py`, `tools/auditar_guia.py`, `nexobot/higiene.py` | Rotas, modelo e ferramentas do CMS; mensagens flash do CMS | Não. |
| `nexobot/saber/administracao.py`, `nexobot/saber/suporte_guia.py` | Respostas do NexoBot (já reescritas no PR #33 para não citar o item de menu; a expressão permanece como nome do conceito) | Não. |
| `tests/` (identidade visual, NexoBot, overflow) | Testes que abrem `/admin/guia` por URL ou afirmam que o rótulo não está no menu | Não. |
| `Docs/` | Documentação histórica | Não. |

Conclusão da auditoria: **a remoção está correta e completa no GitHub desde `635fb01`, integrada à `main` em `1018999`.** Não há nada a reimplementar; nenhum commit de "correção da remoção" foi criado.

## C. Render (versão publicada)

**Acesso ao Render.** Esta sessão não tem chave de API nem ferramenta autorizada do Render (nenhuma variável de ambiente ou conector), e o repositório não contém o hostname real do serviço — os documentos usam `<serviço>.onrender.com` como marcador. **Não foi possível ler o painel: commit Live, data do último deploy, branch vinculada e estado efetivo do Auto-Deploy não foram confirmados** (cenário C para a confirmação direta).

**O que o repositório declara.** `render.yaml`: serviço web `nexo-faturamento-inteligente`, plano `free`, região `oregon`, `branch: main`, `autoDeployTrigger: 'off'` (publicação só por *Manual Deploy*), `healthCheckPath: /healthz`, build `python -I tools/install_dependencies.py …` sem migrações. `Docs/PREPARACAO_RENDER.md` (seção 5) registra que o YAML não prova a configuração efetiva do painel e que, em outra ocasião (SEC-006), o proprietário informou Auto-Deploy **ativado** — portanto as duas possibilidades (deploy manual pendente ou deploy automático já disparado) precisam ser conferidas no painel.

**Sonda pública, somente leitura (28/10/2026 11:30 UTC).** `GET https://nexo-faturamento-inteligente.onrender.com/healthz` e `/static/css/nexo.css` responderam **404** com o cabeçalho `x-render-routing: no-server` (Cloudflare/Render): **nenhum serviço está ligado a esse hostname padrão** — o serviço real usa outro hostname (sufixo aleatório ou domínio próprio), como `Docs/VALIDACAO_VIDEO_RENDER.md` já havia observado. Por isso não foi possível identificar o commit publicado por meios públicos. O repositório não expõe a versão/commit em `/healthz` (devolve só `{"status": "ok"}`) nem no HTML.

**Cache como causa (cenário B)?** Pouco provável pelo código, mas não excluído por cabeçalho: as páginas autenticadas não enviam `Cache-Control` (o `no-store` de `app.py`, linhas 133–138, vale só para os links com token de senha/primeiro acesso) e também não enviam `ETag`/`Last-Modified`, de modo que o navegador não reutiliza a página de forma heurística; o HTML passa pelo Cloudflare do Render como `DYNAMIC` (não armazenado); não há *service worker*; a sidebar é um único elemento servido pelo servidor. Um recarregamento forçado (Ctrl+F5) ou uma janela anônima elimina a dúvida. Permanecem possíveis apenas um proxy intermediário fora do controle da aplicação ou uma outra instância/ambiente (por exemplo um serviço antigo ainda no ar com outro hostname) — ambos só confirmáveis no painel.

**Classificação.**

- **Cenário A (código antigo em produção) — hipótese mais provável, não confirmada.** Sustentação: o YAML versionado desliga o deploy automático; o PR #33 entrou na `main` às 11:02 UTC de 28/10 e o proprietário relatou ver a aba depois disso; a aba existe em todo commit anterior a `635fb01`. Para o menu ficar correto é preciso que o commit publicado seja `101899968c380c7bab9503f50965013e01896d08` (ou qualquer commit da `main` que contenha `635fb01`).
- **Cenário B (código atualizado, aba visível mesmo assim) — improvável pelo código** (`no-store`, sem service worker, sidebar única). Só se sustentaria se o painel mostrar o commit `1018999` como Live e, ainda assim, a aba aparecer em uma janela anônima.
- **Cenário C (sem acesso ao Render) — é a situação desta sessão** para a confirmação do commit Live.

**Como o proprietário confirma em 2 minutos (somente leitura).**
1. Painel do Render → serviço `nexo-faturamento-inteligente` → aba *Events*/*Deploys*: anotar o commit "Live" (7 caracteres), a data/hora do último deploy e a branch; aba *Settings* → *Build & Deploy*: estado do *Auto-Deploy*.
2. Comparar com o GitHub: `main` = `1018999`. Se o Live for `264f713` ou anterior (qualquer data antes de 28/10 11:02 UTC), é o cenário A.
3. Prova independente sem login: no hostname real do serviço, `curl -s https://<host>/static/css/nexo.css | grep -c -- '--topbar-blur-forte'` → `0` indica CSS anterior ao PR #33 (versão antiga publicada); `1` indica a versão nova. (A folha de estilo é pública e mudou no PR #33.)
4. Conferir o menu em janela anônima depois do deploy (exclui cache local).
5. A partir da publicação deste PR (#34), `GET https://<host>/healthz` passa a devolver `{"status": "ok", "versao": "<7 caracteres do commit>"}` (lido de `RENDER_GIT_COMMIT`, que o Render injeta em cada deploy): a conferência da versão publicada deixa de depender do painel.

**Como alinhar a produção (requer autorização expressa do proprietário; nada foi executado).** Conforme `Docs/PREPARACAO_RENDER.md` §5: (1) confirmar que o banco de produção já está na revisão exigida pelo código — a head da `main` `1018999` é `81287c74387a` (migração da gestão contratual, PR #27 de 26/10; conferida nesta tarefa pelo encadeamento de `migrations/versions`, e o §5 do documento citava um valor desatualizado, corrigido neste PR); o PR #33 não criou migrações, mas se a versão publicada for anterior a 26/10 o banco pode estar atrás da head e a publicação exige antes o procedimento de migração com backup (`Docs/PREPARACAO_RENDER.md` §5.3 e `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`); (2) *Manual Deploy* → "Deploy a specific commit" → `101899968c380c7bab9503f50965013e01896d08` (não usar "latest commit" sem conferir o SHA); (3) validar `/healthz`, `/healthz/db`, login administrativo e o menu; (4) decidir sobre o Auto-Deploy no painel de acordo com a política do documento.

## D. Alterações

Nenhuma alteração de interface foi necessária (Situação 1 da tarefa). Alterações desta tarefa, todas fora da interface:

| Arquivo | Situação | Justificativa |
|---|---|---|
| `tests/test_navegacao_admin.py` | novo | Teste de regressão **HTTP** (sem navegador; roda no `unittest discover` do job `security-sqlite-browser` em todo PR e push): em 17 páginas administrativas (dashboard, empresas e seus formulários/detalhes, contratos, lixeira, análises e seus formulários, gerenciar análises, upload/relatório de análise, tickets e as três páginas do CMS `/admin/guia*`) a sidebar inteira (menu e rodapé, com regex tolerante à ordem dos atributos) tem exatamente os seis rótulos, nenhum link para `/admin/guia`, "Sair" único; o item ativo corresponde à página e nenhum fica ativo no CMS; fora do CMS a string `/admin/guia` não aparece na página; a sidebar do cliente (6 páginas) não ganha o item nem aponta para `/admin`. Versão reforçada após a revisão independente (a primeira só olhava o `<nav>` e 8 páginas). |
| `tests/test_overflow_navegador.py` | modificado | Pré-condição no teste do indicador da sidebar: a lista de itens do menu administrativo é exatamente a esperada antes de medir "Dashboard" (achado da revisão). |
| `app.py`, `tests/test_deploy.py` | modificados | `/healthz` passa a devolver também `versao` (7 caracteres de `RENDER_GIT_COMMIT`, ou "desconhecida" fora do Render): única alteração de código, pedida pelo critério "a versão do código tiver sido identificada" — sem isso nenhuma rota pública identifica o commit publicado. Não altera interface, regras de negócio nem banco; `/healthz/db` continua igual. |
| `Docs/PREPARACAO_RENDER.md` | modificado | §5: a head de migração citada (`e4c004a26b01`) estava desatualizada; passa a remeter a `flask db heads` (em `1018999`: `81287c74387a`). |
| `Docs/AJUSTES_NEXO_2026/RELATORIO_GERENCIAMENTO_ANALISES_TOPBAR_REFINAMENTO_PARA_CHATGPT.md` | modificado | Seção H: a frase "Render implanta a `main` automaticamente" (sem base; o YAML diz o contrário) foi corrigida — ela está na cadeia causal do sintoma relatado. |
| `Docs/AJUSTES_NEXO_2026/RELATORIO_REMOCAO_BASE_CONHECIMENTO_PARA_CHATGPT.md` | novo | Este relatório. |

Commits (branch `claude/awesome-pascal-0ho42m` recriada sobre a `main`; PR #34 em rascunho): `21e1101 test(nav): regressao HTTP da sidebar administrativa sem Base de Conhecimento`, `80bb032` e `5093970` (docs, rascunhos deste relatório), e, após a revisão independente: `feat(ops): expor o commit publicado em /healthz`, `test(nav): regressao HTTP da sidebar cobre 17 paginas, rodape e links`, `docs(ops): corrigir deploy automatico e head de migracao na documentacao` e o commit de fechamento deste relatório (SHAs na seção E e no PR). Nenhum commit repete a remoção (`templates/base.html` não foi tocado).

## E. Testes

Ambiente: cópia descartável do código da `main` (`1018999` + os commits desta branch, que não tocam templates), SQLite temporário com as migrações reais, Chromium 1243 (Chrome for Testing 153) via Playwright com CDN servida de cópias locais íntegras, PostgreSQL 16 descartável quando a suíte o exige, administrador e cliente fictícios (`example.invalid`). Nenhum banco real foi tocado.

| Execução | Resultado |
|---|---|
| `tests.test_navegacao_admin` (novo, HTTP, sem navegador) | 1ª versão: 3 testes, 3 OK em 4 s (8 páginas, só o `<nav>`). Versão final (após a revisão): 2 testes com 23 subtestes (17 páginas administrativas + 6 do cliente), OK — executada junto com `test_deploy`, `test_dotenv_security_compat`, `test_configuration_deploy`, `test_backup_restore` e os dois testes de navegador da sidebar: **47 testes, 47 OK** em 57 s. |
| `tests.test_overflow_navegador` + `tests.test_identidade_visual` + `tests.test_gerenciamento_navegador` (oficiais, Chromium) | **37 testes, 37 OK** em 525 s, incluindo `test_menu_administrativo_sem_base_de_conhecimento` (rótulos exatos do menu administrativo), `test_sidebar_item_longo_nao_encosta_no_indicador` (indicador do item ativo, admin e cliente), a varredura de páginas administrativas em todas as larguras, a topbar em 12 páginas × 5 larguras e os testes de identidade visual (marca, cubo, landing, login). |
| Sonda de homologação (Chromium, `scratchpad/bc/probe_bc.py`, registro em `bc_capturas/registro.json`) | Login administrativo; Dashboard, Empresas, Contratos, Lixeira, Análises, Suporte e Gerenciar análises em 1366×768 (sidebar visível, seis itens, item ativo = página, "Sair" presente, sidebar permanece ao rolar até o fim do dashboard), 1024×768 (tablet) e 390×844 (gaveta começa recolhida; abre pelo botão do menu; seis itens; fecha pelo X e pelo Esc, em todas as sete páginas). Teclado: a partir do topo, Tab percorre Dashboard → Empresas → Contratos → Lixeira → Análises → Suporte → Sair, nessa ordem. Em nenhum ponto o texto "Base de Conhecimento" aparece na sidebar. |
| Suíte oficial completa na `main` (`1018999` = código de `deb7b59`) | 837 testes, 0 falhas, 0 pulados — local (823 s) e na CI do PR #33 (run 40624619001) e da cabeça `3a9a65d` (run 40627238726), registradas no relatório anterior. CI do PR #34 na cabeça `5093970` (antes das alterações pós-revisão): run 40681927043, jobs `security-postgresql` e `security-sqlite-browser` verdes (11:42–11:59 UTC), incluindo o teste HTTP novo. Cabeça `43c515b` (com `/healthz` versionado, teste reforçado e correções de documentação): run 40684847351, jobs `security-postgresql` (12:04–12:06 UTC) e `security-sqlite-browser` (12:04–12:19 UTC) verdes. O commit de fechamento deste relatório é só documentação. | |

Problemas encontrados nos testes: nenhum. Nenhum teste existente foi alterado ou removido.

### Capturas (código `1018999` executado em cópia descartável, Chromium headless, administrador fictício)

Capturas reais feitas pelo roteiro de homologação (Chromium headless, Playwright, seed de homologação com empresas "Demo" e administrador "Admin Demonstração", fontes e ícones servidos localmente), entregues ao proprietário no chat e no pacote `NEXO_AUDITORIA_BASE_CONHECIMENTO.zip` (pasta `capturas/`, com `manifest.json` contendo SHA-256 e dimensões):

| Captura | Arquivo | O que mostra |
|---|---|---|
| 1 — Sidebar desktop | `C1_sidebar_desktop_1366.png` | Dashboard administrativo a 1366×768: sidebar com Dashboard (ativo), Empresas, Contratos, Lixeira, Análises e Suporte; "Sair" no rodapé; sem Base de Conhecimento; logomarca, cubo, vidro, ícones, bordas arredondadas e estado ativo preservados. |
| 2 — Sidebar mobile | `C2_sidebar_mobile_390_gaveta_aberta.png` | Gaveta aberta a 390×844 (@2x): os mesmos seis itens e o "Sair"; sem Base de Conhecimento. A sonda confirma que a gaveta fecha pelo botão X, pelo Esc e tocando fora, e que o conteúdo atrás fica inerte. |
| 3 — Dashboard administrativo | `C3_dashboard_admin_rolado_1366.png` | Sistema em funcionamento após a verificação (dashboard rolado, KPIs e gráficos, topbar), com a sidebar inalterada. |
| Complementos | `C4_dashboard_mobile_390_gaveta_recolhida.png`, `C5_analises_desktop_1366.png` | Dashboard no celular com a gaveta recolhida (botão do menu no topo); página Análises com a mesma sidebar. |

Nenhuma captura antiga foi reaproveitada: todas foram geradas nesta tarefa a partir do código `1018999` (os commits desta branch não alteram templates nem CSS).

### Revisão independente

Fluxo de trabalho com três lentes independentes (renderização, implantação/versão, testes de regressão) sobre uma cópia descartável da `main` `1018999`, cada achado submetido a um verificador cético com reprodução própria (identificador `wf_080d954c-1ac`; 12 agentes, 76 min; resultado final: renderização 0 achados; implantação 4 achados, 4 confirmados; testes 5 achados, 2 confirmados e 3 refutados).

| Lente | Resultado |
|---|---|
| Renderização | **0 achados.** Mediu 20 rotas administrativas pelo cliente de teste e 16 páginas/gavetas em Chromium real (árvore de acessibilidade e capturas): nenhum caminho entrega "Base de Conhecimento" como item de navegação; a sidebar está fora de qualquer `{% block %}`, nenhum template filho, JavaScript, CSS, página de erro ou NexoBot a recompõe; o comentário Jinja do PR #33 não vaza para o HTML. Hipóteses coerentes com o sintoma: serviço do Render em commit anterior ao PR #33 (ou outro serviço/branch), página antiga retida pelo navegador (bfcache/aba aberta antes do deploy) ou acesso direto a `/admin/guia` por favorito (que exibe "Base de Conhecimento" como título, não como item). |
| Implantação e versão | **4 achados, 4 confirmados pelos verificadores** (1 MÉDIA, 2 MÉDIA, 1 BAIXA): (a) nenhum marcador de versão/commit exposto pela aplicação → corrigido neste PR (`/healthz` com `versao`, commit `be0c711`); (b) o relatório do PR #33 afirmava sem base que o Render implanta a `main` automaticamente, contradizendo o YAML → corrigido (`43c515b`); (c) `Docs/PREPARACAO_RENDER.md` §5 citava a head de migração `e4c004a26b01`, desatualizada desde 26/10 (`flask db heads` = `81287c74387a`) → corrigido (`43c515b`); (d) `/healthz/db` não confere a revisão do schema, embora o roteiro o use como validação pós-deploy → registrado como pendência (seção G), sem alteração nesta tarefa. Confirmou ainda: PR #33 não altera migrações nem dependências; HTML sem `Cache-Control`/validadores (navegador e CDN não servem página antiga numa navegação nova); estáticos com `no-cache` + `ETag`; hostname padrão do Render sem serviço; CI da `main` verde. |
| Testes de regressão | **5 achados** (2 ALTA, 2 MÉDIA, 1 BAIXA) sobre a cobertura: o único teste da `main` é de navegador, pulado em silêncio sem as cópias íntegras da CDN e restrito a uma página e aos rótulos; a 1ª versão do teste HTTP desta branch só olhava o `<nav>` (um link no rodapé passaria), exigia `class` como primeiro atributo e dizia rodar "nos dois jobs" (o job `security-postgresql` executa só os módulos `tests.postgresql_*`); o teste do indicador assume "Dashboard" como rótulo mais largo sem conferir a lista. Ensaio de mutação em cópia privada (4 formas de reintroduzir o link): o teste de navegador deixou passar 2, a 1ª versão do teste HTTP deixou passar 1, a versão reforçada pega as 4. **Tudo adotado** (`7374d0c`): teste HTTP sobre a sidebar inteira em 17 páginas com regex tolerante, pré-condição no teste do indicador, docstring corrigida. Vereditos dos verificadores (todos com confiança alta): 2 confirmados — a barreira única pulável em silêncio e o teste de navegador restrito a uma página sem conferir links, ambos cobertos pelo teste HTTP reforçado — e 3 refutados por já estarem resolvidos na ponta da branch ou por não caberem (docstring corrigida em `7374d0c`; pré-condição dos rótulos já garantida; não acrescentar passo ao job `security-postgresql`). |

Nenhum achado em nenhuma lente aponta defeito na remoção em si: a conclusão da seção B (remoção completa na `main`) foi confirmada de forma independente.

## F. Resultado final

**A remoção já estava corretamente implementada no GitHub** (PR #33, commit `635fb01`, integrado à `main` em `1018999`): nenhuma correção de interface foi necessária e nenhuma foi feita. Em cópia descartável desse código, a sidebar administrativa apresenta exatamente Dashboard, Empresas, Contratos, Lixeira, Análises e Suporte, com "Sair" no rodapé, em desktop, tablet e celular, com teclado e com rolagem; os testes oficiais de navegação e identidade visual passam (37/37) e o novo teste HTTP (3/3) fixa esse estado nos dois jobs da CI.

**A remoção está no GitHub, mas não foi possível confirmar que está implantada em produção.** O que o proprietário vê é compatível com uma versão publicada anterior a `635fb01` (cenário A), que é o mais provável dado `autoDeployTrigger: 'off'` e o merge das 11:02 UTC; a confirmação exige olhar o commit Live no painel do Render (ou o `curl` da folha de estilo no hostname real), conforme a seção C. **A produção não foi declarada corrigida**, porque o código efetivamente publicado não pôde ser verificado nesta sessão.

## G. Pendências

1. **Proprietário — confirmar a versão publicada** (2 min, somente leitura): no painel do Render, serviço `nexo-faturamento-inteligente` → commit Live, data do último deploy, branch e estado do Auto-Deploy; ou `curl -s https://<host>/static/css/nexo.css | grep -c -- '--topbar-blur-forte'` (`0` = versão anterior ao PR #33).
2. **Proprietário — publicar a `main`** se o Live for anterior a `635fb01`: *Manual Deploy* do commit `101899968c380c7bab9503f50965013e01896d08`, seguindo `Docs/PREPARACAO_RENDER.md` §5 (revisão do banco conferida antes; validar `/healthz`, `/healthz/db`, login e menu; conferir em janela anônima). Nenhum deploy foi feito nesta sessão.
3. **Se, após o deploy, a aba continuar aparecendo** (cenário B): informar o hostname real e o commit Live para nova investigação (proxy intermediário ou segunda instância são as únicas causas que o código não exclui).
4. **Opcional, fora deste escopo:** fazer `/healthz/db` conferir a revisão do schema (`alembic_version` × head do código), já que o roteiro de publicação o usa como validação pós-deploy e hoje ele devolve 200 mesmo com schema defasado (achado da revisão, não implementado); decidir se as rotas do CMS (`/admin/guia*`) continuam acessíveis por endereço; alinhar `README.md` (§Render) à regra "o estado do Auto-Deploy só é conhecido no painel".
5. **PR #34** (rascunho): aguarda CI e a decisão de merge do proprietário; contém apenas o teste de regressão HTTP e este relatório.
