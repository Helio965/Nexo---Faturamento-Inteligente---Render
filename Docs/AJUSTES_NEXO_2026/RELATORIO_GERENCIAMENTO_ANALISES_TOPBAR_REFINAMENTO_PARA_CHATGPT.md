# NEXO: Faturamento Inteligente — Relatório técnico para auditoria independente

## Gerenciamento de análises por empresa, topbar com desfoque gradual, refinamento de bordas e remoção da aba Base de Conhecimento

Documento preparado para ser auditado de forma independente (ChatGPT). Tudo o que está aqui foi executado em cópia descartável do código, com dados fictícios, sem acesso a produção. Nada foi inventado: cada número vem de um log ou de uma captura real citados no pacote de evidências.

## A. Identificação

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| Branch de trabalho | `claude/awesome-pascal-0ho42m` (branch designada desta sessão, recriada sobre a `main`; o nome sugerido `feature/nexo-gerenciamento-analises-topbar-refinamento` fica registrado, mas a sessão só publica na branch designada) |
| SHA inicial (`main`) | `264f713b387f25e88e6e645c53788e0f9e0b9a8a` (merge do PR #32), confirmado antes de iniciar |
| SHA final | `deb7b59148eb0a971551cec2f97eb28c756353dc` (último commit de código/teste: `test(ui): visibilidade por estilo computado…`; os commits de código da rodada de revisão são `25fc333`, `7e29355`, `467047a` e `deb7b59`); os commits posteriores da branch são apenas de documentação (`docs(ui)`, ver seção H) e não alteram código, CSS, templates ou testes |
| Data | 28/10/2026 |
| Ambiente | Ubuntu 24.04, Python 3.12, Flask 3.1, Chromium 1243 (Chrome for Testing 153) via Playwright; SQLite temporário com as migrações reais; PostgreSQL 16 descartável nos ensaios da suíte; CDN servida de cópias locais íntegras (hash SRI); fontes Inter/JetBrains Mono. Firefox e WebKit não existem no ambiente (limitação registrada). |

## B. Auditoria inicial (como funcionava)

Fontes: leitura de `templates/base.html`, `templates/admin/analises.html`, `blueprints/admin.py`, `models.py`, `static/css/nexo.css`, `tests/` e das alterações do PR #32 (merge `264f713`), mais capturas reais do estado inicial (pasta `antes/` do pacote).

**Exclusão de análises.** A listagem geral `/admin/analises` tinha, em cada linha, o botão "Abrir" e um botão de lixeira (`btn-ghost is-danger`) que abria um modal único (`#confirmDeleteModal`) cujo formulário era preenchido em JavaScript com a URL `POST /admin/analise/deletar/<id_analise>` (`admin.analise_deletar`). A rota exigia administrador (`admin_required`), aceitava só POST (CSRF global do Flask-WTF), removia os arquivos físicos dos uploads **antes** do commit e apagava a análise com cascata ORM (`cascade="all, delete-orphan"` em uploads, indicador, relatório e Curva ABC). Não havia verificação de empresa (o id da análise bastava), e uma falha no commit deixaria registros sem arquivo (os arquivos já tinham sido removidos). A exclusão era e continua sendo definitiva (não existe lixeira de análises; a lixeira do sistema é de empresas).

**Topbar.** `header.topbar` em `base.html`, `position: sticky` (14 px do topo), `max-width: 1440px`, fundo `--glass-chrome` (rgba 16,12,30 a 62 %) com `backdrop-filter: blur(18px) saturate(150%)` aplicado ao próprio elemento, uniforme em toda a altura; borda de vidro, raio de 22 px. No celular (≤ 991 px) margem de 10 px e 60 px de altura. O conteúdo rolado passava atrás com um desfoque único, sem profundidade; em telas largas a faixa parava em 1440 px.

**Bordas.** `.nexo-table` com `border-collapse: collapse`: divisórias de células e do cabeçalho retas de ponta a ponta, encostando nas bordas arredondadas do `.table-wrap` (raio 22 px, `overflow: hidden`); realce de linha ao passar o mouse com uma barra reta `box-shadow: inset 3px 0 0` na linha inteira; divisórias dos cabeçalhos de cartões (`.nexo-card-head`), da dica de rolagem, da marca e do rodapé da sidebar e dos modais também retas até as extremidades.

**Navegação.** Sidebar administrativa com sete itens: Dashboard, Empresas, Contratos, Lixeira, Análises, Suporte e **Base de Conhecimento** (`admin.guia`, CMS dos tópicos do Guia que alimentam o Guia do cliente e o NexoBot). O item ativo recebe um ponto à direita. Testes existentes referenciam a página `/admin/guia` (NexoBot, identidade visual, overflow) e o rótulo "Base de Conhecimento" (teste do indicador da sidebar).


## C. Alterações implementadas

### 1. Nova experiência de edição (botão Editar)
A listagem geral ganhou o botão **Editar** (`#btnGerenciar`, `btn-nexo`, ícone de lápis, ao lado de "Nova análise") que leva a `/admin/analises/gerenciar`. A coluna "Ações" da listagem ficou só com "Abrir"; a lixeira, o modal e o script do modal foram **removidos da renderização** (não escondidos por CSS), e a rota antiga `POST /admin/analise/deletar/<id>` deixou de existir (um POST nela devolve 404). A macro `uppill` (selos V/C dos uploads) foi movida para `templates/_macros.html` para ser usada pelas duas telas.

### 2. Seleção de empresas (`/admin/analises/gerenciar`)
Título "Gerenciar análises", subtítulo "Selecione uma empresa para consultar e gerenciar suas análises.", trilha "Análises › Gerenciar análises", campo de busca (`#buscaGerenciar`, filtra por nome fantasia, razão social e CNPJ — digitado com ou sem máscara, mesmo quando o cadastro guardou o CNPJ pontuado —, ignorando acentos, com região `aria-live` e "Limpar busca") e uma grade responsiva (`.empresa-grid`, lista real `<ul>/<li>`, colunas de ≥ 320 px) de cartões-link (`.empresa-card`, um `<a>` sem `role` nem `aria-label`, para o leitor de tela anunciá-lo como link e ler o conteúdo visível): cubo da marca, nome fantasia, razão social, CNPJ formatado, ID, contagem de análises, plano e, quando houver, status Suspensa/Cancelada. Hover e foco elevam o cartão e acendem a borda (`:focus-visible` com anel), Enter abre. Só empresas ativas (fora da lixeira) aparecem; a lixeira tem o próprio fluxo. Nenhuma lixeira de análise nesta tela.

### 3. Exclusão de análises (`/admin/analises/gerenciar/<id_empresa>`)
Cartão da empresa selecionada (mesmo desenho, com marca de seleção, `role="group"` nomeado "Empresa selecionada") e tabela só com as análises dela (período, tipo, quinzena, status, uploads, criação, publicado, ações "Abrir" e "Excluir"). "Excluir" abre o modal `#confirmExcluirAnalise` ("Excluir análise?") com empresa, período, tipo e identificador da análise, o aviso de que a exclusão é definitiva e os botões **Cancelar** / **Confirmar exclusão** (vermelho na identidade). O formulário envia `POST /admin/analises/gerenciar/<id_empresa>/excluir/<id_analise>` com CSRF e `confirmar=sim`. No backend (`admin.analise_excluir`): administrador obrigatório, empresa ativa obrigatória, a análise precisa pertencer à empresa da URL (senão 404, com aviso no log), confirmação obrigatória (senão 400), uma análise por requisição (não existe rota sem id nem exclusão em massa). `_excluir_analise()` passou a apagar primeiro no banco (mídias `db:` na mesma transação) e só depois do commit remover arquivos legados do disco; falha no banco faz rollback e devolve a mensagem "Nada foi alterado"; a exclusão bem-sucedida fica no log da aplicação (análise, empresa e administrador). Depois da exclusão o administrador volta à mesma empresa, com mensagem de sucesso, as demais análises intactas e o link "Voltar à seleção de empresas".

### 4. Reorganização do botão Abrir
Coluna "Ações" com `width: 1%` e `white-space: nowrap` (ocupa só o necessário) e botão `btn-abrir` compacto (5 × 11 px, 0,82 rem, ícone + texto, foco visível). Nas telas ≤ 1440 px as células respiram 10 px nas laterais (16 px nas pontas) e o nome da empresa tem mínimo de 170 px: a listagem de 9 colunas passou a caber inteira a 1366 px, sem rolagem horizontal e sem esconder coluna. No celular continua o modo cartões; a célula de ações volta a ser um bloco normal (um primeiro ensaio mostrou o rótulo "Ações" e os botões quebrando letra por letra nos cartões, corrigido antes da publicação).

### 5. Blur gradual da topbar
O desfoque saiu do próprio `.topbar` e passou para duas camadas decorativas (`::before` e `::after`, `pointer-events: none`, `z-index: -1`): a forte (`blur(26px) saturate(160%)` + véu escuro) é mascarada por um degradê vertical (100 % no topo → 6 % na base) e a suave (`blur(8px) saturate(130%)` + tinta leve) cobre toda a altura. Resultado: topo mais desfocado e mais escuro (protege título, sino e usuário), base mais translúcida, transição contínua sem degraus. Um `backdrop-filter` no pai limitaria o que as camadas "enxergam" e cortaria o menu do sino, por isso foi retirado. Fallbacks: `@supports not (backdrop-filter)` e `prefers-reduced-transparency: reduce` usam um único degradê quase opaco sem camadas (com a borda e o brilho de volta no próprio elemento); nada depende de animação. Por achado da revisão, as duas camadas passaram a cobrir também a caixa da borda (`inset: -1px`) e o anel de 1 px e o brilho interno (`--glass-shine`) são pintados pela camada de cima (`::after`): no desenho inicial ficavam no próprio `.topbar`, por baixo do desfoque — o brilho não aparecia e a borda ficava sobre conteúdo nítido. A revisão também mediu, em rasterização por software, que duas superfícies de `backdrop-filter` custam o dobro de uma por quadro de rolagem; uma variante de camada única foi ensaiada (sonda com capturas), mas deixava o conteúdo da página legível pela metade inferior do cabeçalho, inclusive texto encostado no título, por isso as duas camadas foram mantidas e o custo fica registrado como decisão consciente (quem precisa de menos efeitos tem o fallback de transparência reduzida).

### 6. Aplicação global do cabeçalho
A topbar é o mesmo componente de `base.html` em todas as páginas autenticadas; o `max-width: 1440px` foi removido para a faixa ir do limite da sidebar até a borda direita da área principal em qualquer largura (no celular, de margem a margem, com o botão do menu, o sino e o avatar). O menu do sino continua acima do cabeçalho e dentro da tela.

### 7. Refinamento das bordas
`.nexo-table` em `border-collapse: separate` (spacing 0): as divisórias da primeira e da última célula (e do cabeçalho) terminam num degradê com recuo de 18 px antes das bordas arredondadas; o realce ao passar o mouse e a linha em foco passam a pintar as células com pontas arredondadas (12 px) e o traço roxo acompanha o canto, no lugar da barra reta; cabeçalhos/rodapés de cartões, dica de rolagem, marca e rodapé da sidebar e modais usam divisórias com recuo de 24 px. O modo cartões não é afetado. Nenhum `overflow: hidden` novo. Por achado da revisão: nas tabelas cuja última linha do `tbody` é uma linha-placeholder oculta (Análises, Empresas e Curva ABC do cliente), a última linha visível mantinha a divisória colada à borda arredondada; as linhas-placeholder passaram a usar o atributo `hidden` (os filtros alternam `hidden`, não `style.display`) e a regra `tr:nth-last-child(1 of :not([hidden])) td` tira a divisória da última linha realmente visível.

### 8. Remoção da aba Base de Conhecimento
O item saiu da sidebar administrativa (link, ícone e indicador). As rotas `/admin/guia*` (CMS) continuam existindo, sem link no menu, porque o Guia do cliente e o NexoBot leem os mesmos tópicos (fonte única) e os testes do NexoBot/identidade usam essas páginas; nenhum registro foi apagado e nenhuma migração foi criada. Referências atualizadas: `base.html`, `Docs/RELATORIO_TECNICO.md`, teste do indicador da sidebar (passou a usar "Análises" e "Enviar relatórios") e lista de páginas do teste de overflow; novo teste garante que o menu administrativo é exatamente Dashboard, Empresas, Contratos, Lixeira, Análises e Suporte. Por achados da revisão: duas respostas do NexoBot que mandavam o administrador abrir "Base de Conhecimento" no menu passaram a descrever o CMS do Guia pelo endereço (`/admin/guia`, sem item no menu), mantendo o conteúdo e a palavra "tópicos" que os testes do bot exigem; o teste do indicador da sidebar passou a medir "Dashboard" (o rótulo mais largo do menu administrativo, 75,9 px na Inter) em vez de "Análises"; e `Docs/RELATORIO_TECNICO.md` voltou aos terminadores CRLF originais (a primeira versão convertera o arquivo inteiro para LF, inflando o diff para ~800 linhas; agora o diff tem só as duas linhas realmente alteradas).


## D. Arquivos modificados

| Arquivo | Situação | Motivo |
|---|---|---|
| `Docs/AJUSTES_NEXO_2026/RELATORIO_GERENCIAMENTO_ANALISES_TOPBAR_REFINAMENTO_PARA_CHATGPT.md` | novo | Este relatório. |
| `Docs/RELATORIO_TECNICO.md` | modificado | Registro da saída do CMS do menu e do novo fluxo de gerenciamento (2 linhas; terminadores CRLF preservados). |
| `nexobot/saber/administracao.py` | modificado | Resposta "Como a equipe administra o Guia": orientação sem citar o item de menu removido. |
| `nexobot/saber/suporte_guia.py` | modificado | Resposta sobre quem mantém o Guia: idem. |
| `blueprints/admin.py` | modificado | Rotas do gerenciamento por empresa (`analises_gerenciar`, `analises_empresa`, `analise_excluir`), helper `_excluir_analise` (ordem segura: banco primeiro, arquivos depois do commit) e `_empresa_gerenciavel`; registro em log da exclusão bem-sucedida; rota antiga `analise_deletar` removida. |
| `static/css/nexo.css` | modificado | Topbar com desfoque gradual em duas camadas, de ponta a ponta, com fallbacks; cartões de empresa, trilha e resumo do modal; coluna de ações compacta; acabamento das bordas (divisórias com recuo, realce arredondado, cabeçalhos/rodapés/sidebar/modais); células mais enxutas até 1440 px. |
| `templates/_macros.html` | modificado | Macro `uppill` (selos de upload V/C) compartilhada pelas duas listagens. |
| `templates/admin/analises.html` | modificado | Listagem geral sem lixeira/modal/script de exclusão; botão Editar; botão Abrir compacto (`btn-abrir`, coluna `col-acao`); selos V/C pela macro compartilhada; linha "sem resultados" com `hidden`. |
| `templates/admin/empresas.html` | modificado | Linha "sem resultados" com `hidden` (filtro alterna o atributo) para a última empresa visível ficar sem divisória. |
| `templates/cliente/analise.html` | modificado | Linha vazia da Curva ABC com `hidden` (filtro por classe alterna o atributo), pelo mesmo motivo. |
| `templates/admin/analises_empresa.html` | novo | Nova tela: empresa selecionada, suas análises, lixeira por linha e modal de confirmação com formulário POST (CSRF + confirmar=sim). |
| `templates/admin/analises_gerenciar.html` | novo | Nova tela: seleção de empresas em cartões (lista real de links) com busca (nome, razão social, CNPJ com/sem máscara) e trilha. |
| `templates/base.html` | modificado | Sidebar administrativa sem o item Base de Conhecimento; item Análises ativo também nas telas de gerenciamento. |
| `tests/test_gerenciamento_analises.py` | novo | Novo: 17 cenários HTTP (listagem, seleção, exclusão, segurança, integridade, acessibilidade da grade e busca por CNPJ sem máscara). |
| `tests/test_gerenciamento_navegador.py` | novo | Novo: fluxo completo em Chromium (inclui busca sem acento, CNPJ sem máscara, grade como lista de links, grupo nomeado, espera da navegação real), todas as larguras, topbar em todas as páginas (camadas, máscara, anel/brilho na camada de cima, cobertura da borda), sino, bordas (inclusive última linha visível). |
| `tests/test_overflow_navegador.py` | modificado | Infraestrutura de navegador extraída em `NavegadorCase`; páginas novas na varredura; teste do indicador da sidebar medindo "Dashboard" (rótulo mais largo) e "Enviar relatórios"; novo teste do menu administrativo. |

Não foram alterados: modelos, migrações, regras contratuais, ETL, PDFs, APIs, lógica do NexoBot (só o texto de duas respostas que citavam o item de menu), landing, Supabase/Render.


## E. Testes

**Comando oficial:** `python -B -m unittest discover -s tests -t . -v`, com `NEXO_TEST_BROWSER=1`, `NEXO_TEST_CDN_DIR` (Bootstrap 5.3.3 e Plotly 2.35.2 íntegros) e `NEXO_TEST_POSTGRES_BIN` (PostgreSQL 16 descartável), em cópia descartável do código, com dados fictícios.

| Execução | Código | Resultado |
|---|---|---|
| Suíte oficial — base | `264f713` (`main`) | 814 testes aprovados (suíte final da etapa anterior, local e na CI) |
| Suíte oficial — intermediária (local) | `6678eca` | 836 testes, 0 falhas, 0 erros, 0 pulados, 777 s; ensaios PostgreSQL "isolado", "AJ-06.1" e "gestão contratual" com `status: ok` (+22 testes novos) |
| Suíte oficial — final (local) | `deb7b59` | **837 testes, 0 falhas, 0 erros, 0 pulados**, 823 s; ensaios PostgreSQL "isolado", "AJ-06.1" e "gestão contratual" com `status: ok` (árvore `bea7e5b`, cujo código é o de `deb7b59`; log no pacote) |
| Suíte oficial — final (CI, PR #33) | `bea7e5b` (código de `deb7b59`) | **837 testes, OK** em 841 s no job `security-sqlite-browser` (Chromium instalado pelo `playwright install`) e job `security-postgresql` verde, run 40624619001 (nº 95); os três ensaios PostgreSQL com `status: ok` |
| Módulos desta etapa em execução isolada | `6678eca` → `deb7b59` | 42 testes (gerenciamento HTTP 16 + navegador 5 + overflow 21), 42 OK; após a 1ª rodada de correções da revisão (`9281abf`): gerenciamento HTTP 17 + navegador 5 = 22 OK em 149 s; após a 2ª rodada (`25fc333`…`deb7b59`): HTTP 17 + navegador 5 + overflow 21 = 43 testes em 365 s, 42 OK e 1 falha de teste (o filtro por empresa media a visibilidade por `style.display`, que deixou de ser o mecanismo) corrigida em `deb7b59` e reexecutada (2 OK); NexoBot (saber, api, conhecimento) 89 OK em 76 s |

**Testes de navegador** (Chromium): fluxo completo do gerenciamento (Editar → busca com e sem acento → Limpar → grade como lista real de links, busca por CNPJ sem máscara e com máscara parcial → Tab+Enter no cartão → grupo "Empresa selecionada" → análises só da empresa → modal com empresa/período/tipo/identificador → Cancelar sem efeito → Confirmar exclui só a escolhida → mensagem → Voltar); gerenciamento e listagem em 320, 360, 390, 768, 1024, 1366, 1536 e 1920 px (sem rolagem da listagem a partir de 1366 px, botões de ação legíveis, nada encoberto); topbar em 12 páginas autenticadas × 5 larguras com a página rolada (camadas forte/suave, máscara em degradê, `pointer-events: none`, faixa de ponta a ponta, título visível); sino aberto acima do cabeçalho, inteiro na tela; bordas (`border-collapse: separate`, divisórias com degradê nas pontas, realce arredondado sem a barra reta). **Segurança** (HTTP): 403 para CLIENTE, redirecionamento do anônimo, 405 para GET, 400 sem CSRF ou sem confirmação, 404 para análise de outra empresa/inexistente/empresa na lixeira, cascata e arquivo, falha no commit sem estado inconsistente, ausência de exclusão em massa, rota antiga removida. **Responsividade**: ver acima; zoom 150 % e teclado continuam cobertos pelo módulo de overflow. Mapa dos 25 cenários → testes em `resultados_testes.txt` do pacote.

**Ignorados:** nenhum. **Bloqueados:** Firefox e WebKit (não instalados). Nenhum teste existente foi removido ou enfraquecido; os ajustes em testes próprios desta etapa foram aceitar `border-spacing` computado como "0px" e, por achado da revisão, esperar a navegação real do POST de exclusão (`expect_navigation` + flash) em vez de um `wait_for_url` que já casava com a URL atual.

**Revisão adversarial independente** (fluxo de trabalho com cinco lentes — segurança/backend, templates/JS, CSS da topbar, CSS das bordas, navegação/testes — e verificadores céticos por achado, em cópia descartável):

| Lente | Achados | Gravidade | Destino |
|---|---|---|---|
| Segurança/backend (rotas, CSRF, pertencimento, cascata, transação, storage) | 1 | BAIXA | Teste de navegador esperava a navegação com `wait_for_url` numa URL que já era a atual → `expect_navigation` + flash (`9281abf`). Nenhum defeito CRÍTICO/ALTO/MÉDIO: pertencimento (404), `confirmar=sim` antes de qualquer mutação, POST-only, CSRF, cascata nos quatro filhos, rollback com "Nada foi alterado", arquivos legados só depois do commit — tudo confirmado por leitura e execução. Sugestão adotada: log da exclusão concluída. |
| Templates/JS (escape, estados vazios, acessibilidade, busca) | 3 | 1 MÉDIA, 2 BAIXA | `role="listitem"` em `<a>` apagava a semântica de link (MÉDIA); CNPJ gravado com máscara não era encontrado só com dígitos; `aria-label` em `<div>` sem papel → lista real `<ul>/<li>`, `data-cnpj` + busca por dígitos, `role="group"` (`9281abf`). XSS nos atributos (`data-busca`, `aria-label`) e estados vazios verificados sem defeito. |
| CSS da topbar (Backdrop Root, máscara, sino, alinhamento, fallbacks, custo) | 3 | BAIXA | Brilho interno pintado por baixo das camadas e anel de 1 px fora do desfoque → anel e brilho na camada de cima, camadas cobrindo a borda (`25fc333`). Custo de duas superfícies de `backdrop-filter` (mediana 16,7 → 33,3 ms por quadro a 1920 px em rasterização por software) → ensaiada a variante de camada única, descartada por deixar o conteúdo legível pela metade inferior do cabeçalho; decisão registrada (seção C.5 e I). Confirmados sem defeito: camadas desfocam a página (contraste 127 → 0,1), perfil monotônico sem faixas, sino acima e inteiro, fallbacks ativos. |
| CSS das bordas (collapse → separate, hover/focus, cartões, cabeçalhos, modais, ≤ 1440 px) | 1 | BAIXA | Última linha visível com divisória quando a última do `tbody` é a linha-placeholder oculta (Análises, Empresas, Curva ABC) → `hidden` + `:nth-last-child(1 of :not([hidden]))` (`25fc333`). 112 combinações tabela × largura sem mudança de largura/altura com `separate`; hover/focus, modo cartões, cabeçalhos e modais conferidos sem defeito. |
| Navegação e testes (menu, referências à Base de Conhecimento, cobertura, contagem de testes) | 4 | BAIXA | NexoBot orientava a abrir "Base de Conhecimento" no menu → texto sem o item (`7e29355`); teste do indicador media "Análises" e não o rótulo mais largo → "Dashboard" (`467047a`); busca sem acento não exercitada → cenário "paraiba" (`25fc333`); `Docs/RELATORIO_TECNICO.md` convertido a LF por acidente → CRLF restaurado (`467047a`). Contagem de testes e isolamento do teste de falha no banco confirmados. |

Verificadores céticos (um por achado, com reprodução independente em Chromium e axe-core): 12 verificadores lançados (um por achado); 7 vereditos recebidos até o fechamento deste relatório — 6 "não reproduz na árvore final" por já estarem corrigidos (`role` em `<a>`, busca por CNPJ, `aria-label` sem papel, espera da navegação, anel da borda, última linha visível) e 1 "real, confiança alta" (brilho da topbar), corrigido em `25fc333` seguindo a recomendação do verificador; os 5 restantes (custo das duas camadas, NexoBot, indicador da sidebar, busca sem acento, CRLF) ainda estavam em execução ao fechar e referem-se a achados já tratados ou documentados. Nenhum achado foi descartado sem verificação; os três achados de templates e o do teste de espera foram confirmados "já corrigidos" na árvore final (vereditos `real: false` por estarem resolvidos em `9281abf`), e o do brilho da topbar foi confirmado real e corrigido em `25fc333` com a recomendação do verificador (brilho também preservado nos fallbacks). Identificador do fluxo: `wf_5eefc838-166`.


## F. Evidências

Pacote `NEXO_AJUSTES_ANALISES_TOPBAR_BORDAS.zip` → pasta `evidencias/` (39 capturas PNG reais, índice `INDICE.md` e `manifest.json` com origem, SHA do código, viewport, dimensões e SHA-256 de cada arquivo). Todas as capturas foram feitas em Chromium headless (Playwright) contra o sistema real rodando em cópia descartável, com o seed de homologação (empresas "Demo", e-mails `example.invalid`): nenhuma imagem foi gerada ou retocada artificialmente. ANTES = código `264f713`; DEPOIS = código final da branch.

| Evidência | Arquivos (pasta `evidencias/`) | O que mostra |
|---|---|---|
| E1 — Análises ANTES | `E01_analises_ANTES_1366.png`, `E01b_analises_ANTES_dobra_1366.png`, `E01c_analises_ANTES_390.png` | Listagem geral com lixeira em cada linha, coluna Ações comprimida e cortada pela rolagem na primeira dobra de 1366×768; lixeira também nos cartões do celular. |
| E2 — Análises DEPOIS | `E02_analises_DEPOIS_1366.png`, `E02b_analises_DEPOIS_dobra_1366.png` | Botão Editar ao lado de Nova análise, Ações compacta só com Abrir, sem lixeira, tabela inteira visível a 1366 px sem rolagem horizontal, linha em foco com realce arredondado. |
| E3 — Seleção de empresas | `E03_gerenciar_selecao_empresas_1366.png`, `E03b_gerenciar_busca_1366.png`, `E03c_gerenciar_cartao_hover_1366.png` | Cartões de vidro com cubo, nome fantasia, razão social, CNPJ, ID, contagem e plano; busca filtrando ("aurora" → 1 cartão); hover com elevação; nenhuma lixeira. |
| E4 — Gerenciamento de uma empresa | `E04_gerenciar_empresa_selecionada_1366.png` | Cartão selecionado com marca de confirmação, trilha Análises › Gerenciar análises › empresa, análises só da empresa com Abrir e Excluir por linha, "Voltar à seleção de empresas". |
| E5 — Modal de confirmação | `E05_modal_confirmacao_exclusao_1366.png` | "Excluir análise?" com empresa, período, tipo, identificador, aviso de exclusão definitiva, Cancelar / Confirmar exclusão em vermelho. |
| E6 — Topbar ANTES | `E06_topbar_ANTES_dashboard_y420_1366.png`, `E06b_…faixa_y420…`, `E06c_…y980…`, `E06d_…faixa_y980…` | Dashboard rolado 420 e 980 px: superfície uniforme, conteúdo e gráficos passando atrás com um único desfoque. |
| E7 — Topbar DEPOIS | `E07_topbar_DEPOIS_dashboard_y420_1366.png`, `E07b_…faixa_y420…`, `E07c_…y980…`, `E07d_…faixa_y980…` | Mesmas posições: topo mais desfocado e escuro, base mais translúcida com as formas atrás ainda perceptíveis; título, sino e usuário legíveis. |
| E8 — Topbar em outra página | `E08_topbar_outra_pagina_empresas_1366.png` (+ `E08b_…faixa…`), `E08c_topbar_area_cliente_1366.png` (+ `E08d_…faixa…`), `E08e_topbar_sino_aberto_1366.png` | Componente global: Empresas (admin) e dashboard do cliente com o mesmo efeito, faixa de ponta a ponta; menu do sino aberto acima da topbar sem corte. |
| E9 — Bordas ANTES/DEPOIS | `E09_bordas_ANTES_analises_1366.png` / `E09b_bordas_DEPOIS_analises_1366.png`, `E09c`/`E09d` (empresas), `E09e`/`E09f` (histórico do cliente) | Divisórias retas de ponta a ponta e realce reto (antes) versus divisórias com recuo nas pontas, linha em foco com cantos de 12 px e traço roxo acompanhando o canto (depois). |
| E10 — Sidebar sem Base de Conhecimento | `E10_sidebar_ANTES_com_base_de_conhecimento_1366.png`, `E10b_sidebar_DEPOIS_sem_base_de_conhecimento_1366.png` | Menu com sete itens (antes) e com seis — Dashboard, Empresas, Contratos, Lixeira, Análises, Suporte — (depois); indicador do item ativo preservado. |
| E11 — Celular (390 px) | `E11_mobile_analises_390.png`, `E11b_mobile_gerenciar_selecao_390.png`, `E11c_mobile_gerenciar_empresa_390.png`, `E11d_mobile_modal_confirmacao_390.png`, `E11e_mobile_topbar_dashboard_390.png`, `E11f_mobile_sino_aberto_390.png`, `E11g_mobile_menu_lateral_390.png`, `E11h_mobile_bordas_analises_390.png` | Listagem em modo cartões só com Abrir; seleção de empresas em uma coluna; análises da empresa com Abrir/Excluir sem sobreposição; modal; topbar de margem a margem com botão do menu, sino e usuário; sino aberto inteiro na tela; menu lateral sem Base de Conhecimento; bordas no modo cartões. |

Observação de leitura: o desfoque gradual é sutil por desenho (sem "névoa" artificial); nas faixas recortadas (`*_faixa_*`, 118 px de altura) a diferença entre o topo e a base da topbar é mais fácil de ver, principalmente sobre os gráficos (E7d). Todas as capturas de "antes" e "depois" foram feitas com o mesmo roteiro, o mesmo seed e as mesmas posições de rolagem.

## G. Segurança

- Só administradores: as três rotas usam `admin_required` (login obrigatório + `is_admin`, senão 403); CLIENTE recebe 403 e anônimo vai para o login (testado).
- Só POST exclui: GET na rota de exclusão devolve 405; a listagem e a seleção são GET sem efeito.
- CSRF global do Flask-WTF: sem token ou com token inválido o POST devolve 400 e nada muda (testado).
- Confirmação explícita: além do modal, o formulário envia `confirmar=sim`; sem o campo o backend devolve 400.
- Pertencimento verificado no backend: `analise.id_empresa == id_empresa` da URL; análise de outra empresa, inexistente ou de empresa na lixeira → 404 sem tocar em nada (testado com a análise da outra empresa).
- Uma análise por requisição; não existe rota de exclusão sem identificador nem seleção múltipla (testado: `/excluir/` e `/excluir` → 404).
- Integridade: cascata ORM nos filhos (uploads, indicador, relatório, Curva ABC) numa única transação; arquivos em disco só saem depois do commit; falha simulada no commit mantém análise, filhos e arquivo (testado) e informa "Nada foi alterado".
- A exclusão é **definitiva** (sem lixeira de análises); o modal e a página dizem isso explicitamente.
- Rastreabilidade: cada exclusão concluída gera uma linha de log com o identificador da análise, a empresa e o administrador; as recusas (análise de outra empresa) também são logadas.
- Nenhuma regra comercial ou contratual foi alterada; a lixeira de empresas e a exclusão permanente de empresas não mudaram.


## H. GitHub

| Item | Valor |
|---|---|
| Branch | `claude/awesome-pascal-0ho42m` (recriada sobre a `main` `264f713`; publicação só nesta branch, por regra da sessão) |
| Pull request | [#33 — NEXO: gerenciamento de análises por empresa e refinamento global da interface](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/33) (rascunho até a validação final) |
| CI | Verde na árvore `bea7e5b` (código final `deb7b59`): workflow "NEXO Security CI" run [40624619001](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40624619001), jobs `security-postgresql` (success, 03:05–03:06 UTC) e `security-sqlite-browser` (success, 03:05–03:20 UTC, 837 testes OK). Também verde nas cabeças intermediárias `3c1b612` (run 40618831808), `256cf1b` (40621578097) e `7f3c97f` (40621918630). O commit de fechamento deste relatório (só documentação) dispara a mesma CI; o resultado na cabeça final é conferido no PR. |
| Merge | Não realizado: fica para o proprietário, após a CI e a conferência das condições de implantação (Render implanta a `main` automaticamente; nenhum deploy manual foi feito). |
| Histórico | Sem force push; commits lineares sobre a `main`. |

Commits (ordem cronológica):

| SHA | Mensagem |
|---|---|
| `c585e49` | feat(admin): criar gerenciamento de analises por empresa |
| `98041d3` | feat(ui): topbar com blur gradual, bordas refinadas, cartoes de empresas e acoes compactas |
| `635fb01` | refactor(nav): remover Base de Conhecimento do menu administrativo |
| `0b6a7aa` | test(ui): gerenciamento de analises (HTTP e navegador), topbar, bordas e menu |
| `c702de0` | docs(ui): relatorio tecnico da etapa para auditoria independente (rascunho) |
| `6678eca` | test(ui): aceitar border-spacing computado como valor unico |
| `3c1b612` | docs(ui): secoes de auditoria, alteracoes, arquivos, seguranca, GitHub e pendencias do relatorio |
| `9281abf` | fix(admin): aplicar achados da revisao no gerenciamento de analises |
| `256cf1b` | docs(ui): achados da revisao, correcoes e rastreabilidade no relatorio (parcial) |
| `7f3c97f` | docs(ui): secao de evidencias e SHA final de codigo no relatorio |
| `25fc333` | fix(ui): anel e brilho da topbar por cima do desfoque; ultima linha visivel sem divisoria |
| `7e29355` | fix(nav): respostas do NexoBot sem citar o item de menu removido |
| `467047a` | test(ui): indicador da sidebar mede o rotulo mais largo; CRLF do relatorio tecnico preservado |
| `af40c8e` | docs(ui): correcoes da revisao (topbar, bordas, NexoBot, testes) no relatorio (parcial) |
| `deb7b59` | test(ui): visibilidade por estilo computado no filtro por empresa |
| (último) | docs(ui): evidencias, testes finais, CI e parecer do relatorio — commit de fechamento, só documentação |


## I. Pendências

- **Firefox e WebKit** não estão disponíveis no ambiente: toda a validação de navegador foi no Chromium. As regras novas têm fallback (`@supports not (backdrop-filter)` e `prefers-reduced-transparency`), mas o desfoque gradual em Safari/Firefox não foi observado de fato.
- **Rotas do CMS do Guia** (`/admin/guia*`) continuam existindo sem link no menu, por decisão de preservação (Guia do cliente e NexoBot leem os mesmos tópicos; testes do NexoBot usam essas páginas). Se o proprietário quiser desativar o CMS por completo, é uma mudança à parte (rotas, templates, testes e seed).
- **"Nova análise" dentro da empresa selecionada** abre o formulário geral (com o seletor de empresa), sem pré-selecionar a empresa; não fazia parte do pedido e fica como melhoria futura.
- **Telas acima de 1454 px**: a topbar vai até a borda direita da área principal, enquanto o conteúdo das páginas mantém o limite de 1440 px à esquerda (regra pré-existente de `.page`); a faixa fica mais larga que o conteúdo nessas telas, como pedido ("até a extremidade direita da área principal").
- **Pendências anteriores fora deste escopo** (não alteradas): PDF com cabeçalho cortado e carimbo em UTC; "Períodos pagos: nenhum" ao lado de cobertura vigente em empresa cancelada; ordem dos detalhes do histórico; canal de contato em "Conta encerrada"; setas no sino.


## J. Parecer final

**IMPLEMENTADO E VALIDADO** — com as ressalvas de ambiente abaixo, todas registradas na seção I.

Base da conclusão (nada declarado sem evidência):
- As quatro alterações pedidas estão no código final (`deb7b59`): exclusão retirada da listagem geral e rota antiga removida; novo fluxo Editar → seleção de empresas em cartões → análises da empresa → modal de confirmação → `POST` com CSRF, confirmação explícita, pertencimento verificado no servidor, uma análise por requisição, transação com rollback; coluna Ações compacta sem esconder colunas; topbar global com desfoque gradual de ponta a ponta e fallbacks; bordas com divisórias recuadas e realces arredondados; Base de Conhecimento fora do menu administrativo com Guia do cliente e NexoBot preservados.
- Suíte oficial no código final: 837 testes, 0 falhas, 0 erros, 0 pulados (local, 823 s) e CI verde no PR #33 (seção H); 25 cenários funcionais, topbar em 12 páginas × 5 larguras, responsividade 320–1920 px, sino, bordas e menu cobertos por testes automatizados (seção E).
- 39 capturas reais ANTES/DEPOIS (E1–E11) em 1366 e 390 px com dados fictícios (seção F e pacote ZIP).
- Revisão adversarial independente em cinco lentes: 12 achados (1 MÉDIA, 11 BAIXA), todos tratados — 10 corrigidos no código ou nos testes, 1 decisão documentada (custo de duas camadas de desfoque) e 1 observação de alinhamento acima de 1454 px registrada como decisão do proprietário; nenhum achado CRÍTICO ou ALTO.
- Produção intocada: nenhum acesso ao Supabase ou ao Render, nenhuma migração, nenhum deploy manual, nenhum merge.

Ressalvas: validação de navegador apenas em Chromium (Firefox/WebKit ausentes); o efeito do desfoque gradual é sutil por desenho; a topbar vai até a borda direita em telas acima de 1454 px enquanto o conteúdo mantém o limite de 1440 px; as rotas do CMS do Guia continuam acessíveis por endereço. Merge e implantação ficam a critério do proprietário.
