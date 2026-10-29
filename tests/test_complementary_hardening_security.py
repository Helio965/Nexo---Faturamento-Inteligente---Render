"""Hardening complementar (FASE 6): teto de conexões Socket.IO por usuário,
nome de produto com teto de tamanho/sem controles no ETL, e confinamento do
script de migração de imagens do Guia a static/."""

import unittest

from .deploy_support import DeployTestCase


class SocketConnectionCapTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        self.fixtures()

    def _http_logado(self):
        http = self.app.test_client()
        response = http.post("/auth/login", data={
            "email": "cliente-test@example.invalid", "senha": self.password,
            "csrf_token": self._csrf_de(http),
        })
        self.assertEqual(response.status_code, 302)
        return http

    def _csrf_de(self, http):
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', http.get("/auth/login").get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def test_per_user_socket_connections_are_capped(self):
        from extensions import socketio
        from realtime import MAX_CONEXOES_POR_USUARIO
        http = self._http_logado()
        conexoes = []
        self.addCleanup(lambda: [c.disconnect() for c in conexoes if c.is_connected()])
        try:
            primeira = socketio.test_client(self.app, flask_test_client=http)
        except Exception as erro:  # ambiente sem suporte a WebSocket de teste
            self.skipTest(f"Socket.IO de teste indisponível: {erro}")
        if not primeira.is_connected():
            self.skipTest("Socket.IO de teste não conectou neste ambiente")
        conexoes.append(primeira)
        # Até o teto: todas conectam.
        for _ in range(MAX_CONEXOES_POR_USUARIO - 1):
            conexao = socketio.test_client(self.app, flask_test_client=http)
            conexoes.append(conexao)
            self.assertTrue(conexao.is_connected())
        ativos = sum(1 for c in conexoes if c.is_connected())
        self.assertEqual(ativos, MAX_CONEXOES_POR_USUARIO)
        # A próxima excede o teto e é recusada pelo handshake.
        excedente = socketio.test_client(self.app, flask_test_client=http)
        conexoes.append(excedente)
        self.assertFalse(excedente.is_connected(), "conexão acima do teto deveria ser recusada")


class ProductNameCapTests(unittest.TestCase):
    def _kpis(self, nome_produto):
        import tempfile
        from pathlib import Path
        from etl_processor import calcular_kpis_em_memoria
        with tempfile.TemporaryDirectory(prefix="nexo-nome-") as diretorio:
            vendas = Path(diretorio) / "vendas.csv"
            compras = Path(diretorio) / "compras.csv"
            vendas.write_text(f"Produto;Quantidade;Valor total\n{nome_produto};3;30,00\nOutro item;1;5,00\n",
                              encoding="utf-8")
            compras.write_text("Fornecedor;Valor NF\nFornecedor sintetico;40,00\n", encoding="utf-8")
            resultado = calcular_kpis_em_memoria(str(vendas), str(compras))
        self.assertTrue(resultado.sucesso, getattr(resultado, "erro", None))
        return resultado.kpis

    def test_oversized_product_name_is_length_capped_and_nul_stripped(self):
        from etl_processor import LIMITE_NOME_PRODUTO
        # NUL embutido + nome muito acima do teto (sem quebra de linha, que seria
        # separador de linha no CSV). O teto protege o banco e o layout.
        bruto = "Produto \x00" + ("X" * 400) + " fim"
        kpis = self._kpis(bruto)
        nome = kpis["produto_mais_vendido_nome"]
        self.assertEqual(len(nome), LIMITE_NOME_PRODUTO)
        self.assertNotIn("\x00", nome)
        self.assertTrue(nome.startswith("Produto X"))
        for produto in kpis["curva_abc"]["produtos"]:
            self.assertLessEqual(len(produto["nome"]), LIMITE_NOME_PRODUTO)


class GuiaImageContainmentTests(unittest.TestCase):
    def test_migration_refuses_paths_outside_static_or_non_images(self):
        import os
        import tempfile
        from migrar_arquivos_para_db import _imagem_contida
        with tempfile.TemporaryDirectory(prefix="nexo-static-") as static:
            dentro = os.path.join(static, "img")
            os.makedirs(dentro)
            with open(os.path.join(dentro, "logo.png"), "wb") as arquivo:
                arquivo.write(b"\x89PNG\r\n")
            # Dentro de static/ e com extensão de imagem: aceito.
            self.assertIsNotNone(_imagem_contida(static, "img/logo.png"))
            # Traversal para fora de static/: recusado.
            self.assertIsNone(_imagem_contida(static, "../../etc/passwd"))
            self.assertIsNone(_imagem_contida(static, "/etc/passwd"))
            # Extensão não-imagem, mesmo dentro de static/: recusado.
            with open(os.path.join(dentro, "nota.txt"), "w", encoding="utf-8") as arquivo:
                arquivo.write("x")
            self.assertIsNone(_imagem_contida(static, "img/nota.txt"))


if __name__ == "__main__":
    unittest.main()
