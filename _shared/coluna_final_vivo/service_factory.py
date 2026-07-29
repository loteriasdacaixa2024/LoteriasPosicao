# -*- coding: utf-8 -*-
from typing import List, Tuple, Type

from _shared.coluna_final_vivo.engine import montar_payload
from models.shared import db


def _dezenas_do_sorteio(s) -> List[int]:
    if hasattr(s, "dezenas_lista"):
        return list(s.dezenas_lista())
    if hasattr(s, "dezenas"):
        raw = s.dezenas()
        if isinstance(raw, (set, frozenset)):
            return sorted(raw)
        return list(raw)
    raise TypeError("Modelo de sorteio sem dezenas() ou dezenas_lista()")


def build_coluna_final_vivo_service(sorteio_model: Type, slug: str):
    class ColunaFinalVivoService:
        SLUG = slug

        @classmethod
        def obter_payload(cls) -> dict:
            rows = (
                db.session.query(sorteio_model)
                .order_by(sorteio_model.concurso.asc())
                .all()
            )
            sorteios: List[Tuple[int, str, List[int]]] = []
            for s in rows:
                data = getattr(s, "data", "") or ""
                sorteios.append((int(s.concurso), data, _dezenas_do_sorteio(s)))
            return montar_payload(slug, sorteios)

    return ColunaFinalVivoService
