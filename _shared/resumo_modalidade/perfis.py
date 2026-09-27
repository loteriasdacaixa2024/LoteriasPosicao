# -*- coding: utf-8 -*-
"""Gerador por perfis — lê o DNA do Resumo Geral, sem recalcular o costume."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Sequence, Set

from analise_gaps_ciclo.core import analisar_regua_combinacoes, gaps_de
from resumo_modalidade.service import ResumoModalidadeService, _carregar_sorteios, _sequencias
from resumo_modalidade.specs import ResumoSpec, faixa_de, get_resumo_spec

PERFIS: List[Dict[str, str]] = [
    {
        "id": "repeticao",
        "titulo": "A · Repetição",
        "texto": "1 ou 2 dezenas do concurso anterior, final igual e paridade da moda.",
    },
    {
        "id": "distribuicao",
        "titulo": "B · Distribuição",
        "texto": "Faixas B/M/A, soma, amplitude e paridade da moda.",
    },
    {
        "id": "gaps",
        "titulo": "C · Gaps",
        "texto": "Média dos gaps na faixa habitual, sequência e régua das posições.",
    },
    {
        "id": "finais",
        "titulo": "D · Finais",
        "texto": "Pelo menos um final igual e quantidade de finais distinta da moda.",
    },
    {
        "id": "historico",
        "titulo": "E · Histórico",
        "texto": "Prefere dezenas que mais aparecem no histórico da modalidade.",
    },
]

_IDS = {p["id"] for p in PERFIS}


def _chave(dz: Sequence[int], motor: str):
    nums = [int(x) for x in dz]
    if motor == "colunas":
        return tuple(nums)
    return frozenset(nums)


def _ja_sorteada(dz: Sequence[int], historico: Set, motor: str) -> bool:
    return _chave(dz, motor) in historico


def _fmt(n: int) -> str:
    return f"{int(n):02d}"


def _parse_pares(moda: str, k: int) -> int:
    try:
        left = str(moda or "").replace(" ", "").split("/")[0]
        return int(left.replace("P", ""))
    except (ValueError, IndexError):
        return max(0, k // 2)


def _faixa_p(series: Sequence[float]) -> tuple:
    if not series:
        return 0, 0
    ss = sorted(series)
    n = len(ss)
    return ss[int(0.20 * (n - 1))], ss[int(0.80 * (n - 1))]


def _alvos(spec: ResumoSpec, sorteios: List[Dict[str, Any]], analise: Dict[str, Any]) -> Dict[str, Any]:
    draws = []
    for s in sorteios:
        dz = sorted(int(x) for x in s["dezenas"])[: spec.sorteadas]
        if len(dz) == spec.sorteadas:
            draws.append(dz)
    ultimo = draws[-1] if draws else []
    gap_medios = []
    amps = []
    for dz in draws:
        gs = gaps_de(dz)
        if gs:
            gap_medios.append(sum(gs) / len(gs))
        amps.append(max(dz) - min(dz))
    glo, ghi = _faixa_p(gap_medios)
    alo, ahi = _faixa_p(amps)
    regua = analisar_regua_combinacoes(list(reversed(draws)), limite_linhas=0)
    refs = [
        int(r["referencia"])
        for r in (regua.get("referencias") or [])
        if r.get("referencia") is not None
    ]
    soma = analise.get("soma") or {}
    seq = analise.get("sequencias") or {}
    fin = analise.get("finais") or {}
    rep = analise.get("repeticao") or {}
    top = ((analise.get("faixas") or {}).get("top3") or [None])[0] or {}
    freq = {
        int(r["dezena"]): int(r["qtd"])
        for r in ((analise.get("dezenas") or {}).get("stats") or [])
    }
    return {
        "prev": set(ultimo),
        "historico": {_chave(dz, spec.motor) for dz in draws},
        "pares": _parse_pares((analise.get("par_impar") or {}).get("moda"), spec.sorteadas),
        "rep_lo": 1,
        "rep_hi": 2,
        "rep_moda": int(rep.get("moda") or 1),
        "exige_final": float(fin.get("pct_pelo_menos_um") or 0) >= 55,
        "soma_lo": int(soma.get("p20") or 0),
        "soma_hi": int(soma.get("p80") or 0),
        "seq_qtd": int(seq.get("qtd_mais_freq") or 1),
        "exige_seq": float(seq.get("pct_com_pelo_menos_uma") or 0) >= 55,
        "bma": list(top.get("counts") or []),
        "gap_lo": glo,
        "gap_hi": ghi,
        "amp_lo": alo,
        "amp_hi": ahi,
        "refs": refs,
        "freq": freq,
    }


def _finais_ok(dz: Sequence[int]) -> bool:
    fins: Dict[int, int] = {}
    for d in dz:
        fins[d % 10] = fins.get(d % 10, 0) + 1
    return any(v >= 2 for v in fins.values())


def _du_distintos(dz: Sequence[int]) -> int:
    return len({d % 10 for d in dz})


def _obrigatorio(dz: Sequence[int], ativos: Set[str], alvos: Dict[str, Any], spec: ResumoSpec) -> bool:
    if "repeticao" in ativos and alvos["prev"]:
        nrep = len(set(dz) & alvos["prev"])
        if not (alvos["rep_lo"] <= nrep <= alvos["rep_hi"]):
            return False
    if ("repeticao" in ativos or "finais" in ativos) and alvos["exige_final"]:
        if not _finais_ok(dz):
            return False
    if "repeticao" in ativos or "distribuicao" in ativos:
        pares = sum(1 for d in dz if d % 2 == 0)
        if pares != alvos["pares"]:
            return False
    return True


def _pontos(dz: Sequence[int], ativos: Set[str], alvos: Dict[str, Any], spec: ResumoSpec) -> Dict[str, Any]:
    notas: List[str] = []
    pts = 0
    nrep = len(set(dz) & alvos["prev"]) if alvos["prev"] else 0
    if "repeticao" in ativos and alvos["rep_lo"] <= nrep <= alvos["rep_hi"]:
        pts += 10
        notas.append(f"+10 repetidas {nrep}")
    if ("repeticao" in ativos or "finais" in ativos) and _finais_ok(dz):
        pts += 10
        notas.append("+10 final igual")
    pares = sum(1 for d in dz if d % 2 == 0)
    if ("repeticao" in ativos or "distribuicao" in ativos) and pares == alvos["pares"]:
        pts += 8
        notas.append(f"+8 paridade {pares}P")
    sm = sum(dz)
    if "distribuicao" in ativos and alvos["soma_lo"] <= sm <= alvos["soma_hi"]:
        pts += 8
        notas.append("+8 soma na faixa")
    gs = gaps_de(dz)
    if gs and "gaps" in ativos:
        media = sum(gs) / len(gs)
        if alvos["gap_lo"] <= media <= alvos["gap_hi"]:
            pts += 7
            notas.append("+7 gaps na faixa")
    if "distribuicao" in ativos and alvos["bma"]:
        bag: Dict[str, int] = {}
        for d in dz:
            c = faixa_de(d, spec)
            if c:
                bag[c] = bag.get(c, 0) + 1
        counts = [bag.get(codigo, 0) for codigo, _a, _b, _c in spec.faixas]
        if counts == list(alvos["bma"]):
            pts += 7
            notas.append("+7 faixas da moda")
    amp = max(dz) - min(dz)
    if "distribuicao" in ativos and alvos["amp_lo"] <= amp <= alvos["amp_hi"]:
        pts += 5
        notas.append("+5 amplitude")
    nseq = len(_sequencias(dz))
    if "gaps" in ativos:
        if nseq == alvos["seq_qtd"] or (alvos["exige_seq"] and nseq >= 1):
            pts += 5
            notas.append(f"+5 sequências {nseq}")
    if "gaps" in ativos and alvos["refs"] and len(alvos["refs"]) == len(dz):
        perto = sum(1 for d, r in zip(dz, alvos["refs"]) if abs(d - r) <= 3)
        if perto >= max(1, len(dz) // 2):
            pts += 5
            notas.append(f"+5 régua {perto}/{len(dz)}")
    if "finais" in ativos:
        pts += 4
        notas.append(f"+4 finais distintos {_du_distintos(dz)}")
    if "historico" in ativos and alvos["freq"]:
        rank = sorted(alvos["freq"], key=lambda d: -alvos["freq"][d])
        quentes = set(rank[: max(8, spec.sorteadas)])
        q = len(set(dz) & quentes)
        if q >= spec.sorteadas // 2:
            pts += 5
            notas.append(f"+5 frequência {q}")
    return {"pontos": pts, "notas": notas, "soma": sm, "pares": pares, "repetidas": nrep}


def _amostra(spec: ResumoSpec, n: int, rng: random.Random) -> List[int]:
    uni = list(range(spec.dezena_min, spec.dezena_max + 1))
    if spec.motor == "colunas":
        return [rng.randrange(spec.dezena_min, spec.dezena_max + 1) for _ in range(spec.sorteadas)]
    return sorted(rng.sample(uni, spec.sorteadas))


def _diversos(ranked: List[Dict[str, Any]], quantidade: int, k: int) -> List[Dict[str, Any]]:
    escolhidos: List[Dict[str, Any]] = []
    limite = max(2, k - 3)
    for row in ranked:
        dz = set(row["nums"])
        if any(len(dz & set(o["nums"])) > limite for o in escolhidos):
            continue
        escolhidos.append(row)
        if len(escolhidos) >= quantidade:
            break
    if len(escolhidos) < quantidade:
        vistos = {tuple(r["nums"]) for r in escolhidos}
        for row in ranked:
            if tuple(row["nums"]) in vistos:
                continue
            escolhidos.append(row)
            if len(escolhidos) >= quantidade:
                break
    return escolhidos


def gerar_por_perfis(
    modality_key: str,
    perfis: Sequence[str],
    quantidade: int = 10,
) -> Dict[str, Any]:
    ativos = [p for p in perfis if p in _IDS]
    if not ativos:
        return {"sucesso": False, "erro": "Escolha pelo menos um perfil."}
    spec = get_resumo_spec(modality_key)
    sorteios = _carregar_sorteios(spec)
    if not sorteios:
        return {"sucesso": False, "erro": "Sem sorteios no banco."}
    analise = ResumoModalidadeService._analisar(spec, sorteios)
    alvos = _alvos(spec, sorteios, analise)
    ativo_set = set(ativos)
    rng = random.Random()
    vistos: Set[tuple] = set()
    ranked: List[Dict[str, Any]] = []
    tentativas = 25000 if spec.sorteadas <= 7 else 12000
    for _ in range(tentativas):
        dz = _amostra(spec, spec.sorteadas, rng)
        if _ja_sorteada(dz, alvos["historico"], spec.motor):
            continue
        key = _chave(dz, spec.motor)
        if key in vistos:
            continue
        if not _obrigatorio(dz, ativo_set, alvos, spec):
            continue
        vistos.add(key)
        det = _pontos(dz, ativo_set, alvos, spec)
        ranked.append({"nums": dz, **det})
        if len(ranked) >= 4000:
            break
    ranked.sort(key=lambda r: -r["pontos"])
    ranked = [r for r in ranked if not _ja_sorteada(r["nums"], alvos["historico"], spec.motor)]
    qtd = max(1, min(int(quantidade or 10), 30))
    top = _diversos(ranked, qtd, spec.sorteadas)
    top = [r for r in top if not _ja_sorteada(r["nums"], alvos["historico"], spec.motor)]
    if not top:
        return {
            "sucesso": False,
            "erro": "Nenhuma combinação passou nos obrigatórios destes perfis. Tire um perfil e tente de novo.",
            "perfis": ativos,
        }
    return {
        "sucesso": True,
        "perfis": ativos,
        "quantidade": len(top),
        "examinadas": len(ranked),
        "obrigatorios": _rotulos_obrigatorios(ativo_set, alvos),
        "apostas": [
            {
                "ordem": i,
                "dezenas": [_fmt(d) for d in row["nums"]],
                "pontos": row["pontos"],
                "soma": row["soma"],
                "pares": row["pares"],
                "repetidas": row["repetidas"],
                "notas": row["notas"],
            }
            for i, row in enumerate(top, start=1)
        ],
    }


def _rotulos_obrigatorios(ativos: Set[str], alvos: Dict[str, Any]) -> List[str]:
    out = ["Nenhum perfil devolve combinação já sorteada."]
    if "repeticao" in ativos:
        out.append(f"Repetidas do anterior entre {alvos['rep_lo']} e {alvos['rep_hi']}.")
    if ("repeticao" in ativos or "finais" in ativos) and alvos["exige_final"]:
        out.append("Pelo menos um par com o mesmo final.")
    if "repeticao" in ativos or "distribuicao" in ativos:
        out.append(f"Paridade da moda: {alvos['pares']} pares.")
    return out
