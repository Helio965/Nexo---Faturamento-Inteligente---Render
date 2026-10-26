"""Cenários contratuais sintéticos sobre DeployTestCase (migrações reais, SQLite).

Nenhum dado real: empresas, CNPJs e e-mails são fictícios (example.invalid).
O relógio da política é injetado por NEXO_RELOGIO; nenhum teste espera tempo real.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from tests.deploy_support import DeployTestCase

# 02/03/2026 10:00 em São Paulo.
T0 = datetime(2026, 3, 2, 13, 0, tzinfo=timezone.utc)
TEXTO_PRIVADO = "Conclusão fictícia exclusiva da empresa um"


class ContratosCase(DeployTestCase):
    def setUp(self):
        super().setUp()
        from models import Analise, Usuario
        self.fixtures()
        self.admin = self.db.session.get(Usuario, self.admin_id)
        self.empresa_id = self.db.session.get(Analise, self.analise_id).id_empresa
        self.outra_empresa_id = self.db.session.get(Analise, self.outra_analise_id).id_empresa
        self.relogio(T0)

    # ------------------------------------------------------------------ relógio
    def relogio(self, instante):
        self.agora = instante
        self.app.config["NEXO_RELOGIO"] = lambda: instante

    # --------------------------------------------------------------- análises
    def publicar(self, id_analise, inicio=None, fim=None, base=None, texto=TEXTO_PRIVADO):
        from models import Analise, IndicadorAnalise, RelatorioAnalise
        analise = self.db.session.get(Analise, id_analise)
        if inicio:
            analise.periodo_inicio, analise.periodo_fim = inicio, fim
            analise.mes_referencia, analise.ano_referencia = inicio.month, inicio.year
        analise.status_analise = "CONCLUIDO"
        analise.data_conclusao = datetime(2026, 2, 5, 12)
        analise.indicador = IndicadorAnalise(
            faturamento_total=Decimal("18500"), total_comprado=Decimal("14200"),
            saldo_estimado_compras_vendas=Decimal("-4300"),
            periodo_base_inicio=base[0] if base else None,
            periodo_base_fim=base[1] if base else None,
        )
        analise.relatorio = RelatorioAnalise(
            titulo=f"Análise fictícia {analise.mes_referencia:02d}", conclusao_estrategica=texto,
            resumo_executivo=texto, publicado=True, data_publicacao=datetime(2026, 2, 5, 12),
        )
        self.db.session.commit()
        return analise

    def nova_analise(self, inicio, fim, empresa_id=None, status="AGUARDANDO_RELATORIO"):
        from models import Analise, Empresa
        empresa = self.db.session.get(Empresa, empresa_id or self.empresa_id)
        analise = Analise(
            id_empresa=empresa.id_empresa, id_plano_referencia=empresa.id_plano_atual,
            id_usuario_admin_responsavel=self.admin_id, periodo_inicio=inicio, periodo_fim=fim,
            mes_referencia=inicio.month, ano_referencia=inicio.year, tipo_analise="MENSAL",
            status_analise=status,
        )
        self.db.session.add(analise)
        self.db.session.commit()
        return analise

    # -------------------------------------------------------------- contratos
    def dados(self, **valores):
        from contract_admin import DadosContrato
        from models import Plano
        base = dict(id_plano=self.db.session.scalar(select(Plano.id_plano)),
                    valor_mensal=Decimal("150.00"), data_inicio=date(2026, 1, 1),
                    data_fim=date(2026, 12, 31))
        base.update(valores)
        return DadosContrato(**base)

    def contratar(self, empresa_id=None, **valores):
        import contract_admin
        resultado = contract_admin.criar_contrato(
            self.db.session, empresa_id or self.empresa_id, self.dados(**valores),
            responsavel=self.admin, instante=self.agora,
        )
        self.db.session.commit()
        return resultado.contrato

    def pagar(self, inicio, fim, contrato=None, empresa_id=None, referencia="Comprovante fictício"):
        import contract_admin
        contrato = contrato or self.vigente(empresa_id)
        resultado = contract_admin.registrar_cobertura(
            self.db.session, contrato.id_empresa, contrato.id_contrato,
            periodo_inicio=inicio, periodo_fim=fim, referencia=referencia,
            responsavel=self.admin, instante=self.agora,
        )
        self.db.session.commit()
        return resultado

    def suspender(self, suspenso_em=None, empresa_id=None, motivo="Inadimplência fictícia"):
        import contract_admin
        contrato = self.vigente(empresa_id)
        resultado = contract_admin.suspender_contrato(
            self.db.session, contrato.id_empresa, contrato.id_contrato, contrato.versao,
            motivo=motivo, responsavel=self.admin, suspenso_em=suspenso_em, instante=self.agora,
        )
        self.db.session.commit()
        return resultado.contrato

    def ativar_regras(self, empresa_id=None):
        import contract_admin
        resultado = contract_admin.ativar_regras_contratuais(
            self.db.session, empresa_id or self.empresa_id, justificativa="Conciliação fictícia",
            responsavel=self.admin, instante=self.agora,
        )
        self.db.session.commit()
        return resultado

    def vigente(self, empresa_id=None):
        from contract_policy import obter_contrato_aplicavel
        return obter_contrato_aplicavel(empresa_id or self.empresa_id)

    def situacao(self, empresa_id=None, instante=None):
        from contract_policy import obter_situacao_contratual
        from models import Empresa
        self.db.session.expire_all()
        return obter_situacao_contratual(self.db.session.get(Empresa, empresa_id or self.empresa_id),
                                         instante=instante or self.agora)

    def acesso_sql(self, id_usuario=None):
        from models import Usuario
        from session_security import usuario_pode_acessar
        self.db.session.expire_all()
        return usuario_pode_acessar(self.db.session.get(Usuario, id_usuario or self.cliente_id))
