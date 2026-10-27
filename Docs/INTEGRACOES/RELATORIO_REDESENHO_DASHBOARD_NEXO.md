# Relatório: redesenho premium do dashboard NEXO (vidro, navegação e gráficos)

Reformulação **visual** do painel autenticado (ADMIN e CLIENTE): fundo, sidebar, topbar, cartões, KPIs, tabelas e gráficos.

**Escopo:**
- Somente apresentação: CSS, templates e o JavaScript dos gráficos e do shell.
- Nenhuma regra de negócio, autenticação, permissão, fluxo de suspensão/cancelamento ou lógica contratual foi alterada.
- Login, telas de acesso e landing não mudam. Login, recuperação de senha, landing e "Como aderir" foram comparados pixel a pixel com a `main` anterior ao redesign (`e2b76d8`), sem diferença visível. O PR #29 tinha levado ao login e às telas de acesso uma mudança de botões e campos; o PR #30 a desfez.

> **Atenção (já corrigido na `main`):** o PR #29 foi mesclado (`f9c2178`, 18:35 UTC) com os modais de confirmação (lixeira e exclusão) bloqueados: ficavam sob o véu do Bootstrap e nenhum botão respondia; só o Esc fechava. O PR #30, mesclado em `19389b8` (21:15 UTC), corrige esse defeito e os demais achados de regressão da seção F. Se o Auto-Deploy estiver ativo, a produção pode ter ficado com o defeito nesse intervalo.

---

## A. Identificação

| Item | Valor |
|---|---|
| Data | 26/10/2026 |
| Repositório | `https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render` |
| Branch | `claude/awesome-pascal-0ho42m`, reiniciada a partir da `main` a cada PR mesclado: `e2b76d8` (PR #28), `f9c2178` (PR #29) e `19389b8` (PR #30) |
| Pull Requests | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/29 (redesign, mesclado em `f9c2178`), https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/30 (correções das revisões, mesclado em `19389b8`) e um PR só de documentação com este relatório e as evidências |
| Commits | PR #29: `73d7dfb` (redesign) · `7950dc7` (exemplo de formato sem o valor-sentinela dos testes) · `f4cc45b` (ajustes da revisão visual e de acessibilidade). PR #30: `b8cf8f5` (correções da revisão de regressões) · `247b87b` (correções da revisão final). PR de documentação: commit deste relatório |

## B. Referências analisadas (vídeos enviados)

Os dois vídeos ("Glassy Dashboard V2" e "Dashboard V15") foram decompostos em quadros e usados só como inspiração, sem cópia de layout, textos ou ícones.

| Padrão observado | Como foi adaptado à NEXO |
|---|---|
| Fundo fotográfico desfocado atrás de painéis de vidro | Paisagem própria de crepúsculo, desfocada, com véu escuro e tom roxo da marca |
| Trilho de navegação com ícones em círculos; ativo preenchido | Sidebar em pílulas: ícone num contêiner arredondado; ativo com ícone em gradiente roxo, fundo translúcido e brilho |
| Topbar flutuante em pílula | Topbar em vidro, flutuante, com a área (Administração / Minha empresa) acima do título |
| Cartões grandes e arredondados, KPI com ícone num chip | Cartões de vidro com brilho fino no topo; KPI com chip de ícone, cor de destaque e número maior |
| Gráficos limpos, barras arredondadas, rótulo de valor | Tema Plotly único, barras arredondadas, rótulos de valor, rosca com total no centro |

## C. Auditoria antes de alterar

- **Shell:** `templates/base.html` (sidebar, topbar, sino, flashes, NexoBot e helpers Plotly) e `static/css/nexo.css` (design system).
- **Dashboards:** `templates/admin/dashboard.html` (3 gráficos estáticos) e `templates/cliente/dashboard.html` (4 gráficos), mais `templates/cliente/analise.html` (2 gráficos).
- **Restrições dos testes respeitadas:**
  - o cubo da marca não pode ter fundo, moldura, sombra ou recorte;
  - a marcação exata da sidebar (`<div class="sidebar-brand">` … `<nav class="sidebar-nav">`) não muda;
  - a gaveta móvel fica em `left: 0` quando aberta;
  - `const dashboardData = …;` continua numa linha;
  - nenhum dado de período não pago aparece no HTML;
  - o bloco CSS do NexoBot só troca o gradiente do botão de abrir pelo token `--grad-cta` (contraste AA, sem hex novo); as regras que escondem o NexoBot com a gaveta aberta ficam fora do bloco, e os testes do widget continuam passando;
  - nenhum recurso externo novo é carregado.
- **Problemas visuais já existentes, encontrados e corrigidos:**
  - O comparativo Compras × Vendas nascia em zero e animava sem recalcular o eixo. O eixo ficava preso em [0, 1] ("R$ 1"), com as duas barras cortadas.
  - O valor do Indicador de Pressão de Estoque estourava o cartão estreito.
  - Os eixos e tooltips formatavam números no padrão americano (`1,234.56`).
  - A mescla rasa do tema fazia os gráficos que passavam eixo próprio perderem a grade escura.
  - Os gráficos ficavam espremidos entre 992 e 1200 px.
  - Com análises cadastradas e nenhuma empresa fora da lixeira, a caixa "Análises por status" do admin aparecia vazia (o script dos gráficos só rodava com empresas).

## D. O que mudou

### D.1 Fundo do painel (origem e licença)

- **Arte:** paisagem de crepúsculo estilizada (céu índigo/violeta, brilho no horizonte, cordilheiras em camadas com névoa e lago com reflexo). É **gerada por código** em `scripts/gerar_fundo_dashboard.py`, com semente fixa, e foi salva em `static/img/painel/nexo-fundo-crepusculo.jpg` (1920×1080, JPEG progressivo, 39 KB).
- **Licença:** arte original do projeto. **Não usa foto de terceiros nem exige licença ou atribuição.** Bancos de imagem com licença livre (como o Unsplash) foram considerados, mas a geração própria elimina dependência de licença, download externo e risco de marca ou pessoa identificável.
- **Tratamento:**
  - desfoque já na imagem;
  - véu escuro em degradê e tom roxo da marca em cima (`.app-shell::before`);
  - só no shell autenticado (login e landing não mudam);
  - fixo atrás do conteúdo, sem rolar.

### D.2 Shell, sidebar e topbar

- **Sidebar:** flutuante em vidro.
  - Itens em pílula, com o ícone num contêiner de 36 px.
  - Item ativo com fundo roxo translúcido, borda luminosa, ícone em gradiente, ponto de brilho e `aria-current="page"`.
  - Seções Administração / Minha empresa com filete.
  - Bloco **Sessão ativa** (avatar, nome, perfil e indicador verde) acima do **Sair**.
- **Gaveta móvel (< 992 px):**
  - entra rente à borda esquerda, sobre um véu desfocado;
  - fechada, sai da ordem de Tab;
  - aberta, recebe o foco e deixa o conteúdo atrás inerte;
  - tem um botão **Fechar** visível ao lado dela, alcançável por toque, Tab e leitor de tela;
  - o botão Fechar, o véu ou o Escape fecham a gaveta e devolvem o foco ao botão do menu;
  - o NexoBot some enquanto ela está aberta.
- **Topbar:** flutuante em vidro, alinhada ao conteúdo; chip do usuário em pílula; sino redondo com o número de não lidas anunciado ao leitor de tela.

### D.3 Cartões, KPIs, tabelas e avisos

- **Vidro:** cartões, tabelas, banners, avisos, toasts e barra de auditoria usam tokens próprios (`--glass`, `--glass-strong`, `--glass-blur`…).
- **Botões e campos:** o visual de vidro (cantos de 14 px, campos translúcidos, gradiente de CTA mais escuro, AA) vale só dentro do painel (`.app-shell`). Login e telas de acesso mantêm o estilo da `main` anterior ao redesign (`e2b76d8`).
- **Modais:** o shell não cria contexto de empilhamento, então as confirmações do Bootstrap (lixeira, exclusão) ficam acima do véu e respondem ao clique.
- **Fallbacks:** fundo opaco quando o navegador não tem `backdrop-filter` ou quando o sistema pede transparência reduzida.
- **KPIs:**
  - cor de destaque derivada do ícone (verde, âmbar, vermelho, azul ou roxo) e filete de luz no topo;
  - número maior, sempre numa linha (a fonte só diminui quando o valor não cabe);
  - elevação discreta no hover.
- **Tabelas:**
  - vidro mais opaco e datas sem quebra;
  - quando a tabela rola na horizontal, a coluna de ações fica fixa à direita, desde que ocupe no máximo metade da largura da tabela;
  - em Empresas no celular, onde ela ocuparia quase toda a largura, a coluna não é fixada: a borda direita esmaece enquanto ainda há colunas para rolar;
  - navegando pelo teclado, o esmaecimento some e o botão focado entra inteiro na área visível;
  - a linha não mostra mais cursor de link (só os botões dela são clicáveis).
- **Grade:** o terceiro KPI ocupa a linha toda quando eles aparecem dois a dois (576–1199 px), e a Síntese executiva cabe em três colunas a partir de cerca de 700 px.
- **Cabeçalhos de seção:** um degrau acima dos títulos de cartão, com ícone em contêiner.
- **Links:** no lilás da marca.

### D.4 Gráficos (Plotly 2.35.2, sem dependência nova)

- **Tema único (`NEXO.plotlyLayout`):**
  - grade pontilhada suave, eixos limpos e números em pt-BR (`separators: ',.'`);
  - barras com cantos arredondados (`barcornerradius`);
  - tooltip escura com borda lilás e legenda horizontal;
  - no hover unificado, linha-guia fina e pontilhada em lilás (sem a barra branca padrão do Plotly);
  - a toolbar do Plotly some quando os eixos são fixos;
  - a mescla de eixos, tooltip e legenda vai um nível abaixo (fonte, ticks, título): ajustes locais não apagam mais a cor do tema.
- **Admin:**
  - rosca de status com o total no centro e a contagem na legenda;
  - barras por plano e por status da análise com o valor no topo;
  - eixo só com inteiros;
  - status da análise em ordem de leitura.
- **Cliente:**
  - comparativo com o eixo correto e rótulos de valor;
  - indicador de pressão que se ajusta ao cartão, inclusive ao redimensionar a janela;
  - Pareto com a classe ABC no tom da barra, referência de 80%, legenda fora do gráfico e nomes longos encurtados só no eixo;
  - linha temporal suave com área em degradê sob Vendas, losango em Compras e tooltip sem repetir a data;
  - Compras × Vendas da página de análise na mesma ordem, cores e rótulos da Visão Geral.
- **Cores coerentes:**
  - Vendas em azul e Compras em âmbar nos dois comparativos Compras × Vendas e no histórico. É um par legível também para daltonismo vermelho-verde.
  - O Pareto mantém o roxo da marca, com o tom indicando a classe ABC.
- **Histórico:** a faixa do eixo considera meses distintos. Duas análises quinzenais no mesmo mês não deixam mais um vão vazio à direita.
- **Movimento:** as animações respeitam "reduzir movimento" do sistema, e os gráficos entram com um surgimento curto.

### D.5 Acessibilidade

- **Contraste AA:** textos secundários, avisos, contador do sino, botões de ação e botão do NexoBot foram recalculados sobre o pior trecho do fundo (faixa clara do horizonte).
  - Os avisos com fundo próprio (Enviar relatórios, Detalhe do chamado e Base de Conhecimento) ganharam a base de vidro.
  - O texto solto sobre o fundo ("Nenhum chamado neste status") ficou claro e com sombra.
- **Foco visível:** navegação, botões, sino, itens do sino e acordeão do Guia. Ao voltar para o desktop com o foco no Fechar da gaveta, o foco vai para o item ativo da sidebar.
- **ARIA:** `aria-expanded`/`aria-controls` no botão do menu, `aria-current="page"` no item ativo, contador do sino anunciado no rótulo do botão.
- **Movimento reduzido:** cobre cartões, botões, toasts e o pulso do contador.

## E. Arquivos

| Arquivo | Alteração |
|---|---|
| `static/css/nexo.css` | Tokens de vidro, shell, sidebar, topbar, cartões, KPIs, tabelas, avisos, acessibilidade, responsivo e fallbacks |
| `templates/base.html` | Bloco Sessão ativa, botão Fechar da gaveta, área na topbar, acessibilidade da gaveta e do sino, ajuste de KPIs/tabelas e tema Plotly (`plotlyLayout`, `plotParetoAbc`, `plotLinhaTemporal`) |
| `templates/admin/dashboard.html` | Visual dos 3 gráficos e grade responsiva; "Análises por status" desenhado também quando há análises e nenhuma empresa fora da lixeira (mesmos dados) |
| `templates/cliente/dashboard.html` | Eixo do comparativo, ajuste do indicador (também ao redimensionar), cores, movimento reduzido e grade responsiva (mesmos dados) |
| `templates/cliente/analise.html` | Compras × Vendas com a ordem, as cores e os rótulos da Visão Geral (mesmos dados) |
| `templates/cliente/upload.html`, `templates/cliente/ticket_detalhe.html`, `templates/admin/guia.html` | Aviso com fundo próprio sobre a base de vidro (contraste) |
| `templates/admin/tickets.html` | Texto "Nenhum chamado neste status" claro sobre o fundo (contraste) |
| `static/img/painel/nexo-fundo-crepusculo.jpg` | Fundo novo (arte original) |
| `scripts/gerar_fundo_dashboard.py` | Gerador do fundo |
| `Docs/INTEGRACOES/RELATORIO_REDESENHO_DASHBOARD_NEXO.md` e `evidencias_redesenho_dashboard/` | Este relatório e as capturas |

## F. Validação

- **Capturas reais** (Chromium, Plotly 2.35.2 e Bootstrap servidos localmente, dados fictícios):
  - dashboards admin e cliente em 1440, 1024 e 390 px, com a gaveta aberta;
  - Empresas e Análise.
  - Resultado: nenhum estouro horizontal e nenhum erro de JavaScript em nenhuma delas.
- **Verificações no navegador:**
  - modal "Mover para a lixeira" em 1440 e 390 px: o botão Cancelar é o elemento no topo e fecha o modal;
  - gaveta: o botão Fechar fica visível sobre o véu, recebe o foco com Shift+Tab, fecha a gaveta e devolve o foco ao menu; no desktop ele não aparece;
  - ações visíveis por inteiro (coluna fixa):
    - Empresas em 820, 1024, 1280, 1366, 1440 e 1600 px;
    - Análises em 390 e 1024 px;
    - Histórico e Contratos em 390 px;
  - em Empresas a 390 px a coluna não é fixada e a borda esmaece; com Tab, cada botão fica inteiro na vista e sem máscara;
  - histórico com dois rótulos iguais (quinzenas): faixa do eixo `[-0.25, 2.25]`, sem vão;
  - gaveta aberta e janela ampliada para o desktop: gaveta fechada, conteúdo sem inert e foco no item ativo;
  - hover da linha temporal: tooltip `02/2026 · Vendas: R$ 196.750,00 · Compras: R$ 172.300,00`;
  - legendas com a cor do tema (`#ece9f8`) nos gráficos do admin e do cliente;
  - indicador de pressão de 1024 para 1300 px: o valor continua dentro do cartão;
  - login, recuperação de senha, landing e "Como aderir" (1440 × 2200 px): idênticos à `main` anterior ao redesign (`e2b76d8`), salvo ruído de antialiasing de no máximo 2/255 em 96 pixels de canto do campo focado.
- **Evidências** em `Docs/INTEGRACOES/evidencias_redesenho_dashboard/`:
  - `antes_depois_admin.jpg` e `antes_depois_cliente.jpg`: primeira tela, `main` anterior ao redesign (`e2b76d8`) × versão final;
  - `depois_graficos_cliente.jpg`;
  - `antes_depois_celular.jpg`: dashboard do admin e menu do cliente no celular (390 px).
- **Testes locais** (mesmo ambiente sintético do CI, sem credenciais reais):
  - suíte completa no código final (`247b87b`): **794 testes, OK** (499 s; SQLite, PostgreSQL local e navegador Chromium);
  - antes, em `b8cf8f5`: 794 testes OK na suíte completa (árvore sem o esmaecimento das tabelas) e 199 testes sensíveis à interface OK no commit em si. São eles: contratos no navegador, identidade visual, NexoBot no navegador e na interface, portal e gestão de contratos, landing e deploy.
- **CI (GitHub Actions):**
  - PR #29: verde no head `f4cc45b` (security-postgresql e security-sqlite-browser);
  - PR #30: verde em `b8cf8f5` (security-postgresql e security-sqlite-browser);
  - `main` após o merge do PR #30 (`19389b8`, mesma árvore de `247b87b`): **verde** (security-postgresql e security-sqlite-browser);
  - uma primeira execução em `247b87b` foi cancelada pelo limite de 20 min do job: a instalação do Chrome no runner levou 12 min, e a suíte foi interrompida no meio. Não houve falha de teste.
- **Revisão independente:**
  - três revisores (visual, acessibilidade WCAG 2.2 AA e regressões) e um verificador por revisor, tentando refutar cada achado;
  - 30 achados (10 visuais, 12 de acessibilidade e 8 de regressão), todos confirmados e todos aplicados;
  - o mais grave veio do próprio redesign e chegou à `main` no merge do PR #29 (`f9c2178`): os modais de confirmação (lixeira, exclusão) ficavam sob o véu do Bootstrap e não respondiam ao clique. A correção está em `b8cf8f5` (PR #30);
  - outros achados de regressão corrigidos:
    - coluna de ações fixa cobrindo os dados;
    - botão do menu inacessível com a gaveta aberta;
    - linha-guia branca no hover;
    - indicador estourando ao redimensionar;
    - desfoque redundante nos botões das tabelas;
    - cor da legenda perdida;
    - estilo de botões e campos vazando para o login.
- **Revisão final** (correção do diff do PR #30 e checagem dos fatos deste relatório, cada uma com verificador adversarial):
  - **Código:** 3 defeitos confirmados e corrigidos:
    - o limite de 30% escondia a coluna de ações em notebooks; agora o limite é metade da largura;
    - o esmaecimento escondia o botão focado pelo teclado;
    - o histórico deixava um vão com quinzenas no mesmo mês.
  - **Relatório:** 9 afirmações corrigidas:
    - estado da `main` e da produção;
    - referência da `main` nas comparações;
    - bloco do NexoBot;
    - cores dos gráficos;
    - alcance do Plotly;
    - limites da tabela de Empresas;
    - mudança no gráfico do admin;
    - itens de acessibilidade aplicados só em parte (agora completos).

## G. Produção

- Nada foi executado em produção: nenhum deploy manual, migração, variável ou dado.
- **Auto-Deploy:** o proprietário informou que está ativo na `main`, enquanto o `render.yaml` declara `autoDeployTrigger: 'off'`; o painel não é verificável daqui. Se estiver ativo, cada merge publica a `main` inteira.
- **O que pode ter ido ao ar:** entre o merge do PR #29 (18:35 UTC) e o do PR #30 (21:15 UTC), a `main` tinha os modais de confirmação bloqueados e o login alterado. Com o Auto-Deploy ativo, o deploy de `19389b8` corrige os dois.
- **Migrações:** a mudança visual não exige nenhuma. Em produção, continua valendo o incidente do login (HTTP 500 até a migração `e4c004a26b01` no Supabase), tratado à parte.
- **Conferir no painel do Render** qual commit está no ar.

## H. Pendências e próximos refinamentos possíveis

- **Contraste do botão do login:** o texto branco sobre o tom claro do gradiente atual (`#a855f7`) fica perto de 4:1. O painel já usa o gradiente mais escuro (`--grad-cta`, AA); levar o mesmo ao login é uma linha de CSS, mas mexe na tela de acesso, que ficou fora deste escopo.
- **Tabela de Empresas:** com 8 colunas e 4 ações, rola na horizontal até cerca de 1740 px (com os dados de teste).
  - A partir de ~700 px de janela a coluna de ações fica fixa à direita e pode cobrir parte do status e do e-mail até a rolagem.
  - No celular, as ações ficam no fim da rolagem, com a borda esmaecida como indicação.
  - Um menu compacto de ações seria uma decisão de UX à parte.
- **Quinzenas no histórico:** as duas análises quinzenais do mesmo mês recebem o mesmo rótulo (`MM/AAAA`) e caem no mesmo ponto do gráfico (já era assim). Rótulos únicos exigem mudar o backend, fora deste escopo visual.

- **Light mode:** os vídeos de referência têm variante clara; a NEXO segue no tema escuro, como pedido.
- **Telas de formulário** (contratos, upload, guia) herdam o vidro, mas não tiveram ajuste fino de layout.
- **Gráficos do admin:** seguem estáticos (sem tooltip) por decisão anterior de não capturar o toque no celular. Liberar o hover é uma troca simples se desejado.
- **Plotly:** é carregado em todas as páginas que usam `base.html`, inclusive login e "Como aderir" (já era assim). Carregar só onde há gráfico reduziria o peso das demais.
