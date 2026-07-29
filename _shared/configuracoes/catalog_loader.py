"""Carrega catálogo oficial estático das modalidades (JSON)."""
import json
import os
from typing import Any, Dict, Optional

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalogo_oficial.json")
_cache: Optional[Dict[str, Any]] = None


def carregar_catalogo() -> Dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.isfile(_CATALOG_PATH):
        _cache = {}
        return _cache
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    return _cache


def obter_catalogo_modalidade(modality_key: str) -> Dict[str, Any]:
    return carregar_catalogo().get(modality_key, {})
