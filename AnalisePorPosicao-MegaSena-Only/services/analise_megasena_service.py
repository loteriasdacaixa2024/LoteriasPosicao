"""
analise_megasena_service.py
===========================
Análise estatística da Mega-Sena: 60 dezenas (01-60), sorteiam 6.
"""
import math
import random
from collections import Counter
from models.shared import db
from models.sorteio_megasena import SorteioMegaSena
from sqlalchemy import desc

TOTAL_DEZENAS = 60
NUM_SORTEADAS = 6

class AnaliseMegaSenaService:

    @staticmethod
    def analise_geral():
        sorteios = db.session.query(SorteioMegaSena).order_by(desc(SorteioMegaSena.concurso)).all()
        if not sorteios:
            return None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso
        freq   = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
        visto  = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        resultado = []
        for d in range(1, TOTAL_DEZENAS + 1):
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            pct    = round(freq[d] / total * 100, 1) if total > 0 else 0
            resultado.append({"dezena":d,"dezena_fmt":f"{d:02d}","freq":freq[d],"atraso":atraso,"pct":pct})

        return {
            "dados":           resultado,
            "total_sorteios":  total,
            "ultimo_concurso": ultimo,
            "esperado_pct":    round(NUM_SORTEADAS / TOTAL_DEZENAS * 100, 1),  # 10%
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = db.session.query(SorteioMegaSena).order_by(desc(SorteioMegaSena.concurso)).all()
        return [{"concurso":s.concurso,"data":s.data,"dezenas":s.dezenas_lista(),"dezenas_ordem":s.dezenas_ordem_lista()} for s in sorteios]

    @classmethod
    def analise_avancada(cls):
        """
        Executa mineração estatística e estratégica completa sobre a história da Mega-Sena.
        Computa 17 análises distintas em uma única passagem (Single-Pass) linear para performance máxima.
        """
        # Obter todos os sorteios de forma cronológica ascendente
        sorteios = db.session.query(SorteioMegaSena).order_by(SorteioMegaSena.concurso.asc()).all()
        if not sorteios:
            return None

        total = len(sorteios)
        ultimo_concurso = sorteios[-1].concurso
        ultimo_sorteio_data = sorteios[-1].data
        ultimo_sorteio_dezenas = sorteios[-1].dezenas_lista()

        # --- 1. Inicializações e Estruturas de Dados ---
        freq_geral = {d: 0 for d in range(1, 61)}
        visto_geral = {d: 0 for d in range(1, 61)}

        # Colunas (1 a 10)
        freq_colunas = {c: 0 for c in range(1, 11)}
        visto_colunas = {c: 0 for c in range(1, 11)}
        dist_colunas = {c: {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0} for c in range(1, 11)}

        # Linhas (1 a 6)
        freq_linhas = {l: 0 for l in range(1, 7)}
        visto_linhas = {l: 0 for l in range(1, 7)}
        dist_linhas = {l: {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0} for l in range(1, 7)}
        combinacoes_linhas = Counter()

        # Posições (1ª a 6ª dezena)
        pos_freq = {p: {d: 0 for d in range(1, 61)} for p in range(1, 7)}

        # Repetições
        repetidos_list = []
        freq_repetidos_qtd = Counter()
        freq_repeticao_por_dezena = {d: 0 for d in range(1, 61)}

        # Pares e Ímpares
        par_impar_dist = Counter()

        # Altas e Baixas
        alta_baixa_dist = Counter()

        # Somas e Faixas
        somas_list = []
        faixas_soma = {
            "21-100": 0,
            "101-150": 0,
            "151-200": 0,
            "201-250": 0,
            "251-300": 0,
            "301-345": 0
        }

        # Sequências consecutivas
        consec_counts = {
            "nenhuma": 0,
            "duque": 0,
            "terno": 0,
            "quadra": 0,
            "quina": 0,
            "sena": 0
        }
        freq_duques_consec = Counter()
        freq_ternos_consec = Counter()

        # Estratégias Avançadas
        moldura_set = {
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
            11, 20, 21, 30, 31, 40, 41, 50,
            51, 52, 53, 54, 55, 56, 57, 58, 59, 60
        }
        freq_moldura_centro = Counter()

        cruz_set = {
            5, 6, 15, 16, 25, 26, 35, 36, 45, 46, 55, 56,  # Colunas centrais
            21, 22, 23, 24, 25, 26, 27, 28, 29, 30,        # Linha 3
            31, 32, 33, 34, 35, 36, 37, 38, 39, 40         # Linha 4
        }
        freq_cruz = Counter()

        diag_principal_set = {1, 12, 23, 34, 45, 56}
        diag_secundaria_set = {10, 19, 28, 37, 46, 55}
        freq_diagonais = {
            "principal": 0,
            "secundaria": 0,
            "ambas": 0,
            "nenhuma": 0
        }

        quadrantes_set = {
            1: {1,2,3,4,5, 11,12,13,14,15, 21,22,23,24,25},
            2: {6,7,8,9,10, 16,17,18,19,20, 26,27,28,29,30},
            3: {31,32,33,34,35, 41,42,43,44,45, 51,52,53,54,55},
            4: {36,37,38,39,40, 46,47,48,49,50, 56,57,58,59,60}
        }
        freq_quadrantes = Counter()

        amplitudes_list = []

        # Contadores de tendências recentes
        recent_stats = {
            "par_impar": {10: Counter(), 50: Counter(), 100: Counter()},
            "alta_baixa": {10: Counter(), 50: Counter(), 100: Counter()},
            "colunas": {10: Counter(), 50: Counter(), 100: Counter()},
            "linhas": {10: Counter(), 50: Counter(), 100: Counter()}
        }

        # --- 2. Passagem Única Linear ---
        prev_dezenas = None
        for idx, s in enumerate(sorteios):
            dezenas = s.dezenas()
            dezenas_lista = s.dezenas_lista()

            # Frequência e Último concurso das dezenas
            for d in dezenas:
                freq_geral[d] += 1
                visto_geral[d] = s.concurso

            # Colunas
            col_counts = {c: 0 for c in range(1, 11)}
            for d in dezenas:
                col = (d - 1) % 10 + 1
                freq_colunas[col] += 1
                visto_colunas[col] = s.concurso
                col_counts[col] += 1
            for col, count in col_counts.items():
                dist_colunas[col][count] += 1

            # Linhas
            lin_counts = {l: 0 for l in range(1, 7)}
            for d in dezenas:
                lin = (d - 1) // 10 + 1
                freq_linhas[lin] += 1
                visto_linhas[lin] = s.concurso
                lin_counts[lin] += 1
            for lin, count in lin_counts.items():
                dist_linhas[lin][count] += 1

            # Distribuição de ocupação de linhas
            pattern_str = "-".join(map(str, sorted(lin_counts.values(), reverse=True)))
            combinacoes_linhas[pattern_str] += 1

            # Posições (1ª a 6ª)
            for p_idx, val in enumerate(dezenas_lista):
                pos_freq[p_idx + 1][val] += 1

            # Repetições do concurso anterior
            if prev_dezenas is not None:
                matches = dezenas & prev_dezenas
                rep_count = len(matches)
                repetidos_list.append(rep_count)
                freq_repetidos_qtd[rep_count] += 1
                for md in matches:
                    freq_repeticao_por_dezena[md] += 1
            prev_dezenas = dezenas

            # Pares e Ímpares
            evens = sum(1 for d in dezenas if d % 2 == 0)
            odds = 6 - evens
            par_impar_dist[(evens, odds)] += 1

            # Altas e Baixas
            lows = sum(1 for d in dezenas if d <= 30)
            highs = 6 - lows
            alta_baixa_dist[(lows, highs)] += 1

            # Soma
            draw_sum = sum(dezenas)
            somas_list.append(draw_sum)
            if 21 <= draw_sum <= 100:
                faixas_soma["21-100"] += 1
            elif 101 <= draw_sum <= 150:
                faixas_soma["101-150"] += 1
            elif 151 <= draw_sum <= 200:
                faixas_soma["151-200"] += 1
            elif 201 <= draw_sum <= 250:
                faixas_soma["201-250"] += 1
            elif 251 <= draw_sum <= 300:
                faixas_soma["251-300"] += 1
            elif 301 <= draw_sum <= 345:
                faixas_soma["301-345"] += 1

            # Sequências numéricas consecutivas
            seq_len = 1
            max_seq = 1
            curr_duques = []
            curr_ternos = []
            for i in range(1, 6):
                if dezenas_lista[i] == dezenas_lista[i-1] + 1:
                    seq_len += 1
                    curr_duques.append((dezenas_lista[i-1], dezenas_lista[i]))
                    if seq_len == 3:
                        curr_ternos.append((dezenas_lista[i-2], dezenas_lista[i-1], dezenas_lista[i]))
                else:
                    max_seq = max(max_seq, seq_len)
                    seq_len = 1
            max_seq = max(max_seq, seq_len)

            if max_seq == 1:
                consec_counts["nenhuma"] += 1
            elif max_seq == 2:
                consec_counts["duque"] += 1
            elif max_seq == 3:
                consec_counts["terno"] += 1
            elif max_seq == 4:
                consec_counts["quadra"] += 1
            elif max_seq == 5:
                consec_counts["quina"] += 1
            elif max_seq >= 6:
                consec_counts["sena"] += 1

            for dq in curr_duques:
                freq_duques_consec[dq] += 1
            for tr in curr_ternos:
                freq_ternos_consec[tr] += 1

            # Moldura vs Centro
            moldura_count = sum(1 for d in dezenas if d in moldura_set)
            centro_count = 6 - moldura_count
            freq_moldura_centro[(moldura_count, centro_count)] += 1

            # Cruz
            cruz_count = sum(1 for d in dezenas if d in cruz_set)
            freq_cruz[cruz_count] += 1

            # Diagonais
            has_dp = any(d in diag_principal_set for d in dezenas)
            has_ds = any(d in diag_secundaria_set for d in dezenas)
            if has_dp and has_ds:
                freq_diagonais["ambas"] += 1
            elif has_dp:
                freq_diagonais["principal"] += 1
            elif has_ds:
                freq_diagonais["secundaria"] += 1
            else:
                freq_diagonais["nenhuma"] += 1

            # Quadrantes
            q1 = sum(1 for d in dezenas if d in quadrantes_set[1])
            q2 = sum(1 for d in dezenas if d in quadrantes_set[2])
            q3 = sum(1 for d in dezenas if d in quadrantes_set[3])
            q4 = sum(1 for d in dezenas if d in quadrantes_set[4])
            freq_quadrantes[(q1, q2, q3, q4)] += 1

            # Amplitude
            amp = dezenas_lista[-1] - dezenas_lista[0]
            amplitudes_list.append(amp)

            # Tendências Recentes (Últimos 10, 50, 100)
            rem_idx = total - idx
            for t_range in [10, 50, 100]:
                if rem_idx <= t_range:
                    recent_stats["par_impar"][t_range][(evens, odds)] += 1
                    recent_stats["alta_baixa"][t_range][(lows, highs)] += 1
                    for c in range(1, 11):
                        recent_stats["colunas"][t_range][c] += col_counts[c]
                    for l in range(1, 7):
                        recent_stats["linhas"][t_range][l] += lin_counts[l]

        # --- 3. Processamento de Finais e Rankings ---
        dados_dezenas = []
        for d in range(1, 61):
            atr = (ultimo_concurso - visto_geral[d]) if visto_geral[d] > 0 else total
            pct = round(freq_geral[d] / total * 100, 2)
            dados_dezenas.append({
                "dezena": d,
                "dezena_fmt": f"{d:02d}",
                "freq": freq_geral[d],
                "pct": pct,
                "atraso": atr
            })

        dezenas_ordenadas_freq = sorted(dados_dezenas, key=lambda x: x["freq"], reverse=True)
        dezenas_ordenadas_atraso = sorted(dados_dezenas, key=lambda x: x["atraso"], reverse=True)

        # Colunas atraso e freq
        dados_colunas = []
        for c in range(1, 11):
            atr = (ultimo_concurso - visto_colunas[c]) if visto_colunas[c] > 0 else total
            pct = round(freq_colunas[c] / (total * 6) * 100, 2)
            dados_colunas.append({
                "coluna": c,
                "freq": freq_colunas[c],
                "pct": pct,
                "atraso": atr,
                "dist": {str(k): v for k, v in dist_colunas[c].items()}
            })

        # Linhas atraso e freq
        dados_linhas = []
        for l in range(1, 7):
            atr = (ultimo_concurso - visto_linhas[l]) if visto_linhas[l] > 0 else total
            pct = round(freq_linhas[l] / (total * 6) * 100, 2)
            dados_linhas.append({
                "linha": l,
                "freq": freq_linhas[l],
                "pct": pct,
                "atraso": atr,
                "dist": {str(k): v for k, v in dist_linhas[l].items()}
            })

        # Combinações recorrentes de linhas (Top 5)
        top_comb_linhas = [{"padrao": k, "freq": v, "pct": round(v / total * 100, 2)}
                           for k, v in combinacoes_linhas.most_common(5)]

        # Matriz 6x60 de posições
        dados_posicoes = {}
        for p in range(1, 7):
            sorted_pos = sorted([{"dezena": d, "freq": pos_freq[p][d], "pct": round(pos_freq[p][d] / total * 100, 2)}
                                 for d in range(1, 61)], key=lambda x: x["freq"], reverse=True)
            dados_posicoes[str(p)] = {
                "ranking": sorted_pos[:6],  # Top 6 dezenas que mais aparecem na posição p
                "dist": {str(d): pos_freq[p][d] for d in range(1, 61)}
            }

        # Repetições
        media_repetidos = round(sum(repetidos_list) / len(repetidos_list), 2) if repetidos_list else 0
        dist_repetidos = [{"qtd": k, "freq": v, "pct": round(v / len(repetidos_list) * 100, 2)}
                          for k, v in sorted(freq_repetidos_qtd.items())] if repetidos_list else []
        dezenas_que_mais_repetem = sorted([{"dezena": d, "freq": freq_repeticao_por_dezena[d]}
                                           for d in range(1, 61)], key=lambda x: x["freq"], reverse=True)[:5]

        # Pares e Ímpares
        dist_par_impar = [{"par": k[0], "impar": k[1], "freq": v, "pct": round(v / total * 100, 2)}
                          for k, v in sorted(par_impar_dist.items(), key=lambda x: x[1], reverse=True)]
        tendencias_par_impar = {}
        for t_range in [10, 50, 100]:
            tot_range = min(total, t_range)
            tendencias_par_impar[str(t_range)] = [
                {"par": k[0], "impar": k[1], "freq": v, "pct": round(v / tot_range * 100, 2)}
                for k, v in sorted(recent_stats["par_impar"][t_range].items(), key=lambda x: x[1], reverse=True)
            ]

        # Altas e Baixas
        dist_alta_baixa = [{"baixa": k[0], "alta": k[1], "freq": v, "pct": round(v / total * 100, 2)}
                           for k, v in sorted(alta_baixa_dist.items(), key=lambda x: x[1], reverse=True)]
        tendencias_alta_baixa = {}
        for t_range in [10, 50, 100]:
            tot_range = min(total, t_range)
            tendencias_alta_baixa[str(t_range)] = [
                {"baixa": k[0], "alta": k[1], "freq": v, "pct": round(v / tot_range * 100, 2)}
                for k, v in sorted(recent_stats["alta_baixa"][t_range].items(), key=lambda x: x[1], reverse=True)
            ]

        # Soma Total e Faixas
        somas_recentes = somas_list[-20:] if total >= 20 else somas_list
        concursos_recentes = [s.concurso for s in (sorteios[-20:] if total >= 20 else sorteios)]
        media_soma = round(sum(somas_list) / total, 2)
        dist_somas_faixas = [{"faixa": k, "freq": v, "pct": round(v / total * 100, 2)} for k, v in faixas_soma.items()]

        # Sequências Numéricas
        dist_consecutivas = [{"tipo": k, "freq": v, "pct": round(v / total * 100, 2)} for k, v in consec_counts.items()]
        top_duques_consec = [{"dezena_a": k[0], "dezena_b": k[1], "freq": v}
                             for k, v in freq_duques_consec.most_common(5)]
        top_ternos_consec = [{"dezena_a": k[0], "dezena_b": k[1], "dezena_c": k[2], "freq": v}
                             for k, v in freq_ternos_consec.most_common(5)]

        # Avançado (Moldura, Cruz, Diagonais, Regiões, Amplitude)
        dist_moldura = [{"moldura": k[0], "centro": k[1], "freq": v, "pct": round(v / total * 100, 2)}
                        for k, v in sorted(freq_moldura_centro.items(), key=lambda x: x[1], reverse=True)]
        dist_cruz = [{"qtd_na_cruz": k, "freq": v, "pct": round(v / total * 100, 2)}
                     for k, v in sorted(freq_cruz.items())]
        dist_diagonais = [{"tipo": k, "freq": v, "pct": round(v / total * 100, 2)} for k, v in freq_diagonais.items()]
        dist_quadrantes = [{"q1": k[0], "q2": k[1], "q3": k[2], "q4": k[3], "freq": v, "pct": round(v / total * 100, 2)}
                           for k, v in sorted(freq_quadrantes.items(), key=lambda x: x[1], reverse=True)[:5]]
        media_amplitude = round(sum(amplitudes_list) / total, 2)
        
        # Histograma de Amplitude
        freq_amplitudes = Counter(amplitudes_list)
        dist_amplitudes = [{"amplitude": k, "freq": v, "pct": round(v / total * 100, 2)}
                           for k, v in sorted(freq_amplitudes.items())]

        # --- 4. Geração Preditiva baseada em Modelos Estatísticos ---
        # Garantindo determinismo de pools mas com sorteio seguro
        # Quente: 6 dezenas do top 15 de frequência
        pool_quente = [x["dezena"] for x in dezenas_ordenadas_freq[:15]]
        sugestao_quente = sorted(random.sample(pool_quente, 6))

        # Fria: 6 dezenas do top 15 de atraso
        pool_fria = [x["dezena"] for x in dezenas_ordenadas_atraso[:15]]
        sugestao_fria = sorted(random.sample(pool_fria, 6))

        # Inteligente (Balanced): Mix ideal que passa em filtros de apostadores profissionais
        # 3 quentes, 1 atrasada, 2 neutras
        pool_neutras = [x["dezena"] for x in dezenas_ordenadas_freq[15:45]]
        sugestao_inteligente = None
        
        # Filtros:
        # 1. Soma entre 130 e 220
        # 2. 3P-3I ou 4P-2I ou 2P-4I
        # 3. 3B-3A ou 4B-2A ou 2B-4A
        # 4. Sem sequências consecutivas longas (comprimento máximo 2, no máximo 1 dupla)
        for _ in range(1000):
            sq = random.sample(pool_quente, 3)
            sf = random.sample(pool_fria, 1)
            sn = random.sample(pool_neutras, 2)
            comb = sorted(list(set(sq + sf + sn)))
            if len(comb) < 6:
                continue
            
            # Filtro 1: Soma
            c_sum = sum(comb)
            if not (130 <= c_sum <= 220):
                continue
                
            # Filtro 2: Pares
            c_evens = sum(1 for d in comb if d % 2 == 0)
            if c_evens not in [2, 3, 4]:
                continue
                
            # Filtro 3: Altas/Baixas
            c_lows = sum(1 for d in comb if d <= 30)
            if c_lows not in [2, 3, 4]:
                continue
                
            # Filtro 4: Consecutivas
            seq_len = 1
            max_seq = 1
            pair_count = 0
            for i in range(1, 6):
                if comb[i] == comb[i-1] + 1:
                    seq_len += 1
                    pair_count += 1
                else:
                    max_seq = max(max_seq, seq_len)
                    seq_len = 1
            max_seq = max(max_seq, seq_len)
            
            if max_seq > 2 or pair_count > 1:
                continue
                
            sugestao_inteligente = comb
            break

        # Fallback caso não encontre em 1000 tentativas (muito improvável)
        if not sugestao_inteligente:
            sugestao_inteligente = sorted(random.sample(range(1, 61), 6))

        return {
            "total_sorteios": total,
            "ultimo_concurso": ultimo_concurso,
            "ultimo_sorteio_data": ultimo_sorteio_data,
            "ultimo_sorteio_dezenas": ultimo_sorteio_dezenas,
            
            "dados_dezenas": dados_dezenas,
            "colunas": dados_colunas,
            "linhas": dados_linhas,
            "top_comb_linhas": top_comb_linhas,
            "posicoes": dados_posicoes,
            
            "repeticoes": {
                "media": media_repetidos,
                "dist_qtd": dist_repetidos,
                "top_dezenas": dezenas_que_mais_repetem
            },
            
            "par_impar": {
                "dist": dist_par_impar,
                "tendencias": tendencias_par_impar
            },
            
            "alta_baixa": {
                "dist": dist_alta_baixa,
                "tendencias": tendencias_alta_baixa
            },
            
            "soma": {
                "media": media_soma,
                "dist_faixas": dist_somas_faixas,
                "somas_recentes": somas_recentes,
                "concursos_recentes": concursos_recentes
            },
            
            "sequencias": {
                "dist_consec": dist_consecutivas,
                "top_duques": top_duques_consec,
                "top_ternos": top_ternos_consec
            },
            
            "avancado": {
                "dist_moldura": dist_moldura,
                "dist_cruz": dist_cruz,
                "dist_diagonais": dist_diagonais,
                "dist_quadrantes": dist_quadrantes,
                "media_amplitude": media_amplitude,
                "dist_amplitudes": dist_amplitudes
            },
            
            "preditivo": {
                "quente": sugestao_quente,
                "fria": sugestao_fria,
                "inteligente": sugestao_inteligente
            }
        }
