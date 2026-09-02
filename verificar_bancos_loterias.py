#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verifica status dos bancos SQLite (somente leitura, sem Flask).
Rode na pasta LoteriasPosicao:

  python verificar_bancos_loterias.py
"""
import os
import sqlite3

import certifi
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

# (nome, pasta do app, slug API Caixa, tabela SQLite, porta)
# Todas as modalidades do Dashboard Master (5152–5160)
MODALIDADES = [
    ("Lotofácil", "AnalisePorPosicao-Lotofacil-Only", "lotofacil", "sorteio_lotofacil", 5152),
    ("Super Sete", "AnalisePorPosicao-SuperSete-Only", "supersete", "sorteio_supersete", 5160),
    ("Lotomania", "AnalisePorPosicao-Lotomania-Only", "lotomania", "sorteio_lotomania", 5154),
    ("Quina", "AnalisePorPosicao-Quina-Only", "quina", "sorteio_quina", 5155),
    ("Mega Sena", "AnalisePorPosicao-MegaSena-Only", "megasena", "sorteio_megasena", 5156),
    ("+Milionária", "AnalisePorPosicao-MaisMilionaria-Only", "maismilionaria", "sorteio_maismilionaria", 5157),
    ("Dupla Sena", "AnalisePorPosicao-DuplaSena-Only", "duplasena", "sorteio_duplasena", 5158),
    ("Timemania", "AnalisePorPosicao-Timemania-Only", "timemania", "sorteio_timemania", 5159),
    ("Dia de Sorte", "AnalisePorPosicao--DiaDeSorte-Only", "diadesorte", "sorteio_diadesorte", 5153),
]


def api_ultimo(slug, timeout=12):
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=certifi.where())
        if r.status_code != 200:
            return 0
        d = r.json()
        return int(d.get("numero") or d.get("numeroConcurso") or 0)
    except Exception:
        return 0


def status_sqlite(db_path, tabela, ultimo_api):
    if not os.path.isfile(db_path):
        return {"erro": f"Arquivo não encontrado: {db_path}"}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (tabela,),
        )
        if not cur.fetchone():
            return {"erro": f"Tabela '{tabela}' não existe no banco."}

        cur.execute(f"SELECT COUNT(*), MIN(concurso), MAX(concurso) FROM {tabela}")
        total, mn, mx = cur.fetchone()
        total = total or 0
        mn = mn or 0
        mx = mx or 0

        grav = 0
        if ultimo_api:
            cur.execute(
                f"SELECT COUNT(*) FROM {tabela} WHERE concurso >= 1 AND concurso <= ?",
                (ultimo_api,),
            )
            grav = cur.fetchone()[0] or 0

        falt = max(0, (ultimo_api or 0) - grav) if ultimo_api else 0
        ok = falt == 0 and total > 0 and mn == 1 and ultimo_api > 0

        return {
            "total": total,
            "min": mn,
            "max": mx,
            "faltantes": falt,
            "ok": ok,
        }
    finally:
        conn.close()


def main():
    print("=" * 72)
    print("VERIFICAÇÃO DE BANCOS — LoteriasPosicao (somente leitura)")
    print("=" * 72)

    for nome, pasta, slug, tabela, porta in MODALIDADES:
        db_path = os.path.join(BASE, pasta, "instance", f"{slug}.db")

        ultimo_api = api_ultimo(slug)
        st = status_sqlite(db_path, tabela, ultimo_api)

        if "erro" in st:
            print(f"\n[ERRO] {nome} (porta {porta})")
            print(f"  {st['erro']}")
            print(f"  Caminho: {db_path}")
            continue

        flag = "OK" if st["ok"] else "FALTANDO"
        print(f"\n[{flag}] {nome} (porta {porta})")
        print(f"  Banco: {db_path}")
        print(f"  API último: #{ultimo_api or '?'}")
        print(
            f"  Gravados: {st['total']:,}  |  faixa #{st['min']} a #{st['max']}  |  faltantes: {st['faltantes']:,}"
        )
        if not st["ok"] and ultimo_api:
            script_cli = os.path.join(BASE, pasta, f"sincronizar_{slug}_completo.py")
            if os.path.isfile(script_cli):
                print(f"  -> cd {pasta}")
                print(f"     python sincronizar_{slug}_completo.py")
            else:
                print(f"  -> Sincronize pela UI: http://localhost:{porta}/")
                print(f"     (script CLI ainda não existe para {nome})")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
