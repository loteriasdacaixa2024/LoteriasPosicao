# -*- coding: utf-8 -*-
"""Registra Comparar concursos nas apps 5154–5160 (Lotofácil 5152 já tem implementação local)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # LoteriasPosicao

APPS = [
    ("AnalisePorPosicao-Lotomania-Only", "lotomania"),
    ("AnalisePorPosicao-Quina-Only", "quina"),
    ("AnalisePorPosicao-MegaSena-Only", "megasena"),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria"),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena"),
    ("AnalisePorPosicao-Timemania-Only", "timemania"),
    ("AnalisePorPosicao-SuperSete-Only", "supersete"),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diadesorte"),
]

REGISTER_LINE = "    from analise_comparar.routes_factory import register_comparar"
REGISTER_CALL = "    register_comparar(app, '{key}')"

DESKTOP_INC = "                    {% include 'ac_nav_comparar_desktop.html' %}\n"
MOBILE_INC = "        {% include 'ac_nav_comparar_mobile.html' %}\n"


def patch_app_py(app_py: Path, key: str) -> bool:
    text = app_py.read_text(encoding="utf-8")
    changed = False
    if "register_comparar(app" not in text:
        if "_CC_ROOT" not in text and "_AC_ROOT" not in text:
            insert = '''
import os as _ac_os
import sys as _ac_sys
_AC_ROOT = _ac_os.path.abspath(_ac_os.path.join(_ac_os.path.dirname(__file__), "..", "_shared"))
if _AC_ROOT not in _ac_sys.path:
    _ac_sys.path.insert(0, _AC_ROOT)
'''
            text = text.replace("def create_app():", insert + "\ndef create_app():")
        import_line = "from analise_comparar.routes_factory import register_comparar\n"
        if import_line not in text:
            # após bloco _shared existente ou após imports flask
            if "_CC_ROOT" in text:
                text = re.sub(
                    r"(from auto_sync import start_auto_sync_once\n)",
                    r"\1" + import_line,
                    text,
                    count=1,
                )
            elif "_AC_ROOT" in text:
                text = re.sub(
                    r"(if _AC_ROOT not in _ac_sys\.path:.*?\n)\n",
                    r"\1\n" + import_line,
                    text,
                    count=1,
                    flags=re.DOTALL,
                )
            else:
                text = text.replace(
                    "from flask import Flask\n",
                    "from flask import Flask\n" + import_line,
                    1,
                )
        call = REGISTER_CALL.format(key=key)
        if call not in text:
            marker = "    return app"
            if marker in text:
                text = text.replace(marker, call + "\n\n" + marker, 1)
        changed = True
    if changed:
        app_py.write_text(text, encoding="utf-8")
    return changed


def patch_base(base: Path) -> bool:
    text = base.read_text(encoding="utf-8")
    changed = False
    if "ac_nav_comparar_desktop" not in text:
        # Após link Sincronizar Dados (primeiro dd-link após dd-header Base de Dados)
        m = re.search(
            r'(<div class="dd-header">Base de Dados</div>\s*'
            r'<a class="dd-link" href="/">.*?</a>\s*)',
            text,
            re.DOTALL,
        )
        if m:
            text = text[: m.end()] + DESKTOP_INC + text[m.end() :]
            changed = True
        else:
            # Mega: formato compacto em uma linha
            m2 = re.search(
                r'(<div class="dd-header">Base de Dados</div>\s*'
                r'<a class="dd-link" href="/">.*?</span></span></a>\s*)',
                text,
                re.DOTALL,
            )
            if m2:
                text = text[: m2.end()] + DESKTOP_INC + text[m2.end() :]
                changed = True
    if "ac_nav_comparar_mobile" not in text:
        m = re.search(
            r'(<div class="mobile-group-title">Base de Dados</div>\s*'
            r'<a class="mobile-link" href="/"[^>]*>.*?</a>\s*)',
            text,
            re.DOTALL,
        )
        if m:
            text = text[: m.end()] + MOBILE_INC + text[m.end() :]
            changed = True
    if changed:
        base.write_text(text, encoding="utf-8")
    return changed


def main() -> None:
    for folder, key in APPS:
        app_dir = ROOT / folder
        app_py = app_dir / "app.py"
        base = app_dir / "templates" / "base.html"
        if not app_py.exists():
            print(f"[SKIP] {folder} — app.py não encontrado")
            continue
        pa = patch_app_py(app_py, key)
        pb = patch_base(base) if base.exists() else False
        print(f"[{'OK' if pa or pb else '—'}] {folder} ({key}) app={pa} nav={pb}")


if __name__ == "__main__":
    main()
