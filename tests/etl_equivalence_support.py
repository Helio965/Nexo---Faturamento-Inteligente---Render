"""SEC-005: relatórios inteiramente sintéticos para equivalência comercial.

Nenhuma planilha de cliente é copiada. Os cenários reproduzem as características
documentadas dos layouts C1–C4 e as regras dos leitores anteriores.
"""

import csv
from datetime import date, datetime
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from openpyxl import Workbook
import pandas as pd


SALES = [
    ["nome_produto", "quantidade", "faturamento"],
    ["Arroz sintético", "10", "100,00"],
    ["Feijão sintético", "5", "150,00"],
    ["Óleo sintético", "2", "50,00"],
]
PURCHASES = [
    ["nome_produto", "qtde_comprada", "total_custo"],
    ["Arroz sintético", "20", "200,00"],
    ["Feijão sintético", "10", "250,00"],
    ["Óleo sintético", "8", "180,00"],
]


def write_csv(path, rows, *, delimiter=";", encoding="utf-8-sig"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as output:
        csv.writer(output, delimiter=delimiter, lineterminator="\n").writerows(rows)
    return path


def write_xlsx(path, sheets, *, cached_values=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets:
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    book.save(path)
    book.close()
    if cached_values:
        # openpyxl não calcula fórmulas. Este fixture grava o cache numérico que
        # um exportador legítimo deixaria no XLSX; nenhum Excel é executado.
        with zipfile.ZipFile(path) as archive:
            members = {item.filename: (item, archive.read(item)) for item in archive.infolist()}
        for member, cells in cached_values.items():
            info, raw = members[member]
            root = ET.fromstring(raw)
            namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for reference, value in cells.items():
                cell = root.find(f".//x:c[@r='{reference}']", namespace)
                if cell is None:
                    raise AssertionError("Célula sintética de fórmula ausente.")
                number = cell.find("x:v", namespace)
                if number is None:
                    number = ET.SubElement(cell, "{" + namespace["x"] + "}v")
                number.text = str(value)
            members[member] = (info, ET.tostring(root, encoding="utf-8"))
        with zipfile.ZipFile(path, "w") as archive:
            for info, raw in members.values():
                archive.writestr(info, raw)
    return path


def fixture_pairs(directory):
    """Retorna pares vendas/compras com nomes estáveis e conteúdo controlado."""
    directory = Path(directory)
    pairs = {}

    def pair(name, sales, purchases, *, delimiter=";", encoding="utf-8-sig", xlsx=False,
             sales_sheets=None, purchase_sheets=None, sales_cached=None):
        suffix = ".xlsx" if xlsx else ".csv"
        folder = directory / name
        sv, pc = folder / (name + "_vendas" + suffix), folder / (name + "_compras" + suffix)
        if xlsx:
            write_xlsx(sv, sales_sheets or [("Dados", sales)], cached_values=sales_cached)
            write_xlsx(pc, purchase_sheets or [("Dados", purchases)])
        else:
            write_csv(sv, sales, delimiter=delimiter, encoding=encoding)
            write_csv(pc, purchases, delimiter=delimiter, encoding=encoding)
        pairs[name] = (sv, pc)

    pair("c1_hemorragia_nf", [
        ["Período de : 01/01/26 a 31/01/26"],
        ["id_produto", "descricao_produto", "quantidade", "faturamento", "estoque", "total_custo"],
        ["S1", "Arroz sintético", "5", "R$ 100,00", "-1", "120,00"],
        ["S2", "Feijão sintético", "2", "50,00", "3", "40,00"],
        ["S3", "Óleo sintético", "1", "10,00", "1", "9,00"],
        ["", "TOTAL GERAL", "999", "999.999,99"],
    ], [
        ["fornecedor", "data_nf", "total_compra"],
        ["Fornecedor sintético A", "05/01/26", "R$ 1.000,00"],
        ["Fornecedor sintético B", "15/01/26", "200,00"],
    ])
    pair("c2_refem_unitario", SALES, [
        ["nome_produto", "qtde_comprada", "custo_unitario"],
        ["Arroz sintético", 50, "10,00"],
        ["Feijão sintético", 30, "20,00"],
        ["Óleo sintético", 20, "8,00"],
    ], xlsx=True, sales_sheets=[("Capa", [["Relatório sintético C2"]]), ("Vendas", SALES)])
    pair("c3_ruptura_verboso", [
        ["descricao", "qtde_vendida", "Valor_Arrecadado_Total_Vendas"],
        ["Arroz sintético", 100, "1.000,00"],
        ["Feijão sintético", 20, "400,00"],
        ["Óleo sintético", 3, "90,00"],
    ], [
        ["descricao", "fornecedor", "qtde_comprada", "total_custo"],
        ["Arroz sintético", "Fornecedor sintético", 10, "100,00"],
        ["Feijão sintético", "Fornecedor sintético", 2, "40,00"],
        ["Óleo sintético", "Fornecedor sintético", 0, "0,00"],
    ], xlsx=True)
    c4_sales = [["nome_produto", "quantidade", "faturamento", "categoria", "classe"]]
    c4_purchases = [["nome_produto", "qtde_comprada", "total_custo"]]
    for index, value in enumerate([800, 100, 50, 20, 15, 10, 4, 1], 1):
        c4_sales.append([f"Produto sintético {index}", 11 - index, str(value), "Sintética", "Ignorar"])
        c4_purchases.append([f"Produto sintético {index}", 15 - index, str(value)])
    pair("c4_equilibrio_abc", c4_sales, c4_purchases, xlsx=True)

    # Encoding e separador preservam a mesma política e seus desempates.
    pair("csv_semicolon_utf8sig", SALES, PURCHASES)
    pair("csv_comma_latin1", SALES, PURCHASES, delimiter=",", encoding="latin1")
    cp_sales = [*SALES[:1], ["Café “sintético”", "2", "20,00"], *SALES[2:]]
    pair("csv_tab_cp1252", cp_sales, PURCHASES, delimiter="\t", encoding="cp1252")
    pair("csv_pipe_utf8", SALES, PURCHASES, delimiter="|", encoding="utf-8")
    latin_sales = [*SALES[:1], ["Produto\x81sintético", "2", "20,00"], *SALES[2:]]
    pair("csv_latin1_fallback", latin_sales, PURCHASES, delimiter=",", encoding="latin1")
    quoted = [SALES[0], ['Produto "sintético"; especial\nlinha adicional', "2", "20,00"], *SALES[2:]]
    pair("csv_quoted_multiline", quoted, PURCHASES)
    nul = [SALES[0], ["Produto\x00sintético", "2", "20,00"], *SALES[2:]]
    pair("csv_nul_removal", nul, PURCHASES)
    late = [[f"Linha decorativa sintética {i}"] for i in range(70)] + SALES
    pair("csv_late_delimiter_header", late, PURCHASES, delimiter="|")

    compound = [
        ["nome", "quantidade", "valor"], ["produto", "vendida", "total vendas"],
        ["Arroz sintético", "10", "100,00"], ["Feijão sintético", "5", "150,00"],
    ]
    pair("header_compound", compound, PURCHASES, xlsx=True)
    shifted = [[None] * 7, [None, None, "Período de : 01/02/26 a 28/02/26"],
        [None, None, "extra", "faturamento", "descricao_produto", "quantidade", "id_produto"],
        [None, None, "não comercial", "100,00", "Arroz sintético", "10", "S1"],
        [None, None, "não comercial", "150,00", "Feijão sintético", "5", "S2"],
        [None, None, "", "999.999,99", "TOTAL GERAL", "999", ""],
    ]
    pair("header_shifted_footer", shifted, PURCHASES, xlsx=True)
    explicit = [["id_produto", "nome_produto", "preco_venda", "faturamento", "quantidade", "lucro", "total_custo", "estoque"],
        ["S1", "Café sintético", "999,00", "100,00", "2", "99,00", "120,00", "-1"],
        ["S2", "Cafe sintetico", "999,00", "200,00", "3", "99,00", "150,00", "2"],
        ["S3", "Chá sintético", "999,00", "50,00", "1", "99,00", "10,00", "4"],
        ["", "DESCONTOS", "999", "9999", "999", "999", "999", "999"],
    ]
    pair("explicit_total_normalization_alerts", explicit, PURCHASES)
    derived = [["produto", "quantidade", "preco_unitario"],
        ["Produto sintético A", "2", "1,234.56"],
        ["Produto sintético B", "3", "R$ 10,50"],
        ["Produto sintético C", "1", "(2,50)"],
    ]
    pair("sales_derived_mixed_money", derived, PURCHASES)
    nf_priority = [["fornecedor", "valor_nf", "total_produtos"],
        ["Fornecedor sintético A", "9999,00", "120,00"],
        ["Fornecedor sintético B", "9999,00", "250,00"],
    ]
    pair("purchase_products_total_priority", SALES, nf_priority)
    first = [SALES[0], ["Primeiro sintético", "2", "20"], ["Outro sintético", "1", "30"]]
    second = [SALES[0], ["Segundo sintético", "8", "800"], ["Diferente sintético", "1", "90"]]
    pair("xlsx_sheet_tie", first, PURCHASES, xlsx=True,
         sales_sheets=[("Capa", [["Sintético"]]), ("Primeiro", first), ("Segundo", second)])
    formula = [["produto", "quantidade", "faturamento", "nota", "sem cache"],
        ["Arroz sintético", 10, "=10*10", "NA", "=1+1"],
        ["Feijão sintético", 5, "=5*30", "NULL", None],
        ["Óleo sintético", 2, "50,00", "n/a", None],
    ]
    pair("xlsx_formula_cached_na", formula, PURCHASES, xlsx=True,
         sales_cached={"xl/worksheets/sheet1.xml": {"C2": 100, "C3": 150}})
    reversed_period = [["Período de : 31/03/26 a 01/03/26"], *SALES]
    pair("reversed_period_dates", reversed_period, PURCHASES)
    pair("purchase_period_fallback", SALES, [["Período de : 01/04/26 a 30/04/26"], *PURCHASES])
    pair("one_product_rankings", [SALES[0], ["Único sintético", 3, "60,00"]], PURCHASES)
    return pairs


def reader_fixtures(directory):
    """Casos brutos que expõem diferenças relevantes entre pandas/openpyxl."""
    directory = Path(directory)
    files = {}
    rows = [["texto", "numero", "booleano", "data", "erro", "formula"],
        ["NA", 0, True, datetime(2026, 1, 2, 3, 4, 5), "#N/A", "=1+2"],
        ["NULL", 1234.50, False, date(2026, 2, 3), "#DIV/0!", None],
        ["n/a", -1, None, None, None, None], ["NaN", 2, None, None, None, None],
        ["None", 3, None, None, None, None], [" ", 4, None, None, None, None],
    ]
    files["xlsx_cell_conversion"] = write_xlsx(directory / "xlsx_cell_conversion.xlsx", [("Tipos", rows)])
    all_nan = [["NA", "NULL", "n/a"], [None, None, None]]
    non_nan = [["dados sintéticos", "numero"], ["produto", "1"]]
    files["xlsx_na_count_selection"] = write_xlsx(directory / "xlsx_na_count_selection.xlsx", [("NA", all_nan), ("Dados", non_nan)])
    csv_rows = [["a", "b", "c"], ["NA", "", "nan"], ["NULL", "0"], [], [" fim ", "1", ""]]
    files["csv_empty_string_padding"] = write_csv(directory / "csv_empty_string_padding.csv", csv_rows)
    return files


def plain(value):
    """Serialização sem arredondar números nem apagar campos da comparação."""
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def raw_snapshot(frame):
    rows = []
    for row in frame.itertuples(index=False, name=None):
        rows.append([None if pd.isna(value) else plain(value) for value in row])
    return {"shape": list(frame.shape), "values": rows}
