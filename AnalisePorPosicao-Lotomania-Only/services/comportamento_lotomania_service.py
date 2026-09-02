"""Comportamento LM — Lotomania."""
from __future__ import annotations

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import LOTOMANIA_SPEC
from models.sorteio_lotomania import SorteioLotomania


class ComportamentoLotomaniaService(ComportamentoBaseService):
    SPEC = LOTOMANIA_SPEC
    SorteioModel = SorteioLotomania
