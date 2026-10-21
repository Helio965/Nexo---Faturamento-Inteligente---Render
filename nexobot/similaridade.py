"""Similaridade textual sem dependências externas.

- `distancia`: Damerau-Levenshtein (transposição adjacente) com limite, que
  interrompe o cálculo assim que a distância ultrapassa o máximo pedido.
- `radical`: redutor leve de flexões do português (plural, gênero, verbos
  regulares e sufixos frequentes). Não pretende ser um stemmer completo:
  basta aproximar "enviar/envio/enviei" e "relatório/relatórios".
- `IndiceBM25`: ranking lexical ponderado por campo, com expansão de
  sinônimos e correspondência aproximada para termos fora do vocabulário.

O custo é proporcional ao tamanho da base do Guia (dezenas de tópicos), o que
mantém a busca em poucos milissegundos no plano gratuito do Render.
"""

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
import math


def distancia(a: str, b: str, maximo: int) -> int:
    """Distância de edição com transposições; devolve `maximo + 1` se exceder."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > maximo:
        return maximo + 1
    anterior2 = None
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        atual = [i] + [0] * len(b)
        menor = atual[0]
        for j, cb in enumerate(b, 1):
            custo = 0 if ca == cb else 1
            valor = min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + custo)
            if (anterior2 is not None and i > 1 and j > 1
                    and ca == b[j - 2] and a[i - 2] == cb):
                valor = min(valor, anterior2[j - 2] + 1)
            atual[j] = valor
            menor = min(menor, valor)
        if menor > maximo:
            return maximo + 1
        anterior2, anterior = anterior, atual
    return anterior[-1] if anterior[-1] <= maximo else maximo + 1


def limite_edicao(palavra: str) -> int:
    """Erros tolerados conforme o tamanho: palavras curtas são mais ambíguas."""
    if len(palavra) < 4:
        return 0
    if len(palavra) < 7:
        return 1
    return 2


# Sufixos removidos em ordem (mais longos primeiro). O objetivo é agrupar
# formas flexionadas comuns em perguntas de suporte, não análise morfológica.
_SUFIXOS = (
    "izacoes", "izacao", "amentos", "imentos", "amento", "imento", "acoes", "icoes",
    "acao", "icao", "adoras", "adores", "adora", "ador", "aveis", "ivel", "avel",
    "aremos", "eremos", "iremos", "assem", "essem", "issem", "ariam", "eriam", "iriam",
    "ando", "endo", "indo", "aram", "eram", "iram", "avam", "amos", "emos", "imos",
    "adas", "idas", "ados", "idos", "ada", "ida", "ado", "ido",
    "ar", "er", "ir", "ei", "ou", "eu", "iu", "am", "em", "as", "es", "os", "is",
    "a", "e", "o", "s",
)


@lru_cache(maxsize=4096)
def radical(palavra: str) -> str:
    """Reduz a palavra a um radical aproximado, preservando ao menos 4 letras."""
    if len(palavra) <= 4 or not palavra.isalpha():
        return palavra
    if palavra.endswith("oes") and len(palavra) > 5:
        palavra = palavra[:-3] + "ao"
    elif palavra.endswith("ais") and len(palavra) > 5:
        palavra = palavra[:-3] + "al"
    for sufixo in _SUFIXOS:
        if palavra.endswith(sufixo) and len(palavra) - len(sufixo) >= 4:
            return palavra[: -len(sufixo)]
    return palavra


@dataclass
class Documento:
    """Unidade indexável: os campos têm pesos distintos na pontuação."""
    chave: object
    campos: dict  # nome do campo -> lista de radicais
    pesos: dict   # nome do campo -> peso


@dataclass
class Correspondencia:
    chave: object
    pontuacao: float
    cobertura: float            # fração (ponderada por IDF) da consulta atendida
    termos: frozenset = field(default_factory=frozenset)
    especificos: int = 0        # termos casados que não são genéricos
    diretos: int = 0            # termos não genéricos casados literalmente (sem sinônimo)
    casados: frozenset = field(default_factory=frozenset)  # termos do documento que casaram


class IndiceBM25:
    """BM25F simplificado com cobertura ponderada por IDF para calibrar confiança."""

    K1 = 1.2
    B = 0.6

    def __init__(self, documentos, genericos=frozenset()):
        self.documentos = list(documentos)
        self.genericos = {radical(g) for g in genericos}
        self.total = len(self.documentos)
        self._freq = []
        self._tamanho = []
        df = Counter()
        for doc in self.documentos:
            frequencias = Counter()
            tamanho = 0.0
            for campo, termos in doc.campos.items():
                peso = doc.pesos.get(campo, 1.0)
                for termo in termos:
                    frequencias[termo] += peso
                tamanho += peso * len(termos)
            self._freq.append(frequencias)
            self._tamanho.append(tamanho)
            df.update(frequencias.keys())
        self.media = (sum(self._tamanho) / self.total) if self.total else 0.0
        self.idf = {
            termo: math.log(1 + (self.total - n + 0.5) / (n + 0.5)) for termo, n in df.items()
        }
        self.vocabulario = frozenset(self.idf)
        # Termo inexistente na base pesa como um termo típico: reduz a confiança
        # sem que uma única palavra fora do Guia anule uma correspondência clara.
        self._idf_ausente = (sum(self.idf.values()) / len(self.idf)) if self.idf else 1.0

    def idf_de(self, termo: str) -> float:
        return self.idf.get(termo, self._idf_ausente)

    def aproximar(self, termo: str) -> str | None:
        """Termo da base mais próximo de uma palavra digitada com erro."""
        if termo in self.vocabulario:
            return termo
        maximo = limite_edicao(termo)
        if not maximo:
            return None
        melhor, melhor_dist = None, maximo + 1
        for candidato in self.vocabulario:
            if candidato[:1] != termo[:1] and len(termo) < 6:
                continue
            d = distancia(termo, candidato, maximo)
            if d < melhor_dist:
                melhor, melhor_dist = candidato, d
            elif d == melhor_dist and d <= maximo:
                melhor = None  # empate: não arriscar
        return melhor

    def buscar(self, consulta, limite: int = 5) -> list[Correspondencia]:
        """`consulta`: lista de (termo, peso, origem).

        `origem` é o termo digitado que gerou o termo buscado (ele mesmo, um
        sinônimo ou uma aproximação ortográfica). A cobertura é calculada sobre
        as origens: sinônimos ajudam a encontrar, mas valem menos que o termo
        literal e nunca contam duas vezes para a mesma palavra digitada.
        """
        if not self.total or not consulta:
            return []
        origens = {origem for _, _, origem in consulta}
        base = sum(self._peso_termo(o) for o in origens) or 1.0
        resultados = []
        for i, doc in enumerate(self.documentos):
            freq = self._freq[i]
            norma = self.K1 * (1 - self.B + self.B * self._tamanho[i] / (self.media or 1.0))
            pontuacao = 0.0
            cobertas = {}
            casados = set()
            diretos = set()
            for termo, peso, origem in consulta:
                tf = freq.get(termo)
                if not tf:
                    continue
                pontuacao += peso * self.idf_de(termo) * (tf * (self.K1 + 1)) / (tf + norma)
                casados.add(termo)
                cobertas[origem] = max(cobertas.get(origem, 0.0), peso)
                if peso >= 1.0 and origem not in self.genericos:
                    diretos.add(origem)
            if not casados:
                continue
            cobertura = sum(self._peso_termo(o) * p for o, p in cobertas.items()) / base
            especificos = sum(1 for o in cobertas if o not in self.genericos)
            resultados.append(Correspondencia(
                doc.chave, pontuacao, min(cobertura, 1.0), frozenset(cobertas), especificos,
                len(diretos), frozenset(casados),
            ))
        resultados.sort(key=lambda r: (r.cobertura, r.pontuacao), reverse=True)
        return resultados[:limite]

    def _peso_termo(self, termo: str) -> float:
        peso = self.idf_de(termo)
        return peso * (0.25 if termo in self.genericos else 1.0)
