# Redesign da landing page NEXO

Implementação integrada ao Flask/Jinja2 existente, baseada na referência mobile fornecida. As quatro faixas da imagem foram interpretadas como trechos consecutivos da mesma página. Não foram fornecidos arquivos de código exportados do design.

Base auditada: `origin/main`, commit `a2ba618b1e97e6c9f3d791db402127b1e8ee7a08`.

## Alterações

- Hero centralizado e exclusivamente textual, com os links originais para planos, demonstração e portal.
- Quatro cards de oportunidades com ícones distintos e quatro etapas numeradas. O painel resumido fica depois das etapas; no desktop, o painel organiza os indicadores em três colunas e o comparativo ao lado dos produtos.
- Comparativo horizontal de compras e vendas com diferença estimada hachurada. Valores e produtos originais preservados, com tabela textual acessível.
- Depoimentos autorizados, sete indicadores, demonstração completa, cinco etapas do Método NEXO e rodapé compacto alinhados à identidade da referência.
- Três planos sem botões individuais e um único **Contrate Agora**, centralizado abaixo do conjunto. O link abre `/como-aderir`, com aviso explícito de que a página não conclui uma contratação.
- Contato e envio de avaliação permanecem indisponíveis conforme o fluxo existente. Aprovação e consentimento dos depoimentos continuam obrigatórios.

## Arquivos

| Arquivo | Finalidade |
| --- | --- |
| `templates/landing.html` | Estrutura, reposicionamento do painel, CTA único e conteúdo acessível |
| `static/css/landing.css` | Estilos responsivos e remoção de regras antigas sem uso na landing |
| `static/js/landing.js` | Barras horizontais e apresentação dos três gráficos com dados preservados |
| `tests/test_landing_commercial.py` | Contrato comercial, sequência das seções, CTA, dados e gráficos reais nas oito larguras |
| `tests/test_landing_video_commercial.py` | Cópia local íntegra do Bootstrap no navegador de teste |
| `tests/test_identidade_visual.py` | Cópia local íntegra do Bootstrap no navegador de teste |
| `Docs/landing-redesign/` | Registro da validação e capturas |

O arquivo `static/js/landing-video.js`, MP4 e pôster originais, rotas, autenticação, permissões, banco, cálculos, portais internos, CSP/SRI e configuração do Render não foram alterados. Não foram adicionadas dependências de produção nem variáveis de ambiente.

## Validação

Os testes utilizam SQLite temporário, dados sintéticos e bloqueio de conexões externas. O teste do player serve o template e a mídia em uma aplicação Flask local isolada. Nenhuma conexão com o banco de produção foi necessária.

Configuração utilizada: Chromium em `/usr/bin/chromium`, Playwright já instalado, `NEXO_TEST_BROWSER=1` e cópias locais da CDN em `NEXO_TEST_CDN_DIR`, conferidas pelos hashes SRI oficiais. As capturas usam as fontes Inter e JetBrains Mono.

```bash
NEXO_TEST_BROWSER=1 \
NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/caminho/para/copias-cdn \
python -m unittest \
  tests.test_landing_commercial \
  tests.test_landing_video_commercial \
  tests.test_identidade_visual \
  tests.test_overflow_navegador
```

**61 testes aprovados, sem skips:**

| Módulo | Testes | Resultado |
| --- | ---: | --- |
| `tests.test_landing_commercial` | 22 | OK |
| `tests.test_landing_video_commercial` | 7 | OK |
| `tests.test_identidade_visual` | 11 | OK |
| `tests.test_overflow_navegador` | 21 | OK |

Além da suíte, a prévia Flask foi examinada com Plotly real em **320, 375, 390, 430, 768, 1024, 1440 e 1920 px**: sem rolagem horizontal, rótulos fora dos gráficos ou exceções JavaScript. Os três gráficos carregaram em todas as larguras. O pequeno corte do rótulo de R$ 13.500 em 320 px foi corrigido ajustando somente a escala visual.

Também foram verificados os caminhos estáticos e destinos locais, login, menu por teclado, foco visível, movimento reduzido, ausência de JavaScript/CDN, alternativas textuais, aprovação dos depoimentos e reprodução/pausa/som/tela cheia/erro do vídeo real. `node --check static/js/landing.js` e a verificação de whitespace, respeitando os finais CRLF existentes, passaram.

## Capturas

- [Mobile — 390 px](mobile-390.png)
- [Desktop — 1440 px](desktop-1440.png)

## Publicação

As alterações são propostas em `feature/nexo-landing-redesign`, para revisão contra `main`. Não houve merge nem implantação no Render. Após a aprovação e integração do PR, a publicação deve seguir o fluxo existente do repositório.

Contratação automática, canal de atendimento, envio de avaliações e documentos jurídicos seguem a disponibilidade já informada pelo projeto; nenhum serviço ou contato foi inventado. A suíte completa de todo o repositório não foi executada nesta alteração; foram executados os quatro módulos solicitados e a revisão visual correspondente.
