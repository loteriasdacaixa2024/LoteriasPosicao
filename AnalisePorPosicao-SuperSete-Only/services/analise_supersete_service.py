"""
analise_supersete_service.py
=============================
Análise estatística posicional da Super Sete.

Super Sete tem 7 colunas independentes, cada uma com dígitos 0-9.
A análise é feita POR COLUNA, não globalmente como na Lotofácil.

Para cada coluna (1-7):
  - Frequência de cada dígito (0-9) naquela coluna
  - Atraso de cada dígito naquela coluna (concursos desde a última aparição)
  - Dígito atual (último sorteio)
"""

from models.shared import db
from models.sorteio_supersete import SorteioSuperSete
from sqlalchemy import desc

NUM_COLUNAS = 7
DIGITOS = list(range(10))  # 0-9


class AnaliseSuperSeteService:

    @staticmethod
    def get_stats_banco():
        """Retorna totais do banco para exibição no dashboard."""
        total = db.session.query(SorteioSuperSete).count()
        ultimo = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).first()
        return {
            "total_sorteios": total,
            "ultimo_concurso": ultimo.concurso if ultimo else 0,
            "ultima_data": ultimo.data if ultimo else "—",
        }

    @staticmethod
    def analise_geral():
        """Freq/atraso dos dígitos 0–9 (agregado nas 7 colunas) — compatível com _shared."""
        sorteios = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).all()
        if not sorteios:
            return None
        total = len(sorteios)
        ultimo = sorteios[0].concurso
        freq = {d: 0 for d in DIGITOS}
        visto = {d: 0 for d in DIGITOS}
        for s in sorteios:
            for d in s.digitos():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso
        resultado = []
        for d in DIGITOS:
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            pct = round(freq[d] / (total * NUM_COLUNAS) * 100, 1) if total else 0
            resultado.append({
                "dezena": d,
                "dezena_fmt": str(d),
                "freq": freq[d],
                "atraso": atraso,
                "pct": pct,
            })
        return {
            "dados": resultado,
            "total_sorteios": total,
            "ultimo_concurso": ultimo,
            "esperado_pct": round(100.0 / 10, 1),
        }

    @staticmethod
    def analise_por_coluna():
        """
        Retorna análise completa para cada uma das 7 colunas:
        frequência, atraso e dígito atual de cada dígito (0-9).
        """
        sorteios = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).all()

        if not sorteios:
            return None

        total = len(sorteios)
        ultimo_concurso = sorteios[0].concurso

        resultado = {}

        for col in range(1, NUM_COLUNAS + 1):
            col_key = f'coluna_{col}'

            # Frequência de cada dígito nesta coluna
            freq = {d: 0 for d in DIGITOS}
            visto = {d: 0 for d in DIGITOS}  # último concurso em que apareceu

            for s in sorteios:
                d = getattr(s, col_key)
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

            # Atraso: concursos desde a última aparição
            atraso = {}
            for d in DIGITOS:
                if visto[d] == 0:
                    atraso[d] = total  # nunca saiu
                else:
                    atraso[d] = ultimo_concurso - visto[d]

            # Dígito do último sorteio nesta coluna
            digito_atual = getattr(sorteios[0], col_key)

            # Ranking por atraso (maior primeiro) e frequência (maior primeiro)
            rank_atraso = sorted(DIGITOS, key=lambda d: -atraso[d])
            rank_freq   = sorted(DIGITOS, key=lambda d: -freq[d])

            resultado[col] = {
                "coluna":       col,
                "digito_atual": digito_atual,
                "freq":         freq,
                "atraso":       atraso,
                "rank_atraso":  rank_atraso,
                "rank_freq":    rank_freq,
                "total":        total,
                "ultimo_concurso": ultimo_concurso,
            }

        return resultado

    @staticmethod
    def _classificar_intrasorte(digs):
        """Classifica repetição dentro do mesmo sorteio (dupla, trinca, etc.)."""
        contagem = {}
        for d in digs:
            contagem[d] = contagem.get(d, 0) + 1
        duplas = trincas = outros = 0
        repetidos = []
        for d, qtd in contagem.items():
            if qtd > 1:
                repetidos.append({"digito": d, "qtd": qtd})
            if qtd == 2:
                duplas += 1
            elif qtd == 3:
                trincas += 1
            elif qtd > 3:
                outros += 1

        if duplas == 0 and trincas == 0 and outros == 0:
            tipo = "0_repeticao"
            label = "Todos únicos"
        elif duplas == 1 and trincas == 0 and outros == 0:
            tipo = "1_dupla"
            label = "1 dupla"
        elif duplas == 2 and trincas == 0 and outros == 0:
            tipo = "2_duplas"
            label = "2 duplas"
        elif trincas == 1 and duplas == 0 and outros == 0:
            tipo = "1_trinca"
            label = "1 trinca"
        else:
            tipo = "outros"
            label = "Múltiplas (quadras+)"

        partes = [f"{r['digito']}×{r['qtd']}" for r in sorted(repetidos, key=lambda x: -x["qtd"])]
        texto_rep = ", ".join(partes) if partes else "—"
        return tipo, label, repetidos, len(repetidos), texto_rep

    @staticmethod
    def _fmt_exemplo_concurso(concurso, data, digs, extra=""):
        cols = "-".join(str(d) for d in digs)
        sufixo = f" · {extra}" if extra else ""
        return f"#{concurso} ({data}) · {cols}{sufixo}"

    @classmethod
    def analise_repeticoes(cls):
        """
        Analisa a repetição de dígitos em um mesmo sorteio.
        Retorna estatísticas gerais, top 3 dígitos e top pares de colunas.
        """
        sorteios = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).all()

        if not sorteios:
            return None

        total = len(sorteios)
        tipos = {
            "0_repeticao": 0, "1_dupla": 0, "2_duplas": 0,
            "1_trinca": 0, "outros": 0,
        }
        exemplos_por_tipo = {k: [] for k in tipos}
        max_exemplos = 25

        freq_digitos_repetidos = {d: 0 for d in DIGITOS}
        pares_colunas = {}
        resumo_qtd_digitos = {0: 0, 1: 0, 2: 0, 3: 0}

        for s in sorteios:
            digs = s.digitos()
            tipo, _label, repetidos, qtd_distintos, texto_rep = cls._classificar_intrasorte(digs)
            tipos[tipo] += 1
            bucket = min(qtd_distintos, 3)
            resumo_qtd_digitos[bucket] = resumo_qtd_digitos.get(bucket, 0) + 1

            if len(exemplos_por_tipo[tipo]) < max_exemplos:
                exemplos_por_tipo[tipo].append({
                    "concurso": s.concurso,
                    "data": s.data,
                    "digitos": digs,
                    "repetidos": repetidos,
                    "texto_rep": texto_rep,
                })

            for r in repetidos:
                freq_digitos_repetidos[r["digito"]] += 1

            for i in range(7):
                for j in range(i + 1, 7):
                    if digs[i] == digs[j]:
                        par = (i + 1, j + 1)
                        pares_colunas[par] = pares_colunas.get(par, 0) + 1

        top_3 = sorted(DIGITOS, key=lambda d: -freq_digitos_repetidos[d])[:3]
        top_3_com_freq = [{"digito": d, "qtd_sorteios": freq_digitos_repetidos[d]} for d in top_3]

        top_3_pares = sorted(pares_colunas.items(), key=lambda x: -x[1])[:3]
        top_pares_fmt = [{"c1": x[0][0], "c2": x[0][1], "qtd": x[1]} for x in top_3_pares]

        tipo_labels = {
            "0_repeticao": "Todos únicos",
            "1_dupla": "1 dupla",
            "2_duplas": "2 duplas",
            "1_trinca": "1 trinca",
            "outros": "Múltiplas (quadras+)",
        }

        return {
            "total_analisado": total,
            "tipos": tipos,
            "tipo_labels": tipo_labels,
            "exemplos_por_tipo": exemplos_por_tipo,
            "resumo_qtd_digitos_repetidos": resumo_qtd_digitos,
            "perc_com_repeticao": round((total - tipos["0_repeticao"]) / total * 100, 1) if total > 0 else 0,
            "perc_sem_repeticao": round(tipos["0_repeticao"] / total * 100, 1) if total > 0 else 0,
            "top_3_repetidos": top_3_com_freq,
            "top_pares_colunas": top_pares_fmt,
        }

    @staticmethod
    def ultimos_sorteios():
        """Concursos recentes com metadados para filtros e abas do Sniper."""
        sorteios = db.session.query(SorteioSuperSete).order_by(
            desc(SorteioSuperSete.concurso)
        ).all()

        resultado = []
        for s in sorteios:
            digs = s.digitos()
            tipo, tipo_label, repetidos, qtd_distintos, texto_rep = (
                AnaliseSuperSeteService._classificar_intrasorte(digs)
            )
            resultado.append({
                "concurso": s.concurso,
                "data": s.data,
                "digitos": digs,
                "digitos_ordem": s.digitos_ordem_lista(),
                "repetidos": repetidos,
                "tipo_intrasorte": tipo,
                "tipo_intrasorte_label": tipo_label,
                "qtd_digitos_repetidos": qtd_distintos,
                "texto_repetidos": texto_rep,
                "rep_sequencial": [],
                "qtd_colunas_rep_sequencial": 0,
                "texto_rep_sequencial": "—",
            })

        for i, row in enumerate(resultado):
            if i + 1 >= len(resultado):
                continue
            anterior = resultado[i + 1]["digitos"]
            rep_seq = [
                {"posicao": pos + 1, "digito": digs}
                for pos, digs in enumerate(row["digitos"])
                if digs == anterior[pos]
            ]
            row["rep_sequencial"] = rep_seq
            row["qtd_colunas_rep_sequencial"] = len(rep_seq)
            if rep_seq:
                row["texto_rep_sequencial"] = ", ".join(
                    f"C{x['posicao']}={x['digito']}" for x in rep_seq
                )

        return resultado
