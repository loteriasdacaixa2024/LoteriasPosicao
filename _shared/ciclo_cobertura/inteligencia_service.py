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
    def _fase_ciclo(
        classificacao: str,
        n_pend: int,
        pressao: str,
        concursos: int,
        universo: int = 31,
        sorteadas: int = 7,
    ) -> Dict[str, Any]:
        """inicio | andamento | finalizacao — estratégia pesada no início e no fim."""
        saidas = max(0, universo - n_pend)
        # Início: 1º sorteio do ciclo (tipicamente 24 faltantes após 7 sorteadas)
        if concursos <= 1 or (saidas <= sorteadas and n_pend >= universo - sorteadas - 2):
            fase = "inicio"
            label = "Início do ciclo"
            estrategia_recomendada = True
        elif (
            n_pend <= 8
            or pressao in ("alta", "extrema")
            or classificacao in ("Avançado", "Crítico")
        ):
            fase = "finalizacao"
            label = "Finalização do ciclo"
            estrategia_recomendada = True
        else:
            fase = "andamento"
            label = "Andamento do ciclo"
            estrategia_recomendada = False
        return {
            "fase": fase,
            "label": label,
            "estrategia_recomendada": estrategia_recomendada,
            "dezenas_saidas_ciclo": saidas,
            "dezenas_faltantes": n_pend,
            "hint": (
                "Momento ideal para desdobramento estratégico (2 em 2)."
                if estrategia_recomendada
                else "Análise disponível; geração estratégica com aviso de fase intermediária."
            ),
        }

    @staticmethod
    def _analise_repeticoes_historicas(modality_key: str = "diadesorte") -> Dict[str, Any]:
        """Distribuição histórica de overlaps entre sorteios consecutivos (0/1/2/3+)."""
        sorteios = carregar_sorteios_asc(modality_key)
        cont: Counter = Counter()
        amostras = 0
        ultimo_overlap = None
        for i in range(1, len(sorteios)):
            a = set(int(x) for x in sorteios[i - 1]["dezenas"])
            b = set(int(x) for x in sorteios[i]["dezenas"])
            ov = len(a & b)
            if ov >= 3:
                cont["3+"] += 1
            else:
                cont[str(ov)] += 1
            amostras += 1
            if i == len(sorteios) - 1:
                ultimo_overlap = ov
        total = max(1, amostras)
        dist = {
            "0": round(100.0 * cont.get("0", 0) / total, 1),
            "1": round(100.0 * cont.get("1", 0) / total, 1),
            "2": round(100.0 * cont.get("2", 0) / total, 1),
            "3+": round(100.0 * cont.get("3+", 0) / total, 1),
        }
        # Cenário dominante (2 é o principal da estratégia quando empatado próximo)
        ordem = ["2", "1", "0", "3+"]
        dominante = max(ordem, key=lambda k: (dist.get(k, 0), 1 if k == "2" else 0))
        return {
            "amostras": amostras,
            "distribuicao_pct": dist,
            "contagem": {
                "0": cont.get("0", 0),
                "1": cont.get("1", 0),
                "2": cont.get("2", 0),
                "3+": cont.get("3+", 0),
            },
            "overlap_ultimo_vs_anterior": ultimo_overlap,
            "cenario_dominante": dominante,
            "leitura": (
                f"No histórico ({amostras} pares), repetição de {dominante} dezena(s) "
                f"é o cenário mais frequente ({dist.get(dominante, 0)}%). "
                "2 em 2 permanece a base estratégica; 0/1/3+ não são descartados."
            ),
        }

    @staticmethod
    def _atraso_e_frequencia(modality_key: str = "diadesorte") -> Dict[int, Dict[str, int]]:
        """Por dezena: atraso (concursos desde última saída) e frequência total."""
        spec = get_ciclo_spec(modality_key)
        sorteios = carregar_sorteios_asc(modality_key)
        freq: Counter = Counter()
        ultima_pos: Dict[int, int] = {}
        for i, s in enumerate(sorteios):
            for d in s["dezenas"]:
                di = int(d)
                freq[di] += 1
                ultima_pos[di] = i
        n = len(sorteios)
        out: Dict[int, Dict[str, int]] = {}
        for d in range(spec.dezena_min, spec.dezena_max + 1):
            if d in ultima_pos:
                atraso = n - 1 - ultima_pos[d]
            else:
                atraso = n
            out[d] = {"atraso": int(atraso), "frequencia": int(freq.get(d, 0))}
        return out

    @staticmethod
    def _classificar_estado_ciclo(concursos: int, media: float, percentual: float) -> str:
        # Fechamento alto / poucas faltantes prevalece sobre "poucos concursos"
        if percentual >= 85 or (percentual >= 72 and concursos >= 3):
            if concursos > media * 1.15:
                return "Crítico"
            return "Avançado"
        if concursos > media * 1.15:
            return "Crítico"
        if concursos >= media * 0.85:
            return "Avançado"
        if concursos >= media * 0.55:
            return "Médio"
        if concursos < max(3, media * 0.55):
            return "Inicial"
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
        af = CicloInteligenciaService._atraso_e_frequencia(modality_key)
        freqs = [af[d]["frequencia"] for d in range(spec.dezena_min, spec.dezena_max + 1)]
        atrasos = [af[d]["atraso"] for d in range(spec.dezena_min, spec.dezena_max + 1)]
        med_freq = (sum(freqs) / len(freqs)) if freqs else 1.0
        med_atraso = (sum(atrasos) / len(atrasos)) if atrasos else 1.0

        scores = []
        for d in range(spec.dezena_min, spec.dezena_max + 1):
            meta = af.get(d, {"atraso": 0, "frequencia": 0})
            atraso = meta["atraso"]
            frequencia = meta["frequencia"]
            faixa = CicloInteligenciaService._faixa(d, modality_key)
            recente = d in ultimo
            quente = frequencia >= med_freq * 1.15
            frio = atraso >= med_atraso * 1.25

            score = 30
            if d in pendentes:
                score += 35
                score += min(20, atraso)  # atraso favorece faltante
                if quente:
                    score += 6
                if frio:
                    score += 4
                if faixa == "media":
                    score += 5
                score += max(0, 8 - abs(d - (spec.universo_size // 2)) // 3)
            if recente:
                score += 12

            scores.append({
                "dezena": d,
                "score": min(99, score),
                "pendente": d in pendentes,
                "atraso": atraso,
                "frequencia": frequencia,
                "recente": recente,
                "quente": quente,
                "frio": frio,
                "faixa": faixa,
                "correlacao_mes": False,
            })
        scores.sort(key=lambda x: (-x["score"], x["dezena"]))
        return scores

    @staticmethod
    def scores_faltantes(
        ciclo: dict, pendentes: List[int], modality_key: str = "diadesorte"
    ) -> List[dict]:
        """Scores apenas das faltantes (ordenadas), para painel estratégico."""
        todos = CicloInteligenciaService._scores_dezenas(ciclo, pendentes, modality_key)
        return [s for s in todos if s.get("pendente")]

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
        scores_falt = [s for s in scores if s.get("pendente")]
        ultimo = CicloInteligenciaService._ultimo_sorteio_dezenas(modality_key)
        spec = get_ciclo_spec(modality_key)
        fase_info = CicloInteligenciaService._fase_ciclo(
            estado, n_pend, pressao_nivel, concursos,
            universo=spec.universo_size, sorteadas=spec.sorteadas,
        )
        repeticoes = CicloInteligenciaService._analise_repeticoes_historicas(modality_key)

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
        evolucao = CicloInteligenciaService.analisar_evolucao_ciclo(modality_key)

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
            "fase_ciclo": fase_info,
            "repeticoes_historicas": repeticoes,
            "evolucao_ciclo": evolucao,
            "faltantes": analise_falt,
            "scores_faltantes": scores_falt,
            "historico_semelhante": {
                "amostras": total_sim,
                "distribuicao_entrada": dist,
                "media_faltantes_entrada": media_entrada,
            },
            "fechamento": {
                "tipo": tipo_fech,
                "interpretacao": texto_fech,
            },
            "scores_dezenas": scores[:15],
            "correlacao_mes": None,
            "leitura_automatica": leitura,
            "estrategia": estrategia,
            "ultimo_sorteio": ultimo,
            "dezenas_pendentes": list(pendentes),
            "dezenas_saidas": list(ciclo.get("dezenas_saidas") or []),
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
        fase = analise.get("fase_ciclo") or {}
        rep = analise.get("repeticoes_historicas") or {}
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
            "fase_ciclo": fase.get("fase"),
            "estrategia_recomendada": bool(fase.get("estrategia_recomendada")),
            "repeticao_dominante": rep.get("cenario_dominante"),
        }
        return {
            **analise,
            "operacional": {
                "respostas": respostas,
                "estrategia_recomendada": estr,
                "fase_ciclo": fase,
                "repeticoes_historicas": rep,
                "resumo_final": analise["leitura_automatica"],
            },
        }

    @staticmethod
    def analisar_evolucao_ciclo(modality_key: str = "diadesorte") -> Optional[Dict[str, Any]]:
        """Observa a tabela Evolução do Ciclo: Novas, Qtd. Evolução, Repetidas, Progresso."""
        from .analise_service import AnaliseCicloCoberturaService

        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        if not ciclo:
            return None

        spec = get_ciclo_spec(modality_key)
        univ = spec.universo_size
        sorteadas = spec.sorteadas
        numero = ciclo.get("numero_ciclo")
        n_pend = int(ciclo.get("total_dezenas_pendentes") or len(ciclo.get("dezenas_pendentes") or []))
        progresso_atual = int(ciclo.get("total_dezenas_saidas") or (univ - n_pend))
        pct_atual = round(100.0 * progresso_atual / univ, 1) if univ else 0.0

        detalhes_all = list(ciclo.get("detalhes_concursos") or [])
        do_ciclo = [d for d in detalhes_all if d.get("numero_ciclo") == numero]
        if not do_ciclo:
            n = int(ciclo.get("quantidade_concursos") or 0)
            do_ciclo = sorted(detalhes_all, key=lambda x: x.get("concurso") or 0)[-n:] if n else []

        seq = sorted(do_ciclo, key=lambda x: x.get("concurso") or 0)

        def _linha(d: dict) -> dict:
            novas = [int(x) for x in (d.get("novas") or [])]
            repetidas = [int(x) for x in (d.get("repetidas") or [])]
            qtd = int(d.get("qtd_novas") if d.get("qtd_novas") is not None else len(novas))
            prog = int(d.get("total_preenchido") or 0)
            return {
                "concurso": d.get("concurso"),
                "data": d.get("data") or "",
                "novas": novas,
                "qtd_evolucao": qtd,
                "qtd_novas": qtd,
                "repetidas": repetidas,
                "qtd_repetidas": len(repetidas),
                "progresso": prog,
                "progresso_label": f"{prog}/{univ}",
                "progresso_pct": round(100.0 * prog / univ, 1) if univ else 0.0,
            }

        linhas = [_linha(d) for d in seq]
        recentes = linhas[-3:] if linhas else []
        qtds = [r["qtd_evolucao"] for r in linhas]
        qtds_rec = [r["qtd_evolucao"] for r in recentes]
        reps_q = [r["qtd_repetidas"] for r in linhas]
        reps_rec = [r["qtd_repetidas"] for r in recentes]

        cont: Counter = Counter()
        for q in qtds:
            if q <= 0:
                cont["0"] += 1
            elif q >= 4:
                cont["4+"] += 1
            else:
                cont[str(q)] += 1
        total = max(1, len(qtds))
        dist = {k: round(100.0 * cont.get(k, 0) / total, 1) for k in ("0", "1", "2", "3", "4+")}

        cont_rec: Counter = Counter()
        for q in (qtds_rec or qtds):
            if q <= 0:
                cont_rec["0"] += 1
            elif q >= 4:
                cont_rec["4+"] += 1
            else:
                cont_rec[str(q)] += 1
        tot_r = max(1, sum(cont_rec.values()))
        dist_rec = {k: round(100.0 * cont_rec.get(k, 0) / tot_r, 1) for k in ("0", "1", "2", "3", "4+")}
        ordem = ["1", "2", "0", "3", "4+"]
        dominante = max(ordem, key=lambda k: (dist_rec.get(k, 0), 1 if k in ("1", "2") else 0))

        media_rec = round(sum(qtds_rec) / len(qtds_rec), 2) if qtds_rec else 0.0
        media_ciclo = round(sum(qtds) / len(qtds), 2) if qtds else 0.0
        media_rep_rec = round(sum(reps_rec) / len(reps_rec), 2) if reps_rec else 0.0
        media_rep_ciclo = round(sum(reps_q) / len(reps_q), 2) if reps_q else 0.0
        ultimo = linhas[-1] if linhas else None
        ultimo_q = ultimo["qtd_evolucao"] if ultimo else None

        # Delta de progresso recente (avanço real do ciclo)
        deltas = []
        for i in range(1, len(linhas)):
            deltas.append(max(0, linhas[i]["progresso"] - linhas[i - 1]["progresso"]))
        deltas_rec = deltas[-3:] if deltas else []
        media_delta = round(sum(deltas_rec) / len(deltas_rec), 2) if deltas_rec else media_rec

        # --- Novas Dezenas: pool recente + faixas ---
        novas_recentes: List[int] = []
        for r in recentes:
            novas_recentes.extend(r["novas"])
        novas_recentes = sorted(set(novas_recentes))
        faixas_novas = Counter(
            CicloInteligenciaService._faixa(d, modality_key) for d in novas_recentes
        )
        faixa_nova_prior = (
            max(faixas_novas, key=faixas_novas.get) if faixas_novas else "media"
        )

        # --- Repetidas no Ciclo: pool que mais volta ---
        freq_rep: Counter = Counter()
        for r in linhas:
            for d in r["repetidas"]:
                freq_rep[int(d)] += 1
        top_repetidas = [d for d, _ in freq_rep.most_common(12)]

        # --- Qtd. Evolução → k faltantes ---
        if media_rec <= 0.5 or (ultimo_q == 0 and media_rec < 1.0):
            tendencia = "retencao"
            k_falt_sug = 1
        elif media_rec <= 1.5:
            tendencia = "baixa"
            k_falt_sug = 1
        elif media_rec <= 2.5:
            tendencia = "moderada"
            k_falt_sug = 2
        elif media_rec <= 4:
            tendencia = "media"
            k_falt_sug = 3
        else:
            tendencia = "alta"
            k_falt_sug = min(4, max(2, int(round(media_rec))))
        if dominante == "1" and dist_rec.get("1", 0) >= dist_rec.get("2", 0) + 10 and k_falt_sug >= 2:
            k_falt_sug = max(1, k_falt_sug - 1)
            tendencia = "baixa" if k_falt_sug == 1 else tendencia
        elif dominante == "2" and k_falt_sug == 1 and media_rec >= 1.5:
            k_falt_sug = 2
            tendencia = "moderada"
        if n_pend > 3:
            k_falt_sug = min(k_falt_sug, n_pend - 1, 3)
        # Progresso alto + poucas faltantes: reforça gradual
        if pct_atual >= 75 and n_pend <= 8:
            k_falt_sug = min(k_falt_sug, 2)
        k_falt_sug = max(1, min(k_falt_sug, n_pend, 6))

        # --- Repetidas no Ciclo → k repetentes (média recente, capped) ---
        k_rep_sug = int(round(media_rep_rec)) if reps_rec else int(round(media_rep_ciclo))
        if ultimo_q == 0:
            k_rep_sug = max(k_rep_sug, int(round(media_rep_rec)) if reps_rec else 3)
        k_rep_sug = max(1, min(3, k_rep_sug, sorteadas - 1))
        # Alinha com Qtd: tipicamente sorteadas ≈ novas + repetidas no ciclo
        if k_falt_sug + k_rep_sug > sorteadas:
            k_rep_sug = max(1, sorteadas - k_falt_sug)

        pesos = {
            k: 0.25 * dist.get(k, 0) + 0.75 * dist_rec.get(k, 0)
            for k in ("0", "1", "2", "3", "4+")
        }
        for q in qtds_rec:
            chave = "0" if q <= 0 else ("4+" if q >= 4 else str(q))
            pesos[chave] = pesos.get(chave, 0) + 18
        if n_pend <= 8:
            pesos["4+"] = min(pesos.get("4+", 0), 8)
            pesos["3"] = min(pesos.get("3", 0), 14)

        observacoes = {
            "novas_dezenas": {
                "recentes": novas_recentes,
                "faixa_prioritaria": faixa_nova_prior,
                "leitura": (
                    f"Novas recentes ({len(novas_recentes)}): "
                    f"{', '.join(f'{d:02d}' for d in novas_recentes) or '—'}. "
                    f"Faixa que mais preencheu: {faixa_nova_prior}."
                ),
            },
            "qtd_evolucao": {
                "sequencia": qtds,
                "media_ciclo": media_ciclo,
                "media_recente": media_rec,
                "dominante_recente": dominante,
                "distribuicao_ciclo_pct": dist,
                "distribuicao_recente_pct": dist_rec,
                "leitura": (
                    f"Qtd. Evolução recente média {media_rec} "
                    f"(dominante {dominante}). Ciclo médio {media_ciclo}."
                ),
            },
            "repetidas_no_ciclo": {
                "media_ciclo": media_rep_ciclo,
                "media_recente": media_rep_rec,
                "mais_frequentes": top_repetidas[:8],
                "leitura": (
                    f"Repetidas/concurso: média recente {media_rep_rec} "
                    f"(ciclo {media_rep_ciclo}). "
                    f"Mais recorrentes: "
                    f"{', '.join(f'{d:02d}' for d in top_repetidas[:6]) or '—'}."
                ),
            },
            "progresso": {
                "atual": progresso_atual,
                "universo": univ,
                "percentual": pct_atual,
                "label": f"{progresso_atual}/{univ}",
                "delta_medio_recente": media_delta,
                "faltantes": n_pend,
                "leitura": (
                    f"Progresso {progresso_atual}/{univ} ({pct_atual}%). "
                    f"Avanço médio recente +{media_delta} dezena(s)/concurso. "
                    f"Restam {n_pend}."
                ),
            },
        }

        # Tabela sutil: o que costuma vir (histórico) × neste ciclo
        def _freq_serie(valores: List[int], max_v: int = 7) -> Dict[str, Any]:
            c: Counter = Counter()
            for v in valores:
                c[max(0, min(max_v, int(v)))] += 1
            total = max(1, len(valores))
            linhas_f = []
            for q in range(0, max_v + 1):
                n = int(c.get(q, 0))
                linhas_f.append({
                    "qtd": q,
                    "vezes": n,
                    "pct": round(100.0 * n / total, 1),
                })
            top = sorted(linhas_f, key=lambda x: (-x["vezes"], x["qtd"]))
            top3 = [t for t in top if t["vezes"] > 0][:3]
            return {
                "amostras": len(valores),
                "linhas": linhas_f,
                "top3": top3,
                "mais_frequente": top3[0]["qtd"] if top3 else None,
            }

        # Histórico completo (todos os concursos nos detalhes) = "costuma"
        hist_qtd = [
            int(d.get("qtd_novas") or len(d.get("novas") or []))
            for d in detalhes_all
            if d.get("qtd_novas") is not None or d.get("novas") is not None
        ]
        hist_rep = [
            len(d.get("repetidas") or [])
            for d in detalhes_all
            if d.get("repetidas") is not None or d.get("qtd_novas") is not None
        ]
        # Delta progresso histórico
        por_ciclo: Dict[Any, List[dict]] = {}
        for d in detalhes_all:
            por_ciclo.setdefault(d.get("numero_ciclo"), []).append(d)
        hist_delta: List[int] = []
        for _nc, dets in por_ciclo.items():
            sd = sorted(dets, key=lambda x: x.get("concurso") or 0)
            for i in range(1, len(sd)):
                a = int(sd[i - 1].get("total_preenchido") or 0)
                b = int(sd[i].get("total_preenchido") or 0)
                hist_delta.append(max(0, min(7, b - a)))

        tabela_sutil = {
            "novas_qtd_evolucao": {
                "titulo": "Novas / Qtd. Evolução (quantas costumam vir)",
                "historico": _freq_serie(hist_qtd, 7),
                "ciclo_atual": _freq_serie(qtds, 7),
            },
            "repetidas_qtd": {
                "titulo": "Repetidas no Ciclo (quantas costumam repetir)",
                "historico": _freq_serie(hist_rep, 7),
                "ciclo_atual": _freq_serie(reps_q, 7),
            },
            "progresso_delta": {
                "titulo": "Progresso (quantas dezenas o ciclo avança por concurso)",
                "historico": _freq_serie(hist_delta, 7),
                "ciclo_atual": _freq_serie([max(0, min(7, int(x))) for x in deltas], 7),
            },
        }

        leitura = (
            f"Ciclo #{numero} — Evolução: "
            f"{observacoes['qtd_evolucao']['leitura']} "
            f"{observacoes['novas_dezenas']['leitura']} "
            f"{observacoes['repetidas_no_ciclo']['leitura']} "
            f"{observacoes['progresso']['leitura']} "
            f"Jogo sugerido: {k_falt_sug} nova(s)/faltante(s) + {k_rep_sug} repetida(s) no ciclo."
        )

        return {
            "numero_ciclo": numero,
            "quantidade_concursos": len(linhas),
            "universo": univ,
            "linhas": list(reversed(linhas[-8:])),
            "linhas_cronologicas": linhas,
            "ultimos": recentes,
            "observacoes": observacoes,
            "tabela_sutil": tabela_sutil,
            "sequencia_qtd_novas": qtds,
            "distribuicao_qtd_pct": dist,
            "distribuicao_recente_pct": dist_rec,
            "contagem_qtd": {k: cont.get(k, 0) for k in ("0", "1", "2", "3", "4+")},
            "dominante": dominante,
            "media_ciclo": media_ciclo,
            "media_recente": media_rec,
            "ultimo_qtd_novas": ultimo_q,
            "tendencia": tendencia,
            "k_faltantes_sugerido": k_falt_sug,
            "k_repeticao_sugerido": k_rep_sug,
            "pesos_amostra_k": pesos,
            "novas_recentes": novas_recentes,
            "faixa_nova_prioritaria": faixa_nova_prior,
            "top_repetidas_ciclo": top_repetidas,
            "progresso_atual": progresso_atual,
            "progresso_pct": pct_atual,
            "leitura": leitura,
        }

    @staticmethod
    def analisar_sequencias_repeticao(
        modality_key: str = "diadesorte",
        janela: int = 8,
    ) -> Dict[str, Any]:
        """Classifica dezenas por sequência de repetição (peso, não previsão)."""
        spec = get_ciclo_spec(modality_key)
        sorteios = carregar_sorteios_asc(modality_key)
        if not sorteios:
            return {
                "janela": janela,
                "dezenas": [],
                "por_classe": {},
                "leitura": "Sem sorteios para classificar repetição.",
            }

        recentes = sorteios[-max(4, janela):]
        n = len(recentes)
        appears: Dict[int, List[int]] = {
            d: [] for d in range(spec.dezena_min, spec.dezena_max + 1)
        }
        for i, s in enumerate(recentes):
            for d in s.get("dezenas") or []:
                appears[int(d)].append(i)

        items: List[dict] = []
        for d in range(spec.dezena_min, spec.dezena_max + 1):
            pos = appears[d]
            pos_set = set(pos)
            em_ultimo = (n - 1) in pos_set
            streak = 0
            for j in range(n - 1, -1, -1):
                if j in pos_set:
                    streak += 1
                else:
                    break
            streak_antes = 0
            for j in range(n - 2, -1, -1):
                if j in pos_set:
                    streak_antes += 1
                else:
                    break
            qtd_janela = len(pos)
            qtd_ult4 = sum(1 for p in pos if p >= n - 4)
            qtd_ult5 = sum(1 for p in pos if p >= n - 5)

            if streak >= 4 or qtd_ult4 >= 4:
                classe, peso = "excesso", -12.0
            elif streak == 3 or qtd_ult5 >= 4:
                classe, peso = "prolongada", -6.0
            elif (not em_ultimo) and streak_antes >= 2:
                classe, peso = "possivel_quebra", -4.0
            elif streak == 2:
                classe, peso = "consecutiva", -1.0
            elif em_ultimo:
                classe, peso = "recente", 0.0
            elif qtd_janela == 0:
                classe, peso = "fora", 5.0
            else:
                classe, peso = "esparsa", 2.0

            items.append({
                "dezena": d,
                "classe": classe,
                "peso": peso,
                "streak": streak,
                "qtd_janela": qtd_janela,
                "qtd_ult4": qtd_ult4,
                "em_ultimo": em_ultimo,
                "concursos": [int(recentes[p]["concurso"]) for p in pos],
            })

        por_classe: Dict[str, List[int]] = {}
        for it in items:
            por_classe.setdefault(it["classe"], []).append(it["dezena"])

        def _fmt(xs: List[int], lim: int = 8) -> str:
            xs = sorted(xs)
            corpo = ", ".join(f"{x:02d}" for x in xs[:lim])
            if len(xs) > lim:
                corpo += "…"
            return corpo or "—"

        leitura = (
            f"Sequências (janela {n}): "
            f"excesso {_fmt(por_classe.get('excesso', []), 6)}; "
            f"prolongadas {_fmt(por_classe.get('prolongada', []), 6)}; "
            f"consecutivas {_fmt(por_classe.get('consecutiva', []), 6)}; "
            f"possível quebra {_fmt(por_classe.get('possivel_quebra', []), 6)}. "
            "Peso estratégico — não afirma que a dezena sairá ou não."
        )
        return {
            "janela": n,
            "dezenas": items,
            "por_classe": {k: sorted(v) for k, v in por_classe.items()},
            "pesos": {int(it["dezena"]): float(it["peso"]) for it in items},
            "leitura": leitura,
        }

    @staticmethod
    def _tendencia_serie_evolucao(qtds: List[int]) -> str:
        rec = [int(x) for x in (qtds or [])][-4:]
        if not rec:
            return "estavel"
        if rec[-1] == 0 and (len(rec) < 2 or rec[-2] <= 1):
            return "retencao"
        if len(rec) >= 3:
            if rec[-1] > rec[-2] >= rec[-3]:
                return "crescente"
            if rec[-1] < rec[-2] <= rec[-3]:
                return "decrescente"
            if rec[-1] == rec[-2] == rec[-3]:
                return "estavel"
        if rec[-1] > rec[0]:
            return "crescente"
        if rec[-1] < rec[0]:
            return "decrescente"
        return "estavel"

    @staticmethod
    def _cotas_k_estagio(
        n_pend: int,
        quantidade: int,
        evo: Dict[str, Any],
        pick_n: int,
    ) -> Dict[int, int]:
        """Cotas de k (pendentes por jogo) segundo estágio + série recente."""
        k_max = max(0, min(6, n_pend, pick_n))
        if quantidade <= 0:
            return {}
        k_sug = int(evo.get("k_faltantes_sugerido") or 1)
        k_sug = max(0, min(k_sug, k_max))
        tendencia = str(evo.get("tendencia_serie") or evo.get("tendencia") or "")
        serie = [int(x) for x in (evo.get("sequencia_qtd_novas") or [])]
        recent = serie[-3:] if serie else []

        if n_pend <= 0:
            pesos = {0: 100.0}
        elif n_pend <= 3:
            pesos = {0: 35.0, 1: 50.0, 2: 15.0}
        elif n_pend == 4:
            pesos = {0: 25.0, 1: 50.0, 2: 25.0}
        elif n_pend <= 8:
            pesos = {0: 12.0, 1: 38.0, 2: 38.0, 3: 12.0}
        else:
            pesos = {1: 18.0, 2: 34.0, 3: 32.0, 4: 16.0}

        pesos[k_sug] = pesos.get(k_sug, 0.0) + 18.0
        if recent:
            modo = Counter(min(k_max, max(0, q)) for q in recent).most_common(1)[0][0]
            pesos[modo] = pesos.get(modo, 0.0) + 16.0
        if tendencia in ("retencao", "baixa"):
            pesos[0] = pesos.get(0, 0.0) + 12.0
            if 1 in pesos:
                pesos[1] += 8.0
        elif tendencia == "crescente" and k_sug + 1 <= k_max:
            pesos[k_sug + 1] = pesos.get(k_sug + 1, 0.0) + 8.0

        pesos = {k: w for k, w in pesos.items() if 0 <= k <= k_max and w > 0}
        if not pesos:
            pesos = {min(1, k_max): 100.0}

        total_w = sum(pesos.values()) or 1.0
        keys = sorted(pesos)
        exact = {k: quantidade * pesos[k] / total_w for k in keys}
        cotas = {k: int(exact[k]) for k in keys}
        falta = quantidade - sum(cotas.values())
        ordenados = sorted(keys, key=lambda k: (-(exact[k] - cotas[k]), -pesos[k], k))
        i = 0
        while falta > 0 and ordenados:
            cotas[ordenados[i % len(ordenados)]] += 1
            falta -= 1
            i += 1
        return {k: n for k, n in cotas.items() if n > 0}

    @staticmethod
    def _grupos_distribuicao(candidatas: List[int], n_apostas: int) -> List[List[int]]:
        """Distribui repetidas ativas entre apostas (2+2, cruzamentos, 1 concentrada)."""
        xs = [int(x) for x in candidatas[:6]]
        if not xs:
            return [[] for _ in range(max(1, n_apostas))]
        if len(xs) == 1:
            padroes = [[xs[0]], []]
        elif len(xs) == 2:
            a, b = xs
            padroes = [[a], [b], [a, b], [a], [b]]
        elif len(xs) == 3:
            a, b, c = xs
            padroes = [[a, b], [c], [a, c], [b], [a, b, c], [b, c]]
        else:
            a, b, c, d = xs[0], xs[1], xs[2], xs[3]
            padroes = [
                [a, b], [c, d], [a, c], [b, d], [a, d],
                [b, c], [a, b, c], [d], [a, c], [b, d],
            ]
        out = []
        for i in range(max(1, n_apostas)):
            out.append(list(padroes[i % len(padroes)]))
        return out

    @staticmethod
    def montar_estrategia_ciclo(
        modality_key: str = "diadesorte",
        *,
        quantidade: int = 10,
        pick: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Plano de decisão: novas + evolução + repetidas + progresso → cotas e núcleos."""
        from .analise_service import AnaliseCicloCoberturaService

        spec = get_ciclo_spec(modality_key)
        ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
        if not ciclo:
            return None
        evo = CicloInteligenciaService.analisar_evolucao_ciclo(modality_key) or {}
        seq = CicloInteligenciaService.analisar_sequencias_repeticao(modality_key)

        pick_n = int(pick if pick is not None else spec.pick_default)
        pick_n = max(spec.pick_min, min(spec.pick_max, pick_n))
        qtd = max(1, min(int(quantidade or 10), 80))

        pendentes = [int(x) for x in (ciclo.get("dezenas_pendentes") or [])]
        saidas = [int(x) for x in (ciclo.get("dezenas_saidas") or [])]
        saidas_set = set(saidas)
        n_pend = len(pendentes)
        pct = float(ciclo.get("percentual_completo") or evo.get("progresso_pct") or 0)
        serie = [int(x) for x in (evo.get("sequencia_qtd_novas") or [])]
        tendencia_serie = CicloInteligenciaService._tendencia_serie_evolucao(serie)
        evo = dict(evo)
        evo["tendencia_serie"] = tendencia_serie

        if n_pend <= 3 and pct >= 80:
            estagio = "fechamento"
        elif n_pend <= 8 and pct >= 70:
            estagio = "fechamento"
        elif pct < 40:
            estagio = "inicial"
        elif ciclo.get("quantidade_concursos", 0) > (18 * 1.15):
            estagio = "atrasado"
        else:
            estagio = "evolucao"

        cotas = CicloInteligenciaService._cotas_k_estagio(n_pend, qtd, evo, pick_n)

        af = CicloInteligenciaService._atraso_e_frequencia(modality_key)
        atrasadas = sorted(
            saidas,
            key=lambda d: (-int(af.get(d, {}).get("atraso", 0)), d),
        )
        pesos_rep = seq.get("pesos") or {}
        por = seq.get("por_classe") or {}

        aliviar = [
            d for d in (por.get("excesso") or []) + (por.get("possivel_quebra") or [])
            if d in saidas_set
        ]
        ativas = [
            d for d in (
                (por.get("consecutiva") or [])
                + (por.get("prolongada") or [])
                + (por.get("recente") or [])
            )
            if d in saidas_set and d not in aliviar
        ]
        # ordem: mais presentes na janela primeiro
        meta = {int(it["dezena"]): it for it in (seq.get("dezenas") or [])}
        ativas = sorted(
            dict.fromkeys(ativas),
            key=lambda d: (-int((meta.get(d) or {}).get("qtd_janela") or 0), d),
        )
        fora = [d for d in (por.get("fora") or []) if d in saidas_set]

        nucleo = [d for d in atrasadas if d not in aliviar][:4]
        variacao = [d for d in atrasadas if d not in nucleo]
        for d in fora:
            if d not in nucleo and d not in variacao:
                variacao.insert(0, d)
        grupos = CicloInteligenciaService._grupos_distribuicao(ativas[:4], qtd)

        k_esp = int(evo.get("k_faltantes_sugerido") or 1)
        media_rec = evo.get("media_recente")
        dist_txt = ", ".join(f"{n}×k={k}" for k, n in sorted(cotas.items()))
        pend_txt = ", ".join(f"{d:02d}" for d in pendentes) or "—"
        nucleo_txt = ", ".join(f"{d:02d}" for d in nucleo) or "—"
        aliviar_txt = ", ".join(f"{d:02d}" for d in aliviar[:6]) or "—"
        serie_txt = "–".join(str(x) for x in serie[-4:]) or "—"

        leitura_curta = (
            f"Evolução observada: {k_esp} nova(s) (série {serie_txt}, tendência {tendencia_serie}) · "
            f"Repetição: {'alta' if (evo.get('media_recente') is not None and float(evo.get('media_ciclo') or 5) >= 4) else 'moderada'} · "
            f"Prolongadas/excesso: {aliviar_txt} · "
            f"Pendentes: {n_pend} ({pend_txt}) · "
            f"Progresso: {pct:.0f}% ({estagio}) · "
            f"Estratégia: núcleo {nucleo_txt}; distribuir repetidas ativas; cotas {dist_txt}."
        )
        return {
            "numero_ciclo": ciclo.get("numero_ciclo"),
            "estagio": estagio,
            "progresso_pct": pct,
            "quantidade_concursos": ciclo.get("quantidade_concursos"),
            "pendentes": pendentes,
            "saidas": saidas,
            "k_esperado": k_esp,
            "media_recente": media_rec,
            "tendencia_evolucao": tendencia_serie,
            "serie_qtd": serie[-8:],
            "cotas_k": cotas,
            "nucleo_ancoras": nucleo,
            "variacao_ancoras": variacao[:10],
            "repetidas_ativas": ativas[:6],
            "repetidas_aliviar": aliviar,
            "repetidas_fora": fora[:10],
            "grupos_repetidas": grupos,
            "pesos_repeticao": {int(k): float(v) for k, v in pesos_rep.items()},
            "sequencias": seq,
            "faixa_principal": evo.get("faixa_nova_prioritaria") or "media",
            "leitura_curta": leitura_curta,
            "aviso_nao_previsao": (
                "A análise do ciclo não prevê quais dezenas serão sorteadas. "
                "Ela organiza as apostas segundo comportamentos observados nos ciclos anteriores."
            ),
            "pick": pick_n,
            "quantidade": qtd,
        }

    @staticmethod
    def contexto_estrategia(modality_key: str = "diadesorte") -> Optional[Dict[str, Any]]:
        """Payload para Ciclo — Apostas (aba Ciclo — Estratégias)."""
        analise = CicloInteligenciaService.analisar_ciclo_completo(modality_key)
        if not analise:
            return None
        est = analise["estado_atual"]
        fase = analise.get("fase_ciclo") or {}
        rep = analise.get("repeticoes_historicas") or {}
        evo = CicloInteligenciaService.analisar_evolucao_ciclo(modality_key) or {}
        k_rep = evo.get("k_repeticao_sugerido")
        if k_rep is None:
            dom = str(rep.get("cenario_dominante") or "2")
            k_rep = 2 if dom in ("2", "3+") else max(0, min(3, int(dom) if dom.isdigit() else 2))
        plano = CicloInteligenciaService.montar_estrategia_ciclo(modality_key, quantidade=10)
        return {
            "sucesso": True,
            "numero_ciclo": est.get("numero_ciclo"),
            "fase": fase,
            "estado_atual": est,
            "repeticoes_historicas": rep,
            "evolucao_ciclo": evo,
            "estrategia_ciclo": plano,
            "k_repeticao_sugerido": int(k_rep),
            "k_faltantes_sugerido": int(evo.get("k_faltantes_sugerido") or 2),
            "desdobramento_default": "auto",
            "desdobramento_opcoes": [2, 3, 4, 5, 6],
            "desdobramento_bloqueado": [7],
            "dezenas_pendentes": analise.get("dezenas_pendentes") or [],
            "dezenas_saidas": analise.get("dezenas_saidas") or [],
            "ultimo_sorteio": analise.get("ultimo_sorteio") or [],
            "scores_faltantes": analise.get("scores_faltantes") or [],
            "estrategia": analise.get("estrategia"),
            "leitura": analise.get("leitura_automatica"),
            "elite_href": "/geradores-elite/ciclo-apostas/?modo=estrategia",
        }

