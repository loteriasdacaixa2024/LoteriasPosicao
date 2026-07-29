#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(BASE, "AnalisePorPosicao-Lotomania-Only", "templates", "index.html")

CARD_INNER = """            <p class="text-muted mb-3" style="font-size:.85rem;">
                Importa <strong>todos</strong> os concursos faltantes da API oficial (concurso 1 até o último atual).
            </p>
            <div id="statusBanco" class="alert alert-warning py-2 small mb-3">Verificando base...</div>
            <div class="progress mb-2 d-none" id="syncProgressWrap" style="height:8px;">
                <div class="progress-bar bg-success" id="syncProgressBar" style="width:0%"></div>
            </div>
            <button class="btn w-100 fw-bold" id="btnSyncMain" style="background:var(--accent);color:#fff;"
                onclick="sincronizar()">
                <i class="fas fa-cloud-download-alt me-2"></i>Sincronizar histórico completo
            </button>
            <div id="syncLog" class="mt-3" style="font-size:.8rem;"></div>"""

APPS = [
    ("AnalisePorPosicao-Lotofacil-Only", "carregarDados"),
    ("AnalisePorPosicao-MaisMilionaria-Only", "carregarUltimos"),
    ("AnalisePorPosicao-DuplaSena-Only", "carregarUltimos"),
    ("AnalisePorPosicao-Timemania-Only", "carregarUltimos"),
    ("AnalisePorPosicao--DiaDeSorte-Only", "carregarUltimos"),
]

ref = open(REF, encoding="utf-8").read()
m = re.search(
    r"(    async function carregarStatusBanco\(\) \{.*?    async function carregarStats\(\) \{.*?\n    \})",
    ref,
    re.DOTALL,
)
if not m:
    raise SystemExit("Bloco de referência não encontrado em Lotomania")
SYNC_CORE = m.group(1).replace("await carregarUltimos();", "await __ULTIMOS__();")


def patch(path, ultimos_fn):
    text = open(path, encoding="utf-8").read()
    text2, n = re.subn(
        r"<h5><i class=\"fas fa-satellite-dish me-2\" style=\"color:var\(--accent\);\"></i>Base de Dados</h5>.*?"
        r"<div id=\"syncLog\" class=\"mt-3\" style=\"font-size:\.8rem;\"></div>",
        '<h5><i class="fas fa-satellite-dish me-2" style="color:var(--accent);"></i>Base de Dados</h5>\n' + CARD_INNER,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        return False, "card"

    core = SYNC_CORE.replace("__ULTIMOS__()", f"{ultimos_fn}()")
    text3, n2 = re.subn(
        r"    async function (?:carregarStatusBanco|sincronizar)\(\).*?"
        r"    async function carregarStats\(\) \{.*?\n    \}",
        core,
        text2,
        count=1,
        flags=re.DOTALL,
    )
    if n2 != 1:
        return False, "scripts"

    text4, n3 = re.subn(
        r"document\.addEventListener\('DOMContentLoaded'.*?\}\);",
        "document.addEventListener('DOMContentLoaded', async () => {\n"
        "        await carregarStatusBanco();\n"
        "        await carregarStats();\n"
        f"        await {ultimos_fn}();\n"
        "    });",
        text3,
        count=1,
        flags=re.DOTALL,
    )
    if n3 != 1:
        return False, "dom"

    open(path, "w", encoding="utf-8").write(text4)
    return True, "ok"


def main():
    print("Lotomania já é referência.")
    for pasta, fn in APPS:
        path = os.path.join(BASE, pasta, "templates", "index.html")
        ok, msg = patch(path, fn)
        print(f"{pasta}: {msg}")


if __name__ == "__main__":
    main()
