"""Varredura leve de segredos nos arquivos versionados (CI, advisória).

Sem dependências externas: lê os arquivos que o git rastreia e procura padrões
de credencial de alta confiança (chaves de provedores, PEM, URLs com senha).
Ignora exemplos conhecidos (.env.example, fixtures de teste) e valores
claramente sintéticos. Imprime um resumo em Markdown e SEMPRE sai com 0: é um
aviso para triagem humana, não um portão de merge. A varredura oficial contínua
é o secret scanning nativo do GitHub; este passo cobre o diff a cada PR.
"""

import re
import subprocess
import sys

# (rótulo, regex). Padrões conservadores: preferir não acusar a gerar ruído.
PADROES = [
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Chave privada PEM", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("Token do GitHub", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("Chave da OpenAI", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("Chave da Anthropic", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("Chave do Google", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("Token do Slack", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    # Brevo (e-mail transacional): chave de API e chave SMTP. Só o prefixo
    # aparece na documentação; um valor completo versionado é vazamento.
    ("Chave do Brevo (API)", re.compile(r"xkeysib-[A-Za-z0-9]{32,}-[A-Za-z0-9]{8,}")),
    ("Chave do Brevo (SMTP)", re.compile(r"xsmtpsib-[A-Za-z0-9]{32,}-[A-Za-z0-9]{8,}")),
    ("URL com senha embutida", re.compile(r"://[^/\s:@]+:[^/\s:@]{4,}@[^/\s]+")),
]

# Valores de exemplo/sintéticos que NÃO são segredos reais.
SEGUROS = re.compile(r"(?i)(exemplo|example|synthetic|dummy|changeme|placeholder|xxxx|senha-?teste|your[_-]?key|127\.0\.0\.1|localhost|user:pass)")

# Caminhos cujo conteúdo é intencionalmente ilustrativo (prefixos de diretório
# e arquivos de exemplo/lock), varridos à parte pela revisão humana.
IGNORAR_CAMINHO = re.compile(r"(^|/)tests/|(^|/)static/vendor/|(^|/)\.env\.example$|\.lock$")


def arquivos_versionados():
    saida = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [linha for linha in saida.stdout.splitlines() if linha]


def main() -> int:
    achados = []
    for caminho in arquivos_versionados():
        if IGNORAR_CAMINHO.search(caminho):
            continue
        try:
            with open(caminho, "r", encoding="utf-8", errors="replace") as arquivo:
                for numero, linha in enumerate(arquivo, 1):
                    if len(linha) > 4000:
                        continue
                    for rotulo, padrao in PADROES:
                        if padrao.search(linha) and not SEGUROS.search(linha):
                            achados.append((caminho, numero, rotulo))
        except (OSError, ValueError):
            continue

    resumo = ["## Secret scanning (varredura leve)"]
    if achados:
        resumo.append(f"⚠️ {len(achados)} possível(is) segredo(s) para revisão humana:")
        for caminho, numero, rotulo in achados[:50]:
            resumo.append(f"- `{caminho}:{numero}` — {rotulo}")
        resumo.append("\nRevise manualmente; nenhum valor é exibido aqui.")
    else:
        resumo.append("✅ Nenhum padrão de credencial de alta confiança encontrado.")
    texto = "\n".join(resumo)
    print(texto)
    import os
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        try:
            with open(destino, "a", encoding="utf-8") as saida:
                saida.write(texto + "\n")
        except OSError:
            pass
    # Advisório: nunca trava o merge.
    return 0


if __name__ == "__main__":
    sys.exit(main())
