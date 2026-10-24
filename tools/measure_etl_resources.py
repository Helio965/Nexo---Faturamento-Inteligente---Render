"""SEC-005: medição reproduzível com relatórios exclusivamente sintéticos.

Executar em ambiente de teste. Cada leitura/cálculo recebe um processo novo;
RSS inclui Python e bibliotecas, não é uma medida exclusiva de DataFrames.
Nenhum banco, aplicação Flask, .env ou serviço externo é inicializado.
"""

import argparse
import csv
from datetime import date, datetime
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def _plain(value):
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _probe(options):
    sys.path.insert(0, str(ROOT))
    before_import = time.perf_counter()
    if options.source:
        spec = importlib.util.spec_from_file_location("sec005_original_measurement", options.source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        import etl_processor as module
    import_seconds = time.perf_counter() - before_import
    before = time.perf_counter()
    if options.operation == "read":
        frames = [module._ler_bruto(options.sales), module._ler_bruto(options.purchases)]
        result = {"frames": [{"rows": len(frame), "columns": len(frame.columns),
                              "cells": int(frame.size),
                              "filled": int(frame.notna().to_numpy().sum())}
                             for frame in frames]}
    else:
        calculate = (getattr(module, "_calcular_kpis_local", module.calcular_kpis_em_memoria)
                     if options.operation == "calculate" else module.calcular_kpis_em_memoria)
        result = _plain(calculate(options.sales, options.purchases)._asdict())
    processing_seconds = time.perf_counter() - before
    status = Path("/proc/self/status").read_text().splitlines() if sys.platform == "linux" else []
    memory = {line.split(":", 1)[0]: int(line.split()[1]) for line in status
              if line.startswith(("VmSize:", "VmPeak:", "VmRSS:", "VmHWM:"))}
    print(json.dumps({"operation": options.operation, "source": "baseline" if options.source else "candidate",
                      "import_seconds": import_seconds, "processing_seconds": processing_seconds,
                      "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "child_max_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                      "memory_proc_status_kib": memory, "result": result}, ensure_ascii=False, allow_nan=False))


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream, delimiter=";", lineterminator="\n").writerows(rows)


def _fixtures(folder, csv_rows, xlsx_rows):
    from openpyxl import Workbook

    sales_header = ["nome_produto", "quantidade", "faturamento", "preco_venda", "estoque", "categoria"]
    purchase_header = ["nome_produto", "qtde_comprada", "total_custo", "fornecedor", "data_nf", "codigo"]

    def sales(count):
        yield sales_header
        for index in range(count):
            yield [f"Produto sintético {index % 200:03d}", str(index % 7 + 1),
                   f"{(index % 43 + 1) * 3},50", "9999,00", "15", "Sintética"]

    def purchases(count):
        yield purchase_header
        for index in range(count):
            yield [f"Produto sintético {index % 200:03d}", str(index % 11 + 1),
                   f"{(index % 31 + 1) * 5},25", "Fornecedor sintético", "10/01/2026", str(index)]

    pairs = []
    sv, pc = folder / "medium_sales.csv", folder / "medium_purchases.csv"
    _write_csv(sv, sales(csv_rows))
    _write_csv(pc, purchases(csv_rows))
    pairs.append(("csv_medium", sv, pc, 1))
    for kind, rows in (("sales", sales), ("purchases", purchases)):
        book = Workbook(write_only=True)
        for sheet_index in range(4):
            sheet = book.create_sheet(f"Aba sintética {sheet_index + 1}")
            # A última aba tem um registro adicional, permitindo conferir a
            # seleção sem manter quatro DataFrames na implementação candidata.
            for row in rows(xlsx_rows + (sheet_index == 3)):
                sheet.append(row)
        book.save(folder / f"medium_{kind}.xlsx")
        book.close()
    pairs.append(("xlsx_four_sheets", folder / "medium_sales.xlsx", folder / "medium_purchases.xlsx", 4))
    return pairs


def _metadata(path, sheets):
    result = {"bytes": path.stat().st_size, "sheets": sheets, "uncompressed_bytes": None}
    if path.suffix == ".xlsx":
        with zipfile.ZipFile(path) as archive:
            result["uncompressed_bytes"] = sum(member.file_size for member in archive.infolist())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--csv-rows", type=int, default=10000)
    parser.add_argument("--xlsx-rows", type=int, default=3000)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--source", help=argparse.SUPPRESS)
    parser.add_argument("--sales", help=argparse.SUPPRESS)
    parser.add_argument("--purchases", help=argparse.SUPPRESS)
    parser.add_argument("--operation", choices=("read", "calculate", "public_calculate"), help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.probe:
        _probe(options)
        return
    if not options.baseline or not options.output:
        parser.error("--baseline e --output são obrigatórios")
    if not 1 <= options.csv_rows <= 20000 or not 1 <= options.xlsx_rows <= 5000:
        parser.error("medição aceita somente amostras pequenas e controladas")
    environment = {key: value for key, value in os.environ.items()
                   if key in {"PATH", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL", "TZ"}}
    environment.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       NUMEXPR_NUM_THREADS="1")
    report = {"method": "processo novo por leitura/cálculo; RSS inclui imports; Linux KiB",
              "synthetic_only": True, "csv_data_rows": options.csv_rows,
              "xlsx_data_rows_per_sheet": options.xlsx_rows, "cases": []}
    with tempfile.TemporaryDirectory(prefix="nexo-sec005-measure-") as directory:
        for name, sales, purchases, sheets in _fixtures(Path(directory), options.csv_rows, options.xlsx_rows):
            case = {"name": name, "sales": _metadata(sales, sheets),
                    "purchases": _metadata(purchases, sheets), "runs": []}
            sources = [("baseline", str(options.baseline))]
            if not options.baseline_only:
                sources.append(("candidate", None))
            for label, source in sources:
                operations = ["read", "calculate"]
                if label == "candidate":
                    operations.append("public_calculate")
                for operation in operations:
                    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--probe",
                               "--operation", operation, "--sales", str(sales), "--purchases", str(purchases)]
                    if source:
                        command += ["--source", source]
                    completed = subprocess.run(command, env=environment, capture_output=True, text=True,
                                               check=True, timeout=120, cwd=directory)
                    case["runs"].append(json.loads(completed.stdout))
            if not options.baseline_only:
                original = next(run["result"] for run in case["runs"]
                                if run["source"] == "baseline" and run["operation"] == "calculate")
                candidate = next(run["result"] for run in case["runs"]
                                 if run["source"] == "candidate" and run["operation"] == "calculate")
                case["financial_exact_equal"] = original == candidate
                assert original == candidate, "A medição encontrou divergência no resultado sintético."
            report["cases"].append(case)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(options.output), "cases": len(report["cases"]),
                      "baseline_only": options.baseline_only}))


if __name__ == "__main__":
    main()
