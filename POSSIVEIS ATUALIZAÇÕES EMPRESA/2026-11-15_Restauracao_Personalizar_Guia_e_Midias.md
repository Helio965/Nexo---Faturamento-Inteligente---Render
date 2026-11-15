# Restauração de Personalizar Guia e evolução editorial com mídias

## 1. Identificação e estado da entrega

| Campo | Registro |
| --- | --- |
| Implementação | Recuperação do acesso administrativo ao Guia e evolução do CMS institucional para texto formatado, imagens e vídeos curtos |
| Data | Conclusão em 2026-11-15; implementação iniciada em 2026-11-14 |
| Registro documental inicial | 2026-11-14 20:17:01 -0300, fuso `America/Sao_Paulo` |
| Encerramento da validação local | 2026-11-15 01:20:37 -0300, fuso `America/Sao_Paulo` |
| Repositório autorizado | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render |
| Ambiente | Código de testes e homologação; projeto empresarial fora do escopo |
| Branch | `feature/restaurar-personalizar-guia-midias` |
| Base inicial | `ae8775b23b948d8facb4d2eb69938e6209d91667` |
| Base atualizada | `09e4683` (`origin/main`), que recebeu o PR #49 durante a execução; o commit desta branch foi reaplicado sem conflitos, preservando a política de seleção |
| Commit do código e testes | `4c6cee02ae6d10317b3c81ccf39b3796730f87fc`; este documento é versionado em commit documental posterior |
| Revisão | [Pull Requests da branch](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pulls?q=is%3Apr+head%3Afeature%2Frestaurar-personalizar-guia-midias); o relatório final informa o PR efetivamente criado |
| Status | Código implementado e revisado; validação local documentada abaixo. Migração, configuração de vídeo e limpeza hospedadas continuam nas pendências explícitas desta entrega |
| Banco hospedado | Nenhuma migração aplicada, nenhuma escrita de conteúdo e nenhuma exclusão |
| Integração e publicação | Sem merge automático, sem deploy manual e sem alteração das configurações do Render |

A pasta `POSSIVEIS ATUALIZAÇÕES EMPRESA` já existia e foi reutilizada. Os documentos anteriores foram preservados. Dados utilizados em testes são fictícios e pertencem a bancos descartáveis.

## 2. Diagnóstico: por que a opção desapareceu

O [PR #33](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/33) incluiu o commit `635fb01d154636455db5c739d870d29865c8b4d1`, com o assunto `refactor(nav): remover Base de Conhecimento do menu administrativo`. A alteração retirou da sidebar o link, o ícone e o indicador ativo do CMS. As rotas de listagem, criação, edição e exclusão continuaram existindo para preservar a fonte de dados utilizada pelo Guia do cliente e pelo NexoBot.

O PR também continha mudanças de gerenciamento de análises e acabamento da interface. Não foi revertido integralmente. A presente restauração acrescenta somente o acesso **Personalizar Guia**, com ícone `bi-journal-text`, apontando para a rota existente `/admin/guia`. O indicador ativo de Análises e as demais opções administrativas permanecem preservados. Clientes não recebem o link administrativo.

## 3. Recursos reaproveitados

- Rotas `admin.guia`, `admin.guia_novo`, `admin.guia_editar` e `admin.guia_deletar`, com a autorização administrativa e CSRF preexistentes.
- Modelo `GuiaTopico`, inclusive `categoria`, `pergunta`, `resposta`, `imagem_url`, `ativo` e datas. Sua tabela e suas colunas não foram substituídas.
- Publicação institucional global: os tópicos não têm vínculo de propriedade com uma empresa. Os clientes consultam as mesmas publicações autorizadas.
- `storage.py` e `ArquivoArmazenado`, que mantêm bytes persistentes no banco e participam da mesma transação que os registros referentes aos arquivos.
- Guia do cliente por categorias e accordion, identidade visual, temas e componentes do portal.
- Recuperação de conhecimento e invalidação do cache em `nexobot/conhecimento.py`, além do detector conservador de sinais de teste em `nexobot/higiene.py`.
- Seed legítimo de `seed_guia.py`: três tópicos de Upload, Senhas e PDV. Ele não contém os registros `EZ Test Guia`/`ZZTESTE-guia` e consulta a pergunta já existente inclusive quando o tópico está inativo, evitando republicação por uma simples desativação.

Nenhuma rotina de seed foi executada no banco hospedado. Os registros sintéticos das suítes de segurança e de navegador continuam limitados às fixtures descartáveis; não foram removidos para produzir resultados positivos.

## 4. Funcionalidades e arquitetura implementadas

### 4.1. Gerenciamento e publicação

Personalizar Guia apresenta títulos, categorias, descrição, tipo de conteúdo, publicação, criação/atualização e ações. Há criação, edição, prévia administrativa privada, publicação, despublicação, exclusão lógica e restauração. A listagem permite localizar conteúdos e examinar sinais de teste. A ordem editorial é explícita, entre 0 e 9999, com agrupamento por categoria e desempate determinístico por ID.

Novos tópicos sem publicação explícita ficam em rascunho. `GuiaTopico.ativo` permanece a autoridade de publicação para o cliente e o NexoBot. Os metadados editoriais diferenciam rascunho, publicado, despublicado e excluído logicamente. A restauração de um excluído retorna um **rascunho**, sem republicação automática.

Excluir pela interface retira o tópico da publicação e registra sua exclusão lógica. O conteúdo, seus vínculos de mídia e histórico são preservados. Até dez versões editoriais anteriores ficam referenciadas no histórico; os blobs não são eliminados apenas por saírem do bloco atual. Não existe exclusão física automática de registros de clientes, relatórios ou análises.

### 4.2. Editor visual de blocos

O administrador trabalha com blocos ordenados de texto e mídia. O editor oferece parágrafos, títulos, subtítulos, negrito, itálico, listas numeradas/com marcadores e links; não exige escrever HTML. Blocos podem ser movidos, removidos e recolocados antes de salvar. O envio continua sendo um formulário protegido por CSRF.

O navegador limpa o conteúdo antes de serializar a estrutura e cola texto simples dentro do editor para evitar inserir HTML ativo da área de transferência. A proteção definitiva permanece no servidor: `guia_cms.py` valida o JSON, os tipos e tamanhos dos campos e sanitiza o HTML por uma lista restrita de elementos/atributos. Scripts, manipuladores de eventos, SVG, iframes e elementos executáveis não são aceitos como formatação. URLs são validadas; protocolos perigosos, referências de rede ambíguas e credenciais embutidas não se tornam links permitidos.

O limite editorial é de 80 blocos e 12 mídias por tópico, com orçamento textual limitado pelo serviço. Conteúdo inválido não é publicado parcialmente. Erros devolvem o formulário com o texto preservado para correção. Clientes não podem anexar mídias de outro tópico por alteração do identificador no formulário.

`resposta` recebe uma projeção textual segura do conteúdo formatado. Assim, o NexoBot continua utilizando sua fonte e seu algoritmo existentes; ele não recebe HTML executável e não passa a interpretar vídeos.

### 4.3. Imagens e vídeos

Imagens PNG, JPG/JPEG, WebP e GIF são identificadas pelo conteúdo real e pela extensão. São verificadas a integridade e a decodificação dos quadros. O novo upload aceita até **3 MiB** por imagem, dimensão máxima de 4096 px por eixo, 12 milhões de pixels por quadro, até 60 quadros e 24 milhões de pixels decodificados acumulados. Os bytes válidos são preservados; nomes originais não definem o caminho persistente.

O editor permite várias imagens entre os passos, prévia local, legenda, texto alternativo, alteração de ordem e substituição individual. Uma substituição cria um novo vínculo de mídia; referências anteriores não são destruídas silenciosamente. Imagens antigas podem continuar sendo entregues dentro do limite legado de 20 MiB, sem ampliar o limite dos novos uploads.

Vídeos são limitados a MP4 com uma faixa H.264 e, opcionalmente, uma faixa AAC, até **8 MiB**, **180 segundos**, **1920 × 1080** e **60 quadros/s**. A validação verifica contêiner, metadados, codecs e decodificação efetiva. Não basta renomear um arquivo para `.mp4`. Playlists, arquivos arbitrários, faixas extras e conteúdo corrompido são recusados. WebM não foi acrescentado nesta entrega.

FFmpeg/ffprobe são executados sem shell, com demuxer MP4/MOV explícito, referências externas desabilitadas, restrição de protocolos, número de threads limitado, timeout, limite de CPU, memória e saída. Uma validação de mídia e um lote editorial por processo evitam multiplicar simultaneamente os orçamentos de decodificação. Sem os binários e os limites POSIX necessários, o upload de vídeo é recusado e a interface informa a dependência.

O player usa HTML5, controles nativos, reprodução iniciada pelo usuário e `playsinline`. Vídeos permanecem dentro do tutorial e permitem reprodução, pausa, volume, busca e tela cheia. Falhas de carregamento têm aviso na interface. A prévia do vídeo salvo como rascunho usa a rota autenticada; a CSP não foi flexibilizada para vídeos arbitrários por `blob:` ou terceiros.

### 4.4. Persistência, quotas e entrega parcial

Foi reaproveitado o armazenamento persistente existente para **mídias pequenas de tutoriais**, com limites explícitos. Não foi implementado um serviço de hospedagem irrestrita de vídeos nem provisionado armazenamento de objetos. Vídeos grandes continuam fora do perfil suportado e exigem outro projeto de armazenamento/configuração autorizado.

Os arquivos são guardados como `db:guia/<chave>` em `ArquivoArmazenado`. Os bytes, as mídias editoriais, os blocos e a publicação participam da mesma transação. Rollback conserva o estado anterior. Eles continuam cobertos pelo backup do banco; a reprodução não depende do arquivo temporário original nem da sobrevivência do disco local do servidor.

O limite multipart global preexistente de **20 MiB** não foi aumentado. O tópico tem quota de **24 MiB** de mídias e o Guia inteiro de **128 MiB**, incluindo referências recuperáveis e histórico. No PostgreSQL, a verificação/gravação da quota é serializada por trava transacional; o controle de versão editorial impede sobrescrever silenciosamente outro formulário. Os limites por processo não substituem a validação de capacidade do ambiente hospedado.

A entrega utiliza metadados e tamanho real do banco, com `substr` de BYTEA em blocos de até **256 KiB**. Cada leitura libera sua conexão antes de transmitir o bloco; não há carregamento integral da coluna de vídeo nem retenção da conexão da autorização pela duração do player. São tratados GET, HEAD, Range fechado/aberto/sufixo, `206`, `416`, `Content-Range`, `Accept-Ranges` e `If-Range`. Acesso ocorre antes de consultar os bytes. O cabeçalho é `private, no-store`, com `nosniff` e a CSP restritiva própria da mídia.

### 4.5. Autorizações e referências antigas

Clientes acessam somente mídias atualmente referenciadas por tópicos publicados. Rascunhos, exclusões lógicas, mídias históricas sem vínculo publicado e despublicações não autorizam entrega ao cliente. ADMIN mantém prévia privada. Compartilhar os mesmos bytes entre dois tópicos não apaga a referência legítima do outro.

A rota `/midia/<chave>` deixou de aceitar um blob do Guia apenas por estar autenticado. Imagens antigas em `static/uploads/guia` passam por um redirecionamento canônico e por `/midia-legada-guia/<nome>`, com as guardas normais de sessão, primeiro acesso e publicação. Aliases normalizados da pasta estática também passam por esse caminho. Os arquivos públicos não relacionados ao Guia continuam usando o comportamento estático anterior.

A CSP do portal, as proteções de sessão e as permissões gerais não foram desativadas. As mudanças estão no acesso específico às mídias do Guia, sem substituir o mecanismo de autenticação.

### 4.6. NexoBot, temas e compatibilidade com outras entregas

Os eventos ORM existentes detectam alterações em `GuiaTopico` e invalidam o índice após commit; rollback não publica a alteração de cache. Publicar, editar conteúdo publicado, despublicar e excluir logicamente atualizam a fonte utilizada pelo bot. O mecanismo de TTL existente continua cobrindo outros processos.

A folha `nexo-guia.css` é carregada apenas nas telas pertinentes, com tokens dos temas atuais. Não foi acrescentada uma paleta global. Landing, dashboard administrativo, dashboard de inteligência comercial, contratos, relatórios, notificações, cabeçalho e seletor de temas não foram reconstruídos.

O PR de controle de seleção de textos (#49) estava aberto durante a consulta inicial. Sua branch não foi alterada nem integrada automaticamente. O editor usa a semântica `contenteditable`/`role="textbox"`, compatível com as exceções editáveis daquela política. Esta branch foi criada independentemente a partir da `main`; trabalhos paralelos e correções não publicados não podem ser presumidos como validados.

## 5. Arquivos modificados e justificativas

Todos os caminhos abaixo são completos em relação à raiz do repositório autorizado. No ambiente de execução, a raiz é `/workspace/Nexo---Faturamento-Inteligente---Render`.

| Caminho | Finalidade, alteração e justificativa |
| --- | --- |
| `templates/base.html` | Restaura somente o link administrativo Personalizar Guia e o estado ativo nas rotas do CMS; mantém os indicadores das demais áreas. |
| `blueprints/admin.py` | Reaproveita CRUD do Guia e integra editor, prévia, publicação/despublicação, remoção lógica, restauração e fluxo autenticado de inventário/backup/limpeza; preserva ADMIN e CSRF. |
| `blueprints/cliente.py` | A consulta do Guia utiliza a camada editorial e retorna somente publicações globais, com ordem explícita e fallback legado. |
| `guia_cms.py` | Nova camada do domínio editorial: detecção de esquema, validação/sanitização, projeção textual, estados, quotas, versão, histórico e autorização de mídia. |
| `guia_midias.py` | Novo módulo de validação limitada de imagens/MP4 e entrega de bytes por intervalos, mantendo persistência e limites de recursos. |
| `guia_limpeza.py` | Novo inventário conservador, fingerprint, seleção individual, exportação recuperável e despublicação sem exclusão física. |
| `models.py` | Acrescenta `GuiaEdicao` e `GuiaMidia`, sem novas colunas em `GuiaTopico`; permite operar com o legado antes da migração hospedada. |
| `migrations/versions/c3e08eb3863a_guia_edicao_e_midias.py` | Migração aditiva das duas tabelas, índices, FKs, CHECKs, RLS/privilégios e downgrade que recusa descartar dados. |
| `storage.py` | Encaminha imagens legadas do Guia para a rota autenticada; preserva a interface transacional e os demais arquivos. |
| `app.py` | Aplica ACL de publicação na mídia persistida e protege referências estáticas legadas, sem abrir acesso por aliases nem alterar os endpoints de outras funcionalidades. |
| `templates/admin/guia.html` | Substitui a listagem parcial por gerenciamento editorial com status, metadados, filtros, ações e acesso à revisão de testes. |
| `templates/admin/guia_form.html` | Formulário do editor visual, descrição, ordem, publicação e dados iniciais seguros dos blocos. |
| `templates/admin/guia_previa.html` | Nova prévia privada para o administrador examinar o mesmo conteúdo renderizado ao cliente. |
| `templates/admin/guia_limpeza.html` | Nova interface de inventário, proteção de Upload, revisão individual, backup e confirmação recuperável. |
| `templates/cliente/guia.html` | Preserva categorias/accordion e incorpora texto formatado e múltiplas mídias dentro do tutorial. |
| `templates/_guia_conteudo.html` | Renderização compartilhada do conteúdo sanitizado e de imagens/vídeos, evitando divergência entre prévia e Guia. |
| `static/css/nexo-guia.css` | Estilos locais do gerenciador/editor/conteúdo, responsividade, foco e integração com os temas existentes. |
| `static/js/guia-editor.js` | Controles visuais, limpeza defensiva, blocos, seleção local, formatação, ordenação, prévia de imagem, validação inicial e serialização do formulário. |
| `tools/auditar_guia.py` | Preserva auditoria somente leitura e acrescenta `--inventario`, com ordem legada, classes de ação e fingerprint. |
| `tests/test_guia_cms.py` | Novos testes HTTP de autorização, CSRF, editor, publicação global, mídias, quotas, concorrência, rollback e fallback anterior à migração. |
| `tests/test_guia_midias.py` | Novos testes de formatos reais/disfarçados, limites, codecs, integridade, validador indisponível e Range/HEAD sem consulta integral de bytes. |
| `tests/test_guia_limpeza.py` | Novos testes da fronteira conservadora, famílias identificadas, Upload, backup completo/deduplicado, dados concorrentes, rollback e atualização do bot. |
| `tests/test_guia_limpeza_http.py` | Dez cenários do fluxo HTTP real: autorização, CSRF, seleção protegida, download ZIP/recibo, confirmação, concorrência, expiração, troca de administrador e rollback. |
| `tests/test_guia_schema.py` | Novos testes SQLite de esquema, restrições, defaults, concorrência, legado, cascata e downgrade protegido. |
| `tests/postgresql_guia.py` | Novos testes no PostgreSQL privado: migração, RLS, privilégio de sequência, persistência JSON, versão e reversão. |
| `tests/test_guia_navegador.py` | Novos fluxos reais de editor, imagens, vídeo, publicação para duas empresas e matriz responsiva/temas. |
| `tests/test_guia_seguranca.py` | Novas regressões de aliases de mídia legada, sessão revogada, primeiro acesso, tipos JSON e concorrência limitada. |
| `tests/test_navegacao_admin.py` | Atualiza a expectativa autorizada do menu: Guia presente somente para ADMIN, com indicador ativo, mantendo as demais opções. |
| `tests/test_overflow_navegador.py` | Inclui o novo rótulo e verifica a largura/indicador do item Personalizar Guia, sem reduzir as medições existentes. |
| `tests/test_nexobot_conhecimento.py` | Ajusta o fluxo autorizado para publicação explícita e exclusão recuperável, conservando a verificação de atualização do índice. |
| `tests/test_backup_restore.py` | Atualiza inventário para 36 tabelas e popula/restaura as duas tabelas editoriais, seus vínculos, texto e mídia no ensaio real. |
| `tests/test_contratos_postgresql.py` | Inclui as novas tabelas no inventário posterior às revisões contratuais; preserva as verificações existentes. |
| `tests/test_etl_detalhamento_produtos.py` | Atualiza somente a expectativa do head Alembic, preservando a revisão e os testes do detalhamento. |
| `tests/test_leads_avaliacao.py` | Atualiza o head da cadeia aplicada, mantendo a revisão e os testes dos leads. |
| `.github/workflows/nexo-security-ci.yml` | Disponibiliza FFmpeg nos testes de mídia do job existente e acrescenta a suíte PostgreSQL do Guia. Nenhum teste de segurança foi desligado e nenhuma configuração do Render foi alterada. |
| `POSSIVEIS ATUALIZAÇÕES EMPRESA/2026-11-15_Restauracao_Personalizar_Guia_e_Midias.md` | Este registro: diagnóstico, escopo, dependências, resultados, reprodução seletiva e reversão. |

## 6. Banco de dados e compatibilidade de migração

A revisão **`c3e08eb3863a`**, posterior a `5a9c3e7d1b42`, cria:

- `guia_edicao`: PK/FK do tópico, descrição, ordem, blocos JSON, histórico JSON, referência de publicação, exclusão lógica e versão otimista.
- `guia_midia`: identificador, FK do tópico, referência persistente, tipo imagem/vídeo, legenda, texto alternativo e data.

As FKs têm cascata para exclusão física explicitamente realizada no banco; o CMS não usa essa operação para remover conteúdos. Os blobs permanecem independentes para não apagar automaticamente um arquivo compartilhado. Há índices de ordem/tópico/referência e restrições de tipo, ordem e versão.

No PostgreSQL, as tabelas novas nascem com RLS habilitada. Privilégios públicos e dos papéis de Data API `anon`/`authenticated` são retirados, com política restritiva de negação; os papéis de servidor previstos no projeto mantêm o acesso administrativo apropriado. A sequência de mídia também é protegida. A aplicação Flask continua sendo responsável por autorizar sua sessão; não foi criado acesso direto do cliente à Data API.

A migração foi preparada e exercitada em bancos descartáveis, inclusive com dados legados. **Não foi aplicada no Supabase hospedado.** A detecção de esquema permite manter o Guia e o NexoBot legados antes da aplicação autorizada; o gerenciador ampliado informa sua indisponibilidade em vez de tentar gravar em estruturas ausentes. Não houve modificação do schema empresarial.

O downgrade só remove as tabelas quando ambas estiverem vazias. Com dados editoriais ou mídias, ele recusa a operação. No PostgreSQL há trava durante a verificação/reversão para não permitir descarte por corrida com uma escrita.

## 7. Situação e procedimento de limpeza dos conteúdos de teste

### 7.1. Evidência disponível e ausência de escrita hospedada

Foi consultada a referência de projeto `mgjdsbcohboxzcbicbuc`, indicada pela rotina de bootstrap do repositório e única disponibilizada pela conexão nesta sessão. Os metadados retornaram o projeto ativo; um **SELECT somente leitura** de `public.guia_topico` retornou **`42P01` — tabela inexistente**. Uma segunda consulta de metadados por tabelas com nome contendo `guia`, nos esquemas não sistêmicos desse mesmo projeto, retornou lista vazia. Essa evidência não permite atribuir IDs reais aos tópicos vistos na captura. Nenhum outro banco de projeto foi acessado e nenhum comando DDL/DML foi executado contra o Supabase hospedado.

O proprietário informou não conhecer a referência correta e apresentou uma captura que identifica `ZZTESTE-guia`, a pergunta sobre `zztesteguiaquasar`, `svg image`, `fake png`, `empty img` e variantes de categoria com marcação HTML. São referências visuais para o procedimento; não são uma consulta aos registros hospedados.

| Resultado hospedado | Estado comprovado |
| --- | --- |
| IDs reais dos registros indesejados | **NÃO APURADOS** |
| Quantidade real preservada | **NÃO APURADA**; nenhuma escrita foi feita |
| Quantidade real despublicada | **0 nesta implementação** |
| Quantidade real excluída | **0 nesta implementação** |
| Mídias reais associadas | **NÃO APURADAS** |
| Backup real de registros hospedados | **NÃO GERADO**; depende do banco correto |
| Limpeza efetiva no ambiente hospedado | **PENDENTE**, sem ocultação artificial dos dados no template |

### 7.2. Critérios e recuperação implementados

O inventário lê todos os tópicos na ordem **categoria, ID**, anterior à ordem editorial. A ordem visual não é deduzida do valor do ID isoladamente. A classificação conserva Upload e conteúdos legítimos anteriores à fronteira confirmada. Um marcador EZ único e as famílias explicitamente identificadas `ZZTESTE-guia`/`ZZTEST-guia` permitem identificar os casos conhecidos. Sinais genéricos ou registros posteriores cuja finalidade não esteja confirmada permanecem **REVISAR**.

Os estados são **PRESERVAR**, **REMOVER_DA_PUBLICACAO** e **REVISAR**, acompanhados por motivo e ação prevista. Upload e demais protegidos não podem ser selecionados para essa limpeza, inclusive por alteração do POST. Casos de revisão exigem confirmação individual de seus IDs. Não se executa uma exclusão genérica por categoria ou por posição.

O fluxo administrativo tem quatro etapas: revisar a seleção; gerar token assinado vinculado a usuário, IDs, revisões e fingerprint; baixar o ZIP recuperável; confirmar a despublicação. O token expira em **15 minutos**. A sessão registra um recibo da resposta de download; a confirmação explícita do administrador declara que o arquivo foi guardado. O servidor verifica novamente o inventário antes/depois do backup e antes de alterar a publicação; alterações concorrentes invalidam a confirmação.

O ZIP privado contém campos completos dos tópicos, metadados/blocos/histórico, registros de mídia, bytes deduplicados, manifesto, tamanhos, SHA256 e instruções de recuperação. O limite é de 64 MiB por exportação e 12 MiB por arquivo; grupos grandes devem ser divididos. Se uma mídia estiver ausente, inconsistente, fora da pasta permitida ou acima do limite de backup, a operação falha sem despublicar.

Despublicar mantém registros e mídias. A reversão normal consiste em revisar e publicar novamente no CMS. Para uma perda real, o arquivo privado permite recuperar registros/vínculos e importar os bytes originais, primeiro em banco descartável e sem sobrescrever IDs existentes sem comparação/autorização. A integridade e a deduplicação do backup, o rollback, a preservação de Upload e a republicação após despublicar foram exercitados com dados fictícios.

### 7.3. Execução futura no banco correto

1. Confirmar a referência do Supabase de testes por fonte autorizada do ambiente, sem consultar o projeto empresarial nem divulgar credenciais.
2. Conferir a presença de `guia_topico`, as mídias associadas e a versão publicada da aplicação. Obter autorização específica antes de aplicar qualquer migração hospedada necessária.
3. Abrir Personalizar Guia → Revisar conteúdos de teste ou executar a auditoria somente leitura abaixo, sem anexar respostas privadas aos commits.
4. Conferir IDs, categorias, títulos, publicação e ordem real; preservar Upload e tudo que for legítimo. Revisar individualmente os casos ambíguos e as imagens correspondentes.
5. Preparar e baixar o backup recuperável, guardá-lo em local privado e conferir manifesto/hashes. Confirmar apenas a despublicação dos IDs inequivocamente abrangidos pela solicitação.
6. Validar o Guia de duas empresas fictícias autorizadas, a preservação de Upload, a ausência dos testes selecionados e a atualização do NexoBot. Registrar os IDs e contagens reais sem conteúdo privado desnecessário.
7. Não executar exclusão definitiva automática. Para reverter, republicar os tópicos selecionados após revisão; seus dados continuam presentes.

```bash
.venv/bin/python tools/auditar_guia.py --inventario --json
```

Esse comando exige o ambiente correto configurado pelo operador. Ele não executa migrações, não publica nem despublica e não foi usado para alterar banco hospedado nesta entrega.

## 8. Testes executados e limites das evidências

### 8.1. Ambiente isolado e comandos

Os testes HTTP usam SQLite temporário, migrações reais somente nesses bancos, `.env` desabilitado e barreira contra rede externa. Os testes PostgreSQL criam seus próprios clusters/bancos privados, sem aceitar uma URL de serviço hospedado. O navegador usa aplicação local e cópias de Bootstrap/Plotly/Socket.IO com integridade SRI conferida pelos auxiliares existentes.

```bash
# Regressão focada de CMS, mídia, limpeza, esquema, navegação, bot e segurança.
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_guia_cms tests.test_guia_limpeza tests.test_guia_midias \
  tests.test_guia_schema tests.test_http_hardening_security \
  tests.test_navegacao_admin tests.test_nexobot_conhecimento \
  tests.test_security_deploy.GuideImageTests -v

# Segurança adicional de aliases de mídia/sessão e lote editorial.
.venv/bin/python -B -m unittest tests.test_guia_seguranca -v

# Nova extensão no PostgreSQL privado.
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
  .venv/bin/python -B -m unittest tests.postgresql_guia -v

# Navegador real: formulário, publicação global, imagens e MP4.
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_guia_navegador -v

# Item administrativo restaurado e indicador do rótulo longo.
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_overflow_navegador.OverflowNavegadorTests.test_menu_administrativo_com_personalizar_guia \
  tests.test_overflow_navegador.OverflowNavegadorTests.test_sidebar_item_longo_nao_encosta_no_indicador -v

# Ensaio real de backup.
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
  .venv/bin/python -B -m unittest \
  tests.test_backup_restore.PostgreSQLBackupRestoreTests -v

# Regressões de inventário, leads e detalhamento.
.venv/bin/python -B -m unittest \
  tests.test_backup_restore.BackupDrillSafetyTests \
  tests.test_leads_avaliacao tests.test_etl_detalhamento_produtos -v
```

### 8.2. Resultados verificados antes do fechamento

| Grupo | Evidência registrada |
| --- | --- |
| Módulo de mídia | 21 testes aprovados; 3,472 s; `/tmp/nexo-guia-midias-tests.log` |
| Inventário/backup/limpeza | 12 aprovados; 1,555 s; `/tmp/nexo-guia-limpeza-final.log` |
| Esquema SQLite | 6 aprovados, incluindo comparação do modelo/migração, restrições, concorrência e downgrade protegido |
| PostgreSQL novo | 4 aprovados em 1,930 s, incluindo RLS/privilégios/sequência/legado e serviço real com quota advisory, BYTEA, JSON, Range, versão e rollback; `/tmp/nexo-guide-postgresql-final.log` |
| Backup/compatibilidade existente | Ensaio real de backup/restauração aprovado e 44 verificações existentes aprovadas; conferir o registro final do comando combinado antes de somar grupos |
| Regressão focada combinada | 96 aprovados; zero falhas/erros/ignorados; 20,079 s; `/tmp/nexo-guia-regressao-focada.log` |
| Segurança adicional | 11 aprovados; zero falhas/erros/ignorados; 4,262 s; `/tmp/nexo-guia-seguranca-tests.log` |
| Limpeza administrativa por HTTP | 10 aprovados em 7,000 s; `/tmp/nexo-guia-limpeza-http.log`; reexecutados junto à verificação do instalador: 11 aprovados em 4,841 s, sem duplicar a contagem |
| Guia no navegador | 5 aprovados; zero falhas/erros/ignorados; 60,288 s; `/tmp/nexo-guia-navegador-final.log` |
| Navegação restaurada no navegador | 2 aprovados; 10,618 s; `/tmp/nexo-guia-sidebar-navegador.log` |
| Regressão integral | 1.784 descobertos em 1.579,864 s: 1.782 passaram, 1 falhou pela versão do pip local e 1 geração opcional de capturas foi ignorada. O ambiente foi corrigido pelo instalador oficial do projeto e a verificação que falhou passou; nenhum teste foi alterado para esse ajuste. `/tmp/nexo-guia-suite-completa.log` e `/tmp/nexo-guia-instalador-e-limpeza-final.log` |
| Integração com main atualizada | 52 aprovados em 129,815 s, zero falhas/erros/ignorados: seleção existente, Guia no navegador, CMS, limpeza HTTP, segurança e instalador; `/tmp/nexo-guia-integracao-main-final.log` |
| Revisão final de escopo e segurança | Revisão independente sem achados pendentes; `git -c core.whitespace=cr-at-eol diff --check` aprovado. Landing, dashboards, autenticação, sessões, temas globais e Render preservados |
| GitHub Actions | Resultado local não atesta aprovação remota. Consultar as [execuções desta branch](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions?query=branch%3Afeature%2Frestaurar-personalizar-guia-midias) para o SHA enviado; o relatório final registra o estado efetivamente consultado após abrir o PR |

As linhas de mídia, limpeza e esquema também integram a execução combinada de 96. Reexecuções e grupos sobrepostos não devem ser somados como novos testes únicos. Os logs são temporários do ambiente, não contêm dados reais de clientes e não foram adicionados ao repositório.

### 8.3. Regressão completa e correção do ambiente

```bash
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn \
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
.venv/bin/python -B -m unittest discover -s tests -t . -v

# Somente o instalador da venv; não reinstala os requisitos da aplicação.
.venv/bin/python -I tools/install_dependencies.py --prepare-only

NEXO_TEST_CDN_DIR=/tmp/nexo-cdn .venv/bin/python -B -m unittest \
  tests.test_supply_chain_install.InstalledInstallerCompatibilityTests \
  tests.test_guia_limpeza_http -v
```

A primeira execução integral encontrou `pip 25.0.1` no ambiente; o projeto exige `26.2.2`. O comando `--prepare-only` baixou o wheel da origem oficial, conferiu o SHA256 definido no instalador versionado e corrigiu somente a ferramenta local. O teste de segurança permaneceu intacto e foi aprovado na reexecução. A suíte integral não foi repetida depois dessa correção de ferramenta, pois todos os demais cenários já haviam passado.

Os dez testes HTTP de limpeza foram adicionados após a descoberta inicial da suíte integral e executados separadamente, com resultado aprovado. Total distinto antes da atualização da base: **1.793 cenários aprovados e uma captura opcional ignorada**. Os grupos sobrepostos da tabela não foram somados novamente. A geração de capturas depende de `NEXO_PAINEL_CAPTURAS` e não é um cenário funcional desligado.

Após a atualização isolada desta branch sobre `09e4683`, foi executado o conjunto abaixo. Os **52 cenários passaram**; os sete testes de seleção acrescentados pelo PR #49 também foram efetivamente exercitados. A execução é evidência de compatibilidade entre o editor visual e a política compartilhada de seleção.

```bash
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
NEXO_TEST_CDN_DIR=/tmp/nexo-cdn \
NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
.venv/bin/python -B -m unittest \
  tests.test_selecao_navegador tests.test_guia_navegador \
  tests.test_guia_cms tests.test_guia_limpeza_http tests.test_guia_seguranca \
  tests.test_supply_chain_install.InstalledInstallerCompatibilityTests -v
```

O [PR #50](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/50), de âncoras da landing, foi consultado e seus arquivos foram comparados com os desta entrega: não há sobreposição de arquivos. Nenhuma branch paralela foi integrada ou modificada; a atualização acima reaplicou somente o commit desta implementação sobre a `main` já atualizada pelo responsável do repositório. Não houve force push.

### 8.4. Cenários comprovados

Foram executados criação/edição, rascunho sem publicação implícita, prévia privada, publicar/despublicar, remover/restaurar, mudança de categoria e ordem, texto formatado com acentos/links/listas e tentativas de XSS. O mesmo tópico publicado foi verificado para dois clientes de empresas diferentes e retirado para ambos após despublicar.

Imagens válidas e formatos disfarçados, tamanho/pixels/quadros, múltiplos passos, legenda/alt, substituição, remoção individual, compartilhamento e falha transacional tiveram verificação. Conteúdo de rascunho e histórico não autoriza entrega ao cliente. Os testes novos também verificam sessão revogada, primeiro acesso e aliases de `/static` antes de entregar mídia legada.

Um MP4 H.264/AAC fictício foi enviado pelo editor, persistido e reproduzido no navegador: play, pausa, volume, busca, tela cheia e Range de bytes foram conferidos. Após remover o arquivo original do upload, o vídeo continuou disponível a partir dos bytes no banco. A continuidade da navegação foi verificada depois da reprodução. Não foi declarada interpretação audiovisual pelo NexoBot.

A matriz de apresentação abrange **320, 360, 390, 430, 768, 1024, 1366 e 1920 px**, temas **dark/light/system**, em quatro telas: listagem, editor, prévia e Guia do cliente (**96 combinações**). Inclui títulos longos, texto extenso, imagens, campo de edição e controle de overflow. Foram verificados teclado, foco e colagem no editor. São cenários de navegador com dados fictícios; não substituem homologação manual de acessibilidade.

O navegador executado foi Chromium no Linux. Safari/iOS, Firefox, dispositivos físicos e tecnologias assistivas dependem de homologação específica. O ensaio de vídeo em 390 px comprova layout móvel emulado, não funcionamento em todo dispositivo físico. A presença de FFmpeg local/na CI não comprova sua instalação no runtime hospedado.

## 9. Reprodução seletiva no projeto empresarial

1. Examinar a versão empresarial existente: navegação, rotas de Guia, modelo/seed, armazenamento, CSP, autenticação, NexoBot, migrações e referências estáticas. Não substituir essa base por `git clone` deste repositório nem copiar arquivos completos indiscriminadamente.
2. Identificar o equivalente a `GuiaTopico` e confirmar se a publicação global por `ativo` continua correta. Adaptar somente a extensão editorial necessária e preservar dados/categorias legítimos.
3. Preparar uma migração aditiva compatível com o head empresarial real, com RLS, privilégios de tabelas/sequências e downgrade protegido. Testar upgrade com dados existentes e fallback anterior à migração. A revisão `c3e08eb3863a` desta branch não deve ser aplicada cegamente em outra cadeia.
4. Integrar o serviço editorial e as telas pontualmente. Restaurar somente o item administrativo necessário e preservar os estados ativos de Análises e das demais áreas.
5. Adaptar as regras de mídia ao armazenamento empresarial. Se adotar o perfil de vídeos curtos no banco, validar as quotas, backup/restauração, consumo de memória e tráfego. Para vídeos maiores, projetar armazenamento de objetos privado e autorização de acesso, mediante configuração/aprovação próprias.
6. Disponibilizar FFmpeg/ffprobe com as restrições necessárias no ambiente autorizado e testar a recusa segura quando ausentes. Não considerar vídeo operacional apenas porque o botão aparece na interface.
7. Proteger também referências antigas que possam continuar acessíveis por URLs estáticas ou caches anteriores. Validar autorização por publicação, sessão/primeiro acesso, Range/HEAD e a revogação para novas requisições após despublicar.
8. Inventariar o Guia empresarial real separadamente. Não reutilizar IDs ou classificações do ambiente de testes como se fossem registros empresariais. Preservar Upload e registros legítimos, fazer backup privado e despublicar apenas o que for expressamente autorizado.
9. Executar os testes de autorização/CSRF/XSS/uploads/quotas/concorrência, dois clientes de empresas distintas, NexoBot, responsividade, temas, mídia real e backup. Abrir um PR empresarial próprio. Aplicação de migração, integração e publicação empresarial exigem autorização específica fora desta entrega.

## 10. Reversão e preservação de dados

A reversão funcional deve retirar apenas o item/telas/editor e as integrações específicas desta implementação, preservando correções posteriores de outros trabalhos. Não reverter `app.py`, `base.html`, `models.py` ou os blueprints inteiros se houver alterações concorrentes.

O caminho menos destrutivo é voltar ao leitor legado mantendo as tabelas editoriais e seus blobs intactos até decidir a recuperação. Antes de regressar o código de mídia, avaliar a autorização: restaurar a antiga entrega irrestrita de `/midia` ou arquivos estáticos pode tornar rascunhos novamente acessíveis. A reversão não deve reintroduzir essa exposição.

Uma despublicação da limpeza é revertida no CMS, após revisão, publicando novamente o tópico. Uma exclusão lógica é restaurada como rascunho. Os arquivos e as referências permanecem no banco, inclusive para versões anteriores; não executar varredura genérica ou remoção de blobs por falta de referência no bloco atual.

Para remover fisicamente o esquema editorial, fazer backup e recuperação de ensaio primeiro e obter a autorização correspondente. O downgrade `c3e08eb3863a → 5a9c3e7d1b42` recusa tabelas não vazias por desenho. Não esvaziar essas tabelas apenas para fazer o comando passar e não executar essa reversão hospedada nesta entrega.

## 11. Pendências e resultado real

- Aplicação autorizada da migração no Supabase hospedado e validação posterior do esquema/compatibilidade; não realizada.
- Identificação do banco de testes que contém os registros da captura, inventário com IDs reais, backup privado e limpeza efetiva; pendentes, com zero escritas/despublicações/exclusões hospedadas nesta entrega.
- Disponibilidade/configuração e validação de FFmpeg/ffprobe no runtime hospedado; não confirmadas. Upload/reprodução foram comprovados no ambiente local configurado, sem declaração de operacionalidade no Render.
- Homologação em outros navegadores, dispositivos físicos e tecnologias assistivas.

O código recupera o acesso administrativo e oferece gerenciamento institucional de texto e mídias pela interface, com publicação global, controles de segurança e recuperação. O projeto empresarial permanece fora do escopo. Nenhum merge automático, deploy manual, ajuste do Render ou migração hospedada foi executado.
