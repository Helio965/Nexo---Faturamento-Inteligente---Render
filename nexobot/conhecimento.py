"""Camada C — recuperação de conhecimento sobre o Guia (GuiaTopico).

O Guia cadastrado no CMS do administrador é a fonte autorizada. Apenas
tópicos ATIVOS entram no índice. Os fatos de `portal.py` formam um segundo
índice, consultado somente quando o Guia não tem resposta confiável.

Cache e invalidação (sem migrations, sem tabela nova):
  - O índice é construído sob demanda e guardado por aplicação Flask
    (`app.extensions["nexobot"]`).
  - Eventos do SQLAlchemy marcam qualquer inserção, edição, exclusão ou
    operação em massa sobre `GuiaTopico`; no COMMIT a geração global avança
    e o próximo pedido reconstrói o índice. Rollback descarta a marcação.
  - Um TTL curto cobre alterações feitas fora deste processo (outro worker,
    SQL manual). Com o `render.yaml` atual (1 worker), a invalidação é imediata.

O conteúdo dos tópicos é tratado como dado: nunca como instrução, nunca como
fonte de URLs ou de destinos (um tópico só "aponta" para páginas que já
existem no catálogo fechado de `navegacao.py`).
"""

from dataclasses import dataclass
import logging
import re
import threading
import time

from flask import current_app
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from extensions import db
from models import GuiaTopico

from .lexico import GENERICOS, GRUPOS_SINONIMOS, STOPWORDS
from .navegacao import FORTE, destinos_em
from .normalizacao import sem_acentos
from .portal import FATOS
from .similaridade import Documento, IndiceBM25, radical

logger = logging.getLogger(__name__)

TTL_SEGUNDOS = 60
LIMIAR_ALTO = 0.6        # calibrado em tests/test_nexobot_conhecimento.py
LIMIAR_MEDIO = 0.45
MARGEM_AMBIGUIDADE = 0.06
VANTAGEM_FATO = 0.12
MAXIMO_TOPICOS = 500
MAXIMO_CARACTERES_INDICE = 6000

_PALAVRA = re.compile(r"[a-z0-9]+")
_CHAVE_EXTENSAO = "nexobot"

# --- Invalidação por eventos do ORM ----------------------------------------
_trava_geracao = threading.Lock()
_geracao = 0
_MARCA = "nexobot_guia_alterado"


def geracao_atual() -> int:
    return _geracao


def invalidar() -> None:
    """Força a reconstrução do índice em todos os processos que leem esta geração."""
    global _geracao
    with _trava_geracao:
        _geracao += 1


@event.listens_for(Session, "after_flush")
def _marcar_alteracao(session, _contexto):
    alterados = (*session.new, *session.dirty, *session.deleted)
    if any(isinstance(obj, GuiaTopico) for obj in alterados):
        session.info[_MARCA] = True


@event.listens_for(Session, "do_orm_execute")
def _marcar_operacao_em_massa(estado):
    if (estado.is_update or estado.is_delete or getattr(estado, "is_insert", False)) and any(
            mapper.class_ is GuiaTopico for mapper in estado.all_mappers):
        estado.session.info[_MARCA] = True


@event.listens_for(Session, "after_commit")
def _publicar_alteracao(session):
    if session.info.pop(_MARCA, False):
        invalidar()


@event.listens_for(Session, "after_soft_rollback")
def _descartar_alteracao(session, _transacao):
    session.info.pop(_MARCA, None)


# --- Estruturas ------------------------------------------------------------
@dataclass(frozen=True)
class Trecho:
    origem: str               # "guia" ou "portal"
    chave: object
    pergunta: str
    resposta: str
    categoria: str
    destino: str | None       # página do catálogo relacionada ao assunto


@dataclass(frozen=True)
class Resultado:
    trecho: Trecho | None
    confianca: float
    nivel: str                # "alta", "media" ou "nenhuma"
    alternativas: tuple = ()
    ambiguo: bool = False
    degradado: bool = False   # a base do Guia não pôde ser lida


def tokenizar(texto: str) -> list[str]:
    """Tokens de documento: sem acento, minúsculos, sem palavras funcionais."""
    simples = sem_acentos(str(texto or "").casefold())
    return [t for t in _PALAVRA.findall(simples) if len(t) > 1 and t not in STOPWORDS]


_TIPOS_PERGUNTA = (
    ("porque", re.compile(r"\b(?:por que|porque|pra que|para que|por qual motivo)\b")),
    ("oque", re.compile(r"\b(?:o que (?:eh|e|significa|quer dizer)|significa|significado)\b")),
    ("acontece", re.compile(r"\bo que acontece\b")),
    ("errado", re.compile(r"\b(?:errad[oa]|engan\w*|incorret[oa])\b")),
    ("posso", re.compile(r"\b(?:posso|da para|tem como|eh possivel|e possivel)\b")),
    ("como_sei", re.compile(r"\bcomo (?:eu )?(?:sei|saber|vejo se|confiro)\b")),
)


def tipo_de_pergunta(texto: str) -> str | None:
    """Tipo da pergunta ("por que", "o que significa"...), usado como desempate."""
    simples = " ".join(_PALAVRA.findall(sem_acentos(str(texto or "").casefold())))
    simples = simples.replace(" e ", " eh ") if " o que e " in f" {simples} " else simples
    for nome, padrao in _TIPOS_PERGUNTA:
        if padrao.search(simples):
            return nome
    return None


def _destino_do_assunto(*textos: str) -> str | None:
    """Destino do catálogo nomeado no título/categoria do tópico (se for único)."""
    encontrados = destinos_em(sem_acentos(" ".join(textos).casefold()), minimo=FORTE)
    return next(iter(encontrados)) if len(encontrados) == 1 else None


_SINONIMOS = {}
for _grupo in GRUPOS_SINONIMOS:
    for _palavra in _grupo:
        _SINONIMOS.setdefault(_palavra, set()).update(_grupo - {_palavra})


def montar_consulta(palavras, indice: IndiceBM25) -> list[tuple]:
    """(termo, peso, origem): termo digitado, sinônimos e aproximação ortográfica."""
    consulta, vistos = [], set()
    for palavra in palavras:
        if palavra in STOPWORDS or len(palavra) < 2 or palavra in vistos:
            continue
        vistos.add(palavra)
        termo = radical(palavra)
        consulta.append((termo, 1.0, termo))
        for sinonimo in _SINONIMOS.get(palavra, ()):
            consulta.append((radical(sinonimo), 0.6, termo))
        if termo not in indice.vocabulario:
            aproximado = indice.aproximar(termo)
            if aproximado:
                consulta.append((aproximado, 0.8, termo))
    return consulta


class BaseConhecimento:
    """Índices imutáveis do Guia e dos fatos; seguros para leitura concorrente."""

    def __init__(self, topicos, degradado: bool = False):
        self.topicos = tuple(topicos)
        self.degradado = degradado
        self.fatos = tuple(
            Trecho("portal", f.chave, f.pergunta, f.resposta, "", f.destino) for f in FATOS
        )
        termos_fatos = {f.chave: f.termos for f in FATOS}
        self.indice_guia = IndiceBM25(
            (self._documento(t) for t in self.topicos), genericos=GENERICOS,
        )
        self.indice_fatos = IndiceBM25(
            (self._documento(t, termos_fatos[t.chave]) for t in self.fatos), genericos=GENERICOS,
        )
        self._por_chave = {("guia", t.chave): t for t in self.topicos}
        self._por_chave.update({("portal", t.chave): t for t in self.fatos})
        self._bigramas = {
            (t.origem, t.chave): self._pares(tokenizar(t.pergunta)) for t in (*self.topicos, *self.fatos)
        }
        # Termos do "título" (pergunta, categoria, termos do fato): um assunto citado
        # só no corpo da resposta é indício fraco de que o tópico responde à dúvida.
        self._titulos = {
            (t.origem, t.chave): {radical(p) for p in tokenizar(
                f"{t.pergunta} {t.categoria} {termos_fatos.get(t.chave, '') if t.origem == 'portal' else ''}")}
            for t in (*self.topicos, *self.fatos)
        }
        self._tipos = {(t.origem, t.chave): tipo_de_pergunta(t.pergunta) for t in (*self.topicos, *self.fatos)}
        self._titulo_pergunta = {
            (t.origem, t.chave): {radical(p) for p in tokenizar(t.pergunta)} - {radical(g) for g in GENERICOS}
            for t in (*self.topicos, *self.fatos)
        }

    @staticmethod
    def _pares(tokens) -> set:
        radicais = [radical(t) for t in tokens]
        return set(zip(radicais, radicais[1:]))

    @staticmethod
    def _documento(trecho: Trecho, termos_extras: str = "") -> Documento:
        campos = {
            "pergunta": [radical(t) for t in tokenizar(trecho.pergunta)],
            "categoria": [radical(t) for t in tokenizar(trecho.categoria)],
            "resposta": [radical(t) for t in tokenizar(trecho.resposta[:MAXIMO_CARACTERES_INDICE])],
        }
        if termos_extras:
            campos["termos"] = [radical(t) for t in tokenizar(termos_extras)]
        pesos = {"pergunta": 3.0, "categoria": 1.5, "resposta": 1.0, "termos": 2.0}
        return Documento((trecho.origem, trecho.chave), campos, pesos)

    @property
    def vazia(self) -> bool:
        return not self.topicos

    def categorias(self) -> list[str]:
        return sorted({t.categoria for t in self.topicos if t.categoria})

    def _buscar(self, indice, palavras, tipo=None) -> list:
        """Lista de (ordem, confiança, trecho), da melhor para a pior correspondência.

        - confiança: cobertura da pergunta (ponderada por IDF), reduzida quando só
          sinônimos casaram ou quando o assunto não aparece no título do tópico;
        - ordem: confiança + semelhança com o título + expressões e tipo de
          pergunta em comum (desempata tópicos que citam as mesmas palavras).
        """
        consulta = montar_consulta(palavras, indice)
        termos_consulta = {termo for termo, _, _ in consulta}
        especificos_consulta = {origem for _, _, origem in consulta} - indice.genericos
        resultados = indice.buscar(consulta, limite=5)
        pares = self._pares([p for p in palavras if p not in STOPWORDS])
        ajustados = []
        for r in resultados:
            if r.especificos == 0:
                continue  # só termos genéricos ("portal", "página"): não comprova assunto
            titulo = self._titulos.get(r.chave, set())
            cobertura = r.cobertura if r.diretos else r.cobertura * 0.7
            if not ((r.casados - indice.genericos) & titulo):
                cobertura *= 0.6
            if r.especificos == 1 and len(especificos_consulta) >= 2:
                cobertura *= 0.75  # uma única palavra em comum não comprova o assunto
            bonus = 0.05 * len(pares & self._bigramas.get(r.chave, set()))
            if tipo and tipo == self._tipos.get(r.chave):
                bonus += 0.08  # "por que...?" combina com um tópico que explica o porquê
            bonus = min(bonus, 0.15)
            proprio = self._titulo_pergunta.get(r.chave, set())
            semelhanca = len(proprio & termos_consulta) / len(proprio) if proprio else 0.0
            confianca = min(1.0, cobertura + bonus)
            ordem = cobertura + bonus + 0.25 * semelhanca
            ajustados.append((ordem, confianca, r.pontuacao, self._por_chave[r.chave]))
        ajustados.sort(key=lambda x: (x[0], x[2]), reverse=True)
        return [(ordem, confianca, trecho) for ordem, confianca, _, trecho in ajustados]

    def buscar(self, palavras, destino_pergunta: str | None = None, tipo: str | None = None) -> Resultado:
        palavras = [p for p in palavras if p]
        guia = self._buscar(self.indice_guia, palavras, tipo) if self.topicos else []
        fatos = self._buscar(self.indice_fatos, palavras, tipo)

        def filtrar(lista):
            # Um assunto ligado a outra página nomeada na pergunta não é a resposta.
            if not destino_pergunta:
                return lista
            return [x for x in lista if x[2].destino in (None, destino_pergunta) or x[1] >= 0.85]

        guia, fatos = filtrar(guia), filtrar(fatos)
        ordem = [(guia, LIMIAR_ALTO), (fatos, LIMIAR_ALTO), (guia, LIMIAR_MEDIO), (fatos, LIMIAR_MEDIO)]
        if guia and fatos and fatos[0][0] - guia[0][0] >= VANTAGEM_FATO:
            # O Guia tem prioridade, salvo quando um fato da interface responde
            # a pergunta de forma claramente mais específica.
            ordem = [(fatos, LIMIAR_ALTO)] + ordem
        escolhido = next((lista for lista, limiar in ordem if lista and lista[0][1] >= limiar), None)
        if not escolhido:
            melhor = max((x[1] for x in (*guia[:1], *fatos[:1])), default=0.0)
            return Resultado(None, round(melhor, 2), "nenhuma", degradado=self.degradado)
        ordem_1, confianca, trecho = escolhido[0]
        alternativas = tuple(t for _, c, t in escolhido[1:] if c >= LIMIAR_MEDIO)
        ambiguo = (len(escolhido) > 1 and escolhido[1][1] >= LIMIAR_MEDIO
                   and ordem_1 - escolhido[1][0] < MARGEM_AMBIGUIDADE
                   and escolhido[1][2].pergunta != trecho.pergunta)
        nivel = "alta" if confianca >= LIMIAR_ALTO else "media"
        return Resultado(trecho, round(confianca, 2), nivel, alternativas, ambiguo, self.degradado)


# --- Carga com cache por aplicação ----------------------------------------
def _carregar_topicos() -> list[Trecho]:
    linhas = db.session.execute(
        select(GuiaTopico.id, GuiaTopico.categoria, GuiaTopico.pergunta, GuiaTopico.resposta)
        .where(GuiaTopico.ativo.is_(True))
        .order_by(GuiaTopico.categoria, GuiaTopico.id)
        .limit(MAXIMO_TOPICOS)
    ).all()
    return [
        Trecho("guia", linha.id, str(linha.pergunta or ""), str(linha.resposta or ""),
               str(linha.categoria or ""), _destino_do_assunto(linha.pergunta or "", linha.categoria or ""))
        for linha in linhas
        if (linha.pergunta or "").strip() and (linha.resposta or "").strip()
    ]


class _Estado:
    def __init__(self):
        self.trava = threading.Lock()
        self.base: BaseConhecimento | None = None
        self.geracao = -1
        self.carregado_em = 0.0


def obter_base() -> BaseConhecimento:
    """Base atual; reconstrói se o Guia mudou ou o TTL expirou.

    Falha de banco não derruba o NexoBot: a base volta "degradada" (somente
    fatos do portal) e a resposta informa que o Guia não pôde ser consultado.
    """
    estado = current_app.extensions.setdefault(_CHAVE_EXTENSAO, _Estado())
    agora = time.monotonic()
    base = estado.base
    if base is not None and estado.geracao == _geracao and agora - estado.carregado_em < TTL_SEGUNDOS:
        return base
    with estado.trava:
        if (estado.base is not None and estado.geracao == _geracao
                and time.monotonic() - estado.carregado_em < TTL_SEGUNDOS):
            return estado.base
        geracao = _geracao
        try:
            topicos = _carregar_topicos()
        except SQLAlchemyError as erro:
            db.session.rollback()
            logger.warning("NexoBot: Guia indisponível (%s); usando apenas fatos do portal.",
                           type(erro).__name__)
            return BaseConhecimento((), degradado=True)
        estado.base = BaseConhecimento(topicos)
        estado.geracao = geracao
        estado.carregado_em = time.monotonic()
        return estado.base
