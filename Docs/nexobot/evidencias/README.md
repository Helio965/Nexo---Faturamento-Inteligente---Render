# Evidências visuais do NexoBot Advanced 2.0

Capturas em navegador real (Chromium via Playwright) da aplicação com SQLite temporário, Guia do
`seed_guia.py` e dois tópicos de teste (`ZZTEST-guia`, `ZZTEST-guia <i>XSS</i>`) cadastrados para
reproduzir o sintoma observado em produção. Larguras: 320 px (`is_mobile`, escala 2), 390 px e 1440 px.

| Estado | Antes (1.x) | Depois (2.0) |
| --- | --- | --- |
| Widget aberto | `antes/<largura>_aberto.png` — saudação listava as categorias do banco, inclusive `ZZTEST` | `depois/<largura>_aberto.png` — saudação curta com sugestões clicáveis |
| "Quero saber como o sistema funciona." | `antes/<largura>_como_funciona.png` — "Não encontrei uma orientação específica" | `depois/<largura>_como_funciona.png` — etapas do NEXO em passo a passo, com sugestões |
| "ajuda" | `antes/<largura>_ajuda.png` — categorias concatenadas | `depois/<largura>_ajuda.png` — ajuda curta com sugestões |
| "O que significa pressão de estoque?" | — | `depois/<largura>_pressao_estoque.png` — resumo, explicação e aviso (não é lucro) |

Em 320 px e 390 px o painel ocupa a tela inteira (sem rolagem horizontal, botão flutuante oculto
enquanto aberto); em 1440 px o painel é flutuante. As capturas podem ser regeradas com
`NEXO_TEST_BROWSER=1 NEXO_TEST_SHOTS=<pasta> python -m unittest tests.test_nexobot_navegador`.
