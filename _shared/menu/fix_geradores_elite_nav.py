# -*- coding: utf-8 -*-
"""
Garante menu Geradores de Elite com 3 itens (include nav_cfg) em Quina e Lotomania.
Remove blocos legados hardcoded (só Engine Final) se ainda existirem.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SHARED = ROOT / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

TARGETS = [
    ("AnalisePorPosicao-Quina-Only", "quina"),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania"),
]

DESKTOP_INCLUDE = "{% include 'nav_geradores_elite_desktop.html' %}"
MOBILE_INCLUDE = "{% include 'nav_geradores_elite_mobile.html' %}"

LEGACY_BLOCK = re.compile(
    r"\s*<div class=\"nav-item-wrap\">\s*"
    r"<button class=\"nav-btn\"><i class=\"fas fa-bolt[^\"]*\"[^>]*></i>\s*Geradores de Elite[\s\S]*?"
    r"</div>\s*</div>\s*"
    r"(?=</div>\s*<a class=\"nav-btn nav-gear|</div>\s*<button class=\"nav-toggler\")",
    re.MULTILINE,
)

LEGACY_MOBILE = re.compile(
    r"\s*<div class=\"mobile-group-title\">Geradores de Elite</div>\s*"
    r"<a class=\"mobile-link\" href=\"/geradores-elite/engine-final/\"[\s\S]*?"
    r"(?=<div class=\"mobile-group-title\">Base de Dados</div>)",
    re.MULTILINE,
)


def patch_base(base_path: Path) -> list[str]:
    changes = []
    text = base_path.read_text(encoding="utf-8")
    orig = text

    if LEGACY_BLOCK.search(text) and DESKTOP_INCLUDE not in text:
        text = LEGACY_BLOCK.sub(f"\n            {DESKTOP_INCLUDE}\n", text, count=1)
        changes.append("desktop: legado → include")

    if LEGACY_MOBILE.search(text) and MOBILE_INCLUDE not in text:
        text = LEGACY_MOBILE.sub(f"\n        {MOBILE_INCLUDE}\n        ", text, count=1)
        changes.append("mobile: legado → include")

    if DESKTOP_INCLUDE not in text:
        anchor = "{% include 'cc_nav_desktop.html' %}"
        if anchor in text:
            text = text.replace(anchor, anchor + f"\n            {DESKTOP_INCLUDE}", 1)
            changes.append("desktop: include adicionado")

    if MOBILE_INCLUDE not in text:
        anchor = '<div class="nav-mobile-panel" id="mobilePanel">'
        if anchor in text:
            text = text.replace(
                anchor,
                anchor + f"\n        {MOBILE_INCLUDE}",
                1,
            )
            changes.append("mobile: include adicionado")

    if text != orig:
        base_path.write_text(text, encoding="utf-8")
    return changes


def main() -> int:
    from menu.nav_config import get_nav_config

    errors = []
    for folder, key in TARGETS:
        app_dir = ROOT / folder
        base = app_dir / "templates" / "base.html"
        if not base.is_file():
            errors.append(f"{folder}: base.html ausente")
            continue
        ch = patch_base(base)
        cfg = get_nav_config(key)
        n = len(cfg.get("geradores_elite", {}).get("items") or [])
        print(f"{folder}: itens_nav={n} patches={ch or ['ok']}")
        if n != 3:
            errors.append(f"{folder}: nav_config com {n} itens (esperado 3)")

    if errors:
        print("\nERROS:")
        for e in errors:
            print(" -", e)
        return 1
    print("\nOK — Quina e Lotomania com 3 itens em Geradores de Elite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
