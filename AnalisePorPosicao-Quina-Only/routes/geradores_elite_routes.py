"""Geradores de Elite — blueprint aditivo."""
import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from geradores_elite.routes_factory import build_geradores_elite_blueprint

geradores_elite_bp = build_geradores_elite_blueprint("quina")
