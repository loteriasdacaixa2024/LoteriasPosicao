import os
import sys

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)

from _shared.desdobramento_service_factory import build_desdobramento_service
from services.analise_diadesorte_service import AnaliseDiaDeSorteService

DesdobramentoDiaDeSorteService = build_desdobramento_service(
    AnaliseDiaDeSorteService,
    max_dezena=31,
    suporta_trevo=False,
)
