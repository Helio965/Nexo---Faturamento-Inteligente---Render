# Controle de seleção de textos e interfaces do NEXO

## Identificação

| Campo | Registro |
| --- | --- |
| Implementação | Quinta implementação de homologação: controle visual de seleção, com edição e área de transferência preservadas |
| Data e horário inicial | 2026-11-14 19:04:45 -0300, `America/Sao_Paulo` |
| Conclusão da validação local | 2026-11-14 19:17:13 -0300, `America/Sao_Paulo` |
| Repositório autorizado | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Branch | `feature/controle-selecao-textos-nexo` |
| Base consultada | `ae8775b23b948d8facb4d2eb69938e6209d91667`, `origin/main` |
| Commit da implementação | `779c0f326ce08cbfa590af01a4072f9bd59de953` (CSS, integração e testes); este documento é versionado em commit documental posterior |
| Status | Implementação e validação local concluídas; sem merge/deploy; homologação humana pendente |

## Problema anterior e objetivo

A landing não possuía uma política geral de seleção. O portal tinha um bloco parcial em `nexo.css`, restrito a determinadas classes. As exceções desse bloco também permitiam selecionar contêineres inteiros (`.relatorio-doc`, `.rb-body`, `.alert` e `.form-control`), incluindo relatórios publicados, avisos e rótulos de formulários.

A nova política impede a seleção acidental da apresentação por arrasto, mantendo textos no DOM, cliques, navegação, foco e controles editáveis. É um ajuste visual: não protege informações e não impede captura de tela, inspeção ou extração técnica do conteúdo.

## Arquivos alterados

Os caminhos abaixo são relativos à raiz do repositório autorizado. No ambiente desta implementação, a raiz é `/workspace/Nexo---Faturamento-Inteligente---Render`.

| Caminho completo no repositório | Função e alteração |
| --- | --- |
| `static/css/nexo-selecao.css` | Nova política compartilhada: apresentação sem seleção; exceções para controles nativos e editores semânticos; ilhas não editáveis sem seleção. |
| `static/css/nexo.css` | Substitui somente o bloco antigo de seleção por uma referência ao arquivo compartilhado. A regra própria de `.dado-protegido-marcador` permanece intacta. |
| `templates/landing.html` | Acrescenta um único vínculo ao novo CSS, imediatamente após `landing.css`, preservando CRLF. |
| `templates/base.html` | Carrega a política após os blocos de CSS do portal, cobrindo login, administração, cliente, suporte, configurações, NexoBot e páginas públicas que herdam esta base. |
| `templates/auth/_layout.html` | Acrescenta um vínculo para cobrir as telas independentes de autenticação, preservando CRLF. |
| `templates/erro_simples.html` | Acrescenta um vínculo para cobrir erros independentes do portal. |
| `tests/test_selecao_navegador.py` | Novos cenários de regressão no navegador para seleção informativa, controles, editores, clipboard, temas, larguras e interatividade. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-14_Controle_Selecao_Textos_Interfaces_NEXO.md` | Este registro técnico, reprodução seletiva e reversão. |

Nenhum documento anterior desta pasta foi alterado. Não houve alterações em regras de negócio, autenticação, permissões, JavaScript, cores, fontes, dimensões, temas, modelos, migrações, dependências, workflows ou configurações do Render. O projeto empresarial e os serviços Supabase não foram acessados.

## Implementação técnica e exceções

O `body` das páginas que incluem a folha recebe `-webkit-user-select: none` e `user-select: none`. O escopo da política é definido pelos quatro templates raiz de interface; templates de e-mail não incluem a folha.

O seletor `body :where(...)` restabelece `text` com especificidade controlada em:

- `input`, `textarea`, `select` e `option`, independentemente de classes, inclusive controles criados dinamicamente;
- `[contenteditable=""]`, `[contenteditable="true" i]` e `[contenteditable="plaintext-only" i]`;
- `[role="textbox"]`, para componentes personalizados que declarem essa semântica.

Descendentes comuns de editores mantêm a seleção pelo valor usado de `user-select: auto`, que acompanha a seleção do ancestral. Um elemento `[contenteditable="false" i]` restabelece `none` para uma ilha de apresentação dentro de um editor. Um editor ou controle nativo aninhado continua recebendo sua própria exceção.

O CNPJ de empresas existentes, exposto como `input[readonly]`, conserva seleção e cópia, sem ganhar permissão de alteração. Senhas conservam digitação, seleção e colagem com as restrições nativas do navegador para copiar/recortar senhas. A propriedade CSS não transforma um elemento ARIA em editor: componentes personalizados continuam responsáveis por implementar sua edição.

Não se depende de `.form-control` nem de `.form-select`. As exceções antigas para contêineres informativos foram retiradas; `.selectable` não tinha uso em templates ou scripts. O marcador de dados mascarados conserva sua regra explícita e não é tratado como editor.

Não há `!important`, bloqueio de teclado, interceptação de `copy`, `cut`, `paste` ou `contextmenu`, camadas sobre a interface ou alteração de eventos de ponteiro. Seletores de temas, foco, preenchimento automático, atributos de login e scripts permanecem intactos. A folha não define propriedades de pintura ou geometria, portanto é comum aos temas Sistema, Claro e Escuro e às resoluções existentes.

Os gráficos mantêm os scripts e configurações Plotly existentes. O ajuste de seleção não altera hover, tooltips, zoom, arrasto, legendas, controles nem redimensionamento. O vídeo conserva suas regras específicas anteriores.

## Trabalho paralelo na landing

Antes da edição, o checkout estava limpo. `origin/main` foi atualizado e uma branch independente foi criada a partir de `ae8775b`. As buscas de PRs abertos pelo GitHub não retornaram PR aberto no momento da consulta. As branches remotas de landing e `claude/*` foram inspecionadas; nenhuma branch publicada identificou uma correção de âncoras em andamento. Alterações ainda não publicadas por outra sessão não podem ser verificadas nesta cópia.

`static/css/landing.css` e `static/js/landing.js` permanecem idênticos à base. Em `landing.html`, há somente a inserção do vínculo ao CSS. Não se alteram IDs, âncoras, `scroll-margin-top`, `scroll-padding-top`, `scroll-behavior`, cabeçalho ou layout. Nenhuma outra branch foi integrada, nem houve force push. A compatibilidade com uma correção futura ainda não publicada deve ser conferida quando essa correção estiver disponível.

## Testes locais

Os testes existentes utilizam dados fictícios e bancos SQLite temporários, com barreiras de isolamento e serviços externos bloqueados. A preparação de suas fixtures aplica a cadeia de migrações já existente apenas nesses bancos descartáveis; nenhum arquivo de migração foi criado ou modificado e nenhum banco remoto foi acessado.

O ambiente usa `.venv/bin/python`, Playwright e `/usr/bin/chromium`. Cópias públicas locais de Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Plotly 2.35.2 e Socket.IO 4.7.5 tiveram SHA384/SRI conferido pelos auxiliares existentes. As fontes Inter e JetBrains Mono foram disponibilizadas somente no ambiente local. Não se alteraram as dependências versionadas.

### Regressão de backend, autenticação e segurança

```bash
.venv/bin/python -B -m unittest \
  tests.test_auth_tokens_security tests.test_auth_email_flows \
  tests.test_http_hardening_security tests.test_configuracoes_conta \
  tests.test_nexobot_api tests.test_nexobot_interface \
  tests.test_nexobot_regressao_original tests.test_painel_cliente_visao_geral \
  tests.test_gerenciamento_analises tests.test_identidade_visual \
  tests.test_tema_interface -v
```

Resultado: **359 descobertos, 355 aprovados, 4 ignorados, zero falhas/erros**, em 211,198 s. Os quatro ignorados foram executados posteriormente com os recursos necessários:

```bash
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_http_hardening_security.SubresourceIntegrityTests.test_local_cdn_copies_match_the_pinned_hashes_when_present -v

NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_identidade_visual.IdentidadeVisualBrowserTests -v
```

Integridade de CDN: **1 aprovado**. Identidade visual no navegador: **3 aprovados**, em 27,009 s. Total único desses grupos: **359 testes aprovados**; nenhum dos quatro casos ficou pendente. Os logs locais são `/tmp/nexo-selection-unit-regression.log`, `/tmp/nexo-selection-cdn-integrity.log` e `/tmp/nexo-selection-identity-browser.log` (arquivos temporários do ambiente, não versionados).

### Regressão de interface existente

```bash
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_landing_commercial tests.test_landing_video_commercial \
  tests.test_painel_navegador tests.test_configuracoes_navegador \
  tests.test_nexobot_navegador tests.test_gerenciamento_navegador \
  tests.test_tema_navegador tests.test_csp_navegador \
  tests.test_termos_privacidade tests.test_navegacao_admin -v
```

Resultado: **156 descobertos, 155 aprovados, 1 ignorado, zero falhas/erros**, em 796,497 s. O único ignorado foi `test_capturas_para_documentacao`, cujo comportamento preexistente exige `NEXO_PAINEL_CAPTURAS` para gerar imagens opcionais; nenhum cenário funcional foi desligado ou alterado. Esta execução verifica, entre outros, âncoras e menu da landing, três gráficos da demonstração, vídeo MP4 real (áudio, pausa, loop e tela cheia), painéis, filtros, temas, configurações, suporte/NexoBot, teclado, foco, tabelas e CSP. Log: `/tmp/nexo-selection-regression.log`.

### Seleção e área de transferência

```bash
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_selecao_navegador -v
```

Resultado: **7 testes aprovados, zero falhas/erros/ignorados**, em 88,653 s. Após três aperfeiçoamentos da revisão dos testes (sentinela distinta antes da cópia de e-mail, exigência explícita de evento de contexto não cancelado e confirmação da resposta final do NexoBot), os três cenários afetados foram reexecutados: **3 aprovados**, em 41,879 s. Essa repetição não aumenta o total de sete testes únicos. Logs: `/tmp/nexo-selecao-final.log` e `/tmp/nexo-selecao-revisao.log`. Nenhum erro JavaScript foi detectado pelos cenários novos.

A colagem usa `navigator.clipboard.writeText` apenas para preparar o conteúdo fictício, seguida de teclas nativas `ControlOrMeta+V`. A seleção parcial usa `Home` e `Shift+ArrowRight`; cópia, recorte, colagem e desfazer/refazer são executados pelo teclado, com valor e clipboard conferidos. O teste de login também verifica o envio real do formulário. O cadastro grava somente uma empresa fictícia na fixture temporária e verifica a cópia do CNPJ `readonly`. O NexoBot responde com HTTP 200, conteúdo não vazio e estado de envio finalizado, sem erro na interface.

| Cenário obrigatório | Evidência executada | Resultado |
| --- | --- | --- |
| A: CNPJ fictício | Colagem por teclado no cadastro, envio real e conferência no SQLite descartável; seleção/cópia na edição `readonly` | Aprovado |
| B: e-mail | Colagem no login, cópia com sentinela distinta na área de transferência e envio real | Aprovado |
| C: senha fictícia | Colagem no login, seleção integral e autenticação real da fixture | Aprovado |
| D: mensagem | Colagem/edição em suporte e NexoBot; envio e resposta real do bot local | Aprovado |
| E: seleção parcial | `Home`, cinco `Shift+ArrowRight`, copiar, recortar, colar, desfazer e refazer em busca, nome, suporte, NexoBot e controles dinâmicos | Aprovado |
| F: texto informativo | Arrasto real sem seleção sobre título e demais elementos, com controle positivo e verificação de texto existente | Aprovado |

O teste de arrasto tem controle positivo: o mesmo gesto seleciona o título da landing com a folha desativada e deixa de selecionar com ela ativa. São verificados título, parágrafos, cartões, planos, rodapé, dashboard administrativo, tabelas, indicadores do cliente, relatório publicado e avisos. A matriz usa **320, 360, 390, 430, 768, 1024, 1366 e 1920 px**, com **dark, light e system** no painel do cliente; as regressões existentes verificam a resolução e persistência dos temas.

Editores semânticos e campos dinâmicos são criados somente no DOM de teste para verificar seleção em descendentes e ilhas não editáveis. No Plotly existente, são testados hover e alternância de séries pela legenda. Os eixos travados anteriormente pelo produto continuam travados: um gráfico adicional criado somente no teste por `NEXO.plot` permite verificar um gesto real de zoom quando a configuração o habilita.

Na primeira execução do teste novo de gráfico, o Playwright não alcançou diretamente o ponto SVG porque a camada de arrasto legítima do Plotly o cobre. O teste foi corrigido para mover o mouse às coordenadas do ponto e validar o tooltip real; não houve mudança no gráfico ou na aplicação para contornar a falha.

### Revisão de escopo

```bash
git -c core.whitespace=cr-at-eol diff --check
git diff --exit-code origin/main -- static/css/landing.css static/js/landing.js \
  static/js/landing-video.js render.yaml migrations .github/workflows
```

Os comandos passaram na revisão inicial e após o commit de implementação. `cr-at-eol` permite verificar espaços preservando as terminações CRLF preexistentes de dois templates; não houve conversão integral desses arquivos. A revisão confirmou sete arquivos de código/teste e este documento, sem mudanças fora do escopo. Um inventário adicional confirmou os quatro templates raiz de interface, cada um com exatamente uma inclusão da nova folha, e os e-mails fora da política.

## GitHub Actions

Os resultados acima são locais. Aprovação local não equivale a aprovação do GitHub Actions. As [execuções da branch](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions?query=branch%3Afeature%2Fcontrole-selecao-textos-nexo) devem ser consultadas para o SHA efetivamente enviado; o relatório final da entrega informa separadamente a situação remota verificada após a abertura do PR. Nenhum workflow foi alterado ou desativado.

## Compatibilidade e limites

A execução real usa **Chromium 154 no Linux**, por Playwright. `ControlOrMeta` resolve para Control neste ambiente; Command no macOS não foi executado. O cenário móvel usa `has_touch` e `is_mobile`, com taps e teclado: não reproduz a seleção por pressão prolongada nem o menu nativo de um aparelho físico.

A propriedade padronizada e o prefixo WebKit foram adotados para compatibilidade, mas não houve execução em Firefox, Safari/iOS ou Android físico; não há comparação empírica entre esses navegadores nesta entrega. Gerenciadores de senhas e leitores de tela também dependem de homologação manual. Seus atributos, textos, foco e scripts não foram alterados.

## Reprodução seletiva no projeto empresarial

1. Examinar os templates raiz, folhas de estilo, regras de seleção já existentes, formulários, controles `readonly`, editores, scripts de clipboard e componentes especializados da base empresarial atual. Não substituir essa base por clone deste repositório.
2. Reproduzir somente a política necessária de `nexo-selecao.css`, conciliando exceções legítimas encontradas na empresa. Confirmar especialmente campos internos de editores e contêineres que realmente dependam de seleção.
3. Incluir a folha após os estilos pertinentes em cada template raiz de interface. Não incluí-la em e-mails ou documentos de impressão sem necessidade específica.
4. Se houver o mesmo bloco legado em `nexo.css`, substituir apenas esse bloco; preservar outros seletores e o marcador de dados mascarados. Não copiar integralmente arquivos de tema, layout ou navegação.
5. Validar arrasto sobre apresentação, seleção em campos, colagem real com teclado, recorte/cópia, pesquisas, formulários, suporte, NexoBot, gráficos, vídeo e navegação. Testar as oito larguras e os três temas com dados fictícios.
6. Revisar diff e compatibilidade com trabalhos paralelos, executar as suítes pertinentes e abrir PR próprio. Esta implementação não autoriza migração, merge ou deploy empresarial.

## Reversão exclusiva desta política

Remover somente os quatro vínculos a `css/nexo-selecao.css` e o novo arquivo; restaurar o bloco antigo de seleção em `nexo.css` se o objetivo for voltar exatamente ao comportamento anterior. Não reverter templates ou folhas inteiros, pois poderão conter trabalhos posteriores. Os testes específicos devem acompanhar a política escolhida, sem desligar testes de outras funcionalidades. Nenhuma operação de banco ou infraestrutura é necessária.

## Resultado

A política centralizada impede arrasto seletivo sobre apresentação e preserva edição, seleção e área de transferência nos controles apropriados. As verificações executadas comprovaram login, cadastro, CNPJ, e-mail, senha, suporte, NexoBot, pesquisas, configurações, editores, gráficos, menus, navegação, foco, temas e responsividade. O código e os testes foram enviados à branch independente; este documento acompanha a entrega para revisão em Pull Request.

Total local dos grupos distintos: **521 testes aprovados**, com **1 cenário opcional de capturas ignorado**; reexecuções não foram somadas. Não se declara execução da suíte integral do repositório: foram selecionadas as suítes pertinentes listadas acima. As restrições de browser e homologação manual constam na seção de compatibilidade.

O trabalho publicado da landing foi preservado e nenhuma alteração remota inédita foi incorporada automaticamente. Projeto empresarial, serviços de banco remoto e configurações de infraestrutura permaneceram intactos. Merge, deploy e homologação humana permanecem fora desta entrega.
