# -*- coding: utf-8 -*-
"""
Instala Análise por Posição + Gerador nas apps 5152–5160.
Executar: python install_posicao_analise.py
"""
from __future__ import annotations

import os
import re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

APPS = [
    ("AnalisePorPosicao-SuperSete-Only", "supersete"),
    ("AnalisePorPosicao-Lotofacil-Only", "lotofacil"),
    ("AnalisePorPosicao-Timemania-Only", "timemania"),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria"),
    ("AnalisePorPosicao-MegaSena-Only", "megasena"),
    ("AnalisePorPosicao-Quina-Only", "quina"),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena"),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania"),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diadesorte"),
]

SERVICE_PY = '''# -*- coding: utf-8 -*-
"""Análise por Posição — delegação ao módulo compartilhado."""
import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from posicao_analise.service_factory import make_service

AnalisePosicaoService = make_service("{key}")
'''

WIRE_MARKER = "# POSICAO_ANALISE_WIRED"
WIRE_BLOCK = '''
{marker}
from posicao_analise.app_integration import wire_posicao_analise
wire_posicao_analise(analise_bp, "{key}")
'''

APP_IMPORT = "from posicao_analise.app_integration import extend_posicao_app"
APP_CALL = "    extend_posicao_app(app, '{key}')"


def _write_service(app_dir: str, key: str) -> None:
    path = os.path.join(app_dir, "services", "analise_posicao_service.py")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(SERVICE_PY.format(key=key))


def _patch_analise_routes(app_dir: str, key: str) -> bool:
    path = os.path.join(app_dir, "routes", "analise_routes.py")
    if not os.path.isfile(path):
        return False
    text = open(path, encoding="utf-8").read()
    if WIRE_MARKER in text:
        return False

    # Remove rotas legadas duplicadas (Dia de Sorte)
    text = re.sub(
        r"\n@analise_bp\.route\(\"/por-posicao/\"[\s\S]*?"
        r"@analise_bp\.route\(\"/api/por-posicao/<int:concurso>\"[\s\S]*?"
        r"return jsonify\(\{\"status\": \"error\", \"message\": str\(e\)\}\), 500\n",
        "\n",
        text,
        count=1,
    )

    block = WIRE_BLOCK.format(marker=WIRE_MARKER, key=key)
    if "_SHARED" not in text:
        insert = (
            'import os\nimport sys\n\n'
            '_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))\n'
            'if _SHARED not in sys.path:\n'
            '    sys.path.insert(0, _SHARED)\n\n'
        )
        text = insert + text
    text = text.rstrip() + "\n" + block
    open(path, "w", encoding="utf-8").write(text)
    return True


def _patch_app_py(app_dir: str, key: str) -> bool:
    path = os.path.join(app_dir, "app.py")
    if not os.path.isfile(path):
        return False
    text = open(path, encoding="utf-8").read()
    changed = False

    if APP_IMPORT not in text:
        anchor = "from menu.app_integration import extend_nav_app"
        if anchor in text:
            text = text.replace(
                anchor,
                anchor + "\n" + APP_IMPORT,
                1,
            )
            changed = True
        elif "def create_app():" in text:
            text = text.replace(
                "def create_app():",
                APP_IMPORT + "\n\n\ndef create_app():",
                1,
            )
            changed = True

    call = APP_CALL.format(key=key)
    if call.strip() not in text:
        m = re.search(r"(extend_nav_app\(app, '[^']+'\)\n)", text)
        if m:
            text = text[: m.end()] + call + "\n" + text[m.end() :]
            changed = True

    if changed:
        open(path, "w", encoding="utf-8").write(text)
    return changed


def main() -> None:
    for folder, key in APPS:
        app_dir = os.path.join(BASE, folder)
        if not os.path.isdir(app_dir):
            print(f"[SKIP] {folder}")
            continue
        _write_service(app_dir, key)
        r = _patch_analise_routes(app_dir, key)
        a = _patch_app_py(app_dir, key)
        print(f"[OK] {folder} ({key}) service=1 routes={r} app={a}")


if __name__ == "__main__":
    main()
