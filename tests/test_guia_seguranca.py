"""Regressões de autorização de mídia legada e entradas editoriais inválidas.

Somente arquivos sintéticos, usuários fictícios e SQLite descartável. As
referências antigas e seus aliases precisam passar pelas guardas normais do
portal antes de entregar qualquer imagem.
"""

from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tests.deploy_support import DeployTestCase, ROOT


ADMIN = "admin-test@example.invalid"
CLIENTE = "cliente-test@example.invalid"
NOME = "captura-privada.png"
REFERENCIA = "uploads/guia/" + NOME
ALIASES = (
    "/static/uploads/guia/" + NOME,
    "/static/uploads//guia/" + NOME,
    "/static/./uploads/guia/" + NOME,
    "/static/outra/../uploads/guia/" + NOME,
)


class GuiaSegurancaTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        self.fixtures()
        from models import GuiaTopico

        pasta = self.work_dir / "static-sintetico"
        destino = pasta / "uploads" / "guia" / NOME
        destino.parent.mkdir(parents=True)
        saida = BytesIO()
        Image.new("RGB", (9, 7), "purple").save(saida, format="PNG")
        self.conteudo = saida.getvalue()
        destino.write_bytes(self.conteudo)
        css = pasta / "css" / "nexo.css"
        css.parent.mkdir()
        self.css = (ROOT / "static" / "css" / "nexo.css").read_bytes()
        css.write_bytes(self.css)
        self.stack.enter_context(patch.object(self.app, "_static_folder", str(pasta)))

        topico = GuiaTopico(categoria="Orientações", pergunta="Captura legada reservada",
                            resposta="Orientação fictícia.", ativo=False, imagem_url=REFERENCIA)
        self.db.session.add(topico)
        self.db.session.commit()
        self.id_topico = topico.id

    def publicar(self, estado=True):
        from models import GuiaTopico
        self.db.session.expire_all()
        self.db.session.get(GuiaTopico, self.id_topico).ativo = estado
        self.db.session.commit()

    def url_protegida(self):
        import storage
        with self.app.test_request_context("/"):
            return storage.url_midia(REFERENCIA)

    def assert_sem_imagem(self, caminho):
        resposta = self.obter(caminho, seguir=True)
        self.assertNotEqual(resposta.data, self.conteudo, caminho)
        self.assertNotEqual(resposta.headers.get("Content-Type"), "image/png", caminho)
        return resposta

    def obter(self, caminho, seguir=False):
        resposta = self.client.get(caminho, follow_redirects=seguir)
        self.addCleanup(resposta.close)
        return resposta

    def test_anonimo_nao_acessa_imagem_por_alias_normalizado(self):
        self.publicar()
        self.assertTrue(self.url_protegida().startswith("/midia-legada-guia/"))
        self.assert_sem_imagem(self.url_protegida())
        for caminho in ALIASES:
            with self.subTest(caminho=caminho):
                redirecionamento = self.obter(caminho)
                self.assertEqual(redirecionamento.status_code, 302)
                self.assertIn("/midia-legada-guia/", redirecionamento.headers["Location"])
                self.assertIn("no-store", redirecionamento.headers["Cache-Control"])
                self.assertEqual(redirecionamento.headers.get("Content-Type", "").split(";")[0], "text/html")
                self.assert_sem_imagem(caminho)

    def test_administrador_visualiza_rascunho_sem_cache_por_alias(self):
        self.login(ADMIN)
        for caminho in (self.url_protegida(), *ALIASES):
            with self.subTest(caminho=caminho):
                resposta = self.obter(caminho, seguir=True)
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.data, self.conteudo)
                self.assertEqual(resposta.headers["Content-Type"], "image/png")
                self.assertIn("no-store", resposta.headers["Cache-Control"])
                self.assertEqual(resposta.headers["Content-Security-Policy"], "default-src 'none'; sandbox")
                self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")

    def test_cliente_somente_le_imagem_atualmente_publicada(self):
        self.login(CLIENTE)
        caminhos = (self.url_protegida(), *ALIASES)
        for caminho in caminhos:
            with self.subTest(estado="rascunho", caminho=caminho):
                self.assertEqual(self.assert_sem_imagem(caminho).status_code, 404)
        self.publicar()
        for caminho in caminhos:
            with self.subTest(estado="publicado", caminho=caminho):
                resposta = self.obter(caminho, seguir=True)
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.data, self.conteudo)
        self.publicar(False)
        for caminho in caminhos:
            with self.subTest(estado="despublicado", caminho=caminho):
                self.assertEqual(self.assert_sem_imagem(caminho).status_code, 404)

    def test_cookie_administrativo_revogado_nao_contorna_guardas_por_static(self):
        from session_security import revogar_sessoes_usuario
        self.login(ADMIN)
        self.assertEqual(self.obter(self.url_protegida()).data, self.conteudo)
        self.assertGreater(revogar_sessoes_usuario(self.db.session, self.admin_id, "troca_senha"), 0)
        self.db.session.commit()
        for caminho in ALIASES:
            with self.subTest(caminho=caminho):
                resposta = self.assert_sem_imagem(caminho)
                self.assertEqual(resposta.request.path, "/auth/login")

    def test_cookie_de_outro_boot_nao_libera_previa_legada(self):
        self.login(ADMIN)
        with self.client.session_transaction() as sessao:
            sessao["boot_id"] = "boot-antigo-ficticio"
        for caminho in ALIASES:
            with self.subTest(caminho=caminho):
                self.assertEqual(self.assert_sem_imagem(caminho).request.path, "/auth/login")

    def test_primeiro_acesso_exige_senha_antes_de_imagem_publicada(self):
        from models import Usuario
        self.publicar()
        self.login(CLIENTE)
        self.db.session.get(Usuario, self.cliente_id).primeiro_acesso = True
        self.db.session.commit()
        for caminho in (self.url_protegida(), *ALIASES):
            with self.subTest(caminho=caminho):
                resposta = self.assert_sem_imagem(caminho)
                self.assertEqual(resposta.request.path, "/auth/primeiro-acesso")

    def test_css_publico_permanece_estatico_sem_autenticacao(self):
        resposta = self.obter("/static/css/nexo.css")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data, self.css)
        self.assertNotIn("Location", resposta.headers)
        self.assertNotEqual(resposta.headers.get("Cache-Control"), "private, no-store")

    def test_legenda_e_alt_json_nao_textuais_retornam_400_sem_alterar_topico(self):
        from models import GuiaEdicao, GuiaMidia, GuiaTopico
        self.login(ADMIN)
        midia = GuiaMidia(id_topico=self.id_topico, referencia=REFERENCIA, tipo="imagem",
                          legenda="Legenda original", alt="Descrição original")
        self.db.session.add(midia)
        self.db.session.flush()
        self.db.session.add(GuiaEdicao(id_topico=self.id_topico, versao=1, blocos=[
            {"tipo": "texto", "html": "<p>Original.</p>"}, {"tipo": "midia", "id": midia.id}]))
        self.db.session.commit()
        id_midia = midia.id
        caminho = f"/admin/guia/editar/{self.id_topico}"
        for campo, invalido in (("legenda", ["invalida"]), ("legenda", {"x": "invalida"}),
                                ("alt", True), ("alt", 42)):
            with self.subTest(campo=campo, tipo=type(invalido).__name__):
                self.db.session.expire_all()
                bloco = {"tipo": "midia", "id": id_midia, "legenda": "Alterada", "alt": "Alterada"}
                bloco[campo] = invalido
                resposta = self.client.post(caminho, data={
                    "categoria": "Categoria alterada", "pergunta": "Título alterado", "descricao": "Alterada",
                    "ordem": "1", "status": "publicado", "versao": "1",
                    "csrf_token": self.csrf_token(caminho),
                    "blocos_json": json.dumps([{"tipo": "texto", "html": "<p>Alterado.</p>"}, bloco]),
                })
                self.assertEqual(resposta.status_code, 400)
                self.db.session.expire_all()
                topico = self.db.session.get(GuiaTopico, self.id_topico)
                atual = self.db.session.get(GuiaMidia, id_midia)
                self.assertEqual(topico.pergunta, "Captura legada reservada")
                self.assertFalse(topico.ativo)
                self.assertEqual(atual.legenda, "Legenda original")
                self.assertEqual(atual.alt, "Descrição original")

    def test_lotes_concorrentes_nao_preparam_bytes_e_trava_libera_apos_falha(self):
        import guia_cms
        resultado = object()
        self.assertTrue(guia_cms._EDICAO_TRAVA.acquire(blocking=False))
        try:
            with patch.object(guia_cms, "_salvar", return_value=resultado) as salvar:
                with self.assertRaisesRegex(guia_cms.GuiaErro, "Outro tutorial"):
                    guia_cms.salvar(None, {}, {})
                salvar.assert_not_called()
        finally:
            guia_cms._EDICAO_TRAVA.release()
        with patch.object(guia_cms, "_salvar", side_effect=guia_cms.GuiaErro("Falha sintética")):
            with self.assertRaisesRegex(guia_cms.GuiaErro, "Falha sintética"):
                guia_cms.salvar(None, {}, {})
        with patch.object(guia_cms, "_salvar", return_value=resultado) as salvar:
            self.assertIs(guia_cms.salvar(None, {}, {}), resultado)
            salvar.assert_called_once_with(None, {}, {})

    def test_metadados_existentes_exigem_versao_antes_de_salvar(self):
        from models import GuiaEdicao, GuiaTopico
        self.login(ADMIN)
        self.db.session.add(GuiaEdicao(id_topico=self.id_topico, versao=1,
                                      blocos=[{"tipo": "texto", "html": "<p>Original.</p>"}]))
        self.db.session.commit()
        caminho = f"/admin/guia/editar/{self.id_topico}"
        resposta = self.client.post(caminho, data={
            "categoria": "Alterada", "pergunta": "Título perdido", "descricao": "Alterada",
            "ordem": "1", "status": "publicado", "csrf_token": self.csrf_token(caminho),
            "blocos_json": json.dumps([{"tipo": "texto", "html": "<p>Versão sem controle.</p>"}]),
        })
        self.assertEqual(resposta.status_code, 409)
        self.db.session.expire_all()
        topico = self.db.session.get(GuiaTopico, self.id_topico)
        edicao = self.db.session.get(GuiaEdicao, self.id_topico)
        self.assertEqual(topico.pergunta, "Captura legada reservada")
        self.assertEqual(topico.resposta, "Orientação fictícia.")
        self.assertFalse(topico.ativo)
        self.assertEqual(edicao.versao, 1)

    def test_primeira_edicao_remove_imagem_da_publicacao_preservando_vinculo_e_blob(self):
        import storage
        from models import ArquivoArmazenado, GuiaEdicao, GuiaMidia, GuiaTopico
        chave = "guia/captura-original-recuperavel.png"
        referencia = storage.salvar(self.conteudo, chave)
        topico = self.db.session.get(GuiaTopico, self.id_topico)
        topico.imagem_url, topico.ativo = referencia, True
        self.db.session.commit()
        url = "/midia/" + chave
        self.login(CLIENTE)
        self.assertEqual(self.obter(url).data, self.conteudo)
        self.logout()
        self.login(ADMIN)
        caminho = f"/admin/guia/editar/{self.id_topico}"
        resposta = self.client.post(caminho, data={
            "categoria": "Orientações", "pergunta": "Captura legada reservada", "resposta": "Texto revisado sem imagem.",
            "status": "publicado", "ordem": "0", "remover_imagem": "1", "csrf_token": self.csrf_token(caminho),
        })
        self.assertEqual(resposta.status_code, 302)
        self.db.session.expire_all()
        topico = self.db.session.get(GuiaTopico, self.id_topico)
        edicao = self.db.session.get(GuiaEdicao, self.id_topico)
        retida = self.db.session.scalar(self.db.select(GuiaMidia).where(
            GuiaMidia.id_topico == self.id_topico, GuiaMidia.referencia == referencia))
        self.assertIsNone(topico.imagem_url)
        self.assertTrue(topico.ativo)
        self.assertIsNotNone(retida)
        self.assertFalse(any(b.get("tipo") == "midia" for b in edicao.blocos))
        self.assertEqual(edicao.historico[-1]["imagem_url"], referencia)
        self.assertTrue(edicao.historico[-1]["ativo"])
        self.assertEqual(self.db.session.get(ArquivoArmazenado, chave).conteudo, self.conteudo)
        self.logout()
        self.login(CLIENTE)
        self.assertEqual(self.assert_sem_imagem(url).status_code, 404)
