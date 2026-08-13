"""Parse do Excel Dia de Sorte até a 2ª faixa (6 acertos)."""
from __future__ import annotations

from typing import Any, Dict, List

from .normalize import parse_int, parse_reais, pick, split_localidades


def parse_linha_diadesorte(row: Dict[str, Any]) -> Dict[str, Any] | None:
    conc = parse_int(pick(row, "Concurso"))
    if not conc:
        return None
    bolas = []
    for i in range(1, 8):
        n = parse_int(pick(row, f"Bola{i}", f"Bola {i}"))
        bolas.append(n)
    return {
        "concurso": conc,
        "data": str(pick(row, "Data Sorteio", "Data") or "").strip(),
        "bolas": bolas,
        "mes_sorte": str(pick(row, "Mês da Sorte", "Mes da Sorte") or "").strip(),
        "ganhadores_7": parse_int(pick(row, "Ganhadores 7 acertos")) or 0,
        "rateio_7": parse_reais(pick(row, "Rateio 7 acertos")) or 0.0,
        "ganhadores_6": parse_int(pick(row, "Ganhadores 6 acertos")) or 0,
        "rateio_6": parse_reais(pick(row, "Rateio 6 acertos")) or 0.0,
        "localidades": split_localidades(pick(row, "Cidade / UF", "Cidade/UF")),
    }


def parse_planilha_diadesorte(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        rec = parse_linha_diadesorte(row)
        if not rec or rec["concurso"] in seen:
            continue
        seen.add(rec["concurso"])
        out.append(rec)
    out.sort(key=lambda r: r["concurso"])
    return out
