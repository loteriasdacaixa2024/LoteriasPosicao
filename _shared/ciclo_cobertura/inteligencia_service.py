# -*- coding: utf-8 -*-
"""Motor analítico de Ciclos das Dezenas — indicadores oficiais da análise."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .loaders import carregar_sorteios_asc
from .specs import get_ciclo_spec


class CicloInteligenciaService:
    """Indicadores oficiais consumidos pela página /analise/ciclo-cobertura/."""

    @staticmethod
    def _faixas(modality_key: str) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        spec = get_ciclo_spec(modality_key)
        mid = (spec.dezena_min + spec.dezena_max) // 3
        # Dia de Sorte clássico: 1-10 / 11-20 / 21-31
        if spec.universo_size == 31 and spec.dezena_min == 1:
            return (1, 10), (11, 20), (21, 31)
        a = spec.dezena_min
        b = a + mid - 1
        c = b + 1
        d = c + mid - 1
        return (a, b), (c, d), (d + 1, spec.dezena_max)

    @staticmethod
    def _faixa(dezena: int, modality_key: str = "diadesorte") -> str:
        baixa, media, alta = CicloInteligenciaService._faixas(modality_key)
        if baixa[0] <= dezena <= baixa[1]:
            return "baixa"
        if media[0] <= dezena <= media[1]:
            return "media"
        return "alta"

    @staticmethod
    def _ultimo_sorteio_dezenas(modality_key: str = "diadesorte") -> List[int]:
        sorteios = carregar_sorteios_asc(modality_key)
        if not sorteios:
            return []
        return list(sorteios[-1]["dezenas"])

    @staticmethod
    def _coletar_snapshots_historicos(modality_key: str = "diadesorte") -> List[dict]:
        from .analise_service import AnaliseCicloCoberturaService

        spec = get_ciclo_spec(modality_key)
        alvo = spec.universo_size
        ciclos = AnaliseCicloCoberturaService.calcular_ciclos_completos(modality_key)
        snapshots = []

        for ciclo in ciclos:
            saidas: set = set()
            n_concurso = 0
            for det in ciclo.get("detalhes_concursos", []):
                n_concurso += 1
                pendentes_antes = alvo - len(saidas)
                novas = set(det.get("novas", []))
                snapshots.append({
                    "numero_ciclo": ciclo["numero"],
                    "concurso": det["concurso"],
                    "concursos_no_ciclo": n_concurso,
                    "pendentes_antes": pendentes_antes,
                    "percentual_antes": round((len(saidas) / alvo) * 100, 1),
                    "qtd_faltantes_entraram": len(novas),
                    "qtd_novas": det.get("qtd_novas", 0),
                    "em_andamento": ciclo.get("em_andamento", False),
                })
                saidas.update(novas)
                saidas.update(det.get("repetidas", []))

        return snapshots

    @staticmethod
    def _cenarios_semelhantes(
        pendentes_atual: int,
        modality_key: str = "diadesorte",
        tolerancia_pendentes: int = 1,
    ) -> List[dict]:
        snapshots = CicloInteligenciaService._coletar_snapshots_historicos(modality_key)
        similares = [
            s for s in snapshots
            if abs(s["pendentes_antes"] - pendentes_atual) <= tolerancia_pendentes
            and s["pendentes_antes"] > 0
        ]
        if len(similares) < 5:
            similares = [
                s for s in snapshots
                if s["pendentes_antes"] > 0
                and abs(s["pendentes_antes"] - pendentes_atual) <= 3
            ]
        return similares

    @staticmethod
    def _distribuicao_faltantes_entrada(similares: List[dict]) -> Tuple[Dict[str, float], int]:
        if not similares:
            return {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0}, 0

        contagem: Counter = Counter()
        for s in similares:
            q = s["qtd_faltantes_entraram"]
            if q <= 0:
                contagem["0"] += 1
            elif q == 1:
                contagem["1"] += 1
            elif q == 2:
                contagem["2"] += 1
            elif q == 3:
                contagem["3"] += 1
            else:
                contagem["4+"] += 1

        total = len(similares)
        perc = {
            chave: round((contagem.get(chave, 0) / total) * 100, 1)
            for chave in ["0", "1", "2", "3", "4+"]
        }
        return perc, total

    @staticmethod
    def _classificar_estado_ciclo(concursos: int, media: float, percentual: float) -> str:
        if concursos < max(3, media * 0.55):
            return "Inicial"
        if concursos > media * 1.15:
            return "Crítico"
        if concursos >= media * 0.85 or percentual >= 72:
            return "Avançado"
        if concursos >= media * 0.55:
            return "Médio"
        return "Inicial"

    @staticmethod
    def _calcular_pressao(
        pendentes: int, concursos: int, media: float, perc_fechamento_gradual: float
    ) -> Tuple[str, int]:
        score = 0
        if pendentes <= 3:
            score += 35
        elif pendentes <= 6:
            score += 28
        elif pendentes <= 10:
            score += 18
        elif pendentes <= 15:
            score += 10
        else:
            score += 4

        if media > 0:
            ratio = concursos / media
            if ratio > 1.25:
                score += 30
            elif ratio > 1.05:
                score += 22
            elif ratio > 0.9:
                score += 15
            elif ratio > 0.7:
                score += 8

        if perc_fechamento_gradual > 55:
            score += 12
        elif perc_fechamento_gradual < 30:
            score -= 5

        if score >= 70:
            nivel = "extrema"
        elif score >= 50:
            nivel = "alta"
        elif score >= 30:
            nivel = "média"
        else:
            nivel = "baixa"
        return nivel, min(100, score)

    @staticmethod
    def _analisar_faltantes(pendentes: List[int], modality_key: str = "diadesorte") -> dict:
        baixa, media, alta = CicloInteligenciaService._faixas(modality_key)
        baixas = [d for d in pendentes if baixa[0] <= d <= baixa[1]]
        medias = [d for d in pendentes if media[0] <= d <= media[1]]
        altas = [d for d in pendentes if alta[0] <= d <= alta[1]]
        pares = [d for d in pendentes if d % 2 == 0]
        impares = [d for d in pendentes if d % 2 == 1]

        ordenadas = sorted(pendentes)
        consecutivas = []
        i = 0
        while i < len(ordenadas):
            seq = [ordenadas[i]]
            j = i + 1
            while j < len(ordenadas) and ordenadas[j] == ordenadas[j - 1] + 1:
                seq.append(ordenadas[j])
                j += 1
            if len(seq) >= 2:
                consecutivas.append(seq)
            i = j if j > i + 1 else i + 1

        gaps = [ordenadas[i + 1] - ordenadas[i] for i in range(len(ordenadas) - 1)]
        return {
            "baixas": baixas,
            "medias": medias,
            "altas": altas,
            "pares": pares,
            "impares": impares,
            "consecutivas": consecutivas,
            "espacamento_medio": round(sum(gaps) / len(gaps), 1) if gaps else 0,
            "distribuicao": {
                "baixas": len(baixas),
                "medias": len(medias),
                "altas": len(altas),
            },
        }

    @staticmethod
    def _tipo_fechamento_historico(similares: List[dict]) -> Tuple[str, str]:
        if not similares:
            return "gradual", "Dados insuficientes para classificar fechamento."
        agressivos = sum(1 for s in similares if s["qtd_faltantes_entraram"] >= 4)
        graduais = sum(1 for s in similares if 1 <= s["qtd_faltantes_entraram"] <= 3)
        nulos = sum(1 for s in similares if s["qtd_faltantes_entraram"] == 0)
        total = len(similares)
        pct_agr = agressivos / total * 100
        pct_grad = graduais / total * 100

        if pct_agr > 35:
            tipo = "agressivo"
            texto = (
                f"Histórico indica tendência a fechamento mais intenso "
                f"({pct_agr:.0f}% dos cenários semelhantes entraram com 4+ faltantes de uma vez)."
            )
        else:
            tipo = "gradual"
            texto = (
                f"Histórico favorece fechamento gradual "
                f"({pct_grad:.0f}% dos cenários entraram 1 a 3 faltantes; "
                f"{nulos / total * 100:.0f}% sem entrada de faltantes)."
            )
        return tipo, texto

    @staticmethod
    def _scores_dezenas(
        ciclo: dict, pendentes: List[int], modality_key: str = "diadesorte"
    ) -> List[dict]:
        spec = get_ciclo_spec(modality_key)
        ultimo = set(CicloInteligenciaService._ultimo_sorteio_dezenas(modality_key))
        scores = []
        for d in range(spec.dezena_min, spec.dezena_max + 1):
            score = 30
            if d in pendentes:
                score += 35
            if d in ultimo:
                score += 12
            if CicloInteligenciaService._faixa(d, modality_key) == "media" and d in pendentes:
                score += 5
            # Preferência leve por pendentes centrais na lista (dispersão)
            if d in pendentes:
                score += max(0, 8 - abs(d - (spec.universo_size // 2)) // 3)
            scores.append({
                "dezena": d,
                "score": min(99, score),
                "pendente": d in pendentes,
                "correlacao_mes": False,
            })
        scores.sort(key=lambda x: (-x["score"], x["dezena"]))
        return scores[:15]

    @staticmethod
    def _gerar_leitura(
        estado, n_pend, pct, pressao, media_entrada, tipo_fech, dist_media, media_hist
    ) -> str:
        partes = [
            f"Ciclo {estado.lower()} com {n_pend} dezena(s) faltante(s) e {pct:.0f}% de fechamento.",
            f"Pressão estatística {pressao}.",
        ]
        if media_entrada > 0:
            lo = max(1, int(media_entrada - 0.5))
            hi = min(7, int(media_entrada + 1))
            partes.append(
                f"Cenários semelhantes apresentam entrada média de {lo} a {hi} "
                f"faltante(s) no próximo concurso."
            )
        if tipo_fech == "gradual":
            partes.append("Não recomendado utilizar todas as pendentes no mesmo jogo.")
        if dist_media > 2:
            partes.append(
                f"O ciclo está {dist_media:.0f} concursos acima da média histórica ({media_hist:.1f})."
            )
        elif dist_media < -2:
            partes.append("O ciclo ainda está abaixo da média histórica de duração.")
        return " ".join(partes)

    @staticmethod
    def _definir_estrategia(
        estado, pressao, n_pend, tipo_fech, dist, analise_falt, ultimo
    ) -> dict:
        if n_pend <= 4 and pressao in ("alta", "extrema"):
            qtd_faltantes = min(3, n_pend)
        elif tipo_fech == "gradual":
            qtd_faltantes = 2 if n_pend >= 2 else n_pend
        else:
            qtd_faltantes = min(4, max(2, n_pend // 2))

        pct_2 = dist.get("2", 0) + dist.get("3", 0)
        if pct_2 > 50:
            qtd_faltantes = min(qtd_faltantes, 3)

        faixa_prior = "media"
        dist_f = analise_falt.get("distribuicao", {})
        if dist_f.get("medias", 0) >= dist_f.get("altas", 0):
            faixa_prior = "media"
        elif dist_f.get("altas", 0) > dist_f.get("baixas", 0) + 2:
            faixa_prior = "baixa"

        modo = "equilibrado"
        if pressao in ("alta", "extrema") and n_pend <= 8:
            modo = "agressivo" if tipo_fech == "agressivo" else "equilibrado"
        elif estado == "Inicial" or n_pend > 12:
            modo = "conservador"

        alertas = []
        if n_pend > 10 and estado != "Crítico":
            alertas.append("Ciclo ainda distante da zona crítica — evite fechamento completo.")
        if dist_f.get("altas", 0) > dist_f.get("baixas", 0) + 3:
            alertas.append("Excesso de dezenas altas entre as pendentes.")
        if tipo_fech == "gradual" and qtd_faltantes >= n_pend:
            alertas.append("Risco elevado de fechamento incompleto se usar todas as faltantes.")
        if dist.get("0", 0) > 25:
            alertas.append("Histórico mostra possível retenção (sorteio sem novas faltantes).")

        return {
            "modo_recomendado": modo,
            "faltantes_por_jogo": qtd_faltantes,
            "repetentes_por_jogo": 1 if len(ultimo) >= 7 else 1,
            "fechamento_parcial": tipo_fech == "gradual" or n_pend > 6,
            "priorizar_faixa": faixa_prior,
            "evitar_todas_faltantes": n_pend > 3,
            "alertas": alertas,
            "sugestao": {
                "usar_faltantes": (
                    f"{qtd_faltantes} ou {min(qtd_faltantes + 1, n_pend)} "
                    f"dezenas faltantes por jogo"
                ),
                "repetentes": "1 repetente(s) do último concurso",
                "pares_impares": "manter equilíbrio entre pares e ímpares",
                "faixa": (
                    f"priorizar dezenas {faixa_prior}as"
                    if faixa_prior != "media"
                    else "priorizar dezenas médias"
                ),
                "mes_correlacao": None,
            },
        }

    @staticmethod
    def analisar_ciclo_completo(modality_key: str = "diadesorte") -> Optional[Dict[str, Any]]:
        from .analise_service import AnaliseCicloCoberturaService

        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        metricas = AnaliseCicloCoberturaService.obter_metricas_historicas(modality_key)
        if not ciclo:
            return None

        media = metricas.get("media_concursos", 18) or 18
        concursos = ciclo["quantidade_concursos"]
        pendentes = ciclo["dezenas_pendentes"]
        n_pend = len(pendentes)
        percentual = ciclo["percentual_completo"]

        similares = CicloInteligenciaService._cenarios_semelhantes(n_pend, modality_key)
        dist, total_sim = CicloInteligenciaService._distribuicao_faltantes_entrada(similares)
        tipo_fech, texto_fech = CicloInteligenciaService._tipo_fechamento_historico(similares)
        pct_gradual = dist.get("1", 0) + dist.get("2", 0) + dist.get("3", 0)

        estado = CicloInteligenciaService._classificar_estado_ciclo(concursos, media, percentual)
        pressao_nivel, pressao_score = CicloInteligenciaService._calcular_pressao(
            n_pend, concursos, media, pct_gradual
        )

        distancia_media = round(concursos - media, 1)
        analise_falt = CicloInteligenciaService._analisar_faltantes(pendentes, modality_key)
        scores = CicloInteligenciaService._scores_dezenas(ciclo, pendentes, modality_key)
        ultimo = CicloInteligenciaService._ultimo_sorteio_dezenas(modality_key)

        media_entrada = 0.0
        if similares:
            media_entrada = round(
                sum(s["qtd_faltantes_entraram"] for s in similares) / len(similares), 1
            )

        leitura = CicloInteligenciaService._gerar_leitura(
            estado, n_pend, percentual, pressao_nivel, media_entrada,
            tipo_fech, distancia_media, media,
        )
        estrategia = CicloInteligenciaService._definir_estrategia(
            estado, pressao_nivel, n_pend, tipo_fech, dist, analise_falt, ultimo,
        )

        return {
            "estado_atual": {
                "numero_ciclo": ciclo["numero_ciclo"],
                "faltando": n_pend,
                "fechamento_percentual": percentual,
                "concursos_decorridos": concursos,
                "media_historica_fechamento": media,
                "distancia_media": distancia_media,
                "classificacao": estado,
                "pressao": pressao_nivel,
                "pressao_score": pressao_score,
            },
            "faltantes": analise_falt,
            "historico_semelhante": {
                "amostras": total_sim,
                "distribuicao_entrada": dist,
                "media_faltantes_entrada": media_entrada,
            },
            "fechamento": {
                "tipo": tipo_fech,
                "interpretacao": texto_fech,
            },
            "scores_dezenas": scores,
            "correlacao_mes": None,
            "leitura_automatica": leitura,
            "estrategia": estrategia,
        }

    @staticmethod
    def obter_inteligencia_operacional(
        modality_key: str = "diadesorte",
    ) -> Optional[Dict[str, Any]]:
        analise = CicloInteligenciaService.analisar_ciclo_completo(modality_key)
        if not analise:
            return None
        est = analise["estado_atual"]
        estr = analise["estrategia"]
        respostas = {
            "como_jogar": analise["leitura_automatica"],
            "quantas_faltantes": estr["faltantes_por_jogo"],
            "vale_fechamento": (
                not estr["fechamento_parcial"] if est["faltando"] <= 4 else "parcial"
            ),
            "vale_agressividade": estr["modo_recomendado"] in ("agressivo", "fechamento"),
            "estrutura_segura": (
                "equilibrada"
                if estr["modo_recomendado"] == "equilibrado"
                else estr["modo_recomendado"]
            ),
        }
        return {
            **analise,
            "operacional": {
                "respostas": respostas,
                "estrategia_recomendada": estr,
                "resumo_final": analise["leitura_automatica"],
            },
        }
