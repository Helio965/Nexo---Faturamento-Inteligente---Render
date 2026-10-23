# NexoBot Advanced

Assistente de navegação e suporte do portal do cliente NEXO. Entende mensagens em português do Brasil escritas de formas diferentes, usa o contexto curto da conversa, consulta o Guia cadastrado no CMS e abre somente páginas de um catálogo fechado. Funciona por completo sem serviços externos de IA.

O NexoBot não executa operações: não envia arquivos, não exclui, não publica, não altera senhas ou cadastros e não cria chamados. Ele orienta e, quando o pedido é inequívoco, abre uma página do portal do cliente.

A geração de devolutivas com Claude/Anthropic (`ai_devolutiva.py`) é uma funcionalidade separada e não passa por este código.

## 1. Arquitetura

```
mensagem ──► A. normalizacao ──► B. classificacao ──► E. servico ──► JSON
                                   ▲        │             │  ▲
                        D. contexto┘        │             │  └─ providers (opcional, só redação)
                                            ▼             ▼
                                     navegacao      C. conhecimento (Guia + fatos)
                                   (catálogo fechado)
```

| Camada | Módulo | Responsabilidade |
| --- | --- | --- |
| A. Normalização | `nexobot/normalizacao.py` | Unicode NFKC, remoção de caracteres invisíveis e de controle, acentos, abreviações de chat (`vc`, `pq`, `pra`), repetições (`oiiii`), risadas, emojis, limite de 1000 caracteres e 220 tokens, aspas (comandos citados), interrogação, distinção entre `é` (verbo) e `e` (conjunção). Corrige erros de digitação **somente em direção ao vocabulário do domínio**, com distância de edição limitada e sem chute em empates. |
| B. Classificação | `nexobot/classificacao.py` | Segmenta a mensagem em orações, identifica o ato de fala de cada uma (ordem, pedido polido, desejo, pergunta, negação, relato de problema, operação, citação, cortesia) e o alvo de cada ordem. Registra evidências por intenção e resolve conflitos com regras explícitas e ordenadas. |
| C. Conhecimento | `nexobot/conhecimento.py`, `similaridade.py`, `portal.py` | BM25F sobre os tópicos **ativos** do `GuiaTopico` (título, categoria e resposta com pesos distintos), sinônimos, aproximação ortográfica e calibração de confiança. Fatos da interface (`portal.py`) respondem apenas quando o Guia não tem orientação confiável. |
| D. Contexto | `nexobot/contexto.py` | Memória mínima da conversa, mantida pelo widget e revalidada a cada requisição. |
| E. Decisão | `nexobot/servico.py` | Escolhe a resposta e monta a única ação possível (`navegar` ou `sugerir_navegacao`) a partir do catálogo, com URL gerada por `url_for()`. |
| Apoio | `navegacao.py`, `seguranca.py`, `respostas.py`, `providers.py`, `lexico.py`, `intencoes.py` | Catálogo de destinos; detectores de URL, área administrativa, injeção e código; textos de resposta; integração opcional com IA; léxico; tipos. |

`suporte_bot.py` continua sendo a fachada usada pela API (`responder`).

### Intenções

`navegar`, `orientacao_navegacao`, `duvida_funcional`, `consulta_dados`, `suporte_humano`, `sobre_o_bot`, `ambiguidade`, `comando_negado`, `operacao_nao_permitida`, `acesso_restrito`, `pagina_inexistente`, `pagina_atual`, `fora_do_escopo`, `entrada_suspeita`, `saudacao`, `despedida`, `ajuda_geral`, `confirmacao`, `recusa`, `vazia`, `sem_texto` e `desconhecida`.

Ordem de resolução de conflitos: segurança (URL, área administrativa, injeção, código, dados de outras empresas) > comando citado/hipótese > operação proibida > pedido de valores > negação > ordem de navegação > assunto externo > confirmação/escolha > pedido de atendimento humano > ajuda > pergunta/tarefa/tópico > cortesia > desconhecida.

### Regras de navegação

| Regra | Exemplo | Comportamento |
| --- | --- | --- |
| Ordem explícita | "Abra meu histórico." | Navega, sem confirmação intermediária. |
| Pergunta | "Onde fica meu histórico?" | Explica e oferece botão; não sai da página. |
| Contexto | "Me leve para aquela página." | Navega só se houver destino válido na conversa atual. |
| Negação | "Não quero abrir o dashboard." | Nunca navega. |
| Comando citado | "Se eu escrever abra o dashboard, o sistema vai funcionar?" | Explica como o bot funciona. |
| Múltiplos destinos | "Abra o histórico ou o dashboard." | Pede esclarecimento com botões de escolha. |
| Operação proibida | "Apague meus relatórios e abra o dashboard." | Recusa a operação explicitamente e oferece a página como botão. |
| Página inexistente | "Abra a página de investimentos." | Informa que não é um destino disponível e lista os válidos. |
| Página atual | "Abra o histórico" estando no Histórico | Informa e não recarrega. |
| Segurança | links, `javascript:`, caminhos, área administrativa | Bloqueia; nunca usa texto da mensagem como URL. |

Uma ordem só navega quando a página é **nomeada** ("histórico", "área de suporte", "página de envio de arquivos"). Assuntos apenas relacionados ("a parte que tem as compras", "a tela em que vejo meus dados") viram sugestão com botão.

### Catálogo fechado

| Chave | Endpoint | Rótulo |
| --- | --- | --- |
| `dashboard` | `cliente.dashboard` | Visão Geral |
| `upload` | `cliente.upload` | Enviar Relatórios |
| `historico` | `cliente.historico` | Histórico de Análises |
| `guia` | `cliente.guia` | Guia |
| `suporte` | `cliente.tickets` | Suporte (lista e formulário; não cria chamado) |

Para acrescentar uma página: crie a rota GET com as permissões adequadas, acrescente o `Destino` e seus padrões em `nexobot/navegacao.py` e testes de navegação e de bloqueio. Tópicos do Guia nunca criam destinos.

## 2. Contrato de `POST /api/suporte-bot`

Entrada (JSON, até 16 KB):

```json
{"mensagem": "me leva pra lá",
 "contexto": {"ultimo_destino": "historico", "destino_anterior": "upload",
              "opcoes": [], "modo_opcoes": null, "oferta": "historico"},
 "pagina_atual": "dashboard"}
```

`mensagem` é obrigatória como texto (`null` vira mensagem vazia). `contexto`, `pagina_atual` e o formato legado `ultimo_destino` são opcionais; qualquer valor fora do catálogo é descartado.

Saída (campos novos marcados com *):

| Campo | Descrição |
| --- | --- |
| `resposta` | Texto exibido como texto puro (o widget só interpreta `**negrito**` e quebras de linha). Em navegação direta: "Abrindo …". |
| `fonte` | `local` ou `hf`. |
| `acao` | `null`, `navegar` ou `sugerir_navegacao`. |
| `destino` | Chave do catálogo ou `null`. |
| `url` | Presente apenas com `acao`; vem de `url_for()`. |
| `rotulo_botao` | Presente em `sugerir_navegacao`. |
| `opcoes`* | Botões de escolha em esclarecimentos: `[{destino, url, rotulo_botao}]`. |
| `contexto`* | Contexto que o widget deve reenviar na próxima mensagem. |
| `meta`* | `intencao`, `confianca` (0–1), `origem` (`guia`, `portal`, `catalogo`, `sistema`, `ia`), `motivo`, `correlacao` (id para cruzar com o log) e `degradado` quando o Guia não pôde ser lido. |

Códigos: 200 (inclui mensagens desconhecidas), 400 (JSON malformado, tipo errado, CSRF ausente/inválido — sempre em JSON), 302 (sem sessão, primeiro acesso, conta desativada, sessão de outro boot), 403 (ADMIN), 413 (corpo grande), 429 (30 mensagens/minuto por usuário, em JSON), 500 (falha inesperada, registrada com traceback e `correlacao`). As respostas levam `Cache-Control: no-store` e `X-Content-Type-Options: nosniff`.

### Diferenças em relação ao NexoBot do repositório original

- Navegação direta devolve `resposta` curta ("Abrindo Histórico de Análises…") em vez de vazio.
- Pedidos que misturam operação proibida e página recusam a operação e oferecem a página como botão, em vez de não oferecer nada.
- Campos adicionais `contexto`, `meta` e `opcoes`. O widget anterior ignoraria esses campos.
- Erros 400 mantêm `erro` (contrato do Render) e acrescentam `resposta`.

## 3. Contexto da conversa

O servidor não guarda estado de conversa. O widget mantém, na memória da aba, apenas chaves do catálogo e as reenvia. Consequências: isolamento por usuário, sessão e aba; nada persiste após recarregar a página; um contexto adulterado não pode apontar para fora do catálogo.

- `ultimo_destino`: assunto/página da conversa. Usado por "me leva pra lá", "pode abrir?", "onde vejo?", "como faço?".
- `destino_anterior`: usado por "volta para a anterior". "Análises anteriores" continua sendo o Histórico.
- `oferta`: definido somente quando a resposta terminou com um convite e botão. Um "sim"/"pode"/"ok" só navega se vier logo depois de um convite; cortesias ("obrigado") encerram o convite, mas mantêm o assunto.
- `opcoes` e `modo_opcoes`: respostas como "o segundo", "o histórico" ou "quero enviar um novo" escolhem entre as opções oferecidas. Em `navegar`, a escolha abre a página; em `orientar`, explica e oferece botão.
- Um destino nomeado na mensagem sempre prevalece sobre o contexto. Assuntos não relacionados limpam o contexto.

## 4. Base de conhecimento (Guia)

- Fonte autorizada: tabela `guia_topico` (sem migrations novas). Somente tópicos `ativo = true` entram no índice.
- Cache por aplicação Flask. Inserção, edição, desativação, exclusão e operações em massa sobre `GuiaTopico` feitas pelo ORM invalidam o índice no commit (eventos do SQLAlchemy). Rollback não invalida. Alterações fora do ORM ou de outro processo são refletidas em até 60 s (TTL). Com o `render.yaml` atual (1 worker), alterações pelo CMS valem na mensagem seguinte.
- Confiança calibrada: cobertura da pergunta ponderada por IDF, reduzida quando só sinônimos casam, quando o assunto não aparece no título do tópico ou quando apenas uma palavra específica coincide. Abaixo de 0,45 nada é apresentado; entre 0,45 e 0,6 a resposta é sinalizada ("Encontrei esta orientação, que parece ser…"). Tópicos quase empatados geram pergunta de esclarecimento.
- Fatos do portal (`nexobot/portal.py`): status de processamento, planilha errada, por que compras e vendas, publicação, análises anteriores, Indicador de Pressão de Estoque, Curva ABC, notificações, acesso ao portal, chamados e conta suspensa. Cada fato cita o arquivo de origem no código. O Guia tem prioridade; um fato só o supera quando é claramente mais específico.
- O conteúdo dos tópicos é tratado como dado: não é interpretado como instrução, não define URLs e só aponta para destinos do catálogo.
- Falha de banco ao ler o Guia: rollback, aviso no log (somente o tipo do erro) e resposta indicando que o Guia não pôde ser consultado; a navegação continua funcionando.

## 5. Integração opcional com IA

Verificação feita em 21/10/2026 na documentação oficial da Hugging Face:

- O endpoint usado antes (`api-inference.huggingface.co/models/<modelo>`) foi substituído pelo roteador `https://router.huggingface.co/v1/chat/completions` (compatível com OpenAI), com token fine-grained com a permissão “Make calls to Inference Providers”.
- Contas gratuitas não têm créditos mensais incluídos; o uso é cobrado por consumo.
- O modelo padrão anterior (`mistralai/Mistral-7B-Instruct-v0.3`) aparecia sem provedor ativo na API pública do Hub; o padrão passou a `meta-llama/Llama-3.1-8B-Instruct` (provedores ativos nessa data). Configurável por `HF_MODEL`.

Uso restrito: com `HF_API_TOKEN` definido, o modelo apenas **redige** a resposta de perguntas funcionais a partir de até três trechos do Guia já escolhidos localmente. Não é consultado para navegação, operações, segurança, saudações ou assuntos externos. A pergunta enviada tem e-mails, telefones, documentos, valores, números longos e senhas explícitas removidos. Tempo limite de 3 s para conectar e 10 s para ler; sem redirecionamentos.

A saída é descartada (com uso da resposta local) se estiver vazia, longa demais, contiver links, caminhos, HTML, código, termos financeiros proibidos (margem, lucro, CMV, rentabilidade, prejuízo), alegação de ter executado ações, eco de instruções ou números que não aparecem nos trechos. O modelo nunca define `acao`, `destino` ou `url`.

## 6. Entradas inesperadas

| Entrada | Comportamento |
| --- | --- |
| Vazia, só espaços, `null` | 200 com convite para escrever a dúvida. |
| Só emojis, símbolos ou risadas | 200 pedindo uma frase. |
| Erros de digitação | Corrigidos para termos do domínio (`uplod`, `dashbord`, `chamdos`, `hsitorico`), sem corrigir palavras comuns. |
| Frases longas | Truncadas em 1000 caracteres; corpo HTTP acima de 16 KB recebe 413. |
| Várias perguntas | Até duas são respondidas na mesma mensagem. |
| Contraditórias ("abra o dashboard, não o histórico") | Cada oração é analisada; o destino negado é excluído. |
| JSON malformado, tipos errados, arrays, objetos | 400 em JSON, sem chamar o motor. |
| Contexto inválido | Descartado; nunca define destino. |
| URLs, `javascript:`, `data:`, caminhos, IPs | Bloqueados (`acesso_restrito`). |
| HTML/JavaScript, SQL, Python, comandos de shell | `entrada_suspeita`; nada é executado. O texto é sempre exibido como texto. |
| Injeção de prompt ("ignore as instruções…") | `entrada_suspeita`; regras inalteradas. |
| Dados de outras empresas | Recusa; o bot não tem acesso a dados de empresas. |
| Assuntos externos, poemas, investimentos | Explica o escopo. |
| IA indisponível, sem token, timeout, 401/402/429/5xx, JSON inválido, conteúdo vazio | Resposta local; aviso no log. |
| Guia vazio | Fatos do portal e orientação por página. |
| Falha inesperada de programação | 500 com `correlacao`; traceback no log sem a mensagem do cliente. |

## 7. Segurança

Preservados sem alteração: Flask-Login, perfis ADMIN/CLIENTE (ADMIN recebe 403), CSRF (token no cabeçalho `X-CSRFToken`), primeiro acesso, invalidação por `boot_id`, conta desativada, isolamento por empresa (o bot não consulta dados de empresas), configurações de produção do Render e armazenamento no Supabase.

Acrescentados: limite de 30 mensagens/minuto por usuário; respostas JSON para CSRF e 429 em `/api/`; limite de corpo; `no-store` e `nosniff`; widget sem `innerHTML` (texto via `createTextNode`); ações aceitas pelo navegador apenas se destino e URL coincidirem exatamente com o catálogo renderizado pelo servidor e forem da mesma origem; contexto restrito a chaves do catálogo; logs sem o texto das mensagens.

Observação de auditoria (não alterada, por ser regra de negócio): no Render, clientes de empresas `CANCELADA` continuam podendo entrar no portal; o repositório original bloqueia esse login. O NexoBot segue as mesmas permissões das páginas do cliente.

## 8. Testes

```bash
python -m unittest discover -s tests -p "test_*.py" -v          # suíte completa
python -m unittest discover -s tests -p "test_nexobot*.py" -v   # somente NexoBot
```

| Arquivo | Conteúdo |
| --- | --- |
| `tests/nexobot_corpus.py` | Corpus de frases por comportamento esperado, com variações que não aparecem no código. |
| `test_nexobot_linguagem.py` | Normalização, corpus de intenções, as dez regras de navegação e contexto. |
| `test_nexobot_conhecimento.py` | Precisão e recusa da busca, ambiguidade, prioridade do Guia, base grande, cache (ORM, operações em massa, rollback, TTL, CMS do administrador) e falha de banco. |
| `test_nexobot_api.py` | Contrato HTTP, conversas com contexto, autenticação, CSRF, JSON inválido, 413, 429, isolamento entre usuários, ausência de efeitos nos dados, IA simulada (falhas e saídas inseguras) e concorrência. |
| `test_nexobot_regressao_original.py` | Todos os cenários de `tests/test_nexobot.py` do repositório original, no contrato atual. |
| `test_nexobot_robustez.py` | Fuzzing determinístico (3000 entradas), mutações com erros de digitação (precisão obrigatória: nunca navegar para destino diferente) e fuzzing da API. |
| `test_nexobot_desempenho.py` | Latência e memória medidas. |
| `test_nexobot_interface.py` | Verificações estáticas do widget (sem APIs que interpretam HTML, validação de ações, ARIA, CSS). |
| `test_nexobot_navegador.py` | Chromium real via Playwright (opcional; ver abaixo). |

Os testes de navegador exigem Playwright, que não faz parte de `requirements.txt`:

```bash
python -I tools/install_dependencies.py --requirements requirements-dev.txt
python -m playwright install chromium
NEXO_TEST_BROWSER=1 python -m unittest tests.test_nexobot_navegador -v
# ou, com um Chromium já instalado: NEXO_TEST_CHROMIUM=/caminho/do/chrome
```

Variáveis do fuzzing: `NEXOBOT_FUZZ_SEED`, `NEXOBOT_FUZZ_N`, `NEXOBOT_FUZZ_API_N`.

## 9. Desempenho medido

Ambiente da medição: contêiner Linux com 4 vCPU Intel Xeon 2,1 GHz, 16 GB de RAM, Python 3.12, SQLite temporário, cliente de teste do Flask (sem rede). O plano gratuito do Render tem 0,1 CPU: espere tempos proporcionalmente maiores.

| Medida | Resultado |
| --- | --- |
| Classificação local (985 amostras) | p50 0,10 ms · p95 0,19 ms · máx. 0,34 ms |
| Resposta completa com Guia em cache (591 amostras) | p50 0,20 ms · p95 1,34 ms · máx. 3,44 ms |
| HTTP ponta a ponta no cliente de teste (60 amostras) | p50 ≈ 1,6–2,0 ms · p95 ≈ 1,8–2,4 ms |
| Mensagem de 1000 caracteres | média 4,2 ms |
| Reconstrução do índice (Guia do seed + fatos) | média 2,1–2,9 ms |
| Memória após 3000 mensagens únicas | +1,15 MB (caches LRU com tamanho máximo) |
| Cobertura com erros de digitação (seis sementes, 480 variantes cada) | 94,8 % a 96,7 % navegam corretamente; 0 navegações para destino errado |

Sem IA externa, nenhuma mensagem gera chamada de rede. O índice do Guia é reconstruído só quando o Guia muda ou o TTL expira.

## 10. Limitações conhecidas

- O reconhecimento é baseado em regras linguísticas, léxico e recuperação lexical (BM25 com sinônimos). Não há modelo semântico local: paráfrases muito distantes do vocabulário do portal podem pedir reformulação. Busca por embeddings foi considerada e não implementada: exigiria dependências pesadas (modelo e runtime de inferência) e memória além do orçamento do plano gratuito do Render, e não houve medição que demonstrasse ganho neste domínio pequeno.
- Erros de digitação em palavras curtas (até 3 letras) e combinações de vários erros na mesma palavra podem não ser corrigidos. Nesses casos o bot pede esclarecimento; não navega.
- Construções sintáticas raras (ordens no meio de orações longas, ironia, duplas negações) tendem a resultar em esclarecimento, por desenho.
- O limite de 30 mensagens/minuto usa o armazenamento do Flask-Limiter configurado (`memory://` por padrão): em várias instâncias, configure `RATELIMIT_STORAGE_URI` compartilhado.
- O contexto vive na memória da aba: recarregar a página ou navegar recomeça a conversa.
- A redação por IA não foi testada contra o serviço real (sem token neste ambiente); o contrato do roteador foi seguido conforme a documentação oficial e todos os modos de falha foram simulados.
- Os fatos do portal descrevem o comportamento atual do código; mudanças nas telas exigem atualizar `nexobot/portal.py`.

## 11. Manutenção

- Novo sinônimo de busca: `GRUPOS_SINONIMOS` em `nexobot/lexico.py`.
- Nova forma de pedir uma página: padrão em `_PADROES` de `nexobot/navegacao.py` (FORTE só se nomear a página).
- Palavra sendo "corrigida" indevidamente: inclua em `PALAVRAS_COMUNS`.
- Novo verbo de operação proibida: `VERBOS_OPERACAO` em `nexobot/lexico.py` e `_OPERACOES` em `nexobot/respostas.py`.
- Calibração da busca: `LIMIAR_ALTO`, `LIMIAR_MEDIO`, `MARGEM_AMBIGUIDADE` e `VANTAGEM_FATO` em `nexobot/conhecimento.py`, sempre com os testes de `test_nexobot_conhecimento.py`.
- Toda mudança deve manter a propriedade testada em `test_nexobot_robustez.py`: nenhuma variação de uma ordem pode navegar para um destino diferente.
