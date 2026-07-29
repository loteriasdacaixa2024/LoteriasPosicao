#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aplica melhorias: nav Painel Geral, volantes, Dia de Sorte desdobramento padrão Mega."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APPS_NAV = [
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

VOLANTE_CRIAR_STD = r'''    function criarVolanteOficial() {
        const volante = document.getElementById('volante-grid');
        volante.innerHTML = '';
        const linhas = typeof VOLANTE_LINHAS !== 'undefined'
            ? VOLANTE_LINHAS
            : Math.ceil((MAX_DEZENA - (typeof MIN_DEZENA !== 'undefined' ? MIN_DEZENA : 1) + 1) / 10);
        const minD = typeof MIN_DEZENA !== 'undefined' ? MIN_DEZENA : 1;

        if (minD === 0 && MAX_DEZENA >= 99) {
            for (let col = 0; col <= 9; col++) {
                const lbl = document.createElement('div');
                lbl.className = 'col-label-item';
                lbl.style.gridRow = '1';
                lbl.style.gridColumn = (col + 3).toString();
                lbl.textContent = col;
                volante.appendChild(lbl);
            }
            const hLine = document.createElement('div');
            hLine.className = 'volante-line-horizontal';
            hLine.style.gridRow = '2';
            hLine.style.gridColumn = '3 / span 10';
            volante.appendChild(hLine);
            for (let row = 0; row <= 9; row++) {
                const lbl = document.createElement('div');
                lbl.className = 'row-label-item';
                lbl.style.gridRow = (row + 3).toString();
                lbl.style.gridColumn = '1';
                lbl.textContent = row;
                volante.appendChild(lbl);
            }
            const vLine = document.createElement('div');
            vLine.className = 'volante-line-vertical';
            vLine.style.gridRow = '3 / span 10';
            vLine.style.gridColumn = '2';
            volante.appendChild(vLine);
            for (let linha = 0; linha < 10; linha++) {
                for (let col = 0; col < 10; col++) {
                    const numero = linha * 10 + col;
                    const celula = document.createElement('div');
                    celula.className = 'volante-celula';
                    celula.style.gridRow = (linha + 3).toString();
                    celula.style.gridColumn = (col + 3).toString();
                    const jaSaiuNoCiclo = dezenasSorteadasCiclo.includes(numero);
                    if (jaSaiuNoCiclo) celula.classList.add('cycle-drawn');
                    celula.textContent = numero.toString().padStart(2, '0');
                    celula.dataset.numero = numero;
                    if (jaSaiuNoCiclo) {
                        const check = document.createElement('span');
                        check.className = 'cycle-check';
                        check.innerHTML = '✓';
                        celula.appendChild(check);
                    }
                    celula.addEventListener('click', () => toggleNumeroLocal(numero, celula));
                    volante.appendChild(celula);
                }
            }
            return;
        }

        for (let col = 1; col <= 10; col++) {
            const lbl = document.createElement('div');
            lbl.className = 'col-label-item';
            lbl.style.gridRow = '1';
            lbl.style.gridColumn = (col + 2).toString();
            lbl.textContent = col;
            volante.appendChild(lbl);
        }
        const hLine = document.createElement('div');
        hLine.className = 'volante-line-horizontal';
        hLine.style.gridRow = '2';
        hLine.style.gridColumn = '3 / span 10';
        volante.appendChild(hLine);
        for (let row = 1; row <= linhas; row++) {
            const lbl = document.createElement('div');
            lbl.className = 'row-label-item';
            lbl.style.gridRow = (row + 2).toString();
            lbl.style.gridColumn = '1';
            lbl.textContent = row;
            volante.appendChild(lbl);
        }
        const vLine = document.createElement('div');
        vLine.className = 'volante-line-vertical';
        vLine.style.gridRow = '3 / span ' + linhas;
        vLine.style.gridColumn = '2';
        volante.appendChild(vLine);
        for (let linha = 0; linha < linhas; linha++) {
            for (let col = 1; col <= 10; col++) {
                const numero = linha * 10 + col;
                if (numero < minD || numero > MAX_DEZENA) continue;
                const celula = document.createElement('div');
                celula.className = 'volante-celula';
                celula.style.gridRow = (linha + 3).toString();
                celula.style.gridColumn = (col + 2).toString();
                const jaSaiuNoCiclo = dezenasSorteadasCiclo.includes(numero);
                if (jaSaiuNoCiclo) celula.classList.add('cycle-drawn');
                celula.textContent = numero.toString().padStart(2, '0');
                celula.dataset.numero = numero;
                if (jaSaiuNoCiclo) {
                    const check = document.createElement('span');
                    check.className = 'cycle-check';
                    check.innerHTML = '✓';
                    celula.appendChild(check);
                }
                celula.addEventListener('click', () => toggleNumeroLocal(numero, celula));
                volante.appendChild(celula);
            }
        }
    }'''

VOLANTE_EXTRA = {
    "AnalisePorPosicao-Lotomania-Only": "const MIN_DEZENA = 0;\n    const VOLANTE_LINHAS = 10;",
    "AnalisePorPosicao-Lotofacil-Only": "const MIN_DEZENA = 1;\n    const VOLANTE_LINHAS = 3;",
    "AnalisePorPosicao-Quina-Only": "const MIN_DEZENA = 1;\n    const VOLANTE_LINHAS = 8;",
    "AnalisePorPosicao-Timemania-Only": "const MIN_DEZENA = 1;\n    const VOLANTE_LINHAS = 8;",
    "AnalisePorPosicao-DuplaSena-Only": "const MIN_DEZENA = 1;\n    const VOLANTE_LINHAS = 5;",
    "AnalisePorPosicao-MaisMilionaria-Only": "const MIN_DEZENA = 1;\n    const VOLANTE_LINHAS = 5;",
}


def remove_painel_geral(text: str) -> str:
    text = re.sub(
        r"\s*<!-- Dashboard -->\s*\n\s*<a class=\"nav-btn\" href=\"/[^\"]*\"[^>]*>[\s\S]*?Painel Geral\s*\n\s*</a>\s*\n",
        "\n",
        text,
        count=1,
    )
    text = re.sub(
        r"\s*<a class=\"nav-btn\" href=\"/\"[^>]*>[\s\S]*?Painel Geral\s*</a>\s*\n",
        "\n",
        text,
    )
    text = re.sub(
        r"\s*<a class=\"mobile-link\" href=\"/\?painel=1\"[^>]*>[\s\S]*?Painel Geral\s*</a>\s*\n",
        "\n",
        text,
    )
    text = re.sub(
        r"\s*<a class=\"mobile-link\" href=\"/\" onclick=\"closeMobileNav\(\)\">[\s\S]*?Painel Geral\s*</a>\s*\n",
        "\n",
        text,
        count=1,
    )
    return text


def patch_volante(path: Path):
    text = path.read_text(encoding="utf-8")
    if "function criarVolanteOficial()" not in text:
        return
    app = path.parts[-3] if len(path.parts) > 3 else ""
    extra = VOLANTE_EXTRA.get(app, "const MIN_DEZENA = 1;")
    if "const MIN_DEZENA" not in text:
        text = text.replace(
            "const SUPORTA_TREVO",
            extra + "\n    const SUPORTA_TREVO",
            1,
        )
    text = re.sub(
        r"function criarVolanteOficial\(\) \{[\s\S]*?\n    \}\n\n    function toggleNumeroLocal",
        VOLANTE_CRIAR_STD + "\n\n    function toggleNumeroLocal",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def setup_diasorte_desdobramento():
    src_tpl = ROOT / "AnalisePorPosicao-DuplaSena-Only" / "templates" / "desdobramento.html"
    dst_tpl = ROOT / "AnalisePorPosicao--DiaDeSorte-Only" / "templates" / "desdobramento.html"
    src_model = ROOT / "AnalisePorPosicao-DuplaSena-Only" / "models" / "desdobramento.py"
    dst_model = ROOT / "AnalisePorPosicao--DiaDeSorte-Only" / "models" / "desdobramento.py"
    shutil.copy2(src_model, dst_model)

    tpl = src_tpl.read_text(encoding="utf-8")
    tpl = tpl.replace("Dupla Sena", "Dia de Sorte")
    tpl = tpl.replace("const MAX_DEZENA = 50;", "const MAX_DEZENA = 31;\n    const MIN_DEZENA = 1;\n    const VOLANTE_LINHAS = 4;")
    dst_tpl.write_text(tpl, encoding="utf-8")

    svc = '''import os
import sys

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)

from _shared.desdobramento_service_factory import build_desdobramento_service
from services.analise_diadesorte_service import AnaliseDiaDeSorteService

DesdobramentoDiaDeSorteService = build_desdobramento_service(
    AnaliseDiaDeSorteService,
    max_dezena=31,
    suporta_trevo=False,
)
'''
    (ROOT / "AnalisePorPosicao--DiaDeSorte-Only" / "services" / "desdobramento_service.py").write_text(
        svc, encoding="utf-8"
    )

    routes = (ROOT / "AnalisePorPosicao-DuplaSena-Only" / "routes" / "desdobramento_routes.py").read_text(
        encoding="utf-8"
    )
    routes = routes.replace("Dupla Sena", "Dia de Sorte")
    routes = routes.replace("CicloDuplaSenaService", "CicloDiaDeSorteService")
    routes = routes.replace("DesdobramentoDuplaSenaService", "DesdobramentoDiaDeSorteService")
    routes = routes.replace("MAX_DEZENA = 50", "MAX_DEZENA = 31")
    (ROOT / "AnalisePorPosicao--DiaDeSorte-Only" / "routes" / "desdobramento_routes.py").write_text(
        routes, encoding="utf-8"
    )

    app_py = ROOT / "AnalisePorPosicao--DiaDeSorte-Only" / "app.py"
    txt = app_py.read_text(encoding="utf-8")
    if "import models.desdobramento" not in txt:
        txt = txt.replace("db.create_all()", "        import models.desdobramento\n        db.create_all()")
        app_py.write_text(txt, encoding="utf-8")


def main():
    for app in APPS_NAV:
        base = ROOT / app / "templates" / "base.html"
        if base.is_file():
            t = remove_painel_geral(base.read_text(encoding="utf-8"))
            base.write_text(t, encoding="utf-8")
            print(f"[nav] {app}")

    for app in list(VOLANTE_EXTRA.keys()) + ["AnalisePorPosicao-Lotofacil-Only"]:
        p = ROOT / app / "templates" / "desdobramento.html"
        if p.is_file():
            patch_volante(p)
            print(f"[volante] {app}")

    setup_diasorte_desdobramento()
    print("[ok] Dia de Sorte desdobramento padronizado")


if __name__ == "__main__":
    main()
