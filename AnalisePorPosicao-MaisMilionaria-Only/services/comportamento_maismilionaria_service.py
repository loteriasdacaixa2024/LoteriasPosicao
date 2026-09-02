"""Comportamento +M — +Milionária."""
from __future__ import annotations

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import MAISMILIONARIA_SPEC
from models.sorteio_maismilionaria import SorteioMaisMilionaria


class ComportamentoMaisMilionariaService(ComportamentoBaseService):
    SPEC = MAISMILIONARIA_SPEC
    SorteioModel = SorteioMaisMilionaria
