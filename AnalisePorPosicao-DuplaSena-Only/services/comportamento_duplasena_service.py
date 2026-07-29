"""Comportamento DS2 — Dupla Sena (perfil do 1º sorteio)."""
from __future__ import annotations

from typing import Any, List

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import DUPLASENA_SPEC
from models.sorteio_duplasena import SorteiosDuplaSena


class ComportamentoDuplaSenaService(ComportamentoBaseService):
    SPEC = DUPLASENA_SPEC
    SorteioModel = SorteiosDuplaSena

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        return s.sorteio1_lista()
