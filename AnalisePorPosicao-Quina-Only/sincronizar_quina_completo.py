#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Popular banco Quina (SQLite) — mesmo padrão Mega-Sena (5156).
Preenche TODOS os concursos faltantes de 1 até o último oficial da Caixa.

Uso (PowerShell):
  cd D:/loterias/LoteriasPosicao/AnalisePorPosicao-Quina-Only
  python sincronizar_quina_completo.py

Se parar por timeout, rode de novo — continua de onde parou.
"""
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
from models.sorteio_quina import SorteioQuina

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/quina/"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

TIMEOUT = 30
MAX_RETRIES = 4


def _get(url, timeout=TIMEOUT):
    kwargs = {"headers": HEADERS, "timeout": timeout}
    try:
        return requests.get(url, verify=certifi.where(), **kwargs)
    except requests.exceptions.SSLError:
        return requests.get(url, verify=False, **kwargs)


def _get_com_retry(url, timeout=TIMEOUT, retries=MAX_RETRIES):
    ultimo_erro = None
    for tentativa in range(1, retries + 1):
        try:
            r = _get(url, timeout=timeout)
            return r
        except RequestException as e:
            ultimo_erro = e
            espera = min(2 ** tentativa, 20)
            print(f" [timeout/erro, tentativa {tentativa}/{retries}, aguarda {espera}s]", flush=True)
            time.sleep(espera)
    raise ultimo_erro


def buscar_ultimo_concurso(timeout=TIMEOUT):
    try:
        r = _get_com_retry(API_URL, timeout=timeout)
        if r.status_code != 200:
            return 0
        data = r.json()
        return int(data.get("numero") or data.get("numeroConcurso") or 0)
    except RequestException as e:
        print(f"[API Caixa] Erro ao buscar último concurso: {e}")
        return 0


def buscar_concurso(numero, timeout=TIMEOUT):
    try:
        r = _get_com_retry(f"{API_URL}{numero}", timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except RequestException:
        return None


def concursos_no_banco():
    rows = db.session.query(SorteioQuina.concurso).all()
    return {r[0] for r in rows}


def salvar_concurso(concurso, dados):
    raw = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas")
    if not raw or len(raw) != 5:
        return False
    dez = [int(d) for d in raw]
    db.session.merge(
        SorteioQuina(
            concurso=concurso,
            data=dados.get("dataApuracao", "") or dados.get("data", ""),
            d1=dez[0],
            d2=dez[1],
            d3=dez[2],
            d4=dez[3],
            d5=dez[4],
        )
    )
    return True


def status_banco(ultimo_oficial):
    total = SorteioQuina.query.count()
    min_local = db.session.query(db.func.min(SorteioQuina.concurso)).scalar() or 0
    max_local = db.session.query(db.func.max(SorteioQuina.concurso)).scalar() or 0
    presentes = concursos_no_banco()
    faltantes = sum(1 for i in range(1, ultimo_oficial + 1) if i not in presentes)
    completo = faltantes == 0 and total > 0 and min_local == 1
    return {
        "total": total,
        "min": min_local,
        "max": max_local,
        "faltantes": faltantes,
        "completo": completo,
    }


def sincronizar_lote(faltantes, limite, timeout=TIMEOUT):
    lote = faltantes[:limite]
    ok = fail = 0
    for concurso in lote:
        print(f"[API Caixa] Quina {concurso}...", end="", flush=True)
        try:
            dados = buscar_concurso(concurso, timeout=timeout)
            if dados and salvar_concurso(concurso, dados):
                db.session.commit()
                ok += 1
                print(" [OK]")
            else:
                db.session.rollback()
                fail += 1
                print(" [FALHOU]")
        except Exception as e:
            db.session.rollback()
            fail += 1
            print(f" [ERRO: {e}]")
        time.sleep(0.15)
    return ok, fail, len(lote)


def main():
    parser = argparse.ArgumentParser(description="Sincronizar histórico completo da Quina")
    parser.add_argument("--limite", type=int, default=80, help="Concursos por lote (padrão: 80)")
    parser.add_argument("--teto", type=int, default=0, help="Forçar último concurso (ex: 7034)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout HTTP em segundos (padrão: 30)")
    args = parser.parse_args()
    limite = max(1, min(args.limite, 200))
    timeout = max(10, min(args.timeout, 120))
    global TIMEOUT
    TIMEOUT = timeout

    app = create_app()
    with app.app_context():
        db.create_all()

        ultimo = args.teto or buscar_ultimo_concurso()
        if not ultimo:
            print("ERRO: não foi possível consultar a API da Caixa.")
            return 1

        print("=" * 60)
        print("SINCRONIZAÇÃO QUINA — histórico completo (padrão Mega-Sena)")
        print(f"Banco: instance/quina.db")
        print(f"Último oficial: #{ultimo}")
        print(f"Lote: {limite} concursos por vez")
        print("=" * 60)

        st = status_banco(ultimo)
        print(f"No banco agora: {st['total']} registros (#{st['min']} a #{st['max']})")
        print(f"Faltantes no intervalo 1..{ultimo}: {st['faltantes']}")

        if st["completo"]:
            print(f"\nBase já completa: {st['total']} concursos (1 a {ultimo}).")
            return 0

        total_importado = 0
        while True:
            presentes = concursos_no_banco()
            faltantes = [i for i in range(1, ultimo + 1) if i not in presentes]
            if not faltantes:
                break

            print(f"\n--- Lote: faltam {len(faltantes)} ---")
            ok, fail, _proc = sincronizar_lote(faltantes, limite, timeout=timeout)
            total_importado += ok
            st = status_banco(ultimo)
            print(f"Lote: {ok} ok, {fail} falhas | Total no banco: {st['total']} | Restam: {st['faltantes']}")
            if fail and ok == 0:
                print("Pausa: lote inteiro falhou. Rode o script de novo em alguns minutos.")
                return 2
            time.sleep(0.5)

        st = status_banco(ultimo)
        print("\n" + "=" * 60)
        print(f"CONCLUÍDO — Base completa: {st['total']} concursos (1 a {ultimo})")
        print(f"Importados nesta execução: {total_importado}")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
