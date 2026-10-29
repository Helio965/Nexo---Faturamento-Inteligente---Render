"""Gestão contratual no banco (SQLite + migrações reais): operações, integridade,
coberturas, suspensão, prorrogação, cancelamento, reconciliação e política."""

import json
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

import contract_admin
import contract_policy
from contract_admin import ErroContratual
from tests.contratos_support import T0, ContratosCase


def eventos(db, empresa_id):
    from models import EventoContratual
    return db.session.scalars(select(EventoContratual).where(
        EventoContratual.id_empresa == empresa_id).order_by(EventoContratual.id_evento)).all()


class ContratoCadastroTests(ContratosCase):
    def test_cadastro_valido_grava_snapshot_evento_e_plano(self):
        from models import Empresa
        contrato = self.contratar(valor_mensal=Decimal("135.50"), data_formalizacao=date(2026, 1, 2),
                                  referencia_formalizacao="Contrato fictício em papel nº 1")
        self.assertEqual((contrato.situacao, contrato.valor_mensal_contratado, contrato.versao),
                         ("ATIVO", Decimal("135.50"), 1))
        self.assertEqual(contrato.id_usuario_admin_responsavel, self.admin_id)
        empresa = self.db.session.get(Empresa, self.empresa_id)
        self.assertEqual((empresa.status_conta, empresa.id_plano_atual), ("ATIVA", contrato.id_plano))
        [evento] = eventos(self.db, self.empresa_id)
        self.assertEqual((evento.tipo, evento.origem, evento.id_usuario_responsavel, evento.situacao_posterior),
                         ("CONTRATACAO", "ADMIN", self.admin_id, "ATIVO"))
        self.assertEqual(json.loads(evento.detalhes)["valor_mensal"], "135.50")

    def test_cadastro_invalido_nao_grava_nada(self):
        from models import Contrato
        casos = {
            "valor negativo": dict(valor_mensal=Decimal("-1")),
            "três casas decimais": dict(valor_mensal=Decimal("10.001")),
            "término antes do início": dict(data_fim=date(2025, 12, 31)),
            "formalização futura": dict(data_formalizacao=date(2026, 12, 1)),
            "plano inexistente": dict(id_plano=9999),
            "meses acima da política": dict(meses_suspensao=4),
            "data absurda": dict(data_inicio=date(1999, 1, 1)),
        }
        for nome, valores in casos.items():
            with self.subTest(nome), self.assertRaises(ErroContratual):
                contract_admin.criar_contrato(self.db.session, self.empresa_id, self.dados(**valores),
                                              responsavel=self.admin, instante=self.agora)
            self.db.session.rollback()
        self.assertEqual(self.db.session.scalar(select(func.count(Contrato.id_contrato))), 0)

    def test_valor_aceita_formato_brasileiro(self):
        self.assertEqual(contract_admin.valor_monetario("1.234,56"), Decimal("1234.56"))
        self.assertEqual(contract_admin.valor_monetario("650"), Decimal("650.00"))
        # Ponto com três dígitos é milhar (mil e quinhentos), nunca R$ 1,50.
        self.assertEqual(contract_admin.valor_monetario("1.500"), Decimal("1500.00"))
        self.assertEqual(contract_admin.valor_monetario("650.00"), Decimal("650.00"))
        self.assertEqual(contract_admin.valor_monetario("12,5"), Decimal("12.50"))
        for invalido in ("abc", "NaN", "Infinity", "-5", "1000000.01", "1,234.56", "1.2345", "1e3", ""):
            with self.subTest(invalido), self.assertRaises(ErroContratual):
                contract_admin.valor_monetario(invalido)

    def test_segundo_contrato_vigente_e_recusado(self):
        self.contratar()
        with self.assertRaises(ErroContratual):
            contract_admin.criar_contrato(self.db.session, self.empresa_id, self.dados(),
                                          responsavel=self.admin, instante=self.agora)

    def test_indice_unico_impede_dois_vigentes_mesmo_fora_da_aplicacao(self):
        from models import Contrato
        contrato = self.contratar()
        self.db.session.add(Contrato(
            id_empresa=self.empresa_id, id_plano=contrato.id_plano, valor_mensal_contratado=1,
            data_inicio=date(2026, 2, 1), situacao="ATIVO", id_usuario_admin_responsavel=self.admin_id,
        ))
        with self.assertRaises(IntegrityError):
            self.db.session.commit()

    def test_restricoes_de_banco_para_datas_e_suspensao(self):
        from models import Contrato
        base = dict(id_empresa=self.empresa_id, id_plano=1, valor_mensal_contratado=1,
                    id_usuario_admin_responsavel=self.admin_id)
        invalidos = [
            dict(data_inicio=date(2026, 2, 1), data_fim=date(2026, 1, 1), situacao="ENCERRADO",
                 encerrado_em=T0),
            dict(data_inicio=date(2026, 1, 1), situacao="SUSPENSO"),  # sem prazos
            dict(data_inicio=date(2026, 1, 1), situacao="ATIVO", suspenso_em=T0),
            dict(data_inicio=date(2026, 1, 1), situacao="CANCELADO", cancelado_em=T0),  # sem motivo
            dict(data_inicio=date(2026, 1, 1), situacao="SUSPENSO", suspenso_em=T0,
                 suspensao_limite_original=T0 - timedelta(days=1), suspensao_limite=T0,
                 pdf_limite_original=T0 + timedelta(days=1), pdf_limite=T0 + timedelta(days=1)),
        ]
        for valores in invalidos:
            with self.subTest(valores["situacao"]):
                self.db.session.add(Contrato(**base, **valores))
                with self.assertRaises(IntegrityError):
                    self.db.session.commit()
                self.db.session.rollback()

    def test_somente_admin_ativo_altera_contratos(self):
        from models import Usuario
        cliente = self.db.session.get(Usuario, self.cliente_id)
        with self.assertRaises(ErroContratual):
            contract_admin.criar_contrato(self.db.session, self.empresa_id, self.dados(),
                                          responsavel=cliente, instante=self.agora)

    def test_empresa_na_lixeira_ou_inexistente(self):
        from company_security import excluir_empresa
        excluir_empresa(self.db.session, self.empresa_id)
        self.db.session.commit()
        for empresa_id in (self.empresa_id, 999):
            with self.subTest(empresa_id), self.assertRaises(ErroContratual):
                contract_admin.criar_contrato(self.db.session, empresa_id, self.dados(),
                                              responsavel=self.admin, instante=self.agora)
            self.db.session.rollback()


class RenovacaoEPlanoTests(ContratosCase):
    def _plano(self, nome, valor):
        from models import Plano
        plano = Plano(nome_plano=nome, valor_mensal=valor, qtd_analises_mes=1, tipo_analise_permitida="MENSAL",
                      nivel_entrega_analise="COMPLETA", nivel_dashboard="GERENCIAL", nivel_atendimento="MEDIO")
        self.db.session.add(plano)
        self.db.session.commit()
        return plano

    def test_renovacao_preserva_contrato_anterior(self):
        antigo = self.contratar(valor_mensal=Decimal("120.00"))
        resultado = contract_admin.renovar_contrato(
            self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
            self.dados(valor_mensal=Decimal("150.00"), data_inicio=date(2026, 3, 1), data_fim=date(2027, 2, 28)),
            responsavel=self.admin, instante=self.agora,
        )
        self.db.session.commit()
        self.db.session.expire_all()
        from models import Contrato
        antigo = self.db.session.get(Contrato, antigo.id_contrato)
        self.assertEqual((antigo.situacao, antigo.valor_mensal_contratado, antigo.data_fim),
                         ("ENCERRADO", Decimal("120.00"), date(2026, 12, 31)))
        self.assertIsNotNone(antigo.encerrado_em)
        novo = resultado.contrato
        self.assertEqual((novo.id_contrato_anterior, novo.situacao), (antigo.id_contrato, "ATIVO"))
        self.assertEqual(eventos(self.db, self.empresa_id)[-1].tipo, "RENOVACAO")

    def test_alteracao_de_plano_preserva_valor_e_referencia_das_analises(self):
        from models import Analise, Contrato, Empresa
        antigo = self.contratar()
        prata = self._plano("PRATA", 300)
        plano_analise = self.db.session.get(Analise, self.analise_id).id_plano_referencia
        with self.assertRaises(ErroContratual):  # mesmo plano
            contract_admin.renovar_contrato(
                self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
                self.dados(data_inicio=date(2026, 3, 1)), responsavel=self.admin,
                justificativa="Troca", alteracao_plano=True, instante=self.agora)
        self.db.session.rollback()
        with self.assertRaises(ErroContratual):  # justificativa obrigatória
            contract_admin.renovar_contrato(
                self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
                self.dados(id_plano=prata.id_plano, data_inicio=date(2026, 3, 1)),
                responsavel=self.admin, alteracao_plano=True, instante=self.agora)
        self.db.session.rollback()
        novo = contract_admin.renovar_contrato(
            self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
            self.dados(id_plano=prata.id_plano, valor_mensal=Decimal("300.00"), data_inicio=date(2026, 3, 1)),
            responsavel=self.admin, justificativa="Cliente pediu o Prata", alteracao_plano=True,
            instante=self.agora,
        ).contrato
        self.db.session.commit()
        self.db.session.expire_all()
        antigo = self.db.session.get(Contrato, antigo.id_contrato)
        self.assertEqual((antigo.situacao, antigo.valor_mensal_contratado), ("ENCERRADO", Decimal("150.00")))
        self.assertNotEqual(antigo.id_plano, prata.id_plano)
        self.assertEqual(novo.id_contrato_anterior, antigo.id_contrato)
        self.assertEqual(self.db.session.get(Empresa, self.empresa_id).id_plano_atual, prata.id_plano)
        self.assertEqual(self.db.session.get(Analise, self.analise_id).id_plano_referencia, plano_analise)
        detalhes = json.loads(eventos(self.db, self.empresa_id)[-1].detalhes)
        self.assertEqual((detalhes["plano_anterior"], detalhes["id_plano"]), (antigo.id_plano, prata.id_plano))

    def test_nova_vigencia_precisa_comecar_depois_e_nao_no_futuro(self):
        antigo = self.contratar()
        for inicio in (date(2026, 1, 1), date(2026, 3, 3), date(2027, 1, 1)):  # T0 = 02/03/2026
            with self.subTest(inicio=inicio), self.assertRaises(ErroContratual):
                contract_admin.renovar_contrato(self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
                                                self.dados(data_inicio=inicio), responsavel=self.admin,
                                                instante=self.agora)
            self.db.session.rollback()
        self.assertEqual(self.vigente().id_contrato, antigo.id_contrato)

    def test_contrato_de_outra_empresa_e_recusado(self):
        alheio = self.contratar(empresa_id=self.outra_empresa_id)
        self.contratar()
        with self.assertRaises(ErroContratual):
            contract_admin.renovar_contrato(self.db.session, self.empresa_id, alheio.id_contrato, alheio.versao,
                                            self.dados(data_inicio=date(2027, 1, 1)), responsavel=self.admin,
                                            instante=self.agora)
        self.db.session.rollback()
        with self.assertRaises(ErroContratual):
            contract_admin.registrar_cobertura(self.db.session, self.empresa_id, alheio.id_contrato,
                                               periodo_inicio=date(2026, 1, 1), periodo_fim=date(2026, 1, 31),
                                               referencia="x", responsavel=self.admin, instante=self.agora)

    def test_versao_desatualizada_e_recusada(self):
        contrato = self.contratar()
        with self.assertRaises(ErroContratual):
            contract_admin.suspender_contrato(self.db.session, self.empresa_id, contrato.id_contrato,
                                              contrato.versao + 1, motivo="x", responsavel=self.admin,
                                              instante=self.agora)

    def test_preco_de_catalogo_nao_altera_contratos(self):
        import plan_catalog
        from models import Contrato, HistoricoPrecoPlano, Plano
        contrato = self.contratar(valor_mensal=Decimal("100.00"))
        planejado = plan_catalog.planejar_atualizacao_precos(self.db.session)
        self.assertEqual([(i["plano"].nome_plano, i["anterior"], i["novo"]) for i in planejado],
                         [("BRONZE", Decimal("100"), Decimal("150.00"))])
        self.db.session.rollback()
        plan_catalog.aplicar_atualizacao_precos(self.db.session, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(plan_catalog.aplicar_atualizacao_precos(self.db.session, instante=self.agora), [])
        self.db.session.commit()
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Contrato, contrato.id_contrato).valor_mensal_contratado,
                         Decimal("100.00"))
        bronze = self.db.session.scalar(select(Plano).where(Plano.nome_plano == "BRONZE"))
        self.assertEqual(Decimal(str(bronze.valor_mensal)), Decimal("150.00"))
        [historico] = self.db.session.scalars(select(HistoricoPrecoPlano)).all()
        self.assertEqual((historico.valor_anterior, historico.valor_novo), (Decimal("100.00"), Decimal("150.00")))

    def test_catalogo_padrao_tem_os_novos_precos_e_mantem_beneficios(self):
        import plan_catalog
        self.assertEqual(plan_catalog.precos_padrao(),
                         {"BRONZE": Decimal("150.00"), "PRATA": Decimal("300.00"), "OURO": Decimal("650.00")})
        beneficios = {p["nome_plano"]: (p["qtd_analises_mes"], p["tipo_analise_permitida"], p["nivel_entrega_analise"])
                      for p in plan_catalog.CATALOGO_PLANOS}
        self.assertEqual(beneficios, {"BRONZE": (1, "MENSAL", "BASICA"), "PRATA": (1, "MENSAL", "COMPLETA"),
                                      "OURO": (2, "QUINZENAL", "PREMIUM")})


class CoberturaTests(ContratosCase):
    def test_sobreposicao_e_fora_da_vigencia(self):
        self.contratar()
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        for inicio, fim in ((date(2026, 1, 15), date(2026, 2, 15)), (date(2025, 12, 1), date(2025, 12, 31)),
                            (date(2026, 12, 1), date(2027, 1, 31)), (date(2026, 3, 10), date(2026, 3, 1))):
            with self.subTest(inicio=inicio), self.assertRaises(ErroContratual):
                self.pagar(inicio, fim)
            self.db.session.rollback()
        with self.assertRaises(ErroContratual):
            self.pagar(date(2026, 2, 1), date(2026, 2, 28), referencia="   ")

    def test_fk_composta_impede_cobertura_de_outra_empresa(self):
        from models import CoberturaPaga
        contrato = self.contratar()
        self.db.session.add(CoberturaPaga(
            id_contrato=contrato.id_contrato, id_empresa=self.outra_empresa_id,
            periodo_inicio=date(2026, 1, 1), periodo_fim=date(2026, 1, 31), referencia_confirmacao="x",
            confirmado_em=T0, id_usuario_admin_confirmacao=self.admin_id,
        ))
        with self.assertRaises(IntegrityError):
            self.db.session.commit()

    def test_revogacao_preserva_registro_e_retira_direito(self):
        from models import CoberturaPaga
        self.contratar()
        cobertura = self.pagar(date(2026, 1, 1), date(2026, 1, 31)).evento.id_cobertura
        self.assertEqual(contract_policy.intervalos_pagos(self.empresa_id, instante=self.agora),
                         ((date(2026, 1, 1), date(2026, 1, 31)),))
        contract_admin.revogar_cobertura(self.db.session, self.empresa_id, cobertura, motivo="Estorno fictício",
                                         responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(contract_policy.intervalos_pagos(self.empresa_id, instante=self.agora), ())
        registro = self.db.session.get(CoberturaPaga, cobertura)
        self.assertEqual(registro.revogacao_motivo, "Estorno fictício")
        self.assertEqual([e.tipo for e in eventos(self.db, self.empresa_id)][-2:],
                         ["COBERTURA_CONFIRMADA", "COBERTURA_REVOGADA"])
        with self.assertRaises(ErroContratual):
            contract_admin.revogar_cobertura(self.db.session, self.empresa_id, cobertura, motivo="de novo",
                                             responsavel=self.admin, instante=self.agora)
        # Revogada, o período pode ser registrado de novo (correção).
        self.db.session.rollback()
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))

    def test_cobertura_conta_somente_apos_a_confirmacao(self):
        self.contratar()
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        antes = T0 - timedelta(seconds=1)
        self.assertEqual(contract_policy.intervalos_pagos(self.empresa_id, instante=antes), ())

    def test_contratos_sucessivos_somam_coberturas(self):
        antigo = self.contratar(data_fim=date(2026, 1, 31))
        self.pagar(date(2026, 1, 1), date(2026, 1, 31), contrato=antigo)
        contract_admin.renovar_contrato(self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
                                        self.dados(data_inicio=date(2026, 2, 1), data_fim=date(2026, 12, 31)),
                                        responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.pagar(date(2026, 2, 1), date(2026, 2, 28))
        unidos = contract_policy.intervalos_pagos(self.empresa_id, instante=self.agora)
        self.assertEqual(unidos, ((date(2026, 1, 1), date(2026, 2, 28)),))


class SuspensaoTests(ContratosCase):
    def setUp(self):
        super().setUp()
        self.contratar()
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        self.publicar(self.analise_id)  # janeiro/2026, pago
        self.fevereiro = self.publicar(self.nova_analise(date(2026, 2, 1), date(2026, 2, 28)).id_analise).id_analise
        self.ativar_regras()

    def test_prazos_gravados_e_estado_efetivo(self):
        contrato = self.suspender()
        self.assertEqual(contrato.suspenso_em, T0)
        self.assertEqual(contrato.suspensao_limite, datetime(2026, 6, 2, 13, tzinfo=timezone.utc))
        self.assertEqual(contrato.pdf_limite, datetime(2026, 3, 16, 13, tzinfo=timezone.utc))
        self.assertEqual(contrato.suspensao_limite_original, contrato.suspensao_limite)
        situacao = self.situacao()
        self.assertEqual((situacao.estado, situacao.exportacao_pdf_aberta), ("SUSPENSA", True))
        from models import Analise, Empresa
        self.assertEqual(self.db.session.get(Empresa, self.empresa_id).status_conta, "SUSPENSA")
        janeiro = self.db.session.get(Analise, self.analise_id)
        fevereiro = self.db.session.get(Analise, self.fevereiro)
        self.assertTrue(contract_policy.pode_consultar_analise(situacao, janeiro))
        self.assertFalse(contract_policy.pode_consultar_analise(situacao, fevereiro))  # não pago

    def test_linha_do_tempo_da_suspensao(self):
        self.suspender()
        from models import Analise
        janeiro = lambda: self.db.session.get(Analise, self.analise_id)  # noqa: E731
        pdf = datetime(2026, 3, 16, 13, tzinfo=timezone.utc)
        limite = datetime(2026, 6, 2, 13, tzinfo=timezone.utc)
        um = timedelta(microseconds=1)
        for instante, estado, pdf_aberto, acesso in (
            (T0 + timedelta(days=1), "SUSPENSA", True, True),
            (pdf - um, "SUSPENSA", True, True),
            (pdf, "SUSPENSA", False, True),
            (limite - um, "SUSPENSA", False, True),
            (limite, "SUSPENSAO_EXPIRADA", False, False),
            (limite + timedelta(days=30), "SUSPENSAO_EXPIRADA", False, False),
        ):
            with self.subTest(instante=instante):
                self.relogio(instante)
                situacao = self.situacao()
                self.assertEqual(situacao.estado, estado)
                self.assertEqual(contract_policy.pode_exportar_pdf(situacao, janeiro()), pdf_aberto)
                self.assertEqual(situacao.acesso_portal, acesso)
                self.assertEqual(self.acesso_sql(), acesso)  # cláusula SQL = política Python

    def test_suspensao_retroativa_e_futura(self):
        contrato = self.vigente()
        with self.assertRaises(ErroContratual):
            contract_admin.suspender_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                              motivo="x", responsavel=self.admin,
                                              suspenso_em=T0 + timedelta(minutes=1), instante=self.agora)
        self.db.session.rollback()
        for invalido in (datetime(2025, 12, 31, 12, tzinfo=timezone.utc),  # antes do início do contrato
                         datetime(9999, 12, 31, 23, tzinfo=timezone.utc)):
            with self.subTest(invalido=invalido), self.assertRaises(ErroContratual):
                contract_admin.suspender_contrato(self.db.session, self.empresa_id, contrato.id_contrato,
                                                  contrato.versao, motivo="x", responsavel=self.admin,
                                                  suspenso_em=invalido, instante=self.agora)
            self.db.session.rollback()
        with self.assertRaises(ErroContratual):  # motivo obrigatório
            contract_admin.suspender_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                              motivo=" ", responsavel=self.admin, instante=self.agora)

    def test_conciliacao_registra_suspensao_real_anterior_ao_cadastro(self):
        # O contrato foi cadastrado em T0, mas a suspensão real começou 20 dias antes.
        real = T0 - timedelta(days=20)
        contrato = self.suspender(suspenso_em=real)
        self.assertEqual(contrato.suspenso_em, real)
        self.assertEqual(contrato.pdf_limite, real + timedelta(days=14))
        self.assertFalse(self.situacao().exportacao_pdf_aberta)  # 14 dias já passaram
        self.assertEqual(self.situacao().estado, "SUSPENSA")

    def test_suspensao_depois_de_reativacao_respeita_a_ultima_mudanca(self):
        contrato = self.suspender()
        self.relogio(T0 + timedelta(days=10))
        contract_admin.reativar_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                         justificativa="Pagou", responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        contrato = self.vigente()
        with self.assertRaises(ErroContratual):
            contract_admin.suspender_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                              motivo="x", responsavel=self.admin,
                                              suspenso_em=self.agora - timedelta(days=1), instante=self.agora)

    def test_prazo_contratual_menor(self):
        from models import Contrato
        contrato = self.vigente()
        self.db.session.get(Contrato, contrato.id_contrato).meses_suspensao = 1
        self.db.session.commit()
        contrato = self.suspender()
        self.assertEqual(contrato.suspensao_limite, datetime(2026, 4, 2, 13, tzinfo=timezone.utc))

    def test_prorrogacao_valida_preserva_original_e_nao_amplia_pdf(self):
        contrato = self.suspender()
        original, pdf = contrato.suspensao_limite, contrato.pdf_limite
        novo = datetime(2026, 8, 31, 21, tzinfo=timezone.utc)
        contract_admin.registrar_prorrogacao(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                             novo_limite=novo, justificativa="Acordo fictício",
                                             responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        contrato = self.vigente()
        self.assertEqual((contrato.suspensao_limite, contrato.suspensao_limite_original, contrato.pdf_limite),
                         (novo, original, pdf))
        detalhes = json.loads(eventos(self.db, self.empresa_id)[-1].detalhes)
        self.assertEqual(detalhes["suspensao_limite_anterior"], original.isoformat())
        self.assertFalse(detalhes["ampliacao_pdf"])
        self.relogio(datetime(2026, 7, 1, tzinfo=timezone.utc))
        situacao = self.situacao()
        self.assertEqual((situacao.estado, situacao.exportacao_pdf_aberta, situacao.suspensao_prorrogada),
                         ("SUSPENSA", False, True))
        self.assertEqual(situacao.intervalos_pagos, ((date(2026, 1, 1), date(2026, 1, 31)),))  # sem pagamento novo

    def test_prorrogacoes_invalidas(self):
        contrato = self.suspender()
        invalidos = {
            "anterior ao limite vigente": dict(novo_limite=contrato.suspensao_limite - timedelta(days=1)),
            "igual ao limite": dict(novo_limite=contrato.suspensao_limite),
            "antes da suspensão": dict(novo_limite=T0 - timedelta(days=1)),
            "pdf sem autorização": dict(novo_limite=contrato.suspensao_limite + timedelta(days=30),
                                        novo_limite_pdf=contrato.pdf_limite + timedelta(days=5)),
            "pdf além da suspensão": dict(novo_limite=contrato.suspensao_limite + timedelta(days=30),
                                          novo_limite_pdf=contrato.suspensao_limite + timedelta(days=31),
                                          autorizacao_pdf=True),
        }
        for nome, valores in invalidos.items():
            with self.subTest(nome), self.assertRaises(ErroContratual):
                contract_admin.registrar_prorrogacao(self.db.session, self.empresa_id, contrato.id_contrato,
                                                     contrato.versao, justificativa="x", responsavel=self.admin,
                                                     instante=self.agora, **valores)
            self.db.session.rollback()
        with self.assertRaises(ErroContratual):  # justificativa obrigatória
            contract_admin.registrar_prorrogacao(self.db.session, self.empresa_id, contrato.id_contrato,
                                                 contrato.versao, novo_limite=contrato.suspensao_limite + timedelta(days=1),
                                                 justificativa="", responsavel=self.admin, instante=self.agora)

    def test_ampliacao_de_pdf_com_autorizacao_especifica(self):
        contrato = self.suspender()
        novo_pdf = contrato.pdf_limite + timedelta(days=10)
        contract_admin.registrar_prorrogacao(
            self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
            novo_limite=contrato.suspensao_limite + timedelta(days=30), novo_limite_pdf=novo_pdf,
            autorizacao_pdf=True, justificativa="Aditivo fictício", responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(self.vigente().pdf_limite, novo_pdf)

    def test_reativacao_dentro_e_fora_do_prazo(self):
        contrato = self.suspender()
        self.relogio(contrato.suspensao_limite)
        with self.assertRaises(ErroContratual):
            contract_admin.reativar_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                             justificativa="Pagou", responsavel=self.admin, instante=self.agora)
        self.db.session.rollback()
        self.relogio(T0 + timedelta(days=20))
        contract_admin.reativar_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                         justificativa="Pagou", responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        contrato = self.vigente()
        self.assertEqual((contrato.situacao, contrato.suspenso_em, contrato.pdf_limite), ("ATIVO", None, None))
        self.assertEqual(self.situacao().estado, "ATIVA")

    def test_renovacao_antes_do_encerramento_mantem_acesso(self):
        contrato = self.suspender()
        contract_admin.renovar_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                        self.dados(data_inicio=date(2026, 3, 2), data_fim=date(2027, 3, 1)),
                                        responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.relogio(contrato.suspensao_limite + timedelta(days=1))
        self.assertEqual(self.situacao().estado, "ATIVA")
        self.assertTrue(self.acesso_sql())
        self.assertEqual(contract_admin.reconciliar_vencimentos(self.db.session, aplicar=True).cancelados, [])

    def test_cancelamento_revoga_sessoes(self):
        from models import Usuario
        geracao = self.db.session.get(Usuario, self.cliente_id).geracao_autorizacao
        contrato = self.vigente()
        resultado = contract_admin.cancelar_contrato(self.db.session, self.empresa_id, contrato.id_contrato,
                                                     contrato.versao, motivo="Rescisão fictícia",
                                                     responsavel=self.admin, instante=self.agora)
        self.assertEqual([u.id_usuario for u in resultado.revogados], [self.cliente_id])
        self.db.session.commit()
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Usuario, self.cliente_id).geracao_autorizacao, geracao + 1)
        self.assertEqual(self.situacao().estado, "CANCELADA")
        self.assertFalse(self.acesso_sql())


class ReconciliacaoTests(ContratosCase):
    def setUp(self):
        super().setUp()
        self.contratar()
        self.ativar_regras()
        self.contrato = self.suspender()
        self.relogio(self.contrato.suspensao_limite + timedelta(hours=1))

    def test_simulacao_nao_altera_nada_e_aplicacao_e_idempotente(self):
        from models import Contrato, Empresa, Usuario
        geracao = self.db.session.get(Usuario, self.cliente_id).geracao_autorizacao
        simulacao = contract_admin.reconciliar_vencimentos(self.db.session, aplicar=False, instante=self.agora)
        self.db.session.rollback()
        self.assertEqual([c["id_contrato"] for c in simulacao.candidatos], [self.contrato.id_contrato])
        self.assertEqual(simulacao.cancelados, [])
        self.assertEqual(self.db.session.get(Contrato, self.contrato.id_contrato).situacao, "SUSPENSO")
        # Antes da reconciliação a política já nega o acesso.
        self.assertEqual(self.situacao().estado, "SUSPENSAO_EXPIRADA")
        self.assertFalse(self.acesso_sql())

        aplicado = contract_admin.reconciliar_vencimentos(self.db.session, aplicar=True, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(len(aplicado.cancelados), 1)
        self.db.session.expire_all()
        contrato = self.db.session.get(Contrato, self.contrato.id_contrato)
        self.assertEqual((contrato.situacao, contrato.cancelamento_motivo), ("CANCELADO", contract_admin.MOTIVO_EXPIRACAO))
        self.assertEqual(self.db.session.get(Empresa, self.empresa_id).status_conta, "CANCELADA")
        self.assertEqual(self.db.session.get(Usuario, self.cliente_id).geracao_autorizacao, geracao + 1)
        ultimo = eventos(self.db, self.empresa_id)[-1]
        self.assertEqual((ultimo.tipo, ultimo.origem, ultimo.id_usuario_responsavel), ("CANCELAMENTO", "RECONCILIACAO", None))

        segunda = contract_admin.reconciliar_vencimentos(self.db.session, aplicar=True, instante=self.agora)
        self.db.session.commit()
        self.assertEqual((segunda.candidatos, segunda.cancelados), ([], []))
        self.assertEqual(len([e for e in eventos(self.db, self.empresa_id) if e.tipo == "CANCELAMENTO"]), 1)

    def test_prorrogacao_registrada_antes_impede_cancelamento(self):
        contract_admin.registrar_prorrogacao(
            self.db.session, self.empresa_id, self.contrato.id_contrato, self.contrato.versao,
            novo_limite=self.agora + timedelta(days=15), justificativa="Acordo fictício",
            responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(self.situacao().estado, "SUSPENSA")
        self.assertEqual(contract_admin.reconciliar_vencimentos(self.db.session, aplicar=True).candidatos, [])

    def test_empresa_no_regime_legado_nao_e_reconciliada(self):
        contract_admin.desativar_regras_contratuais(self.db.session, self.empresa_id, justificativa="Contingência",
                                                    responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(contract_admin.reconciliar_vencimentos(self.db.session, aplicar=True).candidatos, [])
        self.assertEqual(self.situacao().regime, "LEGADO")
        self.assertTrue(self.acesso_sql())


class RegimeEPoliticaTests(ContratosCase):
    def test_regime_legado_nao_muda_comportamento(self):
        from models import Analise
        self.publicar(self.analise_id)
        situacao = self.situacao()
        self.assertEqual((situacao.regime, situacao.estado), ("LEGADO", "ATIVA"))
        self.assertTrue(contract_policy.pode_exportar_pdf(situacao, self.db.session.get(Analise, self.analise_id)))
        self.contratar()  # contrato sem regras ativas não restringe
        self.assertTrue(contract_policy.pode_consultar_analise(self.situacao(), self.db.session.get(Analise, self.analise_id)))

    def test_ativacao_exige_contrato_e_nega_sem_cobertura(self):
        from models import Analise
        with self.assertRaises(ErroContratual):
            self.ativar_regras()
        self.db.session.rollback()
        self.publicar(self.analise_id)
        self.contratar()
        self.ativar_regras()
        with self.assertRaises(ErroContratual):
            self.ativar_regras()
        self.db.session.rollback()
        situacao = self.situacao()
        analise = self.db.session.get(Analise, self.analise_id)
        self.assertFalse(contract_policy.pode_consultar_analise(situacao, analise))
        self.pagar(date(2026, 1, 1), date(2026, 1, 15))  # parcial
        self.assertFalse(contract_policy.pode_consultar_analise(self.situacao(), analise))
        self.pagar(date(2026, 1, 16), date(2026, 1, 31))  # consecutivo completa
        self.assertTrue(contract_policy.pode_consultar_analise(self.situacao(), analise))

    def test_base_real_fora_do_pago_bloqueia(self):
        from models import Analise
        self.publicar(self.analise_id, base=(date(2025, 12, 20), date(2026, 1, 31)))
        self.contratar(data_inicio=date(2025, 12, 1))
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        self.ativar_regras()
        self.assertFalse(contract_policy.pode_consultar_analise(self.situacao(), self.db.session.get(Analise, self.analise_id)))

    def test_analise_de_outra_empresa_ou_nao_publicada(self):
        from models import Analise
        self.contratar()
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        self.ativar_regras()
        situacao = self.situacao()
        self.assertFalse(contract_policy.pode_consultar_analise(situacao, self.db.session.get(Analise, self.analise_id)))
        self.publicar(self.outra_analise_id)
        self.assertFalse(contract_policy.pode_consultar_analise(self.situacao(), self.db.session.get(Analise, self.outra_analise_id)))

    def test_regras_ativas_sem_contrato_bloqueiam(self):
        contrato = self.contratar()
        self.ativar_regras()
        contract_admin.cancelar_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                         motivo="x", responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        from company_security import aplicar_status_conta, bloquear_empresa
        empresa = bloquear_empresa(self.db.session, self.empresa_id)
        aplicar_status_conta(self.db.session, empresa, "ATIVA")  # alteração fora do fluxo contratual
        self.db.session.commit()
        self.assertEqual(self.situacao().estado, "SEM_CONTRATO")
        self.assertFalse(self.acesso_sql())

    def test_upload_em_suspensao_somente_para_periodo_pago(self):
        from models import Analise
        self.contratar()
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        self.ativar_regras()
        aberta_paga = self.db.session.get(Analise, self.analise_id)
        aberta_nao_paga = self.nova_analise(date(2026, 2, 1), date(2026, 2, 28))
        self.assertTrue(contract_policy.pode_enviar_relatorio(self.situacao(), aberta_nao_paga))  # ATIVA
        self.suspender()
        situacao = self.situacao()
        self.assertTrue(contract_policy.pode_enviar_relatorio(situacao, aberta_paga))
        self.assertFalse(contract_policy.pode_enviar_relatorio(situacao, aberta_nao_paga))

    def test_nova_analise_fora_da_vigencia(self):
        self.contratar(data_inicio=date(2026, 1, 1), data_fim=date(2026, 6, 30))
        self.ativar_regras()
        situacao = self.situacao()
        self.assertIsNone(contract_policy.motivo_bloqueio_nova_analise(situacao, date(2026, 3, 1), date(2026, 3, 31)))
        self.assertIsNotNone(contract_policy.motivo_bloqueio_nova_analise(situacao, date(2026, 6, 1), date(2026, 7, 31)))
        self.assertIsNotNone(contract_policy.motivo_bloqueio_nova_analise(situacao, date(2025, 12, 1), date(2025, 12, 31)))


class EsquemaAusenteTests(ContratosCase):
    """Código implantado antes da migração: regime legado, sem consultar tabelas novas."""

    def test_sem_tabelas_contratuais_tudo_segue_legado(self):
        import contextlib
        import io
        from unittest.mock import patch
        from flask_migrate import downgrade
        from tests.deploy_support import ROOT
        self.db.session.commit()
        self.db.session.remove()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch("logging.config.fileConfig"):
            downgrade(directory=str(ROOT / "migrations"), revision="e4c004a26b01")
        contract_policy._esquema_por_engine.clear()
        # A migração de sessões (SEC-001) é descendente da de contratos, então o
        # downgrade acima também remove sessao_autenticada. Ela é ortogonal ao
        # regime contratual; recriada aqui para que o login (fail-closed) funcione
        # num cenário que, na prática, nunca roda o código novo sem a tabela.
        from models import SessaoAutenticada, Usuario
        SessaoAutenticada.__table__.create(self.db.engine, checkfirst=True)
        self.admin = self.db.session.get(Usuario, self.admin_id)
        self.assertFalse(contract_policy.esquema_contratual_disponivel())
        self.assertEqual(self.situacao().regime, "LEGADO")
        self.assertTrue(self.acesso_sql())
        with self.assertRaises(contract_policy.EsquemaContratualIndisponivel):
            contract_admin.criar_contrato(self.db.session, self.empresa_id, self.dados(),
                                          responsavel=self.admin, instante=self.agora)
        self.db.session.rollback()
        self.login()
        self.assertEqual(self.client.get("/cliente/dashboard").status_code, 200)

    def test_downgrade_recusa_apagar_dados_contratuais(self):
        import contextlib
        import io
        from unittest.mock import patch
        from flask_migrate import downgrade
        from tests.deploy_support import ROOT
        self.contratar()
        self.db.session.remove()
        # Flask-Migrate converte o RuntimeError do downgrade em SystemExit(1).
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch("logging.config.fileConfig"), self.assertRaises(SystemExit):
            downgrade(directory=str(ROOT / "migrations"), revision="e4c004a26b01")
        contract_policy._esquema_por_engine.clear()
        self.assertTrue(contract_policy.esquema_contratual_disponivel())
        self.assertIsNotNone(self.vigente())


class CorrecoesRevisaoTests(ContratosCase):
    """Regressões dos achados das revisões independentes A–E."""

    def _plano(self, nome):
        from models import Plano
        plano = Plano(nome_plano=nome, valor_mensal=650, qtd_analises_mes=2, tipo_analise_permitida="QUINZENAL",
                      nivel_entrega_analise="PREMIUM", nivel_dashboard="COMPLETO", nivel_atendimento="ALTO")
        self.db.session.add(plano)
        self.db.session.commit()
        return plano

    def test_cobertura_respeita_a_vigencia_efetiva_de_contratos_encerrados_e_cancelados(self):
        antigo = self.contratar(data_fim=date(2026, 12, 31))
        contract_admin.renovar_contrato(self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
                                        self.dados(data_inicio=date(2026, 3, 1)), responsavel=self.admin,
                                        instante=self.agora)
        self.db.session.commit()
        self.pagar(date(2026, 2, 1), date(2026, 2, 28), contrato=antigo)  # antes do sucessor: aceito
        with self.assertRaises(ErroContratual):  # depois do início do sucessor
            self.pagar(date(2026, 3, 1), date(2026, 3, 31), contrato=antigo)
        self.db.session.rollback()
        novo = self.vigente()
        self.relogio(datetime(2026, 4, 10, 15, tzinfo=timezone.utc))
        contract_admin.cancelar_contrato(self.db.session, self.empresa_id, novo.id_contrato, novo.versao,
                                         motivo="Rescisão", responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.pagar(date(2026, 3, 1), date(2026, 3, 31), contrato=novo)  # antes do cancelamento
        with self.assertRaises(ErroContratual):
            self.pagar(date(2026, 4, 11), date(2026, 4, 30), contrato=novo)

    def test_nova_analise_de_periodo_do_contrato_anterior_usa_o_plano_dele(self):
        bronze_id = self.contratar().id_plano
        ouro = self._plano("OURO")
        antigo = self.vigente()
        contract_admin.renovar_contrato(
            self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
            self.dados(id_plano=ouro.id_plano, data_inicio=date(2026, 3, 1)), responsavel=self.admin,
            justificativa="Troca", alteracao_plano=True, instante=self.agora)
        self.db.session.commit()
        self.ativar_regras()
        situacao = self.situacao()
        self.assertIsNone(contract_policy.motivo_bloqueio_nova_analise(situacao, date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(contract_policy.contrato_da_vigencia(self.empresa_id, date(2026, 2, 1), date(2026, 2, 28)).id_plano,
                         bronze_id)
        self.assertEqual(contract_policy.contrato_da_vigencia(self.empresa_id, date(2026, 3, 1), date(2026, 3, 31)).id_plano,
                         ouro.id_plano)
        # Período atravessando a troca não pertence a um único contrato.
        self.assertIsNotNone(contract_policy.motivo_bloqueio_nova_analise(situacao, date(2026, 2, 15), date(2026, 3, 14)))
        # Pelo HTTP: fevereiro gravado com o plano BRONZE; quinzenal de fevereiro recusada.
        from models import Analise
        self.login("admin-test@example.invalid")
        token = self.csrf_token("/admin/analises/nova")
        base = {"csrf_token": token, "id_empresa": str(self.empresa_id), "periodo_inicio": "2026-02-01",
                "periodo_fim": "2026-02-28", "mes_referencia": "2", "ano_referencia": "2026"}
        self.client.post("/admin/analises/nova", data=base | {"tipo_analise": "MENSAL"})
        self.db.session.expire_all()
        nova = self.db.session.scalar(select(Analise).where(Analise.mes_referencia == 2))
        self.assertEqual(nova.id_plano_referencia, bronze_id)
        self.client.post("/admin/analises/nova", data=base | {"tipo_analise": "QUINZENAL", "quinzena_referencia": "1",
                                                              "periodo_fim": "2026-02-15"})
        self.assertEqual(self.db.session.scalar(select(func.count(Analise.id_analise)).where(
            Analise.tipo_analise == "QUINZENAL")), 0)

    def test_nova_analise_decide_com_a_empresa_bloqueada(self):
        """A decisão contratual não pode correr em paralelo com suspensão ou cancelamento."""
        from unittest.mock import patch
        import blueprints.admin as rotas_admin
        self.contratar()
        self.pagar(date(2026, 2, 1), date(2026, 2, 28))
        self.ativar_regras()
        self.login("admin-test@example.invalid")
        token = self.csrf_token("/admin/analises/nova")
        dados = {"csrf_token": token, "id_empresa": str(self.empresa_id), "periodo_inicio": "2026-02-01",
                 "periodo_fim": "2026-02-28", "mes_referencia": "2", "ano_referencia": "2026",
                 "tipo_analise": "MENSAL"}
        with patch.object(rotas_admin, "bloquear_empresa", wraps=rotas_admin.bloquear_empresa) as lock:
            self.client.post("/admin/analises/nova", data=dados)
        self.assertEqual([chamada.args[1] for chamada in lock.call_args_list], [self.empresa_id])

    def test_reconciliacao_registra_quem_acionou(self):
        self.contratar()
        self.ativar_regras()
        contrato = self.suspender()
        self.relogio(contrato.suspensao_limite)
        contract_admin.reconciliar_vencimentos(self.db.session, aplicar=True, acionado_por=self.admin)
        self.db.session.commit()
        ultimo = eventos(self.db, self.empresa_id)[-1]
        self.assertEqual(json.loads(ultimo.detalhes)["acionado_por"], self.admin_id)
        self.assertIsNone(ultimo.id_usuario_responsavel)

    def test_exclusao_permanente_bloqueada_com_historico_contratual(self):
        from models import Contrato, Empresa
        self.contratar()
        from company_security import excluir_empresa
        excluir_empresa(self.db.session, self.empresa_id)
        self.db.session.commit()
        self.login("admin-test@example.invalid")
        resposta = self.client.post(f"/admin/empresa/excluir-permanente/{self.empresa_id}",
                                    data={"csrf_token": self.csrf_token("/admin/lixeira"),
                                          "senha_confirmacao": self.password})
        self.assertEqual(resposta.status_code, 302)
        self.db.session.expire_all()
        self.assertIsNotNone(self.db.session.get(Empresa, self.empresa_id))
        self.assertEqual(self.db.session.scalar(select(func.count(Contrato.id_contrato))), 1)
        pagina = self.client.get("/admin/lixeira").get_data(as_text=True)
        self.assertIn("possui histórico contratual", pagina)

    def test_detalhes_no_regime_legado_mostram_as_acoes_do_contrato(self):
        self.contratar()
        self.login("admin-test@example.invalid")
        html = self.client.get(f"/admin/empresas/{self.empresa_id}/detalhes").get_data(as_text=True)
        for acao in ("Ativar regras contratuais", "Suspender", "Renovar", "Alterar plano", "Registrar período pago"):
            self.assertIn(acao, html)
        self.assertNotIn(f"/admin/empresas/{self.empresa_id}/contratos/novo", html)

    def test_esquema_parcial_falha_fechado_como_erro_de_banco(self):
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError
        self.login()
        self.db.session.execute(text("DROP TABLE historico_preco_plano"))
        self.db.session.commit()
        contract_policy._esquema_por_engine.clear()
        with self.assertRaises(SQLAlchemyError):
            contract_policy.esquema_contratual_disponivel()
        self.db.session.rollback()
        resposta = self.client.get("/cliente/dashboard")
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("Empresa fictícia", resposta.get_data(as_text=True))


    # ---------------------------------------------------------------- revisão E
    def test_contrato_de_empresa_suspensa_nao_a_reativa_e_ativacao_exige_status_coerente(self):
        from models import Empresa
        self.db.session.get(Empresa, self.empresa_id).status_conta = "SUSPENSA"
        self.db.session.commit()
        self.contratar()
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Empresa, self.empresa_id).status_conta, "SUSPENSA")
        with self.assertRaisesRegex(ErroContratual, "difere do contrato"):
            self.ativar_regras()
        self.db.session.rollback()
        self.assertFalse(contract_policy.regime_contratual_ativo(self.empresa_id))
        # Conciliação: a suspensão real, anterior ao cadastro, define os prazos.
        real = T0 - timedelta(days=3)
        contrato = self.suspender(suspenso_em=real)
        self.assertEqual(contrato.suspenso_em, real)
        self.ativar_regras()
        situacao = self.situacao()
        self.assertTrue(situacao.contratual)
        self.assertTrue(situacao.suspensa)
        self.assertEqual(situacao.suspensao_limite, contrato.suspensao_limite)

    def test_renovacao_de_contrato_ativo_de_empresa_suspensa_mantem_o_status_e_suspenso_reativa(self):
        from models import Empresa
        self.db.session.get(Empresa, self.empresa_id).status_conta = "SUSPENSA"
        self.db.session.commit()
        antigo = self.contratar()
        contract_admin.renovar_contrato(self.db.session, self.empresa_id, antigo.id_contrato, antigo.versao,
                                        self.dados(data_inicio=date(2026, 2, 1)), responsavel=self.admin,
                                        instante=self.agora)
        self.db.session.commit()
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Empresa, self.empresa_id).status_conta, "SUSPENSA")
        # Contrato SUSPENSO renovado antes do encerramento: a empresa volta a ATIVA (documento 02, §3).
        contrato = self.suspender()
        contract_admin.renovar_contrato(self.db.session, self.empresa_id, contrato.id_contrato, contrato.versao,
                                        self.dados(data_inicio=date(2026, 3, 1)), responsavel=self.admin,
                                        instante=self.agora)
        self.db.session.commit()
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Empresa, self.empresa_id).status_conta, "ATIVA")

    def test_reativar_empresa_suspensa_exige_justificativa_e_contrato_ativo(self):
        from models import Empresa
        self.db.session.get(Empresa, self.empresa_id).status_conta = "SUSPENSA"
        self.db.session.commit()
        contrato = self.contratar()
        with self.assertRaises(ErroContratual):
            contract_admin.reativar_contrato(self.db.session, self.empresa_id, contrato.id_contrato,
                                             contrato.versao, justificativa="  ", responsavel=self.admin,
                                             instante=self.agora)
        self.db.session.rollback()
        resultado = contract_admin.reativar_contrato(self.db.session, self.empresa_id, contrato.id_contrato,
                                                     contrato.versao, justificativa="Regularizada",
                                                     responsavel=self.admin, instante=self.agora)
        self.db.session.commit()
        self.assertEqual(resultado.empresa.status_conta, "ATIVA")
        self.assertEqual(eventos(self.db, self.empresa_id)[-1].tipo, "REATIVACAO")
        with self.assertRaises(ErroContratual):  # empresa ATIVA e contrato ATIVO: nada a reativar
            contract_admin.reativar_contrato(self.db.session, self.empresa_id, contrato.id_contrato,
                                             self.vigente().versao, justificativa="x", responsavel=self.admin,
                                             instante=self.agora)

    def test_alerta_do_painel_conta_so_suspensoes_vencidas_reconciliaveis(self):
        self.contratar()
        self.suspender()  # regime legado: a reconciliação não atua sobre ela
        self.contratar(empresa_id=self.outra_empresa_id)
        self.ativar_regras(self.outra_empresa_id)
        contrato = self.suspender(empresa_id=self.outra_empresa_id)
        self.relogio(contrato.suspensao_limite + timedelta(days=1))
        self.assertEqual(len(contract_admin.reconciliar_vencimentos(self.db.session, aplicar=False).candidatos), 1)
        self.db.session.rollback()
        self.login("admin-test@example.invalid")
        html = self.client.get("/admin/dashboard").get_data(as_text=True)
        self.assertIn("1 suspensão(ões) vencida(s) aguardando reconciliação", html)

    def _consultas(self, caminho):
        from sqlalchemy import event
        contagem = []

        def contar(*_args):
            contagem.append(1)

        event.listen(self.db.engine, "before_cursor_execute", contar)
        try:
            resposta = self.client.get(caminho)
        finally:
            event.remove(self.db.engine, "before_cursor_execute", contar)
        self.assertEqual(resposta.status_code, 200)
        return len(contagem)

    def test_dashboard_e_historico_nao_consultam_o_banco_por_analise(self):
        self.publicar(self.analise_id, date(2026, 1, 1), date(2026, 1, 31))
        self.login()
        caminhos = ("/cliente/dashboard", "/cliente/historico")
        for caminho in caminhos:
            self._consultas(caminho)  # aquecimento (caches de esquema)
        antes = {caminho: self._consultas(caminho) for caminho in caminhos}
        for mes in (2, 3):
            self.publicar(self.nova_analise(date(2026, mes, 1), date(2026, mes, 28)).id_analise)
        depois = {caminho: self._consultas(caminho) for caminho in caminhos}
        self.assertEqual(depois, antes)

    def test_textos_do_nexobot_distinguem_regime_legado_e_contratual(self):
        from nexobot.saber import empresas_planos, uploads
        registros = {r.id: r for r in empresas_planos.REGISTROS + uploads.REGISTROS}
        suspensa = registros["nexo.empresas.conta_suspensa"].resumo
        self.assertIn("regras contratuais", suspensa)
        self.assertIn("o histórico publicado continua acessível", suspensa)
        envio = registros["nexo.uploads.bloqueado"].explicacao
        self.assertIn("regras contratuais", envio)
        self.assertIn("segue liberado", envio)
        self.assertIn("continua acessível", registros["nexo.empresas.status_conta"].resumo)

class MigracaoLegadoTests(ContratosCase):
    """Upgrade sobre dados legados: nenhum contrato, pagamento ou regime inventado."""

    def _migrar(self, funcao, revisao):
        import contextlib
        import io
        from unittest.mock import patch
        from tests.deploy_support import ROOT
        self.db.session.remove()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch("logging.config.fileConfig"):
            funcao(directory=str(ROOT / "migrations"), revision=revisao)
        contract_policy._esquema_por_engine.clear()

    def test_upgrade_preserva_dados_e_nao_cria_contratos(self):
        from flask_migrate import downgrade, upgrade
        from sqlalchemy import inspect, text
        from company_security import aplicar_status_conta, bloquear_empresa
        self.publicar(self.analise_id)
        empresa = bloquear_empresa(self.db.session, self.outra_empresa_id)
        aplicar_status_conta(self.db.session, empresa, "SUSPENSA")
        self.db.session.commit()
        self._migrar(downgrade, "e4c004a26b01")
        legadas = ("empresa", "usuario", "analise", "relatorio_analise", "indicador_analise", "plano")
        antes = {t: self.db.session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in legadas}
        status = dict(self.db.session.execute(text("SELECT id_empresa, status_conta FROM empresa")).all())
        self._migrar(upgrade, "81287c74387a")
        depois = {t: self.db.session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in legadas}
        self.assertEqual(depois, antes)
        self.assertEqual(dict(self.db.session.execute(text("SELECT id_empresa, status_conta FROM empresa")).all()), status)
        for tabela in contract_policy.TABELAS_CONTRATUAIS:
            self.assertEqual(self.db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar(), 0, tabela)
        indices = {i["name"]: i for i in inspect(self.db.engine).get_indexes("contrato")}
        self.assertTrue(indices["uq_contrato_aplicavel_empresa"]["unique"])
        # Empresas existentes seguem no regime legado: acesso inalterado.
        self.assertEqual(self.situacao().regime, "LEGADO")
        self.assertTrue(self.acesso_sql())


class ComandosTests(ContratosCase):
    def test_reconciliar_simula_por_padrao_e_aplica_com_flag(self):
        from models import Contrato
        self.contratar()
        self.ativar_regras()
        contrato = self.suspender()
        self.relogio(contrato.suspensao_limite + timedelta(minutes=1))
        runner = self.app.test_cli_runner()
        simulacao = runner.invoke(args=["contratos", "reconciliar"])
        self.assertEqual(simulacao.exit_code, 0, simulacao.output)
        self.assertIn("SIMULAÇÃO", simulacao.output)
        self.assertIn("Vencidos: 1; cancelados: 0", simulacao.output)
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Contrato, contrato.id_contrato).situacao, "SUSPENSO")
        aplicado = runner.invoke(args=["contratos", "reconciliar", "--aplicar"])
        self.assertEqual(aplicado.exit_code, 0, aplicado.output)
        self.assertIn("cancelados: 1", aplicado.output)
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Contrato, contrato.id_contrato).situacao, "CANCELADO")
        repetido = runner.invoke(args=["contratos", "reconciliar", "--aplicar"])
        self.assertIn("Vencidos: 0; cancelados: 0", repetido.output)
        for proibido in ("example.invalid", "Empresa fictícia", self.app.config["SECRET_KEY"]):
            self.assertNotIn(proibido, simulacao.output + aplicado.output)

    def test_atualizar_precos_exige_confirmacao_e_e_idempotente(self):
        from models import Plano
        runner = self.app.test_cli_runner()
        simulacao = runner.invoke(args=["planos", "atualizar-precos"])
        self.assertIn("BRONZE: 100", simulacao.output)
        self.assertIn("SIMULAÇÃO", simulacao.output)
        recusado = runner.invoke(args=["planos", "atualizar-precos", "--aplicar"])
        self.assertNotEqual(recusado.exit_code, 0)
        self.db.session.expire_all()
        self.assertEqual(Decimal(str(self.db.session.scalar(select(Plano.valor_mensal)))), Decimal("100"))
        aplicado = runner.invoke(args=["planos", "atualizar-precos", "--aplicar", "--confirmo-janela-autorizada"])
        self.assertEqual(aplicado.exit_code, 0, aplicado.output)
        self.db.session.expire_all()
        self.assertEqual(Decimal(str(self.db.session.scalar(select(Plano.valor_mensal)))), Decimal("150.00"))
        repetido = runner.invoke(args=["planos", "atualizar-precos", "--aplicar", "--confirmo-janela-autorizada"])
        self.assertIn("Catálogo já alinhado", repetido.output)

    def test_seed_cria_planos_com_os_novos_precos(self):
        import seed
        from models import Plano
        from sqlalchemy import delete
        self.db.session.execute(delete(Plano).where(Plano.nome_plano != "BRONZE"))
        self.db.session.commit()
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            seed.seed_planos()
        self.db.session.commit()
        valores = {p.nome_plano: Decimal(str(p.valor_mensal)) for p in self.db.session.scalars(select(Plano))}
        # O seed não altera o plano já existente; os ausentes nascem com o catálogo novo.
        self.assertEqual(valores, {"BRONZE": Decimal("100"), "PRATA": Decimal("300.00"), "OURO": Decimal("650.00")})


if __name__ == "__main__":
    unittest.main()
