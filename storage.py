"""
NEXO - Faturamento Inteligente | Camada de armazenamento de arquivos
====================================================================
PONTO ÚNICO de acesso ao storage dos relatórios ERP (Vendas/Compras) e das
imagens do Guia. Nenhuma rota lê ou grava arquivo diretamente: todas falam só
com esta interface (salvar / resolver / remover / obter / url_midia).

ONDE OS ARQUIVOS FICAM: no próprio Postgres (tabela `arquivo_armazenado`).
Motivo: em host gratuito (Render Free) o disco é EFÊMERO — o que é gravado no
filesystem some a cada deploy, restart ou hibernação. No banco, o arquivo
sobrevive e ainda entra na MESMA transação do registro que o referencia.

REFERÊNCIAS PERSISTIDAS (ex.: upload_relatorio.caminho_arquivo):
  - 'db:<chave>'  → arquivo guardado no banco (formato atual);
  - qualquer outro valor → caminho LEGADO no filesystem (uploads feitos antes
    desta mudança). Continuam legíveis; migrar_arquivos_para_db.py os copia
    para o banco.
"""

import os
import stat
from contextlib import contextmanager
import mimetypes
import tempfile
import threading
from pathlib import Path

from flask import current_app, url_for
from sqlalchemy import func, select

from etl_inputs import ETLInputError

from extensions import db
from models import ArquivoArmazenado

PREFIXO_DB = "db:"

# Cópias locais temporárias dos arquivos do banco: o motor de ETL (pandas/csv)
# lê de um caminho no disco. As chaves carregam o hash do conteúdo, então a
# mesma chave sempre corresponde aos mesmos bytes e a cópia pode ser reusada.
_CACHE_DIR = Path(tempfile.gettempdir()) / "nexo_arquivos"


def _chave(referencia: str) -> str:
    return referencia[len(PREFIXO_DB):]


def _no_cache(chave: str) -> Path:
    return _CACHE_DIR / chave


def salvar(conteudo: bytes, nome_final: str) -> str:
    """Grava os bytes no banco sob a chave `nome_final` e devolve a referência
    persistida ('db:<nome_final>'). NÃO comita: entra na transação do chamador,
    que comita junto com o registro que cita o arquivo (rollback desfaz os dois).
    Regravar a mesma chave substitui o conteúdo (re-upload idêntico)."""
    registro = db.session.get(ArquivoArmazenado, nome_final)
    if registro is None:
        registro = ArquivoArmazenado(chave=nome_final)
        db.session.add(registro)
    registro.conteudo = conteudo
    registro.tamanho = len(conteudo)
    registro.content_type = mimetypes.guess_type(nome_final)[0]
    return PREFIXO_DB + nome_final


def obter(chave: str):
    """Registro ArquivoArmazenado da chave (ou None). Usado para servir mídia."""
    return db.session.get(ArquivoArmazenado, chave)


def resolver(caminho_arquivo: str) -> str:
    """Resolve a referência salva para um caminho absoluto legível no disco.

    - 'db:<chave>': materializa o conteúdo do banco numa cópia temporária local.
      Se a chave não existir, devolve um caminho inexistente — o ETL então acusa
      "Arquivo não encontrado" (falha segura, sem exceção aqui).
    - Legado: relativiza ao UPLOAD_FOLDER quando o valor persistido não existe
      como caminho direto.
    """
    if caminho_arquivo.startswith(PREFIXO_DB):
        return _materializar(_chave(caminho_arquivo))

    caminho = caminho_arquivo
    # Vale também para caminho ABSOLUTO inexistente: se o projeto mudou de pasta
    # (ou de máquina), o path gravado no banco fica obsoleto, mas o arquivo segue
    # no UPLOAD_FOLDER atual com o mesmo nome. O replace cobre paths do Windows
    # lidos em Linux (basename não separa por "\" fora do Windows).
    if not os.path.exists(caminho):
        nome = os.path.basename(caminho.replace("\\", "/"))
        caminho = os.path.join(current_app.config["UPLOAD_FOLDER"], nome)
    return caminho



@contextmanager
def materializar_para_etl(referencia: str, max_bytes: int):
    """Cópia exclusiva e limitada para ETL; nunca remove fonte ou cache comum.

    O tamanho real do BYTEA é verificado no servidor e novamente no SELECT que
    carrega os bytes. O campo tamanho e o cache compartilhado não são autoridade.
    Referências legadas mantêm a resolução anterior, mas são copiadas com limite
    para arquivo próprio, regular e privado, removido ao sair do contexto.
    """
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ETLInputError("invalid_limits", "Configuração de processamento inválida.")
    if not isinstance(referencia, str) or not referencia:
        raise ETLInputError("storage_unavailable", "Arquivo armazenado indisponível. Reenvie o relatório.")
    extension = Path(referencia).suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise ETLInputError("unsupported_format", "Formato armazenado não suportado. Reenvie em CSV ou XLSX.")
    payload = None
    source_fd = None
    try:
        if referencia.startswith(PREFIXO_DB):
            chave = _chave(referencia)
            actual_length = func.length(ArquivoArmazenado.conteudo)
            with db.session.no_autoflush:
                size = db.session.scalar(select(actual_length).where(ArquivoArmazenado.chave == chave))
                if size is None:
                    raise ETLInputError("storage_unavailable", "Arquivo armazenado indisponível. Reenvie o relatório.")
                if size > max_bytes:
                    raise ETLInputError("file_size", "Arquivo armazenado acima do tamanho permitido para processamento.")
                payload = db.session.scalar(select(ArquivoArmazenado.conteudo).where(
                    ArquivoArmazenado.chave == chave, actual_length <= max_bytes,
                ))
            # A segunda condição também protege alterações concorrentes do blob.
            if payload is None:
                raise ETLInputError("storage_unavailable", "Arquivo armazenado indisponível. Reenvie o relatório.")
            if not payload:
                raise ETLInputError("empty_file", "Arquivo armazenado vazio. Reenvie o relatório.")
            if len(payload) > max_bytes:
                raise ETLInputError("file_size", "Arquivo armazenado acima do tamanho permitido para processamento.")
        else:
            # NONBLOCK permite recusar FIFO/dispositivo antes de qualquer leitura.
            source_fd = os.open(resolver(referencia), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
            info = os.fstat(source_fd)
            if not stat.S_ISREG(info.st_mode):
                raise ETLInputError("storage_unavailable", "Arquivo armazenado indisponível. Reenvie o relatório.")
            if info.st_size > max_bytes:
                raise ETLInputError("file_size", "Arquivo armazenado acima do tamanho permitido para processamento.")
        with tempfile.TemporaryDirectory(prefix="nexo-etl-materialized-") as directory:
            destination = Path(directory) / ("arquivo" + extension)
            with destination.open("wb") as output:
                destination.chmod(0o600)
                if payload is not None:
                    output.write(payload)
                else:
                    total = 0
                    with os.fdopen(source_fd, "rb") as source:
                        source_fd = None
                        while True:
                            chunk = source.read(min(64 * 1024, max_bytes + 1 - total))
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > max_bytes:
                                raise ETLInputError("file_size", "Arquivo armazenado acima do tamanho permitido para processamento.")
                            output.write(chunk)
                    if total == 0:
                        raise ETLInputError("empty_file", "Arquivo armazenado vazio. Reenvie o relatório.")
            # Não reter o BYTEA enquanto o processo isolado calcula os KPIs.
            payload = None
            yield str(destination)
    except OSError:
        raise ETLInputError("storage_unavailable", "Não foi possível preparar o arquivo armazenado. Reenvie o relatório.") from None
    finally:
        if source_fd is not None:
            os.close(source_fd)


def _materializar(chave: str) -> str:
    destino = _no_cache(chave)
    if destino.exists():
        return str(destino)
    registro = obter(chave)
    if registro is None:
        return str(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Escrita atômica (arquivo temporário + rename): duas requisições
    # simultâneas nunca leem uma cópia pela metade.
    tmp = destino.with_name(f"{destino.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_bytes(registro.conteudo)
    os.replace(tmp, destino)
    return str(destino)


def remover(caminho_arquivo: str) -> None:
    """Remove o arquivo referenciado.

    - 'db:<chave>': apaga a linha na transação do chamador (efetivada no commit
      dele) e descarta a cópia local temporária.
    - Legado: remove o arquivo físico (best-effort: erros de IO são silenciados,
      pois a remoção do registro no banco é o que de fato importa).
    """
    if not caminho_arquivo:
        return
    if caminho_arquivo.startswith(PREFIXO_DB):
        chave = _chave(caminho_arquivo)
        registro = obter(chave)
        if registro is not None:
            db.session.delete(registro)
        try:
            _no_cache(chave).unlink(missing_ok=True)
        except OSError:
            pass
        return
    try:
        alvo = resolver(caminho_arquivo)
        if alvo and os.path.exists(alvo):
            os.remove(alvo)
    except OSError:
        pass


def url_midia(referencia: str) -> str:
    """URL pública (para <img src>) de uma mídia do Guia. Referências 'db:' são
    servidas pela rota /midia/; as legadas continuam vindo de static/."""
    if not referencia:
        return ""
    if referencia.startswith(PREFIXO_DB):
        return url_for("midia", chave=_chave(referencia))
    return url_for("static", filename=referencia)
