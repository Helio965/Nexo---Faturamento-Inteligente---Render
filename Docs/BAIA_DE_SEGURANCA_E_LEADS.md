# Baia de Segurança dos relatórios

A integração importa a triagem de uploads da NEXO Coder, preservando o motor financeiro do NEXO no Render. O nome deste documento conserva a origem; **a captação de leads e a migração f4c2a8e1d9b6 não fazem parte desta entrega**. Não há novo formulário público, coleta de contatos, TTL de leads ou agendador ativado.

## Fluxo de segurança

| Etapa | Processo | Comportamento |
|---|---|---|
| Cópia limitada | Web | Blocos de 64 KiB até limite + 1 byte; o menor limite entre ETLLimits e 50 MiB prevalece. Content-Length não é autoridade. |
| Assinatura | Web | Primeiros 8 KiB conferem extensão/conteúdo. Executáveis, scripts, markup, PDF, mídia e conteúdo binário são recusados. XLS é reconhecido, mas orienta salvar CSV/XLSX; o portal continua aceitando somente essas duas extensões. |
| Triagem profunda | Worker ETL isolado | Reusa limites estruturais e de expansão; neutraliza fórmulas textuais, exige colunas mínimas de PDV e inventaria partes ativas XLSX. |
| Cópia passiva | Worker ETL isolado | Havendo fórmula, macro, ActiveX, OLE, vínculo externo ou parte não reconhecida, cria CSV ou XLSX apenas com valores. A releitura precisa reproduzir exatamente a matriz neutralizada; caso contrário recusa. |
| Persistência | Web | Arquivo limpo permanece byte a byte. Para cópia neutralizada, hash e tamanho correspondem aos bytes persistidos; o nome original é mantido. Recusados ficam só no diretório temporário da requisição e são removidos. |

`etl_inputs.read_raw` neutraliza também arquivos antigos ao reprocessá-los. No Raio-X os relatórios passam por assinatura, limite e leitor comum; os arquivos enviados não são persistidos pelo diagnóstico. A disponibilidade do Raio-X segue sua configuração comercial própria.

## Neutralização e compatibilidade financeira

Células começando em `=`/`@`, ou em sinal seguido de operador/referência de fórmula, recebem apóstrofo. TAB/CR/LF iniciais viram espaços. BOM residual e fórmulas depois de separadores internos também são tratados. Números comuns com sinal permanecem intactos. A neutralização é idempotente.

O parser financeiro legado ignora o apóstrofo antes de detectar o sinal, evitando que uma quantidade como `-2 un(s)` vire positiva. Um apóstrofo literal antes de número negativo passa também a preservar esse sinal; esse é o único ajuste no parser. O nome exibido de produto que parecia fórmula pode passar a conter apóstrofo.

Não foram importados o novo parser monetário, a interpretação automática de cancelamentos/devoluções, a mudança de Curva ABC para todos os produtos, nem a representação modificada de floats XLSX com três casas. A fixture financeira original permanece intacta. O motor conserva top20, regras de cálculo e limites anteriores; o Raio-X usa interpretação própria em módulo separado.

A conferência de total PDV, seus gates de publicação e suas telas não são ativados nesta entrega. Essas mudanças exigem análise própria da regra de bruto/devoluções e migração revisada; a ausência de tabela nova não deve bloquear a publicação legada.

## Isolamento, prazos e logs

A triagem profunda continua no subprocesso com limites de memória, CPU, arquivo e prazo. A operação `validate` pode gerar cópia de até o tamanho permitido para a entrada; as demais operações permanecem limitadas pelo tamanho do resultado. O prazo de validação dobra, limitado a 120 s, para permitir leitura e releitura da cópia. O limite padrão de resultado do ETL permanece 2 MiB.

A cópia liberada é conferida novamente por tamanho, assinatura e descritor regular, sem seguir symlinks. Rejeições registram motivo, tamanho, extensão e SHA-256; nunca conteúdo, nome original ou caminho temporário. A liberação registra os hashes antes/depois e os tipos de conteúdo neutralizados. A mensagem de recusa é fixa, com orientação específica quando útil.

## Verificação

`tests/test_security_gatekeeper.py` cobre assinatura, arquivos disfarçados, fórmulas, idempotência, números negativos/unidades, round-trip CSV/XLSX, macros/objetos/vínculos, teto, limpeza temporária, logs, uploads admin/cliente e worker real. `tests/test_etl_financial_equivalence.py` compara o corpus sintético histórico, sem substituir os resultados esperados.

Comandos usados e resultados efetivamente obtidos ficam no relatório final da integração. Não se enviam emails reais nem se usa Supabase/Render de produção nos testes. O gatekeeper não requer migração ou dependência nova.
