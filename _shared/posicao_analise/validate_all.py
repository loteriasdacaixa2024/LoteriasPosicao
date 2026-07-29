# -*- coding: utf-8 -*-
"""Valida Análise por Posição + Gerador em todas as modalidades (subprocess isolado)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

APPS = [
    ("AnalisePorPosicao-SuperSete-Only", "supersete", 7),
    ("AnalisePorPosicao-Lotofacil-Only", "lotofacil", 15),
    ("AnalisePorPosicao-Timemania-Only", "timemania", 10),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria", 6),
    ("AnalisePorPosicao-MegaSena-Only", "megasena", 6),
    ("AnalisePorPosicao-Quina-Only", "quina", 5),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena", 6),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania", 20),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diadesorte", 7),
]

SNIPPET = """
import json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..', '_shared')))
from app import create_app
app = create_app()
out = {{'ok': True, 'checks': {{}}, 'key': '{key}', 'expected_n': {expected_n}}}
with app.test_client() as c:
    for name, url in [
        ('analise_page', '/analise/por-posicao/'),
        ('gerador_page', '/geradores-elite/gerador-por-posicao/'),
        ('concursos_api', '/analise/api/por-posicao/concursos'),
        ('analise_api', '/geradores-elite/api/posicao/analise?janela=20'),
    ]:
        r = c.get(url)
        if name.endswith('_page'):
            out['checks'][name] = r.status_code == 200
        elif name == 'concursos_api':
            j = r.get_json() or {{}}
            out['checks'][name] = r.status_code == 200 and j.get('status') == 'success'
        else:
            j = r.get_json() or {{}}
            out['checks'][name] = r.status_code == 200 and j.get('sucesso') is True
        if not out['checks'][name]:
            out['ok'] = False
    r = c.post('/geradores-elite/api/posicao/gerar', json={{'quantidade': 1, 'preset': 'manual', 'janela': 30}})
    j = r.get_json() or {{}}
    n = len((j.get('apostas') or [{{}}])[0].get('dezenas_ordem') or [])
    out['checks']['gerar_api'] = r.status_code == 200 and j.get('sucesso') and n == {expected_n}
    out['n_pos'] = n
    if j.get('apostas'):
        out['sample'] = j['apostas'][0].get('dezenas_ordem_fmt')
    if not out['checks']['gerar_api']:
        out['ok'] = False
        out['erro'] = j.get('erro') or ('n=' + str(n) + ' esperado {expected_n}')
    if '{key}' == 'duplasena':
        r2 = c.post('/geradores-elite/api/posicao/gerar', json={{'quantidade': 1, 'sorteio': 2, 'janela': 30}})
        j2 = r2.get_json() or {{}}
        n2 = len((j2.get('apostas') or [{{}}])[0].get('dezenas_ordem') or [])
        out['checks']['gerar_sorteio2'] = r2.status_code == 200 and j2.get('sucesso') and n2 == 6
        if not out['checks']['gerar_sorteio2']:
            out['ok'] = False
print(json.dumps(out))
"""


def validate_one(folder: str, key: str, expected_n: int) -> dict:
    app_dir = os.path.join(BASE, folder)
    code = SNIPPET.format(key=key, expected_n=expected_n)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=app_dir,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if proc.returncode != 0:
        return {"key": key, "ok": False, "erro": (proc.stderr or proc.stdout)[-500:]}
    line = proc.stdout.strip().splitlines()[-1]
    return json.loads(line)


def main():
    results = []
    for folder, key, n in APPS:
        print(f"Validando {key}...", flush=True)
        results.append(validate_one(folder, key, n))

    print("\n" + "=" * 60)
    ok_count = sum(1 for r in results if r.get("ok"))
    for r in results:
        status = "OK" if r.get("ok") else "FALHA"
        print(f"[{status}] {r.get('key', '?')}")
        for k, v in r.get("checks", {}).items():
            print(f"    {'OK' if v else 'X'} {k}")
        if r.get("sample"):
            print(f"    amostra ({r.get('n_pos')} pos): {r['sample']}")
        if r.get("erro"):
            print(f"    erro: {r['erro']}")
    print("=" * 60)
    print(f"Total: {ok_count}/{len(results)} modalidades OK")
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
