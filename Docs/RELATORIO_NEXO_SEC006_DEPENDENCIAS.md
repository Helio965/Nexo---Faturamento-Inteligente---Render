# NEXO-SEC-006 — finalização e publicação controlada

Data: 23/10/2026. Este relatório distingue validação local, publicação no GitHub e implantação em produção. A execução atual recebeu autorização explícita para commit, push, Pull Request e merge condicionado aos critérios do proprietário; não é necessário solicitar novamente autorização para essas operações.

## A. Identificação

| Item | Estado verificado |
| --- | --- |
| Projeto | NEXO: Faturamento Inteligente |
| Repositório oficial | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| Diretório | `/workspace/Nexo---Faturamento-Inteligente---Render` |
| Branch de trabalho | `security/sec-006-dependency-updates` |
| Commit inicial e base da correção | `f4fd6d31f3ff5eefea534222700623d3e1c3d989` |
| Destino da Pull Request | `main` |
| Validação local | Linux, Python 3.12.14, virtualenv descartável `/tmp/nexo-sec006-validation` |
| Recursos sintéticos | PostgreSQL 17.11 por socket Unix privado, Chromium 154.0.8037.57 e Gunicorn 23.0.0 |

As correções SEC-001, SEC-002 e SEC-003 e o workflow `.github/workflows/nexo-security-ci.yml` já estavam presentes na base. A autorização atual não abrange deploy, alteração de infraestrutura, credenciais ou banco de produção.

## B. Recuperação do trabalho anterior

Foram encontrados os três pins atualizados em `requirements.txt`, os novos testes `tests/test_dependency_security_compat.py` e `tests/test_dependency_wsgi_runtime.py`, o relatório técnico e a auditoria em `Docs/`. O pacote `/workspace/artifacts/NEXO_SEC_006_DEPENDENCIAS_REVISAO.zip` também existe, fora do repositório. A implementação correta foi reaproveitada; não foi reconstruída nem substituída por conteúdo hipotético.

`requirements-dev.txt`, aplicação, autenticação, tokens, sessões, modelos, migrações, workflow, configurações de produção, regras comerciais, identidade visual, NexoBot e vídeo permaneceram sem alterações de implementação. Nesta etapa os relatórios foram atualizados para registrar a autorização de publicação, a nova execução dos testes, a reavaliação dos sete avisos residuais e as condições de merge. O ZIP continua fora do conjunto proposto para commit.

## C. Dependências atualizadas

| Biblioteca | Versão anterior | Versão final | Motivo |
| --- | --- | --- | --- |
| Flask | 3.0.3 | 3.1.3 | Correção de CVE-2026-27205, incluindo acesso à sessão e `Vary: Cookie`. |
| Werkzeug | 3.0.4 | 3.1.9 | Correção de CVE-2024-49767 e demais avisos posteriores contemplados pela versão estável. |
| Flask-SocketIO | 5.4.1 | 5.6.1 | Menor versão oficial verificada que corrige a incompatibilidade de sessão com Flask 3.1.3. |

`python -m pip check` foi reexecutado no ambiente isolado e retornou `No broken requirements found.`. As três versões foram confirmadas por `importlib.metadata` e os módulos foram efetivamente importados do ambiente candidato. As outras 62 distribuições mantiveram as versões da base; 65 distribuições no total, sem adição ou remoção. A virtualenv original `.venv` não recebeu atualizações.

Flask e Werkzeug declaram Python >=3.9; Flask-SocketIO declara Python >=3.8. Python 3.12 é atendido. Os hashes dos três wheels instalados foram conferidos contra PyPI oficial, com artefatos não retirados. As fontes, inventário e hashes completos constam em `AUDITORIA_DEPENDENCIAS_SEC006.md`.

## D. Correções de compatibilidade

A primeira candidata, apenas com Flask/Werkzeug atualizados, passou na resolução de dependências, mas falhou em 24 testes de Socket.IO: `AttributeError: property 'session' of 'RequestContext' object has no setter`. Flask 3.1.3 passou a expor a sessão do contexto por propriedade sem setter; Flask-SocketIO 5.4.1 ainda atribuía `ctx.session` diretamente.

A versão oficial 5.6.1 usa `ctx._session` quando disponível e mantém o caminho anterior para versões antigas do Flask. As versões 5.4.1, 5.5.0, 5.5.1 e 5.6.0 foram conferidas como incompatíveis. A gestão separada de sessão permanece ativa; não foi adotado monkeypatch no aplicativo, nem desativação da revogação. O requisito `python-socketio>=5.12.0` é atendido pela versão 5.17.0 existente, sem nova alteração transitiva.

Fonte oficial: [correção de sessão Flask-SocketIO](https://github.com/miguelgrinberg/flask-socketio/commit/956f8f2847c53d5156620b395912b7c916e15a1b), release 5.6.1 de 21/02/2026, “Session fixes for Flask >= 3.1.3”. A regressão focada posterior passou em 41/41 testes; a suíte final também cobre esses fluxos.

As demais extensões foram preservadas e exercitadas: Flask-SQLAlchemy 3.1.1, Flask-Login 0.6.3, Flask-WTF 1.2.1, Flask-Limiter 3.8.0 e Flask-Migrate 4.0.7. O formato CRLF de `requirements.txt` foi preservado.

Flask 3.1 oferece `MAX_FORM_MEMORY_SIZE` e `MAX_FORM_PARTS`; os padrões são 500.000 bytes para campos multipart não arquivo e 1.000 partes. O limite total NEXO de 20 MiB foi preservado. Os testes usam somente entradas pequenas e limites reduzidos, aceitando CSV/XLSX legítimos e rejeitando excessos sem persistência. Werkzeug 3.1.9 usa `MAX_CONTENT_LENGTH`, e não o orçamento multipart, para corpos URL-encoded. A geração de URL HTTPS com proxy foi verificada. A atualização não substitui as futuras SEC-005 e SEC-010.

## E. CVEs identificados

As versões finais incluem correções para CVE-2026-27205 e CVE-2024-49767. Incluem também cinco avisos Werkzeug dependentes de Windows — CVE-2024-49766, CVE-2025-66221, CVE-2026-21860, CVE-2026-27199 e CVE-2026-102598 — que não se aplicam ao alvo Linux/Python 3.12 avaliado. Não foi presumida exploração em produção.

A auditoria instalada identificou sete CVEs adicionais fora do escopo, relacionados abaixo. A classificação de gravidade não equivale a confirmação de exploração no aplicativo. Nenhum deles foi corrigido ampliando esta tarefa.

| CVE | Biblioteca | Versão afetada observada | Gravidade nas fontes | Aplicabilidade ao NEXO | Recomendação |
| --- | --- | --- | --- | --- | --- |
| [CVE-2025-8869](https://github.com/advisories/GHSA-4xh5-x5gv-qwph) | pip | 25.0.1; GHSA <=25.2; corrigida em 25.3 | Média | Fallback de extração de arquivo durante instalação; o cenário específico do fallback não se aplica ao Python 3.12 com PEP 706. Não é rota HTTP do NEXO. | Revisar tooling de build em tarefa própria; preservar análise da mitigação. |
| [CVE-2026-1703](https://github.com/advisories/GHSA-6vgw-5pg2-w6jp) | pip | 25.0.1; GHSA <26.0; corrigida em 26.0 | Baixa | Depende de processamento de wheel não confiável na instalação. Não foi encontrado fluxo da aplicação que invoque pip por requisição. | Tratar ferramenta de instalação e proveniência de artefatos separadamente. |
| [CVE-2026-3219](https://github.com/advisories/GHSA-58qw-9mgm-455v) | pip | 25.0.1; GHSA <=26.0.1; corrigida em 26.1 | Média | Condicional à instalação de arquivo com interpretação conflitante TAR/ZIP. É risco da cadeia de instalação, sem caminho HTTP identificado no NEXO; exploração no build/produção não confirmada. | Avaliar atualização do tooling e controles de build em tarefa própria. |
| [CVE-2026-6357](https://github.com/advisories/GHSA-jp4c-xjxw-mgf9) | pip | 25.0.1; GHSA <26.1; corrigida em 26.1 | Média | Condicional à instalação de wheel com módulos importados pela verificação de autoatualização do pip; não envolve a requisição Flask normal. Exploração no build/produção não confirmada. | Revisar fluxo de build e ferramenta sem ampliar esta SEC-006. |
| [CVE-2026-8643](https://github.com/advisories/GHSA-wf93-45jw-7689) | pip | 25.0.1; GHSA <26.1.2; corrigida em 26.1.2 | **Alta pela faixa CVSS 3.1 8,0; campo textual GHSA medium** | Travessia de diretório em nomes de entry points ao instalar artefato malicioso. É risco da cadeia de instalação; nenhum caminho de exploração imediata no runtime NEXO foi demonstrado. | Priorizar revisão separada do tooling, registrar a divergência de classificação e verificar a origem dos artefatos. |
| [CVE-2026-13346](https://github.com/advisories/GHSA-qwm4-qh6w-59xr) | pip | 25.0.1; GHSA <26.2.0; corrigida em 26.2.0 | Média | Requer índice malicioso e URLs duplamente codificadas; pacote malicioso sozinho não basta. O advisory destaca pip download --only-binary. As instalações candidatas usaram PyPI oficial; o build real não foi acessado. | Rever tooling e proveniência de build em tarefa específica. |
| [CVE-2026-28684](https://github.com/advisories/GHSA-mf9w-mj56-hr94) | python-dotenv | 1.0.1; GHSA <1.2.2; corrigida em 1.2.2 | Média, CVSS 3.1 6,6 | Depende de escrita por `set_key`/`unset_key` e condições locais de filesystem. O NEXO pesquisado usa `load_dotenv`, sem chamadas diretas às funções vulneráveis. A automação operacional externa não foi auditada. | Revisar escrita de configuração e atualizar em tarefa própria. |

A reconsulta dos sete GHSAs foi concluída em 23/10/2026 pela API oficial, sem falha de acesso. A auditoria instalada foi renovada nesta execução: 65 distribuições, 14 registros brutos da fonte, sete CVEs únicos em dois pacotes, nenhuma distribuição ignorada ou erro de coleta. A auditoria final dos três pacotes atualizados retornou zero avisos conhecidos. A auditoria completa retornou exit code 1 pelos sete CVEs residuais, sem erro de acesso à fonte nem distribuição ignorada. Não é correto descrever todo o ambiente como livre de avisos. A reavaliação não demonstrou vulnerabilidade crítica ou alta explorável no NEXO com risco imediato que, por si só, impedisse a publicação da correção em branch.

## F. Testes locais

O prompt atual exige nova execução; os resultados históricos não substituem essa validação. A suíte completa e os dois módulos PostgreSQL foram reexecutados nesta etapa com os arquivos finais. Os resultados novos estão separados do histórico anterior.

| Execução | Total | Aprovados | Falhas | Erros | Ignorados | Tempo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base original, suíte geral | 315 | 315 | 0 | 0 | 0 | 63,605 s |
| Base original, tokens e sessões PostgreSQL | 78 | 78 | 0 | 0 | 0 | 14,741 s |
| Primeira candidata, extensão Socket.IO antiga | 334 | 310 | 0 | 24 | 0 | 67,710 s |
| Candidata final anterior, suíte geral | 334 | 334 | 0 | 0 | 0 | 69,334 s |
| Candidata final anterior, tokens e sessões PostgreSQL | 78 | 78 | 0 | 0 | 0 | 13,985 s |
| **Nova execução, suíte geral com navegador e Gunicorn** | **334** | **334** | **0** | **0** | **0** | **69,480 s** |
| **Nova execução, PostgreSQL tokens** | **37** | **37** | **0** | **0** | **0** | **6,268 s** |
| **Nova execução, PostgreSQL revogação de sessões** | **41** | **41** | **0** | **0** | **0** | **7,991 s** |

A nova execução totalizou **412 testes aprovados**, sem falhas, erros ou testes ignorados: 334 da suíte geral e 78 dos módulos PostgreSQL separados. Os dois módulos PostgreSQL somaram 14,259 s de execução (6,268 + 7,991 s); essa soma não é medição de um único comando conjunto. Logs novos: `/tmp/nexo-sec006-publication-full.log` e os registros separados dos módulos de tokens e sessões.

Na preparação anterior, sete métodos de probes puros nas versões antigas reproduziram os defeitos em três métodos, com cinco registros de falha do runner: quatro subtestes de acesso à sessão e um de orçamento acumulado multipart. Os novos testes passaram nas versões finais. Isso não representa falha pendente da candidata final.

Comandos da nova execução, usando exclusivamente a virtualenv descartável e recursos sintéticos:

```bash
/tmp/nexo-sec006-validation/bin/python -B -m pip --isolated --no-cache-dir check

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
/tmp/nexo-sec006-validation/bin/python -B -m unittest discover -s tests -t . -v

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
/tmp/nexo-sec006-validation/bin/python -B -m unittest tests.postgresql_auth_tokens -v

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
/tmp/nexo-sec006-validation/bin/python -B -m unittest tests.postgresql_session_revocation -v

git -c core.whitespace=cr-at-eol diff --check
```

A suíte geral cobre os 18 novos testes Flask/Werkzeug e o teste Gunicorn/WSGI, além das regressões de SEC-001/002/003, CSRF, rate limiting, autenticação, ativação, recuperação, primeiro acesso, sessões antigas/múltiplos dispositivos, `BOOT_ID`, handshake e revogação Socket.IO, notificações isoladas, portais, API/visual do NexoBot, navegador, templates, PDF, ETL e dashboards. Os módulos PostgreSQL separados exercitam concorrência e travas reais em cluster privado. Os testes focados já estão incluídos nos totais gerais e não devem ser somados novamente.

O cluster não aceita servidor existente: ambiente filtrado, socket Unix privado e nenhuma interface TCP. O ensaio Gunicorn usa somente loopback, segredo descartável, `.env` desabilitado e armazenamento temporário. Nenhum teste conectou ao Supabase ou Render reais.

## G. GitHub Actions

O workflow existente `.github/workflows/nexo-security-ci.yml` foi preservado. Os jobs esperados são `security-sqlite-browser` e `security-postgresql`. Execuções da nova Pull Request: pendentes de criação da PR e execução nesta etapa. Nenhum resultado local ou de PR anterior está sendo apresentado como aprovação da CI atual. Os links e conclusões reais deverão ser registrados após consulta da execução correspondente ao commit publicado.

## H. Arquivos modificados

Conjunto exclusivo da SEC-006 proposto para commit:

| Arquivo | Conteúdo |
| --- | --- |
| `requirements.txt` | Três pins atualizados; CRLF preservado. |
| `tests/test_dependency_security_compat.py` | 18 testes de sessão, `Vary`, limites multipart, formulários, CSRF, CSV/XLSX e proxy. |
| `tests/test_dependency_wsgi_runtime.py` | Gunicorn/WSGI com PostgreSQL privado e cookies seguros. |
| `Docs/RELATORIO_NEXO_SEC006_DEPENDENCIAS.md` | Relatório A–M, testes, CVEs, publicação e limitações. |
| `Docs/AUDITORIA_DEPENDENCIAS_SEC006.md` | Metadata, fontes, hashes e análise dos avisos. |

Não fazem parte do commit: ZIP, patch externo, inventários de validação, logs, `.env`, credenciais, bancos, backups, virtualenvs, caches ou dados de clientes. As correções anteriores, configurações de produção, workflow e funcionalidades do NEXO permanecem preservados.

## I. Publicação no GitHub

| Item | Estado deste registro pré-publicação |
| --- | --- |
| Branch | `security/sec-006-dependency-updates`, local |
| Commit SEC-006 | Pendente de criação nesta etapa; nenhum SHA novo é declarado neste registro. |
| Push | Pendente de execução nesta etapa. |
| Pull Request | Pendente de abertura nesta etapa; não há URL real a declarar ainda. |
| Título autorizado | `fix(security): NEXO-SEC-006 - atualização segura de dependências` |
| Merge | Não executado; condicionado a todas as verificações e à ausência comprovada de deploy automático não autorizado. |
| SHA de merge | Não existe nesta etapa. |
| `main` | Não modificada por esta execução. |

O proprietário autorizou expressamente commit, push, PR e acompanhamento/correção de CI. A condição de merge é diferente de uma autorização pendente: falta comprovar o comportamento efetivo do Render. Não se deve confundir a publicação da branch com integração à `main`, nem integração ao GitHub com implantação em produção.

## J. Render e Supabase

Nenhum deploy manual, alteração de configuração Render, acesso a dados Supabase, migração de produção ou modificação de credencial foi realizado por esta execução. A versão efetivamente implantada em produção não foi validada: o painel Render não foi acessado por integração autorizada disponível nesta sessão.

`render.yaml` declara `autoDeployTrigger: 'off'`, Python 3.12.10, um worker Gunicorn, 50 threads e `wsgi:app`. Esse arquivo não comprova a configuração efetiva do painel. Não foi encontrado workflow de deploy no repositório. As consultas GitHub a recursos administrativos/deployment/hook retornaram limitações de permissão; portanto não forneceram evidência suficiente para descartar um deploy automático no merge.

**Impedimento de merge:** o risco de implantação automática não autorizada não pôde ser descartado com as informações disponíveis. Pelas seções 2 e 14 do prompt atual, a branch e a PR podem ser publicadas normalmente, mas o merge deve permanecer pendente até evidência da configuração efetiva do serviço Render. Nenhuma proteção foi desativada para superar essa limitação.

A compatibilidade foi verificada por metadata e ambiente Linux/Python 3.12.14, não pelo patch exato 3.12.10 ou pela topologia externa Render/Supabase. Gunicorn simulado usa um worker e 50 threads, mas bind loopback e timeout de 20 s frente a 180 s no Render. Os fluxos Socket.IO foram cobertos pelos clientes de teste da extensão e regressões; não houve teste de WebSocket no serviço Render real. Não há migração de banco ou alteração de variável de produção necessária para esta atualização.

## K. Problemas e pendências

- Publicar a branch, abrir uma única Pull Request e acompanhar os dois jobs da CI sobre o commit efetivamente enviado.
- Obter evidência da configuração efetiva do Render antes de realizar merge; o YAML isoladamente é insuficiente.
- Preservar a reavaliação dos sete CVEs fora do escopo, incluindo a divergência de gravidade do CVE-2026-8643. Tratar tooling de build e python-dotenv em tarefa própria.
- A comparação local preservou os transitivos por constraints de teste externas ao repositório. O build normal não fixa todos os transitivos; a CI da publicação deverá validar a resolução efetiva.
- Observar os novos limites padrão de formulários em eventual homologação operacional futura. Dados reais não foram usados nos testes.
- SEC-005 e SEC-010 continuam separadas. A auditoria Python não cobre sistema operacional, CDN JavaScript ou serviços externos.
- A documentação web Pallets retornou CONNECT 403 na pesquisa anterior; changelogs oficiais foram obtidos dos repositórios dos mantenedores pela API GitHub permitida. Não houve contorno de proxy ou alteração de permissões de rede.

## L. Resultado

**CORRIGIDO COM RESSALVAS.**

A implementação existente foi recuperada e revalidada: 334 testes gerais, 37 PostgreSQL de tokens e 41 PostgreSQL de sessões aprovados, sem falhas, erros ou ignorados. A finalização autorizada está em andamento. Este registro pré-publicação não afirma que o commit, a PR ou a CI atual já existam. A integração à `main` permanece impedida enquanto não for possível descartar deploy automático não autorizado no Render. O estado final deverá ser classificado de acordo com as evidências efetivas de publicação e CI obtidas nesta execução.

## M. Resumo para ChatGPT

**RESUMO PARA CHATGPT: SEC-006 FINALIZADA**

- Dependências: Flask 3.0.3 → 3.1.3; Werkzeug 3.0.4 → 3.1.9; Flask-SocketIO 5.4.1 → 5.6.1, esta última por incompatibilidade de sessão comprovada.
- Arquivos: `requirements.txt`, dois novos módulos de teste e os dois relatórios em `Docs/`; cinco arquivos exclusivos da SEC-006.
- Testes novos: suíte geral 334/334 em 69,480 s; PostgreSQL tokens 37/37 em 6,268 s; PostgreSQL sessões 41/41 em 7,991 s; zero falhas, erros ou ignorados. `pip check` passou e os três módulos foram importados da virtualenv isolada nas versões esperadas.
- CVEs restantes: seis no pip 25.0.1 e um no python-dotenv 1.0.1, com aplicabilidade condicional e fontes na seção E; nenhuma atualização adicional foi aplicada.
- Branch publicada: ainda pendente neste registro pré-publicação; branch local `security/sec-006-dependency-updates`, base `f4fd6d31f3ff5eefea534222700623d3e1c3d989`.
- Pull Request e CI: pendentes de execução nesta etapa; nenhum link ou sucesso foi inventado.
- `main`: não alterada por esta execução; merge exige todas as condições do prompt.
- Render: nenhum deploy/configuração alterados; versão em produção não validada e autodeploy efetivo ainda não comprovado como desligado.
- Pendências operacionais: publicar branch/PR, acompanhar CI e comprovar a configuração efetiva do Render antes de integrar.
- Próxima correção recomendada: revisar separadamente tooling de build, incluindo CVE-2026-8643, e python-dotenv conforme exposição operacional; SEC-005/SEC-010 permanecem em tarefas próprias. Não executar deploy ou migração de produção nesta SEC-006.
