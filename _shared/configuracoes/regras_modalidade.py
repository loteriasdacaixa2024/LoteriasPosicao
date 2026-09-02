# -*- coding: utf-8 -*-
"""
Fonte única de regras oficiais por modalidade.

Preferência de leitura:
1. catalogo_oficial.json (Caixa — universo, sorteadas, marcação, preços)
2. geradores_elite.modality_config.MODALITIES (universo numérico tipado)
3. configuracoes.config.MODALITIES (porta, bolão, links)

Use sempre `get_regras(modality_key)` em novos módulos em vez de literais.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from functools import lru_cache
from typing import Any, Dict, List, Optional

_DIR = os.path.dirname(os.path.abspath(__file__))
_CATALOGO_PATH = os.path.join(_DIR, "catalogo_oficial.json")


@lru_cache(maxsize=1)
def _load_catalogo() -> Dict[str, Any]:
    with open(_CATALOGO_PATH, encoding="utf-8") as f:
        return json.load(f)


def _modality_engine(key: str) -> Dict[str, Any]:
    try:
        from geradores_elite.modality_config import MODALITIES as ENG
        return dict(ENG.get(key) or {})
    except Exception:
        return {}


def _modality_meta(key: str) -> Dict[str, Any]:
    try:
        from configuracoes.config import MODALITIES as META
        return dict(META.get(key) or {})
    except Exception:
        return {}


def get_regras(modality_key: str) -> Dict[str, Any]:
    """
    Regras unificadas da modalidade.

    Campos principais:
      key, nome, porta
      dezena_min, dezena_max, total
      sorteadas          — quantos números saem no sorteio
      pick_min, pick_max, pick_default — marcação no volante
      extra              — mes | time | trevo | None
      tabela_precos      — [{dezenas, valor}, ...]
      universo_label     — texto oficial
    """
    key = (modality_key or "").strip().lower()
    cat = (_load_catalogo().get(key) or {})
    eng = _modality_engine(key)
    meta = _modality_meta(key)
    if not eng and not cat and not meta:
        raise ValueError(f"Modalidade desconhecida: {modality_key}")

    aposta_cat = cat.get("aposta") or {}
    aposta_meta = meta.get("aposta") or {}

    dmin = int(eng.get("dezena_min", 1))
    dmax = int(eng.get("dezena_max", eng.get("total") or 60))
    total = int(eng.get("total") or (dmax - dmin + 1))

    sorteadas = int(
        aposta_cat.get("dezenas_sorteadas")
        or eng.get("sorteadas")
        or aposta_meta.get("fixa")
        or 0
    )
    pick_min = int(
        aposta_cat.get("marcacao_min")
        or eng.get("pick_min")
        or aposta_meta.get("min")
        or sorteadas
    )
    pick_max = int(
        aposta_cat.get("marcacao_max")
        or eng.get("pick_max")
        or aposta_meta.get("max")
        or pick_min
    )
    pick_default = int(eng.get("pick_default") or pick_min)

    precos = cat.get("tabela_precos") or []
    precos_map = {
        int(p["dezenas"]): float(p["valor"])
        for p in precos
        if "dezenas" in p and "valor" in p
    }

    return {
        "key": key,
        "nome": eng.get("nome") or meta.get("nome") or key,
        "porta": int(eng.get("porta") or meta.get("porta") or 0),
        "dezena_min": dmin,
        "dezena_max": dmax,
        "total": total,
        "sorteadas": sorteadas,
        "pick_min": pick_min,
        "pick_max": pick_max,
        "pick_default": pick_default,
        "extra": eng.get("extra") or aposta_cat.get("extra") or aposta_meta.get("extra"),
        "universo_label": aposta_cat.get("universo") or aposta_meta.get("universo") or f"{dmin} a {dmax}",
        "tabela_precos": deepcopy(precos),
        "precos_map": precos_map,
        "export_join": eng.get("export_join", " "),
        "export_is_columns": bool(eng.get("export_is_columns")),
        "api_slug": meta.get("api_slug") or cat.get("api_slug") or key,
    }


def lista_modalidades() -> List[str]:
    cat = set(_load_catalogo().keys())
    eng = set(_modality_engine("__none__") and [])  # noqa — force import path
    try:
        from geradores_elite.modality_config import MODALITIES as ENG
        eng = set(ENG.keys())
    except Exception:
        eng = set()
    return sorted(cat | eng)


def universo_range(modality_key: str) -> range:
    r = get_regras(modality_key)
    return range(r["dezena_min"], r["dezena_max"] + 1)


def validar_tamanho_aposta(modality_key: str, n: int) -> bool:
    r = get_regras(modality_key)
    return r["pick_min"] <= int(n) <= r["pick_max"]


def preco_aposta(modality_key: str, n_dezenas: int) -> Optional[float]:
    r = get_regras(modality_key)
    return r["precos_map"].get(int(n_dezenas))


def formatar_brl(valor: Optional[float]) -> str:
    """Formata no padrão brasileiro: R$ 0,00 / R$ 1.980,00."""
    if valor is None:
        return ""
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return ""
    sinal = "-" if n < 0 else ""
    n = abs(n)
    inteiro, frac = f"{n:.2f}".split(".")
    partes: List[str] = []
    while len(inteiro) > 3:
        partes.append(inteiro[-3:])
        inteiro = inteiro[:-3]
    partes.append(inteiro)
    corpo = ".".join(reversed(partes)) + "," + frac
    return f"{sinal}R$ {corpo}"


def preco_lote(modality_key: str, n_dezenas: int, n_apostas: int) -> Dict[str, Any]:
    unit = preco_aposta(modality_key, int(n_dezenas))
    qtd = max(0, int(n_apostas or 0))
    if unit is None:
        return {
            "unitario": None,
            "total": None,
            "unitario_fmt": "",
            "total_fmt": "",
            "dezenas_por_aposta": int(n_dezenas),
            "qtd_apostas": qtd,
        }
    total = round(unit * qtd, 2)
    return {
        "unitario": unit,
        "total": total,
        "unitario_fmt": formatar_brl(unit),
        "total_fmt": formatar_brl(total),
        "dezenas_por_aposta": int(n_dezenas),
        "qtd_apostas": qtd,
    }
