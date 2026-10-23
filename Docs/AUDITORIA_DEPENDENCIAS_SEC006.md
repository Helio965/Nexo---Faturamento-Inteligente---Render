# Auditoria de dependências — NEXO-SEC-006

Consulta em 23/10/2026. Este documento descreve pesquisa e auditoria local;
não confirma execução de produção nem substitui os testes de integração.
Não foram alterados arquivos do repositório, a virtualenv existente, GitHub ou
serviços de produção por esta frente de pesquisa.

## Escolha de versões e origem

PyPI oficial confirmou **Flask 3.1.3** e **Werkzeug 3.1.9** como versões estáveis
mais recentes na consulta. Ambos têm `Requires-Python >=3.9`, incluem Python
3.12 e disponibilizam wheel universal Python 3, não retirado (yanked=false).
Não houve necessidade de beta/RC. A validação real identificou incompatibilidade
da extensão Flask-SocketIO 5.4.1, mesmo com resolução e pip check aprovados; a
menor atualização compatível é 5.6.1, documentada abaixo. Os resultados dos testes
da aplicação pertencem à frente principal e não são inferidos pela auditoria.

| Biblioteca | Declarada / instalada na base | Recomendada | Compatibilidade por metadata |
| --- | --- | --- | --- |
| Flask | 3.0.3 / 3.0.3 | 3.1.3 | Python>=3.9; requer Werkzeug>=3.1, ItsDangerous>=2.2, Blinker>=1.9, Jinja2>=3.1.2, Click>=8.1.3, MarkupSafe>=2.1.1 |
| Werkzeug | 3.0.4 / 3.0.4 | 3.1.9 | Python>=3.9; MarkupSafe>=2.1.1 |
| Flask-SQLAlchemy | 3.1.1 / 3.1.1 | Preservar | Flask>=2.2.5 e SQLAlchemy>=2.0.16; sem teto incompatível declarado |
| Flask-Login | 0.6.3 / 0.6.3 | Preservar | Flask>=1.0.4 e Werkzeug>=1.0.1; sem teto incompatível declarado |
| Flask-WTF | 1.2.1 / 1.2.1 | Preservar | Flask, ItsDangerous, WTForms; sem teto incompatível declarado |
| Flask-Limiter | 3.8.0 / 3.8.0 | Preservar | Flask>=2 e limits>=3.13; sem teto Flask incompatível declarado |
| Flask-SocketIO | 5.4.1 / 5.4.1 | 5.6.1, ajuste mínimo de compatibilidade | Python>=3.8; Flask>=2.1.0 e python-socketio>=5.12.0; corrige sessão Flask>=3.1.3 |
| Flask-Migrate | 4.0.7 / 4.0.7 | Preservar | Flask>=0.9, Flask-SQLAlchemy>=1 e Alembic>=1.9 |

Transitivos já instalados na base e suficientes aos novos mínimos: Jinja2
3.1.6, ItsDangerous 2.2.0, Click 8.5.0, Blinker 1.9.0 e MarkupSafe 3.0.4.
Compatibilidade declarada pelo resolvedor não prova ausência de regressões.

Fontes oficiais:

- https://pypi.org/pypi/Flask/3.1.3/json
- https://pypi.org/pypi/Werkzeug/3.1.9/json
- https://pypi.org/pypi/Flask-SocketIO/5.6.1/json
- https://github.com/miguelgrinberg/flask-socketio/commit/956f8f2847c53d5156620b395912b7c916e15a1b
- https://github.com/pallets/flask/blob/3.1.3/CHANGES.rst
- https://github.com/pallets/werkzeug/blob/3.1.9/CHANGES.rst

SHA256 do wheel Flask: `f4bcbefc124291925f1a26446da31a5178f9483862233b23c0c96a20701f670c`.
SHA256 do wheel Werkzeug: `6392e50c78460ba618e5b21f08a71f59c99ce99cdc6cf6e3dd7e6ccca8754fab`.
A conferência posterior do relatório de instalação do pip confirmou que os
hashes registrados para os três wheels baixados de files.pythonhosted.org são
iguais à metadata oficial PyPI e que os artefatos não foram retirados. Essa
verificação não substitui os testes de integração. O manifesto sanitizado
contém os hashes e o resultado da comparação, além dos sdists oficiais.

## Avisos no escopo

| Aviso | Afeta a base | Correção conhecida | Aplicabilidade ao NEXO |
| --- | --- | --- | --- |
| CVE-2026-27205 / GHSA-68rp-wp8r-4726 | Flask<3.1.3, inclui 3.0.3 | Flask 3.1.3 | Operações somente sobre chaves de sessão podem omitir Vary:Cookie. Exploração depende de cache/proxy, cabeçalhos e fluxo de sessão; essas condições não foram comprovadas na produção. |
| CVE-2024-49767 / GHSA-q34m-jh98-gwm2 | Werkzeug>=2.0.0rc1 e<=3.0.5 | Werkzeug 3.0.6 | Multipart é utilizado pelo aplicativo; orçamento de campos pode ser contornado na versão antiga. MAX_CONTENT_LENGTH é limite adicional e não torna o bug corrigido. |
| CVE-2024-49766 / GHSA-f9vj-2wh5-fj8j | Werkzeug<=3.0.5 | Werkzeug 3.0.6 | Pré-condição Windows e Python<3.11; não se aplica ao alvo Linux/Python 3.12 avaliado. |
| CVE-2025-66221 / GHSA-hgf8-39gv-g3f2 | Werkzeug<3.1.4 | Werkzeug 3.1.4 | Nomes especiais de dispositivos Windows; não se aplica ao alvo Linux. |
| CVE-2026-21860 / GHSA-87hc-h4r5-73f7 | Werkzeug<3.1.5 | Werkzeug 3.1.5 | Variação de nomes especiais Windows; não se aplica ao alvo Linux. |
| CVE-2026-27199 / GHSA-29vq-49wr-vm6x | Werkzeug<3.1.6 | Werkzeug 3.1.6 | Variação de caminhos Windows; não se aplica ao alvo Linux. |
| CVE-2026-102598 / GHSA-g6x2-hccm-hh4m | Werkzeug<3.1.9 | Werkzeug 3.1.9 | Nomes de dispositivos Windows/NTFS; não se aplica ao alvo Linux. |

Todas as correções acima estão incluídas nas candidatas. Não foi presumida
exploração em produção. A própria versão instalada em produção não foi acessada.
O aviso Flask CVE-2025-47278 afeta somente 3.1.0, corrigido 3.1.1; não afeta a base
3.0.3 nem a candidata3.1.3.

Cada GHSA pode ser consultado em `https://github.com/advisories/<identificador>`.
Foram obtidos os documentos individuais e a relação completa dos pacotes pela
API oficial. A busca foi normalizada para nomes minúsculos: consulta sensível a
nome/case não deve ser usada isoladamente para concluir ausência de aviso.

## Mudanças de comportamento a validar

- Flask 3.1.3 marca como acesso à sessão operações como `in` e `len`, permitindo
  Vary:Cookie também nesses fluxos. Testar resposta com sessão existente e sem
  modificação, não apenas escrita de sessão.
- Flask 3.1 adiciona MAX_FORM_MEMORY_SIZE e MAX_FORM_PARTS e permite limite total
  por requisição. Werkzeug 3.1 muda o orçamento padrão de campos não arquivo de
  ilimitado para 500 kB. Testar formulários legítimos, multipart com limites baixos
  e limite total, sem criar arquivos gigantes.
- **Werkzeug 3.1.9 não aplica max_form_memory_size a application/x-www-form-urlencoded;
  esse formato é limitado por max_content_length.** Os testes de orçamento
  individual/memória devem usar multipart; não esperar 413 urlencoded por um
  controle que a biblioteca explicitamente não aplica mais.
- SERVER_NAME deixa de funcionar como restrição de Host em Flask 3.1; existe
  TRUSTED_HOSTS. Isso não resolve a futura SEC-010 por atualização de versão;
  validar proxy/URLs sem introduzir política canônica fora do escopo.
- PBKDF2 passa a 1.000.000 iterações por padrão em Werkzeug 3.1; scrypt permanece
  o padrão já usado desde 3.0. Preservar política e compatibilidade de hashes.
- Acesso a __version__ já era obsoleto; comprovar versões com importlib.metadata.
  Testar Flask-Login/CSRF/limiter/Socket.IO, sem desabilitar controles.

## Auditoria automatizada executada

Ferramenta **pip-audit 2.10.1** instalada somente em virtualenv de análise fora do
repositório, serviço de advisories PyPI. O ambiente original foi apenas lido por
`--path`; não foi atualizado nem usado para instalar ferramenta de auditoria.

- Base instalada:65 distribuições,27 registros brutos em quatro pacotes.
- A fonte retornou duplicatas. Normalização por CVE:14 avisos únicos, dos quais
  sete pertencem a Flask/Werkzeug e sete estão fora do escopo.
- Candidatas diretas: Flask 3.1.3 e Werkzeug 3.1.9, **zero avisos** na consulta.
  O comando terminou com exit0. Essa consulta direta não inclui todos os
  transitivos de uma instalação candidata completa.
- A auditoria da base terminou com exit1 por achados, não por indisponibilidade
  da base de vulnerabilidades. Nenhuma distribuição foi ignorada.

Comandos de auditoria, usando virtualenv e diretórios temporários de análise:

```bash
python -m pip_audit --path /caminho/venv-original/lib/python3.12/site-packages \
  --format json --aliases on --desc on --progress-spinner off \
  --output baseline-installed-audit.json
python -m pip_audit --disable-pip --no-deps -r candidates.txt \
  --format json --aliases on --desc off --progress-spinner off \
  --output candidate-direct-audit.json
```

Não foi usado --fix, --ignore-vuln ou alteração dos requisitos. O arquivo JSON
sanitizado diferencia registros brutos, CVEs normalizados, escopo e fontes.
A auditoria completa pós-instalação foi executada em modo somente leitura no
ambiente candidato, com --strict e o mesmo serviço PyPI. Não foram instalados
pacotes pelo auditor nesse ambiente. Os testes da aplicação são responsabilidade
da frente principal e não são inferidos a partir desta auditoria.

| Medida | Base instalada | Ambiente candidato completo |
| --- | ---: | ---: |
| Distribuições examinadas | 65 | 65 |
| Registros brutos de avisos | 27 | 14 |
| CVEs únicos após normalização | 14 | 7 |
| Pacotes com avisos | 4 | 2 |
| Avisos em Flask/Werkzeug | 7 CVEs únicos | 0 |
| Distribuições ignoradas ou erros de coleta | 0 | 0 |

Permanecem os seis CVEs de pip 25.0.1 e um de python-dotenv 1.0.1 descritos
abaixo. Por isso a auditoria completa retorna **exit1**, indicando esses achados,
sem significar falha de acesso à base nem conflito de dependências. Não se pode
descrever o ambiente completo como livre de avisos. Os alvos desta SEC-006 não
têm avisos nas bases consultadas nesta data.

Comparação independente final das distribuições: somente Flask, Werkzeug e
Flask-SocketIO mudaram; **62 distribuições permaneceram idênticas**, sem pacote
novo ou removido. As versões lidas por importlib.metadata no candidato final
foram Flask 3.1.3, Werkzeug 3.1.9, Flask-SocketIO 5.6.1, python-socketio 5.17.0,
pip 25.0.1 e python-dotenv 1.0.1. A primeira candidata, com apenas dois pacotes
modificados, fica preservada como evidência intermediária, não resultado final.

Comando adicional executado:

```bash
python -m pip_audit --path /caminho/venv-candidato/lib/python3.12/site-packages \
  --strict --format json --aliases on --desc off --progress-spinner off \
  --output candidate-final-installed-audit.json
```

A saída bruta candidata sem descrições e o resumo JSON sanitizado preservam
contagens, IDs/aliases, correções e escopo. Os hashes dos wheels no relatório de
instalação foram comparados com os hashes PyPI, com três correspondências.
A consulta final inclui Flask-SocketIO 5.6.1 sem aviso conhecido, além de Flask
3.1.3 e Werkzeug 3.1.9. O resumo final é candidate-final-installed-audit-summary.json;
a consulta intermediária está preservada em candidate-installed-audit.json.

## Ajuste mínimo necessário de Flask-SocketIO

A primeira candidata manteve Flask-SocketIO 5.4.1. Embora os requisitos de
metadata e pip check aceitassem essa combinação, a suíte completa da frente
principal apresentou 24 erros: o handler escreve `ctx.session = session_obj`,
mas Flask 3.1.3 usa uma propriedade sem setter para essa sessão. Esse resultado
foi preservado em `/tmp/nexo-sec006-candidate-before-socketio-full.log`.

O changelog oficial de Flask-SocketIO anuncia em **5.6.1, de 21/02/2026**,
“Session fixes for Flask >= 3.1.3”, issue #2153, commit
`956f8f2847c53d5156620b395912b7c916e15a1b`. O diff oficial acrescenta
`if hasattr(ctx, '_session'): ctx._session = session_obj`, preservando a escrita
em `ctx.session` para Flask anterior e escolhendo o contexto correspondente
para outras versões. Não exige desativação de proteção de sessão.

Conferência independente do código publicado nos wheels PyPI não retirados,
com SHA256 validado: 5.4.1, 5.5.0, 5.5.1 e 5.6.0 mantêm a atribuição incompatível;
**5.6.1 é a primeira estável que contém essa correção**. 5.7.0 é a estável mais
recente nesta data, porém não é necessária para esta compatibilidade.

Flask-SocketIO 5.6.1 declara Python>=3.8, Flask>=2.1.0 e
python-socketio>=5.12.0. O python-socketio instalado 5.17.0 é suficiente e foi
preservado; os demais requisitos já existem no ambiente. Wheel oficial
`flask_socketio-5.6.1-py3-none-any.whl`, SHA256
`51a3f71b28b4476c650829607e3a993e076034db6c3cc31f718f0a4b45939d42`,
igual ao relatório de instalação. Auditoria completa final sem avisos nesse
pacote. A auditoria não permite inferir aprovação dos testes de aplicação.

Evidências: `flask-socketio-CHANGES.md`,
`flask-socketio-session-fix-commit.json`,
`flask-socketio-release-source-comparison.json`, metadata PyPI 5.6.1 e
`candidate-final-installed-audit.json`.

## Achados fora do escopo e prioridade

| Pacote/aviso | Contexto | Prioridade sugerida / ação |
| --- | --- | --- |
| python-dotenv 1.0.1, CVE-2026-28684, GHSA-mf9w-mj56-hr94, corrigido 1.2.2 | Severidade oficial média; envolve set_key/unset_key, escrita local e condições de filesystem. Não há chamadas diretas a essas funções no código NEXO pesquisado; usa load_dotenv. | Média e condicional: revisar automação de deploy/escrita local em tarefa própria. Não atualizar nesta SEC-006. |
| pip 25.0.1, CVE-2025-8869 | Severidade média; fallback de extração. Python 3.12 implementa PEP706, de modo que a pré-condição específica desse fallback não se aplica ao alvo. | Revisão de tooling; documentar mitigação por Python 3.12, sem modificar runtime. |
| pip 25.0.1, CVE-2026-1703 | Severidade oficial baixa; processamento de instalação de wheel não confiável. | Baixa/condicional, cadeia de instalação; tratar tooling separadamente. |
| pip 25.0.1, CVE-2026-3219 /6357 /8643 /13346 | Campo textual GHSA médio; CVE-2026-8643 também publica CVSS 8,0, faixa alta. Instalação/índices/artefatos maliciosos; sem caminho HTTP identificado na aplicação. | Priorizar revisão separada do tooling, preservando a divergência de gravidade. Último aviso corrige em 26.2.0. Ver tabela individual reconsultada abaixo. |

pip é tooling presente na virtualenv, não dependência declarada em requirements.txt.
Nenhum desses achados foi ocultado nem atualizado fora do escopo autorizado.
Não foram localizados avisos para as demais distribuições nessa consulta;
isso não demonstra ausência de vulnerabilidades desconhecidas ou futuras.

## Limitações das fontes

Os domínios de documentação Pallets retornaram CONNECT403 pelo proxy. Não houve
mudança de permissões nem tentativa de contorno. Os changelogs dos mesmos
mantenedores foram obtidos dos repositórios oficiais pela API GitHub permitida.
PyPI e advisories GitHub responderam normalmente. Um resultado sem aviso
representa a fotografia dessas bases na data, não uma garantia geral de segurança.

## Reavaliação para publicação autorizada em 23/10/2026

O novo prompt autoriza commit, push e PR; o merge permanece condicionado à confirmação de ausência de deploy automático no Render. A auditoria instalada foi reexecutada com pip-audit 2.10.1: 65 distribuições, 14 registros brutos duplicados, sete CVEs únicos residuais em pip/python-dotenv e zero avisos em Flask 3.1.3, Werkzeug 3.1.9 e Flask-SocketIO 5.6.1. Exit code 1 representa os achados, sem falha de coleta.

### Sete CVEs residuais

Consulta renovada em 23/10/2026, somente leitura. As sete respostas individuais
foram obtidas novamente da API oficial GitHub Security Advisories (`GET
/advisories/<GHSA>`), sem falha de acesso. A relação anterior foi conferida com
`Docs/AUDITORIA_DEPENDENCIAS_SEC006.md` e com o código do repositório. Não foram
atualizadas bibliotecas, virtualenvs, Git, serviços ou configurações.

| CVE | Biblioteca e versão afetada avaliada | Gravidade oficial | Aplicabilidade ao NEXO | Recomendação | Fonte oficial |
| --- | --- | --- | --- | --- | --- |
| CVE-2025-8869 | pip 25.0.1; intervalo GHSA `<=25.2` | Média no GHSA | **Não aplicável ao fallback vulnerável no Python 3.12 avaliado**: o advisory informa que pip não usa esse fallback quando `tarfile` implementa PEP 706. Isso não torna todos os demais cenários de extração seguros. O pacote continua no intervalo detectado pelo auditor. | Manter Python com PEP 706 e tratar a atualização do tooling em tarefa separada; correção específica pip 25.3. | [GHSA-4xh5-x5gv-qwph](https://github.com/advisories/GHSA-4xh5-x5gv-qwph) |
| CVE-2026-1703 | pip 25.0.1; intervalo GHSA `<26.0` | Baixa no GHSA | Condicional à instalação de wheel malicioso; extração fora do diretório é limitada a prefixos do destino. Não foi identificado uso de pip por rotas da aplicação. Exploração no build/produção não foi comprovada. | Atualizar tooling separadamente; correção específica pip 26.0; revisar proveniência dos artefatos. | [GHSA-6vgw-5pg2-w6jp](https://github.com/advisories/GHSA-6vgw-5pg2-w6jp) |
| CVE-2026-3219 | pip 25.0.1; intervalo GHSA `<=26.0.1` | Média no GHSA | Condicional à instalação de arquivo com interpretação conflitante TAR/ZIP. É risco da cadeia de instalação, sem caminho HTTP identificado no NEXO. Exploração efetiva no build/produção não confirmada. | Atualizar tooling separadamente; correção específica pip 26.1; revisar origem e conteúdo de arquivos de instalação. | [GHSA-58qw-9mgm-455v](https://github.com/advisories/GHSA-58qw-9mgm-455v) |
| CVE-2026-6357 | pip 25.0.1; intervalo GHSA `<26.1` | Média no GHSA | Condicional à instalação de wheel com módulos que sejam importados pela verificação de autoatualização do pip. Não envolve o caminho normal de uma requisição Flask. Exploração no build/produção não confirmada. | Atualizar tooling separadamente; correção específica pip 26.1; revisar pacotes antes da instalação. | [GHSA-jp4c-xjxw-mgf9](https://github.com/advisories/GHSA-jp4c-xjxw-mgf9) |
| CVE-2026-8643 | pip 25.0.1; intervalo GHSA `<26.1.2` | **Alta pela faixa do CVSS 3.1 publicado: 8,0; o campo textual `severity` do mesmo GHSA é `medium`** | Condicional à instalação de pacote com nomes maliciosos de entry points `console_scripts`/`gui_scripts`, permitindo escrever scripts fora do diretório alvo. Nenhuma instalação de pacotes comandada por entrada HTTP do NEXO foi encontrada. Não foi comprovada exploração imediata no aplicativo ou no build real. | Tratar como risco alto potencial da cadeia de instalação e priorizar revisão do tooling em tarefa própria; correção específica pip 26.1.2. Não atualizar automaticamente nesta SEC-006. | [GHSA-wf93-45jw-7689](https://github.com/advisories/GHSA-wf93-45jw-7689) |
| CVE-2026-13346 | pip 25.0.1; intervalo GHSA `<26.2.0` | Média no GHSA | Requer índice de pacotes malicioso e URLs duplamente codificadas; o advisory diz que pacote malicioso sozinho não basta e destaca `pip download --only-binary`. As instalações candidatas registradas usaram PyPI oficial. Configuração real do build de produção não foi acessada. | Atualizar tooling separadamente para pelo menos 26.2.0, cobrindo também as correções anteriores; manter índices confiáveis. | [GHSA-qwm4-qh6w-59xr](https://github.com/advisories/GHSA-qwm4-qh6w-59xr) |
| CVE-2026-28684 | python-dotenv 1.0.1; intervalo GHSA `<1.2.2` | Média; CVSS 3.1 6,6 no GHSA | Depende de `set_key`/`unset_key`, escrita local no diretório do `.env`, symlink e fallback de movimentação entre dispositivos. O código NEXO pesquisado usa apenas `load_dotenv` em `config.py`; nenhuma chamada direta às funções de escrita foi encontrada. Não aplicável a esse caminho de leitura inspecionado; automações externas não avaliadas. | Revisar scripts operacionais e programar atualização separada para 1.2.2 ou versão estável adequada. Não alterar nesta SEC-006. | [GHSA-mf9w-mj56-hr94](https://github.com/advisories/GHSA-mf9w-mj56-hr94) e [advisory do mantenedor](https://github.com/theskumar/python-dotenv/security/advisories/GHSA-mf9w-mj56-hr94) |

### Classificação e impedimentos

Os campos textuais atuais dos sete GHSAs classificam seis como médios e um
como baixo. Entretanto, a resposta oficial de CVE-2026-8643 inclui também
CVSS 3.1 8,0, que está na faixa alta. Essa divergência foi preservada na tabela,
em vez de repetir apenas a classificação média anterior. Nenhum aviso crítico
foi identificado nessa relação.

**Não foi comprovada vulnerabilidade crítica ou alta imediatamente explorável
no NEXO que constitua impedimento de integração desta SEC-006.** Isso não é uma
declaração de ausência de risco: CVE-2026-8643 exige tratamento separado e
prioritário da cadeia de instalação. A ausência de inspeção do build/ambiente
real impede classificar toda a operação de produção como não afetada. Não foram
realizados testes de exploração nem acessos ao Render/Supabase.

Pesquisa no código versionado: não foram encontradas chamadas `set_key` ou
`unset_key`; `config.py` importa e usa `load_dotenv`. `render.yaml` declara
`pip install -r requirements.txt`, evidenciando uso de pip na etapa de build,
sem revelar qual versão ou configuração de índice existe no serviço real.
O inventário local inspecionado contém pip 25.0.1 e python-dotenv 1.0.1; pip é
ferramenta presente na virtualenv, não dependência declarada em requirements.

As recomendações são para uma tarefa posterior autorizada. Nenhuma das sete
vulnerabilidades foi ignorada no auditor ou atualizada nesta frente.
