"""Camada E — motor de decisão: interpretação → resposta → ação autorizada.

As três etapas ficam separadas:
  1. `classificar()` entende a mensagem (não autoriza nada);
  2. este módulo escolhe a resposta (Guia, fatos do portal, catálogo, recusa);
  3. `acao_navegacao()` monta a única ação possível — navegar/sugerir — a
     partir de uma chave do catálogo fechado, com URL gerada por `url_for()`.

Nenhum caminho daqui altera dados, cria registros ou chama rotas de escrita.
O modelo generativo opcional apenas redige texto e nunca define a ação.
"""

import logging
import re
import time
import uuid

from . import providers, respostas
from .classificacao import classificar
from .conhecimento import Resultado, obter_base, tipo_de_pergunta
from .contexto import Contexto
from .intencoes import Intencao, Interpretacao
from .lexico import STOPWORDS
from .navegacao import FORTE, acao_navegacao, opcao_navegacao
from .normalizacao import PONTUACAO, TextoNormalizado, normalizar

logger = logging.getLogger("nexobot")

_NAO_PAGINAS = (
    (re.compile(r"\bnotificac"), "As notificações ficam no sininho, no topo da página."),
    (re.compile(r"\bsenhas?\b"), "Para trocar a senha, use “Esqueci minha senha” na tela de login."),
    (re.compile(r"\b(?:sair|logout|deslog\w*)\b"), "Para sair, use “Sair” no fim do menu lateral."),
    (re.compile(r"\b(?:perfil|cadastro|configurac\w*|minha conta|meus dados cadastrais)\b"),
     "O portal do cliente não tem página de perfil; para alterar dados cadastrais, abra um chamado em Suporte."),
)
_SEM_CALCULO = re.compile(r"\b(?:lucro|lucrei|margem|margens|cmv|rentabilidade|prejuizo)\b")


def responder(mensagem, ultimo_destino=None, contexto=None, pagina_atual=None) -> dict:
    """Resposta completa do NexoBot. Não lança exceção para entradas de usuário."""
    inicio = time.perf_counter()
    correlacao = uuid.uuid4().hex[:12]
    ctx = Contexto.da_requisicao(ultimo_destino, contexto, pagina_atual)
    texto = normalizar(mensagem)
    interpretacao = classificar(texto, ctx)
    saida = _Decisao(interpretacao, texto, ctx, correlacao).executar()
    duracao = (time.perf_counter() - inicio) * 1000
    logger.info(
        "nexobot correlacao=%s intencao=%s confianca=%.2f origem=%s acao=%s ms=%.1f",
        correlacao, saida["meta"]["intencao"], saida["meta"]["confianca"],
        saida["meta"]["origem"], saida.get("acao") or "-", duracao,
    )
    return saida


class _Decisao:
    def __init__(self, interpretacao: Interpretacao, texto: TextoNormalizado, ctx: Contexto,
                 correlacao: str):
        self.i = interpretacao
        self.texto = texto
        self.ctx = ctx
        self.correlacao = correlacao
        self.semente = texto.canonico or texto.bruto
        self.degradado = False
        self.origem = "sistema"
        self.intencao = interpretacao.intencao
        self.confianca = interpretacao.confianca

    # -- montagem --------------------------------------------------------
    def _saida(self, resposta: str, acao: str | None = None, destino: str | None = None,
               opcoes=(), contexto: dict | None = None, fonte: str = "local") -> dict:
        saida = {"resposta": resposta, "fonte": fonte, "acao": None, "destino": None}
        if acao and destino:
            saida.update(acao_navegacao(acao, destino))
        botoes = [b for b in (opcao_navegacao(o) for o in opcoes) if b]
        if botoes:
            saida["opcoes"] = botoes
        if self.i.saudacao and self.intencao not in (Intencao.SAUDACAO, Intencao.NAVEGAR) and resposta:
            saida["resposta"] = "Olá! " + resposta
        saida["contexto"] = contexto if contexto is not None else self.ctx.avancar()
        saida["meta"] = {
            "intencao": self.intencao.value,
            "confianca": round(float(self.confianca), 2),
            "origem": self.origem,
            "motivo": self.i.motivo,
            "correlacao": self.correlacao,
        }
        if self.degradado:
            saida["meta"]["degradado"] = True
        return saida

    def _base(self):
        """Base de conhecimento; falhas inesperadas viram modo degradado registrado."""
        try:
            base = obter_base()
        except Exception:  # noqa: BLE001 — registrado com traceback, sem dados do usuário
            logger.exception("NexoBot: falha ao montar a base de conhecimento (correlacao=%s).",
                             self.correlacao)
            self.degradado = True
            return None
        self.degradado = base.degradado
        return base

    def _categorias(self) -> list:
        base = self._base()
        return base.categorias() if base else []

    # -- roteamento por intenção -------------------------------------------
    def executar(self) -> dict:
        tratador = getattr(self, f"_{self.intencao.value}", None) or self._informativa
        return tratador()

    def _vazia(self):
        return self._saida(respostas.VAZIA, contexto=self.ctx.manter())

    def _sem_texto(self):
        return self._saida(respostas.SEM_TEXTO, contexto=self.ctx.manter())

    def _saudacao(self):
        return self._saida(respostas.saudacao(self._categorias(), self.semente), contexto=self.ctx.manter())

    def _despedida(self):
        return self._saida(respostas.despedida(self.semente), contexto=self.ctx.manter())

    def _ajuda_geral(self):
        return self._saida(respostas.ajuda_geral(self._categorias()), contexto=self.ctx.manter())

    def _confirmacao(self):
        return self._saida(respostas.CONFIRMACAO_SEM_CONTEXTO)

    def _recusa(self):
        return self._saida(respostas.RECUSA)

    def _comando_negado(self):
        return self._saida(respostas.NEGADA)

    def _navegar(self):
        self.origem = "catalogo"
        destino = self.i.destino
        return self._saida(respostas.navegando(destino), "navegar", destino,
                           contexto=self.ctx.avancar(destino))

    def _pagina_atual(self):
        self.origem = "catalogo"
        return self._saida(respostas.pagina_atual(self.i.destino), contexto=self.ctx.avancar(self.i.destino))

    def _ambiguidade(self):
        motivo = self.i.motivo
        if motivo == "relatorio_ambiguo":
            opcoes = self.i.opcoes
            return self._saida(respostas.esclarecer_relatorio(), opcoes=opcoes,
                               contexto=self.ctx.avancar(opcoes=opcoes, modo_opcoes="orientar"))
        if self.i.opcoes:
            return self._saida(respostas.esclarecer_destinos(self.i.opcoes, self.i.modo_opcoes),
                               opcoes=self.i.opcoes,
                               contexto=self.ctx.avancar(opcoes=self.i.opcoes, modo_opcoes=self.i.modo_opcoes))
        if motivo == "pergunta_incompleta":
            return self._saida(respostas.PERGUNTA_INCOMPLETA)
        if any(p in {"portal", "sistema", "site", "plataforma"} for p in self.texto.palavras):
            return self._saida(respostas.LUGAR_GENERICO)
        return self._saida(respostas.REFERENCIA_SEM_CONTEXTO)

    def _operacao_nao_permitida(self):
        texto, sugestao = respostas.operacao(self.i.operacoes, self.texto.canonico)
        destino = self.i.destino or sugestao
        if destino == self.ctx.pagina_atual:
            destino = None
        if destino:
            return self._saida(texto, "sugerir_navegacao", destino,
                               contexto=self.ctx.avancar(destino, oferecido=True))
        return self._saida(texto)

    def _acesso_restrito(self):
        texto = respostas.ACESSO_ADMIN if self.i.motivo == "admin" else respostas.ACESSO_URL
        return self._saida(texto)

    def _pagina_inexistente(self):
        dicas = [dica for padrao, dica in _NAO_PAGINAS if padrao.search(self.texto.canonico)]
        texto = respostas.PAGINA_INEXISTENTE + (" " + dicas[0] if dicas else "")
        return self._saida(texto)

    def _fora_do_escopo(self):
        if re.search(r"\b(?:acoes|acao|bolsa|investir|investimentos?|bitcoin|cripto\w*)\b", self.texto.canonico):
            return self._saida(respostas.INVESTIMENTO)
        return self._saida(respostas.variante(respostas.FORA_ESCOPO, self.semente))

    def _entrada_suspeita(self):
        texto = respostas.INJECAO if self.i.motivo == "injecao" else respostas.CODIGO
        return self._saida(texto)

    def _consulta_dados(self):
        if self.i.motivo == "outra_empresa":
            return self._saida(respostas.OUTRA_EMPRESA)
        texto = respostas.DADOS
        if _SEM_CALCULO.search(self.texto.canonico):
            texto += respostas.DADOS_NAO_CALCULADOS
        return self._sugerir(texto, "dashboard")

    def _suporte_humano(self):
        return self._sugerir(respostas.SUPORTE_HUMANO, "suporte")

    def _sobre_o_bot(self):
        return self._saida(respostas.SOBRE_O_BOT)

    def _sugerir(self, texto: str, destino: str | None):
        if not destino:
            return self._saida(texto)
        self.origem = self.origem if self.origem != "sistema" else "catalogo"
        if destino == self.ctx.pagina_atual:
            # Já está na página: explica sem oferecer botão para ela mesma.
            return self._saida(texto, contexto=self.ctx.avancar(destino))
        return self._saida(texto, "sugerir_navegacao", destino,
                           contexto=self.ctx.avancar(destino, oferecido=True))

    # -- perguntas e orientação ------------------------------------------
    def _informativa(self):
        i = self.i
        if len(i.detalhes.get("partes", ())) >= 2:
            return self._varias_perguntas(i.detalhes["partes"])
        if i.opcoes:
            self.origem = "catalogo"
            return self._saida(respostas.orientacao_varios(i.opcoes), opcoes=i.opcoes,
                               contexto=self.ctx.avancar(opcoes=i.opcoes, modo_opcoes="orientar"))
        destino_forte = i.destino if i.forca_destino >= FORTE else None
        base = self._base()
        resultado = self._buscar(base, destino_forte)
        localizacao = i.intencao == Intencao.ORIENTACAO_NAVEGACAO and destino_forte

        if resultado and resultado.trecho and resultado.ambiguo and not localizacao:
            self.origem = "guia"
            self.intencao = Intencao.AMBIGUIDADE
            self.confianca = resultado.confianca
            trechos = (resultado.trecho, *resultado.alternativas)
            return self._saida(respostas.topicos_ambiguos(trechos))

        usar_trecho = bool(resultado and resultado.trecho) and (
            not localizacao or (resultado.trecho.origem == "guia" and resultado.nivel == "alta"
                                and resultado.trecho.destino in (None, destino_forte)))
        if usar_trecho:
            trecho = resultado.trecho
            self.origem = trecho.origem
            if self.intencao == Intencao.DESCONHECIDA:
                self.intencao = Intencao.DUVIDA_FUNCIONAL
            self.confianca = max(self.confianca, resultado.confianca)
            fonte, texto = "local", respostas.topico(trecho, resultado.nivel)
            if trecho.origem == "guia" and providers.configurado():
                redigido = providers.redigir(self.texto.original, (trecho, *resultado.alternativas))
                if redigido:
                    fonte, texto, self.origem = "hf", redigido, "ia"
            destino = destino_forte or trecho.destino or (
                i.destino if i.intencao == Intencao.ORIENTACAO_NAVEGACAO else None)
            return self._sugerir_com(texto, destino, fonte)

        destino = destino_forte or (i.destino if i.intencao == Intencao.ORIENTACAO_NAVEGACAO else None)
        if destino:
            self.origem = "catalogo"
            if self.intencao == Intencao.DESCONHECIDA:
                self.intencao = Intencao.ORIENTACAO_NAVEGACAO
            oferecer = destino != self.ctx.pagina_atual
            texto = respostas.orientacao(destino, self.semente, oferecer=oferecer)
            return self._sugerir(texto, destino)

        if self.degradado:
            return self._saida(respostas.GUIA_INDISPONIVEL, opcoes=("suporte",))
        if self.intencao == Intencao.DESCONHECIDA:
            return self._saida(respostas.variante(respostas.DESCONHECIDA, self.semente))
        self.confianca = min(self.confianca, 0.4)
        return self._saida(respostas.SEM_INFORMACAO, opcoes=("guia", "suporte"))

    def _varias_perguntas(self, partes):
        """Responde até duas perguntas independentes da mesma mensagem."""
        base = self._base()
        textos, destinos, origens = [], [], []
        for parte in partes[:2]:
            destino_forte = parte["destino"] if parte["forca"] >= FORTE else None
            resultado = self._buscar(base, destino_forte, parte["consulta"])
            trecho = resultado.trecho if resultado and not resultado.ambiguo else None
            if trecho and parte["localizacao"] and destino_forte and not (
                    trecho.origem == "guia" and resultado.nivel == "alta"):
                trecho = None  # "onde fica X?": a orientação do catálogo responde melhor
            if trecho:
                textos.append(respostas.topico(trecho, resultado.nivel))
                destinos.append(destino_forte or trecho.destino)
                origens.append(trecho.origem)
            elif destino_forte:
                textos.append(respostas.orientacao(destino_forte, self.semente, oferecer=False))
                destinos.append(destino_forte)
                origens.append("catalogo")
            else:
                textos.append(respostas.PARTE_SEM_INFORMACAO)
        self.origem = origens[0] if origens else "sistema"
        destinos = [d for d in dict.fromkeys(destinos) if d and d != self.ctx.pagina_atual]
        texto = "\n\n".join(textos)
        if len(destinos) > 1:
            return self._saida(texto, opcoes=destinos,
                               contexto=self.ctx.avancar(opcoes=destinos, modo_opcoes="orientar"))
        return self._sugerir(texto, destinos[0] if destinos else None)

    def _sugerir_com(self, texto: str, destino: str | None, fonte: str):
        saida = self._sugerir(texto, destino)
        saida["fonte"] = fonte
        return saida

    def _buscar(self, base, destino_forte, consulta: str | None = None) -> Resultado | None:
        if base is None:
            return None
        consulta = consulta or self.i.consulta or self.texto.canonico
        palavras = [p for p in consulta.split() if p not in PONTUACAO and p not in STOPWORDS]
        if not palavras:
            return None
        try:
            return base.buscar(palavras, destino_forte, tipo_de_pergunta(consulta))
        except Exception:  # noqa: BLE001 — dado inesperado no índice; registrado e degradado
            logger.exception("NexoBot: falha na busca do Guia (correlacao=%s).", self.correlacao)
            self.degradado = True
            return None
