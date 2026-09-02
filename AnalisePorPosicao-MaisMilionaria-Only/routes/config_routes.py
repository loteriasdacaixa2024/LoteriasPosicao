import os
import sys

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from configuracoes.routes_modality import build_config_blueprint

config_bp = build_config_blueprint("maismilionaria")
