#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Backfill mes_num / mes_nome — Dia de Sorte.

Preenche o mês da sorte consultando a API Caixa.
Necessário para o panorama MS (análise e gerador Panorama Top-3).

Uso:
  python backfill_meses_diadesorte.py
  python backfill_meses_diadesorte.py --limite 100
  python backfill_meses_diadesorte.py --loop
"""
from __future__ import annotations

import argparse
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app
from services.api_diadesorte_service import ApiDiaDeSorteService


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill mês da sorte — Dia de Sorte")
    p.add_argument("--limite", type=int, default=80, help="Concursos por lote (máx. 200)")
    p.add_argument(
        "--loop",
        action="store_true",
        help="Repetir lotes até preencher todos ou falha",
    )
    p.add_argument("--pausa", type=float, default=0.35, help="Pausa entre lotes (segundos)")
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("BACKFILL mes_num / mes_nome — Mês da Sorte")
        print("Banco: instance/diadesorte.db")
        print("=" * 60)

        total_proc = 0
        while True:
            st_antes = ApiDiaDeSorteService.status_meses()
            print(
                f"\nPendentes: {st_antes['meses_pendentes']:,} | "
                f"Com mês: {st_antes['meses_preenchidos']:,}"
            )
            if st_antes["completo"]:
                print("\nBase já completa — todos os concursos têm mês da sorte.")
                return 0

            r = ApiDiaDeSorteService.backfill_meses(limite=args.limite)
            total_proc += r.get("processados", 0)
            print(r.get("message", ""))
            print(
                f"Lote: {r.get('sucessos', 0)} ok, {r.get('falhas', 0)} falhas | "
                f"Restam: {r.get('pendentes_restantes', 0):,}"
            )

            if r.get("falhas", 0) and not r.get("sucessos", 0):
                print("\nERRO: lote sem sucessos — interrompido.")
                return 2

            if not args.loop or not r.get("continuar"):
                st = ApiDiaDeSorteService.status_meses()
                print("\n--- Resumo ---")
                print(f"Total concursos: {st['total_concursos']:,}")
                print(f"Com mês:         {st['meses_preenchidos']:,}")
                print(f"Pendentes:       {st['meses_pendentes']:,}")
                print(f"Processados nesta execução: {total_proc}")
                return 0

            time.sleep(max(0.1, args.pausa))


if __name__ == "__main__":
    raise SystemExit(main())
