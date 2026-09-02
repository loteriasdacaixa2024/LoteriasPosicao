# -*- coding: utf-8 -*-
import os
from datetime import datetime
from typing import Any, Dict, List

from _shared.analises_gerais.concurso_audit import auditar_concursos
from _shared.analises_gerais.insights import enriquecer_linhas
from _shared.analises_gerais.loader import carregar_sorteios
from _shared.analises_gerais.metrics import calcular_resumo
from _shared.caixa_api.ultimo_concurso import buscar_status_caixa
from _shared.analises_gerais.registry import SPECS, SPECS_BY_KEY, SUPERSETE_KEY


def _base_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class AnalisesGeraisService:
    @classmethod
    def resumo_completo(cls) -> Dict[str, Any]:
        linhas: List[Dict[str, Any]] = []
        avisos: List[str] = []

        for spec in SPECS:
            sorteios, msg = carregar_sorteios(spec, _base_dir())
            if msg != "ok" and not sorteios:
                linhas.append({
                    "key": spec.key,
                    "nome": spec.nome,
                    "porta": spec.porta,
                    "grupo": spec.grupo,
                    "total_concursos": 0,
                    "erro": msg,
                    "aposta_label": (
                        "7 colunas (0–9 cada)"
                        if spec.grupo == "supersete"
                        else f"{spec.sorteadas} de {spec.total_dezenas}"
                    ),
                })
                avisos.append(f"{spec.nome}: {msg}")
                continue
            row = calcular_resumo(spec, sorteios)
            st_caixa = buscar_status_caixa(spec.key)
            ultimo_api = int(st_caixa.get("ultimo_sorteado") or 0)
            row.update(auditar_concursos(sorteios, ultimo_api, st_caixa))
            linhas.append(row)

        linhas = enriquecer_linhas(linhas)
        volante = [r for r in linhas if r.get("grupo") != "supersete"]
        supersete = next((r for r in linhas if r.get("key") == SUPERSETE_KEY), None)
        return {
            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "modalidades": volante,
            "supersete": supersete,
            "avisos": avisos,
            "legenda": {
                "coluna_2plus": "Concursos com pelo menos 2 dezenas no mesmo final do volante.",
                "finais_distintos": "Todos os finais diferentes (máx. 1 dezena por coluna de final).",
                "ciclo": "Dezenas ainda não sorteadas no ciclo atual (reinicia quando o universo fecha).",
            },
            "legenda_supersete": {
                "mesmo_digito": "Mesmo dígito (0–9) repetido em 2 ou mais colunas no mesmo concurso.",
                "distintos": "Os 7 dígitos do concurso são todos diferentes entre si.",
                "ciclo_coluna": "Por coluna C1–C7: dígitos 0–9 que ainda não saíram no ciclo atual daquela posição.",
            },
        }

    @classmethod
    def resumo_modalidade(cls, key: str) -> Dict[str, Any]:
        spec = SPECS_BY_KEY.get(key)
        if not spec:
            raise KeyError(key)
        sorteios, msg = carregar_sorteios(spec, _base_dir())
        if msg != "ok" and not sorteios:
            row = {
                "key": key,
                "nome": spec.nome,
                "total_concursos": 0,
                "erro": msg,
            }
        else:
            row = calcular_resumo(spec, sorteios)
            st_caixa = buscar_status_caixa(spec.key)
            ultimo_api = int(st_caixa.get("ultimo_sorteado") or 0)
            row.update(auditar_concursos(sorteios, ultimo_api, st_caixa))
        return enriquecer_linhas([row])[0]
