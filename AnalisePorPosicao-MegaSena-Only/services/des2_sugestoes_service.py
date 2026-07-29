"""
Sugestões inteligentes Des2 baseadas no universo completo de 60 dezenas.
Lê o histórico real do banco (freq + atraso por dezena) e sugere COLUNAS
cujas 6 dezenas cobrem 01–60, exibindo as dezenas concretas (ex.: 13, 32, 53).
"""
from typing import List, Dict, Any, Set, Optional
from sqlalchemy import desc

from models.sorteio_megasena import SorteioMegaSena
from services.des2_engine import dezenas_da_coluna


def _carregar_stats_60_dezenas() -> Dict[str, Any]:
    """Uma passagem no banco: estatísticas das 60 dezenas e por coluna."""
    sorteios = SorteioMegaSena.query.order_by(SorteioMegaSena.concurso.asc()).all()
    if not sorteios:
        return {"ok": False}

    total = len(sorteios)
    ultimo = sorteios[-1].concurso
    freq = {d: 0 for d in range(1, 61)}
    visto = {d: 0 for d in range(1, 61)}

    for s in sorteios:
        for d in s.dezenas_lista():
            freq[d] += 1
            visto[d] = s.concurso

    dezenas_rank = []
    for d in range(1, 61):
        atraso = (ultimo - visto[d]) if visto[d] > 0 else total
        linha = (d - 1) // 10 + 1
        col = 10 if d % 10 == 0 else d % 10
        dezenas_rank.append({
            "dezena": d,
            "dezena_fmt": f"{d:02d}",
            "freq": freq[d],
            "atraso": atraso,
            "linha": linha,
            "coluna": col,
        })

    max_freq = max(freq.values()) or 1
    max_atraso = max((x["atraso"] for x in dezenas_rank), default=1) or 1

    colunas_data = []
    for col in range(1, 11):
        dz = dezenas_da_coluna(col)
        stats_col = [x for x in dezenas_rank if x["dezena"] in dz]
        stats_col.sort(key=lambda x: -x["freq"])
        stats_atr = sorted(stats_col, key=lambda x: -x["atraso"])
        freq_total = sum(x["freq"] for x in stats_col)
        colunas_data.append({
            "coluna": col,
            "label": "Col. 0" if col == 10 else f"Col. {col}",
            "dezenas": dz,
            "dezenas_fmt": [f"{d:02d}" for d in dz],
            "freq_total": freq_total,
            "atraso_max": max(x["atraso"] for x in stats_col),
            "top_quentes": stats_col[:3],
            "top_atrasadas": stats_atr[:3],
            "linhas": sorted({x["linha"] for x in stats_col}),
            "score_quente": freq_total / max_freq,
            "score_atrasada": max(x["atraso"] for x in stats_col) / max_atraso,
        })

    top_60_quentes = sorted(dezenas_rank, key=lambda x: -x["freq"])[:12]
    top_60_atrasadas = sorted(dezenas_rank, key=lambda x: -x["atraso"])[:12]

    return {
        "ok": True,
        "total_concursos": total,
        "ultimo_concurso": ultimo,
        "colunas": colunas_data,
        "top_60_quentes": top_60_quentes,
        "top_60_atrasadas": top_60_atrasadas,
        "dezenas_rank": dezenas_rank,
    }


def _pick_colunas(
    colunas_data: List[Dict],
    n: int,
    score_key: str,
    excluir: Optional[Set[int]] = None,
    min_dist: int = 1,
) -> List[int]:
    excluir = excluir or set()
    escolhidas: List[int] = []
    ranked = sorted(colunas_data, key=lambda x: -x[score_key])

    for item in ranked:
        c = item["coluna"]
        if c in excluir or c in escolhidas:
            continue
        if escolhidas and any(abs(c - e) < min_dist for e in escolhidas):
            if len(escolhidas) < max(1, n - 1):
                continue
        escolhidas.append(c)
        if len(escolhidas) == n:
            break

    if len(escolhidas) < n:
        for item in ranked:
            c = item["coluna"]
            if c not in excluir and c not in escolhidas:
                escolhidas.append(c)
            if len(escolhidas) == n:
                break
    return sorted(escolhidas[:n])


def _montar_perfil(
    colunas_ids: List[int],
    colunas_data: List[Dict],
    tipo: str,
    motivo: str,
    universo_top: List[Dict],
) -> Dict[str, Any]:
    info = {c["coluna"]: c for c in colunas_data}
    detalhe = []
    dezenas_destaque = []

    for cid in colunas_ids:
        c = info.get(cid, {})
        detalhe.append({
            "coluna": cid,
            "label": c.get("label", str(cid)),
            "dezenas_coluna": c.get("dezenas_fmt", []),
            "freq_total": c.get("freq_total", 0),
            "atraso_max": c.get("atraso_max", 0),
            "top_quentes": [
                f"{x['dezena_fmt']}({x['freq']}×)" for x in c.get("top_quentes", [])
            ],
            "top_atrasadas": [
                f"{x['dezena_fmt']}({x['atraso']}c)" for x in c.get("top_atrasadas", [])
            ],
        })
        for x in c.get("top_quentes", [])[:2]:
            if x["dezena"] not in dezenas_destaque:
                dezenas_destaque.append(x["dezena"])

    dezenas_destaque_fmt = [f"{d:02d}" for d in sorted(dezenas_destaque)[:12]]
    resumo_cols = " · ".join(
        f"{d['label']}[{', '.join(d['top_quentes'][:2])}]" for d in detalhe
    )

    return {
        "colunas": colunas_ids,
        "tipo": tipo,
        "motivo": motivo,
        "detalhe": detalhe,
        "dezenas_destaque": dezenas_destaque_fmt,
        "universo_60_referencia": [x["dezena_fmt"] for x in universo_top[:8]],
        "resumo": resumo_cols,
        "cobertura": "Cada coluna cobre 6 dezenas em todas as faixas (01–10 até 51–60).",
    }


class Des2SugestoesService:
    """Sugestões derivadas das 60 dezenas reais do banco."""

    @classmethod
    def obter_sugestoes(cls, qtd_dezenas: int) -> Dict[str, Any]:
        necessarias = qtd_dezenas // 2
        base = _carregar_stats_60_dezenas()

        if not base.get("ok"):
            return cls._fallback(necessarias)

        colunas_data = base["colunas"]
        top_q = base["top_60_quentes"]
        top_a = base["top_60_atrasadas"]

        # Quentes: colunas cuja SOMA de freq das 6 dezenas é maior (dados reais)
        quentes_cols = _pick_colunas(colunas_data, necessarias, "score_quente", min_dist=2)
        quentes = _montar_perfil(
            quentes_cols,
            colunas_data,
            "quentes",
            f"Baseado em {base['total_concursos']} concursos: colunas com dezenas mais "
            f"s sorteadas no histórico (ex.: {', '.join(x['dezena_fmt'] for x in top_q[:6])}).",
            top_q,
        )

        excluir_q = set(quentes_cols)
        atrasadas_cols = _pick_colunas(
            colunas_data, necessarias, "score_atrasada", excluir=excluir_q, min_dist=1
        )
        if len(set(atrasadas_cols) & excluir_q) == len(atrasadas_cols):
            atrasadas_cols = _pick_colunas(
                colunas_data, necessarias, "score_atrasada", excluir=set(), min_dist=2
            )
            atrasadas_cols = [c for c in atrasadas_cols if c not in excluir_q][:necessarias]
            while len(atrasadas_cols) < necessarias:
                for item in sorted(colunas_data, key=lambda x: -x["score_atrasada"]):
                    if item["coluna"] not in excluir_q and item["coluna"] not in atrasadas_cols:
                        atrasadas_cols.append(item["coluna"])
                    if len(atrasadas_cols) == necessarias:
                        break

        atrasadas = _montar_perfil(
            sorted(atrasadas_cols[:necessarias]),
            colunas_data,
            "atrasadas",
            f"Colunas com dezenas mais atrasadas no banco (ex.: "
            f"{', '.join(x['dezena_fmt'] for x in top_a[:6])}).",
            top_a,
        )

        balanceadas_cols = cls._balanceadas(
            colunas_data, necessarias, quentes_cols, atrasadas_cols
        )
        balanceadas = _montar_perfil(
            balanceadas_cols,
            colunas_data,
            "balanceadas",
            "Mistura colunas quentes e atrasadas usando o ranking real das 60 dezenas.",
            top_q[:4] + top_a[:4],
        )

        return {
            "necessarias": necessarias,
            "total_concursos": base["total_concursos"],
            "top_60_quentes": [x["dezena_fmt"] for x in top_q[:10]],
            "top_60_atrasadas": [x["dezena_fmt"] for x in top_a[:10]],
            "sugestoes": {
                "quentes": quentes["colunas"],
                "atrasadas": atrasadas["colunas"],
                "balanceadas": balanceadas["colunas"],
            },
            "perfis": {
                "quentes": quentes,
                "atrasadas": atrasadas,
                "balanceadas": balanceadas,
            },
            "estatisticas_colunas": colunas_data,
        }

    @staticmethod
    def _balanceadas(
        colunas_data: List[Dict],
        n: int,
        quentes: List[int],
        atrasadas: List[int],
    ) -> List[int]:
        metade_q = (n + 1) // 2
        escolhidas: List[int] = []
        for c in quentes[:metade_q]:
            if c not in escolhidas:
                escolhidas.append(c)
        for c in atrasadas:
            if c not in escolhidas and len(escolhidas) < n:
                escolhidas.append(c)
        if len(escolhidas) < n:
            misto = sorted(
                colunas_data,
                key=lambda x: -(x["score_quente"] + x["score_atrasada"]),
            )
            for item in misto:
                c = item["coluna"]
                if c not in escolhidas:
                    escolhidas.append(c)
                if len(escolhidas) == n:
                    break
        return sorted(escolhidas[:n])

    @staticmethod
    def _fallback(necessarias: int) -> Dict[str, Any]:
        """Fallback espalhado no volante quando não há banco."""
        quentes = sorted([3, 4, 7, 10][:necessarias])
        atrasadas = sorted([2, 5, 9, 6][:necessarias])
        balanceadas = sorted([3, 6, 8, 4][:necessarias])
        mk = lambda cols, t: {
            "colunas": cols,
            "tipo": t,
            "motivo": "Sem histórico no banco — sincronize os sorteios.",
            "dezenas_destaque": ["13", "32", "38", "43"],
            "universo_60_referencia": ["13", "32", "38", "43", "46", "53"],
            "resumo": "dados de exemplo",
            "detalhe": [],
        }
        return {
            "necessarias": necessarias,
            "total_concursos": 0,
            "top_60_quentes": [],
            "top_60_atrasadas": [],
            "sugestoes": {
                "quentes": quentes,
                "atrasadas": atrasadas,
                "balanceadas": balanceadas,
            },
            "perfis": {
                "quentes": mk(quentes, "quentes"),
                "atrasadas": mk(atrasadas, "atrasadas"),
                "balanceadas": mk(balanceadas, "balanceadas"),
            },
        }
