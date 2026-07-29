"""Comportamento TM — Timemania."""
from __future__ import annotations

from typing import Any, List

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import TIMEMANIA_SPEC
from models.sorteio_timemania import SorteioTimemania


class ComportamentoTimemaniaService(ComportamentoBaseService):
    SPEC = TIMEMANIA_SPEC
    SorteioModel = SorteioTimemania

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        vals = [getattr(s, f"d{i}") for i in range(1, 11)]
        return sorted(v for v in vals if v and int(v) > 0)
