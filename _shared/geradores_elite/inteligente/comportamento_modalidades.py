# -*- coding: utf-8 -*-
"""Adaptadores Comportamento — todas as modalidades."""
from __future__ import annotations

from geradores_elite.comportamento.base_inteligente import ComportamentoBaseInteligente


class ComportamentoLotofacilInteligente(ComportamentoBaseInteligente):
    modality_key = "lotofacil"
    motor = "comportamento_lf"

    @classmethod
    def _svc(cls):
        from services.comportamento_lotofacil_service import ComportamentoLotofacilService
        return ComportamentoLotofacilService


class ComportamentoMegaSenaInteligente(ComportamentoBaseInteligente):
    modality_key = "megasena"
    motor = "comportamento_ms"

    @classmethod
    def _svc(cls):
        from services.comportamento_megasena_service import ComportamentoMegaSenaService
        return ComportamentoMegaSenaService


class ComportamentoDiaDeSorteInteligente(ComportamentoBaseInteligente):
    modality_key = "diadesorte"
    motor = "comportamento_ds"

    @classmethod
    def _svc(cls):
        from services.comportamento_diadesorte_service import ComportamentoDiaDeSorteService
        return ComportamentoDiaDeSorteService


class ComportamentoQuinaInteligente(ComportamentoBaseInteligente):
    modality_key = "quina"
    motor = "comportamento_qn"

    @classmethod
    def _svc(cls):
        from services.comportamento_quina_service import ComportamentoQuinaService
        return ComportamentoQuinaService


class ComportamentoTimemaniaInteligente(ComportamentoBaseInteligente):
    modality_key = "timemania"
    motor = "comportamento_tm"

    @classmethod
    def _svc(cls):
        from services.comportamento_timemania_service import ComportamentoTimemaniaService
        return ComportamentoTimemaniaService


class ComportamentoDuplaSenaInteligente(ComportamentoBaseInteligente):
    modality_key = "duplasena"
    motor = "comportamento_ds2"

    @classmethod
    def _svc(cls):
        from services.comportamento_duplasena_service import ComportamentoDuplaSenaService
        return ComportamentoDuplaSenaService


class ComportamentoMaisMilionariaInteligente(ComportamentoBaseInteligente):
    modality_key = "maismilionaria"
    motor = "comportamento_mm"

    @classmethod
    def _svc(cls):
        from services.comportamento_maismilionaria_service import ComportamentoMaisMilionariaService
        return ComportamentoMaisMilionariaService


class ComportamentoLotomaniaInteligente(ComportamentoBaseInteligente):
    modality_key = "lotomania"
    motor = "comportamento_lm"

    @classmethod
    def _svc(cls):
        from services.comportamento_lotomania_service import ComportamentoLotomaniaService
        return ComportamentoLotomaniaService


class ComportamentoSuperSeteInteligente(ComportamentoBaseInteligente):
    modality_key = "supersete"
    motor = "comportamento_ss"

    @classmethod
    def _svc(cls):
        from services.comportamento_supersete_service import ComportamentoSuperSeteService
        return ComportamentoSuperSeteService
