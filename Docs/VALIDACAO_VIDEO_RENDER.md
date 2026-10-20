# Validação do vídeo promocional no NEXO Render

Execução em 20 de outubro de 2026, a partir do commit `32aa11a` (igual a `origin/main`).
Fonte: `Helio965/Nexo-Faturamento-Inteligente`, commit `c8b0735` (introdução do vídeo),
sem alterações posteriores nos arquivos transferidos até o `HEAD` `015981e`.

## Escopo

- Adicionados: `static/video/` (MP4, GIF, PNG), `tools/nexo-motion/` (17 arquivos) e este documento.
- Modificados: `templates/landing.html` (+28 linhas), `static/css/landing.css` (+30), `README.md` (+23).
- Os blocos HTML/CSS são as linhas exatas do commit de origem, gravadas com o CRLF dos arquivos de destino.
- Nenhuma alteração em `render.yaml`, `wsgi.py`, `app.py`, `config.py`, `requirements*.txt`,
  `models.py`, `storage.py`, `blueprints/`, `migrations/`, `static/js/` ou banco de dados.

## Integridade das mídias

| Arquivo | Verificado com ffprobe/ffmpeg | Bytes | SHA-256 |
|---|---|---:|---|
| `nexo_demo_motion.mp4` | 40,000 s · 1.200 frames · 1920×1080 · 30 fps · H.264 High · yuv420p/TV · AAC LC 48 kHz estéreo · `moov` antes de `mdat` | 11.996.145 | `f7756d2507356c2164409190d0d618d630dba2d83a7d2e012aa38ee909c888fb` |
| `nexo_demo_preview.gif` | 6 s · 72 frames · 640×360 · NETSCAPE2.0 (loop) | 2.818.872 | `f9400ab49d15fd79f64e772ff51ea509ebb545598b1f787d133aa4a51ccf3c84` |
| `nexo_demo_poster.png` | 1920×1080 · RGB · sem metadados de texto | 1.381.547 | `f84ca07f06cab6757649c64f98d5946d3a472e5b3c7263d022d8caef55126ce5` |

Os três arquivos são idênticos aos da origem, foram decodificados integralmente sem erros
e não são ponteiros Git LFS. `tools/nexo-motion/` é idêntico byte a byte à origem; `node_modules/`,
`.npm-cache/`, `out/`, `build/` e `public/audio.wav` continuam ignorados.

## Aplicação Flask (ambiente isolado)

- Suíte `python -B -m unittest discover -t . -s tests`: 49 testes aprovados antes e depois da alteração
  (SQLite temporário, rede bloqueada, `.env` não lido). O teste de assets públicos já baixa o MP4.
- Gunicorn com o comando do `render.yaml` (`-w 1 --threads 50 --timeout 180`, `wsgi:app`),
  `FLASK_ENV=development` e SQLite temporário: `/`, `/healthz`, `/healthz/db`, `/como-aderir` e
  `/auth/login` com HTTP 200; rotas de ADMIN e CLIENTE continuam redirecionando anônimos ao login.
- Mídia pública sem login: MP4 `video/mp4`, GIF `image/gif`, PNG `image/png`, HTTP 200 e mesmo SHA-256.
- `Range`: `bytes=0-1023`, intervalo no meio e sufixo retornam 206 com os bytes exatos; `bytes=0-`
  retorna 206 com `Accept-Ranges: bytes`; intervalo fora do arquivo retorna 416; `If-None-Match` retorna 304.
- Memória do worker: 129,6 MB antes e 130,4 MB durante 40 transferências simultâneas do MP4 (streaming).

## Navegador

Chromium 141 (Playwright), larguras 390, 768 e 1440 px. Esta build não inclui H.264/AAC
(`canPlayType` vazio para MP4), por isso o teste foi dividido:

- MP4 real: sem overflow horizontal, player 16:9 (razão 1,7778), capa 1920×1080 carregada,
  `controls`, `playsinline`, `preload="metadata"`, sem `autoplay`/`muted`, pausado após o carregamento,
  dentro de `#demonstracao` antes do dashboard, sem IDs duplicados e sem erros de JavaScript.
  O download pelo link da legenda gerou `nexo_demo_motion.mp4` com o SHA-256 original.
- Cópia temporária fora do repositório, com o vídeo convertido para WebM/VP9 só para esta build:
  reprodução por clique, pausa, volume/mudo, avanço a 30 s e retorno a 5 s (requisições 206),
  reprodução até o fim sem quadros corrompidos, áudio decodificado e tela cheia. No toque (390 px),
  o primeiro toque exibe os controles nativos, comportamento padrão do Chrome móvel.
- A página sem o vídeo (commit inicial) apresentou o mesmo resultado: zero erros de JavaScript,
  três gráficos Plotly, as mesmas sete seções e o dashboard visível.

## Impacto de hospedagem no Render Free

A documentação de banda do Render indica 5 GB/mês de saída no workspace Hobby, contando respostas
HTTP de web services; sem forma de pagamento, o excedente desliga os serviços até o mês seguinte.

- Carregamento inicial, sem rolar nem tocar no player: assets locais passam de cerca de 67 KB para
  2,5 MB (capa PNG 1,38 MB e cerca de 1 MiB do MP4 bufferizado pelo navegador, embora o `moov`
  tenha 44,8 KB). Aproximadamente 2.200 visitas por mês consumiriam 5 GiB só com essa diferença.
- Cada reprodução completa transfere 12 MB: aproximadamente 450 reproduções por mês consomem 5 GiB.
- Cabeçalho `Cache-Control: no-cache` (padrão do Flask): revisitas revalidam com 304; após um deploy,
  o ETag muda e o arquivo é baixado novamente.
- O GIF do README é servido pelo GitHub e não consome banda do Render.

Alternativas, nenhuma aplicada sem autorização:

1. `preload="none"`: elimina o buffer inicial de cerca de 1 MiB; os metadados só são buscados no play.
2. Capa derivada mais leve para a landing (testes: JPEG 156 KB, WebP 50 KB), mantendo o PNG original.
3. Hospedar o MP4 fora do Render (ex.: GitHub Releases, Supabase Storage ou plataforma de vídeo),
   o que altera a arquitetura e exige decisão do proprietário.

## Limites

- A reprodução do MP4 H.264 não foi executada em um navegador com esse codec neste ambiente;
  a integridade foi comprovada por decodificação completa com FFmpeg.
- Safari/iOS e navegadores físicos não foram testados.
- Não houve deploy: o comportamento foi validado no Gunicorn local, não na infraestrutura do Render.
