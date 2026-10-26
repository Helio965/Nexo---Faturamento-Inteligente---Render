# Relatório NEXO-AJ-00 para revisão

> **Nota de integração (26/10/2026).** Documento produzido na pasta local (sem `.git`) e publicado no repositório oficial `Helio965/Nexo---Faturamento-Inteligente---Render` pela integração de 26/10/2026. A base do ZIP foi confirmada por comparação de conteúdo: o commit `ff8c2d8` da `main` (o `faa59d9` do comentário do ZIP não aparece em nenhuma branch nem PR deste repositório). Afirmações como "sem `.git`", "sem acesso ao remoto" e "VERSÃO NÃO VERIFICADA" descrevem a execução original e foram superadas pelo [relatório da integração](../INTEGRACOES/RELATORIO_INTEGRACAO_GITHUB_ZIP_2026_10_26.md). Caminhos locais com o nome do usuário do Windows foram anonimizados como `%USERPROFILE%`; o restante do conteúdo foi preservado.

Entrega da Etapa 00 (subetapas 0.1 e 0.2): preparação, baseline e proteção do projeto NEXO: Faturamento Inteligente. Detalhes técnicos em [`NEXO_AJ_00_BASELINE.md`](NEXO_AJ_00_BASELINE.md); andamento dos prompts em [`CONTROLE_PROMPTS.md`](CONTROLE_PROMPTS.md).

**Status final: CONCLUÍDO PARA REVISÃO** (depois do complemento; ver seção 0). A NEXO-AJ-00 está registrada como `EXECUTADO / AGUARDANDO REVISÃO` no controle. Nenhuma etapa foi aprovada automaticamente: "concluído para revisão" quer dizer que a entrega está completa e espera a aprovação humana.

**Histórico da entrega:**

| Momento | Status | Motivo |
|---|---|---|
| Primeira entrega, 25/10/2026 11:25 | PARCIAL/BLOQUEADO | Faltava `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md`; índice dos 27 prompts e numeração dos ajustes 01 a 09 pendentes |
| Correção, fase sem o mapa: 25/10/2026, das 11:47 às 12:09 | PARCIAL/BLOQUEADO (inalterado) | O prompt corretivo chegou sem o mapa e três buscas não o encontraram. Às 11:53 foi tirado o manifesto de referência (268 arquivos). Nenhum arquivo foi alterado |
| Correção, complemento com o mapa: 25/10/2026, das 12:55 (mapa recebido) às 13:21 | CONCLUÍDO PARA REVISÃO | A primeira alteração foi às 12:56 (cópia do mapa). Mapa lido; controle dos 27 prompts completado; auditoria independente com 21 apontamentos, todos corrigidos; reauditoria com 2 apontamentos novos de gravidade baixa e 1 resolvido só em parte, também corrigidos; conferências finais aprovadas (seções 0.5 e 0.6) |

A **correção** inteira vai das 11:47 às 13:21. O **complemento** propriamente dito, com o mapa e todas as alterações de arquivos, vai das 12:55 às 13:21.

As seções 1 a 12 são a primeira entrega. Onde o complemento mudou algo, há uma marca **[Complemento]**. Testes, achados de segurança e evidências da primeira entrega foram mantidos sem alteração.

---

## 0. Complemento de 25/10/2026: mapa oficial e controle dos 27 prompts

### 0.1 O que foi corrigido

- **Índice dos 27 prompts.** A primeira versão de `CONTROLE_PROMPTS.md` tinha só `NEXO-AJ-00` e `NEXO-AJ-06.1`, com 26 linhas numeradas reservadas (#2 a #27); a 06.1 ficava numa tabela à parte. O texto da primeira versão dizia "25 linhas", o que não batia com a própria tabela. Agora o controle tem os 27 IDs oficiais, cada um com atividade, tipo, dependências, posição na ordem recomendada, status, evidência e aprovação.
- **Texto do mapa sem paráfrase.** Escopo e critério de aceite dos 27 prompts, as 8 regras gerais (mapa:331-340) e o checklist de saída (mapa:352-360) estão **transcritos literalmente**, com as linhas do mapa. Isso foi conferido por script (seção 0.5, C4).
- **Registro por ID.** Foi incluído o "Registro de execução por ID" com datas, arquivos alterados, testes e ponto de reversão, como pede mapa:364. O backup desta etapa passou a se chamar "ponto de reversão pré-AJ-00", para não ser confundido com o "checkpoint de versão" que o mapa pede depois da aprovação (mapa:360) e que segue pendente.
- **Dependências da 00.** O mapa não declara dependências para `00`, `01`, `02` e `08`; os quatro estão registrados assim, sem inferência.
- **Histórico preservado.** A tabela de buscas pelo mapa feitas na primeira entrega foi mantida no histórico do controle. As versões integrais anteriores dos três documentos estão em `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\evidencias\complemento_mapa\documentos_antes_do_complemento\`.
- **Status da NEXO-AJ-00.** Passou de "PARCIAL — AGUARDANDO REVISÃO" para `EXECUTADO / AGUARDANDO REVISÃO`. Os outros 26 seguem `NÃO EXECUTADO`. Nenhum foi marcado como aprovado.
- **Ajustes 01 a 09.** A primeira entrega supôs que fossem os nove pedidos das imagens e marcou isso como não comprovado. O mapa não usa a palavra "ajuste". **Interpretação, a confirmar na revisão humana:** os "ajustes 01 a 09" correspondem às etapas 01 a 09 da matriz do mapa (mapa:22-33), pelo prefixo comum `NEXO-AJ`. A seção 6 foi refeita por etapa, mantendo o pedido original de cada item, e `CONTROLE_PROMPTS.md` relaciona pedidos e prompts pelo escopo do mapa.
- **Ponto de reversão desatualizado.** `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente.zip`, citado como estado pós-0.2A, foi regravado às 11:28 de 25/10 fora desta execução. Hoje ele tem os 268 arquivos pós-AJ-00 (idênticos por hash à pasta naquele momento; SHA-256 `1C359F29222538590F2CC5E9E615A09B5F870625AE73C0637BDDFDCDBBB95720`). Foram anotadas a seção 8 deste relatório e a seção 1.3 do baseline. A seção 8 do baseline não cita esse ZIP e ficou como estava.

### 0.2 Fonte e documentos modificados

O mapa veio no ZIP `%USERPROFILE%\Downloads\NEXO_MAPA_27_PROMPTS_PARA_CLAUDE_CODE.zip` (7.026 bytes, 12:47, SHA-256 `D14E19BD68CCA5174C1BC0475D0C946A37FE566DC453EACF295D75D88F402748`, uma entrada). O ZIP foi extraído numa pasta nova e vazia da área temporária desta sessão, fora do projeto, e o mapa foi lido integralmente (364 linhas). A pasta temporária não é evidência; a evidência é o mapa na raiz, com o hash conferido.

| Ação | Arquivo |
|---|---|
| Acrescentado (cópia idêntica à do ZIP, SHA-256 `B59E9D7213273BC40D28F8BB61D5EC402F73B9B3A7B27A9D5790E630EFDEED67`) | `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md` (raiz, junto de `app.py`) |
| Reescrito (versão 2, com histórico da versão 1 no fim) | `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md` |
| Editado (este complemento e as marcas [Complemento]) | `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` |
| Editado (notas datadas sobre o mapa e o ZIP da pasta-mãe; nenhuma evidência removida) | `Docs/AJUSTES_NEXO_2026/NEXO_AJ_00_BASELINE.md` |

**Nenhum arquivo de código Python, HTML, CSS, JavaScript, teste, migração, banco ou configuração de implantação foi alterado** (verificação na seção 0.6).

**Fora da pasta do projeto**, em `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\evidencias\complemento_mapa\`:

| Arquivo | O que é |
|---|---|
| `conferir_controle.py` | Verificador de estrutura (C3) |
| `conferir_literal.py` | Verificador de literalidade (C4) |
| `controle_mutante.md`, `controle_mutante_literal.md` | Cópias com erros injetados, usadas para testar os verificadores (C5) |
| `manifesto_pre_correcao_AJ00.json` | Manifesto de referência SHA-256, tirado às 11:53, antes de qualquer alteração desta correção (a primeira foi às 12:56) (C6) |
| `documentos_antes_do_complemento\` | Versões da primeira entrega dos três documentos |

### 0.3 Prompts cadastrados

**27 prompts:**

- **4 de ETAPA:** `NEXO-AJ-00`, `01`, `02` e `08`.
- **23 de SUBETAPA:**
  - 03.1 a 03.4 (4);
  - 04.1 a 04.3 (3);
  - 05.1 a 05.5 (5);
  - 06.1 a 06.4 (4);
  - 07.1 a 07.4 (4);
  - 09.1 a 09.3 (3).

**Status:** 1 `EXECUTADO / AGUARDANDO REVISÃO` e 26 `NÃO EXECUTADO`.

### 0.4 Dependências registradas

Exatamente como declaradas no mapa:

| Prompt | Depende de |
|---|---|
| `03.1` | `00`; `07.1` |
| `03.2` | `03.1` |
| `03.3` | `03.1`; `03.2` |
| `03.4` | `03.3` |
| `04.1` | `03.3` |
| `04.2` | `04.1` |
| `04.3` | `04.2` |
| `05.1` | `03.1`; `06.1` |
| `05.2` | `03.4`; `05.1` |
| `05.3` | `05.1`; `05.2` |
| `05.4` | `03.2`; `05.1` |
| `05.5` | `05.2`; `05.3`; `05.4` |
| `06.1` | `00` |
| `06.2` | `05.4`; `06.1` |
| `06.3` | `06.1` |
| `06.4` | `06.2`; `07.1` |
| `07.1` | `00` |
| `07.2` | `07.1` |
| `07.3` | `07.1`; `06.4` |
| `07.4` | `07.1`; `07.3` |
| `09.1` | `01`–`08` (aplicáveis) |
| `09.2` | `09.1` |
| `09.3` | `09.1`; `09.2` |

O mapa não declara dependências para `00`, `01`, `02` e `08`. Isso foi registrado assim, sem inventar dependências; a posição deles vem da ordem recomendada.

**Ordem recomendada** (mapa:317-329):

1. `00`
2. `06.1`
3. `07.1`
4. `01` e `02`
5. `03.1` a `03.4`
6. `04.1` a `04.3`
7. `05.1` a `05.5`
8. `06.2` a `06.4`
9. `07.2` a `07.4`
10. `08`
11. `09.1` a `09.3`

### 0.5 Verificações realizadas

| # | Verificação | Resultado |
|---|---|---|
| C1 | Leitura integral do mapa (364 linhas, UTF-8 válido, sem BOM) | Feita |
| C2 | Cópia do mapa na raiz × entrada do ZIP | **APROVADO**: SHA-256 idêntico |
| C3 | `conferir_controle.py`: extrai do mapa os 27 IDs, nomes, tipos, dependências e ordem, compara com cada linha do índice e confere que a ordem respeita as dependências, sem ciclos | **APROVADO: 0 divergências.** 27 linhas; IDs, nomes, tipos, dependências e ordem iguais ao mapa; status `00` = `EXECUTADO / AGUARDANDO REVISÃO`, demais = `NÃO EXECUTADO`; nenhum aprovado; ordem compatível, sem ciclos. **Limite:** não cobre o texto de escopo e aceite, que fica com C4 |
| C4 | `conferir_literal.py`: cada trecho entre aspas do escopo, do aceite, das regras e do checklist precisa existir no mapa exatamente igual e na linha indicada | **APROVADO: 69 trechos literais** (27 × 2 de escopo e aceite, 8 regras, 7 itens do checklist), 0 divergências |
| C5 | Teste dos verificadores: (a) controle com 3 erros injetados (dependência trocada, status aprovado, linha removida); (b) uma única expressão trocada no escopo da 05.1 | **APROVADO**: (a) os 3 detectados (5 alertas); (b) detectado |
| C6 | Integridade por SHA-256: pasta atual × manifesto de referência (11:53, 268 arquivos, anterior a qualquer alteração) | **APROVADO**: resultado final na seção 0.6 |
| C7 | Auditoria independente, somente leitura, com 2 auditores: fidelidade ao mapa; coerência entre documentos e preservação da primeira entrega | 21 apontamentos (1 de gravidade alta, 9 média, 11 baixa), **todos corrigidos**. Detalhes na seção 0.6 |
| C8 | Reauditoria independente, somente leitura, das correções de C7 | 20 dos 21 confirmados como resolvidos; 1 resolvido só em parte (janelas de horário) e 2 novos de gravidade baixa (marcas [Complemento] ausentes; resumo de C7 mais forte que os auditores). **Os 3 foram corrigidos** e reconferidos por C3, C4, C6 e buscas de texto (seção 0.6) |

Os testes automatizados do sistema **não foram reexecutados** neste complemento, porque nenhum arquivo de código mudou. Os resultados da seção 9 (569 testes; 13 falhas, 12 erros e 42 ignorados, todos de ambiente) continuam valendo e **não foram reclassificados**.

### 0.6 Resultado final do complemento

**Integridade (C6), na conferência final:**

| Item | Valor |
|---|---|
| Manifesto de referência (11:53, antes de qualquer alteração) | 268 arquivos |
| Pasta depois do complemento | 269 arquivos |
| Inalterados | 265, inclusive todo o código, testes, templates, CSS, JS, migrações e configuração |
| Editados | 3: `CONTROLE_PROMPTS.md`, `RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` e `NEXO_AJ_00_BASELINE.md` |
| Acrescentado | 1: `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md`, na raiz |
| Removidos | 0 |

**Auditoria independente (C7):** os auditores confirmaram que os 27 IDs, tipos, dependências e ordem são iguais aos do mapa e que o status está correto (só a 00 executada e nenhum prompt aprovado). O mapa, na data dele, registrava os 27 como não executados (mapa:364). Também confirmaram que a seção 9 (testes) e a seção 7 (segurança) ficaram idênticas à primeira entrega, sem reclassificação, e que a seção 8 (backup) só recebeu um acréscimo marcado [Complemento], sem remoção. Os 21 apontamentos foram corrigidos assim:

| Apontamento | Correção |
|---|---|
| Resumos de escopo e aceite mais amplos ou mais fracos que o mapa, com qualificadores perdidos ("uploads que iniciem entregas", "explicitamente permitidas", "indevidamente", "quando necessário", "eventualmente", "contato", "sem declarar tarefas não executadas como concluídas" etc.) | Substituídos pela transcrição literal do mapa, conferida por C4 |
| Resumo das regras do mapa sem qualificadores ("manter histórico de SUSPENSA dentro das regras", "segundo regra contratual" etc.) | Regras transcritas literalmente |
| Faltavam o checklist de saída do mapa e o registro por ID com datas, testes e arquivos | Acrescentados; o backup passou a "ponto de reversão pré-AJ-00", e o checkpoint de versão pós-aprovação ficou como pendente |
| A 00 aparecia como "Nenhuma (primeiro prompt)" | Passou a "Não declaradas no mapa", igual às outras ETAPAs |
| "Ajustes 01 a 09 = etapas 01 a 09" apresentado como fato | Marcado como interpretação, a confirmar |
| O marco de validação era descrito como "por prompt" | Corrigido: o marco fecha cada etapa; a parada a cada prompt vem de mapa:15, 340 e 359 |
| "25 linhas reservadas" | Corrigido para 26, com registro da inconsistência da versão 1 |
| As buscas pelo mapa da primeira entrega tinham sumido; a citação histórica estava encurtada | Tabela de buscas reposta no histórico do controle; citação integral na seção 12; caminho das versões anteriores informado |
| A seção 0.6 remetia a uma "seção 0.8" inexistente | Preenchida |
| Horários adiantados ("13:10") e manifesto das 11:53 fora da janela declarada | Horários reais, incluindo as tentativas das 11:47 às 12:09 |
| "Seções 8 e 1.3 do baseline anotadas" (a seção 8 do baseline não foi tocada) | Corrigido |
| Critérios 12 e 13 apontavam para "item h" e "item i", que não existem mais | Passaram a apontar para as etapas 07 e 08 |
| A seção 6 perdeu a coluna "Pedido", com os valores R$ 150/300/650 e "DNS: nome em vez de IP" | Coluna restaurada |
| Artefatos de evidência fora do projeto não estavam listados | Listados na seção 0.2 |

**Reauditoria (C8):** dos 21 apontamentos, 20 foram confirmados como resolvidos. Os três pontos restantes foram corrigidos:

| Apontamento | Correção |
|---|---|
| Janelas de horário diferentes (11:47 ou 12:55) e manifesto das 11:53 chamado de "antes do complemento" | Termos separados: **correção** (11:47 às 13:21), com a fase sem o mapa (11:47 às 12:09), e **complemento** com o mapa (12:55 às 13:21). O manifesto passou a "manifesto de referência, anterior a qualquer alteração"; a primeira alteração foi às 12:56 |
| Mudanças sem marca [Complemento] no critério 19 e na seção 12; o texto riscado do passo 1 da seção 12 tinha sido reescrito | Marcas acrescentadas; o texto original do passo 1 foi restaurado e riscado, com nota de que o mapa ficou na raiz, e não em `Docs/AJUSTES_NEXO_2026/`, por indicação do responsável |
| O resumo de C7 dizia que o status "bate com o mapa" e que o backup ficou "idêntico" | Reescrito conforme o que os auditores disseram |

### 0.7 Pendências que continuam abertas

Nenhuma delas impede a revisão da AJ-00:

- Confirmar no GitHub que `faa59d9` é a `main` que será implantada (exigência do mapa:333).
- Revisão de produção, preços em produção e Auto-Deploy continuam desconhecidos; dependem de acesso autorizado.
- O backup real do banco de produção **não foi feito nem verificado**. O checkpoint é só da pasta local.
- YAML não validado (PyYAML ausente).
- Suítes PostgreSQL e testes de navegador não executados.
- Confirmar a interpretação de que os "ajustes 01 a 09" são as etapas 01 a 09 do mapa.
- O checkpoint de versão depois da aprovação (mapa:360) só pode ser registrado depois da aprovação humana.
- As dúvidas do responsável sobre logo, regra exata do aviso, preço de contratos vigentes, conta cancelada, LGPD e DNS (`Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/README.md:62-70`) serão tratadas nos prompts correspondentes.
- Divergência menor: o mapa cita a logo antiga só em `templates/base.html` e `templates/auth/login.html` (mapa:345), mas ela aparece em 7 templates, além do "N" da landing (baseline, seção 7). O escopo da `NEXO-AJ-01` ("demais ocorrências reais da marca", mapa:55) cobre isso.

**Próxima subetapa planejada:** `NEXO-AJ-06.1`, correção prioritária do bloqueio CANCELADA. Depende só de `NEXO-AJ-00` (mapa:201) e é a 2ª na ordem recomendada. **Só pode começar depois da aprovação humana desta etapa. Não foi iniciada.**

---

## 1. Identificação

| Item | Valor |
|---|---|
| ID | `NEXO-AJ-00` |
| Data e hora | 25/10/2026: primeira entrega das 10:51 às 11:25. **[Complemento]** Correção das 11:47 às 13:21: fase sem o mapa das 11:47 às 12:09; complemento com o mapa das 12:55 às 13:21 (UTC−3) |
| Executor | Claude Code (Claude Opus 5.5) |
| Raiz absoluta | `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente` |
| Sistema | Windows 11 Pro 10.0.26200, 64 bits; Python 3.12.10 |
| ZIP de origem | `%USERPROFILE%\Downloads\Nexo-Faturamento-Inteligente-main.zip`, 18.417.690 bytes, SHA-256 `C308B3A0C6954D7CB0DC704783E94A8BBD870E03924D0646793BC991984D1A33`, 258 arquivos e 35 diretórios |
| Commit | O comentário do ZIP indica `faa59d98a6352c4e076ba11d4469c81486e13474`. **Não comprovado em repositório** (sem Git nem rede) |
| Branch | Não se aplica: a pasta não tem `.git`. O nome do ZIP sugere `main` |

## 2. Resumo

**Realizado:**

- Pasta alvo confirmada, comparada por hash com o ZIP (251 iguais, 7 alterados pela Etapa 0.2A, 7 acrescentados, 0 ausentes) e distinguida de outras 4 cópias e fontes.
- Inventário da arquitetura, dos 14 modelos, das 8 migrações, dos testes, da infraestrutura declarada, da identidade visual, dos preços, dos contratos, da renovação, da suspensão e do cancelamento, da LGPD e do domínio. As evidências estão no formato `arquivo:linha`.
- Achado prioritário **confirmado**: empresa CANCELADA ou SUSPENSA continua entrando e usando o portal. Está comprovado no código e por um teste que passou nesta execução.
- Checkpoint local, fora da pasta, com 265 de 265 arquivos conferidos por hash.
- Sintaxe de 123 arquivos Python, 38 templates, 7 JSON, `alembic.ini` e requirements: sem falhas.
- Suíte completa executada duas vezes numa cópia isolada: 569 testes, com o mesmo resultado da linha de base pós-0.2A.
- Três documentos criados em `Docs/AJUSTES_NEXO_2026/`.

**Não realizado:**

- Índice dos 27 prompts e correspondência dos ajustes 01 a 09: falta o mapa. **[Complemento] Resolvido** com o mapa oficial (seção 0).
- Validação dos YAML: PyYAML não está instalado e não foi instalado.
- Suítes PostgreSQL e testes de navegador (opt-in; as suítes PG exigem POSIX).
- Qualquer correção de código, ajuste visual ou de banco, migração, seed, commit, deploy ou acesso a Supabase, Render, DNS ou GitHub. **`NEXO-AJ-06.1` não foi iniciado.**

## 3. Arquivos inspecionados

Lidos diretamente ou pelas quatro frentes de leitura paralela (somente leitura). Os pontos principais de cada arquivo:

| Arquivo | Pontos importantes |
|---|---|
| `session_security.py` | `usuario_pode_acessar()` verifica ativo, papel e lixeira, não `status_conta` (`:43-57`); `sessao_valida` (`:106-115`) |
| `blueprints/auth.py` | Login exige só senha e `usuario_pode_acessar` (`:268-280`); tokens (`:110,153`); recuperação (`:352-360`); links `_external` (`:355,359`); logout por GET (`:299`) |
| `blueprints/cliente.py` | `cliente_required` só checa o papel (`:61-69`); consulta e PDF filtram dono e publicação, sem status (`:240-292`); upload sem status (`:307-351`) |
| `blueprints/admin.py` | Receita estimada (`:72-79`); única guarda de status na abertura de análise (`:230-232`); edição de status sem revogar sessões (`:433-435`); exclusão permanente (`:523-612`) |
| `company_security.py` | A lixeira incrementa `geracao_autorizacao` (`:58-59`) |
| `realtime.py`, `notifications.py`, `emails.py` | Socket.IO por `sessao_valida` (`realtime.py:147-152`); entrega sem status (`notifications.py:70`); e-mails sem status nem lixeira (`emails.py:104-112`) |
| `models.py` | 14 modelos (seção 5); `status_conta` (`:96,113`); `data_contratacao` (`:94`); `deletado_em` (`:104`); `valor_mensal` (`:43`); docstring desatualizada (`:4,9-11`) |
| `migrations/versions/*` | 8 revisões, head `e4c004a26b01` com UPDATE de dados e downgrade não restaurador (`:10-13,56-67`) |
| `seed.py` | BRONZE 600, PRATA 1000, OURO 1400 (`:35,45,55`); idempotente (`:64-69`) |
| `config.py`, `app.py`, `wsgi.py`, `extensions.py` | `.env` só da raiz (`config.py:23`); SQLite padrão (`:54-57`); CORS do Socket.IO (`:109-118`); cookie Secure em produção (`:205`); ProxyFix (`app.py:343-346`) |
| `render.yaml`, `.github/workflows/nexo-security-ci.yml` | Web Service free em Oregon, `autoDeployTrigger: 'off'` (`render.yaml:8-22`); CI em Linux com `PYTHONUTF8=1` |
| `storage.py`, `ai_devolutiva.py`, `nexobot/providers.py`, `log_security.py` | Planilhas inteiras no banco (`storage.py:52-64`); dados à Anthropic (`ai_devolutiva.py:63-147`) e ao Hugging Face (`providers.py:26,55-65`); mascaramento só de tokens (`log_security.py:17-33`) |
| `templates/` (base, auth, landing, cliente, emails), `static/css/` | Logo em 7 templates; marca "N" na landing; "Sob consulta" (`landing.html:383,396,410`); privacidade não publicada (`landing.html:464-465`); faixa só para SUSPENSA (`cliente/dashboard.html:9`) |
| `tests/` | Isolamento (`tests/deploy_support.py:24-57`); teste que trava o acesso de CANCELADA (`tests/test_company_restore_security.py:431-444`); landing (`test_landing_commercial.py:132`); NexoBot sem preços (`test_nexobot_saber.py:29-30`) |
| `criar_cliente_demo.py` | Credencial de demonstração fixa no código (valor não reproduzido) e `create_app("development")` (`:17-18,21`); uso documentado com `NEXO_DB_DIRECT=1` (`:6`) |
| Documentação | `README.md`; `Docs/REESTRUTURACAO_COMERCIAL/00_01_*`, `00_02_*` e `insumos/2026-10-25/README.md`; `Docs/PREPARACAO_RENDER.md`; `Docs/OPERACAO_BACKUP_RESTAURACAO.md`; `Docs/RELATORIO_TECNICO.md`; `Docs/AUDITORIA_RENDER.md`; `Docs/NEXOBOT_ADVANCED.md`; `schema_nexo_mvp_v4.sql`; Documento Mestre (`.docx`, texto extraído fora da pasta) |

## 4. Arquivos criados, editados e removidos

**Nenhum arquivo de código, template, CSS, JS, migração, teste, banco, upload ou configuração de deploy foi criado, editado ou removido.** A pasta não tem Git, por isso não há `git status`. A comparação abaixo é por SHA-256 contra o manifesto tirado no início da etapa.

| Ação | Caminho |
|---|---|
| Criado (pasta) | `Docs/AJUSTES_NEXO_2026/` |
| Criado | `Docs/AJUSTES_NEXO_2026/NEXO_AJ_00_BASELINE.md` |
| Criado | `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md` |
| Criado | `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` |
| Editado | Nenhum |
| Removido | Nenhum |

**[Complemento]** No complemento, o mapa foi acrescentado à raiz (`NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md`), `CONTROLE_PROMPTS.md` foi reescrito e este relatório e o baseline foram editados. Nenhum outro arquivo mudou (seção 0.2).

**Fora da pasta do projeto** (checkpoint e evidências locais): `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\` (ZIP do checkpoint, manifesto, `LEIA-ME.txt` e `evidencias/` com os logs da suíte e os scripts de verificação).

**Alterações anteriores a esta etapa, presentes na pasta:** 7 arquivos modificados e 1 criado pela Etapa 0.2A (24/10/2026), e 6 arquivos de `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/` salvos nesta mesma sessão, antes da NEXO-AJ-00 (`NEXO_AJ_00_BASELINE.md`, seção 1.2).

## 5. Modelos, banco e migrações

**Contagem comprovada: 14 modelos em 14 tabelas** (15 com `alembic_version`). Não são 12.

| # | Modelo | Tabela | Linha |
|---|---|---|---|
| 1 | `Plano` | `plano` | `models.py:37` |
| 2 | `Segmento` | `segmento` | `:67` |
| 3 | `Empresa` | `empresa` | `:83` |
| 4 | `Usuario` | `usuario` | `:120` |
| 5 | `Analise` | `analise` | `:192` |
| 6 | `UploadRelatorio` | `upload_relatorio` | `:262` |
| 7 | `IndicadorAnalise` | `indicador_analise` | `:305` |
| 8 | `RelatorioAnalise` | `relatorio_analise` | `:336` |
| 9 | `ProdutoCurvaABC` | `produto_curva_abc` | `:365` |
| 10 | `ChamadoSuporte` | `chamado_suporte` | `:408` |
| 11 | `MensagemSuporte` | `mensagem_suporte` | `:457` |
| 12 | `Notificacao` | `notificacao` | `:481` |
| 13 | `GuiaTopico` | `guia_topico` | `:508` |
| 14 | `ArquivoArmazenado` | `arquivo_armazenado` | `:538` |

Divergências documentais: `models.py:4` diz 8; `README.md:142` e `Docs/RELATORIO_TECNICO.md:13` dizem 13; `schema_nexo_mvp_v4.sql` tem 14 tabelas de outro conjunto; `Docs/schema_nexo_mvp_v4 (1).sql` tem 12.

**Migrações:** 8 revisões em cadeia linear até a head `e4c004a26b01`. **Banco local:** nenhum na pasta. **Produção:** revisão aplicada, dados e preços **não conhecidos** (PENDENTE DE TESTE). Nada foi conectado nem migrado.

## 6. Diagnóstico dos futuros ajustes 01 a 09

**[Complemento]** Esta seção segue as etapas 01 a 09 da matriz do mapa (mapa:22-33). Que esses sejam os "ajustes 01 a 09" é uma **interpretação** a confirmar na revisão humana, porque o mapa não usa a palavra "ajuste". Na primeira entrega, sem o mapa, a seção estava organizada pelos nove pedidos das imagens (itens a a i). Os pedidos, as evidências e as classificações daquela versão foram mantidos: cada item aparece na coluna "Pedido", na etapa correspondente. A etapa 09, que não corresponde a nenhum pedido das imagens, ganhou diagnóstico próprio. A versão original está em `Backups_NEXO\NEXO-AJ-00_2026-10-25\evidencias\complemento_mapa\documentos_antes_do_complemento\`.

| Etapa (prompts) | Assunto | Pedido do responsável (item da 1ª entrega) | Situação atual | Evidência | Classificação |
|---|---|---|---|---|---|
| **01** (`NEXO-AJ-01`) | Identidade visual: só o símbolo | f: "Logo: só o cubo" | `nexo-logo.jpeg` (com texto e marca ✦) em 7 templates, a 42 px e a 88 px; "N" na landing; sem favicon. A arte nova `nexo_cubo_centralizado.png` (640×641, com anel branco e fundo escuro) está em Downloads e, idêntica, em `insumos/2026-10-25/01_logo_cubo_sem_texto.png` | `templates/base.html:42-43`; `templates/auth/login.html:11-12`; `static/css/nexo.css:158-166,251-260`; `templates/landing.html:23,448` | COMPROVADO NO CÓDIGO |
| **02** (`NEXO-AJ-02`) | Preços dos planos | e: "Planos Bronze R$ 150, Prata R$ 300, Ouro R$ 650" | O seed grava 600, 1000 e 1400 e pula planos existentes. Há uma linha por plano, sem histórico de preço e sem tela de edição. A receita estimada muda na hora. A landing mostra "Sob consulta", exigido em teste. O NexoBot proíbe preços | `seed.py:35,45,55,64-69`; `models.py:41,43,56`; `blueprints/admin.py:72-79`; `templates/landing.html:383,396,410`; `tests/test_landing_commercial.py:132`; `tests/test_nexobot_saber.py:29-30` | COMPROVADO NO CÓDIGO; valor em produção PENDENTE DE TESTE |
| **03** (`03.1` a `03.4`) | Gestão de contratos | b: "Tudo por contrato" | Só existe `data_contratacao`, sem uso em cálculos. Não há entidade de contrato, vigência, histórico, renovação nem prorrogação. A troca de plano sobrescreve `id_plano_atual`, e a análise guarda só a chave do plano. `fatura_cobranca` existe só no SQL avulso. Qualquer modelo novo exige a 9ª migração | `models.py:94,197`; `blueprints/admin.py:426`; `schema_nexo_mvp_v4.sql:364-387` | COMPROVADO NO CÓDIGO |
| **04** (`04.1` a `04.3`) | Avisos de renovação 7 a 14 dias antes | g: "Aviso de renovação 7 a 14 dias antes" | Não há vencimento modelado nem agendador. Notificações e e-mails só disparam em requisições HTTP. `Notificacao` não tem tipo nem deduplicação. Links absolutos dependem do Host da requisição. O Render Free hiberna | `render.yaml:8,21`; `notifications.py:146-183`; `emails.py:77-149`; `models.py:489-496`; `blueprints/admin.py:868` | COMPROVADO NO CÓDIGO; hibernação DOCUMENTAL (`README.md:349`) |
| **05** (`05.1` a `05.5`) | Contas suspensas | c: "Suspensa: consulta ao período pago; cancelamento em até 3 meses, prorrogável"; d: "Suspensa: exportar PDFs por 14 dias corridos" | A suspensão só bloqueia a abertura de análise. O upload continua aceito. A consulta lista todas as análises publicadas, sem filtro de período pago. O PDF não verifica status nem prazo de 14 dias. Não há data de suspensão, prazo de 3 meses nem prorrogação. O status muda só à mão. A Visão Geral mostra só uma faixa | `blueprints/admin.py:230-232,433`; `blueprints/cliente.py:145-159,229-236,272-292,307-351`; `pdf_export.py:231`; `templates/cliente/dashboard.html:9,21-28` | COMPROVADO NO CÓDIGO; regra exata DOCUMENTAL |
| **06** (`06.1` a `06.4`) | Contas canceladas | a: "Conta cancelada: tela bloqueada ou desfocada com mensagem" (e a parte de cancelamento de c) | Empresa CANCELADA entra, mantém sessão e Socket.IO, recebe tokens de senha e e-mails, consulta, exporta PDF e envia arquivos. A troca de status não revoga sessões. Só há badge vermelho; nenhuma tela de bloqueio. Não há transição automática SUSPENSA → CANCELADA. A lixeira (`deletado_em`) é um mecanismo separado | `session_security.py:43-57`; `blueprints/auth.py:268-280`; `blueprints/admin.py:433-435`; `company_security.py:58-59`; `realtime.py:147-152`; `emails.py:104-112`; `templates/_macros.html:50` | COMPROVADO NO CÓDIGO; TESTADO LOCALMENTE (`tests/test_company_restore_security.py:431-444` passou) |
| **07** (`07.1` a `07.4`) | LGPD e proteção de dados | h: "Revisar o NEXO pela LGPD" | Não há política, termos, aviso de cookies, encarregado nem rotina de retenção. Há terceiros (Anthropic, Hugging Face, Brevo, Render/Supabase nos EUA, CDNs). A exclusão permanente deixa notificações de ADMIN com dados da empresa. Não há rota para o titular exercer direitos. Inventário inicial, **sem conclusão de conformidade** | `templates/landing.html:464-465`; `ai_devolutiva.py:63-147`; `nexobot/providers.py:26,55-65`; `templates/base.html:13,16-17,368`; `blueprints/admin.py:588-594` | COMPROVADO NO CÓDIGO; obrigações legais: análise jurídica pendente |
| **08** (`NEXO-AJ-08`) | Domínio e DNS | i: "DNS: nome em vez de IP" | Não há IP público nem domínio no repositório; `render.yaml` sem `domains:`. Faltam URL canônica (`SERVER_NAME` ou `TRUSTED_HOSTS`) e `SOCKETIO_CORS_ORIGINS` no `render.yaml`. Sem HSTS. O remetente padrão é Gmail | `config.py:109-118,156-159,205`; `blueprints/auth.py:355,359`; `render.yaml:23-42` | COMPROVADO NO CÓDIGO; DNS e painel PENDENTE DE TESTE |
| **09** (`09.1` a `09.3`) | Validação, implantação segura e documentação | — (não corresponde a pedido das imagens) | **09.1:** a suíte local dá 569 testes com 13 falhas, 12 erros e 42 ignorados, todos de ambiente (seção 9). A CI em Linux roda a suíte completa e 5 módulos PostgreSQL. O teste que trava o acesso de CANCELADA terá de ser reescrito. **09.2:** 8 migrações, head `e4c004a26b01` com downgrade não restaurador; revisão em produção desconhecida; Auto-Deploy possivelmente ativo; procedimento de backup real preparado, não executado. **09.3:** o Documento Mestre usa a base `c919b1d`, e o ZIP é `faa59d9`; a documentação traz contagens de tabelas e migrações desatualizadas | `.github/workflows/nexo-security-ci.yml:64-68,111-119`; `migrations/versions/e4c004a26b01_company_authorization_generation.py:10-13,56-67`; `render.yaml:18`; `Docs/PREPARACAO_RENDER.md:83,89`; `models.py:4`; `README.md:142`; `Docs/RELATORIO_TECNICO.md:13,49` | COMPROVADO NO CÓDIGO (testes e migrações); DOCUMENTAL (Auto-Deploy); produção PENDENTE DE TESTE |

## 7. Achados de segurança e conflitos de versões

Nenhum achado foi corrigido nesta etapa.

| # | Gravidade | Achado | Evidência | Classificação |
|---|---|---|---|---|
| S1 | **ALTA** | `status_conta` CANCELADA ou SUSPENSA não restringe login, sessão, tokens de senha, Socket.IO, consulta, PDF, upload nem e-mails | `session_security.py:43-57`; `blueprints/auth.py:110,153,268-280,352-360`; `realtime.py:147-152`; `blueprints/cliente.py:61-69,272-351`; `emails.py:104-112` | COMPROVADO; TESTADO LOCALMENTE |
| S2 | **ALTA** | A troca de status não revoga sessões abertas: a edição não incrementa `geracao_autorizacao`, ao contrário da lixeira | `blueprints/admin.py:433-435` contra `company_security.py:58-59` | COMPROVADO NO CÓDIGO |
| S3 | **ALTA** | `criar_cliente_demo.py` cria ou reseta um cliente com credencial fixa no código, ligado à primeira empresa do banco, com `create_app("development")`, que contorna as travas de produção. O uso documentado (`NEXO_DB_DIRECT=1`) sugere execução contra o banco real | `criar_cliente_demo.py:6,17-18,21,23-25` | COMPROVADO NO CÓDIGO (valor não reproduzido) |
| S4 | **ALTA** | Arquivos `.env`, um backup de `.env` e um banco SQLite existem em `C:\ADS\Nexo - Faturamento Inteligente\Nexo.zip` e no clone antigo `Nexo\Nexo-Faturamento-Inteligente\`. Conteúdo não aberto | Listagem de nomes das entradas | COMPROVADO (nomes); risco de vazamento se compartilhados |
| S5 | **ALTA** | Auto-Deploy: `render.yaml:18` diz `'off'`, mas o responsável informou "ativado". Um merge na `main` pode publicar código antes da migração | `Docs/PREPARACAO_RENDER.md:83,89` | DOCUMENTAL; painel PENDENTE |
| S6 | MÉDIA | Links de e-mail herdam Host e esquema da requisição; não há `SERVER_NAME` nem `TRUSTED_HOSTS` | `blueprints/auth.py:355,359`; `blueprints/admin.py:386,868,1092` | COMPROVADO; exploração PENDENTE DE TESTE |
| S7 | MÉDIA | Sem HSTS, CSP global nem X-Frame-Options; CDNs sem SRI no portal autenticado | `templates/base.html:192,368`; `app.py:136-138,276` | COMPROVADO NO CÓDIGO |
| S8 | MÉDIA | SSL do PostgreSQL não é exigido pelo código (depende da URL do painel) | `config.py:29-45` | COMPROVADO; configuração real PENDENTE |
| S9 | BAIXA | Logout por GET; origens localhost aceitas no Socket.IO se `SOCKETIO_CORS_ORIGINS` faltar; handler de CSRF com redirect e status 400 | `blueprints/auth.py:299`; `config.py:110-113`; `app.py:327` | COMPROVADO NO CÓDIGO |

**Conflitos de versão:**

| # | Conflito | Evidência |
|---|---|---|
| V1 | Commit do ZIP `faa59d9` × Documento Mestre `c919b1d` × `00_01` `8233c5b` × `00_02` `ff8c2d8` (histórico) | Comentário do ZIP; `00_01_BASELINE_GITHUB.md:40`; `00_02_PROTECAO_BANCO_MIGRACOES.md:40` |
| V2 | O ZIP contém artefatos das PRs #20 e #21 que o Documento Mestre (14h40) dá como não integradas. HIPÓTESE: ZIP posterior | `Docs/NEXOBOT_ADVANCED.md`, `Docs/RELATORIO_NEXO_COM001_LANDING_COMERCIAL.md`, `tests/test_landing_commercial.py` presentes |
| V3 | Repositório: Documento Mestre `Helio965/Nexo---Faturamento-Inteligente---Render` × prefixo do ZIP `Nexo-Faturamento-Inteligente` × destino oficial `nexofaturamentointeligente-coder/Nexo-Faturamento-Inteligente` | `00_02_PROTECAO_BANCO_MIGRACOES.md:40-41` |
| V4 | Pacotes locais × fixados: Flask 3.0.3/3.1.3, Werkzeug 3.0.4/3.1.9, Flask-SocketIO 5.4.1/5.6.1, python-dotenv 1.0.1/1.2.4, Pillow 12.2.0/13.0.0; `gunicorn` e `PyYAML` ausentes | `requirements.txt:6,9,10,23,26,34`; `requirements-dev.txt:2` |
| V5 | Documentação de tabelas e migrações desatualizada (8, 13 ou 12 tabelas; "6 migrações reversíveis"; "7 revisões") | `models.py:4`; `README.md:142`; `Docs/RELATORIO_TECNICO.md:13,49`; `Docs/AUDITORIA_RENDER.md:76` |

## 8. Backup e checkpoint

| Item | Valor |
|---|---|
| Método | ZIP local da pasta inteira, tirado **antes** de criar os documentos desta etapa, com regras de exclusão de segredos, e conferido arquivo a arquivo contra a pasta |
| Local | `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\NEXO_checkpoint_pre-AJ-00_2026-10-25.zip` |
| Integridade | 265 de 265 arquivos idênticos; SHA-256 `56886D00074010C39172310E83A50306DE75D0C4623E3C5E3B6BD0B04AD9C8FA` |
| Exclusões | `.env*` (exceto `.env.example`), bancos, dumps, logs, chaves, caches, ambientes virtuais, `instance/`, `.audit_tmp/` e uploads que não sejam `.gitkeep`. Nenhum arquivo se enquadrou |
| Restauração | `LEIA-ME.txt` na mesma pasta: renomear a pasta atual, extrair o ZIP e conferir pelo manifesto |
| Limitações | É um checkpoint **local**, na mesma máquina e no mesmo disco, sem cópia externa. **Não é backup do banco de produção**, que não foi acessado (procedimento preparado em `00_02`, seção G, ainda não executado). Pontos anteriores: o ZIP original em Downloads (sem a 0.2A) e `C:\ADS\Nexo - Faturamento Inteligente\Nexo - Faturamento Inteligente.zip` (pós-0.2A, sem os insumos). **[Complemento]** Esse segundo ZIP foi regravado às 11:28 de 25/10, fora desta execução, e agora contém o estado pós-AJ-00 (268 arquivos), não mais o pós-0.2A. O estado pós-0.2A com os insumos continua no checkpoint desta etapa |
| Recomendação para a próxima etapa | Como não há Git, tirar novo checkpoint igual antes de cada `NEXO-AJ-*`. No repositório oficial, usar uma branch por ID a partir do commit-base confirmado, sem tocar na `main` |

## 9. Testes e verificações

Todas as execuções ocorreram nesta máquina, sem rede e sem credenciais.

| # | Verificação | Comando | Ambiente | Resultado |
|---|---|---|---|---|
| T1 | Pasta × ZIP | `python -B -I manifesto.py <raiz> <zip> <saída>` | Leitura | **APROVADO**: 265 arquivos; 251 iguais, 7 modificados (0.2A), 7 acrescentados, 0 ausentes |
| T2 | Integridade do checkpoint | `python -B -I manifesto.py <raiz> <checkpoint.zip> <saída>` | Leitura | **APROVADO**: 265/265 |
| T3 | Sintaxe e configuração | `python -B -I verificar_sintaxe.py <raiz>` (`ast.parse`, parser Jinja, `json`, `configparser`, regex de requirements; não importa o projeto) | Leitura | **APROVADO**: 123 `.py`, 38 templates, 7 JSON, `alembic.ini`, 18 + 2 dependências fixadas, 0 falhas |
| T4 | YAML (`render.yaml`, workflow da CI) | Mesmo script | — | **BLOQUEADO**: PyYAML ausente; não instalado por regra da etapa |
| T5 | Suíte completa, execução 1 | `python -B -m unittest discover -s tests -t . -v` | Cópia extraída do checkpoint em pasta temporária fora do projeto; sem `.env`; variáveis `ANTHROPIC_*`, `CLAUDE_CODE_*`, `SENTRY-TRACE`, `DATABASE_URL` e `DIRECT_URL` removidas do processo; nenhum `NEXO_TEST_*` | **FALHOU (preexistente)**: 569 testes, 13 falhas, 12 erros, 42 ignorados (192 s). Log truncado pela formatação do PowerShell |
| T6 | Suíte completa, execução 2 | O mesmo, redirecionado por `cmd` | Nova cópia limpa, mesmas condições | **FALHOU (preexistente)**, idêntico: 569, 13, 12, 42 (175 s). Log integral arquivado em `evidencias/` |
| T7 | Teste do status comercial | Dentro de T5 e T6 | — | **APROVADO** nas duas: `test_soft_delete_restore_preserves_existing_commercial_status_policy`. Confirma em execução que SUSPENSA e CANCELADA acessam o portal |
| T8 | Suítes `tests.postgresql_*` | — | — | **NÃO EXECUTADO**: exigem POSIX |
| T9 | Navegador e ensaio de backup PG | — | — | **NÃO EXECUTADO**: opt-in (`NEXO_TEST_BROWSER`, `NEXO_TEST_POSTGRES_BIN`); 33 + 1 ignorados com motivo |

**Isolamento demonstrado antes de executar:**

- `config.py:23` lê só `<raiz>/.env`, que não existe (nem na cópia).
- Sem `DATABASE_URL`, o banco é SQLite dentro da própria cópia (`config.py:54-57`).
- `tests/__init__.py` redefine 23 variáveis e bloqueia rede e dotenv (`tests/deploy_support.py:24-57`).
- O processo não tinha nenhuma credencial de banco, e-mail ou IA.

**Falhas preexistentes:** são as mesmas da linha de base `00_02`, seção E, item E15 (569 testes, 13 falhas, 12 erros, 42 ignorados). Todas são de ambiente; nenhuma foi corrigida.

| Causa | Testes afetados |
|---|---|
| ETL recusado no Windows (`code="platform"`, SEC-005) | `test_deploy` (ETL ×2 e persistência de uploads), `test_etl_runtime_limits` (×3), `test_etl_upload_security` (×6), `test_etl_resource_limits` (×1). Provavelmente também `test_dependency_security_compat` ×2 (`part_limit_accepts_four…` e `valid_csv_and_xlsx_uploads…`: nenhum upload válido foi gravado, `0 != 1` e `0 != 2`, mesma assinatura dos testes de upload acima) |
| Codificação cp1252 (a CI usa `PYTHONUTF8=1`) | `test_etl_financial_equivalence` (`setUpClass`, `UnicodeDecodeError`) |
| Módulos ausentes | `test_sensitive_http_logs` (`gunicorn`), `test_supply_chain_install` (`yaml`) |
| Versões locais diferentes das fixadas | `test_dependency_security_compat`: Werkzeug, orçamento de campos multipart ×2 (`RequestEntityTooLarge not raised`; `302 != 413`); Flask, `Vary: Cookie` ×4 subtestes. `test_dotenv_security_compat` (python-dotenv) |

**Ignorados (42):** 33 de navegador, 3 de `pdftotext`, 2 de probe POSIX, 1 de `NEXO_TEST_POSTGRES_BIN`, 1 de gunicorn simulado, 1 de gunicorn e 1 de `RLIMIT_AS`.

## 10. Pendências, riscos e dependências

| Antes de… | Resolver |
|---|---|
| Qualquer próximo ID | ~~Colocar o mapa na pasta e completar `CONTROLE_PROMPTS.md`~~ **[Complemento] resolvido**; confirmar no GitHub que `faa59d9` é a `main` oficial; aprovação humana desta etapa |
| Cancelamento e suspensão (`NEXO-AJ-06.1`, segundo o prompt) | Decidir se a conta cancelada entra e vê tela desfocada ou se o login é bloqueado; reescrever o teste `tests/test_company_restore_security.py:431-444`; revogar sessões e sockets na troca de status; os prazos de 14 dias e 3 meses dependem de campos de data (migração) |
| Contratos e renovação | Migração nova seguindo `00_02` (seções G, H e K); revisão de produção desconhecida; Auto-Deploy possivelmente ativo; escolher um agendador compatível com o Render Free; definir a regra exata entre 7 e 14 dias |
| Preços | Decidir se contratos vigentes mantêm o preço antigo; atualização de dados em produção só com backup autorizado; ajustar landing, teste e NexoBot se os preços forem publicados |
| Logo | Decidir onde trocar e se haverá recorte transparente do cubo |
| LGPD | Definir escopo (documento, sistema ou ambos); envolver revisão jurídica |
| Domínio | Autorização expressa para Render e DNS; configurar `SOCKETIO_CORS_ORIGINS`, URL canônica e remetente de e-mail |
| Validação | Entregas que tocam ETL, upload ou dependências precisam de validação em Linux/CI |

## 11. Checklist de aceite da Etapa 00

| # | Critério | Situação | Evidência |
|---|---|---|---|
| 1 | Pasta alvo localizada e confirmada, com caminho absoluto | OK | Seção 1; sinais de raiz |
| 2 | ZIP identificado: nome, tamanho, SHA-256 e contagem | OK | Seção 1 |
| 3 | Git verificado sem alterar nada | OK | Sem `.git`; `git init` não executado |
| 4 | Modificações preexistentes identificadas | OK | Seção 4; baseline, seção 1.2 |
| 5 | Várias cópias distinguidas, sem alterar nenhuma | OK | Baseline, seção 1.3 |
| 6 | Arquitetura, pastas e infraestrutura (declarada × verificada) inventariadas | OK | Baseline, seção 2 |
| 7 | Modelos contados com evidência `arquivo:linha` | OK (14) | Seção 5 |
| 8 | Testes, comandos seguros e barreiras identificados | OK | Seção 9 |
| 9 | Futuros ajustes localizados sem implementar | OK | Seção 6 |
| 10 | `nexo_cubo_centralizado.png` localizado | OK | Downloads e cópia idêntica em `insumos/` |
| 11 | Achado de CANCELADA confirmado ou refutado | OK: **confirmado** | Seção 7, S1 |
| 12 | Inventário LGPD inicial, sem concluir conformidade | OK | Seção 6, etapa 07 **[Complemento]** (antes "item h"); baseline, seção 7 |
| 13 | Domínio analisado sem alterar DNS ou provedor | OK | Seção 6, etapa 08 **[Complemento]** (antes "item i") |
| 14 | Checkpoint fora da pasta, sem segredos, verificado | OK | Seção 8 |
| 15 | Sintaxe e configuração validadas sem conectar em produção | OK, com YAML BLOQUEADO | Seção 9, T3 e T4 |
| 16 | Testes só em ambiente isolado, resultados separados por tipo | OK | Seção 9 |
| 17 | Três documentos em `Docs/AJUSTES_NEXO_2026/` | OK | Seção 4 |
| 18 | `CONTROLE_PROMPTS.md` com os 27 prompts do mapa | **OK [Complemento]** (na primeira entrega: BLOQUEADO, mapa ausente) | 27 IDs conferidos contra o mapa com 0 divergências (seção 0.5, C3 e C4) |
| 19 | Nenhum arquivo funcional modificado | OK | Comparação final por hash: 265 inalterados e 3 documentos novos. **[Complemento]** No complemento: 265 inalterados, 3 documentos editados e o mapa acrescentado (seção 0.6) |
| 20 | Nada de commit, push, deploy, migração, seed ou correção | OK | — |
| 21 | `NEXO-AJ-06.1` não iniciado | OK | — |

## 12. Status final

**[Complemento] CONCLUÍDO PARA REVISÃO.** Os 21 critérios da seção 11 estão atendidos. O critério 18 foi resolvido com o mapa oficial, conferido com 0 divergências. No controle, a NEXO-AJ-00 está como `EXECUTADO / AGUARDANDO REVISÃO`; a aprovação depende da revisão humana.

*Registro da primeira entrega (11:25), transcrito na íntegra como histórico:*

> **PARCIAL/BLOQUEADO.** Os critérios 1 a 17 e 19 a 21 estão atendidos. O critério 18 (índice dos 27 prompts e numeração 01 a 09) está bloqueado porque `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md` não existe nesta máquina: foram feitas buscas por nome em `C:\` e `D:\` e por conteúdo nas pastas do usuário. Não houve invenção de IDs.

As buscas estão detalhadas no histórico de `CONTROLE_PROMPTS.md`.

**Próximo passo recomendado:**

1. ~~Colocar o mapa em `Docs/AJUSTES_NEXO_2026/` para completar `CONTROLE_PROMPTS.md`. É um complemento só de documentação desta etapa.~~ **[Complemento] Feito.** O mapa ficou na raiz do projeto, junto de `app.py`, por indicação do responsável.
2. Depois da aprovação humana, seguir para **`NEXO-AJ-06.1`**, o próximo prompt indicado pelo mapa segundo o prompt NEXO-AJ-00. **Ele não foi iniciado.** **[Complemento]** Confirmado pelo mapa: a 06.1 é a "correção prioritária do bloqueio CANCELADA", depende só de `NEXO-AJ-00` (mapa:201) e é a 2ª na ordem recomendada (mapa:320).

**Cuidados ao enviar material para revisão:**

- Não envie `C:\ADS\Nexo - Faturamento Inteligente\Nexo.zip` nem a pasta `Nexo\`: elas contêm `.env` e banco.
- A imagem `Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/03_telas_atuais_marca_portal_admin_login.png` mostra telas do portal com nome de empresa e números. Parecem dados de teste ("Beta Testes"), mas confirme antes de compartilhar.
