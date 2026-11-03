# -*- coding: utf-8 -*-
"""Integração Flask — Resumo Geral das modalidades."""
from __future__ import annotations

import os
import sys

_PKG = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_PKG) not in sys.path:
    sys.path.insert(0, os.path.dirname(_PKG))


def extend_resumo_modalidades_app(app) -> None:
    from menu.app_integration import _merge_template_dirs

    _merge_template_dirs(app, [os.path.join(_PKG, "templates")])


def wire_resumo_modalidades(analise_bp) -> None:
    from resumo_modalidades.routes_factory import register_resumo_modalidades

    register_resumo_modalidades(analise_bp)
