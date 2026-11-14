# Visão Geral do cliente: painel de inteligência comercial

## A. Identificação

| Campo | Registro |
| --- | --- |
| Implementação | Reestruturação da Visão Geral do cliente (`/cliente/dashboard`) em painel vertical de inteligência comercial, com dados reais processados pelo ETL e pela devolutiva publicada |
| Data e horário de execução (registro inicial) | 2026-11-13 21:32:45 -0300 (UTC-0300), fuso `America/Sao_Paulo` |
| Conclusão da validação local | 2026-11-14 01:37:39 -0300 (UTC-0300), fuso `America/Sao_Paulo` |
| Repositório de origem | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Ambiente autorizado | Desenvolvimento e homologação (ambiente de testes), separado do sistema empresarial |
| Branch | `feature/dashboard-inteligencia-comercial-cliente` |
| Referência de `main` antes da alteração | `e1e3e73aa23aad5d588f74563296f4fe1a944417` |
| Commit da implementação | `1f2b8a778940b2293a2b9ba786d927838cdfaf42` (código, migração e testes; este documento é registrado no commit documental seguinte) |
| Status de validação | Validação local concluída: regressão completa, suíte de navegador e suítes PostgreSQL aprovadas, com uma única ressalva de ambiente (versão do pip, descrita em G.2 e reproduzida no `main`). CI do PR aprovada nos três jobs (`security-sqlite-browser`, `security-postgresql` e `security-sca-sast`) no commit `23e6d2f`, executada sobre a combinação com o `main` atual. Homologação humana pendente |
| Integração e publicação | Pull Request em rascunho para homologação, a partir da branch acima. Sem merge e sem deploy nesta entrega. A migração `5a9c3e7d1b42` **não** foi aplicada no Supabase |
| PR #47 (cabeçalho) | Aberto quando verificado durante a implementação (`fix/topbar-fresta-superior-responsividade`); depois foi integrado ao `main` pelo responsável do repositório (2026-11-13 23:46 -0300), fora desta entrega. Esta implementação não o modificou nem o integrou e não altera nenhum arquivo dele (`base.html`, `nexo.css`, `nexo-tema-claro.css` e os testes de cabeçalho e tema). O PR desta entrega não tem conflito com o `main` atual, e a CI dele roda sobre essa combinação |

A pasta `POSSIVEIS ATUALIZAÇÕES EMPRESA` já existia e foi reutilizada. Este documento registra pontos de integração e reprodução; não contém cópias integrais de código. Todos os dados usados em testes e capturas são sintéticos.

## B. Objetivo e comportamento resultante

### B.1. Situação anterior

A Visão Geral (`/cliente/dashboard`) apresentava três cartões monetários (faturamento, total comprado e Indicador de Pressão de Estoque), a síntese executiva em semáforos (`insights.gerar_semaforos`), três cartões de produto, o gráfico Compras x Vendas, o indicador numérico de pressão de estoque, o cartão do relatório estratégico, o Pareto dos 10 primeiros produtos, o histórico comparativo e as tabelas de histórico e de análises em andamento.

Limitações técnicas encontradas na auditoria:

1. O ETL calculava a Curva ABC sobre o universo completo (`_classificar_curva_abc`), mas persistia apenas os 20 primeiros produtos (`TOP_N_CURVA_ABC = 20`) e descartava o resumo por classe (`kpis["curva_abc"]["resumo"]`). Não era possível calcular a participação das classes nem consultar os demais produtos sem distorção.
2. As quantidades compradas por produto não eram persistidas; só o maior saldo estimado (`produto_maior_saldo_parado_*`).
3. O histórico comparativo misturava análises mensais e quinzenais, repetia rótulos `MM/AAAA` para duas quinzenas do mesmo mês e não tratava períodos sobrepostos nem lacunas.
4. A consulta da Visão Geral filtrava apenas `status_analise = 'CONCLUIDO'`, sem exigir `relatorio_analise.publicado`. Em dado legado ou alteração manual (CONCLUIDO sem publicação), o cartão do relatório podia exibir o título e o início da conclusão do rascunho, pois `RelatorioAnalise.publicada` recorre ao rascunho quando não há cópia congelada.
5. O KPI `produto_maior_faturamento_*` do ETL mostra o segundo colocado quando o primeiro coincide com o produto mais vendido (regra do motor para evitar redundância visual).

### B.2. Resultado implementado

A Visão Geral passou a ser um painel vertical com dez seções, na ordem solicitada, mais a navegação por âncoras (sem novas abas ou páginas):

| # | Seção | Âncora | Conteúdo |
| --- | --- | --- | --- |
| 1 | Indicadores principais | `#indicadores` | Seis cartões: faturamento, total comprado, diferença compras − vendas, produto de maior faturamento, produto mais vendido e maior diferença em unidades |
| 2 | Resumo Executivo | `#resumo-executivo` | Resumo publicado pela equipe NEXO (com o selo de IA quando aplicável) e destaques calculados por regra |
| 3 | Insights e interpretações gerenciais | `#insights` | Cartões “o que aconteceu / por que importa / o que fazer / objetivo” |
| 4 | Curva ABC e análise dos produtos | `#curva-abc` | Pareto, distribuição por classe (rosca), cartões A/B/C e consulta paginada |
| 5 | Movimentação dos produtos | `#movimentacao` | Comprado x vendido por produto, interpretação e recomendação, com ressalvas |
| 6 | Compras x Vendas | `#compras-vendas` | Gráfico de barras e cartão de interpretação |
| 7 | Evolução do faturamento | `#evolucao-faturamento` | Barras por período comparável, média, maior, menor e tendência |
| 8 | Evolução de compras e vendas | `#evolucao-compras-vendas` | Duas séries (vendas em azul, compras em âmbar) com lacunas visíveis |
| 9 | Ações recomendadas para o próximo ciclo | `#recomendacoes` | Recomendações priorizadas e fundamentadas |
| 10 | Histórico e devolutiva estratégica | `#historico-devolutiva` | Relatório estratégico, histórico recente com publicação e identificação |

Os blocos preservados sem alteração de regra: saudação, barra de origem dos dados, aviso de renovação, avisos de suspensão, cartão da empresa, estado “Sua primeira análise está em preparação.”, cartão para análise publicada sem indicador, “Análises em andamento” e “Contato NEXO”.

## C. Arquivos modificados

Todos os caminhos são relativos à raiz do repositório autorizado.

| Caminho | Tipo de alteração | Função e justificativa |
| --- | --- | --- |
| `inteligencia_comercial.py` | Novo módulo (regras puras) | Série histórica comparável, comparação entre períodos (total e média diária), estatísticas, distribuição ABC (universo completo ou legado exato), cartões por classe, interpretação da movimentação, variação por produto, insights, recomendações, destaques do resumo executivo e formatadores pt-BR. Sem banco nem Flask; aritmética em `Decimal`. Concentra a regra fora do HTML. |
| `painel_cliente.py` | Novo módulo (montagem) | Reúne, com consultas limitadas, os dados da análise publicada e autorizada e aplica as regras; produz o contexto do template e o JSON dos gráficos (`dashboardData`), preservando as chaves anteriores. |
| `detalhamento_produtos.py` | Novo módulo (acesso a dados) | Disponibilidade do esquema no padrão do projeto (`esquema_*_disponivel`), detalhamento vigente (mesma versão de processamento dos KPIs), autorização das compras por produto pelo período do relatório de compras, consultas limitadas (topo do ranking, destaques por classe, movimentação, linhas com compras acima das vendas, contagens) e consulta paginada com filtros e busca pelo nome normalizado. |
| `etl_processor.py` | Ampliação controlada | Operação detalhada: leitura da unidade de medida e do período de cada arquivo, `_ranking_abc` (fonte única da classificação, extraída de `_classificar_curva_abc` sem mudança de saída), `_montar_detalhamento` (com totais por situação sobre todos os comprados, unidade ausente em todas ou em parte das linhas não comparada e linhas de compra que não são produto excluídas), `calcular_com_detalhamento_local`, `calcular_kpis_detalhados_em_memoria`, persistência em dois SAVEPOINTs (apagar o anterior, gravar o novo com a versão do processamento) e volta ao cálculo original quando a execução detalhada esgota saída, tempo ou recursos do worker. O caminho `calculate` permanece idêntico. |
| `etl_worker.py` | Nova operação | `calculate_detailed` no mesmo processo isolado (limites de memória, CPU, arquivo, saída e bloqueio de rede inalterados). |
| `etl_runtime.py` | Nova função e validação | `run_calculation_detailed` e `validar_detalhamento` (tipos, faixas, unicidade e invariantes, inclusive a soma dos totais por situação); `run_calculation` passa a usar o mesmo validador extraído (`_resultado_calculo`), sem mudança de comportamento. |
| `models.py` | Dois modelos novos | `IndicadorComplementarAnalise` (inclui `versao_processamento` e os totais por situação) e `ProdutoDesempenhoAnalise` (inclui `produto_busca`, preenchido na gravação). Sem relationship em `Analise`; FKs com `ON DELETE CASCADE`. |
| `migrations/versions/5a9c3e7d1b42_detalhamento_produtos_visao_geral.py` | Nova migração aditiva | Cria as duas tabelas com restrições de integridade, liga RLS e as políticas da Data API no PostgreSQL; o downgrade recusa apagar dados. |
| `blueprints/cliente.py` | Alteração da Visão Geral e rota nova | Exige devolutiva publicada na consulta da Visão Geral; delega a montagem a `painel_cliente` com a situação contratual; cria `GET /cliente/analise/<id>/produtos` (JSON, mesmas guardas da página da análise, limite por usuário, `no-store`, `nosniff`, compras por produto só com o período de compras coberto); remove `_historico_temporal`, substituída pela série comparável. |
| `templates/cliente/dashboard.html` | Reestruturação vertical | Dez seções em ordem, navegação por âncoras, estados vazios, legados e parciais; JavaScript inline com nonce (cores só por `NEXO.colors`), consulta paginada com rótulos de coluna no celular e mensagens de erro distintas. Preserva `#chartCliente`, `#chartAbcCliente`, `const dashboardData = …;` em uma linha, avisos, cartão da empresa, análises em andamento e contato. |
| `templates/cliente/_painel.html` | Novo arquivo de macros | Cabeçalho de seção, variação, cartão de insight (estrutura `semaforo-card`), cartão de classe, cartão de recomendação e linhas das consultas. |
| `static/css/nexo-painel-cliente.css` | Nova folha de estilos | Classes próprias do painel com tokens do tema; ajustes do tema claro sob `html[data-theme="light"]`; incluída pelo bloco `extra_css`, sem alterar `nexo.css`, `nexo-tema-claro.css` ou `base.html`. |
| `README.md` | Atualização pontual | Governança de dados e matriz de decisões passam a citar os agregados por produto persistidos. |
| `.github/workflows/nexo-security-ci.yml` | Passo novo na CI | Executa `tests.postgresql_detalhamento_produtos` no job PostgreSQL, como as regras de migração do projeto exigem. |
| `tests/test_inteligencia_comercial_regras.py` | Novo | Regras puras. |
| `tests/test_etl_detalhamento_produtos.py` | Novo | Equivalência financeira, unidades, movimentação, escala, tetos, contrato do worker, persistência, reprocessamento e migração (SQLite). |
| `tests/test_painel_cliente_visao_geral.py` | Novo | Rota, endpoint, segurança, cobertura contratual, legado x completo, histórico. |
| `tests/test_painel_navegador.py` | Novo | Navegador: oito larguras, três temas, consulta paginada, celular, erros e capturas. |
| `tests/postgresql_detalhamento_produtos.py` | Novo | PostgreSQL privado: migração com dados existentes, RLS e políticas, Numeric, cascata, downgrade, portal sem as tabelas. |
| `tests/test_leads_avaliacao.py`, `tests/test_leads_postgresql.py` | Atualização do head | O head passou a ser `5a9c3e7d1b42`; a revisão dos leads continua verificada como parte da cadeia aplicada. |
| `tests/test_backup_restore.py`, `tests/test_contratos_postgresql.py` | Atualização de inventário | 34 tabelas no ensaio de backup; as duas tabelas novas no conjunto de tabelas posteriores. |

Nenhum arquivo de autenticação, sessão, permissões administrativas, landing page, NexoBot, notificações, sidebar, cabeçalho, seletor de temas, `base.html`, `nexo.css`, `nexo-tema-claro.css`, PDF, devolutiva por IA ou configuração do Render foi alterado. As terminações de linha CRLF de `blueprints/cliente.py`, `etl_processor.py` e `models.py` foram preservadas.

## D. Arquitetura

### D.1. Contrato de dados por seção

| Seção | Fonte | Classificação |
| --- | --- | --- |
| Faturamento, total comprado, diferença | `indicador_analise` (`faturamento_total`, `total_comprado`, `saldo_estimado_compras_vendas`) | Já disponível |
| Variação percentual de faturamento e compras | Análise anterior da série comparável | Derivável dos dados persistidos |
| Produto com maior faturamento (nome, valor, participação, quantidade) | Posição 1 do ranking (`produto_curva_abc` ou `produto_desempenho_analise`) | Já disponível |
| Produto mais vendido (nome, quantidade) | `indicador_analise.produto_mais_vendido_*` | Já disponível |
| Participação/posição do mais vendido no faturamento | Ranking (topo ou detalhamento por chave) | Derivável / ampliação controlada |
| Maior diferença em unidades (comprado, vendido, diferença) | `produto_desempenho_analise` | Ampliação controlada; análises anteriores: só a estimativa `saldo_estimado_parado`, rotulada como tal |
| Resumo executivo | `relatorio_analise` (cópia publicada) + regras | Já disponível + derivável |
| Insights e recomendações | Indicadores, distribuição, movimentação, série | Derivável / ampliação controlada |
| Pareto (10 primeiros) | Ranking | Já disponível |
| Distribuição A/B/C sobre todos os produtos | `indicador_complementar_analise` | Ampliação controlada; análises anteriores com menos de 20 produtos: derivável exato; com 20: indisponível |
| Consulta de todos os produtos | `produto_desempenho_analise` (paginada) | Ampliação controlada; análises anteriores: só o top-20 armazenado |
| Movimentação por produto | `produto_desempenho_analise` + totais por situação | Ampliação controlada; compras em nível de nota fiscal: indisponível com as fontes atuais |
| Compras x Vendas | `indicador_analise` | Já disponível |
| Evolução do faturamento e de compras e vendas | Análises publicadas e autorizadas | Derivável |
| Histórico e devolutiva | `analise` + `relatorio_analise` publicado | Já disponível |

### D.2. Fluxo

1. **ETL (consultor):** `processar_arquivos_analise` verifica, num SAVEPOINT, se as tabelas do detalhamento existem. Sem elas, executa exatamente o caminho anterior (`calculate`). Com elas, executa `calculate_detailed` no mesmo worker isolado: o `ResultadoETL` é o mesmo da operação `calculate` e, à parte, segue o detalhamento compacto (linhas posicionais), ajustado ao orçamento de saída (`max_output_bytes` menos o resultado e uma reserva de 256 KiB) e ao teto de 5.000 linhas.
2. **Validação no processo web:** `validar_detalhamento` confere cada campo; o detalhamento inválido é descartado e registrado, sem bloquear os KPIs. Se a execução detalhada esgotar a saída (`output`), o tempo (`timeout`) ou os recursos do worker (`worker`), o cálculo original é refeito sem detalhamento; erros do próprio arquivo falhariam igual sem detalhamento e encerram o processamento como antes.
3. **Persistência:** KPIs e top-20 como antes. O detalhamento usa dois SAVEPOINTs: o primeiro apaga o de processamentos anteriores; o segundo grava o novo, marcado com a `versao_processamento` do indicador gerado na mesma execução. Falha de banco na gravação deixa a análise **sem** detalhamento (nunca devolve o antigo) e preserva os KPIs. Um erro inesperado que não é de banco falha fechado, sem gravação parcial, como no restante do ETL.
4. **Leitura:** `complemento_vigente` só aceita o detalhamento da mesma versão de processamento dos KPIs atuais; um detalhamento de outra versão é ignorado e a análise aparece como sem detalhamento.
5. **Visão Geral:** o blueprint autoriza (empresa da sessão, `CONCLUIDO` + publicado, política contratual) e chama `painel_cliente.montar_painel` com a situação contratual, que faz consultas limitadas e aplica `inteligencia_comercial`. No regime contratual, as compras por produto só aparecem se o período do relatório de compras, quando declarado no cabeçalho, estiver coberto; sem período no cabeçalho, vale o período declarado da análise, já autorizado.
6. **Template:** apresenta o contexto; os gráficos consomem `dashboardData`; as consultas paginadas usam o endpoint JSON.

### D.3. Modelos (revisão 5a9c3e7d1b42)

`indicador_complementar_analise` (1:1 com `analise`): `versao_metodologia`, `versao_processamento`, `abc_total_produtos`, `abc_faturamento_total`, `abc_produtos_{a,b,c}`, `abc_faturamento_{a,b,c}`, `produtos_vendas`, `produtos_compras`, `compras_por_produto`, `unidade_vendas_informada`, `unidade_compras_informada`, `periodo_vendas_inicio/fim`, `periodo_compras_inicio/fim`, `produtos_registrados`, `ranking_registrado`, `movimentacao_total`, `movimentacao_registrada`, `movimentacao_comparaveis`, `movimentacao_sem_venda`, `movimentacao_unidade_divergente`, `movimentacao_unidade_ambigua`, `movimentacao_quantidade_invalida`, `registro_limitado`, `data_geracao`. Restrições: soma das classes igual ao universo; prefixos registrados dentro dos totais; totais por situação todos nulos ou todos preenchidos, não negativos e somando `movimentacao_total`; `uq_indicador_complementar_analise`.

`produto_desempenho_analise`: `produto_chave` (16 hexadecimais, BLAKE2b da chave de agrupamento do ETL), `produto_nome`, `produto_busca` (nome normalizado para a busca, preenchido na gravação), `posicao_ranking`, `classe_abc`, `faturamento`, `quantidade_vendida`, `percentual_individual`, `percentual_acumulado`, `quantidade_comprada`, `unidade_venda`, `unidade_compra`, `situacao_movimentacao`, `diferenca_quantidade`, `posicao_movimentacao`, `data_geracao`. Restrições: classe e posição presentes juntas; diferença só para `COMPARAVEL`; unicidade por análise de chave, posição no ranking e posição na movimentação (índices que também atendem a FK).

As duas FKs usam `ON DELETE CASCADE`. `Analise` não ganhou relationship: excluir a análise remove o detalhamento no banco, sem carregar milhares de linhas no ORM, e nenhuma consulta existente toca as tabelas antes da migração.

### D.4. Endpoint de consulta

`GET /cliente/analise/<id>/produtos?visao=ranking|movimentacao&pagina=N&classe=A|B|C&filtro=…&busca=…`

- Guardas idênticas às da página da análise: empresa da sessão, `CONCLUIDO`, devolutiva publicada (404) e `pode_consultar_analise` (403).
- Visão de movimentação: além das guardas, no regime contratual exige que o período do relatório de compras, quando declarado no cabeçalho, esteja coberto; senão responde “indisponível”, sem itens. Sem período no cabeçalho, vale o período declarado da análise.
- 25 itens por página; página fora da faixa é ajustada; parâmetros inválidos caem no padrão; busca limitada a 80 caracteres e comparada pelo nome normalizado (sem acentos, maiúsculas ou pontuação): `%`, `_` e `\` nunca funcionam como curinga.
- Limite de 120 requisições por minuto por usuário; `Cache-Control: no-store`; `X-Content-Type-Options: nosniff`; nenhum efeito colateral.
- Devolve só campos de exibição já formatados em pt-BR. O navegador monta as linhas com `textContent` e aplica os rótulos de coluna usados no modo cartão.

### D.5. Frontend

- Folha própria `static/css/nexo-painel-cliente.css` (bloco `extra_css`), tokens do tema e regras do claro sob `html[data-theme="light"]`.
- JavaScript inline com `nonce`, sem manipuladores inline e sem cores literais (exigência de `tests/test_tema_interface.py`).
- Reuso: `NEXO.plot`, `NEXO.plotParetoAbc` (Pareto horizontal com linha de % acumulado e referência de 80%), `NEXO.descrever` (alternativa textual), `NEXO.ajustarLayout` (tabelas em cartões no celular), `semaforo-card`, `kpi-tile`, `nexo-card`, `badge_abc`, `nota_pressao` e `nota_abc`.
- Consulta paginada: página, classe, filtro e busca só passam a valer (com o botão marcado) quando a resposta chega; uma ação feita antes da resposta da anterior parte do pedido pendente, de modo que duas ações seguidas se somam. Uma falha não pula página nem deixa a seleção em desacordo com a tabela. Mensagens distintas para limite de consultas (429), análise indisponível (403/404) e sessão expirada (redirecionamento ou página de login/aceite).
- A troca de tema continua recarregando a página com gráficos (mecanismo existente do `base.html`); nenhum controle novo de tema.

## E. Funcionalidades

### E.1. Indicadores principais (`#indicadores`)

Seis cartões, com o período analisado no subtítulo da seção:

| Cartão | Conteúdo | Situações tratadas |
| --- | --- | --- |
| Faturamento do período | Valor; variação em relação ao período anterior comparável (seta, cor e texto); período | Sem período anterior comparável; período anterior sem valor (sem base percentual); durações diferentes declaradas no cartão; valor não informado exibido como “—” |
| Total comprado | Valor; variação em tom neutro (comprar mais não é bom nem ruim por si) | Iguais às do faturamento |
| Diferença entre compras e vendas | Total comprado − faturamento; selo “Pressão de estoque”, “Equilíbrio” ou “Giro saudável” pelos limiares de ±5% do faturamento; percentual do faturamento | Faturamento zero: vale o sinal da diferença; sem os dois totais: “—” e “Não calculado”. Texto fixo: não é lucro, prejuízo nem estoque físico |
| Produto com maior faturamento | Nome, faturamento, participação e quantidade vendida | Sinaliza quando também é o mais vendido; sem produto com faturamento positivo |
| Produto mais vendido (quantidade) | Nome, quantidade, posição e participação no faturamento | Coincidência com o líder declarada nos dois cartões |
| Maior diferença: unidades compradas − vendidas | Produto, comprado, vendido e diferença, com a unidade quando informada | Nenhuma diferença positiva; compras sem produto (nível de nota fiscal); compras fora da cobertura contratada; análise sem detalhamento (estimativa legada rotulada como tal) |

### E.2. Resumo Executivo (`#resumo-executivo`)

Exibe primeiro o resumo executivo publicado pela equipe NEXO (cópia publicada, com o selo existente quando a devolutiva foi gerada com apoio de IA) e, em seguida, “Destaques calculados dos indicadores”: frases montadas por regra a partir do faturamento, das compras, da diferença, do líder, do mais vendido, da Classe A, do principal ponto de atenção, da principal oportunidade e da primeira recomendação. Nenhum serviço externo é chamado ao abrir a página; o texto muda quando os dados mudam.

### E.3. Insights e interpretações gerenciais (`#insights`)

Cartões no padrão visual dos semáforos existentes, com o nível também em texto (Crítico, Atenção, Oportunidade, Informativo) e quatro campos: o que aconteceu, por que isso importa, o que fazer e qual é o objetivo. Cada cartão só existe se a sua condição verificável for satisfeita (ver F). Ordem: crítico, atenção, oportunidade, informativo.

### E.4. Curva ABC e análise dos produtos (`#curva-abc`)

- **Pareto** horizontal dos 10 primeiros produtos, com linha de percentual acumulado e referência de 80% (no celular, o acumulado aparece junto ao nome do produto).
- **Distribuição por classe** em rosca, calculada sobre todos os produtos com venda, com resumo textual (produtos, faturamento e participação de cada classe; os percentuais exibidos somam 100,0%).
- **Cartões A, B e C** com leitura da classe, primeiros produtos e recomendação específica; classe vazia é declarada.
- **Consulta completa** paginada (25 por página) com filtro por classe e busca pelo nome (sem diferenciar acentos, maiúsculas ou pontuação).
- Tabela textual equivalente aos gráficos para leitores de tela.

Escala: as consultas são limitadas e paginadas; 10, 100, 300 ou milhares de produtos usam o mesmo caminho. Empates recebem posições únicas e determinísticas; produtos com faturamento nulo ou não positivo ficam fora da Curva ABC.

### E.5. Movimentação dos produtos (`#movimentacao`)

Tabela por produto com comprado, vendido, diferença, interpretação e recomendação; cada quantidade aparece com a unidade do seu relatório. Filtros: compras acima das vendas (produtos que venderam menos de 90% do volume comprado, critério explicado na própria seção e igual ao das recomendações), todos comparáveis, sem venda correspondente, unidade diferente ou ausente, quantidade inválida e todos os comprados; busca pelo nome. A diferença só é calculada quando o produto consta dos dois relatórios, com unidades compatíveis e quantidades válidas; nos demais casos a linha mostra o motivo, sem número artificial. Ressalvas exibidas quando aplicáveis: unidade não informada, períodos dos relatórios diferentes, produtos sem venda correspondente, unidades divergentes/ausentes, quantidades inválidas e registro parcial. Nenhum texto afirma estoque físico.

### E.6. Compras x Vendas (`#compras-vendas`)

Gráfico de barras (total comprado e total vendido) e cartão de interpretação com os dois valores, a diferença com sinal e a leitura do período, incluindo quando a diferença está dentro da faixa de equilíbrio e quando os relatórios declaram períodos diferentes. Sem um dos totais, o gráfico não é desenhado com valor presumido e o texto informa que a diferença não foi calculada.

### E.7. Evolução do faturamento (`#evolucao-faturamento`)

Barras por período comparável, cada uma com a largura do próprio período (um período sem análise publicada aparece como espaço vazio), linha da média e marca “Atual” no período desta análise. Indicadores: maior, menor e média dos totais, e tendência (crescente, decrescente, oscilante ou estável) com a variação acumulada, calculadas pela média diária quando as durações diferem (o cartão indica). Só entram períodos válidos e comparáveis (ver F).

### E.8. Evolução de compras e vendas (`#evolucao-compras-vendas`)

Duas séries nos mesmos períodos comparáveis: vendas em azul (linha contínua) e compras em âmbar (linha pontilhada, marcador em losango). Lacunas interrompem as linhas. Texto com quantos períodos tiveram compras acima das vendas e a comparação do período atual com o anterior.

### E.9. Ações recomendadas para o próximo ciclo (`#recomendacoes`)

Até cinco recomendações ordenadas por prioridade (Alta, Média, Baixa), cada uma com produto ou grupo, situação identificada, justificativa, ação sugerida e objetivo comercial. Só entram recomendações com dado de suporte, sem duplicidade de alvo e sem ações opostas para o mesmo produto. Nota fixa: orientam o planejamento e não garantem resultado financeiro.

### E.10. Histórico e devolutiva estratégica (`#historico-devolutiva`)

Cartão do relatório estratégico publicado (título e início da conclusão da cópia publicada) e histórico recente das análises publicadas e liberadas pela política contratual: período, tipo, status, data de publicação, identificação e ação “Abrir”.

### E.11. Responsividade, temas e acessibilidade

- Larguras validadas: 320, 360, 390, 430, 768, 1024, 1366 e 1920 px, sem rolagem horizontal da página.
- No celular, as tabelas viram cartões com o nome de cada coluna, inclusive nas páginas carregadas pela consulta.
- Temas claro, escuro e sistema pelo mecanismo existente; nenhum controle de tema novo.
- Cor nunca é a única pista: nível em texto nos insights, selo textual na diferença, marca “Atual” no gráfico, filtro ativo com borda e marca de seleção.
- Consulta paginada com mensagens distintas para limite de consultas, análise indisponível e sessão expirada; página, filtro marcado e busca só mudam quando a resposta chega (uma falha não deixa a tabela e a seleção em desacordo).

## F. Regras de cálculo e confiabilidade

| Regra | Definição |
| --- | --- |
| Diferença compras − vendas | `saldo_estimado_compras_vendas` persistido (= total comprado − faturamento); na falta dele, a conta com os dois valores, se ambos existirem |
| Razão de pressão e selo do indicador | diferença ÷ faturamento, arredondada como é exibida (percentual com uma casa: 5,04% conta como 5,0%); > 5% “Pressão de estoque” (> 15% crítico nos insights); < −5% “Giro saudável”; de −5% a 5% “Equilíbrio”; sem faturamento, vale o sinal da diferença. Os valores de 5% e 15% vêm de `insights.py`; a faixa de equilíbrio e a regra do sinal são próprias da Visão Geral (ver H.8) |
| Variação exibida | (atual − anterior) ÷ \|anterior\| × 100, uma casa, meio para cima; anterior zero: sem base percentual |
| Durações diferentes | Os cartões de faturamento e de total comprado mostram a variação dos totais e declaram as durações (ex.: 31 e 28 dias). Insights, destaques, variação por produto, tendência e variação acumulada da evolução usam a **média diária** (total ÷ dias do período efetivo), para o calendário não aparecer como alta ou queda; maior, menor e média continuam sendo os totais |
| Participação de classe | faturamento da classe ÷ faturamento elegível total (universo completo); exibição por maiores restos para somar 100,0% |
| Legado | menos de 20 linhas armazenadas = ranking completo (o limite sempre foi 20); 20 linhas = participação indisponível |
| Concentração | líder com participação ≥ 30% |
| Saída relativa | vendidas ÷ compradas: < 0,5 baixa; < 0,9 compras acima; ≤ 1,1 alinhada; > 1,1 vendas acima |
| Comparável | situação `COMPARAVEL`: presente nos dois relatórios, unidades compatíveis, quantidades válidas (comprada > 0, vendida ≥ 0) |
| Compras acima das vendas | um único critério em toda a página: produto comparável que vendeu menos de 90% do volume comprado (filtro padrão da tabela, recomendações e insights); diferença positiva menor aparece como compra alinhada. O cartão “maior diferença” mostra a maior diferença positiva entre os comparáveis |
| Unidade | cabeçalho exato (`un`, `und`, `unid`, `unidade(s)`, `um`, `unidade de medida`…), fora das colunas mapeadas, aceito se ≥ 80% dos valores forem unidades reconhecidas; sinônimos normalizados (`LT`→`L`, `Caixa`→`CX`); fator mantido (`CX12`). Se um relatório tem a coluna e o produto está sem unidade nele (em todas ou em parte das linhas), ou com mais de uma unidade, a linha não é comparada. Cada quantidade é exibida com a unidade do seu próprio relatório e a diferença só com a unidade comum aos dois; sem unidade informada, só o número |
| Linhas que não são produto | linhas de compra sem produto ou com descrição de frete, taxa, juros, desconto e afins (a mesma lista que o relatório de vendas descarta) ficam fora do detalhamento; os KPIs não mudam |
| Compras acima das vendas por produto | Conferida na linha do próprio produto (não só nas primeiras linhas da seção): destaques da Classe A, líder e produtos em crescimento com compras acima das vendas não recebem “garantir abastecimento/reposição”; a recomendação da Classe A diz quais ficam de fora e por quê. Com relatórios de períodos diferentes, essas ações ficam neutras (“acompanhar/avaliar pelas vendas observadas”) |
| Variação por produto | mesma série comparável; ≥ 20% e impacto ≥ 2% do faturamento atual; produto ausente no período anterior não entra |
| Classe B | participação ≥ 5% com produtos na classe |
| Classe C reduzida | participação ≤ 10% e mix ≥ 30% |
| Série comparável | mesmo tipo; duração 28–31 dias (mensal) ou 13–16 (quinzenal) pelo período efetivo; sobreposição resolvida por prioridade (a atual; depois a concluída mais recente): um período só sai se sobrepuser outro que permaneceu; lacuna > 3 dias marcada; até 24 períodos, sempre com a atual e a anterior a ela; períodos omitidos identificados como mais antigos ou mais recentes |
| Teto | 5.000 linhas por análise e orçamento de saída; prefixos contínuos registrados (`ranking_registrado`, `movimentacao_registrada`) e `registro_limitado` declarados; totais por situação calculados sobre todos os comprados |
| Versão do detalhamento | o detalhamento exibido é sempre o da mesma `versao_processamento` dos KPIs atuais |
| Estimativa legada | `saldo_estimado_parado` (sem conferência de correspondência nem de unidade) só aparece em análise sem detalhamento e rotulada como estimativa |
| Busca | nome normalizado pela mesma regra do ETL (sem acentos, maiúsculas ou pontuação), igual nas análises com e sem detalhamento |
| Valores ausentes | total não informado não vira zero nem equilíbrio: o indicador exibe “—”, o selo da diferença “Não calculado”, e o gráfico Compras x Vendas não é desenhado com valor presumido |

Valores monetários e percentuais são `Decimal` do banco até a serialização final para o gráfico. Nenhum texto afirma lucro, margem, prejuízo, rentabilidade ou estoque físico. Cada insight e recomendação guarda `rastreio` (indicador, valor, critério, produto), usado nos testes e não exibido ao cliente.

## G. Testes e validação

### G.1. Ambiente de validação

| Item | Versão ou configuração |
| --- | --- |
| Sistema | Linux 6.18 (contêiner de desenvolvimento isolado) |
| Python | 3.12.3 (Flask 3.1.3, SQLAlchemy 2.1.8, pandas 3.0.3) |
| Banco das suítes comuns | SQLite com as migrações reais do projeto |
| PostgreSQL | 16.15 em cluster privado descartável, criado por usuário sem privilégio de administrador e removido ao final |
| Navegador | Chrome for Testing 153.0.8010.12 via Playwright 1.56.0, cópias locais das bibliotecas de CDN conferidas pelo SRI fixado |
| Dados | Exclusivamente sintéticos (empresas, produtos e valores fictícios) |

Nenhum teste acessou o Supabase hospedado, o Render ou o sistema empresarial.

### G.2. Comandos e resultados reais

| Execução | Comando | Resultado |
| --- | --- | --- |
| Regressão completa (sem navegador e sem PostgreSQL) | `python -B -m unittest discover -s tests -t .` | 1.706 testes em 759 s: 1.562 aprovados, 143 pulados (testes de navegador e de PostgreSQL, executados nas linhas abaixo) e 1 erro de ambiente: `tests.test_supply_chain_install` exige o pip 26.2.2 fixado pelo projeto e o ambiente de validação tem o pip 26.3. O mesmo erro ocorre numa cópia limpa do `main`, sem esta alteração |
| Navegador (13 módulos, com as capturas da documentação) | `NEXO_TEST_BROWSER=1 NEXO_TEST_CDN_DIR=<cópias da CDN> NEXO_TEST_CHROMIUM=<Chrome for Testing> NEXO_PAINEL_CAPTURAS=<pasta> python -B -m unittest tests.test_configuracoes_navegador tests.test_contratos_navegador tests.test_csp_navegador tests.test_gerenciamento_navegador tests.test_identidade_visual tests.test_landing_commercial tests.test_landing_video_commercial tests.test_nexobot_navegador tests.test_notificacoes_horario_brasilia tests.test_overflow_navegador tests.test_painel_navegador tests.test_planos_navegador tests.test_tema_navegador` | 180 testes em 1234 s: 179 aprovados e 1 pulado (o teste PostgreSQL de notificações, executado na rodada PostgreSQL); o teste de capturas gerou 44 imagens (10 seções e o topo, em 1366 e 390 px, temas escuro e claro) |
| Módulos que dependem das cópias íntegras da CDN (fora dos 13 de navegador) | `NEXO_TEST_BROWSER=1 NEXO_TEST_CDN_DIR=<cópias da CDN> NEXO_TEST_CHROMIUM=<Chrome for Testing> python -B -m unittest tests.test_cancelled_company_security tests.test_complementary_hardening_security tests.test_contratos_portal tests.test_http_hardening_security tests.test_report_publication_security tests.test_pdf_export_horario tests.test_pdf_export_layout tests.test_pdf_export_security` | 193 testes em 99 s: todos aprovados, nenhum pulado |
| PostgreSQL (11 suítes) | `NEXO_TEST_POSTGRES_BIN=/usr/lib/postgresql/16/bin python -B -m unittest tests.postgresql_detalhamento_produtos tests.postgresql_auth_tokens tests.postgresql_session_revocation tests.postgresql_company_restore_security tests.postgresql_company_restore_migration tests.postgresql_etl_resource_security tests.postgresql_configuracoes tests.test_cancelled_company_postgresql tests.test_contratos_postgresql tests.test_leads_postgresql tests.test_planos_postgresql` | 170 testes em 187 s: todos aprovados |
| PostgreSQL (demais módulos com PostgreSQL) | `NEXO_TEST_POSTGRES_BIN=/usr/lib/postgresql/16/bin python -B -m unittest tests.test_backup_restore tests.test_notificacoes_horario_brasilia tests.test_bootstrap_guard tests.test_dependency_wsgi_runtime` | 37 testes em 39 s: 36 aprovados e 1 pulado (o teste de navegador de notificações, executado na suíte de navegador) |

A validação local partiu do `main` em `e1e3e73`. A CI do PR (GitHub Actions, evento `pull_request`) executa sobre a combinação com o `main` atual, que já inclui o PR #47: os três jobs passaram no commit `23e6d2f`.

As condições de pulo do projeto são navegador, PostgreSQL, cópias íntegras da CDN (e Socket.IO servido a partir delas), pdftotext e recursos POSIX; as três primeiras foram cobertas pelas rodadas específicas acima e as duas últimas estão disponíveis no ambiente, de modo que cada teste pulado na regressão foi executado em outra rodada. O PostgreSQL foi um cluster privado criado pelo próprio teste e removido ao final; nenhum teste acessou o Supabase, o Render ou o sistema empresarial.

### G.3. Cobertura da validação

| Tema | Como foi verificado |
| --- | --- |
| Motor financeiro inalterado | 22 cenários históricos de SEC-005 com `ResultadoETL` idêntico entre `calculate` e `calculate_detailed` no processo, 3 deles também pelo worker isolado; `tests.test_etl_financial_equivalence` sem alteração |
| Cálculos e regras | Variações (inclusive sem base e média diária), estatísticas, tendência, distribuição A/B/C com percentuais somando 100,0%, legado exato x indisponível, saída relativa, insights e recomendações pelas condições de `rastreio`, ausência de termos proibidos (lucro, prejuízo, margem, promessa) |
| Série histórica | Mensal x quinzenal, rótulos de quinzena, sobreposição por prioridade, período atípico, lacunas, período sem vendas, janela de 24 com a atual e a anterior, omitidos antigos e recentes |
| Movimentação | Unidades reconhecidas, divergentes, múltiplas, ausentes e ausentes só em parte das linhas; unidade de um relatório nunca rotula a quantidade do outro; coluna de unidade com nomes de loja ignorada; fator de embalagem preservado; compras em nível de nota fiscal; quantidade inválida; linha de compra sem produto e linhas de frete e juros; totais por situação; registro parcial declarado; critério único de compras acima das vendas |
| Escala e limites | 3.000 produtos com agregados exatos; teto de linhas com prefixos contínuos; orçamento de saída; empates com posições únicas; consulta paginada com página fora da faixa, parâmetros inválidos e busca longa |
| Contrato do worker | Payload válido convertido; adulterações recusadas (chave, situação, diferença, classe, percentual, nome vazio, invariantes, totais por situação, colunas, NaN, chave extra) |
| Persistência e migração | Gravação e regravação, caminho idêntico sem as tabelas, detalhamento indisponível, erro de banco preservando os KPIs, volta ao cálculo original quando a execução detalhada esgota saída, tempo ou recursos (e erro do arquivo falhando como antes), reprocessamento com falha sem ressuscitar o detalhamento anterior, detalhamento de outra versão ignorado, cascata, downgrade protegido, OLD_HEAD → NEW_HEAD com dados existentes |
| PostgreSQL | Migração aditiva sobre dados existentes, RLS e políticas da Data API (`anon`/`authenticated` sem privilégio), paridade modelo/migração, Numeric, totais por situação, busca normalizada, falha do detalhamento, cascata, downgrade e portal sem as tabelas |
| Segurança | Só devolutiva publicada (o resumo exibido é a cópia publicada, nunca o rascunho); isolamento entre empresas; cobertura contratual da análise; compras por produto bloqueadas quando o período do relatório de compras excede a cobertura, com controle positivo após a cobertura; endpoint sem efeito colateral, com `no-store` e `nosniff`; nomes da planilha escapados |
| Desempenho das consultas | Análise com 3.000 produtos detalhados: a Visão Geral carregou 99 linhas de produto em 26 comandos SQL (limites verificados: 100 e 40) e a consulta paginada, 25 linhas em 13 comandos (limite: 15); Visão Geral e histórico sem consulta por análise (N+1) |
| Antes da migração | Downgrade real para `f4c2a8e1d9b6` no SQLite com o portal no ar: Visão Geral e consulta seguem no modo anterior, sem erro; também com a verificação de esquema indicando ausência |
| Valores ausentes | Indicador com total comprado e diferença nulos: nada é apresentado como zero ou equilíbrio |
| Navegador | Oito larguras (320, 360, 390, 430, 768, 1024, 1366 e 1920 px) sem cortes nem rolagem horizontal; cinco gráficos desenhados; temas claro, escuro e sistema (claro e escuro); consulta paginada, filtros e busca com resultado exato (sem diferenciar acentos e maiúsculas, esperando a resposta de cada termo); duas ações seguidas antes da resposta se somam; rótulos de coluna nas linhas carregadas no celular; mensagens para 429 e 404; nenhuma página pulada e seleção mantida após falha; largura das barras pelo período, marca “Atual”, borda do filtro ativo e legenda do Pareto; console sem erros além dos simulados |
| Regressão | Suíte completa do projeto, suíte completa de navegador, as onze suítes PostgreSQL e os testes PostgreSQL de backup e restauração (inventário de 34 tabelas), notificações, proteção do bootstrap e runtime WSGI |

### G.4. Revisão técnica do diff

Antes da abertura do PR, o diff completo passou por duas rodadas de revisão técnica, com verificação independente de cada achado contra o código. A primeira cobriu cinco frentes (cálculos e regras, ETL e migração, segurança, frontend e testes); a segunda revisou as próprias correções (regras e painel, ETL e dados, frontend e testes, e a fidelidade desta documentação). Todos os achados confirmados foram corrigidos nesta entrega, com testes novos ou ajustados. Os 18 testes de regra escritos nas duas rodadas foram executados também contra a versão anterior às correções e falham todos nela (6 falhas e 12 erros); o teste de navegador das ações seguidas falha com o JavaScript anterior à segunda correção.

Primeira rodada:

| Frente | Achado | Correção |
| --- | --- | --- |
| Cálculos | A recomendação da Classe A e a de crescimento conferiam compras acima das vendas só entre as 10 primeiras linhas da movimentação | Conferência na linha do próprio produto e consulta própria das linhas com compras acima das vendas em todo o registro |
| Cálculos | Períodos de 28 x 31 dias ou quinzenas de 13 a 16 dias geravam “alta”/“queda” só pelo calendário | Relevância pela média diária, com as durações declaradas nos textos e no indicador |
| Cálculos | A resolução de sobreposição podia descartar um período sem conflito com os mantidos | Seleção por prioridade (atual, depois conclusão mais recente), aceitando só o que não sobrepõe os já aceitos |
| Cálculos | Cartões podiam sugerir ações opostas para o mesmo produto (crescimento x compras acima das vendas; concentração x compras acima) | Ação ajustada no próprio cartão e recomendação de crescimento suprimida |
| Cálculos | Contagens da movimentação apresentadas como totais quando o registro era parcial | Totais por situação sobre todos os comprados e aviso de registro parcial |
| Cálculos | Janela da série podia perder o período anterior; nota chamava de “mais antigos” períodos mais recentes | Janela sempre com a atual e a anterior; omitidos nomeados pelo lado correto |
| Cálculos | Selo da diferença pelo sinal contradizia “compras e vendas equilibradas” | Selo pelos mesmos limiares de ±5% |
| Cálculos | Quantidades sempre rotuladas “un.” | Unidade informada nos relatórios; sem unidade conhecida, só o número |
| Cálculos | Estimativa legada exibida como diferença validada e motivo “processada antes” nem sempre verdadeiro | Rótulo de estimativa sem conferência e texto neutro |
| Cálculos | Evolução de compras e vendas dava motivo errado para período atual atípico | Mesmo texto de período não comparável da evolução do faturamento |
| ETL/migração | Falha ao gravar o detalhamento num reprocessamento devolvia o detalhamento antigo ao lado dos KPIs novos | Exclusão e gravação em SAVEPOINTs separados e detalhamento ligado à `versao_processamento` dos KPIs |
| ETL/migração | Com teto de registro, as situações não comparáveis eram cortadas sem aviso | Totais por situação persistidos e aviso de registro parcial |
| ETL/migração | Unidade em branco num relatório com coluna de unidade virava comparação validada | Linha não comparada (unidade ausente ou múltipla) |
| ETL/migração | Linha de compra sem produto (frete, serviço) virava o produto “nan” | Excluída do detalhamento, sem alterar os KPIs |
| Segurança | Compras por produto expostas mesmo quando o relatório de compras abrangia período não coberto (regime contratual) | Visão de movimentação bloqueada no painel e no endpoint até o período de compras estar coberto |
| Segurança/Frontend | Respostas 403, 404 e 429 da consulta eram apresentadas como sessão expirada | Mensagens próprias por situação |
| Frontend | Linhas carregadas pela consulta perdiam o nome das colunas no modo cartão do celular | Rótulos e papéis de tabela aplicados a cada página carregada |
| Frontend | Barras da evolução alargavam sobre lacunas; texto citava “linha”; período atual só por cor | Largura de cada barra pelo próprio período, texto próprio e marca “Atual” em texto |
| Frontend | Falha ao carregar avançava a página; filtros de quantidade inválida e de todos os comprados ausentes; filtro ativo com pouco contraste; legenda do Pareto incorreta no celular | Página só muda com resposta; filtros acrescentados; borda e marca no filtro ativo; legenda válida nos dois modos |
| Frontend/dados | Busca diferenciava acentos e pontuação só nas análises com detalhamento | Busca pelo nome normalizado (`produto_busca`) nas duas situações |
| Testes | Valores nulos do indicador apareciam como “Equilíbrio” e “R$ 0,00” | Nível “indisponível”, “—” e “Não calculado”, sem gráfico com valor presumido |
| Testes | Teste de RLS no PostgreSQL não detectaria falta do REVOKE ou papéis errados nas políticas | Privilégios padrão do Supabase simulados e definição completa das políticas comparada |
| Testes | Caminho dos totais por situação, limite de cinco recomendações, resumo publicado e cobertura das compras sem verificação efetiva | Testes de regra e de rota específicos, com controle positivo |
| Testes | Nenhum teste limitava as consultas com milhares de produtos; teste “sem tabelas” não podia falhar | Teste com 3.000 produtos contando linhas e comandos; downgrade real no SQLite |
| Testes | Asserção da busca no navegador passava com resultado vazio | Asserção exata com espera pelo estado da página; a correção revelou uma espera fixa insuficiente sob carga, também substituída |

Segunda rodada (sobre as correções):

| Frente | Achado | Correção |
| --- | --- | --- |
| Regras/ETL | A unidade de um relatório rotulava a quantidade do outro quando só um deles informava unidade | Cada quantidade com a unidade do seu relatório; a diferença só com a unidade comum |
| Regras/Frontend | Duas definições de “compras acima das vendas” (diferença positiva na tabela, saída abaixo de 90% nas recomendações) | Um único critério (saída abaixo de 90%), explicado na seção; a recomendação da Classe A diz quem fica de fora e por quê |
| Regras | Tendência e acumulado da evolução ainda liam o calendário como tendência | Média diária quando as durações diferem, indicada no cartão e no texto |
| Regras | Com relatórios de períodos diferentes, “garantir reposição” convivia com “revisar a compra” na tabela | Ações neutras por produto nesse caso |
| Frontend | Na fronteira de 5%, o selo contradizia o percentual exibido (5,04% exibido como 5,0% e classificado como pressão) | Classificação pelo percentual exibido |
| Frontend | A correção do estado da consulta descartava uma ação feita antes da resposta da anterior | Nova ação parte do pedido pendente; teste com dois cliques simultâneos |
| ETL | Produto com unidade só em parte das linhas era comparado; frete, taxas e juros viravam “produto sem venda” | Linha não comparada (unidade ausente); essas descrições ficam fora do detalhamento |
| ETL | Estouro de tempo ou de recursos só na execução detalhada fazia falhar um processamento que daria certo sem ela | Cálculo original refeito sem detalhamento nesses casos |
| Frontend | Cartão de total comprado não declarava durações diferentes | Mesma nota do cartão de faturamento |
| Testes | Passo de busca no navegador lia a tabela anterior e afirmava busca por ordem de palavras inexistente; asserção de “Não calculado” atendida por outro cartão | Espera pela resposta do próprio termo, termo sem acento e maiúsculas; asserção no cartão certo; verificação de largura das barras, marca “Atual”, borda do filtro e legenda do Pareto |
| Documentação | Ordem de reversão inexecutável, condição da cobertura de compras omitida, limiares descritos como iguais aos da página da análise, lista do NexoBot incompleta e números de testes desatualizados | Seções D, F, G, H e J corrigidas |

### G.5. Evidências visuais (dados sintéticos)

Capturas geradas pelo teste `test_capturas_para_documentacao` (Playwright, Chromium) com os dados fictícios do conjunto de testes de navegador, que usa nomes longos e valores extremos de propósito para testar cortes de texto e números grandes. Nenhum dado real. Arquivos nesta mesma pasta:

| Arquivo | Conteúdo |
| --- | --- |
| `2026-11-14_Dashboard_Visao_Geral_computador_escuro_01_indicadores.jpg` | Indicadores principais, 1366 px, tema escuro |
| `2026-11-14_Dashboard_Visao_Geral_computador_claro_04_curva_abc.jpg` | Curva ABC: Pareto, distribuição por classe, cartões A/B/C e consulta paginada, 1366 px, tema claro |
| `2026-11-14_Dashboard_Visao_Geral_computador_escuro_09_recomendacoes.jpg` | Ações recomendadas, 1366 px, tema escuro (os itens da Classe A com compras acima das vendas ficam fora da ação da Classe A, com o motivo) |
| `2026-11-14_Dashboard_Visao_Geral_celular_claro_05_movimentacao.jpg` | Movimentação dos produtos no celular (tabela em cartões, filtro ativo marcado), 390 px, tema claro |
| `2026-11-14_Dashboard_Visao_Geral_celular_escuro_01_indicadores.jpg` | Indicadores principais no celular, 390 px, tema escuro |

## H. Limitações e pendências

1. **Migração não aplicada no Supabase de testes.** A revisão `5a9c3e7d1b42` foi validada em SQLite e em PostgreSQL 16 descartável. Até ser aplicada (com aprovação), o portal funciona no modo anterior: o ETL não grava o detalhamento e a Visão Geral mostra o que existe, declarando o que não está disponível.
2. **Análises já publicadas não ganham o detalhamento sozinhas.** Nada é recalculado silenciosamente. Para obter distribuição completa, consulta de todos os produtos e movimentação, a análise precisa ser despublicada, reprocessada e publicada de novo pelo consultor (fluxo existente). Até lá: análises com menos de 20 produtos têm distribuição exata; com 20, a participação das classes não é exibida.
3. **Correspondência entre compras e vendas pela descrição.** A mesma chave normalizada do KPI de saldo estimado. Produtos com descrições diferentes nos dois relatórios aparecem como “sem venda correspondente” e ficam fora da diferença. A coluna de código (EAN/SKU) não é usada para casar produtos nesta versão.
4. **Unidade de medida.** Só é validada quando os relatórios trazem a coluna; sem ela, a comparação considera as quantidades como registradas e a ressalva é exibida. Fatores de conversão (CX12 → UN) não são aplicados. O cartão “maior diferença” compara números de produtos que podem ter unidades diferentes entre si (cada um exibido com a sua unidade).
5. **Teto de registro.** Catálogos acima de 5.000 produtos (ou nomes muito longos que esgotem o orçamento de saída de 2 MiB) têm consulta limitada aos primeiros registrados, com aviso; os agregados por classe e os totais por situação continuam exatos.
6. **Cobertura contratual das compras.** O bloqueio pelo período do relatório de compras vale para as compras por produto (novas nesta entrega) quando o relatório de compras declara período no cabeçalho. Sem período no cabeçalho, vale o período declarado da análise, já autorizado (a mesma regra da autorização da análise). Os totais já exibidos antes (total comprado e indicadores agregados) seguem a regra de acesso existente, que não foi alterada por restrição desta entrega; a revisão dessa regra deve ser decidida à parte.
7. **Base de conhecimento do NexoBot.** Por restrição desta entrega o NexoBot não foi alterado. Registros que descrevem a Visão Geral antiga ficam desatualizados e devem ser revistos numa entrega própria. A lista abaixo não é exaustiva: a revisão deve cobrir os 26 registros (em 8 arquivos de `nexobot/saber/`) cujas fontes incluem `templates/cliente/dashboard.html`. Já identificados: `nexobot/saber/dashboard.py` (`nexo.dashboard.visao_geral`, `nexo.dashboard.cards`, `nexo.dashboard.graficos`, `nexo.dashboard.historico_comparativo`, `nexo.dashboard.interpretar_valores`), `nexobot/saber/visao_geral.py` (`nexo.visao_geral.funcionalidades`) e `nexobot/saber/indicadores.py` (`nexo.indicadores.semaforos`, `nexo.indicadores.saldo_parado`, `nexo.indicadores.comparativo`, `nexo.indicadores.pressao_estoque`). O Pareto foi mantido com 10 produtos para não contradizer as respostas atuais.
8. **Faixa de equilíbrio diferente da página da análise.** A Visão Geral usa a faixa de −5% a 5% (“Equilíbrio”); os semáforos da página da análise (`insights.gerar_semaforos`, não alterados) chamam de “giro de estoque saudável” tudo o que não passa de 5%. Com compras 3% acima ou abaixo do faturamento, a Visão Geral mostra “Equilíbrio” e a página da análise, “giro de estoque saudável”. Alinhar as duas telas é uma decisão de produto fora desta entrega.
9. **Imagem de referência.** O arquivo “Dashboard NEXO de Faturamento Inteligente.png” não estava disponível no ambiente; a implementação seguiu a lista textual de componentes da solicitação, sem copiar composição nem valores.
10. **Navegadores.** Validação automatizada em Chromium; Firefox e Safari não foram testados.
11. **Busca por trecho.** A busca encontra um trecho contínuo do nome normalizado (sem acentos, maiúsculas ou pontuação): “agua mineral” encontra “Água mineral com gás”, mas palavras fora de ordem ou separadas por outras não são combinadas.

## I. Reprodução no sistema empresarial

Este guia não autoriza acesso ou alteração do sistema empresarial. Não clonar o repositório de homologação sobre o empresarial.

1. Confirmar no empresarial a existência de `etl_runtime.run_calculation`, `etl_worker.py` com a operação `calculate`, `insights.gerar_semaforos`, `contract_policy.filtrar_analises_consultaveis`, `contract_policy.periodo_coberto`, `IndicadorAnalise.versao_processamento` e `RelatorioAnalise.publicada`. Se algum faltar, adaptar os pontos de integração antes de copiar código.
2. Conferir o head de migrações do empresarial (`flask db heads`). A revisão `5a9c3e7d1b42` encadeia em `f4c2a8e1d9b6`; se o head for outro, gerar uma revisão equivalente com o mesmo conteúdo e `down_revision` correto.
3. Levar, nesta ordem: `models.py` (dois modelos), a migração, `detalhamento_produtos.py`, `inteligencia_comercial.py`, `painel_cliente.py`, as alterações de `etl_processor.py`, `etl_worker.py` e `etl_runtime.py`, `blueprints/cliente.py`, os templates e a folha de estilos.
4. Rodar `tests.test_etl_financial_equivalence` antes e depois: o resultado da operação `calculate` deve permanecer idêntico.
5. Rodar as suítes novas, a regressão completa, a suíte de navegador e `tests.postgresql_detalhamento_produtos` em PostgreSQL descartável.
6. Implantar o código primeiro (expand → migrate → deploy): sem as tabelas tudo funciona como antes.
7. Aplicar a migração por ID (`flask db upgrade 5a9c3e7d1b42`), com `lock_timeout` e `statement_timeout`, depois de backup, conferindo RLS e políticas (`pg_policies`) e que `anon`/`authenticated` não têm privilégio nas tabelas novas.
8. Reprocessar (despublicar, processar e publicar) apenas as análises que precisarem do detalhamento, com o cliente ciente.
9. Revisar a base de conhecimento do NexoBot (item H.7) numa entrega própria, cobrindo todos os registros que citam `templates/cliente/dashboard.html`.

## J. Reversão

A ordem importa: reverter o código remove o arquivo da migração, e a partir daí o `downgrade` não encontra mais a revisão `5a9c3e7d1b42` (o banco ficaria marcado com uma revisão desconhecida, bloqueando migrações futuras). Ver também `Docs/OPERACAO_BACKUP_RESTAURACAO.md`: reverter código não desfaz migração executada.

1. **Se a migração `5a9c3e7d1b42` não foi aplicada:** basta reverter o PR. O portal volta à Visão Geral anterior; o ETL volta a usar só `calculate`.
2. **Se a migração foi aplicada e as tabelas devem sair:** com o código desta entrega ainda implantado, fazer backup, esvaziar `produto_desempenho_analise` e `indicador_complementar_analise` explicitamente, executar `flask db downgrade f4c2a8e1d9b6` (com dados, o downgrade é recusado de propósito) e conferir com `flask db current`. Só então reverter o PR.
3. **Se a migração foi aplicada e as tabelas podem ficar:** reverter apenas o código da aplicação e manter no repositório o arquivo da migração `5a9c3e7d1b42`, com os modelos das duas tabelas e os testes que registram o head e o inventário de tabelas (`tests/test_leads_avaliacao.py`, `tests/test_leads_postgresql.py`, `tests/test_backup_restore.py`, `tests/test_contratos_postgresql.py`); as tabelas ficam sem uso. Uma remoção posterior segue o item 2.
4. **Testes:** na reversão completa (itens 1 e 2), a reversão do PR restaura também os testes que registram o head e o inventário de tabelas.
5. Nada precisa ser feito em `produto_curva_abc`, `indicador_analise`, relatórios publicados, PDF ou devolutivas: eles não foram alterados.
