"""Inventário conservador e backup recuperável do Guia, sem exclusão de dados.

A classificação usa a ordem anterior ao CMS editorial (categoria, id). Uma
seleção administrativa é explícita e revisada novamente antes da despublicação.
O chamador controla autorização, CSRF, recibo de download e COMMIT.
"""

from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
import zipfile

from flask import current_app
from sqlalchemy import func, inspect, select

from extensions import db
from models import ArquivoArmazenado, GuiaTopico
from nexobot.higiene import motivo_teste
import storage


PRESERVAR = "PRESERVAR"
REMOVER = "REMOVER_DA_PUBLICACAO"
REVISAR = "REVISAR"
MAX_BACKUP_BYTES = 64 * 1024 * 1024
MAX_ARQUIVO_BYTES = 12 * 1024 * 1024
MAX_TOPICOS = 200


class LimpezaGuiaErro(ValueError):
    """A operação não pode prosseguir sem nova revisão administrativa."""


def _normalizar(valor):
    texto = unicodedata.normalize("NFKC", str(valor or ""))
    return " ".join(texto.casefold().split())


def _teste_conhecido(topico):
    """Famílias de teste identificadas na referência visual do proprietário."""
    for valor in (topico.categoria, topico.pergunta):
        valor = _normalizar(valor)
        for prefixo in ("zzteste-guia", "zztest-guia"):
            if valor == prefixo or valor.startswith((prefixo + " ", prefixo + "<")):
                return True
    return False


def _json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    raise TypeError("Tipo não serializável no backup do Guia.")


def _serializar(valor):
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json).encode("utf-8")


def _campos(registro):
    return {coluna.name: getattr(registro, coluna.name) for coluna in registro.__table__.columns}


def _tem_tabela(nome):
    return inspect(db.session.connection()).has_table(nome)


def inventariar():
    """Todos os tópicos, sem alterar a ordem legada nem depender da migração nova.

    Uma fronteira exige marcador EZ único ou família de teste ZZTEST[E]-guia
    explicitamente identificada. Sem esses sinais, os registros aguardam revisão.
    """
    topicos = db.session.scalars(select(GuiaTopico).order_by(GuiaTopico.categoria, GuiaTopico.id)).all()
    extensoes = {}
    if _tem_tabela("guia_edicao"):
        from models import GuiaEdicao
        for edicao in db.session.scalars(select(GuiaEdicao)).all():
            extensoes.setdefault(edicao.id_topico, {})["edicao"] = _campos(edicao)
    if _tem_tabela("guia_midia"):
        from models import GuiaMidia
        for midia in db.session.scalars(select(GuiaMidia).order_by(GuiaMidia.id)).all():
            extensoes.setdefault(midia.id_topico, {}).setdefault("midias", []).append(_campos(midia))
    marcadores = [i for i, topico in enumerate(topicos)
                  if _normalizar(topico.pergunta) == "ez test guia"
                  or _normalizar(topico.categoria) == "ez test guia"]
    testes_conhecidos = [i for i, topico in enumerate(topicos) if _teste_conhecido(topico)]
    fronteira = marcadores[0] if len(marcadores) == 1 else (min(testes_conhecidos) if testes_conhecidos else None)
    inventario = []
    for indice, topico in enumerate(topicos):
        upload = _normalizar(topico.categoria) == "upload"
        teste = motivo_teste(topico.categoria, topico.pergunta, topico.resposta)
        if upload:
            classificacao, motivo = PRESERVAR, "Seção Upload preservada expressamente, inclusive suas mídias."
        elif indice in testes_conhecidos:
            classificacao, motivo = REMOVER, "Família ZZTESTE-guia/ZZTEST-guia de teste identificada na referência visual."
        elif fronteira is None:
            classificacao, motivo = REVISAR, "Não há fronteira inequívoca de teste; confirme a ordem visual e a finalidade."
        elif indice < fronteira:
            classificacao, motivo = PRESERVAR, "Tópico anterior ao marcador na ordem legada (categoria, ID)."
        elif indice == fronteira:
            classificacao, motivo = REMOVER, "Marcador EZ Test Guia identificado explicitamente na solicitação."
        elif teste:
            classificacao, motivo = REVISAR, f"Após a fronteira, com sinal de teste fora das famílias confirmadas: {teste}. Revise individualmente."
        else:
            classificacao, motivo = REVISAR, "Após o marcador; finalidade não confirmada. Exige revisão individual."
        inventario.append({
            "id": topico.id, "pergunta": topico.pergunta, "titulo": topico.pergunta,
            "categoria": topico.categoria, "ativo": bool(topico.ativo),
            "ordem_visual": indice + 1, "imagem_url": topico.imagem_url,
            "classificacao": classificacao, "motivo": motivo,
            "acao_prevista": "preservar" if classificacao == PRESERVAR else (
                "despublicar após backup" if classificacao == REMOVER else "revisar antes de decidir"),
            "data_atualizacao": topico.data_atualizacao,
            # A impressão detecta inclusive alteração de resposta, sem expor seu
            # texto integral no inventário ou no formulário administrativo.
            "conteudo_sha256": hashlib.sha256(topico.resposta.encode("utf-8")).hexdigest(),
            "editorial_sha256": hashlib.sha256(_serializar(extensoes.get(topico.id, {}))).hexdigest(),
        })
    return inventario


def fingerprint(inventario):
    """Identifica a revisão exata do inventário exibido ao administrador."""
    return hashlib.sha256(_serializar(inventario)).hexdigest()


def _ids(ids):
    try:
        valores = list(ids)
        if any(isinstance(valor, bool) or not isinstance(valor, (int, str))
               or not re.fullmatch(r"[1-9][0-9]*", str(valor)) for valor in valores):
            raise ValueError
        ids_validos = {int(valor) for valor in valores}
    except (ValueError, TypeError, OverflowError):
        raise LimpezaGuiaErro("Selecione identificadores válidos de tópicos.") from None
    if not ids_validos or len(ids_validos) > MAX_TOPICOS or min(ids_validos) <= 0:
        raise LimpezaGuiaErro(f"Selecione de 1 a {MAX_TOPICOS} tópicos existentes.")
    return sorted(ids_validos)


def validar_selecao(ids, inventario=None, *, revisados=()):
    """Não permite selecionar registros protegidos ou revisar em massa por posição."""
    selecionados = _ids(ids)
    linhas = {item["id"]: item for item in (inventario if inventario is not None else inventariar())}
    revisados = set(_ids(revisados)) if revisados else set()
    if any(id_topico not in linhas for id_topico in selecionados):
        raise LimpezaGuiaErro("Um tópico selecionado não existe mais. Atualize o inventário.")
    if any(linhas[id_topico]["classificacao"] == PRESERVAR for id_topico in selecionados):
        raise LimpezaGuiaErro("Upload e os tópicos classificados como PRESERVAR não podem integrar esta limpeza.")
    if any(linhas[id_topico]["classificacao"] == REVISAR and id_topico not in revisados for id_topico in selecionados):
        raise LimpezaGuiaErro("Confirme individualmente a revisão dos tópicos com classificação REVISAR.")
    return selecionados


def _arquivo_banco(referencia):
    chave = referencia[len(storage.PREFIXO_DB):]
    if not chave.startswith("guia/") or not storage.chave_valida(chave):
        raise LimpezaGuiaErro("Referência de mídia do Guia inválida; backup interrompido.")
    linha = db.session.execute(select(
        ArquivoArmazenado.tamanho, ArquivoArmazenado.content_type,
        func.length(ArquivoArmazenado.conteudo),
    ).where(ArquivoArmazenado.chave == chave)).first()
    if linha is None or linha[0] != linha[2] or not 0 < linha[2] <= MAX_ARQUIVO_BYTES:
        raise LimpezaGuiaErro("Mídia ausente, inconsistente ou acima do limite seguro de backup; nada foi despublicado.")
    conteudo = db.session.scalar(select(ArquivoArmazenado.conteudo).where(ArquivoArmazenado.chave == chave))
    return bytes(conteudo), linha[1]


def _arquivo_legado(referencia):
    nome = PurePosixPath(referencia)
    if nome.is_absolute() or nome.parts[:2] != ("uploads", "guia") or len(nome.parts) != 3 or "\\" in referencia:
        raise LimpezaGuiaErro("Mídia legada fora da pasta do Guia; backup interrompido.")
    raiz = Path(current_app.static_folder).resolve() / "uploads" / "guia"
    caminho = raiz / nome.name
    try:
        resolvido = caminho.resolve(strict=True)
        if not resolvido.is_relative_to(raiz.resolve()) or not resolvido.is_file():
            raise ValueError
        with resolvido.open("rb") as arquivo:
            conteudo = arquivo.read(MAX_ARQUIVO_BYTES + 1)
    except (OSError, ValueError):
        raise LimpezaGuiaErro("Mídia legada indisponível; backup interrompido sem despublicar dados.") from None
    if not 0 < len(conteudo) <= MAX_ARQUIVO_BYTES:
        raise LimpezaGuiaErro("Mídia legada vazia ou acima do limite seguro de backup.")
    return conteudo, None


def exportar_backup(ids):
    """ZIP privado: registros completos, metadados e bytes deduplicados com SHA256.

    Pode exportar qualquer tópico selecionado, inclusive um registro protegido;
    exportar não implica autorização para despublicar. Limites mantêm o download
    utilizável no servidor: grupos grandes devem ser divididos pelo operador.
    """
    selecionados = _ids(ids)
    topicos = db.session.scalars(select(GuiaTopico).where(GuiaTopico.id.in_(selecionados)).order_by(GuiaTopico.id)).all()
    if len(topicos) != len(selecionados):
        raise LimpezaGuiaErro("Não foi possível localizar todos os tópicos para o backup.")
    manifesto = {
        "formato": "nexo-guia-backup-v1", "gerado_em": datetime.now(timezone.utc),
        "topicos": [_campos(topico) for topico in topicos],
        "edicoes": [], "midias": [], "arquivos": [],
    }
    referencias = {topico.imagem_url for topico in topicos if topico.imagem_url}
    if _tem_tabela("guia_edicao"):
        from models import GuiaEdicao
        manifesto["edicoes"] = [_campos(edicao) for edicao in db.session.scalars(
            select(GuiaEdicao).where(GuiaEdicao.id_topico.in_(selecionados)).order_by(GuiaEdicao.id_topico)).all()]
    if _tem_tabela("guia_midia"):
        from models import GuiaMidia
        midias = db.session.scalars(select(GuiaMidia).where(GuiaMidia.id_topico.in_(selecionados)).order_by(GuiaMidia.id)).all()
        manifesto["midias"] = [_campos(midia) for midia in midias]
        referencias.update(midia.referencia for midia in midias)
    saida = io.BytesIO()
    total = 0
    with zipfile.ZipFile(saida, "w", compression=zipfile.ZIP_STORED) as arquivo_zip:
        for indice, referencia in enumerate(sorted(referencias), start=1):
            if not isinstance(referencia, str):
                raise LimpezaGuiaErro("Referência de mídia inválida no tópico.")
            conteudo, tipo = (_arquivo_banco(referencia) if referencia.startswith(storage.PREFIXO_DB)
                              else _arquivo_legado(referencia))
            total += len(conteudo)
            if total > MAX_BACKUP_BYTES:
                raise LimpezaGuiaErro("O backup excede 64 MiB; divida a seleção em grupos menores.")
            caminho = f"midias/{indice:04d}.bin"
            arquivo_zip.writestr(caminho, conteudo)
            manifesto["arquivos"].append({
                "referencia": referencia, "arquivo": caminho, "tamanho": len(conteudo),
                "content_type": tipo, "sha256": hashlib.sha256(conteudo).hexdigest(),
            })
        dados = _serializar(manifesto)
        if len(dados) + total > MAX_BACKUP_BYTES:
            raise LimpezaGuiaErro("O backup excede 64 MiB; divida a seleção em grupos menores.")
        arquivo_zip.writestr("manifesto.json", dados)
        arquivo_zip.writestr("manifesto.sha256", hashlib.sha256(dados).hexdigest() + "  manifesto.json\n")
        arquivo_zip.writestr("RECUPERACAO.md", _INSTRUCOES_RECUPERACAO)
    return saida.getvalue()


def despublicar(ids, fingerprint_expected, *, revisados=()):
    """Despublica somente IDs revisados; conserva registros e todas as mídias.

    Não executa COMMIT. O recibo de backup e a autorização devem ser exigidos
    pela rota antes de chamar este helper. Rollback restaura o estado anterior.
    """
    inventario = inventariar()
    if not isinstance(fingerprint_expected, str) or fingerprint(inventario) != fingerprint_expected:
        raise LimpezaGuiaErro("O Guia mudou desde o inventário. Revise e gere um novo backup.")
    selecionados = validar_selecao(ids, inventario, revisados=revisados)
    topicos = db.session.scalars(select(GuiaTopico).where(GuiaTopico.id.in_(selecionados)).with_for_update()).all()
    # Com lock, repetir a impressão impede aplicar uma seleção sobre texto,
    # categoria ou publicação alterados por outra sessão administrativa.
    db.session.expire_all()
    if fingerprint(inventariar()) != fingerprint_expected:
        raise LimpezaGuiaErro("O Guia mudou durante a confirmação. Gere um novo inventário e backup.")
    despublicados = 0
    for topico in topicos:
        if topico.ativo:
            if _tem_tabela("guia_edicao"):
                from models import GuiaEdicao
                edicao = db.session.get(GuiaEdicao, topico.id)
                if edicao is None:
                    edicao = GuiaEdicao(id_topico=topico.id, versao=1)
                    db.session.add(edicao)
                else:
                    edicao.versao += 1
                if not edicao.publicado_em:
                    edicao.publicado_em = topico.data_atualizacao or topico.data_criacao or datetime.now(timezone.utc)
            topico.ativo = False
            topico.data_atualizacao = datetime.now(timezone.utc)
            despublicados += 1
    return {"selecionados": len(topicos), "despublicados": despublicados, "excluidos": 0,
            "preservados": len(inventario) - len(topicos)}


_INSTRUCOES_RECUPERACAO = """# Recuperação do backup privado do Guia

Este arquivo contém somente os tópicos selecionados e suas mídias. Guarde-o em
local privado. Não adicione o ZIP ao GitHub nem à pasta pública da aplicação.

1. Confira o SHA256 de manifesto.json com manifesto.sha256. Para cada entrada de
   arquivos no manifesto, confira tamanho e SHA256 do arquivo binário indicado.
2. A limpeza apenas despublica: para reverter normalmente, abra o tópico no CMS,
   revise-o e publique novamente. Seus textos e mídias não foram apagados.
3. Para recuperação após perda real, use uma cópia descartável do banco primeiro.
   Restaure cada topico e seus metadados editoriais respeitando os IDs e vínculos;
   importe os bytes pela camada storage.salvar sob a referência original db:guia/.
   Não sobrescreva IDs existentes sem comparar os registros e obter autorização.
4. Para mídias legadas, o manifesto preserva a referência relativa; restaure os
   bytes somente dentro da pasta static/uploads/guia, sem aceitar caminhos externos.
5. Confira blocos, histórico, imagens e vídeos na prévia administrativa e mantenha
   o tópico despublicado até a revisão final. Teste a publicação com contas fictícias.

Nenhuma instrução deste arquivo executa migração, restauração ou publicação
automaticamente. Não use o arquivo para substituir o banco inteiro da empresa.
"""
