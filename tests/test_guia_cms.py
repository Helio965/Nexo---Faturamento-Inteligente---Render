"""CMS do Guia: publicação global, editor e autorização com SQLite descartável.

Os dados, arquivos e usuários são fictícios. A fixture bloqueia a rede e não lê
credenciais locais; nenhum teste depende de Supabase ou serviços hospedados.
"""

from io import BytesIO
import json
from unittest.mock import patch

from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from tests.deploy_support import DeployTestCase


ADMIN = "admin-test@example.invalid"
CLIENTE = "cliente-test@example.invalid"
OUTRO_CLIENTE = "outro-guia@example.invalid"


def imagem(cor="purple"):
    destino = BytesIO()
    Image.new("RGB", (24, 16), cor).save(destino, "PNG")
    return destino.getvalue()


class GuiaCMSTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        self.fixtures()
        from models import Analise, Usuario
        outra_empresa = self.db.session.get(Analise, self.outra_analise_id).id_empresa
        outro = Usuario(nome="Outro cliente fictício", email=OUTRO_CLIENTE, role="CLIENTE",
                        id_empresa=outra_empresa, primeiro_acesso=False)
        outro.set_senha(self.password)
        self.db.session.add(outro)
        self.db.session.commit()
        self.email_atual = None

    def entrar(self, email=ADMIN):
        if self.email_atual:
            self.logout()
        self.login(email)
        self.email_atual = email

    def topico(self, titulo):
        from models import GuiaTopico
        self.db.session.expire_all()
        return self.db.session.scalar(self.db.select(GuiaTopico).where(GuiaTopico.pergunta == titulo))

    def versao(self, id_topico):
        from models import GuiaEdicao
        self.db.session.expire_all()
        edicao = self.db.session.get(GuiaEdicao, id_topico)
        return edicao.versao if edicao else 0

    def salvar(self, titulo="Tutorial fictício", *, id_topico=None, status="rascunho", blocos=None,
               esperado=302, **valores):
        caminho = f"/admin/guia/editar/{id_topico}" if id_topico else "/admin/guia/novo"
        dados = {
            "categoria": "Orientações", "pergunta": titulo,
            "descricao": "Descrição fictícia para todos os clientes.", "ordem": "0", "status": status,
            "csrf_token": self.csrf_token(caminho),
            "blocos_json": json.dumps(blocos if blocos is not None else [
                {"tipo": "texto", "html": "<p>Primeiro passo de orientação fictícia.</p>"}
            ], ensure_ascii=False),
        }
        if id_topico:
            dados["versao"] = str(self.versao(id_topico))
        dados.update(valores)
        resposta = self.client.post(caminho, data=dados)
        self.assertEqual(resposta.status_code, esperado, resposta.get_data(as_text=True)[:1600])
        return resposta

    def acao(self, topico, acao, *, esperado=302, versao=None):
        resposta = self.client.post(f"/admin/guia/{topico.id}/publicacao", data={
            "acao": acao, "versao": str(self.versao(topico.id) if versao is None else versao),
            "csrf_token": self.csrf_token("/admin/guia"),
        })
        self.assertEqual(resposta.status_code, esperado, resposta.get_data(as_text=True)[:1000])
        return resposta

    def corpo_cliente(self, email=CLIENTE):
        self.entrar(email)
        resposta = self.client.get("/cliente/guia")
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_data(as_text=True)

    def test_gestao_exige_admin_e_csrf_inclusive_previa_e_publicacao(self):
        self.assertEqual(self.client.get("/admin/guia").status_code, 302)
        self.entrar()
        self.salvar()
        topico = self.topico("Tutorial fictício")
        self.assertEqual(self.client.post("/admin/guia/novo", data={}).status_code, 400)
        self.assertEqual(self.client.post(f"/admin/guia/{topico.id}/publicacao", data={"acao": "publicar"}).status_code, 400)
        self.assertEqual(self.client.post(f"/admin/guia/{topico.id}/deletar", data={}).status_code, 400)
        self.entrar(CLIENTE)
        token = self.csrf_token("/cliente/guia")
        for caminho in ("/admin/guia", "/admin/guia/novo", f"/admin/guia/editar/{topico.id}",
                        f"/admin/guia/{topico.id}/previa"):
            self.assertEqual(self.client.get(caminho).status_code, 403, caminho)
        for caminho in ("/admin/guia/novo", f"/admin/guia/editar/{topico.id}",
                        f"/admin/guia/{topico.id}/publicacao", f"/admin/guia/{topico.id}/deletar"):
            self.assertEqual(self.client.post(caminho, data={"csrf_token": token}).status_code, 403, caminho)
        self.assertNotIn("Personalizar Guia", self.client.get("/cliente/guia").get_data(as_text=True))

    def test_rascunho_publicacao_e_despublicacao_sao_globais(self):
        self.entrar()
        self.salvar("Orientação institucional exclusiva")
        topico = self.topico("Orientação institucional exclusiva")
        self.assertFalse(topico.ativo)
        for email in (CLIENTE, OUTRO_CLIENTE):
            self.assertNotIn(topico.pergunta, self.corpo_cliente(email))
        self.entrar()
        self.acao(topico, "publicar")
        for email in (CLIENTE, OUTRO_CLIENTE):
            self.assertIn(topico.pergunta, self.corpo_cliente(email))
        self.entrar()
        self.acao(topico, "despublicar")
        from models import GuiaEdicao
        self.db.session.expire_all()
        self.assertIsNotNone(self.db.session.get(GuiaEdicao, topico.id).publicado_em)
        for email in (CLIENTE, OUTRO_CLIENTE):
            self.assertNotIn(topico.pergunta, self.corpo_cliente(email))

    def test_criacao_sem_status_continua_rascunho(self):
        self.entrar()
        dados = {"categoria": "Uso", "pergunta": "Rascunho por padrão", "resposta": "Orientação não publicada.",
                 "csrf_token": self.csrf_token("/admin/guia/novo")}
        self.assertEqual(self.client.post("/admin/guia/novo", data=dados).status_code, 302)
        self.assertFalse(self.topico("Rascunho por padrão").ativo)
        self.assertNotIn("Rascunho por padrão", self.corpo_cliente())

    def test_texto_rico_preserva_formatacao_e_sanitiza_html_ativo(self):
        self.entrar()
        html = ('<h2>Título com acentuação</h2><h3>Passos</h3><p>Olá <strong>mundo</strong> '
                '<em>especial</em> &amp; símbolos.</p><ol><li>Primeiro</li><li>Segundo</li></ol>'
                '<ul><li>Alternativa</li></ul><a href="https://example.invalid/guia">Ajuda segura</a>'
                '<script>alert("xss")</script><img src=x onerror="alert(1)">'
                '<svg onload="alert(2)"><a href="javascript:alert(3)">Risco</a></svg>'
                '<a href="java&#x73;cript:alert(4)">Link perigoso</a>'
                '<iframe src="https://example.invalid/"></iframe><p style="color:red" onclick="alert(5)">Texto.</p>')
        self.salvar("Formatação e segurança", status="publicado", blocos=[{"tipo": "texto", "html": html}])
        topico = self.topico("Formatação e segurança")
        self.assertIn("Primeiro", topico.resposta)
        self.assertNotIn("<strong>", topico.resposta)
        corpo = self.corpo_cliente()
        for trecho in ("<h2>Título com acentuação</h2>", "<strong>mundo</strong>", "<em>especial</em>",
                       "<ol>", "<ul>", 'href="https://example.invalid/guia"'):
            self.assertIn(trecho, corpo)
        self.assertNotIn('<script>alert("xss")', corpo)
        self.assertNotIn('onerror="', corpo)
        self.assertNotIn('onload="', corpo)
        self.assertNotIn('onclick="alert', corpo)
        self.assertNotIn('href="javascript:', corpo.lower())
        self.assertNotIn('<iframe src=', corpo)

    def test_protocolos_perigosos_nao_viram_links_publicados(self):
        self.entrar()
        perigosos = ("javascript:alert(1)", "data:text/html,alert(1)", "vbscript:msgbox(1)", "//evil.invalid/x")
        blocos = [{"tipo": "texto", "html": "<p>Links de teste</p>" + "".join(
            f'<a href="{url}">Destino {i}</a>' for i, url in enumerate(perigosos))}]
        self.salvar("Links filtrados", status="publicado", blocos=blocos)
        corpo = self.corpo_cliente()
        for url in perigosos:
            self.assertNotIn(f'href="{url}"', corpo)

    def test_ordenacao_explicita_e_categoria_editavel(self):
        self.entrar()
        self.salvar("Segundo na categoria", status="publicado", categoria="Passos", ordem="20")
        self.salvar("Primeiro na categoria", status="publicado", categoria="Passos", ordem="10")
        corpo = self.corpo_cliente()
        self.assertLess(corpo.index("Primeiro na categoria"), corpo.index("Segundo na categoria"))
        segundo = self.topico("Segundo na categoria")
        self.entrar()
        self.salvar(segundo.pergunta, id_topico=segundo.id, status="publicado", categoria="Passos", ordem="5")
        corpo = self.corpo_cliente()
        self.assertLess(corpo.index("Segundo na categoria"), corpo.index("Primeiro na categoria"))

    def test_validacao_nao_perde_texto_digitado_e_nao_cria_registro(self):
        self.entrar()
        resposta = self.salvar("Título que deve permanecer", categoria="", esperado=400,
                              blocos=[{"tipo": "texto", "html": "<p>Texto a corrigir.</p>"}])
        corpo = resposta.get_data(as_text=True)
        self.assertIn("Título que deve permanecer", corpo)
        self.assertIn("Texto a corrigir.", corpo)
        self.assertIsNone(self.topico("Título que deve permanecer"))

    def test_versao_antiga_nao_sobrescreve_edicao_mais_recente(self):
        self.entrar()
        self.salvar("Título inicial")
        topico = self.topico("Título inicial")
        antiga = self.versao(topico.id)
        self.salvar("Título mais recente", id_topico=topico.id)
        self.salvar("Título perdido", id_topico=topico.id, versao=str(antiga), esperado=409)
        self.assertIsNotNone(self.topico("Título mais recente"))
        self.assertIsNone(self.topico("Título perdido"))

    def test_multiplas_imagens_entre_passos_legendas_ordem_e_remocao_individual(self):
        self.entrar()
        blocos = [{"tipo": "texto", "html": "<p>Passo anterior.</p>"},
                  {"tipo": "midia", "id": "nova_a", "legenda": "Tela inicial", "alt": "Captura inicial"},
                  {"tipo": "texto", "html": "<p>Passo posterior.</p>"},
                  {"tipo": "midia", "id": "nova_b", "legenda": "Tela final", "alt": "Captura final"}]
        self.salvar("Tutorial ilustrado", status="publicado", blocos=blocos,
                    midia_nova_a=(BytesIO(imagem()), "primeira.png"),
                    midia_nova_b=(BytesIO(imagem("orange")), "segunda.png"))
        from models import GuiaEdicao, GuiaMidia
        topico = self.topico("Tutorial ilustrado")
        self.db.session.expire_all()
        edicao = self.db.session.get(GuiaEdicao, topico.id)
        ids = [b["id"] for b in edicao.blocos if b["tipo"] == "midia"]
        self.assertEqual(len(ids), 2)
        medias = {m.id: m for m in self.db.session.scalars(self.db.select(GuiaMidia).where(GuiaMidia.id_topico == topico.id))}
        urls = ["/midia/" + medias[i].referencia.removeprefix("db:") for i in ids]
        corpo = self.corpo_cliente()
        self.assertLess(corpo.index("Passo anterior."), corpo.index(urls[0]))
        self.assertLess(corpo.index(urls[0]), corpo.index("Passo posterior."))
        self.assertLess(corpo.index("Passo posterior."), corpo.index(urls[1]))
        self.assertIn('alt="Captura inicial"', corpo)
        for url in urls:
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.headers["Content-Type"], "image/png")
            self.assertIn("no-store", resposta.headers["Cache-Control"])
        self.entrar()
        self.salvar(topico.pergunta, id_topico=topico.id, status="publicado", blocos=[
            {"tipo": "midia", "id": ids[1], "legenda": "Só a tela final", "alt": "Captura final"},
            {"tipo": "texto", "html": "<p>Texto reorganizado.</p>"},
        ])
        corpo = self.corpo_cliente()
        self.assertIn(urls[1], corpo)
        self.assertNotIn(urls[0], corpo)
        self.assertEqual(self.client.get(urls[0]).status_code, 404)
        self.assertEqual(self.client.get(urls[1]).status_code, 200)
        self.db.session.expire_all()
        self.assertTrue(self.db.session.get(GuiaEdicao, topico.id).historico)

    def test_midia_do_rascunho_e_despublicacao_nao_expoem_arquivo(self):
        self.entrar()
        self.salvar("Imagem reservada", blocos=[
            {"tipo": "texto", "html": "<p>Conteúdo reservado.</p>"},
            {"tipo": "midia", "id": "nova_a", "legenda": "Reservada", "alt": "Imagem reservada"}],
            midia_nova_a=(BytesIO(imagem()), "reservada.png"))
        from models import GuiaMidia
        topico = self.topico("Imagem reservada")
        midia = self.db.session.scalar(self.db.select(GuiaMidia).where(GuiaMidia.id_topico == topico.id))
        url = "/midia/" + midia.referencia.removeprefix("db:")
        self.assertEqual(self.client.get(url).status_code, 200)  # prévia privada do administrador
        for email in (CLIENTE, OUTRO_CLIENTE):
            self.entrar(email)
            self.assertEqual(self.client.get(url).status_code, 404)
        self.entrar()
        self.acao(topico, "publicar")
        self.entrar(CLIENTE)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.entrar()
        self.acao(topico, "despublicar")
        self.entrar(CLIENTE)
        self.assertEqual(self.client.get(url, headers={"If-None-Match": '"antigo"'}).status_code, 404)

    def test_nao_permite_anexar_midia_pertencente_a_outro_topico(self):
        self.entrar()
        self.salvar("Dono da imagem", blocos=[
            {"tipo": "texto", "html": "<p>Original.</p>"},
            {"tipo": "midia", "id": "nova_a", "legenda": "Original", "alt": "Original"}],
            midia_nova_a=(BytesIO(imagem()), "original.png"))
        from models import GuiaMidia
        dono = self.topico("Dono da imagem")
        id_midia = self.db.session.scalar(self.db.select(GuiaMidia.id).where(GuiaMidia.id_topico == dono.id))
        self.salvar("Tentativa de apropriação", blocos=[
            {"tipo": "texto", "html": "<p>Outro tópico.</p>"},
            {"tipo": "midia", "id": id_midia, "legenda": "Adulterada", "alt": "Adulterada"}], esperado=400)
        self.assertIsNone(self.topico("Tentativa de apropriação"))

    def test_upload_invalido_nao_publica_parcialmente_nem_substitui_original(self):
        self.entrar()
        self.salvar("Sem substituição parcial", status="publicado")
        topico = self.topico("Sem substituição parcial")
        resposta_anterior = topico.resposta
        self.salvar(topico.pergunta, id_topico=topico.id, status="publicado", esperado=400, blocos=[
            {"tipo": "texto", "html": "<p>Texto que não deve persistir.</p>"},
            {"tipo": "midia", "id": "nova_x", "legenda": "Inválida", "alt": "Inválida"}],
            midia_nova_x=(BytesIO(b"arquivo executavel disfarcado"), "falso.png"))
        self.assertEqual(self.topico(topico.pergunta).resposta, resposta_anterior)

    def test_falha_no_storage_desfaz_topico_metadados_e_publicacao(self):
        self.entrar()
        with patch("guia_cms.storage.salvar", side_effect=SQLAlchemyError("falha sintética")):
            self.salvar("Publicação interrompida", status="publicado", esperado=503, blocos=[
                {"tipo": "texto", "html": "<p>Não publicar pela metade.</p>"},
                {"tipo": "midia", "id": "nova_x", "legenda": "Captura", "alt": "Captura"}],
                midia_nova_x=(BytesIO(imagem()), "captura.png"))
        self.assertIsNone(self.topico("Publicação interrompida"))
        self.assertNotIn("Publicação interrompida", self.corpo_cliente())

    def test_quotas_impedem_novas_midias_sem_publicacao_parcial(self):
        self.entrar()
        from models import ArquivoArmazenado
        for limite in ("MAX_TOPICO_BYTES", "MAX_GUIA_BYTES"):
            with self.subTest(limite=limite), patch("guia_cms." + limite, 1):
                self.salvar("Quota excedida " + limite, status="publicado", esperado=400, blocos=[
                    {"tipo": "texto", "html": "<p>Não gravar upload acima da quota.</p>"},
                    {"tipo": "midia", "id": "nova_quota", "legenda": "Captura", "alt": "Captura"}],
                    midia_nova_quota=(BytesIO(imagem()), "captura.png"))
            self.assertIsNone(self.topico("Quota excedida " + limite))
        self.assertEqual(self.db.session.scalar(self.db.select(self.db.func.count()).select_from(ArquivoArmazenado)), 0)

    def test_remocao_individual_preserva_midia_compartilhada_com_outro_topico(self):
        self.entrar()
        for titulo in ("Primeiro tutorial compartilhado", "Segundo tutorial compartilhado"):
            self.salvar(titulo, status="publicado", blocos=[
                {"tipo": "texto", "html": "<p>Texto institucional.</p>"},
                {"tipo": "midia", "id": "nova_compartilhada", "legenda": "Compartilhada", "alt": "Compartilhada"}],
                midia_nova_compartilhada=(BytesIO(imagem()), "compartilhada.png"))
        from models import ArquivoArmazenado, GuiaMidia
        primeiro = self.topico("Primeiro tutorial compartilhado")
        referencia = self.db.session.scalar(self.db.select(GuiaMidia.referencia).where(GuiaMidia.id_topico == primeiro.id))
        self.salvar(primeiro.pergunta, id_topico=primeiro.id, status="publicado", blocos=[
            {"tipo": "texto", "html": "<p>Texto sem imagem neste tópico.</p>"}])
        self.assertIsNotNone(self.db.session.get(ArquivoArmazenado, referencia.removeprefix("db:")))
        corpo = self.corpo_cliente()
        self.assertIn("Segundo tutorial compartilhado", corpo)
        self.assertEqual(self.client.get("/midia/" + referencia.removeprefix("db:")).status_code, 200)

    def test_exclusao_logica_preserva_conteudo_e_restaura_como_rascunho(self):
        self.entrar()
        self.salvar("Conteúdo recuperável", status="publicado")
        topico = self.topico("Conteúdo recuperável")
        resposta = self.client.post(f"/admin/guia/{topico.id}/deletar", data={
            "versao": str(self.versao(topico.id)), "csrf_token": self.csrf_token("/admin/guia")})
        self.assertEqual(resposta.status_code, 302)
        from models import GuiaEdicao
        self.db.session.expire_all()
        self.assertIsNotNone(self.db.session.get(GuiaEdicao, topico.id).excluido_em)
        self.assertIsNotNone(self.topico(topico.pergunta))
        self.assertNotIn(topico.pergunta, self.corpo_cliente())
        self.entrar()
        self.acao(topico, "restaurar")
        self.db.session.expire_all()
        self.assertIsNone(self.db.session.get(GuiaEdicao, topico.id).excluido_em)
        self.assertFalse(self.topico(topico.pergunta).ativo)
        self.assertIn('>Rascunho</span>', self.client.get("/admin/guia").get_data(as_text=True))
        self.assertNotIn(topico.pergunta, self.corpo_cliente())

    def test_edicao_publicada_atualiza_texto_seguro_e_cache_do_nexobot(self):
        from nexobot import conhecimento
        from tests.test_nexobot_conhecimento import buscar
        self.entrar()
        self.salvar("Como configurar o quimeraguiacms?", status="publicado", blocos=[
            {"tipo": "texto", "html": "<p>Primeira orientação <strong>quimeraguiacms</strong>.</p>"}])
        topico = self.topico("Como configurar o quimeraguiacms?")
        base = conhecimento.obter_base()
        self.assertIn("Primeira orientação", buscar(base, "como configurar quimeraguiacms").trecho.resposta)
        self.salvar(topico.pergunta, id_topico=topico.id, status="publicado", blocos=[
            {"tipo": "texto", "html": "<p>Orientação revisada quimeraguiacms.</p>"}])
        atual = buscar(conhecimento.obter_base(), "como configurar quimeraguiacms").trecho
        self.assertIn("Orientação revisada", atual.resposta)
        self.assertNotIn("<p>", atual.resposta)
        self.acao(topico, "despublicar")
        self.assertIsNone(buscar(conhecimento.obter_base(), "como configurar quimeraguiacms").trecho)

    def test_ausencia_do_esquema_novo_preserva_guia_e_bot_legados(self):
        from models import GuiaEdicao, GuiaMidia, GuiaTopico
        legado = GuiaTopico(categoria="Upload", pergunta="Orientação legada preservada?",
                            resposta="Use a opção Enviar relatórios.", ativo=True)
        self.db.session.add(legado)
        self.db.session.commit()
        id_legado, titulo = legado.id, legado.pergunta
        # Remove somente as tabelas novas da fixture descartável. A leitura deve
        # funcionar de verdade com o esquema antigo, não apenas com guardas mockadas.
        self.db.session.remove()
        GuiaMidia.__table__.drop(self.db.engine)
        GuiaEdicao.__table__.drop(self.db.engine)
        self.assertIn(titulo, self.corpo_cliente())
        from nexobot import conhecimento
        self.assertTrue(any(t.pergunta == titulo for t in conhecimento.obter_base().topicos))
        self.entrar()
        resposta = self.client.get("/admin/guia")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(titulo, resposta.get_data(as_text=True))
        token = self.csrf_token("/admin/guia")
        resposta = self.client.post("/admin/guia/novo", data={
            "categoria": "Upload", "pergunta": "Não salvar sem migração", "resposta": "x", "csrf_token": token})
        self.assertEqual(resposta.status_code, 503)
        self.assertIsNone(self.topico("Não salvar sem migração"))
        self.assertEqual(self.db.session.get(GuiaTopico, id_legado).pergunta, titulo)
