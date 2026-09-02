# -*- coding: utf-8 -*-
"""
Worker CLI: sincroniza uma modalidade sem servidor HTTP na porta local.
Uso: python sync_worker.py <key> [modo] [limite]
Saída: JSON no stdout (uma linha).
"""
from __future__ import annotations

import importlib
import json
import os
import sys


def _pos_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _bootstrap_paths() -> str:
    root = _pos_root()
    shared = os.path.join(root, "_shared")
    for p in (root, shared):
        if p not in sys.path:
            sys.path.insert(0, p)
    return root


def _setup_modality_path(mod_dir: str) -> None:
    if mod_dir not in sys.path:
        sys.path.insert(0, mod_dir)
    os.chdir(mod_dir)


def _importar_especiais_pendentes(key: str, service_cls) -> None:
    from configuracoes.config import CONCURSOS_ESPECIAIS
    from models.shared import db

    for esp in CONCURSOS_ESPECIAIS.get(key, []):
        n = int(esp.get("concurso") or 0)
        if not n:
            continue
        dados = service_cls.buscar_concurso_especifico(n)
        if not dados:
            continue
        if hasattr(service_cls, "_salvar_concurso") and service_cls._salvar_concurso(n, dados):
            db.session.commit()


def run_sync(key: str, modo: str = "completo", limite: int = 60) -> dict:
    _bootstrap_paths()
    from _shared.analises_gerais.registry import SPECS_BY_KEY
    from _shared.analises_gerais.sync_registry import SYNC_SERVICES

    spec = SPECS_BY_KEY.get(key)
    if not spec:
        return {"status": "error", "message": f"Modalidade desconhecida: {key}"}

    svc = SYNC_SERVICES.get(key)
    if not svc:
        return {"status": "error", "message": f"Sem serviço de sync para: {key}"}

    mod_module, cls_name, supersete_style = svc
    mod_dir = os.path.join(_pos_root(), spec.app_dir)
    if not os.path.isdir(mod_dir):
        return {"status": "error", "message": f"Pasta não encontrada: {mod_dir}"}

    _setup_modality_path(mod_dir)
    app_mod = importlib.import_module("app")
    if not hasattr(app_mod, "create_app"):
        return {"status": "error", "message": "app.create_app não encontrado"}
    flask_app = app_mod.create_app()

    svc_mod = importlib.import_module(mod_module)
    service_cls = getattr(svc_mod, cls_name)

    with flask_app.app_context():
        if supersete_style:
            result = service_cls.sincronizar_banco()
        else:
            result = service_cls.sincronizar_banco(modo=modo, limite=limite)
        _importar_especiais_pendentes(key, service_cls)

    if not isinstance(result, dict):
        return {"status": "error", "message": "Resposta inválida do serviço"}
    return result


def main() -> None:
    _bootstrap_paths()
    key = sys.argv[1]
    modo = sys.argv[2] if len(sys.argv) > 2 else "completo"
    limite = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    out = run_sync(key, modo, limite)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
