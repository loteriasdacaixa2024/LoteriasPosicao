"""
Análise de Comportamento MS — Mega-Sena.
"""
from __future__ import annotations

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import MEGASENA_SPEC
from models.sorteio_megasena import SorteioMegaSena


class ComportamentoMegaSenaService(ComportamentoBaseService):
    SPEC = MEGASENA_SPEC
    SorteioModel = SorteioMegaSena
