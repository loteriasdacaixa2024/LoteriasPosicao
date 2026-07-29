import os
import sys

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)

from _shared.desdobramento_service_factory import build_desdobramento_service
from services.analise_lotomania_service import AnaliseLotomaniaService

DesdobramentoLotomaniaService = build_desdobramento_service(
    AnaliseLotomaniaService,
    max_dezena=99,
    dezena_min=0,
    suporta_trevo=False,
)
