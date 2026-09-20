# -*- coding: utf-8 -*-
"""Satélites da Central 8083: job de Excel (boot) e Conferências (sob demanda)."""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modality_launcher import port_open, pos_root, resolve_python, wait_for_port

EXPECTED_XLSX = (
    "LOTOFACIL.xlsx",
    "DIA_DE_SORTE.xlsx",
    "LOTOMANIA.xlsx",
    "QUINA.xlsx",
    "MEGA_SENA.xlsx",
    "MAIS_MILIONARIA.xlsx",
    "DUPLA_SENA.xlsx",
    "TIMEMANIA.xlsx",
    "SUPER_SETE.xlsx",
)
CONFERENCIAS_PORT = 8081
CONFERENCIAS_URL = f"http://127.0.0.1:{CONFERENCIAS_PORT}/"
DOWNLOAD_TIMEOUT_SEC = 240
CONFERENCIAS_WAIT_SEC = 75.0

_download_lock = threading.Lock()
_download_running = False
_download_status: Dict[str, Any] = {
    "estado": "idle",
    "ok": None,
    "mensagem": "Ainda não executado nesta sessão.",
    "iniciado_em": None,
    "terminado_em": None,
    "arquivos": [],
    "erros": [],
    "pid": None,
    "python": None,
    "script": None,
}

_conf_lock = threading.Lock()
_conf_proc: Optional[subprocess.Popen] = None
_conf_started_by_us = False
_conf_log_handle = None


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _state_dir() -> str:
    d = os.path.join(pos_root(), "AnalisePorPosicao-Central", "logs", "componentes")
    os.makedirs(d, exist_ok=True)
    return d


def _lock_path() -> str:
    return os.path.join(_state_dir(), "download.lock")


def _status_path() -> str:
    return os.path.join(_state_dir(), "download_status.json")


def _pid_alive(pid: int) -> bool:
    """Confere se o PID ainda existe. No Windows, os.kill(pid, 0) MATA o processo."""
    if not pid or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
        )
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and int(code.value) == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return False


def _persist_download_status() -> None:
    payload = dict(_download_status)
    try:
        with open(_status_path(), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _write_lock_pid(pid: int) -> None:
    with open(_lock_path(), "w", encoding="utf-8") as f:
        f.write(str(int(pid)))


def _acquire_file_lock(pid: int) -> bool:
    path = _lock_path()
    if os.path.isfile(path):
        try:
            raw = open(path, encoding="utf-8").read().strip()
            old = int(raw or "0")
        except Exception:
            old = 0
        if old and old != pid and _pid_alive(old):
            return False
    try:
        _write_lock_pid(pid)
        return True
    except Exception:
        return False


def _release_file_lock() -> None:
    try:
        os.remove(_lock_path())
    except OSError:
        pass


def _tcp_up(port: int, timeout: float = 0.12) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def resolve_download_python() -> str:
    """Usa o Python da Central. O venv da pasta de download está quebrado."""
    return resolve_python()


def resolve_conferencias_python() -> str:
    root = pos_root()
    venv = os.path.join(
        root,
        "LoteriasExtras",
        "conferencias",
        "venv-modalidades",
        "Scripts",
        "python.exe",
    )
    if os.path.isfile(venv):
        return venv
    return resolve_python()


def conferencias_dir() -> str:
    return os.path.join(
        pos_root(),
        "LoteriasExtras",
        "conferencias",
        "AnalisePorPosicao-Central",
    )


def download_dir() -> str:
    return os.path.join(pos_root(), "DownloadTodosResultadosLoterias")


def download_script() -> str:
    return os.path.join(download_dir(), "DownloadResultadosLoteriasCaixa.py")


def download_xlsx_dir() -> str:
    return os.path.join(download_dir(), "downloads")


def _parse_download_output(text: str) -> tuple[List[Dict[str, Any]], List[str]]:
    arquivos: List[Dict[str, Any]] = []
    erros: List[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(
            r"Download conclu.{0,8}:\s*(.+?)\s*\((\d+)\s*bytes\)",
            line,
            re.IGNORECASE,
        )
        if m:
            arquivos.append({
                "arquivo": m.group(1),
                "bytes": int(m.group(2)),
            })
            continue
        low = line.lower()
        if low.startswith("erro") or "não devolveu" in low or "nao devolveu" in low:
            erros.append(line)
    return arquivos, erros


def _xlsx_local_date(path: str) -> Optional[date]:
    try:
        st = os.stat(path)
    except OSError:
        return None
    if st.st_size <= 2:
        return None
    return datetime.fromtimestamp(st.st_mtime).date()


def inspect_xlsx_freshness() -> Dict[str, Any]:
    """Os 9 Excel oficiais: compara só o dia local, ignora a hora."""
    hoje = datetime.now().date()
    folder = download_xlsx_dir()
    presentes: List[Dict[str, Any]] = []
    faltando: List[str] = []
    anteriores: List[str] = []
    for name in EXPECTED_XLSX:
        path = os.path.join(folder, name)
        dia = _xlsx_local_date(path)
        if dia is None:
            faltando.append(name)
            continue
        presentes.append({
            "arquivo": name,
            "dia": dia.strftime("%d/%m/%Y"),
            "bytes": int(os.path.getsize(path)),
        })
        if dia < hoje:
            anteriores.append(name)
    return {
        "hoje": hoje.strftime("%d/%m/%Y"),
        "atualizado_hoje": (not faltando and not anteriores),
        "presentes": presentes,
        "faltando": faltando,
        "anteriores": anteriores,
    }


def _mark_download_skipped_today(info: Dict[str, Any]) -> None:
    global _download_status
    arquivos = [
        {"arquivo": p["arquivo"], "bytes": p.get("bytes")}
        for p in (info.get("presentes") or [])
    ]
    with _download_lock:
        _download_status = {
            "estado": "ok",
            "ok": True,
            "mensagem": f"Excel já atualizado hoje ({info.get('hoje')}). Download pulado.",
            "iniciado_em": None,
            "terminado_em": _now(),
            "arquivos": arquivos,
            "erros": [],
            "pid": None,
            "python": resolve_download_python(),
            "script": download_script(),
            "pulado": True,
            "motivo": "mesmo_dia",
        }
        _persist_download_status()


def boot_download_se_necessario() -> None:
    """No boot: baixa só se faltar arquivo ou se o dia do Excel for anterior a hoje."""
    info = inspect_xlsx_freshness()
    if info["atualizado_hoje"]:
        _mark_download_skipped_today(info)
        print(
            f"[Central] Excel já é de hoje ({info['hoje']}). "
            "Download automático pulado."
        )
        return
    motivos: List[str] = []
    if info["faltando"]:
        motivos.append("faltando: " + ", ".join(info["faltando"]))
    if info["anteriores"]:
        motivos.append("dia anterior: " + ", ".join(info["anteriores"]))
    print("[Central] Excel desatualizado — " + "; ".join(motivos or ["checagem falhou"]) + ".")
    print("[Central] Job de Excel: em segundo plano, sem travar a interface.")
    start_download_job_background()


def _xlsx_updated_since(started_ts: float) -> List[Dict[str, Any]]:
    """Confirma na pasta real — o log no Windows pode chegar em cp1252."""
    out: List[Dict[str, Any]] = []
    folder = download_xlsx_dir()
    if not os.path.isdir(folder):
        return out
    slack = started_ts - 2.0
    for name in EXPECTED_XLSX:
        path = os.path.join(folder, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        if st.st_mtime >= slack and st.st_size > 2:
            out.append({"arquivo": path, "bytes": int(st.st_size)})
    return out


def _merge_arquivos(*grupos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    merged: List[Dict[str, Any]] = []
    for grupo in grupos:
        for item in grupo or []:
            key = os.path.normcase(os.path.basename(str(item.get("arquivo") or "")))
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def status_download() -> Dict[str, Any]:
    st = dict(_download_status)
    st["em_andamento"] = bool(_download_running) or st.get("estado") == "rodando"
    return st


def _decode_log_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_log_since(log_path: str, marker: str) -> str:
    try:
        with open(log_path, "rb") as f:
            raw = f.read()
    except OSError:
        return ""
    text = _decode_log_bytes(raw)
    idx = text.rfind(marker)
    return text[idx:] if idx >= 0 else text


def _set_download_result(
    *,
    estado: str,
    ok: Optional[bool],
    mensagem: str,
    arquivos: List[Dict[str, Any]],
    erros: List[str],
    pid: Optional[int],
    python: str,
    script: str,
    returncode: Any = None,
    duplicado: bool = False,
) -> Dict[str, Any]:
    global _download_running, _download_status
    with _download_lock:
        _download_running = False
        _download_status = {
            "estado": estado,
            "ok": ok,
            "mensagem": mensagem,
            "iniciado_em": _download_status.get("iniciado_em"),
            "terminado_em": _now(),
            "arquivos": arquivos,
            "erros": erros,
            "pid": pid,
            "python": python,
            "script": script,
            "returncode": returncode,
        }
        if duplicado:
            _download_status["duplicado"] = True
        _persist_download_status()
    return status_download()


def run_download_job(timeout_sec: float = DOWNLOAD_TIMEOUT_SEC) -> Dict[str, Any]:
    """Executa o script original. Não duplica se já estiver rodando."""
    global _download_running, _download_status

    with _download_lock:
        if _download_running:
            st = status_download()
            st["mensagem"] = "Download já em andamento — não foi iniciado de novo."
            st["duplicado"] = True
            return st

        script = download_script()
        cwd = download_dir()
        py = resolve_download_python()

        if not os.path.isfile(script):
            _download_status = {
                "estado": "erro",
                "ok": False,
                "mensagem": f"Script não encontrado: {script}",
                "iniciado_em": _now(),
                "terminado_em": _now(),
                "arquivos": [],
                "erros": [f"Script não encontrado: {script}"],
                "pid": None,
                "python": py,
                "script": script,
            }
            _persist_download_status()
            return status_download()

        if not os.path.isfile(py):
            _download_status = {
                "estado": "erro",
                "ok": False,
                "mensagem": f"Python não encontrado para o job de Excel: {py}",
                "iniciado_em": _now(),
                "terminado_em": _now(),
                "arquivos": [],
                "erros": [f"Python não encontrado: {py}"],
                "pid": None,
                "python": py,
                "script": script,
            }
            _persist_download_status()
            return status_download()

        _download_running = True
        _download_status = {
            "estado": "rodando",
            "ok": None,
            "mensagem": "Atualizando resultados em Excel…",
            "iniciado_em": _now(),
            "terminado_em": None,
            "arquivos": [],
            "erros": [],
            "pid": None,
            "python": py,
            "script": script,
        }
        _persist_download_status()

    log_path = os.path.join(_state_dir(), "download.log")
    proc = None
    acquired_lock = False
    marker = f"--- {_now()} python={py} ---"
    try:
        if not _acquire_file_lock(os.getpid()):
            return _set_download_result(
                estado="idle",
                ok=None,
                mensagem="Outro download já estava em execução (lock). Não duplicado.",
                arquivos=[],
                erros=[],
                pid=None,
                python=py,
                script=script,
                duplicado=True,
            )
        acquired_lock = True

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        started_ts = time.time()
        log_f = open(log_path, "a", encoding="utf-8")
        try:
            log_f.write(f"\n{marker}\n")
            log_f.flush()
            proc = subprocess.Popen(
                [py, "-u", "DownloadResultadosLoteriasCaixa.py"],
                cwd=cwd,
                env=env,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            _write_lock_pid(proc.pid)
            with _download_lock:
                _download_status["pid"] = proc.pid
                _persist_download_status()

            timed_out = False
            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    pass
        finally:
            try:
                log_f.flush()
                log_f.close()
            except Exception:
                pass

        stdout = _read_log_since(log_path, marker)
        arquivos, erros = _parse_download_output(stdout)
        arquivos = _merge_arquivos(arquivos, _xlsx_updated_since(started_ts))
        if timed_out:
            if arquivos:
                avisos = list(erros)
                avisos.append(f"Tempo esgotado após {int(timeout_sec)}s, mas {len(arquivos)} arquivo(s) já estavam na pasta.")
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write("\n[TIMEOUT]\n")
                except OSError:
                    pass
                return _set_download_result(
                    estado="ok",
                    ok=True,
                    mensagem=f"{len(arquivos)} arquivo(s) atualizado(s).",
                    arquivos=arquivos,
                    erros=avisos,
                    pid=proc.pid if proc else None,
                    python=py,
                    script=script,
                    returncode=proc.returncode if proc else None,
                )
            erros.append(f"Tempo esgotado após {int(timeout_sec)}s.")
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("\n[TIMEOUT]\n")
            except OSError:
                pass
            return _set_download_result(
                estado="erro",
                ok=False,
                mensagem=f"Tempo esgotado após {int(timeout_sec)}s. A Central segue no ar.",
                arquivos=arquivos,
                erros=erros,
                pid=proc.pid if proc else None,
                python=py,
                script=script,
                returncode=proc.returncode if proc else None,
            )

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[exit {proc.returncode}]\n")
        except OSError:
            pass

        if proc.returncode not in (0, None) and not erros and not arquivos:
            erros.append(f"Processo encerrou com código {proc.returncode}.")
        ok = bool(arquivos) and proc.returncode in (0, None)
        if not ok and arquivos:
            ok = True
        msg = (
            f"{len(arquivos)} arquivo(s) atualizado(s)."
            if ok
            else ("Falha no download: " + "; ".join(erros[:4] or ["nenhum Excel foi gravado na pasta downloads."]))
        )
        return _set_download_result(
            estado="ok" if ok else "erro",
            ok=ok,
            mensagem=msg,
            arquivos=arquivos,
            erros=erros,
            pid=proc.pid,
            python=py,
            script=script,
            returncode=proc.returncode,
        )
    except Exception as e:
        return _set_download_result(
            estado="erro",
            ok=False,
            mensagem=f"Falha ao executar o job de Excel: {e}",
            arquivos=[],
            erros=[str(e)],
            pid=getattr(proc, "pid", None),
            python=py,
            script=script,
        )
    finally:
        if acquired_lock:
            _release_file_lock()
        with _download_lock:
            _download_running = False


def start_download_job_background() -> None:
    def _runner():
        try:
            st = run_download_job()
            mark = "OK" if st.get("ok") else "ERRO"
            print(f"[Central] Excel [{mark}] {st.get('mensagem')}")
            for err in st.get("erros") or []:
                print(f"    - {err}")
        except Exception as e:
            print(f"[Central] Excel [ERRO] {e}")

    t = threading.Thread(target=_runner, name="excel-download-job", daemon=True)
    t.start()


def status_conferencias() -> Dict[str, Any]:
    online = _tcp_up(CONFERENCIAS_PORT)
    alive = bool(_conf_proc is not None and _conf_proc.poll() is None)
    return {
        "online": online,
        "porta": CONFERENCIAS_PORT,
        "url": CONFERENCIAS_URL,
        "iniciado_pela_central": bool(_conf_started_by_us and alive),
        "pid": _conf_proc.pid if alive else None,
        "python": resolve_conferencias_python(),
        "pasta": conferencias_dir(),
    }


def ensure_conferencias(wait_timeout: float = CONFERENCIAS_WAIT_SEC) -> Dict[str, Any]:
    """Sobe a Central LotoCheck (8081) se necessário. Não mata processo existente."""
    global _conf_proc, _conf_started_by_us, _conf_log_handle

    with _conf_lock:
        if port_open(CONFERENCIAS_PORT):
            st = status_conferencias()
            st["ok"] = True
            st["iniciado_agora"] = False
            st["mensagem"] = "Conferências já estavam em execução."
            return st

        cwd = conferencias_dir()
        py = resolve_conferencias_python()
        app_py = os.path.join(cwd, "app.py")
        if not os.path.isdir(cwd) or not os.path.isfile(app_py):
            return {
                "ok": False,
                "online": False,
                "iniciado_agora": False,
                "porta": CONFERENCIAS_PORT,
                "url": CONFERENCIAS_URL,
                "mensagem": f"Pasta de conferências não encontrada: {cwd}",
            }
        if not os.path.isfile(py):
            return {
                "ok": False,
                "online": False,
                "iniciado_agora": False,
                "porta": CONFERENCIAS_PORT,
                "url": CONFERENCIAS_URL,
                "mensagem": f"Python das conferências não encontrado: {py}",
            }

        log_path = os.path.join(_state_dir(), "conferencias.log")
        try:
            if _conf_log_handle:
                try:
                    _conf_log_handle.close()
                except Exception:
                    pass
            _conf_log_handle = open(log_path, "a", encoding="utf-8")
            _conf_log_handle.write(f"\n--- iniciando {_now()} python={py} ---\n")
            _conf_log_handle.flush()
            env = os.environ.copy()
            env.pop("LOTOCHECK_SKIP_CHILDREN", None)
            conf_root = os.path.dirname(cwd)
            env["PYTHONPATH"] = conf_root
            _conf_proc = subprocess.Popen(
                [py, "app.py"],
                cwd=cwd,
                env=env,
                stdout=_conf_log_handle,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            return {
                "ok": False,
                "online": False,
                "iniciado_agora": False,
                "porta": CONFERENCIAS_PORT,
                "url": CONFERENCIAS_URL,
                "mensagem": f"Falha ao iniciar conferências: {e}",
            }

        time.sleep(0.4)
        if _conf_proc.poll() is not None:
            _conf_started_by_us = False
            return {
                "ok": False,
                "online": False,
                "iniciado_agora": False,
                "porta": CONFERENCIAS_PORT,
                "url": CONFERENCIAS_URL,
                "pid": _conf_proc.pid,
                "mensagem": (
                    f"Conferências encerraram ao iniciar (código {_conf_proc.returncode}). "
                    f"Veja {log_path}"
                ),
            }

        _conf_started_by_us = True
        up = wait_for_port(CONFERENCIAS_PORT, timeout_sec=wait_timeout)
        if not up:
            return {
                "ok": False,
                "online": False,
                "iniciado_agora": True,
                "porta": CONFERENCIAS_PORT,
                "url": CONFERENCIAS_URL,
                "pid": _conf_proc.pid,
                "iniciado_pela_central": True,
                "mensagem": (
                    f"Conferências iniciadas (PID {_conf_proc.pid}) mas a porta "
                    f"{CONFERENCIAS_PORT} não respondeu em {int(wait_timeout)}s. "
                    f"Veja {log_path}"
                ),
            }

        st = status_conferencias()
        st["ok"] = True
        st["iniciado_agora"] = True
        st["mensagem"] = "Conferências iniciadas e disponíveis."
        return st


def stop_conferencias_if_started_by_us() -> None:
    """Encerra só o processo que a Central 8083 criou (árvore no Windows)."""
    global _conf_proc, _conf_started_by_us, _conf_log_handle
    if not _conf_started_by_us or _conf_proc is None:
        return
    pid = _conf_proc.pid
    if sys.platform == "win32":
        try:
            subprocess.run(
                f"taskkill /F /T /PID {pid}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            try:
                _conf_proc.kill()
            except Exception:
                pass
    else:
        try:
            _conf_proc.terminate()
            _conf_proc.wait(timeout=5)
        except Exception:
            try:
                _conf_proc.kill()
            except Exception:
                pass
    _conf_proc = None
    _conf_started_by_us = False
    if _conf_log_handle:
        try:
            _conf_log_handle.close()
        except Exception:
            pass
        _conf_log_handle = None


def status_componentes() -> Dict[str, Any]:
    return {
        "download": status_download(),
        "conferencias": status_conferencias(),
    }


def boot_satelites() -> None:
    """Excel só se o dia dos arquivos for anterior a hoje. Conferências sob demanda."""
    boot_download_se_necessario()
    print("[Central] Conferências só sobem se o botão for clicado.")


def boot_satelites_depois_da_central(port: int) -> None:
    """Não atrasa o app.run da Central — espera a porta e aí dispara o Excel."""

    def _go():
        deadline = time.time() + 30
        while time.time() < deadline:
            if _tcp_up(port):
                try:
                    boot_satelites()
                except Exception as e:
                    print(f"[Central] Excel/satélites isolados falharam ({e}). A Central segue.")
                return
            time.sleep(0.2)

    threading.Thread(target=_go, name="boot-satelites", daemon=True).start()
