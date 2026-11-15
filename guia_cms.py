"""Edição institucional do Guia; publicação continua autorizada por ativo.

As tabelas editoriais são opcionais até a migração ser autorizada. Leituras
legadas do portal e do NexoBot não dependem delas. Nenhum método faz commit.
"""

import copy
import hashlib
import json
import re
import threading
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ArquivoArmazenado, GuiaTopico
import storage


MAX_TEXTO = 65536
MAX_BLOCOS = 80
MAX_MIDIAS = 12
MAX_TOPICO_BYTES = 24 * 1024 * 1024
MAX_GUIA_BYTES = 128 * 1024 * 1024
_EDICAO_TRAVA = threading.BoundedSemaphore(1)


class GuiaErro(ValueError):
    pass


class GuiaConflito(GuiaErro):
    pass


def esquema_disponivel():
    try:
        insp = inspect(db.session.connection())
        return all(insp.has_table(t) for t in ("guia_edicao", "guia_midia"))
    except SQLAlchemyError:
        db.session.rollback()
        return False


def _modelos():
    from models import GuiaEdicao, GuiaMidia
    return GuiaEdicao, GuiaMidia


def link_seguro(valor):
    if not isinstance(valor, str) or len(valor) > 2048:
        return ""
    valor = valor.strip()
    if not valor or "\\" in valor or any(ord(c) < 32 or ord(c) == 127 for c in valor):
        return ""
    try:
        u = urlsplit(valor)
        if u.scheme.lower() in ("http", "https") and u.hostname and not u.username and not u.password:
            return valor
        if u.scheme.lower() == "mailto" and "@" in u.path and not u.netloc:
            return valor
        if not u.scheme and not u.netloc and valor.startswith(("/", "#")) and not valor.startswith("//"):
            return valor
    except ValueError:
        pass
    return ""


class _HTMLSeguro(HTMLParser):
    permitidas = {"p", "h2", "h3", "strong", "em", "b", "i", "ul", "ol", "li", "a", "br", "blockquote"}
    ignoradas = {"script", "style", "iframe", "object", "embed", "svg", "math", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.saida, self.pilha, self.ignorar = [], [], []
        self.nos = 0

    def handle_starttag(self, tag, attrs):
        self.nos += 1
        if self.nos > 2048:
            raise GuiaErro("Conteúdo com formatação excessivamente complexa.")
        if self.ignorar:
            if tag in self.ignoradas:
                self.ignorar.append(tag)
            return
        if tag in self.ignoradas:
            self.ignorar.append(tag)
            return
        if tag not in self.permitidas:
            return
        atributo = ""
        if tag == "a":
            href = link_seguro(dict(attrs).get("href", ""))
            if href:
                atributo = ' href="' + escape(href, quote=True) + '" rel="noopener noreferrer"'
        self.saida.append("<" + tag + atributo + ">")
        if tag != "br":
            self.pilha.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != "br":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.ignorar:
            if tag == self.ignorar[-1]:
                self.ignorar.pop()
            return
        if tag in self.pilha:
            while self.pilha:
                atual = self.pilha.pop()
                self.saida.append("</" + atual + ">")
                if atual == tag:
                    break

    def handle_data(self, valor):
        if not self.ignorar:
            self.saida.append(escape(valor))

    def resultado(self):
        return "".join(self.saida) + "".join("</" + t + ">" for t in reversed(self.pilha))


def sanitizar_html(valor):
    if not isinstance(valor, str) or len(valor) > MAX_TEXTO:
        raise GuiaErro("O conteúdo deve ter até 65.536 caracteres.")
    parser = _HTMLSeguro()
    parser.feed(valor)
    parser.close()
    saida = parser.resultado()
    if len(saida) > MAX_TEXTO:
        raise GuiaErro("O conteúdo formatado excede o limite permitido.")
    return saida


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []

    def handle_data(self, data):
        self.partes.append(data)

    def handle_endtag(self, tag):
        if tag in {"p", "h2", "h3", "li", "blockquote"}:
            self.partes.append("\n")

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.partes.append("\n")


def texto_html(valor):
    parser = _Texto()
    parser.feed(valor)
    return "".join(parser.partes).strip()


def _url(referencia):
    if not referencia:
        return ""
    if referencia.startswith("db:guia/") or referencia.startswith("uploads/guia/"):
        return storage.url_midia(referencia)
    return ""


def _estado(topico, edicao):
    if edicao and edicao.excluido_em:
        return "excluido"
    if topico.ativo:
        return "publicado"
    return "despublicado" if edicao and edicao.publicado_em else "rascunho"


def _utc(valor):
    return valor.replace(tzinfo=timezone.utc) if valor and valor.tzinfo is None else valor


def visualizar(topico, edicao=None, midias=None, disponivel=None):
    if disponivel is None:
        disponivel = esquema_disponivel()
    if disponivel:
        Edicao, Midia = _modelos()
        edicao = edicao or db.session.get(Edicao, topico.id)
        if midias is None:
            midias = db.session.scalars(select(Midia).where(Midia.id_topico == topico.id)).all()
    por_id = {m.id: m for m in midias or ()}
    blocos = []
    if edicao and isinstance(edicao.blocos, list) and edicao.blocos:
        for bloco in edicao.blocos[:MAX_BLOCOS]:
            if not isinstance(bloco, dict):
                continue
            if bloco.get("tipo") == "texto":
                blocos.append({"tipo": "texto", "html": sanitizar_html(bloco.get("html", ""))})
            elif bloco.get("tipo") == "midia" and bloco.get("id") in por_id:
                m = por_id[bloco["id"]]
                blocos.append(dict(tipo="midia", id=m.id, url=_url(m.referencia),
                                   tipo_midia=m.tipo, legenda=m.legenda, alt=m.alt))
    else:
        blocos.append({"tipo": "texto", "html": "<p>" + escape(topico.resposta).replace("\n", "<br>") + "</p>"})
        if topico.imagem_url:
            blocos.append(dict(tipo="midia", id="legado", url=_url(topico.imagem_url),
                               tipo_midia="imagem", legenda="", alt="Ilustração: " + topico.pergunta))
    tipos = {b.get("tipo_midia") for b in blocos if b["tipo"] == "midia"}
    tipo = "Tutorial com múltiplas mídias" if len(tipos) > 1 else (
        "Texto com imagens" if "imagem" in tipos else "Texto com vídeo" if "video" in tipos else "Texto")
    return dict(id=topico.id, categoria=topico.categoria, pergunta=topico.pergunta,
                resposta=topico.resposta, descricao=edicao.descricao if edicao else "",
                ativo=bool(topico.ativo), status=_estado(topico, edicao),
                data_criacao=_utc(topico.data_criacao), data_atualizacao=_utc(topico.data_atualizacao),
                ordem=edicao.ordem if edicao else 0, versao=edicao.versao if edicao else 0,
                blocos=blocos, tipo_conteudo=tipo, excluido=bool(edicao and edicao.excluido_em))


def listar(somente_publicados=False):
    disponivel = esquema_disponivel()
    consulta = select(GuiaTopico)
    if somente_publicados:
        consulta = consulta.where(GuiaTopico.ativo.is_(True))
    topicos = db.session.scalars(consulta.order_by(GuiaTopico.categoria, GuiaTopico.id)).all()
    edicoes, midias = {}, {}
    if disponivel:
        Edicao, Midia = _modelos()
        edicoes = {e.id_topico: e for e in db.session.scalars(select(Edicao))}
        for midia in db.session.scalars(select(Midia)):
            midias.setdefault(midia.id_topico, []).append(midia)
    resultado = [visualizar(t, edicoes.get(t.id), midias.get(t.id, []), disponivel) for t in topicos]
    if somente_publicados:
        resultado = [t for t in resultado if not t["excluido"]]
    return sorted(resultado, key=lambda t: (t["categoria"], t["ordem"], t["id"]))


def _campo(form, chave, tamanho, obrigatorio=False):
    valor = form.get(chave)
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise GuiaErro(f"O campo {chave} deve conter texto.")
    valor = valor.strip()
    if (obrigatorio and not valor) or len(valor) > tamanho:
        raise GuiaErro(f"Preencha {chave} com até {tamanho} caracteres.")
    return valor


def _versao(edicao, form):
    atual = edicao.versao if edicao else 0
    if edicao and "versao" not in form:
        raise GuiaConflito("Reabra o tópico para obter a versão atual antes de salvar.")
    try:
        recebida = int(form.get("versao", atual))
    except (TypeError, ValueError):
        raise GuiaConflito("Versão inválida. Reabra o tópico antes de salvar.")
    if recebida != atual:
        raise GuiaConflito("Este tópico foi alterado em outra janela. Reabra antes de salvar.")


def _trava_quota():
    if db.session.get_bind().dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(1313293641)"))


def _quota(topico, novos):
    Edicao, Midia = _modelos()
    chaves = set(db.session.scalars(select(Midia.referencia).where(Midia.id_topico == topico.id))) if topico.id else set()
    if topico.imagem_url:
        chaves.add(topico.imagem_url)
    chaves.update("db:" + chave for chave, _ in novos)
    atuais = [c[3:] for c in chaves if c.startswith("db:")]
    tamanho = db.session.scalar(select(func.coalesce(func.sum(func.length(ArquivoArmazenado.conteudo)), 0))
                                .where(ArquivoArmazenado.chave.in_(atuais))) if atuais else 0
    existentes = set(db.session.scalars(select(ArquivoArmazenado.chave).where(
        ArquivoArmazenado.chave.in_([c for c, _ in novos])))) if novos else set()
    adicional = sum(len(m.conteudo) for chave, m in dict(novos).items() if chave not in existentes)
    total = db.session.scalar(select(func.coalesce(func.sum(func.length(ArquivoArmazenado.conteudo)), 0))
                              .where(ArquivoArmazenado.chave.startswith("guia/")))
    if int(tamanho) + adicional > MAX_TOPICO_BYTES:
        raise GuiaErro("O tópico atingiu 24 MiB de mídias, incluindo o histórico recuperável.")
    if int(total) + adicional > MAX_GUIA_BYTES:
        raise GuiaErro("O Guia atingiu a quota de 128 MiB. Revise o armazenamento com backup antes de ampliar.")


def salvar(topico, form, files):
    # Um lote mantém os bytes preparados até a gravação transacional. A trava
    # limita lotes simultâneos por processo; a quota PostgreSQL continua global.
    if not _EDICAO_TRAVA.acquire(blocking=False):
        raise GuiaErro("Outro tutorial está sendo salvo. Aguarde alguns instantes e tente novamente.")
    try:
        return _salvar(topico, form, files)
    finally:
        _EDICAO_TRAVA.release()


def _salvar(topico, form, files):
    if not esquema_disponivel():
        raise GuiaErro("Gerenciamento ampliado indisponível até a aplicação autorizada da migração do Guia.")
    from guia_midias import validar_upload
    Edicao, Midia = _modelos()
    edicao = db.session.get(Edicao, topico.id) if topico.id else None
    _versao(edicao, form)
    if edicao and edicao.excluido_em:
        raise GuiaErro("Restaure o tópico antes de editar.")
    categoria = _campo(form, "categoria", 80, True)
    pergunta = _campo(form, "pergunta", 240, True)
    descricao = _campo(form, "descricao", 500)
    try:
        ordem = int(form.get("ordem", 0))
    except (ValueError, TypeError):
        raise GuiaErro("A ordem deve ser um número entre 0 e 9999.")
    if not 0 <= ordem <= 9999:
        raise GuiaErro("A ordem deve ser um número entre 0 e 9999.")
    status = form.get("status") or ("publicado" if form.get("ativo") else "rascunho")
    if status not in {"rascunho", "publicado", "despublicado"}:
        raise GuiaErro("Status de publicação inválido.")
    antigos = {m.id: m for m in db.session.scalars(select(Midia).where(Midia.id_topico == topico.id))} if topico.id else {}
    bruto = form.get("blocos_json")
    if bruto is None:
        resposta = _campo(form, "resposta", MAX_TEXTO, True)
        blocos = [{"tipo": "texto", "html": "<p>" + escape(resposta).replace("\n", "<br>") + "</p>"}]
        if files.get("imagem") and files["imagem"].filename:
            blocos.append({"tipo": "midia", "id": "nova_legada"})
        elif topico.imagem_url and not form.get("remover_imagem"):
            # Edições antigas conservam a imagem atual em vez de removê-la.
            if antigos:
                existente = next((m.id for m in antigos.values() if m.referencia == topico.imagem_url), "legado")
            else:
                existente = "legado"
            blocos.append({"tipo": "midia", "id": existente})
    else:
        if len(bruto) > MAX_TEXTO * 2:
            raise GuiaErro("Conteúdo acima do limite permitido.")
        try:
            blocos = json.loads(bruto)
        except (TypeError, ValueError):
            raise GuiaErro("Estrutura de conteúdo inválida.")
    if not isinstance(blocos, list) or not 1 <= len(blocos) <= MAX_BLOCOS:
        raise GuiaErro("Use entre 1 e 80 blocos de conteúdo.")
    preparados, uploads, vistos = [], [], set()
    texto_total = 0
    for bloco in blocos:
        if not isinstance(bloco, dict):
            raise GuiaErro("Bloco de conteúdo inválido.")
        if bloco.get("tipo") == "texto":
            html = sanitizar_html(bloco.get("html", ""))
            texto_total += len(html)
            preparados.append({"tipo": "texto", "html": html})
        elif bloco.get("tipo") == "midia":
            identificador = bloco.get("id")
            if isinstance(identificador, bool) or not isinstance(identificador, (int, str)) or str(identificador) in vistos:
                raise GuiaErro("Identificador de mídia inválido ou repetido.")
            vistos.add(str(identificador))
            existente = antigos.get(identificador)
            legado = identificador == "legado" and bool(topico.imagem_url)
            novo = isinstance(identificador, str) and re.fullmatch(r"nova_[a-zA-Z0-9_]{1,48}", identificador)
            if not (existente or legado or novo):
                raise GuiaErro("A mídia não pertence a este tópico.")
            arquivo = files.get("imagem") if identificador == "nova_legada" else files.get("midia_" + str(identificador))
            validado = validar_upload(arquivo) if arquivo and arquivo.filename else None
            if novo and not validado:
                raise GuiaErro("Selecione um arquivo para a nova mídia.")
            chave = "guia/" + hashlib.sha256(validado.conteudo).hexdigest() + "." + validado.extensao if validado else None
            if validado:
                uploads.append((chave, validado))
            preparados.append(dict(tipo="midia", existente=existente, legado=legado,
                                    validado=validado, chave=chave,
                                    legenda=_campo(bloco, "legenda", 500), alt=_campo(bloco, "alt", 240)))
        else:
            raise GuiaErro("Tipo de bloco não permitido.")
    if texto_total > MAX_TEXTO or len(vistos) > MAX_MIDIAS:
        raise GuiaErro("Use até 65.536 caracteres e 12 mídias por tópico.")
    _trava_quota()
    _quota(topico, uploads)
    agora = datetime.now(timezone.utc)
    anterior = visualizar(topico) if topico.id else None
    imagem_anterior = topico.imagem_url
    topico.categoria, topico.pergunta = categoria, pergunta
    db.session.add(topico)
    db.session.flush()
    # A primeira edição também registra a mídia legada que foi removida do
    # documento, mantendo um vínculo recuperável e sua contabilização na quota.
    if anterior and imagem_anterior and not any(m.referencia == imagem_anterior for m in antigos.values()):
        legada = Midia(id_topico=topico.id, referencia=imagem_anterior, tipo="imagem", legenda="", alt="")
        db.session.add(legada)
        db.session.flush()
        antigos[legada.id] = legada
    if edicao is None:
        edicao = Edicao(id_topico=topico.id, versao=1)
        if anterior and anterior["ativo"]:
            edicao.publicado_em = topico.data_atualizacao or topico.data_criacao or agora
        db.session.add(edicao)
    historico = list(edicao.historico or [])
    if anterior:
        historico.append(dict(data=agora.isoformat(), categoria=anterior["categoria"],
                              pergunta=anterior["pergunta"], resposta=anterior["resposta"],
                              descricao=anterior["descricao"], ordem=anterior["ordem"],
                              imagem_url=imagem_anterior, ativo=anterior["ativo"],
                              blocos=copy.deepcopy(edicao.blocos),
                              midias=[dict(id=m.id, referencia=m.referencia, tipo=m.tipo,
                                           legenda=m.legenda, alt=m.alt) for m in antigos.values()
                                      if any(b.get("tipo") == "midia" and b.get("id") == m.id
                                             for b in (edicao.blocos or []))]))
    edicao.historico = historico[-10:]
    salvos, textos, primeira_imagem = [], [], None
    for bloco in preparados:
        if bloco["tipo"] == "texto":
            salvos.append(bloco)
            textos.append(texto_html(bloco["html"]))
            continue
        midia = bloco["existente"]
        if bloco["validado"]:
            validado = bloco["validado"]
            referencia = storage.salvar(validado.conteudo, bloco["chave"])
            # Substituições recebem novo registro; versões anteriores continuam recuperáveis.
            midia = Midia(id_topico=topico.id, referencia=referencia, tipo=validado.tipo)
            db.session.add(midia)
        elif midia is None and bloco["legado"]:
            midia = next((m for m in antigos.values() if m.referencia == imagem_anterior), None)
            if midia is None:
                midia = Midia(id_topico=topico.id, referencia=imagem_anterior, tipo="imagem")
                db.session.add(midia)
        midia.legenda, midia.alt = bloco["legenda"], bloco["alt"]
        db.session.flush()
        salvos.append({"tipo": "midia", "id": midia.id})
        if midia.tipo == "imagem" and primeira_imagem is None:
            primeira_imagem = midia.referencia
    projecao = "\n\n".join(t for t in textos if t).strip()
    if not projecao and not vistos:
        raise GuiaErro("Escreva o conteúdo ou adicione uma mídia ao tutorial.")
    topico.resposta = projecao or descricao or pergunta
    topico.imagem_url = primeira_imagem
    topico.ativo = status == "publicado"
    topico.data_atualizacao = agora
    edicao.descricao, edicao.ordem, edicao.blocos = descricao, ordem, salvos
    if topico.ativo:
        edicao.publicado_em = agora
    # Força atualização/versionamento mesmo quando somente metadados de mídia mudaram.
    if anterior and edicao.versao == anterior["versao"]:
        edicao.versao += 1
    db.session.flush()
    return topico


def alterar_publicacao(topico, acao, versao=None):
    if not esquema_disponivel():
        raise GuiaErro("A migração do Guia ainda não está disponível neste ambiente.")
    Edicao, _ = _modelos()
    edicao = db.session.get(Edicao, topico.id)
    _versao(edicao, {"versao": versao} if versao is not None else {})
    if edicao is None:
        edicao = Edicao(id_topico=topico.id, versao=1)
        if topico.ativo:
            edicao.publicado_em = topico.data_atualizacao or topico.data_criacao
        db.session.add(edicao)
    if acao == "restaurar":
        edicao.excluido_em = None
        edicao.publicado_em = None
        topico.ativo = False
    elif acao in {"publicar", "despublicar"} and not edicao.excluido_em:
        topico.ativo = acao == "publicar"
        if topico.ativo:
            edicao.publicado_em = datetime.now(timezone.utc)
    else:
        raise GuiaErro("Ação de publicação inválida. Restaure tópicos excluídos antes de publicar.")
    topico.data_atualizacao = datetime.now(timezone.utc)
    if edicao.versao:
        edicao.versao += 1
    db.session.flush()


def excluir(topico, versao=None):
    alterar_publicacao(topico, "despublicar", versao)
    Edicao, _ = _modelos()
    edicao = db.session.get(Edicao, topico.id)
    edicao.excluido_em = datetime.now(timezone.utc)
    topico.ativo = False
    # Exclusão lógica conserva registros, mídias e histórico para recuperação.


def pode_servir_referencia(referencia, usuario):
    if not usuario.is_authenticated:
        return False
    if usuario.is_admin:
        return True
    if not getattr(usuario, "is_cliente", False):
        return False
    disponivel = esquema_disponivel()
    # A coluna legada continua sendo autorizada para tópicos publicados.
    for topico in db.session.scalars(select(GuiaTopico).where(GuiaTopico.ativo.is_(True))):
        if topico.imagem_url == referencia:
            return True
    if disponivel:
        Edicao, Midia = _modelos()
        candidatos = db.session.execute(select(Midia, Edicao).join(Edicao, Edicao.id_topico == Midia.id_topico)
            .join(GuiaTopico, GuiaTopico.id == Midia.id_topico)
            .where(Midia.referencia == referencia, GuiaTopico.ativo.is_(True), Edicao.excluido_em.is_(None))).all()
        for midia, edicao in candidatos:
            if any(isinstance(b, dict) and b.get("tipo") == "midia" and b.get("id") == midia.id for b in edicao.blocos or []):
                return True
    return False


def pode_servir(chave, usuario):
    return storage.chave_valida(chave) and chave.startswith("guia/") and pode_servir_referencia("db:" + chave, usuario)
