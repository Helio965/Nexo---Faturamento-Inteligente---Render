# 04 — Plano de migração e implantação

> **Nada deste plano foi executado em produção.** Nenhuma migração rodou no Supabase, nenhum deploy foi feito no Render e nenhuma variável foi alterada. Os passos abaixo são para uma janela futura autorizada pelo proprietário.

## 1. Migrações necessárias

| Ordem | Revisão | Conteúdo | Observação |
|---|---|---|---|
| 1 | `e4c004a26b01` (SEC-004) | `usuario.geracao_autorizacao` e o bloqueio conservador da lixeira legada | **Pré-requisito.** Na última verificação, a produção estava em `b7c4e2a9f031`, e o código atual da `main` já exige esta revisão (login com HTTP 500 sem ela). Tem janela própria: escritores parados, conforme `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md` |
| 2 | `81287c74387a` (gestão contratual) | Tabelas `regime_contratual`, `contrato`, `cobertura_paga`, `evento_contratual` e `historico_preco_plano`, com índices, FKs e CHECKs nomeados | Somente adição (expand). Não insere dados nem altera tabelas existentes |

## 2. Dependência da SEC-004

O código desta entrega mantém todas as proteções da SEC-004 e da AJ-06.1 (geração persistente, revogação, Socket.IO). Por isso ele **também** precisa da `e4c004a26b01`. A revisão contratual vem depois dela na cadeia Alembic.

## 3. Compatibilidade com o deploy automático

O Auto-Deploy da `main` no Render pode estar ativo, e isso não é verificável daqui. Para reduzir o risco, o código foi feito para funcionar **antes** da revisão `81287c74387a`:

- Nenhuma coluna foi adicionada a modelos existentes. A flag de regime é uma tabela própria.
- `esquema_contratual_disponivel()` detecta a ausência das tabelas novas e mantém todas as empresas no regime legado, sem consultá-las. As telas de contratos mostram o aviso "migração pendente".
- Se o esquema estiver **parcial**, ou se a consulta ao catálogo falhar, o sistema falha fechado.

Isso **não** dispensa a `e4c004a26b01`, que o código anterior a esta entrega já exigia. **Recomendação:** não fazer o merge na `main` enquanto a produção não estiver, no mínimo, em `e4c004a26b01`. Depois, aplicar `81287c74387a` na mesma janela ou em outra.

## 4. Estratégia para dados legados

- **Nenhum contrato é inventado** e **nenhum período anterior é marcado como pago**. Após a migração, todas as empresas ficam no **regime legado**, com o comportamento atual.
- **Conciliação administrativa**, empresa por empresa, em Admin → Empresas → Detalhes:
  1. Localizar a documentação do acordo real (data, plano, valor, vigência).
  2. "Novo contrato", com a formalização e a referência do documento.
  3. "Registrar período pago", somente para os períodos com comprovante.
  4. Se a empresa estiver suspensa de fato: "Suspender", informando o **instante real** da suspensão (o retroativo é permitido até o início do contrato ou a última alteração).
  5. Conferir em Detalhes a situação calculada e os períodos consolidados.
  6. "Ativar regras contratuais", com justificativa.
- **Empresas CANCELADAS:** continuam bloqueadas no regime legado. Se for necessário registrar o histórico contratual delas, crie o contrato e cancele-o. Atenção: criar um contrato **reativa** a empresa até o cancelamento, por isso faça os dois passos em sequência e fora do horário de uso.
- **A visão geral (Admin → Contratos)** lista as empresas ainda no regime legado e as pendências.

## 5. Procedimento de backup (antes de qualquer migração)

Seguir `Docs/OPERACAO_BACKUP_RESTAURACAO.md`, que já inclui as cinco tabelas novas no inventário. Em resumo:

1. Dump lógico completo em formato customizado (`pg_dump -Fc`), pela conexão direta.
2. Conferir `pg_restore --list`, o SHA-256 e o tamanho.
3. Fazer uma restauração isolada de verificação, em banco descartável.
4. Guardar o arquivo em local privado e cifrado.

O ensaio automatizado (`tests.test_backup_restore`) cobre as 20 tabelas (19 do ORM mais `alembic_version`).

## 6. Ordem de implantação recomendada

1. Backup verificado (§5).
2. `NEXO_DB_DIRECT=1 flask db current`: somente leitura, confirma a revisão.
3. Se estiver em `b7c4e2a9f031`, aplicar **primeiro** `flask db upgrade e4c004a26b01`, na janela da SEC-004.
4. `flask db upgrade 81287c74387a`, **pelo ID**, nunca `head` às cegas. Usar `lock_timeout` e `statement_timeout` na sessão.
5. Conferir o esquema: as cinco tabelas, o índice `uq_contrato_aplicavel_empresa` e `SELECT COUNT(*)` igual a zero nas tabelas novas.
6. Merge e deploy do código, já com o esquema pronto.
7. Atualizar os preços do catálogo, **somente com autorização**:
   1. `flask planos atualizar-precos` (simulação; conferir a saída).
   2. `flask planos atualizar-precos --aplicar --confirmo-janela-autorizada`.
8. Homologação: login ADMIN e CLIENTE; uma empresa de teste no regime contratual; PDFs; página de conta encerrada.
9. Conciliação gradual das empresas (§4).

## 7. Habilitação gradual

- A habilitação é por empresa, pela ativação explícita das regras, sempre registrada em evento.
- Para retirar uma empresa sem migração, use "Desativar regras contratuais" (registrado). Ela volta ao regime legado.
- A reconciliação de vencimentos atua **somente** sobre empresas no regime contratual.
- **Nenhuma tarefa automática foi configurada no Render.** A reconciliação pode ser feita pelo botão em Admin → Contratos ou por `flask contratos reconciliar --aplicar`, em execução manual ou futura tarefa agendada aprovada. A segurança não depende dela: a expiração já é aplicada pela política no instante-limite.

## 8. Verificações posteriores

- `/healthz/db`; login ADMIN; login CLIENTE ATIVO (regime legado) sem mudança de comportamento.
- Admin → Contratos sem o aviso de "migração pendente".
- `flask contratos reconciliar` em simulação: lista vazia ou somente casos esperados.
- Logs sem erros de esquema (`UndefinedTable`, `UndefinedColumn`).

## 9. Riscos de rollback

- **Reverter o código não desfaz a migração.** O código anterior ignora as tabelas novas, e elas podem permanecer.
- **O downgrade da `81287c74387a` recusa-se a rodar** se houver qualquer linha contratual: ele apagaria contratos, pagamentos e auditoria. Prefira manter as tabelas e desativar as regras por empresa.
- **Empresas canceladas pela gestão contratual continuam com `status_conta = CANCELADA`** após um rollback de código. Reverter isso é decisão administrativa, feita pela edição da empresa e auditada.
- **O downgrade da `e4c004a26b01`** tem as restrições próprias documentadas na SEC-004.

## 10. Procedimento de recuperação

1. **Falha durante a migração `81287c74387a`:** no PostgreSQL ela é atômica (DDL transacional) e a revisão permanece `e4c004a26b01`. Corrigir a causa e repetir.
2. **Erro funcional após o deploy:**
   - Desativar as regras das empresas afetadas, o que as devolve ao regime legado.
   - Se necessário, reverter o código. As tabelas ficam.
3. **Corrupção ou perda de dados:** restaurar o backup do §5, seguindo o documento operacional (restauração em banco novo, verificação e troca controlada).
