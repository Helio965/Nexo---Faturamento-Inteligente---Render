# Pendências futuras de segurança — SEC-004 e SEC-005

Registro exclusivamente documental incluído na SEC-006B por determinação do
proprietário. As correções abaixo devem ser planejadas e executadas em tarefas
separadas. Este documento não altera o comportamento da aplicação, o banco de
dados, as configurações de produção ou as regras comerciais.

## NEXO-SEC-004: Restauração de empresas e usuários

**Status: PENDENTE, NÃO IMPLEMENTAR AGORA.**

### Problema identificado

O procedimento de restauração de uma empresa pode reativar usuários que já
estavam desativados antes de a empresa ser enviada para a lixeira. Na base deste
registro, a rota administrativa `empresa_restaurar`, em
[`blueprints/admin.py`](../blueprints/admin.py#L489), remove a marca de exclusão
da empresa e executa, nas linhas 503–504:

```python
for u in empresa.usuarios:
    u.ativo = True
```

O trecho aplica o mesmo estado a todos os usuários vinculados, sem distinguir
a desativação anterior daquela causada pelo envio da empresa à lixeira. O
procedimento de exclusão reversível, no mesmo arquivo, define `ativo = False`
para os usuários vinculados nas linhas 460–461. O registro dessa condição não
significa que ela tenha sido corrigida na SEC-006B.

### Objetivo da correção futura

Preservar o estado de ativação anterior de cada usuário, impedindo que a
restauração da empresa restabeleça acessos que estavam desativados por decisão
administrativa anterior.

### Cuidados e dependências técnicas

- Preservar o histórico de usuários, análises, relatórios e chamados.
- Preservar permissões, papéis e isolamento entre empresas; não reativar usuários
  administrativos ou comerciais indevidamente.
- Preservar o funcionamento da lixeira e bloquear o acesso à empresa excluída
  enquanto ela permanecer na lixeira.
- Manter as proteções de autenticação, CSRF e revogação HTTP/Socket.IO já
  implementadas nas SEC-002 e SEC-003.
- Avaliar como registrar o estado anterior dos usuários antes da desativação
  decorrente da exclusão reversível. Não inferir retroativamente que todo usuário
  desativado deve voltar a ficar ativo.
- Definir o tratamento de registros antigos sem informação suficiente, de
  alterações administrativas durante a permanência na lixeira e de operações
  repetidas ou concorrentes.
- Caso seja necessário persistir informação adicional, planejar uma migração
  revisada, sua compatibilidade com dados existentes e os testes correspondentes.
  Nenhuma mudança de schema está autorizada por este registro.

Arquivos a avaliar futuramente: `blueprints/admin.py`; modelos, migrações e
testes administrativos somente se a solução escolhida demonstrar necessidade.

### Critérios de aceitação futuros

1. Um usuário desativado antes da exclusão reversível continua desativado após a
   restauração da empresa.
2. Usuários anteriormente ativos são restaurados conforme uma política explícita
   e validada, sem alterar papéis ou permissões.
3. Empresas na lixeira permanecem sem acesso autorizado aos seus dados, inclusive
   por sessões e conexões existentes, conforme as proteções já implementadas.
4. Exclusão e restauração em sequência, inclusive ciclos repetidos, preservam os
   estados e o histórico previstos, sem afetar usuários de outra empresa.
5. Erros de persistência não deixam empresa e usuários em estados parciais.
6. Os testes isolados cobrem usuários com estados anteriores diferentes e, se
   houver migração ou concorrência relevante, verificam esses cenários com banco
   descartável antes de qualquer proposta de produção.

**Gravidade preliminar:** alta potencial, pela possibilidade de restabelecer
acesso anteriormente desativado. A classificação é provisória e depende da
política de acesso e do fluxo administrativo efetivo; não constitui pontuação
CVSS nem comprovação de exploração em produção.

## NEXO-SEC-005: Limites de processamento ETL

**Status: PENDENTE, NÃO IMPLEMENTAR AGORA.**

### Problema identificado

O processamento de planilhas pode consumir recursos excessivos ao carregar
arquivos grandes ou com muitas abas, linhas e colunas. Na base deste registro,
[`etl_processor.py`](../etl_processor.py#L191), função `_ler_bruto`, contém nas
linhas 203–204 a leitura de todas as abas XLSX antes de selecionar a matriz com
mais células preenchidas:

```python
pd.read_excel(
    caminho_arquivo,
    dtype=str,
    header=None,
    engine="openpyxl",
    sheet_name=None,
)
```

Os limites de requisição e de formulários multipart exercitados na SEC-006 não
equivalem a limites de expansão de XLSX, quantidade de células ou recursos do
processamento ETL. A leitura CSV também precisa de orçamento próprio. Nenhum
desses limites de processamento foi implementado nesta etapa documental.

### Objetivo da correção futura

Estabelecer limites adequados de processamento sem comprometer os relatórios
comerciais legítimos, os cálculos de faturamento, os indicadores e a Curva ABC.
Os valores dos limites devem ser definidos com critérios operacionais e testes;
este registro não inventa limites nem altera o processamento atual.

### Itens para futura análise

- Tamanho máximo do arquivo e orçamento para conteúdo descompactado.
- Quantidade máxima de abas, linhas, colunas e células processadas, por aba e no
  conjunto do documento.
- Consumo de memória e tempo máximo de processamento, incluindo tratamento de
  interrupção e limpeza de recursos.
- Arquivos XLSX excessivamente complexos ou malformados e proteção contra
  expansão excessiva de arquivos compactados.
- Limites próprios para CSV, validação de codificações, linhas irregulares e
  campos extensos, sem modificar as regras comerciais de interpretação.
- Tratamento seguro de erros, sem exposição de detalhes internos ou dados de
  clientes e sem persistência parcial de resultados inválidos.
- Preservação dos formatos legítimos suportados, das regras de faturamento,
  dos indicadores e da Curva ABC.

Dependências técnicas a avaliar: estratégias de leitura de pandas/openpyxl,
inspeção segura da estrutura ZIP do XLSX, orçamento de recursos e integração
com os pontos que chamam o ETL. Não é uma autorização para substituir essas
bibliotecas, criar serviços externos ou modificar banco/infraestrutura.

Arquivo principal: `etl_processor.py`. Rotas de upload/processamento e testes
correspondentes deverão ser avaliados somente na futura correção e conforme a
necessidade demonstrada.

### Critérios de aceitação futuros

1. Limites de bytes, expansão, abas, linhas, colunas, células, memória e tempo
   possuem política documentada e comportamento definido ao excedê-los.
2. Arquivos XLSX/CSV legítimos usados nas regressões mantêm os resultados de
   faturamento, indicadores e Curva ABC dentro dos limites aceitos.
3. Entradas malformadas ou acima do orçamento são rejeitadas de forma controlada,
   sem persistência parcial, exposição de dados ou consumo sem limite definido.
4. Os testes incluem limites, valores imediatamente abaixo/acima e expansão de
   conteúdo com amostras sintéticas pequenas; não realizam negação de serviço
   contra sistemas reais nem utilizam arquivos de clientes.
5. A rejeição e a limpeza de recursos são verificadas no fluxo de integração,
   preservando autenticação, CSRF, isolamento entre empresas e as proteções das
   SEC-001, SEC-002, SEC-003 e SEC-006.
6. A solução é validada em ambiente descartável, com evidências de desempenho e
   regressão antes de qualquer proposta de implantação.

**Gravidade preliminar:** média, por risco de indisponibilidade decorrente de
consumo de recursos. A avaliação final depende da capacidade de processamento,
dos controles de acesso e da exposição do fluxo; não houve teste de exploração
ou medição contra o ambiente de produção.

## Registro e limites desta entrega

| Item | Valor |
| --- | --- |
| Data do registro | 23/10/2026, referência de calendário America/Sao_Paulo. |
| Commit de referência desta base | `5eb352403d4df7659602047472ab0afcd9540b28`. |
| Referência conhecida no pedido | `415466ef2c89fb3e1fbae6dec4ce575a6688923e`; a base atual inclui o avanço documental posterior. |
| Tarefa que inclui este registro | NEXO-SEC-006B, segurança das dependências e do processo de instalação. |
| SEC-004 | Pendente; gravidade preliminar alta potencial; arquivo principal `blueprints/admin.py`. |
| SEC-005 | Pendente; gravidade preliminar média; arquivo principal `etl_processor.py`. |
| Dependências futuras | Política de restauração de acessos, eventual persistência/migração planejada, orçamentos ETL e testes isolados de regressão. |
| Alterações funcionais neste registro | Nenhuma. SEC-004 e SEC-005 não foram implementadas. |
| Produção | Nenhum acesso a dados reais, deploy, migração ou alteração de configuração é realizado por este documento. |

Os critérios de aceitação de cada pendência estão registrados acima para
planejamento futuro. Sua execução e qualquer integração ou implantação exigem
uma tarefa posterior com escopo e autorização próprios.
