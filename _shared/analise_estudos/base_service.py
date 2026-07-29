# -*- coding: utf-8 -*-
"""Serviço base — carga de sorteios e filtros."""
from __future__ import annotations

import importlib
from collections import Counter
from typing import Any, Dict, List, Type

from sqlalchemy import desc

from models.shared import db

from analise_estudos.specs import BASES_LABEL, get_estudos_config, janelas_validas


class AnaliseEstudosBase:
    modality_key: str = "diadesorte"

    @classmethod
    def _cfg(cls) -> Dict[str, Any]:
        return get_estudos_config(cls.modality_key)

    @classmethod
    def _model(cls) -> Type:
        cfg = cls._cfg()
        module = cfg.get("model_module") or ""
        class_name = cfg.get("model_class") or ""
        if not module or not class_name:
            raise ValueError(f"Modelo não configurado: {cls.modality_key}")
        mod = importlib.import_module(module)
        return getattr(mod, class_name)

    @classmethod
    def _normalizar_base(cls, base: str) -> str:
        b = (base or "geral").strip().lower()
        permitidas = set(cls._cfg().get("bases_ui") or ("geral",))
        if b in BASES_LABEL and b in permitidas:
            return b
        return "geral"

    @classmethod
    def _normalizar_janela(cls, janela: int) -> int:
        j = int(janela)
        validas = janelas_validas(cls.modality_key)
        if j in validas:
            return j
        return cls._cfg()["janela_default"]

    @classmethod
    def carregar_sorteios_asc(
        cls,
        base_estatistica: str = "geral",
        janela: int = 0,
    ) -> List[Any]:
        Model = cls._model()
        base = cls._normalizar_base(base_estatistica)
        q = db.session.query(Model).order_by(Model.concurso)
        if hasattr(Model, "filtro_base"):
            q = Model.filtro_base(q, base)
        elif base != "geral":
            return []
        rows = q.all()
        if janela and janela > 0:
            rows = rows[-janela:]
        return rows

    @classmethod
    def dezenas_ordem(cls, sorteio: Any) -> List[int]:
        if hasattr(sorteio, "dezenas_ordem_lista"):
            return list(sorteio.dezenas_ordem_lista())
        if hasattr(sorteio, "digitos_ordem_lista"):
            return list(sorteio.digitos_ordem_lista())
        if hasattr(sorteio, "digitos"):
            return list(sorteio.digitos())
        dz = sorteio.dezenas()
        return sorted(dz) if not isinstance(dz, list) else list(dz)

    @classmethod
    def listar_concursos(cls, limite: int = 150, base: str = "geral") -> List[Dict[str, Any]]:
        Model = cls._model()
        base = cls._normalizar_base(base)
        q = db.session.query(Model).order_by(desc(Model.concurso))
        if hasattr(Model, "filtro_base"):
            q = Model.filtro_base(q, base)
        elif base != "geral":
            return []
        if limite and limite > 0:
            q = q.limit(int(limite))
        return [
            {"concurso": r.concurso, "data": getattr(r, "data", "") or ""}
            for r in q.all()
        ]

    @classmethod
    def resumo_indicadores(
        cls,
        linhas: List[Dict[str, Any]],
        indicadores: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        total = len(linhas)
        out: Dict[str, Dict[str, Any]] = {}
        for cod in indicadores:
            vals = [int(row.get(cod, 0)) for row in linhas if cod in row]
            if not vals:
                out[cod] = {"moda": 0, "moda_pct": 0, "media": 0, "distribuicao": {}}
                continue
            cnt = Counter(vals)
            moda, moda_qtd = cnt.most_common(1)[0]
            out[cod] = {
                "moda": int(moda),
                "moda_pct": round(moda_qtd / total * 100, 1) if total else 0,
                "media": round(sum(vals) / len(vals), 2),
                "min": min(vals),
                "max": max(vals),
                "distribuicao": {str(k): v for k, v in sorted(cnt.items())},
            }
        return out

    @classmethod
    def meta_bases(cls) -> Dict[str, Any]:
        Model = cls._model()
        total = db.session.query(Model).count()
        field = cls._cfg().get("ganhadores_field")
        if not field or not hasattr(Model, field):
            return {
                "total_geral": total,
                "vencedores": 0,
                "acumulados": 0,
                "sem_classificacao": total,
                "bases_disponiveis": ["geral"],
            }
        col = getattr(Model, field)
        venc = db.session.query(Model).filter(col >= 1).count()
        acum = db.session.query(Model).filter(col == 0).count()
        sem = total - venc - acum
        return {
            "total_geral": total,
            "vencedores": venc,
            "acumulados": acum,
            "sem_classificacao": sem,
            "bases_disponiveis": ["geral", "vencedores", "acumulados"],
        }

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        cfg = cls._cfg()
        bases = cfg.get("bases_ui") or ("geral",)
        return {
            "modality_key": cls.modality_key,
            "modality_nome": cfg["nome"],
            "janelas": list(cfg["janelas_ui"]),
            "janela_default": cfg["janela_default"],
            "bases_estatistica": [
                {"id": b, "label": BASES_LABEL[b]} for b in bases if b in BASES_LABEL
            ],
            "extra_mes": cfg.get("extra_mes", False),
            "dezena_min": cfg["dezena_min"],
            "dezena_max": cfg["dezena_max"],
            "sorteadas": cfg["sorteadas"],
            "page_subtitle": cfg.get("page_subtitle", ""),
        }
