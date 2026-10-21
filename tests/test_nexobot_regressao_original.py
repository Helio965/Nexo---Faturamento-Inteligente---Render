"""Regressão: cenários do tests/test_nexobot.py do repositório original.

Executar da raiz: python -m unittest tests.test_nexobot_regressao_original -v

As frases e as expectativas de navegação foram preservadas. Diferenças de
contrato intencionais do NexoBot Advanced (documentadas em
Docs/NEXOBOT_ADVANCED.md):
  - navegação direta devolve `resposta` curta ("Abrindo …") em vez de "";
  - pedidos com operação proibida + página recusam a operação e oferecem a
    página como BOTÃO (`sugerir_navegacao`), sem navegar;
  - campos adicionais: `contexto`, `meta` e, em esclarecimentos, `opcoes`.
"""

import unittest

from nexobot.classificacao import classificar
from nexobot.contexto import Contexto
from nexobot.intencoes import Intencao
from nexobot.normalizacao import normalizar
from tests.test_nexobot_api import NexoBotApiBase


def parser(mensagem, contexto=None):
    return classificar(normalizar(mensagem),
                       Contexto.da_requisicao(contexto, {"oferta": contexto} if contexto else None))


COMANDOS = {
    "upload": (
        "Me leve para o upload.", "Quero que você me leve para a página de upload de compras e vendas.",
        "Me direcione para o upload.", "Me coloca na parte de envio de arquivos.",
        "Pode abrir a página de relatórios?", "Abre a área para mandar planilha.",
        "Me leve por favor para o upload.", "Me mande para o upload.",
        "Me leve para essa página de upload.", "Quero que você me direcione para esse local de upload.",
        "Quero enviar meus arquivos, me leve para o upload.", "Abre essa área de relatórios.",
        "Me leve para este local de upload.", "Abra o upload.",
        "Quero enviar meus arquivos, me leve para essa página de upload.",
    ),
    "dashboard": (
        "Quero abrir meu dashboard.", "Me leve para o dashboard.", "Abra meu painel inicial.",
        "Abra a tela inicial do cliente.", "QUERO ACESSAR A VISÃO GERAL AGORA!", "Abra agora meu painel.",
        "Abra diretamente o meu dashboard.", "Quero ir para aquela tela do dashboard.",
        "Abra aquele painel inicial.", "Preciso ver meu faturamento, abra o dashboard.",
    ),
    "historico": (
        "Abra minhas análises anteriores.", "Quero acessar o histórico de análises.",
        "Abra meus relatórios anteriores.", "Quero acessar a página do meu histórico.",
        "ME LEVE PARA ESSA PÁGINA DO HISTÓRICO!", "Abra minha área de relatórios anteriores.",
        "Preciso consultar minhas análises anteriores, abra o histórico.",
        "Quero consultar minhas análises anteriores, abra o histórico.",
    ),
    "guia": (
        "Quero ir para o Guia.", "Acesse a página do Guia.", "Abra esta página do Guia.",
        "Abra o guia para ver um exemplo.", "Abra o Guia para saber como usar o portal.",
    ),
    "suporte": (
        "Me leve para abrir um chamado.", "Quero ir para a área de suporte.",
        "Me direcione para a área de suporte.", "Me direciona para essa parte do suporte.",
        "Quero abrir um chamado, me leve para o suporte.", "Quero criar um chamado, abre a área de suporte.",
    ),
}
COMANDOS_COM_CONTEXTO = (
    ("Estou no upload, quero abrir o histórico.", "upload", "historico"),
    ("Abra meu histórico.", "upload", "historico"),
    ("Quero abrir um chamado, me leve para o Guia.", "upload", "guia"),
    ("Quero enviar meus relatórios, abra o dashboard.", "upload", "dashboard"),
    ("Quero ir para o histórico.", "upload", "historico"),
    ("Estou no upload, me leve para histórico.", "upload", "historico"),
    ("Me leve para guia sobre upload.", "upload", "guia"),
    ("NexoBot, me leva para o histórico.", "guia", "historico"),
    ("Ah, eu quero acessar meu dashboard.", "guia", "dashboard"),
    ("Por favor, me direcione para o Guia.", "guia", "guia"),
    ("Opa, quero ir para o suporte.", "guia", "suporte"),
    ("Eu quero que você me leve para o upload.", "guia", "upload"),
)
CONTEXTUAIS = (
    "Então me leva pra lá.", "Quero ir pra essa página.", "Pode me direcionar?", "Abre esse local.",
    "Me manda pra lá.", "Quero acessar essa parte.", "Vai pra essa aba.", "Pode abrir?",
    "Então me direcione.", "Me coloca nesse local.", "Me leva pra lá.", "Pode abrir essa página?",
    "Quero ir pra esse local.", "Me coloca nessa aba.", "Então me leve até lá.", "Me leva naquela aba.",
    "Me leve naquele local.", "Eu quero que você me leve para lá.", "NexoBot, me leva pra lá.",
    "Ah, me leva pra lá.", "Opa, pode me levar para aquela página?", "Por favor, NexoBot, me direcione para lá.",
    "Bot, me leva pra lá.", "Assistente, pode abrir aquela tela?", "Ei, me leva para essa página.",
    "Bom, eu quero acessar essa parte.", "Por gentileza, me direcione para aquele lugar.",
    "NexoBot, você poderia me levar até ali?", "Opa, por favor, me coloca nessa aba.",
    "Me leva pra lá, NexoBot, por favor.", "Ah, assistente, por gentileza, pode me direcionar?",
    "EU QUERO QUE VOCÊ ME LEVE PARA LÁ!", "Ah, NexoBot, eu quero que você me leve para lá.",
    "Eu quero ir para essa página, por favor.", "Quero que me leve.",
)
INFORMATIVAS = (
    ("Onde faço upload dos arquivos de compras e vendas?", "upload"), ("Onde envio os relatórios?", "upload"),
    ("Onde fica o upload?", "upload"), ("Como acesso meu histórico?", "historico"),
    ("Como faço para acessar o upload?", "upload"), ("Como faço para acessar o dashboard?", "dashboard"),
    ("Existe uma página para ver análises anteriores?", "historico"),
    ("Como funciona a área de suporte?", "suporte"),
    ("Existe uma área onde eu possa enviar as planilhas de compras e vendas?", "upload"),
    ("Onde envio meus relatórios?", "upload"), ("Quero ver como funciona o upload.", "upload"),
    ("Preciso ver como funciona a área de suporte.", "suporte"),
    ("Quero consultar como acessar meu histórico.", "historico"),
    ("Upload: onde envio meus arquivos?", "upload"), ("Dashboard: como entro?", "dashboard"),
    ("Como faço para acessar meu dashboard?", "dashboard"),
    ("Existe uma área para consultar meus relatórios anteriores?", "historico"),
    ("Como posso abrir um chamado?", "suporte"), ("Como faço para acessar o histórico?", "historico"),
    ("Onde faço upload de compras e vendas?", "upload"),
    ("NexoBot, como faço para acessar meu dashboard?", "dashboard"),
    ("Ah, existe uma página para consultar minhas análises anteriores?", "historico"),
    ("Você pode me explicar onde fica a área de suporte?", "suporte"),
    ("Quero enviar meus relatórios.", "upload"), ("Quero enviar meus arquivos.", "upload"),
    ("Preciso fazer o upload dos arquivos de compras.", "upload"), ("Quero criar um chamado.", "suporte"),
    ("Onde envio as planilhas de compras e vendas?", "upload"),
    ("Onde ficam minhas análises anteriores?", "historico"),
)
NEGACOES = (
    "Não quero ir para o upload.", "NÃO ABRA O DASHBOARD.", "Não me leve ao histórico.", "Não me manda pra lá.",
    "Não me leve para o upload.", "Não quero abrir o dashboard.", "Não me direcione para o histórico.",
    "Não quero abrir o histórico.", "Não abra essa página de upload.", "Ah, eu não quero ir para o upload.",
    "NexoBot, não me leve para lá.", "Por gentileza, não abra aquela página.",
)
MULTIPLOS = (
    "Me leva para o dashboard ou para o histórico.", "Me leva para o upload e para o dashboard.",
    "Abra o upload e abra o histórico.", "Me leve upload ou abra dashboard.", "Quero ir upload ou abra dashboard.",
    "Abra upload ou quero abrir dashboard.", "Quero ir upload e abra dashboard.", "Abra upload e quero abrir dashboard.",
)
OPERACOES = (
    "Exclua todos os relatórios.", "Mude minha senha para 12345678.", "Execute o ETL agora.",
    "Envie um e-mail para outro@example.test.", "Crie um chamado automaticamente.",
    "Me mande para o upload e exclua todos os relatórios.", "Envie os arquivos de compras para mim.",
    "Envie meus relatórios automaticamente.", "Quero que você envie meus arquivos, me leve para o upload.",
    "Quero que você crie um chamado, abra o suporte.", "Exclua minhas análises e depois abra o dashboard.",
    "Abra o dashboard e execute o ETL.", "Publique o relatório e abra o histórico.",
    "Quero excluir minhas análises, abra o dashboard.", "Apaga minhas análises e abre o dashboard.",
    "Deleta os relatórios e abre o histórico.", "Executa o ETL e abre dashboard.",
    "Envia meus arquivos e abre o upload.", "Excluir minhas análises e abra dashboard.",
    "Abra meu dashboard. Como funciona isso? Exclua minhas análises.",
    "Quero enviar meus arquivos automaticamente, me leve upload.",
    "Preciso criar chamado automaticamente, abra suporte.", "NexoBot, exclua minhas análises.",
    "Eu quero que você envie meus relatórios automaticamente.", "Crie um chamado para mim sem abrir a página.",
    "Publique meus relatórios.", "Execute o processamento ETL.", "Ah, NexoBot, execute o ETL e me leve para lá.",
)
CITACOES = (
    "Se eu disser abra o histórico, isso vai funcionar?", "Você respondeu abra o histórico.",
    "A expressão abra upload é um exemplo.", 'Se eu falar "me leve para lá", você vai me direcionar?',
    'Se eu falar "me leve para o dashboard", você vai me direcionar?',
    'NexoBot, se eu disser "me leva pra lá", o que acontece?',
    'Ah, caso eu escreva "abra aquela página", isso vai funcionar?',
)
DESCONHECIDOS = (
    "Me leve para a página de controle de estoque físico.",
    "Me leve para página de controle estoque físico, lembra do upload?",
    "Me leve para controle de estoque upload.", "NexoBot, me leva para uma página que não existe.",
    "Ah, me leva para controle de estoque físico.", "Opa, abre essa página de cobrança fiscal.",
    "Eu quero ir para aquele módulo extraterrestre.", "Por gentileza, me leve para lá estoque.",
    "Me leva para o local do bot.", "Me leve para assistente.",
)
RELATOS = (
    "O que aconteceu lá ontem?", "Eu estava naquela página ontem.", "NexoBot, o que aconteceu lá?",
    "NexoBot, você pode explicar o que tem naquela página?", "Você pode explicar como funciona aquela página?",
    "Eu quero saber o que existe nessa área.", "Ah, NexoBot!",
)
BLOQUEADOS = (
    "Abra https://example.com.", "Me leve para //example.com/upload.", "Abra javascript:alert(1)",
    "Abra /admin/dashboard.", "Abra o upload em https://example.com.", "NexoBot, me leve para https://example.com.",
    "Ah, abra javascript:alert(1).", "Opa, me leve para //example.com/upload.",
    "Por favor, abra o painel de administração.", "Eu quero que você me leve para /admin/dashboard.",
    "Abra o painel de administração.",
)


class ParserOriginalTests(unittest.TestCase):
    def test_comandos(self):
        for destino, mensagens in COMANDOS.items():
            for mensagem in mensagens:
                with self.subTest(mensagem=mensagem):
                    i = parser(mensagem, "suporte")
                    self.assertEqual((i.intencao, i.destino), (Intencao.NAVEGAR, destino))
        for mensagem, contexto, destino in COMANDOS_COM_CONTEXTO:
            with self.subTest(mensagem=mensagem):
                i = parser(mensagem, contexto)
                self.assertEqual((i.intencao, i.destino), (Intencao.NAVEGAR, destino))

    def test_contextuais_com_e_sem_contexto(self):
        for mensagem in CONTEXTUAIS:
            for contexto in ("guia", "upload"):
                with self.subTest(mensagem=mensagem, contexto=contexto):
                    i = parser(mensagem, contexto)
                    self.assertEqual((i.intencao, i.destino), (Intencao.NAVEGAR, contexto))
            for invalido in (None, "", "admin", "/cliente/upload", "https://example.com", "inexistente"):
                with self.subTest(mensagem=mensagem, contexto=invalido):
                    self.assertEqual(parser(mensagem, invalido).intencao, Intencao.AMBIGUIDADE)

    def test_informativas_oferecem_botao(self):
        for mensagem, destino in INFORMATIVAS:
            with self.subTest(mensagem=mensagem):
                i = parser(mensagem, "guia")
                self.assertIn(i.intencao, (Intencao.ORIENTACAO_NAVEGACAO, Intencao.DUVIDA_FUNCIONAL))
                self.assertEqual(i.destino, destino)

    def test_bloqueios(self):
        casos = ((NEGACOES, {Intencao.COMANDO_NEGADO}), (MULTIPLOS, {Intencao.AMBIGUIDADE}),
                 (OPERACOES, {Intencao.OPERACAO_NAO_PERMITIDA}), (CITACOES, {Intencao.SOBRE_O_BOT}),
                 (DESCONHECIDOS, {Intencao.PAGINA_INEXISTENTE}),
                 (BLOQUEADOS, {Intencao.ACESSO_RESTRITO, Intencao.ENTRADA_SUSPEITA}))
        for mensagens, esperadas in casos:
            for mensagem in mensagens:
                with self.subTest(mensagem=mensagem):
                    self.assertIn(parser(mensagem, "upload").intencao, esperadas)
        for mensagem in RELATOS:
            with self.subTest(mensagem=mensagem):
                self.assertNotEqual(parser(mensagem, "upload").intencao, Intencao.NAVEGAR)


class ApiOriginalTests(NexoBotApiBase):
    def test_contrato_http_dos_cenarios_originais(self):
        for destino, mensagens in COMANDOS.items():
            for mensagem in mensagens:
                with self.subTest(mensagem=mensagem):
                    d = self.perguntar(mensagem)
                    self.assertEqual((d["acao"], d["destino"]), ("navegar", destino))
        for mensagem, destino in INFORMATIVAS:
            with self.subTest(mensagem=mensagem):
                d = self.perguntar(mensagem)
                self.assertEqual((d["acao"], d["destino"]), ("sugerir_navegacao", destino))
        for mensagem in (*NEGACOES, *MULTIPLOS, *CITACOES, *DESCONHECIDOS, *RELATOS, *BLOQUEADOS):
            with self.subTest(mensagem=mensagem):
                d = self.perguntar(mensagem, {"ultimo_destino": "upload", "oferta": "upload"})
                self.assertNotEqual(d["acao"], "navegar")
                if mensagem in (*NEGACOES, *MULTIPLOS, *DESCONHECIDOS, *BLOQUEADOS):
                    self.assertIsNone(d["acao"])
        for mensagem in OPERACOES:
            with self.subTest(mensagem=mensagem):
                d = self.perguntar(mensagem, {"ultimo_destino": "upload"})
                self.assertNotEqual(d["acao"], "navegar")
                self.assertIn("Não posso", d["resposta"])

    def test_suporte_e_upload_sem_efeitos_colaterais(self):
        antes = self.contagens()
        for mensagem in ("Me leve para abrir um chamado.", "Quero abrir um chamado, me leve para o suporte.",
                         "Quero criar um chamado.", "Abra o upload."):
            self.perguntar(mensagem)
        self.assertEqual(self.contagens(), antes)

    def test_emails_e_notificacoes_nao_inventam_rotas(self):
        for mensagem in ("Onde vejo os e-mails enviados?", "Como recebo as notificações?"):
            with self.subTest(mensagem=mensagem):
                d = self.perguntar(mensagem)
                self.assertNotEqual(d["acao"], "navegar")


if __name__ == "__main__":
    unittest.main()
