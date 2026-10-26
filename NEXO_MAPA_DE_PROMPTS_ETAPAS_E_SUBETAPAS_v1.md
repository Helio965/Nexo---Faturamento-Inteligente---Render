# NEXO | Mapa de prompts por etapa e subetapa

**Versão:** 1.0 | **Data:** 25/10/2026 | **Status:** PLANEJAMENTO, sem execução | **Tipo:** complemento ao Documento Mestre

## Decisão principal

**27 prompts futuros: 4 por ETAPA completa e 23 por SUBETAPA.**

**Prompts por etapa:** `NEXO-AJ-00`, `NEXO-AJ-01`, `NEXO-AJ-02`, `NEXO-AJ-08`.

**Prompts por subetapa:** `NEXO-AJ-03.1` a `03.4`; `04.1` a `04.3`; `05.1` a `05.5`; `06.1` a `06.4`; `07.1` a `07.4`; `09.1` a `09.3`.

## Premissas e escopo

- Objetivo: classificar de forma definitiva quais futuras instruções para Claude Code devem cobrir uma ETAPA inteira e quais devem ser divididas por SUBETAPA, com execução incremental e validação antes de avançar.
- Base analisada: imagens e anotações fornecidas em 25/10/2026, Nexo-Faturamento-Inteligente-main.zip e NEXO_DOCUMENTO_MESTRE_ETAPAS_SUBETAPAS_E_STATUS.docx (referência documental de 24/10/2026).
- A numeração NEXO-AJ é um plano complementar e não substitui as 8 etapas nem os códigos COM/SEC já existentes no Documento Mestre.
- Nenhum prompt executável foi redigido e nenhum arquivo do código-fonte do NEXO foi modificado neste planejamento.

## Matriz geral (uma etapa não significa um prompt automaticamente)

| Etapa | Assunto | Tipo de prompt | Quantidade | Identificação |
|---|---|---|---:|---|
| 00 | Preparação e segurança da baseline | ETAPA | 1 | `NEXO-AJ-00` |
| 01 | Identidade visual: somente o símbolo NEXO | ETAPA | 1 | `NEXO-AJ-01` |
| 02 | Preços dos planos | ETAPA | 1 | `NEXO-AJ-02` |
| 03 | Gestão de contratos | SUBETAPA | 4 | `NEXO-AJ-03.x` |
| 04 | Avisos de renovação | SUBETAPA | 3 | `NEXO-AJ-04.x` |
| 05 | Contas suspensas | SUBETAPA | 5 | `NEXO-AJ-05.x` |
| 06 | Contas canceladas | SUBETAPA | 4 | `NEXO-AJ-06.x` |
| 07 | LGPD e proteção de dados | SUBETAPA | 4 | `NEXO-AJ-07.x` |
| 08 | Domínio e DNS | ETAPA | 1 | `NEXO-AJ-08` |
| 09 | Validação, implantação segura e documentação | SUBETAPA | 3 | `NEXO-AJ-09.x` |

## Detalhamento de cada etapa e subetapa

### Etapa 00: Preparação e segurança da baseline

**Decisão:** um prompt por **ETAPA completa**. **Total:** 1.

**ID do prompt futuro:** `NEXO-AJ-00`.

**Escopo:** Agrupar 0.1 e 0.2: extrair o ZIP, identificar a cópia/branch/commit, inventariar os arquivos e testes, registrar divergências com o Documento Mestre, proteger banco e uploads e estabelecer ponto de reversão.

**Critério de aceite:** Um diagnóstico verificável da baseline e backups sem alterar o produto.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 01: Identidade visual: somente o símbolo NEXO

**Decisão:** um prompt por **ETAPA completa**. **Total:** 1.

**ID do prompt futuro:** `NEXO-AJ-01`.

**Escopo:** Agrupar 1.1 a 1.5: usar o arquivo nexo_cubo_centralizado.png, atualizar o cabeçalho/sidebar ADMIN e CLIENTE, login e demais ocorrências reais da marca, corrigindo redundância de texto; manter responsividade e legibilidade.

**Critério de aceite:** Todas as telas aplicáveis usam o símbolo sem nome dentro da imagem, sem duplicações e sem alterar regras de negócio.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 02: Preços dos planos

**Decisão:** um prompt por **ETAPA completa**. **Total:** 1.

**ID do prompt futuro:** `NEXO-AJ-02`.

**Escopo:** Agrupar 2.1 a 2.3: catálogo, seed, dados já existentes, landing page e receita estimada; Bronze R$ 150, Prata R$ 300, Ouro R$ 650. Conferir o efeito em contratos vigentes antes de atualizar preços históricos.

**Critério de aceite:** Preços consistentes nas telas e no banco, sem sobrescrever indevidamente valores históricos acordados.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 03: Gestão de contratos

**Decisão:** um prompt por **SUBETAPA**. **Total:** 4.

**Por que dividir:** Modelo, interface, renovação e histórico envolvem persistência e operações distintas; prompts separados reduzem risco de migração e perda de vigência.

#### 03.1 | Modelo de dados e migrações contratuais

**Prompt futuro:** `NEXO-AJ-03.1`. **Dependências:** 00; 07.1.

**Escopo:** Definir vigência, histórico, datas de início/fim, acordos, prazo de suspensão, preço contratado quando necessário; criar migrações sem perda de dados.

**Aceite:** Migração testada em cópia SQLite/PostgreSQL; leitura de dados antigos preservada.

#### 03.2 | Cadastro e edição administrativa do contrato

**Prompt futuro:** `NEXO-AJ-03.2`. **Dependências:** 03.1.

**Escopo:** Tela e validações do ADMIN para registrar contrato, plano, datas, documentos/metadados disponíveis e condições acordadas, sem autocadastro ou pagamento automático.

**Aceite:** ADMIN administra contrato sem editar dados diretamente no banco; acesso CLIENTE bloqueado.

#### 03.3 | Renovação contratual e vigência

**Prompt futuro:** `NEXO-AJ-03.3`. **Dependências:** 03.1; 03.2.

**Escopo:** Registrar renovação acordada, novas datas, status adequado e idempotência para evitar renovações duplicadas.

**Aceite:** Renovação confirma novo período sem apagar contrato anterior.

#### 03.4 | Histórico contratual e consistência temporal

**Prompt futuro:** `NEXO-AJ-03.4`. **Dependências:** 03.3.

**Escopo:** Consultar versões/contratos anteriores e distinguir períodos pagos do plano de catálogo; regras para alterações retroativas e conflitos de datas.

**Aceite:** Histórico rastreável permite identificar exatamente o período pago.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 04: Avisos de renovação

**Decisão:** um prompt por **SUBETAPA**. **Total:** 3.

**Por que dividir:** Antecedência contratual, comunicação e execução programada são componentes separáveis e devem ter testes próprios.

#### 04.1 | Regra de antecedência de 7 a 14 dias

**Prompt futuro:** `NEXO-AJ-04.1`. **Dependências:** 03.3.

**Escopo:** Persistir/interpretar antecedência definida conforme o contrato; não atribuir arbitrariamente prazos a planos. Considerar renovação/prorrogação.

**Aceite:** Datas calculadas e testadas nas bordas 7 e 14 dias.

#### 04.2 | Notificações e mensagens de renovação

**Prompt futuro:** `NEXO-AJ-04.2`. **Dependências:** 04.1.

**Escopo:** Exibir alerta de renovação no portal e integrar, quando configurado, e-mail transacional; preservar mensagens privadas e identificadores por usuário.

**Aceite:** Cliente recebe comunicado com data correta, sem vazamento a outra empresa.

#### 04.3 | Verificação periódica e não duplicação

**Prompt futuro:** `NEXO-AJ-04.3`. **Dependências:** 04.2.

**Escopo:** Execução programada segura para localizar contratos a vencer, gerar alertas uma vez e reagir a renovações; observar infraestrutura disponível.

**Aceite:** Várias execuções não criam avisos repetidos nem deixam clientes elegíveis sem aviso.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 05: Contas suspensas

**Decisão:** um prompt por **SUBETAPA**. **Total:** 5.

**Por que dividir:** Permissões de leitura, PDFs, janela contratual e interface exigem autorização no servidor e validação em cada fronteira.

#### 05.1 | Restrições funcionais de SUSPENSA

**Prompt futuro:** `NEXO-AJ-05.1`. **Dependências:** 03.1; 06.1.

**Escopo:** Impedir novas análises, processamento, uploads que iniciem entregas e outras operações novas; manter autenticação para acesso permitido.

**Aceite:** Cliente suspenso só consegue ações explicitamente permitidas, inclusive por URL direta.

#### 05.2 | Consulta ao histórico pago

**Prompt futuro:** `NEXO-AJ-05.2`. **Dependências:** 03.4; 05.1.

**Escopo:** Exibir apenas análises publicadas vinculadas a períodos cobertos pela contratação efetivamente paga e à própria empresa.

**Aceite:** Consultas cruzadas/fora do período são negadas pelo backend.

#### 05.3 | Exportação de PDF durante 14 dias

**Prompt futuro:** `NEXO-AJ-05.3`. **Dependências:** 05.1; 05.2.

**Escopo:** Registrar marco temporal da suspensão; liberar /cliente/analise/<id>/pdf nos primeiros 14 dias corridos e negar após limite, preservando outras regras de publicação e empresa.

**Aceite:** Testes de fronteira antes/no/depois da janela e acesso direto à rota.

#### 05.4 | Janela de até 3 meses e prorrogação

**Prompt futuro:** `NEXO-AJ-05.4`. **Dependências:** 03.2; 05.1.

**Escopo:** Registrar início de suspensão, data-limite de cancelamento e prorrogação expressamente acordada pelo ADMIN; usar meses de calendário conforme regra documentada, não presumir 90 dias.

**Aceite:** Prazo e prorrogação persistidos, com validação de autor e histórico.

#### 05.5 | Interface informativa de suspensão

**Prompt futuro:** `NEXO-AJ-05.5`. **Dependências:** 05.2; 05.3; 05.4.

**Escopo:** Mostrar estado SUSPENSA, informações úteis de renovação, janela para PDFs e histórico, sem oferecer botões que falharão.

**Aceite:** Interface clara em desktop e celular, sem sugerir acesso ilimitado.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 06: Contas canceladas

**Decisão:** um prompt por **SUBETAPA**. **Total:** 4.

**Por que dividir:** Bloqueio de acesso é prioridade de segurança; transição, tela pública e preservação do histórico interno vêm em mudanças controladas.

#### 06.1 | Correção prioritária do bloqueio CANCELADA

**Prompt futuro:** `NEXO-AJ-06.1`. **Dependências:** 00.

**Escopo:** Corrigir sessão, login, rotas, endpoints PDF, APIs e notificações para negar acesso do CLIENTE de empresa CANCELADA; ADMIN interno mantém permissões. Não impedir acesso histórico legítimo de SUSPENSA.

**Aceite:** Teste negativo com sessão já aberta, login novo, IDOR e APIs; sem vazamentos.

#### 06.2 | Transição controlada SUSPENSA para CANCELADA

**Prompt futuro:** `NEXO-AJ-06.2`. **Dependências:** 05.4; 06.1.

**Escopo:** Executar cancelamento quando expirar prazo acordado, até três meses salvo prorrogação; garantir idempotência, trilha básica e não exclusão física.

**Aceite:** Transição correta somente de empresas elegíveis, respeitando exceções.

#### 06.3 | Tela/mensagem segura para conta cancelada

**Prompt futuro:** `NEXO-AJ-06.3`. **Dependências:** 06.1.

**Escopo:** Criar tela própria no visual NEXO, eventualmente desfoque decorativo, sem renderizar dados de painel ao fundo; mensagem de cancelamento e contato. Evitar enumeração de contas na tela pública.

**Aceite:** Conta cancelada recebe mensagem apropriada sem acesso aos dados.

#### 06.4 | Preservação de dados e acesso interno do ADMIN

**Prompt futuro:** `NEXO-AJ-06.4`. **Dependências:** 06.2; 07.1.

**Escopo:** Manter visibilidade interna do histórico sem confundir CANCELADA com deletado_em da lixeira; testar permissões, trilha e limites de retenção.

**Aceite:** Dados preservados sob política válida e cliente permanece bloqueado.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 07: LGPD e proteção de dados

**Decisão:** um prompt por **SUBETAPA**. **Total:** 4.

**Por que dividir:** Inventário, documentos, retenção e correções técnicas são entregas de natureza diferente; não anunciar conformidade automática.

#### 07.1 | Inventário de dados, terceiros e lacunas LGPD

**Prompt futuro:** `NEXO-AJ-07.1`. **Dependências:** 00.

**Escopo:** Mapear dados pessoais, finalidades, contratos, Render, Supabase, SMTP, APIs de IA, arquivos e logs efetivamente utilizados; classificar lacunas sem mudar código.

**Aceite:** Inventário e matriz de riscos iniciais documentados.

#### 07.2 | Minutas de política, termos e cancelamento

**Prompt futuro:** `NEXO-AJ-07.2`. **Dependências:** 07.1.

**Escopo:** Preparar textos e links de privacidade, termos e cancelamento coerentes com o serviço; submeter à revisão jurídica antes de afirmar conformidade ou publicar versão final.

**Aceite:** Minutas rastreáveis com pendências jurídicas identificadas.

#### 07.3 | Retenção, exclusão e direitos de titulares

**Prompt futuro:** `NEXO-AJ-07.3`. **Dependências:** 07.1; 06.4.

**Escopo:** Especificar políticas de retenção e fluxos dos titulares por status da empresa; não apagar registros automaticamente por atingir 3 meses, pois cancelamento ≠ eliminação legal.

**Aceite:** Prazos e exceções definidos e implementações autorizadas testadas.

#### 07.4 | Controles técnicos de privacidade e segurança

**Prompt futuro:** `NEXO-AJ-07.4`. **Dependências:** 07.1; 07.3.

**Escopo:** Corrigir lacunas comprovadas em acesso, logs, backups, arquivos e compartilhamento, mantendo testes anti-IDOR.

**Aceite:** Riscos residuais e evidências de teste documentados, sem alegar certificação jurídica.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 08: Domínio e DNS

**Decisão:** um prompt por **ETAPA completa**. **Total:** 1.

**ID do prompt futuro:** `NEXO-AJ-08`.

**Escopo:** Agrupar 8.1 a 8.4: auditar configuração Render/domínio, preparar URLs/HTTPS/cookies/e-mails/Socket.IO, gerar instruções exatas para registros DNS e conferir testes. O registro DNS externo depende de ação no provedor e não pode ser resolvido apenas editando o ZIP.

**Critério de aceite:** Aplicação pronta para domínio próprio e checklist externo de DNS/SSL validável.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

### Etapa 09: Validação, implantação segura e documentação

**Decisão:** um prompt por **SUBETAPA**. **Total:** 3.

**Por que dividir:** Testes integrados, plano de implantação/rollback e documentação precisam de responsáveis e evidências diferentes.

#### 09.1 | Testes integrados e regressão

**Prompt futuro:** `NEXO-AJ-09.1`. **Dependências:** 01–08 (aplicáveis).

**Escopo:** Testar plano/contrato, avisos, ATIVA/SUSPENSA/CANCELADA, 14 dias, 3 meses/prorrogação, PDF, uploads, autenticação, suporte e responsividade.

**Aceite:** Suíte executada e falhas descritas com evidência.

#### 09.2 | Preparação de migrações e implantação com rollback

**Prompt futuro:** `NEXO-AJ-09.2`. **Dependências:** 09.1.

**Escopo:** Revisar migrações de SQLite e PostgreSQL/Supabase, backups, alterações Render e passos de reversão. Não executar produção sem autorização.

**Aceite:** Runbook e checklist de deploy/rollback, sem alterações automáticas em produção.

#### 09.3 | Documentação final e conciliação com Documento Mestre

**Prompt futuro:** `NEXO-AJ-09.3`. **Dependências:** 09.1; 09.2.

**Escopo:** Atualizar regras, fluxo/permissões, testes e índice do Documento Mestre, marcando o que de fato foi entregue.

**Aceite:** Documentos coerentes com a versão implementada, sem declarar tarefas não executadas como concluídas.

**Marco de validação:** revisão dos arquivos alterados, testes relevantes e aprovação antes da próxima etapa.

## Ordem recomendada de execução (independente da numeração)

- 1. NEXO-AJ-00 (inspeção e baseline).
- 2. NEXO-AJ-06.1 (bloqueio CANCELADA: correção de segurança urgente).
- 3. NEXO-AJ-07.1 (inventário LGPD para embasar dados e retenção).
- 4. NEXO-AJ-01 e NEXO-AJ-02 (identidade e preços, cada qual como prompt de ETAPA).
- 5. NEXO-AJ-03.1 → 03.2 → 03.3 → 03.4 (contratos).
- 6. NEXO-AJ-04.1 → 04.2 → 04.3 (avisos de renovação).
- 7. NEXO-AJ-05.1 → 05.2 → 05.3 → 05.4 → 05.5 (suspensão).
- 8. NEXO-AJ-06.2 → 06.3 → 06.4 (cancelamento; 06.1 já ocorreu).
- 9. NEXO-AJ-07.2 → 07.3 → 07.4 (adequações LGPD remanescentes).
- 10. NEXO-AJ-08 (prontidão de domínio/DNS; ações externas do provedor à parte).
- 11. NEXO-AJ-09.1 → 09.2 → 09.3 (teste, operação planejada e documentação).

## Regras obrigatórias para todos os prompts

- FONTE/BASELINE: comparar a pasta extraída do ZIP com a branch/commit que será realmente implantado. O Documento Mestre menciona outra baseline e PRs em andamento; evitar sobrepor alterações COM-001/SEC e identificar conflitos.
- SEGURANÇA: corrigir primeiro o acesso de empresa CANCELADA identificado no ZIP. Bloquear também sessões anteriores, APIs, PDFs e Socket.IO; manter histórico de SUSPENSA dentro das regras.
- CONTRATO: contratação e renovação são acordos NEXO–empresa. Preço exibido no catálogo não deve apagar preço/vigência histórica de um acordo já firmado.
- PRAZOS: alertas 7–14 dias ANTES do vencimento segundo regra contratual; PDF durante 14 dias corridos APÓS suspensão; cancelamento em até 3 meses, prorrogável por acordo registrado. Estes prazos são independentes.
- LGPD: cancelamento de conta não equivale a apagar todos os dados. Política de retenção, contratos e revisão jurídica devem preceder exclusões automáticas.
- VISUAL: trocar a imagem antiga com NEXO/Faturamento Inteligente pelo símbolo fornecido sem nome dentro da imagem, evitando texto duplicado; manter identidade e acessibilidade.
- DNS: Claude Code pode preparar/validar configuração no projeto e um checklist. Alterações de registros DNS, controle do domínio e certificações no provedor são operações externas ao ZIP.
- LIMITES DE PROMPT: objetivo claro, arquivos-alvo detectados, invariantes, testes unitários/de integração, relatório final de diff, sem avançar automaticamente, sem deploy ou migração em produção sem autorização.

## Achados técnicos do ZIP que influenciaram a classificação

- O ZIP examinado contém 14 modelos SQLAlchemy ativos; a baseline documental mais antiga descreve 12. Preservar os dois modelos adicionais: GuiaTopico e ArquivoArmazenado.
- Arquivo antigo de logo: static/img/nexo-logo.jpeg; referências observadas em templates/base.html e templates/auth/login.html.
- O seed.py armazena BRONZE=600, PRATA=1000 e OURO=1400; templates/landing.html apresenta “Sob consulta”. Os valores novos são 150/300/650 reais, interpretados como valor mensal conforme plano.valor_mensal atual.
- Empresa possui data_contratacao e status_conta, mas não esquema contratual completo com vigência e acordos de prorrogação.
- session_security.py, função usuario_pode_acessar(), filtra empresa por id e deletado_em, sem verificar status_conta CANCELADA nesta cópia.
- blueprints/cliente.py, rota /analise/<id_analise>/pdf, valida propriedade/publicação, mas não janela de 14 dias da suspensão.
- Existem funções de lixeira em company_security.py; não misturar exclusão lógica com cancelamento contratual.

## Checklist obrigatório de saída do Claude Code

- [ ] Confirmar a pasta/repositório alvo e não alterar a versão errada.
- [ ] Enumerar arquivos inspecionados e arquivos modificados.
- [ ] Mostrar decisões tomadas e eventuais lacunas que dependem da NEXO.
- [ ] Executar testes pertinentes e registrar resultados/restrições.
- [ ] Identificar migrações e riscos de dados, sem executar em produção automaticamente.
- [ ] Não ampliar escopo, não iniciar o próximo prompt sozinho.
- [ ] Somente após aprovação, registrar checkpoint de versão.

## Controle de status

Todos os 27 prompts estão **PLANEJADOS / NÃO REDIGIDOS / NÃO EXECUTADOS**. Acompanhamento deve ser atualizado por ID, com datas, evidências de teste e arquivos alterados.
