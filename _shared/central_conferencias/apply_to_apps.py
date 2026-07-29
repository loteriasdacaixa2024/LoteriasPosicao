# -*- coding: utf-8 -*-
"""Aplica Central de Conferências (menu + abas) em 5152–5160."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # LoteriasPosicao

APPS = [
    ("AnalisePorPosicao-Lotofacil-Only", "lotofacil", True),
    ("AnalisePorPosicao-SuperSete-Only", "supersete", True),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania", True),
    ("AnalisePorPosicao-Quina-Only", "quina", True),
    ("AnalisePorPosicao-MegaSena-Only", "megasena", False),  # já completo
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria", True),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena", True),
    ("AnalisePorPosicao-Timemania-Only", "timemania", True),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diasorte", True),
]

NAV_DESKTOP_OLD = re.compile(
    r"\s*<a class=\"nav-btn\" href=\"/central-conferencias/\">.*?</a>\s*",
    re.DOTALL,
)

MOBILE_OLD = re.compile(
    r"\s*<div class=\"mobile-group-title\">Resultados</div>\s*"
    r"<a class=\"mobile-link\" href=\"/central-conferencias/\".*?</a>\s*",
    re.DOTALL,
)

MOBILE_SIMPLE = re.compile(
    r"\s*<a class=\"mobile-link\" href=\"/central-conferencias/\"[^>]*>.*?</a>\s*",
    re.DOTALL,
)


def patch_app_py(app_py: Path, key: str, register_routes: bool) -> None:
    text = app_py.read_text(encoding="utf-8")
    if "central_conferencias.app_integration" in text:
        if register_routes and "register_conferencia_extras" not in text:
            text = text.replace(
                "register_conferencia_extras(conferencia_bp",
                "register_conferencia_extras(conferencia_bp",
            )
        app_py.write_text(text, encoding="utf-8")
        return
    insert = f'''
import os as _cc_os
import sys as _cc_sys
_CC_ROOT = _cc_os.path.abspath(_cc_os.path.join(_cc_os.path.dirname(__file__), "..", "_shared"))
if _CC_ROOT not in _cc_sys.path:
    _cc_sys.path.insert(0, _CC_ROOT)
from central_conferencias.app_integration import extend_app as cc_extend_app, register_conferencia_extras
'''
    if "def create_app():" in text and insert.strip() not in text:
        text = text.replace("def create_app():", insert + "\ndef create_app():")
    if "cc_extend_app(app" not in text:
        text = text.replace(
            "    db.init_app(app)",
            f"    db.init_app(app)\n    cc_extend_app(app, '{key}')",
        )
    if register_routes and "register_conferencia_extras(conferencia_bp" not in text:
        text = text.replace(
            "app.register_blueprint(conferencia_bp",
            f"register_conferencia_extras(conferencia_bp, '{key}')\n    app.register_blueprint(conferencia_bp",
            1,
        )
    app_py.write_text(text, encoding="utf-8")


def patch_base(base: Path) -> None:
    text = base.read_text(encoding="utf-8")
    if "{% include 'cc_nav_desktop.html' %}" in text:
        return
    if "Central de Conferências" in text and "cc_nav_desktop" not in text:
        return  # Mega já tem menu completo inline
    nav_inc = "            {% include 'cc_nav_desktop.html' %}\n"
    mob_inc = "        {% include 'cc_nav_mobile.html' %}\n"

    if NAV_DESKTOP_OLD.search(text):
        text = NAV_DESKTOP_OLD.sub("\n" + nav_inc, text, count=1)
    elif "Central de Conferências" not in text:
        # inserir antes de Geradores de Elite ou Painel
        marker = '<div class="nav-item-wrap">\n                <button class="nav-btn"><i class="fas fa-bolt'
        if marker in text:
            text = text.replace(marker, nav_inc + "\n            " + marker, 1)

    if MOBILE_OLD.search(text):
        text = MOBILE_OLD.sub("\n" + mob_inc, text, count=1)
    elif "cc_nav_mobile" not in text and 'href="/central-conferencias/"' in text:
        text = MOBILE_SIMPLE.sub(mob_inc, text, count=1)

    base.write_text(text, encoding="utf-8")


def patch_conferencia(conf: Path) -> None:
    text = conf.read_text(encoding="utf-8")
    if "cc_conferencia_shell_start" not in text:
        text = text.replace(
            "{% block content %}",
            "{% block content %}\n{% include 'cc_conferencia_shell_start.html' %}\n",
            1,
        )
    if "cc_conferencia_shell_end" not in text:
        text = re.sub(
            r"document\.addEventListener\('DOMContentLoaded',\s*carregar\);",
            "// carregar via abas (cc_conferencia_scripts)",
            text,
        )
        marker = "{% endblock %}\n{% block scripts %}"
        if marker in text:
            text = text.replace(
                marker,
                "{% include 'cc_conferencia_shell_end.html' %}\n{% endblock %}\n{% block scripts %}\n{% include 'cc_conferencia_scripts.html' %}\n",
                1,
            )
    # Corrigir bloco scripts duplicado (bug de aplicação anterior)
    text = re.sub(
        r"</script>\s*\{% include 'cc_conferencia_shell_end.html' %\}\s*\{% endblock %\}\s*\{% block scripts %\}\s*\{% include 'cc_conferencia_scripts.html' %\}\s*\{% endblock %\}",
        "</script>\n{% endblock %}",
        text,
        flags=re.DOTALL,
    )
  # Fechar content antes de scripts se shell_end ficou dentro de scripts
    if text.count("{% block scripts %}") == 1 and "cc_conferencia_shell_end" in text:
        bad = re.search(
            r"(\{% block scripts %\}.*?)({% include 'cc_conferencia_shell_end.html' %})",
            text,
            re.DOTALL,
        )
        if bad:
            text = text.replace(
                bad.group(0),
                "{% include 'cc_conferencia_shell_end.html' %}\n{% endblock %}\n\n{% block scripts %}\n{% include 'cc_conferencia_scripts.html' %}\n"
                + bad.group(1).replace("{% block scripts %}", "").replace("{% include 'cc_conferencia_scripts.html' %}", ""),
                1,
            )
    conf.write_text(text, encoding="utf-8")


def main():
    for folder, key, register in APPS:
        app_dir = ROOT / folder
        if not app_dir.is_dir():
            print(f"SKIP {folder}")
            continue
        patch_app_py(app_dir / "app.py", key, register)
        patch_base(app_dir / "templates" / "base.html")
        if register:
            patch_conferencia(app_dir / "templates" / "conferencia.html")
        print(f"OK {folder} ({key})")


if __name__ == "__main__":
    main()
