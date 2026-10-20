# Validação do vídeo promocional no NEXO Render

> **Atualização posterior:** a funcionalidade mudou para reprodução automática, muda, em loop, sem links de download na interface. As medições de `preload="none"` e início sob clique descritas abaixo são históricas e **não comprovam o consumo de banda do novo modo autoplay**. A nova configuração deve ser medida antes de publicar em produção.

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
