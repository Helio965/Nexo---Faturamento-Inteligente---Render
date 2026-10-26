# Controle dos prompts NEXO-AJ

Registro do andamento dos 27 prompts de ajuste do NEXO. Cada prompt executado deve atualizar a sua linha e o seu registro de execução e produzir `Docs/AJUSTES_NEXO_2026/RELATORIO_<ID>_PARA_CHATGPT.md`. **Nenhum prompt é considerado aprovado só porque o Claude Code declarou sucesso:** a coluna "Aprovação" é preenchida apenas pela revisão humana.

Última atualização: 26/10/2026, integração do ZIP local ao repositório oficial no GitHub (histórico no fim do arquivo).

## Atualização de 26/10/2026: mudança de metodologia e integração ao GitHub

**Metodologia.** O proprietário decidiu **não usar mais a sequência dos 27 prompts como roteiro obrigatório**. O mapa e este controle continuam valendo como **referências técnicas e registro histórico**: as funcionalidades já implementadas são preservadas, os requisitos continuam relevantes, as etapas podem ser executadas em outra ordem e as próximas atividades serão priorizadas conforme as necessidades atuais do projeto. A coluna "Ordem" e a seção "Ordem recomendada" passam a ser apenas informativas, e não há mais "próximo prompt" obrigatório. Os itens "NÃO EXECUTADO" **não** devem ser desenvolvidos automaticamente.

**Integração.** O conteúdo local (ZIP derivado do commit `ff8c2d8` da `main`) foi conciliado com a `main` do repositório `Helio965/Nexo---Faturamento-Inteligente---Render` (base `94e9b6a`), indicado pelo proprietário como oficial no pedido de integração e com a Etapa 0.2 do PR #22. Detalhes, inventário, testes e pendências: [`Docs/INTEGRACOES/RELATORIO_INTEGRACAO_GITHUB_ZIP_2026_10_26.md`](../INTEGRACOES/RELATORIO_INTEGRACAO_GITHUB_ZIP_2026_10_26.md). Integrar à `main` **não** significa implantar em produção.

**Situação por ambiente em 26/10/2026** (somente as atividades com execução registrada):

| Atividade | Implementada localmente | Integrada ao GitHub | Testada | CI | Homologação | Implantação em produção |
|---|---|---|---|---|---|---|
| Etapa 0.1 (baseline, PR #19) | Não (feita no GitHub) | Sim, na `main` (PR #19) | Não se aplica (documentação) | Aprovada no PR #19 | Não se aplica | Não se aplica |
| Etapa 0.2 (PR #22) | Não (feita no GitHub) | Na branch `feature/reestruturacao-comercial-nexo`; trazida para a linha da `main` pelo PR de integração | Não se aplica (documentação e `.gitignore`) | Ver PR de integração | Não se aplica | Não se aplica |
| Etapa 0.2A (backup e migrações) | Sim (24/10/2026) | PR de integração | Sim: verificador e ensaio isolado em PostgreSQL descartável | Ver PR de integração | **Pendente**: nenhum backup ou restauração do Supabase real foi executado | Não se aplica (scripts e documentos operacionais) |
| `NEXO-AJ-00` | Sim (25/10/2026) | PR de integração (documentos) | Não se aplica (diagnóstico) | Não se aplica | Aprovação humana pendente | Não se aplica |
| `NEXO-AJ-06.1` | Sim (25/10/2026) | PR de integração | Sim: SQLite e PostgreSQL descartável | Ver PR de integração | **Pendente** | **Pendente**: depende de a `main` ser publicada e de o Supabase estar na revisão `e4c004a26b01` (incidente HTTP 500, `RELATORIO_CORRECAO_MIGRACAO_SUPABASE_NEXO.md`) |
| Demais 25 prompts `NEXO-AJ` | Não | Não | — | — | — | — |

## Fonte oficial

| Item | Valor |
|---|---|
| Mapa | `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md`, na pasta principal do projeto (junto de `app.py`) |
| Versão e data | 1.0, 25/10/2026, "complemento ao Documento Mestre" (mapa:3) |
| Tamanho e hash | 364 linhas, 19.774 bytes, SHA-256 `B59E9D7213273BC40D28F8BB61D5EC402F73B9B3A7B27A9D5790E630EFDEED67` |
| Origem | `%USERPROFILE%\Downloads\NEXO_MAPA_27_PROMPTS_PARA_CLAUDE_CODE.zip` (7.026 bytes, 25/10/2026 12:47, SHA-256 `D14E19BD68CCA5174C1BC0475D0C946A37FE566DC453EACF295D75D88F402748`, uma única entrada). A cópia na raiz é idêntica byte a byte à entrada do ZIP |
| Composição | **27 prompts: 4 de ETAPA completa e 23 de SUBETAPA** (mapa:7-11) |
| Relação com o Documento Mestre | A numeração NEXO-AJ é um plano complementar e não substitui as 8 etapas nem os códigos COM/SEC do Documento Mestre (mapa:17) |

## Índice dos 27 prompts

Legenda de status: `NÃO EXECUTADO`, `EM EXECUÇÃO`, `EXECUTADO / AGUARDANDO REVISÃO`, `APROVADO`, `REPROVADO`.

As dependências são as declaradas no mapa, na notação dele (`00` = `NEXO-AJ-00`). Quando o mapa não declara dependências, isso está escrito assim, sem inferência. "Ordem" é a posição do prompt na sequência recomendada pelo mapa (mapa:317-329). Datas, testes e arquivos alterados de cada prompt ficam no "Registro de execução por ID", como pede mapa:364.

| # | ID | Atividade | Tipo | Dependências (mapa) | Ordem | Status | Evidência de entrega | Aprovação |
|---|---|---|---|---|---|---|---|---|
| 1 | `NEXO-AJ-00` | Preparação e segurança da baseline (agrupa 0.1 e 0.2) | ETAPA | Não declaradas no mapa¹ (1ª na ordem recomendada) | 1 | **EXECUTADO / AGUARDANDO REVISÃO** | `NEXO_AJ_00_BASELINE.md`; `RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md`; este arquivo; ponto de reversão pré-AJ-00 em `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\` (registro abaixo) | Pendente (revisão humana) |
| 2 | `NEXO-AJ-01` | Identidade visual: somente o símbolo NEXO (agrupa 1.1 a 1.5) | ETAPA | Não declaradas no mapa¹ | 4 | NÃO EXECUTADO | — | — |
| 3 | `NEXO-AJ-02` | Preços dos planos (agrupa 2.1 a 2.3) | ETAPA | Não declaradas no mapa¹ | 4 | NÃO EXECUTADO | — | — |
| 4 | `NEXO-AJ-03.1` | Modelo de dados e migrações contratuais | SUBETAPA | `00`; `07.1` | 5 | NÃO EXECUTADO | — | — |
| 5 | `NEXO-AJ-03.2` | Cadastro e edição administrativa do contrato | SUBETAPA | `03.1` | 5 | NÃO EXECUTADO | — | — |
| 6 | `NEXO-AJ-03.3` | Renovação contratual e vigência | SUBETAPA | `03.1`; `03.2` | 5 | NÃO EXECUTADO | — | — |
| 7 | `NEXO-AJ-03.4` | Histórico contratual e consistência temporal | SUBETAPA | `03.3` | 5 | NÃO EXECUTADO | — | — |
| 8 | `NEXO-AJ-04.1` | Regra de antecedência de 7 a 14 dias | SUBETAPA | `03.3` | 6 | NÃO EXECUTADO | — | — |
| 9 | `NEXO-AJ-04.2` | Notificações e mensagens de renovação | SUBETAPA | `04.1` | 6 | NÃO EXECUTADO | — | — |
| 10 | `NEXO-AJ-04.3` | Verificação periódica e não duplicação | SUBETAPA | `04.2` | 6 | NÃO EXECUTADO | — | — |
| 11 | `NEXO-AJ-05.1` | Restrições funcionais de SUSPENSA | SUBETAPA | `03.1`; `06.1` | 7 | NÃO EXECUTADO | — | — |
| 12 | `NEXO-AJ-05.2` | Consulta ao histórico pago | SUBETAPA | `03.4`; `05.1` | 7 | NÃO EXECUTADO | — | — |
| 13 | `NEXO-AJ-05.3` | Exportação de PDF durante 14 dias | SUBETAPA | `05.1`; `05.2` | 7 | NÃO EXECUTADO | — | — |
| 14 | `NEXO-AJ-05.4` | Janela de até 3 meses e prorrogação | SUBETAPA | `03.2`; `05.1` | 7 | NÃO EXECUTADO | — | — |
| 15 | `NEXO-AJ-05.5` | Interface informativa de suspensão | SUBETAPA | `05.2`; `05.3`; `05.4` | 7 | NÃO EXECUTADO | — | — |
| 16 | `NEXO-AJ-06.1` | Correção prioritária do bloqueio CANCELADA | SUBETAPA | `00` | 2 | **EXECUTADO / AGUARDANDO REVISÃO** | `RELATORIO_NEXO_AJ_06_1_PARA_CHATGPT.md`; ponto de reversão pré-AJ-06.1 em `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-06.1_2026-10-25\` (registro abaixo) | Pendente (revisão humana) |
| 17 | `NEXO-AJ-06.2` | Transição controlada SUSPENSA para CANCELADA | SUBETAPA | `05.4`; `06.1` | 8 | NÃO EXECUTADO | — | — |
| 18 | `NEXO-AJ-06.3` | Tela/mensagem segura para conta cancelada | SUBETAPA | `06.1` | 8 | NÃO EXECUTADO | — | — |
| 19 | `NEXO-AJ-06.4` | Preservação de dados e acesso interno do ADMIN | SUBETAPA | `06.2`; `07.1` | 8 | NÃO EXECUTADO | — | — |
| 20 | `NEXO-AJ-07.1` | Inventário de dados, terceiros e lacunas LGPD | SUBETAPA | `00` | 3 | NÃO EXECUTADO | — | — |
| 21 | `NEXO-AJ-07.2` | Minutas de política, termos e cancelamento | SUBETAPA | `07.1` | 9 | NÃO EXECUTADO | — | — |
| 22 | `NEXO-AJ-07.3` | Retenção, exclusão e direitos de titulares | SUBETAPA | `07.1`; `06.4` | 9 | NÃO EXECUTADO | — | — |
| 23 | `NEXO-AJ-07.4` | Controles técnicos de privacidade e segurança | SUBETAPA | `07.1`; `07.3` | 9 | NÃO EXECUTADO | — | — |
| 24 | `NEXO-AJ-08` | Domínio e DNS (agrupa 8.1 a 8.4) | ETAPA | Não declaradas no mapa¹ | 10 | NÃO EXECUTADO | — | — |
| 25 | `NEXO-AJ-09.1` | Testes integrados e regressão | SUBETAPA | `01`–`08` (aplicáveis) | 11 | NÃO EXECUTADO | — | — |
| 26 | `NEXO-AJ-09.2` | Preparação de migrações e implantação com rollback | SUBETAPA | `09.1` | 11 | NÃO EXECUTADO | — | — |
| 27 | `NEXO-AJ-09.3` | Documentação final e conciliação com Documento Mestre | SUBETAPA | `09.1`; `09.2` | 11 | NÃO EXECUTADO | — | — |

Totais: 27 prompts, 4 ETAPA (`00`, `01`, `02`, `08`) e 23 SUBETAPA (03: 4, 04: 3, 05: 5, 06: 4, 07: 4, 09: 3). Status: 2 EXECUTADO / AGUARDANDO REVISÃO (`00` e `06.1`) e 25 NÃO EXECUTADO. Aprovados: 0.

¹ O mapa não declara dependências para os prompts de ETAPA `00`, `01`, `02` e `08` (as seções deles, mapa:37-71 e 273-283, não têm o campo "Dependências"). A posição de cada um vem só da ordem recomendada: `00` é o 1º; `01` e `02` vêm depois de `00`, `06.1` e `07.1`; `08` vem depois das etapas 03 a 07. Isso é sequência recomendada, não dependência formal.

**Redação dos prompts:** na data do mapa, os 27 estavam "PLANEJADOS / NÃO REDIGIDOS / NÃO EXECUTADOS" (mapa:364). O prompt da NEXO-AJ-00 foi recebido pelo Claude Code na conversa de 25/10/2026 e executado. Os outros 26 não foram redigidos nem recebidos por este controle até esta atualização.

## Ordem recomendada de execução (mapa:317-329)

| Ordem | Prompts |
|---|---|
| 1 | `NEXO-AJ-00` (inspeção e baseline) |
| 2 | `NEXO-AJ-06.1` (bloqueio CANCELADA: correção de segurança urgente) |
| 3 | `NEXO-AJ-07.1` (inventário LGPD para embasar dados e retenção) |
| 4 | `NEXO-AJ-01` e `NEXO-AJ-02` (identidade e preços, cada qual como prompt de ETAPA) |
| 5 | `NEXO-AJ-03.1` → `03.2` → `03.3` → `03.4` (contratos) |
| 6 | `NEXO-AJ-04.1` → `04.2` → `04.3` (avisos de renovação) |
| 7 | `NEXO-AJ-05.1` → `05.2` → `05.3` → `05.4` → `05.5` (suspensão) |
| 8 | `NEXO-AJ-06.2` → `06.3` → `06.4` (cancelamento; 06.1 já ocorreu) |
| 9 | `NEXO-AJ-07.2` → `07.3` → `07.4` (adequações LGPD remanescentes) |
| 10 | `NEXO-AJ-08` (prontidão de domínio/DNS; ações externas do provedor à parte) |
| 11 | `NEXO-AJ-09.1` → `09.2` → `09.3` (teste, operação planejada e documentação) |

Conferido por script: todas as dependências declaradas são atendidas por prompts que aparecem antes na ordem recomendada, e o grafo não tem ciclos.

**Próximo prompt:** pela ordem recomendada, `NEXO-AJ-07.1` (3º, mapa:321), que depende só de `00` (mapa:241). **Não foi iniciado.** Antes dele, cabe a revisão humana de `00` e de `06.1`. **[26/10/2026]** Com a mudança de metodologia registrada no início deste arquivo, a ordem acima deixou de ser obrigatória: não há próximo prompt definido, e a prioridade será dada pelo proprietário.

*Histórico desta seção:* até 25/10/2026 14:38 o próximo prompt era `NEXO-AJ-06.1`, executado por autorização expressa do responsável (prompt oficial NEXO-AJ-06.1), embora a aprovação da `00` não esteja registrada nesta tabela.

## Escopo e critério de aceite por prompt (transcrição literal do mapa)

O texto abaixo é **cópia literal** do mapa, sem paráfrase. As linhas indicam onde conferir. Um script verifica que cada trecho existe no mapa exatamente como está aqui. A única diferença tipográfica é a crase em volta de `/cliente/analise/<id>/pdf` (05.3), necessária para o `<id>` aparecer no Markdown; o script a desconsidera.

| ID | Escopo (mapa) | Critério de aceite (mapa) | Linhas |
|---|---|---|---|
| `00` | "Agrupar 0.1 e 0.2: extrair o ZIP, identificar a cópia/branch/commit, inventariar os arquivos e testes, registrar divergências com o Documento Mestre, proteger banco e uploads e estabelecer ponto de reversão." | "Um diagnóstico verificável da baseline e backups sem alterar o produto." | 43, 45 |
| `01` | "Agrupar 1.1 a 1.5: usar o arquivo nexo_cubo_centralizado.png, atualizar o cabeçalho/sidebar ADMIN e CLIENTE, login e demais ocorrências reais da marca, corrigindo redundância de texto; manter responsividade e legibilidade." | "Todas as telas aplicáveis usam o símbolo sem nome dentro da imagem, sem duplicações e sem alterar regras de negócio." | 55, 57 |
| `02` | "Agrupar 2.1 a 2.3: catálogo, seed, dados já existentes, landing page e receita estimada; Bronze R$ 150, Prata R$ 300, Ouro R$ 650. Conferir o efeito em contratos vigentes antes de atualizar preços históricos." | "Preços consistentes nas telas e no banco, sem sobrescrever indevidamente valores históricos acordados." | 67, 69 |
| `03.1` | "Definir vigência, histórico, datas de início/fim, acordos, prazo de suspensão, preço contratado quando necessário; criar migrações sem perda de dados." | "Migração testada em cópia SQLite/PostgreSQL; leitura de dados antigos preservada." | 83, 85 |
| `03.2` | "Tela e validações do ADMIN para registrar contrato, plano, datas, documentos/metadados disponíveis e condições acordadas, sem autocadastro ou pagamento automático." | "ADMIN administra contrato sem editar dados diretamente no banco; acesso CLIENTE bloqueado." | 91, 93 |
| `03.3` | "Registrar renovação acordada, novas datas, status adequado e idempotência para evitar renovações duplicadas." | "Renovação confirma novo período sem apagar contrato anterior." | 99, 101 |
| `03.4` | "Consultar versões/contratos anteriores e distinguir períodos pagos do plano de catálogo; regras para alterações retroativas e conflitos de datas." | "Histórico rastreável permite identificar exatamente o período pago." | 107, 109 |
| `04.1` | "Persistir/interpretar antecedência definida conforme o contrato; não atribuir arbitrariamente prazos a planos. Considerar renovação/prorrogação." | "Datas calculadas e testadas nas bordas 7 e 14 dias." | 123, 125 |
| `04.2` | "Exibir alerta de renovação no portal e integrar, quando configurado, e-mail transacional; preservar mensagens privadas e identificadores por usuário." | "Cliente recebe comunicado com data correta, sem vazamento a outra empresa." | 131, 133 |
| `04.3` | "Execução programada segura para localizar contratos a vencer, gerar alertas uma vez e reagir a renovações; observar infraestrutura disponível." | "Várias execuções não criam avisos repetidos nem deixam clientes elegíveis sem aviso." | 139, 141 |
| `05.1` | "Impedir novas análises, processamento, uploads que iniciem entregas e outras operações novas; manter autenticação para acesso permitido." | "Cliente suspenso só consegue ações explicitamente permitidas, inclusive por URL direta." | 155, 157 |
| `05.2` | "Exibir apenas análises publicadas vinculadas a períodos cobertos pela contratação efetivamente paga e à própria empresa." | "Consultas cruzadas/fora do período são negadas pelo backend." | 163, 165 |
| `05.3` | "Registrar marco temporal da suspensão; liberar `/cliente/analise/<id>/pdf` nos primeiros 14 dias corridos e negar após limite, preservando outras regras de publicação e empresa." | "Testes de fronteira antes/no/depois da janela e acesso direto à rota." | 171, 173 |
| `05.4` | "Registrar início de suspensão, data-limite de cancelamento e prorrogação expressamente acordada pelo ADMIN; usar meses de calendário conforme regra documentada, não presumir 90 dias." | "Prazo e prorrogação persistidos, com validação de autor e histórico." | 179, 181 |
| `05.5` | "Mostrar estado SUSPENSA, informações úteis de renovação, janela para PDFs e histórico, sem oferecer botões que falharão." | "Interface clara em desktop e celular, sem sugerir acesso ilimitado." | 187, 189 |
| `06.1` | "Corrigir sessão, login, rotas, endpoints PDF, APIs e notificações para negar acesso do CLIENTE de empresa CANCELADA; ADMIN interno mantém permissões. Não impedir acesso histórico legítimo de SUSPENSA." | "Teste negativo com sessão já aberta, login novo, IDOR e APIs; sem vazamentos." | 203, 205 |
| `06.2` | "Executar cancelamento quando expirar prazo acordado, até três meses salvo prorrogação; garantir idempotência, trilha básica e não exclusão física." | "Transição correta somente de empresas elegíveis, respeitando exceções." | 211, 213 |
| `06.3` | "Criar tela própria no visual NEXO, eventualmente desfoque decorativo, sem renderizar dados de painel ao fundo; mensagem de cancelamento e contato. Evitar enumeração de contas na tela pública." | "Conta cancelada recebe mensagem apropriada sem acesso aos dados." | 219, 221 |
| `06.4` | "Manter visibilidade interna do histórico sem confundir CANCELADA com deletado_em da lixeira; testar permissões, trilha e limites de retenção." | "Dados preservados sob política válida e cliente permanece bloqueado." | 227, 229 |
| `07.1` | "Mapear dados pessoais, finalidades, contratos, Render, Supabase, SMTP, APIs de IA, arquivos e logs efetivamente utilizados; classificar lacunas sem mudar código." | "Inventário e matriz de riscos iniciais documentados." | 243, 245 |
| `07.2` | "Preparar textos e links de privacidade, termos e cancelamento coerentes com o serviço; submeter à revisão jurídica antes de afirmar conformidade ou publicar versão final." | "Minutas rastreáveis com pendências jurídicas identificadas." | 251, 253 |
| `07.3` | "Especificar políticas de retenção e fluxos dos titulares por status da empresa; não apagar registros automaticamente por atingir 3 meses, pois cancelamento ≠ eliminação legal." | "Prazos e exceções definidos e implementações autorizadas testadas." | 259, 261 |
| `07.4` | "Corrigir lacunas comprovadas em acesso, logs, backups, arquivos e compartilhamento, mantendo testes anti-IDOR." | "Riscos residuais e evidências de teste documentados, sem alegar certificação jurídica." | 267, 269 |
| `08` | "Agrupar 8.1 a 8.4: auditar configuração Render/domínio, preparar URLs/HTTPS/cookies/e-mails/Socket.IO, gerar instruções exatas para registros DNS e conferir testes. O registro DNS externo depende de ação no provedor e não pode ser resolvido apenas editando o ZIP." | "Aplicação pronta para domínio próprio e checklist externo de DNS/SSL validável." | 279, 281 |
| `09.1` | "Testar plano/contrato, avisos, ATIVA/SUSPENSA/CANCELADA, 14 dias, 3 meses/prorrogação, PDF, uploads, autenticação, suporte e responsividade." | "Suíte executada e falhas descritas com evidência." | 295, 297 |
| `09.2` | "Revisar migrações de SQLite e PostgreSQL/Supabase, backups, alterações Render e passos de reversão. Não executar produção sem autorização." | "Runbook e checklist de deploy/rollback, sem alterações automáticas em produção." | 303, 305 |
| `09.3` | "Atualizar regras, fluxo/permissões, testes e índice do Documento Mestre, marcando o que de fato foi entregue." | "Documentos coerentes com a versão implementada, sem declarar tarefas não executadas como concluídas." | 311, 313 |

**Validação e parada entre prompts:**

- **Marco de validação de etapa:** o mapa fecha cada etapa com "revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa" (mapa:47, 59, 71, 111, 143, 191, 231, 271, 283 e 315). O marco aparece uma vez por etapa, não depois de cada subetapa.
- **Parada a cada prompt:** a obrigação de não avançar sozinho, também entre subetapas, vem de outras linhas do mapa: "execução incremental e validação antes de avançar" (mapa:15), "sem avançar automaticamente" (mapa:340) e "não iniciar o próximo prompt sozinho" (mapa:359).

## Pedidos do responsável e etapas do mapa

Os nove pedidos das imagens de 25/10/2026 (`Docs/REESTRUTURACAO_COMERCIAL/insumos/2026-10-25/`) se distribuem pelos prompts conforme o escopo de cada um no mapa:

| Pedido | Origem | Prompts |
|---|---|---|
| Conta cancelada: tela própria ou com desfoque e mensagem | Imagem 04, item 1 | `06.3` (tela); `06.1` (bloqueio de acesso) |
| Tudo por contrato | Imagem 04, item 2 | `03.1` a `03.4` |
| Suspensa: dados pagos e cancelamento em até 3 meses, prorrogável | Imagem 04, item 3 | `05.2`, `05.4`, `06.2` |
| Suspensa: PDFs por 2 semanas | Imagem 04, item 4 | `05.3` |
| Planos R$ 150, R$ 300 e R$ 650 | Imagem 04, item 5 | `02` |
| Logo só com o cubo | Imagem 04, item 6 | `01` |
| Aviso de renovação 1 a 2 semanas antes | Imagem 05, item 1 | `04.1` a `04.3` |
| Revisão LGPD | Imagem 05, item 2 | `07.1` a `07.4` |
| DNS: nome em vez de IP | Imagem 05, item 3 | `08` |

A etapa 09 (validação, implantação segura e documentação) não corresponde a um pedido das imagens.

**"Ajustes 01 a 09":** o prompt NEXO-AJ-00 cita "futuros ajustes 01 a 09", mas o mapa não usa a palavra "ajuste". **Interpretação** deste controle, a confirmar na revisão humana: eles correspondem às etapas 01 a 09 da matriz do mapa (IDs `NEXO-AJ-01` a `NEXO-AJ-09.x`, mapa:22-33), pelo prefixo comum `NEXO-AJ`. A primeira versão deste arquivo tinha suposto outra correspondência, com os nove pedidos das imagens, e já a marcava como não comprovada.

## Regras do mapa para todos os prompts (transcrição literal, mapa:331-340)

- "FONTE/BASELINE: comparar a pasta extraída do ZIP com a branch/commit que será realmente implantado. O Documento Mestre menciona outra baseline e PRs em andamento; evitar sobrepor alterações COM-001/SEC e identificar conflitos."
- "SEGURANÇA: corrigir primeiro o acesso de empresa CANCELADA identificado no ZIP. Bloquear também sessões anteriores, APIs, PDFs e Socket.IO; manter histórico de SUSPENSA dentro das regras."
- "CONTRATO: contratação e renovação são acordos NEXO–empresa. Preço exibido no catálogo não deve apagar preço/vigência histórica de um acordo já firmado."
- "PRAZOS: alertas 7–14 dias ANTES do vencimento segundo regra contratual; PDF durante 14 dias corridos APÓS suspensão; cancelamento em até 3 meses, prorrogável por acordo registrado. Estes prazos são independentes."
- "LGPD: cancelamento de conta não equivale a apagar todos os dados. Política de retenção, contratos e revisão jurídica devem preceder exclusões automáticas."
- "VISUAL: trocar a imagem antiga com NEXO/Faturamento Inteligente pelo símbolo fornecido sem nome dentro da imagem, evitando texto duplicado; manter identidade e acessibilidade."
- "DNS: Claude Code pode preparar/validar configuração no projeto e um checklist. Alterações de registros DNS, controle do domínio e certificações no provedor são operações externas ao ZIP."
- "LIMITES DE PROMPT: objetivo claro, arquivos-alvo detectados, invariantes, testes unitários/de integração, relatório final de diff, sem avançar automaticamente, sem deploy ou migração em produção sem autorização."

## Checklist obrigatório de saída do Claude Code (transcrição literal, mapa:352-360)

Vale para cada prompt executado:

- [ ] "Confirmar a pasta/repositório alvo e não alterar a versão errada."
- [ ] "Enumerar arquivos inspecionados e arquivos modificados."
- [ ] "Mostrar decisões tomadas e eventuais lacunas que dependem da NEXO."
- [ ] "Executar testes pertinentes e registrar resultados/restrições."
- [ ] "Identificar migrações e riscos de dados, sem executar em produção automaticamente."
- [ ] "Não ampliar escopo, não iniciar o próximo prompt sozinho."
- [ ] "Somente após aprovação, registrar checkpoint de versão."

## Regra permanente para os próximos prompts

Cada `NEXO-AJ-*` deve:

1. produzir `Docs/AJUSTES_NEXO_2026/RELATORIO_<ID>_PARA_CHATGPT.md`;
2. atualizar a sua linha nesta tabela;
3. listar todos os arquivos modificados;
4. informar os testes executados e as evidências;
5. descrever riscos e limitações;
6. informar o ponto de reversão;
7. orientar a entrega para revisão humana.

## Registro de execução por ID (mapa:364)

### `NEXO-AJ-00`

| Item | Registro |
|---|---|
| Datas | Primeira entrega: 25/10/2026, 10:51 às 11:25. Correção: 11:47 às 13:21. Na fase sem o mapa (11:47 às 12:09) nenhum arquivo foi alterado; às 11:53 foi tirado o manifesto de referência. O complemento com o mapa foi das 12:55 às 13:21, com a primeira alteração às 12:56 |
| Arquivos alterados no projeto | Primeira entrega: criados os 3 documentos de `Docs/AJUSTES_NEXO_2026/`. Complemento: acrescentado `NEXO_MAPA_DE_PROMPTS_ETAPAS_E_SUBETAPAS_v1.md` na raiz; reescrito este controle; editados `RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` e `NEXO_AJ_00_BASELINE.md`. **Nenhum arquivo de código, teste, template, CSS, JS, migração, banco ou configuração de implantação** |
| Testes e evidências | Suíte `unittest` em cópia isolada, executada 2 vezes: 569 testes, 13 falhas, 12 erros, 42 ignorados, todos de ambiente e iguais à linha de base pós-0.2A. Sintaxe e configuração: 0 falhas, com YAML bloqueado. Integridade por SHA-256. Conferência do controle contra o mapa. Detalhes no relatório, seções 0.5 e 9 |
| Ponto de reversão | Ponto de reversão **pré-AJ-00** (cópia local da pasta antes da etapa): `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\NEXO_checkpoint_pre-AJ-00_2026-10-25.zip`. O **checkpoint de versão** que o mapa pede depois da aprovação (mapa:360) **ainda não foi registrado**: fica pendente até a aprovação humana |
| Relatório | `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_00_PARA_CHATGPT.md` |
| Aprovação | Pendente (revisão humana) |

### `NEXO-AJ-06.1`

| Item | Registro |
|---|---|
| Datas | 25/10/2026, das 13:49 às 14:38 (UTC−3) |
| Arquivos alterados no projeto | Código: `session_security.py`, `company_security.py`, `blueprints/auth.py`, `blueprints/admin.py`, `notifications.py` e `templates/admin/empresa_form.html` (só um campo oculto). Textos do NexoBot: `nexobot/saber/empresas_planos.py`, `nexobot/saber/administracao.py`, `nexobot/saber/uploads.py`. Testes: `tests/test_company_restore_security.py` (expectativa corrigida); novos `tests/test_cancelled_company_security.py` (30 testes) e `tests/test_cancelled_company_postgresql.py` (opt-in). Documentos: este controle e `RELATORIO_NEXO_AJ_06_1_PARA_CHATGPT.md`. Nenhum arquivo removido; nenhuma migração, banco, CSS, JS, landing ou configuração de implantação alterados |
| Testes e evidências | Suíte completa em cópia isolada: 600 testes, as mesmas 13 falhas e 12 erros da linha de base (todos de ambiente, investigados um a um) e 43 ignorados. Suítes de segurança e do NexoBot: 313 OK. Teste PostgreSQL 18.1 opt-in: OK. Mutação: 15 de 15 mutantes detectados. Revisão adversarial com 3 lentes: apontamentos do escopo corrigidos. Complemento em Linux (WSL, dependências fixadas, autorizado pelo responsável): 638 testes, 0 falhas, 0 erros, 39 ignorados (navegador, `pdftotext` e PostgreSQL não instalados). Detalhes no relatório 06.1 |
| Ponto de reversão | Ponto de reversão **pré-AJ-06.1**: `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-06.1_2026-10-25\NEXO_checkpoint_pre-AJ-06.1_2026-10-25.zip` (269 arquivos, SHA-256 `6A568DF4…F84FC7F`). O checkpoint de versão pós-aprovação (mapa:360) segue pendente |
| Relatório | `Docs/AJUSTES_NEXO_2026/RELATORIO_NEXO_AJ_06_1_PARA_CHATGPT.md` |
| Aprovação | Pendente (revisão humana) |

Os outros 25 prompts ainda não têm registro de execução.

## Histórico deste controle

| Data e hora | Versão | Alteração |
|---|---|---|
| 25/10/2026 11:03 | 1 | Criado na primeira entrega da NEXO-AJ-00, sem o mapa. O índice tinha `NEXO-AJ-00` na linha 1 e **26 linhas numeradas reservadas** (#2 a #27, "a preencher pelo mapa"); a `NEXO-AJ-06.1` ficava numa tabela à parte. O texto da própria versão 1 falava em "25 linhas", o que não batia com a tabela. A NEXO-AJ-00 ficou como "PARCIAL — AGUARDANDO REVISÃO" |
| 25/10/2026 13:21 | 2 | Complemento da NEXO-AJ-00. Mapa oficial recebido; os 27 IDs foram cadastrados com atividade, tipo, dependências, ordem e status. Escopo, aceite, regras e checklist foram transcritos literalmente do mapa. Foi incluído o registro de execução por ID. A NEXO-AJ-00 passou a "EXECUTADO / AGUARDANDO REVISÃO" e os outros 26 seguem "NÃO EXECUTADO". A correspondência dos "ajustes 01 a 09" foi refeita, como interpretação a confirmar |
| 25/10/2026 14:38 | 3 | NEXO-AJ-06.1 executada: linha 16 passou a "EXECUTADO / AGUARDANDO REVISÃO", com o registro de execução acrescentado; próximo prompt pela ordem recomendada passou a ser `NEXO-AJ-07.1`. A estrutura dos 27 prompts não mudou |
| 26/10/2026 | 4 | Integração ao GitHub: registrada a mudança de metodologia (sequência dos 27 prompts deixa de ser obrigatória) e a situação por ambiente. Caminhos locais com o nome do usuário do Windows foram anonimizados como `%USERPROFILE%`, e nomes de projetos sem relação, generalizados. Os status e as aprovações da tabela de índice não mudaram: a aprovação continua dependendo de revisão humana |

**Buscas pelo mapa feitas na versão 1** (preservadas da primeira entrega):

| Busca | Resultado |
|---|---|
| Nome `*MAPA*`, `*MAPA_DE_PROMPTS*` e `*ETAPAS_E_SUBETAPAS*` em todo o perfil do usuário (Downloads, Documentos, Desktop, OneDrive, AppData) e em `C:\ADS` | Só arquivos sem relação (de outros projetos) |
| Nome `*MAPA_DE_PROMPTS*` e `*NEXO_MAPA*` em `C:\` e `D:\` inteiros | Nenhum arquivo |
| Texto `NEXO-AJ-0`, `MAPA_DE_PROMPTS` e `MAPA DE PROMPTS` em `.md` e `.txt` de Downloads, Documentos, Desktop, OneDrive e `C:\ADS` | Nenhuma ocorrência |
| `NEXO_DOCUMENTO_MESTRE_ETAPAS_SUBETAPAS_E_STATUS.docx` (Downloads) | Usa outra numeração (Etapas 1 a 8 e subetapas `n.m`); não cita nenhum ID `NEXO-AJ` |

Depois disso, entre 11:47 e 12:09, a busca foi repetida três vezes (nome exato e variações em `C:\` e `D:\`, anexos da sessão e arquivos recentes), também sem resultado. O mapa só chegou às 12:55, no ZIP indicado pelo responsável.

**Cópia integral da versão 1** deste arquivo e das versões da primeira entrega do relatório e do baseline: `C:\ADS\Nexo - Faturamento Inteligente\Backups_NEXO\NEXO-AJ-00_2026-10-25\evidencias\complemento_mapa\documentos_antes_do_complemento\`.
