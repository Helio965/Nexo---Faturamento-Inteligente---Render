# Relatório de implementação — Gestão contratual e ciclo de vida das empresas

> **Para auditoria técnica independente.** Este relatório descreve o que foi implementado, como foi validado e o que ainda depende de decisão ou de autorização.
>
> **Classificação:** IMPLEMENTADO E VALIDADO EM AMBIENTE DE TESTES · AGUARDANDO HOMOLOGAÇÃO (seção I). **Não está classificado como "pronto para produção".**
>
> **Estado:** o código **já foi mesclado na `main` pelo proprietário** (PR #27, merge `dcaa896`, 26/10/2026 às 16:20 UTC). Este relatório foi finalizado depois do merge e acompanha um PR de documentação.
>
> **O que eu não executei:** nenhuma migração no Supabase, nenhum deploy manual no Render, nenhuma variável, senha ou dado alterado (seção G). Se o Auto-Deploy do Render estiver ativo, o merge pode ter disparado uma publicação automática, o que **não é verificável daqui** (seção G).

Documentos de apoio, na mesma pasta:

- `01_ARQUITETURA_CONTRATUAL.md`: entidades, política e integrações.
- `02_REGRAS_DE_NEGOCIO.md`: regras e convenções propostas.
- `03_MATRIZ_DE_ACESSOS.md`: quem acessa o quê, por estado.
- `04_PLANO_DE_MIGRACAO_E_IMPLANTACAO.md`: ordem segura de implantação, que **não** foi executada.
- `05_PENDENCIAS_DE_DECISAO_COMERCIAL.md`: o que exige homologação do proprietário.

---

## A. Identificação

| Item | Valor |
|---|---|
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| Branch utilizada | `claude/awesome-pascal-0ho42m` |
| Branch sugerida no pedido | `feature/nexo-gestao-contratual-ciclo-vida`, **não usada**: esta sessão só tem permissão de push na branch designada acima |
| Base (`main`) | `6abc96c591c51da55fa1a8c62e678f22e67a8672` (merge do PR #26, identidade visual) |
| SHA inicial da branch | `413827818be03c93c3d407fa2933a5f4c458c0f9`: a `main` acima mais um commit de documentação do merge do PR #26 |
| SHA final do código | `800ca1d39986cf02a927e9d8abbfc8b4e739e5f0` (correções da verificação posterior à revisão E; o anterior era `006483a`) |
| Commit deste relatório | Posterior ao merge, em PR de documentação à parte (o PR #27 já estava mesclado e não foi reutilizado) |
| Pull Request | https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/27, **mesclado** pelo proprietário (merge `dcaa89643d7ead3889d493c02cab190f4547a7b4`) |
| Data | 26/10/2026 |
| Ambiente de validação | Container Linux efêmero; Python em venv; SQLite em memória; PostgreSQL 16 descartável e local; Chromium com Playwright. Nenhuma credencial real |

---

## B. Auditoria inicial

### B.1 O que já existia

- **Status da conta:** `Empresa.status_conta` (ATIVA, SUSPENSA ou CANCELADA), editado livremente pelo ADMIN no formulário da empresa, e `Empresa.id_plano_atual`.
- **Planos:** tabela `plano` com `valor_mensal` (seed antigo: R$ 600, R$ 1.000 e R$ 1.400) e benefícios (`qtd_analises_mes`, `tipo_analise_permitida` etc.).
- **Bloqueio NEXO-AJ-06.1:** o critério único `session_security.condicoes_empresa_acessivel`, aplicado no login, na guarda de sessão, nos tokens de senha, no CAS, no Socket.IO e nas notificações. Também a `usuario.geracao_autorizacao` (SEC-004, revisão `e4c004a26b01`) e `aplicar_status_conta` (`company_security.py`), que revoga as sessões dos CLIENTE ao entrar em CANCELADA e também ao sair dela, exigindo novo login após a reativação. As transições entre ATIVA e SUSPENSA não revogam sessões.
- **SUSPENSA:** banner informativo; histórico e PDF integrais; nova análise já exigia empresa ATIVA.
- **CANCELADA:** login recusado com a mensagem genérica "Esta conta está desativada".
- **PDF:** gerador em `/cliente/analise/<id>/pdf`, sem prazo.
- **Comercial público:** a landing mostra "Sob consulta"; o NexoBot não cita preços, por regra editorial da sua base de conhecimento (NexoBot Advanced, `nexobot/saber/modelo.py`, verificada em `tests/test_nexobot_saber.py`).
- **O que não existia:** contrato, vigência, período pago, prorrogação, histórico de preços e qualquer prazo de suspensão. Existia apenas `Empresa.data_contratacao`, uma data cadastral obrigatória e editável no formulário, que continua independente de `Contrato.data_inicio` e não é usada pela política contratual.

### B.2 O que precisava ser criado

- Entidades de contrato, período pago (cobertura), evento contratual, histórico de preço e a habilitação por empresa (regime).
- Uma política central de autorização contratual, no servidor, em Python e em SQL.
- Operações administrativas auditadas: contratar, renovar, trocar de plano, suspender, prorrogar, reativar, cancelar, registrar e revogar pagamento, ativar e desativar regras.
- Reconciliação de suspensões vencidas, idempotente e protegida contra concorrência.
- A página de conta encerrada, o novo catálogo de preços e a atualização auditada dos preços.

### B.3 O que foi reutilizado (sem refazer)

- **Critério único da AJ-06.1:** a cláusula contratual foi **acrescentada** a `condicoes_empresa_acessivel`. Por isso, login, guarda, tokens, CAS, Socket.IO e notificações herdam a regra sem código paralelo.
- **`aplicar_status_conta` e `geracao_autorizacao`:** fazem a revogação ao cancelar, inclusive pela reconciliação.
- **Gerador de PDF:** inalterado; a decisão ocorre antes dele.
- **Tabela `plano`, layout de autenticação, macros de template e a identidade visual do PR #26:** usados sem alteração de marca.
- **Infraestrutura de testes:** `DeployTestCase`, que roda as migrações reais; o padrão de PostgreSQL descartável dos testes da AJ-06.1; e o ensaio de backup.

### B.4 O que foi modificado

- **Rotas do cliente** (`blueprints/cliente.py`): situação contratual por requisição; filtros no dashboard e no histórico; 403 na análise e no PDF; reverificação do upload.
- **Rotas do ADMIN** (`blueprints/admin.py`):
  - receita estimada com o valor contratado;
  - alertas contratuais;
  - abertura de análise por vigência, com lock da empresa;
  - edição da empresa com status e plano bloqueados quando "governada";
  - publicação que só avisa o cliente se ele puder abrir a análise;
  - exclusão permanente bloqueada com histórico contratual.
- **Login** (`blueprints/auth.py`): página de conta encerrada e hash fictício para e-mails inexistentes.
- **Demais arquivos:** `session_security.py` (cláusula), `models.py`, `config.py` (parâmetros `CONTRATO_*`), `seed.py`, `app.py`, templates, CSS e textos do NexoBot. Documentação existente atualizada: `Docs/OPERACAO_BACKUP_RESTAURACAO.md` (19 tabelas ORM e aviso sobre o downgrade da `81287c74387a`) e `Docs/AJUSTES_NEXO_2026/CONTROLE_PROMPTS.md`. O registro do merge do PR #26 no relatório da identidade visual veio do commit inicial `4138278`.
- **Cinco módulos de teste existentes** foram ajustados de forma legítima: `test_backup_restore`, `test_cancelled_company_postgresql`, `test_cancelled_company_security`, `test_identidade_visual` e `test_pdf_export_security`. Houve, por exemplo, a troca "desativada" → "Conta encerrada" com mais asserções, a contagem de tabelas de 15 para 20 e a fixture contratual no ensaio de backup. O `setUp` de `PDFPortalContractTests` passou a simular a política contratual (regime legado, empresa ATIVA), e `test_pdf_export_security` ganhou dois testes novos. A revisão E conferiu que nenhuma verificação foi afrouxada.

---

## C. Implementação

### C.1 Contratos

- **Modelo `Contrato`:** plano, valor mensal contratado (snapshot), vigência (`data_inicio` e `data_fim` opcional), formalização (data e referência), situação (ATIVO, SUSPENSO, ENCERRADO ou CANCELADO), prazos de suspensão e de PDF, `versao` para concorrência otimista e responsável.
- **Um vigente por empresa:** só pode existir um contrato ATIVO ou SUSPENSO, garantido pelo índice único parcial `uq_contrato_aplicavel_empresa`.
- **Renovação e troca de plano:** criam um **novo** contrato ligado ao anterior (`id_contrato_anterior`); o anterior vira ENCERRADO e conserva plano, valor e período. A nova vigência não pode começar no futuro: agendamento não é suportado e ficou como pendência.
- **Contratação de empresa CANCELADA:** reativa a empresa e exige novo login, porque a geração sobe.
- **Contratação de empresa SUSPENSA:** **não** a reativa. Isso serve à conciliação (correção da revisão E).
- **Regularização explícita:** com contrato ATIVO e empresa SUSPENSA, a ação **"Reativar empresa"** (Detalhes) devolve a empresa a ATIVA com justificativa obrigatória e evento `REATIVACAO`, sem revogar sessões. A renovação e a troca de plano de um contrato ATIVO **não** reativam a empresa SUSPENSA; a renovação de um contrato SUSPENSO continua reativando-a. Sem esta ação, a conciliação ficava sem saída (achado da verificação posterior à revisão E, corrigido em `800ca1d`).
- **Edição da empresa "governada":** quando há contrato vigente ou regras ativas, status e plano mudam só por operações contratuais.
- **Arquivos:** `models.py`, `contract_admin.py` e `blueprints/contratos.py`.

### C.2 Períodos pagos (coberturas)

- **Registro:** `CoberturaPaga` é confirmada manualmente pelo ADMIN, com referência obrigatória, intervalo inclusivo e quem confirmou. Não há presunção de pagamento.
- **Correção:** só por revogação com motivo. O registro original é preservado.
- **Sobreposição:** proibida entre coberturas vigentes da mesma empresa.
- **Vigência efetiva:** a cobertura precisa caber no período em que o contrato realmente valeu:
  - ENCERRADO: até a véspera do sucessor;
  - CANCELADO: até a data do cancelamento.
- **Direito a uma análise:** o período declarado, unido ao período real da base, precisa estar **inteiramente** dentro da união das coberturas não revogadas.
  - A união considera todos os contratos da empresa, e intervalos consecutivos se unem.
  - Cobertura parcial não dá acesso.
  - No regime contratual, isso vale também para a empresa ATIVA.

### C.3 Suspensão

- **Registro:** o ADMIN informa o motivo e o instante oficial (padrão: agora). O instante nunca pode ser futuro e pode ser retroativo, mas não pode ser anterior ao início da vigência nem à última alteração registrada no contrato (por exemplo, uma reativação). Além disso, o prazo de acesso calculado a partir dele ainda precisa estar em aberto: uma suspensão retroativa cujo limite já passou é recusada ("Com essa data o prazo de suspensão já estaria encerrado").
- **Prazos gravados no contrato:**
  - acesso: início + **3 meses de calendário** no fuso America/Sao_Paulo, com o último dia do mês quando o dia não existe;
  - PDF: início + **14 dias corridos**, nunca além do acesso.
  - Os limites são **exclusivos**.
- **O que a empresa SUSPENSA pode fazer:** autenticar-se, consultar análises pagas, exportar PDF dentro do prazo e abrir chamados.
- **O que ela não pode fazer:** receber novas análises, ver períodos não pagos ou enviar arquivos, exceto para análise aberta de período pago.
- **Alcance:** os prazos e bloqueios desta seção, e o cancelamento por expiração (C.5), valem somente para empresas com as regras contratuais ativadas (linha em `regime_contratual`). No regime legado, que é o de todas as empresas após a migração até a conciliação, os prazos gravados num contrato SUSPENSO não produzem efeito: a empresa SUSPENSA mantém consulta e PDF sem prazo, e a reconciliação não a cancela.
- **No instante-limite (regime contratual):** a política já trata a empresa como `SUSPENSAO_EXPIRADA`, inclusive na cláusula SQL, sem depender de agendador.
- **Parâmetros:** `CONTRATO_SUSPENSAO_MESES`, `CONTRATO_EXPORTACAO_PDF_DIAS` e `CONTRATO_FUSO_HORARIO`, além de `Contrato.meses_suspensao`, que permite a um contrato prever um prazo de suspensão menor ou igual ao padrão: a aplicação aceita de 1 até `CONTRATO_SUSPENSAO_MESES` (3 por padrão; o formulário oferece 1 ou 2 meses). O intervalo de 1 a 12 é apenas o limite do CHECK `ck_contrato_meses_suspensao` no banco.

### C.4 Prorrogação

- **Requisitos:** só para contrato SUSPENSO, com justificativa obrigatória e novo limite futuro, posterior ao vigente.
- **Limite original:** fica preservado. O evento `PRORROGACAO` guarda o original, o anterior e o novo.
- **Efeitos:**
  - não representa pagamento;
  - não amplia o PDF, salvo autorização contratual específica, limitada ao novo limite de acesso.
- **Concorrência:** a corrida com a reconciliação é resolvida pelo lock da empresa e pela reavaliação, testado em PostgreSQL.

### C.5 Cancelamento

- **Manual:** exige motivo e a confirmação digitada "CANCELAR". O contrato vira CANCELADO e a empresa CANCELADA, com revogação de sessões, tokens e Socket.IO (AJ-06.1). Nenhum dado é apagado.
- **Por expiração:** `reconciliar_vencimentos`, pelo botão em Admin → Contratos ou por `flask contratos reconciliar --aplicar`.
  - O padrão é a simulação.
  - É idempotente.
  - No PostgreSQL usa `pg_try_advisory_xact_lock` mais o lock e a reavaliação de cada empresa.
  - Quando acionada pelo botão, grava o ID do ADMIN em `detalhes.acionado_por` de cada evento de CANCELAMENTO que gerar (a origem continua RECONCILIACAO, sem `id_usuario_responsavel`). Pela CLI o operador não é registrado, e uma execução que não cancela nenhum contrato não deixa registro de quem a acionou.
- **Página "Conta encerrada"** (`templates/auth/conta_encerrada.html`):
  - aparece só depois de a senha correta ser validada;
  - não cria sessão nem flash e envia `Cache-Control: no-store`;
  - não mostra dados da empresa;
  - e-mails inexistentes passam por uma verificação de senha contra um hash fictício com o mesmo algoritmo e custo (padrão do Werkzeug), o que equipara o tempo de resposta ao de uma senha errada; o hash fictício é gerado na primeira ocorrência de cada processo, e não há teste automatizado de tempo;
  - **nenhum canal de contato foi inventado**.

### C.6 Exportação de PDFs

A rota decide **antes de gerar qualquer byte**. Para empresa sem acesso ao portal (cancelada, suspensão expirada ou regime contratual sem contrato vigente), a guarda de sessão derruba a sessão antes da rota e a requisição é redirecionada ao login (302), sem gerar PDF; o 403 da própria rota fica como camada redundante. Com acesso ao portal, a ordem é:

1. 404 se a análise não pertence à empresa, não está concluída ou não está publicada.
2. 403 se o período não está pago.
3. 403 com a mensagem definida no pedido ("Seu prazo para exportação de relatórios foi encerrado...") se a empresa está SUSPENSA fora do prazo de PDF.

O botão só aparece quando a exportação é permitida.

### C.7 Preços

- **Fonte única:** `plan_catalog.py`, com BRONZE R$ 150,00, PRATA R$ 300,00 e OURO R$ 650,00. Os benefícios não mudaram.
- **Bancos novos:** `seed.py` usa o catálogo para criar os planos ausentes.
- **Bancos existentes:** `flask planos atualizar-precos` faz a simulação por padrão.
  - A gravação exige `--aplicar --confirmo-janela-autorizada`.
  - É idempotente e registra cada mudança em `historico_preco_plano`.
  - **Não foi executado em produção.**
- **Contratos:** guardam o valor acordado e nunca são repreçados.
- **Landing e NexoBot:** continuam sem preços. A publicação é decisão pendente (documento 05, item 12).

### C.8 Interfaces

- **ADMIN:**
  - item "Contratos" na barra lateral (visão geral, pendências, reconciliação);
  - botão "Detalhes" na lista de empresas;
  - página Empresas → Detalhes com contrato vigente, situação calculada, períodos pagos consolidados, histórico de eventos e as ações;
  - formulários de contrato, renovação, troca de plano, suspensão, prorrogação, reativação, cancelamento e período pago;
  - avisos no dashboard.
- **CLIENTE:**
  - aviso de suspensão contratual com as datas-limite;
  - aviso de PDF encerrado;
  - página `acesso_restrito` (403) sem dados protegidos;
  - página de conta encerrada.
- **Identidade visual:** o cubo transparente do PR #26 foi preservado. Nenhum logotipo antigo foi restaurado.

### C.9 Autorizações

- **Política única no servidor** (`contract_policy.py`), somente leitura.
  - **Python:** `obter_situacao_contratual`, `pode_consultar_analise`, `pode_exportar_pdf`, `pode_enviar_relatorio` e `motivo_bloqueio_nova_analise`.
  - **SQL:** só a decisão de **acesso ao portal** tem forma SQL (`condicao_sql_vinculo_contratual`, dentro de `condicoes_empresa_acessivel`), usada no login, na guarda de sessão, nos tokens, no Socket.IO e nas notificações. Consulta por período pago, PDF, envio e nova análise são decididos somente em Python.
- **Testes de equivalência:** a cláusula SQL e o `acesso_portal` calculado em Python são comparados no mesmo instante, em SQLite e em PostgreSQL.
- **Relógio:** injetável (`NEXO_RELOGIO`) e fixado na primeira leitura de cada requisição (guarda de sessão, rota e template usam o mesmo instante). A única releitura deliberada é a reverificação do upload (`obter_situacao_contratual(..., atualizar=True)`), que relê empresa, contrato e relógio.
- **Ordem de locks:** Empresa → Contrato/Regime → Usuário.
- **Telas de contratos:** só para ADMIN, com CSRF global (Flask-WTF). O CLIENTE recebe 403.
- **Esquema ausente:** todas as empresas ficam no regime legado.
- **Esquema parcial:** falha fechada (`EsquemaContratualInconsistente`, subclasse de `SQLAlchemyError`).

---

## D. Banco de dados

### D.1 Novas entidades e campos

| Tabela | Campos principais |
|---|---|
| `regime_contratual` | `id_empresa` (PK e FK, chave natural), `ativado_em`, `id_usuario_admin_ativacao` |
| `contrato` | `id_contrato`, `id_empresa`, `id_plano`, `id_contrato_anterior`, `valor_mensal_contratado` NUMERIC(12,2), `data_inicio`, `data_fim`, `data_formalizacao`, `referencia_formalizacao`, `situacao`, `meses_suspensao`, `suspenso_em`, `suspensao_motivo`, `suspensao_limite_original`, `suspensao_limite`, `pdf_limite_original`, `pdf_limite`, `encerrado_em`, `cancelado_em`, `cancelamento_motivo`, `observacoes`, `id_usuario_admin_responsavel`, `versao`, `data_criacao`, `data_atualizacao` |
| `cobertura_paga` | `id_cobertura`, `id_contrato`, `id_empresa`, `periodo_inicio`, `periodo_fim`, `referencia_confirmacao`, `confirmado_em`, `id_usuario_admin_confirmacao`, `revogada_em`, `revogacao_motivo`, `id_usuario_admin_revogacao`, `data_criacao` |
| `evento_contratual` | `id_evento`, `id_empresa`, `id_contrato`, `id_cobertura`, `tipo`, `ocorrido_em`, `origem` (ADMIN ou RECONCILIACAO), `id_usuario_responsavel`, `situacao_anterior`, `situacao_posterior`, `justificativa`, `detalhes` (TEXT com JSON serializado pela aplicação; sem tipo JSON/JSONB no banco) |
| `historico_preco_plano` | `id_historico`, `id_plano`, `valor_anterior`, `valor_novo`, `alterado_em`, `origem` |

Os instantes são `timestamptz` (`InstanteUTC`). No SQLite, são texto UTC.

### D.2 Relacionamentos

- Contrato → empresa, plano e usuário.
- `id_contrato_anterior` usa FK **composta** (`fk_contrato_anterior_mesma_empresa`).
- Cobertura → contrato da mesma empresa (`fk_cobertura_contrato_mesma_empresa`).
- Evento → contrato e cobertura da mesma empresa (`fk_evento_contrato_mesma_empresa`, `fk_evento_cobertura_mesma_empresa`).
- Nenhum `relationship` ou `backref` novo foi criado em modelos existentes, e nenhuma coluna foi adicionada a `empresa`, `usuario`, `analise` ou `plano` (Etapa 0.2, G.4).

### D.3 Constraints e índices (nomeados)

- **Contrato:**
  - CHECKs: `ck_contrato_situacao`, `ck_contrato_valor`, `ck_contrato_vigencia`, `ck_contrato_meses_suspensao`, `ck_contrato_versao`, `ck_contrato_anterior_distinto`;
  - coerência de estados: `ck_contrato_suspensao` (prazos presentes, ordenados e com o PDF dentro do acesso), `ck_contrato_ativo_sem_prazos`, `ck_contrato_encerrado`, `ck_contrato_cancelado`;
  - unicidade: `uq_contrato_id_empresa`, `uq_contrato_anterior` e o índice parcial **`uq_contrato_aplicavel_empresa`** (`WHERE situacao IN ('ATIVO','SUSPENSO')`), além de `ix_contrato_empresa`.
- **Cobertura:** `ck_cobertura_periodo`, `ck_cobertura_referencia`, `ck_cobertura_revogacao` (os três campos de revogação juntos), `uq_cobertura_id_empresa`, `ix_cobertura_empresa` e `ix_cobertura_contrato`.
- **Evento:** `ck_evento_tipo`, `ck_evento_origem` (ADMIN exige responsável; RECONCILIACAO não tem), `ix_evento_empresa` e `ix_evento_contrato`.
- **Histórico de preço:** `ck_historico_preco_valor` e `ix_historico_preco_plano`.

### D.4 Migração

- **`81287c74387a_gestao_contratual.py`** (`down_revision = e4c004a26b01`): somente adição (expand). Não insere dados e não altera tabelas existentes.
- **`compare_metadata`:** vazio em SQLite e em PostgreSQL.
- **Downgrade:** recusa-se a rodar se qualquer tabela contratual tiver linhas.

### D.5 Dependências

- **SEC-004 (`e4c004a26b01`) é pré-requisito.** Segundo informação de terceiros (a verificação independente do ChatGPT), citada em `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md` e **não reverificada por falta de acesso**, a produção estaria em `b7c4e2a9f031`; o valor deve ser confirmado pela consulta somente leitura P1 antes de qualquer migração. O código da `main` já exige a SEC-004, com o incidente de HTTP 500 documentado em `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`.
- **O código contratual funciona antes da `81287c74387a`:** sem as tabelas, todas as empresas ficam no regime legado e as telas Admin → Contratos e Empresas → Detalhes exibem "Gestão contratual indisponível neste banco. A migração 81287c74387a ainda não foi aplicada.", e as operações contratuais são recusadas com mensagem equivalente.

### D.6 Estratégia de dados legados

- **Nenhum contrato é inventado** e **nenhum período é marcado como pago**.
- Após a migração, todas as empresas ficam no **regime legado**, com o comportamento anterior. A exceção é a CANCELADA, que passa a ver a página "Conta encerrada".
- **Conciliação manual, empresa a empresa** (documento 04, §4): contrato real, períodos com comprovante, suspensão com o instante real se houver, conferência e ativação das regras.
- **Ativação das regras** (`contract_admin.ativar_regras_contratuais`): exige ADMIN, justificativa, empresa fora da lixeira, regras ainda inativas, contrato vigente (ATIVO ou SUSPENSO, com a suspensão ainda não expirada) e status da empresa coerente com o contrato (SUSPENSA com SUSPENSO, ATIVA com ATIVO). **Não exige cobertura paga registrada:** se as regras forem ativadas antes do registro dos períodos pagos, o cliente perde imediatamente o acesso a todas as análises, inclusive as já publicadas. A tela de Detalhes avisa disso, e o teste `test_ativacao_exige_contrato_e_nega_sem_cobertura` cobre esse comportamento. Por isso, os períodos pagos devem ser registrados antes da ativação.
- **Desativação:** devolve a empresa ao legado e fica registrada.

---

## E. Testes

### E.1 Suíte completa (estado final do código, `800ca1d`)

Executada sobre uma cópia da árvore de trabalho idêntica ao commit `800ca1d`. Uma execução anterior, sobre `006483a`, também passou (784 testes, 0 falhas). Comando equivalente ao da CI: `python -m unittest discover -s tests -t . -v`, com o ambiente sintético (SQLite em memória, PostgreSQL 16 descartável, Chromium).

| Métrica | Resultado |
|---|---|
| Testes executados | 794 |
| Aprovados | 794 |
| Falhas | 0 |
| Erros | 0 |
| Ignorados (skips) | 0 (os módulos de PostgreSQL e de navegador coletados pelo `discover` rodaram de fato) |
| Duração | 402,9 s |

Referência: antes desta entrega, a mesma suíte tinha 649 testes, todos aprovados.

Os cinco módulos PostgreSQL executados à parte pelo job `security-postgresql` da CI (`tests/postgresql_*.py`, 33 testes) não fazem parte da contagem acima e não foram reexecutados localmente sobre o código final; o resultado deles vem da CI (seção F).

### E.2 Testes novos da gestão contratual

| Módulo | Testes | Conteúdo |
|---|---|---|
| `tests/test_contratos_prazos.py` | 23 | Aritmética de datas: 3 meses de calendário (31/01 → 28/02 em ano comum e → 29/02 em ano bissexto; 30/11 → 29/02; viradas de ano; horário), 14 dias corridos, limites exclusivos, fuso, PDF nunca além do acesso |
| `tests/test_contratos_gestao.py` | 61 | Operações, integridade, coberturas e vigência efetiva, suspensão retroativa, prorrogação, cancelamento, reconciliação (simulação e aplicação), regime, política Python × SQL, esquema ausente ou parcial, migração sobre dados legados, comandos de CLI, regressões das revisões A–E |
| `tests/test_contratos_portal.py` | 51 | HTTP do CLIENTE e do ADMIN: dashboard, histórico, análise, PDF, upload, suporte, notificações, API do NexoBot, Socket.IO, login e conta encerrada, CSRF, concorrência otimista, formulários |
| `tests/test_contratos_postgresql.py` | 1 teste com **40 verificações** | PostgreSQL 16 real e descartável (seção E.3) |
| `tests/test_contratos_navegador.py` | 7 | Chromium real (seção E.4) |

**Testes existentes ampliados:**

- `test_cancelled_company_security` e `test_cancelled_company_postgresql`: conta encerrada, `no-store`, sem fingerprint;
- `test_pdf_export_security`: bloqueio antes de gerar;
- `test_backup_restore`: 20 tabelas;
- `test_identidade_visual`.

### E.3 PostgreSQL (40 verificações, banco descartável)

1. **Migração sobre dados legados:** contagens e estados preservados, nenhum dado contratual criado, metadados iguais aos modelos, constraints nomeadas, índice parcial.
2. **`timestamptz`:** ida e volta em UTC, prazos de calendário persistidos, comparação no SQL, instante sem fuso recusado.
3. **Cláusula SQL × política:** legado, contrato ativo, suspenso dentro do prazo, no limite e depois dele, sem contrato, cancelado, limite do PDF exclusivo.
4. **Reconciliações concorrentes:** o lock consultivo bloqueia; há um único cancelamento e uma única revogação; a operação é idempotente.
5. **Contratações concorrentes:** esperam o lock da empresa; há um único vigente, inclusive em corrida real; o índice parcial é efetivo.
6. **Prorrogação × reconciliação:** quem vem primeiro decide, sem estado intermediário.
7. **Exclusão permanente:** bloqueada com histórico contratual, sem afetar as outras empresas.
8. **Downgrade:** recusado com dados contratuais; com as tabelas vazias, funciona; o acesso legado continua sem o esquema; o novo upgrade funciona.

Os testes de PostgreSQL pré-existentes da AJ-06.1 e do backup também foram executados na suíte completa.

### E.4 Navegador (Chromium real)

- Conta encerrada após o login de empresa cancelada.
- Conta encerrada no instante-limite da suspensão.
- Painel suspenso com os prazos.
- Análise sem botão de exportação no limite do PDF e depois dele.
- ADMIN: detalhes, formulários e visão geral.
- Registro de período pago pelo formulário.
- Prorrogação com `datetime-local` lido no fuso de São Paulo, com o navegador configurado em Tóquio.

### E.5 Cenários temporais (relógio injetado, sem espera real)

- **Instantes de referência:** suspensão às 10:00 locais de 02/03/2026; um instante antes, no limite e depois do acesso e do PDF.
- **Meses curtos:** 31/01 em ano comum (→ 28/02) e em ano bissexto (→ 29/02); 30/11/2027 + 3 meses → 29/02/2028.
- **Datas-limite:** virada de ano; datas antes e depois da suspensão; suspensão retroativa na conciliação.
- **Prorrogação:** depois do limite, mas antes da reconciliação; prorrogação com e sem autorização de PDF.
- **Faixa de datas:** valores fora de 2000–2100 recusados sem HTTP 500.

### E.6 Testes de segurança

- **Isolamento:** nada de uma empresa aparece para outra (404).
- **Período não pago:** 403 sem vazar texto privado, verificado com um marcador fictício.
- **PDF:** recusado antes da geração.
- **Uploads:** a situação contratual é conferida antes de ler o arquivo e reverificada depois da validação, relendo empresa, contrato e relógio (teste em que o prazo vence durante a validação).
- **Revogação de acesso:** sessão derrubada no limite; Socket.IO recusado e derrubado pela varredura; notificações e e-mails não entregues; tokens e CAS recusados.
- **Conta encerrada:** sem sessão, com `no-store`, e e-mail inexistente recebe a mensagem genérica; o teste confere que só o e-mail inexistente aciona o hash fictício. O limite de taxa é o da rota de login e não tem teste específico nesta entrega (a limitação fica desligada na base de testes); não há teste de tempo.
- **Telas de contratos:** 403 para o CLIENTE; POST sem token CSRF recusado com 400, sem alterar nada; versão desatualizada recusada; datas fora de 2000–2100 recusadas sem HTTP 500.
- **Esquema parcial:** falha fechada (503 no portal).

### E.7 Revisões independentes A–E

Cinco revisões somente leitura, cada uma com um foco:

- **A:** arquitetura;
- **B:** segurança;
- **C:** integridade financeira;
- **D:** prazos;
- **E:** regressões.

Depois, cada achado passou por verificação adversarial. No total foram 23 achados brutos, com duplicatas entre revisões. Os confirmados foram corrigidos. Uma conferência posterior (verificação dos fatos deste relatório contra o código, os testes e o histórico do Git) mostrou que **cinco** correções da primeira rodada ficaram sem teste que falhasse sem elas. Elas receberam teste na rodada seguinte (commit `800ca1d`), e cada teste novo foi comprovado em cópia descartável com a correção revertida:

| Achado (severidade) | Correção | Commit |
|---|---|---|
| "1.500" gravado como R$ 1,50 (alta, C) | Formato brasileiro aceito; formatos ambíguos recusados | `6e88df5` |
| Suspensão retroativa recusada na conciliação; prazos recomeçavam (média, B/D) | O cadastro do contrato não limita mais o instante real | `6e88df5` |
| Detalhes no regime legado sem as ações do contrato (média, D) | Contrato vigente exibido com as ações | `6e88df5` |
| Renovação ou troca de plano com início futuro encerrava o atual na hora (média, A) | A nova vigência não pode começar no futuro | `6e88df5` |
| Nova análise de período do contrato anterior recusada (média, A/C) | Vale a vigência efetiva de qualquer contrato não cancelado; grava o plano desse contrato, inclusive na regra QUINZENAL | `6e88df5` |
| Cobertura aceita após o encerramento ou o cancelamento (média, C) | Limitada à vigência efetiva | `6e88df5` |
| Exclusão permanente apagava o histórico financeiro (média, C) | Bloqueada com histórico contratual | `6e88df5` |
| Esquema parcial derrubava a varredura do Socket.IO (baixa, A) | Vira `SQLAlchemyError`, com falha fechada | `6e88df5` |
| `analise_nova` sem o lock da empresa (baixa, A) | Decisão tomada com a empresa bloqueada | `6e88df5` |
| FK simples evento → cobertura (baixa, A) | FK composta | `6e88df5` |
| Reverificação do upload com objetos e relógio antigos (baixa, B/D) | Relê empresa, contrato e relógio | `6e88df5` |
| Datas perto de 9999 geravam HTTP 500 (baixa, B/D) | Faixa 2000–2100 | `6e88df5` |
| Reconciliação pelo botão sem autor (baixa, C) | Registra `acionado_por` | `6e88df5` |
| N+1 no dashboard e no histórico do cliente (E) | Carregamento em lote (`selectinload`); teste compara o número de consultas com 1 e com 3 análises | `006483a` |
| Textos do NexoBot errados para o regime legado (E) | Textos distinguem o legado do contratual, sem prazos nem valores | `006483a` |
| Contratar empresa SUSPENSA a reativava em silêncio (E) | Mantém SUSPENSA; a ativação das regras exige status coerente | `006483a` |
| Painel do ADMIN contava suspensões legadas como reconciliáveis (E) | Conta só as do regime contratual | `006483a` |
| Empresa SUSPENSA com contrato ATIVO ficava sem caminho para ATIVA após a correção anterior (média, verificação posterior à E) | Ação explícita e auditada "Reativar empresa"; avisos e mensagens apontam para ela | `800ca1d` |
| Renovação ou troca de plano reativava em silêncio a empresa SUSPENSA com contrato ATIVO (baixa, idem) | Não reativa; contrato SUSPENSO renovado continua reativando | `800ca1d` |
| Painel contava suspensão legada em "terminando em breve" e a deixava sem alerta ao vencer (baixa, idem) | Prazos só no regime contratual; legada vencida conta como pendência de conciliação | `800ca1d` |

**Achados não acatados:**

- **Publicação com HTTP 500 após o commit (E):** refutado na verificação. O código anterior já lia o banco depois do commit, fora do `try`.
- **Atualização do catálogo reprecifica a receita estimada das empresas legadas (baixa, C):** é o comportamento esperado, porque empresas sem contrato não têm valor acordado. Ficou registrado como pendência 19 do documento 05. A atualização não foi executada.

**Cobertura de regressão das correções:**

- **Revisão E (`006483a`):** as quatro correções têm teste que falha sem elas (N+1, SUSPENSA na contratação, contagem do painel e textos do NexoBot), comprovado em cópias descartáveis com a correção revertida.
- **Primeira rodada (`6e88df5`), testes acrescentados em `800ca1d`:** faixa de datas pelo HTTP, reverificação do upload, quem acionou a reconciliação pelo botão, lock da empresa em `analise_nova` e a FK composta evento → cobertura (agora na lista de constraints nomeadas do teste PostgreSQL).
- **Segunda rodada (`800ca1d`):** os testes de conciliação completa pelo HTTP, da renovação de contrato ATIVO com empresa SUSPENSA e do painel falham sem a correção.
- **Comprovação:** com seis correções revertidas ao mesmo tempo numa cópia descartável, os testes correspondentes falharam (9 falhas e 3 erros em 111 testes); com o código restaurado, passaram.
- **Sem mutação própria:** o teste de CSRF negativo (POST sem token → 400) e o do hash fictício não foram verificados por reversão do código de produção; o de CSRF confirma a proteção global já existente.

---

## F. GitHub

- **Branch publicada:** `claude/awesome-pascal-0ho42m`.
- **Pull Request:** https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/pull/27. Esteve em rascunho com o aviso "não fazer merge ainda" e foi marcado como pronto para revisão e **mesclado pelo proprietário em 26/10/2026 às 16:20 UTC**, no merge `dcaa89643d7ead3889d493c02cab190f4547a7b4`. Os commits abaixo, até `800ca1d`, estão na `main`.

| SHA | Commit |
|---|---|
| `003d3f111a04e0645a9ee8f75b0378d1c36211ce` | feat(contracts): implementar modelos e migracoes contratuais |
| `dbd093a55ea3af5ebfed220ee32c81c0f78cf90a` | feat(plans): atualizar catalogo Bronze Prata e Ouro |
| `4f120153b31707009aff36078a6408948a75a8aa` | feat(contracts): implementar gestao administrativa e historico |
| `aa8dde2f3b10da7763f50e0d768fe1f49519e0c8` | feat(access): controlar suspensao e cobertura paga |
| `1f135ab8c088f9a6d20097fae2fb5f1d16a44a2d` | feat(pdf): limitar exportacao durante suspensao |
| `a428472574c94c83c1a6cd6f49ee5b12a4be044c` | feat(auth): adicionar experiencia de conta cancelada |
| `9cbc942e69d70099ded71c7a9e99029d180b13de` | test(contracts): cobrir ciclo contratual e regras temporais |
| `02d4787bd498743ae9989dad511f9639a7cd6308` | docs(contracts): documentar regras e implantacao segura |
| `059508e6fefd172672c4548c8877c299326d3188` | test(contracts): validar gestao contratual em PostgreSQL real |
| `d4258663950d8a686d5b13d4a6b94895b5890953` | test(contracts): cobrir portal HTTP e navegador da gestao contratual |
| `6e88df542cc99e43469d3c79efb1b7f86d0e9346` | fix(contracts): corrigir achados das revisoes independentes A-D |
| `006483a42a64f6ed02d3abd04e703c5becacbeac` | fix(contracts): corrigir achados da revisao E |
| `389e547c5f7796e2169e4b5eedfdfca24fa260fc` | docs(contracts): registrar convencao da receita estimada sem contrato |
| `800ca1d39986cf02a927e9d8abbfc8b4e739e5f0` | fix(contracts): fechar a conciliacao de empresa suspensa e cobrir achados sem teste |
| `dcaa89643d7ead3889d493c02cab190f4547a7b4` | Merge pull request #27 (feito pelo proprietário) |
| (posterior ao merge) | docs(contracts): relatorio de implementacao para auditoria (PR de documentação à parte) |

**Situação da CI** (GitHub Actions, jobs `security-sqlite-browser` e `security-postgresql`) no momento da redação:

- **Verdes:** `02d4787` e `059508e`.
- **`6e88df5`:** `security-postgresql` verde; `security-sqlite-browser` **cancelado** pela própria CI, ao ser substituído pelo push seguinte (run 40348812711). Não houve falha.
- **`389e547` (PR, run 40351703621):** `security-postgresql` verde; `security-sqlite-browser` **cancelado** depois de 20 min. O job tem `timeout-minutes: 20`, e o passo de instalação do navegador (`playwright install-deps`) levou cerca de 18 minutos nessa execução, de modo que o passo da suíte nem chegou a rodar. A causa parece ser de infraestrutura: a execução de `059508e` terminou o job inteiro em cerca de 6 minutos e, nas execuções seguintes (`800ca1d` e `main`), o mesmo passo de instalação do navegador levou cerca de 10 segundos. É uma inferência: o job de `389e547` não foi reexecutado.
- **`800ca1d` (PR, run 40358095861):** estava **pendente** quando o proprietário fez o merge. Depois terminou **verde** nos dois jobs: `security-postgresql` e `security-sqlite-browser` (suíte completa, navegador e ensaio de backup, passo de cerca de 7,5 minutos).
- **`main` após o merge (`dcaa896`, run 40358112023):** **verde** nos dois jobs, `security-postgresql` e `security-sqlite-browser` (conferido em 26/10/2026 às 16:30 UTC). **A CI completa do código final está, portanto, confirmada na `main`**, em acordo com a suíte local (E.1, 794 testes).

**Estado do merge:** **mesclado na `main` pelo proprietário** (`dcaa896`). Eu havia recomendado esperar a produção chegar, no mínimo, à revisão `e4c004a26b01` (seção H.4), porque o `render.yaml` declara `autoDeployTrigger: 'off'`, mas o proprietário informou Auto-Deploy **ativado** na `main` (SEC-006, `Docs/PREPARACAO_RENDER.md`), e o estado real do painel não é verificável daqui; deve-se presumir que um merge na `main` dispara implantação. **Decisão do proprietário:** fazer o merge mesmo com o login da produção em HTTP 500 (erro já existente, ligado à SEC-004), porque a correção desse erro será tratada em separado. Esta entrega não agrava nem corrige esse erro. Depois do merge, **verificar no painel do Render se houve publicação automática e qual commit está no ar.**

---

## G. Produção

Confirmo expressamente:

- **Nenhum dado de produção foi alterado.**
- **Nenhuma migração foi executada no Supabase.** Nenhum `flask db upgrade`, `downgrade` ou `stamp` foi executado contra produção. Todas as migrações rodaram em SQLite em memória ou em PostgreSQL local e descartável.
- **Nenhum deploy manual foi realizado por mim no Render.** Nenhuma variável foi alterada e nenhuma tarefa agendada foi criada. **O merge feito pelo proprietário pode ter disparado publicação automática**, se o Auto-Deploy estiver ativo; isso não é verificável daqui e precisa ser conferido no painel.
- **Nenhuma senha ou credencial foi modificada.** Os testes usam apenas senhas sintéticas.
- **Nenhuma informação confidencial foi publicada.** Não há `.env`, tokens, banco real nem capturas privadas. Os dados de teste são fictícios (`example.invalid`).
- **Os preços não foram atualizados no banco de produção.** O comando de atualização existe, mas não foi executado.

---

## H. Pendências

### H.1 Funcionalidades concluídas (no ambiente de testes)

- Contratos com histórico: contratação, renovação, troca de plano, versão e auditoria.
- Coberturas pagas e direito por período.
- Suspensão com os prazos de 3 meses e 14 dias.
- Prorrogação auditável.
- Cancelamento manual e por reconciliação.
- Bloqueio total via AJ-06.1.
- Página de conta encerrada.
- PDF com prazo.
- Novo catálogo de preços com atualização auditada.
- Telas do ADMIN e avisos do CLIENTE.
- Habilitação gradual por empresa.
- Testes em SQLite, PostgreSQL e navegador.
- Documentos 01 a 05.

### H.2 Funcionalidades parcialmente concluídas

- **Preços:** aplicados no catálogo, no seed e nas telas do ADMIN. A **landing** e o **NexoBot** continuam sem preço por decisão pendente.
- **Aviso de renovação ao cliente (AJ-04.x):** não implementado. Só a visão do ADMIN mostra os contratos perto do vencimento.
- **Renovação e troca de plano agendadas:** não suportadas.
- **Comprovante anexado e integração com gateway:** não existem. A confirmação é manual, com referência.
- **Reconciliação automática:** sem agendador. A segurança não depende dele.

### H.3 Decisões comerciais pendentes (documento 05)

Duração dos contratos; comprovação dos pagamentos; data exata de início da suspensão; contagem dos 14 dias; contagem dos três meses; condições de prorrogação; atendimento durante a suspensão; reativação; contratos antigos e prazo de conciliação; direito à análise quando ATIVA; contrato vencido sem renovação; publicação de preços; canal oficial de contato; agendamento da reconciliação; retenção do histórico contratual; receita estimada de empresas sem contrato (item 19, convenção implementada). Os itens 13 e 18 estão na H.2; o item 15 não exige decisão.

**Todas estão implementadas como convenções propostas, parametrizadas e testadas, e não como decisões aprovadas.**

### H.4 Dependências de produção

1. Backup verificado (`Docs/OPERACAO_BACKUP_RESTAURACAO.md`).
2. Produção na revisão `e4c004a26b01` (SEC-004), em janela própria.
3. `81287c74387a`, aplicada pelo ID.
4. Merge (**já feito pelo proprietário**) e deploy (a verificar no painel).
5. Atualização de preços, somente com autorização.
6. Homologação.
7. Conciliação gradual.

O roteiro completo está no documento 04. **Dos passos acima, só o merge foi feito, pelo proprietário.** Os demais não foram executados por mim.

### H.5 Riscos técnicos restantes

- **Auto-Deploy:** o `render.yaml` declara `off`, mas o proprietário informou (SEC-006) que está **ativado** na `main`; o painel não é verificável daqui, então se presume que o merge publica. Um merge antes da SEC-004 em produção repetiria o incidente de HTTP 500 do login, que já existe na `main` independentemente desta entrega.
- **Rollback:**
  - reverter o código não desfaz a migração;
  - o downgrade da `81287c74387a` se recusa a rodar com dados;
  - empresas canceladas continuam CANCELADAS.
- **Conciliação:** é manual e depende de documentação real de cada empresa. Enquanto não for feita, as empresas seguem no regime legado.
- **Desempenho no plano gratuito do Render:** cada rota do cliente ganhou ao menos uma consulta (regime). No regime contratual, há também as consultas do contrato aplicável e das coberturas pagas, e a guarda de sessão ganhou subconsultas na cláusula SQL. O N+1 detectado foi corrigido. Não houve teste de carga.
- **Validação:** os testes rodaram em ambiente sintético. Falta a homologação com dados reais anonimizados.

---

## I. Conclusão

**Classificação: IMPLEMENTADO E VALIDADO EM AMBIENTE DE TESTES · AGUARDANDO HOMOLOGAÇÃO.**

**Por que a primeira classificação se aplica:**

- As cinco regras do pedido estão implementadas no servidor, com política única, testes temporais e de segurança, verificação em PostgreSQL real e em navegador, e cinco revisões independentes com os achados confirmados corrigidos.
- A suíte completa passou (seção E.1).

**Por que ainda aguarda homologação:**

- As convenções de prazo, de prorrogação e de comprovação, assim como a publicação de preços, são **propostas** que dependem do proprietário (documento 05).

**Por que não é "pronto para implantação controlada" nem "pronto para produção":**

- Depende da SEC-004 em produção, de backup verificado, da migração `81287c74387a` em janela autorizada e da homologação.
- Nada disso foi executado nesta atividade.
- O código já está na `main`. Sem a migração `81287c74387a`, todas as empresas ficam no regime legado e as telas de contratos mostram o aviso de migração pendente, mas isso não substitui a SEC-004, que a `main` já exigia.
