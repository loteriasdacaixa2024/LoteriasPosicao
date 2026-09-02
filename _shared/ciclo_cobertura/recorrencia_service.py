# -*- coding: utf-8 -*-
"""Recorrência das Repetidas no Ciclo — janela dos últimos N concursos."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .analise_service import AnaliseCicloCoberturaService
from .specs import get_ciclo_spec

JANELAS = (4, 5, 6, 8, 10)
JANELA_DEFAULT = 4
POS_DETALHE_DEFAULT = 4
BACKTEST_JANELAS = (50, 100, 200)
CONJUNTO_CONSTRUTOR_N = 16

GRUPO_ORDEM = (
    "muito_forte",
    "forte",
    "repetido",
    "baixa_presenca",
    "ausentes",
)
GRUPO_LABEL = {
    "muito_forte": "Muito forte",
    "forte": "Forte",
    "repetido": "Repetidas",
    "baixa_presenca": "Baixa presença",
    "ausentes": "Ausentes",
}
NUCLEO_KEYS = ("muito_forte", "forte", "repetido")


def _fmt(nums: Sequence[int]) -> str:
    return " · ".join(f"{int(n):02d}" for n in nums) if nums else "—"


def _rotulo(freq: int, max_f: int) -> str:
    if freq <= 0:
        return "Ausente"
    if freq == 1:
        return "Baixa presença"
    if freq == 2:
        return "Repetida"
    if freq >= 3 and freq == max_f:
        return "Muito forte"
    return "Forte"


def _ints(vals: Iterable[Any]) -> List[int]:
    return sorted({int(x) for x in (vals or []) if x is not None and x != ""})


def _freq_repetidas(linhas: Sequence[dict]) -> Tuple[Counter, int]:
    freq: Counter = Counter()
    ocorrencias = 0
    for row in linhas:
        for d in _ints(row.get("repetidas") or []):
            freq[d] += 1
            ocorrencias += 1
    return freq, ocorrencias


def _montar_classificacao(freq: Counter, univ: Sequence[int]) -> Dict[str, Any]:
    max_f = max(freq.values()) if freq else 0
    tabela = []
    for d in univ:
        f = int(freq.get(d, 0))
        tabela.append({
            "dezena": d,
            "vezes": f,
            "rotulo": _rotulo(f, max_f),
        })

    def grupo(pred) -> List[int]:
        return [t["dezena"] for t in tabela if pred(t["vezes"])]

    ausentes = grupo(lambda f: f == 0)
    baixa = grupo(lambda f: f == 1)
    repetidas = grupo(lambda f: f == 2)
    fortes = grupo(lambda f: f >= 3 and f < max_f) if max_f >= 4 else []
    muito_fortes = grupo(lambda f: f >= 3 and f == max_f) if max_f >= 3 else []
    if max_f == 3:
        muito_fortes = grupo(lambda f: f == 3)
        fortes = []

    nucleo_forte = sorted(set(muito_fortes) | set(fortes))
    ranking = sorted(
        [t for t in tabela if t["vezes"] >= 2],
        key=lambda t: (-t["vezes"], t["dezena"]),
    )
    por_frequencia = []
    for v in range(max_f, -1, -1):
        nums = grupo(lambda f, vv=v: f == vv)
        if not nums:
            continue
        por_frequencia.append({
            "vezes": v,
            "dezenas": nums,
            "fmt": _fmt(nums),
            "rotulo": _rotulo(v, max_f) if v else "Ausente",
            "qtd": len(nums),
        })

    grupos = {
        "nucleo_forte": nucleo_forte,
        "muito_forte": muito_fortes,
        "forte": fortes,
        "repetido": repetidas,
        "baixa_presenca": baixa,
        "ausentes": ausentes,
    }
    return {
        "max_f": max_f,
        "tabela": tabela,
        "grupos": grupos,
        "fmt": {
            "nucleo_forte": _fmt(nucleo_forte),
            "muito_forte": _fmt(muito_fortes),
            "forte": _fmt(fortes),
            "repetido": _fmt(repetidas),
            "baixa_presenca": _fmt(baixa),
            "ausentes": _fmt(ausentes),
        },
        "ranking": ranking,
        "por_frequencia": por_frequencia,
    }


def _mapa_grupo(grupos: Dict[str, List[int]]) -> Dict[int, str]:
    mapa: Dict[int, str] = {}
    for key in GRUPO_ORDEM:
        for d in grupos.get(key) or []:
            mapa[int(d)] = key
    return mapa


def _pools_de_grupos(grupos: Dict[str, List[int]]) -> Dict[str, List[int]]:
    nucleo = sorted(
        set(grupos.get("nucleo_forte") or []) | set(grupos.get("repetido") or [])
    )
    baixa = list(grupos.get("baixa_presenca") or [])
    ausentes = list(grupos.get("ausentes") or [])
    return {
        "ausentes_baixa": sorted(set(ausentes) | set(baixa)),
        "forte_repetidas": nucleo,
        "nucleo_baixa": sorted(set(nucleo) | set(baixa)),
        "ausentes": ausentes,
    }


def _inter(resultado: Sequence[int], pool: Sequence[int]) -> List[int]:
    ps = set(pool)
    return [d for d in resultado if d in ps]


def _avaliar_resultado(
    resultado: Sequence[int],
    grupos: Dict[str, List[int]],
) -> Dict[str, Any]:
    mapa = _mapa_grupo(grupos)
    por_grupo: Dict[str, List[int]] = {k: [] for k in GRUPO_ORDEM}
    desconhecidas: List[int] = []
    for d in resultado:
        key = mapa.get(int(d))
        if key:
            por_grupo[key].append(int(d))
        else:
            desconhecidas.append(int(d))
    qtd = {k: len(por_grupo[k]) for k in GRUPO_ORDEM}
    nucleo_n = sum(qtd[k] for k in NUCLEO_KEYS)
    baixa_n = qtd["baixa_presenca"]
    aus_n = qtd["ausentes"]
    if aus_n == 0 and nucleo_n > 0:
        padrao = "nucleo_baixa"
        padrao_label = "Núcleo recorrente + baixa presença"
    elif aus_n > nucleo_n and aus_n >= baixa_n:
        padrao = "ausentes_dominam"
        padrao_label = "Ausentes dominam o resultado"
    elif aus_n > 0:
        padrao = "misto"
        padrao_label = "Misto (núcleo/baixa com alguma ausente)"
    else:
        padrao = "baixa"
        padrao_label = "Só baixa presença"

    pools = _pools_de_grupos(grupos)
    nucleo_baixa = pools["nucleo_baixa"]
    ausentes = pools["ausentes"]
    hits_nb = _inter(resultado, nucleo_baixa)
    hits_aus = _inter(resultado, ausentes)
    tetos = {
        "ausentes_baixa": len(_inter(resultado, pools["ausentes_baixa"])),
        "forte_repetidas": len(_inter(resultado, pools["forte_repetidas"])),
        "nucleo_baixa": len(hits_nb),
        "nucleo_baixa_1aus": len(hits_nb) + min(1, len(hits_aus)),
    }
    return {
        "por_grupo": por_grupo,
        "qtd": qtd,
        "nucleo_n": nucleo_n,
        "baixa_n": baixa_n,
        "ausentes_n": aus_n,
        "padrao": padrao,
        "padrao_label": padrao_label,
        "tetos": tetos,
        "tamanho_pool": {k: len(v) for k, v in pools.items()},
        "fmt_por_grupo": {k: _fmt(por_grupo[k]) for k in GRUPO_ORDEM},
    }


def _media(vals: Sequence[float], casas: int = 2) -> float:
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), casas)


def _dist_teto(tetos: Sequence[int], pick: int) -> Dict[str, int]:
    dist = {str(i): 0 for i in range(0, pick + 1)}
    for t in tetos:
        k = max(0, min(pick, int(t)))
        dist[str(k)] += 1
    return dist


def _agregar_estrategias(
    avaliacoes: Sequence[dict],
    pick: int,
) -> List[Dict[str, Any]]:
    specs = (
        ("ausentes_baixa", "Ausentes + Baixa"),
        ("forte_repetidas", "Forte + Repetidas"),
        ("nucleo_baixa", "Núcleo + Baixa"),
        ("nucleo_baixa_1aus", "Núcleo + Baixa + 1 Ausente"),
    )
    out = []
    n = len(avaliacoes)
    for sid, nome in specs:
        tetos = [int(a["tetos"].get(sid, 0)) for a in avaliacoes]
        tamanhos = []
        if sid == "nucleo_baixa_1aus":
            for a in avaliacoes:
                tamanhos.append(
                    int(a["tamanho_pool"].get("nucleo_baixa", 0))
                    + min(1, int(a["tamanho_pool"].get("ausentes", 0)))
                )
        else:
            tamanhos = [int(a["tamanho_pool"].get(sid, 0)) for a in avaliacoes]
        dist = _dist_teto(tetos, pick)
        pool_medio = _media(tamanhos, 1)
        media = _media(tetos)
        dens = round(media / pool_medio, 3) if pool_medio else 0.0
        out.append({
            "id": sid,
            "nome": nome,
            "n": n,
            "media": media,
            "melhor": max(tetos) if tetos else 0,
            "pior": min(tetos) if tetos else 0,
            "pool_medio": pool_medio,
            "densidade": dens,
            "esperado_aleatorio": round(pick * dens, 2),
            "dist": dist,
            "pct_ge5": round(100.0 * sum(1 for t in tetos if t >= 5) / n, 1) if n else 0.0,
            "pct_ge6": round(100.0 * sum(1 for t in tetos if t >= 6) / n, 1) if n else 0.0,
            "pct_7": round(100.0 * sum(1 for t in tetos if t >= pick) / n, 1) if n else 0.0,
        })
    return out


def _composicao_media(avaliacoes: Sequence[dict]) -> Dict[str, float]:
    if not avaliacoes:
        return {k: 0.0 for k in (*GRUPO_ORDEM, "nucleo")}
    n = len(avaliacoes)
    out = {}
    for k in GRUPO_ORDEM:
        out[k] = round(sum(int(a["qtd"].get(k, 0)) for a in avaliacoes) / n, 2)
    out["nucleo"] = round(sum(int(a["nucleo_n"]) for a in avaliacoes) / n, 2)
    return out


def _vencer_estrategias(estrategias: Sequence[dict]) -> Optional[str]:
    if not estrategias:
        return None
    # Teto bruto favorece pool grande. Densidade = qualidade da dezena no pool.
    ranked = sorted(
        estrategias,
        key=lambda e: (
            -float(e.get("densidade") or 0),
            -float(e.get("media") or 0),
            float(e.get("pool_medio") or 0),
        ),
    )
    return ranked[0]["id"]


def _montar_conclusao(
    *,
    ciclo_num: Any,
    janela: int,
    detalhe: Sequence[dict],
    bt: Dict[str, Any],
    vencedor: Optional[str],
) -> Dict[str, Any]:
    paragrafos: List[str] = []
    if detalhe:
        zeros = sum(1 for d in detalhe if int(d.get("ausentes_n") or 0) == 0)
        n_det = len(detalhe)
        concs = ", ".join(f"#{d['concurso']}" for d in detalhe)
        paragrafos.append(
            f"Nos {n_det} concurso(s) mais recente(s) ({concs}), "
            f"{zeros} saíram sem nenhuma dezena da lista de ausentes."
        )
        mix = []
        for d in detalhe:
            mix.append(
                f"#{d['concurso']}: {d['nucleo_n']} do núcleo + {d['baixa_n']} de baixa presença + "
                f"{d['ausentes_n']} ausente(s)"
            )
        paragrafos.append("O que saiu, na prática: " + "; ".join(mix) + ".")

    slice50 = bt.get("50") or {}
    comp = slice50.get("composicao_media") or {}
    pct0 = slice50.get("pct_zero_ausentes")
    if slice50.get("n"):
        paragrafos.append(
            f"Olhando os últimos {slice50['n']} concursos um a um "
            f"(sempre classificando só com os {janela} anteriores, "
            f"sem usar o resultado daquele dia): em média saíram "
            f"{comp.get('nucleo', 0)} dezena(s) do núcleo, "
            f"{comp.get('baixa_presenca', 0)} de baixa presença e "
            f"{comp.get('ausentes', 0)} ausente(s)."
            + (
                f" Em {pct0}% dos concursos, nenhuma ausente saiu."
                if pct0 is not None
                else ""
            )
        )

    rec = "nucleo_baixa"
    rec_label = "Núcleo recorrente + Baixa presença"
    if vencedor == "nucleo_baixa_1aus":
        rec = "nucleo_baixa_1aus"
        rec_label = "Núcleo + Baixa + 1 Ausente (recuperação pontual)"
    elif vencedor == "ausentes_baixa":
        rec = "ausentes_baixa"
        rec_label = "Ausentes + Baixa presença"
    elif vencedor == "forte_repetidas":
        rec = "forte_repetidas"
        rec_label = "Forte + Repetidas"

    paragrafos.append(
        "Um conjunto maior (Ausentes + Baixa, uns 26 números) naturalmente 'pesca' mais dezenas "
        "do resultado. Isso não quer dizer que seja o melhor para um jogo de 7. "
        "O critério justo é a densidade: quantos acertos você consegue por dezena colocada no conjunto."
    )
    if rec in ("nucleo_baixa", "nucleo_baixa_1aus"):
        paragrafos.append(
            "Dezena que não saiu na janela não fica 'mais provável' por isso. "
            "O núcleo que a análise marcou como forte ou repetido precisa entrar no jogo."
        )
        paragrafos.append(
            "Na prática: o pool principal é Núcleo + Baixa presença. "
            "As ausentes ficam de reserva — no máximo 1 dezena por aposta, só para recuperar alguma atrasada."
        )
    else:
        paragrafos.append(
            f"Neste recorte, o conjunto «{rec_label}» rendeu mais acertos por dezena usada. "
            "Mesmo assim, evite que as ausentes tomem conta de cada jogo."
        )

    return {
        "titulo": f"Ciclo #{ciclo_num} · interpretação da recorrência",
        "resumo": f"Recomendação: {rec_label}.",
        "como_ler": (
            "Esta caixa traduz os números da recorrência em uma decisão prática: "
            "quais dezenas entram no pool principal do seu jogo, e quais ficam só como reserva."
        ),
        "paragrafos": paragrafos,
        "recomendacao_pool": rec,
        "recomendacao_label": rec_label,
        "problema_atual": (
            "O pool antigo (Ausentes + Baixa presença) deixa de fora o núcleo — "
            "justamente as dezenas que a análise apontou como fortes ou repetidas."
        ),
    }


def _walk_forward(
    detalhes_asc: Sequence[dict],
    univ: Sequence[int],
    janela: int,
    pick: int,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    n = len(detalhes_asc)
    if n <= janela:
        return out
    for i in range(janela, n):
        prev = detalhes_asc[i - janela:i]
        alvo = detalhes_asc[i]
        resultado = _ints(alvo.get("dezenas") or [])
        if len(resultado) < pick:
            continue
        freq, ocorrencias = _freq_repetidas(prev)
        if ocorrencias <= 0:
            continue
        clf = _montar_classificacao(freq, univ)
        av = _avaliar_resultado(resultado, clf["grupos"])
        conc_janela = [r.get("concurso") for r in prev]
        out.append({
            "concurso": alvo.get("concurso"),
            "data": alvo.get("data") or "",
            "numero_ciclo": alvo.get("numero_ciclo"),
            "resultado": resultado,
            "fmt_resultado": _fmt(resultado),
            "janela_concursos": conc_janela,
            "grupos": clf["grupos"],
            "fmt": clf["fmt"],
            **av,
        })
    return out


def _fatia_backtest(avaliacoes: Sequence[dict], limite: int, pick: int) -> Dict[str, Any]:
    fatia = list(avaliacoes[-limite:]) if limite else list(avaliacoes)
    n = len(fatia)
    if not n:
        return {"n": 0, "ok": False}
    comp = _composicao_media(fatia)
    pct_zero = round(100.0 * sum(1 for a in fatia if int(a["ausentes_n"]) == 0) / n, 1)
    pct_nucleo_baixa = round(
        100.0 * sum(1 for a in fatia if a.get("padrao") == "nucleo_baixa") / n,
        1,
    )
    estrategias = _agregar_estrategias(fatia, pick)
    concs = [a.get("concurso") for a in fatia]
    return {
        "ok": True,
        "n": n,
        "concurso_de": concs[0],
        "concurso_ate": concs[-1],
        "composicao_media": comp,
        "pct_zero_ausentes": pct_zero,
        "pct_padrao_nucleo_baixa": pct_nucleo_baixa,
        "estrategias": estrategias,
        "vencedor": _vencer_estrategias(estrategias),
    }


def _overlay_janela_atual(
    janela_rows: Sequence[dict],
    grupos: Dict[str, List[int]],
    pick: int,
) -> List[Dict[str, Any]]:
    """Resultado oficial (7 dezenas) nos grupos da classificação atual da aba."""
    out: List[Dict[str, Any]] = []
    conc_janela = [r.get("concurso") for r in janela_rows]
    for row in janela_rows:
        resultado = _ints(row.get("dezenas") or [])
        if len(resultado) < pick:
            continue
        av = _avaliar_resultado(resultado, grupos)
        out.append({
            "concurso": row.get("concurso"),
            "data": row.get("data") or "",
            "numero_ciclo": row.get("numero_ciclo"),
            "resultado": resultado,
            "fmt_resultado": _fmt(resultado),
            "janela_concursos": conc_janela,
            "classificacao": "atual",
            **av,
        })
    return out


def _montar_conjunto_construtor(
    grupos: Dict[str, List[int]],
    tabela: Sequence[dict],
    pos: Optional[Dict[str, Any]],
    pendentes_ciclo: Optional[Sequence[int]] = None,
    alvo: int = CONJUNTO_CONSTRUTOR_N,
    scores_faltantes: Optional[Sequence[dict]] = None,
) -> Dict[str, Any]:
    """Recorte de até `alvo` dezenas: faltantes do ciclo primeiro, depois núcleo × baixa."""
    freq_map = {int(t["dezena"]): int(t.get("vezes") or 0) for t in tabela}
    nucleo = sorted(
        set(int(x) for x in (grupos.get("nucleo_forte") or []))
        | set(int(x) for x in (grupos.get("repetido") or [])),
        key=lambda d: (-freq_map.get(d, 0), d),
    )
    baixa = [int(x) for x in (grupos.get("baixa_presenca") or [])]
    hits: Counter = Counter()
    recencia: Dict[int, int] = {}
    baixa_set = set(baixa)
    for i, row in enumerate((pos or {}).get("detalhe") or []):
        for n in (row.get("por_grupo") or {}).get("baixa_presenca") or []:
            n = int(n)
            if n in baixa_set:
                hits[n] += 1
                recencia.setdefault(n, i)
    baixa_ord = sorted(
        baixa,
        key=lambda d: (-hits.get(d, 0), recencia.get(d, 99), d),
    )
    pendentes_unicas = list(dict.fromkeys(
        int(x) for x in (pendentes_ciclo or []) if x is not None
    ))
    rank: Dict[int, float] = {}
    for s in scores_faltantes or []:
        if not isinstance(s, dict) or s.get("dezena") is None:
            continue
        rank[int(s["dezena"])] = -float(s.get("score") or 0)
    pendentes = sorted(pendentes_unicas, key=lambda d: (rank.get(d, 0), d))
    escolhidas: List[int] = []
    nucleo_in: List[int] = []
    baixa_in: List[int] = []
    falt_in: List[int] = []
    seen: Set[int] = set()

    def _add(d: int, bucket: List[int]) -> None:
        if d in seen or len(escolhidas) >= alvo:
            return
        seen.add(d)
        escolhidas.append(d)
        bucket.append(d)

    for d in pendentes:
        _add(d, falt_in)
    for d in nucleo:
        _add(d, nucleo_in)
    for d in baixa_ord:
        _add(d, baixa_in)

    ordenadas = sorted(escolhidas)
    partes = []
    if falt_in:
        partes.append(
            f"{len(falt_in)} faltante(s) do ciclo fixada(s) ({_fmt(sorted(falt_in))})"
        )
    partes.append(f"{len(nucleo_in)} do núcleo")
    if baixa_in:
        partes.append(f"{len(baixa_in)} de baixa presença")
    if len(pendentes) > len(falt_in):
        partes.append(
            f"{len(pendentes) - len(falt_in)} pendente(s) ficaram de fora do teto de {alvo}"
        )
    como = "As 16 priorizam o que o ciclo ainda precisa fechar, depois o núcleo e a baixa presença. " + "; ".join(partes) + "."
    return {
        "n": len(ordenadas),
        "alvo": alvo,
        "dezenas": ordenadas,
        "fmt": _fmt(ordenadas),
        "nucleo": sorted(nucleo_in),
        "baixa": sorted(baixa_in),
        "faltantes_ciclo": sorted(falt_in),
        "como_escolheu": como,
        "href": (
            "/geradores-elite/construtor-construcoes/?origem=recorrencia&dezenas="
            + ",".join(str(d) for d in ordenadas)
            + (
                "&faltantes=" + ",".join(str(d) for d in sorted(falt_in))
                if falt_in else ""
            )
        ),
    }


def pos_analise_recorrencia(
    ciclo: dict,
    spec,
    janela: int,
    *,
    grupos_atuais: Optional[Dict[str, List[int]]] = None,
    janela_rows: Optional[Sequence[dict]] = None,
    k_detalhe: int = POS_DETALHE_DEFAULT,
) -> Dict[str, Any]:
    univ = list(range(int(spec.dezena_min), int(spec.dezena_max) + 1))
    pick = int(spec.sorteadas)
    detalhes = list(ciclo.get("detalhes_concursos") or [])
    detalhes.sort(key=lambda d: int(d.get("concurso") or 0))
    wf = _walk_forward(detalhes, univ, janela, pick)
    if not wf:
        return {
            "ok": False,
            "erro": (
                f"Ainda não há concursos suficientes para comparar o passado com esta janela. "
                f"É preciso de mais de {janela} concursos com repetidas."
            ),
        }

    overlay: List[Dict[str, Any]] = []
    if grupos_atuais and janela_rows:
        overlay = _overlay_janela_atual(janela_rows, grupos_atuais, pick)
    k = max(1, min(int(k_detalhe or POS_DETALHE_DEFAULT), 10))
    if overlay:
        detalhe = overlay[:k]
    else:
        detalhe = wf[-min(k, len(wf)):]

    backtest = {}
    for lim in BACKTEST_JANELAS:
        backtest[str(lim)] = _fatia_backtest(wf, lim, pick)

    vencedor = (backtest.get("50") or {}).get("vencedor") or "nucleo_baixa"
    conclusao = _montar_conclusao(
        ciclo_num=ciclo.get("numero_ciclo"),
        janela=janela,
        detalhe=detalhe,
        bt=backtest,
        vencedor=vencedor,
    )
    return {
        "ok": True,
        "sem_vazamento": True,
        "janela": janela,
        "pick": pick,
        "avaliacoes": len(wf),
        "detalhe": detalhe,
        "composicao_media_detalhe": _composicao_media(detalhe),
        "backtest": backtest,
        "conclusao": conclusao,
        "nota": (
            "Cada cartão pega o resultado oficial (as 7 dezenas que saíram) e mostra "
            "em qual grupo da janela cada uma estava. É o confronto direto: "
            "o que o ciclo classificou × o que de fato saiu."
        ),
        "resumo": "O resultado oficial de cada concurso, dezena a dezena, nos grupos da janela.",
        "como_ler": (
            "Aqui a gente não inventa o jogo: pega o que já saiu e pergunta "
            "se aquelas dezenas estavam no núcleo, na baixa presença ou nas ausentes. "
            "Se o núcleo aparece no resultado, ele merece lugar na aposta. "
            "Se as ausentes quase não saem, não devem dominar o volante."
        ),
        "backtest_resumo": "Qual jeito de montar o pool acertou mais, de forma justa, no histórico.",
        "backtest_como_ler": (
            "Para cada concurso antigo, a classificação usa só o que já tinha acontecido — "
            "ninguém olha o gabarito daquele dia na hora de montar o conjunto. "
            "Depois comparamos quatro formas de escolher as dezenas. "
            "A linha destacada é a que rendeu mais acertos por dezena usada, "
            "o critério justo para um jogo de 7 números. "
            "Um pool enorme acerta mais dezenas no papel, mas dilui o jogo: "
            "por isso a densidade pesa mais do que o total bruto."
        ),
    }


def analisar_recorrencia(
    modality_key: str,
    n: int = JANELA_DEFAULT,
) -> Dict[str, Any]:
    spec = get_ciclo_spec(modality_key)
    pedido = int(n or JANELA_DEFAULT)
    if pedido not in JANELAS:
        pedido = JANELA_DEFAULT

    ciclo = AnaliseCicloCoberturaService.obter_ciclo_atual(modality_key)
    if not ciclo:
        return {"ok": False, "erro": "Sem ciclo em andamento no banco."}

    detalhes = list(ciclo.get("detalhes_concursos") or [])
    detalhes.sort(key=lambda d: int(d.get("concurso") or 0), reverse=True)
    janela = detalhes[:pedido]
    if not janela:
        return {"ok": False, "erro": "Sem concursos na coluna Repetidas no Ciclo."}

    univ = list(range(int(spec.dezena_min), int(spec.dezena_max) + 1))
    freq, ocorrencias = _freq_repetidas(janela)
    linhas: List[Dict[str, Any]] = []
    for row in janela:
        reps = _ints(row.get("repetidas") or [])
        linhas.append({
            "concurso": row.get("concurso"),
            "data": row.get("data") or "",
            "numero_ciclo": row.get("numero_ciclo"),
            "repetidas": reps,
            "dezenas": _ints(row.get("dezenas") or []),
        })

    clf = _montar_classificacao(freq, univ)
    grupos = clf["grupos"]
    ausentes = grupos["ausentes"]
    baixa = grupos["baixa_presenca"]
    ranking = clf["ranking"]

    usadas = [t["dezena"] for t in clf["tabela"] if t["vezes"] > 0]
    n_univ = len(univ)
    n_usadas = len(usadas)
    n_aus = len(ausentes)
    cobertura_pct = round(100.0 * n_usadas / n_univ, 1) if n_univ else 0.0
    ausentes_pct = round(100.0 * n_aus / n_univ, 1) if n_univ else 0.0

    top2 = ranking[:2]
    top2_ocor = sum(t["vezes"] for t in top2)
    top2_pct = round(100.0 * top2_ocor / ocorrencias, 1) if ocorrencias else 0.0
    lider = ranking[0] if ranking else None
    lider_pct = round(100.0 * lider["vezes"] / ocorrencias, 1) if lider and ocorrencias else 0.0

    faixas = []
    for nome, lo, hi in spec.faixas:
        nums = list(range(lo, hi + 1))
        pres = [d for d in nums if freq.get(d, 0) > 0]
        aus = [d for d in nums if freq.get(d, 0) == 0]
        faixas.append({
            "nome": nome,
            "label": f"{lo:02d}–{hi:02d}",
            "de": lo,
            "ate": hi,
            "tamanho": len(nums),
            "presentes": pres,
            "ausentes": aus,
            "qtd_presentes": len(pres),
            "qtd_ausentes": len(aus),
        })

    pendentes_ciclo = [int(x) for x in (ciclo.get("dezenas_pendentes") or [])]
    scores_falt = []
    try:
        from .inteligencia_service import CicloInteligenciaService
        scores_falt = CicloInteligenciaService.scores_faltantes(
            ciclo, pendentes_ciclo, modality_key
        ) or []
    except Exception:
        scores_falt = []
    pool_atual = sorted(set(ausentes) | set(baixa))
    pools = _pools_de_grupos(grupos)
    pool_principal = pools["nucleo_baixa"]
    pool_com_ciclo = sorted(set(pool_atual) | set(pendentes_ciclo))

    pos = pos_analise_recorrencia(
        ciclo,
        spec,
        pedido,
        grupos_atuais=grupos,
        janela_rows=janela,
    )
    rec_pool = ((pos.get("conclusao") or {}).get("recomendacao_pool") if pos.get("ok") else None) or "nucleo_baixa"
    conjunto = _montar_conjunto_construtor(
        grupos,
        clf["tabela"],
        pos if pos.get("ok") else None,
        pendentes_ciclo,
        scores_faltantes=scores_falt,
    )

    concursos = [r["concurso"] for r in linhas]
    fmt = dict(clf["fmt"])
    fmt["pool"] = _fmt(pool_atual)
    fmt["pool_principal"] = _fmt(pool_principal)
    fmt["pool_recuperacao"] = _fmt(ausentes)

    return {
        "ok": True,
        "fonte": "repetidas_no_ciclo",
        "janela": pedido,
        "janela_efetiva": len(linhas),
        "janelas": list(JANELAS),
        "concursos": concursos,
        "linhas": linhas,
        "ocorrencias": ocorrencias,
        "leitura": (
            f"Universo {spec.dezena_min:02d}–{spec.dezena_max:02d}: "
            f"{len(linhas)} linha(s) da coluna Repetidas no Ciclo "
            f"({ocorrencias} ocorrências)."
        ),
        "universo": n_univ,
        "dezena_min": spec.dezena_min,
        "dezena_max": spec.dezena_max,
        "tabela": clf["tabela"],
        "ranking": ranking,
        "por_frequencia": clf["por_frequencia"],
        "grupos": grupos,
        "fmt": fmt,
        "cobertura": {
            "usadas": n_usadas,
            "ausentes": n_aus,
            "pct_usadas": cobertura_pct,
            "pct_ausentes": ausentes_pct,
        },
        "destaques": {
            "lider": lider,
            "lider_pct": lider_pct,
            "top2": top2,
            "top2_ocor": top2_ocor,
            "top2_pct": top2_pct,
            "n_repetidas": len(ranking),
            "n_baixa": len(baixa),
            "n_ausentes": n_aus,
        },
        "faixas": faixas,
        "ciclo": {
            "numero": ciclo.get("numero_ciclo"),
            "percentual": ciclo.get("percentual_completo"),
            "pendentes": pendentes_ciclo,
            "fmt_pendentes": _fmt(pendentes_ciclo),
            "em_andamento": bool(ciclo.get("em_andamento")),
            "scores_faltantes": [
                {"dezena": int(s["dezena"]), "score": s.get("score")}
                for s in scores_falt
                if isinstance(s, dict) and s.get("dezena") is not None
            ],
        },
        "pool": {
            "ausentes_x_baixa": pool_atual,
            "nucleo_x_baixa": pool_principal,
            "recuperacao_ausentes": ausentes,
            "com_faltantes_ciclo": pool_com_ciclo,
            "qtd_baixa_no_pool": len(baixa),
            "qtd_ausentes_no_pool": len(ausentes),
            "qtd_nucleo_no_pool": len(pools["forte_repetidas"]),
            "recomendado": rec_pool,
        },
        "conjunto_construtor": conjunto,
        "pos_analise": pos,
    }
