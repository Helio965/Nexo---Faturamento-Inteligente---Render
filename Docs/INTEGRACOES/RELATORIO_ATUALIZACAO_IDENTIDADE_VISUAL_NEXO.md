# Relatório: atualização da identidade visual do NEXO (cubo transparente)

Substituição da marca antiga (imagem com cubo, moldura e nome embutido, e monograma "N" da landing) pelo símbolo oficial do cubo roxo em PNG transparente, em todo o sistema. Atividade exclusivamente visual.

**Resultado: todas as ocorrências da marca antiga foram substituídas; CI aprovada; integrada à `main` pelo proprietário (merge `6abc96c`, seção G). A publicação em produção não foi confirmada.**

---

## A. Identificação

| Item | Valor |
|---|---|
| Data | 26/10/2026 |
| Repositório | `https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render` |
| Branch | `claude/awesome-pascal-0ho42m`. O nome sugerido (`feature/nexo-identidade-cubo-transparente`) não foi usado porque esta sessão só tem autorização de push para a branch designada pelo ambiente. A branch foi reiniciada a partir da `main` atual, porque o PR anterior dela (#25) já estava integrado |
| Commit inicial (`main`) | `fcf43fabafe3345004bcb2d936052d245964adbb` (merge do PR #25). Templates e arquivos estáticos não mudavam desde `ff8c2d8` |
| Commit final da implementação | `b744c933e878f5b1a9f486024252a72bd7519132` (feat(ui): atualizar identidade visual NEXO com cubo transparente). Este relatório vai no commit seguinte, que não consegue citar o próprio SHA |
| Arquivos recebidos | Duas imagens PNG do cubo (com e sem brilho). A captura de referência das telas atuais (imagem A, `f694f042-….png`) não chegou anexada; serviu como referência a captura redigida já versionada em `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/03_telas_atuais_marca_portal_admin_login_redigida.png`, com as mesmas três telas. Nenhuma captura do sistema real foi publicada |

## B. Diagnóstico

A arte antiga `static/img/nexo-logo.jpeg` (1024×1024, JPEG, sem transparência) trazia, numa só imagem, o cubo, um círculo branco, o fundo roxo-escuro e o texto "NEXO - FATURAMENTO INTELIGENTE". Ao lado ou abaixo dela, o sistema escrevia de novo "NEXO" e "Faturamento Inteligente", o que causava redundância. Os contêineres ainda pintavam um quadrado escuro (`#10051a`) com sombra e cantos arredondados. Na landing, a marca era um quadrado em gradiente roxo com a letra "N".

Pontos que usavam a marca antiga (busca completa em templates, CSS, JS, Python, e-mails, PDF e ferramentas):

| Local | Componente | Marca antiga |
|---|---|---|
| `templates/auth/login.html` | `.auth-logo` | `nexo-logo.jpeg` |
| `templates/auth/recuperar_senha.html` | `.auth-logo` | `nexo-logo.jpeg` |
| `templates/auth/resetar_senha.html` | `.auth-logo` | `nexo-logo.jpeg` |
| `templates/auth/primeiro_acesso.html` | `.auth-logo` | `nexo-logo.jpeg` |
| `templates/auth/primeiro_acesso_token.html` | `.auth-logo` | `nexo-logo.jpeg` |
| `templates/como_aderir.html` | `.auth-logo` | `nexo-logo.jpeg` |
| `templates/base.html` (sidebar do ADMIN e do CLIENTE) | `.sidebar-brand .brand-logo` | `nexo-logo.jpeg` |
| `templates/landing.html`, cabeçalho | `.brand .brand-mark` | quadrado com "N" |
| `templates/landing.html`, rodapé | `.footer-brand .brand-mark` | quadrado com "N" |

Sem marca gráfica (mantidos): `templates/auth/_layout.html` só estrutura a página; os e-mails (`templates/emails/_base.html`) usam o nome "NEXO" em texto sobre faixa em gradiente, sem imagem nem monograma; o PDF não usa logotipo; o NexoBot usa ícone de robô; o vídeo promocional desenha o cubo em SVG próprio (`tools/nexo-motion`) e não foi alterado; não há favicon nem metadados de imagem; o `user-avatar` (inicial do usuário) não é marca e não foi tocado. Uma varredura independente de completude (seção F) confirmou que esses 9 pontos eram toda a marca gráfica servida pela aplicação.

## C. Alterações

**Login** (`templates/auth/login.html`, `static/css/nexo.css`). O cubo **com brilho** (`nexo-cubo-brilho.png`) fica centralizado acima do nome, com 104 px de altura e largura automática pela proporção. Até 575 px de largura, o cubo passa a 88 px e os espaçamentos do cabeçalho do cartão diminuem, para o login continuar cabendo em 375×667 sem rolagem. O contêiner `.auth-logo` deixou de ter fundo `#10051a`, cantos arredondados, sombra e `overflow: hidden`: o cartão aparece pelas áreas transparentes, e o brilho do próprio arquivo não é cortado. Logo abaixo, em texto: "NEXO" e, em linha própria, "Faturamento Inteligente"; depois "Acesso ao Portal", "Entre com seu e-mail e senha" e os campos. A autenticação não mudou.

**ADMIN** (`templates/base.html`, `static/css/nexo.css`). O cubo **sem brilho** (`nexo-cubo-transparente.png`) fica à esquerda, com 42 px de altura, e "NEXO" com o subtítulo à direita. O `.brand-logo` não pinta mais o quadrado escuro nem aplica sombra ou recorte. Largura da sidebar, navegação e responsividade não mudaram. A imagem ganhou altura explícita em pixels: com o PNG em retrato (253×279), `height: 100%` dentro do grid fazia o cubo vazar 4 px da caixa (defeito encontrado pelo teste em navegador e corrigido antes da publicação).

**CLIENTE**. O portal usa o mesmo `base.html`, e a troca vale em todas as telas. Verificado em Visão Geral, Histórico, Análise, Enviar relatórios, Guia e Suporte (teste HTTP e capturas), e no menu móvel aberto. Dados, gráficos, indicadores e permissões não mudaram.

**Landing page** (`templates/landing.html`, `static/css/landing.css`). O quadrado roxo com a letra "N" (`<span class="brand-mark">N</span>`) foi substituído por `<img class="brand-symbol">` com o cubo sem brilho: 40 px de altura, 34 px até 640 px de largura. A regra antiga `.brand-mark` (gradiente, cantos e sombra) foi removida. O link continua com `aria-label="NEXO Faturamento Inteligente, início"`. Menu, links, botões, vídeo, planos, gráficos e responsividade não mudaram.

**Rodapé da landing.** A mesma assinatura do cabeçalho: cubo, "NEXO" e "Faturamento Inteligente".

**Outras páginas de autenticação.** Recuperar senha, resetar senha, primeiro acesso, primeiro acesso por token e "Como obter acesso" passaram a usar o cubo com brilho, na mesma estrutura do login. Nenhum cubo foi acrescentado onde antes não havia marca gráfica.

**Acessibilidade.** Em todas as assinaturas, o nome já está em texto ao lado (ou no `aria-label` do link), então a imagem é decorativa (`alt=""`). Isso evita que leitores de tela leiam "NEXO" duas vezes. A arte antiga tinha `alt="Logo NEXO"`/`alt="NEXO"` e o texto ao lado, e por isso era lida em dobro. As imagens têm `width="253" height="279"` para o navegador reservar o espaço (sem salto de layout) e `decoding="async"`. A navegação por teclado não mudou.

**Arte antiga.** `static/img/nexo-logo.jpeg` foi removida do repositório, porque ficou sem uso e o proprietário pediu que nenhuma tela use mais a arte com o nome embutido. Ela continua no histórico do Git e como insumo `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/02_logo_cubo_com_texto.jpg`. O README do `tools/nexo-motion`, que a citava como referência do cubo animado, ganhou uma nota. Os inventários históricos de `Docs/` que a listam foram mantidos como registro de época.

## D. Arquivos

| Arquivo | Situação | Alteração |
|---|---|---|
| `static/img/nexo-cubo-brilho.png` | Criado | Cubo com brilho, idêntico ao recebido |
| `static/img/nexo-cubo-transparente.png` | Criado | Cubo sem brilho, idêntico ao recebido |
| `static/img/nexo-logo.jpeg` | Removido | Arte antiga com nome embutido, sem uso |
| `templates/auth/login.html` | Modificado (CRLF preservado) | Cubo com brilho |
| `templates/auth/recuperar_senha.html` | Modificado (CRLF) | Cubo com brilho |
| `templates/auth/resetar_senha.html` | Modificado (CRLF) | Cubo com brilho |
| `templates/auth/primeiro_acesso.html` | Modificado (CRLF) | Cubo com brilho |
| `templates/auth/primeiro_acesso_token.html` | Modificado (CRLF) | Cubo com brilho |
| `templates/como_aderir.html` | Modificado (CRLF) | Cubo com brilho |
| `templates/base.html` | Modificado | Cubo sem brilho na sidebar |
| `templates/landing.html` | Modificado (CRLF) | Cubo sem brilho no cabeçalho e no rodapé |
| `static/css/nexo.css` | Modificado | `.auth-logo`, `.auth-logo img`, `.auth-eyebrow`, `.brand-logo`, `.brand-logo img` e regras móveis do cartão de acesso (`.auth-brand`, `.auth-logo img`) |
| `static/css/landing.css` | Modificado (CRLF) | `.brand-mark` substituído por `.brand-symbol` (desktop e ≤640 px) |
| `tests/test_identidade_visual.py` | Criado | 11 testes (arquivos, HTTP e navegador) |
| `tools/nexo-motion/README.md` | Modificado | Nota sobre o novo símbolo |
| `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/README.md` | Modificado | Registro de que o pedido da logo foi atendido |
| `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md` | Modificado | Situação da identidade visual (escopo da `NEXO-AJ-01`) e histórico na versão 6 |
| `Docs/INTEGRACOES/RELATORIO_ATUALIZACAO_IDENTIDADE_VISUAL_NEXO.md` e `Docs/INTEGRACOES/evidencias_identidade_visual/*.png` | Criados | Este relatório e as pranchas de evidência |

Cada template mudou só na linha da imagem: 1 linha por arquivo, 2 na landing.

## E. Imagens

| Arquivo | Uso | Formato | Dimensões | Transparência | Tamanho | SHA-256 |
|---|---|---|---|---|---|---|
| `static/img/nexo-cubo-brilho.png` | Login e demais telas de acesso | PNG RGBA | 253 × 279 | Cantos com alfa 0; 54,2% transparente, 32,1% semitransparente (halo), 13,6% opaco | 81.094 bytes | `d330df378bea4cf4…` |
| `static/img/nexo-cubo-transparente.png` | Sidebar, cabeçalho e rodapé da landing | PNG RGBA | 253 × 279 | Cantos com alfa 0; 71,6% transparente, 14,8% semitransparente, 13,6% opaco | 68.691 bytes | `f0edaf0a7d869356…` |

- A identificação de qual imagem tem brilho foi feita pela proporção de pixels semitransparentes e por inspeção visual sobre o fundo escuro do sistema. O teste automatizado confere essa diferença.
- A otimização PNG sem perdas não reduziu os arquivos. Por isso os originais foram mantidos byte a byte, com canal alfa intacto, sem conversão para JPEG e sem fundo acrescentado.
- Os arquivos são servidos por `url_for('static', filename='img/…')`, sem caminho absoluto nem URL externa.

## F. Testes

Ambiente local: Python 3.12 com `requirements-dev.txt`, SQLite isolado com migrações reais e dados fictícios, PostgreSQL 16 descartável e Chromium do Playwright. Nada de produção.

| Execução | Testes | Resultado |
|---|---:|---|
| `tests.test_identidade_visual` (novo): 3 de arquivos, 5 HTTP e 3 de navegador | 11 | OK |
| Suíte completa local `python -B -m unittest discover -s tests -t . -v` (com `NEXO_TEST_BROWSER=1` e `NEXO_TEST_POSTGRES_BIN`), estado final | 649 | **OK**, 0 falhas, 0 erros, 0 ignorados (antes eram 638) |
| CI do PR, commit `b744c93` (run `40332212093`) | 649 + job PostgreSQL | **success** nos dois jobs (`security-sqlite-browser` e `security-postgresql`) |

**O que o teste novo cobre:**
- os dois PNGs são RGBA, com cantos de alfa 0, área transparente e traço opaco, e a versão com brilho tem mais pixels semitransparentes;
- `nexo-logo.jpeg` e `.brand-mark` não existem nem são citados em templates, CSS ou JS;
- nenhuma regra de CSS que alcance o símbolo (inclusive em grupo, pseudoelemento ou media query) desenha fundo, borda, sombra, filtro ou recorte;
- os PNGs são servidos como `image/png`;
- a assinatura correta (uma imagem, `alt=""`, 253×279, "NEXO" e "Faturamento Inteligente" uma vez cada) aparece na landing (cabeçalho e rodapé), no login, em recuperar senha, em como aderir, em resetar senha, no primeiro acesso, no primeiro acesso por token e na sidebar do ADMIN (dashboard, guia) e do CLIENTE (dashboard, histórico, análise, enviar relatórios, guia, suporte);
- em navegador: imagem carregada, sem fundo, sombra ou recorte no contêiner nem `::before`/`::after`, proporção mantida, sem rolagem horizontal. As alturas são 40/34 px na landing (1440, 1024, 768, 375 e 320), 104/88 px nas telas de acesso (1440, 1024, 768, 375 e 320), com o cubo centralizado e inteiro dentro do cartão, e 42 px na sidebar (1440, 1280 e 1024), alinhada ao texto.

**Testes visuais (Teste A a F)**, com capturas em densidade 2x e dados fictícios. As pranchas antes × depois estão em `Docs/INTEGRACOES/evidencias_identidade_visual/`:

| Teste | Resultado |
|---|---|
| A. Login | O cubo com brilho aparece centralizado e transparente, sem moldura, com "NEXO" e o subtítulo abaixo (`antes_depois_login_sidebar.png`) |
| B. ADMIN | Cubo sem brilho, nome e subtítulo na sidebar, sem quadrado escuro nem nome repetido (mesma prancha) |
| C. CLIENTE | Mesma assinatura do ADMIN em todas as telas do portal: os recortes de dashboard, histórico, análise, envio, guia e suporte saíram idênticos pixel a pixel |
| D. Landing | O quadrado com "N" virou o cubo (`antes_depois_landing.png`) |
| E. Rodapé | Mesma assinatura do cabeçalho (mesma prancha) |
| F. Celular | Login a 320 px, menu do CLIENTE aberto a 375 px e cabeçalho da landing a 375 px, sem rolagem horizontal (`depois_celular.png`) |

**Revisão adversarial independente.** Três revisores (QA visual; código, acessibilidade e escopo; completude da troca) fizeram cerca de 60 capturas e medições extras de 320 a 1920 px. Não houve achado crítico, alto ou médio. Os achados baixos foram tratados assim:

- **Corrigidos antes da publicação:**
  - o cartão de acesso ficou mais alto, e o login a 375×667 passou a rolar 13 px. Agora cabe sem rolagem, e o cartão ficou só ~3 px mais alto que o original;
  - a verificação de CSS do teste tinha falsos negativos e um falso positivo;
  - o teste em navegador liberava mais da CDN que os demais testes;
  - a cobertura de tablet e notebook era menor que a pedida.
- **Defeito pego pelo próprio teste em navegador e corrigido antes da publicação:** a imagem da sidebar vazava 4 px da caixa (seção C).
- **Registrados, sem mudança:**
  - O cubo sem brilho tem pouco contraste em tamanho pequeno (40 px na landing e 42 px na sidebar). É característica do arquivo, e logotipos estão isentos dos critérios de contraste da WCAG. Se o proprietário quiser mais presença, a opção compatível com as regras é aumentar a landing para até 44 px.
  - O halo da versão com brilho é sutil sobre o cartão. Está no próprio arquivo e não é cortado.
  - Já antes desta mudança, entre 576 e 992 px o link da marca da landing ocupava toda a coluna do grid (área de foco mais larga).
  - Já antes desta mudança, o subtítulo "Faturamento Inteligente" tem contraste de cerca de 3,8:1.
  - A 360×640 e a 320×568 o login já rolava na `main` e agora rola 6–7 px a mais.
  - Não há favicon, como antes.
  - O vídeo promocional mostra o cubo SVG antigo, mantido porque o pedido proíbe alterar o vídeo.
  - Com usuário logado, a página "Como obter acesso" mostra duas assinaturas: a da sidebar e a do cartão, a mesma estrutura de antes.

**Não executado:** nada contra Render ou Supabase; nenhum teste em Safari, Firefox ou dispositivo físico (apenas Chromium/Chrome).

## G. GitHub

| Item | Valor |
|---|---|
| Branch publicada | `claude/awesome-pascal-0ho42m` (push fast-forward a partir de `c74aa58`, sem force push) |
| Commit da implementação | `b744c933e878f5b1a9f486024252a72bd7519132`: feat(ui): atualizar identidade visual NEXO com cubo transparente |
| Commit do relatório | O commit seguinte, com este relatório e as pranchas de evidência |
| Pull Request | [Helio965/Nexo---Faturamento-Inteligente---Render#26](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/26), base `main` |
| Estado da CI | Run `40332212093` em `b744c93`: **success** (649 testes no job com navegador; job PostgreSQL aprovado). A CI do commit do relatório aparece no PR |
| Merge | **Integrado** pelo proprietário (`Helio965`) em 26/10/2026, 10:56:04 (UTC−3), commit `6abc96c591c51da55fa1a8c62e678f22e67a8672`, com árvore idêntica a `4daa89c` |
| CI da `main` após o merge | Run `40334980562` em `6abc96c`: **success** |

**Por que o executor não fez o merge.** O `render.yaml` declara `autoDeployTrigger: 'off'`, mas `Docs/PREPARACAO_RENDER.md` e `Docs/RELATORIO_NEXO_SEC006_DEPENDENCIAS.md` registram que o proprietário informou Auto-Deploy **ativado** na `main`. Não há acesso ao painel do Render a partir deste ambiente para confirmar. Pela regra do pedido, os commits ficaram publicados e o PR ficou pronto. O proprietário fez o merge em seguida; se o Auto-Deploy estiver ativo, o Render pode ter publicado `6abc96c`, o que não foi verificado daqui. A mudança é só visual e não exige migração. Em produção, porém, continua valendo o incidente do login (HTTP 500 até a migração `e4c004a26b01` no Supabase), que é tratado à parte.

## H. Resultado final

- **Todas as ocorrências do logotipo antigo foram substituídas:** 6 telas de acesso, a sidebar (ADMIN e CLIENTE) e o cabeçalho e o rodapé da landing. Nenhum template, CSS ou JS cita mais `nexo-logo.jpeg` nem `.brand-mark`, e o arquivo antigo saiu do repositório.
- **Em cada assinatura o nome NEXO aparece uma única vez, em texto:** na imagem não há nome, e ela é decorativa para leitores de tela.
- **O cubo aparece sobre o fundo real da interface,** sem fotografia quadrada, moldura escura nem círculo artificial, com as transparências e o brilho originais preservados.
- **Login:** cubo com brilho. **ADMIN, CLIENTE, landing e rodapé:** cubo sem brilho.
- **Preservados:** tema escuro, tons roxos, organização das telas e responsividade.
- **Sem alteração:** autenticação, autorização, sessões, banco, migrações, modelos, regras de empresas, planos, preços, ETL, PDF, APIs, NexoBot, vídeo e fluxos administrativos.
- **Render e Supabase:** não foram acessados nem alterados. Não houve deploy nem migração.
- **Pendências:** conferir no Render se `6abc96c` foi publicado. Opcionalmente, avaliar com o proprietário um cubo maior na landing (até 44 px), favicon a partir de uma versão quadrada do cubo e a atualização do vídeo promocional com o novo símbolo, cada um como tarefa própria.
