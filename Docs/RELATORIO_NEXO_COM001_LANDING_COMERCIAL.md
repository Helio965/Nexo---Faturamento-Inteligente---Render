# NEXO-COM-001 — Landing comercial

Registro de implementação e validação local em 24/10/2026 (America/Sao_Paulo).
A implementação foi publicada na PR #21, em rascunho. O resultado da CI é
registrado por commit na seção S; consultar a PR para o estado mais recente.
Este registro não comprova implantação nem disponibilidade dos canais pendentes.

## A. Diagnóstico da landing anterior

A página apresentava a solução como MVP acadêmico, repetia o acesso ao portal
como se fosse aquisição e explicava detalhes de implementação ao empresário.
O cabeçalho tinha duas ações concorrentes para portal/demonstração; o hero
exibia badges de processo em vez de priorizar benefícios. Havia um depoimento
demonstrativo atribuído a pessoa/empresa sem evidência de autorização no projeto.

A página `/como-aderir` incluía telefone e e-mail explicitamente provisórios e
expectativa de resposta comercial não confirmada. O contato do dashboard também
mostrava campos "preencher depois". Não foi encontrado checkout, URL de contratação,
WhatsApp Business confirmado, dados societários autorizados ou políticas revisadas.
O e-mail de suporte mencionado no requisito é referência, não prova de canal ativo.

## B. Alterações implementadas

Preservados Flask/Jinja, tema escuro/púrpura e conteúdo financeiro oficial. A
apresentação passou a destacar compreensão dos relatórios, oportunidades e apoio
à reposição, sem garantir faturamento, giro ou medição de estoque físico.
Foram reorganizados hero, benefícios, processo, indicadores, demonstração, planos,
CTAs e rodapé. Removidas as referências acadêmicas da apresentação; comentários,
autoria e documentos históricos permanecem preservados.

Não houve alteração em `app.py`, login, modelos, migrações, dependências, segurança,
ETL, cálculo financeiro, NexoBot, notificações, Socket.IO ou configuração do Render.

## C. Comparativo de textos

| Antes | Depois / finalidade |
| --- | --- |
| "Consultoria de dados · MVP acadêmico" | "Inteligência para a sua loja", identidade comercial |
| Hero com processamento e consultor | "Decisões mais claras para fazer sua loja crescer.", seguido de benefício e contexto |
| "Seus dados existem" com problema primeiro | Oportunidades a partir dos relatórios de compras e vendas |
| "consultoria de dados [...] com portal digital" | Interpretação dos relatórios e Parecer Estratégico do Sistema |
| Pandas, pipeline e Plotly.js na copy | Envio, organização, indicadores e parecer em quatro etapas |
| "KPIs do MVP" | "Indicadores Estratégicos" |
| "Mais que gráfico: interpretação estratégica" | "Mais gráficos, menos textos e dados soltos." |
| Botões de planos "Acessar portal" | "Contrate Agora", desativados e explicados até haver canal real |
| Depoimento demonstrativo atribuído a cliente | Estado vazio explícito, sem nomes ou resultados fictícios |
| Telefone/e-mail provisórios em `/como-aderir` | Informação de canal ainda não publicado e acesso ao portal existente |

## D. Cabeçalho

Um CTA principal "Acessar Portal" leva ao login real. Demonstração permanece na
navegação. Em telas menores, o menu tem botão nativo, `aria-controls`, estado
expandido, fechamento por Escape/com foco de volta, clique externo e seleção de
âncora. Sem JavaScript, a navegação continua disponível. O comportamento do menu
independe do carregamento da biblioteca dos gráficos.

## E. Proposta de valor

O empresário encontra os benefícios primeiro: clareza sobre compras/vendas,
oportunidades, preservação do capital de giro e sinais de possível excesso de
compras. O texto não promete aumento de faturamento, eliminação de encalhe,
estoque físico, lucro ou margem. A revisão/elaboração pela equipe NEXO continua
expressa, inclusive antes da publicação do parecer no portal.

## F. Cards e depoimentos

R1: envie seus relatórios; R2: organização dos dados; R3: indicadores estratégicos;
R4: parecer estratégico. Os cards descrevem o fluxo sem jargão de implementação.

O carrossel reutilizável tem anterior/próximo, indicadores de posição, anúncio de
estado e navegação por teclado, sem avanço automático. O template aceita somente
itens futuros com aprovação e consentimento explícitos e escapa seus textos.
Isso não substitui a autorização e a consulta segura que a COM-002 deverá fazer
no servidor. Sem dados aprovados, mostra estado vazio e oculta controles inúteis.
Os conteúdos sintéticos dos testes nunca são publicados. "Deixar Avaliação" fica
desativado, com aviso de indisponibilidade.

## G. Indicadores

Preservados faturamento total, total comprado, Indicador de Pressão de Estoque,
produto mais vendido, produto com maior faturamento, produto com maior saldo
estimado parado e a referência à Curva ABC. O box de transparência foi substituído
por nota discreta: a pressão é uma estimativa, não estoque físico, lucro ou margem.
Não foram alterados cálculos nem os três conjuntos de dados demonstrativos.

Os três gráficos têm alternativas textuais consultáveis (descrição dos dois
valores no hero e tabelas nos outros dois) e aviso caso a biblioteca
esteja indisponível. A mesma versão 2.35.2 do Plotly utilizada pelo portal é
carregada via jsDelivr de forma assíncrona. O carregamento/falha não impede menu,
carrossel ou player. O aviso só some após renderização bem-sucedida do gráfico.

## H. Vídeo

Título "Seja um cliente NEXO e tenha acesso ao portal." e legenda "Valores
ilustrativos". Mantidos MP4, poster, lazy start, loop, reprodução muda inicial,
sonda/permissão do navegador, gesto quando exigido, áudio condicionado à visibilidade
integral, tratamento de erros, retry e fullscreen. A máquina de estados existente
foi estendida, sem reescrever o player, para pausa/retomada explícita, opção de
silenciar persistente e respeito a `prefers-reduced-motion`.

A pausa manual não é desfeita por rolagem, pageshow ou eventos de retomada. Com
movimento reduzido, o vídeo aguarda reprodução explícita. Expandir sozinho não
ignora essa preferência. Som continua silenciado quando qualquer área do vídeo
fica sob o cabeçalho ou fora da viewport. As permissões do navegador prevalecem.

Hashes SHA-256 preservados:

- MP4: `f7756d2507356c2164409190d0d618d630dba2d83a7d2e012aa38ee909c888fb`.
- Poster: `0e3882b673f95e4826235fc04b7d881459f19d7a5d573cfb8c371e3234087a4d`.

## I. Planos

BRONZE, PRATA e OURO mantêm características e frequências anteriores: Bronze e
Prata com uma análise mensal, Ouro com até duas/recorte quinzenal; preços "Sob
consulta". Melhoradas hierarquia, legibilidade e diferenciação visual. Nenhuma
cobrança, assinatura ou elegibilidade do backend foi alterada.

## J. CTAs

| Ação | Comportamento atual |
| --- | --- |
| Acessar Portal / Login do Cliente | Login real, preservado |
| Conheça os planos | Âncora dos planos |
| Veja o NEXO em ação / Demonstração | Âncora da demonstração |
| Contrate Agora (três planos) | Desativado, aviso de contratação ainda indisponível |
| Falar com a equipe NEXO | Desativado, aguarda WhatsApp Business oficial |
| Como obter acesso | Página informativa real, sem simular checkout ou contato |
| Deixar Avaliação | Desativado, aguarda COM-002 funcional |
| Abrir suporte (dashboard autenticado) | Rota de chamados já existente, sem contato fictício |

O fluxo de aquisição ainda depende de conteúdo oficial. A COM-001 não entrega
contratação funcional na ausência desse canal; não confundir o login com checkout.

## K. Rodapé

Quatro colunas: marca/proposta, navegação, privacidade/uso e contatos. Razão social,
CNPJ, redes e contatos não foram inventados. O site informa a ausência das políticas
de privacidade, termos e cancelamento, em vez de oferecer links jurídicos fictícios.
A publicação desses documentos exige conteúdo real revisado pelo responsável.

## L. Responsividade

Playwright/Chromium nas larguras 320, 375, 390, 430, 768, 1024 e 1440 px: sem
rolagem horizontal da página, portal acessível e menu adequado à largura. Grid dos
cards, planos e rodapé adapta as colunas. Rótulos/margens do gráfico horizontal
se adaptam no mobile sem alterar os valores ou nomes completos dos dados.

Prévia local adicional confirmou os três gráficos reais do Plotly em todas as
sete larguras. Bootstrap e Plotly retornaram HTTP 200 via jsDelivr. Google Fonts
foi bloqueado pelo proxy deste ambiente; a página usou fontes de fallback legíveis.
Ícones de seta em SVG dispensam glifos especiais da fonte externa.

## M. Acessibilidade

Adicionados skip link, `main`, hierarquia de títulos, regiões com nomes distintos,
foco visível, alvos de interação de pelo menos 44 px nos controles principais,
estado expandido do menu, respeito a movimento reduzido e cores de texto secundário
mais legíveis. Navegação por teclado, Escape, foco e dados textuais dos gráficos
são cobertos por testes. Os tokens secundários testados atendem contraste 4,5:1
contra os fundos indicados; botões principais usam gradiente mais escuro.

Auditoria adicional axe-core 4.10.3 em Chromium, 390 e 1440 px, com WCAG A/AA e
boas práticas: **zero violações automáticas detectadas**, 41 regras aprovadas em
cada largura. A duplicidade inicial de nome de região foi corrigida e a auditoria
reexecutada. Há verificações inconclusivas de contraste com gradientes/gráficos,
link no texto e legendagem do vídeo que exigem revisão humana.

Não se declara conformidade WCAG integral. A descrição resumida da demonstração
não substitui transcrição integral ou legendas sincronizadas. Não foram realizados
ensaios com leitor de tela, Safari/iOS real, Firefox ou dispositivos físicos.

## N. Testes automatizados específicos

- `tests/test_landing_commercial.py`: **20 testes aprovados**, sem falha ou skip.
  HTTP da aplicação real, login com dados sintéticos, links/âncoras/ativos, CTAs,
  texto, indicadores, estado vazio e filtro/escape de depoimentos; Chromium para
  as sete larguras, teclado, ausência de JavaScript/CDN e integração dos gráficos.
  O teste de integração dos dados usa um stub explícito do Plotly; a prévia
  adicional descrita em L verificou a biblioteca real.
- `tests/test_landing_video_commercial.py`: **7 testes aprovados**, sem falha ou
  skip, com MP4 real em Chromium. Reprodução/loop, movimento reduzido, gesto, pausa
  por teclado, mudo persistente, recorte de um pixel sob o cabeçalho, fullscreen e
  erro HTTP controlado/recuperação. A prévia Flask do player não importa banco ou
  `.env`; login é verificado separadamente na aplicação real. Eventos sintéticos
  exercitam as rotas de retomada, sem representar teste físico de troca de aba.

Comandos executados com Python 3.12.14 do ambiente isolado
`/tmp/nexo-sec006b-validation/bin/python`, Playwright 1.56 e
`NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium`:

```bash
python -B -m unittest tests.test_landing_commercial -v
python -B -m unittest tests.test_landing_video_commercial -v
```

## O. Regressões gerais

Suíte completa: **558 testes aprovados**, zero falhas e zero skips, em **128,604 s**.
Os 27 testes novos fazem parte desses 558; não devem ser somados novamente. Com
os 108 testes PostgreSQL separados, foram **666 testes aprovados** nesta validação.

```bash
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest discover -s tests -t . -v

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest \
  tests.postgresql_auth_tokens tests.postgresql_session_revocation \
  tests.postgresql_company_restore_security tests.postgresql_company_restore_migration \
  tests.postgresql_etl_resource_security -v
```

PostgreSQL real **descartável/privado**, com a infraestrutura existente: **108
testes aprovados**, zero falhas/skips, 26,339 s. Nenhum banco existente ou Supabase
de produção foi utilizado. As regressões cobrem PDFs, tokens, sessões, restauração,
uploads/ETL, primeiro acesso, CSRF/rate limiting, dashboards, notificações,
NexoBot Advanced, dependências e inicialização Flask/Gunicorn. Foram executados
também `node --check` nos dois scripts e `git diff --check`.

O workflow `nexo-security-ci.yml` mantém a descoberta completa e os módulos
PostgreSQL obrigatórios. Foi necessário selecionar o Google Chrome pré-instalado
no runner para os testes do MP4 H.264/AAC, conforme limitação do Chromium 141
já registrada em `VALIDACAO_VIDEO_RENDER.md`. Playwright instala as dependências
de sistema; nenhum teste é ignorado e nenhuma mídia é substituída.

Falhas do unittest também geram annotations com nome e traceback escapado/limitado,
além do log normal. O código de saída original é preservado. YAML/bash foram
validados; ensaio efêmero do wrapper confirmou exit 0 em sucesso e exit 1 com
annotation em falha sintética. Esse ensaio não integra o total dos 666 testes.
Não foram alteradas dependências Python nem a lógica dos testes de segurança.

## P. Arquivos modificados

| Arquivo | Finalidade |
| --- | --- |
| `templates/landing.html` | Estrutura semântica, copy, CTAs, planos, carrossel vazio, tabelas e controles do vídeo |
| `static/css/landing.css` | Identidade preservada, hierarquia, responsividade, contraste e foco |
| `static/js/landing.js` | Menu/carrossel independentes da CDN e gráficos com fallback/mobile |
| `static/js/landing-video.js` | Extensões mínimas de pausa, mudo e movimento reduzido |
| `templates/como_aderir.html` | Orientação de acesso sem contatos provisórios/checkout fictício |
| `templates/cliente/dashboard.html` | Troca dos contatos "preencher depois" pelo suporte existente |
| `.github/workflows/nexo-security-ci.yml` | Navegador compatível com o MP4 e annotations de falha, preservando a suíte e seu exit status |
| `tests/test_landing_commercial.py` | 20 testes HTTP/DOM/Chromium |
| `tests/test_landing_video_commercial.py` | 7 testes do player e mídia real |
| `Docs/PLANO_ACAO_COMERCIAL_LANDING_NEXO.md` | Seis seções do plano e matriz de rastreabilidade |
| `Docs/PENDENCIAS_NEXO_COM002_AVALIACOES.md` | Requisitos futuros de avaliação, consentimento e moderação |
| `Docs/RELATORIO_NEXO_COM001_LANDING_COMERCIAL.md` | Este relatório técnico e evidências de publicação |

## Q. Pendências e validação comercial

| Pergunta | Resposta verificada / limite |
| --- | --- |
| 1. Um empresário entende o NEXO em segundos? | A primeira dobra explicita interpretação de compras/vendas e apoio a decisões; validação qualitativa com empresários ainda necessária. |
| 2. A headline tem benefício claro? | Sim: clareza para decidir e apoiar crescimento, sem garantia de resultado. |
| 3. CTAs têm objetivos distintos? | Sim: portal, planos, demonstração e informação de acesso; aquisição/avaliação indisponíveis ficam desativadas. |
| 4. Contratação leva a canal válido? | Ainda não. Não existe canal oficial confirmado; botão desativado com explicação. |
| 5. Os planos são diferenciados? | Sim: profundidade de parecer e frequência anteriores preservadas. |
| 6. Indicadores são corretos? | A apresentação preserva os oficiais e qualifica pressão/saldo como estimativas, sem cálculo novo. |
| 7. Vídeo funciona em navegadores modernos? | Confirmado em Chromium real; Safari/iOS e Firefox pendentes. |
| 8. Portal continua acessível? | Sim, link real e login verificados com dados sintéticos. |
| 9. Funciona em mobile? | Sim nas sete larguras em Chromium; dispositivo físico ainda pendente. |
| 10. Há promessas sem comprovação? | Não foram introduzidas garantias de faturamento, lucro ou estoque; revisão comercial humana recomendada. |
| 11. Há depoimentos/resultados fictícios como reais? | Não; nenhum depoimento publicado, valores da demonstração marcados como ilustrativos. |
| 12. Contatos estão confirmados? | Não; e-mail, WhatsApp, redes e URL oficial continuam pendentes, sem divulgação fictícia. |
| 13. Políticas estão disponíveis/revisadas? | Não; responsável deve fornecer os documentos reais e aprovação jurídica. |
| 14. Visitante entende como contratar? | Entende a indisponibilidade e a orientação de acesso; solicitação comercial efetiva depende do canal oficial. |

Faltam WhatsApp Business/URL autorizada, e-mail ativo, razão social/CNPJ, redes
autorizadas, políticas reais revisadas e depoimentos consentidos. O formulário de
avaliação não existe e não foi anunciado como disponível. Esses itens impedem
classificar a aquisição comercial como pronta, mesmo com a interface implementada.

## R. Requisitos transferidos para COM-002

Ver `PENDENCIAS_NEXO_COM002_AVALIACOES.md`: definição verificável de 60 dias de uso
ativo, nota 1–5, comentário público, sugestão privada, moderação, consentimento,
retirada de publicação, suporte e isolamento entre empresas. Não foram criadas
tabelas, migrações, gatilhos, formulários ou endpoints de avaliação nesta etapa.
O componente público está preparado para integração futura com DTO restrito.

## S. GitHub e publicação

- Repositório: `Helio965/Nexo---Faturamento-Inteligente---Render`.
- Base inicial: `8233c5bddbd1f6c67a4d95c7b0a2a470724738c8`.
- Base atualizada antes da publicação: `c919b1d17e6cbf4bf9dac09e29cefca67d908d06`.
  A PR #19 integrou somente o documento de baseline por ação externa; esta branch
  foi avançada por fast-forward, preservando esse documento e as alterações locais.
- Branch publicada: `feature/com-001-landing-page-comercial`.
- Commit de implementação: `9396c71a63ace0fb27096cd3d0621f47ad8bdb9b`.
- PR real: [#21 — NEXO-COM-001](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/21),
  criada em rascunho, aberta e sem auto-merge na verificação desta atualização.
- [Execução inicial 40116109112](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40116109112):
  `security-postgresql` aprovado (1 min 57 s), `security-sqlite-browser` falhou
  (7 min 43 s). A API confirmou esses resultados, mas o armazenamento redirecionado
  dos logs foi bloqueado pelo proxy. A annotation original trouxe somente exit 1;
  não foi possível obter os tracebacks dessa primeira execução.
- A incompatibilidade do Chromium Playwright com H.264/AAC já documentada motivou
  a seleção do Chrome do runner e a publicação de diagnósticos nas annotations.
  Não atribuir todas as falhas iniciais a codecs sem seus tracebacks. A correção
  exige nova execução completa; o resultado por commit e os links definitivos dos
  dois jobs são registrados na descrição da PR e na entrega final desta execução.
  Não reutilizar um resultado anterior como se comprovasse outro commit.
- Nenhum merge, auto-merge ou deploy foi executado. A integração e a publicação
  em produção dependem de autorização posterior.

## T. Riscos, limites e próxima etapa

**Implementação local validada e PR publicada; conteúdo oficial e aprovação da
CI são estados separados.** O resultado remoto mais recente deve ser consultado
na PR e na entrega desta execução.
Não classificar esta documentação como comprovação de disponibilidade em produção.

Bootstrap, Plotly e fontes continuam com dependências CDN existentes. O novo
fallback mantém dados textuais/controles mesmo sem Plotly; bloqueios de fonte usam
fallback do sistema. Testes de laboratório não comprovam todos os navegadores,
leitores de tela, desempenho em Render ou resultados comerciais. Acesso ao painel
Render, entrega de e-mails e políticas jurídicas não foram homologados.

Nenhum deploy, merge, migração ou modificação no Supabase de produção foi executado
por esta tarefa. O Auto-Deploy foi informado como ativo pelo proprietário; por isso
a PR deve permanecer aberta para revisão. Não presumir que sua aprovação ou seus
testes autorizam integração à `main`.

Próxima etapa: revisar a PR e a copy com o proprietário, confirmar canais/dados
oficiais e documentos jurídicos, homologar dispositivos/navegadores e acessibilidade
do vídeo; só então planejar publicação autorizada. COM-002 permanece **planejada,
não implementada**. Não há migração necessária à COM-001.
