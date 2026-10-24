"""Detectores de risco e validação de saídas.

Os detectores trabalham sobre o texto "bruto" (casefold, com símbolos), porque
URLs, caminhos e código perdem a forma na normalização linguística. Nenhum
detector executa, resolve ou visita o conteúdo: apenas o classifica.
"""

import re

from .normalizacao import sem_acentos

# Esquemas, domínios, IPs, localhost e caminhos absolutos ("/admin", "//host").
_URL = re.compile(
    r"\b[a-z][a-z0-9+.\-]*\s*:\s*/\s*/"
    r"|\b(?:https?|ftp|sftp|wss?|javascript|vbscript|data|file|blob|mailto|tel|about|chrome)\s*:"
    r"|(?:^|[\s(\[{<\"'])/{1,2}[a-z0-9_.%~\-]"
    r"|\\\\|%2f|%5c|&#|\bwww\."
    r"|\b(?:[a-z0-9\-]+\.)+(?:com|net|org|io|dev|br|app|gov|edu|info|xyz|me|co|ai|site|online|"
    r"shop|top|ru|cn|tk|ly|gl|link|click|biz|us|uk)\b"
    r"|\b(?:\d{1,3}\.){3}\d{1,3}\b|\blocalhost\b",
    re.IGNORECASE,
)
_ADMIN = re.compile(
    r"\b(?:admin|administracao|administrador[ae]?s?|administrativ[oa]s?|superusuario|"
    r"backoffice|back office|lixeira|gestao de empresas|area do consultor|root)\b"
)
_INJECAO = re.compile(
    r"\b(?:ignore|ignora|ignorar|esqueca|esquece|desconsidere|desconsidera|descarte)\b"
    r"(?: \w+){0,4} (?:instrucoes|instrucao|regras|ordens|orientacoes|diretrizes|prompt|comandos)\b"
    r"|\b(?:system prompt|prompt (?:do )?sistema|seu prompt|suas instrucoes|suas regras internas)\b"
    r"|\b(?:a partir de agora|agora) (?:voce|vc) (?:eh|e|sera|vai ser|deve)\b"
    r"|\bmodo (?:desenvolvedor|developer|dan|deus|god|irrestrito|sem restricoes|admin)\b"
    r"|\bjailbreak\b|\bsem (?:restricoes|filtros|limites)\b"
    r"|\b(?:finja|finge|aja|age|atue|comporte se) (?:que|como)\b"
    r"|\b(?:ignore|disregard) (?:all |the |your )?(?:previous|prior|above)\b"
    r"|\b(?:act as|you are now|developer mode|pretend to be)\b"
)
_MARCAS_PROMPT = re.compile(r"\[/?inst\]|<\|?(?:system|im_start|im_end)\|?>|###\s*(?:instruction|system)",
                            re.IGNORECASE)
_SQL = re.compile(
    r"\b(?:select|insert|update|delete|drop|alter|truncate|union|grant|create)\b[\s\S]{0,60}?"
    r"\b(?:from|into|table|set|where|database|schema|select|values)\b"
    r"|;\s*--|'\s*or\s*'?\d*'?\s*=\s*'?\d*|\bor\s+1\s*=\s*1\b|\bxp_cmdshell\b|\bpg_sleep\b",
    re.IGNORECASE,
)
_CODIGO = re.compile(
    r"\bimport\s+[a-z_]+|\bfrom\s+[a-z_.]+\s+import\b|__import__|\bos\.(?:system|popen|remove)"
    r"|\bsubprocess\b|\beval\s*\(|\bexec\s*\(|\bdef\s+\w+\s*\(|\bprint\s*\(|\blambda\s*\w*:"
    r"|<\s*script|<\s*/\s*script|<\s*iframe|<\s*img[^>]*on\w+\s*=|\bon(?:error|load|click)\s*="
    r"|\brm\s+-rf\b|\bcurl\s+-|\bwget\s+|\$\(|\bsudo\s+|\bchmod\s+|\bbash\s+-c\b"
    r"|\bdocument\.cookie\b|\bwindow\.location\b|\bfetch\s*\(",
    re.IGNORECASE,
)
_OUTRA_EMPRESA = re.compile(
    r"\b(?:dados|faturamento|relatorios?|analises?|vendas|compras|informacoes|indicadores|clientes|senha)"
    r"(?: \w+){0,3} (?:de|da|do|das|dos) (?:outras? empresas?|outros clientes|todas as empresas|"
    r"todos os clientes|concorrentes?|outro cliente)\b"
    r"|\b(?:lista|listar|liste|relacao) (?:de |das |dos )?(?:empresas|clientes|usuarios)\b"
    r"|\b(?:outras empresas|outros clientes|todas as empresas|todos os clientes)\b"
)
_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
_DOCUMENTO = re.compile(r"\b\d{2,3}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[\-\s]?\d{2}\b|\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[\-\s]?\d{2}\b")
_TELEFONE = re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[\-\s]?\d{4}\b")
_NUMERO_LONGO = re.compile(r"\d[\d.,]{5,}")
_MOEDA = re.compile(r"r\$\s*[\d.,]+", re.IGNORECASE)
_SENHA_EXPLICITA = re.compile(r"\b(senha|password)\b(\s*(?:e|eh|é|para|pra|:|=)\s*)\S+", re.IGNORECASE)


def contem_url(bruto: str) -> bool:
    return bool(_URL.search(bruto or ""))


def menciona_admin(canonico: str) -> bool:
    return bool(_ADMIN.search(canonico or ""))


def tentativa_injecao(canonico: str, bruto: str) -> bool:
    return bool(_INJECAO.search(canonico or "") or _MARCAS_PROMPT.search(bruto or ""))


def contem_codigo(bruto: str) -> bool:
    return bool(_SQL.search(bruto or "") or _CODIGO.search(bruto or ""))


def pede_outra_empresa(canonico: str) -> bool:
    return bool(_OUTRA_EMPRESA.search(canonico or ""))


def redigir(texto: str) -> str:
    """Remove dados pessoais e valores antes de enviar texto a terceiros."""
    texto = _EMAIL.sub("[email]", texto or "")
    texto = _SENHA_EXPLICITA.sub(r"\1\2[omitida]", texto)
    texto = _MOEDA.sub("[valor]", texto)
    texto = _DOCUMENTO.sub("[documento]", texto)
    texto = _TELEFONE.sub("[telefone]", texto)
    return _NUMERO_LONGO.sub("[numero]", texto)


# --- Validação de saídas de modelos externos -------------------------------
_PROIBIDOS_SAIDA = ("margem", "lucro", "cmv", "rentab", "prejuiz")
_ACAO_ALEGADA = re.compile(
    r"\b(?:ja )?(?:abri|enviei|exclui|apaguei|deletei|removi|alterei|troquei|publiquei|criei|"
    r"cadastrei|processei|executei|redefini|cancelei|atualizei|anexei)\b"
)
_MARKUP = re.compile(r"<[a-z/!][^>]*>|```|\]\(|\[[^\]]+\]\s*\(|!\[", re.IGNORECASE)
_NUMEROS = re.compile(r"\d+(?:[.,]\d+)?")


def validar_saida_modelo(texto, fontes: str, limite: int = 1200) -> str | None:
    """Aceita a redação do modelo somente se não extrapolar as fontes.

    Rejeita: vazio, texto longo demais, links/caminhos, HTML/markdown de link,
    termos financeiros proibidos, alegação de ter executado ações, eco de
    instruções e números que não aparecem nas fontes (valores inventados).
    """
    if not isinstance(texto, str):
        return None
    texto = texto.strip()
    if not texto or len(texto) > limite:
        return None
    simples = sem_acentos(texto.casefold())
    if any(p in simples for p in _PROIBIDOS_SAIDA):
        return None
    if contem_url(simples) or _MARKUP.search(texto) or contem_codigo(texto):
        return None
    if _ACAO_ALEGADA.search(simples) or _INJECAO.search(simples):
        return None
    numeros_fonte = set(_NUMEROS.findall(fontes or ""))
    if any(n not in numeros_fonte for n in _NUMEROS.findall(texto)):
        return None
    return texto


def texto_resposta(texto: str, limite: int = 6000) -> str:
    """Saneia o texto devolvido ao widget (que já o exibe como texto puro)."""
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(texto or ""))
    if len(texto) > limite:
        texto = texto[: limite - 1].rstrip() + "…"
    return texto
