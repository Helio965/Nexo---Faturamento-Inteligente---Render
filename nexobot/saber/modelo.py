"""Modelo dos registros da base de conhecimento do NexoBot.

Cada `Conhecimento` descreve UM assunto do NEXO em quatro níveis de
profundidade, para que o motor escolha quanto mostrar conforme a pergunta:

  1. `resumo`      — resposta curta (uma ou duas frases);
  2. `explicacao`  — explicação para quem quer entender;
  3. `passos`      — passo a passo para quem quer fazer;
  4. `detalhes`    — aprofundamento: limitações, o que NÃO é, nuances.

Regras editoriais (verificadas em tests/test_nexobot_saber.py):
  - todo registro cita em `fontes` os arquivos do código que o embasam;
  - nada aqui afirma preço, prazo comercial, promoção ou funcionalidade
    que o código não implemente; roadmap aparece sempre como roadmap;
  - o texto é tratado como DADO: nunca contém URLs, HTML ou instruções;
  - `destino` só aponta para chaves do catálogo fechado (navegacao.py).
"""

from dataclasses import dataclass, field

TIPOS = frozenset({"visao_geral", "conceito", "procedimento", "regra", "tecnico", "roteiro"})
AUDIENCIAS = frozenset({"CLIENTE", "ADMIN"})


@dataclass(frozen=True)
class Conhecimento:
    id: str
    titulo: str                       # pergunta canônica, em português do Brasil
    categoria: str                    # rótulo exibido ("Visão Geral", "Indicadores"...)
    resumo: str                       # nível 1
    explicacao: str = ""              # nível 2 (parágrafos separados por linha em branco)
    passos: tuple = ()                # nível 3
    detalhes: str = ""                # nível 4
    exemplo: str = ""                 # exemplo hipotético, sempre identificado como tal
    aviso: str = ""                   # ressalva curta exibida em todos os níveis
    perguntas: tuple = ()             # formulações equivalentes (indexadas como título)
    termos: str = ""                  # sinônimos e termos de busca adicionais
    relacionados: tuple = ()          # ids sugeridos como próximas perguntas
    proximo: str | None = None        # id do passo seguinte num roteiro ("e depois?")
    destino: str | None = None        # página do catálogo relacionada
    audiencia: tuple = ("CLIENTE",)
    tipo: str = "conceito"
    fontes: tuple = field(default_factory=tuple)

    @property
    def tem_passos(self) -> bool:
        return bool(self.passos)

    def nivel_maximo(self) -> int:
        """Maior nível que acrescenta conteúdo novo a este registro."""
        if self.detalhes or self.exemplo:
            return 4
        if self.passos:
            return 3
        if self.explicacao:
            return 2
        return 1

    def texto_indexavel(self) -> str:
        """Corpo usado na busca (não é exibido): todos os níveis."""
        partes = [self.resumo, self.explicacao, *self.passos, self.detalhes, self.aviso]
        return "\n".join(p for p in partes if p)


def registro(**campos) -> Conhecimento:
    """Fábrica com validação imediata: erros de edição aparecem na importação."""
    obj = Conhecimento(**campos)
    problemas = validar(obj)
    if problemas:
        raise ValueError(f"Registro {obj.id!r} inválido: " + "; ".join(problemas))
    return obj


_PROIBIDO_NO_TEXTO = ("http://", "https://", "<script", "javascript:", "www.")


def validar(c: Conhecimento) -> list[str]:
    problemas = []
    if not c.id or c.id.count(".") < 2 or not c.id.startswith("nexo."):
        problemas.append("id deve ter o formato nexo.<assunto>.<chave>")
    if not c.titulo.strip() or not c.resumo.strip():
        problemas.append("titulo e resumo são obrigatórios")
    if c.tipo not in TIPOS:
        problemas.append(f"tipo desconhecido: {c.tipo}")
    if not c.audiencia or set(c.audiencia) - AUDIENCIAS:
        problemas.append("audiencia inválida")
    if not c.fontes:
        problemas.append("fontes (arquivos do código) são obrigatórias")
    if not c.perguntas:
        problemas.append("ao menos uma pergunta equivalente é obrigatória")
    corpo = " ".join([c.titulo, c.resumo, c.explicacao, c.detalhes, c.exemplo, c.aviso, *c.passos]).lower()
    for marca in _PROIBIDO_NO_TEXTO:
        if marca in corpo:
            problemas.append(f"texto não pode conter {marca!r}")
    if c.exemplo and "hipot" not in c.exemplo.lower():
        problemas.append("exemplo precisa ser identificado como hipotético")
    return problemas
