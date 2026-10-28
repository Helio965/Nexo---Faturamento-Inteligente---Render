# Relatório: auditoria e correção de falhas visuais, responsividade e estabilização do frontend do NEXO

## 1. Identificação

| Item | Valor |
|---|---|
| Projeto | NEXO: Faturamento Inteligente |
| Data | 27/10/2026 |
| Branch de trabalho | `claude/awesome-pascal-0ho42m` (branch desta sessão; o nome sugerido `fix/nexo-correcao-overflow-responsividade-20261027` não foi usado porque a sessão publica apenas na branch designada) |
| SHA inicial (auditado) | `0f4a53e9003452dc66c0322a0269a22f52a96f5f` (`main`, merge do PR #31) |
| SHA final | «SHA_FINAL» |
| Ambiente | Cópia descartável do código fora do repositório; SQLite temporário com as migrações reais; dados fictícios (`@example.invalid`, CNPJs com prefixo 99); rede bloqueada, CDN servida de cópias locais; relógio da política contratual fixado em 02/03/2026 10:00 (São Paulo). Nenhum acesso ao Render, ao Supabase ou a banco real. |
| Navegadores | Chrome for Testing 153.0.8010.12 (Chromium) via Playwright 1.56.0, pt-BR, fuso America/Sao_Paulo. Firefox e WebKit não estão instalados no ambiente; ficam registrados como limitação. |
| Larguras | 320, 360, 390, 768, 1024, 1366, 1440, 1536 e 1920 px; zoom de 125%, 150% e 200% sobre 1366 px (viewport CSS menor com escala maior); paisagem 844×390. |
| Sistema | Ubuntu 24.04.5 LTS, Python 3.12.3, Flask 3.1.3, SQLAlchemy 2.1.6 |

## 2. Resumo

A auditoria reproduziu, em navegador real e com medições das posições dos elementos, os problemas apontados nas dez imagens e encontrou outros. Os cortes de informação tinham uma causa comum: a coluna de ações fixa (`position: sticky; right: 0`), aplicada pelo script do shell a toda tabela que rolasse, ficava por cima das colunas vizinhas. Nas medições ANTES, isso encobria 28 a 149 px de dados em 70 combinações de página e largura (Análises em todas as larguras; Empresas, Contratos, Lixeira, Histórico, Suporte e as tabelas dos dashboards no celular e no tablet).

As correções preservam a identidade visual (vidro, roxo, fundo artístico, cartões translúcidos, sidebar e gráficos) e não escondem informação:

- **Tabelas:** nenhuma coluna fica mais por cima das outras. Uma tabela mais larga que o contêiner rola na horizontal dentro dele, com a borda esmaecida, uma dica "Deslize para ver as outras colunas" visível até o fim da rolagem, foco pelo teclado e setas. Quando a tabela precisaria de bem mais que a largura disponível (celular, tablet, zoom alto), ela vira uma grade de cartões na mesma linguagem visual: uma linha por cartão, cada valor com o rótulo da coluna. Nada é removido.
- **Análises** mostra Empresa, Período, Tipo, Quinzena, Status, Uploads, Criação, Publicado e Ações em todas as larguras; **Lixeira** mostra a data de remoção inteira, com "Restaurar" e "Excluir" separados e na identidade do painel.
- **KPIs** não encolhem abaixo de 18 px: quando o valor não cabe, quebra a linha em vez de ser cortado.
- **Pareto da Curva ABC** em barras horizontais: o nome do produto fica no eixo vertical em até três linhas (sem rótulos diagonais, sem sobreposição), o nome completo vai para a tooltip e para a descrição acessível; o % acumulado fica no eixo superior (ou escrito no fim da barra, no celular).
- **NexoBot** menor no tablet e no celular (só o ícone abaixo de 992 px); os avisos em tempo real sobem para não ficar no mesmo canto; o espaço reservado no fim da página e o sumiço com a gaveta aberta foram mantidos.
- **Sidebar:** o ponto do item ativo passou a ser um item do flex depois do rótulo; "Base de Conhecimento" não encosta mais nele.
- **Envio de relatórios:** o campo de arquivo entrou na ordem de Tab (estava `display: none`), arrastar e soltar funciona, o arquivo já enviado aparece como "Arquivo recebido" (não como selecionado), as dropzones ocupam o slot inteiro e enviar sem arquivo é barrado antes do POST.
- **Componentes sem tema:** selects com seta, caixa de seleção e modais na paleta; ações destrutivas em vermelho; páginas 403/404/500 do NEXO em português.
- **Navegação e formatação:** botão "Análises" de cada empresa abre a lista já filtrada; e-mail volta preenchido após senha errada; link "Pular para o conteúdo"; percentuais, CNPJ e segmento em pt-BR; mensagens com botão de fechar e pausa ao passar o mouse.

Testes: suíte oficial com 814 testes aprovados, 0 falhas, 0 erros e 0 pulados no código final (794 na base), localmente e na CI e o novo `tests/test_overflow_navegador.py` (20 testes novos: 15 em navegador e 5 HTTP), que mede posições reais (coluna encoberta por célula fixa, KPI estourando ou com fonte abaixo de 18 px, botão flutuante sobre controle, rótulo de gráfico cortado ou sobreposto, campo de arquivo fora do Tab) em oito larguras e no zoom de 150%, com dados fictícios extensos.

## 3. Inventário de problemas

Gravidade: CRÍTICA (bloqueia uma tarefa), ALTA (esconde informação essencial), MÉDIA (prejudica leitura ou uso), BAIXA (acabamento). "Medido" indica valor obtido nas sondas ANTES (`metricas/medicoes_antes.json` do pacote de evidências).

| ID | Tela | Problema | Causa comprovada | Gravidade | Correção | Status |
|---|---|---|---|---|---|---|
| FE-01 | Análises (admin) | Colunas Criação, Publicado e Status encobertas pela coluna de ações. Medido: Criação 130 px + Publicado 28 px a 1366; Criação 59 + Publicado 102 a 1440; Publicado 81 a 1536; Status 149 a 1024; no celular, Período 107–145 px. Cabeçalhos "PUB…" cortados. | `.table-responsive-x.tem-rolagem .col-acoes { position: sticky; right: 0 }` aplicado pelo script de `base.html` a toda tabela que rola; a célula fixa é pintada por cima das vizinhas na posição inicial da rolagem. | ALTA | Coluna fixa removida; rolagem indicada (máscara + dica + foco/setas); cartões quando a tabela precisa de mais de 1,35× a largura; período quebra entre as datas; botão de exclusão na identidade. | Corrigido |
| FE-02 | Lixeira (admin) | "Movido em" e os botões "Restaurar"/"Excluir permanente" encobertos; botões Bootstrap sólidos (verde/vermelho) colados. | Mesma causa de FE-01; `btn btn-success`/`btn btn-danger` fora do design system; célula com `white-space: nowrap`. | ALTA | Sem coluna fixa; e-mail com ponto de quebra após "@"; botões `btn-ghost` separados (gap 6 px, quebram em duas fileiras quando falta espaço); cartões no celular/tablet. | Corrigido |
| FE-03 | Empresas (admin) | Status e E-mail encobertos a 1366–1440 (349 px de ações); a 768 a coluna fixa cobre Segmento, Plano, Status e E-mail; no celular a tabela de 8 colunas segue sem layout próprio. | Mesma causa de FE-01; quatro botões em `nowrap`. | ALTA | Sem coluna fixa; ações em `.acoes` (quebram em duas fileiras); cartões em duas colunas no tablet e uma no celular; CNPJ com máscara; segmento sem "Moda E Acessórios". | Corrigido |
| FE-04 | Contratos, Detalhes da empresa, Histórico, Suporte, Chamados, Base de Conhecimento, tabelas dos dashboards | No celular (320–390) e no tablet, a coluna fixa cobre o Detalhe/Status (medido: Status 29–100 px e Detalhe 34–100 px a 320 em Contratos). | Mesma causa de FE-01. | MÉDIA | Tratamento genérico das tabelas (rolagem indicada ou cartões), sem alterar os templates dessas páginas. | Corrigido |
| FE-05 | Pareto da Curva ABC (dashboard e análise do cliente) | Rótulos diagonais truncados em 22/12 caracteres (medido: 10 rótulos com "…" e 8 pares sobrepostos em todas as larguras); nome completo ausente também na tooltip. | `tickangle: -38` com `ticktext` encurtado e `hovermode: 'x unified'` (o título da tooltip usa o ticktext). | MÉDIA | Barras horizontais, nome em até 3 linhas (quebra por palavra), tooltip com nome completo, classe e acumulado; eixo superior do % acumulado; no celular, duas ou três marcas compactas ("R$ 25 mil") e o % acumulado na última linha do rótulo; `role="img"` com resumo. | Corrigido |
| FE-06 | Sidebar | Ponto do item ativo a 3–4 px do rótulo "Base de Conhecimento" (parece parte do texto). | `.nav-item.active::before` absoluto em `right: 12px`, sem reservar espaço. | MÉDIA | Ponto como `::after` no fluxo do flex (`margin-left: auto`); rótulo longo quebra a linha em vez de colidir. | Corrigido |
| FE-07 | Enviar relatórios (cliente) e Upload (admin) | Campo de arquivo inacessível por teclado e tecnologia assistiva (`display: none`); arrastar e soltar prometido mas inoperante (`drop` só fazia `preventDefault`); arquivo já enviado exibido como se estivesse selecionado; dropzones `inline-block` com larguras irregulares; enviar sem arquivo ia ao servidor. | `.dropzone input[type=file] { display: none }`; handler de `drop` incompleto; estado único "nome do arquivo". | CRÍTICA (WCAG 2.1.1) | Campo escondido só visualmente (permanece no Tab, Enter/Espaço abrem o seletor, foco na dropzone); `drop` coloca o arquivo no campo; estados "Arquivo recebido"/"Selecionado para envio"/erro; validação de extensão e de envio vazio no navegador; dropzone em bloco; comportamento compartilhado em `base.html`. | Corrigido |
| FE-08 | NexoBot | Pílula "NexoBot" larga no tablet cobre títulos dos cartões; toasts de tempo real no mesmo canto do botão. | Rótulo exibido a partir de 640 px; `.nexo-toast-wrap` em `bottom: 22px`. | BAIXA | Rótulo só a partir de 992 px (botão redondo de 56 px abaixo disso); toasts a 96 px do fundo quando o NexoBot existe. | Corrigido |
| FE-09 | KPIs | Script reduzia a fonte até 16 px e, se ainda não coubesse, o `overflow: hidden` do cartão cortava o valor. | `ajustarKpis` com piso de 16 px e `white-space: nowrap` sem alternativa. | MÉDIA | Piso de 18 px; abaixo disso o valor quebra a linha (`white-space: normal`, `overflow-wrap: anywhere`). Nome de produto nos cartões de destaque quebra a linha. | Corrigido |
| FE-10 | Formulários e modais | Selects sem seta (pareciam campos de texto); caixa de seleção quase invisível desmarcada e azul marcada; modais no cinza padrão do Bootstrap. | `background:` (atalho) zerava o `background-image` do `.form-select`; `.form-check-input` sem tema; `.modal-content.bg-dark`. | MÉDIA | `background-color` nos campos; checkbox na paleta; `.nexo-modal` (vidro, cantos de 20 px, botões temáticos) nos três modais. | Corrigido |
| FE-11 | Erros 403/404/500 | Página padrão do servidor (branca, "Not Found", inglês, sem link). | Sem `errorhandler` para esses códigos. | MÉDIA | Handlers em `app.py` renderizando `erro_simples.html` (cartão das telas de acesso, link para o painel ou para o início); JSON em `/api/`. Status HTTP inalterado. | Corrigido |
| FE-12 | Navegação | Botão "Análises" de uma empresa abria a lista sem filtro; e-mail apagado após senha errada; ordem de Tab no login passava por "Esqueci minha senha" antes da senha; placeholder "••••••••" parecia senha preenchida. | Link sem parâmetro; `render_template` sem `email_digitado`; link no DOM antes do campo. | MÉDIA / BAIXA | `?empresa=<id>` pré-seleciona o filtro (por id, não por nome); `email_digitado` devolvido; link abaixo do campo; placeholder removido. | Corrigido |
| FE-13 | Formatação pt-BR | Percentuais "18.6%" na tabela ABC; CNPJ sem máscara; "Moda E Acessórios"; "(18 dia(s))". | `'%.1f'|format`; sem filtro de CNPJ; `|title`; texto fixo. | BAIXA | Vírgula decimal; macro `cnpj`; macro `segmento` só reformata valores com `_`/caixa alta; "faltam 18 dias". | Corrigido |
| FE-14 | Acessibilidade | Sem "Pular para o conteúdo" (9 paradas de Tab); botões de linha com nomes idênticos; chips V/C só por cor; filtro ABC sem semântica de abas; gráficos sem alternativa textual; mensagens de sucesso somem em 4,2 s sem fechar; textos das telas de acesso e asterisco de obrigatório abaixo de 4,5:1. | — | MÉDIA / BAIXA | Skip link; `aria-label` com o nome da empresa/período; texto oculto nos chips; `role="tab"` + `aria-selected`; `role="img"` + resumo em todos os gráficos; mensagens com botão de fechar, 6 s e pausa com mouse/foco; `--text-dim` das telas de acesso para #9d98ba e asterisco #c4a0fb. | Corrigido |
| FE-15 | Celular e acabamento | Título da topbar truncado ("Enviar relatórios E…"); botões quebrando em 2 linhas; selo de IA em 3 colunas; busca de Empresas casava com os rótulos dos botões e sem "Limpar"; painel de notificações 4% transparente. | `white-space: nowrap` + `text-overflow`; `page_title` longo; `ia-banner` com nós soltos; busca em `textContent` da linha. | BAIXA | Título em até 2 linhas abaixo de 576 px e "Enviar relatórios"; `nowrap` nos botões; selo em `span`; busca só nas células de dados, com contagem anunciada e "Limpar busca"; painel opaco. | Corrigido |
| FE-16 | Gestão contratual | Formulários com 980 px fixos desalinhados dos avisos; "Cancelar contrato"/"Revogar" só vermelhos no hover; botões só de ícone nos detalhes; confirmação destrutiva no roxo comum. | `style="max-width:980px"`; `.btn-ghost.is-danger` só com `:hover`; `.btn-nexo.is-danger` sem regra CSS. | BAIXA / MÉDIA | Largura cheia; vermelho em repouso; "Período pago"/"Revogar" com texto e `aria-label`; `.btn-nexo.is-danger` vermelho. | Corrigido |
| FE-17 | Revisão independente das correções (achados sobre o código novo) | (a) `white-space: nowrap` global nos botões fazia "Voltar"/"Confirmar" dos formulários contratuais sair pela esquerda da tela no celular (medido: 432–516 px de botões para 296–366 px úteis); (b) dropzone continuava em "Selecionado para envio" depois que o navegador limpava o campo (reabrir o seletor e cancelar) e perdia o estado "recebido" após um arquivo inválido; (c) no Pareto, dois produtos com o nome encurtado idêntico viravam uma barra só (categoria duplicada); (d) dica "Deslize…" alinhada à direita caía na faixa esmaecida da máscara; (e) anel de foco do contêiner rolável esmaecido; (f) `border-secondary` do Bootstrap (`!important`) vencia a cor de borda dos modais. | Regras novas desta própria correção, revisadas por agentes independentes antes da publicação. | ALTA (a) / MÉDIA (b) / BAIXA (c–f) | `nowrap` restrito a `.page-head-actions` e botões quebram no modo cartões; `limparSelecao()` restaura o estado inicial (recebido ou vazio); barras do Pareto em posições numéricas com `tickvals`/`ticktext`; dica alinhada à esquerda com reserva de 88 px; `:is(:focus-visible, :has(:focus-visible))`; `border-secondary` removido dos seis cabeçalhos/rodapés. Regressão coberta no teste (formulários contratuais a 320–390, cancelamento da seleção, par de nomes gêmeos, dica fora da máscara). | Corrigido |
| FE-18 | Revisão independente (backend e acessibilidade) | (a) A página de erro 500 nova voltaria à página branca do servidor quando o erro original fosse do banco com usuário logado: no PostgreSQL a transação fica abortada e a consulta do sininho (context processor) dentro do próprio handler lançava exceção (reproduzido em PostgreSQL 16 descartável pelo revisor; em SQLite não ocorre); (b) filtro ABC com `role="tab"`/`aria-selected` sem o comportamento de abas (setas, `tabindex` rodante, `tabpanel`): papel anunciado não correspondia à interação (WCAG 4.1.2); (c) `aria-label` do campo de arquivo substituía o texto visível da dropzone no nome acessível (WCAG 2.5.3) e omitia o estado "Arquivo recebido"/nome do arquivo; (d) medições de gráfico pulavam em silêncio sem a cópia local do Plotly. | Código novo desta correção. | MÉDIA (a–c) / BAIXA (d) | `db.session.rollback()` no handler de 500 e sininho tolerante a falha do banco (página sai sem notificações, com aviso no log) — confirmado de novo em PostgreSQL 16 descartável: os quatro cenários (anônimo/logado × falha de banco/erro comum/404) devolvem a página do NEXO; o verificador cético apontou o subcaso "banco cai no meio da requisição e fica fora" (context processors do sininho e do catálogo do NexoBot ainda lançavam com o usuário expirado), coberto em seguida por tolerância nos dois processors e por uma contingência em `_pagina_erro` que renderiza o template sem o contexto da sessão — reproduzido com o servidor derrubado dentro da view (cliente, admin e anônimo: página do NEXO, status 500); filtro ABC como `role="group"` + `aria-pressed`; campo de arquivo com `aria-labelledby` (título do slot + estado + nome do arquivo); teste de layout exige Plotly íntegro (hash SRI conferido) ou é pulado com o motivo. | Corrigido |
| FE-19 | Pareto no celular com fonte de reserva | Com a fonte de reserva do sistema (DejaVu Sans, mais larga que a Inter — caso de quem não carrega o Google Fonts), a 320 px o rótulo do 1º produto era cortado pela margem esquerda do gráfico: a margem direita de 84 px reservada ao "% acum." fora da barra não deixava espaço para o nome. Encontrado na execução dos testes de layout sem a Inter (fontconfig só com DejaVu/Liberation). | Orçamento fixo de 18 caracteres por linha + margem direita fixa, calibrados na Inter. | MÉDIA | No celular o % acumulado vai na última linha do rótulo (em âmbar, como a linha do computador) e a margem direita cai para 16 px; os caracteres por linha são calculados pela largura do gráfico e pela fonte efetiva (`NEXO.larguraTexto`, ~40 % da largura), expostos em `data-por-linha` para o teste. Suíte executada com Inter e com fontes de reserva. | Corrigido |
| FE-20 | Gráficos Plotly ao redimensionar (lente de gráficos da revisão independente) | (a) Qualquer `resize` (girar o celular, teclado do Android, barra de endereço do Safari) fazia o Plotly apagar `layout.height` e a caixa `.chart-box` cair para a `min-height` de 220 px enquanto o SVG mantinha a altura (536 px para 10 produtos) por cima da nota e do cartão seguinte; no segundo `resize` o gráfico era redesenhado com 220 px (mecanismo já existia na `main`, agravado pela altura proporcional ao número de produtos); (b) o modo estreito/largo do Pareto era decidido uma vez só: girar de paisagem para retrato mantinha o layout largo numa caixa de 330 px; (c) a altura `44·n+96` não cabia três linhas por nome (rótulos vizinhos a −3/−6 px); (d) entre 560 e ~570 px os valores do eixo giravam e eram cortados na base. Reproduzido pelo revisor em harness com o bloco NEXO extraído de `base.html`. | `responsive: true` + altura só no layout; modo calculado no `newPlot`; altura por produto fixa; estimativa de largura do Plotly. | ALTA (a) / MÉDIA (b, c) / BAIXA (d) | `NEXO.plot` fixa a altura da caixa quando o layout traz altura; o Pareto guarda os dados e reavalia o modo num `ResizeObserver` (com debounce), redesenhando ao trocar de modo; altura calculada pelas linhas reais dos rótulos (line-height 1,3 + folga); marcas redondas e compactas no eixo (sem rotação). Teste: cenário de redimensionamento (1366 → 360 → 1366 → paisagem → 390) exigindo caixa = SVG, modo certo e sem rótulos sobrepostos; sobreposição vertical dos rótulos do eixo Y agora medida; rótulos girados não geram falso positivo. | Corrigido |

**Descartados após verificação** (não são defeitos):

- Texto pequeno nas imagens de página inteira: efeito da redução da captura; na resolução original os tamanhos são os do design (0,9 rem nas tabelas, 0,74 rem nos rótulos).
- Barra lateral esticada nas capturas de página inteira: artefato da captura; no navegador ela é fixa.
- "mm/dd/yyyy" e "Choose File": idioma da interface do navegador de teste.

**Revisão independente (adversarial) das próprias correções.** Antes da publicação final, cinco agentes revisores independentes (shell JS, CSS, backend, acessibilidade e gráficos Plotly) leram o diff e a árvore de trabalho e reproduziram hipóteses em harness próprio (Chromium, Node, PostgreSQL 16 descartável); cada achado foi depois entregue a um agente cético com a instrução de refutá-lo. Resultado: 16 achados (FE-17 a FE-20), todos tratados — 15 corrigidos antes de a verificação rodar (os céticos registraram "já corrigido na árvore") e 1 confirmado pelo cético (banco fora do ar durante a página de erro 500), corrigido em seguida e reproduzido de novo. O resumo com os vereditos está no pacote de evidências (`revisao_adversarial_resumo.txt`).

## 4. Auditoria por interface

- **Login e telas de acesso:** cartão, cubo e redirecionamentos corretos. Corrigidos a ordem de Tab, o placeholder e o contraste dos textos auxiliares; o e-mail volta preenchido após senha errada. Sem rolagem horizontal de 320 a 1366 px.
- **Administração: Dashboard.** KPIs, alerta e três gráficos íntegros; as tabelas "Homologação" e "Últimas análises" viram cartões no celular. Gráficos com descrição acessível.
- **Empresas.** Ver FE-03. Busca acessível (rótulo, resultado anunciado, "Limpar busca"); botões com nome da empresa; modal na identidade.
- **Contratos (visão geral e detalhes).** Tabelas sem coluna fixa; no celular, cartões com "Detalhe" completo; formulários na largura dos avisos; ações destrutivas sinalizadas; checkbox e selects temáticos. O quadro "Situação contratual" e o histórico não mudaram de conteúdo.
- **Análises.** Ver FE-01. Filtro por empresa pré-selecionável; modal de exclusão na identidade; chips V/C com texto.
- **Lixeira.** Ver FE-02. Confirmações destrutivas preservadas (modal e `POST`).
- **Base de Conhecimento e Guia.** Sidebar corrigida (FE-06); tabela com ações em `.acoes`; o Guia do cliente não mudou.
- **Cliente: Dashboard e Análise detalhada.** KPIs (FE-09), Pareto (FE-05), indicador sem barra de zoom, percentuais com vírgula, CNPJ mascarado, filtro ABC com semântica de abas, selo de IA sem quebra em colunas, descrições acessíveis nos gráficos.
- **Gráficos.** Plotly mantido. Pareto horizontal; linha temporal com `automargin`; descrições textuais; números pt-BR inalterados. Nenhuma fórmula, valor ou classe ABC foi alterada.
- **Tabelas.** Regra única em `base.html` + `nexo.css` para todas as tabelas `.table-responsive-x`.
- **Suporte e Guia.** Tratamento genérico das tabelas; "Novo chamado" funciona (alterna o formulário).
- **NexoBot.** Ver FE-08. Mecanismo de atendimento intocado.
- **Responsividade.** Todas as páginas auditadas sem rolagem horizontal e sem elemento fora da tela de 320 a 1920 px e no zoom de 125–200% (medições DEPOIS).

## 5. Correções implementadas (arquivos)

| Arquivo | O que mudou e por quê |
|---|---|
| `static/css/nexo.css` | Remoção da coluna fixa; dica de rolagem, barra de rolagem fina e foco do contêiner; modo cartões (`.em-cartoes`); `.col-nome`, `.t-email`, `.t-periodo`, `.acoes`; padding das células 14 px até 1599 px; KPI com quebra de linha; sidebar com ponto no fluxo e rodapé compacto em paisagem; dropzone em bloco com campo escondido só visualmente e estados; `background-color` nos campos (seta do select), checkbox temático, asterisco #c4a0fb; `.btn-nexo.is-danger`, `.btn-ghost.is-danger` em repouso, `nowrap` só nos botões do cabeçalho da página (e quebra no modo cartões); dica de rolagem fora da faixa esmaecida e anel de foco do contêiner íntegro; toasts acima do NexoBot; rótulo do NexoBot só ≥ 992 px; `.skip-link`; `.nexo-modal`; título da topbar em 2 linhas no celular; `--text-dim` das telas de acesso; `.ia-banner` com quebra; `.form-contrato`; páginas de erro. |
| `templates/base.html` | Skip link e `main#conteudo`; mensagens com fechar e pausa; `ajustarKpis` com piso de 18 px e quebra; `prepararTabela`/`marcarTabelas` (rótulos `data-label`, papéis ARIA, dica, foco, setas, modo cartões por medição); dropzones compartilhadas (com `limparSelecao()` ao cancelar a seleção ou recusar o arquivo); `NEXO.fmtBRL`, `fmtCompacto`, `quebrarRotulo`, `descrever`; Pareto horizontal em posições numéricas (uma barra por produto mesmo com nomes encurtados iguais); linha temporal com descrição e `automargin`. |
| `templates/_macros.html` | Macros `cnpj`, `periodo`, `email`; `segmento` sem `|title` indevido. |
| `templates/admin/analises.html` | Filtro por id de empresa com pré-seleção; `col-nome`, `t-periodo`, `.acoes`; chips com texto oculto; botão de exclusão `btn-ghost is-danger`; modal `nexo-modal` (sem `border-secondary`). |
| `templates/admin/lixeira.html` | Botões `btn-ghost` separados em `.acoes`; CNPJ e e-mail com macros; modal `nexo-modal` (sem `border-secondary`). |
| `templates/admin/empresas.html` | Busca acessível com "Limpar busca"; `.acoes` com `aria-label` por empresa; link "Análises" com `?empresa=`; CNPJ, segmento e e-mail com macros; modal `nexo-modal` (sem `border-secondary`). |
| `templates/admin/contratos.html` | "faltam N dias" / "há N dia(s)" sem parênteses duplos. |
| `templates/admin/empresa_detalhe.html` | Botões "Período pago" e "Revogar" com texto e `aria-label`; CNPJ mascarado. |
| `templates/admin/contrato_form.html`, `contrato_acao.html`, `cobertura_form.html` | Formulário na largura dos avisos (`form-contrato`); CNPJ mascarado. |
| `templates/admin/dashboard.html` | Descrições acessíveis dos três gráficos; `automargin` no eixo das análises por status; período com macro. |
| `templates/admin/guia.html` | Ações em `.acoes` com `aria-label`. |
| `templates/admin/upload.html`, `templates/cliente/upload.html` | Dropzone com estados e campo acessível; script local removido (compartilhado); título "Enviar relatórios". |
| `templates/cliente/dashboard.html` | CNPJ mascarado; indicador sem barra de zoom; descrições acessíveis; períodos com macro. |
| `templates/cliente/analise.html` | Percentuais com vírgula; filtro ABC `role="tab"`; selo de IA em `span`; descrição do gráfico. |
| `templates/cliente/historico.html` | Período com macro (quebra entre as datas). |
| `templates/auth/login.html` | Link "Esqueci minha senha" depois do campo; sem placeholder de pontos. |
| `templates/erro_simples.html` | Cartão das telas de acesso, código do erro, link para o painel/início. |
| `app.py` | `errorhandler` 403/404/500 (HTML no portal, JSON em `/api/`), `_painel_url` tolerante a banco indisponível. |
| `blueprints/admin.py` | `analises?empresa=<id>` validado (só dígitos). |
| `blueprints/auth.py` | `email_digitado` após tentativa inválida. |
| `tests/test_overflow_navegador.py` | Novo: regressão de overflow/responsividade/acessibilidade (ver seção 6). |

Não foram alterados: modelos, migrações, regras contratuais, ETL, PDFs, APIs, autenticação (além de devolver o e-mail digitado), NexoBot e a landing.

## 6. Testes

**Comando oficial:** `python -B -m unittest discover -s tests -t . -v`, com `NEXO_TEST_BROWSER=1`, `NEXO_TEST_CHROMIUM` (Chrome for Testing 153 / Chromium 1243), `NEXO_TEST_CDN_DIR` (cópias íntegras de Bootstrap 5.3.3 e Plotly 2.35.2, hash SRI conferido) e `NEXO_TEST_POSTGRES_BIN` (PostgreSQL 16 descartável, criado e destruído pelo próprio ensaio). Executado em cópia descartável do código, fora do repositório, com o mesmo ambiente sintético da CI (nenhuma credencial real).

| Execução | Código | Resultado |
|---|---|---|
| Suíte oficial — base | `0f4a53e` (`main`) | 794 testes aprovados (resultado da homologação anterior, mesma suíte que entrou na `main`); CI verde no merge |
| Suíte oficial — final (local) | `093fbee` | **814 testes, 0 falhas, 0 erros, 0 pulados**, 632 s; ensaios PostgreSQL "isolado", "AJ-06.1" e "gestão contratual" com `status: ok` e `production_access: false` |
| Suíte oficial — final (CI, PR #32) | `093fbee` | `security-sqlite-browser`: 814 testes OK em 705 s; `security-postgresql`: OK (run 40606041025) |
| `tests/test_overflow_navegador.py` com a fonte Inter | `093fbee` | 20/20 (`OverflowNavegadorTests` 15 + `PaginasDeErroTests` 5) |
| `tests/test_overflow_navegador.py` com fontes de reserva (fontconfig só com DejaVu/Liberation, sem Inter) | `093fbee` | 20/20 — simula quem não carrega o Google Fonts |
| Módulos de navegador já existentes (`test_contratos_navegador`, `test_identidade_visual`, `test_nexobot_navegador`) | durante as correções e na suíte final | OK (51 testes na execução isolada; todos incluídos nos 814) |
| Reprodução em PostgreSQL 16 (página de erro 500) | `093fbee` | 8 cenários (falha SQL com banco em pé; banco derrubado dentro da requisição; cliente/admin/anônimo; 404) devolvem a página do NEXO com o status correto |

**O que o novo módulo mede** (posições reais no navegador, não só `scrollWidth`): célula encoberta por célula fixa; modo cartões com rótulo em cada valor e botões dentro do cartão; última coluna alcançável (rolagem e setas ← →); dica de rolagem fora da faixa esmaecida; KPI estourando ou com fonte abaixo de 18 px; NexoBot sobre controles no fim da página e escondido com a gaveta aberta; indicador da sidebar com folga ≥ 6 px do rótulo; controle além do limite recortado (ex.: botões "Voltar/Confirmar" a 320–390 px); gráficos com `role="img"` e descrição, rótulos sem corte, sem sobreposição horizontal nem vertical, reticências só quando o nome não cabe em 3 linhas (caracteres por linha reais do gráfico), uma barra por produto, SVG dentro da caixa, modo estreito/largo coerente com a largura e redimensionamento 1366 → 360 → 1366 → paisagem → 390; dropzone acessível pelo teclado (Tab, foco visível, nome acessível com os textos visíveis), envio vazio barrado, formato recusado, estado "recebido" restaurado; filtro ABC como botões de alternância por teclado; filtro `?empresa=`; busca de Empresas com "Limpar busca"; 404/403/500 na identidade (HTML) e JSON em `/api/`; e-mail devolvido após senha errada; página de erro com o banco inacessível. Larguras 320, 360, 390, 768, 1024, 1366, 1536 e 1920 px, zoom 150 % e páginas públicas (só regressão).

**Falhas encontradas pelos testes durante o trabalho (todas corrigidas antes da publicação final):** CI vermelha em `7c22786` porque o runner não tinha cópia do Bootstrap (modal da Lixeira não abria; a landing bloqueava o substituto pelo SRI) e `test_contratos_navegador` acusava `scrollWidth` em "detalhes" (referência de 140 caracteres sem espaços vazando do cartão) e `form.relatorio-doc` renomeado; localmente: cabeçalho do slot de envio a 320 px com nome de arquivo longo; rótulo do Pareto cortado a 320 px e marcas do eixo sobrepostas a 1366 px com a fonte de reserva; truncamento de rótulos medido com o orçamento errado. Nenhum teste foi alterado para esconder uma regressão: as mudanças nos testes ampliaram o que é medido (sobreposição vertical, rótulos girados, resize, nome acessível) ou corrigiram localizadores do próprio teste novo.

**Ignorados:** nenhum. **Bloqueados:** Firefox e WebKit (não instalados no ambiente; limitação registrada). Os testes de layout exigem as cópias íntegras do Bootstrap/Plotly: sem elas a classe é pulada com o motivo no log (na CI as cópias são baixadas e conferidas; nas duas execuções finais nada foi pulado).

## 7. Evidências visuais

«EVIDENCIAS»

## 8. Riscos e limitações

- **Firefox e WebKit** não estão disponíveis no ambiente; tudo foi validado no Chromium. As regras usadas (`:has()`, `backdrop-filter`, `text-wrap: balance`, `-webkit-line-clamp`) têm fallback: sem `:has()` o foco da dropzone fica só no anel do campo oculto (invisível), por isso o campo também recebe `aria-label`; `text-wrap: balance` é só estético.
- **Modo cartões no notebook (1024 px):** Análises e Empresas viram cartões em duas colunas porque a tabela precisaria de mais de 1,35× a largura. Se o proprietário preferir tabela com rolagem nessa largura, basta subir o fator em `marcarTabelas` (`base.html`).
- **Análises e Lixeira a 1366–1440 px** continuam rolando na horizontal (9 e 7 colunas não cabem): a rolagem é indicada, nenhuma coluna fica encoberta e o teclado alcança todas; mas "Ações" não está visível sem rolar. Uma alternativa futura é reduzir "Período" a uma data por linha ou mover "Publicado" para dentro de "Status".
- **Nomes de produto com mais de ~54/78 caracteres** recebem reticências no eixo do Pareto (o nome completo fica na tooltip, na descrição acessível e na tabela ABC).
- **Botão flutuante do NexoBot** continua cobrindo o que estiver sob ele no meio de uma página longa, como qualquer botão flutuante; no fim da página há espaço reservado e, com a gaveta aberta, ele some.
- **Pendências fora do escopo de frontend** (documentadas na homologação anterior, não alteradas): cabeçalho do PDF cortado no topo e carimbo em UTC (gerador de PDF); "Períodos pagos: nenhum" ao lado de cobertura VIGENTE em empresa cancelada (lógica contratual); ordem alfabética dos detalhes do histórico; badges ausentes no regime legado; canal de contato em "Conta encerrada"/"Como aderir"; destaque do campo com erro ao registrar período pago; navegação por setas no sino; classes ABC só por tom no Pareto (a classe aparece na tooltip e na tabela).
- **Testes de layout na CI:** a CI não tinha cópia do Bootstrap (servia um CSS mínimo e um script vazio: modais não abriam, a landing bloqueava o substituto pelo SRI) nem as fontes Inter/JetBrains Mono (métricas mais largas do DejaVu Sans). O job `security-sqlite-browser` passou a instalar as fontes e a baixar Bootstrap 5.3.3 e Plotly 2.35.2 conferindo o hash SRI; sem cópia íntegra, a classe de layout é pulada com o motivo no log (não há como medir a grade sem a folha de estilo real). As demais suítes não mudaram.
- **Base de Conhecimento** na sidebar quebra em duas linhas quando o item está ativo (o ponto ocupa 18 px); é intencional para o ponto nunca colidir com o texto.

## 9. GitHub

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| Base | `main` em `0f4a53e9003452dc66c0322a0269a22f52a96f5f` |
| Branch | `claude/awesome-pascal-0ho42m` (branch designada desta sessão; nome sugerido `fix/nexo-correcao-overflow-responsividade-20261027` registrado, não usado) |
| Pull request | [#32 — NEXO: correção de cortes de informações, tabelas, gráficos e responsividade](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/32) (rascunho, pronto para revisão do proprietário) |
| SHA das correções de código | `093fbee` (último commit de código; os commits de documentação posteriores só tocam este relatório) |
| CI | `security-postgresql` e `security-sqlite-browser` verdes em `c0e0168` (812 testes, 0 pulados, os 18 testes de layout executados com Bootstrap, Plotly e Inter reais); e verdes de novo em `093fbee` (run 40606041025: 814 testes, 0 pulados, PostgreSQL 16 descartável com os três ensaios `status: ok`). |
| Merge | Não realizado: o PR fica em rascunho para o proprietário revisar; há incerteza sobre implantação automática no Render a partir da `main`, por isso nenhum merge foi feito e nenhum deploy manual foi executado. |
| Histórico | Sem rebase, sem amend após publicação, sem force push. |

Commits (em ordem cronológica):

| SHA | Mensagem |
|---|---|
| `cc43c7f` | fix(ui): tabelas sem coluna fixa, cartoes no celular, KPIs, sidebar, NexoBot e componentes |
| `885920d` | fix(ui): templates do admin e do cliente sem cortes, acessiveis e em pt-BR |
| `dd9180d` | fix(app): paginas de erro do NEXO, filtro de analises por empresa e e-mail no login |
| `7c22786` | test(ui): regressao de overflow, responsividade e acessibilidade em navegador |
| `70edde0` | fix(ui): cartoes sem vazamento de palavras longas, eixo compacto do Pareto e periodo que quebra |
| `5a777af` | test(ui): tolerancia de reticencias pela largura do grafico e referencia sem espacos |
| `f69d412` | fix(ui): revisao independente - botoes no celular, dropzone, Pareto, dica, modais e cabecalho do envio |
| `0771dd2` | test(ui): regressoes da revisao, pre-condicao do Bootstrap e copias integras da CDN na CI |
| `d209613` | docs(ui): rascunho do relatorio da auditoria e correcoes do frontend |
| `deccb46` | fix(app): pagina de erro resistente a falha do banco, filtro ABC e nome acessivel do envio |
| `7da0767` | test(ui): erro 500 com banco em falha, filtro ABC por teclado, nome do campo de arquivo e Plotly integro |
| `c0e0168` | docs(ui): achados da revisao independente (backend e acessibilidade) no inventario |
| `4654800` | fix(charts): Pareto no celular com o % acumulado no rotulo e linhas medidas pela fonte efetiva |
| `532cc23` | test(ui): tolerancia de reticencias pelos caracteres por linha reais do grafico |
| `35bfc10` | docs(ui): Pareto com fonte de reserva no inventario |
| `090c722` | fix(app): pagina de erro tambem com o banco fora do ar |
| `2a5da9e` | test(app): pagina de erro com todo context processor falhando (banco inacessivel) |
| `e279cac` | fix(charts): marcas redondas e compactas no eixo do faturamento do Pareto |
| `cae1d43` | docs(ui): banco fora do ar no inventario da revisao independente |
| `024dd46` | fix(charts): graficos nao colapsam ao redimensionar e o Pareto reavalia o modo |
| `4386497` | test(ui): redimensionamento do Pareto, sobreposicao vertical dos rotulos e SVG dentro da caixa |
| `093fbee` | docs(ui): graficos ao redimensionar no inventario da revisao independente |

## 10. Produção

Não foram alterados: Render, Supabase, banco real, credenciais, variáveis de ambiente, configurações de deploy ou migrações. Nenhum deploy manual foi feito. Os scripts de captura e os dados fictícios ficaram fora do repositório.
