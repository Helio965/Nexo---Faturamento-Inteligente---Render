"""SEC-005: um filho por processo servidor, sem banco, com prazo e AS limitados."""

from dataclasses import asdict
from datetime import date
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading

from etl_limits import ETLLimits, get_limits

_WORKER_PATH = Path(__file__).resolve().with_name("etl_worker.py")
_ADMISSION = threading.BoundedSemaphore(1)


def _worker_environment():
    allowed = {"PATH", "HOME", "SYSTEMROOT", "WINDIR", "TMPDIR", "TEMP", "TMP",
               "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
               "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
               "http_proxy", "https_proxy", "all_proxy", "no_proxy"}
    result = {key: value for key, value in os.environ.items() if key in allowed}
    result.update({key: "1" for key in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def _stop_owned_process(process):
    if process.poll() is None:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
    process.wait(timeout=5)


def _run_job(operation, paths, *, extension=None, limits=None):
    from etl_inputs import ETLInputError
    policy = get_limits() if limits is None else limits
    if not isinstance(policy, ETLLimits):
        raise ValueError("Política ETL inválida.")
    if not _ADMISSION.acquire(blocking=False):
        raise ETLInputError("busy", "Há outro arquivo em validação ou processamento. Tente novamente em instantes.")
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix="nexo-etl-job-") as work:
            root = Path(work)
            request = root / "request.json"
            output = root / "result.json"
            data = json.dumps({"operation": operation, "paths": [os.fspath(path) for path in paths],
                               "extension": extension, "limits": asdict(policy)}, ensure_ascii=True)
            if len(data.encode()) > 16_384:
                raise ETLInputError("request", "Referência de arquivo inválida para processamento.")
            request.write_text(data)
            process = subprocess.Popen(
                [sys.executable, "-I", "-B", str(_WORKER_PATH), str(request), str(output)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=root, env=_worker_environment(), start_new_session=(os.name == "posix"),
            )
            try:
                process.wait(timeout=policy.timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop_owned_process(process)
                raise ETLInputError("timeout", "Tempo de processamento excedido. Reduza ou divida o relatório.") from None
            if not output.is_file() or output.stat().st_size > policy.max_output_bytes:
                raise ETLInputError("worker", "Processamento interrompido pelo limite de recursos ou por arquivo inválido.")
            with output.open("rb") as stream:
                payload = stream.read(policy.max_output_bytes + 1)
            if len(payload) > policy.max_output_bytes:
                raise ETLInputError("output", "Resultado excede o orçamento permitido.")
            try:
                envelope = json.loads(payload)
            except (ValueError, UnicodeError):
                raise ETLInputError("worker", "Não foi possível concluir o processamento com segurança.") from None
            if not isinstance(envelope, dict) or type(envelope.get("ok")) is not bool:
                raise ETLInputError("worker", "Resposta inválida do processamento isolado.")
            if not envelope["ok"]:
                code = envelope.get("code", "worker")
                message = envelope.get("message")
                if (not isinstance(code, str) or len(code) > 64 or not isinstance(message, str)
                        or not 1 <= len(message) <= 1024):
                    raise ETLInputError("worker", "Não foi possível processar o arquivo com segurança.")
                raise ETLInputError(code, message)
            if process.returncode != 0 or not isinstance(envelope.get("result"), dict):
                raise ETLInputError("worker", "Não foi possível concluir o processamento com segurança.")
            return envelope["result"]
    except ETLInputError:
        raise
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ETLInputError("worker", "Processamento temporariamente indisponível. Tente novamente.") from None
    finally:
        try:
            if process is not None and process.poll() is None:
                _stop_owned_process(process)
        finally:
            _ADMISSION.release()


def run_validation(path, extension, limits=None):
    """Triagem da Baia de Segurança no processo isolado (security_gatekeeper.triar). Quando há
    algo a neutralizar, o arquivo é lido duas vezes (o original e a cópia conferida): o prazo é
    o dobro do configurado, dentro do teto do ETLLimits (120 s), como no Raio-X."""
    from dataclasses import replace
    policy = get_limits() if limits is None else limits
    if isinstance(policy, ETLLimits):
        policy = replace(policy, timeout_seconds=min(120, policy.timeout_seconds * 2))
    return _run_job("validate", [path], extension=extension, limits=policy)


def run_raio_x(paths, limits=None):
    """Raio-X de entrada no processo isolado. Lê vários meses de uma vez: o prazo é o dobro
    do configurado, dentro do teto do ETLLimits (120 s)."""
    from dataclasses import replace
    from etl_inputs import ETLInputError
    from raio_x import CHAVES_RESULTADO
    policy = get_limits() if limits is None else limits
    policy = replace(policy, timeout_seconds=min(120, policy.timeout_seconds * 2))
    result = _run_job("raio_x", paths, limits=policy)
    if set(result) != CHAVES_RESULTADO:
        raise ETLInputError("worker", "Resultado inválido do processamento isolado.")
    return result


def run_calculation(path_vendas, path_compras, limits=None):
    result = _run_job("calculate", [path_vendas, path_compras], limits=limits)
    return _resultado_calculo(result)


def run_calculation_detailed(path_vendas, path_compras, limits=None):
    """Mesmo cálculo financeiro de run_calculation e, à parte, o detalhamento por
    produto (ranking completo e movimentação). Devolve (ResultadoETL, detalhamento).

    O ResultadoETL passa pela MESMA validação de run_calculation. O detalhamento é
    conferido campo a campo (tipos, faixas, unicidade e invariantes); se vier
    inválido é descartado (None) e registrado, sem bloquear o processamento."""
    import logging
    from etl_inputs import ETLInputError
    result = _run_job("calculate_detailed", [path_vendas, path_compras], limits=limits)
    if set(result) != {"resultado", "detalhamento", "detalhamento_erro"} or not isinstance(result["resultado"], dict):
        raise ETLInputError("worker", "Resultado inválido do processamento isolado.")
    resultado = _resultado_calculo(result["resultado"])
    detalhamento = None
    if result["detalhamento"] is not None:
        try:
            detalhamento = validar_detalhamento(result["detalhamento"])
        except ValueError as erro:
            logging.getLogger(__name__).warning("Detalhamento por produto descartado (%s).", str(erro)[:32])
    elif result["detalhamento_erro"] is not None:
        logging.getLogger(__name__).warning("Detalhamento por produto indisponível (%s).",
                                            str(result["detalhamento_erro"])[:32])
    return resultado, detalhamento


_CAMPOS_RESUMO_INT = (
    "abc_total_produtos", "abc_produtos_a", "abc_produtos_b", "abc_produtos_c", "produtos_vendas",
    "produtos_registrados", "ranking_registrado", "movimentacao_total", "movimentacao_registrada",
)
_CAMPOS_RESUMO_VALOR = ("abc_faturamento_total", "abc_faturamento_a", "abc_faturamento_b", "abc_faturamento_c")
_CAMPOS_RESUMO_BOOL = ("compras_por_produto", "unidade_vendas_informada", "unidade_compras_informada",
                       "registro_limitado")
_CAMPOS_RESUMO_DATA = ("periodo_vendas_inicio", "periodo_vendas_fim", "periodo_compras_inicio", "periodo_compras_fim")
# Totais por situação da movimentação sobre todos os produtos comprados.
_CAMPOS_RESUMO_SITUACAO = ("movimentacao_comparaveis", "movimentacao_sem_venda", "movimentacao_unidade_divergente",
                           "movimentacao_unidade_ambigua", "movimentacao_quantidade_invalida")


def _inteiro(valor, minimo=0):
    if type(valor) is not int or valor < minimo:
        raise ValueError("inteiro")
    return valor


def _decimal(valor, opcional=True, minimo=None, maximo=None):
    import math
    from decimal import Decimal
    if valor is None and opcional:
        return None
    if type(valor) not in (int, float) or not math.isfinite(valor):
        raise ValueError("numero")
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise ValueError("faixa")
    return Decimal(repr(float(valor)))


def _texto(valor, maximo, opcional=True):
    if valor is None and opcional:
        return None
    if not isinstance(valor, str) or not 1 <= len(valor) <= maximo or "\x00" in valor:
        raise ValueError("texto")
    return valor


def validar_detalhamento(payload) -> dict:
    """Confere o detalhamento produzido pelo worker isolado e o devolve no formato
    dos modelos (nomes de atributos). Qualquer desvio levanta ValueError."""
    import re
    from etl_processor import (COLUNAS_DETALHAMENTO, LIMITE_PRODUTOS_DETALHADOS, SITUACOES_DETALHAMENTO,
                               VERSAO_DETALHAMENTO)
    if not isinstance(payload, dict) or set(payload) != {"resumo", "colunas", "produtos"}:
        raise ValueError("estrutura")
    if payload["colunas"] != list(COLUNAS_DETALHAMENTO):
        raise ValueError("colunas")
    bruto = payload["resumo"]
    esperado = set(_CAMPOS_RESUMO_INT) | set(_CAMPOS_RESUMO_VALOR) | set(_CAMPOS_RESUMO_BOOL) | set(
        _CAMPOS_RESUMO_DATA) | set(_CAMPOS_RESUMO_SITUACAO) | {"versao", "produtos_compras"}
    if not isinstance(bruto, dict) or set(bruto) != esperado or bruto["versao"] != VERSAO_DETALHAMENTO:
        raise ValueError("resumo")
    resumo = {"versao_metodologia": VERSAO_DETALHAMENTO}
    for campo in _CAMPOS_RESUMO_INT + _CAMPOS_RESUMO_SITUACAO:
        resumo[campo] = _inteiro(bruto[campo])
    for campo in _CAMPOS_RESUMO_VALOR:
        resumo[campo] = _decimal(bruto[campo], opcional=False, minimo=0)
    for campo in _CAMPOS_RESUMO_BOOL:
        if type(bruto[campo]) is not bool:
            raise ValueError("booleano")
        resumo[campo] = bruto[campo]
    for campo in _CAMPOS_RESUMO_DATA:
        valor = bruto[campo]
        if valor is not None:
            try:
                valor = date.fromisoformat(valor)
            except (TypeError, ValueError):
                raise ValueError("data") from None
        resumo[campo] = valor
    resumo["produtos_compras"] = None if bruto["produtos_compras"] is None else _inteiro(bruto["produtos_compras"])
    if (resumo["abc_produtos_a"] + resumo["abc_produtos_b"] + resumo["abc_produtos_c"] != resumo["abc_total_produtos"]
            or resumo["ranking_registrado"] > resumo["abc_total_produtos"]
            or resumo["movimentacao_registrada"] > resumo["movimentacao_total"]
            or sum(resumo[campo] for campo in _CAMPOS_RESUMO_SITUACAO) != resumo["movimentacao_total"]):
        raise ValueError("invariante")

    linhas = payload["produtos"]
    if (not isinstance(linhas, list) or len(linhas) > LIMITE_PRODUTOS_DETALHADOS
            or len(linhas) != resumo["produtos_registrados"]):
        raise ValueError("produtos")
    hexa = re.compile(r"^[0-9a-f]{16}$")
    chaves, posicoes, posicoes_mov, produtos = set(), set(), set(), []
    for linha in linhas:
        if not isinstance(linha, list) or len(linha) != len(COLUNAS_DETALHAMENTO):
            raise ValueError("linha")
        (chave, nome, posicao, classe, faturamento, qtd_vendida, perc_ind, perc_acum, qtd_comprada,
         unidade_venda, unidade_compra, situacao, diferenca, posicao_mov) = linha
        if not isinstance(chave, str) or not hexa.match(chave) or chave in chaves:
            raise ValueError("chave")
        chaves.add(chave)
        if posicao is not None:
            _inteiro(posicao, 1)
            if posicao in posicoes or classe not in ("A", "B", "C"):
                raise ValueError("posicao")
            posicoes.add(posicao)
        elif classe is not None or perc_ind is not None or perc_acum is not None:
            raise ValueError("classe")
        if situacao is not None and situacao not in SITUACOES_DETALHAMENTO:
            raise ValueError("situacao")
        if (situacao is None) != (posicao_mov is None) or (situacao is None) != (qtd_comprada is None):
            raise ValueError("movimentacao")
        if posicao_mov is not None:
            _inteiro(posicao_mov, 1)
            if posicao_mov in posicoes_mov:
                raise ValueError("posicao_movimentacao")
            posicoes_mov.add(posicao_mov)
        if diferenca is not None and situacao != "C":
            raise ValueError("diferenca")
        if posicao is None and posicao_mov is None:
            raise ValueError("irrelevante")
        produtos.append({
            "produto_chave": chave,
            "produto_nome": _texto(nome, 200, opcional=False),
            "posicao_ranking": posicao,
            "classe_abc": classe,
            "faturamento": _decimal(faturamento),
            "quantidade_vendida": _decimal(qtd_vendida),
            "percentual_individual": _decimal(perc_ind, minimo=0, maximo=100),
            "percentual_acumulado": _decimal(perc_acum, minimo=0, maximo=100),
            "quantidade_comprada": _decimal(qtd_comprada),
            "unidade_venda": _texto(unidade_venda, 12),
            "unidade_compra": _texto(unidade_compra, 12),
            "situacao_movimentacao": SITUACOES_DETALHAMENTO.get(situacao) if situacao else None,
            "diferenca_quantidade": _decimal(diferenca),
            "posicao_movimentacao": posicao_mov,
        })
    return {"resumo": resumo, "produtos": produtos}


def _resultado_calculo(result):
    from etl_processor import ResultadoETL
    from etl_inputs import ETLInputError
    if (set(result) != set(ResultadoETL._fields) or result.get("sucesso") is not True
            or not isinstance(result.get("kpis"), dict) or not isinstance(result.get("telemetria"), dict)
            or not isinstance(result.get("alertas"), list)):
        raise ETLInputError("worker", "Resultado inválido do processamento isolado.")
    for name in ("periodo_base_inicio", "periodo_base_fim"):
        value = result["kpis"].get(name)
        if value is not None:
            try:
                result["kpis"][name] = date.fromisoformat(value)
            except (ValueError, TypeError):
                raise ETLInputError("worker", "Período inválido no resultado do processamento.") from None
    return ResultadoETL(**result)
