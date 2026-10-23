# Evidências de infraestrutura — NEXO

Auditoria inicial em 22/10/2026 UTC; estado de integração atualizado em 23/10/2026 (America/Sao_Paulo). Repositório oficial `Helio965/Nexo---Faturamento-Inteligente---Render`. O Codex não alterou configurações externas nem executou merges, deploy, backup ou alterações de dados de produção.

## GitHub: estado observado

| Verificação | Resultado efetivo |
| --- | --- |
| Metadados do repositório | Privado, `visibility=private`, não arquivado, não desabilitado; branch padrão `main`. |
| Permissões expostas para o usuário | `admin`, `maintain`, `push`, `pull` e `triage`: `true`. Isso não comprova que a integração possua toda permissão administrativa de API. |
| `GET /branches/main` | SHA `255957d1807b792cd18298b34df01653db8afc22`; `protected=false`. |
| Verificação após integração externa | SHA `d6f0a9e20ccf0879919a10e0e6223c8290f5a8c2`; `protected=false`; CI de push aprovado no run 39705823783. |
| `GET /actions/workflows` | `total_count=0` na auditoria inicial, antes da nova implementação de CI. |
| `GET /branches/main/protection` | HTTP 403, `Resource not accessible by integration`. Endpoint exige `administration=read`; detalhes da configuração clássica não foram acessíveis. |
| `GET /rulesets` | HTTP 403, `Upgrade to GitHub Pro or make this repository public to enable this feature.` Recurso indisponível para a combinação atual de conta/repositório privado. |
| `GET /actions/permissions` | HTTP 403, `Resource not accessible by integration`; configuração administrativa de Actions não pôde ser inspecionada. |
| Consulta ao plano pelo usuário autenticado | Campo `plan` não retornado (`null`); não foi possível comprovar o nome do plano. |

Os 403 acima vieram da API GitHub: corpo JSON, documentação do endpoint e `X-GitHub-Request-Id` presentes. Diferem do bloqueio de proxy CONNECT 403 registrado anteriormente. As APIs de metadados, branch e workflows responderam normalmente. Não foram impressos tokens, credenciais ou cabeçalhos de autenticação. Não houve tentativa de contornar a restrição ou mutação de regras.

### Procedimento de proteção a apresentar ao proprietário

1. Manter o repositório privado. Não contratar plano nem mudar visibilidade automaticamente.
2. Em Settings → Rules/Branches, verificar a disponibilidade real de proteção clássica e rulesets para o plano. A leitura de proteção clássica requer também permissão administrativa apropriada na integração; `admin=true` nos metadados não substitui essa permissão.
3. Se um recurso de proteção estiver disponível e o proprietário autorizar sua alteração, preparar regra para `main`: exigir PR, revisão por outro responsável quando houver revisor disponível, verificações CI obrigatórias usando os nomes exatos dos jobs após a primeira execução real, resolução das conversas, bloqueio de force push e de exclusão, e restrição de alterações diretas.
4. Antes de ativar verificações obrigatórias, confirmar que o workflow executa em PRs normais e que os checks corretos são publicados. Nunca selecionar check inexistente, opcional ou com nome variável.
5. Definir responsável substituto e procedimento de recuperação administrativa auditável, sem criar um bloqueio impossível de administrar. Um proprietário único não pode aprovar a própria revisão; a política precisa refletir a disponibilidade de um segundo revisor.
6. Se a conta privada continuar sem suporte, documentar a opção de plano compatível para decisão do proprietário, sem contratação. Enquanto isso, seguir revisão e testes antes de qualquer merge. Essa política manual **não equivale a proteção técnica**.

Nenhuma proteção foi aplicada nesta tarefa de auditoria; a verificação observou `main` sem proteção ativa.

## Render: acesso e limites

Não há ferramenta Render autorizada conectada na sessão. A busca de ferramentas encontrou apenas a ferramenta de configuração do ambiente Codex, que não fornece acesso ao painel Render. Os documentos versionados não informam um domínio real verificado; o README contém somente `https://<seu-servico>.onrender.com/healthz/db`. Não foi inventado um endereço a partir do nome do serviço.

| Item | Estado |
| --- | --- |
| `main` GitHub no início | `255957d1807b792cd18298b34df01653db8afc22` confirmado pela API. |
| Commit publicado no Render | Não verificado: acesso ao serviço/painel não disponível. |
| Metadados GitHub de deployment | Leitura negada pela integração (403); sem statuses tradicionais Render no commit da main. Checks Actions não comprovam deploy. |
| Histórico, status e logs de inicialização | Não verificados. |
| Auto deploy efetivo do painel | Não verificado. O arquivo versionado não prova o estado do painel. |
| Health check real | Não executado: URL do serviço real não foi identificada por fonte verificável. |
| YAML versionado | `branch: main`, `autoDeployTrigger: 'off'`, build `pip install -r requirements.txt`, `/healthz`, Gunicorn com 1 worker e 50 threads. |
| Ensaio de backup/restore | Executado em PostgreSQL 17.11 descartável: 1/1 aprovado em 1,916 s, 15 tabelas, quatro uploads, cinco arquivos e production_access=false; também aprovado na regressão completa. Não comprova backup do Supabase. |

O `wsgi.py` explica que salas Socket.IO e rate limiting são locais ao processo; a arquitetura versionada usa um worker com threads. Não presumir que esse estado de memória atende múltiplas instâncias. A SEC-003 mantém a autoridade no banco e protege as emissões, além do handshake.

## Plano de publicação futura — exige autorização específica

Este é um procedimento preparado, não executado. Nenhum comando de deploy ou migração deve ser inferido como autorização.

1. **Inventário privado**: proprietário registra ID/domínio do serviço, commit publicado, histórico, status, configuração real de auto deploy, comando Gunicorn e número de instâncias. Conferir acesso e retorno de `/healthz` e `/healthz/db`. Não divulgar valores de variáveis nem caminhos contendo tokens nos registros.
2. **Referência candidata**: as três frentes já alcançaram a main por merges externos, no SHA `d6f0a9e20ccf0879919a10e0e6223c8290f5a8c2`, com CI aprovado. Esse é um candidato técnico, ainda sujeito à verificação operacional e autorização explícita de deploy. Não usar simplesmente “latest commit” sem comparar o SHA do deploy ao candidato. O SHA `255957d` permanece como base histórica da auditoria.
3. **Dependências e schema**: registrar versões e diff de requirements/migrations. Se nenhuma migração for adicionada pelas implementações, a publicação não precisa executar DDL, seed, `create_all`, upgrade/downgrade ou restauração. Qualquer mudança de schema inesperada interrompe o procedimento para plano e autorização próprios.
4. **Evidências antes da publicação**: CI real aprovado, suíte completa, concorrência PostgreSQL, backup/restore sintético, fluxos de e-mail com transporte simulado, revogação de cookies antigos e bloqueio de notificações Socket.IO revogadas, CSRF, rate limiting, PDF e regressões gerais. Teste ignorado ou não executado continua identificado como tal.
5. **E-mails e domínio**: conferir HTTPS e URLs externas, remetente verificado, disponibilidade/configuração do Brevo sem exibir chaves. Teste real de e-mail somente em homologação autorizada, com destinatário controlado. Retorno de agendamento não prova entrega; revisar falha assíncrona e evento de entrega no provedor.
6. **Backup/recuperação**: seguir `Docs/OPERACAO_BACKUP_RESTAURACAO.md`. Um procedimento e um ensaio sintético não comprovam backup atual de produção. Acesso/backup real precisa de autorização, destino privado e responsável; nunca restaurar sobre o Supabase como teste.
7. **Impacto esperado**: links v1 deixam de valer pela SEC-002 e devem ser reemitidos pelo formulário. A SEC-003 deve invalidar cookies sem vínculo válido e sessões de credenciais antigas. Documentar para o suporte a necessidade de novo login. Não reintroduzir tokens antigos nem cookies sem vínculo por compatibilidade.
8. **Transição de processos**: parar/drenar workers antigos, reiniciar a instância com o candidato aprovado e reconectar Socket.IO mediante autenticação válida. Não manter código antigo aceitando sessões/tokens enquanto o novo é anunciado como ativo. Rollout em várias instâncias exige estratégia compatível com a nova implementação e sua validação.
9. **Publicação manual autorizada**: proprietário seleciona o SHA aprovado no Render, confirma ambiente e autorização e publica sem migração implícita. Registrar horário e commit efetivamente implantado. A tarefa atual não executa essa operação.
10. **Validação após publicar**: primeiro saúde e inicialização; depois login/logout, ativação/reenvio/recuperação com conta autorizada de homologação, invalidação de sessão anterior, handshake e conexão Socket.IO revogada, isolamento de usuário/empresa, notificações, dashboard admin/cliente, upload/ETL/PDF, NexoBot, página inicial/vídeo/assets e entrega de e-mail controlado. Conferir ausência de bearer tokens nos logs do aplicativo, Gunicorn, proxy Render e observabilidade, sem imprimir um token real.
11. **Interrupção**: parar liberação se saúde não estabilizar, schema divergir, houver migração inesperada, cookie antigo autenticar, conexão revogada receber dados, duas redefinições confirmarem, isolamento falhar, token vazar, e-mail falhar ou os dados persistidos apresentarem inconsistência. Registrar somente evidência sanitizada e preservar estado para investigação.
12. **Aprovação final**: responsável valida SHA, checks, saúde e fluxos com evidências antes de liberar normalmente. Nenhum teste isolado comprova configurações reais, volume, grants/RLS ou disponibilidade contínua do Supabase/Render.

## Plano de rollback

Preferir correção adiante quando reverter reabrir falha de segurança. Antes da publicação, registrar uma referência segura conhecida, com testes e compatibilidade com o schema atual; não escolher apenas o commit anteriormente publicado, cuja segurança pode ser desconhecida.

- Rollback de código exige autorização própria, revisão do diff e implantação do SHA seguro escolhido; não há reset/force push na `main`.
- Não voltar ao token v1 nem aceitar cookies sem vínculo da SEC-003 para recuperar compatibilidade. Se não houver versão anterior segura, restringir acesso/colocar em manutenção conforme procedimento autorizado e preparar correção adiante.
- Reiniciar/drenar processos para não manter trabalhadores com políticas divergentes; revogação de sessões pode exigir novo login.
- Reverter Git não reverte schema nem dados. Sem mudança de schema neste conjunto, não há razão para executar downgrade/restore. Se uma alteração estrutural vier a ser aprovada, preparar plano independente e compatibilidade de código antes da publicação.
- Recuperação de banco somente com autorização específica, restauração em destino separado e reconciliação de dados posteriores; não sobrescrever produção nem assumir que existe backup real sem evidência.

## Intervenções externas pendentes

| Necessidade | Responsável/ação necessária |
| --- | --- |
| Verificar painel Render, SHA implantado, auto deploy e URL | Proprietário com acesso de leitura ao serviço ou integração autorizada. |
| Confirmar configurações e entrega real do provedor de e-mail | Proprietário do Brevo/homologação, com destinatário controlado. |
| Proteção administrativa GitHub | Proprietário avalia plano privado e permissões da integração; não mudar visibilidade nem comprar plano automaticamente. |
| Configurar checks obrigatórios | Somente após CI real aprovado e autorização administrativa, se suportado pelo plano. |
| Integração das PRs | #12/#11/#10 já integradas externamente; o Codex não realizou merges. Novas PRs continuam exigindo revisão e autorização. |
| Deploy no Render | Autorização explícita posterior; não executado nesta tarefa. |
| Backup/migração/recuperação real Supabase | Autorização específica e plano próprio; não realizado. |

Fontes lidas: `render.yaml`, `wsgi.py`, `README.md`, `Docs/PREPARACAO_RENDER.md`, `Docs/OPERACAO_BACKUP_RESTAURACAO.md`, `tests/test_backup_restore.py`; respostas GET da API GitHub acima.

## Referências preparadas nesta tarefa

Homologação: PR #10, commit `b728fe0`. Revogação: PR #11, commit `c9b1f31`.
CI/documentação: PR #12, commit inicial `bb85788`. Os merges externos das bases
encadeadas incorporaram as três frentes à main `d6f0a9e`, com CI aprovado no
[run 39705823783](https://github.com/Helio965/Nexo---Faturamento-Inteligente---Render/actions/runs/39705823783).
A seleção para publicação continua dependendo de autorização explícita e da
identificação/validação do serviço real. Nenhuma dessas PRs autoriza deploy.
