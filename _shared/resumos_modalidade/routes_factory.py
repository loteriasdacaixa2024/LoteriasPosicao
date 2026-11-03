# -*- coding: utf-8 -*-
"""Rota /analise/resumos-modalidade/ — só este pacote."""
from __future__ import annotations

from flask import Blueprint, render_template

from resumos_modalidade.service import montar_todos


def register_resumos_modalidade(analise_bp: Blueprint, modality_key: str) -> None:
    @analise_bp.route("/resumos-modalidade/")
    def resumos_modalidade_page():
        return render_template(
            "resumos_modalidade.html",
            page_title="Resumo Geral das modalidades",
            blocos=montar_todos(),
        )
