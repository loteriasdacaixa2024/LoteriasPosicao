# -*- coding: utf-8 -*-
"""Mapeamento modalidade → serviço de sincronização Caixa (import no app da modalidade)."""
from __future__ import annotations

from typing import Dict, Tuple

# (módulo relativo ao app da modalidade, classe, usa_assinatura_supersete)
SYNC_SERVICES: Dict[str, Tuple[str, str, bool]] = {
    "lotofacil": ("services.api_lotofacil_service", "ApiLotofacilService", False),
    "diadesorte": ("services.api_diadesorte_service", "ApiDiaDeSorteService", False),
    "lotomania": ("services.api_lotomania_service", "ApiLotomaniaService", False),
    "quina": ("services.api_quina_service", "ApiQuinaService", False),
    "megasena": ("services.api_megasena_service", "ApiMegaSenaService", False),
    "maismilionaria": ("services.api_maismilionaria_service", "ApiMaisMilionariaService", False),
    "duplasena": ("services.api_duplasena_service", "ApiDuplaSenaService", False),
    "timemania": ("services.api_timemania_service", "ApiTimemaniaSService", False),
    "supersete": ("services.api_supersete_service", "ApiSuperSeteService", True),
}
