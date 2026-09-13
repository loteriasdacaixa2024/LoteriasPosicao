# -*- coding: utf-8 -*-
"""Baixa os Excel oficiais da CAIXA para a pasta única do projeto."""
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DEST_DIR = HERE / "downloads"
DEST_DIR.mkdir(parents=True, exist_ok=True)

URLS = {
    "Lotofacil": "LOTOFACIL.xlsx",
    "Dia-de-Sorte": "DIA_DE_SORTE.xlsx",
    "Lotomania": "LOTOMANIA.xlsx",
    "Quina": "QUINA.xlsx",
    "Mega-Sena": "MEGA_SENA.xlsx",
    "Mais-Milionaria": "MAIS_MILIONARIA.xlsx",
    "Dupla-Sena": "DUPLA_SENA.xlsx",
    "Timemania": "TIMEMANIA.xlsx",
    "Super-Sete": "SUPER_SETE.xlsx",
}

BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download"
HEADERS = {"Accept": "*/*", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _get(url: str):
    try:
        import certifi
        return requests.get(url, headers=HEADERS, timeout=90, verify=certifi.where())
    except Exception:
        import urllib3
        urllib3.disable_warnings()
        return requests.get(url, headers=HEADERS, timeout=90, verify=False)


for slug, filename in URLS.items():
    url = f"{BASE}?modalidade={slug}"
    response = _get(url)
    if response.status_code != 200:
        print(f"Erro ao baixar {slug}. HTTP {response.status_code}")
        continue
    if response.content[:2] != b"PK":
        print(f"A CAIXA não devolveu Excel para {slug}.")
        continue
    dest = DEST_DIR / filename
    dest.write_bytes(response.content)
    print(f"Download concluído: {dest} ({len(response.content)} bytes)")
