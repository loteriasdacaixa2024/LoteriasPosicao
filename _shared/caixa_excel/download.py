"""Download do Excel oficial CAIXA para a pasta Downloads."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import requests

from .config import DOWNLOADS_DIR, excel_download_url, excel_filename

HEADERS = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TIMEOUT = 90


def _get(url: str):
    try:
        import certifi
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=certifi.where())
    except requests.exceptions.SSLError:
        import urllib3
        urllib3.disable_warnings()
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)


def baixar_excel(key: str) -> Dict:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOADS_DIR / excel_filename(key)
    url = excel_download_url(key)
    r = _get(url)
    if r.status_code != 200:
        raise RuntimeError(f"Download CAIXA falhou (HTTP {r.status_code}) em {url}")
    if r.content[:2] != b"PK":
        raise RuntimeError("A CAIXA não devolveu um arquivo Excel (.xlsx).")
    dest.write_bytes(r.content)
    return {
        "arquivo": str(dest),
        "bytes": len(r.content),
        "url": url,
        "filename": dest.name,
    }
