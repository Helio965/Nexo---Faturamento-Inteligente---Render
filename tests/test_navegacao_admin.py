"""
Regressão da navegação administrativa (28/10/2026): a sidebar do administrador
renderiza exatamente Dashboard, Empresas, Contratos, Lixeira, Análises e Suporte —
sem "Base de Conhecimento" e sem link para o CMS do Guia (admin.guia) — em todas
as páginas administrativas, inclusive na própria página do CMS (alcançável por
URL), e a sidebar do cliente também não ganha o item. O botão Sair continua no
rodapé da sidebar.

Teste HTTP (sem navegador): roda nos dois jobs da CI. O equivalente em Chromium
(gaveta do celular, teclado, indicador do item ativo) está em
tests/test_overflow_navegador.py (test_menu_administrativo_sem_base_de_conhecimento).
"""
import re
import unittest

from tests.contratos_support import ContratosCase

ROTULOS_ADMIN = ["Dashboard", "Empresas", "Contratos", "Lixeira", "Análises", "Suporte"]
PAGINAS_ADMIN = ["/admin/dashboard", "/admin/empresas", "/admin/contratos", "/admin/lixeira",
                 "/admin/analises", "/admin/analises/gerenciar", "/admin/tickets", "/admin/guia"]
ROTULOS_CLIENTE = ["Visão Geral", "Enviar relatórios", "Histórico", "Guia", "Suporte"]
PAGINAS_CLIENTE = ["/cliente/dashboard", "/cliente/upload", "/cliente/historico", "/cliente/guia",
                   "/cliente/tickets"]


def _sidebar(html):
    inicio = html.index('<nav class="sidebar-nav">')
    return html[inicio:html.index("</nav>", inicio)]


def _texto(trecho):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", trecho)).strip()


def _rotulos(nav, apenas_ativos=False):
    classe = "nav-item active" if apenas_ativos else "nav-item"
    itens = re.findall(r'<a class="' + classe + r'[^"]*"[^>]*>(.*?)</a>', nav, flags=re.S)
    return [_texto(item) for item in itens]


class NavegacaoAdminSemBaseDeConhecimentoTests(ContratosCase):
    def _pagina(self, caminho):
        resposta = self.client.get(caminho)
        self.assertEqual(resposta.status_code, 200, caminho)
        return resposta.get_data(as_text=True)

    def test_sidebar_admin_tem_exatamente_seis_itens_sem_base_de_conhecimento(self):
        self.login("admin-test@example.invalid")
        for caminho in PAGINAS_ADMIN:
            html = self._pagina(caminho)
            nav = _sidebar(html)
            self.assertEqual(_rotulos(nav), ROTULOS_ADMIN, caminho)
            self.assertNotIn("Base de Conhecimento", nav, caminho)
            self.assertNotIn("/admin/guia", nav, caminho)
            # "Sair" permanece no rodapé da sidebar, fora da lista principal, uma única vez.
            self.assertEqual(html.count('class="nav-item nav-logout"'), 1, caminho)

    def test_item_ativo_marca_a_pagina_corrente(self):
        self.login("admin-test@example.invalid")
        esperado = (("/admin/dashboard", ["Dashboard"]), ("/admin/empresas", ["Empresas"]),
                    ("/admin/contratos", ["Contratos"]), ("/admin/lixeira", ["Lixeira"]),
                    ("/admin/analises/gerenciar", ["Análises"]), ("/admin/tickets", ["Suporte"]),
                    ("/admin/guia", []))  # o CMS não tem item no menu: nenhum item ativo
        for caminho, ativos in esperado:
            nav = _sidebar(self._pagina(caminho))
            self.assertEqual(_rotulos(nav, apenas_ativos=True), ativos, caminho)

    def test_sidebar_cliente_nao_ganha_o_item(self):
        self.login("cliente-test@example.invalid")
        for caminho in PAGINAS_CLIENTE:
            nav = _sidebar(self._pagina(caminho))
            self.assertEqual(_rotulos(nav), ROTULOS_CLIENTE, caminho)
            self.assertNotIn("Base de Conhecimento", nav, caminho)


if __name__ == "__main__":
    unittest.main()
