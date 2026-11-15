# Correção do alinhamento da navegação por âncoras da landing page

## 1. Identificação

| Campo | Registro |
| --- | --- |
| Correção | Quarta implementação de homologação: alinhamento das seções da landing page na navegação pelo menu superior |
| Data e horário deste registro | 2026-11-14 22:28 -03 — `America/Sao_Paulo` |
| Repositório | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Ambiente | Testes e homologação do NEXO |
| Branch | `fix/landing-ancoras-alinhamento-header` |
| Commit inicial, confirmado em `origin/main` antes das alterações | `ae8775b23b948d8facb4d2eb69938e6209d91667` |
| Commits de código e testes | `fdd58e01a9728306a77e70bb457d01346fbdb93d` (correção e testes), `d5c8c0929bb4af90b74831e153fb9e7182f9740b` (reservas proporcionais à fonte e ajustes dos testes) e `849afb3f8d045c5cefac7c56aa9f7dd02ddc4101` (piso de 44 px na reserva de 641 a 992 px) |
| Commit de documentação | Commit posterior ao de código, identificável no histórico deste arquivo |
| Status | Implementação concluída e validada localmente; Pull Request aberto para revisão; homologação pendente |
| Integração | Pull Request para revisão, sem merge automático e sem deploy manual |

Na conferência inicial, a árvore de trabalho estava limpa, `main` estava no merge do PR #48 e não havia Pull Request aberto no repositório. A pasta `POSSIVEIS ATUALIZAÇÕES EMPRESA` foi reutilizada sem alterar os documentos das implementações anteriores.

O escopo se limita ao posicionamento das seções durante a navegação da landing page: `static/css/landing.css`, `static/js/landing.js` e um módulo de testes novo. Não houve alteração em textos, cores, logo, componentes, gráficos, autenticação, dashboards, banco de dados, Supabase, Render ou no projeto empresarial. O vídeo da demonstração e o `landing-video.js` também não foram alterados: o `landing.js` apenas grava um quadro antes a mesma medida do cabeçalho que o vídeo já usava (seção 5.2).

## 2. Problema anterior

A landing page mantém o cabeçalho (`header.nexo-header`) fixo no topo com `position: sticky; top: 0`. Os botões Início, Como funciona, Indicadores, Demonstração e Planos são âncoras HTML (`#inicio`, `#como-funciona`, `#indicadores`, `#demonstracao`, `#planos`) e o navegador rola até a seção correspondente.

Medições no Chromium, depois de clicar no menu e esperar o fim da rolagem, mostraram que a seção escolhida parava longe do cabeçalho em todas as larguras pedidas:

| Tela | Altura do cabeçalho | Início da seção abaixo da borda do cabeçalho | Título (h2) abaixo da borda do cabeçalho |
| --- | --- | --- | --- |
| Computador (1024, 1366, 1440, 1920 px) | 71,2 a 73,3 px | 126,2 a 129,3 px | 257,3 a 260,4 px |
| Tablet (768, 820, 992 px) | 71,2 px | 128,4 a 129,3 px | 259,5 a 260,4 px |
| Celular (320, 360, 390, 430 px) | 65,6 px | 133,9 a 134,8 px | 246,4 a 247,4 px |

Essa faixa de 126 a 135 px exibia o final da seção anterior: em Como funciona, o fim de "Oportunidades nos seus dados"; em Indicadores, o fim dos depoimentos; em Demonstração, o fim da lista de indicadores; em Planos, os últimos cartões do "Método NEXO". O título só aparecia muito abaixo do cabeçalho. Início não tinha o problema, porque a página volta ao topo.

O acesso direto por endereço com âncora era irregular e variava com o conteúdo carregado depois da rolagem. Em Como funciona, o resultado era igual ao do clique. Em Indicadores e Demonstração, a seção ficava entre 69 e 77 px abaixo do cabeçalho no computador e no tablet, e entre 37 e 61 px no celular. Em Planos, ficava 17 px abaixo do cabeçalho de 1366 px para cima e sob o cabeçalho de 1024 px para baixo: −3,1 px em 1024 px, −28 px no tablet e de −88 a −155 px no celular. Em 320 px, o título de Planos ficava quase todo sob o cabeçalho: começava 42,2 px acima da borda, e só os últimos 22 px apareciam.

Durante a investigação também apareceram dois efeitos que já existiam no `main` e que dependem do mesmo mecanismo de compensação:

- **Voltar e Avançar:** depois de três ou mais seções visitadas pelo menu, o primeiro Voltar restaurava a posição certa. A partir do segundo Voltar seguido, porém, a página voltava a uma posição de 279 a 398 px acima daquela em que o usuário a deixou (390 × 844 e 1366 × 768, na execução registrada; o valor varia entre execuções), e a seção aparecia esse tanto mais abaixo na tela. O Avançar repetia o erro nas mesmas entradas.
- **Foco no cabeçalho:** com a página rolada até o meio, focar pelo teclado um controle do próprio cabeçalho fazia a página rolar de 398 a 440 px.

## 3. Causa técnica

### 3.1. `scroll-padding-top` e `scroll-margin-top` somados

`static/css/landing.css` tinha duas compensações independentes, ambas fixas em 100 px:

```css
html { scroll-behavior: smooth; scroll-padding-top: 100px; }
section[id], main[id], footer[id] { scroll-margin-top: 100px; }
```

Para levar um elemento à vista, o navegador desconta o `scroll-padding-top` do contêiner de rolagem (a raiz do documento) e também o `scroll-margin-top` do elemento de destino. As duas propriedades se somam: a seção parava a 200 px do topo da janela. Como o cabeçalho mede de 65,6 a 73,3 px com o menu fechado, sobravam de 126 a 135 px entre a borda do cabeçalho e o início da seção. Nenhum dos dois valores vinha da altura do cabeçalho.

### 3.2. Altura real do cabeçalho

A altura do cabeçalho muda com a faixa de largura e com o estado do menu. Ela também depende das fontes, porque os textos usam `rem`, e do zoom.

| Faixa de largura | Com JavaScript (menu fechado) | Sem JavaScript (links abertos no cabeçalho) |
| --- | --- | --- |
| Acima de 1100 px | 73,28 px | 73,28 px |
| 993 a 1100 px | 71,17 px | 71,17 px |
| 641 a 992 px | 71,17 px | 186,17 px |
| Até 640 px | 65,59 px | 226,59 px |

Um valor único em pixels não serve para todas as faixas. No menu móvel, o cabeçalho cresce quando o menu abre e volta ao tamanho original quando um link é escolhido.

### 3.3. `padding-top` das seções

As seções têm `padding: 80px 0` (64 px até 640 px de largura). Esse espaçamento interno separa o início da seção do primeiro conteúdo (a etiqueta e o título). Com o recuo acumulado de 200 px, o título ficava de 246 a 260 px abaixo do cabeçalho. Com a seção alinhada, sobra só o espaçamento interno da própria seção.

### 3.4. Navegação por âncoras, rolagem suave e conteúdo carregado depois

O navegador calcula a posição final da rolagem quando a navegação começa, e a rolagem suave (`scroll-behavior: smooth`, definida no `landing.css` e no reboot do Bootstrap 5.3.3) anima até essa posição fixa.

No acesso direto por endereço com âncora, a rolagem inicial também era suave e começava logo após a leitura do documento. Antes de ela terminar, os gráficos (Plotly, carregado de forma assíncrona) eram desenhados e o `landing.js` escondia as três notas "Os dados da demonstração também estão disponíveis na descrição abaixo." que ficam acima das seções seguintes. O conteúdo acima do destino diminuía de 58 px (computador) até cerca de 290 px (320 px de largura). A animação, porém, terminava na posição calculada antes disso.

Exemplo registrado no código original, em 1366 × 768, com `/#indicadores`:

- o documento terminou de ser lido em 0,41 s;
- por volta de 1,02 s, com a rolagem suave em andamento (posição de 158 px), os gráficos estavam prontos e as notas, escondidas;
- a animação terminou na posição calculada antes disso, com a seção a 69,5 px do cabeçalho, e não a 126,8 px como no clique.

Em Planos no celular, o deslocamento foi maior que a sobra de 134 px, e por isso a seção terminou sob o cabeçalho.

Com a página parada, o Chromium compensa sozinho esse tipo de mudança de altura (ancoragem de rolagem): reexibir uma das notas acima da seção moveu a rolagem de 3274 para 3331 px, e a seção continuou a 126,8 px do cabeçalho. O problema acontece quando a mudança ocorre no meio de uma animação.

### 3.5. Efeito de `scroll-padding-top` no histórico e no foco

Uma página mínima, sem nenhum código da landing (cabeçalho fixo com quatro links e seis seções, quatro delas destinos dos links), reproduziu no Chromium 153 o desvio de Voltar/Avançar sempre que a raiz tinha `scroll-padding-top`. Com `scroll-margin-top` só nos destinos, ou sem compensação, todas as posições foram restauradas exatamente.

Na landing, as mesmas medições mostraram:

- com `scroll-padding-top` na raiz, focar um link do cabeçalho rolava a página;
- com margem de rolagem aplicada também aos controles do cabeçalho, a página ainda rolava de 56 a 59 px e o histórico voltava a errar (59 e 162 px).

Isso orientou a escolha do mecanismo único (seção 5.1): margem de rolagem em todo o conteúdo fora do cabeçalho, sem `scroll-padding` na raiz.

### 3.6. JavaScript da navegação e vídeo da demonstração

O `landing.js` controla o menu móvel até 992 px: o botão Menu abre e fecha `#landing-navigation`, e o clique num link do menu fecha o menu dentro do próprio evento de clique.

A rolagem até a âncora é a ação padrão do link. Ela acontece logo depois desse evento, já com o menu fechado, e não é interceptada pelo script. Por isso, qualquer medida da altura do cabeçalho usada na compensação precisa ser atualizada nesse mesmo evento: o `ResizeObserver` só avisa a mudança no quadro seguinte.

O mesmo vale para o vídeo da demonstração. O `landing-video.js` limita a largura do quadro do vídeo pela altura da janela menos o cabeçalho (`--nexo-demo-header`) e mede o cabeçalho também com o menu aberto, um quadro depois de cada mudança.

Em telas baixas de até 992 px de largura, como o celular deitado, abrir o menu encolhe o vídeo em até 115 px. Ao escolher Planos, que fica abaixo do vídeo, o destino da rolagem era calculado com o vídeo ainda encolhido. O vídeo voltava ao tamanho logo depois e a rolagem suave terminava de 85 a 115 px abaixo do cabeçalho. Esse caso foi encontrado na revisão da versão da correção que já usava `scroll-margin-top`, mas ainda não sincronizava o vídeo, e foi medido nas telas 568 × 320, 667 × 375, 844 × 390, 932 × 430 e 992 × 500.

## 4. Arquivos modificados

| Caminho | Finalidade | Alteração realizada | Justificativa técnica |
| --- | --- | --- | --- |
| `static/css/landing.css` | Folha de estilos exclusiva da landing page | Remove `scroll-padding-top: 100px` da raiz e a regra `section[id], main[id], footer[id] { scroll-margin-top: 100px; }`. Acrescenta a variável `--nexo-header-height` (token em `:root` e redefinição nas media queries de 1100, 992 e 640 px), a margem de rolagem única `scroll-margin-top: var(--nexo-header-height)` para todo o conteúdo fora do cabeçalho (mais 8 px nos controles focáveis) e a regra que mantém a rolagem imediata até o fim do carregamento. | Um só mecanismo de compensação, igual à altura real do cabeçalho em cada faixa de largura, sem somar deslocamentos; sem `scroll-padding` na raiz, que no Chromium desalinhava o histórico e o foco (seção 3.5). |
| `static/js/landing.js` | Menu móvel, depoimentos e gráficos da landing | Acrescenta `syncHeaderOffset()`, que mede o cabeçalho e grava `--nexo-header-height` (e `--nexo-demo-header` no quadro do vídeo); chama a função ao iniciar, num `ResizeObserver` do cabeçalho e dentro de `setMenu()`; acrescenta a classe `landing-smooth-scroll` ao fim do carregamento. O restante do arquivo (menu, depoimentos e gráficos) não muda. | A altura do cabeçalho varia com a largura, as fontes, o zoom e o menu móvel. A medição no próprio evento do menu garante que a rolagem do link use o cabeçalho já fechado; a do vídeo evita que ele mude de altura depois de a rolagem ser calculada nas telas baixas. |
| `tests/test_landing_ancoras_navegador.py` | Novo módulo de testes da navegação por âncoras | Dois testes sem navegador (mecanismo único) e dez testes no Chromium com medições por `getBoundingClientRect()`. | Comprova o comportamento pedido em todas as larguras e estados, e falha no código anterior. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-14_Correcao_Alinhamento_Navegacao_Landing_Page.md` | Este documento | Novo | Registro técnico da quarta implementação. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-14_landing_ancoras_*_antes_depois.png` | Capturas comparativas | Oito imagens novas (seção 7) | Evidência visual com o mesmo enquadramento antes e depois. |

## 5. Solução implementada

### 5.1. Um único mecanismo: margem de rolagem com a altura do cabeçalho

Regras removidas ou modificadas em `static/css/landing.css`:

```css
/* antes */
html { scroll-behavior: smooth; scroll-padding-top: 100px; }
section[id], main[id], footer[id] { scroll-margin-top: 100px; }

/* depois */
html { scroll-behavior: smooth; }
main, main *, footer, footer * { scroll-margin-top: var(--nexo-header-height); }
:is(main, footer) :is(a[href], button, input, select, textarea, summary, [tabindex]) { scroll-margin-top: calc(var(--nexo-header-height) + 8px); }
```

A compensação passa a ser feita só por `scroll-margin-top`, com o valor da variável `--nexo-header-height`, que é a altura do cabeçalho. A margem vale para o elemento que o navegador leva à vista. Com ela:

- os destinos das âncoras (seções, conteúdo principal e rodapé) param com o início exatamente na borda inferior do cabeçalho;
- qualquer outro elemento da página que o navegador leve à vista, como um controle que recebe o foco do teclado, também para abaixo do cabeçalho;
- os controles focáveis recebem 8 px a mais, para que o contorno de foco (3 px, com afastamento de 4 px) fique inteiro abaixo da borda.

Nenhum elemento dentro do cabeçalho recebe a margem. A raiz não tem mais `scroll-padding`, então não existe soma de deslocamentos. Isso também corrige o histórico (Voltar/Avançar) e o foco nos controles do cabeçalho (seção 3.5).

### 5.2. Altura real do cabeçalho

A variável tem dois níveis.

**Folha de estilos (sem JavaScript e antes da primeira medição).** Há um valor por faixa de largura, escrito com a composição real do cabeçalho naquela faixa: borda, espaçamento vertical, item mais alto da linha e, até 992 px, a segunda linha com os links abertos. Os tamanhos de texto estão em `rem`, então o valor acompanha a fonte padrão do navegador enquanto os textos do cabeçalho não quebram linha (seção 6.6). Com a fonte padrão de 16 px, os valores coincidem com as alturas medidas da seção 3.2, com diferença menor que 0,01 px, que vem do arredondamento do layout:

| Faixa | Expressão | Valor com fonte de 16 px |
| --- | --- | --- |
| Acima de 1100 px | `calc(25px + max(44px, 2.871rem, 1.518rem + 24px))` | 73,29 px |
| 993 a 1100 px | `calc(25px + max(44px, 1.683rem, 1.386rem + 24px))` | 71,18 px |
| 641 a 992 px (links abertos, duas linhas) | `calc(52px + max(44px, 1.683rem, 1.386rem + 24px) + 2 * max(44px, 1.485rem + 20px))` | 186,18 px |
| Até 640 px (links abertos, três linhas) | `calc(50px + max(44px, 1.5675rem, 1.287rem + 24px) + 3 * max(44px, 1.419rem + 20px))` | 226,59 px |

**JavaScript.** Em `static/js/landing.js`, a função `syncHeaderOffset()`:

- lê `getBoundingClientRect().height` do cabeçalho (a medida inclui a borda) e grava o valor em `--nexo-header-height` no elemento `html`, sobrepondo-se à folha;
- é chamada ao iniciar, por um `ResizeObserver` do cabeçalho (`box: 'border-box'`, com `resize` da janela como alternativa) e dentro de `setMenu()`, logo depois de mostrar ou esconder os links do menu móvel;
- só grava quando a altura muda;
- grava também `--nexo-demo-header` no quadro do vídeo da demonstração, com o mesmo cálculo que o `landing-video.js` já fazia (`Math.ceil` da altura). Isso só antecipa para o próprio evento uma atualização que o `landing-video.js` fazia no quadro seguinte, sem mudar o funcionamento do vídeo. Assim, nas telas baixas, o tamanho do vídeo fica definitivo antes de o navegador calcular a rolagem até uma seção abaixo dele.

A chamada dentro de `setMenu()` é a que resolve o menu móvel. O clique num link fecha o menu dentro do próprio evento, a variável recebe a altura do cabeçalho já fechado, e a rolagem nativa do link, que acontece logo em seguida, usa esse valor. Não existe laço de recálculo: a variável não afeta o tamanho do cabeçalho, que é o único elemento observado.

### 5.3. Acesso direto por endereço e carregamento da página

Regra e classe acrescentadas:

```css
html.landing-enhanced:not(.landing-smooth-scroll) { scroll-behavior: auto; }
```

```js
function enableSmoothScroll() {
  window.requestAnimationFrame(function () { htmlRoot.classList.add('landing-smooth-scroll'); });
}
if (document.readyState === 'complete') enableSmoothScroll();
else window.addEventListener('load', enableSmoothScroll, { once: true });
```

Enquanto a página carrega, a rolagem até a âncora é imediata. No acesso direto (`/#planos`), na recarga e num clique feito antes do fim do carregamento, a posição é aplicada de uma vez. Quando os gráficos e as fontes mudam depois a altura do conteúdo acima da seção, o navegador mantém a seção no lugar, porque nenhuma animação está em curso (seção 3.4). Nas medições, a seção continuou alinhada depois da chegada dos gráficos.

Ao fim do carregamento, a classe `landing-smooth-scroll` libera a rolagem suave de antes para todos os cliques. Sem JavaScript a regra não se aplica, e a rolagem suave continua como antes. Com `prefers-reduced-motion: reduce`, o bloco existente continua desligando as animações.

Sem essa regra, e já com a compensação corrigida, o acesso direto terminava com a seção de 51,7 a 289,7 px sob o cabeçalho, porque a animação ia até o destino calculado antes de os gráficos ficarem prontos (medição registrada na seção 6.4.4).

### 5.4. Espaçamento interno das seções

O `padding` das seções (80 px no computador e no tablet, 64 px até 640 px) não foi alterado. Com o início da seção na borda do cabeçalho, entre a borda e a etiqueta da seção há só o espaçamento interno da própria seção. O título fica 131 px abaixo do cabeçalho no computador e no tablet e 112 px no celular; antes, ficava de 246 a 260 px. O fim da seção anterior, com o seu espaçamento inferior e a sua linha divisória, fica fora da área visível. Reduzir o espaçamento comprimiria a página inteira e mudaria o ritmo visual. Se a homologação preferir os títulos mais próximos do cabeçalho, o ajuste pode ser feito só no `padding-top` das seções.

### 5.5. Comportamento final

- **Computador (1024 a 1920 px) e tablet (768 a 992 px):** a seção escolhida começa na borda inferior do cabeçalho fixo (diferença de no máximo 0,5 px), com rolagem suave e o título inteiro visível.
- **Celular (320 a 430 px, também deitado):** o botão Menu abre os links; o link escolhido fecha o menu e a seção para logo abaixo do cabeçalho já fechado (65,6 ou 71,2 px, conforme a largura), sem deslocamento posterior.
- **Sem JavaScript:** os links ficam abertos no cabeçalho, como antes, e a rolagem usa as alturas da folha.
- **Movimento reduzido:** a rolagem é imediata e o alinhamento é o mesmo.
- **Histórico:** Voltar e Avançar restauram exatamente a posição de cada entrada, e o clique repetido na mesma seção não cria entrada nova.
- **Teclado:** "Pular para o conteúdo" leva ao topo do conteúdo; o foco do teclado não fica sob o cabeçalho; focar um controle do próprio cabeçalho não rola a página.
- **Redimensionamento, densidade de pixels e fonte maior:** a variável acompanha a nova altura do cabeçalho, sem posições antigas.

## 6. Testes

### 6.1. Ambiente

Todos os testes rodaram em ambiente isolado:

- servidor Flask local, com banco SQLite descartável criado pelas migrações reais (`tests/deploy_support.py`);
- rede externa bloqueada;
- Chromium (Chrome for Testing 153.0.8010.12) controlado pelo Playwright 1.56, com Python 3.12.3 (na CI, o job usa o Google Chrome instalado no runner);
- Bootstrap 5.3.3 e Plotly 2.35.2 servidos a partir de cópias locais com o hash SRI oficial conferido (`NEXO_TEST_CDN_DIR`);
- fontes Inter instaladas localmente, como na CI, porque o Google Fonts fica bloqueado nos testes.

Não houve acesso ao Supabase, ao Render nem ao projeto empresarial.

### 6.2. Comandos

```bash
# Módulo novo (no Chromium)
NEXO_TEST_BROWSER=1 NEXO_TEST_CDN_DIR=<cópias íntegras da CDN> NEXO_TEST_CHROMIUM=<Chrome for Testing> \
  python -B -m unittest tests.test_landing_ancoras_navegador -v

# O mesmo módulo contra o código anterior: cópia separada do main (git worktree) com o arquivo de teste copiado
git worktree add --detach <pasta> origin/main
cp tests/test_landing_ancoras_navegador.py <pasta>/tests/
cd <pasta> && <mesmas variáveis> python -B -m unittest tests.test_landing_ancoras_navegador -v
git worktree remove --force <pasta>

# Regressão completa, como o job security-sqlite-browser da CI (sem os testes que exigem o PostgreSQL privado)
NEXO_TEST_BROWSER=1 NEXO_TEST_CDN_DIR=<cópias íntegras da CDN> NEXO_TEST_CHROMIUM=<Chrome for Testing> \
  python -B -m unittest discover -s tests -t . -v
```

### 6.3. Resoluções e cenários

| Grupo | Larguras × alturas | Cenários |
| --- | --- | --- |
| Computador | 1024 × 768, 1366 × 768, 1440 × 900, 1920 × 1080 | Menu: ida (Início → Como funciona → Indicadores → Demonstração → Planos) e volta (Planos → … → Início), com rolagem suave |
| Tablet | 768 × 1024, 820 × 1180, 992 × 800 | Mesma sequência, pelo menu móvel |
| Celular | 320 × 568, 360 × 740, 390 × 844, 430 × 932 | Mesma sequência, pelo menu móvel |
| Celular deitado | 568 × 320, 667 × 375, 844 × 390 | Mesma sequência, pelo menu móvel (o vídeo muda de altura com o menu aberto) |
| Acesso direto (no módulo de testes) | 1366 × 768, 820 × 1180, 390 × 844, 320 × 568 | `/#como-funciona`, `/#indicadores`, `/#demonstracao`, `/#planos`, recarga com âncora e link de "Como obter acesso" para `/#planos` |
| Outros | 1366 × 768 e 390 × 844 | Clique antes do fim do carregamento, Voltar/Avançar, clique repetido, teclado, link "Pular para o conteúdo", botões "Conheça os planos" e "Veja o NEXO em ação", links do rodapé, "Voltar ao início", foco com Shift+Tab, foco no cabeçalho, redimensionamento entre 320 e 1920 px, fonte padrão de 20 px |
| Sem JavaScript | 1366, 1024, 820, 390 e 320 px; 1366, 820 e 390 px com fonte de 20 px | Todas as âncoras do menu aberto no cabeçalho |
| Movimento reduzido | 1366 × 768 | Rolagem sem animação e alinhamento imediato |

Além do módulo de testes, as medições das seções 2, 3, 6.4 e 7 vêm de scripts locais de medição, fora do repositório. Eles usam a mesma infraestrutura do módulo (servidor de teste, cópias da CDN, Chromium e as mesmas variáveis `NEXO_TEST_*`) e gravam as medidas com `getBoundingClientRect()`:

| Medição | O que registra |
| --- | --- |
| Antes x depois (seções 2, 6.4.1 e 6.4.2) | Clique pelo menu (ida e volta) e acesso direto, com rolagem suave, em 11 telas no código anterior e 14 no código final, que acrescenta o celular deitado |
| Altura do cabeçalho (seção 3.2) | Altura em 24 larguras de 320 a 2560 px, com e sem JavaScript |
| Linha do tempo do acesso direto (seção 3.4) | Posição da rolagem, da seção e das notas dos gráficos a cada quadro, no código original |
| Histórico e foco (seções 2, 3.5 e 6.5) | Página mínima sem código da landing e variantes do mecanismo aplicadas à landing: Voltar/Avançar, foco com Shift+Tab e foco no cabeçalho |
| Celular deitado (seções 3.6 e 6.4.4) | Menu móvel em 568 × 320, 667 × 375, 844 × 390, 932 × 430 e 992 × 500, com e sem animação |
| Cenários extras (seção 6.4.4) | Clique com o Plotly retido, densidade de pixels, fonte padrão de 20 e 24 px, retirada da regra de carregamento em memória e navegação sem JavaScript com fontes de 12 a 20 px |
| Capturas (seção 7) | Imagens antes e depois na mesma tela e seção, com a linha do início medido da seção |

Em cada navegação, o teste mede com `getBoundingClientRect()`:

- a borda inferior do cabeçalho e o início da seção, com tolerância de 1 px. A posição de rolagem é arredondada para pixels inteiros e as posições do layout são fracionárias, então a diferença real é de até 0,5 px;
- que nenhum elemento da seção anterior aparece abaixo da borda do cabeçalho;
- que o título está abaixo do cabeçalho e dentro da tela;
- que, antes da etiqueta da seção, há só o espaçamento interno da própria seção;
- que o endereço tem o identificador correto e que não existe rolagem horizontal.

Dois casos usam 2 px. No clique feito durante o carregamento, a verificação depois da chegada dos gráficos soma um segundo arredondamento, o da ancoragem de rolagem do navegador; logo após o clique vale 1 px. Sem JavaScript, os 2 px são margem para diferenças de métrica de fonte entre ambientes: a reserva calculada pela folha difere da altura real em menos de 0,01 px, e as medições ficaram entre −0,50 e +0,48 px.

### 6.4. Resultados

#### 6.4.1. Antes e depois, pelo menu (ida e volta)

Valores medidos com `getBoundingClientRect()`, em px, a partir da borda inferior do cabeçalho. Valor positivo indica que a seção ou o título começa abaixo da borda; negativo, que fica sob o cabeçalho. "Antes" é o código do `main` (`ae8775b`); "depois" é o código com a correção (`d5c8c09`). O commit seguinte (`849afb3`) só altera a reserva sem JavaScript para fontes padrão menores que 14,4 px. Os valores são de Como funciona, Indicadores, Demonstração e Planos.

| Tela | Início da seção, antes | Início da seção, depois | Título, antes | Título, depois | Seção anterior visível, antes | Seção anterior visível, depois |
| --- | --- | --- | --- | --- | --- | --- |
| Computador (1024, 1366, 1440, 1920) | +126,2 a +129,3 | −0,4 a +0,5 | +257,3 a +260,4 | +130,7 a +131,6 | 126,2 a 129,3 | 0,0 a 0,5 |
| Tablet (768, 820, 992) | +128,4 a +129,3 | −0,3 a +0,4 | +259,5 a +260,4 | +130,8 a +131,5 | 128,4 a 129,3 | 0,0 a 0,4 |
| Celular (320, 360, 390, 430) | +133,9 a +134,8 | −0,4 a +0,4 | +246,4 a +247,4 | +112,1 a +113,0 | 133,9 a 134,8 | 0,0 a 0,4 |
| Celular deitado (568 × 320, 667 × 375, 844 × 390) | não medido | −0,5 a +0,4 | não medido | +112,3 a +131,5 | não medido | 0,0 a 0,4 |

Início levou a página ao topo (`scrollY` 0) nas 14 telas medidas depois e nas 11 medidas antes, com a apresentação inicial logo abaixo do cabeçalho. O celular deitado ficou fora da medição inicial; no código anterior, o módulo de testes registrou ali Como funciona de 128,4 a 134,8 px abaixo do cabeçalho e Planos a 243,6 px (844 × 390, pelo menu móvel). Os valores de "seção anterior visível" depois da correção são frações de pixel do arredondamento da rolagem.

#### 6.4.2. Acesso direto por endereço com âncora

| Tela | Início da seção, antes | Início da seção, depois | Título, antes | Título, depois |
| --- | --- | --- | --- | --- |
| Computador | −3,1 a +129,3 | −0,4 a +0,5 | +128,0 a +260,4 | +130,7 a +131,6 |
| Tablet | −28,0 a +129,2 | −0,3 a +0,4 | +103,1 a +260,3 | +130,8 a +131,5 |
| Celular | −154,8 a +134,7 | −0,4 a +0,4 | −42,2 a +247,3 | +112,1 a +113,0 |
| Celular deitado | não medido | −0,5 a +0,4 | não medido | +112,3 a +131,5 |

No celular, o título de Planos ficava quase todo sob o cabeçalho: em 320 px, começava 42,2 px acima da borda e só os últimos 22 px apareciam.

#### 6.4.3. Módulo de testes novo

| Execução | Resultado |
| --- | --- |
| Código com a correção (`d5c8c09`) | 12 testes aprovados em 343,7 s. Em `849afb3`, os dois testes sem navegador e o teste sem JavaScript foram executados de novo e aprovados |
| Código anterior (`main`, `ae8775b`) com o mesmo arquivo de teste | Os 12 testes falham, com 55 falhas de verificação e nenhum erro de execução. Exemplos: "Seção começa abaixo da borda do cabeçalho" com 126,9 px (computador), 128,4 px (tablet), 134,6 px (celular) e 243,6 px (Planos no celular deitado, pelo menu móvel); "Seção começa sob o cabeçalho" com −88,4 px (390 px) e −154,8 px (320 px) em Planos pelo acesso direto; "Foco rolou além do necessário"; ausência de `syncHeaderOffset()` em `setMenu` |

#### 6.4.4. Medições complementares no código final

| Cenário | Resultado |
| --- | --- |
| Celular deitado com o menu (568 × 320, 667 × 375, 844 × 390, 932 × 430, 992 × 500), com e sem animação | Planos, a partir do topo, de Demonstração e de Como funciona: −0,5 a 0,0 px (30 navegações). Na versão com `scroll-margin-top` antes da sincronização do vídeo: até +115,0 px. Demonstração e Como funciona: −0,3 a +0,4 px |
| Clique em Planos antes do fim do carregamento, com o Plotly retido (1366, 390 e 320 px) | −0,39 a −0,20 px no clique; depois da chegada dos gráficos, que encolhem o conteúdo acima da seção, −0,42 a +0,30 px |
| Densidade de pixels 2, 2,625 e 3 (celular) e 1,25 e 1,5 (computador) | −0,42 a +0,45 px |
| Fonte padrão de 20 e 24 px, com JavaScript (1366 e 390 px) | Cabeçalho de 70,7 a 109,1 px; seções a −0,31 a +0,36 px |
| Sem JavaScript, com fontes de 16 e 20 px (1366, 1024, 820, 390 e 320 px) | −0,50 a +0,48 px em 50 navegações, com o cabeçalho de 71,2 a 244,8 px |
| Sem JavaScript, com fontes de 12 e 14 px (1366, 820, 768 e 390 px), depois do commit `849afb3` | −0,45 a +0,48 px em 40 navegações. Antes dele, a reserva de 641 a 992 px ficaria até 3,4 px menor que o cabeçalho com fonte de 12 px |
| Acesso direto sem a regra de rolagem imediata no carregamento, só para comparação (regra retirada em memória) | Seção de 51,7 a 289,7 px sob o cabeçalho em Indicadores, Demonstração e Planos. Com a regra: −0,4 a +0,5 px |
| Voltar, Avançar e clique repetido | Posições restauradas exatamente; nenhuma entrada nova no histórico com o clique repetido |
| Foco com Shift+Tab num controle coberto pelo cabeçalho | Controle a cerca de 8 px da borda, com o contorno de foco inteiro visível |
| Foco num controle do próprio cabeçalho com a página no meio | Nenhuma rolagem |

#### 6.4.5. Regressão completa

| Execução | Resultado |
| --- | --- |
| Regressão completa sobre `d5c8c09` (`unittest discover` com navegador), em 2.232,7 s | 1.723 testes: 1.711 aprovados, 11 pulados e 1 erro de ambiente |

- **Pulados:** 10 testes exigem o PostgreSQL privado (`NEXO_TEST_POSTGRES_BIN`), que a CI executa no job `security-postgresql`. O outro só gera capturas da Visão Geral quando `NEXO_PAINEL_CAPTURAS` está definido.
- **Erro de ambiente:** `tests.test_supply_chain_install` exige o pip 26.2.2 fixado pelo projeto, e o ambiente local tem o pip 26.3. O mesmo erro ocorre na cópia separada do `main`, sem esta correção.
- **Módulos ligados à landing, todos aprovados:** `test_landing_ancoras_navegador` (12 testes), `test_landing_commercial` (conteúdo, navegação, gráficos e acessibilidade da landing), `test_landing_video_commercial` (vídeo da demonstração), `test_identidade_visual`, `test_overflow_navegador`, `test_csp_navegador` e `test_tema_navegador`.
- **Commit `849afb3`:** veio depois dessa regressão e muda uma única expressão da reserva sem JavaScript. Nele, os testes sem navegador e o teste sem JavaScript do módulo novo foram executados de novo e aprovados. A CI do Pull Request executa a suíte completa sobre o commit final.

### 6.5. Problemas identificados durante a implementação e correções adicionais

1. **Acesso direto e conteúdo carregado depois (seção 3.4).** A medição inicial do código original mostrou que o acesso direto dependia do momento em que os gráficos ficavam prontos. Por isso, a correção inclui desde a primeira versão a rolagem imediata durante o carregamento (seção 5.3).
   - **Comprovação:** para confirmar que essa regra é necessária, a medição foi repetida no código final com a regra retirada em memória. Sem ela, a seção terminava de 51,7 a 289,7 px acima da borda, ou seja, coberta pelo cabeçalho, em Indicadores, Demonstração e Planos (seção 6.4.4).
   - **Resultado:** com a regra, os 12 casos que ficavam deslocados, e também os 4 de Como funciona que já estavam alinhados, ficaram a no máximo 0,5 px da borda.
2. **Histórico e foco com `scroll-padding-top` (seção 3.5).** A primeira versão da correção usava `scroll-padding-top` com a altura do cabeçalho. Ela alinhava as seções, mas mantinha dois defeitos que já existiam no `main`:
   - Voltar/Avançar restauravam posições de 384 a 816 px erradas;
   - focar um controle do cabeçalho rolava a página de 384 a 422 px.

   **Correção adicional:** troca do mecanismo por `scroll-margin-top` (seção 5.1).
3. **Revisão independente do diff.** A revisão cobriu cinco frentes (CSS, JavaScript, testes, acessibilidade e escopo). O achado principal (celular deitado) foi confirmado por dois verificadores independentes e medido no navegador. Os demais foram avaliados no código e, quando dependiam do comportamento do navegador, medidos no Chromium antes da alteração.
   - **Celular deitado (seção 3.6):** com o menu aberto, Planos parava de 85 a 115 px abaixo do cabeçalho, porque o vídeo mudava de altura depois do cálculo da rolagem. **Correção adicional:** `syncHeaderOffset()` grava também a reserva do vídeo. Depois dela, o resultado ficou entre −0,5 e +0,4 px.
   - **Contorno de foco:** com margem exatamente igual ao cabeçalho, a parte de cima do contorno de foco (3 px de linha e 4 px de afastamento) ficava sob o cabeçalho. **Correção adicional:** 8 px a mais para os controles focáveis.
   - **Cobertura de elementos:** a primeira lista de seletores cobria só elementos com `id` e controles. Sem `scroll-padding` na raiz, texto, cartões e itens sem `id` ficariam sem compensação quando o navegador os levasse à vista por outros caminhos (por exemplo, recursos de acessibilidade), e o `scroll-padding` antigo cobria esses casos. **Correção adicional:** a margem vale para todo o conteúdo de `main` e `footer`.
   - **Reservas sem JavaScript:** os valores em px valiam só para a fonte padrão de 16 px. **Correção adicional:** composição em `calc()` com `rem` (seção 5.2), verificada sem JavaScript com fontes de 16 e 20 px.
   - **Testes:**
     - o cenário de Shift+Tab não exercitava a margem e agora deixa o controle inteiro sob o cabeçalho;
     - uma verificação estática era satisfeita por um comentário, e o código passou a ser lido sem comentários;
     - os valores das reservas estavam fixados no teste e foram trocados por invariantes do mecanismo;
     - as esperas pelo fim da rolagem passaram a ser por quadros de animação e pelo alinhamento; restam só duas janelas de 500 ms que confirmam que a página não se desloca depois do clique e, sem JavaScript, a leitura da posição a cada 50 ms;
     - a espera pelo carregamento deixou de depender da classe criada pela correção: no código anterior, os testes passam a falhar pelo alinhamento, e não por tempo esgotado.
   - **Rolagem suave só depois do carregamento:** mantida por decisão técnica (item 1 e seção 6.6), com teste que segura a resposta do Plotly e verifica o alinhamento antes e depois da chegada dos gráficos.
4. **Ajuste do próprio teste.** A etiqueta das seções é um elemento em linha, e o alinhamento pela linha de base do texto a desce até cerca de 1,4 px no celular. A verificação de "área vazia" passou a medir a etiqueta a partir do início da seção, e não da borda do cabeçalho.

### 6.6. Limitações conhecidas

- **Rolagem imediata durante o carregamento.** Até o evento `load` (que também espera o Plotly da CDN), a rolagem até as âncoras é imediata, e não animada. Em conexões lentas, um clique feito antes do fim do carregamento salta direto para a seção. É uma troca deliberada: com animação, a chegada dos gráficos no meio da rolagem deixava a seção fora do lugar. Depois do carregamento, a rolagem suave é a mesma de antes.
- **Navegadores verificados.** Localmente, os testes usaram o Chromium (Chrome for Testing 153.0.8010.12); a CI usa o Google Chrome instalado no runner. Safari (iOS) e Firefox não foram verificados; a homologação deve conferir num iPhone e num Android reais.
- **Busca na página.** A busca (Ctrl+F) e a navegação por cursor usam o retângulo do texto, e não a margem de rolagem dos elementos. Sem `scroll-padding` na raiz, uma ocorrência que já esteja sob o cabeçalho pode não ser rolada para a área livre. Esse caso não foi verificado em navegador.
- **Reserva sem JavaScript.** As reservas da folha foram verificadas com fontes padrão de 12, 14, 16 e 20 px. Com fontes maiores, os textos do cabeçalho podem quebrar linha, e a reserva não acompanha essa quebra. Exemplo medido com JavaScript: com fonte de 24 px, em 1366 px de largura, os links do cabeçalho de computador quebram linha e o cabeçalho mede 109,1 px, enquanto a reserva da folha dá 93,9 px. Sem JavaScript, o início da seção ficaria então cerca de 15 px sob o cabeçalho, com o título ainda visível; essa estimativa não foi medida. O mesmo pode ocorrer nas telas estreitas, com o menu aberto. Com JavaScript, a altura medida cobre esses casos.
- **Tempo de execução.** O módulo novo leva cerca de seis minutos no Chromium (343,7 s na execução final). A suíte da CI tem limite de 60 minutos.

## 7. Comparação visual

As capturas foram geradas pelo Chromium (Playwright) com o mesmo procedimento antes e depois da correção. Em cada caso:

- a landing foi aberta no topo e a página carregou por completo (gráficos desenhados);
- no celular, o menu foi aberto e o link correspondente foi clicado;
- a captura foi feita depois do fim da rolagem, na mesma largura e altura de janela;
- "antes" é o código do `main` (`ae8775b`), servido por uma cópia separada do repositório; "depois" é esta branch;
- a linha âmbar tracejada marca o início medido da seção (`getBoundingClientRect().top`), e o valor no topo de cada metade é a distância medida até a borda inferior do cabeçalho;
- as capturas foram feitas com movimento reduzido, para que o vídeo da demonstração mostre o mesmo quadro (o pôster) nas duas versões.

A landing não tem dados de clientes, e os valores que aparecem nos gráficos e no vídeo são os ilustrativos já publicados na própria página.

| Seção | Largura × altura | Antes (início da seção abaixo do cabeçalho) | Depois | Imagem |
| --- | --- | --- | --- | --- |
| Como funciona | 1366 × 768 | 126,9 px (título a 258,0 px) | −0,1 px (título a 131,0 px) | [2026-11-14_landing_ancoras_como-funciona_1366_antes_depois.png](2026-11-14_landing_ancoras_como-funciona_1366_antes_depois.png) |
| Indicadores | 1366 × 768 | 126,5 px (título a 257,6 px) | 0,5 px (título a 131,6 px) | [2026-11-14_landing_ancoras_indicadores_1366_antes_depois.png](2026-11-14_landing_ancoras_indicadores_1366_antes_depois.png) |
| Demonstração | 1366 × 768 | 126,5 px (título a 257,6 px) | 0,5 px (título a 131,6 px) | [2026-11-14_landing_ancoras_demonstracao_1366_antes_depois.png](2026-11-14_landing_ancoras_demonstracao_1366_antes_depois.png) |
| Planos | 1366 × 768 | 126,3 px (título a 257,4 px) | 0,3 px (título a 131,4 px) | [2026-11-14_landing_ancoras_planos_1366_antes_depois.png](2026-11-14_landing_ancoras_planos_1366_antes_depois.png) |
| Como funciona | 390 × 844 | 133,9 px (título a 246,4 px) | −0,1 px (título a 112,4 px) | [2026-11-14_landing_ancoras_como-funciona_390_antes_depois.png](2026-11-14_landing_ancoras_como-funciona_390_antes_depois.png) |
| Indicadores | 390 × 844 | 134,2 px (título a 246,7 px) | 0,2 px (título a 112,7 px) | [2026-11-14_landing_ancoras_indicadores_390_antes_depois.png](2026-11-14_landing_ancoras_indicadores_390_antes_depois.png) |
| Demonstração | 390 × 844 | 134,4 px (título a 247,0 px) | 0,4 px (título a 113,0 px) | [2026-11-14_landing_ancoras_demonstracao_390_antes_depois.png](2026-11-14_landing_ancoras_demonstracao_390_antes_depois.png) |
| Planos | 390 × 844 | 134,6 px (título a 247,1 px) | −0,4 px (título a 112,1 px) | [2026-11-14_landing_ancoras_planos_390_antes_depois.png](2026-11-14_landing_ancoras_planos_390_antes_depois.png) |

Nas imagens de computador, a parte de cima mostra o antes e a de baixo, o depois. Nas de celular, o antes fica à esquerda e o depois à direita.

## 8. Reprodução no sistema empresarial

A correção deve ser refeita no projeto empresarial a partir dos componentes equivalentes, sem `git clone` para substituir a base existente e sem copiar arquivos inteiros deste repositório. Procedimento recomendado:

1. **Localizar os componentes.** Identificar o template da landing, a folha de estilos e os scripts equivalentes a `templates/landing.html`, `static/css/landing.css`, `static/js/landing.js` e `static/js/landing-video.js`. Confirmar o seletor do cabeçalho fixo (aqui, `.nexo-header` com `position: sticky; top: 0`), os identificadores das âncoras do menu e do rodapé, o botão do menu móvel e a função que mostra e esconde os links (aqui, `setMenu`).
2. **Mapear as compensações existentes.** Procurar `scroll-padding`, `scroll-margin`, `scrollIntoView`, `scrollTo` e tratadores de `click` em links `href="#..."` no CSS e no JavaScript da landing. Cada compensação encontrada deve ser substituída, e não somada a outra.
3. **Medir o cabeçalho real.** Em cada faixa de largura das media queries do cabeçalho, medir `getBoundingClientRect().height` do cabeçalho com e sem JavaScript (sem JavaScript, o menu móvel pode ficar aberto) e identificar o item mais alto de cada linha, incluindo as alturas mínimas (`min-height`) dos controles. A partir dessa composição, escrever a reserva `--nexo-header-height` de cada faixa em `calc()` com `rem`, conferindo que o resultado com fonte de 16 px coincide com a medição (seção 5.2).
4. **Aplicar o mecanismo único.** Remover o `scroll-padding-top` da raiz e as margens de rolagem antigas e declarar `main, main *, footer, footer * { scroll-margin-top: var(--nexo-header-height); }`, mais 8 px para os controles focáveis (seção 5.1), com os nomes de elementos do projeto empresarial. Nenhum elemento dentro do cabeçalho fixo deve receber a margem.
5. **Atualizar a altura pelo script do menu.** Acrescentar a função equivalente a `syncHeaderOffset()` e chamá-la ao iniciar, num `ResizeObserver` do cabeçalho e dentro da função que abre e fecha o menu móvel, logo depois de mostrar ou esconder os links. Se a landing empresarial dimensionar algum conteúdo pela altura do cabeçalho, como o vídeo aqui, gravar essa medida na mesma função.
6. **Rolagem imediata durante o carregamento.** Se a landing empresarial carregar gráficos, fontes ou outros conteúdos que mudam de altura depois da primeira renderização, acrescentar a regra `html.landing-enhanced:not(.landing-smooth-scroll) { scroll-behavior: auto; }` e a classe adicionada um quadro depois do evento `load` (seção 5.3), com a classe que o script do projeto já aplica ao iniciar.
7. **Manter o restante.** Não alterar textos, cores, espaçamentos internos das seções, componentes, gráficos ou vídeos. A rolagem suave e o bloco `prefers-reduced-motion` existentes continuam valendo.
8. **Validar.** Escrever no projeto empresarial, com os utilitários de teste dele, os cenários e as verificações da seção 6.3: as mesmas telas, as medições com `getBoundingClientRect()` e as tolerâncias. O módulo `tests/test_landing_ancoras_navegador.py` serve de referência, mas depende de três utilitários deste repositório: o servidor e o banco de teste (`tests/deploy_support.py`), as cópias da CDN com SRI conferido (`tests/test_contratos_navegador.py`) e a liberação de conexões locais (`tests/test_nexobot_navegador.py`). Executar também os testes da landing e de navegador do próprio projeto.

## 9. Reversão

Para desfazer somente esta correção:

1. Reverter os commits de código desta branch com `git revert`, do mais novo para o mais antigo e sem reescrever o histórico: `git revert --no-edit 849afb3 d5c8c09 fdd58e0`. Se o PR for integrado por merge, `git revert -m 1 <commit do merge>` desfaz tudo de uma vez. Reverter só um dos commits deixa a correção pela metade. O commit de documentação pode ser mantido como registro ou revertido junto.
2. Se a reversão precisar ser manual:
   - **`static/css/landing.css`:** restaurar `html { scroll-behavior: smooth; scroll-padding-top: 100px; }` e `section[id], main[id], footer[id] { scroll-margin-top: 100px; }`. Remover a variável `--nexo-header-height` (o token em `:root` e as redefinições nas media queries de 1100, 992 e 640 px), as duas regras novas de `scroll-margin-top` e a regra `html.landing-enhanced:not(.landing-smooth-scroll)`.
   - **`static/js/landing.js`:** remover `htmlRoot`, `header`, `demoFrame`, `syncedHeight` e `syncHeaderOffset`, as duas chamadas de `syncHeaderOffset()` (dentro de `setMenu` e logo depois do bloco do menu), o `ResizeObserver` (e a alternativa por `resize`) e a função `enableSmoothScroll` com o seu `load`. A primeira linha da função volta a ser `document.documentElement.classList.add('landing-enhanced');`.
   - **Testes:** remover `tests/test_landing_ancoras_navegador.py`, porque ele descreve o comportamento corrigido e falha no código anterior.
3. Nenhuma outra parte do sistema depende dessas regras. Não há migração de banco, configuração do Render ou do Supabase nem dependência nova a desfazer. O `landing-video.js` não foi alterado e volta a ser o único a gravar `--nexo-demo-header`.
4. Depois da reversão, `git diff ae8775b -- static/css/landing.css static/js/landing.js` deve sair vazio, se nenhuma outra alteração nesses arquivos tiver sido integrada depois. Executar também `tests.test_landing_commercial`, `tests.test_landing_video_commercial` e os demais testes de navegador para confirmar o retorno ao estado anterior.

## 10. Resultado

| Critério de aceitação | Situação | Evidência |
| --- | --- | --- |
| 1. O cabeçalho continua fixo | Cumprido | `position: sticky; top: 0` inalterado; topo do cabeçalho em 0 px em todas as medições dos testes |
| 2. Início funciona corretamente | Cumprido | Página no topo (`scrollY` 0) e apresentação inicial logo abaixo do cabeçalho, pelo menu, pelo rodapé e por "Voltar ao início" |
| 3. Como funciona alinhado | Cumprido | Início da seção a no máximo 0,5 px da borda do cabeçalho nas 14 telas |
| 4. Indicadores alinhado | Cumprido | Idem |
| 5. Demonstração alinhada | Cumprido | Idem, com o vídeo e os gráficos preservados |
| 6. Planos alinhado | Cumprido | Idem, inclusive no celular deitado, depois da correção do vídeo |
| 7. Conteúdo anterior fora da área visível | Cumprido | Nenhum elemento da seção anterior abaixo da borda do cabeçalho (verificação em todos os testes de alinhamento) |
| 8. Títulos não encobertos | Cumprido | Título abaixo da borda e inteiro na tela sempre que cabe nela |
| 9. Sem espaços verticais excessivos | Cumprido | Entre a borda do cabeçalho e a etiqueta da seção há só o espaçamento interno da seção (80 ou 64 px); título a 131 ou 112 px do cabeçalho, antes de 246 a 260 px |
| 10. Rolagem suave mantida | Cumprido, com a ressalva da seção 6.6 | Animação verificada depois do carregamento; durante o carregamento a rolagem é imediata, de propósito |
| 11. Navegação móvel funcional | Cumprido | Menu abre e fecha ao escolher o link; o cabeçalho volta à altura fechada e a seção não se desloca depois, também no celular deitado |
| 12. Âncoras diretas funcionam | Cumprido | `/#como-funciona`, `/#indicadores`, `/#demonstracao` e `/#planos` alinhados após o carregamento completo e na recarga; também a partir de "Como obter acesso" |
| 13. Histórico correto | Cumprido | Voltar e Avançar restauram a posição exata de cada entrada; o clique repetido não cria entrada |
| 14. Identidade visual inalterada | Cumprido | Nenhuma cor, texto, logo, espaçamento ou componente alterado; diferença só na posição de parada da rolagem (seção 7) |
| 15. Vídeos e gráficos funcionando | Cumprido | `test_landing_video_commercial` (vídeo) e `test_landing_commercial` (gráficos e conteúdo) aprovados na regressão completa; o `landing-video.js` não foi alterado |
| 16. Sem regressões nos testes executados | Cumprido | Regressão completa: 1.711 aprovados, 11 pulados (PostgreSQL privado e capturas opcionais) e 1 erro de ambiente, a versão do pip, que também ocorre no `main` (seção 6.4.5) |
| 17. Documentação técnica completa | Cumprido | Este documento |
| 18. Implementação em Pull Request | Cumprido | Branch `fix/landing-ancoras-alinhamento-header` |
| 19. Nenhum componente empresarial alterado | Cumprido | Alterações só neste repositório de testes, sem acesso ao projeto empresarial, ao Supabase ou ao Render |

**Pendências para a homologação**

- Conferir a navegação num celular e num tablet reais (iOS/Safari e Android/Chrome). Os testes automatizados usaram o Chromium.
- Avaliar se o espaçamento interno das seções (80 e 64 px) deve ser reduzido para aproximar o título do cabeçalho (seção 5.4).
- Publicar no ambiente de testes do Render só depois do merge aprovado. Esta entrega não executou merge nem deploy.
