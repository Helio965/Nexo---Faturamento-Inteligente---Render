"""Limpeza do Guia: inventário, backup integral e despublicação recuperável.

Somente SQLite descartável da suíte existente; nenhum banco remoto é acessado.
Os IDs são intencionalmente diferentes da ordem visual de categoria e ID.
"""

import contextlib
import hashlib
import io
import json
from unittest.mock import patch
import zipfile

from sqlalchemy import select

import guia_limpeza as limpeza
from tests.deploy_support import DeployTestCase


class GuiaLimpezaTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        from models import GuiaTopico
        self.Topico = GuiaTopico
        self.db.session.add_all([
            GuiaTopico(id=100, categoria="Antes", pergunta="Instrução legítima anterior", resposta="Conteúdo válido.", ativo=True),
            GuiaTopico(id=10, categoria="EZ Test Guia", pergunta="  eZ   TeSt Guia  ", resposta="Marcador de teste.", ativo=True),
            GuiaTopico(id=1, categoria="Upload", pergunta="Como enviar relatórios?", resposta="Instruções legítimas de Upload.", ativo=True),
            GuiaTopico(id=6, categoria="ZA", pergunta="Orientação cuja finalidade precisa ser confirmada", resposta="Revisar o registro.", ativo=True),
            GuiaTopico(id=5, categoria="ZZTEST-guia", pergunta="ZZTEST registro sintético", resposta="Resposta fictícia.", ativo=True),
        ])
        self.db.session.commit()

    def _topico(self, id_topico):
        return self.db.session.get(self.Topico, id_topico)

    def _impressao(self):
        return limpeza.fingerprint(limpeza.inventariar())

    def _arquivo(self, dados):
        arquivo = zipfile.ZipFile(io.BytesIO(dados))
        self.addCleanup(arquivo.close)
        manifesto_bruto = arquivo.read("manifesto.json")
        self.assertEqual(arquivo.read("manifesto.sha256").decode().split()[0], hashlib.sha256(manifesto_bruto).hexdigest())
        return arquivo, json.loads(manifesto_bruto)

    def test_inventario_segue_categoria_id_e_preserva_upload_mesmo_depois_do_marcador(self):
        inventario = limpeza.inventariar()
        self.assertEqual([item["id"] for item in inventario], [100, 10, 1, 6, 5])
        self.assertEqual([item["ordem_visual"] for item in inventario], [1, 2, 3, 4, 5])
        classificacoes = {item["id"]: item["classificacao"] for item in inventario}
        self.assertEqual(classificacoes, {100: limpeza.PRESERVAR, 10: limpeza.REMOVER,
                                        1: limpeza.PRESERVAR, 6: limpeza.REVISAR, 5: limpeza.REMOVER})
        self.assertTrue(all(item["motivo"] and item["acao_prevista"] for item in inventario))

    def test_sem_marcador_unico_nao_deduz_fronteira_por_id(self):
        self._topico(10).pergunta = "Marcador removido"
        self._topico(10).categoria = "Exemplo"
        self._topico(5).categoria = "ZZTEST genérico"
        self.db.session.commit()
        inventario = limpeza.inventariar()
        self.assertEqual({item["classificacao"] for item in inventario if item["id"] != 1}, {limpeza.REVISAR})
        self._topico(100).pergunta = "EZ Test Guia"
        self._topico(5).pergunta = "EZ Test Guia"
        self.db.session.commit()
        self.assertEqual({item["classificacao"] for item in limpeza.inventariar() if item["id"] != 1}, {limpeza.REVISAR})

    def test_familias_da_referencia_visual_sao_identificadas_sem_ez_unico(self):
        self._topico(10).categoria = "Exemplo"
        self._topico(10).pergunta = "Orientação legítima sem marcador"
        self._topico(5).categoria = "ZZTESTE-guia"
        self._topico(5).pergunta = "Como usar o recurso zztesteguiaquasar?"
        casos = (
            ("ZZTESTE-guia", "svg image"),
            ("ZZTESTE-guia", "fake png"),
            ("ZZTESTE-guia", "empty img"),
            ("ZZTESTE-guia <i>XSS</i>", "Conteúdo de teste"),
            ("ZZTEST-guia <img src=x onerror=alert(1)>", "Conteúdo de teste"),
        )
        for indice, (categoria, pergunta) in enumerate(casos, start=201):
            self.db.session.add(self.Topico(id=indice, categoria=categoria, pergunta=pergunta,
                                           resposta="Registro sintético.", ativo=True))
        self.db.session.add(self.Topico(id=300, categoria="ZZZ orientações", pergunta="Finalidade a confirmar",
                                       resposta="Não inferir apenas pela posição.", ativo=True))
        self.db.session.add(self.Topico(id=301, categoria="ZZZ testes genéricos", pergunta="ZZTEST genérico fora da família",
                                       resposta="Revisão individual.", ativo=True))
        self.db.session.commit()
        inventario = {item["id"]: item for item in limpeza.inventariar()}
        for id_topico in (5, 201, 202, 203, 204, 205):
            self.assertEqual(inventario[id_topico]["classificacao"], limpeza.REMOVER)
        for id_topico in (100, 10, 1, 6):
            self.assertEqual(inventario[id_topico]["classificacao"], limpeza.PRESERVAR)
        self.assertEqual(inventario[300]["classificacao"], limpeza.REVISAR)
        self.assertEqual(inventario[301]["classificacao"], limpeza.REVISAR)

    def test_selecao_rejeita_upload_legitimos_anteriores_ids_invalidos_e_casos_nao_revisados(self):
        for ids in ([1], [100], [999], [True], [1.5], ["1.0"], []):
            with self.subTest(ids=ids), self.assertRaises(limpeza.LimpezaGuiaErro):
                limpeza.validar_selecao(ids)
        with self.assertRaisesRegex(limpeza.LimpezaGuiaErro, "individualmente"):
            limpeza.validar_selecao([6])
        self.assertEqual(limpeza.validar_selecao([6, 10, 10], revisados=[6]), [6, 10])

    def test_impressao_detecta_texto_publicacao_e_midia_editorial_alterados(self):
        from models import GuiaEdicao, GuiaMidia
        original = self._impressao()
        self._topico(5).resposta = "Resposta modificada sem mudar o título"
        self.db.session.commit()
        atual = self._impressao()
        self.assertNotEqual(original, atual)
        self._topico(5).ativo = False
        self.db.session.commit()
        publicacao = self._impressao()
        self.assertNotEqual(atual, publicacao)
        self.db.session.add(GuiaEdicao(id_topico=5, descricao="Descrição", ordem=4, blocos=[]))
        self.db.session.add(GuiaMidia(id_topico=5, referencia="db:guia/ficticia.png", tipo="imagem"))
        self.db.session.commit()
        self.assertNotEqual(publicacao, self._impressao())

    def test_despublicacao_explicita_preserva_registros_midias_e_aceita_rollback(self):
        import storage
        referencia = storage.salvar(b"bytes ficticios preservados", "guia/limpeza.png")
        self._topico(10).imagem_url = referencia
        self.db.session.commit()
        impressao = self._impressao()
        resultado = limpeza.despublicar([10, 5], impressao)
        self.assertEqual(resultado, {"selecionados": 2, "despublicados": 2, "excluidos": 0, "preservados": 3})
        self.assertFalse(self._topico(10).ativo)
        self.assertTrue(self._topico(1).ativo)
        self.assertTrue(self._topico(100).ativo)
        self.db.session.flush()
        self.db.session.rollback()
        self.assertTrue(self._topico(10).ativo)
        self.assertIsNotNone(storage.obter("guia/limpeza.png"))

    def test_alteracao_posterior_ao_inventario_impede_despublicar_sem_nova_revisao(self):
        impressao = self._impressao()
        self._topico(5).pergunta = "ZZTEST título alterado depois da revisão"
        self.db.session.commit()
        with self.assertRaisesRegex(limpeza.LimpezaGuiaErro, "mudou"):
            limpeza.despublicar([10, 5], impressao)
        self.assertTrue(self._topico(10).ativo)
        self.assertTrue(self._topico(5).ativo)

    def test_despublicar_e_republicar_atualiza_cache_do_bot_sem_apagar_conteudo(self):
        from nexobot.conhecimento import obter_base
        from models import GuiaEdicao
        base = obter_base()
        self.assertIn(10, {trecho.chave for trecho in base.topicos})
        limpeza.despublicar([10], self._impressao())
        self.db.session.commit()
        depois = obter_base()
        self.assertIsNot(base, depois)
        self.assertNotIn(10, {trecho.chave for trecho in depois.topicos})
        self.assertEqual(self._topico(10).resposta, "Marcador de teste.")
        self.assertIsNotNone(self.db.session.get(GuiaEdicao, 10).publicado_em)
        self._topico(10).ativo = True
        self.db.session.commit()
        self.assertIn(10, {trecho.chave for trecho in obter_base().topicos})

    def test_backup_preserva_registros_editoriais_historico_e_bytes_deduplicados(self):
        from models import GuiaEdicao, GuiaMidia
        import storage
        imagem = b"imagem ficticia com bytes exatos\x00\xff"
        video = b"video ficticio com bytes exatos\x01\xfe"
        ref_imagem = storage.salvar(imagem, "guia/imagem-compartilhada.png")
        ref_video = storage.salvar(video, "guia/video-historico.mp4")
        self._topico(10).imagem_url = ref_imagem
        self._topico(100).imagem_url = ref_imagem
        midia = GuiaMidia(id_topico=10, referencia=ref_imagem, tipo="imagem", legenda="Legenda com acentuação", alt="Captura fictícia")
        historica = GuiaMidia(id_topico=10, referencia=ref_video, tipo="video")
        self.db.session.add_all([midia, historica])
        self.db.session.flush()
        blocos = [{"tipo": "texto", "html": "<p>Passo legítimo</p>"}, {"tipo": "midia", "id": midia.id}]
        self.db.session.add(GuiaEdicao(id_topico=10, descricao="Descrição pública", ordem=7, blocos=blocos,
                                     historico=[{"blocos": [{"tipo": "midia", "id": historica.id}]}]))
        self.db.session.commit()
        arquivo, manifesto = self._arquivo(limpeza.exportar_backup([10]))
        self.assertEqual(manifesto["formato"], "nexo-guia-backup-v1")
        self.assertEqual([topico["id"] for topico in manifesto["topicos"]], [10])
        self.assertEqual(manifesto["topicos"][0]["resposta"], "Marcador de teste.")
        self.assertEqual(manifesto["edicoes"][0]["blocos"], blocos)
        self.assertEqual(len(manifesto["midias"]), 2)
        self.assertEqual(len(manifesto["arquivos"]), 2)
        recuperados = {}
        for item in manifesto["arquivos"]:
            conteudo = arquivo.read(item["arquivo"])
            self.assertEqual(hashlib.sha256(conteudo).hexdigest(), item["sha256"])
            self.assertEqual(len(conteudo), item["tamanho"])
            recuperados[item["referencia"]] = conteudo
        self.assertEqual(recuperados, {ref_imagem: imagem, ref_video: video})
        # A seleção não apaga nem altera a referência compartilhada por um tópico legítimo.
        self.assertEqual(self._topico(100).imagem_url, ref_imagem)
        self.assertTrue(self._topico(10).ativo)

    def test_backup_sem_extensao_editorial_continua_compativel_com_esquema_anterior(self):
        from models import GuiaEdicao, GuiaMidia
        self.db.session.rollback()
        GuiaMidia.__table__.drop(self.db.engine)
        GuiaEdicao.__table__.drop(self.db.engine)
        self.assertEqual(len(limpeza.inventariar()), 5)
        _, manifesto = self._arquivo(limpeza.exportar_backup([10]))
        self.assertEqual(manifesto["edicoes"], [])
        self.assertEqual(manifesto["midias"], [])

    def test_backup_recusa_midia_ausente_inconsistente_traversal_e_excesso(self):
        from models import ArquivoArmazenado
        import storage
        for referencia in ("db:guia/ausente.png", "db:../segredo.png", "../../arquivo.png", "uploads/guia/../arquivo.png"):
            with self.subTest(referencia=referencia):
                self._topico(10).imagem_url = referencia
                self.db.session.commit()
                with self.assertRaises(limpeza.LimpezaGuiaErro):
                    limpeza.exportar_backup([10])
                self.assertTrue(self._topico(10).ativo)
        referencia = storage.salvar(b"bytes ficticios", "guia/inconsistente.png")
        self._topico(10).imagem_url = referencia
        self.db.session.commit()
        registro = self.db.session.get(ArquivoArmazenado, "guia/inconsistente.png")
        registro.tamanho = 100
        self.db.session.commit()
        with self.assertRaisesRegex(limpeza.LimpezaGuiaErro, "inconsistente"):
            limpeza.exportar_backup([10])
        registro.tamanho = len(b"bytes ficticios")
        self.db.session.commit()
        with patch.object(limpeza, "MAX_BACKUP_BYTES", 4), self.assertRaisesRegex(limpeza.LimpezaGuiaErro, "excede"):
            limpeza.exportar_backup([10])

    def test_ferramenta_inventario_json_e_somente_leitura(self):
        from tools import auditar_guia
        saida = io.StringIO()
        with patch("app.create_app", return_value=self.app), \
                patch("sys.argv", ["auditar_guia.py", "--inventario", "--json"]), \
                contextlib.redirect_stdout(saida):
            self.assertEqual(auditar_guia.main(), 0)
        dados = json.loads(saida.getvalue())
        self.assertEqual(dados["total_analisado"], 5)
        self.assertEqual([item["id"] for item in dados["inventario"]], [100, 10, 1, 6, 5])
        self.assertTrue(all(topico.ativo for topico in self.db.session.scalars(select(self.Topico))))
