"""URLs oficiais de download Excel CAIXA e pasta única de resultados."""
from __future__ import annotations

from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent
REPO_ROOT = _SHARED.parent
# Fonte oficial: uma pasta só (evita duplicar em LoteriasPosicao/Downloads).
DOWNLOADS_DIR = REPO_ROOT / "DownloadTodosResultadosLoterias" / "downloads"
LEGACY_DOWNLOADS_DIR = REPO_ROOT / "Downloads"

EXCEL_DOWNLOAD_BASE = (
    "https://servicebus3.caixa.gov.br/portaldeloterias/api/resultados/download"
)

# slug da query ?modalidade=  (confirmado: Dia-de-Sorte)
EXCEL_MODALIDADE = {
    "diadesorte": "Dia-de-Sorte",
    "megasena": "Mega-Sena",
    "lotofacil": "Lotofacil",
    "quina": "Quina",
    "lotomania": "Lotomania",
    "timemania": "Timemania",
    "duplasena": "Dupla-Sena",
    "supersete": "Super-Sete",
    "maismilionaria": "Mais-Milionaria",
}

EXCEL_FILENAME = {
    "diadesorte": "DIA_DE_SORTE.xlsx",
    "megasena": "MEGA_SENA.xlsx",
    "lotofacil": "LOTOFACIL.xlsx",
    "quina": "QUINA.xlsx",
    "lotomania": "LOTOMANIA.xlsx",
    "timemania": "TIMEMANIA.xlsx",
    "duplasena": "DUPLA_SENA.xlsx",
    "supersete": "SUPER_SETE.xlsx",
    "maismilionaria": "MAIS_MILIONARIA.xlsx",
}

JSON_FILENAME = {
    "diadesorte": "DIA_DE_SORTE_premiacao.json",
}


def excel_download_url(key: str) -> str:
    slug = EXCEL_MODALIDADE.get(key) or key
    return f"{EXCEL_DOWNLOAD_BASE}?modalidade={slug}"


def excel_filename(key: str) -> str:
    return EXCEL_FILENAME.get(key) or f"{key.upper()}.xlsx"


def resolve_excel_path(key: str) -> Path:
    """Prefere a pasta única; só cai no Downloads legado se o arquivo não existir."""
    name = excel_filename(key)
    preferred = DOWNLOADS_DIR / name
    if preferred.is_file():
        return preferred
    legacy = LEGACY_DOWNLOADS_DIR / name
    if legacy.is_file():
        return legacy
    return preferred


def json_filename(key: str) -> str:
    return JSON_FILENAME.get(key) or f"{key.upper()}_premiacao.json"
