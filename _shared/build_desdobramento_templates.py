#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
MEGA = os.path.join(BASE, "..", "AnalisePorPosicao-MegaSena-Only", "templates", "desdobramento.html")

TREVO_PANEL = """
</div>
<div class="tab-pane fade" id="painel-trevos">
<div class="card border-0 shadow-sm mb-4">
<div class="card-body text-center py-4">
<h3 class="fw-bold mb-2">Fechamento de Trevos</h3>
<p class="text-muted small mb-3">Escolha 4 trevos (1 a 6). O sistema gera as 6 combinações de 2 trevos — cobertura se acertar 2 dos 4.</p>
<div class="d-flex justify-content-center gap-2 flex-wrap mb-3" id="volante-trevos"></div>
<div class="mb-3"><span class="fw-bold" id="contador-trevos">0</span> / 4 trevos</div>
<input type="text" id="nome-trevo" class="form-control mb-3 mx-auto" style="max-width:320px" placeholder="Nome do fechamento de trevos">
<button class="btn btn-primary fw-bold" id="btn-gerar-trevos" disabled>Gerar 6 apostas de trevos</button>
<div id="resultado-trevos" class="mt-4 text-start mx-auto" style="max-width:480px;display:none"></div>
</div>
</div>
</div>
</div>
"""

TREVO_JS = """
<script>
(function trevoModule() {
    if (typeof SUPORTA_TREVO === 'undefined' || !SUPORTA_TREVO) return;
    let trevosSel = [];
    const grid = document.getElementById('volante-trevos');
    if (!grid) return;
    for (let t = 1; t <= 6; t++) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-outline-primary rounded-circle fw-bold';
        b.style.cssText = 'width:52px;height:52px';
        b.textContent = t;
        b.onclick = () => {
            if (b.classList.contains('active')) {
                b.classList.remove('active');
                trevosSel = trevosSel.filter(x => x !== t);
            } else if (trevosSel.length < 4) {
                b.classList.add('active');
                trevosSel.push(t);
            } else Swal.fire('Aviso', 'Máximo 4 trevos.', 'warning');
            document.getElementById('contador-trevos').textContent = trevosSel.length;
            document.getElementById('btn-gerar-trevos').disabled = trevosSel.length !== 4;
        };
        grid.appendChild(b);
    }
    document.getElementById('btn-gerar-trevos').addEventListener('click', async () => {
        const nome = document.getElementById('nome-trevo').value || 'Trevos';
        const r = await fetch('/desdobramento/api/desdobrar-trevos', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ trevos: trevosSel.sort((a,b)=>a-b), nome })
        });
        const data = await r.json();
        if (data.status !== 'success') { Swal.fire('Erro', data.message || 'Falha', 'error'); return; }
        const box = document.getElementById('resultado-trevos');
        box.style.display = 'block';
        box.innerHTML = '<h6 class="fw-bold">6 pares de trevos</h6>' + data.apostas.map((ap,i) =>
            `<div class="border rounded p-2 mb-1">Aposta ${i+1}: Trevo ${ap[0]} + Trevo ${ap[1]}</div>`).join('');
        Swal.fire('OK', `${data.total_apostas} apostas de trevos salvas.`, 'success');
        if (typeof atualizarHistorico === 'function') atualizarHistorico();
    });
})();
</script>
"""


def patch_for_50(html, nome, mx=50, linhas=5, trevo=False):
    t = html
    t = t.replace("Mega-Sena", nome).replace("Mega Sena", nome)
    t = t.replace("var(--mega-green)", "var(--primary)")
    t = t.replace("var(--mega-dark)", "var(--primary-dark, #1a1a2e)")
    t = t.replace("var(--mega-light)", "var(--accent)")
    t = t.replace("60 dezenas", f"{mx} dezenas")
    t = t.replace("/ 60 *", f"/ {mx} *")
    t = t.replace("de 60", f"de {mx}")
    t = re.sub(
        r"for \(let linha = 0; linha < 6; linha\+\+\)",
        f"for (let linha = 0; linha < {linhas}; linha++)",
        t,
    )
    t = re.sub(
        r"for \(let row = 1; row <= 6; row\+\+\)",
        f"for (let row = 1; row <= {linhas}; row++)",
        t,
    )
    t = t.replace("vLine.style.gridRow = '3 / span 6'", f"vLine.style.gridRow = '3 / span {linhas}'")
    t = t.replace("num > 60", f"num > {mx}")
    t = t.replace("01 e 60", f"01 e {mx:02d}")
    old = """                const numero = linha * 10 + col;
                const celula = document.createElement('div');"""
    new = f"""                const numero = linha * 10 + col;
                if (numero > {mx}) continue;
                const celula = document.createElement('div');"""
    t = t.replace(old, new)
    inject = f"const MAX_DEZENA = {mx};\n    const SUPORTA_TREVO = {'true' if trevo else 'false'};\n    "
    t = t.replace("    const dezenasSorteadasCiclo", inject + "const dezenasSorteadasCiclo", 1)
    if trevo:
        tabs = (
            '<ul class="nav nav-tabs mb-4 justify-content-center" id="desdTabs">'
            '<li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" '
            'data-bs-target="#painel-dezenas" type="button">Dezenas principais</button></li>'
            '<li class="nav-item"><button class="nav-link" data-bs-toggle="tab" '
            'data-bs-target="#painel-trevos" type="button">Trevos</button></li></ul>'
            '<div class="tab-content"><div class="tab-pane fade show active" id="painel-dezenas">'
        )
        t = t.replace("<!-- HEADER PRINCIPAL -->", tabs + "\n<!-- HEADER PRINCIPAL -->")
        if "{% endblock %}" in t:
            t = t.replace("{% endblock %}", TREVO_PANEL + TREVO_JS + "\n{% endblock %}", 1)
        else:
            t += TREVO_PANEL + TREVO_JS
    return t


def main():
    html = open(MEGA, encoding="utf-8").read()
    targets = [
        (os.path.join(BASE, "..", "AnalisePorPosicao-MaisMilionaria-Only", "templates", "desdobramento.html"), "+Milionária", True),
        (os.path.join(BASE, "..", "AnalisePorPosicao-DuplaSena-Only", "templates", "desdobramento.html"), "Dupla Sena", False),
    ]
    for dest, nome, trevo in targets:
        out = patch_for_50(html, nome, trevo=trevo)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(out)
        print("OK", dest)

    src = os.path.join(BASE, "..", "AnalisePorPosicao--DiaDeSorte-Only", "templates", "gerador_especial.html")
    dst = os.path.join(BASE, "..", "AnalisePorPosicao--DiaDeSorte-Only", "templates", "desdobramento.html")
    ds = open(src, encoding="utf-8").read()
    ds = ds.replace("/gerador-especial/", "/desdobramento/")
    ds = ds.replace("Gerador Especial", "Desdobramento Inteligente")
    ds = ds.replace("gerador especial", "desdobramento", 1)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(ds)
    print("OK", dst)


if __name__ == "__main__":
    main()
