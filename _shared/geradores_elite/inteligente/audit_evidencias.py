# -*- coding: utf-8 -*-
"""
Auditoria do painel de evidências — compara API inteligente vs serviço de repetição.
Uso: python audit_evidencias.py
Exclui: lotofacil, supersete.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_SHARED = os.path.join(ROOT, "_shared")

APPS = [
    ("AnalisePorPosicao-Quina-Only", "quina", 5155),
    ("AnalisePorPosicao-MegaSena-Only", "megasena", 5156),
    ("AnalisePorPosicao-Lotomania-Only", "lotomania", 5154),
    ("AnalisePorPosicao-DuplaSena-Only", "duplasena", 5158),
    ("AnalisePorPosicao--DiaDeSorte-Only", "diadesorte", 5153),
    ("AnalisePorPosicao-Timemania-Only", "timemania", 5159),
    ("AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria", 5157),
]

_WORKER = r'''
import json, os, sys
app_dir = sys.argv[1]
key = sys.argv[2]
shared = sys.argv[3]
sys.path.insert(0, shared)
sys.path.insert(0, app_dir)
os.chdir(app_dir)

from app import create_app
from analise_repeticao.repeticao_service import RepeticaoConcursosService
from geradores_elite.inteligente import get_inteligente_service
from geradores_elite.inteligente.faixas_config import contar_faixas_volante

app = create_app()
errors = []
summary = {}
with app.app_context():
    svc_cls = get_inteligente_service(key)
    raw = RepeticaoConcursosService(key)
    modo = getattr(svc_cls, "modo_analise", "volante")
    analise = raw.analisar_completo(modo)
    if not analise.get("sucesso"):
        print(json.dumps({"ok": False, "errors": [analise.get("erro")], "summary": {}}))
        raise SystemExit(0)
    api = svc_cls.analise_completa_api()
    if not api.get("sucesso"):
        print(json.dumps({"ok": False, "errors": [api.get("erro")], "summary": {}}))
        raise SystemExit(0)
    ev = api["evidencias"]
    rep = ev["repeticoes"]
    resumo = analise["resumo_ultimo_par"]
    vol, pos = resumo["volante"], resumo["posicional"]
    for nome, got, exp in [
        ("ultimo_par_volante", rep["ultimo_par_volante"]["qtd"], len(vol["dezenas"])),
        ("ultimo_par_posicional", rep["ultimo_par_posicional"]["qtd"], int(pos["quantidade"])),
        ("media_volante", rep["media_volante"]["qtd"], int(round(float(resumo["media_historica_quantidade_volante"])))),
        ("media_posicional", rep["media_posicional"]["qtd"], int(round(float(resumo["media_historica_posicional"])))),
    ]:
        if got != exp:
            errors.append(f"{nome} painel={got} servico={exp}")
    faixas_api = {t["chave"]: t["vezes"] for t in ev.get("tipos_sorteio") or []}
    faixas_ref = contar_faixas_volante(raw, key)
    if faixas_api != faixas_ref:
        errors.append(f"faixas painel={faixas_api} ref={faixas_ref}")
    total_pares = int(analise.get("total_pares_analisados") or 0)
    if sum(faixas_ref.values()) != total_pares:
        errors.append(f"soma faixas != {total_pares}")
    rank_api = [x["dezena"] for x in ev.get("numeros_fortes") or []]
    rank_ref = [r["dezena"] for r in (analise.get("ranking_mais_repetem") or [])[:3]]
    if rank_api != rank_ref:
        errors.append(f"ranking {rank_api} vs {rank_ref}")
    top = (ev.get("tipos_sorteio") or [{}])[0]
    summary = {
        "pares": total_pares,
        "ult_vol": rep["ultimo_par_volante"]["qtd"],
        "med_vol": rep["media_volante"]["qtd"],
        "faixa_top": f"{top.get('label')}={top.get('vezes')}",
    }
print(json.dumps({"ok": not errors, "errors": errors, "summary": summary}))
'''


def main() -> int:
    all_errors: list[str] = []
    report: list[str] = []

    for folder, key, porta in APPS:
        app_dir = os.path.join(ROOT, folder)
        if not os.path.isdir(app_dir):
            all_errors.append(f"SKIP {folder}")
            continue
        proc = subprocess.run(
            [sys.executable, "-c", _WORKER, app_dir, key, _SHARED],
            capture_output=True,
            text=True,
            cwd=app_dir,
        )
        if proc.returncode != 0:
            all_errors.append(f"{key}: subprocess falhou — {proc.stderr[:300]}")
            continue
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            all_errors.append(f"{key}: saída inválida — {proc.stdout[:200]}")
            continue
        if not data.get("ok"):
            for e in data.get("errors") or []:
                all_errors.append(f"{key}: {e}")
        s = data.get("summary") or {}
        if s:
            report.append(
                f"{key} ({porta}): pares={s.get('pares')} "
                f"últ.vol={s.get('ult_vol')} méd.vol={s.get('med_vol')} "
                f"faixa-top={s.get('faixa_top')}"
            )

    print("=== Resumo ===")
    for line in report:
        print(line)
    if all_errors:
        print("\n=== FALHAS ===")
        for e in all_errors:
            print(" -", e)
        return 1
    print("\nOK — painel consistente com o serviço de repetição (7 modalidades).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
