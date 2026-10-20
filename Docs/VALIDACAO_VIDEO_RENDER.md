# Validação do vídeo promocional no NEXO Render

> **Estado atual: player v3.** O comportamento vigente, os testes em navegador real e as medições de banda estão na seção [Player v3 — correção definitiva](#player-v3--correção-definitiva-20-de-outubro-de-2026), no fim deste documento. As seções anteriores são históricas: descrevem versões com `preload="none"` sob clique (PR inicial), `autoplay` com controles nativos (PR #3) e `autoplay` com áudio condicionado (PR #4).

Execução em 20 de outubro de 2026, a partir do commit `32aa11a` (igual a `origin/main`), em duas etapas:
integração do vídeo (commit `3fcbc80`) e otimização do carregamento (commit seguinte).
Fonte: `Helio965/Nexo-Faturamento-Inteligente`, commit `c8b0735` (introdução do vídeo),
sem alterações posteriores nos arquivos transferidos até o `HEAD` `015981e`.

## Escopo

- Integração: `static/video/` (MP4, GIF, PNG), `tools/nexo-motion/` (17 arquivos),
  `templates/landing.html` (+28 linhas), `static/css/landing.css` (+30), `README.md` (+23) e este documento.
  Os blocos HTML/CSS são as linhas exatas do commit de origem, gravadas com o CRLF dos arquivos de destino.
- Otimização: `templates/landing.html` (2 linhas: `preload` e `poster`), nova capa
  `static/video/nexo_demo_poster.jpg`, dois parágrafos da seção audiovisual do `README.md` e este documento.
- Nenhuma alteração em `render.yaml`, `wsgi.py`, `app.py`, `config.py`, `requirements*.txt`, `models.py`,
  `storage.py`, `blueprints/`, `migrations/`, `static/js/`, testes, variáveis de ambiente ou banco de dados.

## Integridade das mídias

| Arquivo | Verificação | Bytes | SHA-256 |
|---|---|---:|---|
| `nexo_demo_motion.mp4` | 40,000 s · 1.200 frames · 1920×1080 · 30 fps · H.264 High · yuv420p/TV · AAC LC 48 kHz estéreo · `moov` antes de `mdat` | 11.996.145 | `f7756d2507356c2164409190d0d618d630dba2d83a7d2e012aa38ee909c888fb` |
| `nexo_demo_preview.gif` | 6 s · 72 frames · 640×360 · NETSCAPE2.0 (loop) | 2.818.872 | `f9400ab49d15fd79f64e772ff51ea509ebb545598b1f787d133aa4a51ccf3c84` |
| `nexo_demo_poster.png` | 1920×1080 · RGB · sem metadados de texto | 1.381.547 | `f84ca07f06cab6757649c64f98d5946d3a472e5b3c7263d022d8caef55126ce5` |
| `nexo_demo_poster.jpg` | 1920×1080 · 4:4:4 · progressivo · sem EXIF/XMP · derivado do PNG | 121.782 | `0e3882b673f95e4826235fc04b7d881459f19d7a5d573cfb8c371e3234087a4d` |

MP4, GIF e PNG são idênticos aos da origem, decodificados integralmente sem erros e não são ponteiros
Git LFS; o MP4 não foi recomprimido na otimização. `tools/nexo-motion/` é idêntico à origem;
`node_modules/`, `.npm-cache/`, `out/`, `build/` e `public/audio.wav` continuam ignorados.

## Otimização de banda

### Problema identificado

Com `preload="metadata"` e a capa PNG, cada visita à landing, sem rolar nem tocar no player, transferia
1,59 a 2,50 MB de arquivos locais (página sem vídeo: 66.851 bytes): 1,38 MB da capa e de 164 KB a
1 MiB do MP4 pré-carregado pelo navegador, embora o `moov` tenha 44,8 KB. A capa também atrasava o
evento `load` para 2,7 s em 4G e 8,3 s em rede lenta.

### Alterações

1. `preload="none"` no `<video>`; controles nativos, `playsinline`, proporção 16:9, legenda e link de
   download preservados, sem `autoplay`.
2. Capa da landing em JPEG (qualidade 80, cor 4:4:4, progressivo), gerada a partir do PNG original com o
   Pillow 13.0.0 do `requirements.txt` (comando no README). O PNG original foi preservado.

A WebP foi avaliada primeiro (q82: 50.408 bytes; q92: 89.468 bytes), mas a tabela interna de tipos do
Python 3.12 não conhece `.webp` (entrou no 3.13). Em um host sem `/etc/mime.types`, simulado aqui, o Flask
serve a WebP como `application/octet-stream`. O Chrome ainda a exibe por detecção de conteúdo, mas o
cabeçalho fica incorreto e outros navegadores não foram testados. Registrar o tipo exigiria alterar
`app.py`/`config.py`, protegidos nesta tarefa. O JPEG é servido como `image/jpeg` pela tabela interna,
com ou sem `/etc/mime.types`, e é suportado por todos os navegadores.

| Capa | Bytes | PSNR (dB) | SSIM |
|---|---:|---:|---:|
| PNG original | 1.381.547 | — | — |
| WebP q92 (avaliada) | 89.468 | 40,64 | 0,974 |
| **JPEG q80 4:4:4 (adotada)** | **121.782** | **41,45** | **0,973** |

Na ampliação de 4× de textos e traços, o JPEG 4:4:4 manteve o slogan laranja mais próximo do original
que a WebP; traços roxos e textos cinza ficaram equivalentes. A capa ficou 91,2% menor que o PNG.

### Medições do carregamento inicial

Google Chrome 155, cache vazio, sem rolagem nem interação, 6 s após o `load`, mediana de 3 execuções.
Bytes locais = corpo HTTP recebido do Flask, que o Render transmitiria. Redes simuladas via CDP:
4G = 5 Mbps / 70 ms; lenta = 1,6 Mbps / 150 ms. Os CDNs (Bootstrap, Plotly, fontes) vieram de cache
local, sem limitação, e são iguais nas três versões.

| Cenário | Sem vídeo | Antes (PNG + `metadata`) | Final (JPEG + `none`) |
|---|---:|---:|---:|
| 1440 px, local | 66.851 B · 767 ms | 1.585.242–2.499.049 B · 818 ms | 190.704 B · 803 ms |
| 1440 px, 4G | 66.851 B · 841 ms | 1.614.670 B · 2.736 ms | 190.704 B · 875 ms |
| 1440 px, lenta | 66.851 B · 948 ms | 1.614.670 B · 8.259 ms | 190.704 B · 1.125 ms |
| 390 px, local | 66.851 B · 767 ms | 1.650.778–2.499.049 B · 816 ms | 190.704 B · 758 ms |
| 390 px, 4G | 66.851 B · 882 ms | 1.614.670 B · 2.735 ms | 190.704 B · 855 ms |
| 390 px, lenta | 66.851 B · 909 ms | 1.614.670 B · 8.255 ms | 190.704 B · 1.130 ms |

- Requisições locais: 4 sem vídeo, 6 antes (inclui 1 ao MP4), 5 na versão final (0 ao MP4).
- Requisições externas reais: 11 nas três versões. O CDP lista 6 entradas a mais nas versões com vídeo:
  URIs `data:image/svg+xml` dos ícones dos controles nativos, sem tráfego de rede.
- Redução por visita: 88,0% a 92,4% em relação à versão anterior; acréscimo de 123.853 bytes em relação
  à página sem vídeo. Capa pronta em cerca de 40 ms (local), 455 ms (4G) e 1,1 s (lenta).

### Início da reprodução após o play

MP4 original no Chrome 155, 1440 px, do evento `play` (acionado pelo botão nativo) ao primeiro quadro
exibido, mediana de 3 execuções. Medido com `preload="none"` antes da troca da capa WebP pelo JPEG; a
capa já está carregada nesse momento e não interfere no tempo após o clique.

| Rede | Antes (`metadata`) | Final (`none`) | Travamentos nos primeiros 15 s |
|---|---:|---:|---|
| Local | 78 ms | 139 ms | 0 nas duas |
| 4G | 81 ms | 443 ms | 0 nas duas |
| Lenta | 90 ms | 1.081 ms | 3 nas duas (posição ≈ 10,4 s após 15 s) |

A taxa média do MP4 (cerca de 2,4 Mbps) supera 1,6 Mbps, então a rede lenta trava nas duas versões;
isso independe do `preload`.

### Comportamento de `preload="none"`

- No Chrome 155 (390, 768 e 1440 px), nenhuma requisição ao MP4 antes da interação; `readyState` 0.
  Outros navegadores podem tratar o atributo de forma diferente.
- Antes do play, a barra mostra `0:00` sem a duração total.
- O botão de play nativo e a tecla Espaço iniciam a reprodução. O clique no meio da área do vídeo não
  inicia no Chrome desktop enquanto os metadados não foram carregados (com `preload="metadata"`,
  iniciava). No toque, o primeiro toque exibe os controles, como na versão anterior. Nenhum JavaScript
  foi adicionado, para não conflitar com o clique nativo de outros navegadores.

## Aplicação Flask (ambiente isolado)

- Suíte `python -B -m unittest discover -t . -s tests`: 49 testes executados e aprovados, 0 falhas,
  0 erros, 0 ignorados, na linha de base, na integração e na versão final (SQLite temporário, rede
  bloqueada, `.env` não lido). Os testes conferem os arquivos referenciados por `url_for('static', ...)`.
- Gunicorn com o comando do `render.yaml` (`-w 1 --threads 50 --timeout 180`, `wsgi:app`),
  `FLASK_ENV=development` e SQLite temporário: `/`, `/healthz`, `/healthz/db`, `/como-aderir` e
  `/auth/login` com HTTP 200; rotas de ADMIN e CLIENTE continuam redirecionando anônimos ao login.
- Mídia pública sem login: MP4 `video/mp4`, GIF `image/gif`, PNG `image/png`, JPEG `image/jpeg`,
  HTTP 200 e mesmo SHA-256 dos arquivos do repositório; JPEG e MP4 mantêm o MIME sem `/etc/mime.types`.
- `Range` no MP4: intervalos retornam 206 com os bytes exatos, `bytes=0-` retorna 206 com
  `Accept-Ranges: bytes`, intervalo fora do arquivo retorna 416 e `If-None-Match` retorna 304.
- Memória do worker: 129,6 MB antes e 130,4 MB durante 40 transferências simultâneas do MP4 (streaming).

## Navegadores

- Google Chrome 155.0.8059.84, pacote oficial extraído localmente (`canPlayType` H.264/AAC: `probably`),
  com o MP4 original em 390, 768 e 1440 px: capa JPEG 1920×1080 carregada, player 16:9 (razão 1,7778)
  sem overflow horizontal, sem `autoplay`/`muted`, decodificação 1920×1080 com áudio AAC, pausa,
  volume e mudo, avanço a 30 s e retorno a 5 s com requisição 206, reprodução até o fim sem quadros
  corrompidos, tela cheia, download com o SHA-256 original, sete seções, três gráficos Plotly, dashboard
  visível, nenhuma âncora quebrada, nenhum ID duplicado e zero erros de JavaScript.
- Chromium 141 (Playwright, primeira etapa): build sem H.264/AAC. Validou layout e estrutura com o MP4
  real; a mecânica dos controles foi testada com uma cópia WebM temporária, que não comprova o MP4.
- A página sem vídeo (commit inicial) teve o mesmo resultado em erros, gráficos, seções e dashboard.

## Impacto de hospedagem no Render Free

A documentação de banda do Render indica 5 GB/mês de saída no workspace Hobby, contando respostas HTTP
de web services; sem forma de pagamento, o excedente desliga os serviços até o mês seguinte.

- Antes: o acréscimo de 1,52 a 2,43 MB por visita esgotaria 5 GiB com 2.207 a 3.535 visitas por mês.
- Final: o acréscimo de 123.853 bytes por visita corresponde a cerca de 43.300 visitas por mês;
  a página inteira (190.704 bytes locais), a cerca de 28.100 visitas.
- Cada reprodução completa continua transferindo 12 MB (cerca de 447 reproduções por mês para 5 GiB).
  Esse é o risco remanescente, proporcional ao uso real do player.
- `Cache-Control: no-cache` (padrão do Flask): revisitas revalidam com 304; após um deploy, o ETag muda
  e os arquivos são baixados novamente. O GIF do README é servido pelo GitHub.
- Se as reproduções crescerem, a alternativa é hospedar o MP4 fora do Render, o que altera a arquitetura
  e depende de decisão do proprietário.

## Gatilhos de implantação

- `render.yaml`: `branch: main`, `autoDeployTrigger: 'off'`, sem configuração de prévias; o repositório
  não tem workflows em `.github/`. Push em outra branch não altera a `main`.
- O `render.yaml` não comprova a configuração atual do painel. Segundo a documentação do Render, o
  auto-deploy é definido nas configurações do serviço e as prévias de Pull Request são opcionais e
  desligadas por padrão; se estiverem ativadas, a instância de prévia copia as variáveis do serviço
  base, inclusive o `DATABASE_URL` de produção. Recomenda-se conferir no painel: Auto-Deploy desligado
  e Pull Request Previews desligado.

## Limites

- Firefox, Safari/iOS, Edge e aparelhos físicos não foram testados; o Chrome rodou em modo headless e o
  modo móvel foi emulado.
- Redes lentas foram simuladas via CDP; os tempos refletem apenas os arquivos servidos pelo Flask.
- Não houve deploy: o comportamento foi validado no Gunicorn local, não na infraestrutura do Render.

## Atualização: demonstração contínua, sem link de download

- O player da página pública usa `autoplay`, `muted`, `loop`, `playsinline`, `controls` e `controlslist="nodownload"`.
- Foram removidos o link de download na legenda, a âncora de fallback HTML5 e os links diretos para MP4 no README. A prévia GIF do README não é mais clicável.
- A reprodução começa sem som por política de autoplay dos navegadores; o usuário pode pausar ou ativar o som nos controles. O loop recomeça quando o vídeo termina, salvo interrupções impostas pelo navegador, dispositivo ou usuário.
- `controlslist="nodownload"` não é DRM. O MP4 permanece um arquivo estático público, tecnicamente recuperável por usuários com ferramentas de rede.
- A reprodução automática pode solicitar cerca de 12 MB ao iniciar e, conforme cache e comportamento do navegador, realizar transferências adicionais ao repetir. Não reutilize as estimativas anteriores de banda por visita sem uma nova medição; monitore consumo no Render.
- Nenhum componente de backend, banco de dados, runtime, armazenamento, migrações ou hospedagem foi alterado nesta atualização.
- Esta atualização foi revisada estaticamente no GitHub; testes de reprodução em navegador e regressão local **ainda precisam ser executados** antes da aprovação do deploy.

## Atualização adicional: áudio condicionado à visibilidade integral

- Novo player sem controles nativos e com botão de tela cheia personalizado. A única ação inicial extra é **Ativar som**, exigida pelos navegadores que bloqueiam áudio automático. O vídeo continua em loop silencioso enquanto não houver liberação.
- O JavaScript verifica que **todo o retângulo do vídeo** está dentro da viewport, considera a área coberta pelo cabeçalho sticky, usa `IntersectionObserver` com `threshold: 1` e silencia o vídeo na rolagem, no redimensionamento e quando a aba perde a visibilidade.
- Quando volta a ficar integralmente visível, tenta restaurar o som autorizado. Não há tentativa de contornar as restrições de autoplay com áudio.
- Ao usar tela cheia, a área do cabeçalho não entra no cálculo e o áudio permanece autorizado enquanto a aba estiver visível.
- O navegador controla o formato de tela cheia e, no iOS, poderá fornecer uma interface nativa diferente. Se a API não estiver disponível, o botão deve ser desativado ou usar o fallback permitido.
- **Limite funcional:** `muted` silencia a faixa de áudio, mas NÃO impede o download dos respectivos bytes que estão muxados dentro do MP4; essa separação exigiria arquitetura adicional.
- **Risco:** reprodução em loop, mesmo fora de vista, pode elevar consumo de banda e bateria. Vídeos maiores que a viewport nunca atingiriam 100% visível; o CSS limita a largura do player em função da altura disponível.
- **Acessibilidade:** remover a possibilidade de pausar uma animação automática com duração superior a cinco segundos viola WCAG 2.2 SC 2.2.2 para conteúdo não essencial; rever antes de afirmar conformidade.
- Esta alteração foi analisada estaticamente; o teste de comportamento em navegadores físicos e a medição do novo consumo de dados ainda são **pendentes**.

## Player v3 — correção definitiva (20 de outubro de 2026)

Branch `fix/player-demo-loop-audio-visibilidade`, criada a partir da `main` em `0bcdc93` (merge da PR #4).
Esta seção substitui as duas "Atualizações" anteriores: elas descreviam a intenção da PR #3 e da PR #4,
mas foram validadas apenas estaticamente ou por simulação de DOM.

### Diagnóstico da PR #4

**Deploy (não verificável a partir deste ambiente).** O `render.yaml` usa `autoDeployTrigger: 'off'`.
A PR #4 entrou na `main` em 20/10/2026 às 17:44 (BRT); sem um *Manual Deploy* posterior, a produção
continua com a versão anterior (PR #3: controles nativos e `autoplay muted loop`, sem
`landing-video.js`). Não há acesso ao painel do Render e o endereço público não consta no repositório
(o subdomínio padrão `nexo-faturamento-inteligente.onrender.com` responde 404 com
`x-render-routing: no-server`). O proprietário deve confirmar:

1. Render → serviço → **Events**: commit do último deploy concluído (`0bcdc93` ou posterior para a PR #4).
2. `curl -sI https://<serviço>.onrender.com/static/js/landing-video.js` — 404 indica versão anterior à PR #4.
3. `curl -s https://<serviço>.onrender.com/ | grep -c 'data-player-version="3"'` — `1` indica esta correção.
4. Cache: o Flask serve estáticos com `Cache-Control: no-cache` e ETag; o navegador revalida JS/CSS a cada
   carregamento. Após o deploy, só a navegação por "voltar" (bfcache) pode exibir a página antiga.

**Código (comprovado em Chrome 156 real, `main` e correção servidas lado a lado pelo mesmo Gunicorn).**

| Achado na PR #4 | Evidência medida | Efeito para o visitante |
|---|---|---|
| Uso do atributo `autoplay`: enquanto não há interação, o Chrome pausa o vídeo mudo totalmente fora da tela e em aba oculta | 0,0 s de avanço em 4 s fora da tela; 0,0 s em 5 s de aba oculta (tempo parado em 2,57 s e 2,46 s) | Quem não clica em "Ativar som" vê o vídeo parar ao rolar e retomar do mesmo ponto — o loop "não continua" |
| O script só chamava `play()` dentro do clique de som | Após o clique, o mesmo vídeo continuou fora da tela (6,0 s em 6 s) | O defeito some justamente para quem clicou, o que dificulta reproduzi-lo |
| `visualViewport` ignorado | Zoom por pinça 2× (móvel emulado): áudio a −21,9 dBFS com metade do vídeo fora da área visível | Som com parte do vídeo fora da tela |
| Pré-carga forçada pelo `autoplay` | 4,4 a 6,6 MB do MP4 baixados nos 3 s após abrir a landing, sem rolar até o vídeo | Banda do Render consumida por todo visitante |
| Testes da PR | Somente simulação de DOM (declarado na própria PR) | Comportamento real não verificado |

O cálculo de visibilidade da PR #4 funcionava no Chrome desktop depois da autorização (1 px fora
silenciava; o retorno restaurava o som). No iPhone, a política documentada do WebKit também pausa vídeos
`autoplay` mudos fora da tela, então o mesmo sintoma é esperado (não testado em aparelho).

### Nova lógica (`static/js/landing-video.js`)

- **Máquina de estados**: `playback` (`idle`, `starting`, `playing`, `interrupted`, `needs-gesture`,
  `error`) e `audio` (`unknown`, `probing`, `needs-gesture`, `confirming`, `allowed`), com as entradas
  `fullyVisible`, `fullscreen` e `pageVisible`. Só `setMuted()` escreve em `video.muted`, e só quando o
  valor muda. O estado é exposto em `data-playback`, `data-audio`, `data-visibility` e
  `data-fullscreen` no quadro do player.
- **Reprodução**: sem `autoplay`; `preload="none"`; o script chama `play()` mudo quando o vídeo chega a
  uma altura de tela da área visível e nunca chama `pause()`. Loop pelo atributo `loop` (com reforço no
  evento `ended`). Pausas involuntárias são retomadas apenas em pontos de controle — aba volta a ficar
  visível, `pageshow`, `resume`, `online`, entrada/saída de tela cheia —, nunca na rolagem.
- **Visibilidade integral** (`computeFullyVisible`): retângulo do `<video>` contra a `visualViewport`
  (zoom por pinça, teclado virtual), sobreposição do cabeçalho fixo (ignorada em tela cheia),
  ancestrais com `overflow` diferente de `visible` (bordas fracionárias, sem os inteiros arredondados de
  `clientWidth/clientHeight`) e aba visível. Tolerância de meio pixel físico (`0,5 / (DPR × escala)`, no
  máximo 0,5 px CSS): absorve arredondamentos sem permitir som com 1 px fora. Rolagem e
  redimensionamento são agrupados em um `requestAnimationFrame`; o `IntersectionObserver` dispensa o
  cálculo quando o vídeo está longe da tela; `ResizeObserver` acompanha player e cabeçalho.
- **Permissão de áudio**: com 100% visível, consulta `navigator.getAutoplayPolicy('mediaelement')` quando
  existe (Firefox); senão, uma sonda de 50 ms de silêncio (`data:` URI) em elemento de áudio separado
  (Chrome, Edge, Safari). Permitido: o som entra quando a sonda termina. Bloqueado: aparece
  **Ativar som da demonstração**; o clique desmuta e chama `play()` dentro do gesto e só marca
  `allowed` quando o navegador confirma. Uma pausa logo após desmutar é verificada com um `play()`
  com som: só `NotAllowedError` devolve o player ao mudo com o botão. Nada é salvo em `localStorage`.
- **Bloqueio até da reprodução muda** (ex.: modo de pouca energia do iOS): o `NotAllowedError` mostra
  **Reproduzir demonstração** no lugar do botão de som.
- **Tela cheia**: Fullscreen API no quadro do player (`requestFullscreen`/`webkitRequestFullscreen`), sem
  controles nativos; no iPhone, `webkitEnterFullscreen()` (player nativo, ver limitações). Mesmo botão,
  Esc ou mecanismo do navegador para sair; rótulo alterna entre "Expandir vídeo" e "Sair da tela cheia".
- **Erro de mídia**: `NotSupportedError` ou erro da fonte mostram "Não foi possível carregar o vídeo de
  demonstração." sobre a capa, com **Tentar novamente** (somente por clique; sem novas tentativas
  automáticas). Quedas de rede no meio da reprodução são tratadas pelo próprio navegador.

### Interface (`templates/landing.html` e `static/css/landing.css`)

- Permanece: vídeo, capa JPEG (121.782 bytes), botão **Expandir vídeo** no canto inferior direito.
- Temporários: **Ativar som da demonstração** (só quando o navegador exige gesto) e **Reproduzir
  demonstração** (só se o navegador bloquear até a reprodução muda); **Tentar novamente** no erro.
- Removidos: barra nativa, play/pause, avanço/retrocesso, volume, velocidade, Picture-in-Picture,
  reprodução remota, download e menu de contexto de mídia (o vídeo tem `pointer-events: none`).
- Sem JavaScript: capa estática e nenhum botão (todos nascem `hidden`).
- Dimensionamento: largura máxima = `(100svh − cabeçalho − 2 × 16 px − 2 px) × 16/9` (com `vh` como
  alternativa), mínimo de 240 px. A altura do cabeçalho é medida pelo script (`--nexo-demo-header`).

### Limitações impostas pelos navegadores

- **iPhone**: não há tela cheia de elementos; o botão abre o player nativo do iOS, que exibe controles
  do sistema (pausa, busca, volume). Eles não podem ser removidos. Ao sair, o script retoma a reprodução se
  ela tiver sido pausada (previsto no código; não testado em aparelho).
- **Segundo plano**: em aba oculta o som é cortado. Antes de qualquer interação, o Chrome pausa o vídeo
  mudo em segundo plano (economia de energia); o player retoma do mesmo ponto quando a aba volta.
  Após uma interação, o Chrome mantém a reprodução. Safari/iOS e Chrome Android podem pausar vídeos em
  segundo plano; o player retoma ao voltar (previsto; não testado em aparelho).
- **Nova visita/recarga**: a autorização de áudio não é persistida. No Chrome, após recarregar a página,
  o botão de som reaparece (medido).
- **Controles do sistema**: teclas de mídia, central de controle e fones podem pausar; o script não
  impede (retoma apenas nos pontos de controle listados).
- Interações em outros pontos da página contam como gesto no Chrome/Edge: depois delas o som pode
  entrar sem o botão, ao voltar à visibilidade integral (comportamento do navegador).

### Testes reais

**Ambiente.** Contêiner Linux, Xvfb 1920×1080 (sem gerenciador de janelas), Google Chrome
156.0.8078.47 e Microsoft Edge 155.0.4283.62 oficiais (H.264/AAC nativos), Playwright 1.56 e CDP direto.
App local com o comando do `render.yaml` (`gunicorn -w 1 --threads 50 --timeout 180 wsgi:app`),
`FLASK_ENV=development` e SQLite temporário fora do repositório, com dados fictícios — nenhum acesso
ao Supabase. A versão da `main` (PR #4) foi servida em paralelo por outro Gunicorn para comparação.

**Áudio real.** A saída do navegador vai para um *sink* nulo do PulseAudio (48 kHz), gravado
continuamente; o nível RMS é medido em dBFS. A trilha do MP4 tem cerca de −23 dBFS RMS: "audível"
nas tabelas significa −20 a −25 dBFS medidos na saída; "mudo" significa −120 dBFS (silêncio digital).

**Cuidados de método** (sem eles, os testes passariam por motivos errados):

- `page.evaluate()` e `page.screenshot()` do Playwright executam scripts com `userGesture: true` no
  Chromium e concedem ativação de usuário à página, o que libera o áudio sem clique. Todas as leituras
  de estado usam `Runtime.evaluate` com `userGesture: false` e as capturas usam
  `Page.captureScreenshot`; a ativação foi conferida em cada passo (`navigator.userActivation`).
- O Playwright mantém abas em segundo plano como "visíveis" (emulação de foco). Os testes de aba oculta
  usam o Chrome controlado por CDP direto, abrindo outra aba na mesma janela (`visibilityState`
  passa a `hidden`, como na troca real de aba).
- Esc foi enviado pelo X11 (`xdotool`), pois eventos de teclado do CDP não chegam à interface do
  navegador. Sem gerenciador de janelas, a tela cheia ocupa a área da janela e minimizar não pôde
  ser testado.
- Móvel = **emulação** no Chrome (viewport, DPR, toque, user agent). Não substitui Safari/iOS nem
  aparelhos Android reais.

**Resultados no Chrome 156 (correção)** — matriz de comportamento pedida:

| Cenário | Exigido | Medido |
|---|---|---|
| Página carregada | Inicia quando permitido | Inicia mudo a uma altura de tela do vídeo; 0 byte de MP4 antes disso; 1º quadro 0,15–0,25 s após rolar (local/4G) |
| Vídeo termina | Reinicia | Voltas em 40, 80 e 120 s, sem `ended` e sem pausa (busca ao início em cerca de 30 ms) |
| Parcialmente visível | Mudo | −120 dBFS com 1 px fora embaixo ou 1 px sob o cabeçalho |
| 100% visível e autorizado | Som | −21 a −24 dBFS |
| Sai 1 px | Mudo | Silêncio na saída em 87 ms (mediana; máx. 113 ms, 8 ciclos) |
| Volta a 100% | Som restaurado | Som na saída em 84 ms (mediana; máx. 100 ms) |
| Rolagem / fora da tela | Continua | 4,0 s em 4 s e 6,0 s em 6 s fora da tela (PR #4: 0,0 s) |
| Áudio silenciado | Continua | `paused=false` em todas as amostras mudas |
| Clique / duplo clique no vídeo | Não pausa | O alvo do clique é o quadro, não o vídeo; continua tocando; não abre tela cheia |
| Mouse sobre o vídeo | Sem controles | `controls=false`; captura da faixa inferior sem barra |
| Tentar avançar / mudar volume | Sem controle | Teclas ←, →, ↑, ↓, j, k, l, m, Home, End, 0, 5, f: tempo contínuo, `volume=1`, `muted` inalterado |
| Tela cheia | Expande sem barra | Quadro em tela cheia, rótulo "Sair da tela cheia", som mantido (−22 a −25 dBFS) |
| Sair da tela cheia | Tempo preservado | Esc real, mesmo botão, Enter/Espaço: tempo contínuo em todas as transições |
| Troca de aba | Mudo | Silêncio em 95 ms |
| Volta à aba | Nova verificação | Som em 72 ms (vídeo 100% visível) |
| Navegador bloqueia áudio | Botão temporário | "Ativar som da demonstração" só com 100% visível; some após o clique (som a −22 dBFS) |
| Áudio autorizado | Sem novo clique | 8 ciclos de borda, 3 travessias com a roda do mouse e ±1 px: sem novo clique e sem alternâncias espúrias (0 em 5 s parado na borda) |
| Outras seções | Layout preservado | 5 links do menu, 3 gráficos Plotly da landing, 0 erro de JavaScript |

**Resoluções, zoom e cabeçalho** (Chrome 156; móvel e zoom emulados por viewport + DPR). Em todas, a
posição de 100% visível é alcançável, o botão aparece, as bordas exatas dão som e 1 px fora (embaixo ou
sob o cabeçalho) silencia — som/silêncio medidos na saída: −20,9 a −21,4 dBFS e −120 dBFS.

| Configuração | Altura do vídeo | Cabeçalho | Altura visível | Resultado |
|---|---:|---:|---:|---|
| 1920×1080 | 727,9 px | 74,5 px | 1080 px | Aprovado |
| 1440×900 | 727,9 | 74,5 | 900 | Aprovado |
| 1366×768 | 626,6 | 74,5 | 768 | Aprovado |
| 768×1024 (tablet, DPR 2) | 390,4 | 74,5 | 1024 | Aprovado |
| 390×844 (celular, DPR 3) | 204,8 | 91,9 | 844 | Aprovado |
| 360×640 (celular, DPR 3) | 187,9 | 91,9 | 640 | Aprovado |
| 640×360 (celular deitado) | 249,9 | 74,5 | 360 | Aprovado |
| 1366×768 com zoom de 125%, 150% e 200% | 486,9 / 390,4 / 256,9 | 91,9 / 74,5 / 91,9 | 614 / 512 / 384 | Aprovado |
| 1920×1080 com zoom de 90% | 727,9 | 74,5 | 1200 | Aprovado |
| Cabeçalho alto (≈143 px) em 1366×768 e 390×844 | 589,9 / 204,8 | 142,5 / 143,9 | 768 / 844 | Aprovado |

Com cabeçalho de ≈143 px em 1366×768, a PR #4 nunca alcança 100% de visibilidade (vídeo de 626,6 px
para 625,5 px livres): o botão de som não aparece e o áudio nunca toca. A correção reduz o vídeo para
589,9 px.

Outros casos (Chrome 156): emulação móvel com pinça 2× silencia (a PR #4 mantinha o som); MP4 com 404
mostra o painel de erro em cerca de 0,4 s, com uma única requisição e recuperação por "Tentar
novamente"; sem JavaScript, nenhum botão aparece; Tab + Enter ativa o som e o foco passa para "Expandir
vídeo"; uma interação em outro ponto da página libera o som sem o botão; após recarregar, o botão volta;
com a reprodução muda bloqueada (simulação: `play()` rejeitando `NotAllowedError` sem gesto), aparece
"Reproduzir demonstração" e o clique inicia o vídeo.

**Microsoft Edge 155.0.4283.62**: mesma bateria em modo reduzido — cenário principal, tela cheia
(mouse, Esc real, mesmo botão, teclado), aba oculta, três emulações móveis, 7 configurações da matriz
(1920×1080, 1366×768, 768×1024, 390×844, 360×640, zoom de 125% e cabeçalho alto) e cenários
complementares. Resultados iguais aos do Chrome: som só com 100% visível (−20,9 a −24,2 dBFS),
−120 dBFS com 1 px fora, reprodução contínua fora da tela (4,0 s em 4 s), pausa do Edge em aba oculta
antes de qualquer interação com retomada ao voltar, tela cheia com tempo contínuo, 7/7 na matriz.

**Regressão do NEXO**: suíte `python -B -m unittest discover -t . -s tests` com SQLite temporário —
49 testes aprovados, como na `main`. No Chrome real: `/`, `/como-aderir` e `/auth/login` com HTTP 200;
rotas protegidas redirecionam anônimos ao login; ADMIN acessa dashboard (3 gráficos Plotly), empresas e
análises e recebe 403 na área do cliente; CLIENTE acessa dashboard (4 gráficos), análise publicada (2
gráficos) e histórico e recebe 403 na área do ADMIN; `/healthz`, `/healthz/db`, CSS, JS, capa e MP4 com
HTTP 200 e MIME corretos. Nenhum erro de JavaScript; o único erro de recurso na landing é o
`/favicon.ico` 404, já existente na `main`.

**Não testado** (indisponível neste ambiente): Firefox, Safari (macOS e iOS), aparelhos Android e iPhone
reais. A API `getAutoplayPolicy` (usada no Firefox) e o modo nativo de tela cheia do iPhone não foram
exercitados.

### Acessibilidade (WCAG 2.2)

- **Critério 2.2.2 Pausar, parar, ocultar (nível A)**: conteúdo em movimento que começa sozinho, dura
  mais de 5 s e aparece junto com outro conteúdo precisa de um mecanismo para pausar, parar ou ocultar,
  salvo se for essencial. O player pedido (40 s em loop, sem pausa) **não atende** a esse critério.
  Enquanto essa decisão for mantida, a página não pode ser declarada conforme à WCAG 2.2.
- **Critério 1.4.2 Controle de áudio (nível A)**: áudio automático com mais de 3 s exige meio de pausar
  ou de controlar o volume. Aqui o som só começa após um gesto (botão ou interação na página) e para
  quando o vídeo sai da área visível, mas não há botão de mudo. É um risco a avaliar.
- Atendido no que foi implementado: botões nativos com nome acessível e foco visível, operáveis por
  teclado (Tab, Enter, Espaço) e toque; quando o botão de som some, o foco passa para "Expandir vídeo";
  o vídeo não recebe foco; nenhum atalho global do navegador ou do sistema é capturado.
- **Alternativa para decisão posterior** (não implementada, para não contrariar o requisito atual):
  (1) com `prefers-reduced-motion: reduce`, não iniciar sozinho e mostrar a capa com "Reproduzir
  demonstração"; (2) um botão discreto "Pausar animação", acessível por teclado — é a opção de menor
  impacto visual que atende ao 2.2.2; (3) descrição textual do conteúdo do vídeo.

### Banda e hospedagem

Bytes do MP4 recebidos pelo navegador (eventos de rede do CDP; Chrome 156, 1366×768, sem limitação,
vídeo mudo). O arquivo tem 11.996.145 bytes; a trilha AAC (cerca de 157 kbit/s, ≈ 0,79 MB) é baixada
mesmo com o vídeo mudo, porque está multiplexada no MP4.

| Situação | PR #4 (`main`) | Correção |
|---|---:|---:|
| Abrir a landing sem rolar até o vídeo (3 s) | 4,4 a 6,6 MB | 0 B |
| Primeira volta completa (40 s) | 12,0 MB, 1 requisição | 12,0 MB, 1 requisição (`Range: bytes=0-`) |
| 2ª e 3ª voltas | 0 B adicional | 0 B adicional |
| Fora da tela, sem interação | vídeo pausado (6,3 MB já baixados em 50 s) | vídeo tocando: 7 voltas em 5 min, 12,0 MB no total |
| Recarregar a mesma aba | 0 B | 0 B (cache de mídia do Chrome) |
| Nova sessão do navegador, mesmo perfil | mesmo comportamento do servidor | baixa de novo (206 com o arquivo inteiro) |
| Alternar som, tela cheia e rolagem | — | nenhuma requisição nova |

- **Conexões lentas** (limitação do CDP): primeiro quadro após rolar até o vídeo e tempo travado na primeira volta.

  | Rede | 1º quadro | Travamentos na 1ª volta |
  |---|---:|---|
  | Local | 0,18 s | nenhum |
  | 4G (9 Mbit/s, 60 ms) | 0,25 s | nenhum |
  | "Slow 4G" (1,6 Mbit/s, 150 ms) | 1,0 s | 19,2 s (a volta de 40 s levou 61,7 s) |
  | 3G (0,78 Mbit/s, 300 ms) | 2,0 s | 37,2 s em 60 s (18 s de vídeo exibidos) |

  A taxa média do MP4 (2,4 Mbit/s) supera as duas redes mais lentas; as voltas seguintes não travam,
  pois o arquivo já está no navegador. O estado do player permanece `playing` durante a espera.
- **Queda de rede real** (proxy TCP com 800 kbit/s derrubado por 25 s): o Chrome ficou em espera
  (`waiting`/`stalled`) mostrando o último quadro, sem erro; com a rede de volta, retomou sozinho. O
  player não gerou erros nem tentativas próprias.
- **MP4 indisponível** (404): painel "Não foi possível carregar o vídeo de demonstração." em cerca de 0,4 s, com uma única
  requisição ao arquivo, sem área preta (a capa continua visível) e sem novas tentativas automáticas;
  "Tentar novamente" recupera a reprodução quando o arquivo volta.
- **Cache entre sessões**: o Flask responde `Cache-Control: no-cache` com ETag. Sem `Range`, a
  revalidação devolve 304; com `Range` (o que os navegadores usam para mídia), o Werkzeug devolve
  **206 com o arquivo inteiro** (verificado com `curl`). Por isso cada nova sessão do navegador baixa os
  12 MB novamente; recarregar a mesma aba reaproveitou o cache de mídia do Chrome (0 bytes).
- **Render**: a documentação atual informa 5 GB/mês de saída no plano Hobby; acima disso há cobrança
  por GB (com forma de pagamento) ou suspensão dos serviços até o mês seguinte. 5 GB equivalem a cerca
  de 416 reproduções completas por mês, sem contar o restante do site.

**Melhorias opcionais** (dependem de autorização, por isso não foram aplicadas):

1. Versão mais leve do MP4 para a landing (o original permanece no repositório). Estimativas geradas
   aqui e **não versionadas** (H.264 `preset slow`, AAC; SSIM medido contra o original):

   | Versão | Tamanho | Taxa média | SSIM |
   |---|---:|---:|---:|
   | Original 1080p | 12,0 MB | 2,4 Mbit/s | — |
   | 1080p CRF 26, AAC 128 kbit/s | 5,7 MB | 1,1 Mbit/s | 0,994 |
   | 720p CRF 23, AAC 96 kbit/s | 3,8 MB | 0,76 Mbit/s | 0,985 |
   | 720p CRF 26, AAC 96 kbit/s | 2,4 MB | 0,49 Mbit/s | 0,982 |

   A 720p CRF 23 fica abaixo de 1,6 Mbit/s ("Slow 4G") e triplica as reproduções possíveis na franquia
   de 5 GB; exige aprovação visual (textos finos em tela cheia) antes de substituir a mídia.
2. Cabeçalho de cache longo para `static/video/` com nome versionado, ou 304 também para requisições
   com `Range` — exige alterar `app.py`/`config.py`, fora do escopo autorizado.
3. Hospedar o MP4 em CDN/armazenamento externo — muda a arquitetura de hospedagem.

### Compatibilidade com a infraestrutura

Alterados somente `templates/landing.html`, `static/js/landing-video.js`, `static/css/landing.css`,
`README.md` e este documento. Sem mudanças em `render.yaml`, `wsgi.py`, `app.py`, `config.py`,
`models.py`, `storage.py`, `requirements*.txt`, `blueprints/`, `migrations/`, `etl_processor.py`, no
MP4, no banco/Supabase, em variáveis de ambiente ou nos comandos de build e início. Sem bibliotecas
novas: JavaScript nativo. Nenhum deploy foi feito.

### Pendências antes do deploy

1. Confirmar no painel do Render o commit hoje implantado e fazer o *Manual Deploy* só depois de aprovar
   e mesclar esta correção.
2. Testar em aparelhos e navegadores indisponíveis aqui: iPhone/Safari, Android/Chrome, Safari no macOS
   e Firefox. No iPhone, observar a tela cheia nativa (com controles do sistema), a retomada ao sair dela
   e o modo de pouca energia (botão "Reproduzir demonstração").
3. Decidir sobre acessibilidade (critérios 2.2.2 e 1.4.2) e sobre banda (versão leve do MP4 e/ou cache
   longo do vídeo, que exige alterar `app.py`/`config.py`).
4. Depois do deploy, acompanhar no painel do Render a banda dos primeiros dias.
5. Observações: `/favicon.ico` responde 404 na landing (pré-existente, sem relação com o player); o
   botão "Expandir vídeo" cobre parte da frase "DADOS. ANÁLISE. DECISÃO" gravada no canto inferior
   direito do próprio vídeo (ajuste visual opcional).
