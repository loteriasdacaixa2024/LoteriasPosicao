# -*- coding: utf-8 -*-
"""Integração Flask — resumos_modalidade."""
from __future__ import annotations

import os
import sys

_PKG = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_PKG) not in sys.path:
    sys.path.insert(0, os.path.dirname(_PKG))


def extend_resumos_modalidade_app(app) -> None:
    from menu.app_integration import _merge_template_dirs

    _merge_template_dirs(app, [os.path.join(_PKG, "templates")])


def wire_resumos_modalidade(analise_bp, modality_key: str) -> None:
    from resumos_modalidade.routes_factory import register_resumos_modalidade

    register_resumos_modalidade(analise_bp, modality_key)
