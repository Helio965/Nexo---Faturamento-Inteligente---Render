"""Validação limitada e entrega de mídias do Guia, sem alterar sua publicação.

O chamador valida a autorização e mantém arquivos e referências na mesma
transação. Vídeos pequenos usam o armazenamento persistente já existente;
não são materializados integralmente na memória durante a reprodução.
"""

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import warnings

from PIL import Image, UnidentifiedImageError


MAX_IMAGEM_BYTES = 3 * 1024 * 1024
MAX_VIDEO_BYTES = 8 * 1024 * 1024
MAX_VIDEO_SEGUNDOS = 180
MAX_IMAGEM_DIMENSAO = 4096
MAX_IMAGEM_PIXELS = 12_000_000
MAX_IMAGEM_QUADROS = 60
MAX_IMAGEM_PIXELS_TOTAIS = 24_000_000
# Imagens antigas podiam ocupar até o limite multipart preexistente (20 MiB).
# A entrega em blocos mantém essas referências legíveis sem afrouxar novos uploads.
MAX_IMAGEM_ARMAZENADA_BYTES = 20 * 1024 * 1024
_TAMANHO_BLOCO = 256 * 1024
_MAX_SAIDA_VALIDADOR = 128 * 1024
# O serviço atual usa um worker com várias threads. Uma validação por processo
# evita multiplicar decodificações e seus orçamentos de memória em paralelo.
_VALIDACAO_TRAVA = threading.BoundedSemaphore(1)
VIDEO_INDISPONIVEL = (
    "Upload de vídeo indisponível neste ambiente: é necessário configurar "
    "FFmpeg e ffprobe com suporte aos limites de recursos do servidor."
)
VIDEO_ORIENTACAO = "MP4 H.264/AAC, até 8 MiB, 3 minutos, 1920 × 1080 e 60 quadros/s."

_IMAGENS = {
    "png": ("PNG", "image/png"),
    "jpg": ("JPEG", "image/jpeg"),
    "jpeg": ("JPEG", "image/jpeg"),
    "webp": ("WEBP", "image/webp"),
    "gif": ("GIF", "image/gif"),
}
_TIPOS = {ext: tipo for ext, (_, tipo) in _IMAGENS.items()} | {"mp4": "video/mp4"}
_RANGE = re.compile(r"bytes=(\d*)-(\d*)\Z", re.ASCII)


class GuiaMidiaErro(ValueError):
    """Arquivo inválido, acima do limite ou validador indisponível."""

    def __init__(self, mensagem, *, operacao=None, codigo_saida=None, motivo=None):
        super().__init__(mensagem)
        # Diagnóstico técnico restrito: nunca retém stderr, nome ou conteúdo da mídia.
        self.operacao = operacao
        self.codigo_saida = codigo_saida
        self.motivo = motivo


@dataclass(frozen=True)
class MidiaValidada:
    conteudo: bytes
    extensao: str
    content_type: str
    tipo: str


def disponibilidade_video() -> bool:
    if os.name != "posix" or not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        return False
    try:
        import resource
        return all(hasattr(resource, nome) for nome in ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_FSIZE"))
    except ImportError:
        return False


def _ler_limitado(arquivo, limite):
    try:
        conteudo = arquivo.read(limite + 1)
    except (OSError, ValueError) as erro:
        raise GuiaMidiaErro("Não foi possível ler o arquivo enviado.") from erro
    if not isinstance(conteudo, bytes) or not conteudo:
        raise GuiaMidiaErro("O arquivo enviado está vazio ou é inválido.")
    if len(conteudo) > limite:
        raise GuiaMidiaErro(f"O arquivo ultrapassa o limite de {limite // (1024 * 1024)} MiB.")
    return conteudo


def _validar_imagem(conteudo, extensao):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(conteudo)) as imagem:
                if imagem.format != _IMAGENS[extensao][0]:
                    raise GuiaMidiaErro("O conteúdo da imagem não corresponde à extensão.")
                largura, altura = imagem.size
                if (largura <= 0 or altura <= 0 or max(largura, altura) > MAX_IMAGEM_DIMENSAO
                        or largura * altura > MAX_IMAGEM_PIXELS):
                    raise GuiaMidiaErro("A imagem excede os limites de resolução permitidos.")
                quadros = getattr(imagem, "n_frames", 1)
                if quadros > MAX_IMAGEM_QUADROS or largura * altura * quadros > MAX_IMAGEM_PIXELS_TOTAIS:
                    raise GuiaMidiaErro("A imagem animada excede o limite de quadros ou resolução acumulada.")
                imagem.verify()
            # verify() não decodifica todos os pixels e quadros de todos os formatos.
            with Image.open(BytesIO(conteudo)) as imagem:
                for quadro in range(quadros):
                    imagem.seek(quadro)
                    imagem.load()
    except GuiaMidiaErro:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as erro:
        raise GuiaMidiaErro("Imagem inválida ou corrompida. Envie PNG, JPEG, WebP ou GIF íntegro.") from erro


def _motivo_validador(codigo, diagnostico):
    texto = diagnostico.lower()
    if b"cannot allocate memory" in texto or b"resource temporarily unavailable" in texto:
        return "recursos"
    if b"unrecognized option" in texto or b"option not found" in texto:
        return "opcao_incompativel"
    if codigo < 0:
        return "sinal"
    return "decodificacao"


def _rodar_validador(operacao, caminho):
    binario = shutil.which("ffprobe" if operacao == "probe" else "ffmpeg")
    if not binario:
        raise GuiaMidiaErro(VIDEO_INDISPONIVEL)
    # O processo Python intermediário aplica rlimits antes de exec(), sem usar
    # preexec_fn (inseguro em um servidor com várias threads).
    comando = [sys.executable, "-I", str(Path(__file__).resolve()), "--processo-video",
               operacao, binario, str(caminho)]
    # As arenas de malloc por thread reservam memória VIRTUAL mesmo com RSS
    # pequeno. No FFmpeg 6.1.1 elas deixam pouca margem sob RLIMIT_AS=512 MiB.
    # Uma arena reduz essa reserva sem ampliar nenhum limite do worker. A
    # configuração é exclusiva dos processos filhos, inclusive após exec().
    ambiente = dict(os.environ, MALLOC_ARENA_MAX="1")
    try:
        with tempfile.TemporaryFile() as saida, tempfile.TemporaryFile() as diagnostico:
            resultado = subprocess.run(comando, stdin=subprocess.DEVNULL, stdout=saida,
                                       stderr=diagnostico, env=ambiente, timeout=10 if operacao == "probe" else 30,
                                       check=False, start_new_session=True)
            if resultado.returncode:
                diagnostico.seek(0)
                motivo = _motivo_validador(resultado.returncode, diagnostico.read(4096))
                raise GuiaMidiaErro("Vídeo inválido, corrompido ou acima dos recursos permitidos para validação.",
                                   operacao=operacao, codigo_saida=resultado.returncode, motivo=motivo)
            saida.seek(0)
            dados = saida.read(_MAX_SAIDA_VALIDADOR + 1)
            if len(dados) > _MAX_SAIDA_VALIDADOR:
                raise GuiaMidiaErro("O vídeo contém metadados excessivos.")
            return dados
    except (OSError, subprocess.TimeoutExpired) as erro:
        raise GuiaMidiaErro("Não foi possível validar o vídeo dentro dos limites do servidor.") from erro


def _numero_positivo(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        raise GuiaMidiaErro("O vídeo não informa duração válida.") from None
    if not math.isfinite(numero) or numero <= 0:
        raise GuiaMidiaErro("O vídeo não informa duração válida.")
    return numero


def _validar_video(conteudo):
    if not disponibilidade_video():
        raise GuiaMidiaErro(VIDEO_INDISPONIVEL)
    # Perfil MP4 comum: ftyp inicial com marca ISO/MP4 reconhecida. Forçar o
    # demuxer MOV abaixo impede que um arquivo disfarçado vire uma playlist.
    marcas = {b"isom", b"iso2", b"iso3", b"iso4", b"iso5", b"iso6", b"iso7", b"iso8", b"iso9",
              b"mp41", b"mp42", b"avc1", b"M4V ", b"dash", b"msdh", b"msix"}
    if (len(conteudo) < 16 or conteudo[4:8] != b"ftyp" or conteudo[8:12] not in marcas
            or not 16 <= int.from_bytes(conteudo[:4], "big") <= min(len(conteudo), 4096)):
        raise GuiaMidiaErro("O arquivo não contém um contêiner MP4 compatível.")
    with tempfile.TemporaryDirectory(prefix="nexo-guia-validacao-") as pasta:
        caminho = Path(pasta) / "video.mp4"
        caminho.write_bytes(conteudo)
        caminho.chmod(0o600)
        try:
            metadados = json.loads(_rodar_validador("probe", caminho))
            formato = metadados["format"]
            duracao = _numero_positivo(formato.get("duration"))
            faixas = metadados["streams"]
            if not isinstance(faixas, list) or not 1 <= len(faixas) <= 2:
                raise GuiaMidiaErro("Use um vídeo MP4 com uma faixa de vídeo e, opcionalmente, uma de áudio.")
            videos = [faixa for faixa in faixas if faixa.get("codec_type") == "video"]
            audios = [faixa for faixa in faixas if faixa.get("codec_type") == "audio"]
            if len(videos) != 1 or len(audios) > 1 or len(videos) + len(audios) != len(faixas):
                raise GuiaMidiaErro("O vídeo contém faixas não permitidas.")
            video = videos[0]
            if video.get("codec_name") != "h264" or any(a.get("codec_name") != "aac" for a in audios):
                raise GuiaMidiaErro("Use MP4 com vídeo H.264 e áudio AAC, quando houver áudio.")
            largura, altura = int(video["width"]), int(video["height"])
            if not 0 < largura <= 1920 or not 0 < altura <= 1080:
                raise GuiaMidiaErro("O vídeo deve ter resolução de até 1920 × 1080.")
            try:
                fps = Fraction(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0")
            except (ValueError, ZeroDivisionError):
                raise GuiaMidiaErro("O vídeo não informa taxa de quadros válida.") from None
            if fps <= 0 or fps > 60:
                raise GuiaMidiaErro("O vídeo deve ter até 60 quadros por segundo.")
            duracoes = [duracao] + [_numero_positivo(f["duration"]) for f in faixas if f.get("duration")]
            if max(duracoes) > MAX_VIDEO_SEGUNDOS:
                raise GuiaMidiaErro("O vídeo deve ter duração de até 3 minutos.")
            _rodar_validador("decode", caminho)
        except GuiaMidiaErro:
            raise
        except (KeyError, TypeError, ValueError, OverflowError, UnicodeError) as erro:
            raise GuiaMidiaErro("Não foi possível identificar um vídeo MP4 íntegro e compatível.") from erro


def validar_upload(arquivo) -> MidiaValidada:
    nome = getattr(arquivo, "filename", None)
    if not isinstance(nome, str) or not nome.strip():
        raise GuiaMidiaErro("Selecione um arquivo de imagem ou vídeo.")
    extensao = Path(nome.replace("\\", "/")).suffix.lower().lstrip(".")
    if extensao not in _TIPOS:
        raise GuiaMidiaErro("Formato não permitido. Use PNG, JPEG, WebP, GIF ou MP4.")
    video = extensao == "mp4"
    if not _VALIDACAO_TRAVA.acquire(blocking=False):
        raise GuiaMidiaErro("Outra mídia está sendo validada. Aguarde alguns instantes e tente novamente.")
    try:
        conteudo = _ler_limitado(arquivo, MAX_VIDEO_BYTES if video else MAX_IMAGEM_BYTES)
        if video:
            _validar_video(conteudo)
        else:
            _validar_imagem(conteudo, extensao)
        return MidiaValidada(conteudo, extensao, _TIPOS[extensao], "video" if video else "imagem")
    finally:
        _VALIDACAO_TRAVA.release()


def _intervalo(cabecalho, total):
    forma = _RANGE.fullmatch(cabecalho.strip())
    if not forma or not any(forma.groups()) or any(len(parte) > 20 for parte in forma.groups()):
        raise ValueError("Intervalo inválido")
    inicio, fim = forma.groups()
    if not inicio:
        sufixo = int(fim)
        if sufixo <= 0:
            raise ValueError("Intervalo inválido")
        return max(0, total - sufixo), total - 1
    inicio = int(inicio)
    fim = min(int(fim), total - 1) if fim else total - 1
    if inicio >= total or fim < inicio:
        raise ValueError("Intervalo inválido")
    return inicio, fim


def servir_midia(chave):
    """Entrega GET/HEAD; o chamador deve verificar publicação/permissão ANTES.

    Consulta o tamanho real no banco, não confia no campo tamanho, e carrega
    no máximo um bloco por vez. Cada bloco libera sua conexão antes de ser
    transmitido, sem prender a sessão de autorização à duração do player.
    """
    from flask import Response, abort, request
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session
    from extensions import db
    from models import ArquivoArmazenado
    import storage

    if request.method not in {"GET", "HEAD"}:
        abort(405)
    if not storage.chave_valida(chave) or not chave.startswith("guia/"):
        abort(404)
    extensao = Path(chave).suffix.lower().lstrip(".")
    esperado = _TIPOS.get(extensao)
    if not esperado:
        abort(404)
    tamanho_real = func.length(ArquivoArmazenado.conteudo)
    metadados = db.session.execute(select(ArquivoArmazenado.content_type, tamanho_real).where(
        ArquivoArmazenado.chave == chave,
    )).first()
    limite = MAX_VIDEO_BYTES if extensao == "mp4" else MAX_IMAGEM_ARMAZENADA_BYTES
    if not metadados or metadados[0] != esperado or not metadados[1] or metadados[1] > limite:
        abort(404)
    total = metadados[1]
    etag = '"' + sha256(f"{chave}:{total}".encode()).hexdigest() + '"'
    cabecalhos = {
        "Content-Type": esperado,
        "Content-Disposition": "inline",
        "Cache-Control": "private, no-store",
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    }
    inicio, fim, status = 0, total - 1, 200
    intervalo = request.headers.get("Range")
    if_range = request.headers.get("If-Range")
    if intervalo and (not if_range or if_range == etag):
        try:
            inicio, fim = _intervalo(intervalo, total)
        except ValueError:
            cabecalhos["Content-Range"] = f"bytes */{total}"
            return Response(status=416, headers=cabecalhos)
        status = 206
        cabecalhos["Content-Range"] = f"bytes {inicio}-{fim}/{total}"
    cabecalhos["Content-Length"] = str(fim - inicio + 1)
    if request.method == "HEAD":
        return Response(status=status, headers=cabecalhos)
    engine = db.engine

    def blocos():
        posicao = inicio
        while posicao <= fim:
            quantidade = min(_TAMANHO_BLOCO, fim - posicao + 1)
            with Session(bind=engine) as consulta:
                bloco = consulta.scalar(select(func.substr(ArquivoArmazenado.conteudo, posicao + 1, quantidade)).where(
                    ArquivoArmazenado.chave == chave, tamanho_real == total,
                ))
            if not bloco or len(bloco) != quantidade:
                return  # mídia removida/substituída durante a reprodução: nunca expõe outro arquivo
            yield bytes(bloco)
            posicao += quantidade

    return Response(blocos(), status=status, headers=cabecalhos)


def _processo_video(operacao, binario, caminho):
    """Worker isolado: limites também se aplicam após exec do FFmpeg/ffprobe."""
    import resource
    limite_memoria = 512 * 1024 * 1024
    cpu = 8 if operacao == "probe" else 20
    resource.setrlimit(resource.RLIMIT_AS, (limite_memoria, limite_memoria))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (_MAX_SAIDA_VALIDADOR, _MAX_SAIDA_VALIDADOR))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    entrada = ["-max_alloc", "67108864", "-f", "mov", "-protocol_whitelist", "file,pipe",
               "-enable_drefs", "0", "-use_absolute_path", "0", "-i", caminho]
    if operacao == "probe":
        argumentos = [binario, "-v", "error", *entrada, "-show_entries",
                      "format=format_name,duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,duration",
                      "-of", "json"]
    elif operacao == "decode":
        argumentos = [binario, "-v", "error", "-nostdin", "-xerror", "-threads", "1",
                      "-filter_threads", "1", "-err_detect", "explode", *entrada,
                      "-map", "0:v:0", "-map", "0:a?", "-threads", "1", "-f", "null", "-"]
    else:
        raise SystemExit(2)
    os.execv(binario, argumentos)


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--processo-video":
        raise SystemExit(2)
    _processo_video(*sys.argv[2:])
