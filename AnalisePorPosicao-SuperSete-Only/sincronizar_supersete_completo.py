#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Sincroniza histórico completo Super Sete (1..último API). Porta 5160."""
import argparse
import os
import sys
import time

import certifi
import requests
from requests.exceptions import RequestException

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from app import create_app
from models.shared import db
from models.sorteio_supersete import SorteioSuperSete

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/supersete/"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
TIMEOUT, MAX_RETRIES = 30, 4


def _get(url, timeout=TIMEOUT):
    kw = {"headers": HEADERS, "timeout": timeout}
    try:
        return requests.get(url, verify=certifi.where(), **kw)
    except requests.exceptions.SSLError:
        return requests.get(url, verify=False, **kw)


def _get_retry(url, timeout=TIMEOUT):
    for t in range(1, MAX_RETRIES + 1):
        try:
            return _get(url, timeout)
        except RequestException:
            if t == MAX_RETRIES:
                raise
            time.sleep(min(2 ** t, 20))
    return None


def ultimo_api(timeout=TIMEOUT):
    r = _get_retry(API_URL, timeout)
    if r.status_code != 200:
        return 0
    try:
        d = r.json()
    except ValueError:
        return 0
    return int(d.get("numero") or d.get("numeroConcurso") or 0)


def buscar(n, timeout=TIMEOUT):
    try:
        r = _get_retry(f"{API_URL}{n}", timeout)
        return r.json() if r.status_code == 200 else None
    except RequestException:
        return None


def presentes():
    return {r[0] for r in db.session.query(SorteioSuperSete.concurso).all()}


def salvar(concurso, dados):
    raw = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas")
    if not raw or len(raw) != 7:
        return False
    cols = [int(x) for x in raw]
    db.session.merge(SorteioSuperSete(
        concurso=concurso,
        data=dados.get("dataApuracao", "") or dados.get("data", ""),
        coluna_1=cols[0],
        coluna_2=cols[1],
        coluna_3=cols[2],
        coluna_4=cols[3],
        coluna_5=cols[4],
        coluna_6=cols[5],
        coluna_7=cols[6],
    ))
    return True


def status(ultimo):
    total = SorteioSuperSete.query.count()
    mn = db.session.query(db.func.min(SorteioSuperSete.concurso)).scalar() or 0
    mx = db.session.query(db.func.max(SorteioSuperSete.concurso)).scalar() or 0
    grav = db.session.query(SorteioSuperSete.concurso).filter(
        SorteioSuperSete.concurso >= 1, SorteioSuperSete.concurso <= ultimo
    ).count() if ultimo else 0
    falt = max(0, ultimo - grav) if ultimo else 0
    return total, mn, mx, falt, falt == 0 and total > 0 and mn == 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limite", type=int, default=80)
    p.add_argument("--teto", type=int, default=0)
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()
    limite = max(1, min(args.limite, 200))
    timeout = max(10, min(args.timeout, 120))

    app = create_app()
    with app.app_context():
        db.create_all()
        ultimo = args.teto or ultimo_api(timeout)
        if not ultimo:
            print("ERRO: API Caixa indisponível.")
            return 1
        print("=" * 60)
        print("SINCRONIZAÇÃO SUPER SETE — histórico completo")
        print("Banco: instance/supersete.db | Porta: 5160")
        print(f"Último oficial: #{ultimo} | Lote: {limite}")
        print("=" * 60)
        total, mn, mx, falt, ok = status(ultimo)
        print(f"No banco: {total:,} (#{mn} a #{mx}) | Faltantes: {falt:,}")
        if ok:
            print(f"\nBase já completa (1 a {ultimo}).")
            return 0
        imp = 0
        while True:
            faltantes = [i for i in range(1, ultimo + 1) if i not in presentes()]
            if not faltantes:
                break
            print(f"\n--- Lote: faltam {len(faltantes)} ---")
            ok_l = fail = 0
            for c in faltantes[:limite]:
                print(f"[API] Super Sete {c}...", end="", flush=True)
                try:
                    d = buscar(c, timeout)
                    if d and salvar(c, d):
                        db.session.commit()
                        ok_l += 1
                        print(" [OK]")
                    else:
                        db.session.rollback()
                        fail += 1
                        print(" [FALHOU]")
                except Exception as ex:
                    db.session.rollback()
                    fail += 1
                    print(f" [ERRO: {ex}]")
                time.sleep(0.12)
            imp += ok_l
            total, _, _, falt, _ = status(ultimo)
            print(f"Lote: {ok_l} ok, {fail} falhas | Total: {total:,} | Restam: {falt:,}")
            if fail and ok_l == 0:
                print("Pausa: rode de novo em alguns minutos.")
                return 2
            time.sleep(0.4)
        total, _, _, _, _ = status(ultimo)
        print(f"\nCONCLUÍDO — {total:,} concursos (1 a {ultimo}) | Importados: {imp}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
