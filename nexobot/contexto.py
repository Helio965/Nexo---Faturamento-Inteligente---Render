"""Camada D — contexto conversacional mínimo, validado a cada requisição.

Decisão arquitetural: o servidor NÃO guarda estado de conversa. O widget
mantém, na memória da própria aba, somente identificadores do catálogo
(nunca URLs, textos ou dados da empresa) e os reenvia a cada mensagem. Assim
o contexto fica isolado por usuário, sessão e aba, desaparece ao recarregar a
página e não pode ser usado para escolher um destino fora do catálogo: tudo
que não for uma chave conhecida é descartado aqui.
"""

from dataclasses import dataclass

from .navegacao import validar_destino

MODOS_OPCOES = frozenset({"navegar", "orientar"})
MAXIMO_OPCOES = 5


@dataclass(frozen=True)
class Contexto:
    ultimo_destino: str | None = None     # destino oferecido/aberto por último
    destino_anterior: str | None = None   # o destino antes do último ("a anterior")
    opcoes: tuple = ()                    # destinos oferecidos num esclarecimento pendente
    modo_opcoes: str | None = None        # o esclarecimento era sobre abrir ou orientar
    pagina_atual: str | None = None       # página do catálogo em que o widget está
    oferta: str | None = None             # destino oferecido com botão na resposta anterior

    @classmethod
    def da_requisicao(cls, ultimo_destino=None, contexto=None, pagina_atual=None) -> "Contexto":
        """Aceita o formato legado (`ultimo_destino` solto) e o objeto `contexto`."""
        dados = contexto if isinstance(contexto, dict) else {}
        ultimo = validar_destino(dados.get("ultimo_destino")) or validar_destino(ultimo_destino)
        anterior = validar_destino(dados.get("destino_anterior"))
        opcoes_brutas = dados.get("opcoes")
        opcoes = ()
        if isinstance(opcoes_brutas, (list, tuple)):
            validas = [validar_destino(o) for o in opcoes_brutas[:MAXIMO_OPCOES]]
            opcoes = tuple(dict.fromkeys(o for o in validas if o))
        modo = dados.get("modo_opcoes") if dados.get("modo_opcoes") in MODOS_OPCOES else None
        if len(opcoes) < 2:
            opcoes, modo = (), None
        oferta = validar_destino(dados.get("oferta"))
        return cls(
            oferta=oferta if oferta == ultimo else None,
            ultimo_destino=ultimo,
            destino_anterior=anterior if anterior != ultimo else None,
            opcoes=opcoes,
            modo_opcoes=modo,
            pagina_atual=validar_destino(pagina_atual if pagina_atual is not None
                                         else dados.get("pagina_atual")),
        )

    def avancar(self, destino: str | None = None, opcoes=(), modo_opcoes=None,
                oferecido: bool = False) -> dict:
        """Contexto a devolver ao widget depois desta resposta.

        - Novo destino: vira o último; o anterior é preservado para "a anterior".
          `oferecido` indica que a resposta terminou com um convite ("Quer ir?"),
          o que autoriza um "sim" na próxima mensagem.
        - Esclarecimento: guarda as opções; mantém o último destino.
        - Nada relevante: o contexto é limpo (não se reaproveita destino antigo).
        """
        if destino:
            anterior = self.ultimo_destino if self.ultimo_destino != destino else self.destino_anterior
            return {"ultimo_destino": destino, "destino_anterior": anterior,
                    "opcoes": [], "modo_opcoes": None, "oferta": destino if oferecido else None}
        if opcoes:
            return {"ultimo_destino": self.ultimo_destino, "destino_anterior": self.destino_anterior,
                    "opcoes": list(opcoes)[:MAXIMO_OPCOES], "modo_opcoes": modo_opcoes, "oferta": None}
        return {"ultimo_destino": None, "destino_anterior": None, "opcoes": [], "modo_opcoes": None,
                "oferta": None}

    def manter(self) -> dict:
        """Cortesias não apagam a conversa, mas encerram um convite pendente."""
        return {"ultimo_destino": self.ultimo_destino, "destino_anterior": self.destino_anterior,
                "opcoes": list(self.opcoes), "modo_opcoes": self.modo_opcoes, "oferta": None}
