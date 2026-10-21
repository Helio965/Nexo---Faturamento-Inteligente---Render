"""Redação das respostas locais, por intenção e nível de confiança.

As variações evitam repetir sempre a mesma frase, mas são escolhidas de forma
determinística (hash da mensagem normalizada): a mesma pergunta recebe a mesma
resposta, o que mantém testes e diagnóstico reproduzíveis. Nenhum texto
inventa valores, prazos ou funcionalidades: os fatos vêm do catálogo
(`navegacao.py`), do Guia ou de `portal.py`.
"""

import hashlib
import re

from .navegacao import DESTINOS, ROTULOS, lista_rotulos


def variante(opcoes, semente: str) -> str:
    indice = int(hashlib.sha256(semente.encode("utf-8")).hexdigest()[:8], 16) % len(opcoes)
    return opcoes[indice]


PAGINAS = lista_rotulos()


def saudacao(categorias, semente: str) -> str:
    assuntos = ", ".join(categorias[:6]) if categorias else "envio de relatórios, senha e navegação"
    abertura = variante(("Olá! Eu sou o NexoBot.", "Oi! Aqui é o NexoBot.", "Olá! Sou o NexoBot, assistente do portal."),
                        semente)
    return (f"{abertura} Posso tirar dúvidas sobre o uso do portal ({assuntos}) e abrir "
            f"as páginas {PAGINAS}. Como posso ajudar?")


def ajuda_geral(categorias) -> str:
    assuntos = ", ".join(categorias[:8]) if categorias else "o uso do portal"
    return (
        "Posso ajudar de três formas:\n"
        f"• Responder dúvidas a partir do Guia do portal (assuntos: {assuntos}).\n"
        f"• Abrir páginas: {PAGINAS}. Basta pedir, por exemplo, “abra o histórico”.\n"
        "• Explicar onde fica cada funcionalidade, com um botão para você ir até lá.\n"
        "Não executo envios, exclusões nem alterações, e não tenho acesso aos valores "
        "das suas análises por esta conversa."
    )


def despedida(semente: str) -> str:
    return variante((
        "Por nada! Se precisar, é só chamar.",
        "Disponha! Estou por aqui se surgir outra dúvida.",
        "Imagina! Qualquer coisa, é só escrever.",
    ), semente)


VAZIA = "Pode escrever sua dúvida sobre o portal que eu te ajudo."
SEM_TEXTO = ("Recebi só símbolos ou emojis e não consegui identificar uma pergunta. "
             "Escreva em poucas palavras o que você precisa, por exemplo: “onde envio meus relatórios?”.")
NEGADA = "Tudo bem. Vou manter você na página atual."
RECUSA = "Tudo bem! Se precisar de outra coisa, é só chamar."
CONFIRMACAO_SEM_CONTEXTO = (f"Certo! Me diga o que você precisa ou qual página deseja abrir: {PAGINAS}.")
REFERENCIA_SEM_CONTEXTO = f"Qual página você deseja abrir: {PAGINAS}?"
PERGUNTA_INCOMPLETA = ("Sobre qual parte do portal é a sua dúvida? Posso explicar, por exemplo, "
                       "como enviar relatórios, consultar análises anteriores ou recuperar a senha.")
LUGAR_GENERICO = f"Você já está no portal NEXO. Qual página deseja abrir: {PAGINAS}?"
PAGINA_INEXISTENTE = ("Essa página não faz parte das áreas que posso abrir. "
                      f"As disponíveis são: {PAGINAS}. Qual delas você deseja?")
SUPORTE_HUMANO = ("Para falar com a equipe NEXO, abra um chamado na página Suporte: "
                  "lá você descreve a sua dúvida e acompanha as respostas. Quer ir até lá?")
SOBRE_O_BOT = (
    "Quando você me pede diretamente — por exemplo, “abra o histórico” — eu abro a página na hora. "
    "Perguntas como “onde fica o histórico?” recebem uma explicação e um botão, sem sair da página. "
    f"Só abro as páginas do portal do cliente: {PAGINAS}."
)
ACESSO_URL = (f"Por segurança, não abro endereços, links ou caminhos digitados. "
              f"Posso abrir somente as páginas do portal: {PAGINAS}.")
ACESSO_ADMIN = ("A área administrativa é exclusiva da equipe NEXO e não pode ser aberta por aqui. "
                "Se precisar falar com a equipe, use a página Suporte.")
INJECAO = ("Não posso mudar as minhas regras de funcionamento. Sigo ajudando com o uso do portal NEXO: "
           "dúvidas do Guia e acesso às páginas do cliente.")
CODIGO = ("Não executo comandos, códigos ou consultas enviados pela conversa. "
          "Posso orientar sobre o uso do portal e abrir as páginas do cliente.")
OUTRA_EMPRESA = ("Não tenho acesso a dados de empresas por esta conversa — nem da sua, nem de outras. "
                 "Cada cliente vê apenas as análises da própria empresa, dentro do portal.")
DADOS = ("Não tenho acesso aos valores das suas análises por esta conversa. Você pode consultar os "
         "indicadores disponíveis na Visão Geral e, para análises anteriores, no Histórico.")
DADOS_NAO_CALCULADOS = (" O portal também não apresenta lucro, margem ou CMV: os indicadores são "
                        "sinalizações gerenciais estimadas.")
FORA_ESCOPO = (
    "Sou o assistente do portal NEXO e só consigo ajudar com o uso do portal: envio de relatórios, "
    "análises publicadas, Guia e Suporte. Para outros assuntos, não tenho como responder.",
    "Esse assunto foge do que eu consigo fazer: sou focado no uso do portal NEXO. Posso ajudar com "
    "envio de relatórios, histórico de análises, senha de acesso ou abrir um chamado.",
)
INVESTIMENTO = ("Não dou recomendações de investimento ou de compra de ações. Posso ajudar com o uso "
                "do portal NEXO, como enviar relatórios ou consultar suas análises.")
DESCONHECIDA = (
    "Não tenho certeza se entendi. Você pode reformular em poucas palavras? Posso explicar como "
    f"enviar relatórios, consultar análises e recuperar a senha, ou abrir {PAGINAS}.",
    "Não encontrei uma orientação para essa mensagem. Tente descrever o que você quer fazer no portal "
    "— por exemplo, “onde vejo minhas análises anteriores?”. Se preferir, consulte o Guia ou abra um "
    "chamado em Suporte.",
)
SEM_INFORMACAO = ("Não encontrei uma orientação específica para isso. Você pode consultar o Guia ou "
                  "abrir um chamado para a equipe NEXO.")
PARTE_SEM_INFORMACAO = ("Sobre a outra dúvida, não encontrei uma orientação específica. "
                        "Você pode consultar o Guia ou abrir um chamado para a equipe NEXO.")
GUIA_INDISPONIVEL = ("No momento não consegui consultar o Guia do portal. Tente novamente em instantes; "
                     "se for urgente, abra um chamado em Suporte.")


def navegando(destino: str) -> str:
    return f"Abrindo {ROTULOS[destino]}…"


def pagina_atual(destino: str) -> str:
    return f"Você já está em {ROTULOS[destino]}."


def orientacao(destino: str, semente: str, oferecer: bool = True) -> str:
    texto = DESTINOS[destino].orientacao
    if not oferecer:
        return texto
    convite = variante(("Quer acessar essa seção?", "Posso abrir para você.",
                        "Use o botão abaixo para ir até lá."), semente)
    return f"{texto} {convite}"


def orientacao_varios(destinos) -> str:
    return "\n\n".join(DESTINOS[d].orientacao for d in destinos if d in DESTINOS)


def esclarecer_destinos(opcoes, modo: str | None) -> str:
    nomes = lista_rotulos(opcoes)
    if modo == "navegar":
        return f"Você deseja abrir {nomes}? Escolha uma das páginas."
    return f"Sua dúvida é sobre {nomes}? Escolha uma opção."


def esclarecer_relatorio() -> str:
    return "Você quer enviar um relatório novo ou consultar um relatório anterior?"


def topico(trecho, nivel: str) -> str:
    texto = f"**{trecho.pergunta}**\n\n{trecho.resposta}"
    if nivel == "media":
        return "Encontrei esta orientação, que parece ser o que você procura:\n\n" + texto
    return texto


def topicos_ambiguos(trechos) -> str:
    itens = "\n".join(f"• {t.pergunta}" for t in trechos[:3])
    return ("Encontrei mais de um assunto parecido no Guia:\n" + itens +
            "\nQual deles você procura? Pode responder com outras palavras.")


# --- Operações recusadas ----------------------------------------------------
_OPERACOES = (
    (r"^(?:exclu|apag|delet|remov|limp|zer)", "excluir ou apagar dados",
     "Exclusões não são feitas pelo portal do cliente. Se precisar, abra um chamado em Suporte.",
     "suporte"),
    (r"^(?:publiq|public|despubliq|despublic)", "publicar ou despublicar análises",
     "A publicação é feita pela equipe NEXO depois da validação, e você é avisado no sininho "
     "quando ela acontece.", None),
    (r"^(?:execut|rod|process|reprocess|homolog|aprov|dispar|recalcul)", "processar arquivos ou executar rotinas",
     "O processamento é feito pela equipe NEXO depois que os dois arquivos são enviados e validados.",
     "upload"),
    (r"^(?:envi|mand|anex|import|reenvi)", "enviar arquivos ou mensagens por você",
     "Você mesmo pode anexar os arquivos de Vendas e Compras em Enviar Relatórios.", "upload"),
    (r"^(?:cri|cadastr|ger)", "criar registros ou chamados por você",
     "Para falar com a equipe NEXO, você pode abrir um chamado na página Suporte.", "suporte"),
    (r"^(?:baix|transfer|pag)", "baixar arquivos ou fazer pagamentos por você",
     "Os PDFs das análises publicadas ficam disponíveis no Histórico.", "historico"),
    (r"^(?:cancel|bloque|desbloque|ativ|desativ|restaur|fech|encerr|reabr|respond)",
     "alterar contas, status ou chamados",
     "Pedidos desse tipo são tratados pela equipe NEXO: abra um chamado em Suporte.", "suporte"),
    (r"^(?:alter|edit|modific|mud|troc|atualiz|corrig|ajust|reset|redefin)", "alterar dados ou configurações",
     "Alterações de cadastro são tratadas pela equipe NEXO: abra um chamado em Suporte.", "suporte"),
)
_SENHA = re.compile(r"\bsenhas?\b")
_VERBO_DE_ALTERACAO = re.compile(r"^(?:alter|mud|troc|reset|redefin|atualiz|edit|modific|corrig|ger|cri)")
_EMAIL = re.compile(r"\b(?:email|emails|mensagem|mensagens)\b")


def operacao(verbos, texto: str) -> tuple[str, str | None]:
    """Texto da recusa e página sugerida para a parte que o cliente pode fazer."""
    descricoes, orientacoes, destino = [], [], None
    for verbo in verbos:
        for padrao, descricao, orientar, sugestao in _OPERACOES:
            if re.match(padrao, verbo):
                if _SENHA.search(texto) and _VERBO_DE_ALTERACAO.match(verbo):
                    descricao = "alterar a sua senha"
                    orientar = ("Para trocar a senha, use “Esqueci minha senha” na tela de login: "
                                "enviamos um link de redefinição válido por 15 minutos.")
                    sugestao = None
                elif padrao.startswith("^(?:envi") and _EMAIL.search(texto):
                    descricao, orientar, sugestao = "enviar e-mails ou mensagens", "", None
                elif padrao.startswith("^(?:cri") and re.search(r"\b(?:chamados?|tickets?)\b", texto):
                    descricao = "criar chamados por você"
                if descricao not in descricoes:
                    descricoes.append(descricao)
                if orientar and orientar not in orientacoes:
                    orientacoes.append(orientar)
                destino = destino or sugestao
                break
        else:
            if "executar ações no portal" not in descricoes:
                descricoes.append("executar ações no portal")
    lista = " nem ".join(descricoes)
    texto_final = (f"Não posso {lista} — eu apenas oriento e abro páginas do portal, sem alterar dados.")
    if orientacoes:
        texto_final += " " + " ".join(orientacoes)
    return texto_final, destino
