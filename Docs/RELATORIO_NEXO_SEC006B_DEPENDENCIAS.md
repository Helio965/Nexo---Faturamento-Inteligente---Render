# NEXO-SEC-006B — dependências e segurança do processo de instalação

Data: 23/10/2026, referência de calendário America/Sao_Paulo. Registro técnico
pré-publicação. A execução está autorizada a criar commit, enviar a branch e
abrir uma Pull Request para revisão; merge na `main`, deploy e alteração do
Render/Supabase reais não fazem parte desta autorização.

## A. Identificação

| Item | Estado |
| --- | --- |
| Projeto | NEXO: Faturamento Inteligente |
| Repositório | `Helio965/Nexo---Faturamento-Inteligente---Render` |
| Diretório | `/workspace/Nexo---Faturamento-Inteligente---Render` |
| Branch | `security/sec-006b-supply-chain-hardening` |
| Base efetiva desta tarefa | `5eb352403d4df7659602047472ab0afcd9540b28` |
| Referência conhecida no pedido | `415466ef2c89fb3e1fbae6dec4ce575a6688923e` |
| Validação | Linux, Python 3.12.14, virtualenvs descartáveis fora do repositório. |
| Ambiente de desenvolvimento/teste | `/tmp/nexo-sec006b-validation` |
| Ensaio do build versionado de runtime | `/tmp/nexo-sec006b-render-build` |

A `main` avançou desde a referência conhecida pelo merge externo da PR
documental #15. A branch desta tarefa partiu do estado atual, preservando as
correções SEC-001, SEC-002, SEC-003 e SEC-006. Os pins Flask 3.1.3, Werkzeug 3.1.9
e Flask-SocketIO 5.6.1 foram mantidos. Nenhuma implementação anterior foi refeita.

## B. Vulnerabilidades

A auditoria anterior encontrou seis CVEs no pip 25.0.1 da virtualenv examinada
e um no python-dotenv 1.0.1 declarado pelo projeto. Pip é ferramenta de
instalação; sua versão local não comprova qual instalador o Render utiliza.
Os sete advisories foram reconsultados em fontes oficiais. As candidatas
selecionadas estão fora de todos os intervalos afetados abaixo.

| CVE e fonte oficial | Biblioteca / intervalo afetado | Primeira correção | Aplicabilidade e gravidade |
| --- | --- | --- | --- |
| [CVE-2025-8869](https://github.com/advisories/GHSA-4xh5-x5gv-qwph) | pip <=25.2 | 25.3 | Média; fallback de extração TAR. A pré-condição específica não se aplica ao Python 3.12 com PEP 706, mas a versão antiga está no intervalo da base de advisories. |
| [CVE-2026-1703](https://github.com/advisories/GHSA-6vgw-5pg2-w6jp) | pip <26.0 | 26.0 | Baixa; processamento de wheel malicioso na instalação. Não foi identificado uso de pip comandado por requisições HTTP do NEXO. |
| [CVE-2026-3219](https://github.com/advisories/GHSA-58qw-9mgm-455v) | pip <=26.0.1 | 26.1 | Média; interpretação conflitante TAR/ZIP na cadeia de instalação. |
| [CVE-2026-6357](https://github.com/advisories/GHSA-jp4c-xjxw-mgf9) | pip <26.1 | 26.1 | Média; instalação de wheel com módulos importados pelo mecanismo de verificação de atualização do pip. |
| [CVE-2026-8643](https://github.com/advisories/GHSA-wf93-45jw-7689) | pip <26.1.2 | 26.1.2 | Campo textual GHSA médio, mas CVSS 3.1 8,0 corresponde à faixa alta. Entry points maliciosos podem escrever scripts fora do destino durante instalação; a divergência de gravidade foi preservada. |
| [CVE-2026-13346](https://github.com/advisories/GHSA-qwm4-qh6w-59xr) | pip <26.2.0 | 26.2.0 | Média; índice malicioso e URLs duplamente codificadas. Pacote malicioso sozinho não basta para o cenário descrito. |
| [CVE-2026-28684](https://github.com/advisories/GHSA-mf9w-mj56-hr94) | python-dotenv <1.2.2 | 1.2.2 | Média, CVSS 3.1 6,6; escrita por `set_key`/`unset_key` e condições locais de filesystem. O NEXO usa `load_dotenv`; a atualização remove a dependência vulnerável sem presumir exploração desse caminho no aplicativo. |

Não foram executados testes de exploração contra produção. A classificação de
gravidade não equivale a confirmação de exploração no NEXO. As versões
efetivamente utilizadas nos ambientes locais estão registradas nas seções C,
D e I; GitHub Actions e Render real têm estados separados.

Fontes adicionais: [metadata PyPI do pip 26.2.2](https://pypi.org/pypi/pip/26.2.2/json),
[metadata PyPI do python-dotenv 1.2.4](https://pypi.org/pypi/python-dotenv/1.2.4/json)
e os documentos individuais GitHub Security Advisories vinculados acima.

## C. Dependências

| Componente | Versão anterior observada | Versão escolhida | Tratamento |
| --- | --- | --- | --- |
| python-dotenv | 1.0.1 | **1.2.4** | Único pin de aplicação alterado em `requirements.txt`. |
| pip | 25.0.1 na virtualenv da auditoria anterior | **26.2.2** | Bootstrap verificado antes dos requisitos; não foi acrescentado a `requirements.txt`. |
| Flask / Werkzeug / Flask-SocketIO | 3.1.3 / 3.1.9 / 5.6.1 | Preservadas | Correções da SEC-006 mantidas. |

As candidatas existem no PyPI oficial, são estáveis, não retiradas e declaram
Python >=3.10, incluindo Python 3.12. Os wheels universais foram baixados e
conferidos com os hashes da metadata oficial. Não foi necessária uma versão
alternativa nem beta/RC.

| Artefato | SHA256 oficial conferido |
| --- | --- |
| `pip-26.2.2-py3-none-any.whl` | `fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70` |
| `python_dotenv-1.2.4-py3-none-any.whl` | `42269a8a5b3fd54ffa6f3d84b18abed50064717576b4ecf03dc4a55d8aa04fdc` |

O ambiente de teste foi instalado de forma limpa, com o resolvedor normal e
sem modificar a virtualenv anterior. Seu inventário contém 66 distribuições;
58 versões foram preservadas em relação ao candidato SEC-006 de 65 distribuições.
Além de pip/python-dotenv, a resolução de requisitos transitivos sem pin
selecionou Alembic 1.20.1, certifi 2026.10.23, jiter 0.18.0,
python-dateutil 3.0.0 e WTForms 3.3.0, e acrescentou tzdata 2026.5. Esses
transitivos não receberam novos pins nem alterações indiscriminadas no
repositório; são diferenças da instalação limpa efetivamente testada e
auditada. Não se afirma que a comparação isola somente duas distribuições.

## D. Processo de instalação

### Diagnóstico

Antes da SEC-006B, os dois jobs de CI executavam `python -m pip install -r
requirements-dev.txt` e o Blueprint Render declarava `pip install -r
requirements.txt`. Esses comandos não fixavam nem verificavam o instalador
antes dos requisitos. O projeto não especificava índice adicional ou
dependência direta por URL Git nesses arquivos. Configurações pip externas, índices e versão fornecida pelo ambiente poderiam
influenciar o build.

Os comandos versionados anteriores não permitem determinar retrospectivamente
a versão exata usada em cada execução histórica do GitHub Actions ou no Render.
A versão conhecida pela auditoria local anterior é pip 25.0.1. O instalador
fornecido pelo Python/ambiente de build pode variar; a versão real do Render
permanece não verificada.

### Estratégia implementada

O novo `tools/install_dependencies.py` é um programa de instalação baseado
somente na biblioteca padrão. Ele não importa a aplicação nem carrega `.env`.
O mesmo comando é utilizado no CI, no build versionado e nos guias locais:

```bash
# Runtime, dentro do ambiente Python de destino.
python -I tools/install_dependencies.py --requirements requirements.txt

# Desenvolvimento e testes, dentro de virtualenv descartável/local.
python -I tools/install_dependencies.py --requirements requirements-dev.txt
```

A sequência executada é:

1. Baixar o wheel pip 26.2.2 do endereço HTTPS exato em
   `files.pythonhosted.org`, com validação TLS e controles de proxy preservados.
2. Recusar redirecionamentos para outra origem, protocolo HTTP, credenciais em
   URL ou porta não permitida; limitar o download a 16 MiB e verificar o SHA256
   fixo antes de executar qualquer código do wheel.
3. Executar o pip corrigido diretamente do wheel verificado, com Python `-I`,
   em vez de solicitar ao pip vulnerável existente que processe o bootstrap.
4. Instalar esse wheel com `--no-index --no-deps --force-reinstall` e confirmar
   a versão instalada por metadata e pelo módulo importado.
5. Somente após a confirmação, instalar os requisitos permitidos do NEXO com
   pip 26.2.2, PyPI oficial e TLS ativo; executar `pip check` no mesmo ambiente.

Falha de hash, download, bootstrap ou confirmação da versão interrompe a
sequência antes da instalação de dependências da aplicação. A opção
`--prepare-only` prepara/verifica o instalador sem instalar os requisitos.

Os processos filhos recebem ambiente filtrado, preservando proxy/TLS do
sistema e variáveis necessárias de plataforma, sem os segredos da aplicação.
`PIP_CONFIG_FILE` aponta para `os.devnull`, juntamente com `--isolated`, para
excluir configuração global/site/usuário e índices herdados. `PYTHONPATH` e
variáveis `PIP_*` herdadas não são repassados; `NETRC` aponta para arquivo vazio
privado e keyring é desabilitado na instalação dos requisitos. Não são usados
`--trusted-host`, índices desconhecidos ou desativação TLS. O Python não é
atualizado ou substituído por esse processo.

O relatório JSON da instalação de teste registra pip 26.2.2 e os artefatos
resolvidos. A frente de auditoria confirmou fontes HTTPS oficiais, SHA256 e
artefatos não retirados nos 65 artefatos instalados nessa etapa; o pip foi
preparado previamente, perfazendo 66 distribuições no inventário instalado.
Hash de origem não demonstra ausência de código malicioso desconhecido no
próprio pacote ou de comprometimento futuro da origem.

## E. GitHub Actions

Nos dois jobs do workflow `.github/workflows/nexo-security-ci.yml`, a instalação
direta com pip foi substituída pelo helper compartilhado, depois da seleção de
Python 3.12 e antes das dependências e testes. O próprio helper confirma
`pip=26.2.2` antes de processar `requirements-dev.txt`.

Foram preservados os nomes `security-sqlite-browser` e `security-postgresql`,
os jobs, os comandos das suítes gerais/navegador/PostgreSQL, o ensaio de backup,
os SHAs das actions e a permissão mínima `contents: read`. Nenhum segredo real
foi acrescentado nem teste desativado. O novo teste de instalador verifica
também o pip efetivamente importado e seu código vendorizado no Python de
destino; os contratos YAML exigem a ordem de preparação antes dos testes.

Estado neste registro pré-publicação: workflow preparado e validado localmente;
execução GitHub Actions desta SEC-006B ainda pendente da abertura da PR. Não se
declara o pip da CI corrigido apenas por ter alterado o YAML. Os resultados e
links reais serão registrados após a execução do commit publicado.

## F. Render

O `buildCommand` versionado em `render.yaml` passa a executar o mesmo helper
com `requirements.txt`. O comando foi executado em uma segunda virtualenv
descartável, `/tmp/nexo-sec006b-render-build`, com Python 3.12.14. Pip 26.2.2 foi
preparado antes dos requisitos de runtime e o `pip check` concluiu sem conflitos.
O inventário e a auditoria independentes desse ensaio confirmaram 62 distribuições
instaladas, incluindo pip 26.2.2 e python-dotenv 1.2.4, zero avisos conhecidos,
nenhuma distribuição ignorada e exit 0. O relatório da instalação registrou 61
artefatos de runtime, todos HTTPS oficiais com SHA256 e não retirados; pip foi
preparado antes e é a 62ª distribuição auditada. Esses dados não são inferidos
a partir do ambiente de desenvolvimento.

Os testes de contrato validam a sintaxe YAML e preservam Python 3.12.10,
Gunicorn com um worker/50 threads, timeout 180 s, `wsgi:app`, `/healthz` e
`autoDeployTrigger: 'off'` no arquivo. O suporte a Python 3.12 é demonstrado por
metadata e execução local 3.12.14; o patch exato 3.12.10 e a infraestrutura real
Render/Supabase não foram executados.

O comando efetivo configurado diretamente no painel pode divergir do Blueprint.
O proprietário informou anteriormente Auto-Deploy ativado; o YAML não é prova
do estado atual do painel. Nenhuma leitura ou alteração do painel, deploy,
acesso ao Supabase, migração de produção ou mudança de credenciais foi realizada
nesta SEC-006B. A atualização do ambiente Render real permanece **não
comprovada**. A adoção futura do build, integração à `main` e implantação exigem
revisão e autorização posterior, fora desta execução.

## G. Arquivos modificados

Conjunto local da SEC-006B previsto para revisão e commit:

| Arquivo | Alteração e justificativa |
| --- | --- |
| `requirements.txt` | python-dotenv 1.0.1 → 1.2.4; pins SEC-006 preservados, sem adicionar pip ao runtime. |
| `tools/install_dependencies.py` | Bootstrap pip fixo/verificado, confirmação de versão e instalação controlada de requisitos. |
| `.github/workflows/nexo-security-ci.yml` | Helper compartilhado nos dois jobs, antes dos requisitos e testes. |
| `render.yaml` | Preparação do build versionado com o helper; sem mudar painel ou contrato de runtime. |
| `tests/test_supply_chain_install.py` | 15 testes de hash, origem, ambiente, ordem/falhas, pip efetivo e contratos CI/Render. |
| `tests/test_dotenv_security_compat.py` | 12 testes de leitura, precedência, escrita atômica e configuração isolada do NEXO. |
| `tests/test_nexobot_navegador.py` | Somente instrução de instalação no docstring, sem alterar o teste funcional. |
| `README.md` | Instalação local pelo helper e atualização da referência ao build Python. |
| `Docs/CI_SEGURANCA.md` | Procedimento de CI/reprodução com instalador verificado. |
| `Docs/PREPARACAO_RENDER.md` | Build seguro preparado e distinção do painel real/Auto-Deploy. |
| `Docs/NEXOBOT_ADVANCED.md` | Instalação das dependências de teste pelo mesmo helper; sem mudança funcional no NexoBot. |
| `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md` | Registro exclusivamente documental das duas futuras correções. |
| `Docs/RELATORIO_NEXO_SEC006B_DEPENDENCIAS.md` | Este relatório técnico A–N, evidências, limitações e estado da publicação. |

Nenhuma mudança foi feita em `config.py`, blueprints de autenticação/admin,
`etl_processor.py`, mecanismos de sessão/notificação, modelos, migrações,
PDF, visual ou vídeo. A lógica comercial foi preservada. Artefatos de auditoria,
logs, relatórios pip, virtualenvs e arquivos temporários permanecem fora do Git.

## H. Testes

Os resultados históricos da SEC-006 não são utilizados como se fossem desta
execução. A nova validação aprovou **439 testes**: 361 gerais e 78 PostgreSQL
(37 tokens e 41 sessões), sem falhas, erros ou testes ignorados. Os módulos
PostgreSQL foram executados separadamente; 14,479 s é a soma de seus tempos
(6,292 + 8,187 s), não medição de um comando conjunto. Os testes focados abaixo
foram executados no ambiente candidato e estão incluídos na suíte completa;
não devem ser somados novamente ao total.

| Execução | Total | Aprovados | Falhas | Erros | Ignorados | Tempo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Testes do instalador/contratos | 15 | 15 | 0 | 0 | 0 | 0,104 s |
| Testes de dotenv/configuração | 12 | 12 | 0 | 0 | 0 | 2,875 s |
| Reprodução na versão antiga dotenv 1.0.1 | 1 método | 0 | 2 subtestes esperados | 0 | 0 | 0,002 s |
| Nova suíte completa, navegador e PostgreSQL habilitados | 361 | 361 | 0 | 0 | 0 | 72,339 s |
| Novo PostgreSQL: tokens | 37 | 37 | 0 | 0 | 0 | 6,292 s |
| Novo PostgreSQL: sessões | 41 | 41 | 0 | 0 | 0 | 8,187 s |

O probe de escrita modela uma falha `EXDEV` com symlink apenas dentro de
diretório temporário privado: na versão antiga, os subtestes `set`/`unset`
reproduzem o fallback vulnerável; na versão nova, o alvo permanece intacto e
a falha é controlada. Não houve escrita em arquivo `.env` real, outro
filesystem ou serviço externo. As demais verificações exercitam precedência
do ambiente, interpolação, Unicode, permissões de arquivo regular e
inicialização desenvolvimento/teste/produção simulada sem expor segredos.

Os testes do instalador simulam downloads/processos para verificar recusa de
hash incorreto, origem indevida, tamanho excessivo e falha de versão antes dos
requisitos. A instalação real ocorreu somente nos ambientes descartáveis. O
probe de pip efetivo confirma metadata/módulo e origem do código vendorizado.

Comandos de referência desta execução, a partir da raiz do repositório:

```bash
# Bootstrap e instalação limpa do ambiente de desenvolvimento/teste.
/tmp/nexo-sec006b-validation/bin/python -I tools/install_dependencies.py \
  --requirements requirements-dev.txt --report /tmp/nexo-sec006b-install-report.json

# Build versionado de runtime, em outra virtualenv descartável.
/tmp/nexo-sec006b-render-build/bin/python -I tools/install_dependencies.py \
  --requirements requirements.txt --report /tmp/nexo-sec006b-render-install-report.json

/tmp/nexo-sec006b-validation/bin/python -B -m unittest \
  tests.test_supply_chain_install -v
/tmp/nexo-sec006b-validation/bin/python -B -m unittest \
  tests.test_dotenv_security_compat -v

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
NEXO_TEST_BROWSER=1 NEXO_TEST_CHROMIUM=/usr/bin/chromium \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest discover -s tests -t . -v

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest \
  tests.postgresql_auth_tokens -v

NEXO_TEST_POSTGRES_BIN=/tmp/nexo-pg17-tools/usr/lib/postgresql/17/bin \
/tmp/nexo-sec006b-validation/bin/python -B -m unittest \
  tests.postgresql_session_revocation -v

git -c core.whitespace=cr-at-eol diff --check
```

O conjunto existente verifica login/logout, recuperação, ativação, primeiro
acesso, tokens, revogação HTTP/Socket.IO, notificações isoladas, CSRF, limiter,
uploads, ETL, dashboards, PDF, NexoBot, navegador, WSGI, health checks e produção
simulada. PostgreSQL é privado e descartável; nenhum teste aceita uma URL de
servidor de produção. Gunicorn e a configuração de produção simulada são
exercitados pelas regressões existentes, preservando as proteções anteriores.

## I. Auditoria posterior

`pip-audit 2.10.1` foi executado em uma virtualenv de análise separada. Não foram
usados `--fix`, `--ignore-vuln`, omissão silenciosa do pip ou resolução por
instalador vulnerável no ambiente candidato. Os escopos foram separados:

| Auditoria | Escopo efetivo | Resultado conhecido neste registro |
| --- | --- | --- |
| Candidatas diretas | pip 26.2.2 e python-dotenv 1.2.4, sem resolvedor/deps | Duas distribuições, zero avisos, exit 0. |
| Requisitos declarados de runtime | 18 dependências diretas fixadas, sem expandir transitivos | Zero avisos, exit 0. Pip não está nesse arquivo e é verificado separadamente. |
| Requisitos exclusivos de desenvolvimento | PyYAML e Playwright, dois pins | Zero avisos, exit 0. |
| União dos requisitos declarados | 20 pins diretos, runtime e desenvolvimento | Zero avisos, exit 0. Não equivale à auditoria de transitivos instalados. |
| Ambiente de desenvolvimento instalado | 66 distribuições, incluindo pip 26.2.2 e transitivos efetivos | Zero avisos, sem distribuição ignorada ou erro de coleta. |
| Runtime instalado no ensaio de build | 62 distribuições, incluindo pip 26.2.2 e transitivos efetivos | Zero avisos, nenhuma distribuição ignorada/erro de coleta, exit 0. |

As auditorias de requisitos declarados usaram entradas exatas e sem expansão
de dependências; a auditoria instalada cobriu os transitivos efetivamente
resolvidos. As consultas aos sete advisories oficiais e aos intervalos foram
feitas separadamente, evitando concluir ausência de avisos por falha de busca.

Comandos de auditoria executados pela frente de pesquisa:

```bash
# Exemplo do escopo instalado de desenvolvimento; ferramenta em venv separada.
/tmp/nexo-sec006-audit-env/bin/python -B -m pip_audit \
  --path /tmp/nexo-sec006b-validation/lib/python3.12/site-packages \
  --strict --cache-dir /tmp/nexo-sec006b-research/audit-cache \
  --format json --aliases on --desc off --progress-spinner off \
  --output /tmp/nexo-sec006b-research/installed-development-audit.json

# Pins declarados, sem resolver transitivos; usar também os arquivos de escopo separado.
/tmp/nexo-sec006-audit-env/bin/python -B -m pip_audit \
  --disable-pip --no-deps --strict \
  -r /tmp/nexo-sec006b-research/declared-all-requirements.txt \
  --cache-dir /tmp/nexo-sec006b-research/audit-cache \
  --format json --aliases on --desc off --progress-spinner off \
  --output /tmp/nexo-sec006b-research/declared-all-audit.json
```

### Comprovação por aviso e ambiente

| CVE | Versão anterior | Versão corrigida efetiva nos ambientes locais | Ambiente avaliado | Resultado |
| --- | --- | --- | --- | --- |
| CVE-2025-8869 | pip 25.0.1 | pip 26.2.2 | Desenvolvimento e build de runtime simulados | Fora do intervalo afetado; cenário de fallback também depende de Python/PEP 706. |
| CVE-2026-1703 | pip 25.0.1 | pip 26.2.2 | Desenvolvimento e build de runtime simulados | Fora do intervalo afetado. |
| CVE-2026-3219 | pip 25.0.1 | pip 26.2.2 | Desenvolvimento e build de runtime simulados | Fora do intervalo afetado. |
| CVE-2026-6357 | pip 25.0.1 | pip 26.2.2 | Desenvolvimento e build de runtime simulados | Fora do intervalo afetado. |
| CVE-2026-8643 | pip 25.0.1 | pip 26.2.2 | Desenvolvimento e build de runtime simulados | Fora do intervalo afetado; divergência GHSA textual/CVSS registrada. |
| CVE-2026-13346 | pip 25.0.1 | pip 26.2.2 | Desenvolvimento e build de runtime simulados | Fora do intervalo afetado; PyPI oficial utilizado. |
| CVE-2026-28684 | python-dotenv 1.0.1 | python-dotenv 1.2.4 | Pin declarado e ambientes locais instalados | Fora do intervalo afetado; probe sintético reproduz defeito antigo e aprova versão nova. |

Os cinco resultados operacionais não são equivalentes:

| Camada | Evidência / limite |
| --- | --- |
| Dependência declarada | `requirements.txt` passou a python-dotenv 1.2.4; pip é controlado pelo helper, fora desse arquivo. |
| Virtualenvs locais | Pip 26.2.2 e dotenv 1.2.4 instalados pelo helper; versão do instalador confirmada antes dos requisitos e `pip check` aprovado. |
| GitHub Actions | Workflow preparado para o mesmo helper e teste de versão efetiva; execução real desta PR ainda pendente neste registro. |
| Build versionado para Render | Comando preparado e executado em ambiente local independente; não é execução na plataforma Render. |
| Render real | Comando efetivo, versões, build e runtime não acessados; nenhuma vulnerabilidade marcada como corrigida em produção. |

### Riscos residuais e limites da auditoria

- Zero avisos é uma fotografia das bases consultadas em 23/10/2026, não prova de
  ausência de falhas desconhecidas, comprometimento da origem ou avisos futuros.
- O hash fixo protege o bootstrap do pip. O projeto ainda não mantém lockfile
  completo nem hashes fixos de todos os transitivos; versões transitivas podem
  variar entre builds. A resolução real da CI deverá ser validada na PR.
- Os hashes e a origem dos artefatos do ambiente desta execução foram
  registrados; isso não transforma todos os futuros downloads em artefatos
  bloqueados por hash no repositório.
- A auditoria instalada inclui a distribuição pip. Dependências vendorizadas
  do pip não aparecem automaticamente como distribuições independentes; sua
  presença no wheel verificado não demonstra auditoria separada de cada código
  vendorizado.
- Sistema operacional, pacotes APT, Chromium, CDN JavaScript e infraestrutura
  externa não são abrangidos pela auditoria Python desta tarefa.
- A virtualenv anterior e ambientes de terceiros não são atualizados pelo
  commit. Sua adequação depende da adoção explícita do novo procedimento.

## J. Pendências SEC-004 e SEC-005

Foi criado `Docs/PENDENCIAS_SEGURANCA_SEC004_SEC005.md`, exclusivamente
documental, com duas seções independentes e o status **PENDENTE, NÃO IMPLEMENTAR
AGORA**. O registro contém data, base, trechos reais, gravidade preliminar,
arquivos envolvidos, dependências técnicas e critérios de aceitação futuros.

- SEC-004: restauração de empresas pode reativar usuários anteriormente
  desativados; `blueprints/admin.py`, rota `empresa_restaurar` e laço
  `for u in empresa.usuarios: u.ativo = True`. A solução futura deverá preservar
  estado anterior, histórico, permissões e bloqueio enquanto estiver na lixeira;
  eventual migração exige planejamento e testes próprios.
- SEC-005: orçamento de processamento XLSX/CSV; `etl_processor.py`, leitura
  `pd.read_excel(..., sheet_name=None)`. A tarefa futura deverá considerar
  expansão, abas, linhas, colunas, células, memória, tempo e erros seguros,
  preservando faturamento, indicadores e Curva ABC.

Nenhuma das duas correções foi implementada. Não foram alterados `admin.py`,
`etl_processor.py`, modelos, schema ou migrações. Limites HTTP/multipart não
foram apresentados como solução do orçamento ETL.

## K. Publicação no GitHub

| Item | Estado pré-publicação deste registro |
| --- | --- |
| Branch exclusiva | `security/sec-006b-supply-chain-hardening`, local. |
| Commit-base | `5eb352403d4df7659602047472ab0afcd9540b28` |
| Commit SEC-006B | Ainda não criado nesta etapa; não há SHA novo a declarar. |
| Push | Ainda não realizado nesta etapa. |
| Pull Request | Ainda não aberta nesta etapa; sem URL fictícia. |
| Título previsto | `fix(security): SEC-006B - corrigir dependências e fortalecer instalação` |
| Merge / deploy | Não realizados; integração à `main` e implantação dependem de autorização posterior. |

O plano de publicação autorizado é revisar o diff/arquivos novos e a ausência
de segredos, criar commits exclusivos da SEC-006B, enviar somente essa branch e
abrir uma PR para revisão, preferencialmente em rascunho. Não é necessário
solicitar nova autorização para essas operações já autorizadas. A PR deverá
permanecer disponível para revisão, mesmo se a CI passar. Não será executado
merge, force push, exclusão de branch ou alteração de painel Render.

### Critérios de suspensão e rollback

Se houver regressão, falha de hash/versão, conflito de dependências ou CI
reprovada, suspender a proposta de integração e corrigir a causa na branch da
SEC-006B, com nova verificação pertinente. Não remover testes ou proteções para
aprovar o build, nem substituir a versão validada por intervalo aberto.

Uma reversão futura deve ser revisada e autorizada separadamente, considerar
o estado efetivo do instalador e do build e evitar reintroduzir versões
vulneráveis sem tratamento/decisão explícita. Reverter código não reverte
automaticamente o pip já instalado nem o estado de produção. Esta tarefa não
executa rollback, migração, alteração do painel ou comando em produção.

## L. GitHub Actions

Execuções reais da nova PR SEC-006B: **ainda pendentes de publicação neste
registro**. Não se utilizam a CI da SEC-006, execuções da base ou testes locais
como aprovação da PR atual. Após a criação, consultar a execução associada ao
SHA efetivamente enviado e os resultados de `security-sqlite-browser` e
`security-postgresql`.

Se a CI apresentar falha relacionada à SEC-006B, examinar os logs disponíveis,
corrigir a causa, executar a verificação local pertinente, publicar o commit
complementar e acompanhar a nova execução. Aprovação da CI não autoriza merge
ou deploy nesta tarefa.

## M. Resultado final

**CORRIGIDO LOCALMENTE E PREPARADO PARA PUBLICAÇÃO, COM RESSALVAS OPERACIONAIS.**

Registro pré-publicação: a branch/PR e a execução de CI desta SEC-006B ainda
serão criadas; não há alegação de integração ou implantação.

As sete vulnerabilidades foram reavaliadas; python-dotenv foi atualizado para
1.2.4 e o instalador compartilhado prepara/verifica pip 26.2.2 antes dos
requisitos. O ambiente de desenvolvimento instalado e os requisitos diretos
auditados não apresentaram avisos conhecidos. As novas execuções aprovaram
361 testes gerais, 37 PostgreSQL de tokens e 41 PostgreSQL de sessões, sem
falhas, erros ou ignorados. A auditoria independente do runtime local simulado
cobriu 62 distribuições, incluindo pip, também com zero avisos. Publicação e
resultados reais da CI da PR devem ser acrescentados após sua execução.

O build versionado para Render foi preparado e testado localmente, sem
alteração do painel real ou alegação de correção em produção. SEC-004 e SEC-005
foram apenas documentadas. Permanecem as limitações de produção, de resolução
de transitivos sem lockfile completo e de abrangência da auditoria Python.

## N. Resumo para ChatGPT

**RESUMO PARA CHATGPT: NEXO-SEC-006B**

- Sete avisos analisados: CVE-2025-8869, CVE-2026-1703, CVE-2026-3219,
  CVE-2026-6357, CVE-2026-8643, CVE-2026-13346 e CVE-2026-28684, com fontes
  oficiais e aplicabilidade na seção B.
- Versões selecionadas: pip 26.2.2 e python-dotenv 1.2.4; hashes dos wheels
  conferidos. Flask 3.1.3, Werkzeug 3.1.9 e Flask-SocketIO 5.6.1 preservados.
- Correção efetiva local: instalador corrigido executado do wheel verificado
  antes dos requisitos, versão confirmada e `pip check` aprovado nos ambientes
  descartáveis de desenvolvimento e build de runtime. Não incluir pip
  simplesmente em `requirements.txt` como substituto dessa preparação.
- Arquivos: helper, pin dotenv, CI, build versionado, dois novos módulos de
  teste, guias de instalação, este relatório e registro das futuras SEC-004/005;
  tabela completa na seção G.
- Testes focados: instalador 15/15 em 0,104 s; dotenv 12/12 em 2,875 s.
  Reprodução segura na versão antiga: um método com dois subtestes de falha
  esperada em 0,002 s. Nova suíte geral 361/361 em 72,339 s; PostgreSQL tokens
  37/37 em 6,292 s e sessões 41/41 em 8,187 s; 439 testes aprovados no total,
  zero falhas, erros ou ignorados.
- Auditoria: candidatas diretas 2/2, runtime declarado 18, desenvolvimento
  declarado 2, união direta 20 e ambiente de desenvolvimento instalado 66
  distribuições e runtime local simulado 62 distribuições, todos com zero
  avisos conhecidos nos respectivos escopos. Nenhuma omissão silenciosa do pip.
- GitHub: branch local `security/sec-006b-supply-chain-hardening`, base
  `5eb352403d4df7659602047472ab0afcd9540b28`; commit, push, URL real da PR e CI
  ainda pendentes neste registro. Nenhum resultado publicado foi inventado.
- Render: build versionado preparado; painel efetivo, versões e implantação
  reais não verificados. Nenhum merge, deploy ou alteração de produção
  autorizado/realizado pela SEC-006B.
- SEC-004 e SEC-005: **PENDENTES, APENAS DOCUMENTADAS**, sem implementação
  funcional em admin, ETL ou schema.
- Próxima ação: concluir evidências, publicar branch/PR e acompanhar os dois
  jobs da CI; manter a PR para revisão do proprietário, sem merge ou deploy.
