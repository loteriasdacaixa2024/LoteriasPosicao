# -*- coding: utf-8 -*-
"""Rota da página Resumo Geral das modalidades."""
from __future__ import annotations

from flask import Blueprint, render_template

from resumo_modalidades.service import montar_pagina


def register_resumo_modalidades(analise_bp: Blueprint) -> None:
    @analise_bp.route("/resumo-modalidades/")
    def resumo_modalidades_page():
        return render_template(
            "resumo_modalidades.html",
            page_title="Resumo Geral das modalidades",
            data=montar_pagina(),
        )
