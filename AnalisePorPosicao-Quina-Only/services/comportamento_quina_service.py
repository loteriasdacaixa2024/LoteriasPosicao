"""Comportamento QN — Quina."""
from __future__ import annotations

from geradores_elite.comportamento.base_service import ComportamentoBaseService
from geradores_elite.comportamento.specs import QUINA_SPEC
from models.sorteio_quina import SorteioQuina


class ComportamentoQuinaService(ComportamentoBaseService):
    SPEC = QUINA_SPEC
    SorteioModel = SorteioQuina
