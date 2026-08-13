"""Normalização de rateio (R$) e Cidade/UF do Excel CAIXA."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _norm_header(h: str) -> str:
    t = (h or "").strip().lower()
    t = t.replace("á", "a").replace("ã", "a").replace("â", "a")
    t = t.replace("é", "e").replace("ê", "e")
    t = t.replace("í", "i")
    t = t.replace("ó", "o").replace("ô", "o")
    t = t.replace("ú", "u")
    t = t.replace("ç", "c")
    t = re.sub(r"\s+", " ", t)
    return t


def pick(row: Dict[str, Any], *aliases: str) -> Any:
    wanted = {_norm_header(a) for a in aliases}
    for k, v in row.items():
        if _norm_header(k) in wanted:
            return v
    return None


def parse_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    s = str(v).strip().replace(".", "").replace(" ", "")
    if not s or s.lower() in ("nao", "não", "-", "none"):
        return 0 if s.lower() in ("nao", "não") else None
    try:
        return int(float(s.replace(",", ".")))
    except (TypeError, ValueError):
        return None


def parse_reais(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip().upper().replace("R$", "").replace(" ", "")
    if not s or s in ("-", "NAO", "NÃO", "NONE"):
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def fmt_reais(v: Optional[float]) -> str:
    if v is None:
        return "—"
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def title_cidade(nome: str) -> str:
    raw = re.sub(r"\s+", " ", (nome or "").strip())
    if not raw:
        return ""
    parts = []
    for w in raw.split(" "):
        low = w.lower()
        if low in ("de", "da", "do", "das", "dos", "e"):
            parts.append(low)
        else:
            parts.append(w[:1].upper() + w[1:].lower() if w else w)
    return " ".join(parts)


def split_localidades(raw: Any) -> List[Dict[str, str]]:
    """
    'CAMPINAS/SP' → [{cidade, uf}]
    'CANAL ELETRONICO; SAO PAULO/SP' → duas localidades
    """
    if raw is None:
        return []
    text = str(raw).strip()
    if not text or text.lower() in ("none", "nan", "-"):
        return []
    chunks = [p.strip() for p in re.split(r"[;|]", text) if p.strip()]
    out: List[Dict[str, str]] = []
    seen = set()
    for chunk in chunks:
        cidade, uf = chunk, ""
        if "/" in chunk:
            cidade, uf = chunk.rsplit("/", 1)
            cidade, uf = cidade.strip(), uf.strip().upper()
            uf = re.sub(r"[^A-Z]", "", uf)[:2]
        cidade_n = title_cidade(cidade)
        key = (cidade_n.lower(), uf)
        if key in seen:
            continue
        seen.add(key)
        out.append({"cidade": cidade_n, "uf": uf})
    return out
