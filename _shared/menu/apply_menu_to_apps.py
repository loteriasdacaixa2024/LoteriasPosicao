# -*- coding: utf-8 -*-
"""Padroniza menus em todas as modalidades — injeta nav_cfg e includes compartilhados."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APPS = [
    ("AnalisePorPosicao-Lotofacil-Only", "lotofacil"),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diadesorte"),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania"),
    ("AnalisePorPosicao-Quina-Only", "quina"),
    ("AnalisePorPosicao-MegaSena-Only", "megasena"),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria"),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena"),
    ("AnalisePorPosicao-Timemania-Only", "timemania"),
    ("AnalisePorPosicao-SuperSete-Only", "supersete"),
]

NAV_IMPORT = """from menu.app_integration import extend_nav_app"""

NAV_CALL = "    extend_nav_app(app, '{key}')"


def patch_app_py(app_dir: Path, key: str) -> bool:
    app_py = app_dir / "app.py"
    text = app_py.read_text(encoding="utf-8")
    changed = False

    if "extend_nav_app" not in text:
        anchor = "from analise_repeticao.routes_factory import register_repeticao"
        if anchor not in text:
            anchor = "from configuracoes.app_integration import extend_config_app"
        text = text.replace(anchor, anchor + "\n" + NAV_IMPORT)
        changed = True

    call = NAV_CALL.format(key=key)
    if call not in text:
        anchor = f"cc_extend_app(app, '{key}')"
        if anchor in text:
            text = text.replace(anchor, anchor + "\n" + call)
        elif "extend_config_app(app)" in text:
            text = text.replace(
                "extend_config_app(app)",
                "extend_config_app(app)\n" + call,
            )
        changed = True

    if key == "megasena" and "register_conferencia_extras" in text:
        if "register_conferencia_extras(conferencia_bp" not in text:
            text = text.replace(
                "register_repeticao(app, 'megasena')",
                "register_repeticao(app, 'megasena')\n    register_conferencia_extras(conferencia_bp, 'megasena')",
            )
            changed = True

    if changed:
        app_py.write_text(text, encoding="utf-8")
    return changed


def patch_base_html(app_dir: Path) -> bool:
    base = app_dir / "templates" / "base.html"
    text = base.read_text(encoding="utf-8")
    orig = text

    # Dados desktop: entre dd-header Base de Dados e fechamento do nav-dropdown de Dados
    text = re.sub(
        r'(<div class="dd-header">Base de Dados</div>\s*)'
        r'(?:<a class="dd-link"[\s\S]*?)(?=\s*</div>\s*</div>\s*(?:<!-- Análise|<div class="nav-item-wrap">\s*<button class="nav-btn">\s*<i class="fas fa-crosshairs))',
        r'\1{% include \'nav_dados_block_desktop.html\' %}\n',
        text,
        count=1,
    )

    # Análise desktop
    text = re.sub(
        r'(<div class="dd-header">(?:Ferramentas de Análise|Ferramentas)</div>\s*)'
        r'(?:<a class="dd-link"[\s\S]*?)(?=\s*</div>\s*</div>\s*(?:<!-- Conferência|<!-- Desdob|<a class="nav-btn"|<div class="nav-item-wrap">\s*<button class="nav-btn">\s*<i class="fas fa-sparkles|<div class="nav-item-wrap">\s*<button class="nav-btn">\s*<i class="fas fa-bolt|{% include \'cc_nav_desktop))',
        r'\1{% include \'nav_analise_block_desktop.html\' %}\n',
        text,
        count=1,
    )

    # Desdobramentos desktop — single button or dropdown block before cc_nav
    text = re.sub(
        r'<!-- Conferência -->\s*'
        r'(?:<a class="nav-btn" href="/desdobramento/"[\s\S]*?</a>\s*'
        r'|<div class="nav-item-wrap">\s*<button class="nav-btn">\s*<i class="fas fa-sparkles[\s\S]*?</div>\s*</div>\s*)',
        '{% include \'nav_desdobramento_desktop.html\' %}\n            ',
        text,
        count=1,
    )
    text = re.sub(
        r'<a class="nav-btn" href="/desdobramento/"><i class="fas fa-sparkles[^"]*"></i> Desdobramentos</a>\s*',
        '{% include \'nav_desdobramento_desktop.html\' %}\n            ',
        text,
        count=1,
    )
    text = re.sub(
        r'<div class="nav-item-wrap">\s*<button class="nav-btn">\s*<i class="fas fa-sparkles nav-icon"></i> Desdobramentos[\s\S]*?</div>\s*</div>\s*',
        '{% include \'nav_desdobramento_desktop.html\' %}\n            ',
        text,
        count=1,
    )

    # Mega hardcoded CC → shared includes
    if "Conferência Histórica" in text and "cc_nav_desktop.html" not in text:
        text = re.sub(
            r'<div class="nav-item-wrap">\s*<button class="nav-btn">\s*<i class="fas fa-trophy nav-icon"></i> Central de Conferências[\s\S]*?</div>\s*</div>\s*',
            "{% include 'cc_nav_desktop.html' %}\n            ",
            text,
            count=1,
        )

    # Mobile Base de Dados
    text = re.sub(
        r'(<div class="mobile-group-title">Base de Dados</div>\s*)'
        r'(?:<a class="mobile-link"[\s\S]*?)(?=\s*<div class="mobile-group-title">Análise</div>)',
        r'\1{% include \'nav_dados_block_mobile.html\' %}\n        ',
        text,
        count=1,
    )

    # Mobile Análise
    text = re.sub(
        r'(<div class="mobile-group-title">Análise</div>\s*)'
        r'(?:<a class="mobile-link"[\s\S]*?)(?=\s*(?:<a class="mobile-link" href="/desdobramento/"|<div class="mobile-group-title">Central|<div class="mobile-group-title">Geradores|{% include \'cc_nav_mobile|<a class="mobile-link" href="/configuracoes/))',
        r'\1{% include \'nav_analise_block_mobile.html\' %}\n        ',
        text,
        count=1,
    )

    # Mobile desdobramento before cc
    if 'href="/des2/"' in text and "nav_desdobramento_mobile" not in text:
        text = re.sub(
            r'<a class="mobile-link" href="/desdobramento/"[\s\S]*?</a>\s*'
            r'<a class="mobile-link" href="/des2/"[\s\S]*?</a>\s*',
            "{% include 'nav_desdobramento_mobile.html' %}\n        ",
            text,
            count=1,
        )

    text = re.sub(
        r'<a class="mobile-link" href="/desdobramento/" onclick="closeMobileNav\(\)"><i class="fas fa-sparkles"></i>\s*Desdobramentos</a>\s*',
        "{% include 'nav_desdobramento_mobile.html' %}\n        ",
        text,
        count=1,
    )

    # Mobile CC mega inline
    if "Conferência Histórica" in text and "cc_nav_mobile.html" not in text:
        text = re.sub(
            r'<div class="mobile-group-title">Central de Conferências</div>\s*'
            r'(?:<a class="mobile-link"[\s\S]*?)(?=\s*<div class="mobile-group-title">Geradores|<a class="mobile-link" href="/configuracoes/)',
            "{% include 'cc_nav_mobile.html' %}\n        ",
            text,
            count=1,
        )

    # Config mobile padrão (se cc_nav presente e config ausente)
    if "cc_nav_mobile.html" in text and 'href="/configuracoes/" onclick="closeMobileNav()' not in text:
        text = text.replace(
            "{% include 'cc_nav_mobile.html' %}",
            "{% include 'cc_nav_mobile.html' %}\n        "
            '<a class="mobile-link" href="/configuracoes/" onclick="closeMobileNav()" title="Configurações">'
            '<i class="fas fa-cog"></i> Configurações</a>',
            1,
        )

    if text != orig:
        base.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    for folder, key in APPS:
        app_dir = ROOT / folder
        if not app_dir.is_dir():
            print(f"SKIP {folder}")
            continue
        a = patch_app_py(app_dir, key)
        b = patch_base_html(app_dir)
        print(f"{folder}: app={a} base={b}")


if __name__ == "__main__":
    main()
