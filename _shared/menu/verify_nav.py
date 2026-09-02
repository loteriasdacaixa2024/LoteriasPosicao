# -*- coding: utf-8 -*-
"""Verifica estrutura de menu padronizada em todas as modalidades."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SHARED = ROOT / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

APPS = [
    "AnalisePorPosicao-Lotofacil-Only",
    "AnalisePorPosicao--DiaDeSorte-Only",
    "AnalisePorPosicao-Lotomania-Only",
    "AnalisePorPosicao-Quina-Only",
    "AnalisePorPosicao-MegaSena-Only",
    "AnalisePorPosicao-MaisMilionaria-Only",
    "AnalisePorPosicao-DuplaSena-Only",
    "AnalisePorPosicao-Timemania-Only",
    "AnalisePorPosicao-SuperSete-Only",
]

REQUIRED_BASE = [
    "extend_nav_app",
    "nav_dados_block_desktop.html",
    "nav_analise_block_desktop.html",
    "nav_desdobramento_desktop.html",
    "nav_geradores_elite_desktop.html",
    "nav_dados_block_mobile.html",
    "nav_analise_block_mobile.html",
    "nav_desdobramento_mobile.html",
    "nav_geradores_elite_mobile.html",
    "cc_nav_desktop.html",
    "cc_nav_mobile.html",
    "ac_nav_comparar_desktop.html",
    "ac_nav_repeticao_desktop.html",
]

REQUIRED_ROUTES = [
    "register_comparar",
    "register_repeticao",
    "extend_nav_app",
    "cc_extend_app",
]


def audit():
    errors = []
    for folder in APPS:
        app_dir = ROOT / folder
        app_py = (app_dir / "app.py").read_text(encoding="utf-8")
        base = (app_dir / "templates" / "base.html").read_text(encoding="utf-8")
        name = folder.replace("AnalisePorPosicao-", "").replace("--", "")
        for token in REQUIRED_BASE:
            if token not in base and token not in app_py:
                errors.append(f"{name}: falta `{token}` em base.html ou app.py")
        for token in REQUIRED_ROUTES:
            if token not in app_py:
                errors.append(f"{name}: app.py sem `{token}`")
        if "lotofacil" in folder.lower():
            if "analise_comparar_bp" not in app_py or "extend_nav_app" not in app_py:
                errors.append(f"{name}: Lotofácil incompleta")
        elif "register_comparar" not in app_py or "register_repeticao" not in app_py:
            errors.append(f"{name}: falta register_comparar/repeticao")
        if "megasena" in folder.lower() and "register_conferencia_extras" not in app_py:
            errors.append(f"{name}: Mega-Sena sem register_conferencia_extras")
        if re.search(r'dd-title">Comparar concursos<', base):
            errors.append(f"{name}: menu Comparar ainda hardcoded (deveria usar include)")
        if re.search(r'dd-title">Análise por Coluna<', base):
            errors.append(f"{name}: Super Sete ainda com label antigo no Dados")
        if re.search(r'href="/geradores-elite/engine-final/"', base) and "nav_geradores_elite_desktop.html" not in base:
            errors.append(f"{name}: Geradores de Elite desktop ainda hardcoded (falta include)")
        if "repeticao-apostas" not in base and "nav_geradores_elite" in base:
            pass  # include carrega via nav_cfg — checado abaixo
    # nav_cfg: 2 itens em Geradores + dados_extras onde aplicável
    from menu.nav_config import get_nav_config

    MODALITY_KEYS = {
        "Lotofacil-Only": "lotofacil",
        "DiaDeSorte-Only": "diadesorte",
        "Lotomania-Only": "lotomania",
        "Quina-Only": "quina",
        "MegaSena-Only": "megasena",
        "MaisMilionaria-Only": "maismilionaria",
        "DuplaSena-Only": "duplasena",
        "Timemania-Only": "timemania",
        "SuperSete-Only": "supersete",
    }
    for folder in APPS:
        key_suffix = folder.replace("AnalisePorPosicao-", "").replace("--", "")
        mod_key = MODALITY_KEYS.get(key_suffix)
        if not mod_key:
            continue
        cfg = get_nav_config(mod_key)
        ge_items = cfg.get("geradores_elite", {}).get("items") or []
        min_ge = 4 if mod_key == "lotofacil" else 3
        if len(ge_items) != min_ge:
            errors.append(f"{key_suffix}: geradores_elite deve ter {min_ge} itens (tem {len(ge_items)})")
        try:
            from geradores_elite.inteligente import GERADORES_ELITE_MENU_TITLES, tem_gerador_inteligente

            titles = [it.get("title") for it in ge_items]
            expected = list(GERADORES_ELITE_MENU_TITLES)
            if mod_key == "lotofacil":
                expected = expected + ["Comportamento → Apostas"]
            if titles != expected:
                errors.append(f"{key_suffix}: títulos Geradores Elite {titles}")
            if not tem_gerador_inteligente(mod_key):
                errors.append(f"{key_suffix}: sem gerador Sniper inteligente (auto/manual)")
        except ImportError:
            pass
        if mod_key != "lotofacil" and not cfg.get("dados_extras"):
            errors.append(f"{key_suffix}: falta dados_extras (5º item Dados) no nav_config")
    return errors


if __name__ == "__main__":
    errs = audit()
    if errs:
        print("FALHAS:")
        for e in errs:
            print(" -", e)
        raise SystemExit(1)
    print("OK — 9 modalidades com estrutura de menu padronizada.")
