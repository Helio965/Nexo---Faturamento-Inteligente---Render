# NEXO: Faturamento Inteligente — Relatório técnico para auditoria independente

## Horário oficial de Brasília no sininho de notificações e no suporte (chamados e mensagens)

Documento preparado para auditoria independente (ChatGPT). Tudo o que está aqui foi lido no repositório oficial ou executado em cópia descartável do código, com dados fictícios, sem acesso a produção (Render, Supabase ou banco real). Fato verificado e hipótese aparecem sempre separados. Cada número vem de um log, de um teste ou de uma captura do pacote de evidências (seção G).

## A. Identificação

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| SHA inicial (`main`) | `04d8422659ec6ea0b9d5ffcbe3504e33220b113b`, "Merge pull request #36", 29/10/2026 14:06 (−03:00). Conferido com `git fetch` antes de começar e de novo antes do push. |
| SHA final | Código: `5e9cefbbf9df9edefa50dc3599eb34b16abba6db` (`5e9cefb`), último commit de código, com a CI verde. Depois dele vem só o commit deste relatório, "docs(timezone): registrar auditoria e evidencias", que acrescenta este arquivo em `Docs/`. |
| Branch | `fix/nexo-horario-brasilia-notificacoes-suporte`, criada a partir da `main` `04d8422`. |
| PR | [#37](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/37), em rascunho, base `main`. Sem merge e sem deploy. |
| Data | 29/10/2026 |
| Ambiente | Contêiner isolado Ubuntu 24.04, Python 3.12.3 (o CI usa 3.12; o `render.yaml` fixa 3.12.10), Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.6, Flask-SocketIO 5.6.1, Alembic 1.20.1, `tzdata` 2026.5, PostgreSQL 16.15 descartável (socket Unix privado, sem TCP), Chromium com Playwright 1.56 e o cliente Socket.IO 4.7.5 conferido por hash. Sem chave do Render, sem credencial do Supabase. |

## B. Problema

**Relato.** Quando um cliente abre um chamado, o horário mostrado no sininho do administrador aparece adiantado, "cerca de duas horas", em relação ao horário de Brasília. O pedido estende a verificação a todos os fluxos de suporte e de notificação.

**O que foi verificado.** Os cinco campos de horário do suporte e do sininho, e todos os pontos em que eles aparecem:

| Campo (tabela.coluna) | Gravado por (código anterior) | Exibido em (código anterior) |
|---|---|---|
| `notificacao.data_criacao` | `DEFAULT CURRENT_TIMESTAMP` do banco | sininho recarregado: `n.data_criacao.strftime('%d/%m %H:%M')` (`templates/base.html:144`) |
| (payload do Socket.IO) | `datetime.now().strftime("%d/%m %H:%M")`, relógio do processo (`notifications.py:54`) | item inserido em tempo real no sininho (`templates/base.html:915`) |
| `mensagem_suporte.data_envio` | `DEFAULT CURRENT_TIMESTAMP` | conversa dos dois papéis: `strftime('%d/%m/%Y %H:%M')` (`templates/_chat.html:19`) |
| `chamado_suporte.data_abertura` | `DEFAULT CURRENT_TIMESTAMP` | "aberto em" (só a data) nos dois detalhes do chamado; "Aberto em" (só a data) na lista do cliente; coluna "Atualizado" da lista do admin quando não há atualização |
| `chamado_suporte.data_atualizacao` | `datetime.now(timezone.utc)` nas rotas de resposta e de status | coluna "Atualizado" da lista do admin: `(c.data_atualizacao or c.data_abertura).strftime(...)` |
| `chamado_suporte.data_fechamento` | `datetime.now(timezone.utc)` ao resolver | não era exibido |

Nenhum e-mail transacional imprime data ou hora (`emails.py`, `templates/emails/`), e nenhum texto de notificação embute horário (os sete gatilhos passam por `criar_notificacao`: envio de relatório, novo chamado, resposta do cliente, publicação da devolutiva, processamento, resposta do admin e resolução).

## C. Causa raiz

### C.1 Fatos reproduzidos

Reprodução em `repro.py` (pacote, pasta `reproducao/`): PostgreSQL descartável com as migrations reais, usuários fictícios, as rotas HTTP reais e um cliente Socket.IO por papel. O roteiro é: o cliente abre o chamado, o admin responde, o cliente responde, o admin resolve e o cliente reabre. Cada horário exibido foi comparado com o instante real, lido antes e depois de cada requisição e convertido para America/Sao_Paulo. A matriz cruza o fuso do processo (o relógio do servidor) com o TimeZone da sessão do banco.

1. **Tipo das colunas.** As cinco colunas são `timestamp without time zone` (consulta em `information_schema.columns` depois de `flask db upgrade` até o head `81287c74387a`). Nenhuma revisão posterior à inicial `d87a6fbc2fbe` as altera.
2. **Gravação.** O PostgreSQL grava nessas colunas o relógio do TimeZone **da sessão**:
   - o `CURRENT_TIMESTAMP` do `DEFAULT` é o início da transação (`timestamptz`), convertido para o fuso da sessão na atribuição;
   - o psycopg2 envia `datetime.now(timezone.utc)` como `'...+00:00'::timestamptz`, que também é convertido para o fuso da sessão.
   
   Evidência: o mesmo instante (18:15 UTC) ficou gravado como `17:15` com a sessão em `Atlantic/Azores` e como `18:15` com a sessão em UTC (`antes_UTC_Atlantic-Azores.json` × `antes_UTC_UTC.json`).
3. **Exibição.** Os seis templates exibiam o valor com `strftime`, sem nenhuma conversão. O que se via era, portanto, o relógio da sessão do banco.
4. **Tempo real.** O payload usava `datetime.now()` sem fuso: o relógio de parede do processo, independente do valor gravado.
5. **Navegador.** O JavaScript não calcula horário (insere o texto `n.hora` que veio pronto). O fuso do navegador não interfere; o teste de navegador da seção F usa um navegador em `Asia/Tokyo` e outro em `America/Los_Angeles`.
6. **Socket.IO e Jinja.** Os dois só transportam e imprimem texto; nenhum dos dois converte.
7. **Conversão duplicada.** O código anterior não fazia conversão nenhuma. O risco de conversão dupla aparece em correções improvisadas, como subtrair 3 h de um valor que já está em Brasília quando a sessão do banco usa `America/Sao_Paulo`.

Resultado antes (`04d8422`) e depois (`5e9cefb`) da correção. Cada célula é a diferença entre o horário exibido e o horário real de Brasília; "data" indica que o ponto mostra só a data, correta naquele momento, e "—" que o ponto não existe na versão:

| Fuso do processo | TimeZone da sessão do banco | Versão | Tempo real (Socket.IO) | Sininho recarregado | Listagem admin | Conversa | Cabeçalho "aberto em" | Painel do chamado | Pontos corretos |
|---|---|---|---|---|---|---|---|---|---|
| UTC | UTC | antes | +3 h | +3 h | +3 h | +3 h | data | — | 4/27 |
| UTC | UTC | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| UTC | America/Sao_Paulo | antes | +3 h | 0 h | 0 h | 0 h | data | — | 22/27 |
| UTC | America/Sao_Paulo | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| America/Sao_Paulo | UTC | antes | 0 h | +3 h | +3 h | +3 h | data | — | 9/27 |
| America/Sao_Paulo | UTC | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| America/Sao_Paulo | America/Sao_Paulo | antes | 0 h | 0 h | 0 h | 0 h | data | — | 27/27 |
| America/Sao_Paulo | America/Sao_Paulo | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| Asia/Tokyo | UTC | antes | +12 h | +3 h | +3 h | +3 h | data | — | 4/27 |
| Asia/Tokyo | UTC | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| Atlantic/Azores | UTC | antes | +2 h | +3 h | +3 h | +3 h | data | — | 4/27 |
| Atlantic/Azores | UTC | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| America/Noronha | UTC | antes | +1 h | +3 h | +3 h | +3 h | data | — | 4/27 |
| America/Noronha | UTC | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |
| UTC | Atlantic/Azores | antes | +3 h | +2 h | +2 h | +2 h | data | — | 4/27 |
| UTC | Atlantic/Azores | depois | 0 h | 0 h | 0 h | 0 h | 0 h | 0 h | 31/31 |

Com servidor e banco em UTC, a configuração padrão do Render e do Supabase, **tudo** aparece **3 h** adiantado: tempo real, sininho recarregado, lista do admin e conversa dos dois papéis. As telas que mostram só a data erram entre 21:00 e 23:59, quando em UTC já é o dia seguinte (cenário B da seção F). Com o código corrigido (head final `5e9cefb`), as 31 leituras dão 0 h nas oito combinações.

### C.2 Produção (não verificado: sem acesso, por instrução)

- **Render.** O `render.yaml` não define `TZ`, e o padrão dos serviços do Render é UTC. Não foi possível ver variáveis definidas só no painel.
- **Supabase.** O padrão do PostgreSQL do Supabase é `TimeZone = UTC`. Nada no código define o fuso da sessão (`config.py` só usa `pool_pre_ping` e `pool_recycle`). Pelo pooler de transação (porta 6543), opções `-c` por conexão não são confiáveis (Supavisor; `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`).
- **Consequência.** Se as duas premissas valem, produção mostra +3 h. Para confirmar sem alterar nada, o proprietário pode rodar o diagnóstico somente leitura `scripts/diagnosticar_fuso_horario.py` (seção E.4).

### C.3 Sobre as "cerca de duas horas"

Uma diferença de 2 h **não** foi reproduzida com a configuração padrão de produção. Ela aparece, exata, só quando o relógio que grava ou exibe está em UTC−1:
- **processo em UTC−1** (por exemplo `TZ=Atlantic/Azores`; nesta data os Açores estão em UTC−1): +2 h no tempo real e +3 h no resto;
- **sessão do banco em UTC−1**: +2 h no sininho recarregado, na lista e na conversa, e +3 h no tempo real.

Hipóteses, nenhuma confirmada:
- **(a) Observação aproximada.** Comparar o horário de uma notificação com o relógio algum tempo depois: um aviso de 1 h atrás, mostrado com +3 h, parece estar 2 h à frente.
- **(b) Relógio de comparação com regra antiga de horário de verão.** Um computador ou celular com a base de fusos IANA anterior à versão 2018a (janeiro de 2018) ainda segue a regra de 2008 a 2017: horário de verão de Brasília a partir do terceiro domingo de outubro.
  - Em 29/10/2026, esse relógio mostraria UTC−2, e o sininho, em UTC, ficaria exatamente 2 h à frente dele.
  - Bases de 2018a a 2019a só aplicariam o horário de verão a partir de novembro. As posteriores já não têm horário de verão, que foi extinto em 2019.
- **(c) Configuração não padrão** de `TZ` no painel do Render ou de `TimeZone` no banco, em fuso UTC−1. O diagnóstico da seção E.4 responde à parte do banco.

**A correção não depende da causa.** O horário exibido deixa de depender do fuso do servidor, do banco e do navegador. Isso vale para as oito combinações da matriz e para os quatro TimeZones de sessão do cenário J.

## D. Solução

Arquivos alterados (diff contra `04d8422`):

1. **`horario.py` (novo).** Formatador único e documentado:
   - `UTC = timezone.utc` e `BRASILIA = ZoneInfo("America/Sao_Paulo")`;
   - `agora_utc()`, que delega ao relógio único do portal (`contract_policy.agora(nova_leitura=True)`, controlado nos testes por `NEXO_RELOGIO`);
   - `instante_utc()`, que recusa valor sem fuso;
   - `horario_brasilia(instante, formato="completo" | "curto" | "data", rotulo=False)`, que devolve "29/10/2026 às 14:34", "29/10 14:34" ou "29/10/2026", e "—" para `None`. O "às" fica fora do `strftime`, como no PDF, então a localidade do servidor não interfere. `rotulo=True` acrescenta "(Horário de Brasília)";
   - `iso_utc()`, que devolve ISO 8601 com fuso ("2026-10-29T17:34:00+00:00").

   O `contract_policy.formatar_instante` não foi reaproveitado para exibição. Ele formata no fuso configurável da política de prazos e recusa valores sem fuso, e não tem o formato curto do sininho. Manter os dois separados preserva os prazos contratuais intactos; o relógio, este sim, é o mesmo.
2. **`models.py`.**
   - Novo tipo `InstanteUTCSemFuso` (`TypeDecorator` sobre `DateTime()` sem fuso) nas cinco colunas. Na escrita, exige fuso explícito, converte para UTC e grava o relógio UTC sem fuso: o TimeZone da sessão deixa de mudar o valor gravado. Na leitura, devolve o instante com fuso UTC.
   - `default=agora_utc` (relógio do Python) em `data_abertura`, `data_envio` e `data_criacao`. O `server_default` continua igual, só espelhando o esquema.
   - Desempate por id na ordem das mensagens.
   - Nenhuma migração de esquema ou de dados. O tipo da coluna não muda, e o `compare_metadata` continua vazio em SQLite e em PostgreSQL.
3. **`notifications.py`.** O payload do Socket.IO sai do `data_criacao` gravado, que o flush já preencheu:
   - `hora` ("29/10 14:34") e `hora_completa` ("29/10/2026 às 14:34 (Horário de Brasília)"), da mesma função usada pelo template;
   - `instante` (ISO 8601 com fuso).

   Só há strings no payload (nada de `datetime`), e a montagem não lê atributos depois do commit. A fila pós-commit, a entrega só após o COMMIT, o descarte no rollback, a sala por credencial e o FOR SHARE ficaram intactos.
4. **`app.py`.** Filtros Jinja `horario_brasilia` e `iso_utc`.
5. **`templates/_macros.html`.** A macro `m.horario(instante, formato)` gera `<time datetime="ISO" title="… (Horário de Brasília)">texto</time>`, ou "—".
6. **`templates/base.html`.** O sininho renderizado usa a macro no formato curto, o mesmo da versão anterior (sem redesenho). O JavaScript cria o `<time>` pelo DOM (`setAttribute`, `title`, `textContent`); não há HTML montado com os campos de horário. Contador, badge, limite de 5 itens, links, toast e o `escapeHtml` do texto continuam iguais.
7. **`templates/_chat.html`.** O horário de cada mensagem passa a ser o de Brasília, o mesmo para admin e cliente.
8. **`templates/admin/tickets.html`.** O cabeçalho passa de "Atualizado" para "**Última atividade**": a coluna mostrava a abertura quando não havia atualização, e o rótulo agora diz o que ela é (última mensagem ou mudança de status; sem nenhuma, a abertura).
9. **`templates/admin/ticket_detalhe.html`.**
   - Cabeçalho "aberto em 29/10/2026 às 14:34".
   - No painel lateral, os quatro eventos separados: **Aberto em**, **Última mensagem**, **Última atualização** e **Resolvido em**. Este último só aparece enquanto o chamado está resolvido.
   - Os instantes não são forçados a coincidir: abertura, primeira mensagem e notificação têm cada um a própria leitura do relógio (cenário F).
10. **`templates/cliente/tickets.html`** e **`templates/cliente/ticket_detalhe.html`.** Data de abertura em Brasília. O aviso de resolvido informa quando ("resolvido em 29/10/2026 às 15:27").
11. **`blueprints/admin.py`** e **`blueprints/cliente.py`.**
   - `data_atualizacao` e `data_fechamento` passam a usar `agora_utc()`.
   - Uma leitura do relógio por ação. Ao resolver, ela vale para a atualização e para o fechamento. Numa resposta, do admin ou do cliente, vale para a mensagem e para a atualização do chamado (achado da revisão independente, seção F.5).
   - A abertura do chamado, a primeira mensagem e a notificação continuam com leituras próprias.
12. **`scripts/diagnosticar_fuso_horario.py` (novo).** Diagnóstico somente leitura para o proprietário (seção E.4).
13. **`.github/workflows/nexo-security-ci.yml`.** Baixa o cliente Socket.IO 4.7.5 com conferência do hash SRI, como já fazia com Bootstrap e Plotly, para o teste de navegador em tempo real rodar no CI. Sem a cópia íntegra, o teste é pulado e o aviso da CI diz qual.
14. **`tests/test_overflow_navegador.py`.** As datas fictícias de dois chamados passam a ter fuso UTC explícito. O novo tipo recusa datetime sem fuso; nenhuma verificação foi alterada.

## E. Convenção

### E.1 Regra única

| Etapa | Regra |
|---|---|
| Gravar | Instante absoluto em UTC. Nas cinco colunas legadas sem fuso, o valor é o relógio UTC sem fuso, convertido pelo Python (`InstanteUTCSemFuso`). Valor sem fuso é recusado (`ValueError`): não se presume que seja UTC. |
| Ler | Valor sem fuso vindo dessas colunas = UTC, pela convenção documentada (E.2). Leitura sempre devolve `datetime` com fuso UTC. |
| Exibir | Sempre America/Sao_Paulo (IANA, com o histórico de horário de verão), pelo `horario.py`, no servidor. |
| Transferir | ISO 8601 com fuso (`2026-10-29T17:34:00+00:00`) no atributo `datetime` e no payload, ao lado do texto já formatado. O JavaScript não converte. |
| Relógio | `agora_utc()` → `contract_policy.agora(nova_leitura=True)`: o mesmo relógio da política, injetável nos testes. Nenhum `datetime.now()` sem fuso, nenhum deslocamento fixo. |

### E.2 Registros existentes (sem migração)

**De onde vêm.** Desde o primeiro commit publicado (`fc63708`, 19/10/2026), o código grava as cinco colunas de duas formas só: pelo `CURRENT_TIMESTAMP` do banco e por `datetime.now(timezone.utc)`. Nas duas, o valor gravado é o relógio do TimeZone da sessão no momento da gravação (C.1, item 2). O banco de produção foi criado pelas migrations, sem cópia de dados de outro banco (`RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`).

**Por que são UTC.** Com a sessão em UTC, o padrão do Supabase, os registros antigos já estão no relógio UTC: a mesma convenção da leitura nova. Eles passam a aparecer no horário certo sem `UPDATE` nenhum (cenário K, ponta a ponta, em SQLite e em PostgreSQL).

**O que não foi presumido.** Não foi presumido que a sessão de produção esteja em UTC. O fuso dos registros antigos não foi "corrigido" nem reinterpretado por estimativa. A premissa é verificada antes de publicar (E.4). Se ela falhar, vale o plano da E.5.

### E.3 Por que não migrar agora para `timestamptz`

Converter as colunas (`ALTER COLUMN … TYPE timestamptz USING col AT TIME ZONE 'UTC'`) tornaria o tipo explícito, mas:
- trava as tabelas (`ACCESS EXCLUSIVE`);
- precisa ser executada em produção;
- grava no banco a mesma premissa de UTC, que ainda não foi verificada.

Ela não é indispensável: o tipo do Python já torna a escrita independente da sessão. Fica como opção futura (seção J), junto com trocar o `DEFAULT CURRENT_TIMESTAMP` por `timezone('utc', now())`. Essa troca cobriria inserções feitas fora do ORM, que ainda recebem o relógio da sessão.

### E.4 Diagnóstico somente leitura (antes de publicar)

`python scripts/diagnosticar_fuso_horario.py`, com a mesma `DATABASE_URL` da aplicação, que o script resolve como o `config.py`.

**O que ele faz.**
- **Usa só a URL da aplicação.** Antes de conectar, remove as variáveis do terminal que mudariam o alvo ou a sessão: `PGHOST`, `PGHOSTADDR`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGSERVICE`, `PGSERVICEFILE`, `PGOPTIONS`, `PGTZ` e `PGDATESTYLE`.
  - `PGTZ` e `PGOPTIONS` mudariam o fuso da sessão do script.
  - `PGHOST` e `PGSERVICE` mudariam o banco consultado.
  - As de TLS e autenticação (`PGSSLMODE`, `PGSSLROOTCERT`, `PGREQUIREAUTH` etc.) continuam valendo.
- **Exige TLS para host remoto.** Sem `sslmode` na URL nem em `PGSSLMODE`, a conexão usa `sslmode=require`. Para conferir também o certificado do servidor, use `sslmode=verify-full` com `PGSSLROOTCERT`.
- **Só lê.** Abre uma transação `READ ONLY` e a desfaz no fim.
- **Não expõe credenciais.** Não imprime a senha nem a mensagem do driver; uma URL malformada sai com código 2 e só o nome da exceção.
- **Informa:**
  - o banco e o usuário consultados;
  - o TimeZone da sessão e a origem dessa configuração (`pg_settings.source`: `default`, `database`, `user` etc.);
  - o relógio do banco e os tipos das cinco colunas.
- **Veredito.**
  - Código 0: sessão em UTC e as cinco colunas encontradas. É compatível com a convenção, se a configuração não mudou desde a gravação dos registros.
  - Código 1: sessão em outro fuso. Verificar antes de publicar.
  - Código 2: não executado ou inconclusivo, por exemplo num banco sem as cinco colunas.

O cenário J executa o diagnóstico, pela função e pela linha de comando, contra os quatro bancos descartáveis. Ele põe `PGTZ=UTC` e `PGOPTIONS` no ambiente para provar que são ignorados. O resultado é código 0 em UTC, código 1 nos outros fusos e código 2 num banco sem o esquema; o teste confere também que nada foi gravado.

### E.5 Plano se o diagnóstico não der UTC (não executado)

**Não publicar.** Nesse caso, os registros antigos estão no relógio do fuso da sessão.

**Tratamento possível, a ser autorizado pelo proprietário:**
1. Backup.
2. Medir a amplitude: contagem e intervalo de datas por tabela.
3. Uma migração única que converta os valores antigos daquele fuso para UTC (`(col AT TIME ZONE '<fuso da sessão>') AT TIME ZONE 'UTC'`). Ela vale somente para as linhas anteriores ao deploy da correção, identificadas pelo id máximo registrado no momento do deploy.
4. Ensaio do mesmo procedimento numa cópia restaurada.

O cenário J já demonstra o efeito: um registro gravado como o código antigo, numa sessão em Brasília, aparece 3 h mais cedo se for lido como UTC.

## F. Testes

### F.1 Módulo novo `tests/test_notificacoes_horario_brasilia.py`

23 testes em quatro classes:
- `HorarioBrasiliaTests` (17). Usam as rotas reais e as migrations reais (SQLite novo a cada teste, por `DeployTestCase`). Há dois usuários fictícios, ADMIN e CLIENTE, cada um com sessão HTTP e cliente Socket.IO próprios. O relógio é injetado por `NEXO_RELOGIO`.
- `HorarioBrasiliaPostgreSQLTests` (1).
- `DiagnosticoFusoHorarioTests` (4).
- `HorarioBrasiliaNavegadorTests` (1).

| Cenário | Teste | O que verifica |
|---|---|---|
| A | `test_a_formatador_converte_o_instante_para_brasilia` | 29/10/2026 17:34 UTC → "29/10/2026 às 14:34", "29/10 14:34", "29/10/2026", rótulo e ISO. O mesmo instante expresso em outro fuso dá o mesmo texto, sem conversão dupla. `None` dá "—" e "". |
| A | `test_a_29_10_2026_17h34_utc_aparece_14h34_em_todos_os_pontos` | Ponta a ponta: payload, sininho recarregado, lista do admin, lista do cliente, conversa dos dois papéis e cabeçalho. Os valores gravados ficam em UTC. |
| B | `test_b_virada_do_dia_usa_a_data_de_brasilia` | 30/10 01:30 UTC vira 29/10 22:30 em todas as telas, e a lista do cliente mostra 29/10, não 30/10. 30/10 03:05 UTC vira 30/10 00:05. |
| C | `test_c_fuso_do_processo_nao_muda_o_horario_exibido` | Sete fusos de processo: UTC, Tóquio, Noronha, Açores, Kiritimati, Los Angeles e São Paulo. O teste confere antes que o relógio do processo de fato mudou. |
| D | `test_d_relogio_de_outro_fuso_exibido_como_brasilia_adianta_o_deslocamento` | Ilustra o mecanismo do código anterior: exibir sem conversão o relógio de outro fuso adianta exatamente o deslocamento desse fuso. São +3 h em UTC, +2 h em UTC−1 (Açores), +1 h em Noronha e 0 em São Paulo. O payload novo dá 14:34 em todos. É uma ilustração, não a prova da causa em produção (C.3). O código anterior foi executado de fato nessas configurações pelo `repro.py` (C.1). |
| E | `test_e_horario_de_verao_historico_pelas_regras_iana` | Instantes de 2018, 2019 e 2026, inclusive as duas transições: o 00:00 que não existiu em 04/11/2018 e a hora 23 repetida em 16/02/2019. O deslocamento é −2 ou −3 h conforme a data. Ponta a ponta em 15/12/2018. |
| F | `test_f_payload_do_tempo_real_usa_o_instante_gravado` | Com o relógio avançando 1 min a cada leitura, o payload é igual ao valor gravado, e só há strings nele. Abertura, mensagem e notificação têm instantes distintos (não são forçados a coincidir). |
| F | `test_f_resposta_e_resolucao_leem_o_relogio_uma_vez` | Com o mesmo relógio, nas respostas do admin e do cliente, "Última mensagem", "Última atualização" e "Última atividade" coincidem. Na resolução, "Resolvido em" coincide com a "Última atualização" no painel e no aviso do cliente. |
| G | `test_g_sininho_recarregado_mostra_o_texto_do_tempo_real` | Admin e cliente: texto, `datetime` e `title` do tempo real iguais aos da recarga. |
| H | `test_h_admin_e_cliente_veem_o_mesmo_instante_de_cada_mensagem` | Cinco mensagens alternadas, com a mesma lista nos dois papéis. |
| I | `test_i_roteiro_completo_de_um_chamado` | Sete etapas: abertura (14:34), resposta do admin (14:52), resposta do cliente (15:03), mudança de status (15:15), resolução (15:27), resposta do admin depois de resolver (15:40) e reabertura (22:30 de 29/10, quando em UTC já é 30/10). Em cada etapa: payload, recarga, conversa dos dois papéis, painel, as duas listas e o isolamento (o outro papel não recebe nada). Depois de 15:40, "Resolvido em" continua 15:27 e fica antes da "Última atualização". O aviso de resolvido só aparece para o cliente enquanto o chamado está resolvido. |
| I | `test_i_demais_gatilhos_do_sininho_usam_o_mesmo_horario` | Envio de relatório (para os admins), processamento e publicação (para os clientes), com os textos reais dos gatilhos. |
| J | `HorarioBrasiliaPostgreSQLTests.test_j_postgresql_mostra_o_mesmo_horario_em_qualquer_timezone_de_sessao` | Processo separado em Asia/Tokyo e quatro bancos, com a sessão em UTC, America/Sao_Paulo, Atlantic/Azores e Asia/Tokyo. Em cada um:<br>• o roteiro I inteiro, com as mesmas expectativas do SQLite;<br>• valores gravados em UTC, inclusive um instante com fuso de Tóquio gravado pelo ORM;<br>• um registro legado gravado como o código antigo;<br>• o diagnóstico pela função e pela linha de comando, com `PGTZ` e `PGOPTIONS` no ambiente.<br>Inclui um banco sem o esquema (código 2). |
| K | `test_k_registros_legados_no_relogio_utc_sem_deslocamento` | Linhas inseridas por SQL como o código antigo gravava (valor UTC explícito e `DEFAULT CURRENT_TIMESTAMP`) aparecem em Brasília, na ordem certa junto com as novas. Ler não regrava nada. |
| K | `test_k_escrita_converte_qualquer_fuso_para_o_relogio_utc` | Instantes com fuso de Brasília e de Tóquio, gravados pelo ORM nas cinco colunas, ficam como o relógio UTC (17:34 bruto) e aparecem 14:34. |
| L | `test_l_nada_e_entregue_apos_rollback` | O rollback não entrega a notificação; o commit entrega, com o horário certo. O outro papel não recebe nada. |
| L | `test_l_texto_do_chamado_nao_entra_nos_campos_de_horario` | Um assunto com HTML e um horário falso no texto não alteram os campos de horário, que mantêm o formato fixo. A página não fica com HTML injetado. |
| L | `test_l_horario_sem_fuso_e_recusado` | O formatador e a escrita no banco recusam valor sem fuso, e nada é entregue. |
| L | `DiagnosticoFusoHorarioTests` (4 testes) | URL malformada dá código 2, sem trecho da senha. URL que não é PostgreSQL não consulta nada. Host remoto sem `sslmode` exige TLS. As variáveis que mudariam o alvo ou a sessão (`PGHOST`, `PGSERVICE`, `PGTZ`, `PGOPTIONS`) são ignoradas; as de TLS e autenticação (`PGSSLMODE`, `PGSSLROOTCERT`, `PGREQUIREAUTH`) ficam. |
| Navegador | `HorarioBrasiliaNavegadorTests.test_navegador_tempo_real_recarga_e_conversa_no_horario_de_brasilia` | Admin num Chromium em Asia/Tokyo e cliente em America/Los_Angeles, com Socket.IO real. O cliente abre o chamado pelo formulário, com HTML no assunto. Verifica:<br>• o tempo real e o contador do sininho;<br>• a recarga e a lista do admin;<br>• a resposta do admin às 14:52 recebida em tempo real pelo cliente;<br>• a conversa dos dois papéis;<br>• o texto, o `datetime` e o `title` de cada `<time>`;<br>• nenhum `<img>` ou `<script>` injetado, nenhum script executado e nenhum erro de JavaScript. |

**Resultado no head final `5e9cefb`: 23 de 23 OK, nenhum pulado.**
- Local (`testes/modulo_novo_5e9cefb.log`): PostgreSQL 16.15 e Chromium, com a cópia do cliente Socket.IO conferida por hash.
- CI (execução 122, F.4): PostgreSQL do Ubuntu 24.04 e Chrome.
- Contra o código anterior: 18 dos 23 falham (F.2).

### F.2 Os testes novos detectam o código antigo e mutações da correção

**Contra o código anterior.** O módulo final foi rodado sobre a `main` `04d8422`, com `horario.py`, o diagnóstico e o módulo de testes copiados: **18 dos 23 testes falham**.
- Todos os testes que exercitam a aplicação falham.
- Os 5 que passam testam só as funções novas copiadas junto: o formatador e o diagnóstico.
- Log: `testes/testes_novos_contra_codigo_anterior_04d8422.log`.

**Teste de mutação.** Cada um dos 29 mutantes desfaz uma parte da correção numa cópia do head `5e9cefb`. Os 23 testes do módulo rodaram contra cada mutante, em SQLite, PostgreSQL e navegador. Resultado: **29 de 29 mortos** (`testes/mutacao_resultado_final.json`).

| Grupo | Mutantes | Morto por |
|---|---|---|
| Tempo real | M01 volta a `datetime.now()`; M02 relê o relógio em vez do valor gravado; M16 JavaScript sem `datetime`; M20 JavaScript sem `escapeHtml` no texto | A, B, C, D, E, F, G, I, J, L e navegador |
| Telas | M03 sininho recarregado com `strftime`; M04 conversa sem conversão; M05 lista do cliente com a data UTC; M06 lista do admin só com a abertura; M07 "Resolvido em" após a reabertura; M17 `title` sem rótulo; M21 e M22 "Resolvido em" com a última atualização; M24 aviso do cliente após a reabertura | A, B, C, F, G, H, I, J, K e navegador |
| Tipo da coluna | M08 entrega o datetime com fuso ao driver; M09 lê o valor sem fuso como horário local do processo; M18 aceita valor sem fuso; M19 tira o fuso sem converter para UTC | C, J, K e L |
| Default e rotas | M10 notificação volta ao `CURRENT_TIMESTAMP`; M14 e M15 respostas com o relógio real; M23 resposta regrava o fechamento; M25 resolução com duas leituras | A a L |
| Formatador | M11 deslocamento fixo de −3 h; M12 ISO sem normalizar; M13 data curta em UTC | E, A, L e B |
| Diagnóstico | M26 apaga todas as `PG*`, inclusive as de TLS; M27 sem TLS para host remoto; M28 aceita banco sem o esquema; M29 respeita `PGTZ` | J e `DiagnosticoFusoHorarioTests` |

Os mutantes M19 a M29 vieram da revisão independente (F.5). Na revisão, os sete marcados como sobreviventes (M19 a M25) passavam pela suíte; os testes acrescentados em `5e9cefb` os matam.

### F.3 Suíte oficial completa

A suíte rodou no head final `5e9cefb` com a configuração da CI:
- SQLite em memória, PostgreSQL 16.15 descartável e Chromium, com as cópias íntegras da CDN;
- as mesmas variáveis sintéticas do workflow, sem credenciais e sem acesso à rede externa.

**Resultado: 927 testes, OK, nenhum pulado e nenhuma falha** (`testes/suite_completa_5e9cefb.log`).
- São os 904 testes que já existiam na `main` `04d8422`, todos passando, mais os 23 novos.
- A CI deu o mesmo número no mesmo commit (F.4).
- Entre os testes existentes estão os de prazos contratuais (`tests/test_contratos_prazos.py`) e os de horário do PDF (`tests/test_pdf_export_horario.py`). Esses testes e os módulos que eles cobrem (`contract_policy.py` e `pdf_export.py`) não foram alterados, e todos passam.
- O único teste existente alterado é o `tests/test_overflow_navegador.py`, só nos dados fictícios (D, item 14, e seção I).

### F.4 CI do GitHub

Workflow `NEXO Security CI`, com dois jobs: `security-sqlite-browser` (suíte completa com PostgreSQL descartável e Chrome) e `security-postgresql` (cinco módulos em PostgreSQL real). Execuções na branch do PR:

| Execução | Commit | Resultado |
|---|---|---|
| [118](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40933460526) | `5d37a7f` | Vermelha. 921 testes, com 1 falha anterior a este PR: `test_overflow_navegador.OverflowNavegadorTests.test_pareto_acompanha_o_redimensionamento` (seção I). Todos os testes de horário passaram. |
| [119](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40936399824) | `5999877` | Cancelada pelo push seguinte (`cancel-in-progress` do workflow). |
| [120](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40936968526) | `3c57ba7` | Verde: 922 testes OK. |
| [121](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40940369924) | `947d9a9` | Verde: 924 testes OK. |
| [122](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/40943952415) | `5e9cefb` | **Verde nos dois jobs: 927 testes OK, nenhum pulado.** Os 23 testes novos rodaram, inclusive o J (PostgreSQL) e o de navegador: as quatro cópias da CDN, entre elas a do cliente Socket.IO, conferiram com o hash SRI. |

O commit deste relatório só acrescenta arquivos em `Docs/` e dispara mais uma execução; o resultado fica registrado no PR.

### F.5 Revisão independente

**Como foi feita.** Fluxo de trabalho com seis lentes independentes: corretude, tempo real, telas, banco e legado, segurança, e testes e requisitos. Cada lente leu o diff e o código, reproduziu o que podia numa cópia e devolveu achados com evidência. Cada achado passou depois por um verificador independente, instruído a tentar refutá-lo.

**Resultado.** As lentes registraram 11 achados, agrupados abaixo em 10 linhas (a 9 reúne dois). Nove linhas foram tratadas.
- **Linhas 1, 3, 4, 5, 7, 8 e 9:** um teste falha sem a correção. Esses testes são:
  - os mutantes M19 a M29 da F.2;
  - para a linha 1, o log `resposta_uma_leitura_sem_correcao_falha.log`;
  - para as linhas 3 e 4, os testes do diagnóstico.
- **Linhas 6 e 10:** mudanças de texto, no aviso da CI e no nome e na docstring do cenário D.
- **Linha 2:** mantida por decisão de projeto.

**Verificação.** Ela rodou depois das correções, sobre os heads `947d9a9` a `5e9cefb`; o código das rotas é o mesmo nesses commits.
- Os 10 achados tratados não se reproduzem mais. Para cada um, o verificador indicou o commit que o resolveu.
- A linha 2 se reproduz e foi classificada como real, de gravidade baixa. Os detalhes e a opção para o proprietário estão na J.2.

| # | Lente | Achado | Gravidade | Situação |
|---|---|---|---|---|
| 1 | corretude, tempo real e telas | Numa resposta, a atualização do chamado e a mensagem vinham de duas leituras do relógio. Na virada do minuto, a "Última atualização" ficava antes da "Última mensagem". | baixa | Corrigido em `3c57ba7`: uma leitura por resposta. O teste falha sem a correção. |
| 2 | corretude | A abertura, a primeira mensagem e a notificação, assim como a notificação de uma resposta ou de uma resolução, têm cada uma a própria leitura do relógio. Na virada do minuto, rótulos da mesma ação podem diferir em 1 min. | baixa | Mantido por decisão de projeto. A Etapa 8 pede para não forçar a abertura e as mensagens a coincidir, e a notificação é um evento próprio (teste F). O verificador confirmou o efeito: 0,11% das ações com 20 ms de ida e volta ao banco e 0,91% com 180 ms. A opção para o proprietário está na J.2. |
| 3 | banco e legado | O diagnóstico dava "compatível" sem confirmar o esquema nem o fuso da aplicação (banco vazio; `PGTZ` ou `PGOPTIONS` no terminal). | média | Corrigido em `947d9a9`. |
| 4 | banco e legado | Uma URL malformada gerava traceback com trecho da senha e código 1. | baixa | Corrigido em `947d9a9`: código 2, sem a senha. |
| 5 | segurança | O `947d9a9` apagava `PGSSLMODE` e `PGSSLROOTCERT`. Num ataque intermediário (MITM), a senha poderia sair em texto claro. | média | Corrigido em `a66fb53`: preserva TLS e autenticação e exige TLS para host remoto. |
| 6 | segurança | Se o download do Socket.IO falhasse, a CI ficava verde sem o teste de tempo real, e o aviso citava outro conjunto de testes. | baixa | O aviso agora nomeia o teste pulado (`5e9cefb`). A indisponibilidade da CDN não reprova a CI, a mesma política já usada para Bootstrap e Plotly. |
| 7 | testes | A conversão para UTC na escrita não tinha teste. | média | Teste em SQLite e no J (`5e9cefb`). |
| 8 | testes | O escape do texto no sininho em tempo real não era conferido no navegador. | média | Teste de navegador com HTML no assunto (`5e9cefb`). |
| 9 | testes | "Resolvido em" só era conferido quando igual à última atualização; a leitura única ao resolver não tinha teste. | baixa | Roteiro com resposta após resolver e teste com relógio que avança (`5e9cefb`). |
| 10 | testes | O cenário D afirmava como causa o que é hipótese. | baixa | Renomeado e redigido como ilustração (`5e9cefb`). O código anterior foi executado de fato com UTC−1 no `repro.py` (C.1). |

**Sem achados.** As lentes verificaram, sem encontrar problema:
- O payload só tem strings e é montado antes do commit.
- Com rollback, rollback de SAVEPOINT ou falha no COMMIT, nada é entregue.
- O texto em tempo real e o da recarga são idênticos em SQLite e em PostgreSQL.
- Injeção de HTML (com `<img onerror>`, `<script>`, `<time>` e `<small>` falsos): nenhum elemento injetado.
- Isolamento entre empresas.
- O número de consultas por página é igual ao da `main` (sem N+1).
- Os arquivos CRLF foram preservados.
- Todos os `<time>` são válidos.
- O esquema não muda: `compare_metadata` vazio.
- O processo do J é isolado: nenhuma conexão sai dele, mesmo com `DATABASE_URL` ou `PG*` apontando para um servidor falso.

**Fora do escopo.** As lentes registraram pontos anteriores a este PR, que estão na seção J.

## G. Evidências

O pacote `NEXO_CORRECAO_HORARIO_BRASILIA_SUPORTE.zip` fica no ambiente desta sessão, fora do repositório; o caminho real está na mensagem de entrega. Ele não contém credenciais, dados reais de clientes nem dumps de produção. Os únicos usuários são fictícios (`@example.invalid`), e as senhas aleatórias deles não foram registradas.

| Pasta/arquivo | Conteúdo |
|---|---|
| `RELATORIO_CORRECAO_HORARIO_NOTIFICACOES_SUPORTE_PARA_CHATGPT.md` | Este relatório. |
| `capturas/antes_*.png` (7) e `capturas/depois_*.png` (7) | O mesmo roteiro antes (`04d8422`) e depois (`5e9cefb`), com o relógio real, servidor e banco em UTC (como em produção) e Socket.IO real. Telas: sininho do admin em tempo real e recarregado, lista do admin, conversa do admin com o painel, sininho do cliente em tempo real, conversa e lista do cliente. Os ícones não aparecem porque a fonte de ícones vem de uma CDN bloqueada no ambiente isolado. |
| `matriz/capturas_antes_matriz.json`, `matriz/capturas_depois_matriz.json` | O que as capturas mostram, como dado: o texto lido no DOM em cada ponto, o horário real de Brasília e o UTC no momento do evento. As capturas não são a prova; estes valores são. |
| `matriz/matriz_horarios_reproducao.md` e `.csv` | A matriz da seção C.1: oito combinações de fuso do processo × TimeZone da sessão, antes e depois. O `.csv` traz cada leitura: exibido, real e diferença. |
| `reproducao/resultados/*.json` (16) | A saída bruta do `repro.py` em cada combinação: antes = `04d8422`, depois = `5e9cefb`. |
| `scripts_de_homologacao/` | `repro.py` (matriz), `captura.py` (capturas) e `mutacao.py` (29 mutantes). |
| `testes/suite_completa_5e9cefb.log` | A suíte oficial completa no head final, com PostgreSQL e navegador (F.3). |
| `testes/modulo_novo_5e9cefb.log` | Os 23 testes novos no head final (F.1). |
| `testes/testes_novos_contra_codigo_anterior_04d8422.log` | Os mesmos 23 testes contra o código anterior: 18 falham (F.2). |
| `testes/mutacao_resultado_final.json` | Os 29 mutantes e os testes que mataram cada um (F.2). |
| `testes/ensaio_postgresql_cenario_J.json` | O relatório do processo do cenário J no head final: valores brutos gravados em cada TimeZone de sessão, registro legado e diagnóstico. |
| `testes/pareto_*.log`, `testes/test_overflow_navegador_com_correcao.log` | Reprodução e correção do teste instável do Pareto (I). |
| `testes/resposta_uma_leitura_sem_correcao_falha.log` | O teste da leitura única falhando sem a correção (F.5, achado 1). |
| `ci/execucao_122_5e9cefb_suite.log`, `ci/execucao_122_5e9cefb_copias_cdn.log` | Os logs da CI no head final: a suíte (927 OK) e a conferência SRI das cópias da CDN (F.4). |
| `revisao/revisao_independente_resultado.json` | O resultado da revisão independente: os achados de cada lente, o veredito do verificador e os resumos (F.5). |
| `arquivos_modificados.txt`, `referencias.txt` | O `git diff --stat` contra `04d8422`, os commits, o PR e as execuções da CI. |

## H. Segurança

- **Injeção de HTML.**
  - Os campos de horário são gerados pelo servidor a partir do instante (formato fixo, conferido por expressão regular no teste L). Nenhum dado do usuário chega a eles: um assunto com `<img onerror>` e um horário falso dentro do texto não mudam `hora`, `hora_completa` nem `instante`.
  - No sininho, o JavaScript cria o `<time>` pelo DOM (`setAttribute` e `textContent`). O texto da notificação continua passando pelo `escapeHtml`.
  - No servidor, o Jinja escapa tudo (autoescape).
- **Entrega.**
  - Continua só depois do COMMIT. O rollback descarta o payload (teste L, além dos testes de sessão existentes).
  - O payload é montado antes do commit e só com strings: nada de objeto ORM nem de `datetime`, o que evita os dois modos de falha silenciosa apontados na auditoria (leitura após commit e serialização).
- **Isolamento.** Sala por usuário e credencial, FOR SHARE e reverificação de acesso sem alteração. Em todas as etapas do roteiro I, o papel que não deveria ser notificado não recebe nada.
- **Diagnóstico.**
  - É somente leitura: `READ ONLY`, `rollback`, e o teste J confere `transaction_read_only = on` e que o número de linhas não muda.
  - Não exibe credencial nem a mensagem do driver.
  - Exige TLS para host remoto e preserva as variáveis de TLS do terminal, para a senha não trafegar em texto claro (achado 5 da F.5).
- **CI.** O cliente Socket.IO é baixado do jsdelivr e só usado se o hash SRI oficial conferir; sem a cópia íntegra, o teste de navegador é pulado.
- **Dados e acesso.**
  - Os dados são fictícios (`@example.invalid`), e as senhas, aleatórias por execução, ficam fora dos relatórios.
  - Os testes de PostgreSQL usam um cluster privado em socket Unix, num processo com ambiente saneado.
  - Nenhum acesso a Render, Supabase ou produção.

## I. GitHub

- **Branch:** `fix/nexo-horario-brasilia-notificacoes-suporte`, criada a partir da `main` `04d8422`. A `main` não mudou durante o trabalho (conferido com `git fetch` antes do último push).
- **PR:** [#37](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/37), "NEXO: correção dos horários de Brasília no sininho e no suporte", em **rascunho**, base `main`, sem conflitos.
- **O que não foi feito, por instrução:** merge, deploy e qualquer alteração no Render ou no Supabase.

**Commits** (em ordem):

| Commit | Mensagem | Conteúdo |
|---|---|---|
| `9d897f7` | fix(timezone): padronizar horario das notificacoes | `horario.py`, `InstanteUTCSemFuso`, defaults, filtros e macro, diagnóstico |
| `b72248c` | fix(realtime): corrigir timestamp do sininho SocketIO | Payload a partir do instante gravado e `<time>` pelo DOM |
| `4e9f5d2` | fix(suporte): corrigir horarios dos chamados e mensagens | Conversa, cabeçalhos, listas, painel e rotas |
| `5d37a7f` | test(timezone): validar horario de Brasilia nos eventos | Cenários A–L, PostgreSQL, navegador e CI |
| `5999877` | test(dashboard): Pareto deterministico nos dados do teste de layout | Correção do teste instável, portada (abaixo) |
| `3c57ba7` | fix(suporte): uma leitura do relogio por resposta ao chamado | Achado 1 da revisão |
| `947d9a9` | fix(diagnostico): exigir o esquema do NEXO e ignorar PG* do terminal | Achados 3 e 4 |
| `a66fb53` | fix(diagnostico): preservar TLS do terminal e exigir TLS para host remoto | Achado 5 |
| `5e9cefb` | test(timezone): cobrir as lacunas apontadas pela revisao independente | Achados 6 a 10 |
| este commit | docs(timezone): registrar auditoria e evidencias | Este relatório |

**CI vermelha em `5d37a7f`, causa anterior a este PR.** O teste `test_pareto_acompanha_o_redimensionamento` é instável: todas as análises dos dados de teste são publicadas com a mesma `data_conclusao`, e o desempate por `data_criacao` (1 s de resolução no SQLite) depende de o setUp cruzar ou não a virada de um segundo. A falha já tinha sido diagnosticada no [PR #36](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/36), mas o patch proposto lá não entrou na `main` antes do merge. Nesta branch:
- a falha foi reproduzida com `time.sleep(1.1)`;
- as mesmas quatro linhas foram portadas para os dados do teste, sem mudar nenhuma verificação;
- o teste passou com o mesmo `sleep`.

Explicação publicada no PR: [comentário](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/37#issuecomment-6505797060). Desde então, a CI ficou verde em todas as execuções (F.4).

## J. Pendências

### J.1 Antes do merge e do deploy (proprietário)

1. **Rodar o diagnóstico somente leitura** (E.4) com a `DATABASE_URL` da aplicação: `python scripts/diagnosticar_fuso_horario.py`.
   - Código 0: pode publicar.
   - Código 1: não publicar; seguir o plano da E.5.
   - Código 2: conferir a URL e repetir.

   Este trabalho não teve acesso ao banco de produção, por instrução. A premissa de sessão em UTC (C.2) continua não verificada até essa execução.
2. **Conferir o Auto-Deploy no painel do Render.** O `render.yaml` declara `autoDeployTrigger: 'off'`, mas quem decide é a configuração do serviço no painel. Se o Auto-Deploy estiver ativo, o merge na `main` pode iniciar uma implantação automaticamente. O PR fica como rascunho, aguardando aprovação; nenhum merge ou deploy foi feito.
3. **Depois do deploy, confirmar as "cerca de 2 h"** (C.3).
   - Abrir um chamado de teste e comparar o sininho com a hora oficial de Brasília (por exemplo, a do Observatório Nacional), não com o relógio de um aparelho.
   - Se o aparelho de comparação mostrar 1 h a mais que a hora oficial (UTC−2 em vez de UTC−3), a hipótese (b) se confirma: o sistema dele tem regra de horário de verão antiga e precisa de atualização.

### J.2 Opções futuras do mesmo tema (não executadas)

- **Migração para `timestamptz`** e troca do `DEFAULT CURRENT_TIMESTAMP` por `timezone('utc', now())` nas cinco colunas (E.3). Isso tornaria o tipo explícito no banco e cobriria inserções fora do ORM. Ela precisa de janela de manutenção, porque o `ALTER COLUMN` trava as tabelas, e de autorização do proprietário. Não é necessária para esta correção.
- **Achado 2 da revisão: leituras próprias do relógio na mesma ação** (mantido como está, por decisão de projeto).
  - O verificador independente reproduziu o efeito. Quando o minuto vira entre as leituras do relógio, que ficam a poucos milissegundos umas das outras, cada uma no seu próprio flush, rótulos da mesma ação podem diferir em 1 minuto. Por exemplo: "aberto em 14:34", primeira mensagem às 14:35 e sininho do admin às 14:35. Também pode acontecer entre uma resposta e a notificação da contraparte.
  - Cada rótulo continua no horário de Brasília certo do próprio registro, e a ordem é preservada.
  - Medição do verificador, com latência simulada por comando SQL: 0,11% das ações com 20 ms de ida e volta ao banco, 0,36% com 70 ms e 0,91% com 180 ms.
  - Não foi alterado porque a Etapa 8 pede que a abertura e as mensagens não sejam forçadas a coincidir ("poderão ser ligeiramente diferentes por causa do processamento da requisição"). Uma notificação é um evento próprio, criado depois da mensagem.
  - Se o proprietário preferir que a notificação repita o instante da mensagem ou da resolução que a gerou, a mudança é pequena: um parâmetro `instante` opcional em `criar_notificacao`, `notificar_admins` e `notificar_clientes_empresa`. As rotas de resposta e de resolução já têm esse instante. O teste F passaria a exigir igualdade.
- **Mesma natureza, fora do escopo pedido** (instantes exibidos sem conversão; a Etapa 11 pede não ampliar para análises e contratos):
  - `templates/admin/lixeira.html:42`: `deletado_em` exibido com hora (`%d/%m/%Y %H:%M`). É gravado por `datetime.now(timezone.utc)` (`company_security.excluir_empresa`) numa coluna sem fuso, o mesmo mecanismo da C.1. Com servidor e banco em UTC, apareceria 3 h adiantado; não foi reproduzido neste trabalho.
  - Só a data, que pelo mesmo mecanismo erraria entre 21:00 e 23:59 de Brasília:
    - `data_criacao` da análise em `templates/admin/analises.html:80` e `templates/admin/analises_empresa.html:85`;
    - `data_publicacao` do relatório em `templates/cliente/historico.html:40`;
    - `data_atualizacao`/`data_criacao` do Guia em `templates/admin/guia.html:49`.

    A correção seria a mesma: `m.horario(..., 'data')` e o tipo `InstanteUTCSemFuso` nessas colunas, com testes próprios.
  - Os períodos e as vigências contratuais são do tipo `Date` (datas de calendário) e estão corretos.
  - O PDF tem formatação própria em Brasília (`pdf_export.formatar_data_hora`), preservada por instrução. Unificar com `horario.py` é opcional.

### J.3 Problemas não relacionados, encontrados durante a análise (atividade futura)

1. **Reabertura pelo cliente não limpa `data_fechamento`** (`blueprints/cliente.py`, rota de resposta: RESOLVIDO → EM_ATENDIMENTO). A mudança de status pelo admin limpa. A exibição já está protegida: "Resolvido em" e o aviso do cliente só aparecem com o status RESOLVIDO. Mesmo assim, o dado fica desatualizado.
2. **Marcar como RESOLVIDO um chamado já resolvido** notifica o cliente de novo, reenvia o e-mail e regrava o `data_fechamento`.
3. **O e-mail de resolvido é enviado antes do `commit`** (`email_ticket_resolvido` em `alterar_status`). Se o commit falhar, o cliente recebe o e-mail de uma resolução que não ficou gravada. A notificação do sininho, ao contrário, só sai depois do commit.
4. **A badge do sininho é classificada pelo texto da notificação** (`classificar_notificacao`). Um assunto de chamado com certas palavras pode mudar a cor e o rótulo da badge. É só cosmético; o texto é escapado.
5. **Clicar no toast do tempo real abre o link direto**, sem passar por `/notificacoes/<id>/abrir`, então a notificação continua não lida. O item do sininho passa pela rota e marca como lida.
6. **Os scripts e folhas de estilo da CDN no `base.html`** (Bootstrap, Bootstrap Icons, Plotly e Socket.IO) não têm o atributo `integrity` (SRI) nem `crossorigin`.
7. **Os handlers do Socket.IO (`@socketio.on` em `realtime.py`) são registrados quando o módulo é importado.** Essa importação acontece dentro de `create_app`, depois do `socketio.init_app`. Num processo com mais de uma app, o que só acontece nos testes, os handlers ficam apenas no servidor da primeira. Por isso o módulo de testes novo importa `realtime` antes da primeira `create_app`. Em produção há uma app por processo e o efeito não aparece.
