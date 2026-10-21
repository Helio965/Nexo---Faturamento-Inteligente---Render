"""Fatos da interface do portal do cliente usados como apoio ao Guia.

Cada fato descreve um comportamento VERIFICÁVEL no código (fonte indicada).
Eles só respondem quando o Guia cadastrado pelo administrador não tem uma
orientação confiável para a pergunta: o Guia continua sendo a fonte
principal. Mudou o comportamento do portal? Atualize o fato e a referência.
Nenhum fato contém valores, prazos de negócio ou dados de empresas.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fato:
    chave: str
    pergunta: str          # formulação típica (indexada com peso alto)
    termos: str            # sinônimos e expressões que as pessoas usam
    resposta: str
    destino: str | None    # página relacionada (vira botão de sugestão)


FATOS = (
    Fato(
        "status_processamento",
        "Como sei se meu relatório foi processado?",
        "status arquivo enviado processado processamento validado validacao homologado "
        "aguardando recebido erro andamento situacao conferir acompanhar",
        # templates/cliente/upload.html (badges) e blueprints/admin.py (publicação)
        "Em Enviar Relatórios, cada arquivo enviado mostra o seu status: "
        "“Aguardando validação” enquanto a equipe NEXO confere, depois “Processado” "
        "ou “Erro”. Quando a análise é publicada, você recebe um aviso no sininho "
        "e ela passa a aparecer na Visão Geral e no Histórico.",
        "upload",
    ),
    Fato(
        "planilha_errada",
        "O que faço se enviei a planilha errada?",
        "errada errado enganado engano incorreto incorreta trocar substituir reenviar "
        "corrigir arquivo planilha relatorio outro novamente de novo",
        # blueprints/cliente.py:upload — reenvio do mesmo tipo substitui o anterior
        "Enquanto a análise estiver aberta para envio, mande novamente o arquivo do "
        "mesmo tipo (Vendas ou Compras) em Enviar Relatórios: o novo arquivo substitui "
        "o anterior. Se a análise já não aparecer para envio, abra um chamado em "
        "Suporte para a equipe NEXO avaliar.",
        "upload",
    ),
    Fato(
        "compras_e_vendas",
        "Por que preciso mandar os arquivos de compras e de vendas?",
        "porque motivo razao precisa necessario obrigatorio dois ambos compras vendas "
        "arquivos relatorios",
        # etl_processor.py — Curva ABC (vendas) e saldo compras - vendas
        "Os dois arquivos alimentam a análise: o de Vendas gera o faturamento e a "
        "Curva ABC dos produtos, e o de Compras é comparado com as vendas no "
        "Indicador de Pressão de Estoque. Por isso a análise só segue para validação "
        "quando os dois foram recebidos.",
        "upload",
    ),
    Fato(
        "publicacao",
        "O que acontece quando minha análise é publicada?",
        "publicada publicacao publicar disponivel pronta concluida liberada devolutiva "
        "aviso avisado notificado notificacao email resultado",
        # blueprints/admin.py:analise_relatorio (publicar) e notifications.py
        "Quando a equipe NEXO publica a devolutiva, você recebe uma notificação no "
        "sininho (e um e-mail, quando o envio de e-mails está ativo). A análise passa "
        "a aparecer na Visão Geral e no Histórico, onde também pode ser exportada em PDF.",
        "historico",
    ),
    Fato(
        "analise_anterior",
        "Posso consultar uma análise anterior?",
        "consultar ver rever acessar abrir analise anterior antiga passada historico "
        "meses anteriores pdf exportar baixar",
        # blueprints/cliente.py:historico, analise e analise_pdf
        "Sim. O Histórico lista todas as análises já publicadas para a sua empresa. "
        "Abra uma delas para ver os detalhes e use a exportação em PDF, se precisar.",
        "historico",
    ),
    Fato(
        "pressao_estoque",
        "O que significa o Indicador de Pressão de Estoque?",
        "indicador pressao estoque significa significado quer dizer entender saldo "
        "positivo negativo giro saudavel equilibrio",
        # templates/_macros.html:nota_pressao e templates/cliente/dashboard.html
        "É uma sinalização gerencial estimada que compara o total comprado com o "
        "total vendido no período. Valor positivo indica que se comprou mais do que "
        "se vendeu (pressão de estoque); negativo indica giro saudável. Segundo o "
        "próprio portal, ele não representa lucro, margem, CMV nem estoque físico real.",
        "dashboard",
    ),
    Fato(
        "curva_abc",
        "O que é a Curva ABC?",
        "curva abc classe a b c classificacao produtos pareto estrategico tatico "
        "operacional ranking faturamento produto",
        # templates/_macros.html:badge_abc e templates/cliente/dashboard.html
        "A Curva ABC classifica os produtos pelo faturamento: Classe A são os "
        "estratégicos (núcleo do faturamento), B os táticos (faixa intermediária) e "
        "C os operacionais (cauda longa). O gráfico de Pareto mostra o faturamento "
        "por produto e o percentual acumulado.",
        "dashboard",
    ),
    Fato(
        "notificacoes",
        "Como recebo as notificações?",
        "notificacao notificacoes aviso avisos sininho sino alerta alertas receber "
        "recebo avisado email",
        # templates/base.html (sininho) e notifications.py
        "Os avisos aparecem no sininho, no topo da página, inclusive em tempo real. "
        "Clique em um aviso para abrir o item relacionado e use “Marcar todas como "
        "lidas” para limpar a contagem.",
        None,
    ),
    Fato(
        "acesso_portal",
        "Não consigo entrar no portal. O que faço?",
        "entrar login logar acessar acesso conta bloqueada desativada senha esqueci "
        "consigo entro portal erro",
        # blueprints/auth.py (login, recuperação com link de 15 minutos)
        "Confira o e-mail e a senha digitados. Se esqueceu a senha, use “Esqueci minha "
        "senha” na tela de login: enviamos um link de redefinição válido por 15 "
        "minutos. Se aparecer a mensagem de conta desativada, fale com a equipe NEXO.",
        None,
    ),
    Fato(
        "chamados_status",
        "Como acompanho meus chamados?",
        "chamado chamados ticket tickets acompanhar status resposta respondido resolvido "
        "reabrir aberto atendimento",
        # blueprints/cliente.py:tickets e ticket_detalhe
        "Em Suporte você vê os seus chamados e as respostas da equipe NEXO. Um "
        "chamado resolvido pode ser reaberto: basta enviar uma nova mensagem nele.",
        "suporte",
    ),
    Fato(
        "conta_suspensa",
        "Minha conta está suspensa. O que posso fazer?",
        "suspensa suspensao conta bloqueada entregas bloqueadas",
        # templates/cliente/dashboard.html (aviso de conta suspensa)
        "Com a conta suspensa você continua acessando o histórico de análises "
        "publicadas, mas novas entregas ficam temporariamente bloqueadas. Para "
        "regularizar, fale com a equipe NEXO pelo Suporte.",
        "suporte",
    ),
)
