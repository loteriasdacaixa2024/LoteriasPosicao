"""
Análise geométrica estrutural do volante Mega-Sena (6×10).
Foco em colunas (finais), linhas (faixas 01-10 … 51-60) e assinaturas C-L-I.
"""
from collections import Counter
from typing import List, Dict, Any, Tuple, Optional

from models.sorteio_megasena import SorteioMegaSena
from models.shared import db

COLUNA_LABELS = {
    1: "Coluna 1 (01, 11, 21, 31, 41, 51)",
    2: "Coluna 2 (02, 12, 22, 32, 42, 52)",
    3: "Coluna 3 (03, 13, 23, 33, 43, 53)",
    4: "Coluna 4 (04, 14, 24, 34, 44, 54)",
    5: "Coluna 5 (05, 15, 25, 35, 45, 55)",
    6: "Coluna 6 (06, 16, 26, 36, 46, 56)",
    7: "Coluna 7 (07, 17, 27, 37, 47, 57)",
    8: "Coluna 8 (08, 18, 28, 38, 48, 58)",
    9: "Coluna 9 (09, 19, 29, 39, 49, 59)",
    10: "Coluna 0 (10, 20, 30, 40, 50, 60)",
}

LINHA_LABELS = {
    1: "01–10",
    2: "11–20",
    3: "21–30",
    4: "31–40",
    5: "41–50",
    6: "51–60",
}


def final_coluna(d: int) -> int:
    return 10 if d % 10 == 0 else d % 10


def linha_dezena(d: int) -> int:
    return (d - 1) // 10 + 1


def analisar_sorteio(dezenas: List[int]) -> Dict[str, Any]:
    """Extrai geometria de um concurso (6 dezenas)."""
    col_counts = Counter(final_coluna(d) for d in dezenas)
    lin_counts = Counter(linha_dezena(d) for d in dezenas)

    cols_dup = sum(1 for c in range(1, 11) if col_counts.get(c, 0) >= 2)
    lins_dup = sum(1 for l in range(1, 7) if lin_counts.get(l, 0) >= 2)
    cols_tripla = sum(1 for c in range(1, 11) if col_counts.get(c, 0) >= 3)
    cols_quad = sum(1 for c in range(1, 11) if col_counts.get(c, 0) >= 4)
    isoladas = sum(col_counts.get(c, 0) for c in range(1, 11) if col_counts.get(c, 0) == 1)

    max_col = max((col_counts.get(c, 0) for c in range(1, 11)), default=0)
    max_lin = max((lin_counts.get(l, 0) for l in range(1, 7)), default=0)

    assinatura = f"C{cols_dup}-L{lins_dup}-I{isoladas}"
    nome_estrutura = _nomear_estrutura(cols_dup, lins_dup, isoladas, max_col, max_lin)

    return {
        "dezenas": sorted(dezenas),
        "dezenas_fmt": [f"{d:02d}" for d in sorted(dezenas)],
        "col_counts": {str(c): col_counts.get(c, 0) for c in range(1, 11)},
        "lin_counts": {str(l): lin_counts.get(l, 0) for l in range(1, 7)},
        "cols_duplicadas": cols_dup,
        "lins_duplicadas": lins_dup,
        "cols_tripla": cols_tripla,
        "cols_quadrupla": cols_quad,
        "isoladas": isoladas,
        "max_coluna": max_col,
        "max_linha": max_lin,
        "assinatura": assinatura,
        "nome_estrutura": nome_estrutura,
        "colunas_ativas": [c for c in range(1, 11) if col_counts.get(c, 0) > 0],
        "linhas_ativas": [l for l in range(1, 7) if lin_counts.get(l, 0) > 0],
    }


def _nomear_estrutura(c: int, l: int, i: int, max_c: int, max_l: int) -> str:
    if c >= 2 and l >= 2:
        return "Cruzado Duplo"
    if c >= 2 and l == 1:
        return "Colunar Duplo"
    if c == 1 and l >= 2:
        return "Linear Duplo"
    if max_c >= 3:
        return "Coluna Tripla+"
    if i >= 4:
        return "Espalhado (muitas isoladas)"
    if i == 6:
        return "Totalmente Isolado"
    return "Misto Equilibrado"


def _pct(qtd: int, total: int) -> float:
    return round(qtd / total * 100, 1) if total else 0.0


def _item_estat(qtd: int, total: int) -> Dict[str, Any]:
    return {"quantidade": qtd, "porcentagem": _pct(qtd, total)}


class GeometriaVolanteService:

    @classmethod
    def analise_completa(cls) -> Optional[Dict[str, Any]]:
        sorteios = (
            db.session.query(SorteioMegaSena)
            .order_by(SorteioMegaSena.concurso.asc())
            .all()
        )
        if not sorteios:
            return None

        total = len(sorteios)
        freq_colunas = Counter()
        freq_linhas = Counter()
        freq_celulas = Counter()

        # Distribuições estruturais
        com_col_2plus = com_col_3 = com_col_4 = 0
        com_lin_2plus = com_lin_3 = com_lin_4 = 0
        com_2_linhas_dup = com_3_linhas_dup = 0

        assinaturas = Counter()
        estruturas_nome = Counter()
        estruturas_compostas = Counter()

        exemplos: Dict[str, Dict] = {}
        historico_assinaturas: List[Dict] = []

        for s in sorteios:
            dz = s.dezenas_lista()
            geo = analisar_sorteio(dz)
            geo["concurso"] = s.concurso
            geo["data"] = s.data

            for d in dz:
                freq_colunas[final_coluna(d)] += 1
                freq_linhas[linha_dezena(d)] += 1
                freq_celulas[(linha_dezena(d), final_coluna(d))] += 1

            if geo["max_coluna"] >= 2:
                com_col_2plus += 1
            if geo["max_coluna"] >= 3:
                com_col_3 += 1
            if geo["max_coluna"] >= 4:
                com_col_4 += 1
            if geo["max_linha"] >= 2:
                com_lin_2plus += 1
            if geo["max_linha"] >= 3:
                com_lin_3 += 1
            if geo["max_linha"] >= 4:
                com_lin_4 += 1
            if geo["lins_duplicadas"] >= 2:
                com_2_linhas_dup += 1
            if geo["lins_duplicadas"] >= 3:
                com_3_linhas_dup += 1

            assinaturas[geo["assinatura"]] += 1
            estruturas_nome[geo["nome_estrutura"]] += 1

            chave_composta = _chave_estrutura_completa(geo)
            estruturas_compostas[chave_composta] += 1

            if chave_composta not in exemplos:
                exemplos[chave_composta] = {
                    "concurso": s.concurso,
                    "data": s.data,
                    "dezenas": geo["dezenas_fmt"],
                    "geo": geo,
                }
            if geo["nome_estrutura"] not in exemplos:
                exemplos[f"nome:{geo['nome_estrutura']}"] = {
                    "concurso": s.concurso,
                    "data": s.data,
                    "dezenas": geo["dezenas_fmt"],
                    "geo": geo,
                }

            historico_assinaturas.append({
                "concurso": s.concurso,
                "assinatura": geo["assinatura"],
                "nome": geo["nome_estrutura"],
            })

        ultimo = analisar_sorteio(sorteios[-1].dezenas_lista())
        ultimo["concurso"] = sorteios[-1].concurso
        ultimo["data"] = sorteios[-1].data
        freq_ultimo_nome = estruturas_nome[ultimo["nome_estrutura"]]

        dist_colunas = [
            {
                "coluna": c,
                "label": COLUNA_LABELS[c],
                "label_curto": f"Col. {0 if c == 10 else c}",
                "frequencia": freq_colunas[c],
                "porcentagem": _pct(freq_colunas[c], total * 6),
            }
            for c in sorted(freq_colunas.keys())
        ]
        dist_colunas.sort(key=lambda x: -x["frequencia"])

        dist_linhas = [
            {
                "linha": l,
                "label": LINHA_LABELS[l],
                "frequencia": freq_linhas[l],
                "porcentagem": _pct(freq_linhas[l], total * 6),
            }
            for l in range(1, 7)
        ]
        dist_linhas.sort(key=lambda x: -x["frequencia"])

        estatisticas_coluna = [
            {
                "estrutura": "Concursos com pelo menos 2 dezenas na mesma coluna",
                **_item_estat(com_col_2plus, total),
                "exemplo": exemplos.get("col2+") or _buscar_exemplo(sorteios, lambda g: g["max_coluna"] >= 2),
            },
            {
                "estrutura": "Concursos com 3 dezenas na mesma coluna",
                **_item_estat(com_col_3, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["max_coluna"] >= 3),
            },
            {
                "estrutura": "Concursos com 4 dezenas na mesma coluna",
                **_item_estat(com_col_4, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["max_coluna"] >= 4),
            },
            {
                "estrutura": "Concursos com pelo menos 2 dezenas na mesma linha",
                **_item_estat(com_lin_2plus, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["max_linha"] >= 2),
            },
            {
                "estrutura": "Concursos com 3 dezenas na mesma linha",
                **_item_estat(com_lin_3, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["max_linha"] >= 3),
            },
            {
                "estrutura": "Concursos com 4 dezenas na mesma linha",
                **_item_estat(com_lin_4, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["max_linha"] >= 4),
            },
            {
                "estrutura": "Concursos com 2+ linhas com ≥2 dezenas cada (padrão multi-linha)",
                **_item_estat(com_2_linhas_dup, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["lins_duplicadas"] >= 2),
            },
            {
                "estrutura": "Concursos com 3+ linhas com ≥2 dezenas cada (padrão multi-linha)",
                **_item_estat(com_3_linhas_dup, total),
                "exemplo": _buscar_exemplo(sorteios, lambda g: g["lins_duplicadas"] >= 3),
            },
        ]

        estruturas_completas = []
        for nome, freq in estruturas_compostas.most_common(15):
            ex = exemplos.get(nome, {})
            estruturas_completas.append({
                "estrutura": nome,
                "frequencia": freq,
                "porcentagem": _pct(freq, total),
                "exemplo": {
                    "concurso": ex.get("concurso"),
                    "data": ex.get("data"),
                    "dezenas": ex.get("dezenas", []),
                    "geo": ex.get("geo"),
                },
            })

        # Heatmap 6x10 (freq % por célula)
        heatmap = []
        for lin in range(1, 7):
            row = []
            for col in range(1, 11):
                f = freq_celulas.get((lin, col), 0)
                row.append({
                    "linha": lin,
                    "coluna": col,
                    "frequencia": f,
                    "porcentagem": _pct(f, total),
                })
            heatmap.append(row)

        return {
            "total_concursos": total,
            "ultimo_concurso": sorteios[-1].concurso,
            "estatisticas_coluna_repeticao": estatisticas_coluna,
            "distribuicao_colunas": dist_colunas,
            "distribuicao_linhas": dist_linhas,
            "estruturas_completas": estruturas_completas,
            "assinaturas_top": [
                {
                    "assinatura": a,
                    "frequencia": f,
                    "porcentagem": _pct(f, total),
                    "exemplo": _exemplo_assinatura(sorteios, a),
                }
                for a, f in assinaturas.most_common(12)
            ],
            "ultimo_concurso_analise": {
                **ultimo,
                "freq_historica_nome": freq_ultimo_nome,
                "pct_historica_nome": _pct(freq_ultimo_nome, total),
            },
            "heatmap": heatmap,
            "geometria_avancada": cls._geometria_avancada(
                sorteios, assinaturas, estruturas_nome, freq_celulas, total
            ),
            "sugestoes_estruturais": cls._sugestoes(
                total, com_col_2plus, com_col_3, dist_colunas,
                estruturas_nome, estruturas_compostas, ultimo,
            ),
        }

    @staticmethod
    def _geometria_avancada(sorteios, assinaturas, estruturas_nome, freq_celulas, total):
        """Dados para aba Geometria do Volante."""
        ano_atual = sorteios[-1].data[-4:] if sorteios[-1].data else ""
        por_ano = Counter()
        for s in sorteios[-100:]:
            if len(s.data) >= 4:
                por_ano[s.data[-4:]] += estruturas_nome[analisar_sorteio(s.dezenas_lista())["nome_estrutura"]]

        regioes = []
        for (lin, col), f in freq_celulas.most_common(20):
            regioes.append({
                "linha": lin,
                "coluna": col,
                "label": f"{LINHA_LABELS[lin]} × Col.{0 if col == 10 else col}",
                "frequencia": f,
                "porcentagem": _pct(f, total),
            })

        raras = [
            {"assinatura": a, "frequencia": f, "porcentagem": _pct(f, total)}
            for a, f in sorted(assinaturas.items(), key=lambda x: x[1])[:8]
        ]

        return {
            "regioes_frequentes": regioes[:10],
            "regioes_raras": sorted(regioes, key=lambda x: x["frequencia"])[:10],
            "estruturas_raras": raras,
            "estruturas_dominantes": [
                {"nome": n, "frequencia": f, "porcentagem": _pct(f, total)}
                for n, f in estruturas_nome.most_common(6)
            ],
            "tendencia_recente_100": por_ano.most_common(3) if por_ano else [],
        }

    @staticmethod
    def _sugestoes(total, com_col_2, com_col_3, dist_colunas, estruturas_nome, compostas, ultimo):
        pct_col2 = _pct(com_col_2, total)
        top_cols = dist_colunas[:3]
        top_est = estruturas_nome.most_common(1)[0] if estruturas_nome else ("", 0)
        top_comp = compostas.most_common(1)[0] if compostas else ("", 0)

        itens = [
            f"Alta incidência histórica ({pct_col2}%) de pelo menos 2 dezenas na mesma coluna.",
            f"Colunas mais recorrentes: {', '.join(c['label_curto'] for c in top_cols)}.",
            f"Estrutura predominante no histórico: {top_est[0]} ({_pct(top_est[1], total)}%).",
            f"Padrão composto mais comum: {top_comp[0]} ({_pct(top_comp[1], total)}%).",
        ]
        if ultimo["cols_duplicadas"] < 2:
            itens.append("Últimos concursos abaixo da média em colunas duplicadas — possível reversão.")
        sugerida = top_comp[0] if top_comp else "2 colunas duplicadas + 1 linha dupla"
        return {
            "itens": itens,
            "estrutura_sugerida": sugerida,
            "assinatura_sugerida": assinaturas_sugerida(ultimo, top_comp),
        }


def _chave_estrutura_completa(geo: Dict) -> str:
    c, l, i = geo["cols_duplicadas"], geo["lins_duplicadas"], geo["isoladas"]
    partes = []
    if c >= 2:
        partes.append(f"{c} colunas duplicadas")
    if l >= 2:
        partes.append(f"{l} linhas duplicadas")
    if geo["cols_tripla"] >= 1:
        partes.append(f"{geo['cols_tripla']} coluna tripla")
    if i >= 3:
        partes.append(f"{i} dezenas isoladas")
    elif i > 0 and c < 2:
        partes.append(f"{i} dezenas isoladas")
    if not partes:
        return "Distribuição uniforme"
    return " + ".join(partes)


def assinaturas_sugerida(ultimo: Dict, top_comp: Tuple) -> str:
    c = max(ultimo.get("cols_duplicadas", 0), 2)
    l = max(ultimo.get("lins_duplicadas", 0), 1)
    i = max(0, 6 - c * 2 - l)
    return f"C{c}-L{l}-I{i}"


def _buscar_exemplo(sorteios, pred) -> Optional[Dict]:
    for s in reversed(sorteios):
        g = analisar_sorteio(s.dezenas_lista())
        if pred(g):
            return {
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": g["dezenas_fmt"],
                "geo": g,
            }
    return None


def _exemplo_assinatura(sorteios, assinatura: str) -> Optional[Dict]:
    for s in reversed(sorteios):
        g = analisar_sorteio(s.dezenas_lista())
        if g["assinatura"] == assinatura:
            return {"concurso": s.concurso, "data": s.data, "dezenas": g["dezenas_fmt"], "geo": g}
    return None
