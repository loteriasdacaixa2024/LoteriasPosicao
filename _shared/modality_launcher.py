# -*- coding: utf-8 -*-
"""Sobe os apps Flask de cada modalidade (usado pela Central na porta 8083)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests

from configuracoes.config import MODALITIES

_processes: List[subprocess.Popen] = []
_started = False

MODALITY_DIRS = {
    "lotofacil": "AnalisePorPosicao-Lotofacil-Only",
    "supersete": "AnalisePorPosicao-SuperSete-Only",
    "lotomania": "AnalisePorPosicao-Lotomania-Only",
    "quina": "AnalisePorPosicao-Quina-Only",
    "megasena": "AnalisePorPosicao-MegaSena-Only",
    "maismilionaria": "AnalisePorPosicao-MaisMilionaria-Only",
    "duplasena": "AnalisePorPosicao-DuplaSena-Only",
    "timemania": "AnalisePorPosicao-Timemania-Only",
    "diadesorte": "AnalisePorPosicao--DiaDeSorte-Only",
}


def pos_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve_python() -> str:
    venv = os.path.join(pos_root(), "VenvLoterias", "Scripts", "python.exe")
    if os.path.isfile(venv):
        return venv
    return sys.executable


def _logs_dir() -> str:
    d = os.path.join(pos_root(), "AnalisePorPosicao-Central", "logs", "modalidades")
    os.makedirs(d, exist_ok=True)
    return d


def _child_env() -> dict:
    root = pos_root()
    shared = os.path.join(root, "_shared")
    env = os.environ.copy()
    parts = [root, shared]
    if env.get("PYTHONPATH"):
        parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def kill_process_on_port(port: int) -> None:
    try:
        cmd = f"netstat -ano | findstr LISTENING | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True).decode("utf-8", errors="ignore")
        pids = set()
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            m = re.search(r"(\d+)\s*$", line.strip())
            if m:
                pids.add(m.group(1))
        for pid in pids:
            if pid and pid != "0":
                subprocess.run(
                    f"taskkill /F /PID {pid}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception:
        pass


def port_open(port: int, timeout: float = 0.8) -> bool:
    try:
        r = requests.get(f"http://127.0.0.1:{port}/", timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def wait_for_port(port: int, timeout_sec: float = 60.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(0.5)
    return False


def _start_one(key: str, folder: str, kill_existing: bool) -> Tuple[bool, str]:
    root = pos_root()
    mod_dir = os.path.join(root, folder)
    porta = MODALITIES[key]["porta"]
    nome = MODALITIES[key]["nome"]

    if not os.path.isdir(mod_dir):
        return False, f"{nome}: pasta não encontrada ({folder})"

    if kill_existing:
        kill_process_on_port(porta)

    log_path = os.path.join(_logs_dir(), f"{key}.log")
    log_f = open(log_path, "a", encoding="utf-8")
    log_f.write(f"\n--- iniciando {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_f.flush()

    py = resolve_python()
    try:
        p = subprocess.Popen(
            [py, "app.py"],
            cwd=mod_dir,
            env=_child_env(),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        log_f.write(f"ERRO ao iniciar: {e}\n")
        log_f.close()
        return False, f"{nome}: falha ao iniciar ({e})"

    _processes.append(p)
    time.sleep(0.35)

    if p.poll() is not None:
        log_f.write(f"Processo encerrou com código {p.returncode}\n")
        log_f.close()
        return False, f"{nome}: encerrou ao iniciar (veja {log_path})"

    return True, f"{nome}: PID {p.pid} na porta {porta}"


def start_all_modalities(
    kill_existing: bool = True,
    wait_online: bool = True,
    wait_timeout_per_port: float = 55.0,
    force: bool = False,
) -> Dict[str, object]:
    """
    Sobe as 9 modalidades (5152–5160).
    Retorna resumo com portas online e mensagens.
    """
    global _started
    if _started and not force:
        return status_modalities()

    if force:
        stop_all_modalities()

    root = pos_root()
    py = resolve_python()
    print(f"[Central] Python: {py}")
    print(f"[Central] Raiz:   {root}")

    mensagens: List[str] = []
    for key, folder in MODALITY_DIRS.items():
        ok, msg = _start_one(key, folder, kill_existing)
        mensagens.append(msg)
        print(f"  [{'OK' if ok else 'ERRO'}] {msg}")

    _started = True

    online: Dict[str, bool] = {}
    if wait_online:
        print("[Central] Aguardando portas…")
        for key in MODALITY_DIRS:
            porta = MODALITIES[key]["porta"]
            nome = MODALITIES[key]["nome"]
            up = wait_for_port(porta, timeout_sec=wait_timeout_per_port)
            online[key] = up
            mark = "ONLINE" if up else "OFFLINE"
            print(f"  [{mark}] {nome} — http://127.0.0.1:{porta}")
    else:
        for key in MODALITY_DIRS:
            online[key] = port_open(MODALITIES[key]["porta"])

    n_ok = sum(1 for v in online.values() if v)
    print(f"[Central] {n_ok}/{len(MODALITY_DIRS)} modalidades respondendo.")

    return {
        "mensagens": mensagens,
        "online": online,
        "total": len(MODALITY_DIRS),
        "online_count": n_ok,
    }


def status_modalities() -> Dict[str, object]:
    online = {}
    for key in MODALITY_DIRS:
        online[key] = port_open(MODALITIES[key]["porta"])
    return {
        "online": online,
        "total": len(MODALITY_DIRS),
        "online_count": sum(1 for v in online.values() if v),
    }


def stop_all_modalities() -> None:
    global _started
    for p in _processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    _processes.clear()
    _started = False
