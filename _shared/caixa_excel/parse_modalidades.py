# -*- coding: utf-8 -*-
"""Parsers do Excel CAIXA por modalidade — só premiação complementar.

As dezenas/bolas lidas do Excel NÃO devem ser gravadas em sorteio_*.
Servem apenas de auditoria no payload (bolas_excel).
Loteria Federal está fora do escopo.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .normalize import parse_int, parse_reais, pick, split_localidades
from .parse_diadesorte import parse_planilha_diadesorte


def _data(row: Dict[str, Any]) -> str:
    return str(pick(row, "Data Sorteio", "Data do Sorteio", "Data") or "").strip()


def _faixa(row: Dict[str, Any], ganha: Tuple[str, ...], rateio: Tuple[str, ...], nome: str) -> Dict[str, Any]:
    return {
        "nome": nome,
        "ganhadores": parse_int(pick(row, *ganha)) or 0,
        "rateio": parse_reais(pick(row, *rateio)) or 0.0,
    }


def _base(row: Dict[str, Any], bolas: List[Optional[int]]) -> Optional[Dict[str, Any]]:
    conc = parse_int(pick(row, "Concurso"))
    if not conc:
        return None
    return {
        "concurso": conc,
        "data": _data(row),
        "bolas_excel": [b for b in bolas if b is not None],
        "localidades": split_localidades(pick(row, "Cidade / UF", "Cidade/UF")),
        "faixas": [],
        "extras": {},
    }


def _bolas(row: Dict[str, Any], n: int, prefix: str = "Bola") -> List[Optional[int]]:
    out: List[Optional[int]] = []
    for i in range(1, n + 1):
        out.append(parse_int(pick(row, f"{prefix}{i}", f"{prefix} {i}")))
    return out


def parse_megasena(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _base(row, _bolas(row, 6))
    if not rec:
        return None
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 6 acertos",), ("Rateio 6 acertos",), "6 acertos"),
        _faixa(row, ("Ganhadores 5 acertos",), ("Rateio 5 acertos",), "5 acertos"),
        _faixa(row, ("Ganhadores 4 acertos",), ("Rateio 4 acertos",), "4 acertos"),
    ]
    return rec


def parse_lotofacil(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _base(row, _bolas(row, 15))
    if not rec:
        return None
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 15 acertos",), ("Rateio 15 acertos",), "15 acertos"),
        _faixa(row, ("Ganhadores 14 acertos",), ("Rateio 14 acertos",), "14 acertos"),
        _faixa(row, ("Ganhadores 13 acertos",), ("Rateio 13 acertos",), "13 acertos"),
        _faixa(row, ("Ganhadores 12 acertos",), ("Rateio 12 acertos",), "12 acertos"),
        _faixa(row, ("Ganhadores 11 acertos",), ("Rateio 11 acertos",), "11 acertos"),
    ]
    return rec


def parse_quina(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _base(row, _bolas(row, 5))
    if not rec:
        return None
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 5 acertos",), ("Rateio 5 acertos",), "5 acertos"),
        _faixa(row, ("Ganhadores 4 acertos",), ("Rateio 4 acertos",), "4 acertos"),
        _faixa(row, ("Ganhadores 3 acertos",), ("Rateio 3 acertos",), "3 acertos"),
        _faixa(row, ("Ganhadores 2 acertos",), ("Rateio 2 acertos",), "2 acertos"),
    ]
    return rec


def parse_lotomania(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _base(row, _bolas(row, 20))
    if not rec:
        return None
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 20 acertos",), ("Rateio 20 acertos",), "20 acertos"),
        _faixa(row, ("Ganhadores 19 acertos",), ("Rateio 19 acertos",), "19 acertos"),
        _faixa(row, ("Ganhadores 18 acertos",), ("Rateio 18 acertos",), "18 acertos"),
        _faixa(row, ("Ganhadores 17 acertos",), ("Rateio 17 acertos",), "17 acertos"),
        _faixa(row, ("Ganhadores 16 acertos",), ("Rateio 16 acertos",), "16 acertos"),
        _faixa(row, ("Ganhadores 15 acertos",), ("Rateio 15 acertos",), "15 acertos"),
        _faixa(
            row,
            ("Ganhadores Nenhum Número", "Ganhadores Nenhum Numero"),
            ("Rateio Nenhum Número", "Rateio Nenhum Numero"),
            "0 acertos",
        ),
    ]
    return rec


def parse_timemania(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _base(row, _bolas(row, 7))
    if not rec:
        return None
    rec["extras"]["time_coracao"] = str(pick(row, "Time Coração", "Time Coracao") or "").strip()
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 7 acertos",), ("Rateio 7 acertos",), "7 acertos"),
        _faixa(row, ("Ganhadores 6 acertos",), ("Rateio 6 acertos",), "6 acertos"),
        _faixa(row, ("Ganhadores 5 acertos",), ("Rateio 5 acertos",), "5 acertos"),
        _faixa(row, ("Ganhadores 4 acertos",), ("Rateio 4 acertos",), "4 acertos"),
        _faixa(row, ("Ganhadores 3 acertos",), ("Rateio 3 acertos",), "3 acertos"),
        _faixa(row, ("Ganhadores Time Coração", "Ganhadores Time Coracao"), ("Rateio Time Coração", "Rateio Time Coracao"), "Time"),
    ]
    return rec


def parse_duplasena(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    s1 = [
        parse_int(pick(row, f"Bola{i} sorteio 1", f"Bola{i} Sorteio 1", f"Bola{i} sorteio1"))
        for i in range(1, 7)
    ]
    s2 = [
        parse_int(pick(row, f"Bola{i} sorteio 2", f"Bola{i} Sorteio 2", f"Bola{i} sorteio2"))
        for i in range(1, 7)
    ]
    rec = _base(row, [b for b in s1 if b is not None])
    if not rec:
        return None
    rec["extras"]["bolas_excel_s1"] = [b for b in s1 if b is not None]
    rec["extras"]["bolas_excel_s2"] = [b for b in s2 if b is not None]
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 6 acertos  Sorteio 1", "Ganhadores 6 acertos Sorteio 1"), ("Rateio 6 acertos  Sorteio1", "Rateio 6 acertos Sorteio 1"), "S1 6 acertos"),
        _faixa(row, ("Ganhadores 5   acertos Sorteio1", "Ganhadores 5 acertos Sorteio1"), ("Rateio 5 acertos Sorteio1",), "S1 5 acertos"),
        _faixa(row, ("Ganhadores 4 acertos Sorteio1",), ("Rateio 4 acertos Sorteio1",), "S1 4 acertos"),
        _faixa(row, ("Ganhadores 3 acertos Sorteio1",), ("Rateio 3 acertos Sorteio1",), "S1 3 acertos"),
        _faixa(row, ("Ganhadores 6 acertos Sorteio2",), ("Rateio 6 acertos  Sorteio 2", "Rateio 6 acertos Sorteio 2"), "S2 6 acertos"),
        _faixa(row, ("Ganhadores 5 acertos Sorteio2",), ("Rateio 5 acertos Sorteio 2", "Rateio 5 acertos Sorteio2"), "S2 5 acertos"),
        _faixa(row, ("Ganhadores 4 acertos Sorteio2",), ("Rateio 4 acertos Sorteio 2", "Rateio 4 acertos Sorteio2"), "S2 4 acertos"),
        _faixa(row, ("Ganhadores 3 acertos Sorteio2",), ("Rateio 3 acertos Sorteio 2", "Rateio 3 acertos Sorteio2"), "S2 3 acertos"),
    ]
    return rec


def parse_supersete(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cols = [parse_int(pick(row, f"Coluna {i}", f"Coluna{i}")) for i in range(1, 8)]
    rec = _base(row, [c for c in cols if c is not None])
    if not rec:
        return None
    rec["extras"]["colunas_excel"] = cols
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 7 acertos",), ("Rateio 7 acertos",), "7 acertos"),
        _faixa(row, ("Ganhadores 6 acertos",), ("Rateio 6 acertos",), "6 acertos"),
        _faixa(row, ("Ganhadores 5 acertos",), ("Rateio 5 acertos",), "5 acertos"),
        _faixa(row, ("Ganhadores 4 acertos",), ("Rateio 4 acertos",), "4 acertos"),
        _faixa(row, ("Ganhadores 3 acertos",), ("Rateio 3 acertos",), "3 acertos"),
    ]
    return rec


def parse_maismilionaria(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rec = _base(row, _bolas(row, 6))
    if not rec:
        return None
    rec["extras"]["trevo1"] = parse_int(pick(row, "Trevo1", "Trevo 1"))
    rec["extras"]["trevo2"] = parse_int(pick(row, "Trevo2", "Trevo 2"))
    rec["faixas"] = [
        _faixa(row, ("Ganhadores 6 Números + 2 Trevos", "Ganhadores 6 Numeros + 2 Trevos"), ("Rateio 6 acertos + 2 Trevos",), "6+2 trevos"),
        _faixa(row, ("Ganhadores 6  acertos + 1 ou nenhum Trevo",), ("Rateio 6  acertos + 1  ou nenhum Trevo",), "6 dez"),
        _faixa(row, ("Ganhadores 5  acertos + 2 Trevos",), ("Rateio 5  acertos + 2 Trevos",), "5+2 trevos"),
        _faixa(row, ("Ganhadores 5 acertos + 1 ou nenhum Trevo",), ("Rateio 5  acertos + 1 ou nenhum Trevo",), "5 dez"),
        _faixa(row, ("Ganhadores 4  acertos + 2 Trevos",), ("Rateio 4  acertos + 2 Trevos",), "4+2 trevos"),
        _faixa(row, ("Ganhadores 4  acertos + 1 ou nenhum Trevo",), ("Rateio 4  acertos + 1 ou nenhum Trevo",), "4 dez"),
        _faixa(row, ("Ganhadores 3  acertos + 2 Trevos",), ("Rateio 3  acertos + 2 Trevos",), "3+2 trevos"),
        _faixa(row, ("Ganhadores 3  acertos + 1 Trevo",), ("Rateio 3  acertos + 1 Trevo",), "3+1 trevo"),
        _faixa(row, ("Ganhadores 2  acertos + 2 Trevos",), ("Rateio 2  acertos + 2 Trevos",), "2+2 trevos"),
        _faixa(row, ("Ganhadores 2  acertos + 1 Trevo",), ("Rateio 2  acertos + 1 Trevo",), "2+1 trevo"),
    ]
    return rec


def parse_diadesorte_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Adapta o parser histórico do Dia de Sorte ao formato complementar."""
    out: List[Dict[str, Any]] = []
    for rec in parse_planilha_diadesorte(rows):
        out.append({
            "concurso": rec["concurso"],
            "data": rec.get("data") or "",
            "bolas_excel": rec.get("bolas") or [],
            "localidades": rec.get("localidades") or [],
            "faixas": [
                {"nome": "7 acertos", "ganhadores": rec.get("ganhadores_7") or 0, "rateio": rec.get("rateio_7") or 0.0},
                {"nome": "6 acertos", "ganhadores": rec.get("ganhadores_6") or 0, "rateio": rec.get("rateio_6") or 0.0},
            ],
            "extras": {"mes_sorte": rec.get("mes_sorte") or ""},
        })
    return out


_ROW_PARSERS: Dict[str, Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = {
    "megasena": parse_megasena,
    "lotofacil": parse_lotofacil,
    "quina": parse_quina,
    "lotomania": parse_lotomania,
    "timemania": parse_timemania,
    "duplasena": parse_duplasena,
    "supersete": parse_supersete,
    "maismilionaria": parse_maismilionaria,
}


def parse_planilha(key: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    key = (key or "").strip().lower()
    if key == "diadesorte":
        return parse_diadesorte_rows(rows)
    fn = _ROW_PARSERS.get(key)
    if not fn:
        raise ValueError(f"Modalidade sem parser Excel complementar: {key}")
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        rec = fn(row)
        if not rec or rec["concurso"] in seen:
            continue
        seen.add(rec["concurso"])
        out.append(rec)
    out.sort(key=lambda r: r["concurso"])
    return out
