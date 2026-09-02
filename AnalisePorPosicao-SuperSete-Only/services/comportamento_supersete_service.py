"""Comportamento SS — Super Sete."""
from __future__ import annotations

from geradores_elite.comportamento.supersete_service import ComportamentoSuperSeteService as _Base
from models.sorteio_supersete import SorteioSuperSete


class ComportamentoSuperSeteService(_Base):
    SorteioModel = SorteioSuperSete
