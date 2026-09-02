#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Registra /configuracoes/ e ícone engrenagem nas modalidades."""
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

APPS = [
    ("AnalisePorPosicao-Lotofacil-Only", "lotofacil"),
    ("AnalisePorPosicao-SuperSete-Only", "supersete"),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania"),
    ("AnalisePorPosicao-Quina-Only", "quina"),
    ("AnalisePorPosicao-MegaSena-Only", "megasena"),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria"),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena"),
    ("AnalisePorPosicao-Timemania-Only", "timemania"),
]

GEAR_CSS = """
        .nav-gear-isolated {
            margin-left: auto;
            flex-shrink: 0;
            padding: .45rem .75rem !important;
        }
        .nav-gear-isolated i { font-size: 1rem; }
"""

GEAR_HTML = """            <a class="nav-btn nav-gear-isolated" href="/configuracoes/" title="Configurações"><i class="fas fa-cog"></i></a>
"""

ROUTES_FILE = '''import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from configuracoes.routes_modality import build_config_blueprint

config_bp = build_config_blueprint("{key}")
'''


def patch_app_py(app_path: str, has_config: bool):
    txt = open(app_path, encoding="utf-8").read()
    if "extend_config_app" in txt and "build_config_blueprint" in txt:
        return False
    if has_config and "config_bp" in txt and "from routes.config_routes import config_bp" in txt:
        # Dia de Sorte — só integração shared
        if "extend_config_app" not in txt:
            block = """
from configuracoes.app_integration import extend_config_app
"""
            if "from auto_sync import" in txt:
                txt = txt.replace("from auto_sync import", block + "from auto_sync import", 1)
            if "cc_extend_app(app," in txt:
                txt = txt.replace(
                    "cc_extend_app(app,",
                    "extend_config_app(app)\n    cc_extend_app(app,",
                    1,
                )
            open(app_path, "w", encoding="utf-8").write(txt)
        return True
    inserts = []
    if "from routes.config_routes import config_bp" not in txt:
        inserts.append("from routes.config_routes import config_bp")
    if "extend_config_app" not in txt:
        inserts.append("from configuracoes.app_integration import extend_config_app")
    for line in inserts:
        if "from auto_sync import" in txt:
            txt = txt.replace("from auto_sync import", line + "\nfrom auto_sync import", 1)
        elif "from central_conferencias" in txt:
            txt = txt.replace(
                "from central_conferencias.app_integration",
                line + "\nfrom central_conferencias.app_integration",
                1,
            )
    if "extend_config_app(app)" not in txt:
        txt = txt.replace(
            "cc_extend_app(app,",
            "extend_config_app(app)\n    cc_extend_app(app,",
            1,
        )
    if "register_blueprint(config_bp" not in txt:
        txt = txt.replace(
            "app.register_blueprint(geradores_elite_bp)",
            "app.register_blueprint(config_bp, url_prefix='/configuracoes')\n    app.register_blueprint(geradores_elite_bp)",
            1,
        )
    open(app_path, "w", encoding="utf-8").write(txt)
    return True


def patch_base_html(path: str):
    txt = open(path, encoding="utf-8").read()
    if "nav-gear-isolated" in txt:
        return False
    if GEAR_CSS.strip() not in txt:
        txt = txt.replace("</style>", GEAR_CSS + "\n    </style>", 1)
    # Remove texto Configurações no meio do menu
    txt = re.sub(
        r'\s*<a class="nav-btn" href="/configuracoes/"><i class="fas fa-cog[^"]*"></i>\s*Configurações</a>\s*',
        "\n",
        txt,
        flags=re.I,
    )
    txt = re.sub(
        r'<div class="mobile-group-title">Sistema</div>\s*<a class="mobile-link" href="/configuracoes/"[^>]*>[\s\S]*?</a>\s*',
        "",
        txt,
        count=1,
    )
    # Engrenagem antes do toggler
    if "nav-toggler" in txt and GEAR_HTML.strip() not in txt:
        txt = re.sub(
            r'(\s*)<button class="nav-toggler"',
            GEAR_HTML + r"\1<button class=\"nav-toggler\"",
            txt,
            count=1,
        )
    # Mobile gear (não reintroduzir link Painel Geral nas modalidades)
    mobile_gear = '<a class="mobile-link" href="/configuracoes/" onclick="closeMobileNav()" title="Configurações"><i class="fas fa-cog"></i> Configurações</a>\n        '
    if 'href="/configuracoes/" onclick="closeMobileNav()"' not in txt and "cc_nav_mobile.html" in txt:
        txt = txt.replace(
            "{% include 'cc_nav_mobile.html' %}",
            mobile_gear + "{% include 'cc_nav_mobile.html' %}",
            1,
        )
    open(path, "w", encoding="utf-8").write(txt)
    return True


def main():
    for folder, key in APPS:
        app_dir = os.path.join(ROOT, folder)
        routes_path = os.path.join(app_dir, "routes", "config_routes.py")
        if not os.path.isfile(routes_path):
            with open(routes_path, "w", encoding="utf-8") as f:
                f.write(ROUTES_FILE.format(key=key))
            print("routes", folder)
        patch_app_py(os.path.join(app_dir, "app.py"), has_config=False)
        patch_base_html(os.path.join(app_dir, "templates", "base.html"))
        print("OK", folder)

    # Dia de Sorte
    ds = os.path.join(ROOT, "AnalisePorPosicao--DiaDeSorte-Only")
    patch_app_py(os.path.join(ds, "app.py"), has_config=True)
    patch_base_html(os.path.join(ds, "templates", "base.html"))
    print("OK Dia de Sorte")


if __name__ == "__main__":
    main()
