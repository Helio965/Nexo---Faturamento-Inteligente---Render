# Correção do cabeçalho fixo e da fresta superior

## 1. Identificação

| Campo | Registro |
| --- | --- |
| Implementação | Segunda implementação de homologação: proteção visual contínua do cabeçalho e ajuste de legibilidade |
| Data e horário deste registro | 2026-11-13 13:21 -03 — `America/Sao_Paulo` |
| Conclusão da validação local | 2026-11-13 13:35:20 -0300 — `America/Sao_Paulo` |
| Repositório autorizado | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Ambiente | Testes e homologação do NEXO |
| Branch | `fix/topbar-fresta-superior-responsividade` |
| Commit inicial, confirmado em `origin/main` antes das alterações | `e1e3e73aa23aad5d588f74563296f4fe1a944417` |
| Commit de código e testes | `35ae4d0ef16dc5af8a20d0af6a411be53732f0a3` |
| Commit final de implementação | `35ae4d0ef16dc5af8a20d0af6a411be53732f0a3`; a documentação e suas evidências são registradas em commit documental posterior, identificável no histórico deste arquivo |
| Status | Implementação concluída e validada localmente; revisão e homologação remotas pendentes conforme seções 6 e 10 |
| Integração | Entrega em branch e Pull Request para revisão, sem merge automático e sem deploy manual |

A conferência inicial encontrou a árvore de trabalho limpa e o checkout no mesmo commit da versão mais recente de `main`. A implementação anterior do seletor de temas já estava integrada pelo PR #46. A pasta `POSSIVEIS ATUALIZAÇÕES EMPRESA` foi reutilizada. O documento `2026-11-12_Seletor_de_Tema_Nas_Configuracoes_Admin_Cliente.md` não foi sobrescrito nem alterado.

O escopo funcional se limita às duas folhas de estilo do painel e à inclusão de uma decoração no cabeçalho compartilhado. Não houve acesso ao Supabase, alterações em infraestrutura do Render, mudanças no projeto empresarial, alterações em migrações versionadas ou no funcionamento do backend.

## 2. Problema identificado

O cabeçalho compartilhado de ADMIN e CLIENTE já acompanhava a rolagem com `position: sticky`. Entretanto, mantinha uma distância superior de 14 px no desktop e de 10 px abaixo de 992 px de largura. Durante a rolagem, essa faixa permitia ler partes do conteúdo da página sem passar pelas camadas de vidro do componente.

As capturas anteriores reproduzem o defeito com dados das próprias páginas: no dashboard administrativo, números dos indicadores aparecem acima do cabeçalho; no dashboard do cliente em 390 px, parte do faturamento permanece visível nessa faixa. Os cantos externos aos raios arredondados também não eram protegidos pelas camadas existentes.

Dentro do cabeçalho, o desfoque mais intenso perdia força progressivamente na parte inferior. A camada suave não oferecia, sozinha, a ocultação necessária. A correção precisava proteger toda a região do topo sem aumentar a largura da barra, conectá-la à sidebar ou retirar seus cantos arredondados.

## 3. Causa técnica confirmada

Em `static/css/nexo.css`, a regra original combinava:

```css
.topbar {
  position: sticky;
  top: var(--shell-gap); /* 14px */
  margin: var(--shell-gap) var(--shell-gap) 0 0;
}
```

A margem superior determinava o afastamento inicial; `top` conservava esse afastamento quando o elemento se tornava aderente durante a rolagem. A media query até `991.98px` repetia o problema com `margin: 10px 10px 0` e `top: 10px`.

Os pseudo-elementos `::before` e `::after` tinham `inset: -1px` e `border-radius: inherit`: cobriam a caixa e sua borda, respeitando o contorno arredondado, mas não alcançavam a fresta superior nem os pixels externos aos cantos.

O `::before` usava `blur(26px) saturate(160%)` com máscara cujo último ponto tinha alpha `0.06`. O véu dessa camada terminava em alpha `0.30`; a máscara reduzia sua contribuição na base para aproximadamente `0.018`. Somada ao véu `0.22` do `::after`, a cobertura de cor nessa região era de aproximadamente 23%, enquanto a camada que permanecia inteira aplicava apenas `blur(8px)`. Essa composição explica a proteção desigual; aumentar apenas o desfoque não corrigiria as áreas sem cobertura.

O cabeçalho é um contexto de empilhamento em `z-index: 1020`. A sidebar usa `1040`, sua sobreposição usa `1035`, os modais Bootstrap usam as camadas `1050/1055`, os avisos usam `1080` e o NexoBot usa `1090`. A solução não cria contextos novos em `.app-shell` ou `.main-area`, que poderiam aprisionar os modais abaixo de seus próprios fundos.

## 4. Arquivos modificados

| Caminho | Função e seções alteradas | Alteração e motivo |
| --- | --- | --- |
| `static/css/nexo.css` | Design system interno; tokens, shell, cabeçalho e media queries | Compartilha o cenário do painel em `--shell-background`; elimina o afastamento vertical; inclui a proteção dos cantos; torna o vidro uniforme; ajusta os fallbacks e a entrelinha do título. Preserva dimensões horizontais, alturas, controles e raios. |
| `static/css/nexo-tema-claro.css` | Variação clara do painel; shell e cabeçalho | Define o cenário compartilhado como `var(--bg)` e aplica o fallback opaco à camada arredondada `::before`, mantendo a proteção independente dos cantos. |
| `templates/base.html` | Estrutura global autenticada; início do `<header class="topbar">` | Acrescenta apenas `<span class="topbar-shield" aria-hidden="true"></span>`, sem função interativa ou alteração nos controles existentes. |
| `tests/test_topbar_navegador.py` | Novo módulo de regressão do cabeçalho em Chromium | Verifica geometria renderizada, rolagem nas duas direções, cobertura por pixels, temas, fallback, páginas de ADMIN/CLIENTE, orientação, escala e componentes interativos. |
| `tests/test_gerenciamento_navegador.py` | Regressão existente do cabeçalho global | Atualiza somente as expectativas substituídas pela correção: vidro uniforme sem máscara, ausência do segundo filtro e posição superior zero. Preserva verificações de margens, título, borda, cliques e menu do sino. |
| `tests/test_tema_interface.py` | Verificações estruturais dos fallbacks claros | Passa a conferir o fundo branco em `.topbar::before`, onde a superfície arredondada é efetivamente pintada na nova composição. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-13_Correcao_Cabecalho_Fixo_e_Fresta_Superior.md` | Documento desta implementação | Registra diagnóstico, implementação, validação, reprodução e reversão. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-13_topbar_*.png` | Oito capturas comparativas listadas na seção 6 | Conservam as evidências do defeito e do comportamento após o ajuste, com dados fictícios locais. |

Os arquivos existentes `tests/test_overflow_navegador.py`, `tests/test_tema_navegador.py` e `tests/test_configuracoes_navegador.py` são usados na validação sem alteração de suas expectativas. Os formulários, rotas, JavaScript de temas, autenticação, notificações e regras de negócio não fazem parte do diff.

## 5. Implementação técnica

### 5.1. Posição vertical e preservação horizontal

O cabeçalho permanece no fluxo do documento com `position: sticky`, agora em `top: 0`. A margem superior passa a zero no desktop e no celular. Não é necessário substituir o componente por `position: fixed` nem acrescentar um espaçador artificial.

As medidas horizontais foram preservadas:

| Propriedade | Desktop, a partir de 992 px | Abaixo de 992 px |
| --- | --- | --- |
| Início horizontal do cabeçalho | `sidebar-w + 2 × shell-gap`, atualmente 292 px | 10 px |
| Margem direita | 14 px | 10 px |
| Altura | 68 px | 60 px |
| Raio | 22 px | 18 px |

O primeiro conteúdo continua abaixo do cabeçalho no fluxo normal. Os `scroll-margin-top` existentes, usados para foco e âncoras, foram preservados: seu espaço adicional continua conservador após a redução do offset vertical.

### 5.2. Proteção dos cantos e recomposição do fundo

Foi extraída para `--shell-background` a mesma composição de paisagem, gradientes e cor que já pintava o painel. O fundo fixo do shell e a proteção do cabeçalho consomem esse único token, evitando duas descrições divergentes do cenário.

```css
.topbar-shield {
  position: absolute;
  inset: -1px;
  clip-path: inset(0);
  pointer-events: none;
  z-index: -2;
}
.topbar-shield::before {
  content: "";
  position: fixed;
  inset: 0;
  background: var(--shell-background);
}
```

A proteção tem o tamanho local do cabeçalho, inclusive sua borda. Seu pseudo-elemento pinta o cenário nas coordenadas da viewport; o recorte local limita essa pintura ao retângulo protegido. Assim, os pixels externos aos cantos arredondados mostram o fundo do painel, em vez do conteúdo rolável. Como o cenário coincide com o restante do shell, não surge uma faixa retangular de cor diferente.

O recorte pertence somente à decoração. O próprio cabeçalho não recebe `overflow: hidden`, `clip-path`, `transform` ou filtro que recorte o menu de notificações. Não há bloqueio de rolagem no documento inteiro. A decoração é excluída da árvore de acessibilidade com `aria-hidden="true"` e não participa dos cliques ou toques.

### 5.3. Vidro e ocultação contínua

O `::before` do cabeçalho mantém o filtro forte já existente, `blur(26px) saturate(160%)`, com véu escuro uniforme `rgba(14, 10, 30, 0.66)`. A opacidade conserva a intensidade do véu que existia no topo, agora distribuída pela altura toda; a máscara em degradê foi retirada. O `::after` continua com acabamento `rgba(16, 12, 30, 0.22)`, anel e brilho interno, mas deixa de aplicar o filtro suave redundante.

A ocultação combina cenário opaco atrás da superfície, véu de cor e desfoque. Ela não depende de um aumento de `blur()`. Os pseudo-elementos de acabamento continuam arredondados por `border-radius: inherit` e cobrem a borda com `inset: -1px`.

### 5.4. Tema claro e preferência por menos transparência

No tema claro, `--shell-background: var(--bg)` recompõe o fundo lavanda existente. Os véus brancos `0.6` e `0.9`, o anel e o brilho claro permanecem vinculados ao tema. O modo Sistema continua resolvido pelo mecanismo anterior nas Configurações, sem novo controle no cabeçalho.

Sem suporte a `backdrop-filter`, a camada arredondada `::before` recebe um degradê totalmente opaco no escuro e fundo `#ffffff` no claro. O mesmo princípio é usado em `prefers-reduced-transparency: reduce`, que também desliga o filtro. A proteção dos cantos e o acabamento continuam ativos nesses ramos.

O ramo geral de transparência reduzida passa a alterar `--shell-background` para `var(--bg)`, em vez de trocar apenas o fundo do shell. Dessa forma, shell e proteção usam o mesmo fundo liso também nessa preferência.

O fallback precisa pintar a camada arredondada acima da proteção. Pintar somente o fundo do elemento `.topbar` e ocultar os dois pseudo-elementos permitiria que a proteção, como descendente do contexto de empilhamento, cobrisse esse fundo e apagasse o contraste visual do componente.

### 5.5. Proporção, alinhamento e responsividade

O título principal passa discretamente de `1.12rem` para `1.16rem`, com `line-height: 1.2`. O subtítulo conserva `0.68rem`, recebe `line-height: 1.25` e separação inferior de 2 px. A centralização continua apoiada no `align-items: center` do layout flex.

No celular estreito, o título conserva `0.98rem`, as duas linhas e a quebra de palavras existentes. A altura da barra não aumenta. O sino conserva 42 px e o avatar 36 px. A informação do usuário continua oculta onde o espaço é insuficiente; no desktop, os nomes longos continuam cedendo espaço ao título, com reticências e nome completo no atributo `title`.

### 5.6. Empilhamento e componentes

O `z-index` externo do cabeçalho permanece `1020`. Dentro dele, a proteção usa `-2`, o vidro e seu acabamento usam `-1`, e os controles permanecem acima dessas decorações. Não há uma nova camada cobrindo a sidebar, os modais ou o NexoBot.

O menu do sino conserva sua marcação, eventos Bootstrap e formulários. A sidebar móvel conserva os botões de abertura/fechamento e a sobreposição de fundo. Nenhuma regra de posicionamento dos controles foi substituída.

## 6. Testes realizados

### 6.1. Ambiente e isolamento

Os testes usam o servidor Flask local, usuários e empresas fictícios e bancos SQLite descartáveis da infraestrutura já existente em `NavegadorCase`/`ContratosCase`. Essa infraestrutura inicializa o esquema com migrações locais nesses bancos de teste. Não houve acesso ou execução de migrações no Supabase nem em qualquer banco externo; nenhum arquivo de migração foi alterado.

O navegador é Chromium local em `/usr/bin/chromium`, controlado pelo Playwright 1.56.0. Bootstrap, ícones, Plotly e Socket.IO são respondidos por cópias locais em `/workspace/work/cdn`, com a conferência de SRI prevista no harness. Não foi necessário alterar dependências de produção.

### 6.2. Comandos

Executados a partir da raiz do repositório:

```bash
.venv/bin/python -B -m unittest tests.test_tema_interface -v

.venv/bin/python -B -m unittest \
  tests.test_identidade_visual \
  tests.test_navegacao_admin \
  tests.test_nexobot_interface -v

NEXO_TEST_BROWSER=1 \
NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/workspace/work/cdn \
.venv/bin/python -B -m unittest \
  tests.test_overflow_navegador \
  tests.test_tema_navegador \
  tests.test_configuracoes_navegador \
  tests.test_gerenciamento_navegador -v

NEXO_TEST_BROWSER=1 \
NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/workspace/work/cdn \
.venv/bin/python -B -m unittest tests.test_topbar_navegador -v

NEXO_TEST_BROWSER=1 \
NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/workspace/work/cdn \
.venv/bin/python -B -m unittest \
  tests.test_topbar_navegador.TopbarNavegadorTests.test_sino_sidebar_modal_e_nexobot_continuam_clicaveis -v

NEXO_TEST_BROWSER=1 \
NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/workspace/work/cdn \
.venv/bin/python -B -m unittest \
  tests.test_identidade_visual.IdentidadeVisualBrowserTests -v

git diff --check
```

Os caminhos `/workspace/work` acima identificam apenas artefatos temporários da execução, não dependências do produto. Em outra máquina, `NEXO_TEST_CDN_DIR` deve apontar para as cópias íntegras preparadas conforme os testes e a CI existentes.

### 6.3. Cobertura e resultados

**138 testes distintos aprovados nas rodadas de validação local, sem falha pendente.**

| Grupo | Resultado registrado |
| --- | --- |
| `tests.test_tema_interface` | 24 aprovados, 2,740 s |
| `tests.test_identidade_visual`, `tests.test_navegacao_admin`, `tests.test_nexobot_interface` | 30 aprovados na rodada sem navegador; 3 testes de identidade inicialmente omitidos foram aprovados na execução explícita de `IdentidadeVisualBrowserTests` (38,929 s), totalizando 33 distintos |
| `tests.test_overflow_navegador`, `tests.test_tema_navegador`, `tests.test_configuracoes_navegador`, `tests.test_gerenciamento_navegador` | 76 aprovados em uma execução concluída sem falhas ou omissões, 928,687 s |
| `tests.test_topbar_navegador` | 5 cenários distintos aprovados: 4 na rodada consolidada e o cenário de interação reexecutado com sucesso após a correção da espera do painel (38,856 s) |
| Revisão do diff e `git diff --cached --check` | Aprovados; somente os arquivos declarados nesta documentação |

Os cenários renderizados não registraram erros JavaScript no coletor do harness. O teste global existente percorreu as páginas autenticadas em cinco resoluções; os novos testes acrescentaram 352 medições de geometria e rolagem, 32 comparações visuais e 8 combinações de fallback/transparência reduzida.

Na elaboração dos novos testes, foram corrigidas premissas do próprio ensaio: aguardar os debounces de 120/150 ms do layout após redimensionar, conferir o dropdown em relação ao sino que o ancora e manter as expectativas de fallback na camada `::before`. O NexoBot existe somente no CLIENTE; seu contêiner externo não tem caixa visível, portanto a espera verifica o painel interno. Essas correções não exigiram mudanças adicionais no produto. A rodada consolidada final aprovou quatro cenários; a interação foi reexecutada após ajustar essa espera e também passou. Os cinco cenários distintos estão verificados no arquivo final.

Os três testes de navegador de identidade visual inicialmente omitidos na execução sem `NEXO_TEST_BROWSER` foram executados separadamente com o navegador habilitado e aprovados. As contagens acima são de testes distintos, sem duplicar reexecuções.

Permanecem para homologação: revisão do Pull Request, CI remota e ensaios em Firefox, Safari e aparelhos físicos. A suíte completa do repositório não foi executada localmente; foram selecionadas as regressões relacionadas a esta alteração. Não há falha local pendente nos cenários verificados.

Na comparação de 8 larguras × 2 temas × 2 posições de rolagem, a composição final com véu `0.66` apresentou diferença máxima de **0/255** nos pixels protegidos; a menor diferença máxima da região de controle exposta abaixo do cabeçalho foi de **240/255**. Servindo as folhas de estilo anteriores com o mesmo oráculo, o controle de regressão reproduziu diferença de **251/255**, acima do limite de 3/255. O teste, portanto, distingue o defeito anterior da composição corrigida e não depende de tornar o vidro quase sólido.

A nova regressão verifica as larguras 320, 360, 390, 430, 768, 1024, 1366 e 1920 px, em claro e escuro. Mede a posição real antes da rolagem e após pequenos deslocamentos junto ao topo, avanço para posições maiores e retorno para cima. Também confere altura, raios, margens laterais, centralização dos controles, ausência de sobreposição e ausência de rolagem horizontal.

O cenário visual acrescenta conteúdo em fluxo normal com texto, números, cartões, tabela e gráfico SVG de alto contraste. Compara duas capturas: conteúdo visível e o mesmo conteúdo oculto sem alterar o fluxo. O retângulo comparado vai do topo da viewport à borda inferior do cabeçalho, incluindo os cantos, título e sino. A tolerância máxima é de 3 níveis por canal em 255. Uma região de controle abaixo do cabeçalho precisa mudar em mais de 100 níveis, comprovando que a cena contém conteúdo contrastante efetivamente exposto.

O fallback sem filtro é exercitado retirando o reconhecimento de `backdrop-filter` nas folhas servidas exclusivamente pelo teste: a expressão `@supports` torna-se falsa e o ramo real de fallback é executado. A preferência por transparência reduzida é ativada por emulação de mídia no Chromium. Isso não equivale a ensaios em motores antigos sem a propriedade.

São incluídas páginas representativas de ADMIN (`/admin/dashboard`, `/admin/empresas`, `/admin/contratos`, `/admin/analises`, `/admin/tickets`, `/admin/configuracoes`) e CLIENTE (`/cliente/dashboard`, `/cliente/historico`, `/cliente/tickets`, `/cliente/configuracoes`). As suítes existentes acrescentam outras páginas autenticadas, nomes extensos, gráficos reais, foco e ancoragem.

As alterações de orientação e de altura são simuladas no mesmo documento, incluindo 390 × 844, 844 × 390 e 390 × 660. O ensaio de escala usa o padrão existente de viewport de 911 × 512 CSS px com fator 1.5, equivalente de layout a aproximadamente 1366 px em 150%; não aciona o controle de zoom da interface do navegador.

### 6.4. Capturas comparativas

Os oito arquivos estão diretamente na pasta existente `POSSIVEIS ATUALIZAÇÕES EMPRESA`, ao lado deste documento:

| Cenário | Antes | Depois |
| --- | --- | --- |
| ADMIN, 1366 px, escuro | [2026-11-13_topbar_antes_1366_dark_admin.png](2026-11-13_topbar_antes_1366_dark_admin.png) | [2026-11-13_topbar_depois_1366_dark_admin.png](2026-11-13_topbar_depois_1366_dark_admin.png) |
| ADMIN, 1366 px, claro | [2026-11-13_topbar_antes_1366_light_admin.png](2026-11-13_topbar_antes_1366_light_admin.png) | [2026-11-13_topbar_depois_1366_light_admin.png](2026-11-13_topbar_depois_1366_light_admin.png) |
| CLIENTE, 390 px, escuro | [2026-11-13_topbar_antes_390_dark_cliente.png](2026-11-13_topbar_antes_390_dark_cliente.png) | [2026-11-13_topbar_depois_390_dark_cliente.png](2026-11-13_topbar_depois_390_dark_cliente.png) |
| CLIENTE, 390 px, claro | [2026-11-13_topbar_antes_390_light_cliente.png](2026-11-13_topbar_antes_390_light_cliente.png) | [2026-11-13_topbar_depois_390_light_cliente.png](2026-11-13_topbar_depois_390_light_cliente.png) |

As capturas posicionam o mesmo indicador real próximo de `y = 2px` na viewport. No desktop, a caixa do cabeçalho passa de `(x=292, y=14, largura=1060, altura=68)` para `(x=292, y=0, largura=1060, altura=68)`. Em 390 px, passa de `(x=10, y=10, largura=370, altura=60)` para `(x=10, y=0, largura=370, altura=60)`. A pequena diferença entre os valores de `scrollY` antes e depois compensa exatamente a remoção da margem superior, mantendo o indicador na mesma posição para comparação.

## 7. Guia de reprodução na versão empresarial

Esta entrega não foi aplicada ao projeto empresarial. Uma integração futura deve analisar o código correspondente e reproduzir o princípio da correção, sem substituir os arquivos completos pelo conteúdo do ambiente de testes.

1. Localizar o cabeçalho compartilhado, seu ancestral de rolagem, o fundo efetivo do painel e todas as regras de breakpoint que alteram `top`, margem, altura e raios. Conferir se o projeto empresarial usa os mesmos tokens e o mesmo contexto de layout.
2. Registrar as medidas horizontais antes da mudança em desktop, tablet e celular. Identificar adaptações locais de sidebar, largura máxima e nome do usuário; não assumir os valores de 292/14/10 px como universais.
3. Remover apenas o afastamento vertical que deixa conteúdo descoberto. Preservar `sticky` se seu contêiner permitir o mesmo comportamento; confirmar a acessibilidade do primeiro conteúdo e das âncoras.
4. Compartilhar a composição real do fundo em um token equivalente. O cenário da proteção precisa ter as mesmas coordenadas e a mesma resolução visual do cenário do shell; fundos específicos de cada tema e a preferência por menos transparência também precisam usar esse token.
5. Acrescentar a decoração com `aria-hidden` e `pointer-events: none` no componente correspondente. Limitar o recorte à decoração, deixando menus e controles fora dele. Não criar contextos de empilhamento em ancestrais que contenham modais.
6. Ajustar o véu e o desfoque para proteção uniforme na altura toda. Conferir se existem outros pseudo-elementos, máscaras, filtros ou regras específicas que sobrescrevam o resultado. Reproduzir um fallback de superfície opaca sem desativar a proteção dos cantos.
7. Reavaliar a tipografia em função das fontes e dos títulos reais. Preservar as adaptações móveis e o espaço para sino/avatar; verificar nomes longos e o início do breakpoint de desktop.
8. Executar a matriz de testes e as comparações de pixels com dados fictícios locais no projeto de destino. Repetir os ensaios de menus, modais, foco, tema Sistema e gráficos. Fazer revisão visual nos navegadores suportados antes de aprovar a integração.
9. Integrar por branch e revisão próprias do ambiente empresarial, respeitando seus controles de publicação. Não copiar migrações, configuração de infraestrutura, dados ou credenciais desta entrega.

## 8. Riscos e compatibilidade

| Ponto | Efeito possível | Prevenção ou limite da validação |
| --- | --- | --- |
| Mudança futura no fundo do shell | Cantos podem mostrar um cenário diferente se a proteção não acompanhar | Manter shell e proteção consumindo `--shell-background`, inclusive em temas e preferências de mídia. |
| `transform`, `filter`, `contain` ou contexto novo nos ancestrais | Alteração do referencial da decoração fixa ou da prioridade dos modais | Não acrescentar essas propriedades a `.app-shell`/`.main-area` sem repetir os ensaios renderizados. |
| Recorte aplicado ao cabeçalho inteiro | Menu do sino ou foco visual podem ser cortados | Manter `clip-path` restrito a `.topbar-shield`. |
| Fallback pintado somente no fundo do pai | A proteção pode encobrir a superfície arredondada | Pintar o fallback em `::before`, acima da proteção, e conservar o acabamento. |
| Títulos e nomes longos em resoluções próximas a 992 px | Disputa de espaço horizontal | Conservar as limitações responsivas do nome e as verificações existentes de títulos extensos. |
| Mudança dinâmica da viewport móvel | O cenário precisa permanecer alinhado durante o redimensionamento | Usar o cenário fixo à viewport com recorte local; não depender de `background-attachment: fixed`. |
| Outros motores e aparelhos físicos | Diferenças de composição e de comportamento do navegador móvel | A validação automatizada local usa Chromium; Safari, Firefox e aparelhos físicos continuam sujeitos à homologação do projeto. |

Não há tentativa de modificar a barra de endereço ou os controles nativos do navegador. A proteção atua exclusivamente na área renderizada do site.

## 9. Procedimento de reversão

Antes de integrar, basta não aplicar o Pull Request ou descartar exclusivamente esta branch. Após uma eventual integração, desfazer o commit de implementação `35ae4d0ef16dc5af8a20d0af6a411be53732f0a3` em uma nova branch de correção e submeter o resultado à revisão. A documentação e as capturas podem permanecer como histórico técnico.

Se houver alterações posteriores nos mesmos trechos, reverter somente os blocos desta entrega, após comparar o diff do commit:

1. Retirar o `span.topbar-shield` e suas duas regras de decoração.
2. Restaurar o posicionamento vertical anterior somente se esse for o comportamento de reversão aprovado.
3. Restaurar a composição original do fundo, os dois filtros, a máscara e os fallbacks anteriores, sem sobrescrever outros ajustes de tema ou do layout.
4. Reverter o ajuste específico de tipografia e as expectativas de teste diretamente relacionadas a esta implementação.
5. Executar novamente as regressões de temas, menus, foco e responsividade.

Não restaurar `base.html` ou as folhas de estilo inteiras a partir de um commit antigo. Essa ação poderia remover a implementação anterior que transferiu os temas para as Configurações ou outras mudanças posteriores. Não são necessárias operações em banco de dados nem em infraestrutura para reverter este ajuste visual.

## 10. Resultado final

O código corrige a causa geométrica da fresta ao eliminar o afastamento vertical e protege também os pixels externos aos cantos arredondados. A superfície de vidro recebe proteção uniforme, com uma composição que preserva o cenário do painel e as margens laterais. A proporção do título foi ajustada sem aumentar a altura da barra ou o tamanho dos controles.

Os critérios efetivamente verificados, seus resultados e eventuais pendências constam da seção 6. A homologação visual nos demais navegadores suportados e a revisão do Pull Request antecedem qualquer integração. Nenhum merge automático, deploy manual, acesso ao Supabase ou alteração do ambiente empresarial faz parte desta entrega.


Critérios aprovados localmente: cabeçalho estável nas duas direções de rolagem; proteção contínua do topo, cantos e borda inferior; preservação de margens, largura, altura e raios; centralização e proporção dos textos; sino, avatar, nomes extensos e menu móvel; claro, escuro e Sistema; ausência de overflow e erros JavaScript nos cenários executados; fallback e transparência reduzida; foco e primeiro conteúdo acessíveis. Documento e oito capturas foram registrados na pasta existente. Não há teste do escopo selecionado com falha pendente.
