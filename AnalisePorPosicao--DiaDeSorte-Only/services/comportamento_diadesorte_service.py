"""
Análise de Comportamento DS — Dia de Sorte.
"""
from __future__ import annotations

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import DIADESORTE_SPEC
from models.sorteio_diadesorte import SorteioDiaDeSorte


class ComportamentoDiaDeSorteService(ComportamentoBaseService):
    SPEC = DIADESORTE_SPEC
    SorteioModel = SorteioDiaDeSorte
