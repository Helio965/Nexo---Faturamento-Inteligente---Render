"""Personalizar Guia no Chromium real, com aplicação e mídias locais.

Ative como as demais regressões: NEXO_TEST_BROWSER=1,
NEXO_TEST_CHROMIUM=/usr/bin/chromium e NEXO_TEST_CDN_DIR com cópias SRI válidas.
Nenhum usuário, banco ou serviço hospedado participa dos cenários.
"""

import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tests import test_overflow_navegador as navegador
from tests.test_guia_cms import imagem


ADMIN = "admin-test@example.invalid"
CLIENTE = "cliente-test@example.invalid"
OUTRO_CLIENTE = "outro-guia-navegador@example.invalid"
LARGURAS = (320, 360, 390, 430, 768, 1024, 1366, 1920)


@unittest.skipUnless(navegador._BROWSER, "Defina NEXO_TEST_BROWSER=1 e instale Playwright.")
class GuiaNavegadorTests(navegador.NavegadorCase):
    def setUp(self):
        super().setUp()
        from models import Usuario
        outro = Usuario(nome="Outro cliente fictício", email=OUTRO_CLIENTE, role="CLIENTE",
                        id_empresa=self.outra_empresa_id, primeiro_acesso=False)
        outro.set_senha(self.password)
        self.db.session.add(outro)
        self.db.session.commit()

    def _esperar(self, pagina, expressao):
        # A CSP não permite eval; cada avaliação é executada pelo Playwright,
        # evitando o laço interno com eval de wait_for_function.
        for _ in range(200):
            if pagina.evaluate(expressao):
                return
            pagina.wait_for_timeout(50)
        self.fail(expressao)

    def _novo(self, pagina, titulo="Tutorial do navegador"):
        self.ir(pagina, "/admin/guia/novo")
        self._esperar(pagina, "document.getElementById('guiaSalvar') && !document.getElementById('guiaSalvar').disabled")
        pagina.fill("#pergunta", titulo)
        pagina.fill("#categoria", "Orientações do navegador")
        pagina.fill("#descricao", "Tutorial fictício criado pela interface administrativa.")
        pagina.fill("#ordem", "10")
        textos = pagina.locator('.guia-editor-bloco[data-guia-tipo="texto"] [contenteditable="true"]')
        if textos.count() == 0:
            pagina.locator('[data-guia-adicionar="texto"]').click()
        return textos.first

    def _imagem(self, pagina, legenda, cor):
        pagina.locator('[data-guia-adicionar="imagem"]').click()
        bloco = pagina.locator('.guia-editor-bloco[data-guia-tipo="imagem"]').last
        bloco.locator('input[type="file"]').set_input_files({
            "name": "captura.png", "mimeType": "image/png", "buffer": imagem(cor)})
        bloco.locator("[data-guia-legenda]").fill(legenda)
        bloco.locator("[data-guia-alt]").fill("Captura fictícia: " + legenda)
        bloco.locator("img").evaluate("e => e.decode()")
        self.assertTrue(bloco.locator("img").is_visible())
        self.assertTrue(bloco.locator("img").get_attribute("src").startswith("blob:"))
        return bloco

    def _salvar(self, pagina, status="rascunho"):
        pagina.select_option("#status", status)
        with pagina.expect_response(lambda r: r.request.method == "POST" and "/admin/guia" in r.url) as envio, \
                pagina.expect_navigation(wait_until="load"):
            pagina.locator("#guiaSalvar").click()
        alertas = pagina.locator(".guia-cms-erro[role=alert]:visible")
        mensagem = "; ".join(alertas.all_inner_texts())
        self.assertEqual(envio.value.status, 302, f"Publicação retornou HTTP {envio.value.status}: {mensagem}")
        self.assertTrue(pagina.url.endswith("/admin/guia"), pagina.url)

    def _id(self, titulo):
        from models import GuiaTopico
        self.db.session.expire_all()
        topico = self.db.session.scalar(self.db.select(GuiaTopico).where(GuiaTopico.pergunta == titulo))
        self.assertIsNotNone(topico)
        return topico.id

    def _publicacao(self, pagina, id_topico, acao):
        self.ir(pagina, "/admin/guia")
        seletor = f'form[action="/admin/guia/{id_topico}/publicacao"] button[name="acao"][value="{acao}"]'
        with pagina.expect_navigation(wait_until="load"):
            pagina.locator(seletor).click()

    def _cliente(self, email=CLIENTE):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, email)
        self.ir(pagina, "/cliente/guia")
        return pagina

    def _fixture(self, titulo, *, com_imagem=True):
        self.login(ADMIN)
        blocos = [{"tipo": "texto", "html": "<h2>Passo importante</h2><p>" +
                  "Orientação extensa, acentuada e fictícia para utilização do portal. " * 30 + "</p>"}]
        dados = {"categoria": "Tutoriais", "pergunta": titulo, "descricao": "Descrição fictícia extensa. " * 10,
                 "status": "publicado", "ordem": "0", "csrf_token": self.csrf_token("/admin/guia/novo")}
        if com_imagem:
            from io import BytesIO
            blocos.append({"tipo": "midia", "id": "nova_tela", "legenda": "Captura explicativa", "alt": "Tela fictícia"})
            dados["midia_nova_tela"] = (BytesIO(imagem()), "captura.png")
        dados["blocos_json"] = json.dumps(blocos, ensure_ascii=False)
        resposta = self.client.post("/admin/guia/novo", data=dados)
        self.assertEqual(resposta.status_code, 302, resposta.get_data(as_text=True)[:1000])
        return self._id(titulo)

    def test_editor_publicacao_global_previa_imagens_e_despublicacao(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, ADMIN)
        titulo = "Tutorial institucional pela interface"
        texto = self._novo(pagina, titulo)
        self.assertEqual(pagina.locator("#status").input_value(), "rascunho")
        texto.fill("Passo inicial com acentuação")
        texto.select_text()
        pagina.locator('[data-guia-comando="bold"]').first.click()
        self.assertRegex(texto.inner_html(), r"<(?:b|strong)>")
        self._imagem(pagina, "Primeira tela", "purple")
        pagina.locator('[data-guia-adicionar="texto"]').click()
        pagina.locator('[contenteditable="true"]').last.fill("Passo seguinte depois da primeira captura.")
        self._imagem(pagina, "Segunda tela", "orange")
        self._salvar(pagina)
        id_topico = self._id(titulo)
        self.ir(pagina, f"/admin/guia/{id_topico}/previa")
        self.assertIn(titulo, pagina.locator("main").inner_text())
        self.assertEqual(pagina.locator(".guia-conteudo img").count(), 2)
        self.assertEqual(pagina.locator(".guia-conteudo figcaption").all_text_contents(), ["Primeira tela", "Segunda tela"])
        for img in pagina.locator(".guia-conteudo img").all():
            img.scroll_into_view_if_needed()
            img.evaluate("e => e.decode()")
            self.assertTrue(img.evaluate("e => e.complete && e.naturalWidth === 24"))
        primeira_url = pagina.locator(".guia-conteudo img").first.get_attribute("src")
        primeira = self._cliente()
        segunda = self._cliente(OUTRO_CLIENTE)
        for cliente in (primeira, segunda):
            self.assertNotIn(titulo, cliente.locator("main").inner_text())
            self.assertEqual(cliente.request.get(self.base + primeira_url).status, 404)
        self._publicacao(pagina, id_topico, "publicar")
        for cliente in (primeira, segunda):
            cliente.reload(wait_until="load")
            self.assertIn(titulo, cliente.locator("main").inner_text())
            self.assertEqual(cliente.locator(".guia-conteudo img").count(), 2)
            resposta = cliente.request.get(self.base + primeira_url)
            self.assertEqual(resposta.status, 200)
            self.assertIn("no-store", resposta.headers["cache-control"])
        self._publicacao(pagina, id_topico, "despublicar")
        for cliente in (primeira, segunda):
            cliente.reload(wait_until="load")
            self.assertNotIn(titulo, cliente.locator("main").inner_text())
            self.assertEqual(cliente.request.get(self.base + primeira_url).status, 404)

    def test_editor_reordena_remove_desfaz_e_substitui_imagem(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, ADMIN)
        texto = self._novo(pagina, "Imagens reorganizadas pela interface")
        texto.fill("Explicação anterior às imagens.")
        self._imagem(pagina, "Captura um", "purple")
        segunda = self._imagem(pagina, "Captura dois", "orange")
        segunda.locator('[data-guia-mover="acima"]').click()
        legendas = pagina.locator("[data-guia-legenda]").evaluate_all("es => es.map(e => e.value)")
        self.assertEqual(legendas, ["Captura dois", "Captura um"])
        ultima = pagina.locator('.guia-editor-bloco[data-guia-tipo="imagem"]').last
        ultima.locator("[data-guia-remover]").click()
        self.assertEqual(pagina.locator('[data-guia-tipo="imagem"]').count(), 1)
        pagina.locator("#guiaDesfazerRemocao").click()
        self.assertEqual(pagina.locator('[data-guia-tipo="imagem"]').count(), 2)
        ultima = pagina.locator('.guia-editor-bloco[data-guia-tipo="imagem"]').last
        ultima.locator("[data-guia-remover]").click()
        self._salvar(pagina, "publicado")
        id_topico = self._id("Imagens reorganizadas pela interface")
        self.ir(pagina, f"/admin/guia/editar/{id_topico}")
        self._esperar(pagina, "!document.getElementById('guiaSalvar').disabled")
        bloco = pagina.locator('.guia-editor-bloco[data-guia-tipo="imagem"]').first
        bloco.locator('input[type="file"]').set_input_files({
            "name": "substituta.png", "mimeType": "image/png", "buffer": imagem("green")})
        bloco.locator("[data-guia-legenda]").fill("Captura substituída")
        self._salvar(pagina, "publicado")
        cliente = self._cliente()
        self.assertEqual(cliente.locator(".guia-conteudo img").count(), 1)
        self.assertEqual(cliente.locator(".guia-conteudo figcaption").inner_text(), "Captura substituída")
        imagem_cliente = cliente.locator(".guia-conteudo img")
        resposta = cliente.request.get(self.base + imagem_cliente.get_attribute("src"))
        self.assertEqual(resposta.body(), imagem("green"))

    def test_editor_cola_texto_seguro_formata_listas_links_e_aceita_teclado(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, ADMIN)
        texto = self._novo(pagina, "Editor acessível e formatado")
        pagina.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.base)
        pagina.evaluate("navigator.clipboard.writeText('Texto de orientação com acentuação.')")
        texto.click()
        pagina.keyboard.press("ControlOrMeta+V")
        self.assertEqual(texto.inner_text(), "Texto de orientação com acentuação.")
        texto.select_text()
        pagina.locator('[data-guia-estilo]').first.select_option("h2")
        self.assertIn("<h2>", texto.inner_html())
        pagina.locator('[data-guia-adicionar="texto"]').click()
        lista = pagina.locator('[contenteditable="true"]').last
        lista.fill("Primeiro passo\nSegundo passo")
        lista.select_text()
        lista.locator("..").locator('[data-guia-comando="insertOrderedList"]').click()
        self.assertIn("<ol>", lista.inner_html())
        pagina.locator('[data-guia-adicionar="texto"]').click()
        link = pagina.locator('[contenteditable="true"]').last
        link.fill("Consultar a orientação")
        link.select_text()
        pagina.once("dialog", lambda dialog: dialog.accept("https://example.invalid/tutorial"))
        link.locator("..").locator('[data-guia-comando="createLink"]').click()
        self.assertIn('href="https://example.invalid/tutorial"', link.inner_html())
        self._salvar(pagina, "publicado")
        cliente = self._cliente()
        self.assertIn("Texto de orientação com acentuação.", cliente.locator(".guia-conteudo h2").inner_text())
        self.assertGreater(cliente.locator(".guia-conteudo ol li").count(), 0)
        self.assertEqual(cliente.locator('.guia-conteudo a[href="https://example.invalid/tutorial"]').count(), 1)
        # A ordem de Tab alcança o conteúdo e mantém indicação de foco no editor.
        self.ir(pagina, "/admin/guia/novo")
        self._esperar(pagina, "!document.getElementById('guiaSalvar').disabled")
        pagina.focus("#pergunta")
        pagina.keyboard.press("Tab")
        self.assertEqual(pagina.evaluate("document.activeElement.id"), "categoria")
        self.assertTrue(pagina.evaluate("document.activeElement.matches(':focus-visible')"))

    def test_listagem_editor_previa_e_guia_nas_oito_larguras_e_tres_temas(self):
        titulo = ("Como consultar as orientações do portal com um título propositalmente longo e acentuado? " * 2).strip()
        id_topico = self._fixture(titulo)
        admin = self.abrir(1366, 900)
        self.entrar(admin, ADMIN)
        cliente = self._cliente()
        telas = ((admin, "/admin/guia"), (admin, f"/admin/guia/editar/{id_topico}"),
                 (admin, f"/admin/guia/{id_topico}/previa"), (cliente, "/cliente/guia"))
        for tema in ("dark", "light", "system"):
            for pagina, caminho in telas:
                pagina.evaluate("t => localStorage.setItem('theme', t)", tema)
                self.ir(pagina, caminho)
                if "editar" in caminho:
                    self._esperar(pagina, "!document.getElementById('guiaSalvar').disabled")
                for largura in LARGURAS:
                    with self.subTest(tema=tema, caminho=caminho, largura=largura):
                        pagina.set_viewport_size({"width": largura, "height": 900})
                        pagina.wait_for_timeout(60)
                        self.assert_layout(pagina, largura, f"Guia {caminho} {tema} @{largura}px")
                        self.assertEqual(pagina.evaluate("localStorage.getItem('theme')"), tema)
                        self.assertTrue(pagina.locator("main").is_visible())

    def test_video_mp4_persistente_reproduz_pausa_busca_volume_e_tela_cheia(self):
        from guia_midias import disponibilidade_video
        if not disponibilidade_video() or not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg/ffprobe com limites de recursos são necessários para validar vídeo.")
        video_path = Path(self.work_dir) / "tutorial-ficticio.mp4"
        processo = subprocess.run([
            shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=c=purple:s=320x180:r=24",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "4", "-threads", "1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(video_path),
        ], capture_output=True, timeout=30)
        self.assertEqual(processo.returncode, 0, processo.stderr.decode(errors="replace"))
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, ADMIN)
        texto = self._novo(pagina, "Vídeo explicativo fictício")
        texto.fill("Assista às instruções de teste.")
        pagina.locator('[data-guia-adicionar="video"]').click()
        bloco = pagina.locator('.guia-editor-bloco[data-guia-tipo="video"]').last
        bloco.locator('input[type="file"]').set_input_files(str(video_path))
        bloco.locator("[data-guia-legenda]").fill("Vídeo de demonstração fictício")
        bloco.locator("[data-guia-alt]").fill("Tutorial audiovisual fictício")
        self._salvar(pagina, "publicado")
        cliente = self._cliente()
        video = cliente.locator(".guia-conteudo video")
        self.assertEqual(video.count(), 1)
        self.assertTrue(video.evaluate("v => v.controls && !v.autoplay && v.playsInline"))
        video.scroll_into_view_if_needed()
        self._esperar(cliente, "document.querySelector('video').readyState >= 1")
        self.assertAlmostEqual(video.evaluate("v => v.duration"), 4, delta=.3)
        video.evaluate("v => v.play()")
        self._esperar(cliente, "!document.querySelector('video').paused && document.querySelector('video').currentTime > .15")
        video.evaluate("v => v.pause()")
        self.assertTrue(video.evaluate("v => v.paused"))
        video.evaluate("v => {v.volume=.25; v.currentTime=2;}")
        self._esperar(cliente, "Math.abs(document.querySelector('video').currentTime - 2) < .2 && !document.querySelector('video').seeking")
        self.assertAlmostEqual(video.evaluate("v => v.volume"), .25)
        video.evaluate("v => v.requestFullscreen()")
        self.assertTrue(cliente.evaluate("document.fullscreenElement === document.querySelector('video')"))
        cliente.evaluate("document.exitFullscreen()")
        self._esperar(cliente, "document.fullscreenElement === null")
        url = self.base + video.get_attribute("src")
        parcial = cliente.request.get(url, headers={"Range": "bytes=0-63"})
        self.assertEqual(parcial.status, 206)
        self.assertEqual(parcial.body(), video_path.read_bytes()[:64])
        self.assertTrue(parcial.headers["content-range"].startswith("bytes 0-63/"))
        # Persiste no banco: não há dependência do arquivo original do upload.
        video_path.unlink()
        cliente.reload(wait_until="load")
        self._esperar(cliente, "document.querySelector('video').readyState >= 1")
        self.assertAlmostEqual(cliente.locator("video").evaluate("v => v.duration"), 4, delta=.3)
        cliente.set_viewport_size({"width": 390, "height": 844})
        self.assertLessEqual(cliente.locator("video").bounding_box()["width"], 390)
        self.ir(cliente, "/cliente/historico")
        self.assertIn("Histórico", cliente.locator("main").inner_text())
