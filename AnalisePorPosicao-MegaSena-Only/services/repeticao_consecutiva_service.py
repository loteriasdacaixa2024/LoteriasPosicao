"""
Repetição de dezenas entre concursos consecutivos da Mega-Sena.
Análise estrutural histórica (não gera dezenas aleatórias).
"""
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from models.shared import db
from models.sorteio_megasena import SorteioMegaSena


def _pct(qtd: int, total: int) -> float:
    return round(qtd / total * 100, 1) if total else 0.0


def _ano_de_data(data: str) -> Optional[str]:
    if not data or len(data) < 4:
        return None
    parts = data.split("/")
    if len(parts) == 3:
        return parts[2]
    return data[-4:]


def _decada(ano: str) -> Optional[str]:
    if not ano or not ano.isdigit() or len(ano) < 4:
        return None
    base = (int(ano) // 10) * 10
    return f"{base}s"


class RepeticaoConsecutivaService:

    @classmethod
    def analise_completa(cls) -> Optional[Dict[str, Any]]:
        sorteios = (
            db.session.query(SorteioMegaSena)
            .order_by(SorteioMegaSena.concurso.asc())
            .all()
        )
        if len(sorteios) < 2:
            return None

        total_pares = len(sorteios) - 1
        freq_qtd = Counter()
        exemplos_por_qtd: Dict[int, List[Dict]] = defaultdict(list)
        historico: List[Dict[str, Any]] = []

        por_ano: Dict[str, List[int]] = defaultdict(list)
        por_decada: Dict[str, List[int]] = defaultdict(list)

        streak_sem = streak_com = 0
        max_streak_sem = max_streak_com = 0
        inicio_max_sem = fim_max_sem = None
        inicio_max_com = fim_max_com = None
        cur_inicio_sem = cur_inicio_com = None

        prev = sorteios[0]
        for s in sorteios[1:]:
            atual_dz = s.dezenas()
            prev_dz = prev.dezenas()
            rep_set = atual_dz & prev_dz
            qtd = len(rep_set)
            freq_qtd[qtd] += 1

            ex_item = {
                "concurso_anterior": prev.concurso,
                "data_anterior": prev.data,
                "dezenas_anterior": [f"{d:02d}" for d in sorted(prev_dz)],
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": [f"{d:02d}" for d in sorted(atual_dz)],
                "repetidas": [f"{d:02d}" for d in sorted(rep_set)],
                "quantidade": qtd,
            }
            if len(exemplos_por_qtd[qtd]) < 5:
                exemplos_por_qtd[qtd].append(ex_item)

            historico.append({
                "concurso": s.concurso,
                "quantidade": qtd,
                "repetidas": sorted(rep_set),
            })

            ano = _ano_de_data(s.data)
            if ano:
                por_ano[ano].append(qtd)
                dec = _decada(ano)
                if dec:
                    por_decada[dec].append(qtd)

            if qtd == 0:
                if streak_sem == 0:
                    cur_inicio_sem = s.concurso
                streak_sem += 1
                if streak_com > max_streak_com:
                    max_streak_com = streak_com
                    inicio_max_com = cur_inicio_com
                    fim_max_com = s.concurso - 1
                streak_com = 0
                cur_inicio_com = None
                if streak_sem > max_streak_sem:
                    max_streak_sem = streak_sem
                    inicio_max_sem = cur_inicio_sem
                    fim_max_sem = s.concurso
            else:
                if streak_com == 0:
                    cur_inicio_com = s.concurso
                streak_com += 1
                if streak_sem > max_streak_sem:
                    max_streak_sem = streak_sem
                    inicio_max_sem = cur_inicio_sem
                    fim_max_sem = s.concurso - 1
                streak_sem = 0
                cur_inicio_sem = None
                if streak_com > max_streak_com:
                    max_streak_com = streak_com
                    inicio_max_com = cur_inicio_com
                    fim_max_com = s.concurso

            prev = s

        if streak_sem > max_streak_sem:
            max_streak_sem = streak_sem
            inicio_max_sem = cur_inicio_sem
            fim_max_sem = sorteios[-1].concurso
        if streak_com > max_streak_com:
            max_streak_com = streak_com
            inicio_max_com = cur_inicio_com
            fim_max_com = sorteios[-1].concurso

        todas_qtds = [h["quantidade"] for h in historico]
        media_global = round(sum(todas_qtds) / len(todas_qtds), 2) if todas_qtds else 0

        distribuicao = []
        for k in range(7):
            qtd_freq = freq_qtd.get(k, 0)
            if k == 0:
                label = "0 dezenas repetidas"
            elif k == 1:
                label = "1 dezena repetida"
            else:
                label = f"{k} dezenas repetidas"
            distribuicao.append({
                "repeticoes": label,
                "quantidade": qtd_freq,
                "porcentagem": _pct(qtd_freq, total_pares),
                "exemplos": exemplos_por_qtd.get(k, []),
            })

        ult = sorteios[-1]
        pen = sorteios[-2]
        ult_rep = ult.dezenas() & pen.dezenas()
        ult_qtd = len(ult_rep)
        freq_ult_qtd = freq_qtd.get(ult_qtd, 0)

        ultimo_analise = {
            "concurso": ult.concurso,
            "concurso_anterior": pen.concurso,
            "dezenas_repetidas_qtd": ult_qtd,
            "dezenas_repetidas": [f"{d:02d}" for d in sorted(ult_rep)],
            "dezenas_atual": [f"{d:02d}" for d in ult.dezenas_lista()],
            "dezenas_anterior": [f"{d:02d}" for d in pen.dezenas_lista()],
            "freq_historica_estrutura": freq_ult_qtd,
            "pct_historica_estrutura": _pct(freq_ult_qtd, total_pares),
        }

        def _media_lista(vals: List[int]) -> float:
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        media_por_ano = [
            {"ano": ano, "media": _media_lista(vals), "concursos": len(vals)}
            for ano, vals in sorted(por_ano.items())
        ]
        media_por_decada = [
            {"decada": dec, "media": _media_lista(vals), "concursos": len(vals)}
            for dec, vals in sorted(por_decada.items())
        ]

        def _resumo_janela(n: int) -> Dict[str, Any]:
            slice_h = historico[-n:] if len(historico) >= n else historico
            if not slice_h:
                return {}
            dist = Counter(h["quantidade"] for h in slice_h)
            media = round(sum(h["quantidade"] for h in slice_h) / len(slice_h), 2)
            moda = dist.most_common(1)[0][0] if dist else 0
            return {
                "concursos": len(slice_h),
                "media_repeticao": media,
                "moda_repeticao": moda,
                "distribuicao": {str(k): dist.get(k, 0) for k in range(7)},
                "acima_media_historica": media > media_global,
            }

        recente_10 = _resumo_janela(10)
        recente_30 = _resumo_janela(30)

        ultimos_100 = historico[-100:] if len(historico) >= 100 else historico
        media_100 = (
            round(sum(h["quantidade"] for h in ultimos_100) / len(ultimos_100), 2)
            if ultimos_100 else 0
        )
        tendencia = "estável"
        if media_100 > media_global + 0.15:
            tendencia = "acima da média"
        elif media_100 < media_global - 0.15:
            tendencia = "abaixo da média"

        sugestoes = cls._sugestoes_estruturais(
            distribuicao, media_global, recente_10, tendencia, ult_qtd
        )

        return {
            "total_concursos": len(sorteios),
            "total_pares_analisados": total_pares,
            "ultimo_concurso": ult.concurso,
            "distribuicao": distribuicao,
            "media_historica": media_global,
            "sequencias": {
                "maior_sem_repeticao": {
                    "concursos": max_streak_sem,
                    "de": inicio_max_sem,
                    "ate": fim_max_sem,
                },
                "maior_com_repeticao": {
                    "concursos": max_streak_com,
                    "de": inicio_max_com,
                    "ate": fim_max_com,
                },
            },
            "media_por_ano": media_por_ano,
            "media_por_decada": media_por_decada,
            "tendencia_recente_100": {
                "media": media_100,
                "tendencia": tendencia,
                "media_historica": media_global,
            },
            "ultimos_10": recente_10,
            "ultimos_30": recente_30,
            "ultimo_concurso_analise": ultimo_analise,
            "sugestoes_estruturais": sugestoes,
        }

    @staticmethod
    def _sugestoes_estruturais(
        distribuicao: List[Dict],
        media: float,
        recente_10: Dict,
        tendencia: str,
        ult_qtd: int,
    ) -> Dict[str, Any]:
        itens = []
        q1 = next((d for d in distribuicao if d["repeticoes"] == "1 dezena repetida"), {})
        q2 = next((d for d in distribuicao if d["repeticoes"] == "2 dezenas repetidas"), {})
        pct_1_2 = (q1.get("porcentagem", 0) or 0) + (q2.get("porcentagem", 0) or 0)
        itens.append(
            f"Historicamente a Mega-Sena tende a repetir entre 1 e 2 dezenas do concurso anterior "
            f"({pct_1_2:.1f}% dos pares consecutivos)."
        )

        q4plus = sum(
            d["porcentagem"] for d in distribuicao
            if d["repeticoes"] not in (
                "0 dezenas repetidas",
                "1 dezena repetida",
                "2 dezenas repetidas",
                "3 dezenas repetidas",
            )
        )
        itens.append(
            f"Repetições de 4 ou mais dezenas são extremamente raras ({q4plus:.1f}% do histórico)."
        )

        if tendencia == "acima da média":
            itens.append(
                f"Os últimos 100 concursos estão acima da média histórica "
                f"({media:.2f} dezenas em média por transição)."
            )
        elif tendencia == "abaixo da média":
            itens.append(
                f"Os últimos 100 concursos estão abaixo da média histórica "
                f"({media:.2f} dezenas em média por transição)."
            )
        else:
            itens.append(
                f"Tendência recente (últimos 100) alinhada à média histórica ({media:.2f} dezenas)."
            )

        if recente_10.get("acima_media_historica"):
            itens.append("Os últimos 10 concursos apresentam repetição acima da média histórica.")
        elif recente_10:
            itens.append("Os últimos 10 concursos estão na média ou abaixo em repetição consecutiva.")

        estrutura = "repetir entre 1 e 2 dezenas do último resultado"
        if ult_qtd >= 3:
            estrutura = (
                "considerar faixa de 0 a 2 repetições "
                "(último concurso teve repetição acima da média)"
            )
        elif ult_qtd == 0:
            estrutura = (
                "considerar faixa de 1 a 2 repetições "
                "(último concurso não repetiu nenhuma dezena)"
            )

        return {
            "itens": itens,
            "estrutura_sugerida": estrutura,
            "ultimo_padrao": ult_qtd,
        }
