# -*- coding: utf-8 -*-
"""Rotas — Grades de Dígitos."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from grades_digitos.service import conferir
from grades_digitos.specs import get_grades_config, tem_grades_digitos


def register_grades_digitos(analise_bp: Blueprint, modality_key: str) -> None:
    if not tem_grades_digitos(modality_key):
        return

    @analise_bp.route("/grades-digitos/")
    def grades_digitos_page():
        cfg = get_grades_config(modality_key)
        return render_template(
            "grades_digitos.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            dezena_min=cfg["dezena_min"],
            dezena_max=cfg["dezena_max"],
            api_conferir="/analise/api/grades-digitos/conferir",
        )

    @analise_bp.route("/api/grades-digitos/conferir", methods=["POST"])
    def api_grades_digitos_conferir():
        try:
            corpo = request.get_json(silent=True) or {}
            out = conferir(modality_key, corpo.get("inicios"))
            return jsonify({"sucesso": True, **out})
        except ValueError as exc:
            return jsonify({"sucesso": False, "erro": str(exc)}), 400
        except Exception as exc:
            return jsonify({"sucesso": False, "erro": str(exc)}), 500
