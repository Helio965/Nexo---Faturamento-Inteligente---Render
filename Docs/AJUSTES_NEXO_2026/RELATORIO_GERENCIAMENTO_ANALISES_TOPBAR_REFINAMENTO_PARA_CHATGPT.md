# NEXO: Faturamento Inteligente — Relatório técnico para auditoria independente

## Gerenciamento de análises por empresa, topbar com desfoque gradual, refinamento de bordas e remoção da aba Base de Conhecimento

Documento preparado para ser auditado de forma independente (ChatGPT). Tudo o que está aqui foi executado em cópia descartável do código, com dados fictícios, sem acesso a produção. Nada foi inventado: cada número vem de um log ou de uma captura real citados no pacote de evidências.

## A. Identificação

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| Branch de trabalho | `claude/awesome-pascal-0ho42m` (branch designada desta sessão, recriada sobre a `main`; o nome sugerido `feature/nexo-gerenciamento-analises-topbar-refinamento` fica registrado, mas a sessão só publica na branch designada) |
| SHA inicial (`main`) | `264f713b387f25e88e6e645c53788e0f9e0b9a8a` (merge do PR #32), confirmado antes de iniciar |
| SHA final | «SHA_FINAL» |
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
Título "Gerenciar análises", subtítulo "Selecione uma empresa para consultar e gerenciar suas análises.", trilha "Análises › Gerenciar análises", campo de busca (`#buscaGerenciar`, filtra por nome fantasia, razão social e CNPJ, ignorando acentos, com região `aria-live` e "Limpar busca") e uma grade responsiva (`.empresa-grid`, colunas de ≥ 320 px) de cartões-link (`.empresa-card`): cubo da marca, nome fantasia, razão social, CNPJ formatado, ID, contagem de análises, plano e, quando houver, status Suspensa/Cancelada. Hover e foco elevam o cartão e acendem a borda (`:focus-visible` com anel), Enter abre. Só empresas ativas (fora da lixeira) aparecem; a lixeira tem o próprio fluxo. Nenhuma lixeira de análise nesta tela.

### 3. Exclusão de análises (`/admin/analises/gerenciar/<id_empresa>`)
Cartão da empresa selecionada (mesmo desenho, com marca de seleção) e tabela só com as análises dela (período, tipo, quinzena, status, uploads, criação, publicado, ações "Abrir" e "Excluir"). "Excluir" abre o modal `#confirmExcluirAnalise` ("Excluir análise?") com empresa, período, tipo e identificador da análise, o aviso de que a exclusão é definitiva e os botões **Cancelar** / **Confirmar exclusão** (vermelho na identidade). O formulário envia `POST /admin/analises/gerenciar/<id_empresa>/excluir/<id_analise>` com CSRF e `confirmar=sim`. No backend (`admin.analise_excluir`): administrador obrigatório, empresa ativa obrigatória, a análise precisa pertencer à empresa da URL (senão 404, com aviso no log), confirmação obrigatória (senão 400), uma análise por requisição (não existe rota sem id nem exclusão em massa). `_excluir_analise()` passou a apagar primeiro no banco (mídias `db:` na mesma transação) e só depois do commit remover arquivos legados do disco; falha no banco faz rollback e devolve a mensagem "Nada foi alterado". Depois da exclusão o administrador volta à mesma empresa, com mensagem de sucesso, as demais análises intactas e o link "Voltar à seleção de empresas".

### 4. Reorganização do botão Abrir
Coluna "Ações" com `width: 1%` e `white-space: nowrap` (ocupa só o necessário) e botão `btn-abrir` compacto (5 × 11 px, 0,82 rem, ícone + texto, foco visível). Nas telas ≤ 1440 px as células respiram 10 px nas laterais (16 px nas pontas) e o nome da empresa tem mínimo de 170 px: a listagem de 9 colunas passou a caber inteira a 1366 px, sem rolagem horizontal e sem esconder coluna. No celular continua o modo cartões; a célula de ações volta a ser um bloco normal (um primeiro ensaio mostrou o rótulo "Ações" e os botões quebrando letra por letra nos cartões, corrigido antes da publicação).

### 5. Blur gradual da topbar
O desfoque saiu do próprio `.topbar` e passou para duas camadas decorativas (`::before` e `::after`, `pointer-events: none`, `z-index: -1`): a forte (`blur(26px) saturate(160%)` + véu escuro) é mascarada por um degradê vertical (100 % no topo → 6 % na base) e a suave (`blur(8px) saturate(130%)` + tinta leve) cobre toda a altura. Resultado: topo mais desfocado e mais escuro (protege título, sino e usuário), base mais translúcida, transição contínua sem degraus. Um `backdrop-filter` no pai limitaria o que as camadas "enxergam" e cortaria o menu do sino, por isso foi retirado. Fallbacks: `@supports not (backdrop-filter)` e `prefers-reduced-transparency: reduce` usam um único degradê quase opaco sem camadas; nada depende de animação.

### 6. Aplicação global do cabeçalho
A topbar é o mesmo componente de `base.html` em todas as páginas autenticadas; o `max-width: 1440px` foi removido para a faixa ir do limite da sidebar até a borda direita da área principal em qualquer largura (no celular, de margem a margem, com o botão do menu, o sino e o avatar). O menu do sino continua acima do cabeçalho e dentro da tela.

### 7. Refinamento das bordas
`.nexo-table` em `border-collapse: separate` (spacing 0): as divisórias da primeira e da última célula (e do cabeçalho) terminam num degradê com recuo de 18 px antes das bordas arredondadas; o realce ao passar o mouse e a linha em foco passam a pintar as células com pontas arredondadas (12 px) e o traço roxo acompanha o canto, no lugar da barra reta; cabeçalhos/rodapés de cartões, dica de rolagem, marca e rodapé da sidebar e modais usam divisórias com recuo de 24 px. O modo cartões não é afetado. Nenhum `overflow: hidden` novo.

### 8. Remoção da aba Base de Conhecimento
O item saiu da sidebar administrativa (link, ícone e indicador). As rotas `/admin/guia*` (CMS) continuam existindo, sem link no menu, porque o Guia do cliente e o NexoBot leem os mesmos tópicos (fonte única) e os testes do NexoBot/identidade usam essas páginas; nenhum registro foi apagado e nenhuma migração foi criada. Referências atualizadas: `base.html`, `Docs/RELATORIO_TECNICO.md`, teste do indicador da sidebar (passou a usar "Análises" e "Enviar relatórios") e lista de páginas do teste de overflow; novo teste garante que o menu administrativo é exatamente Dashboard, Empresas, Contratos, Lixeira, Análises e Suporte.


## D. Arquivos modificados

«ARQUIVOS»

## E. Testes

«TESTES»

## F. Evidências

«EVIDENCIAS»

## G. Segurança

- Só administradores: as três rotas usam `admin_required` (login obrigatório + `is_admin`, senão 403); CLIENTE recebe 403 e anônimo vai para o login (testado).
- Só POST exclui: GET na rota de exclusão devolve 405; a listagem e a seleção são GET sem efeito.
- CSRF global do Flask-WTF: sem token ou com token inválido o POST devolve 400 e nada muda (testado).
- Confirmação explícita: além do modal, o formulário envia `confirmar=sim`; sem o campo o backend devolve 400.
- Pertencimento verificado no backend: `analise.id_empresa == id_empresa` da URL; análise de outra empresa, inexistente ou de empresa na lixeira → 404 sem tocar em nada (testado com a análise da outra empresa).
- Uma análise por requisição; não existe rota de exclusão sem identificador nem seleção múltipla (testado: `/excluir/` e `/excluir` → 404).
- Integridade: cascata ORM nos filhos (uploads, indicador, relatório, Curva ABC) numa única transação; arquivos em disco só saem depois do commit; falha simulada no commit mantém análise, filhos e arquivo (testado) e informa "Nada foi alterado".
- A exclusão é **definitiva** (sem lixeira de análises); o modal e a página dizem isso explicitamente.
- Nenhuma regra comercial ou contratual foi alterada; a lixeira de empresas e a exclusão permanente de empresas não mudaram.


## H. GitHub

«GITHUB»

## I. Pendências

«PENDENCIAS»

## J. Parecer final

«PARECER»
