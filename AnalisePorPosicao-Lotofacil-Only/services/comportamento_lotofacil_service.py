"""
Análise de Comportamento LF — Lotofácil.
"""
from __future__ import annotations

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import LOTOFACIL_SPEC
from models.sorteio_lotofacil import SorteioLotofacil


class ComportamentoLotofacilService(ComportamentoBaseService):
    SPEC = LOTOFACIL_SPEC
    SorteioModel = SorteioLotofacil

    @classmethod
    def _dezenas_from_sorteio(cls, s):
        return s.dezenas()
