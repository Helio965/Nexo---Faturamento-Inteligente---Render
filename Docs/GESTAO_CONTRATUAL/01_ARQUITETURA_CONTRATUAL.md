# 01 — Arquitetura contratual

Gestão contratual e ciclo de vida das empresas do NEXO. Implementação na branch `claude/awesome-pascal-0ho42m` (PR para a `main`). Nada foi aplicado em produção.

## 1. Visão geral

```
Plano (catálogo público) ──┐
                           ├─> Contrato (acordo com a empresa; snapshot do valor)
Empresa ───────────────────┘        │
   │                                ├─> CoberturaPaga (períodos efetivamente pagos)
   │                                └─> EventoContratual (histórico, somente inclusão)
   └─> RegimeContratual (habilitação gradual das regras, por empresa)

contract_policy.py  — decisões (somente leitura): estado efetivo, acesso, consulta, PDF, envio
contract_admin.py   — operações transacionais: contratar, renovar, trocar plano, suspender,
                      prorrogar, reativar, cancelar, coberturas, regras, reconciliação
blueprints/contratos.py — telas ADMIN (Empresas → Detalhes → Contratos; visão geral)
cli_contratos.py    — `flask contratos reconciliar` e `flask planos atualizar-precos` (simulação padrão)
plan_catalog.py     — fonte única dos preços e benefícios padrão dos planos
```

A política é **uma só** e roda no servidor. Ela aparece de duas formas equivalentes:

- **Python** (`obter_situacao_contratual`, `pode_consultar_analise`, `pode_exportar_pdf`, `pode_enviar_relatorio`, `motivo_bloqueio_nova_analise`). Usada pelas rotas do cliente, pela publicação de devolutivas, pela abertura de análises e pelo login (página de conta encerrada).
- **SQL** (`condicao_sql_vinculo_contratual`). Entra em `session_security.condicoes_empresa_acessivel`, o critério único da NEXO-AJ-06.1, e por isso vale para login, guarda de sessão a cada requisição, tokens de senha, troca de senha (CAS), Socket.IO (handshake, eventos, varredura de 1 s) e notificações.

Testes comparam as duas formas no mesmo instante: SQLite em `tests/test_contratos_gestao.py` e PostgreSQL em `tests/test_contratos_postgresql.py`.

## 2. Entidades

### 2.1 `regime_contratual` (`RegimeContratual`)

| Campo | Tipo | Regra |
|---|---|---|
| `id_empresa` | int, PK e FK `empresa` | Chave natural, sem sequência |
| `ativado_em` | timestamptz | Instante da ativação |
| `id_usuario_admin_ativacao` | FK `usuario` | Administrador responsável |

A presença da linha significa **regras contratuais ativas** para a empresa; a ausência significa regime legado. A ativação e a desativação geram `EventoContratual` (`REGRAS_ATIVADAS` / `REGRAS_DESATIVADAS`).

**Por que uma tabela própria em vez de uma coluna em `empresa`:** a Etapa 0.2 (G.4, padrão expand → migrate → deploy) proíbe colunas novas em `Empresa`, `Usuario`, `Analise` e `Plano` enquanto não houver garantia de que a migração chega antes do código. Uma coluna nova mapeada no ORM quebraria todas as consultas de `Empresa` se o código fosse implantado antes da migração. Foi o que aconteceu com `usuario.geracao_autorizacao`: o login em produção deu HTTP 500.

### 2.2 `contrato` (`Contrato`)

| Campo | Tipo | Regra |
|---|---|---|
| `id_contrato` | PK | |
| `id_empresa` | FK `empresa` | |
| `id_plano` | FK `plano` | Plano contratado |
| `id_contrato_anterior` | int, único | Contrato renovado ou substituído. FK composta `(id_contrato_anterior, id_empresa)` → `contrato(id_contrato, id_empresa)`: a ligação sempre aponta para um contrato da mesma empresa |
| `valor_mensal_contratado` | numeric(12,2) | Snapshot do valor acordado; CHECK ≥ 0. Não muda quando o catálogo muda |
| `data_inicio` / `data_fim` | date | `data_fim` nulo = prazo indeterminado; CHECK `data_fim >= data_inicio` |
| `data_formalizacao`, `referencia_formalizacao` | date, texto(200) | Registro da formalização. Não há assinatura eletrônica nem guarda de documentos |
| `situacao` | `ATIVO`, `SUSPENSO`, `ENCERRADO`, `CANCELADO` | CHECK nomeado |
| `meses_suspensao` | int 1–12 (a aplicação limita ao máximo configurado) | Prazo menor previsto em contrato; nulo = padrão |
| `suspenso_em`, `suspensao_motivo` | timestamptz, texto | Instante oficial e motivo da suspensão |
| `suspensao_limite_original`, `suspensao_limite` | timestamptz | O original nunca muda; a prorrogação move só o vigente |
| `pdf_limite_original`, `pdf_limite` | timestamptz | Prazo de exportação de PDF; só aumenta com autorização contratual específica |
| `encerrado_em`, `cancelado_em`, `cancelamento_motivo` | timestamptz, texto | |
| `observacoes` | texto | |
| `id_usuario_admin_responsavel` | FK `usuario` | Quem registrou |
| `versao` | int ≥ 1 | Controle otimista: o formulário envia a versão exibida |
| `data_criacao`, `data_atualizacao` | timestamptz | |

**Restrições nomeadas:**

- `ck_contrato_situacao`, `ck_contrato_valor`, `ck_contrato_vigencia`, `ck_contrato_meses_suspensao`, `ck_contrato_versao`, `ck_contrato_anterior_distinto`.
- `ck_contrato_suspensao`: um contrato SUSPENSO tem todos os prazos preenchidos, e eles respeitam a ordem limite original > início, limite ≥ original, PDF original > início, PDF ≥ PDF original e PDF ≤ limite.
- `ck_contrato_ativo_sem_prazos`: um contrato ATIVO não tem prazos de suspensão nem datas de encerramento ou cancelamento.
- `ck_contrato_encerrado` e `ck_contrato_cancelado`: exigem a data e, no cancelamento, também o motivo.
- `uq_contrato_id_empresa`: alvo das FKs compostas.
- `uq_contrato_anterior`: cada contrato tem no máximo um sucessor.
- **Índice único parcial `uq_contrato_aplicavel_empresa`** em `(id_empresa) WHERE situacao IN ('ATIVO','SUSPENSO')`: no máximo um contrato vigente por empresa, garantido pelo banco tanto no PostgreSQL quanto no SQLite.

### 2.3 `cobertura_paga` (`CoberturaPaga`)

| Campo | Tipo | Regra |
|---|---|---|
| `id_cobertura` | PK | |
| `id_contrato`, `id_empresa` | FK composta → `contrato(id_contrato, id_empresa)` | Impede que uma cobertura fique ligada ao contrato de outra empresa |
| `periodo_inicio`, `periodo_fim` | date | Intervalo inclusivo; CHECK `fim >= inicio`; a aplicação exige que esteja dentro da vigência do contrato |
| `referencia_confirmacao` | texto(200), não vazio | Referência administrativa (comprovante, nota) |
| `confirmado_em`, `id_usuario_admin_confirmacao` | timestamptz, FK | |
| `revogada_em`, `revogacao_motivo`, `id_usuario_admin_revogacao` | | Revogação auditada. O CHECK `ck_cobertura_revogacao` exige os três campos juntos |

O registro é imutável: para corrigir, revoga-se a cobertura com motivo e registra-se outra. A sobreposição entre coberturas vigentes da mesma empresa é recusada pela aplicação, sob o lock da empresa.

### 2.4 `evento_contratual` (`EventoContratual`)

Trilha somente de inclusão. Tem os campos `tipo` (CHECK nomeado), `ocorrido_em`, `origem` e `id_usuario_responsavel`. O CHECK `ck_evento_origem` amarra os dois últimos: `ADMIN` exige responsável e `RECONCILIACAO` exige responsável nulo. Também guarda `situacao_anterior`/`situacao_posterior`, `justificativa` e `detalhes` (JSON com os valores anteriores e novos), e se liga à cobertura e ao contrato pela FK composta. A aplicação nunca altera nem apaga um evento; a única exceção é a exclusão permanente da empresa, que já existia (ver §5).

Tipos registrados: `CONTRATACAO`, `RENOVACAO`, `ALTERACAO_PLANO`, `SUSPENSAO`, `PRORROGACAO`, `REATIVACAO`, `CANCELAMENTO`, `COBERTURA_CONFIRMADA`, `COBERTURA_REVOGADA`, `REGRAS_ATIVADAS` e `REGRAS_DESATIVADAS`.

### 2.5 `historico_preco_plano` (`HistoricoPrecoPlano`)

Cada alteração de `plano.valor_mensal` feita pela atualização do catálogo registra plano, valor anterior, valor novo, instante e origem (versão do catálogo).

## 3. Tempo e fuso

- Os instantes contratuais usam o tipo `InstanteUTC` (`models.py`).
  - **PostgreSQL:** `timestamptz`.
  - **SQLite:** texto UTC em formato fixo, o que mantém corretas as comparações SQL de prazo.
  - Instante sem fuso é recusado na gravação.
- Relógio único: `contract_policy.agora()`. Testes injetam o relógio com `app.config["NEXO_RELOGIO"]`, e o instante fica fixo durante a requisição. O relógio do navegador nunca é usado.
- Os prazos são calculados no fuso `CONTRATO_FUSO_HORARIO` (padrão `America/Sao_Paulo`) e gravados em UTC.
- Na tela, as datas aparecem no mesmo fuso (filtro Jinja `instante_local`).

## 4. Implantação gradual e esquema ausente

`contract_policy.esquema_contratual_disponivel()` confere se as cinco tabelas existem. O resultado é guardado por engine; uma ausência é reavaliada a cada 30 s.

- **Antes da migração:** todo o sistema fica no regime legado. A cláusula SQL vira `TRUE`, a política devolve LEGADO e as telas de contratos avisam que a migração está pendente. Nenhuma tabela nova é consultada.
- **Esquema parcial ou erro de consulta:** falha fechado (exceção).
- **Depois da migração:** cada empresa continua no regime legado até o administrador concluir a conciliação e ativar as regras (§2.1).

## 5. Integrações com o que já existia (reutilizado, não refeito)

| Área | Como se integra |
|---|---|
| NEXO-AJ-06.1 | `condicoes_empresa_acessivel()` ganhou a terceira condição (vínculo contratual), sem perder as outras duas. Status `CANCELADA` continua bloqueando. Toda transição contratual de status passa por `company_security.aplicar_status_conta`, que revoga as sessões ao entrar ou sair de CANCELADA (geração persistente). A ordem dos locks é Empresa → Contrato/Regime → Usuario |
| Rotas do cliente | Dashboard, histórico, análise, PDF e upload consultam a política. Os dados não autorizados não chegam ao HTML nem ao JSON do gráfico. O gráfico histórico usa só as análises autorizadas |
| Login | Senha correta de conta encerrada mostra `auth/conta_encerrada.html`, sem sessão. E-mail inexistente agora custa um hash fictício, o que elimina a diferença de tempo que permitia enumerar contas |
| Admin | Novo item "Contratos" na barra lateral e botão "Detalhes" na lista de empresas. A edição da empresa bloqueia status e plano quando há contrato vigente ou regras ativas. `analise_nova` respeita a vigência e grava o plano do contrato. O dashboard soma o valor contratado na receita estimada e mostra as pendências. A publicação só avisa o cliente se ele puder consultar a análise |
| Exclusão permanente | Remove eventos, coberturas, contratos e regime antes dos usuários (só quando o esquema existe) |
| NexoBot | Os textos sobre suspensão, PDF e planos foram ajustados, sem citar prazos nem valores (regra editorial do bot) |
| Backup | O inventário do documento operacional e o ensaio de backup/restauração cobrem as cinco tabelas novas |

## 6. Migração

A revisão é `81287c74387a` (`down_revision = e4c004a26b01`).

- **Upgrade:** cria apenas tabelas novas, índices, FKs e CHECKs. Não insere dados e não altera colunas existentes.
- **Downgrade:** recusa-se a rodar se houver qualquer linha nas tabelas novas.

Validação: `compare_metadata` vazio e ida e volta de upgrade/downgrade em SQLite e PostgreSQL 16 descartável. Os detalhes de implantação estão no documento 04.

## 7. Justificativas técnicas

- **Contrato separado do catálogo.** Mudar o preço público não altera valores acordados, e trocar de plano preserva o contrato anterior.
- **Coberturas como intervalos, não como flag de pagamento.** Análises criadas depois podem referir-se a períodos pagos; o direito vem do intervalo pago, não da data de criação do registro.
- **Período exigido = período declarado ampliado pelo período real da base** (`indicador_analise.periodo_base_*`). Assim, nenhum dado de período não pago chega ao cliente por indicadores agregados.
- **Limites gravados no instante da suspensão.** Mudar a configuração depois não altera suspensões em curso.
- **Validação da expiração dentro do SQL.** A política reconhece o fim do prazo mesmo que a reconciliação ainda não tenha gravado o cancelamento.
