# -*- coding: utf-8 -*-
"""Serviço genérico — comparar dois concursos (sorteio real)."""
from __future__ import annotations

import importlib
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import desc

from models.shared import db

from .compare_config import get_compare_config


def _pares_impares(dezenas: List[int]) -> Tuple[int, int]:
    p = sum(1 for d in dezenas if d % 2 == 0)
    return p, len(dezenas) - p


def _load_model(cfg: dict):
    mod = importlib.import_module(cfg["model_module"])
    return getattr(mod, cfg["model_class"])


def _dezenas_set(row: Any, cfg: dict, sorteio: int = 1) -> Set[int]:
    if cfg.get("dual_sorteio"):
        key = "sorteio1_set" if sorteio == 1 else "sorteio2_set"
        return set(getattr(row, cfg[key])())
    if cfg.get("set_method"):
        val = getattr(row, cfg["set_method"])()
        return set(val) if not isinstance(val, set) else val
    if cfg.get("ordered_fields"):
        return {getattr(row, f) for f in cfg["ordered_fields"]}
    raise ValueError("Config sem origem de dezenas")


def _dezenas_ordered(row: Any, cfg: dict, sorteio: int = 1) -> List[int]:
    if cfg.get("dual_sorteio"):
        key = "sorteio1_list" if sorteio == 1 else "sorteio2_list"
        return list(getattr(row, cfg[key])())
    if cfg.get("ordered_fields"):
        return [getattr(row, f) for f in cfg["ordered_fields"]]
    if cfg.get("display_method"):
        return list(getattr(row, cfg["display_method"])())
    if cfg.get("set_method"):
        val = getattr(row, cfg["set_method"])()
        return sorted(val) if isinstance(val, set) else list(val)
    raise ValueError("Config sem lista ordenada")


def _repetidas_posicional(ordered_a: List[int], ordered_b: List[int]) -> List[Dict[str, int]]:
    n = min(len(ordered_a), len(ordered_b))
    out = []
    for i in range(n):
        if ordered_a[i] == ordered_b[i]:
            out.append({"posicao": i + 1, "dezena": ordered_a[i]})
    return out


def _pack_concurso(row: Any, cfg: dict, sorteio: int = 1) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "concurso": row.concurso,
        "data": getattr(row, "data", None),
        "dezenas": sorted(_dezenas_set(row, cfg, sorteio)),
        "dezenas_exibicao": _dezenas_ordered(row, cfg, sorteio),
    }
    if cfg.get("extra_trevos"):
        payload["trevos"] = sorted(getattr(row, cfg["trevo_list_method"])())
    if cfg.get("extra_time"):
        payload["time_num"] = getattr(row, "time_num", None)
        payload["time_nome"] = getattr(row, "time_nome", None) or ""
    if cfg.get("extra_mes"):
        payload["mes_num"] = getattr(row, cfg.get("mes_field", "mes_num"), None)
        payload["mes_nome"] = getattr(row, cfg.get("mes_label_field", "mes_nome"), None) or ""
    if cfg.get("layout") == "colunas":
        payload["colunas"] = _dezenas_ordered(row, cfg, sorteio)
    return payload


def _build_grade_grid(
    cfg: dict,
    set_a: Set[int],
    set_b: Set[int],
    rep_v: Set[int],
    rep_p: Set[int],
    pos_map_a: Dict[int, int],
    pos_map_b: Dict[int, int],
) -> List[Dict[str, Any]]:
    grade = []
    for d in range(cfg["dezena_min"], cfg["dezena_max"] + 1):
        grade.append({
            "dezena": d,
            "em_a": d in set_a,
            "em_b": d in set_b,
            "repetiu_volante": d in rep_v,
            "repetiu_posicional": d in rep_p,
            "posicao_a": pos_map_a.get(d),
            "posicao_b": pos_map_b.get(d),
        })
    return grade


def _build_grade_colunas(cfg: dict, cols_a: List[int], cols_b: List[int]) -> List[Dict[str, Any]]:
    grade = []
    n = cfg["colunas"]
    for i in range(n):
        da = cols_a[i] if i < len(cols_a) else None
        db_ = cols_b[i] if i < len(cols_b) else None
        grade.append({
            "coluna": i + 1,
            "valor_a": da,
            "valor_b": db_,
            "repetiu": da is not None and da == db_,
        })
    return grade


class CompararConcursosService:
    def __init__(self, modality_key: str):
        self.modality_key = modality_key
        self.cfg = get_compare_config(modality_key)
        self.Model = _load_model(self.cfg)

    def listar_concursos(self, limit: int = 150) -> List[Dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        rows = (
            db.session.query(self.Model)
            .order_by(desc(self.Model.concurso))
            .limit(lim)
            .all()
        )
        out = []
        for s in rows:
            item = {"concurso": s.concurso, "data": getattr(s, "data", None)}
            if self.cfg.get("layout") == "colunas":
                item["colunas"] = _dezenas_ordered(s, self.cfg)
            else:
                item["dezenas"] = sorted(_dezenas_set(s, self.cfg))
            out.append(item)
        return out

    def comparar(
        self,
        concurso_a: Optional[int] = None,
        concurso_b: Optional[int] = None,
        modo: str = "volante",
        sorteio_a: int = 1,
        sorteio_b: int = 1,
    ) -> Dict[str, Any]:
        cfg = self.cfg
        modos = cfg.get("modos") or ["volante"]
        modo = modo if modo in modos else modos[0]

        rows = (
            db.session.query(self.Model)
            .order_by(self.Model.concurso.asc())
            .all()
        )
        if len(rows) < 2:
            return {"sucesso": False, "erro": "É necessário ao menos 2 concursos no banco."}

        if concurso_a is None:
            concurso_a = rows[-2].concurso
        if concurso_b is None:
            concurso_b = rows[-1].concurso

        s_a = db.session.get(self.Model, int(concurso_a))
        s_b = db.session.get(self.Model, int(concurso_b))
        if not s_a or not s_b:
            return {"sucesso": False, "erro": "Concurso não encontrado."}
        if s_a.concurso == s_b.concurso:
            return {"sucesso": False, "erro": "Selecione dois concursos diferentes."}
        if s_a.concurso > s_b.concurso:
            s_a, s_b = s_b, s_a
            sorteio_a, sorteio_b = sorteio_b, sorteio_a

        sorteio_a = 2 if int(sorteio_a) == 2 else 1
        sorteio_b = 2 if int(sorteio_b) == 2 else 1

        if cfg.get("layout") == "colunas":
            return self._comparar_colunas(s_a, s_b, modo)

        set_a = _dezenas_set(s_a, cfg, sorteio_a)
        set_b = _dezenas_set(s_b, cfg, sorteio_b)
        ordered_a = _dezenas_ordered(s_a, cfg, sorteio_a)
        ordered_b = _dezenas_ordered(s_b, cfg, sorteio_b)

        rep_v = sorted(set_a & set_b)
        rep_pos = _repetidas_posicional(ordered_a, ordered_b) if len(modos) > 1 or "posicional" in modos else []
        rep_p_set = {x["dezena"] for x in rep_pos}
        pares, impares = _pares_impares(rep_v)

        pos_map_a = {d: i for i, d in enumerate(ordered_a, start=1)}
        pos_map_b = {d: i for i, d in enumerate(ordered_b, start=1)}

        result: Dict[str, Any] = {
            "sucesso": True,
            "modo": modo,
            "layout": "grid",
            "concurso_a": _pack_concurso(s_a, cfg, sorteio_a),
            "concurso_b": _pack_concurso(s_b, cfg, sorteio_b),
            "sorteio_a": sorteio_a,
            "sorteio_b": sorteio_b,
            "resumo": {
                "volante": {
                    "quantidade": len(rep_v),
                    "dezenas": rep_v,
                    "pares": pares,
                    "impares": impares,
                },
                "posicional": {
                    "quantidade": len(rep_pos),
                    "detalhe": rep_pos,
                },
            },
            "grade": _build_grade_grid(cfg, set_a, set_b, set(rep_v), rep_p_set, pos_map_a, pos_map_b),
        }

        if cfg.get("extra_trevos"):
            ta = set(getattr(s_a, cfg["trevo_set_method"])())
            tb = set(getattr(s_b, cfg["trevo_set_method"])())
            rep_t = sorted(ta & tb)
            result["trevos"] = {
                "a": sorted(ta),
                "b": sorted(tb),
                "repetidos": rep_t,
                "quantidade": len(rep_t),
            }

        if cfg.get("extra_time"):
            ta = getattr(s_a, "time_num", None)
            tb = getattr(s_b, "time_num", None)
            result["time"] = {
                "a": {"num": ta, "nome": getattr(s_a, "time_nome", None) or ""},
                "b": {"num": tb, "nome": getattr(s_b, "time_nome", None) or ""},
                "repetiu": ta is not None and ta == tb and ta not in (0, None),
            }

        if cfg.get("extra_mes"):
            ma = getattr(s_a, cfg.get("mes_field", "mes_num"), None)
            mb = getattr(s_b, cfg.get("mes_field", "mes_num"), None)
            result["mes"] = {
                "a": {
                    "num": ma,
                    "nome": getattr(s_a, cfg.get("mes_label_field", "mes_nome"), None) or "",
                },
                "b": {
                    "num": mb,
                    "nome": getattr(s_b, cfg.get("mes_label_field", "mes_nome"), None) or "",
                },
                "repetiu": ma is not None and ma == mb and ma not in (0, None),
            }

        return result

    def _comparar_colunas(self, s_a: Any, s_b: Any, modo: str) -> Dict[str, Any]:
        cfg = self.cfg
        cols_a = _dezenas_ordered(s_a, cfg)
        cols_b = _dezenas_ordered(s_b, cfg)
        grade = _build_grade_colunas(cfg, cols_a, cols_b)
        rep = [g for g in grade if g["repetiu"]]
        return {
            "sucesso": True,
            "modo": modo,
            "layout": "colunas",
            "concurso_a": _pack_concurso(s_a, cfg),
            "concurso_b": _pack_concurso(s_b, cfg),
            "resumo": {
                "posicional": {
                    "quantidade": len(rep),
                    "detalhe": [{"posicao": g["coluna"], "dezena": g["valor_a"]} for g in rep],
                },
                "volante": {"quantidade": 0, "dezenas": [], "pares": 0, "impares": 0},
            },
            "grade_colunas": grade,
        }

    def indicacao_padrao(self) -> Dict[str, Any]:
        """Pool inicial da linha SUPER (rastreável) + faixa do volante."""
        cfg = self.cfg
        dmin = int(cfg["dezena_min"])
        dmax = int(cfg["dezena_max"])
        n_sort = len(cfg.get("ordered_fields") or []) or 7
        max_ind = int(cfg.get("indicacao_max") or max(n_sort * 2, n_sort))
        tamanho = min(dmax - dmin + 1, max_ind)
        origem = {
            "id": "frequencia",
            "label": "Dezenas mais frequentes no histórico desta modalidade",
            "url": "/analise/",
        }
        dados_freq = self._freq_dezenas()
        try:
            from concentracao_acertos.specs import (
                get_concentracao_config,
                tem_concentracao_acertos,
            )
            from concentracao_acertos.core import pool_sugerido
            if tem_concentracao_acertos(self.modality_key):
                cc = get_concentracao_config(self.modality_key)
                ests = cc.get("estrategias") or []
                size = min(int((ests[0] or {}).get("pool_size") or tamanho) if ests else tamanho, max_ind)
                dezenas = pool_sugerido(
                    dados_freq, size, "freq", dezena_min=dmin, dezena_max=dmax,
                )
                origem = {
                    "id": "concentracao",
                    "label": "Concentração de acertos — Estratégia A (frequência)",
                    "url": "/analise/concentracao-acertos/",
                }
                return self._pack_indicacao(dezenas, origem, dmin, dmax, n_sort)
        except Exception:
            pass
        ordenado = sorted(dados_freq, key=lambda r: (-int(r.get("freq") or 0), int(r.get("dezena") or 0)))
        dezenas = [int(r["dezena"]) for r in ordenado[:tamanho]]
        return self._pack_indicacao(dezenas, origem, dmin, dmax, n_sort)

    def historico_indicados(self, limit: int = 15, offset: int = 0) -> Dict[str, Any]:
        """Concursos para a grade Indicado × Sorteios (mais recente primeiro)."""
        cfg = self.cfg
        off = max(0, int(offset or 0))
        q = db.session.query(self.Model).order_by(desc(self.Model.concurso))
        total = q.count()
        pedido = int(limit if limit is not None else 0)
        if pedido <= 0:
            rows = q.offset(off).all()
        else:
            lim = max(1, min(pedido, 8000))
            rows = q.offset(off).limit(lim).all()
        concursos = []
        for s in rows:
            concursos.append({
                "concurso": s.concurso,
                "data": getattr(s, "data", None) or "",
                "dezenas": sorted(_dezenas_set(s, cfg)),
                "dezenas_exibicao": _dezenas_ordered(s, cfg),
            })
        return {
            "sucesso": True,
            "total": total,
            "offset": off,
            "limit": len(concursos),
            "tem_mais": off + len(concursos) < total,
            "concursos": concursos,
        }

    def _freq_dezenas(self) -> List[Dict[str, Any]]:
        cfg = self.cfg
        dmin = int(cfg["dezena_min"])
        dmax = int(cfg["dezena_max"])
        freq = {d: 0 for d in range(dmin, dmax + 1)}
        rows = db.session.query(self.Model).all()
        for s in rows:
            for d in _dezenas_set(s, cfg):
                if dmin <= int(d) <= dmax:
                    freq[int(d)] += 1
        return [{"dezena": d, "freq": freq[d]} for d in range(dmin, dmax + 1)]

    def _pack_indicacao(self, dezenas, origem, dmin, dmax, n_sort) -> Dict[str, Any]:
        max_ind = int(self.cfg.get("indicacao_max") or 15)
        nums = sorted({int(d) for d in (dezenas or []) if dmin <= int(d) <= dmax})[:max_ind]
        return {
            "sucesso": True,
            "dezenas": nums,
            "origem": origem,
            "dezena_min": dmin,
            "dezena_max": dmax,
            "sorteadas": int(n_sort),
            "indicacao_max": max_ind,
        }
