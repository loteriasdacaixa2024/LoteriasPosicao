"""Leitor mínimo de .xlsx (primeira planilha) sem openpyxl."""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in (cell_ref or "") if ch.isalpha())
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return max(0, n - 1)


def _shared_strings(zf: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: List[str] = []
    for si in root.findall("m:si", NS):
        texts = list(si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
        out.append("".join(t.text or "" for t in texts))
    return out


def _cell_value(cell: ET.Element, strings: List[str]) -> Any:
    t = cell.get("t")
    v = cell.find("m:v", NS)
    raw = v.text if v is not None else None
    if raw is None:
        is_el = cell.find("m:is", NS)
        if is_el is not None:
            texts = list(is_el.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
            return "".join(x.text or "" for x in texts)
        return None
    if t == "s" and str(raw).isdigit():
        idx = int(raw)
        return strings[idx] if 0 <= idx < len(strings) else raw
    if t == "b":
        return str(raw) in ("1", "true", "TRUE")
    return raw


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    names = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
    names.sort()
    if not names:
        raise ValueError("Planilha não encontrada no Excel.")
    return names[0]


def ler_xlsx_dicts(path: Path, *, max_col: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retorna linhas como dict {header: valor}. Cabeçalho = primeira linha."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with zipfile.ZipFile(path) as zf:
        strings = _shared_strings(zf)
        root = ET.fromstring(zf.read(_first_sheet_path(zf)))
        rows_el = root.findall("m:sheetData/m:row", NS)
        if not rows_el:
            return []
        headers: List[str] = []
        out: List[Dict[str, Any]] = []
        for i, row in enumerate(rows_el):
            cells: Dict[int, Any] = {}
            for c in row.findall("m:c", NS):
                ref = c.get("r") or ""
                idx = _col_index(ref) if ref else len(cells)
                cells[idx] = _cell_value(c, strings)
            if not cells:
                continue
            width = max(cells) + 1
            if max_col is not None:
                width = min(width, max_col)
            vals = [cells.get(j) for j in range(width)]
            if i == 0:
                headers = [str(v or "").strip() for v in vals]
                continue
            if not any(v not in (None, "") for v in vals):
                continue
            rec: Dict[str, Any] = {}
            for j, h in enumerate(headers):
                if not h:
                    continue
                rec[h] = vals[j] if j < len(vals) else None
            out.append(rec)
        return out
