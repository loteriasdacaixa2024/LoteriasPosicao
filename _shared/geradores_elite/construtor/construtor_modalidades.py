# -*- coding: utf-8 -*-
"""Adaptadores Construtor — modalidades volante."""
from __future__ import annotations

from typing import Any, List

from geradores_elite.construtor.construtor_base_service import ConstrutorBaseService
from geradores_elite.construtor.construtor_specs import (
    DIADESORTE_CONSTRUTOR,
    DUPLASENA_CONSTRUTOR,
    LOTOFACIL_CONSTRUTOR,
    LOTOMANIA_CONSTRUTOR,
    MAISMILIONARIA_CONSTRUTOR,
    MEGASENA_CONSTRUTOR,
    QUINA_CONSTRUTOR,
    TIMEMANIA_CONSTRUTOR,
)


class ConstrutorMegaSenaService(ConstrutorBaseService):
    SPEC = MEGASENA_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_megasena", "SorteioMegaSena")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloMegaSenaService
        return CicloMegaSenaService

    @classmethod
    def _analise_service(cls):
        from services.analise_megasena_service import AnaliseMegaSenaService
        return AnaliseMegaSenaService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_megasena_service import ComportamentoMegaSenaService
        return ComportamentoMegaSenaService


class ConstrutorQuinaService(ConstrutorBaseService):
    SPEC = QUINA_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_quina", "SorteioQuina")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloQuinaService
        return CicloQuinaService

    @classmethod
    def _analise_service(cls):
        from services.analise_quina_service import AnaliseQuinaService
        return AnaliseQuinaService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_quina_service import ComportamentoQuinaService
        return ComportamentoQuinaService


class ConstrutorTimemaniaService(ConstrutorBaseService):
    SPEC = TIMEMANIA_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_timemania", "SorteioTimemania")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloTimemaniaService
        return CicloTimemaniaService

    @classmethod
    def _analise_service(cls):
        from services.analise_timemania_service import AnaliseTimemaniaService
        return AnaliseTimemaniaService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_timemania_service import ComportamentoTimemaniaService
        return ComportamentoTimemaniaService

    @classmethod
    def _time_label(cls, time_num: int) -> str:
        from models.sorteio_timemania import TIMES_DO_CORACAO
        return TIMES_DO_CORACAO.get(int(time_num), str(time_num))


class ConstrutorDuplaSenaService(ConstrutorBaseService):
    SPEC = DUPLASENA_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_duplasena", "SorteiosDuplaSena")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloDuplaSenaService
        return CicloDuplaSenaService

    @classmethod
    def _analise_service(cls):
        from services.analise_duplasena_service import AnaliseDuplaSenaService
        return AnaliseDuplaSenaService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_duplasena_service import ComportamentoDuplaSenaService
        return ComportamentoDuplaSenaService

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        if hasattr(s, "sorteio1_lista"):
            return list(s.sorteio1_lista())
        return super()._dezenas_from_sorteio(s)

    @classmethod
    def _acertos_linha_sorteio(cls, dezenas: List[int], sorteio: Any) -> int:
        s1 = sorteio.sorteio1() if hasattr(sorteio, "sorteio1") else set()
        s2 = sorteio.sorteio2() if hasattr(sorteio, "sorteio2") else set()
        return max(cls._contar_acertos(dezenas, s1), cls._contar_acertos(dezenas, s2))


class ConstrutorMaisMilionariaService(ConstrutorBaseService):
    SPEC = MAISMILIONARIA_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_maismilionaria", "SorteioMaisMilionaria")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloMaisMilionariaService
        return CicloMaisMilionariaService

    @classmethod
    def _analise_service(cls):
        from services.analise_maismilionaria_service import AnaliseMaisMilionariaService
        return AnaliseMaisMilionariaService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_maismilionaria_service import ComportamentoMaisMilionariaService
        return ComportamentoMaisMilionariaService


class ConstrutorLotofacilService(ConstrutorBaseService):
    SPEC = LOTOFACIL_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_lotofacil", "SorteioLotofacil")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloLotofacilService
        return CicloLotofacilService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_lotofacil_service import ComportamentoLotofacilService
        return ComportamentoLotofacilService


class ConstrutorLotomaniaService(ConstrutorBaseService):
    SPEC = LOTOMANIA_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_lotomania", "SorteioLotomania")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloLotomaniaService
        return CicloLotomaniaService

    @classmethod
    def _analise_service(cls):
        from services.analise_lotomania_service import AnaliseLotomaniaService
        return AnaliseLotomaniaService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_lotomania_service import ComportamentoLotomaniaService
        return ComportamentoLotomaniaService


class ConstrutorDiaDeSorteService(ConstrutorBaseService):
    SPEC = DIADESORTE_CONSTRUTOR
    _sorteio_model_path = ("models.sorteio_diadesorte", "SorteioDiaDeSorte")

    @classmethod
    def _ciclo_service(cls):
        from services.ciclo_service import CicloDiaDeSorteService
        return CicloDiaDeSorteService

    @classmethod
    def _analise_service(cls):
        from services.analise_diadesorte_service import AnaliseDiaDeSorteService
        return AnaliseDiaDeSorteService

    @classmethod
    def _comportamento_service(cls):
        from services.comportamento_diadesorte_service import ComportamentoDiaDeSorteService
        return ComportamentoDiaDeSorteService

    @classmethod
    def _extras_ultimo_sorteio(cls, sorteio: Any) -> dict:
        from models.sorteio_diadesorte import MESES_DO_ANO
        out = super()._extras_ultimo_sorteio(sorteio)
        mn = getattr(sorteio, "mes_num", None)
        if mn:
            out["mes_nome"] = getattr(sorteio, "mes_nome", None) or MESES_DO_ANO.get(mn, "")
        return out

    @classmethod
    def _serializar_construcao(cls, c):
        from models.sorteio_diadesorte import MESES_DO_ANO
        out = super()._serializar_construcao(c)
        if c.mes_num:
            out["mes_nome"] = MESES_DO_ANO.get(c.mes_num)
        return out


from geradores_elite.construtor.construtor_supersete_service import ConstrutorSuperSeteService

CONSTRUTOR_REGISTRY = {
    "diadesorte": ConstrutorDiaDeSorteService,
    "megasena": ConstrutorMegaSenaService,
    "quina": ConstrutorQuinaService,
    "timemania": ConstrutorTimemaniaService,
    "duplasena": ConstrutorDuplaSenaService,
    "maismilionaria": ConstrutorMaisMilionariaService,
    "lotofacil": ConstrutorLotofacilService,
    "lotomania": ConstrutorLotomaniaService,
    "supersete": ConstrutorSuperSeteService,
}

MODALIDADES_CONSTRUTOR = frozenset(CONSTRUTOR_REGISTRY.keys())
