# -*- coding: utf-8 -*-
"""Consulta status oficial na API Caixa (último sorteado, próximo, especial)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import certifi
import requests

from configuracoes.config import CONCURSOS_ESPECIAIS, MODALITIES

BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}


def _get_json(url: str, timeout: int = 25) -> Optional[dict]:
    kwargs = {"headers": HEADERS, "timeout": timeout}
    try:
        r = requests.get(url, verify=certifi.where(), **kwargs)
    except requests.exceptions.SSLError:
        r = requests.get(url, verify=False, **kwargs)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def _api_url(key: str, concurso: Optional[int] = None) -> str:
    meta = MODALITIES[key]
    slug = meta.get("api_slug") or key
    base = meta.get("api_url") or f"{BASE}/{slug}/"
    if concurso:
        return f"{base.rstrip('/')}/{concurso}"
    return base


def buscar_ultimo_oficial(key: str, timeout: int = 25) -> int:
    st = buscar_status_caixa(key, timeout=timeout)
    return int(st.get("ultimo_sorteado") or 0)


def buscar_status_caixa(key: str, timeout: int = 25) -> Dict[str, Any]:
    """
    ultimo_sorteado = último concurso com resultado na API (ex.: Quina 7039).
    proximo_regular = próximo da série diária (ex.: 7040).
    especiais = concursos paralelos cadastrados (ex.: Quina de São João 7051).
    """
    data = _get_json(_api_url(key), timeout=timeout)
    out: Dict[str, Any] = {
        "ultimo_sorteado": 0,
        "proximo_regular": 0,
        "indicador_especial": False,
        "valor_acumulado_especial": None,
        "data_ultimo_sorteio": "",
        "data_proximo_sorteio": "",
        "especiais": list(CONCURSOS_ESPECIAIS.get(key, [])),
        "api_ok": False,
    }
    if not data:
        return out

    out["api_ok"] = True
    out["ultimo_sorteado"] = int(data.get("numero") or data.get("numeroConcurso") or 0)
    out["proximo_regular"] = int(data.get("numeroConcursoProximo") or 0)
    out["indicador_especial"] = bool(data.get("indicadorConcursoEspecial"))
    out["valor_acumulado_especial"] = data.get("valorAcumuladoConcursoEspecial")
    out["data_ultimo_sorteio"] = data.get("dataApuracao") or ""
    out["data_proximo_sorteio"] = data.get("dataProximoConcurso") or ""

    for esp in out["especiais"]:
        n = int(esp.get("concurso") or 0)
        if not n:
            continue
        det = _get_json(_api_url(key, n), timeout=timeout)
        esp["disponivel_api"] = det is not None
        if det:
            esp["data_sorteio"] = det.get("dataApuracao") or esp.get("data_sorteio", "")
            esp["sorteado"] = bool(det.get("dezenasSorteadasOrdemSorteio") or det.get("listaDezenas"))

    return out


def listar_especiais(key: str) -> List[Dict[str, Any]]:
    return list(CONCURSOS_ESPECIAIS.get(key, []))
