# -*- coding: utf-8 -*-
"""Insights automáticos — regras determinísticas sobre o enriquecimento."""
from __future__ import annotations

from typing import Any, Dict, List


def gerar_insights(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not payload.get("sucesso"):
        return out

    resumo = payload.get("resumo") or {}
    foco = payload.get("concurso_foco") or {}
    basicos = foco.get("basicos") or {}
    cruz = foco.get("cruzamentos") or []
    pct_com = resumo.get("pct_com") or {}
    medias = resumo.get("medias") or {}
    total = int(resumo.get("total_sorteios") or 0)
    conc = foco.get("concurso")

    # 1) tipicidade pares
    pares_q = int((basicos.get("pares") or {}).get("quantidade") or 0)
    media_p = float(medias.get("pares") or 0)
    if conc and media_p:
        diff = pares_q - media_p
        if abs(diff) >= 1.5:
            sentido = "acima" if diff > 0 else "abaixo"
            out.append({
                "tipo": "destaque",
                "titulo": "Paridade atípica",
                "texto": (
                    f"Concurso {conc}: {pares_q} pares "
                    f"({sentido} da média {media_p:.1f} da janela)."
                ),
            })

    # 2) repetidos
    rep = basicos.get("repetidos") or {}
    if int(rep.get("quantidade") or 0) >= 3:
        dez = ", ".join(f"{d:02d}" for d in rep.get("dezenas") or [])
        out.append({
            "tipo": "alerta",
            "titulo": "Alta repetição",
            "texto": f"Concurso {conc} repetiu {rep['quantidade']} dezenas do anterior: {dez}.",
        })
    elif int(rep.get("quantidade") or 0) == 0 and conc:
        out.append({
            "tipo": "info",
            "titulo": "Sem repetidos",
            "texto": f"Concurso {conc} não repetiu nenhuma dezena do concurso anterior.",
        })

    # 3) sequências na janela
    pct_seq = float(pct_com.get("sequencias") or 0)
    if pct_seq >= 70:
        out.append({
            "tipo": "info",
            "titulo": "Sequências frequentes",
            "texto": f"{pct_seq}% dos {total} concursos da janela tiveram ao menos uma sequência.",
        })

    # 4) maior cruzamento do concurso
    if cruz:
        top = max(cruz, key=lambda c: int(c.get("quantidade") or 0))
        if int(top.get("quantidade") or 0) >= 2:
            dez = ", ".join(f"{d:02d}" for d in top.get("dezenas") or [])
            out.append({
                "tipo": "cruzamento",
                "titulo": top.get("label") or "Cruzamento",
                "texto": (
                    f"Maior interseção no concurso {conc}: "
                    f"{top['quantidade']} dezena(s) — {dez} "
                    f"({top.get('percentual_concurso')}% do volante)."
                ),
            })

    # 5) cruzamento raro/frequente na janela
    cruz_j = resumo.get("cruzamentos_janela") or []
    if cruz_j:
        mais = max(cruz_j, key=lambda c: float(c.get("percentual_janela") or 0))
        menos = min(cruz_j, key=lambda c: float(c.get("percentual_janela") or 0))
        out.append({
            "tipo": "janela",
            "titulo": "Cruzamento mais comum",
            "texto": (
                f"{mais['label']} aparece em {mais['percentual_janela']}% "
                f"dos concursos da janela."
            ),
        })
        if menos["id"] != mais["id"]:
            out.append({
                "tipo": "janela",
                "titulo": "Cruzamento mais raro",
                "texto": (
                    f"{menos['label']} só em {menos['percentual_janela']}% "
                    f"da janela."
                ),
            })

    # 6) finais
    fin = basicos.get("finais") or {}
    if int(fin.get("quantidade") or 0) >= 2:
        out.append({
            "tipo": "info",
            "titulo": "Finais iguais",
            "texto": (
                f"Concurso {conc}: {fin['quantidade']} dezenas compartilham final "
                f"— {', '.join(f'{d:02d}' for d in fin.get('dezenas') or [])}."
            ),
        })

    return out[:8]
