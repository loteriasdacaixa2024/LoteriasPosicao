#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    {
        "app_dir": "AnalisePorPosicao-Lotofacil-Only",
        "nome": "Lotofácil",
        "slug": "lotofacil",
        "max_dezena": 25,
        "analise_import": "services.analise_lotofacil_service",
        "analise_class": "AnaliseLotofacilService",
        "service_class": "DesdobramentoLotofacilService",
        "ciclo_class": "CicloLotofacilService",
        "sorteio_import": "models.sorteio_lotofacil",
        "sorteio_class": "SorteioLotofacil",
        "dezenas_method": "dezenas",
    },
    {
        "app_dir": "AnalisePorPosicao-Lotomania-Only",
        "nome": "Lotomania",
        "slug": "lotomania",
        "max_dezena": 100,
        "analise_import": "services.analise_lotomania_service",
        "analise_class": "AnaliseLotomaniaService",
        "service_class": "DesdobramentoLotomaniaService",
        "ciclo_class": "CicloLotomaniaService",
        "sorteio_import": "models.sorteio_lotomania",
        "sorteio_class": "SorteioLotomania",
        "dezenas_method": "dezenas_lista",
    },
    {
        "app_dir": "AnalisePorPosicao-Quina-Only",
        "nome": "Quina",
        "slug": "quina",
        "max_dezena": 80,
        "analise_import": "services.analise_quina_service",
        "analise_class": "AnaliseQuinaService",
        "service_class": "DesdobramentoQuinaService",
        "ciclo_class": "CicloQuinaService",
        "sorteio_import": "models.sorteio_quina",
        "sorteio_class": "SorteioQuina",
        "dezenas_method": "dezenas_lista",
    },
    {
        "app_dir": "AnalisePorPosicao-Timemania-Only",
        "nome": "Timemania",
        "slug": "timemania",
        "max_dezena": 80,
        "analise_import": "services.analise_timemania_service",
        "analise_class": "AnaliseTimemaniaSService",
        "service_class": "DesdobramentoTimemaniaService",
        "ciclo_class": "CicloTimemaniaService",
        "sorteio_import": "models.sorteio_timemania",
        "sorteio_class": "SorteioTimemania",
        "dezenas_method": "dezenas_lista",
    },
]

SUPERSETE = {
    "app_dir": "AnalisePorPosicao-SuperSete-Only",
    "nome": "Super Sete",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_menu_plural(path_base: Path):
    txt = read(path_base)
    if '/desdobramento/' not in txt:
        txt = txt.replace(
            "{% include 'cc_nav_desktop.html' %}",
            '<a class="nav-btn" href="/desdobramento/"><i class="fas fa-sparkles nav-icon"></i> Desdobramentos</a>\n            {% include \'cc_nav_desktop.html\' %}',
        )
        txt = txt.replace(
            "{% include 'cc_nav_mobile.html' %}",
            '<a class="mobile-link" href="/desdobramento/" onclick="closeMobileNav()"><i class="fas fa-sparkles"></i> Desdobramentos</a>\n        {% include \'cc_nav_mobile.html\' %}',
        )
    else:
        txt = txt.replace("> Desdobramento<", "> Desdobramentos<")
        txt = txt.replace(">Desdobramento<", ">Desdobramentos<")
        txt = txt.replace("Desdobramento Inteligente</a>", "Desdobramentos</a>")
        txt = txt.replace('mobile-group-title">Desdobramento<', 'mobile-group-title">Desdobramentos<')
    write(path_base, txt)


def patch_app(app_path: Path, has_model: bool):
    txt = read(app_path)
    if "from routes.desdobramento_routes import desdobramento_bp" not in txt:
        txt = txt.replace(
            "from routes.modelos_routes import modelos_bp\n",
            "from routes.modelos_routes import modelos_bp\nfrom routes.desdobramento_routes import desdobramento_bp\n",
        )
    if "app.register_blueprint(desdobramento_bp, url_prefix='/desdobramento')" not in txt:
        txt = txt.replace(
            "app.register_blueprint(modelos_bp,",
            "app.register_blueprint(modelos_bp,",
        )
        txt = txt.replace(
            "app.register_blueprint(geradores_elite_bp)",
            "app.register_blueprint(desdobramento_bp, url_prefix='/desdobramento')\n    app.register_blueprint(geradores_elite_bp)",
        )
    if has_model and "import models.desdobramento" not in txt:
        txt = txt.replace("db.create_all()", "import models.desdobramento\n        db.create_all()")
    write(app_path, txt)


def build_ciclo_service(cfg: dict) -> str:
    return f"""from models.shared import db
from {cfg["sorteio_import"]} import {cfg["sorteio_class"]}

TOTAL = {cfg["max_dezena"]}


class {cfg["ciclo_class"]}:
    @staticmethod
    def obter_ciclo_atual():
        try:
            sorteios = db.session.query({cfg["sorteio_class"]}).order_by(
                {cfg["sorteio_class"]}.concurso.asc()
            ).all()
        except Exception:
            sorteios = []
        ciclo_num = 1
        dezenas_sorteadas = set()
        concursos_no_ciclo = 0
        for s in sorteios:
            dezenas = getattr(s, "{cfg["dezenas_method"]}")()
            dezenas_sorteadas.update(dezenas)
            concursos_no_ciclo += 1
            if len(dezenas_sorteadas) >= TOTAL:
                ciclo_num += 1
                dezenas_sorteadas = set()
                concursos_no_ciclo = 0
        base = 0 if "{cfg["slug"]}" == "lotomania" else 1
        faltantes = sorted(set(range(base, TOTAL + 1)) - dezenas_sorteadas)
        return {{
            "ciclo_num": ciclo_num,
            "dezenas_sorteadas": sorted(dezenas_sorteadas),
            "dezenas_faltantes": faltantes,
            "total_sorteadas": len(dezenas_sorteadas),
            "total_faltantes": len(faltantes),
            "concursos_no_ciclo": concursos_no_ciclo,
        }}
"""


def build_service(cfg: dict) -> str:
    return f"""import os
import sys

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)

from _shared.desdobramento_service_factory import build_desdobramento_service
from {cfg["analise_import"]} import {cfg["analise_class"]}

{cfg["service_class"]} = build_desdobramento_service(
    {cfg["analise_class"]},
    max_dezena={cfg["max_dezena"]},
    suporta_trevo=False,
)
"""


def build_routes(cfg: dict) -> str:
    low = cfg["max_dezena"]
    return f"""from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from services.ciclo_service import {cfg["ciclo_class"]}
from services.desdobramento_service import {cfg["service_class"]}

desdobramento_bp = Blueprint('desdobramento', __name__)
MAX_DEZENA = {cfg["max_dezena"]}
MIN_DEZENA = {0 if cfg["slug"] == "lotomania" else 1}


@desdobramento_bp.route('/')
def desdobramento_index():
    try:
        ciclo_info = {cfg["ciclo_class"]}.obter_ciclo_atual()
    except Exception as e:
        print(f"Erro ao obter ciclo: {{e}}")
        ciclo_info = {{
            "ciclo_num": 1,
            "dezenas_sorteadas": [],
            "dezenas_faltantes": list(range(MIN_DEZENA, MAX_DEZENA + 1)),
            "total_sorteadas": 0,
            "total_faltantes": MAX_DEZENA,
            "concursos_no_ciclo": 0,
        }}
    return render_template(
        'desdobramento.html',
        ciclo=ciclo_info,
        modalidade='{cfg["nome"]}',
        max_dezena=MAX_DEZENA,
        suporta_trevo=False,
    )


@desdobramento_bp.route('/api/ciclo', methods=['GET'])
def api_ciclo():
    try:
        return jsonify({{"status": "success", **{cfg["ciclo_class"]}.obter_ciclo_atual()}})
    except Exception as e:
        return jsonify({{"status": "error", "message": str(e)}}), 500


@desdobramento_bp.route('/api/sugestoes-colunas', methods=['GET'])
def api_sugestoes_colunas():
    try:
        return jsonify({{"status": "success", "sugestoes": {cfg["service_class"]}.obter_sugestoes_colunas()}})
    except Exception:
        fallback = list(range(max(MIN_DEZENA, 1), min(MAX_DEZENA, 16) + 1))
        return jsonify({{"status": "success", "sugestoes": {{
            "quentes": {{"colunas": [1, 2, 3, 4], "dezenas": fallback}},
            "atrasadas": {{"colunas": [5, 6, 7, 8], "dezenas": fallback}},
            "balanceadas": {{"colunas": [1, 2, 5, 6], "dezenas": fallback}},
        }}}})


def _validar_colunas(numeros):
    colunas = {{}}
    for n in numeros:
        col = 10 if n % 10 == 0 else n % 10
        colunas.setdefault(col, []).append(n)
    if len(colunas) != 4:
        return "Deve selecionar dezenas de exatamente 4 colunas."
    for col, dezenas in colunas.items():
        if len(dezenas) != 4:
            return f"A coluna {{col}} deve conter exatamente 4 dezenas."
    return None


@desdobramento_bp.route('/api/desdobrar', methods=['POST'])
def api_desdobrar():
    try:
        data = request.get_json() or {{}}
        numeros = data.get('numeros', [])
        nome = data.get('nome', f"Desdobramento {{datetime.now().strftime('%d/%m/%Y %H:%M')}}")
        modo = data.get('modo', 'bronze').lower()
        if len(numeros) != 16:
            return jsonify({{"status": "error", "message": "Deve fornecer exatamente 16 números."}}), 400
        for num in numeros:
            if num < MIN_DEZENA or num > MAX_DEZENA:
                return jsonify({{"status": "error", "message": f"Os números devem estar entre {{MIN_DEZENA:02d}} e {{MAX_DEZENA:02d}}."}}), 400
        err = _validar_colunas(numeros)
        if err:
            return jsonify({{"status": "error", "message": err}}), 400
        id_salvo = {cfg["service_class"]}.salvar_desdobramento(nome, numeros, modo)
        detalhes = {cfg["service_class"]}.buscar_por_id(id_salvo)
        if not detalhes:
            return jsonify({{"status": "error", "message": "Erro ao recuperar desdobramento salvo."}}), 500
        return jsonify({{"status": "success", "sucesso": True, **detalhes}})
    except Exception as e:
        return jsonify({{"status": "error", "message": str(e)}}), 500


@desdobramento_bp.route('/api/desdobramentos', methods=['GET'])
def api_listar_desdobramentos():
    try:
        tipo = request.args.get('tipo')
        return jsonify({{"status": "success", "desdobramentos": {cfg["service_class"]}.listar_todos(tipo)}})
    except Exception as e:
        return jsonify({{"status": "error", "message": str(e)}}), 500


@desdobramento_bp.route('/api/desdobramento/<int:id>', methods=['GET'])
def api_buscar_desdobramento(id):
    try:
        detalhes = {cfg["service_class"]}.buscar_por_id(id)
        if not detalhes:
            return jsonify({{"status": "error", "message": "Desdobramento não encontrado."}}), 404
        return jsonify({{"status": "success", "desdobramento": detalhes}})
    except Exception as e:
        return jsonify({{"status": "error", "message": str(e)}}), 500


@desdobramento_bp.route('/api/desdobramento/<int:id>', methods=['DELETE'])
def api_deletar_desdobramento(id):
    try:
        if not {cfg["service_class"]}.deletar_por_id(id):
            return jsonify({{"status": "error", "message": "Desdobramento não encontrado."}}), 404
        return jsonify({{"status": "success", "sucesso": True}})
    except Exception as e:
        return jsonify({{"status": "error", "message": str(e)}}), 500
"""


def build_supersete_routes() -> str:
    return """from flask import Blueprint, jsonify, render_template, request
from itertools import product

desdobramento_bp = Blueprint('desdobramento', __name__)


@desdobramento_bp.route('/')
def desdobramento_index():
    return render_template('desdobramento.html', modalidade='Super Sete')


@desdobramento_bp.route('/api/gerar', methods=['POST'])
def api_gerar():
    data = request.get_json() or {}
    colunas = data.get('colunas', [])
    if len(colunas) != 7:
        return jsonify({"status": "error", "message": "Informe 7 colunas."}), 400
    listas = []
    for i, c in enumerate(colunas, 1):
        vals = sorted({int(v) for v in c if str(v).isdigit() and 0 <= int(v) <= 9})
        if not vals:
            return jsonify({"status": "error", "message": f"Coluna {i} sem dígitos válidos (0-9)."}), 400
        if len(vals) > 4:
            return jsonify({"status": "error", "message": f"Coluna {i} excedeu 4 dígitos (limite de segurança)."}), 400
        listas.append(vals)
    apostas = [list(p) for p in product(*listas)]
    if len(apostas) > 4096:
        return jsonify({"status": "error", "message": "Combinações acima do limite (4096). Reduza os dígitos por coluna."}), 400
    return jsonify({"status": "success", "total": len(apostas), "apostas": apostas})
"""


def build_supersete_template() -> str:
    return """{% extends 'base.html' %}
{% block content %}
<div class="container-fluid py-3">
  <div class="card shadow-sm border-0 mb-3">
    <div class="card-body">
      <h4 class="fw-bold mb-2">Desdobramentos — Super Sete</h4>
      <p class="text-muted mb-0">Selecione os dígitos por coluna (0-9). O sistema gera as combinações possíveis respeitando as regras por coluna.</p>
    </div>
  </div>
  <div class="card shadow-sm border-0 mb-3">
    <div class="card-body">
      <div class="row g-2" id="cols"></div>
      <button class="btn btn-success mt-3" id="btn-gerar">Gerar combinações</button>
      <div class="small text-muted mt-2">Limite de segurança: até 4 dígitos por coluna e 4096 combinações.</div>
    </div>
  </div>
  <div class="card shadow-sm border-0">
    <div class="card-body">
      <h6 class="fw-bold mb-2">Resultado</h6>
      <div id="total" class="mb-2 text-success fw-bold"></div>
      <pre id="out" style="max-height:340px;overflow:auto;"></pre>
    </div>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script>
const root = document.getElementById('cols');
for (let c = 1; c <= 7; c++) {
  const wrap = document.createElement('div');
  wrap.className = 'col-md-6 col-lg-3';
  wrap.innerHTML = `<label class="form-label fw-bold">Coluna ${c}</label><input class="form-control" id="col-${c}" placeholder="Ex: 1,4,7">`;
  root.appendChild(wrap);
}
document.getElementById('btn-gerar').addEventListener('click', async () => {
  const colunas = [];
  for (let c = 1; c <= 7; c++) {
    const val = (document.getElementById(`col-${c}`).value || '').split(',').map(x => x.trim()).filter(Boolean);
    colunas.push(val);
  }
  const r = await fetch('/desdobramento/api/gerar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ colunas })
  });
  const data = await r.json();
  if (data.status !== 'success') {
    Swal.fire('Erro', data.message || 'Falha ao gerar.', 'error');
    return;
  }
  document.getElementById('total').textContent = `Total de apostas: ${data.total}`;
  document.getElementById('out').textContent = data.apostas.map(a => a.join('')).join('\\n');
});
</script>
{% endblock %}
"""


def build_template_for(cfg: dict, source_html: str) -> str:
    t = source_html
    t = t.replace("Dupla Sena", cfg["nome"])
    t = t.replace("50 dezenas (01–50)", f"{cfg['max_dezena']} dezenas")
    t = t.replace("MAX_DEZENA = 50", f"MAX_DEZENA = {cfg['max_dezena']}")
    t = t.replace("num > 50", f"num > {cfg['max_dezena']}")
    t = t.replace("01 e 50", f"{(0 if cfg['slug'] == 'lotomania' else 1):02d} e {cfg['max_dezena']:02d}")
    t = t.replace("Dezenas</a>", "Desdobramentos</a>")
    t = t.replace(">Desdobramento<", ">Desdobramentos<")
    return t


def main():
    dupla_model = read(ROOT / "AnalisePorPosicao-DuplaSena-Only" / "models" / "desdobramento.py")
    dupla_template = read(ROOT / "AnalisePorPosicao-DuplaSena-Only" / "templates" / "desdobramento.html")

    for cfg in TARGETS:
        app_root = ROOT / cfg["app_dir"]
        write(app_root / "models" / "desdobramento.py", dupla_model)
        write(app_root / "services" / "ciclo_service.py", build_ciclo_service(cfg))
        write(app_root / "services" / "desdobramento_service.py", build_service(cfg))
        write(app_root / "routes" / "desdobramento_routes.py", build_routes(cfg))
        write(app_root / "templates" / "desdobramento.html", build_template_for(cfg, dupla_template))
        patch_app(app_root / "app.py", has_model=True)
        ensure_menu_plural(app_root / "templates" / "base.html")
        print("OK", cfg["nome"])

    ss_root = ROOT / SUPERSETE["app_dir"]
    write(ss_root / "routes" / "desdobramento_routes.py", build_supersete_routes())
    write(ss_root / "templates" / "desdobramento.html", build_supersete_template())
    patch_app(ss_root / "app.py", has_model=False)
    ensure_menu_plural(ss_root / "templates" / "base.html")
    print("OK", SUPERSETE["nome"])


if __name__ == "__main__":
    main()

