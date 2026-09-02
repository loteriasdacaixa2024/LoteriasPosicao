#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Backfill ganhadores_7 — Dia de Sorte.

Preenche a coluna ganhadores_7 (faixa principal, 7 acertos) consultando a API Caixa.
Necessário para as abas Vencedores / Acumulados da análise comportamental.

Uso:
  python backfill_ganhadores_diadesorte.py
  python backfill_ganhadores_diadesorte.py --limite 100
  python backfill_ganhadores_diadesorte.py --loop
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
    p = argparse.ArgumentParser(description="Backfill ganhadores_7 — Dia de Sorte")
    p.add_argument("--limite", type=int, default=80, help="Concursos por lote (máx. 200)")
    p.add_argument(
        "--loop",
        action="store_true",
        help="Repetir lotes até preencher todos ou falha",
    )
    p.add_argument("--pausa", type=float, default=0.35, help="Pausa entre lotes (segundos)")
    p.add_argument(
        "--pausa-entre",
        type=float,
        default=0.45,
        help="Pausa entre cada concurso dentro do lote (segundos)",
    )
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("BACKFILL ganhadores_7 — faixa principal (7 acertos)")
        print("Banco: instance/diadesorte.db")
        print("=" * 60)

        total_proc = 0
        while True:
            st_antes = ApiDiaDeSorteService.status_ganhadores()
            print(
                f"\nPendentes: {st_antes['ganhadores_pendentes']:,} | "
                f"Com vencedor: {st_antes['concursos_com_vencedor_7']:,} | "
                f"Acumulados: {st_antes['concursos_acumulados_7']:,}"
            )
            if st_antes["completo"]:
                print("\nBase já completa — todos os concursos têm ganhadores_7.")
                return 0

            r = ApiDiaDeSorteService.backfill_ganhadores(
                limite=args.limite,
                pausa_entre=args.pausa_entre,
            )
            total_proc += r.get("processados", 0)
            print(r.get("message", ""))
            print(
                f"Lote: {r.get('sucessos', 0)} ok, {r.get('falhas', 0)} falhas | "
                f"Restam: {r.get('pendentes_restantes', 0):,}"
            )

            if r.get("falhas", 0) and not r.get("sucessos", 0):
                print("\nAVISO: lote sem sucessos (API pode estar limitando). Aguardando 30s...")
                time.sleep(30)
                continue

            if not args.loop or not r.get("continuar"):
                st = ApiDiaDeSorteService.status_ganhadores()
                print("\n--- Resumo ---")
                print(f"Total concursos: {st['total_concursos']:,}")
                print(f"Preenchidos:     {st['ganhadores_preenchidos']:,}")
                print(f"Pendentes:       {st['ganhadores_pendentes']:,}")
                print(f"Com vencedor 7:  {st['concursos_com_vencedor_7']:,}")
                print(f"Acumulados 7:    {st['concursos_acumulados_7']:,}")
                soma = st["concursos_com_vencedor_7"] + st["concursos_acumulados_7"]
                if st["ganhadores_preenchidos"] and soma == st["ganhadores_preenchidos"]:
                    print("Validação OK: vencedores + acumulados = preenchidos")
                print(f"Processados nesta execução: {total_proc}")
                return 0

            time.sleep(max(0.1, args.pausa))


if __name__ == "__main__":
    raise SystemExit(main())
