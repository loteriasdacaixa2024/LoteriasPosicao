# -*- coding: utf-8 -*-
"""Análise oficial de Ciclos das Dezenas — fonte de dados para a rota /analise/ciclo-cobertura/.

Adaptado da especificação em docs/NovaAnalise/analise_ciclos_dezenas e do motor
validado no app Dia de Sorte de referência. Usa SorteioDiaDeSorte via loaders.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .loaders import carregar_sorteios_asc
from .specs import get_ciclo_spec


class AnaliseCicloCoberturaService:
    """Ciclo = período até todas as dezenas do universo saírem ao menos uma vez."""

    @staticmethod
    def calcular_ciclos_completos(modality_key: str = "diadesorte") -> List[dict]:
        spec = get_ciclo_spec(modality_key)
        sorteios = carregar_sorteios_asc(modality_key)
        if not sorteios:
            return []

        alvo = spec.universo_size
        ciclos: List[dict] = []
        ciclo_atual = {
            "numero": 1,
            "concurso_inicio": None,
            "concurso_fim": None,
            "dezenas_saidas": set(),
            "quantidade_concursos": 0,
            "historico_concursos": [],
            "detalhes_concursos": [],
        }

        for s in sorteios:
            dezenas_set = set(int(x) for x in s["dezenas"])
            novas = dezenas_set - ciclo_atual["dezenas_saidas"]
            repetidas = dezenas_set & ciclo_atual["dezenas_saidas"]

            if ciclo_atual["concurso_inicio"] is None:
                ciclo_atual["concurso_inicio"] = s["concurso"]

            ciclo_atual["dezenas_saidas"].update(dezenas_set)
            ciclo_atual["quantidade_concursos"] += 1
            ciclo_atual["historico_concursos"].append(s["concurso"])
            data_raw = s.get("data") or ""
            if hasattr(data_raw, "strftime"):
                data_fmt = data_raw.strftime("%d/%m/%Y")
            else:
                data_fmt = str(data_raw)
            ciclo_atual["detalhes_concursos"].append({
                "concurso": s["concurso"],
                "data": data_fmt,
                "novas": sorted(novas),
                "repetidas": sorted(repetidas),
                "qtd_novas": len(novas),
                "total_preenchido": len(ciclo_atual["dezenas_saidas"]),
                "dezenas": sorted(dezenas_set),
            })

            if len(ciclo_atual["dezenas_saidas"]) >= alvo:
                ciclo_atual["concurso_fim"] = s["concurso"]
                ciclo_atual["dezenas_saidas"] = list(ciclo_atual["dezenas_saidas"])
                ciclos.append(dict(ciclo_atual))
                # Novo ciclo começa no próximo concurso (não reutiliza o que fechou).
                ciclo_atual = {
                    "numero": len(ciclos) + 1,
                    "concurso_inicio": None,
                    "concurso_fim": None,
                    "dezenas_saidas": set(),
                    "quantidade_concursos": 0,
                    "historico_concursos": [],
                    "detalhes_concursos": [],
                }

        if ciclo_atual["quantidade_concursos"] > 0:
            ciclo_atual["dezenas_saidas"] = list(ciclo_atual["dezenas_saidas"])
            ciclo_atual["em_andamento"] = True
            ciclos.append(ciclo_atual)

        return ciclos

    @staticmethod
    def obter_ciclo_atual(modality_key: str = "diadesorte") -> Optional[dict]:
        spec = get_ciclo_spec(modality_key)
        ciclos = AnaliseCicloCoberturaService.calcular_ciclos_completos(modality_key)
        if not ciclos:
            return None

        ciclo_atual = ciclos[-1]
        todas = set(range(spec.dezena_min, spec.dezena_max + 1))
        saidas = set(ciclo_atual["dezenas_saidas"])
        pendentes = sorted(todas - saidas)

        historico_detalhes = []
        for c in ciclos:
            for d in c.get("detalhes_concursos", []):
                d_copy = dict(d)
                d_copy["numero_ciclo"] = c["numero"]
                historico_detalhes.append(d_copy)

        ultimo_cnc = historico_detalhes[-1]["concurso"] if historico_detalhes else None
        return {
            "numero_ciclo": ciclo_atual["numero"],
            "concurso_inicio": ciclo_atual["concurso_inicio"],
            "concurso_atual": ultimo_cnc,
            "quantidade_concursos": ciclo_atual["quantidade_concursos"],
            "dezenas_saidas": sorted(saidas),
            "dezenas_pendentes": pendentes,
            "total_dezenas_saidas": len(saidas),
            "total_dezenas_pendentes": len(pendentes),
            "percentual_completo": round((len(saidas) / spec.universo_size) * 100, 2),
            "universo": spec.universo_size,
            "em_andamento": ciclo_atual.get("em_andamento", False),
            "detalhes_concursos": sorted(
                historico_detalhes, key=lambda x: x["concurso"], reverse=True
            ),
        }

    @staticmethod
    def obter_metricas_historicas(modality_key: str = "diadesorte") -> dict:
        ciclos = AnaliseCicloCoberturaService.calcular_ciclos_completos(modality_key)
        ciclos_completos = [c for c in ciclos if not c.get("em_andamento", False)]
        if not ciclos_completos:
            return {
                "total_ciclos": 0,
                "media_concursos": 0,
                "ciclo_mais_curto": None,
                "ciclo_mais_longo": None,
                "distribuicao": {},
            }

        quantidades = [c["quantidade_concursos"] for c in ciclos_completos]
        distribuicao = {
            "10-15": 0, "16-20": 0, "21-25": 0, "26-30": 0, "31-35": 0, "36+": 0,
        }
        for qtd in quantidades:
            if qtd <= 15:
                distribuicao["10-15"] += 1
            elif qtd <= 20:
                distribuicao["16-20"] += 1
            elif qtd <= 25:
                distribuicao["21-25"] += 1
            elif qtd <= 30:
                distribuicao["26-30"] += 1
            elif qtd <= 35:
                distribuicao["31-35"] += 1
            else:
                distribuicao["36+"] += 1

        curto = min(ciclos_completos, key=lambda x: x["quantidade_concursos"])
        longo = max(ciclos_completos, key=lambda x: x["quantidade_concursos"])
        return {
            "total_ciclos": len(ciclos_completos),
            "media_concursos": round(sum(quantidades) / len(quantidades), 1),
            "ciclo_mais_curto": {
                "numero": curto["numero"],
                "concursos": curto["quantidade_concursos"],
                "inicio": curto["concurso_inicio"],
                "fim": curto["concurso_fim"],
            },
            "ciclo_mais_longo": {
                "numero": longo["numero"],
                "concursos": longo["quantidade_concursos"],
                "inicio": longo["concurso_inicio"],
                "fim": longo["concurso_fim"],
            },
            "distribuicao": distribuicao,
        }

    @staticmethod
    def comparar_ciclo_atual_com_historico(modality_key: str = "diadesorte") -> Optional[dict]:
        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        metricas = AnaliseCicloCoberturaService.obter_metricas_historicas(modality_key)
        if not ciclo or not metricas["total_ciclos"]:
            return None

        qtd = ciclo["quantidade_concursos"]
        media = metricas["media_concursos"]
        ciclos = AnaliseCicloCoberturaService.calcular_ciclos_completos(modality_key)
        completos = [c for c in ciclos if not c.get("em_andamento", False)]
        if completos:
            menores = len([c for c in completos if c["quantidade_concursos"] <= qtd])
            percentil = round((menores / len(completos)) * 100, 1)
        else:
            percentil = 0

        if qtd < media * 0.8:
            status = "curto"
        elif qtd > media * 1.2:
            status = "longo"
        else:
            status = "normal"

        if status == "curto":
            insight = f"Ciclo atual está {round(media - qtd, 1)} concursos abaixo da média histórica."
        elif status == "longo":
            insight = (
                f"Ciclo atual com {qtd} concursos já ultrapassou "
                f"{percentil:.0f}% dos ciclos históricos."
            )
        else:
            insight = f"Ciclo atual está dentro da normalidade ({qtd} concursos, média: {media})."

        return {
            "concursos_atual": qtd,
            "media_historica": media,
            "diferenca": round(qtd - media, 1),
            "percentil": percentil,
            "status": status,
            "insight": insight,
        }

    @staticmethod
    def obter_insights_e_recomendacoes(modality_key: str = "diadesorte") -> Optional[dict]:
        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        metricas = AnaliseCicloCoberturaService.obter_metricas_historicas(modality_key)
        if not ciclo or not metricas["total_ciclos"]:
            return None

        qtd = ciclo["quantidade_concursos"]
        media = metricas["media_concursos"]
        pendentes = ciclo["total_dezenas_pendentes"]
        insights = []

        if qtd < media * 0.7:
            insights.append({
                "titulo": "Ciclo em Estágio Inicial",
                "ponto": "positivo",
                "texto": (
                    f"O ciclo atual tem apenas {qtd} concursos. Historicamente, "
                    "a maioria dos ciclos fecha entre 10 e 20 concursos."
                ),
            })
        elif qtd < media:
            insights.append({
                "titulo": "Ciclo em Maturação",
                "ponto": "neutro",
                "texto": (
                    f"Com {qtd} concursos, estamos chegando próximo à média "
                    f"de fechamento ({media})."
                ),
            })
        else:
            insights.append({
                "titulo": "Ciclo Prolongado",
                "ponto": "alerta",
                "texto": (
                    f"Este ciclo já dura {qtd} concursos, superando a média histórica. "
                    "A probabilidade de fechamento iminente aumenta a cada sorteio."
                ),
            })

        if pendentes <= 3:
            insights.append({
                "titulo": "Retas Finais",
                "ponto": "positivo",
                "texto": (
                    f"Restam apenas {pendentes} dezenas para o ciclo fechar. "
                    "Em grande parte dos casos, as últimas dezenas saem em poucos concursos."
                ),
            })
        elif pendentes > 15:
            insights.append({
                "titulo": "Muitas Pendências",
                "ponto": "neutro",
                "texto": (
                    f"Ainda restam {pendentes} dezenas. O ciclo ainda tem fôlego "
                    "para vários concursos antes de fechar."
                ),
            })

        if qtd >= 20 and pendentes <= 5:
            prob = "ALTA"
        elif qtd >= 15:
            prob = "MÉDIA"
        else:
            prob = "BAIXA"
        insights.append({
            "titulo": "Expectativa de Fechamento",
            "ponto": "info",
            "texto": (
                f"A probabilidade estatística de o ciclo fechar nos próximos 3 concursos "
                f"é considerada {prob}."
            ),
        })

        recomendacoes = []
        if pendentes <= 5:
            recomendacoes.append({
                "texto": (
                    f"Priorize as {pendentes} pendentes nas apostas, sem tentar "
                    "fechá-las todas no mesmo jogo."
                ),
                "cor": "success",
                "icone": "fa-bullseye",
            })
        elif pendentes > 12:
            recomendacoes.append({
                "texto": (
                    "Ciclo ainda aberto: use poucas faltantes por jogo e acompanhe "
                    "a Qtd. Evolução na aba Ciclo Atual."
                ),
                "cor": "info",
                "icone": "fa-chart-line",
            })
        else:
            recomendacoes.append({
                "texto": (
                    "Equilibre faltantes e dezenas já saídas; veja a Inteligência "
                    "Operacional para o modo sugerido."
                ),
                "cor": "primary",
                "icone": "fa-balance-scale",
            })
        if qtd > media:
            recomendacoes.append({
                "texto": (
                    f"Duração acima da média ({media}): atenção à pressão de fechamento."
                ),
                "cor": "warning",
                "icone": "fa-exclamation-triangle",
            })

        return {"insights": insights, "recomendacoes": recomendacoes}

    @staticmethod
    def obter_historico_ultimos_ciclos(
        modality_key: str = "diadesorte", quantidade: int = 10
    ) -> List[dict]:
        ciclos = AnaliseCicloCoberturaService.calcular_ciclos_completos(modality_key)
        completos = [c for c in ciclos if not c.get("em_andamento", False)]
        ultimos = completos[-quantidade:] if len(completos) > quantidade else completos
        out = []
        for c in reversed(ultimos):
            out.append({
                "numero": c["numero"],
                "concurso_inicio": c["concurso_inicio"],
                "concurso_fim": c.get("concurso_fim"),
                "quantidade_concursos": c["quantidade_concursos"],
            })
        return out

    @staticmethod
    def obter_estatisticas_comportamento(modality_key: str = "diadesorte") -> dict:
        spec = get_ciclo_spec(modality_key)
        ciclos = AnaliseCicloCoberturaService.calcular_ciclos_completos(modality_key)
        completos = [c for c in ciclos if not c.get("em_andamento", False)]
        if not completos:
            return {
                "media_dezenas_novas": 0.0,
                "media_dezenas_repetidas": 0.0,
                "percentual_medio_novas": 0,
                "percentual_medio_repetidas": 0,
                "frequencia_sorteios": {
                    "total": 0, "nula": 0, "baixa": 0, "media": 0, "alta": 0,
                },
            }

        total_novas = 0
        total_repetidas = 0
        total_sorteadas = 0
        freq_nula = freq_baixa = freq_media = freq_alta = 0
        total_sorteios = 0

        for c in completos:
            novas = len(c["dezenas_saidas"])
            total_ciclo = c["quantidade_concursos"] * spec.sorteadas
            repetidas = max(0, total_ciclo - novas)
            total_novas += novas
            total_repetidas += repetidas
            total_sorteadas += total_ciclo
            for det in c.get("detalhes_concursos", []):
                q = det.get("qtd_novas", 0)
                if q == 0:
                    freq_nula += 1
                elif q in (1, 2):
                    freq_baixa += 1
                elif q in (3, 4):
                    freq_media += 1
                else:
                    freq_alta += 1
                total_sorteios += 1

        n = len(completos)
        media_novas = round(total_novas / n, 1)
        media_rep = round(total_repetidas / n, 1)
        pct_novas = round((total_novas / total_sorteadas) * 100, 1) if total_sorteadas else 0
        pct_rep = round((total_repetidas / total_sorteadas) * 100, 1) if total_sorteadas else 0
        return {
            "media_dezenas_novas": media_novas,
            "media_dezenas_repetidas": media_rep,
            "percentual_medio_novas": pct_novas,
            "percentual_medio_repetidas": pct_rep,
            "frequencia_sorteios": {
                "total": total_sorteios,
                "nula": freq_nula,
                "baixa": freq_baixa,
                "media": freq_media,
                "alta": freq_alta,
            },
        }

    @staticmethod
    def payload_metricas(modality_key: str = "diadesorte") -> Dict[str, Any]:
        metricas = AnaliseCicloCoberturaService.obter_metricas_historicas(modality_key)
        if not metricas.get("total_ciclos"):
            return {
                "sucesso": False,
                "mensagem": "Sem ciclos completos suficientes para métricas.",
            }
        return {
            "sucesso": True,
            "dados": {
                "metricas": metricas,
                "comparacao": AnaliseCicloCoberturaService.comparar_ciclo_atual_com_historico(
                    modality_key
                ),
                "historico": AnaliseCicloCoberturaService.obter_historico_ultimos_ciclos(
                    modality_key, 10
                ),
                "inteligencia": AnaliseCicloCoberturaService.obter_insights_e_recomendacoes(
                    modality_key
                ),
                "estatisticas": AnaliseCicloCoberturaService.obter_estatisticas_comportamento(
                    modality_key
                ),
            },
        }

    @staticmethod
    def obter_dezenas_sugeridas(modality_key: str = "diadesorte", quantidade: int = 3) -> List[int]:
        from .inteligencia_service import CicloInteligenciaService

        analise = CicloInteligenciaService.analisar_ciclo_completo(modality_key)
        if analise and analise.get("scores_dezenas"):
            top = [
                s["dezena"]
                for s in analise["scores_dezenas"]
                if s.get("pendente")
            ][:quantidade]
            if top:
                return top
        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        if not ciclo:
            return []
        return list(ciclo["dezenas_pendentes"][:quantidade])

    @staticmethod
    def payload_oficial(modality_key: str = "diadesorte") -> Dict[str, Any]:
        """Payload único consumido pela página de análise (e, no futuro, pelo gerador)."""
        from .inteligencia_service import CicloInteligenciaService

        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        if not ciclo:
            return {
                "sucesso": False,
                "mensagem": "Nenhum ciclo encontrado. Verifique se há sorteios cadastrados.",
            }

        return {
            "sucesso": True,
            "dados": ciclo,
            "inteligencia": AnaliseCicloCoberturaService.obter_insights_e_recomendacoes(
                modality_key
            ),
            "motor_ciclo": CicloInteligenciaService.analisar_ciclo_completo(modality_key),
            "comparacao": AnaliseCicloCoberturaService.comparar_ciclo_atual_com_historico(
                modality_key
            ),
            "top_3": AnaliseCicloCoberturaService.obter_dezenas_sugeridas(modality_key, 3),
            "metricas": AnaliseCicloCoberturaService.obter_metricas_historicas(modality_key),
        }
