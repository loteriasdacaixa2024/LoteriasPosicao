import subprocess
import atexit
import os
import sys
from flask import Flask, render_template, request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lotteries_config import LOTTERIES, ESTRATEGIAS_SLUGS, PUBLIC_BASE_URL, public_url

from remote_wsgi import apply_proxy

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
apply_proxy(app)
processes = []

INITIALS = {
    "lotofacil": "LF",
    "dia_de_sorte": "DS",
    "quina": "QN",
    "megasena": "MS",
    "lotomania": "LM",
    "timemania": "TM",
    "duplasena": "DP",
    "maismilionaria": "MM",
    "supersete": "SS",
}


def kill_process_on_port(port):
    try:
        cmd = f'netstat -ano | findstr LISTENING | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        pids = set()
        for line in output.strip().split('\n'):
            parts = line.split()
            if not parts:
                continue
            pid = parts[-1]
            if pid.isdigit() and pid != '0':
                pids.add(pid)
        for pid in pids:
            print(f" [LIMPEZA] Terminando processo orfão PID {pid} na porta {port}...")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def print_banner():
    name_w = max(len(s) for s in ESTRATEGIAS_SLUGS)
    print()
    for slug in ESTRATEGIAS_SLUGS:
        port = LOTTERIES[slug]["port"]
        print(f"  {slug.ljust(name_w)}  :{port}")

    print()
    for slug in ESTRATEGIAS_SLUGS:
        port = LOTTERIES[slug]["port"]
        print(f"  [{slug}] http://localhost:{port}")

    print()
    for slug in ESTRATEGIAS_SLUGS:
        folder = LOTTERIES[slug]["folder"]
        print(f"  [{slug}] {public_url(folder)}")

    print()
    print("  CENTRAL PARA ACESSO GERAL")
    print("  [central] http://localhost:8084")
    print(f"  [central] {PUBLIC_BASE_URL}")
    print()


def start_modalities():
    if os.environ.get("SKIP_CHILD_SERVICES") == "1":
        print_banner()
        return

    venv_python = os.path.join(os.path.dirname(ROOT), "conferencias", "venv-modalidades", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        print(f" [AVISO] venv não encontrado: {venv_python}")
        venv_python = sys.executable

    for slug in ESTRATEGIAS_SLUGS:
        cfg = LOTTERIES.get(slug) or {}
        folder = cfg.get("folder", slug)
        port = cfg.get("port")
        mod_dir = os.path.join(ROOT, folder)
        if not os.path.exists(os.path.join(mod_dir, "app.py")):
            print(f" [ERRO] Pasta da modalidade não encontrada: {mod_dir}")
            continue
        if port:
            kill_process_on_port(port)
        p = subprocess.Popen(
            [venv_python, "app.py"],
            cwd=mod_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(p)

    print_banner()


def stop_modalities():
    for p in processes:
        p.terminate()
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()


atexit.register(stop_modalities)


def is_public_access():
    forwarded = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip().lower()
    host = (forwarded or request.host or "").split(":")[0].lower()
    prefix = (request.headers.get("X-Forwarded-Prefix") or request.script_root or "")
    if host in ("localhost", "127.0.0.1"):
        return False
    if "marciofernandomaia.com.br" in host:
        return True
    if prefix.rstrip("/").endswith("estrategias") or "/estrategias" in prefix:
        return True
    return False


@app.route('/')
def index():
    public = is_public_access()
    modalities = []
    for slug in ESTRATEGIAS_SLUGS:
        cfg = LOTTERIES[slug]
        folder = cfg.get("folder", slug)
        href = public_url(folder) if public else f"http://localhost:{cfg['port']}"
        modalities.append({
            "slug": slug,
            "name": cfg["name"],
            "port": cfg["port"],
            "color": cfg.get("colors", {}).get("primary", "#d4e31a"),
            "logo": (cfg.get("extra") or {}).get("remote_logo", ""),
            "icon": cfg.get("icon", ""),
            "initials": INITIALS.get(slug, slug[:2].upper()),
            "href": href,
        })
    return render_template(
        "index.html",
        modalities=modalities,
        public_access=public,
    )


if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        start_modalities()
    from quiet_terminal import silence_startup
    silence_startup()
    app.run(host='0.0.0.0', port=8084, debug=False, use_reloader=False)
