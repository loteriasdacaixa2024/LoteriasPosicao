"""
Instala Geradores de Elite nas apps 5152–5160 (aditivo).
Executar: python install_geradores_elite.py
"""
import os
import re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

APPS = [
    ("AnalisePorPosicao-Lotofacil-Only", "lotofacil"),
    ("AnalisePorPosicao-SuperSete-Only", "supersete"),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania"),
    ("AnalisePorPosicao-Quina-Only", "quina"),
    ("AnalisePorPosicao-MegaSena-Only", "megasena"),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria"),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena"),
    ("AnalisePorPosicao-Timemania-Only", "timemania"),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diadesorte"),
]

ROUTES_PY = '''"""Geradores de Elite — blueprint aditivo (porta dedicada)."""
import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from geradores_elite.routes_factory import build_geradores_elite_blueprint

geradores_elite_bp = build_geradores_elite_blueprint("{key}")
'''

MENU_DESKTOP = """
            <div class="nav-item-wrap">
                <button class="nav-btn"><i class="fas fa-bolt" style="font-size:.82rem;opacity:.85;"></i> Geradores de Elite <i
                        class="fas fa-chevron-down caret"></i></button>
                <div class="nav-dropdown">
                    <div class="dd-header">Geradores de Elite</div>
                    <a class="dd-link" href="/geradores-elite/engine-final/"><span class="dd-icon"
                            style="background:var(--accent-light);color:var(--primary);"><i
                                class="fas fa-brain"></i></span><span class="dd-text-block"><span
                                class="dd-title">Engine Final</span><span
                                class="dd-desc">Gerador pensante com análises integradas</span></span></a>
                </div>
            </div>
"""

MENU_MOBILE = """
        <div class="mobile-group-title">Geradores de Elite</div>
        <a class="mobile-link" href="/geradores-elite/engine-final/" onclick="closeMobileNav()"><i
                class="fas fa-brain"></i> Engine Final</a>
"""

MARKER = "<!-- GE_ELITE_MENU -->"


def patch_app_py(app_dir: str) -> bool:
    path = os.path.join(app_dir, "app.py")
    if not os.path.isfile(path):
        return False
    text = open(path, encoding="utf-8").read()
    if "geradores_elite_bp" in text:
        return False
    if "from routes.geradores_elite_routes import geradores_elite_bp" not in text:
        text = text.replace(
            "def create_app():",
            "from routes.geradores_elite_routes import geradores_elite_bp\n\n\ndef create_app():",
            1,
        )
    if "register_blueprint(geradores_elite_bp)" not in text:
        m = re.search(r"(app\.register_blueprint\([^\n]+\)\n)", text)
        if m:
            insert_at = m.end()
            text = (
                text[:insert_at]
                + "    app.register_blueprint(geradores_elite_bp)\n"
                + text[insert_at:]
            )
        else:
            return False
    open(path, "w", encoding="utf-8").write(text)
    return True


def patch_base_html(app_dir: str) -> bool:
    path = os.path.join(app_dir, "templates", "base.html")
    if not os.path.isfile(path):
        return False
    text = open(path, encoding="utf-8").read()
    if MARKER in text or "/geradores-elite/engine-final/" in text:
        return False
    block = MARKER + MENU_DESKTOP + MARKER + "_DESKTOP\n"
    # Inserir antes do toggler ou Painel
    anchors = [
        '<button class="nav-toggler"',
        '<a class="nav-btn" href="/"><i class="fas fa-th-large',
        '<a class="nav-btn" href="/"><i class="fas fa-th-large nav-icon">',
    ]
    for anchor in anchors:
        if anchor in text:
            text = text.replace(anchor, block + anchor, 1)
            break
    else:
        text = text.replace("</div>\n        <button class=\"nav-toggler\"", block + "</div>\n        <button class=\"nav-toggler\"", 1)

    if "/geradores-elite/engine-final/" not in text.split("nav-mobile-panel", 1)[-1] if "nav-mobile-panel" in text else "":
        if '<div class="nav-mobile-panel" id="mobilePanel">' in text:
            text = text.replace(
                '<div class="nav-mobile-panel" id="mobilePanel">',
                '<div class="nav-mobile-panel" id="mobilePanel">' + MENU_MOBILE,
                1,
            )
    open(path, "w", encoding="utf-8").write(text)
    return True


def main():
    for folder, key in APPS:
        app_dir = os.path.join(BASE, folder)
        if not os.path.isdir(app_dir):
            print(f"[SKIP] {folder}")
            continue
        routes_path = os.path.join(app_dir, "routes", "geradores_elite_routes.py")
        os.makedirs(os.path.dirname(routes_path), exist_ok=True)
        open(routes_path, "w", encoding="utf-8").write(ROUTES_PY.format(key=key))
        a = patch_app_py(app_dir)
        b = patch_base_html(app_dir)
        print(f"[OK] {folder} ({key}) routes=1 app={a} menu={b}")


if __name__ == "__main__":
    main()
