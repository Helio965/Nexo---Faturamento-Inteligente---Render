"""Fluxo administrativo da limpeza: autorização, backup e commit recuperável.

Todos os registros e arquivos são fictícios em SQLite descartável. As rotas
reais mantêm autenticação e CSRF; nenhum banco hospedado é acessado.
"""

import hashlib
import io
import json
import re
import time
from unittest.mock import patch
import zipfile

from sqlalchemy.exc import SQLAlchemyError

from tests.deploy_support import DeployTestCase


CAMINHO = "/admin/guia/limpeza"
ADMIN = "admin-test@example.invalid"
OUTRO_ADMIN = "outro-admin-guia@example.invalid"


class GuiaLimpezaHTTPTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        self.fixtures()
        from models import GuiaTopico, Usuario
        self.Topico = GuiaTopico
        outro = Usuario(nome="Outro administrador fictício", email=OUTRO_ADMIN,
                        role="ADMIN", primeiro_acesso=False)
        outro.set_senha(self.password)
        self.db.session.add_all([
            outro,
            GuiaTopico(id=91, categoria="Antes", pergunta="Orientação legítima anterior",
                       resposta="Conteúdo institucional preservado.", ativo=True),
            GuiaTopico(id=3, categoria="Upload", pergunta="Como enviar os relatórios?",
                       resposta="Instruções legítimas de Upload preservadas.", ativo=True),
            GuiaTopico(id=7, categoria="ZZTESTE-guia", pergunta="ZZTESTE tópico selecionado",
                       resposta="Registro fictício confirmado como teste.", ativo=True),
            GuiaTopico(id=8, categoria="ZZTESTE-guia", pergunta="ZZTESTE outro tópico de teste",
                       resposta="Outro registro fictício confirmado.", ativo=True),
            GuiaTopico(id=5, categoria="ZZZ orientações", pergunta="Conteúdo com finalidade a revisar",
                       resposta="Não remover apenas pela posição visual.", ativo=True),
        ])
        self.db.session.commit()

    def ativos(self):
        self.db.session.expire_all()
        return {t.id: t.ativo for t in self.db.session.scalars(self.db.select(self.Topico))}

    def preparar(self, ids=(7,), *, esperado=200, revisados=()):
        pagina = self.client.get(CAMINHO)
        self.assertEqual(pagina.status_code, 200)
        impressao = re.search(r'name="fingerprint"\s+value="([0-9a-f]+)"', pagina.get_data(as_text=True))
        self.assertIsNotNone(impressao)
        resposta = self.client.post(CAMINHO, data={
            "acao": "preparar", "ids": [str(i) for i in ids], "revisados": [str(i) for i in revisados],
            "fingerprint": impressao.group(1), "csrf_token": self.csrf_token(CAMINHO),
        })
        self.assertEqual(resposta.status_code, esperado, resposta.get_data(as_text=True)[:1000])
        encontrado = re.search(r'name="backup_token"\s+value="([^"]+)"', resposta.get_data(as_text=True))
        if esperado == 200:
            self.assertIsNotNone(encontrado)
            return encontrado.group(1)
        self.assertIsNone(encontrado)
        return None

    def baixar(self, token, *, esperado=200):
        resposta = self.client.get(CAMINHO + "/backup", query_string={"token": token})
        self.assertEqual(resposta.status_code, esperado)
        if esperado == 200:
            self.assertEqual(resposta.headers["Content-Type"], "application/zip")
            self.assertIn("no-store", resposta.headers["Cache-Control"])
            self.assertIn("attachment", resposta.headers["Content-Disposition"])
        return resposta

    def aplicar(self, token, *, esperado=200, confirmar=True):
        dados = {"acao": "aplicar", "backup_token": token, "csrf_token": self.csrf_token(CAMINHO)}
        if confirmar:
            dados["confirmar_despublicacao"] = "1"
        resposta = self.client.post(CAMINHO, data=dados)
        self.assertEqual(resposta.status_code, esperado, resposta.get_data(as_text=True)[:1000])
        return resposta

    def recibo(self):
        with self.client.session_transaction() as sessao:
            return sessao.get("guia_backup_recibo")

    def test_todas_as_rotas_exigem_admin_e_formularios_mantem_csrf(self):
        self.assertEqual(self.client.get(CAMINHO).status_code, 302)
        self.assertEqual(self.client.get(CAMINHO + "/backup?token=invalido").status_code, 302)
        self.login("cliente-test@example.invalid")
        self.assertEqual(self.client.get(CAMINHO).status_code, 403)
        self.assertEqual(self.client.get(CAMINHO + "/backup?token=invalido").status_code, 403)
        resposta = self.client.post(CAMINHO, data={"acao": "preparar", "csrf_token": self.csrf_token("/cliente/guia")})
        self.assertEqual(resposta.status_code, 403)
        self.logout()
        self.login(ADMIN)
        for acao in ("preparar", "aplicar"):
            self.assertEqual(self.client.post(CAMINHO, data={"acao": acao}).status_code, 400)
        self.assertTrue(all(self.ativos().values()))

    def test_selecao_forjada_nao_despublica_upload_ou_topico_legitimo(self):
        self.login(ADMIN)
        for id_topico in (3, 91, 999):
            with self.subTest(id_topico=id_topico):
                self.preparar([id_topico], esperado=400)
        self.assertTrue(all(self.ativos().values()))
        self.assertIsNone(self.recibo())

    def test_despublicacao_exige_download_e_confirmacao_antes_de_alterar_dados(self):
        self.login(ADMIN)
        token = self.preparar()
        self.assertIsNone(self.recibo())
        self.aplicar(token, esperado=400)
        self.assertTrue(all(self.ativos().values()))
        self.baixar(token)
        self.assertEqual(self.recibo(), hashlib.sha256(token.encode()).hexdigest())
        self.aplicar(token, esperado=400, confirmar=False)
        self.assertTrue(all(self.ativos().values()))

    def test_backup_zip_real_e_aplicacao_despublicam_somente_ids_selecionados(self):
        import storage
        from models import ArquivoArmazenado
        imagem = b"bytes de imagem ficticia preservados no backup\x00\xff"
        referencia = storage.salvar(imagem, "guia/limpeza-http.png")
        self.db.session.get(self.Topico, 7).imagem_url = referencia
        self.db.session.commit()
        self.login(ADMIN)
        token = self.preparar([7, 8])
        resposta = self.baixar(token)
        with zipfile.ZipFile(io.BytesIO(resposta.data)) as arquivo:
            bruto = arquivo.read("manifesto.json")
            manifesto = json.loads(bruto)
            self.assertEqual(arquivo.read("manifesto.sha256").decode().split()[0], hashlib.sha256(bruto).hexdigest())
            self.assertEqual({t["id"] for t in manifesto["topicos"]}, {7, 8})
            self.assertEqual(len(manifesto["arquivos"]), 1)
            midia = manifesto["arquivos"][0]
            self.assertEqual(arquivo.read(midia["arquivo"]), imagem)
            self.assertEqual(midia["sha256"], hashlib.sha256(imagem).hexdigest())
            self.assertIn("RECUPERACAO.md", arquivo.namelist())
        resultado = self.aplicar(token)
        self.assertIn("2 tópico(s) despublicado(s)", resultado.get_data(as_text=True))
        self.assertEqual(self.ativos(), {91: True, 3: True, 7: False, 8: False, 5: True})
        self.assertIsNone(self.recibo())
        self.assertEqual(self.db.session.get(ArquivoArmazenado, "guia/limpeza-http.png").conteudo, imagem)
        self.assertEqual(self.db.session.get(self.Topico, 7).resposta, "Registro fictício confirmado como teste.")

    def test_caso_duvidoso_so_e_selecionado_com_revisao_individual_explicita(self):
        self.login(ADMIN)
        self.preparar([5], esperado=400)
        token = self.preparar([5], revisados=[5])
        self.baixar(token)
        self.aplicar(token)
        self.assertEqual(self.ativos(), {91: True, 3: True, 7: True, 8: True, 5: False})

    def test_mudanca_apos_download_invalida_confirmacao_sem_despublicar(self):
        self.login(ADMIN)
        token = self.preparar([7, 8])
        self.baixar(token)
        self.db.session.get(self.Topico, 8).resposta = "Texto alterado depois do inventário."
        self.db.session.commit()
        resposta = self.aplicar(token, esperado=400)
        self.assertIn("Guia mudou", resposta.get_data(as_text=True))
        self.assertTrue(all(self.ativos().values()))
        self.assertEqual(self.db.session.get(self.Topico, 8).resposta, "Texto alterado depois do inventário.")

    def test_midia_ausente_impede_backup_e_nao_emite_recibo(self):
        self.db.session.get(self.Topico, 7).imagem_url = "db:guia/nao-existe.png"
        self.db.session.commit()
        self.login(ADMIN)
        token = self.preparar()
        self.baixar(token, esperado=400)
        self.assertIsNone(self.recibo())
        self.aplicar(token, esperado=400)
        self.assertTrue(all(self.ativos().values()))

    def test_token_e_vinculado_ao_administrador_que_revisou(self):
        self.login(ADMIN)
        token = self.preparar()
        self.logout()
        self.login(OUTRO_ADMIN)
        self.baixar(token, esperado=400)
        self.aplicar(token, esperado=400)
        self.assertIsNone(self.recibo())
        self.assertTrue(all(self.ativos().values()))

    def test_token_expirado_ou_adulterado_nao_libera_backup(self):
        self.login(ADMIN)
        token = self.preparar()
        self.baixar(("x" if token[0] != "x" else "y") + token[1:], esperado=400)
        self.assertIsNone(self.recibo())
        instante_expirado = int(time.time()) + 901
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=instante_expirado):
            self.baixar(token, esperado=400)
        self.assertTrue(all(self.ativos().values()))

    def test_falha_de_banco_na_aplicacao_reverte_alteracoes_parciais(self):
        import guia_limpeza
        self.login(ADMIN)
        token = self.preparar([7, 8])
        self.baixar(token)

        def falhar_apos_primeira_alteracao(*args, **kwargs):
            self.db.session.get(self.Topico, 7).ativo = False
            self.db.session.flush()
            raise SQLAlchemyError("detalhe privado sintetico nao deve aparecer")

        with patch.object(guia_limpeza, "despublicar", side_effect=falhar_apos_primeira_alteracao):
            resposta = self.aplicar(token, esperado=503)
        self.assertNotIn("detalhe privado sintetico", resposta.get_data(as_text=True))
        self.assertTrue(all(self.ativos().values()))
