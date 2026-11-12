# Seletor de tema nas Configurações de ADMIN e CLIENTE

## A. Identificação

| Campo | Registro |
| --- | --- |
| Implementação | Controle de aparência Sistema, Claro e Escuro nas Configurações do NEXO |
| Data e horário de execução (registro inicial) | 2026-11-12 16:10:33 -03 (UTC-0300) — fuso `America/Sao_Paulo` |
| Conclusão da validação local | 2026-11-12 16:29:06 -0300 — `America/Sao_Paulo` |
| Repositório de origem | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Ambiente autorizado | Desenvolvimento e homologação; separado do sistema empresarial |
| Branch | `feature/tema-configuracoes-admin-cliente` |
| Referência de `main` antes da alteração | `995a76c0392d799a34fba4c1c3a64fc246dd8361` |
| Commit da implementação | `f14c79b08bff11b753df12415d0dd9e7596c8120` (código e testes; este documento é registrado no commit documental seguinte) |
| Status de validação | Validação local do escopo concluída: 251 testes distintos aprovados nas rodadas executadas, sem falhas pendentes; homologação humana e CI do PR ainda pendentes |
| Integração e publicação | Sem merge ou deploy nesta entrega; integração depende da revisão e homologação do PR |

A existência da pasta `POSSIVEIS ATUALIZAÇÕES EMPRESA` foi verificada antes de sua criação. Ela não existia nesta implementação. Este documento registra pontos de integração e reprodução; não contém cópias integrais de código.

## B. Objetivo e comportamento resultante

O portal autenticado oferecia somente a alternância entre claro e escuro por um botão circular com sol/lua no cabeçalho. A página do CLIENTE apresentava um cartão Tema informativo que remetia ao botão superior; a página do ADMIN não apresentava um seletor de aparência próprio.

O botão foi retirado do cabeçalho global. A seleção está disponível diretamente em:

- `/cliente/configuracoes`: seção Preferências, cartão Tema, fora do formulário de Avisos.
- `/admin/configuracoes`: nova seção Aparência, cartão Tema, após Conta e e-mail e antes de Documentos Legais; atalho Aparência no menu de seções.

As opções são Sistema, Claro e Escuro. A mudança é imediata e usa exclusivamente o navegador. Não depende de Salvar preferências, requisição HTTP, recurso de configuração da conta ou disponibilidade de migrações de outros módulos.

| Opção | Valor em `localStorage.theme` | Aparência aplicada |
| --- | --- | --- |
| Sistema | `system` | Resolvida com `prefers-color-scheme: dark`; acompanha alterações do dispositivo |
| Claro | `light` | Tema claro existente do NEXO |
| Escuro | `dark` | Tema escuro existente do NEXO |

Os valores antigos `light` e `dark` continuam válidos. Ausência de preferência e valores desconhecidos continuam resultando em escuro, mesmo quando o dispositivo prefere claro. O modo Sistema é uma opção expressa do usuário.

## C. Arquivos modificados

Todos os caminhos abaixo são completos a partir da raiz do repositório autorizado.

| Caminho | Tipo de alteração | Função e justificativa |
| --- | --- | --- |
| `templates/base.html` | Alteração pontual do HTML e JavaScript existente | Retira o botão `themeToggle` e seu script acoplado; centraliza resolução e aplicação do tema no script autenticado do início do `head`; amplia sincronização entre abas, cache de navegação e mudanças do sistema; ajusta o espaço do cabeçalho após a retirada do controle. |
| `templates/_seletor_tema.html` | Novo componente Jinja compartilhado | Define uma única estrutura dos três botões e texto de ajuda para ADMIN e CLIENTE, evitando controles divergentes. |
| `templates/cliente/configuracoes.html` | Substituição de conteúdo do cartão existente | Inclui o seletor funcional no cartão Tema, sem modificar os formulários ou condicionar o controle à disponibilidade das preferências da conta. |
| `templates/admin/configuracoes.html` | Inclusão de seção e atalho | Adiciona Aparência e reutiliza o mesmo componente, preservando senha, SMTP, cópia de chamados, documentos e auditoria. |
| `static/css/nexo.css` | Inclusão de regras locais do seletor | Usa tokens já existentes para grupo horizontal, seleção, hover e foco em ambos os temas, sem alterar a paleta oficial. |
| `static/css/nexo-tema-claro.css` | Ajuste mínimo de acessibilidade | Acrescenta halo claro ao foco do botão de fechar a gaveta, preservando contraste sobre o avatar agora visível em 320 px; mantém o contorno roxo existente. |
| `tests/test_tema_interface.py` | Atualização de verificações estruturais | Remove a exigência do botão antigo e verifica o controle compartilhado apenas nas Configurações, os três valores, CSP e preservação do sino/perfil. |
| `tests/test_tema_navegador.py` | Atualização e ampliação de testes de comportamento | Exercita os três modos, armazenamento, mudanças do sistema, abas, navegação, primeira pintura, gráficos, acessibilidade e preservação das páginas públicas. |
| `tests/test_configuracoes_navegador.py` | Atualização e ampliação de regressões de Configurações | Amplia as larguras para 320, 390, 768, 1024 e 1366 px, verifica grupo horizontal/contraste, funcionamento sem migrações de configurações e ausência de POST; usa o sino no teste de foco do cabeçalho após retirada do botão de tema. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-12_Seletor_de_Tema_Nas_Configuracoes_Admin_Cliente.md` | Novo documento técnico | Registra a alteração de homologação, validação real, requisitos de reprodução e reversão seletiva. |

`static/css/nexo-tema-claro.css` conserva suas paletas e regras de tema; a única mudança é o halo de foco da gaveta descrito acima. Nenhum arquivo de autenticação, permissões, backend, banco, migração, credencial, dependência de produção, hospedagem ou infraestrutura integra esta implementação.

## D. Implementação detalhada

### D.1. Cabeçalho e carregamento inicial

Em `templates/base.html`, foi removido o botão com `id="themeToggle"`, classes `bell-btn theme-toggle`, ícone sol/lua e atributos associados à alternância. O script que procurava esse elemento foi retirado do cabeçalho, eliminando o vínculo JavaScript com um botão inexistente. Não há mais restauração de foco por `sessionStorage.themeFoco`, porque a seleção acontece nas Configurações e não requer recarregar essas páginas.

O sino `bellBtn`, seu dropdown, os formulários de notificações, o avatar, os dados de usuário, o menu lateral e os controles de navegação permanecem no mesmo fluxo. O espaçamento continua apoiado no layout flex existente da barra superior.

A regra específica que ocultava `.topbar-right .user-chip` abaixo de 390 px foi removida: ela reservava espaço para o botão de tema e deixou de ser necessária. O limite de largura de `.user-meta` passou de `calc(100vw - 810px)` para `calc(100vw - 756px)`, liberando os 54 px anteriormente reservados ao botão e seu intervalo. O tratamento de nomes extensos por reticências e o atributo `title` foram preservados.

A infraestrutura do tema permanece dentro de `{% if current_user.is_authenticated %}`. Seu script continua com `nonce="{{ csp_nonce }}"`, antes das folhas de estilo. A preferência é lida e resolvida nessa etapa, com atualização de `data-theme` e `data-bs-theme` antes da primeira pintura. O stylesheet claro continua sendo carregado somente para sessões autenticadas; suas regras continuam dependentes de `html[data-theme="light"]`.

### D.2. Componente compartilhado e acessibilidade

`templates/_seletor_tema.html` contém `.theme-selector`, com `role="group"`, nome acessível Tema e associação ao texto `tema-preferencia-ajuda`. Os três botões `.theme-option` usam:

- `type="button"`, impedindo submissão involuntária de formulários.
- `data-theme-preference="system"`, `"light"` ou `"dark"`, que é o contrato consumido pelo mecanismo global.
- Rótulos acessíveis Sistema, Claro e Escuro, além dos textos visíveis.
- Ícones Bootstrap `bi-display`, `bi-sun` e `bi-moon`, decorativos com `aria-hidden="true"`.
- `aria-pressed`, atualizado para refletir exclusivamente a preferência lógica selecionada.

O grupo usa botões HTML nativos, alcançáveis por Tab e acionáveis por Enter ou Espaço. O estado ativo tem borda reforçada, peso de fonte e marca de seleção, além da cor. O foco usa `:focus-visible` com contorno explícito. Não há handlers `onclick`, bibliotecas adicionais ou submissão de preferência ao servidor.

O CLIENTE inclui o componente no cartão já existente. O ADMIN o inclui em um cartão novo. Não existem duas implementações de persistência ou de detecção do sistema.

### D.3. Funções do mecanismo de tema

O script autenticado de `base.html` mantém a variável local `preferencia`, que representa a escolha lógica, e um `MediaQueryList` obtido por `matchMedia('(prefers-color-scheme: dark)')`. O tema efetivo continua sendo `light` ou `dark` nos atributos HTML e na integração de gráficos.

| Função | Responsabilidade real |
| --- | --- |
| `normalizar(valor)` | Aceita `light` e `system`; `dark`, ausência e outros valores resultam em `dark`. Nenhum valor desconhecido é copiado diretamente para os atributos de tema. |
| `preferenciaSalva()` | Lê `localStorage.theme` em `try/catch` e normaliza o resultado. Se a leitura estiver bloqueada, mantém a preferência em memória da página. |
| `preferenciaPersistida(valor)` | Normaliza o valor lido e verifica, em `try/catch`, se a preferência que será aplicada pode ser restaurada do armazenamento. Ausência ou valor inválido podem restaurar o padrão escuro; leitura bloqueada retorna falso. |
| `resolver(valor)` | Converte somente a opção `system` na aparência atual do dispositivo; as opções explícitas permanecem claras ou escuras. Sem `matchMedia`, conserva escuro como fallback. |
| `refletir()` | Atualiza `aria-pressed` de todos os `button[data-theme-preference]`, comparando-os à escolha lógica, e não ao tema efetivo. |
| `aplicar(valor, persistida)` | Normaliza a preferência, resolve o tema, sincroniza os botões e aplica os atributos; reutiliza o tratamento preexistente de gráficos conforme mudança real da paleta e possibilidade de persistência. |
| `sistemaMudou()` | Reaplica a preferência somente se ela for `system`; claro e escuro explícitos ignoram mudanças do dispositivo. |

Na inicialização, `aplicar(preferenciaSalva(), false)` resolve o tema antes dos estilos. Um listener delegado de clique no documento usa `closest('button[data-theme-preference]')`, permitindo clicar no ícone ou no texto e alcançar o botão correspondente. O listener já está registrado enquanto o HTML e as bibliotecas estão carregando. Ele tenta salvar a opção lógica e chama `aplicar()` mesmo quando a gravação falha. O partial emite `nexo:tema-seletor` em um script com nonce imediatamente após os botões; o listener global chama `refletir()` antes das bibliotecas do rodapé, impedindo indicar Escuro por engano enquanto uma CDN lenta termina de carregar. `DOMContentLoaded` também sincroniza os estados acessíveis ao finalizar o DOM, sem duplicar a lógica.

### D.4. Persistência, abas e mudanças do sistema

A chave permanece `localStorage.theme`, compartilhada pela mesma origem do navegador. Não foi criado armazenamento por conta ou por perfil. Assim, ADMIN e CLIENTE que utilizam o mesmo navegador/origem continuam compartilhando a preferência, conforme a política anterior.

O listener `storage` considera alterações na chave `theme` e limpeza do armazenamento (`key === null`). Eventos de outras chaves são ignorados; quando `storageArea` é fornecida, eventos de `sessionStorage` são ignorados. A escolha recebida é normalizada e aplicada, inclusive quando `system` resolve para a mesma aparência já exibida: nesse caso o botão ativo muda sem recarga desnecessária.

O listener `pageshow`, quando `event.persisted` indica restauração do cache de navegação, lê uma fotografia da preferência salva e verifica a persistência em relação a esse mesmo valor. Isso evita decidir a recarga com base na preferência antiga que estava em memória no momento em que a página foi colocada no cache.

O `MediaQueryList` usa `addEventListener('change', sistemaMudou)`, com fallback a `addListener` para implementações anteriores. O valor `system` permanece gravado mesmo quando a aparência efetiva muda. O botão Sistema permanece selecionado após essas mudanças.

Com armazenamento bloqueado, as exceções de leitura e escrita são tratadas. A preferência em memória e os atributos da página continuam funcionando. A garantia nesse cenário é restrita à página atual: uma nova navegação pode recuperar a preferência anterior ou o padrão escuro, pois o navegador impediu a persistência.

### D.5. Plotly e páginas com gráficos

A implementação não redefine as paletas de `NEXO.definirPaleta`, `NEXO.colors`, `NEXO.abcColor`, `NEXO.spike`, `NEXO.plotlyLayout` ou os helpers de desenho. O comentário de integração foi atualizado para refletir a mudança de interface.

O procedimento existente foi preservado com uma condição adicional de mudança efetiva da aparência:

1. Sem `.js-plotly-plot`, a mudança é imediata, sem reload. Se `NEXO.definirPaleta` já existir, ela recebe o tema novo. Se a biblioteca ainda estiver carregando, os gráficos seguintes são inicializados a partir do atributo de tema atualizado.
2. Com gráficos já desenhados, mudança real de claro/escuro e preferência persistida, a página recarrega para redesenhar os gráficos com todas as cores e configurações originais do template. Isso também atende mudanças vindas de outra aba ou do sistema operacional.
3. Com gráficos e mesma aparência efetiva, não há recarga apenas por trocar a opção lógica entre uma escolha explícita e Sistema.
4. Se o armazenamento impedir recuperar a escolha, não há reload que a perderia. Os gráficos mantêm a paleta em que foram desenhados e recebem, quando necessário, fundo `#140f27` ou `#ffffff` e borda arredondada para conservar legibilidade. Ao voltar para essa paleta, o fundo de proteção é removido. Esse fallback já existia antes da alteração.

A limitação desse fallback deve ser mantida explícita: armazenamento bloqueado não força uma repintura completa da paleta interna de gráficos já desenhados; preserva sua legibilidade na página atual. O funcionamento normal com armazenamento disponível continua redesenhando a paleta integralmente.

### D.6. CSS e preservação das páginas públicas

As regras novas em `static/css/nexo.css` ficam restritas às classes `.theme-selector` e `.theme-option`. O grupo usa flex horizontal, `max-width: 100%`, espaçamento compacto e `min-width: 0` nos botões. A seleção usa os tokens existentes `--primary`, `--primary-soft`, `--text` e `--primary-2`; superfícies e bordas reutilizam os tokens do NEXO. A folha clara existente redefine esses tokens no tema claro; nenhum token ou regra de paleta precisou ser alterado para o seletor. Em `nexo-tema-claro.css`, o foco de `.sidebar-close` recebeu apenas `box-shadow: 0 0 0 6px #ffffff, var(--shadow-glass)`, preservando `outline-color: var(--roxo-forte)`. O halo mantém o foco visível tanto sobre o véu quanto sobre o avatar roxo, que voltou a aparecer no cabeçalho de 320 px.

Login, landing page e demais páginas públicas não recebem o mecanismo autenticado nem o seletor. Nenhum template público foi alterado. A política CSP e os hashes SRI de recursos externos foram preservados; listeners continuam em script com nonce, sem relaxamento de diretivas.

## E. Requisitos e dependências

Não há nova dependência de produção nem configuração adicional para usar o recurso. São reutilizados:

- Jinja/Flask para incluir o componente nas duas páginas existentes.
- Bootstrap 5.3.3 e Bootstrap Icons 1.11.3 já presentes no portal.
- Plotly.js 2.35.2 e os helpers `NEXO` já disponíveis em `base.html`.
- APIs nativas `localStorage`, `matchMedia`, `storage`, `pageshow` e eventos de DOM.
- Design tokens de `static/css/nexo.css` e a folha `static/css/nexo-tema-claro.css` já existente.

O contrato entre componente e script é o atributo `data-theme-preference` dos botões. O contrato com os estilos existentes são `data-theme` e `data-bs-theme` na raiz. O contrato com gráficos é a classe `.js-plotly-plot` e a função de paleta existente.

Não são necessários Supabase, tabelas, alterações de esquema, migrações, endpoints, credenciais, variáveis de ambiente ou mudanças na hospedagem. Nenhum recurso empresarial foi consultado ou modificado. Os testes usam a infraestrutura de isolamento já existente, com dados fictícios e SQLite temporário; migrações existentes eventualmente aplicadas a esses bancos descartáveis não representam alteração de banco externo.

## F. Testes e validação

### F.1. Ambiente de validação

A validação de navegador utiliza Playwright disponível no ambiente e Chromium em `/usr/bin/chromium`. Os fixtures existentes sobem a aplicação em loopback, usam SQLite temporário e bloqueiam a rede externa do teste. Cópias das versões exatas de Bootstrap, Bootstrap Icons, Plotly e Socket.IO foram preparadas em `/workspace/work/nexo-cdn`, com os hashes SHA-384/SRI conferidos antes de serem servidas pelos fixtures.

As fontes Inter e JetBrains Mono foram disponibilizadas somente para os processos de teste, via pacotes Fontsource 5.3.0 em `/workspace/work/nexo-fonts/fonts`, com cache em `/workspace/work/nexo-font-cache`. `fc-match` confirmou Inter e JetBrains Mono. Esses diretórios são auxiliares, não fazem parte do commit e não alteram a aplicação ou as configurações de hospedagem.

### F.2. Comandos e resultados reais

Foram aprovados **251 testes distintos** nas rodadas locais: 177 de regressão adicional e 74 de tema/Configurações (24 de interface e 50 de navegador). As repetições dirigidas abaixo não são somadas como novos testes. Não há falhas pendentes nos cenários exercitados.

| Rodada de tema/Configurações | Quantidade | Resultado real |
| --- | ---: | --- |
| Inicial: três módulos completos, antes de finalizar os ajustes | 73 | 1129.744 s; `FAILED (failures=4, errors=2)`. Os problemas e as correções estão descritos em F.4. |
| Interface + seleção com CDN retida + foco da gaveta + novo caso `pageshow` | 27 | Aprovados em 87,790 s, sem falhas ou testes pulados |
| Armazenamento bloqueado/Sistema + Sistema com CDN lenta + primeira pintura/legado após estabilizar o preparo | 3 | Aprovados em 80,496 s, sem falhas ou testes pulados |
| Cabeçalho nas cinco larguras, com prova de título artificial extenso | 1 | Aprovado em 63,211 s |
| Troca entre abas antes de desenhar gráficos, após estabilizar o estado inicial | 1 | Aprovado em 78,177 s |

A rodada inicial importou 73 testes; o caso de `pageshow` foi acrescentado durante a revisão e executado na rodada dirigida, totalizando 74 casos distintos desses três módulos. Os casos que falharam inicialmente foram corrigidos e aprovados nas execuções dirigidas; a matriz de Configurações concluiu os 19 testes sem falha.


O comando de regressão não navegador iniciado durante a implementação foi:

```bash
.venv/bin/python -B -m unittest   tests.test_configuracoes_conta   tests.test_navegacao_admin   tests.test_identidade_visual   tests.test_http_hardening_security -v
```

Resultado: 177 testes executados em 267,042 s; 173 aprovados, 4 pulados por ausência das variáveis de navegador/CDN nessa primeira rodada; nenhuma falha. Os quatro testes pulados foram executados em seguida com navegador e CDNs configurados:

```bash
XDG_DATA_HOME=/workspace/work/nexo-fonts XDG_CACHE_HOME=/workspace/work/nexo-font-cache NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium NEXO_TEST_CDN_DIR=/workspace/work/nexo-cdn .venv/bin/python -B -m unittest tests.test_identidade_visual.IdentidadeVisualBrowserTests tests.test_http_hardening_security.SubresourceIntegrityTests.test_local_cdn_copies_match_the_pinned_hashes_when_present -v
```

Resultado complementar: 4 testes aprovados em 52,948 s, sem falhas ou testes pulados. As duas rodadas cobrem 177 testes distintos aprovados.

O comando da rodada completa de tema/Configurações usou as seguintes variáveis e módulos:

```bash
XDG_DATA_HOME=/workspace/work/nexo-fonts XDG_CACHE_HOME=/workspace/work/nexo-font-cache NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium NEXO_TEST_CDN_DIR=/workspace/work/nexo-cdn .venv/bin/python -m unittest   tests.test_tema_interface   tests.test_tema_navegador   tests.test_configuracoes_navegador -v
```

As rodadas dirigidas utilizaram as mesmas variáveis de navegador, CDNs e fontes mostradas acima, com os alvos abaixo:

```bash
.venv/bin/python -m unittest tests.test_tema_interface tests.test_tema_navegador.TemaNavegadorTests.test_selecao_salva_aparece_antes_das_bibliotecas_do_rodape tests.test_tema_navegador.TemaNavegadorTests.test_foco_do_fechar_menu_passa_3_para_1_sobre_o_veu tests.test_tema_navegador.TemaNavegadorTests.test_pageshow_recarrega_graficos_com_preferencia_alterada_ou_removida -v
.venv/bin/python -m unittest tests.test_tema_navegador.TemaNavegadorTests.test_armazenamento_bloqueado_preserva_a_legibilidade_do_grafico_no_modo_sistema tests.test_tema_navegador.TemaNavegadorTests.test_sistema_troca_o_tema_antes_de_desenhar_os_graficos tests.test_tema_navegador.TemaNavegadorTests.test_sistema_na_primeira_pintura_e_preferencias_antigas -v
.venv/bin/python -m unittest tests.test_tema_navegador.TemaNavegadorTests.test_topbar_preserva_avatar_e_sino_nos_dois_temas_sem_botao_de_tema -v
.venv/bin/python -m unittest tests.test_tema_navegador.TemaNavegadorTests.test_trocar_antes_de_desenhar_os_graficos_nao_deixa_paleta_velha -v
```

Também foram executados diagnósticos isolados dos casos de armazenamento/Sistema, foco da gaveta e seleção com CDN retida para identificar as causas das falhas iniciais. Esses diagnósticos não acrescentam casos distintos à contagem. `git diff --check` foi executado após as alterações e aprovado.

### F.3. Cobertura da validação

A tabela relaciona os critérios de aceitação aos testes efetivamente preparados e executados. Os resultados consolidados das rodadas constam na seção F.2.

| Critério | Evidência automatizada |
| --- | --- |
| Ausência do controle antigo, sino e perfil preservados | `TemplatesTests.test_cabecalho_preserva_sino_e_perfil_sem_controle_de_tema`, HTML servido e `test_topbar_preserva_avatar_e_sino_nos_dois_temas_sem_botao_de_tema` |
| Seletor nas Configurações de ADMIN e CLIENTE | `HtmlServidoTests.test_com_sessao_script_com_nonce_folha_e_seletor_so_nas_configuracoes`, testes de ambos os perfis no navegador |
| Claro, Escuro, persistência após reload e navegação | `test_alternar_persiste_entre_paginas_e_apos_recarga` |
| Sistema, valor lógico persistido e reação a mudanças do dispositivo | `test_sistema_persiste_a_opcao_logica_e_acompanha_mudancas_do_so` |
| Compatibilidade com preferências antigas e valores inválidos | `test_sistema_na_primeira_pintura_e_preferencias_antigas`, `test_valor_invalido_em_localstorage_e_ignorado` |
| Sincronização entre abas, inclusive limpeza da preferência | `test_sincroniza_entre_abas_pelo_evento_storage` |
| Troca de modo com mesma aparência sem recarga de gráfico | `test_sistema_com_mesma_aparencia_nao_recarrega_graficos` |
| Restauração do cache com preferência alterada ou removida | `test_pageshow_recarrega_graficos_com_preferencia_alterada_ou_removida` |
| Paleta de dashboards ADMIN/CLIENTE e análise | `test_pagina_com_grafico_recarrega_e_troca_a_paleta_por_outra_aba`, `test_trocar_antes_de_desenhar_os_graficos_nao_deixa_paleta_velha`; verificação de cores efetivas dos eixos, `NEXO.spike` e `NEXO.abcColor` |
| Componentes de indicadores e Curva ABC legíveis | `test_contraste_das_amostras_principais`, testes estruturais de paleta e os cenários de análise com Plotly |
| Armazenamento bloqueado sem erro e escolha válida na página atual | `test_localstorage_bloqueado_nao_quebra_e_o_seletor_altera_a_pagina_atual`, `test_armazenamento_bloqueado_preserva_a_legibilidade_do_grafico_no_modo_sistema` |
| Ausência de erros JavaScript e violações CSP | `test_sem_violacao_de_csp_nem_erro_no_console_nos_tres_modos`, coletores do fixture e verificações de nonce/SRI |
| Primeira pintura e seleção antes das bibliotecas do rodapé | `test_tema_aplicado_antes_da_primeira_pintura_sem_clique`, `test_selecao_salva_aparece_antes_das_bibliotecas_do_rodape`, cenários com CDN retida |
| Responsividade em 320, 390, 768, 1024 e 1366 px | `ConfiguracoesNavegadorTests.test_sem_rolagem_horizontal_nos_dois_temas`, `test_seletor_tem_tres_botoes_horizontais_e_contraste_nos_dois_temas` |
| Teclado, estado acessível e foco visível | `test_teclado_altera_o_tema_e_exibe_foco_nas_configuracoes`, medições de pixels dos indicadores de foco; `aria-pressed` único após as escolhas |
| Páginas públicas preservadas | `test_login_continua_escuro_com_theme_light_guardado`, HTML público e testes de identidade visual de landing/login |
| Configurações funcionais sem disponibilidade das migrações de conta | `test_seletor_nao_envia_formularios_nem_depende_das_migracoes_de_configuracoes`; formulários indisponíveis permanecem desabilitados e o seletor continua ativo sem POST |
| Formulários, notificações, perfil e navegação preservados | Suíte de Configurações de conta, regressões de Configurações no navegador, navegação administrativa, sino e identidade visual |

Também foi realizada inspeção visual local de 12 combinações: ADMIN/CLIENTE × 1366/320/390 px × claro/escuro, com dados fictícios. Não foram observados cortes ou sobreposições do seletor; sino e avatar continuaram visíveis em 320 px. O contraste mínimo medido nas amostras do seletor e ajuda foi 6,52:1. A inspeção usou o mesmo fixture isolado, sem acessar o sistema hospedado.

### F.4. Problemas corrigidos e limites de validação

- Na revisão, o cálculo de persistência em `pageshow` foi corrigido para comparar o armazenamento ao snapshot salvo, em vez da preferência antiga da página em cache. O teste novo exige redesenho na paleta correta tanto após mudança quanto após remoção da chave.
- A seleção acessível inicialmente dependia de `DOMContentLoaded`. O evento com nonce emitido pelo partial antecipa `refletir()`, inclusive quando uma CDN do rodapé está retida.
- A preservação do avatar em 320 px colocou seu fundo roxo sob o foco do botão de fechar a gaveta. O teste existente mediu 1,16:1 no lado esquerdo; ocultar apenas o avatar na comparação de diagnóstico elevou a medida a 3,97:1, confirmando a causa. O halo claro resolveu o problema sem ocultar o avatar ou reduzir o critério: com o ajuste, as medidas foram direita 3,79:1, esquerda 10,87:1, cima 4,02:1 e baixo 5,26:1. O mesmo teste passou também em 390 e 768 px.
- Dois testes novos iniciavam o login em Sistema, alteravam o esquema já no dashboard e navegavam imediatamente. A mudança do dispositivo disparava a recarga correta do gráfico, concorrendo com o `goto` do próprio teste. A preparação dos ciclos de troca entre abas também foi ajustada para gravar o estado inicial na própria aba que será navegada, evitando um evento `storage` de preparação concorrente; a troca que constitui a asserção continua sendo feita na outra aba. O parâmetro opcional `esquema` de `_sessao` agora configura esse estado antes do login; as mudanças do dispositivo que constituem o comportamento testado continuam no corpo de cada teste.
- O teste de seleção com Bootstrap retido podia amostrar os botões durante o parsing, porque o navegador solicita scripts por carregamento especulativo antes de terminar o HTML anterior. Ele agora aguarda a seleção esperada enquanto Bootstrap continua retido e exige `document.readyState === 'loading'`. Se a seleção dependesse de `DOMContentLoaded`, o teste continuaria falhando por timeout.
- Ao estender o teste do cabeçalho até 1366 px, o título artificial original passou a caber. Ele foi ampliado para três vezes o texto de referência, garantindo que o teste continue provando a detecção de truncamento em todas as larguras; os títulos reais continuam sendo verificados sem corte.
- As expectativas do botão antigo foram substituídas por ações nas Configurações e, nos dashboards, por mudanças reais em outra aba. Não foram reduzidos os requisitos de contraste, estado acessível, CSP ou paleta para obter aprovação.

A suíte completa de todos os módulos do repositório não foi repetida localmente; foram executadas as suítes pertinentes descritas acima. Os checks integrais de CI serão disparados pelo PR e deverão ser avaliados antes do merge. A validação de navegador local utilizou Chromium e viewports simulados; não incluiu Firefox/WebKit ou dispositivos físicos. Não houve teste no ambiente empresarial, conexão com Supabase remoto nem deploy no Render, conforme o escopo autorizado. A homologação humana no ambiente hospedado permanece para o processo posterior de aprovação.

O fallback de gráficos com armazenamento bloqueado conserva legibilidade e a paleta em que os gráficos nasceram, como descrito em D.5; não representa repintura integral nessa condição excepcional. A persistência entre páginas depende da permissão do navegador para usar armazenamento.

## G. Guia para implementação futura no sistema empresarial

O procedimento a seguir é um guia de reprodução técnica. Ele não autoriza acesso ou alteração do sistema empresarial nesta implementação.

1. Criar uma branch a partir do estado aprovado do projeto empresarial e registrar o commit de referência. Ler suas instruções locais e comparar a implementação atual de tema, cabeçalho, Configurações, CSP, scripts de gráficos e testes com os pontos descritos neste documento.
2. Identificar a chave de preferência existente, os atributos HTML usados pelos estilos e os helpers de paleta. Confirmar que não há outro botão, script ou folha que imponha tema depois da primeira pintura. Fazer adaptações locais quando houver diferenças; não copiar arquivos inteiros do repositório de testes.
3. Remover somente o botão de tema da barra superior e os handlers que dependam dele. Manter sino, dropdown de notificações, dados do usuário, navegação, formulários e políticas de autenticação. Reavaliar as regras responsivas que reservavam espaço ao botão antes de transplantar qualquer cálculo de largura.
4. Introduzir um componente compartilhado equivalente ao seletor, com os três valores lógicos, ícones já disponíveis, botões nativos e `aria-pressed`. Incluí-lo no cartão Tema do CLIENTE e em Aparência do ADMIN, fora de formulários e condições de disponibilidade de outros módulos.
5. Ampliar a validação de valores da preferência para aceitar `system` e preservar `light`/`dark`. Manter escuro para ausência/valor inválido. Separar preferência lógica do tema efetivo e aplicar os atributos antes dos estilos, dentro do fluxo autenticado e usando o nonce já aprovado pelo projeto empresarial.
6. Registrar listeners de clique, `storage`, `pageshow` e mudança do `MediaQueryList`. Preservar a escolha em memória quando o storage estiver bloqueado; comparar a persistência ao valor que será restaurado. Não transformar `system` permanentemente em `light` ou `dark`.
7. Integrar com o mecanismo de gráficos existente. Se ele também gera cores nos templates, conservar o redesenho completo quando necessário; evitar reload sem gráfico e quando a aparência efetiva não muda. Conferir dashboards ADMIN/CLIENTE, análises, indicadores e Curva ABC, incluindo CDN lenta e armazenamento indisponível.
8. Adicionar somente as regras CSS do componente, usando os tokens de marca locais. Validar contraste, marca de seleção independente da cor, foco visível e teclado. Não substituir o design system, paletas oficiais, logos ou folhas completas.
9. Atualizar os testes para localizar o seletor nas Configurações. Executar os cenários da seção F, com navegador real, CSP aplicada, dados fictícios e armazenamento por origem. Exercitar 320, 390, 768, 1024 e 1366 px e verificar notificações/perfil após retirada do botão.
10. Revisar o diff para excluir alterações em banco, autenticação, permissões, contratos, empresas, notificações, e-mails, migrações, credenciais e hospedagem. Registrar comandos e resultados reais, abrir PR e submeter à homologação antes de integrar ou publicar.

Não clonar o repositório de homologação sobre o empresarial. O documento e o diff servem como referência para implementar o mesmo comportamento sobre a base de destino, respeitando diferenças existentes.

## H. Riscos e reversão

### H.1. Riscos e compatibilidade

- O armazenamento continua sendo por navegador e origem. Usuários diferentes no mesmo navegador compartilham a preferência, como anteriormente.
- `system` exige suporte a `matchMedia`; sem essa API, a aparência fica escura. Valores legados permanecem reconhecidos.
- Alterações reais da paleta em páginas com gráficos podem recarregar a página, preservando a estratégia anterior. Páginas sem gráficos e mudanças de modo com mesma aparência não precisam recarregar.
- Com storage bloqueado, a escolha vale na página atual e gráficos já desenhados conservam sua paleta com fundo de proteção. Não é garantida persistência entre páginas quando o navegador a impede.
- O componente depende do contrato `data-theme-preference` e dos tokens existentes; alterações futuras nesses pontos exigem atualizar o mecanismo e as verificações correspondentes.
- O halo de foco da gaveta deve ser preservado enquanto o avatar puder aparecer sob esse controle. A alteração de espaço do cabeçalho deve ser reavaliada quando forem acrescentados novos controles ou mudarem fontes/títulos. Os resultados de responsividade devem ser consultados na seção F.

### H.2. Reversão exclusiva desta implementação

A opção preferencial é reverter somente o commit de implementação indicado na seção A, por PR, depois de verificar eventuais alterações posteriores nos mesmos trechos. O documento pode permanecer como histórico com o status de reversão registrado.

Se houver conflitos com mudanças posteriores, reverter manualmente apenas:

1. A retirada do botão e seu vínculo JavaScript em `templates/base.html`, restaurando o mecanismo anterior a partir do commit de referência e seus ajustes de largura/visibilidade do avatar.
2. O include no cartão Tema do CLIENTE, restaurando a orientação anterior.
3. A seção Aparência e seu atalho no ADMIN.
4. O novo partial, se não houver outros consumidores, as regras `.theme-selector`/`.theme-option` e o halo acrescentado a `.sidebar-close:focus-visible` na folha clara, caso a regra antiga de ocultação do avatar também seja restaurada.
5. As expectativas dos testes relacionadas exclusivamente ao comportamento revertido.

Nenhuma reversão de migração ou banco é necessária. O valor `system` eventualmente salvo pode ser removido do navegador ou substituído por `light`/`dark`; a implementação anterior já usa escuro como fallback para valores não reconhecidos. Não limpar outras chaves nem preferências da conta.

Autenticação, permissões, contratos, empresas, análises, notificações, e-mails, documentos legais, auditoria, banco e infraestrutura devem permanecer intocados durante a reversão. Toda integração e publicação continua sujeita à validação humana do PR.
