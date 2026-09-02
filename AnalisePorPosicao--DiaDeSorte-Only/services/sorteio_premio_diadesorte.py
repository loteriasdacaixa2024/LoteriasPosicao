# -*- coding: utf-8 -*-
"""Extração de premiação (7 e 6 acertos) e localidades — API Caixa Dia de Sorte."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def extrair_ganhadores_7(dados: Dict[str, Any]) -> Optional[int]:
    """
    Retorna quantidade de ganhadores na faixa principal (7 acertos).
    None se a API não trouxer listaRateioPremio utilizável.
    """
    faixa = extrair_faixa(dados, 7)
    if faixa is None:
        return None
    return int(faixa["ganhadores"])


def extrair_faixa(dados: Dict[str, Any], acertos: int) -> Optional[Dict[str, Any]]:
    """Ganhadores + rateio de uma faixa (7 ou 6 acertos). None se a lista não existir."""
    if not dados:
        return None
    lista = dados.get("listaRateioPremio")
    if not isinstance(lista, list):
        return None
    alvo = f"{int(acertos)} acertos"
    faixa_n = 1 if int(acertos) == 7 else (2 if int(acertos) == 6 else None)
    for item in lista:
        if not isinstance(item, dict):
            continue
        desc = (item.get("descricaoFaixa") or "").strip().lower()
        faixa = item.get("faixa")
        if desc == alvo or (faixa_n is not None and faixa == faixa_n):
            try:
                ganh = max(0, int(item.get("numeroDeGanhadores", 0) or 0))
            except (TypeError, ValueError):
                ganh = 0
            try:
                rateio = float(item.get("valorPremio") or 0)
            except (TypeError, ValueError):
                rateio = 0.0
            return {"ganhadores": ganh, "rateio": rateio}
    return {"ganhadores": 0, "rateio": 0.0}


def extrair_localidades_api(dados: Dict[str, Any]) -> List[Dict[str, str]]:
    """Cidade e UF já separados em listaMunicipioUFGanhadores."""
    if not dados:
        return []
    lista = dados.get("listaMunicipioUFGanhadores")
    if not isinstance(lista, list):
        return []
    out: List[Dict[str, str]] = []
    seen = set()
    for item in lista:
        if not isinstance(item, dict):
            continue
        cidade = str(item.get("municipio") or "").strip()
        uf = str(item.get("uf") or "").strip().upper()
        if uf in ("--", "-", "NA", "N/A"):
            uf = ""
        uf = "".join(ch for ch in uf if ch.isalpha())[:2]
        cidade_n = _title_cidade(cidade)
        key = (cidade_n.lower(), uf)
        if not cidade_n and not uf:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append({"cidade": cidade_n, "uf": uf})
    return out


def _title_cidade(nome: str) -> str:
    raw = " ".join((nome or "").split())
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


def classificar_base_concurso(ganhadores_7: Optional[int]) -> Optional[str]:
    """'vencedores' | 'acumulados' | None (desconhecido)."""
    if ganhadores_7 is None:
        return None
    return "vencedores" if ganhadores_7 >= 1 else "acumulados"
