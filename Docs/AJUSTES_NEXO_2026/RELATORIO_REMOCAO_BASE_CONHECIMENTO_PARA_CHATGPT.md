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

**Como alinhar a produção (requer autorização expressa do proprietário; nada foi executado).** Conforme `Docs/PREPARACAO_RENDER.md` §5: (1) confirmar que o banco de produção já está na revisão exigida pelo código (`flask db current` × `flask db heads`; o PR #33 não criou migrações, então a exigência é a mesma da versão atualmente publicada se esta já for de 26/10 ou posterior); (2) *Manual Deploy* → "Deploy a specific commit" → `101899968c380c7bab9503f50965013e01896d08` (não usar "latest commit" sem conferir o SHA); (3) validar `/healthz`, `/healthz/db`, login administrativo e o menu; (4) decidir sobre o Auto-Deploy no painel de acordo com a política do documento.

## D. Alterações

Nenhuma alteração de interface foi necessária (Situação 1 da tarefa). Alterações desta tarefa, todas fora da interface:

| Arquivo | Situação | Justificativa |
|---|---|---|
| `tests/test_navegacao_admin.py` | novo | Teste de regressão **HTTP** (sem navegador, roda nos dois jobs da CI): em `/admin/dashboard`, `/admin/empresas`, `/admin/contratos`, `/admin/lixeira`, `/admin/analises`, `/admin/analises/gerenciar`, `/admin/tickets` e `/admin/guia` a sidebar tem exatamente os seis rótulos, sem "Base de Conhecimento" e sem link para `/admin/guia`, com "Sair" uma única vez no rodapé; o item ativo corresponde à página (e nenhum fica ativo no CMS); a sidebar do cliente não ganha o item. Complementa o teste de navegador já existente (gaveta do celular, teclado, indicador). |
| `Docs/AJUSTES_NEXO_2026/RELATORIO_REMOCAO_BASE_CONHECIMENTO_PARA_CHATGPT.md` | novo | Este relatório. |

Commits: «COMMITS». Nenhum commit repete a remoção (`templates/base.html` não foi tocado).

## E. Testes

«E_TESTES»

### Capturas (código `1018999` executado em cópia descartável, Chromium headless, administrador fictício)

«E_CAPTURAS»

### Revisão independente

«REVISAO»

## F. Resultado final

«F»

## G. Pendências

«G»
