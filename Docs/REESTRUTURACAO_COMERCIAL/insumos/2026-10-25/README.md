# Insumos do proprietário — 2026-10-25

Material enviado pelo proprietário do NEXO em 25/10/2026, guardado aqui para orientar as próximas etapas da reestruturação comercial. **Nada foi implementado ainda: o proprietário vai dar as instruções.**

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `01_logo_cubo_sem_texto.png` (640×641) | Cubo NEXO (linhas roxas em degradê) dentro de um anel branco, fundo roxo escuro, **sem texto** |
| `02_logo_cubo_com_texto.jpg` (640×641) | A mesma arte com "NEXO - FATURAMENTO / INTELIGENTE". É a arte que está hoje em `static/img/nexo-logo.jpeg` |
| `03_telas_atuais_marca_portal_admin_login_redigida.png` | Capturas das telas atuais: marca "N" (quadrado roxo), Visão Geral do cliente, Dashboard do admin e tela "Acesso ao Portal". **Versão redigida** (ver nota abaixo) |
| `04_regras_contrato_status_planos_logo.png` | Regras 1 a 6: contas canceladas e suspensas, contrato, exportação de PDFs, preços dos planos, logo |
| `05_regras_aviso_renovacao_lgpd_dns.png` | Regras 1 a 3: aviso de renovação, LGPD, DNS |

## Requisitos transcritos

### Imagem 04

1. **Empresas canceladas** terão uma tela diferente, ou a mesma tela com desfoque e uma mensagem.
2. **Tudo é feito por contrato** entre a NEXO e a empresa interessada.
3. **Contas suspensas** poderão ver os dados já pagos no período definido em contrato. Se a empresa não renovar, terá **até 3 meses** até a conta ser cancelada. Esse prazo pode ser **prolongado por acordo** entre a NEXO e a empresa.
4. **Contas suspensas** terão **até 2 semanas** para exportar os PDFs (relatórios) feitos durante a vigência do contrato.
5. **Planos:** Bronze R$ 150 · Prata R$ 300 · Ouro R$ 650.
6. **Logo:** tirar a logo da imagem e colocar somente o quadrado (cubo) da NEXO.

### Imagem 05

1. **Aviso de renovação:** de 1 a 2 semanas antes do vencimento do contrato (a antecedência varia conforme o tempo contratado), a empresa recebe um aviso de renovação. Ela pode não renovar, o que leva à suspensão, ou reavaliar o contrato para manter o serviço.
2. **Revisar a NEXO pela LGPD.**
3. **DNS: nome em vez de IP.**

## Linha do tempo que as regras descrevem

```
vencimento − 1 a 2 semanas   aviso de renovação
vencimento                   sem renovação → SUSPENSA
vencimento + 2 semanas       fim da exportação de PDFs
vencimento + 3 meses         CANCELADA (prazo prorrogável por acordo)
depois                       tela bloqueada (com desfoque) e mensagem
```

## O que o código faz hoje (levantado em 25/10/2026)

| Tema | Situação atual | Distância para a regra nova |
|---|---|---|
| Contrato | `Empresa` só tem `data_contratacao` (`models.py:94`). Não há data de vencimento, duração, data de suspensão nem prorrogação | Faltam campos de vigência, o que exige migração de banco (seguir a proteção da Etapa 0.2A) |
| Status da conta | `ATIVA/SUSPENSA/CANCELADA` existe (`models.py:113`), mas a troca é **manual** no formulário do admin (`blueprints/admin.py:433`) | Faltam a suspensão e o cancelamento automáticos por data, ou ao menos um alerta para a equipe |
| Conta suspensa | A Visão Geral mostra um aviso (`templates/cliente/dashboard.html:9`). Só a abertura de nova análise é bloqueada (`blueprints/admin.py:230`) | Falta limitar a exportação de PDFs a 2 semanas e a visualização ao período pago |
| Conta cancelada | Não encontrei tratamento: login, portal e PDFs funcionam normalmente, e nem o aviso de conta suspensa aparece (o template só testa `SUSPENSA`) | Falta a tela com desfoque e a mensagem |
| Exportação de PDF | `pdf_export.py` não consulta o status da conta | Falta o bloqueio por status e por prazo |
| Aviso de renovação | Já existem `notifications.py` e `emails.py` | Falta o disparo por data (agendamento) |
| Preços | `seed.py` grava Bronze 600, Prata 1000, Ouro 1400. O valor do banco de produção não foi conferido | Atualizar o seed e os dados de produção com backup antes. O card "receita mensal estimada" do admin (`blueprints/admin.py:74`) e o formulário de empresa (`templates/admin/empresa_form.html:92`) leem `valor_mensal` |
| Logo | `nexo-logo.jpeg` (com texto) é usado no login, no primeiro acesso, na recuperação e no reset de senha, em "como aderir" e na barra lateral (`templates/base.html:43`). A landing usa um quadrado com "N" (`templates/landing.html:23` e `:448`) | Trocar pela arte só do cubo |
| NexoBot | `nexobot/saber/empresas_planos.py:130-177` diz que conta suspensa ou cancelada "continua acessando o histórico" | Reescrever depois que as regras forem implementadas |

## Observações

- O `static/img/nexo-logo.jpeg` atual tem uma **marca d'água de imagem gerada (✦) no canto inferior direito**. As artes 01 e 02 não têm.
- A arte 01 ainda tem fundo escuro e anel branco. Em tamanhos pequenos (barra lateral, favicon), um recorte do cubo com fundo transparente fica mais nítido.
- Em "tirar a logo da imagem", "a imagem" pode ser a da tela de login, a da barra lateral ou as duas.

## Dúvidas a decidir com o proprietário

1. **Logo:** trocar em todas as telas (login, barra lateral, landing com o "N") ou só no login? Manter o anel branco e o fundo, ou usar só o cubo com fundo transparente?
2. **Conta suspensa:** "ver os dados já pagos" vale para todo o período até o cancelamento (3 meses) ou só para as análises do período contratado?
3. **Aviso de renovação:** qual é a regra exata entre 1 e 2 semanas? Por exemplo: contrato de até X meses → 1 semana; acima disso → 2 semanas.
4. **Planos:** os novos preços valem também para contratos em vigor ou só para novos contratos? Os demais atributos dos planos (análises por mês, tipo, nível) continuam os mesmos?
5. **Conta cancelada:** o usuário ainda consegue entrar e vê a tela desfocada, ou o login é bloqueado com a mensagem?
6. **LGPD:** a revisão é um documento de conformidade (dados tratados, base legal, retenção, direitos do titular) ou também inclui mudanças no sistema? O prazo de 3 meses até o cancelamento e o destino dos dados depois dele entram na política de retenção.
7. **DNS:** já existe um domínio próprio registrado? A hospedagem é a do `render.yaml` (Render)?

## Nota de integração (26/10/2026)

Acrescentada ao fim do arquivo para não deslocar as referências de linha (`README.md:62-70`) usadas em `Docs/AJUSTES_NEXO_2026/`.

Estes insumos são referências do proprietário e não significam que as funcionalidades representadas já existam. A identidade visual do sistema **não** foi alterada nesta integração. Ao publicar no GitHub:

- `01`, `02`, `04` e `05` foram mantidos byte a byte (o `01` conserva o SHA-256 `ff29a45f…2b16b6d` citado em `Docs/AJUSTES_NEXO_2026/NEXO_AJ_00_BASELINE.md`).
- A captura original `03_telas_atuais_marca_portal_admin_login.png` **não foi versionada**. Ela mostra razão social, CNPJ, nomes de arquivos, valores financeiros de uma empresa, os totais do painel ADMIN (empresas por status, receita mensal estimada, gráficos) e uma URL na barra de status. O próprio relatório da NEXO-AJ-00 pede confirmação antes de compartilhá-la. Foi publicada a versão `03_telas_atuais_marca_portal_admin_login_redigida.png`, com esses trechos cobertos por tarjas "REDIGIDO" e com marca, layout e tela de login preservados. O original continua com o proprietário; se ele confirmar que são dados fictícios, pode versioná-lo depois.
- Após a NEXO-AJ-06.1, a linha "Conta cancelada" da tabela "O que o código faz hoje" ficou desatualizada: login, sessões, rotas, PDFs, uploads, notificações e Socket.IO do CLIENTE de empresa CANCELADA passaram a ser bloqueados. A tela própria com desfoque e mensagem (06.3) e a transição automática (06.2) continuam pendentes.
- **Logo (26/10/2026):** o pedido "tirar a logo da imagem e colocar somente o cubo" foi atendido com duas artes novas do proprietário, em PNG transparente: `static/img/nexo-cubo-brilho.png` (login e telas de acesso) e `static/img/nexo-cubo-transparente.png` (sidebar, cabeçalho e rodapé da landing). A `static/img/nexo-logo.jpeg` citada acima foi removida, e o "N" da landing deu lugar ao cubo. Detalhes em [`RELATORIO_ATUALIZACAO_IDENTIDADE_VISUAL_NEXO.md`](../../../INTEGRACOES/RELATORIO_ATUALIZACAO_IDENTIDADE_VISUAL_NEXO.md).
