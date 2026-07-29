import atexit
import os
import sys

import requests
from flask import Flask, Response, jsonify, redirect, render_template, request
from jinja2 import ChoiceLoader, FileSystemLoader

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_shared"))
_POS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (_POS_ROOT, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from configuracoes.app_integration import extend_config_app
from configuracoes.config import MODALITIES as MODALITIES_CFG
from configuracoes.public_urls import (
    CENTRAL_PORT,
    is_tunnel_or_remote_host,
    modalities_public_map,
    modality_public_url,
)
from configuracoes.routes_central import config_central_bp
from _shared.analises_gerais.routes_central import analises_gerais_bp
from _shared.modality_launcher import (
    start_all_modalities,
    status_modalities,
    stop_all_modalities,
)
from modality_proxy import proxy_modality_request

app = Flask(__name__)
extend_config_app(app)
app.register_blueprint(config_central_bp, url_prefix="/configuracoes")

_tpl_ag = os.path.join(_SHARED, "analises_gerais", "templates")
_loaders = [app.jinja_loader, FileSystemLoader(_tpl_ag)]
app.jinja_loader = ChoiceLoader(_loaders)

app.register_blueprint(analises_gerais_bp, url_prefix="/analises-gerais")

atexit.register(stop_all_modalities)

MODALIDADES = {
    key: (int(meta["porta"]), meta.get("nome", key))
    for key, meta in MODALITIES_CFG.items()
}

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def _request_public_host():
    host = request.headers.get("X-Forwarded-Host") or request.host
    scheme = (
        request.headers.get("X-Forwarded-Proto")
        or request.scheme
        or "http"
    )
    return host, scheme


@app.route("/")
def central_dashboard():
    host, scheme = _request_public_host()
    mods = modalities_public_map(request_host=host, request_scheme=scheme)
    ordem = [
        "lotofacil", "diadesorte", "lotomania", "quina", "megasena",
        "maismilionaria", "duplasena", "timemania", "supersete",
    ]
    cards = [mods[k] for k in ordem if k in mods]
    return render_template(
        "index.html",
        modality_cards=cards,
        modality_urls={k: v["url"] for k, v in mods.items()},
        modality_ports={k: v["porta"] for k, v in mods.items()},
        central_port=CENTRAL_PORT,
        via_proxy=is_tunnel_or_remote_host(host),
    )


@app.route("/goto/<mod_id>/", defaults={"subpath": ""})
@app.route("/goto/<mod_id>/<path:subpath>")
def goto_modalidade(mod_id, subpath):
    """
    Local → http://localhost:515x/...
    Tunnel → /m/<mod>/...  (mesma origem 8083)
    """
    if mod_id not in MODALIDADES:
        return jsonify({"error": "Modalidade não encontrada"}), 404
    host, scheme = _request_public_host()
    path = "/" + (subpath or "") if subpath else "/"
    target = modality_public_url(
        mod_id, path,
        request_host=host,
        request_scheme=scheme,
    )
    qs = request.query_string.decode("utf-8", errors="ignore")
    if qs:
        target = target + ("&" if "?" in target else "?") + qs
    return redirect(target, code=302)


@app.route("/m/<mod_id>/", defaults={"subpath": ""}, methods=_PROXY_METHODS)
@app.route("/m/<mod_id>/<path:subpath>", methods=_PROXY_METHODS)
def proxy_modalidade(mod_id, subpath):
    """Proxy path-based: /m/duplasena/... → 127.0.0.1:5158/..."""
    mod_data = MODALIDADES.get(mod_id)
    if not mod_data:
        return jsonify({"error": "Modalidade não encontrada"}), 404
    port, _nome = mod_data
    return proxy_modality_request(mod_id, port, subpath, request)


@app.route("/api/modelos/<mod_id>", methods=["POST"])
def proxy_modelos(mod_id):
    mod_data = MODALIDADES.get(mod_id)
    if not mod_data:
        return jsonify({"error": "Modalidade não encontrada"}), 404

    port, nome = mod_data
    try:
        r = requests.post(f"http://127.0.0.1:{port}/modelos/api/backtesting", timeout=120)
        if r.status_code == 200:
            data = r.json()
            data["modalidade_nome"] = nome
            return jsonify(data)
        if r.status_code == 404:
            return jsonify({"error": "Endpoint de modelos não encontrado nesta loteria."})
        return jsonify({"error": f"Erro {r.status_code} na origem."})
    except requests.exceptions.RequestException:
        return jsonify({"error": "API Offline ou tempo limite excedido."})


@app.route("/api/modelos/<mod_id>/gerar/<int:modelo_id>", methods=["POST"])
def proxy_gerar_modelo(mod_id, modelo_id):
    mod_data = MODALIDADES.get(mod_id)
    if not mod_data:
        return jsonify({"error": "Modalidade não encontrada"}), 404
    port, _nome = mod_data
    try:
        r = requests.post(
            f"http://127.0.0.1:{port}/modelos/api/gerar/{modelo_id}",
            timeout=120,
        )
        return Response(
            r.content,
            status=r.status_code,
            content_type=r.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API Offline: {e}"}), 502


@app.route("/api/urls")
def api_urls_publicas():
    host, scheme = _request_public_host()
    return jsonify({
        "status": "success",
        "central_port": CENTRAL_PORT,
        "via_proxy": is_tunnel_or_remote_host(host),
        "modalities": modalities_public_map(request_host=host, request_scheme=scheme),
    })


def _should_boot_modalities() -> bool:
    return os.environ.get("WERKZEUG_RUN_MAIN") != "true"


@app.route("/api/modalidades/status", methods=["GET"])
def api_modalidades_status():
    st = status_modalities()
    return jsonify({"status": "success", **st})


@app.route("/api/modalidades/iniciar", methods=["POST"])
def api_modalidades_iniciar():
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force"))
    st = start_all_modalities(force=force, wait_online=True)
    return jsonify({"status": "success", **st})


if __name__ == "__main__":
    if _should_boot_modalities():
        print("[Central] Subindo apps das modalidades (5152–5160) para links e APIs…")
        start_all_modalities(wait_online=True)
    app.run(host="0.0.0.0", port=CENTRAL_PORT, debug=False)
