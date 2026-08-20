# -*- coding: utf-8 -*-
"""
Soma vs média do padrão — regra única para interface e exportação.

Regra (alinhada à lógica tubular/média já usada no sistema):
- Média preferencial: média das somas dos sorteios históricos com o mesmo padrão inicial.
- Fallback: média das somas das apostas teóricas do padrão (quando não há amostra histórica).
- Tolerância próxima (tol): max(2, round(desvio_padrão_populacional || amplitude/4 || 4)).
- Dentro da média: |soma − média| ≤ max(1, round(tol / 2)).
- Próxima da média: |soma − média| ≤ tol.
- Fora da faixa: demais casos.
"""
from __future__ import annotations

import io
import re
import statistics
import zipfile
from typing import Any, Dict, Iterable, List, Optional, Sequence
from xml.sax.saxutils import escape


# Cores suaves por modalidade (RGB hex) — identificação visual no Excel
MODALIDADE_FILL = {
    "diadesorte": "FFF8E1",
    "lotofacil": "F3E5F5",
    "lotomania": "FFF3E0",
    "megasena": "E3F2FD",
    "quina": "FFFDE7",
    "duplasena": "FFEBEE",
    "maismilionaria": "E8EAF6",
    "timemania": "E8F5E9",
    "supersete": "E8F5E9",
}

STATUS_FILL = {
    "dentro": "E8F5E9",   # verde muito claro
    "proxima": "FFF8E1",  # amarelo muito claro
    "fora": "FFFFFF",
}

STATUS_LABEL = {
    "dentro": "Dentro da média",
    "proxima": "Próxima da média",
    "fora": "Fora da faixa",
}


def _norm_padrao(padrao: str) -> str:
    digs = [x for x in str(padrao or "").replace(",", " ").split() if x.strip().isdigit()]
    return " ".join(digs)


def calcular_faixa_soma(
    somas: Sequence[float],
    *,
    fonte: str = "historico",
) -> Optional[Dict[str, Any]]:
    """Calcula média e tolerâncias a partir de uma lista de somas."""
    vals = [float(s) for s in somas if s is not None]
    if not vals:
        return None
    avg = statistics.mean(vals)
    media = int(round(avg))
    std = float(statistics.pstdev(vals)) if len(vals) > 1 else 0.0
    span = float(max(vals) - min(vals)) if len(vals) > 1 else 0.0
    tol_proxima = int(max(2, round(std or (span / 4) or 4)))
    tol_dentro = int(max(1, round(tol_proxima / 2)))
    return {
        "media": media,
        "media_exata": round(avg, 2),
        "desvio": round(std, 2),
        "min": int(min(vals)),
        "max": int(max(vals)),
        "tol_dentro": tol_dentro,
        "tol_proxima": tol_proxima,
        "amostra": len(vals),
        "fonte": fonte,
        "regra": (
            "media +/- desvio (tubular/media): "
            "dentro <= tol/2; proxima <= tol; senao fora"
        ),
    }


def classificar_soma(soma: Any, faixa: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Classifica uma soma em relação à faixa do padrão."""
    try:
        s = int(soma)
    except (TypeError, ValueError):
        s = 0
    if not faixa or faixa.get("media") is None:
        return {
            "soma": s,
            "media": None,
            "distancia": None,
            "status_media": "fora",
            "status_media_label": "Sem média",
            "tol_dentro": None,
            "tol_proxima": None,
        }
    media = int(faixa["media"])
    dist = s - media
    ad = abs(dist)
    tol_d = int(faixa.get("tol_dentro") or 1)
    tol_p = int(faixa.get("tol_proxima") or 2)
    if ad <= tol_d:
        st = "dentro"
    elif ad <= tol_p:
        st = "proxima"
    else:
        st = "fora"
    return {
        "soma": s,
        "media": media,
        "distancia": dist,
        "status_media": st,
        "status_media_label": STATUS_LABEL.get(st, st),
        "tol_dentro": tol_d,
        "tol_proxima": tol_p,
    }


def somas_historicas_do_padrao(
    linhas: Iterable[Dict[str, Any]],
    padrao: str,
) -> List[int]:
    alvo = _norm_padrao(padrao)
    out: List[int] = []
    for l in linhas or []:
        p = _norm_padrao(str(l.get("padrao_inicial") or ""))
        if not p and l.get("dezenas"):
            try:
                dez = sorted(int(x) for x in (l.get("dezenas") or []))
                p = " ".join(str(int(d) // 10) for d in dez)
            except Exception:
                p = ""
        if p != alvo:
            continue
        try:
            out.append(int(l.get("soma") or 0))
        except (TypeError, ValueError):
            continue
    return out


def enriquecer_jogos_com_media(
    jogos: List[Dict[str, Any]],
    faixa: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for j in jogos or []:
        row = dict(j)
        cls = classificar_soma(row.get("soma"), faixa)
        row.update(cls)
        out.append(row)
    return out


def resumo_status(jogos: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    c = {"dentro": 0, "proxima": 0, "fora": 0}
    for j in jogos or []:
        st = str(j.get("status_media") or "fora")
        if st not in c:
            st = "fora"
        c[st] += 1
    return c


def modalidade_fill(modality_key: str) -> str:
    return MODALIDADE_FILL.get(str(modality_key or "").lower(), "F5F5F5")


def _col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def build_xlsx_apostas(
    *,
    modality_key: str,
    modality_nome: str,
    padrao: str,
    descricao: str,
    faixa: Optional[Dict[str, Any]],
    jogos: Sequence[Dict[str, Any]],
) -> bytes:
    """
    Gera .xlsx mínimo (Office Open XML) com:
    - cabeçalhos em MAIÚSCULO
    - largura de coluna estimada pelo conteúdo
    - cor suave da modalidade no cabeçalho
    - destaque sutil da linha conforme status_media
    """
    headers = [
        "MODALIDADE",
        "PADRÃO",
        "DESCRIÇÃO",
        "APOSTA",
        "SOMA",
        "MÉDIA",
        "DISTÂNCIA DA MÉDIA",
        "STATUS",
        "CONCURSO",
        "ID",
    ]
    rows_data: List[List[Any]] = []
    for j in jogos or []:
        dist = j.get("distancia")
        dist_s = "" if dist is None else (f"+{dist}" if int(dist) > 0 else str(dist))
        rows_data.append([
            modality_nome,
            padrao,
            descricao or "",
            j.get("dezenas_fmt") or "",
            j.get("soma"),
            j.get("media") if j.get("media") is not None else "",
            dist_s,
            j.get("status_media_label") or "",
            j.get("concurso") or "",
            j.get("id") or "",
        ])

    widths = []
    for i, h in enumerate(headers):
        mx = len(h)
        for r in rows_data:
            mx = max(mx, len(str(r[i] if i < len(r) else "")))
        widths.append(min(42, max(8, mx + 2)))

    header_fill = modalidade_fill(modality_key)
    style_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FF1A1A1A"/><name val="Calibri"/></font>
  </fonts>
  <fills count="5">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF{header_fill}"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF{STATUS_FILL['dentro']}"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF{STATUS_FILL['proxima']}"/></patternFill></fill>
  </fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="0" fillId="3" borderId="0" applyFill="1"/>
    <xf numFmtId="0" fontId="0" fillId="4" borderId="0" applyFill="1"/>
  </cellXfs>
</styleSheet>"""

    def cell_xml(ref: str, value: Any, style: int = 0) -> str:
        if value is None or value == "":
            return f'<c r="{ref}" s="{style}"/>'
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
        txt = escape(str(value))
        return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{txt}</t></is></c>'

    sheet_rows = []
    cells = []
    for i, h in enumerate(headers, start=1):
        cells.append(cell_xml(f"{_col_letter(i)}1", h, 1))
    sheet_rows.append(f'<row r="1">{"".join(cells)}</row>')

    for ridx, row in enumerate(rows_data, start=2):
        st = str((jogos[ridx - 2] or {}).get("status_media") or "fora")
        style = 2 if st == "dentro" else (3 if st == "proxima" else 0)
        cells = []
        for i, val in enumerate(row, start=1):
            s = style if style and i in (5, 6, 7, 8) else (style if style else 0)
            cells.append(cell_xml(f"{_col_letter(i)}{ridx}", val, s))
        sheet_rows.append(f'<row r="{ridx}">{"".join(cells)}</row>')

    cols_xml = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(widths, start=1)
    )
    last_col = _col_letter(len(headers))
    last_row = 1 + len(rows_data)
    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <cols>{cols_xml}</cols>
  <sheetData>
    {''.join(sheet_rows)}
  </sheetData>
  <autoFilter ref="A1:{last_col}{last_row}"/>
</worksheet>"""

    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Apostas" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", style_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def safe_filename_padrao(padrao: str) -> str:
    s = re.sub(r"[^\d]+", "", str(padrao or ""))
    return s or "padrao"
