# 02 — Regras de negócio da gestão contratual

> **Convenções propostas.** Prazos, contagens e efeitos marcados como *proposta* foram adotados para permitir a implementação e os testes. Eles **ainda não foram homologados comercialmente**: veja `05_PENDENCIAS_DE_DECISAO_COMERCIAL.md`. Os parâmetros estão centralizados em `config.py` (`CONTRATO_*`), e não espalhados pelo código.

## 1. Regimes

| Regime | Quando | Efeito |
|---|---|---|
| **Legado** | Empresa sem linha em `regime_contratual`. É o caso de **todas** as empresas existentes após a migração | Comportamento anterior preservado: ATIVA e SUSPENSA acessam o histórico publicado e o PDF; CANCELADA bloqueia (AJ-06.1) e agora vê a tela de conta encerrada |
| **Contratual** | Ativado pelo ADMIN depois de registrar o contrato vigente e os períodos comprovadamente pagos | Valem as regras abaixo; acesso sem cobertura paga comprovada é negado |

O ADMIN só consegue ativar as regras se houver contrato ATIVO, ou SUSPENSO ainda dentro do prazo, e se o status da empresa coincidir com o do contrato (ATIVA com ATIVO, SUSPENSA com SUSPENSO). A desativação volta a empresa ao regime legado e fica registrada; é uma contingência de implantação.

## 2. Contratação

- O ADMIN escolhe o plano, informa o valor mensal contratado e a vigência (o término é opcional; sem ele, o prazo é indeterminado). Também pode registrar a formalização (data e referência), um prazo de suspensão menor (opcional) e observações.
  - **Valor contratado:** é preenchido com o preço de catálogo e pode ser ajustado a uma condição negociada; aceita no máximo 2 casas decimais e fica entre 0 e 1.000.000.
  - **Formato do valor:** aceita o formato brasileiro (`1.500` = mil e quinhentos; `1.234,56`) ou ponto decimal com até duas casas (`650.00`). Ponto seguido de exatamente três dígitos é sempre milhar. Formatos ambíguos (`1,234.56`) são recusados.
  - **Formalização:** a data não pode ficar no futuro.
- Só pode existir **um contrato vigente** (ATIVO ou SUSPENSO) por empresa; o banco garante essa regra.
- A contratação deixa a empresa ATIVA e sincroniza `empresa.id_plano_atual`.
- **Empresa SUSPENSA na conciliação:** a contratação **não** a reativa. Ela continua SUSPENSA, no regime legado, até o ADMIN registrar no contrato a suspensão com o instante real (ou reativá-la, se a situação foi regularizada). Enquanto o status da empresa e o do contrato divergirem, a ativação das regras é recusada.
- **Reativação após cancelamento:** se a empresa estava CANCELADA, a nova contratação a reativa. As sessões antigas continuam inválidas, porque a geração de autorização sobe ao sair de CANCELADA, e é exigido novo login. Períodos não pagos continuam negados.
- Assinatura eletrônica e armazenamento de documentos **não** existem: registra-se só a referência da formalização.
- Contratos de empresas antigas **não** são criados automaticamente.

## 3. Renovação e alteração de plano

- Ambas criam um **novo** contrato ligado ao anterior (`id_contrato_anterior`). O anterior passa a ENCERRADO e conserva plano, valor e período originais.
- A nova vigência deve começar **depois** do início do contrato atual e **não pode começar no futuro**. Renovação ou troca de plano agendada não é suportada: o contrato atual passa a ENCERRADO no ato, então o registro deve ser feito a partir da data de início da nova vigência.
- **Alteração de plano:** exige um plano diferente e uma justificativa. As análises já produzidas mantêm o próprio `id_plano_referencia`.
- **Suspensão em curso:** a renovação pode ser feita a partir de um contrato SUSPENSO (*renovação antes do encerramento*), e a empresa volta a ATIVA.

## 4. Coberturas pagas (períodos efetivamente pagos)

- **Registro:** é confirmado manualmente pelo ADMIN, com referência administrativa obrigatória e intervalo de datas inclusivo dentro da vigência do contrato. Não existe integração com gateway de pagamento.
- **Não há presunção de pagamento:** o contrato não é considerado pago por inteiro e nenhum período anterior é marcado como pago automaticamente.
- **Sobreposição:** é proibida entre coberturas vigentes da mesma empresa.
- **Vigência efetiva:** a cobertura precisa caber no período em que o contrato realmente valeu. Para um contrato ENCERRADO, isso vai até a véspera do início do sucessor; para um CANCELADO, até a data do cancelamento. O término previsto sempre limita os dois casos.
- **Correção:** feita por revogação com motivo, sem apagar o registro original.
- **Validade no tempo:** a cobertura conta a partir de `confirmado_em` e deixa de contar ao ser revogada.
- **Direito a uma análise:**
  - O período exigido é o declarado (`periodo_inicio` a `periodo_fim`), ampliado pelo período real lido da base (`indicador_analise.periodo_base_*`), quando existir.
  - Esse período precisa estar **inteiramente** dentro da união das coberturas, considerando todos os contratos da empresa.
  - Intervalos consecutivos (por exemplo, fim em 31/01 e início em 01/02) se unem; uma lacuna de um dia já impede o acesso.
  - Cobertura parcial não dá acesso.
- **Agregados:** o gráfico histórico e as listas usam apenas análises autorizadas.

## 5. Suspensão (*proposta*)

- **Registro:** o ADMIN registra o motivo e o **instante oficial** da suspensão. Se o instante não for informado, vale o momento atual.
  - O instante não pode estar no futuro.
  - Também não pode ser anterior ao início da vigência do contrato nem à última mudança de situação registrada nele (por exemplo, uma reativação). O cadastro do contrato não conta como mudança: na conciliação, a suspensão real anterior ao cadastro pode ser registrada, e os prazos contam desse instante real.
- **Prazos calculados e gravados no contrato:**
  - Acesso histórico até **início + 3 meses de calendário**, contados no fuso America/Sao_Paulo. Mantém-se o mesmo dia e a mesma hora locais; quando o mês de destino é mais curto, usa-se o último dia dele (por exemplo, 31/01 + 1 mês = 28/02, ou 29/02 em ano bissexto). **Não são 90 dias**: de 01/03 a 01/06 há 92 dias.
  - O contrato pode prever um prazo menor (1 ou 2 meses).
  - Exportação de PDF até **início + 14 dias corridos**, na mesma hora local. Esse prazo nunca ultrapassa o fim da suspensão.
  - Os limites são **exclusivos**: no instante-limite, o prazo já terminou.
- **O que a empresa SUSPENSA pode fazer:**
  - autenticar-se enquanto o prazo vale;
  - consultar o histórico das análises cobertas;
  - exportar o PDF dessas análises enquanto durar o prazo de PDF;
  - abrir chamados de suporte.
- **O que a empresa SUSPENSA não pode fazer:**
  - receber novas análises;
  - enviar arquivos, exceto para uma análise aberta de período já pago;
  - ver períodos não pagos;
  - exportar PDF depois do prazo.
- **Reativação:** o ADMIN pode reativar enquanto o prazo vale. Depois do limite, só por renovação, nova contratação ou prorrogação.

## 6. Prorrogação da suspensão

- Somente para um contrato SUSPENSO. Exige justificativa e um novo limite que seja posterior ao limite vigente, posterior ao início da suspensão e futuro.
- O **limite original** fica preservado. O evento `PRORROGACAO` guarda o original, o anterior e o novo limite.
- A prorrogação **não** representa pagamento: o direito às análises continua dependendo das coberturas.
- A prorrogação **não** amplia o prazo de PDF. A exceção é uma *autorização contratual específica*, indicada em campo próprio: o novo prazo de PDF deve ser posterior ao atual e não pode passar do novo limite da suspensão.
- Pode ser registrada mesmo depois do limite, enquanto a reconciliação não tiver cancelado o contrato; o acesso volta a valer até o novo limite. **Proposta**: confirmar na homologação.

## 7. Cancelamento e fim do prazo

- **Cancelamento manual pelo ADMIN:** exige motivo e a confirmação digitada "CANCELAR". O contrato vira CANCELADO e a empresa vira CANCELADA. As sessões, os tokens e o Socket.IO dos usuários CLIENTE são revogados (AJ-06.1). Os dados são preservados.
- **Fim do prazo da suspensão, sem renovação, nova contratação ou prorrogação:**
  1. **No mesmo instante:** a política passa a tratar a empresa como `SUSPENSAO_EXPIRADA`. O portal é negado já na cláusula SQL, antes de qualquer gravação.
  2. **Reconciliação** (`flask contratos reconciliar`, ou o botão em Admin → Contratos):
     - grava o cancelamento, com origem `RECONCILIACAO` e motivo padrão;
     - sobe a geração de autorização dos usuários e derruba as conexões.
     - É idempotente e protegida contra execuções concorrentes (lock consultivo no PostgreSQL, mais o lock de cada empresa, com reavaliação do prazo).
     - Por padrão, faz só a simulação.
- **Agendamento:** **nenhum foi configurado**. A segurança não depende do agendador, porque a expiração já é aplicada pela política.
- **Tela "Conta encerrada":** quem informa a senha correta de uma conta CANCELADA, com suspensão expirada ou sem contrato no regime contratual recebe a página informativa. Não há sessão, dashboard, indicadores, histórico nem PDF (ver documento 03).

## 8. Exportação de PDF

A rota `/cliente/analise/<id>/pdf` decide, **antes de gerar qualquer byte**, nesta ordem:

1. A análise pertence à empresa, está concluída e publicada; caso contrário, 404.
2. A empresa tem acesso ao portal e o período está coberto; caso contrário, 403.
3. A empresa está ATIVA, ou está SUSPENSA dentro do prazo de PDF; caso contrário, 403 com a mensagem: "Seu prazo para exportação de relatórios foi encerrado. As análises históricas autorizadas continuam disponíveis para consulta durante o período de suspensão."

A tela da análise só mostra o botão de exportar quando a exportação é permitida. O gerador de PDF não foi alterado.

## 8.1 Novas análises no regime contratual

O ADMIN só abre uma análise para empresa ATIVA, e o período inteiro precisa caber na vigência efetiva de **algum** contrato não cancelado da empresa: o vigente ou um anterior encerrado. O plano de referência gravado (`id_plano_referencia`) é o desse contrato. Se mais de um servir, vale o de início mais recente. A regra QUINZENAL (só OURO) também usa o plano desse contrato. A decisão é tomada com a empresa bloqueada, para não correr em paralelo com uma suspensão ou um cancelamento.

## 8.2 Exclusão permanente

A exclusão permanente (lixeira → excluir definitivamente) fica **bloqueada** para empresas com histórico contratual (contratos, períodos pagos, eventos ou regime). Esses registros são financeiros e de auditoria, e a política de retenção depende de decisão (documento 05). A empresa continua na lixeira.

## 9. Valores dos planos

| Plano | Valor mensal padrão | Benefícios (inalterados) |
|---|---|---|
| BRONZE | R$ 150,00 | Análise mensal básica, 1 por mês, dashboard resumido |
| PRATA | R$ 300,00 | Análise mensal completa, 1 por mês, dashboard gerencial |
| OURO | R$ 650,00 | Análises quinzenais premium, 2 por mês, dashboard completo |

- **Fonte única:** `plan_catalog.py`. O `seed.py` usa esse catálogo para criar planos ausentes.
- **Bancos existentes:** a atualização é auditada e idempotente, feita por `flask planos atualizar-precos`.
  - O padrão é a simulação.
  - Para gravar, é obrigatório usar `--aplicar --confirmo-janela-autorizada`.
  - Cada alteração fica registrada em `historico_preco_plano`.
  - **Não foi executada em produção.**
- **Contratos existentes:** nunca são alterados. Cada contrato guarda o valor acordado.
- **Landing e NexoBot:** continuam sem exibir preços ("Sob consulta" e a regra editorial do bot), porque publicar preços é decisão pendente (documento 05).
