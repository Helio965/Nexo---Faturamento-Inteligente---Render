# NEXO: Faturamento Inteligente — Relatório técnico para auditoria independente

## Exportação PDF: formatação, paginação, gráfico de pizza da Curva ABC, "Síntese executiva" e horário oficial de Brasília

Documento preparado para auditoria independente (ChatGPT). Tudo o que está aqui foi lido no repositório oficial ou executado em cópia descartável do código, com dados sintéticos, sem acesso a produção (Render, Supabase ou banco real). Fato verificado e hipótese aparecem sempre separados. Cada número vem de um log, de um teste ou de uma captura incluídos no pacote de evidências (seção H).

## A. Identificação

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| SHA inicial (`main`) | `7bd383b02a68c5685e2bb081d67e0c3745bd65b5` — "Merge pull request #34", 28/10/2026 10:07 (−03:00). Conferido com `git fetch` antes de começar. |
| Branch de trabalho | `claude/awesome-pascal-0ho42m` (branch designada desta sessão). O nome sugerido `fix/nexo-pdf-layout-grafico-abc-horario-brasilia` fica registrado, mas a sessão só publica na branch designada. |
| PR principal | [#35](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/35) — "NEXO: correção completa dos PDFs com gráfico ABC e horário de Brasília" (6 commits). **Integrado pelo proprietário** em 29/10/2026 às 13:37 UTC (10:37 em Brasília), quando o job de navegador do CI e a revisão independente ainda estavam em andamento. Merge na `main`: `c6f129954fdd6a5e6c71c35840fde1410a657fb5`. |
| PR de acompanhamento | [#36](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/36) (rascunho), sobre a `main` `c6f1299`: correção do CI da `main`, correções da revisão independente, horário (metadados, localidade, relógio único) e este relatório. |
| Data | 29/10/2026 |
| Ambiente | Contêiner isolado Ubuntu 24.04, Python 3.12.3 (o CI usa 3.12; o `render.yaml` fixa 3.12.10), ReportLab 4.2.5, poppler-utils (`pdftotext`), Chromium para os testes de navegador, PyMuPDF 2.0 em ambiente virtual separado só para a inspeção visual. Sem chave do Render, sem credencial do Supabase. |
| Documento de referência | `analise_nexo_202606_5 (3).pdf` **não estava disponível nesta sessão** (procurado em todo o sistema de arquivos e nos anexos). Os defeitos foram reproduzidos com o gerador da `main` e dados sintéticos com exatamente os valores informados no pedido (faturamento R$ 4.311,00; Top 5 R$ 4.256,00; outros R$ 55,00; 74,23 / 17,63 / 5,10 / 0,93 / 0,84 / 1,28 %). |

## B. Auditoria inicial (como funcionava)

Fontes: leitura de `pdf_export.py`, `blueprints/cliente.py`, `insights.py`, `etl_processor.py`, `contract_policy.py`, `config.py`, `render.yaml`, `requirements.txt`, `tests/test_pdf_export_security.py` e `.github/workflows/nexo-security-ci.yml` na `main` `7bd383b`; reprodução do documento com o gerador da `main` e inspeção geométrica do PDF resultante (PyMuPDF e `pdftotext -bbox-layout`).

| Item auditado | Situação encontrada |
|---|---|
| Gerador | `pdf_export.py` (297 linhas, terminadores CRLF), ReportLab *platypus* com `SimpleDocTemplate`; função pública `gerar_pdf_analise(analise, semaforos, abc_top)`. |
| Rota | `GET /cliente/analise/<id>/pdf` → `analise_pdf` em `blueprints/cliente.py` (linha 314). `@cliente_required` (login + papel CLIENTE). Ordem das verificações: análise existe, pertence à empresa do usuário, `status_analise == "CONCLUIDO"`, relatório existe e está publicado (senão 404); depois a política contratual (`pode_consultar_analise`, `pode_exportar_pdf`), que responde 403 **antes** de gerar qualquer byte; só então `gerar_semaforos` e `gerar_pdf_analise(analise, semaforos, analise.curva_abc)`. Resposta `application/pdf` com `Content-Disposition: attachment; filename="analise_nexo_AAAAMM_ID.pdf"`. |
| Dependências | `reportlab==4.2.5` (`requirements.txt`). `zoneinfo` é da biblioteca padrão; a base de fusos vem do sistema operacional e, como reserva, do pacote `tzdata` 2026.5, já instalado como dependência do `python-dateutil` 3.0.0 (exigido por `pandas` 3.0.3), mas não declarado. Na revisão independente o `tzdata` passou a ser declarado em `requirements.txt` (seção F, item 8). |
| Testes existentes | `tests/test_pdf_export_security.py` (NEXO-SEC-001): 20 testes — 13 de conteúdo e segurança do documento (marcação literal, sem imagens/links/recursos externos, caracteres especiais, A4, opcionais ausentes, integridade) e 7 da rota (cliente autorizado, anônimo, administrador, outra empresa, não publicada, prazo encerrado, período não pago, erro sem detalhes). O CI (`nexo-security-ci.yml`) instala `poppler-utils` e roda a suíte completa em Python 3.12. |
| Cálculo do horário | Linha 293: `f"Documento gerado pelo portal NEXO em {datetime.now().strftime('%d/%m/%Y %H:%M')}."` — `datetime.now()` **sem fuso**, ou seja, no fuso configurado no processo. O `render.yaml` só define `PYTHON_VERSION=3.12.10` (nenhuma variável `TZ`), e o padrão dos serviços do Render é UTC; no Render o PDF sai, portanto, 3 horas à frente de Brasília (UTC−3 desde o fim do horário de verão, em 2019). O rodapé não trazia horário. |
| Cache | O PDF é gerado a cada pedido, em memória (`BytesIO`); não existe cache no servidor (sem Flask-Caching, sem arquivo gravado). A resposta não tinha `Cache-Control`, `ETag` nem `Last-Modified`. Não há *service worker*. |

**Problemas do documento, reproduzidos com o gerador antigo e os dados de referência** (inspeção automática em `inspecao/inspecao_ANTES.json` do pacote; capturas em `capturas/08_*` e `capturas/09_*`):

| # | Problema | Evidência |
|---|---|---|
| 1 | Cabeçalho cortado: a faixa roxa começa acima da página; "NEXO" e "Análise Executiva" ficam parcialmente fora dela. | Caixas de texto em y = −9,7 pt ("NEXO") e y = −4,0 pt ("Análise Executiva"); desenho da faixa de y = −13,8 a 48,5 pt. Causa: `_BarraTopo` sem `wrap()` — o Flowable media 0 × 0. |
| 2 | Título encostado na linha da empresa (sobreposição das caixas de texto). | Área de interseção de 771,5 pt² entre o título e "Empresa … · CNPJ … · Período …"; estilo do título sem espaço depois. |
| 3 | Título isolado: "Devolutiva do consultor" é a última linha da página 1, e o texto começa só na página 2. | `titulo_isolado_no_fim_da_pagina` na página 1. |
| 4 | Margens irregulares: indicadores e cartões da síntese 12 pt mais largos que o quadro (6 pt para fora de cada lado); tabela ABC 6 mm mais estreita que eles. | Larguras: quadro 481,2 pt; indicadores e cartões 493,2 pt; tabela 476,2 pt. |
| 5 | Rodapé só com "Página N" (sem total) e sem data/hora de geração. | Texto do rodapé. |
| 6 | "% acum." com ponto decimal (74.2%), destoando do restante em pt-BR. | Texto da tabela. |
| 7 | Título "Síntese executiva (5W2H)". | Texto do PDF. |
| 8 | Devolutiva: "Resumo executivo." e "Conclusão estratégica." como prefixo em negrito do parágrafo, e as quebras de linha e parágrafos do consultor colapsados num bloco só. | Texto do PDF comparado com o texto de entrada. |
| 9 | Horário de geração no fuso do processo (UTC no Render). | `datetime.now()` ingênuo; ensaio da seção F. |
| 10 | Valores muito grandes quebravam em duas linhas nas células dos indicadores. | Variante de valores grandes (`test_03_valores_grandes_cabem_inteiros_nas_celulas`). |

Varredura com o gerador antigo: os **265** documentos gerados (13 variantes extremas, 72 combinações de tamanho dos textos da devolutiva e 180 de paginação) tinham problemas, com o cabeçalho fora da página em todos (seção G.5).

**Sobre "duas horas de diferença".** Com o código antigo a diferença é de exatamente 3 horas quando o processo está em UTC (ensaio da seção F). Uma diferença de 2 horas não foi reproduzida com nenhuma configuração padrão. Hipóteses (não confirmadas): (a) comparação com um download anterior — o nome `analise_nexo_202606_5 (3).pdf` indica que o mesmo arquivo foi baixado ao menos três vezes, e um arquivo gerado 1 hora antes, com +3 h, aparenta +2 h; (b) processo configurado num fuso diferente de UTC. A correção independe da causa: o horário não depende mais do fuso do servidor e cada exportação gera um arquivo novo.

## C. Correções de formatação

Todas em `pdf_export.py`. Nenhuma usa margem artificial para esconder o defeito: cada uma ataca a causa. Os itens marcados **(#36)** vieram da revisão independente (seção G.7) e foram aplicados no PR de acompanhamento.

1. **Cabeçalho (`_BarraTopo`).** A faixa passa a declarar o próprio tamanho em `wrap()` (`min(largura, availWidth)` × 22 mm) e a desenhar tudo dentro de `0 ≤ y ≤ 22 mm`, com `saveState`/`restoreState`. À esquerda ficam "NEXO" (20 pt) e "Faturamento Inteligente" (8,5 pt), empilhados; à direita, "Análise Executiva" (12 pt) e "Referência MM/AAAA" (8,5 pt). Todos estão centralizados na vertical, com 10 mm de recuo. O platypus reserva a altura da faixa, então nada mais a sobrepõe.
2. **Quadro e margens.** `BaseDocTemplate` com um `Frame` sem recuo interno: a largura útil é exatamente 493,2 pt (A4 menos 18 mm de cada lado). Indicadores, tabela ABC, seção do gráfico e cartões somam essa largura, o que é verificado por teste. A margem superior é de 15 mm; a inferior, de 24 mm, fica reservada ao rodapé.
3. **Rodapé (`_desenhar_rodape` + `_canvas_com_rodape`).** Um canvas numerado guarda o estado de cada página e só desenha o rodapé no `save()`, quando o total já é conhecido. Elementos:
   - Régua a 17 mm.
   - A 12,5 mm: "Página X de Y" em negrito, à direita, e o aviso "Sinalização gerencial estimada… Não representa lucro, margem ou CMV.", à esquerda.
   - A 8,5 mm: "Gerado em dd/mm/aaaa às hh:mm (horário de Brasília)", à direita, e "NEXO · empresa · Referência MM/AAAA", à esquerda.

   **(#36)** Se faltar espaço, só o nome da empresa é encurtado, com reticências: a referência nunca some. O corte usa busca binária; antes era quadrático, e um nome de 20 mil caracteres levava cerca de 80 s.
4. **Paginação sem títulos isolados nem buracos.**
   - Os blocos curtos viajam inteiros com o título (`KeepTogether`): "Indicadores do período" com o quadro; "Curva ABC" com a tabela e a explicação; a seção do gráfico inteira; "Síntese executiva" com o primeiro cartão; cada cartão.
   - **(#36)** Na devolutiva, um primeiro parágrafo de até 8 linhas viaja inteiro com "Devolutiva do consultor" e "Resumo executivo" (ou com "Conclusão estratégica"). Um parágrafo mais longo começa logo abaixo dos títulos: um `CondPageBreak` garante espaço para os títulos e três linhas, e o resto quebra entre páginas sem linhas viúvas ou órfãs. Antes, ele deixava até 59% de uma página em branco.
   - **(#36)** O espaço entre seções virou `spaceBefore` dos títulos, que o quadro ignora no topo de uma página. Antes, um espaçador de 7 mm descia o conteúdo da página seguinte.
   - **(#36)** A frase final "Documento gerado pelo portal NEXO…" viaja com as duas últimas linhas do último parágrafo. Antes, ficava sozinha numa página nova em cerca de 3% das combinações.
   - **(#36, `2774819`)** Quando o último bloco já é indivisível, a frase final entra **no mesmo** bloco, sem aninhar um `KeepTogether` dentro de outro. Isso vale para a conclusão de um parágrafo de até 8 linhas (o formato que a IA produz), para o último cartão (sem devolutiva), para o gráfico e para "Sem texto registrado". No ReportLab, um `KeepTogether` interno mede 0xffffff de altura, então o externo sempre forçava uma quebra de página. O fim do documento ia sozinho para uma página nova e a anterior ficava com metade ou mais em branco (documento de referência com conclusão de um parágrafo: 3 páginas em vez de 2). Esse defeito foi introduzido no próprio #36 (`9ed1711`), nunca chegou à `main` e foi apontado pela frente de requisitos (seção G.7).
   - Nada força o documento a caber em uma ou duas páginas.
5. **Título do documento.** Estilo próprio (16/20 pt) com 4 pt de espaço antes da linha da empresa, o que acaba com a sobreposição.
6. **Indicadores (`_kpis_flowable`).** Três colunas iguais. O valor reduz o corpo (de 13 pt até no mínimo 8 pt) para caber inteiro numa linha da célula.
7. **Tabela da Curva ABC (`_abc_flowable`).** O que se mantém e o que mudou:
   - **Igual à anterior:** colunas e cabeçalho roxo (#, Produto, Classe, Faturamento (R$), % acum.), cores de classe, zebra, valores vindos do banco. Classe e % acumulado **não** são recalculados.
   - **Apresentação:** a largura é igual à dos demais blocos; o nome do produto quebra dentro da coluna; o faturamento reduz o corpo (até 6,5 pt) quando o valor é muito grande; "% acum." usa vírgula decimal; o título fica no singular quando há um só produto.
   - **(#36)** Uma linha excepcionalmente longa se divide entre páginas (`splitInRow`), em vez de impedir a geração.
8. **Devolutiva (`_devolutiva` + `_paragrafos`).** Título "Devolutiva do consultor" e subtítulos "Resumo executivo" e "Conclusão estratégica". O texto do consultor aparece como foi escrito: linha em branco = novo parágrafo, quebra simples = nova linha, como na página web. Cada linha é escapada.
9. **(#36) Exportação que nunca falha por tamanho de texto.** O nome do produto e os nomes da empresa não têm limite de tamanho no banco. No #35, nomes de cerca de 313 caracteres já derrubavam a geração com `LayoutError` (HTTP 500), por causa da legenda ao lado do gráfico.
   - A legenda mostra o nome em no máximo 3 linhas, com reticências; o nome completo continua na tabela.
   - Um cartão da síntese maior que uma página inteira usa uma versão divisível do mesmo cartão. Os cartões normais continuam idênticos.
   - Verificado com textos de 12 mil caracteres: geração sem erro, nenhum problema de geometria em nenhuma das páginas e referência no rodapé de todas.
10. **Valores (#36).** R$ e "% acum." usam a mesma regra do portal (filtro `m.brl` e `'%.1f'` de float, com vírgula), que também era a do PDF anterior. O documento mostra exatamente os números da tela, inclusive nos empates (91,85 → "91,8%" nos dois). Um teste compara com a macro real do portal. A primeira versão do #35 arredondava com `Decimal`, o que fazia o PDF divergir da tela em cerca de 1 a cada 10 percentuais gravados com duas casas; isso foi revertido na revisão. As participações do gráfico, que só existem no PDF, continuam em `Decimal` exato.

**Segurança.** Na rota, a autenticação, o vínculo cliente–empresa, o estado de publicação e a política contratual continuam verificados **antes** da geração, com o mesmo código. A rota só ganhou a docstring, dois cabeçalhos (`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`) e o relógio único da requisição (seção F).

Todo texto externo continua escapado uma única vez na entrada dos `Paragraph`, inclusive nos dois lugares novos:

- **Nome na legenda:** o corte acontece antes do escape, então nenhuma entidade fica partida.
- **Empresa no rodapé:** é desenhada como texto literal no canvas, que não interpreta marcação.

Os novos testes de escape falham quando o código é mutado com escape duplo ou com escape no canvas. O log de inconsistência registra só o identificador da análise e um código, sem valores comerciais. Nenhuma imagem, link ou recurso externo pode ser carregado (interceptado e verificado pelos testes de segurança).

## D. Gráfico de pizza

**Posição e títulos.** A seção nova fica entre a explicação da Curva ABC e a "Síntese executiva", na ordem pedida:

1. Título da Curva ABC, tabela e explicação.
2. **"Distribuição do faturamento por produto"**, com o subtítulo **"Participação dos principais produtos no faturamento do período."**
3. Gráfico (à esquerda, 54 mm) e legenda (à direita).
4. Nota.
5. "Síntese executiva".

O bloco todo é um `KeepTogether`. Com a legenda limitada a 3 linhas por nome, sua altura é sempre menor que uma página; se não couber depois da tabela, vai inteiro para a página seguinte, com o título.

**Dados (`calcular_distribuicao`).** São os mesmos produtos da tabela (os 5 primeiros de `analise.curva_abc`, na ordem do ranking) e o `faturamento_total` do indicador do período. Nada é fixo no código.

- A participação individual é faturamento do produto ÷ faturamento total × 100, em `Decimal`, guardada sem arredondar. Ela é exibida com 2 casas, arredondando meio para cima.
- "Outros produtos" = faturamento total − soma dos produtos exibidos, quando a diferença aparece em centavos. As comparações usam o valor como é exibido.
- Os dados financeiros **não** são ajustados para a soma dos percentuais arredondados dar 100%. Quando a soma exibida difere de 100,00%, a nota do gráfico diz isso.

Valores de referência (dados sintéticos com os números do pedido):

| Fatia | Faturamento (R$) | Participação exata | Exibida |
|---|---|---|---|
| Fax Térmico Panasonic (A) | 3.200,00 | 74,2287… % | 74,23% |
| Leitor Zip Drive Iomega (B) | 760,00 | 17,6293… % | 17,63% |
| Mouse Bola Serial (C) | 220,00 | 5,1032… % | 5,10% |
| Pilha AA (C) | 40,00 | 0,9279… % | 0,93% |
| Diskette Maxell (C) | 36,00 | 0,8351… % | 0,84% |
| Outros produtos | 55,00 | 1,2758… % | 1,28% |
| **Faturamento total** | **4.311,00** | **100%** | **100,00%** |

A soma das participações exibidas é 100,01%, efeito do arredondamento de cada linha. A soma exata é 100%, e a soma dos faturamentos é exatamente R$ 4.311,00 (teste `test_20_integridade…`). A nota "Percentuais arredondados para duas casas decimais: a soma exibida pode diferir de 100% por arredondamento." aparece nesse caso.

**Inconsistências, tratadas de forma explícita e segura.** As inconsistências geram um aviso "Atenção:" no PDF e um código no log, sem valores comerciais. Os dados não são alterados.

| Situação | Comportamento |
|---|---|
| Soma dos produtos exibidos > faturamento total | A base passa a ser a soma dos produtos, sem fatia "Outros"; o aviso traz os dois valores; o total da legenda é rotulado "Soma dos produtos exibidos". |
| Faturamento total ausente | Base = soma dos produtos; o aviso diz "não informado". |
| Faturamento total zero ou negativo **(#36)** | Base = soma dos produtos; o aviso cita o valor ("não é positivo (R$ −500,00)"), coerente com o quadro de indicadores. |
| Produto da tabela com faturamento zero, negativo ou inválido **(#36)** | Fica fora do gráfico (continua na tabela). A base passa a ser a soma dos exibidos, sem "Outros", para o valor dele não ser somado a "Outros" como se fosse de outro produto. |
| Nenhum produto com faturamento positivo **(#36)** | A seção aparece com título, subtítulo e o motivo, em vez de sumir sem explicação. |
| Participação gravada na Curva ABC diferente da calculada **(#36)** | Acontece quando o período tem produtos com faturamento líquido negativo, como devoluções. O ETL soma todos no faturamento total, mas a Curva ABC usa só os positivos. O gráfico segue a fórmula pedida (sobre o faturamento total) e o PDF avisa que as bases diferem. |
| Diferença menor que um centavo | Tratada como arredondamento: sem "Outros" e sem aviso. |

**Desenho (`_grafico_pizza`).**

- `Drawing` + `Pie` do ReportLab: vetorial, 2D, sem 3D e sem imagem.
- Começa às 12 h, no sentido horário, com fatias separadas por um filete branco de 1,2 pt e contorno fino no círculo.
- O percentual aparece dentro das fatias de 12% ou mais, em branco ou tinta escura, o que tiver mais contraste. As menores não recebem rótulo; a legenda traz todos os valores.
- Com uma fatia só (100%), o percentual fica no centro.

**Cores.** As fatias usam uma rampa ordinal no roxo da marca (`#5a06bb → #b4a1fc`; mais escuro = maior participação), validada com o verificador de paletas:

- luminosidade monotônica;
- ΔL ≥ 0,06 entre vizinhos (distinguíveis para daltônicos e na impressão em tons de cinza);
- um só matiz;
- contraste ≥ 2:1 no extremo claro.

"Outros produtos" usa um cinza neutro (`#d5d8e2`, com ΔE ≥ 16,8 contra todos os passos). A identidade de cada fatia não depende só da cor: cada linha da legenda traz o nome e o valor.

**Legenda (`_legenda_flowable`).**

- Colunas: amostra de cor (3,6 mm), Produto (até 3 linhas), Classe (na cor da classe; "—" para Outros), Faturamento (R$) e Participação (em negrito).
- Linha de total no fim.
- Corpo de 8,5 pt, cabeçalho de 8 pt; valores enormes reduzem até 6,5 pt dentro da própria célula.
- Sem sobreposição, verificado por geometria com um nome de 143 caracteres e outro de 100 caracteres sem nenhum espaço.

## E. Síntese executiva

O título passou de "Síntese executiva (5W2H)" para **"Síntese executiva"**. Nada mais mudou na seção: os cartões vêm de `insights.gerar_semaforos` (sem alteração), com título, nível (CRÍTICO / ATENÇÃO / OPORTUNIDADE), "O QUE FAZER" e "POR QUE FAZER", mesmas cores e mesmo desenho. Mudou só a paginação: o título viaja com o primeiro cartão. Verificado por `test_10_sintese_executiva_sem_5w2h_e_com_todos_os_cartoes` (todo o texto dos cartões presente, "5W2H" ausente do documento inteiro), `test_11_titulo_da_sintese_sem_5w2h` (nenhum `Paragraph` criado contém "5W2H") e pelo teste de segurança existente.

Fora do PDF, "5W2H" continua em outros lugares que não fazem parte deste pedido (subtítulo da seção na página web da análise, `templates/cliente/analise.html`; comentários de `insights.py` e `templates/_macros.html`; README; instrução do `ai_devolutiva.py`; uma pergunta do NexoBot sobre o painel). Nada disso foi alterado.

## F. Correção de horário

**1. Comportamento anterior.** A última linha do PDF era `Documento gerado pelo portal NEXO em {datetime.now().strftime('%d/%m/%Y %H:%M')}.`, sem indicação de fuso e sem horário no rodapé.

Ensaio com o **mesmo instante absoluto** (29/10/2026 15:02 UTC = 12:02 em Brasília) e o processo configurado em fusos diferentes (`TZ` + `time.tzset()`; arquivo `horario/horario_evidencias.txt` do pacote):

| Fuso do processo | Antes (gerador da `main`) | Depois |
|---|---|---|
| `UTC` (padrão do Render) | `… em 29/10/2026 15:02.` | `… em 29/10/2026 às 12:02 (horário de Brasília).` |
| `America/Sao_Paulo` | `… em 29/10/2026 12:02.` | `… em 29/10/2026 às 12:02 (horário de Brasília).` |
| `America/Manaus` | `… em 29/10/2026 11:02.` | `… em 29/10/2026 às 12:02 (horário de Brasília).` |
| `Europe/Lisbon` | `… em 29/10/2026 15:02.` | `… em 29/10/2026 às 12:02 (horário de Brasília).` |
| `Asia/Tokyo` | `… em 30/10/2026 00:02.` | `… em 29/10/2026 às 12:02 (horário de Brasília).` |

**2. Causa.** `datetime.now()` sem argumento devolve a hora local **do processo**, sem fuso. O código assumia que o servidor estava em Brasília. No Render ele está em UTC, então o horário saía 3 horas adiantado (e com o dia seguinte depois das 21:00 de Brasília).

**3. Fuso do servidor.** O `render.yaml` não define `TZ` (só `PYTHON_VERSION`), e o padrão dos serviços do Render é UTC. Isso não foi confirmado no painel, por falta de acesso.

Neste contêiner, `/etc/timezone` = `Etc/UTC` e `time.tzname` = `('UTC', 'UTC')`. Com a correção, o fuso do servidor deixa de importar. **Nada foi alterado** no relógio do servidor, no Render ou na configuração de horário do banco.

**4. Funções alteradas e criadas.**

Em `pdf_export.py`:

- `_agora_utc()` — lê o relógio com fuso explícito: `datetime.now(timezone.utc)`.
- `fuso_brasilia()` — `ZoneInfo("America/Sao_Paulo")` (constante `FUSO_HORARIO_OFICIAL`). O `lru_cache` guarda só o objeto de fuso, nunca um horário.
- `instante_de_geracao(gerado_em=None)` — recusa instante sem fuso (`ValueError`) e converte uma única vez, com `astimezone(fuso_brasilia())`.
- `formatar_data_hora()` — `dd/mm/aaaa às hh:mm`. **(#36)** Só a parte ASCII passa pelo `strftime`, então o "às" não depende da localidade do servidor. Antes, `LC_ALL=C` com `PYTHONUTF8=0` gerava `UnicodeEncodeError`.
- **(#36)** `data_pdf()` — monta os metadados `CreationDate`/`ModDate` com o **mesmo** instante do carimbo e o deslocamento dele (`D:20261029120200-03'00'`). Antes, o ReportLab gravava o relógio local do servidor, ignorava o instante escolhido e errava fusos de meia hora.
- `gerar_pdf_analise(…, *, gerado_em=None)` — calcula o carimbo **uma vez por exportação** e usa o mesmo valor no rodapé de todas as páginas, na frase final e nos metadados.

Em `blueprints/cliente.py` (`analise_pdf`):

- Docstring e dois cabeçalhos da resposta.
- **(#36)** O carimbo passa a vir de `contract_policy.agora()`, o "relógio único" documentado da política contratual. É o mesmo instante que autorizou a exportação, lido de novo a cada pedido. Em produção é o relógio real: `NEXO_RELOGIO` só existe como função injetada pelos testes.
- As verificações de acesso não mudaram.

**5. Como `America/Sao_Paulo` foi implementado.** Com `zoneinfo` (biblioteca padrão) e o banco de fusos IANA: o deslocamento de cada data vem das regras oficiais (UTC−3 hoje; UTC−2 nos verões até 2019; horário de verão abolido em 2019).

Não existe no código subtração fixa de 2 ou 3 horas, regra manual de horário de verão, `utcnow()`, `localtime()` nem segunda conversão. O teste `test_codigo_sem_deslocamento_fixo_nem_relogio_ingenuo` analisa a árvore sintática do módulo e falha se algo assim aparecer.

Revisão independente desta parte: 200.204 instantes de 1985 a 2035, incluindo ±1 s em torno das 68 transições de `America/Sao_Paulo`, conferidos contra o `localtime` da libc. Resultado: 0 divergências.

**6. Validação.**

- **Testes:** os 19 do item 10.
- **Ensaio:** o do item 1.
- **PDF final:** gerado pelo código final (`dbacfa3`) com o relógio real e o processo em UTC (`horario/horario_da_geracao_final.txt`). Com o relógio em 15:23:45 UTC, o PDF traz "Gerado em 29/10/2026 às 12:23 (horário de Brasília)" no rodapé das 2 páginas e na frase final. Os metadados são `CreationDate`/`ModDate` = `D:20261029122345-03'00'`.

**7. Novo carimbo a cada exportação.** O instante é lido dentro de cada pedido: nada é calculado na importação do módulo nem guardado entre pedidos. O PDF continua sendo gerado em memória a cada pedido, sem cache no servidor.

A resposta passou a enviar `Cache-Control: no-store`, para nenhum navegador, proxy ou CDN guardar o arquivo, e `X-Content-Type-Options: nosniff`, sem `ETag` nem `Last-Modified`.

Teste de rota: dois `GET` seguidos, com o relógio da requisição injetado em 15:02 e 15:09 UTC, devolvem dois documentos diferentes, com 12:02 e 12:09.

**8. Dependências.** `zoneinfo` é da biblioteca padrão (Python ≥ 3.9; o projeto usa 3.12). A base de fusos vem de `/usr/share/zoneinfo` e, quando o sistema não a tem, do pacote `tzdata`.

**(#36)** `tzdata==2026.5` passou a ser declarado em `requirements.txt`. Antes ele chegava só como dependência transitiva do `python-dateutil` 3.0.0. Num servidor sem a base do sistema e com um `python-dateutil` 2.9, toda exportação daria erro 500.

O teste `test_funciona_sem_a_base_de_fusos_do_sistema_operacional` força `zoneinfo.reset_tzpath([])` e agora falha, em vez de ser ignorado, se o pacote faltar.

**9. Período financeiro e horários gravados intactos.** `periodo_inicio` e `periodo_fim` são datas de calendário (`date`) e continuam impressas como estão, sem conversão de fuso. O gerador não grava nada no banco nem lê horários dele.

Teste `test_05_periodo_financeiro_e_valores_nao_mudam_com_o_horario`:

- Exportação em 01/07/2026 01:30 UTC (ainda 30/06 em Brasília) com o processo em Tóquio (já 01/07 lá).
- O documento mantém "Período 01/06/2026 – 30/06/2026" e "Referência 06/2026".
- Fora o carimbo, o texto é idêntico ao de outra exportação, e os objetos de entrada não mudam.

**10. Testes de horário (`tests/test_pdf_export_horario.py`, 19).**

| Pedido | Teste |
|---|---|
| Servidor em UTC: 29/10 15:02 UTC → 12:02 | `InstanteDeGeracaoTests.test_01…` e `HorarioNoDocumentoTests.test_01…` (no PDF, sem "15:02" em lugar nenhum) |
| Virada do dia: 30/10 01:15 UTC → 29/10 22:15 | `…test_02…` (instante e documento) |
| Processo em outro fuso | `…test_03…` em 9 fusos (UTC, São Paulo, Manaus, Noronha, Nova York, Lisboa, Tóquio, Kiritimati, GMT+12), com prova de que o fuso do processo mudou de fato. Cobre o relógio simulado e o real; o texto do PDF é idêntico nos 9. |
| Exportações sucessivas | `…test_04…` (3 leituras de relógio → 3 carimbos; o relógio real é lido 1 vez por exportação) e o teste da rota |
| Período financeiro inalterado | `HorarioNoDocumentoTests.test_05…` |
| Horário no texto do PDF | `…test_06…` (rodapé de cada página num documento com 3+ páginas, com uma única leitura do relógio) |
| Datas históricas e horário de verão | `…test_07…`: 15/01/2019 15:00 UTC → 13:00 (UTC−2); início do verão (04/11/2018 02:59 → 03/11 23:59 e 03:00 → 04/11 01:00); fim do verão (17/02/2019 01:59 → 16/02 23:59 e 02:00 → 16/02 23:00, hora repetida); verão abolido (03/11/2019 03:00 → 00:00); 2019 e 2026 → UTC−3 |
| Extras | Instante sem fuso recusado; instantes em outros fusos convertidos; zeros à esquerda; base de fusos do pacote `tzdata`; nenhum deslocamento fixo no código-fonte; **(#36)** metadados do arquivo com o mesmo instante, em três fusos de processo e numa data de horário de verão; formatação numa localidade ASCII (subprocesso); rota com o relógio da requisição injetado via `NEXO_RELOGIO`; gerar o PDF não altera `TZ`, `time.tzname`, `time.timezone` nem `time.altzone` do processo, e o gerador não toca em `os.environ` nem em `os.putenv` (o pedido proíbe alterar o relógio do servidor) |

## G. Testes

Todos os testes rodaram em cópias descartáveis do código, com o mesmo ambiente sintético do CI (`SECRET_KEY` fictícia, SQLite em memória, nenhuma credencial real), pelo usuário sem privilégios `nexotest`. Os logs estão na pasta `testes/` do pacote.

### G.1 Módulos do PDF

| Módulo | Testes | Situação |
|---|---|---|
| `tests/test_pdf_export_layout.py` (novo) | 44 | Geometria lida do PDF real com `pdftotext -bbox-layout`, estrutura dos flowables, cálculo do gráfico, varreduras finas de paginação. |
| `tests/test_pdf_export_horario.py` (novo) | 19 | Seção F, item 10. |
| `tests/test_pdf_export_security.py` (existente, 20 → 22) | 22 | Os 20 testes originais continuam e entraram 2 novos (escape na legenda e no rodapé). |

`python -B -m unittest tests.test_pdf_export_layout tests.test_pdf_export_horario tests.test_pdf_export_security -v` → **`Ran 85 tests … OK`**, sem nenhum teste ignorado (o `pdftotext` está instalado aqui e no CI; log em `testes/14_modulos_pdf_85_testes_em_dbacfa3.log`).

Auxiliares de `tests/pdf_layout_support.py` usados pelas verificações de página:

- `titulo_isolado`: título no fim do corpo da página. O subtítulo do gráfico não conta como conteúdo.
- `pagina_sem_conteudo`: página só com títulos, o subtítulo do gráfico e/ou a frase final.
- `lacunas_evitaveis`: o começo da página seguinte, até o próximo título de seção, cabia no espaço livre da anterior e mesmo assim foi empurrado.
- `grafico_partido`: o título do gráfico numa página sem a nota que fecha o bloco.
- `linhas_visuais`: linhas de tabela e de legenda reconstruídas pela posição das palavras na página, sem depender da ordem de leitura do `pdftotext`.
- `problemas_de_geometria`: texto fora das margens ou da página e sobreposição.

**Os 20 itens pedidos para `tests/test_pdf_export_layout.py`:**

| # | Item | Teste(s) |
|---|---|---|
| 1 | Cabeçalho completo | `test_01_cabecalho_completo_dentro_da_pagina`, `test_barra_topo_declara_o_proprio_tamanho` |
| 2 | Indicadores financeiros | `test_02_indicadores_financeiros` |
| 3 | Valores grandes | `test_03_valores_grandes_cabem_inteiros_nas_celulas` |
| 4 | Curva ABC | `test_04_curva_abc_preservada` (linhas na ordem, pela posição na página), `test_tabela_abc_e_quadro_de_indicadores_ocupam_a_largura_util` (inclui o cabeçalho roxo com texto branco) |
| 5 | Nomes longos | `test_05_nomes_longos_quebram_sem_invadir_a_coluna_da_classe`, `test_textos_gigantes_nao_impedem_a_exportacao`, `test_legenda_tem_altura_limitada` |
| 6 | Gráfico de pizza | `test_06_grafico_abaixo_da_tabela_e_antes_da_sintese`, `test_06_grafico_de_pizza_vetorial_com_os_mesmos_dados_da_tabela` (o gráfico que o documento desenha: 2D, cores da rampa na ordem da tabela e iguais às da legenda), `test_paleta_do_grafico_na_identidade_nexo`, `test_fatia_unica_mostra_100_por_cento_no_centro`, `test_secao_do_grafico_nao_se_parte_e_titulo_viaja_com_o_grafico` (inclui o desenho dentro da própria coluna) |
| 7 | Legenda | `test_07_legenda_e_percentuais_no_documento`, `test_07_legenda_com_cor_nome_classe_faturamento_e_percentual` (corpo mínimo de 8 pt em todas as células) |
| 8 | Percentuais individuais | `test_08_percentuais_individuais_da_referencia` |
| 9 | Outros produtos | `test_09_outros_produtos_so_quando_ha_faturamento_fora_do_top5`, `test_notas_do_grafico_so_quando_se_aplicam` (explicação de "Outros produtos" e do arredondamento só quando se aplicam), `test_devolucoes_fora_da_tabela_sao_explicitadas`, `test_inconsistencias_tratadas_explicitamente`, `test_inconsistencia_soma_maior_que_o_total_e_explicita`, `test_secao_sem_faturamento_positivo_explica_o_motivo` |
| 10 | Síntese executiva | `test_10_sintese_executiva_sem_5w2h_e_com_todos_os_cartoes` |
| 11 | Ausência de "(5W2H)" | `test_11_titulo_da_sintese_sem_5w2h` (e `test_10`) |
| 12 | Devolutiva | `test_12_devolutiva_titulos_juntos_dos_textos_e_estrutura_preservada`, `test_primeiro_paragrafo_longo_comeca_na_mesma_pagina`, `test_conclusao_curta_fica_na_pagina_do_resumo` (texto determinístico de `ai_devolutiva` e conclusões de 1, 4 e 9 frases), `test_titulos_da_devolutiva_nunca_isolados_em_qualquer_altura` (65 documentos) |
| 13 | Rodapé | `test_13_rodape_em_todas_as_paginas`, `test_rodape_mantem_a_referencia_com_razao_social_longa` |
| 14 | Paginação | `test_14_paginacao_sem_titulo_isolado_em_varias_combinacoes` (18 combinações), `test_frase_final_e_titulos_nunca_ficam_sozinhos_numa_pagina` (29 casos), `test_espaco_entre_secoes_some_no_topo_da_pagina`, `test_ultimo_bloco_nao_muda_de_pagina_com_espaco_sobrando`, `test_secoes_do_inicio_nunca_isoladas_no_pe_da_primeira_pagina` (75 documentos). Todos conferem título isolado, página sem conteúdo, lacuna evitável e gráfico partido. |
| 15 | Documentos longos | `test_15_documento_longo_preserva_todo_o_texto_em_ordem`, `test_textos_gigantes_nao_impedem_a_exportacao` (30 mil caracteres de resumo e 8,8 mil de conclusão chegam inteiros) |
| 16 | Caracteres especiais | `test_16_caracteres_especiais_preservados` |
| 17 | Data de geração | `test_17_data_de_geracao_no_fim_do_documento` |
| 18 | Horário de Brasília | `test_18_horario_de_brasilia_no_rodape_e_na_frase_final` (detalhes de fuso em `test_pdf_export_horario.py`) |
| 19 | Exportações em momentos diferentes | `test_19_exportacoes_em_momentos_diferentes` (e `test_04` e o teste da rota em `test_pdf_export_horario.py`) |
| 20 | Integridade das informações | `test_20_integridade_dos_dados_de_entrada_e_dos_valores`, `test_valores_iguais_aos_do_portal`, `test_formatacao_monetaria_e_percentual` |

**Alterações em testes existentes** (em `tests/test_pdf_export_security.py`, por exigência do pedido, sem remover nenhuma verificação):

- "Síntese executiva (5W2H)" passou a "Síntese executiva", com a nova verificação de que "5W2H" não aparece no documento.
- "Resumo executivo." e "Conclusão estratégica." perderam o ponto final, porque agora são subtítulos e não prefixos do parágrafo.
- "Página 1" passou a "Página 1 de " (mais forte).
- Entrou "Distribuição do faturamento por produto" na lista de componentes obrigatórios.
- **(#36)** O teste de escape por campo registrava os textos trocando `pdf_export.Paragraph` por um `MagicMock`. Agora usa uma subclasse de `Paragraph` que registra os mesmos textos, com as mesmas verificações. Com isso saiu do gerador o apelido `_ClasseParagraph`, que só existia para o `isinstance` funcionar sob o `MagicMock`.

Nenhum teste existente foi removido, ignorado ou enfraquecido.

### G.2 Os testes novos detectam os defeitos antigos

Os testes de layout, então 26, rodaram contra o gerador da `main` `7bd383b`, com um adaptador só para aceitar `gerado_em`. Resultado: **36 falhas e 8 erros** (`testes/02_testes_de_layout_contra_o_gerador_antigo.log`), entre elas:

- cabeçalho fora da página (caixas com y < 0);
- faixa com `wrap()` = (0, 0);
- larguras 476 × 493 pt;
- título isolado em 18 de 18 combinações de paginação;
- "Página N" sem total;
- ponto decimal;
- "5W2H";
- ausência do gráfico e da legenda;
- horário sem "(horário de Brasília)";
- ausência do aviso de inconsistência.

Naquela execução, o teste de formatação também apontava "R$ 1,005 → 1,00". Na revisão, essa regra de arredondamento (a do portal) foi mantida de propósito, e o teste passou a comparar com a macro do portal (seção C, item 10).

Na revisão independente, cada mutação dos testes de escape (escape duplo na legenda, escape no canvas do rodapé) foi pega exatamente pelo teste correspondente.

**(#36) Correção da frase final.** Os testes novos e as verificações ampliadas rodaram contra o gerador `4356a4a`, anterior à correção `2774819`: **11 falhas** (`testes/08_testes_novos_contra_4356a4a_11_falhas.log`). Com a correção: 0.

**(#36) Teste de mutação.** A frente de qualidade dos testes montou 58 mutações do gerador e da rota. Entre elas:

- tirar a fatia "Outros" ou as notas do gráfico;
- trocar títulos;
- pizza 3D, cores trocadas, paleta fora da identidade, pizza maior que a coluna;
- tirar `KeepTogether`;
- relógio ingênuo, −3 h fixo, carimbo em cache, metadados no relógio local;
- rota sem checagem de empresa, rota sem `pode_exportar_pdf`, PDF reaproveitado.

Cada mutação foi aplicada sozinha sobre o código final, numa cópia descartável, e os três módulos do PDF rodaram contra o mutante.

- **Resultado: 58 de 58 mutantes falham em pelo menos um teste** (`testes/12_mutacao_58_mutantes.txt`).
- Antes das mudanças desta etapa, 18 passavam pela suíte: os 16 apontados pela revisão e as duas notas do gráfico (explicação de "Outros produtos" e de arredondamento), que a revisão não listou. Cada um ganhou um teste.

### G.3 Estados intermediários dos commits

Cada commit do #35 foi conferido isoladamente: o arquivo compila e o PDF de referência sai sem nenhum problema de geometria.

| Commit | `tests.test_pdf_export_security` | Outros testes |
|---|---|---|
| `94af8e9` | 20/20 OK | — |
| `06784f7` | 20/20 OK | testes do NexoBot (`test_nexobot_saber` + `test_nexobot_conhecimento`): 43/43 OK |
| `80ec8c5` | 20/20 OK | — |
| `bd80d8b` | 20/20 OK | — |
| `3fad8d3`, `3b0bdfd` | 20/20 OK | código final do #35: módulos do PDF 63/63 OK; suíte completa na seção G.4 |

No #36, o estado entre os dois commits de correção (`9ed1711`) foi testado com os módulos do PDF, `test_deploy` e `test_contratos_portal`: 138 testes, OK. Depois, cada commit novo foi conferido isoladamente com os módulos do PDF: `2774819`, 80 testes, OK; `ede054f`, 84 testes, OK, ainda com o apelido de `Paragraph` no gerador; `dbacfa3`, 85 testes, OK.

### G.4 Suíte oficial completa

`python -B -m unittest discover -s tests -t . -v`, com os testes de navegador (Chromium) e os ensaios PostgreSQL descartáveis:

| Estado | Resultado |
|---|---|
| `3b0bdfd` (cabeça do #35) | **882 testes, 2 falhas**: os dois testes de aviso, por causa do logger desativado pelo `fileConfig()` do Alembic (seção I). Corrigido em `4aa3316`. |
| `4356a4a` (#36, antes da correção da frase final) | **895 testes, OK**, em 1.485,8 s (`testes/11_suite_completa_4356a4a_895_testes.log`). |
| `dbacfa3` (#36, código final) | **904 testes, OK**, em 1.401,1 s (`testes/15_suite_completa_dbacfa3_904_testes.log`). Inclui o teste do Pareto, que passou nesta execução. |

Além disso:

- Subconjunto que exercita a rota do PDF e as regras contratuais, com o código do #36: `test_cancelled_company_security`, `test_contratos_portal`, `test_contratos_navegador`, `test_deploy`, os três módulos do NexoBot e `test_supply_chain_install`. Somados aos módulos do PDF, foram **281 testes, OK**, nenhum ignorado.
- Os 47 templates compilam no ambiente Jinja da própria aplicação. Nenhum template foi alterado.

### G.5 Homologação visual (PyMuPDF e `pdftotext`)

A inspeção automática de cada página (PyMuPDF) verifica:

- texto fora da página ou na borda superior;
- sobreposição entre linhas;
- título no fim da página (título e subtítulo do gráfico também contam);
- página só com títulos e/ou a frase final;
- **(#36)** bloco do gráfico partido;
- **(#36)** lacuna evitável: o começo da página seguinte cabia no espaço livre da anterior e foi empurrado;
- desenho fora da página.

A mesma varredura de 265 documentos (13 variantes extremas, 72 de títulos isolados e 180 de paginação), **com o detector final**, nas quatro versões do gerador:

| Versão do gerador | Documentos com problema | Problemas encontrados |
|---|---|---|
| `main` antes do #35 (`7bd383b`) | **265/265** | 530 textos fora da página, 530 na borda superior, 537 sobreposições, 97 títulos isolados, 265 desenhos fora da página, 5 páginas sem conteúdo |
| #35, hoje na `main` (`c6f1299`) | **15/265** | 15 páginas só com título e/ou a frase final |
| cabeça anterior do #36 (`4356a4a`) | **106/265** | 106 lacunas evitáveis: a conclusão curta ou o último bloco empurrado para uma página nova (seção C, item 4) |
| **final do #36 (`dbacfa3`)** | **0/265** | — |

As rodadas anteriores usavam detectores sem as verificações de lacuna evitável e de gráfico partido; a rodada do #35 também não verificava página sem conteúdo. Por isso, a versão anterior deste relatório mostrava 0/265 para o #35 e para o `811f2e5`. Os resumos estão em `inspecao/varredura_final_4_versoes/`.

As 13 variantes extremas são: referência, valores grandes, nomes longos, devolutiva longa, caracteres especiais, soma maior que o total, um produto, sem "Outros", sem indicador, sem relatório, sem curva, produto zerado e muitos cartões.

Além da varredura, as páginas foram renderizadas e **olhadas** (não só geradas): referência, nomes longos, devoluções, sem faturamento positivo, razão social longa, conclusão longa, um produto. As capturas estão na seção H.

### G.6 CI do GitHub (workflow `NEXO Security CI`)

| Execução | Commit | Resultado |
|---|---|---|
| 107 (PR #35, aberto) | `3b0bdfd` | Cancelada pelo próprio workflow (`cancel-in-progress`) quando o PR foi marcado como pronto. |
| 108 (PR #35, pronto) | `3b0bdfd` | `security-postgresql` ok; `security-sqlite-browser` **falhou**: os 2 testes de aviso (seção I). |
| 109 (push na `main`) | `c6f1299` | O mesmo: 2 falhas. |
| 110 (PR #36) | `4aa3316` | Os 2 testes de aviso passaram. A única falha foi `test_overflow_navegador…test_pareto_acompanha_o_redimensionamento` ("360px: Pareto não desenhado"), um teste de navegador do gráfico de Pareto do dashboard. A diferença do PR não toca o dashboard, e o mesmo teste passou nas execuções 108 e 109 e na suíte local completa. |
| 111 (PR #36) | `811f2e5` | Cancelada pelo workflow quando chegou o commit seguinte. |
| 112 (PR #36) | `4356a4a` | **Sucesso nos dois jobs**, inclusive o teste do Pareto. |
| 113 (PR #36) | `09fc3ca` | `security-postgresql` ok. `security-sqlite-browser`: 903 testes, 1 falha, de novo o teste do Pareto ("360px: Pareto não desenhado"). Todos os testes do PDF passaram. A causa foi reproduzida (abaixo). |
| 114 (PR #36) | `dbacfa3` (código final) | **Sucesso nos dois jobs**: `security-sqlite-browser` com 904 testes, OK, e os ensaios PostgreSQL; `security-postgresql` ok. |

**Causa do teste instável do Pareto (fora do PDF, anterior a este trabalho).**

1. Os dados dos testes de navegador publicam todas as análises com a mesma `data_conclusao` (05/02/2026 12:00, em `tests/contratos_support.py`).
2. O dashboard escolhe a análise "mais recente" por `data_conclusao` e desempata por `data_criacao`. Essa coluna vem do `CURRENT_TIMESTAMP` do SQLite, com resolução de 1 segundo.
3. Quando a preparação do teste cruza a virada de um segundo entre a criação da análise principal (a única com Curva ABC) e a das demais, uma análise sem Curva ABC passa a ser a "mais recente". O dashboard então não tem gráfico de Pareto algum.

Reprodução determinística (`testes/13_reproducao_pareto.log`):

- no mesmo segundo, o Pareto aparece;
- com a virada de um segundo forçada, ele não aparece.

A correção proposta tem quatro linhas, só nos dados do teste (`tests/test_overflow_navegador.py`): a análise principal recebe a `data_conclusao` mais recente. Com ela, o Pareto aparece nos dois casos. Ela não foi aplicada neste PR, por estar fora do escopo do PDF; está descrita no comentário do PR #36.

### G.7 Revisão independente (seis frentes)

Depois do #35, uma revisão independente com seis frentes olhou o código e gerou documentos com entradas adversariais. As frentes eram: layout e paginação, cálculo do gráfico e integridade, fuso e cache, segurança, qualidade dos testes e requisitos.

Cada achado aplicável foi **reproduzido** antes da correção e ganhou um teste de regressão. Resumo dos achados e do destino de cada um:

| Frente | Achado | Gravidade | Destino |
|---|---|---|---|
| Layout / segurança | Nomes de produto longos (≥ ~313 caracteres em 5 nomes) derrubavam a exportação com `LayoutError` (HTTP 500), uma regressão em relação à `main` antiga (~3.000) | maior | Corrigido (#36): legenda com até 3 linhas, `splitInRow` na tabela, cartão divisível. Teste com 12 mil caracteres. |
| Layout | Logo abaixo desse limite, título do gráfico sozinho numa página e nota separada | menor | Corrigido junto (altura da legenda limitada); detector de "página sem conteúdo". |
| Layout | Frase final sozinha numa página nova (~3% das combinações) | menor | Corrigido: viaja com as 2 últimas linhas do último parágrafo. |
| Layout | Primeiro parágrafo longo da devolutiva deixava até 59% da página em branco | menor | Corrigido: `CondPageBreak` + parágrafo que quebra. |
| Layout / cálculo | Seção do gráfico sumia sem aviso quando nenhum produto tinha faturamento positivo | menor | Corrigido: a seção explica o motivo. |
| Layout | Rodapé perdia "Referência MM/AAAA" com nome de empresa longo; corte quadrático | menor | Corrigido: só o nome é encurtado, por busca binária. |
| Layout | Valor da legenda não reduzia o corpo (≥ 10¹³) | detalhe | Corrigido. |
| Layout | Espaçador de 7 mm levado para o topo da página | detalhe | Corrigido (`spaceBefore`). |
| Cálculo | Arredondamento `Decimal` no PDF × `float` no portal: números diferentes nos empates (91,85 → 91,9% no PDF e 91,8% na tela) | menor | Corrigido: o PDF segue a regra do portal; teste contra a macro real. |
| Cálculo | Devoluções (faturamento líquido negativo fora da tabela) faziam o gráfico e a Curva ABC usarem bases diferentes sem aviso | menor | Corrigido: aviso explícito, mantendo a fórmula pedida. |
| Cálculo | Mensagens imprecisas (total negativo chamado de "indisponível"; produto inválido chamado de "zero ou negativo") | detalhe | Corrigido. |
| Cálculo | Produto excluído do Top 5 somado a "Outros" | detalhe | Corrigido: a base passa a ser a soma dos exibidos, com aviso. |
| Cálculo | Tolerância de meio centavo gerava artefatos na fronteira | detalhe | Corrigido: comparação pelo valor exibido. |
| Cálculo / segurança | O log de inconsistência gravava valores comerciais e não tinha o id da análise | detalhe | Corrigido: só o id e o código. |
| Fuso | `tzdata` só transitivo; sem base do sistema, toda exportação daria 500 | menor | Corrigido: `tzdata==2026.5` declarado; o teste deixa de ser ignorado. |
| Fuso | Metadados `CreationDate`/`ModDate` no fuso do servidor, errados em fusos de meia hora | detalhe | Corrigido: mesmo instante do carimbo. |
| Fuso | "às" dentro do `strftime` falhava com localidade ASCII sem UTF-8 | detalhe | Corrigido (teste em subprocesso). |
| Fuso | Segundo relógio em vez do relógio único `contract_policy.agora()` | detalhe | Corrigido na rota. |
| Fuso | `notifications.py` (sino em tempo real) e a data de publicação no histórico ainda usam horário do servidor (UTC) | detalhe, anterior a este trabalho | **Não alterado** (fora do fluxo do PDF); registrado na seção J. |
| Segurança | O escape único nos dois lugares novos (legenda, rodapé) não estava fixado por teste | menor | Corrigido: 2 testes novos, validados por mutação. |
| Segurança | `_brl` com `Decimal` levantava erro para valores ≥ 10²⁶ | detalhe | Corrigido (formatação igual à do portal). |
| Requisitos | A frase final aninhava um `KeepTogether` em outro quando o último bloco já era indivisível. Conclusão de um parágrafo (o formato da IA), último cartão, gráfico ou "Sem texto registrado" iam sozinhos para uma página nova e a anterior ficava com metade ou mais em branco. Regressão do próprio #36 (`9ed1711`), nunca integrada à `main`. | bloqueante | Corrigido (`2774819`): a frase final entra no mesmo bloco (seção C, item 4). Na varredura de 265 documentos: 106 com o defeito no `4356a4a`, 0 depois. Testes novos: 11 falhas contra o código anterior, 0 depois (seção G.2). |
| Requisitos | Emoji no texto do consultor saem como ■ (fonte Helvetica padrão do PDF) | detalhe, anterior a este trabalho (o gerador de `7bd383b` faz o mesmo) | **Não alterado**: exige embutir uma fonte TTF. Registrado na seção J. |
| Qualidade dos testes | 16 mutantes do gerador passavam pela suíte: bloco do gráfico partido (título e subtítulo no pé da página), pizza 3D, cores da pizza diferentes das da legenda, paleta fora da identidade, gráfico em outra ordem, cabeçalho da ABC sem roxo, `KeepTogether` removido da ABC, dos indicadores ou da devolutiva, texto do consultor cortado em 20 mil caracteres, legenda em 6 ou 7 pt, fuso global do processo alterado, pizza maior que a coluna ou deslocada sobre a legenda | maior (4), menor (3), detalhe (1) | Corrigido (`ede054f`): um teste para cada caso (seção G.1, itens 4 a 7, 12, 14, 15 e 18). A verificação por mutação está na seção G.2. |
| Qualidade dos testes | Linhas de tabela e de legenda conferidas na ordem de leitura do `pdftotext`, que muda com o layout | menor | Corrigido: `linhas_visuais` reconstrói as linhas pela posição das palavras. |
| Qualidade dos testes | `assertNoLogs` que não podia falhar na suíte completa (logger desativado pelo Alembic) | menor | Corrigido: o teste reativa o logger. |
| Qualidade dos testes | Testes trocavam `Paragraph` por `MagicMock`, o que obrigou um apelido no código de produção | detalhe | Corrigido: subclasse que registra os textos; apelido removido (`09fc3ca`). |
| Qualidade dos testes | O teste do espaço entre seções passaria sem verificar nada se o documento tivesse uma página só | detalhe | Corrigido: exige uma segunda página aberta por título de seção. |

**Verificação adversarial.** As seis frentes somaram 39 achados: 1 bloqueante, 5 maiores, 15 menores e 18 detalhes. Cada achado foi reexaminado por um verificador independente, instruído a tentar refutá-lo e a dizer se a correção já estava no código atual. Resultado:

- **38 confirmados e 1 refutado.** O refutado é o erro de localidade com o "às" no `strftime`: o verificador não o reproduziu. A mudança feita para ele é inofensiva e foi mantida.
- Os verificadores conferiram cada correção no código da cabeça do PR. Nos 12 achados de qualidade dos testes e no bloqueante de requisitos, confirmaram que a correção está em `ede054f` e `2774819`.
- Restaram só observações sem efeito prático:
  - com devoluções, "Outros produtos" continua com o valor líquido, o que o aviso explica;
  - valores abaixo de um centavo podem dar participação acima de 100% (seção J, item 9).

Os textos completos dos revisores e dos verificadores estão em `revisao_independente/achados_brutos.md`.

Sem achado em: autorização e ordem das verificações na rota; escape de todos os demais textos; ausência de links, imagens e recursos externos; cache (`no-store` é suficiente: sem Flask-Caching, sem *service worker*, sem `ETag`); conversão de fuso em 200.204 instantes; integridade das entradas (cópia profunda antes e depois).

## H. Evidências

Pacote `NEXO_PDF_CORRECAO_COMPLETA_HORARIO_BRASILIA.zip`. Ele fica no ambiente desta sessão, fora do repositório, e foi entregue ao proprietário junto com este relatório. O caminho real está na mensagem de entrega.

Estrutura:

| Pasta / arquivo | Conteúdo |
|---|---|
| `RELATORIO_PDF_GRAFICO_ABC_HORARIO_BRASILIA_PARA_CHATGPT.md` | Este relatório. |
| `LEIA-ME.md` | Índice do pacote e como reproduzir. |
| `pdf/analise_nexo_202606_5_CORRIGIDA_COMPLETA.pdf` | PDF final, gerado pelo código final do #36 (`dbacfa3`) com o relógio real e o processo em UTC. **Dados sintéticos** (empresa "Empresa Demonstração — DADOS SINTÉTICOS", título "(dados sintéticos)"). |
| `pdf/analise_nexo_202606_5_ANTES_reproducao.pdf` | O mesmo conteúdo gerado pelo código da `main` `7bd383b` (reprodução dos defeitos). |
| `capturas/01_*` a `06_*` | Cabeçalho e indicadores (antes e depois), tabela da Curva ABC, gráfico de pizza com legenda, síntese executiva, devolutiva, data de geração (frase final e rodapé). |
| `capturas/07_*`, `08_*` | Páginas completas depois e antes. |
| `capturas/09_*` | Comparativo lado a lado, antes × depois, por página. |
| `capturas/casos/` | Casos de borda (PDF e páginas renderizadas): nomes longos, devoluções fora da tabela, sem faturamento positivo, razão social longa, conclusão longa, soma maior que o total e conclusão de um parágrafo (caso 7: antes, com `4356a4a`, 3 páginas e a conclusão sozinha; depois, 2 páginas). |
| `horario/` | Ensaio antes × depois em 5 fusos de processo; horário real da geração do PDF final; script do ensaio. |
| `inspecao/` | Inspeções antes e depois. `varredura_final_4_versoes/`: resumos da varredura de 265 documentos com o detector final, em quatro versões do gerador. As rodadas anteriores, com o detector da época, ficam em `varredura_final/` e `varredura_pos_merge_35/`. |
| `testes/` | Logs: módulos do PDF, validade contra o gerador antigo e contra `4356a4a`, estados intermediários, suítes completas, subconjunto de rota e contratos, teste de mutação (58 mutantes) e reprodução do teste instável do Pareto. |
| `alteracoes/` | Lista de commits, estatística, diff completo desde `7bd383b` e arquivos alterados. |
| `revisao_independente/` | Achados das seis frentes, com reprodução, e os vereditos da verificação adversarial de cada achado. O destino de cada um está na seção G.7. |
| `scripts/` | Geração dos dados sintéticos, do PDF final, das capturas, das variantes, da inspeção e dos estados intermediários dos commits. |

## I. GitHub

| Item | Valor |
|---|---|
| Branch | `claude/awesome-pascal-0ho42m` (sem force push; todos os pushes foram *fast-forward*) |
| PR #35 | [Helio965/Nexo---Faturamento-Inteligente---Render#35](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/35). Seis commits, na ordem sugerida: `94af8e9 fix(pdf): corrigir cabecalho e paginacao`, `06784f7 feat(pdf): adicionar grafico de pizza da Curva ABC`, `80ec8c5 fix(pdf): melhorar legenda e apresentacao dos produtos`, `bd80d8b refactor(pdf): remover 5W2H do titulo da sintese`, `3fad8d3 fix(pdf): padronizar horario de geracao para Brasilia`, `3b0bdfd test(pdf): validar fuso horario e integridade dos documentos`. Aberto como rascunho; marcado como pronto e integrado pelo proprietário (`c6f1299`, 13:37 UTC). |
| PR #36 | [Helio965/Nexo---Faturamento-Inteligente---Render#36](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/36) (rascunho), na ordem: `4aa3316 test(pdf): reativar o logger do gerador nos testes de aviso`, `9ed1711 fix(pdf): correcoes da revisao independente (paginacao, legenda, valores e avisos)`, `811f2e5 fix(pdf): metadados, localidade e relogio unico no horario de geracao`, `c7ef8c4 test(pdf): itens 18 e 19 explicitos no teste de layout`, `4356a4a docs(pdf): registrar auditoria e evidencias`, `2774819 fix(pdf): frase final sem KeepTogether aninhado`, `ede054f test(pdf): fortalecer os testes do PDF (revisao da qualidade dos testes)`, `09fc3ca refactor(pdf): remover o apelido de Paragraph criado para os testes`, `dbacfa3 test(pdf): notas do grafico so quando se aplicam` e o commit `docs(pdf): …` com esta versão do relatório. |
| Por que a `main` ficou vermelha depois do #35 | Na suíte completa, os testes que aplicam as migrations passam por `migrations/env.py`. Ali, `fileConfig()` do Alembic desativa os loggers já criados (`disable_existing_loggers=True`), entre eles o `pdf_export`. Daí em diante, os dois testes que conferem o aviso com `assertLogs` falham. Isolados, passavam. O gerador não muda: o processo web (`gunicorn wsgi:app`) não executa migrations. A correção, em `4aa3316`, reativa o logger durante esses testes, como `tests/test_nexobot_saber.py` já fazia. Reprodução mínima e correção estão registradas no PR #36. |
| Merge, deploy | **Nenhum merge feito por mim, nenhum deploy, nenhuma alteração no Render ou no Supabase.** |

## J. Pendências

1. **Documento de referência.** `analise_nexo_202606_5 (3).pdf` não estava disponível; a reprodução usou dados sintéticos com os mesmos valores. Depois do deploy, exportar a análise 06/2026 #5 de novo e conferir com o original.
2. **Deploy.** O código precisa ser publicado no Render para valer em produção. O `render.yaml` versionado desliga o deploy automático (`autoDeployTrigger: 'off'`); o estado efetivo só se confirma no painel. Na publicação, o `pip install -r requirements.txt` instala o `tzdata` 2026.5, que já é a versão em uso hoje.
3. **"Duas horas de diferença".** Com o código antigo, a diferença reproduzida é de exatamente 3 horas, com o servidor em UTC. As 2 horas relatadas não foram reproduzidas; as hipóteses estão na seção B. Depois do deploy, o horário independe do servidor.
4. **CI: teste do Pareto do dashboard.** `test_pareto_acompanha_o_redimensionamento` falhou nas execuções 110 (`4aa3316`) e 113 (`09fc3ca`) e passou nas demais.
   - A causa está nos dados do teste e foi reproduzida (seção G.6): análises publicadas com a mesma `data_conclusao` e desempate por um carimbo de 1 segundo.
   - Não tem relação com o PDF e não é defeito do produto: em produção, a `data_conclusao` de cada publicação tem o instante real.
   - A correção proposta tem quatro linhas no módulo de testes de navegador. Até ser aplicada, o job de navegador pode falhar de forma intermitente neste e noutros PRs.
5. **Fora do fluxo do PDF (não alterado, por escopo).**
   - O payload em tempo real das notificações (`notifications.py`, `datetime.now()` ingênuo) mostra no sino um horário 3 h à frente de Brasília.
   - A data de publicação no histórico (`templates/cliente/historico.html`) usa o valor UTC gravado, então publicações entre 21:00 e 23:59 de Brasília aparecem com o dia seguinte.
   - `contract_policy.formatar_instante` também põe "às" dentro do `strftime`.
   - O subtítulo da página web da análise ainda cita "(5W2H)" (`templates/cliente/analise.html`).
   - O texto determinístico da devolutiva (`ai_devolutiva._gerar_fallback`, usado quando a IA não responde) escreve o percentual do produto líder com ponto decimal ("74.23% do total"). O PDF reproduz o texto exatamente como foi gravado e não o corrige.

   Tudo isso pode ser corrigido na exibição ou na geração do texto, sem mexer nos dados gravados. Fica como sugestão de tarefa separada.
6. **Metadados.** "Creator" e "Subject" do PDF continuam "(unspecified)", padrão do ReportLab e igual à versão anterior. É só cosmético.
7. **`tzdata` fixado em 2026.5.** Acompanhar as versões novas, como os demais pacotes fixados. Quando o servidor tem `/usr/share/zoneinfo`, o `zoneinfo` usa primeiro a base do sistema.
8. **Emoji no texto do consultor.** O PDF usa a Helvetica padrão do ReportLab. Caracteres fora da codificação dela, como emoji, saem como "■"; acentos, "≥", "✓", "−", "€", "™" e "½" saem corretos. O gerador anterior (`7bd383b`) fazia o mesmo. Resolver exige embutir uma fonte TTF de cobertura ampla, mudança que vale como tarefa separada.
9. **Casos extremos de cálculo sem efeito prático.** Com valores abaixo de um centavo (por exemplo, total de R$ 0,01 e produto de R$ 0,014), a participação pode passar de 100%. O ETL grava os valores com duas casas, então isso não ocorre com dados reais; por isso não foi alterado.

**Parecer.** As correções pedidas estão implementadas e foram verificadas por teste, por inspeção automática da geometria e por inspeção visual das páginas:

- cabeçalho, margens e paginação;
- gráfico de pizza com legenda e "Outros produtos";
- "Síntese executiva" sem "(5W2H)";
- devolutiva preservada;
- horário de Brasília independente do servidor.

A revisão independente achou uma regressão do próprio #36: a conclusão curta ia sozinha para uma página nova. Ela foi corrigida em `2774819`, antes de qualquer integração. A revisão achou também doze lacunas nos testes, que foram fechadas e conferidas por mutação (58 de 58 mutantes pegos).

No código final (`dbacfa3`):

- a varredura de 265 documentos não aponta nenhum problema;
- os 85 testes dos módulos do PDF passam;
- o CI passou nos dois jobs (execução 114).

O #35 já está na `main`; o #36 deve ser integrado antes do deploy. O teste instável do Pareto do dashboard não tem relação com o PDF: a causa foi reproduzida e há uma correção proposta no PR. Nada foi publicado no Render nem alterado no Supabase.
