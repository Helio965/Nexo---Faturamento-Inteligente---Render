"""Mídias do Guia: conteúdo real, recursos limitados e respostas parciais.

Os testes HTTP usam apenas o banco SQLite descartável da suíte. A rota local
exercita o entregador após a autorização (testada separadamente nas rotas CMS).
"""

from io import BytesIO
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from sqlalchemy import event
from werkzeug.datastructures import FileStorage

import guia_midias as midias
from tests.deploy_support import DeployTestCase


def imagem(formato="PNG", tamanho=(3, 3)):
    saida = BytesIO()
    Image.new("RGB", tamanho, "blue").save(saida, format=formato)
    return saida.getvalue()


def upload(conteudo, nome):
    return FileStorage(stream=BytesIO(conteudo), filename=nome)


class ValidacaoImagensGuiaTests(unittest.TestCase):
    def test_formatos_reais_preservam_bytes_e_ignoram_nome_com_caminho(self):
        for extensao, formato, mime in (("png", "PNG", "image/png"), ("jpg", "JPEG", "image/jpeg"),
                                       ("jpeg", "JPEG", "image/jpeg"), ("webp", "WEBP", "image/webp"),
                                       ("gif", "GIF", "image/gif")):
            with self.subTest(extensao=extensao):
                conteudo = imagem(formato)
                resultado = midias.validar_upload(upload(conteudo, "../../captura." + extensao))
                self.assertEqual(resultado.conteudo, conteudo)
                self.assertEqual(resultado.extensao, extensao)
                self.assertEqual(resultado.content_type, mime)
                self.assertEqual(resultado.tipo, "imagem")

    def test_extensoes_executaveis_svg_e_conteudo_disfarcado_sao_recusados(self):
        for conteudo, nome in ((b"<script>alert(1)</script>", "x.png"), (imagem(), "x.jpg"),
                               (imagem(), "x.exe"), (b"<svg/onload=alert(1)>", "x.svg"),
                               (imagem()[:40], "x.png"), (b"", "vazio.png")):
            with self.subTest(nome=nome, tamanho=len(conteudo)):
                with self.assertRaises(midias.GuiaMidiaErro):
                    midias.validar_upload(upload(conteudo, nome))

    def test_upload_grande_e_lido_com_limite_explicito(self):
        class LeituraLimitada(BytesIO):
            def read(self, tamanho=-1):
                self.ultima_leitura = tamanho
                if tamanho < 0:
                    raise AssertionError("Leitura ilimitada")
                return super().read(tamanho)

        arquivo = FileStorage(stream=LeituraLimitada(b"x" * (midias.MAX_IMAGEM_BYTES + 20)), filename="x.png")
        with self.assertRaises(midias.GuiaMidiaErro):
            midias.validar_upload(arquivo)
        self.assertEqual(arquivo.stream.ultima_leitura, midias.MAX_IMAGEM_BYTES + 1)

    def test_resolucao_e_orcamento_de_pixels_sao_limitados_antes_de_decodificar(self):
        with self.assertRaises(midias.GuiaMidiaErro):
            midias.validar_upload(upload(imagem(tamanho=(4097, 1)), "x.png"))
        with patch.object(midias, "MAX_IMAGEM_PIXELS", 8):
            with self.assertRaises(midias.GuiaMidiaErro):
                midias.validar_upload(upload(imagem(), "x.png"))

    def test_gif_animado_valido_e_orcamentos_de_quadros(self):
        saida = BytesIO()
        frames = [Image.new("RGB", (3, 3), cor) for cor in ("red", "blue", "green")]
        frames[0].save(saida, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
        conteudo = saida.getvalue()
        self.assertEqual(midias.validar_upload(upload(conteudo, "passos.gif")).conteudo, conteudo)
        with patch.object(midias, "MAX_IMAGEM_QUADROS", 2):
            with self.assertRaises(midias.GuiaMidiaErro):
                midias.validar_upload(upload(conteudo, "passos.gif"))
        with patch.object(midias, "MAX_IMAGEM_PIXELS_TOTAIS", 26):
            with self.assertRaises(midias.GuiaMidiaErro):
                midias.validar_upload(upload(conteudo, "passos.gif"))

    def test_video_sem_validador_falha_sem_aceitar_o_arquivo(self):
        with patch.object(midias.shutil, "which", return_value=None):
            self.assertFalse(midias.disponibilidade_video())
            with self.assertRaisesRegex(midias.GuiaMidiaErro, "indisponível"):
                midias.validar_upload(upload(b"arquivo de video ficticio", "tutorial.mp4"))

    def test_video_grande_e_recusado_antes_do_processo_externo(self):
        with patch.object(midias, "MAX_VIDEO_BYTES", 100), patch.object(midias, "_rodar_validador") as processo:
            with self.assertRaises(midias.GuiaMidiaErro):
                midias.validar_upload(upload(b"x" * 101, "tutorial.mp4"))
            processo.assert_not_called()

    def test_validacao_concorrente_e_recusada_antes_de_ler_ou_decodificar(self):
        arquivo = upload(imagem(), "captura.png")
        self.assertTrue(midias._VALIDACAO_TRAVA.acquire(blocking=False))
        try:
            with patch.object(arquivo, "read") as ler, patch.object(midias, "_validar_imagem") as decodificar:
                with self.assertRaisesRegex(midias.GuiaMidiaErro, "Outra mídia"):
                    midias.validar_upload(arquivo)
                ler.assert_not_called()
                decodificar.assert_not_called()
        finally:
            midias._VALIDACAO_TRAVA.release()
        self.assertEqual(midias.validar_upload(arquivo).content_type, "image/png")


@unittest.skipUnless(midias.disponibilidade_video(), "FFmpeg/ffprobe e limites POSIX ausentes para validar MP4 real.")
class ValidacaoVideosGuiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta = tempfile.TemporaryDirectory(prefix="guia-mp4-teste-")
        cls.addClassCleanup(cls.pasta.cleanup)
        cls.valido = cls.gerar("valido.mp4")

    @classmethod
    def gerar(cls, nome, *, codec="libx264", duracao="0.5", fps="10", resolucao="64x48"):
        caminho = Path(cls.pasta.name) / nome
        subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
                        f"color=c=blue:s={resolucao}:r={fps}:d={duracao}", "-f", "lavfi", "-i",
                        f"sine=frequency=440:duration={duracao}", "-c:v", codec, "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-t", duracao, "-threads", "1", "-movflags", "+faststart", str(caminho)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
        return caminho.read_bytes()

    def test_mp4_h264_aac_real_e_decodificado_e_preservado(self):
        try:
            resultado = midias.validar_upload(upload(self.valido, "tutorial.mp4"))
        except midias.GuiaMidiaErro as erro:
            self.fail(f"MP4 válido rejeitado: etapa={erro.operacao}; código={erro.codigo_saida}; motivo={erro.motivo}")
        self.assertEqual(resultado.conteudo, self.valido)
        self.assertEqual((resultado.tipo, resultado.content_type, resultado.extensao), ("video", "video/mp4", "mp4"))

    def test_html_playlist_e_mp4_corrompido_sao_recusados(self):
        for conteudo in (b"<html><script>alert(1)</script></html>", b"#EXTM3U\nfile:///etc/passwd\n", self.valido[:-400]):
            with self.subTest(tamanho=len(conteudo)):
                with self.assertRaises(midias.GuiaMidiaErro):
                    midias.validar_upload(upload(conteudo, "tutorial.mp4"))

    def test_codec_de_video_incompativel_e_recusado(self):
        with self.assertRaisesRegex(midias.GuiaMidiaErro, "H.264"):
            midias.validar_upload(upload(self.gerar("mpeg4.mp4", codec="mpeg4"), "tutorial.mp4"))

    def test_duracao_resolucao_e_fps_sao_limitados(self):
        for nome, parametros in (("longo.mp4", {"duracao": "181", "fps": "1"}),
                                 ("grande.mp4", {"duracao": "0.1", "resolucao": "1922x1080"}),
                                 ("rapido.mp4", {"fps": "61"})):
            with self.subTest(nome=nome):
                with self.assertRaises(midias.GuiaMidiaErro):
                    midias.validar_upload(upload(self.gerar(nome, **parametros), "tutorial.mp4"))

    def test_timeout_do_validador_nao_e_aceito_como_sucesso(self):
        with patch.object(midias.subprocess, "run", side_effect=subprocess.TimeoutExpired("validador", 10)):
            with self.assertRaisesRegex(midias.GuiaMidiaErro, "limites do servidor"):
                midias.validar_upload(upload(self.valido, "tutorial.mp4"))


class ExecucaoValidadorGuiaTests(unittest.TestCase):
    def test_uma_arena_apenas_no_filho_sem_ampliar_limites(self):
        def executar(comando, **opcoes):
            self.assertEqual(opcoes["env"]["MALLOC_ARENA_MAX"], "1")
            self.assertEqual(opcoes["timeout"], 30)
            self.assertTrue(opcoes["start_new_session"])
            self.assertEqual(opcoes["stdin"], subprocess.DEVNULL)
            self.assertEqual(comando[-3:], ["decode", "/bin/ffmpeg-sintetico", "/sintetico.mp4"])
            return subprocess.CompletedProcess(comando, 0)

        with patch.dict(os.environ, {"MALLOC_ARENA_MAX": "64"}), \
                patch.object(midias.shutil, "which", return_value="/bin/ffmpeg-sintetico"), \
                patch.object(midias.subprocess, "run", side_effect=executar):
            self.assertEqual(midias._rodar_validador("decode", "/sintetico.mp4"), b"")
            self.assertEqual(os.environ["MALLOC_ARENA_MAX"], "64")

    def test_falha_retem_somente_etapa_codigo_e_classificacao_sem_stderr_privado(self):
        def executar(comando, **opcoes):
            opcoes["stderr"].write(b"Resource temporarily unavailable /privado/nome-secreto.mp4 credencial-secreta\n")
            return subprocess.CompletedProcess(comando, 245)

        with patch.object(midias.shutil, "which", return_value="/bin/ffmpeg-sintetico"), \
                patch.object(midias.subprocess, "run", side_effect=executar), \
                self.assertRaises(midias.GuiaMidiaErro) as falha:
            midias._rodar_validador("decode", "/sintetico.mp4")
        erro = falha.exception
        self.assertEqual((erro.operacao, erro.codigo_saida, erro.motivo), ("decode", 245, "recursos"))
        self.assertNotIn("nome-secreto", str(erro) + repr(vars(erro)))
        self.assertNotIn("credencial-secreta", str(erro) + repr(vars(erro)))

    @unittest.skipUnless(os.name == "posix", "Limites POSIX do worker.")
    def test_worker_preserva_memoria_cpu_saida_descritores_e_restricoes_ffmpeg(self):
        import resource
        with patch.object(resource, "setrlimit") as limitar, patch.object(midias.os, "execv") as executar:
            midias._processo_video("decode", "/bin/ffmpeg-sintetico", "/sintetico.mp4")
        limites = dict(chamada.args for chamada in limitar.call_args_list)
        self.assertEqual(limites[resource.RLIMIT_AS], (512 * 1024 * 1024,) * 2)
        self.assertEqual(limites[resource.RLIMIT_CPU], (20, 21))
        self.assertEqual(limites[resource.RLIMIT_FSIZE], (128 * 1024,) * 2)
        self.assertEqual(limites[resource.RLIMIT_NOFILE], (64, 64))
        argumentos = executar.call_args.args[1]
        for flag, valor in (("-max_alloc", "67108864"), ("-f", "mov"),
                            ("-protocol_whitelist", "file,pipe"), ("-enable_drefs", "0"),
                            ("-use_absolute_path", "0"), ("-filter_threads", "1"), ("-err_detect", "explode")):
            self.assertEqual(argumentos[argumentos.index(flag) + 1], valor)
        self.assertIn("-xerror", argumentos)
        self.assertEqual([argumentos[i + 1] for i, arg in enumerate(argumentos) if arg == "-threads"], ["1", "1"])


class EntregaMidiasGuiaTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        import storage
        self.chave = "guia/midia-ficticia.png"
        self.conteudo = b"0123456789abcdefghijklmnopqrstuvwxyz"
        storage.salvar(self.conteudo, self.chave)
        self.db.session.commit()
        self.app.add_url_rule("/_midia_teste/<path:chave>", "midia_teste", midias.servir_midia)
        self.sql = []

        def observar(conexao, cursor, comando, parametros, contexto, muitos):
            self.sql.append(comando)

        event.listen(self.db.engine, "before_cursor_execute", observar)
        self.addCleanup(event.remove, self.db.engine, "before_cursor_execute", observar)

    def obter(self, *, metodo="GET", cabecalhos=None, chave=None):
        return self.client.open("/_midia_teste/" + (chave or self.chave), method=metodo, headers=cabecalhos or {})

    def test_entrega_integral_em_blocos_sem_carregar_coluna_inteira(self):
        with patch.object(midias, "_TAMANHO_BLOCO", 4):
            resposta = self.obter()
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.data, self.conteudo)
        self.assertEqual(resposta.headers["Content-Length"], str(len(self.conteudo)))
        self.assertEqual(resposta.headers["Content-Type"], "image/png")
        self.assertEqual(resposta.headers["Cache-Control"], "private, no-store")
        self.assertEqual(resposta.headers["Content-Security-Policy"], "default-src 'none'; sandbox")
        self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resposta.headers["Accept-Ranges"], "bytes")
        self.assertEqual(sum("substr(" in sql.lower() for sql in self.sql), 9)
        self.assertFalse(any("SELECT arquivo_armazenado.conteudo " in sql for sql in self.sql))

    def test_intervalos_fechado_aberto_sufixo_e_fim_limitado(self):
        for cabecalho, esperado, content_range in (("bytes=2-5", b"2345", "bytes 2-5/36"),
                                                 ("bytes=32-", b"wxyz", "bytes 32-35/36"),
                                                 ("bytes=-3", b"xyz", "bytes 33-35/36"),
                                                 ("bytes=34-900", b"yz", "bytes 34-35/36"),
                                                 ("bytes=-100", self.conteudo, "bytes 0-35/36")):
            with self.subTest(range=cabecalho):
                resposta = self.obter(cabecalhos={"Range": cabecalho})
                self.assertEqual(resposta.status_code, 206)
                self.assertEqual(resposta.data, esperado)
                self.assertEqual(resposta.headers["Content-Range"], content_range)
                self.assertEqual(resposta.headers["Content-Length"], str(len(esperado)))

    def test_intervalos_invalidos_multiplos_e_inalcancaveis_retornam_416(self):
        for intervalo in ("bytes=36-", "bytes=10-1", "bytes=-0", "bytes=-", "bytes=1-2,5-6", "itens=1-2",
                          "bytes=" + "9" * 200 + "-", "bytes=x-y"):
            with self.subTest(range=intervalo):
                resposta = self.obter(cabecalhos={"Range": intervalo})
                self.assertEqual(resposta.status_code, 416)
                self.assertEqual(resposta.headers["Content-Range"], "bytes */36")
                self.assertEqual(resposta.data, b"")

    def test_head_nao_consulta_bytes_e_usa_tamanho_real(self):
        from models import ArquivoArmazenado
        self.db.session.get(ArquivoArmazenado, self.chave).tamanho = 1
        self.db.session.commit()
        self.sql.clear()
        resposta = self.obter(metodo="HEAD")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data, b"")
        self.assertEqual(resposta.headers["Content-Length"], "36")
        self.assertFalse(any("substr(" in sql.lower() for sql in self.sql))
        resposta = self.obter(metodo="HEAD", cabecalhos={"Range": "bytes=2-5"})
        self.assertEqual(resposta.status_code, 206)
        self.assertEqual(resposta.headers["Content-Length"], "4")
        self.assertEqual(resposta.data, b"")

    def test_if_range_divergente_devolve_o_arquivo_integral(self):
        resposta = self.obter(cabecalhos={"Range": "bytes=2-5", "If-Range": '"outra-versao"'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data, self.conteudo)
        resposta = self.obter(cabecalhos={"Range": "bytes=2-5", "If-Range": resposta.headers["ETag"]})
        self.assertEqual(resposta.status_code, 206)
        self.assertEqual(resposta.data, b"2345")

    def test_chaves_mime_e_arquivos_nao_autorizados_pelo_entregador(self):
        import storage
        for chave in ("relatorio.csv", "guia/x.html", "guia/../segredo.png", "guia/inexistente.png"):
            with self.subTest(chave=chave):
                self.assertEqual(self.obter(chave=chave).status_code, 404)
        storage.salvar(b"<script>x</script>", "guia/invalido.png")
        registro = storage.obter("guia/invalido.png")
        registro.content_type = "text/html"
        self.db.session.commit()
        self.assertEqual(self.obter(chave="guia/invalido.png").status_code, 404)

    def test_limite_real_e_verificado_antes_de_consultar_bytes(self):
        self.sql.clear()
        with patch.object(midias, "MAX_IMAGEM_ARMAZENADA_BYTES", 10):
            self.assertEqual(self.obter().status_code, 404)
        self.assertFalse(any("substr(" in sql.lower() for sql in self.sql))

    def test_video_armazenado_oferece_mime_e_range_corretos(self):
        import storage
        storage.salvar(b"0123456789", "guia/tutorial.mp4")
        self.db.session.commit()
        resposta = self.obter(chave="guia/tutorial.mp4", cabecalhos={"Range": "bytes=3-6"})
        self.assertEqual(resposta.status_code, 206)
        self.assertEqual(resposta.headers["Content-Type"], "video/mp4")
        self.assertEqual(resposta.headers["Content-Range"], "bytes 3-6/10")
        self.assertEqual(resposta.data, b"3456")
