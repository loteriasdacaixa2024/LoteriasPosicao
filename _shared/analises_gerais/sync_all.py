# -*- coding: utf-8 -*-
"""
Sincronização Caixa para Análises Gerais.

Modo padrão ``direct``: grava no SQLite de cada modalidade sem precisar
do servidor HTTP na porta 515x (Mega 5156, etc.). A Central (8083) basta.

Modo ``http``: POST /api/sincronizar em cada app (requer modalidade no ar).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from configuracoes.config import MODALITIES

SYNC_BODY = {"modo": "completo", "limite": 200}
SYNC_TIMEOUT = 300
MAX_SYNC_ROUNDS = 40


def _pos_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _resolve_python() -> str:
    venv = os.path.join(_pos_root(), "VenvLoterias", "Scripts", "python.exe")
    if os.path.isfile(venv):
        return venv
    return sys.executable


def _result_from_payload(
    key: str,
    nome: str,
    porta: int,
    data: Dict[str, Any],
    via: str,
) -> Dict[str, Any]:
    st = (data.get("status") or "").lower()
    ok = st in ("success", "info", "ok") and st != "error"
    msg = data.get("message") or data.get("msg") or ""
    if ok and not msg:
        novos = data.get("news") or data.get("novos") or data.get("inseridos") or data.get("importados")
        if novos is not None:
            msg = f"{novos} registro(s) atualizado(s)"
        else:
            msg = "OK"
    if via == "direct" and ok:
        msg = f"{msg} (via Central, sem porta {porta})"
    return {
        "key": key,
        "nome": nome,
        "porta": porta,
        "ok": ok,
        "offline": False,
        "via": via,
        "message": msg or ("Erro na sincronização" if not ok else "OK"),
        "detalhe": data,
    }


def _sync_one_direct(key: str, porta: int, nome: str) -> Dict[str, Any]:
    root = _pos_root()
    worker = os.path.join(root, "_shared", "analises_gerais", "sync_worker.py")
    py = _resolve_python()
    limite = SYNC_BODY.get("limite", 60)
    modo = SYNC_BODY.get("modo", "completo")
    env = os.environ.copy()
    shared = os.path.join(root, "_shared")
    env["PYTHONPATH"] = os.pathsep.join([root, shared, env.get("PYTHONPATH", "")])

    try:
        proc = subprocess.run(
            [py, worker, key, str(modo), str(limite)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=SYNC_TIMEOUT,
            env=env,
        )
        raw = (proc.stdout or "").strip()
        if not raw and proc.stderr:
            raw = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ""
        if proc.returncode != 0 and not raw:
            return {
                "key": key,
                "nome": nome,
                "porta": porta,
                "ok": False,
                "via": "direct",
                "message": proc.stderr.strip()[:300] or f"Falha ao sincronizar (código {proc.returncode})",
            }
        try:
            data = json.loads(raw.splitlines()[-1])
        except json.JSONDecodeError:
            return {
                "key": key,
                "nome": nome,
                "porta": porta,
                "ok": False,
                "via": "direct",
                "message": f"Resposta inválida: {raw[:200]}",
            }
        return _result_from_payload(key, nome, porta, data, "direct")
    except subprocess.TimeoutExpired:
        return {
            "key": key,
            "nome": nome,
            "porta": porta,
            "ok": False,
            "via": "direct",
            "message": "Tempo esgotado — tente de novo",
        }
    except Exception as e:
        return {
            "key": key,
            "nome": nome,
            "porta": porta,
            "ok": False,
            "via": "direct",
            "message": str(e),
        }


def _sync_one_http(key: str, porta: int, nome: str) -> Dict[str, Any]:
    url = f"http://127.0.0.1:{porta}/api/sincronizar"
    try:
        r = requests.post(
            url,
            json=SYNC_BODY,
            timeout=SYNC_TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        try:
            data = r.json()
        except Exception:
            data = {"status": "error", "message": r.text[:200] if r.text else "Resposta inválida"}
        ok = r.status_code == 200 and data.get("status") != "error"
        if not ok and data.get("status") != "error":
            data["status"] = "error"
        res = _result_from_payload(key, nome, porta, data, "http")
        res["status_code"] = r.status_code
        if not res["ok"]:
            res["message"] = data.get("message") or res["message"]
        return res
    except requests.exceptions.ConnectionError:
        return {
            "key": key,
            "nome": nome,
            "porta": porta,
            "ok": False,
            "offline": True,
            "via": "http",
            "message": f"Offline (porta {porta}) — use a Central em 8083 (sync direto)",
        }
    except requests.exceptions.Timeout:
        return {
            "key": key,
            "nome": nome,
            "porta": porta,
            "ok": False,
            "via": "http",
            "message": "Tempo esgotado — tente de novo",
        }
    except Exception as e:
        return {
            "key": key,
            "nome": nome,
            "porta": porta,
            "ok": False,
            "via": "http",
            "message": str(e),
        }


def _precisa_continuar_sync(detalhe: Dict[str, Any]) -> bool:
    if not detalhe:
        return False
    st = (detalhe.get("status") or "").lower()
    rest = int(detalhe.get("faltantes_restantes") or 0)
    if detalhe.get("continuar") is True:
        return True
    if st == "progress" and rest > 0:
        return True
    if rest > 0:
        return True
    return False


def _sync_one_until_complete(key: str, porta: int, nome: str, mode: str) -> Dict[str, Any]:
    """Repete lotes até fechar lacunas e alcançar o último concurso da Caixa."""
    last: Dict[str, Any] = {}
    rounds = 0
    total_news = 0

    while rounds < MAX_SYNC_ROUNDS:
        rounds += 1
        if mode == "http":
            last = _sync_one_http(key, porta, nome)
        elif mode == "direct":
            last = _sync_one_direct(key, porta, nome)
        else:
            last = _sync_one_direct(key, porta, nome)
            if not last.get("ok"):
                http = _sync_one_http(key, porta, nome)
                if http.get("ok"):
                    http["message"] = (http.get("message") or "") + " (fallback HTTP)"
                    last = http

        det = last.get("detalhe") or {}
        total_news += int(det.get("news") or det.get("novos") or 0)
        if not _precisa_continuar_sync(det):
            if last.get("ok") or (det.get("status") or "").lower() in ("success", "info"):
                break
            if (det.get("status") or "").lower() == "error":
                break
            break

    if rounds > 1 and last.get("ok"):
        msg = last.get("message") or "OK"
        last["message"] = f"{msg} ({rounds} lote(s), +{total_news} concurso(s))"
    last["sync_rounds"] = rounds
    last["sync_news_total"] = total_news
    return last


def _sync_one(key: str, porta: int, nome: str, mode: str) -> Dict[str, Any]:
    return _sync_one_until_complete(key, porta, nome, mode)


def sincronizar_todas_modalidades(
    max_workers: int = 2,
    keys: Optional[List[str]] = None,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sincroniza modalidades com a API Caixa.

    mode: direct (padrão) | http | auto
    """
    if mode is None:
        mode = os.environ.get("ANALISES_SYNC_MODE", "direct").lower()
    if mode not in ("direct", "http", "auto"):
        mode = "direct"

    items = []
    for key, meta in MODALITIES.items():
        if keys and key not in keys:
            continue
        items.append((key, meta["porta"], meta["nome"]))

    resultados: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {
            pool.submit(_sync_one, k, p, n, mode): k for k, p, n in items
        }
        for fut in as_completed(fut_map):
            resultados.append(fut.result())

    ordem = {k: i for i, k in enumerate(MODALITIES.keys())}
    resultados.sort(key=lambda x: ordem.get(x["key"], 99))
    ok_n = sum(1 for r in resultados if r.get("ok"))
    return {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "modo": mode,
        "total": len(resultados),
        "sucesso": ok_n,
        "falhas": len(resultados) - ok_n,
        "resultados": resultados,
    }
