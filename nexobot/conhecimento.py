"""Camada C — recuperação de conhecimento: Guia (GuiaTopico) + base interna (saber).

Duas fontes alimentam a busca:
  - o Guia cadastrado no CMS do administrador (apenas tópicos ATIVOS), que
    continua sendo a fonte autorizada para orientações operacionais
    específicas da equipe;
  - a base de conhecimento versionada em `nexobot/saber`, que descreve o
    funcionamento real do NEXO (verificado no código) em quatro níveis de
    profundidade. Na saída ela aparece com origem "portal".

Prioridade: um tópico do Guia com correspondência alta vence; a base interna
vence quando responde de forma claramente mais específica ou quando o Guia
não tem resposta confiável.

Cache e invalidação (sem migrations, sem tabela nova):
  - O índice é construído sob demanda e guardado por aplicação Flask
    (`app.extensions["nexobot"]`).
  - Eventos do SQLAlchemy marcam qualquer inserção, edição, exclusão ou
    operação em massa sobre `GuiaTopico`; no COMMIT a geração global avança
    e o próximo pedido reconstrói o índice. Rollback descarta a marcação.
  - Um TTL curto cobre alterações feitas fora deste processo (outro worker,
    SQL manual). Com o `render.yaml` atual (1 worker), a invalidação é imediata.

Higiene: tópicos do Guia com sinais inequívocos de conteúdo de teste
(`higiene.py`) não são apresentados como assuntos oficiais, têm a confiança
reduzida na busca (só respondem a uma pergunta praticamente idêntica, com
confiança média) e são registrados no log para revisão administrativa. Nada é
apagado: a decisão de desativar ou excluir é da equipe, pelo CMS.

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

from . import higiene, saber
from .lexico import GENERICOS, GRUPOS_SINONIMOS, STOPWORDS
from .navegacao import FORTE, destinos_em
from .normalizacao import normalizar, sem_acentos
from .similaridade import Documento, IndiceBM25, radical

logger = logging.getLogger(__name__)

TTL_SEGUNDOS = 60
LIMIAR_ALTO = 0.6        # calibrado em tests/test_nexobot_conhecimento.py
LIMIAR_MEDIO = 0.45
MARGEM_AMBIGUIDADE = 0.06
VANTAGEM_FATO = 0.12
PENALIDADE_TESTE = 0.5   # tópico do Guia com sinais de teste: no máximo confiança média
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
    origem: str               # "guia" ou "portal" (base interna)
    chave: object
    pergunta: str
    resposta: str
    categoria: str
    destino: str | None       # página do catálogo relacionada ao assunto
    registro: object = None   # saber.Conhecimento quando origem == "portal"
    teste: bool = False       # tópico do Guia com sinais de conteúdo de teste
    motivo_teste: str | None = None


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
    ("oque", re.compile(r"\b(?:o que (?:eh|e|sao|significa|quer dizer)|significa|significado)\b")),
    ("acontece", re.compile(r"\bo que acontece\b")),
    ("errado", re.compile(r"\b(?:errad[oa]|engan\w*|incorret[oa])\b")),
    ("problema", re.compile(r"\b(?:nao consigo|nao consegui|nao estou conseguindo|nao funciona|nao funcionou|"
                            r"nao abre|nao aparece|nao aceita|nao carrega|nao entra|nao recebi|nao chegou|deu erro|"
                            r"da erro|erro ao|com erro|problema|travou|bloqueado|bloqueada|invalido|invalida|sumiu|"
                            r"desapareceu|cade)\b")),
    ("posso", re.compile(r"\b(?:posso|podemos|pode|podem|consigo|consegue|da para|tem como|eh possivel|e possivel)\b")),
    ("como_sei", re.compile(r"\bcomo (?:eu )?(?:sei|saber|vejo se|confiro)\b")),
    ("quem", re.compile(r"\bquem\b")),
    ("quando", re.compile(r"\bquando\b")),
    ("quais", re.compile(r"\bquais\b")),
    # "Como abro um chamado?": pergunta de procedimento; desempata contra "pode abrir um chamado por mim?".
    ("como", re.compile(r"^(?:\w+ ){0,2}como\b")),
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


def trechos_da_base() -> tuple:
    """Registros da base interna como trechos (origem "portal")."""
    return tuple(
        Trecho("portal", c.id, c.titulo, c.texto_indexavel(), c.categoria, c.destino, registro=c)
        for c in saber.REGISTROS
    )


def _formulacoes(trecho: Trecho) -> tuple:
    """Título e formulações equivalentes (base interna) ou só o título (Guia).

    As formulações passam pela mesma normalização das mensagens dos usuários
    ("abro" → "abrir", "pra" → "para"), para que a comparação seja justa.
    """
    textos = (trecho.pergunta, *trecho.registro.perguntas) if trecho.registro is not None else (trecho.pergunta,)
    return tuple(normalizar(t).canonico for t in textos)


class _Estruturas:
    """Índice BM25 e mapas auxiliares de um conjunto de trechos (imutáveis após criados)."""

    def __init__(self, trechos):
        trechos = tuple(trechos)
        formulacoes = {(t.origem, t.chave): _formulacoes(t) for t in trechos}
        self.indice = IndiceBM25(
            (BaseConhecimento._documento(t, formulacoes[(t.origem, t.chave)]) for t in trechos),
            genericos=GENERICOS,
        )
        self.por_chave = {(t.origem, t.chave): t for t in trechos}
        # Expressões (bigramas) de qualquer formulação do assunto.
        self.bigramas = {
            chave: set().union(*(BaseConhecimento._pares(tokenizar(f)) for f in forms))
            for chave, forms in formulacoes.items()
        }
        # Termos do "título" (formulações, categoria, termos extras): um assunto
        # citado só no corpo da resposta é indício fraco de que o tópico responde.
        self.titulos = {
            (t.origem, t.chave): {radical(p) for p in tokenizar(
                " ".join((*formulacoes[(t.origem, t.chave)], t.categoria,
                          t.registro.termos if t.registro is not None else "")))}
            for t in trechos
        }
        self.tipos = {
            chave: {tp for tp in (tipo_de_pergunta(f) for f in forms) if tp}
            for chave, forms in formulacoes.items()
        }
        genericos = {radical(g) for g in GENERICOS}
        self.formulacoes_radicais = {
            chave: [conjunto for conjunto in ({radical(p) for p in tokenizar(f)} - genericos for f in forms)
                    if conjunto]
            for chave, forms in formulacoes.items()
        }


_estruturas_internas: _Estruturas | None = None
_trava_internas = threading.Lock()


def _internas() -> _Estruturas:
    """Estruturas da base interna, construídas uma vez por processo.

    A base interna é código versionado: não muda em tempo de execução. Só a parte
    do Guia é reconstruída quando o CMS muda, o que mantém a reconstrução barata.
    """
    global _estruturas_internas
    if _estruturas_internas is None:
        with _trava_internas:
            if _estruturas_internas is None:
                _estruturas_internas = _Estruturas(trechos_da_base())
    return _estruturas_internas


class BaseConhecimento:
    """Índices imutáveis do Guia e da base interna; seguros para leitura concorrente."""

    def __init__(self, topicos, degradado: bool = False):
        self.topicos = tuple(topicos)
        self.degradado = degradado
        internas = _internas()
        guia = _Estruturas(self.topicos)
        self.fatos = tuple(internas.por_chave.values())
        self.indice_guia = guia.indice
        self.indice_fatos = internas.indice
        self._por_chave = {**guia.por_chave, **internas.por_chave}
        self._bigramas = {**guia.bigramas, **internas.bigramas}
        self._titulos = {**guia.titulos, **internas.titulos}
        self._tipos = {**guia.tipos, **internas.tipos}
        self._formulacoes_radicais = {**guia.formulacoes_radicais, **internas.formulacoes_radicais}

    @staticmethod
    def _pares(tokens) -> set:
        radicais = [radical(t) for t in tokens]
        return set(zip(radicais, radicais[1:]))

    @staticmethod
    def _documento(trecho: Trecho, formulacoes: tuple) -> Documento:
        campos = {
            "pergunta": [radical(t) for t in tokenizar(" ".join(formulacoes))],
            "categoria": [radical(t) for t in tokenizar(trecho.categoria)],
            "resposta": [radical(t) for t in tokenizar(trecho.resposta[:MAXIMO_CARACTERES_INDICE])],
        }
        if trecho.registro is not None and trecho.registro.termos:
            campos["termos"] = [radical(t) for t in tokenizar(trecho.registro.termos)]
        pesos = {"pergunta": 3.0, "categoria": 1.5, "resposta": 1.0, "termos": 2.0}
        return Documento((trecho.origem, trecho.chave), campos, pesos)

    @property
    def vazia(self) -> bool:
        return not self.topicos

    def categorias(self) -> list[str]:
        """Categorias do Guia apresentáveis ao cliente (sem conteúdo de teste)."""
        return sorted({t.categoria for t in self.topicos if t.categoria and not t.teste})

    def topicos_suspeitos(self) -> list[Trecho]:
        return [t for t in self.topicos if t.teste]

    def por_id(self, registro_id: str) -> Trecho | None:
        """Trecho da base interna pelo id do registro."""
        return self._por_chave.get(("portal", registro_id))

    def _buscar(self, indice, palavras, tipo=None) -> list:
        """Lista de (ordem, confiança, trecho), da melhor para a pior correspondência.

        - confiança: cobertura da pergunta (ponderada por IDF), reduzida quando só
          sinônimos casaram ou quando o assunto não aparece no título do tópico;
        - ordem: confiança + semelhança com a formulação mais próxima + expressões
          e tipo de pergunta em comum (desempata tópicos que citam as mesmas palavras).
        """
        consulta = montar_consulta(palavras, indice)
        termos_consulta = {termo for termo, _, _ in consulta}
        especificos_consulta = {origem for _, _, origem in consulta} - indice.genericos
        # Radicais da pergunta sem genéricos: igual a uma formulação → correspondência exata.
        consulta_radicais = {radical(p) for p in palavras if p not in STOPWORDS} - indice.genericos
        resultados = indice.buscar(consulta, limite=8)
        pares = self._pares([p for p in palavras if p not in STOPWORDS])
        maior_pontuacao = max((r.pontuacao for r in resultados), default=0.0) or 1.0
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
            if tipo and tipo in self._tipos.get(r.chave, ()):
                bonus += 0.08  # "por que...?" combina com um tópico que explica o porquê
            bonus = min(bonus, 0.15)
            formulacoes = self._formulacoes_radicais.get(r.chave, ())
            semelhanca = max((len(f & termos_consulta) / len(f) for f in formulacoes), default=0.0)
            exata = bool(consulta_radicais) and consulta_radicais in formulacoes
            trecho = self._por_chave[r.chave]
            confianca = min(1.0, cobertura + bonus)
            # Desempate entre coberturas iguais: formulação mais parecida (ou idêntica) e
            # presença mais forte dos termos no título/termos do registro (BM25).
            ordem = (cobertura + bonus + 0.2 * semelhanca + (0.1 if exata else 0.0)
                     + 0.1 * (r.pontuacao / maior_pontuacao))
            if trecho.teste:
                confianca *= PENALIDADE_TESTE
                ordem *= PENALIDADE_TESTE
            ajustados.append((ordem, confianca, r.pontuacao, trecho))
        ajustados.sort(key=lambda x: (x[0], x[2]), reverse=True)
        return [(ordem, confianca, trecho) for ordem, confianca, _, trecho in ajustados]

    def _mesmo_assunto(self, topico: Trecho, registro: Trecho) -> bool:
        """O tópico do Guia trata do mesmo assunto de um registro da base interna?

        Quando o administrador escreve um tópico com título equivalente ao de um
        registro, o Guia passa a valer: é a forma de a equipe sobrepor a base.
        """
        titulo = next(iter(self._formulacoes_radicais.get((topico.origem, topico.chave), ())), set())
        if not titulo:
            return False
        melhor = max((2 * len(titulo & f) / (len(titulo) + len(f))
                      for f in self._formulacoes_radicais.get((registro.origem, registro.chave), ())),
                     default=0.0)
        return melhor >= 0.6

    def _escolher(self, guia, fatos):
        """Prioridade entre Guia (administrador) e base interna.

        1. Guia com confiança alta vence, salvo quando a base interna é claramente
           mais confiante (+0,15) e trata de OUTRO assunto (ex.: "por que preciso
           dos dois arquivos?" contra o tópico "como fazer o upload").
        2. Base interna com confiança alta vence, salvo quando um tópico do Guia
           sobre o mesmo assunto tem confiança ao menos média.
        3. Entre correspondências médias, o Guia vence, a não ser que a base
           interna seja claramente mais específica (VANTAGEM_FATO).
        """
        g = guia[0] if guia else None
        f = fatos[0] if fatos else None
        mesmo = bool(g and f and self._mesmo_assunto(g[2], f[2]))
        if g and g[1] >= LIMIAR_ALTO and (not f or f[1] - g[1] < 0.15 or mesmo):
            return guia
        if f and f[1] >= LIMIAR_ALTO and not (g and g[1] >= LIMIAR_MEDIO and mesmo):
            return fatos
        if g and g[1] >= LIMIAR_MEDIO and (not f or f[1] < LIMIAR_MEDIO or mesmo
                                          or g[0] + VANTAGEM_FATO >= f[0]):
            return guia
        if f and f[1] >= LIMIAR_MEDIO:
            return fatos
        if g and g[1] >= LIMIAR_MEDIO:
            return guia
        return None

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
        escolhido = self._escolher(guia, fatos)
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
    trechos = []
    for linha in linhas:
        pergunta, resposta, categoria = str(linha.pergunta or ""), str(linha.resposta or ""), str(linha.categoria or "")
        if not pergunta.strip() or not resposta.strip():
            continue
        motivo = higiene.motivo_teste(categoria, pergunta, resposta)
        trechos.append(Trecho(
            "guia", linha.id, pergunta, resposta, categoria,
            _destino_do_assunto(pergunta, categoria), teste=motivo is not None, motivo_teste=motivo,
        ))
    suspeitos = [t for t in trechos if t.teste]
    if suspeitos:
        logger.warning(
            "NexoBot: %d tópico(s) ativo(s) do Guia com sinais de conteúdo de teste (ids: %s). "
            "Eles não são apresentados como assuntos ao cliente; revise e desative pelo CMS.",
            len(suspeitos), ", ".join(str(t.chave) for t in suspeitos),
        )
    return trechos


class _Estado:
    def __init__(self):
        self.trava = threading.Lock()
        self.base: BaseConhecimento | None = None
        self.geracao = -1
        self.carregado_em = 0.0


def obter_base() -> BaseConhecimento:
    """Base atual; reconstrói se o Guia mudou ou o TTL expirou.

    Falha de banco não derruba o NexoBot: a base volta "degradada" (somente
    a base interna) e a resposta informa que o Guia não pôde ser consultado.
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
            logger.warning("NexoBot: Guia indisponível (%s); usando apenas a base interna.",
                           type(erro).__name__)
            return BaseConhecimento((), degradado=True)
        estado.base = BaseConhecimento(topicos)
        estado.geracao = geracao
        estado.carregado_em = time.monotonic()
        return estado.base
