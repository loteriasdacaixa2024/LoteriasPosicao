# -*- coding: utf-8 -*-
"""
Três fontes já calculadas no sistema, juntas numa aposta:

1. Volante do ciclo — dezenas que ainda não saíram.
2. Estatísticas básicas (2a) — forma da janela inteira.
3. Sequência sorteada — padrão, nº da sequência e status da soma.

Diagonais seguem a mesma leitura de volante do gerador.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from geradores_elite.estatisticas_ciclo.service import (
    tem_gerador_estatisticas_ciclo,
)


FONTES = {
    "ciclo": "/analise/ciclo-cobertura/",
    "estatisticas": "/analise/escolha-visual/",
    "sequencia": "/analise/analises-inteligentes/",
}


def resumir_sequencias(
    linhas: Sequence[Dict[str, Any]],
    *,
    recentes: int = 8,
    top: int = 6,
) -> Dict[str, Any]:
    por: Dict[str, Dict[str, Any]] = {}
    status: Counter = Counter()
    for row in linhas or []:
        pad = str(row.get("padrao") or "").strip()
        if not pad:
            continue
        bloco = por.setdefault(pad, {
            "padrao": pad,
            "frequencia": 0,
            "jogos": int(row.get("jogos_possiveis") or 0),
            "descricao": row.get("descricao") or "",
            "media": row.get("media"),
            "n_padrao": row.get("n_padrao"),
            "dentro": 0,
            "proxima": 0,
            "fora": 0,
        })
        bloco["frequencia"] += 1
        st = str(row.get("status_media") or "fora")
        if st not in ("dentro", "proxima", "fora"):
            st = "fora"
        bloco[st] += 1
        status[st] += 1
        if row.get("media") is not None:
            bloco["media"] = row.get("media")
        if row.get("jogos_possiveis"):
            bloco["jogos"] = int(row.get("jogos_possiveis") or 0)
        if row.get("descricao"):
            bloco["descricao"] = row.get("descricao")
        if row.get("n_padrao"):
            bloco["n_padrao"] = row.get("n_padrao")

    total = int(sum(status.values()))
    base = total or 1
    top_list = sorted(por.values(), key=lambda item: (-int(item["frequencia"]), str(item["padrao"])))[: int(top)]
    for item in top_list:
        item["pct"] = round(100.0 * int(item["frequencia"]) / base, 1)

    recentes_rows: List[Dict[str, Any]] = []
    for row in list(linhas or [])[-int(recentes):][::-1]:
        recentes_rows.append({
            "concurso": row.get("concurso"),
            "data": row.get("data") or "",
            "n_padrao": row.get("n_padrao"),
            "padrao": row.get("padrao") or "",
            "jogos": row.get("jogos_possiveis"),
            "sequencia_n": row.get("sequencia_n"),
            "dezenas_fmt": row.get("dezenas_fmt") or "",
            "soma": row.get("soma"),
            "status_media": row.get("status_media") or "",
            "status_media_label": row.get("status_media_label") or "",
        })

    return {
        "total": total,
        "status": {
            "dentro": int(status["dentro"]),
            "proxima": int(status["proxima"]),
            "fora": int(status["fora"]),
            "pct_dentro": round(100.0 * status["dentro"] / base, 1),
            "pct_proxima": round(100.0 * status["proxima"] / base, 1),
            "pct_fora": round(100.0 * status["fora"] / base, 1),
        },
        "top_padroes": top_list,
        "recentes": recentes_rows,
        "fonte": FONTES["sequencia"],
    }


def _volante(dmin: int, dmax: int, pendentes: Sequence[int], saidas: Sequence[int]) -> List[Dict[str, Any]]:
    pend = {int(n) for n in pendentes}
    sai = {int(n) for n in saidas}
    out = []
    for n in range(int(dmin), int(dmax) + 1):
        if n in pend:
            estado = "pendente"
        elif n in sai:
            estado = "saiu"
        else:
            estado = "fora"
        out.append({"n": n, "estado": estado})
    return out


def _texto_ideia(
    *,
    ciclo: Dict[str, Any],
    ciclo_info: Dict[str, Any],
    medias: Dict[str, Any],
    alvo: Dict[str, Any],
    seq: Dict[str, Any],
    diagonais: Dict[str, Any],
    k: int,
) -> str:
    pend = int((ciclo_info or {}).get("pendentes") if ciclo_info else len(ciclo.get("dezenas_pendentes") or []))
    modo = str((ciclo_info or {}).get("modo") or "")
    if modo == "fim":
        ciclo_txt = (
            f"O ciclo está no fim ({pend} dezenas amarelas). "
            "Elas entram na aposta quando cabem no padrão sorteado."
        )
    elif modo == "fechado":
        ciclo_txt = (
            "O ciclo fechou: não há dezena amarela. "
            "O próximo sorteio reabre o volante. Até lá a forma vem das outras duas fontes."
        )
    else:
        ciclo_txt = (
            f"O ciclo ainda tem muitas dezenas amarelas ({pend}). "
            "Nesta fase elas ficam na prévia e não travam o jogo inteiro."
        )
    st = (seq or {}).get("status") or {}
    pares = medias.get("pares")
    impares = medias.get("impares")
    repetidos = medias.get("repetidos")
    sequencias = medias.get("sequencias")
    finais = medias.get("finais")
    diag_pct = (diagonais or {}).get("janela_pct")
    diag_txt = (
        f"Na janela, {diag_pct}% dos sorteios formaram diagonal no volante."
        if diag_pct is not None
        else "A diagonal de cada aposta aparece no chip abaixo dos números."
    )
    return (
        f"Cada aposta junta três leituras que o sistema já calcula, com {k} dezenas do volante oficial. "
        f"{ciclo_txt} "
        f"A forma segue a janela inteira das Estatísticas Básicas: "
        f"média de {pares} pares, {impares} ímpares, {repetidos} repetidas, "
        f"{sequencias} sequências e {finais} finais iguais "
        f"(alvo de geração: {alvo.get('pares')} pares e 1 ou 2 repetidas do último concurso). "
        f"O padrão e a soma vêm da tabela Sequência sorteada: "
        f"{st.get('pct_dentro', 0)}% dentro da média, {st.get('pct_proxima', 0)}% próxima "
        f"e {st.get('pct_fora', 0)}% fora da faixa. "
        "Padrões que mais saíram e somas dentro ou próximas da média pesam mais. "
        "A aposta nova repete o padrão e a faixa de soma de um concurso real, com dezenas diferentes. "
        f"{diag_txt}"
    )


def _publico(ctx: Dict[str, Any], sequencia: Dict[str, Any], ideia: str, alvo: Dict[str, Any]) -> Dict[str, Any]:
    ciclo = ctx.get("ciclo") or {}
    est = ctx.get("estatisticas") or {}
    dmin = int(ctx.get("dezena_min") or 1)
    dmax = int(ctx.get("dezena_max") or 31)
    return {
        "sucesso": True,
        "modality_key": ctx.get("modality_key"),
        "dezena_min": dmin,
        "dezena_max": dmax,
        "sorteadas": int(ctx.get("sorteadas") or 7),
        "extra_mes": bool(ctx.get("extra_mes")),
        "ideia": ideia,
        "fontes": FONTES,
        "ciclo": {
            "numero_ciclo": ciclo.get("numero_ciclo"),
            "concurso_inicio": ciclo.get("concurso_inicio"),
            "concurso_atual": ciclo.get("concurso_atual"),
            "quantidade_concursos": ciclo.get("quantidade_concursos"),
            "dezenas_saidas": ciclo.get("dezenas_saidas") or [],
            "dezenas_pendentes": ciclo.get("dezenas_pendentes") or [],
            "total_dezenas_pendentes": ciclo.get("total_dezenas_pendentes"),
            "percentual_completo": ciclo.get("percentual_completo"),
            "universo": ciclo.get("universo"),
            "em_andamento": ciclo.get("em_andamento"),
        },
        "ciclo_panorama": ctx.get("ciclo_panorama") or {},
        "volante": _volante(
            dmin,
            dmax,
            ciclo.get("dezenas_pendentes") or [],
            ciclo.get("dezenas_saidas") or [],
        ),
        "estatisticas": {
            "total_sorteios": est.get("total_sorteios"),
            "medias": est.get("medias") or {},
            "pct_com": est.get("pct_com") or {},
            "ultimo_concurso": (est.get("ultimo") or {}).get("concurso"),
            "ultimo_data": (est.get("ultimo") or {}).get("data"),
        },
        "alvo_forma": {
            "pares": alvo.get("pares"),
            "rep_min": alvo.get("rep_min"),
            "rep_max": alvo.get("rep_max"),
        },
        "sequencias": sequencia,
        "diagonais": ctx.get("diagonais") or {},
    }


def contexto_tres_fontes(modality_key: str) -> Dict[str, Any]:
    if not tem_gerador_estatisticas_ciclo(modality_key):
        return {"sucesso": False, "erro": "Estas três fontes não estão disponíveis nesta modalidade."}

    from geradores_elite.estatisticas_ciclo.gerador import _perfil_alvo
    from geradores_elite.estatisticas_ciclo.service import contexto_estatisticas_ciclo

    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return ctx

    try:
        from analise_inteligentes_diadesorte.service import make_inteligentes_service
        payload = make_inteligentes_service(modality_key).sequencias_sorteadas(base="geral")
    except Exception as exc:
        return {"sucesso": False, "erro": f"Falha ao ler a sequência sorteada: {exc}"}

    linhas = list(payload.get("linhas") or [])
    if not linhas:
        return {"sucesso": False, "erro": "A tabela de sequência sorteada está vazia."}

    sequencia = resumir_sequencias(linhas)
    sequencia["primeiro_concurso"] = payload.get("primeiro_concurso")
    sequencia["ultimo_concurso"] = payload.get("ultimo_concurso")
    est = ctx.get("estatisticas") or {}
    alvo = _perfil_alvo(est.get("medias") or {}, est.get("ultimo"))
    ideia = _texto_ideia(
        ciclo=ctx.get("ciclo") or {},
        ciclo_info=ctx.get("ciclo_panorama") or {},
        medias=est.get("medias") or {},
        alvo=alvo,
        seq=sequencia,
        diagonais=ctx.get("diagonais") or {},
        k=int(ctx.get("sorteadas") or 7),
    )
    return _publico(ctx, sequencia, ideia, alvo)


def _formatar_apostas(out: Dict[str, Any]) -> None:
    for i, ap in enumerate(out.get("apostas") or [], start=1):
        ap["numero"] = i
        if ap.get("mes_num") is not None:
            ap["mes"] = ap.get("mes_num")
        ap["modo_motor_aposta"] = "tres_fontes"
        seed = ap.get("semente") or {}
        pad = ap.get("padrao_inicial") or seed.get("padrao") or "—"
        status = ap.get("status_media_label") or "—"
        seq_n = seed.get("sequencia_n")
        conc = seed.get("concurso")
        ap["perfil_referencia"] = {
            "texto_curto": (
                f"Padrão {pad}"
                + (f" · sequência Nº {seq_n}" if seq_n else "")
                + (f" · concurso {conc}" if conc else "")
                + f" · {status}"
            ),
        }


def gerar_apostas_tres_fontes(
    modality_key: str,
    *,
    quantidade: int = 10,
    mes_valor: Optional[Any] = None,
    dezenas_pedidas: Optional[int] = None,
    descartar_ja_sorteadas: bool = True,
) -> Dict[str, Any]:
    if not tem_gerador_estatisticas_ciclo(modality_key):
        return {"sucesso": False, "erro": "Estas três fontes não estão disponíveis nesta modalidade."}

    from geradores_elite.estatisticas_ciclo.gerador_panorama import gerar_apostas_panorama
    from geradores_elite.estatisticas_ciclo.service import (
        _anexar_meses,
        contexto_estatisticas_ciclo,
    )

    ctx = contexto_estatisticas_ciclo(modality_key)
    if not ctx.get("sucesso"):
        return ctx

    historico = set()
    try:
        from geradores_elite.validacao.pipeline import carregar_mapa_historico_detalhado
        historico = set(carregar_mapa_historico_detalhado(modality_key).keys())
    except Exception:
        historico = set()

    est = ctx.get("estatisticas") or {}
    k_oficial = int(ctx.get("sorteadas") or 7)
    dmin = int(ctx.get("dezena_min") or 1)
    dmax = int(ctx.get("dezena_max") or 31)
    teto = max(k_oficial, dmax - dmin + 1)
    try:
        k_saida = int(dezenas_pedidas) if dezenas_pedidas else k_oficial
    except (TypeError, ValueError):
        k_saida = k_oficial
    if k_saida < k_oficial:
        k_saida = k_oficial
    if k_saida > teto:
        k_saida = teto
    out = gerar_apostas_panorama(
        pendentes=(ctx.get("ciclo") or {}).get("dezenas_pendentes") or [],
        linhas_basicas=ctx.get("linhas_basicas") or [],
        medias=est.get("medias") or {},
        quantidade=quantidade,
        dezena_min=dmin,
        dezena_max=dmax,
        k=k_oficial,
        k_saida=k_saida,
        descartar_ja_sorteadas=bool(descartar_ja_sorteadas),
        historico=historico,
        modality_key=modality_key,
        ponderar=True,
    )
    if not out.get("sucesso"):
        return out

    out = _anexar_meses(out, ctx, mes_valor)
    _formatar_apostas(out)
    ciclo_info = ctx.get("ciclo_panorama") or {}
    modo = str(ciclo_info.get("modo") or "")
    if modo == "fim":
        ciclo_txt = "ciclo no fim: pendentes entram quando cabem no padrão"
    elif modo == "fechado":
        ciclo_txt = "ciclo fechado: sem pendentes para encaixar"
    else:
        ciclo_txt = "ciclo no começo: pendentes só na prévia"
    alvo = out.get("alvo") or {}
    out["modo_geracao"] = "tres_fontes"
    out["fontes"] = FONTES
    out["ciclo_panorama"] = ciclo_info
    out["criterios_modo_auto"] = [
        ciclo_txt,
        (
            f"forma da janela: {alvo.get('pares')} pares"
            if descartar_ja_sorteadas
            else f"forma da janela: {alvo.get('pares')} pares · {alvo.get('rep_min')}–{alvo.get('rep_max')} repetidas"
        ),
        "sequência sorteada: padrão frequente e soma dentro ou próxima da média",
        f"cada aposta com {k_saida} dezenas",
        "diagonal do volante em cada aposta",
    ]
    if descartar_ja_sorteadas:
        out["criterios_modo_auto"].append(
            "descarte ligado: sem dezenas do último concurso e sem jogo já sorteado"
        )
    return out
