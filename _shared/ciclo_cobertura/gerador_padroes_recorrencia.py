# -*- coding: utf-8 -*-
"""Gerador CICLO-RECORRÊNCIA — 10 apostas por Padrões II no universo fixo de 16."""
from __future__ import annotations

import importlib.util
import os
import random
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .specs import get_ciclo_spec


def _load_core():
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "geradores_elite", "construtor", "construcoes_core.py",
    ))
    spec = importlib.util.spec_from_file_location("construcoes_core_recorrencia", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_core = _load_core()
QTD_APOSTAS_FIXA = _core.QTD_APOSTAS_FIXA
_montar_por_padrao = _core._montar_por_padrao
aposta_pertence_ao_pool = _core.aposta_pertence_ao_pool
padrao_inicial_de = _core.padrao_inicial_de
padrao_viavel = _core.padrao_viavel
parse_padrao = _core.parse_padrao
pool_por_digito_inicial = _core.pool_por_digito_inicial

INICIAIS = (0, 1, 2, 3)
K_DEFAULT = 7
QTD_APOSTAS = QTD_APOSTAS_FIXA
ALVO_UNIVERSO = 16


def _norm_padrao(raw: str) -> str:
    digs = parse_padrao(raw)
    return " ".join(str(int(x)) for x in digs)


def padrao_cabe(dezenas: Sequence[int], padrao: str) -> bool:
    digs = parse_padrao(padrao)
    if not digs:
        return False
    return padrao_viavel(digs, sorted({int(x) for x in dezenas}))


def montar_lote_padroes(
    dezenas: Sequence[int],
    catalogo: Sequence[str],
    *,
    ultimo: str = "",
    selecionados: Optional[Sequence[str]] = None,
    qtd: int = QTD_APOSTAS,
) -> List[str]:
    """10 padrões: escolhido (último) + selecionados + demais diferenciados viáveis."""
    alvo = int(qtd)
    pool = sorted({int(x) for x in dezenas})
    viaveis: List[str] = []
    vistos: set = set()
    for raw in catalogo or []:
        if not padrao_cabe(pool, raw):
            continue
        n = _norm_padrao(raw)
        if n in vistos:
            continue
        vistos.add(n)
        viaveis.append(n)
    if not viaveis:
        return []
    ok = set(viaveis)
    ordem: List[str] = []
    seen: set = set()

    def _push(raw: str) -> None:
        if not raw:
            return
        n = _norm_padrao(raw)
        if n in seen or n not in ok:
            return
        seen.add(n)
        ordem.append(n)

    _push(ultimo)
    for raw in selecionados or []:
        _push(raw)
    for p in viaveis:
        _push(p)
    if not ordem:
        return []
    return [ordem[i] if i < len(ordem) else ordem[i % len(ordem)] for i in range(alvo)]


def classificar_iniciais(dezenas: Sequence[int]) -> Dict[str, Any]:
    nums = sorted({int(x) for x in dezenas})
    grupos = pool_por_digito_inicial(nums)
    contagem = {int(i): len(grupos.get(int(i), [])) for i in INICIAIS}
    return {
        "dezenas": nums,
        "grupos": {str(i): list(grupos.get(i, [])) for i in INICIAIS},
        "contagem": contagem,
        "total": len(nums),
    }


def necessidade_lote(padroes: Sequence[str], k: int = K_DEFAULT) -> Dict[str, Any]:
    """Necessidade do lote = máximo por inicial (dezenas NÃO são estoque entre apostas)."""
    max_need = {int(i): 0 for i in INICIAIS}
    itens: List[Dict[str, Any]] = []
    for idx, raw in enumerate(padroes or []):
        digs = parse_padrao(raw)
        pstr = " ".join(str(int(x)) for x in digs)
        need = {int(i): 0 for i in INICIAIS}
        for d in digs:
            if int(d) in need:
                need[int(d)] += 1
        for i in INICIAIS:
            max_need[int(i)] = max(max_need[int(i)], need[int(i)])
        itens.append({
            "indice": idx + 1,
            "padrao": pstr,
            "digs": digs,
            "need": need,
            "tamanho_ok": len(digs) == int(k),
        })
    return {"max_need": max_need, "itens": itens, "k": int(k)}


def _faltas(contagem: Dict[int, int], max_need: Dict[int, int]) -> List[Dict[str, Any]]:
    out = []
    for i in INICIAIS:
        disp = int(contagem.get(int(i), 0))
        nec = int(max_need.get(int(i), 0))
        if disp < nec:
            out.append({
                "inicial": int(i),
                "necessario": nec,
                "disponivel": disp,
                "falta": nec - disp,
            })
    return out


def validar_universo(
    dezenas: Sequence[int],
    padroes: Sequence[str],
    *,
    k: int = K_DEFAULT,
    alvo: int = ALVO_UNIVERSO,
) -> Dict[str, Any]:
    clf = classificar_iniciais(dezenas)
    nec = necessidade_lote(padroes, k=k)
    padroes_norm = [_norm_padrao(p) for p in (padroes or []) if parse_padrao(p)]
    tamanho_ok = all(it["tamanho_ok"] for it in nec["itens"]) if nec["itens"] else False
    qtd_ok = len(padroes_norm) == QTD_APOSTAS
    univ_ok = clf["total"] == int(alvo)
    faltas = _faltas(clf["contagem"], nec["max_need"]) if padroes_norm else []
    padroes_ok = []
    padroes_falha = []
    for it in nec["itens"]:
        if not it["tamanho_ok"]:
            padroes_falha.append({**it, "ok": False, "motivo": "tamanho_incompativel"})
            continue
        ok = padrao_viavel(it["digs"], clf["dezenas"])
        row = {**it, "ok": ok}
        (padroes_ok if ok else padroes_falha).append(row)

    gerar_ok = bool(
        univ_ok
        and qtd_ok
        and tamanho_ok
        and not faltas
        and len(padroes_ok) == QTD_APOSTAS
        and not padroes_falha
    )
    return {
        "ok": gerar_ok,
        "universo_ok": univ_ok,
        "universo_n": clf["total"],
        "universo_alvo": int(alvo),
        "classificacao": clf,
        "max_need": nec["max_need"],
        "faltas": faltas,
        "qtd_padroes": len(padroes_norm),
        "qtd_padroes_ok": qtd_ok,
        "padroes_ok": padroes_ok,
        "padroes_falha": padroes_falha,
        "reutilizacao_entre_apostas": "PERMITIDA",
        "duplicacao_interna": "BLOQUEADA",
        "gerar_liberado": gerar_ok,
    }


def _freq_map(tabela: Sequence[dict]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for t in tabela or []:
        try:
            out[int(t["dezena"])] = int(t.get("vezes") or 0)
        except (TypeError, ValueError, KeyError):
            continue
    return out


def _score_map(scores: Sequence[dict]) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for s in scores or []:
        if not isinstance(s, dict) or s.get("dezena") is None:
            continue
        out[int(s["dezena"])] = float(s.get("score") or 0)
    return out


def _faltantes_ciclo(rec: Optional[Dict[str, Any]], pool: Optional[Iterable[int]] = None) -> List[int]:
    """Dezenas que o ciclo ainda precisa fechar, já no universo das 16 quando `pool` vem."""
    rec = rec or {}
    ciclo = rec.get("ciclo") or {}
    cj = rec.get("conjunto_construtor") or {}
    raw: List[int] = []
    for src in (
        cj.get("faltantes_ciclo"),
        ciclo.get("pendentes"),
        ciclo.get("dezenas_pendentes"),
    ):
        for x in src or []:
            try:
                raw.append(int(x))
            except (TypeError, ValueError):
                continue
    seen = set()
    uniq: List[int] = []
    for n in raw:
        if n in seen:
            continue
        seen.add(n)
        uniq.append(n)
    if pool is not None:
        permitido = {int(x) for x in pool}
        uniq = [n for n in uniq if n in permitido]
    scores = _score_map(ciclo.get("scores_faltantes") or [])
    uniq.sort(key=lambda n: (-scores.get(n, 0.0), n))
    return uniq


def _ranking_candidatas(
    inicial: int,
    excluir: Iterable[int],
    rec: Dict[str, Any],
) -> List[int]:
    """Ordem núcleo × baixa presença (nunca aleatória)."""
    excl = {int(x) for x in excluir}
    grupos = rec.get("grupos") or {}
    pool = rec.get("pool") or {}
    ciclo = rec.get("ciclo") or {}
    spec_min = int(rec.get("dezena_min") or 1)
    spec_max = int(rec.get("dezena_max") or 31)
    freq = _freq_map(rec.get("tabela") or [])
    scores = _score_map(ciclo.get("scores_faltantes") or [])
    pendentes = set(_faltantes_ciclo(rec))
    nucleo = set(int(x) for x in (grupos.get("nucleo_forte") or [])) | set(
        int(x) for x in (grupos.get("repetido") or [])
    )
    baixa = set(int(x) for x in (grupos.get("baixa_presenca") or []))
    nucleo_x_baixa = set(int(x) for x in (pool.get("nucleo_x_baixa") or []))

    def _match(n: int) -> bool:
        return int(n) not in excl and (int(n) // 10) == int(inicial)

    buckets: List[Tuple[int, float, int, int]] = []
    for n in range(spec_min, spec_max + 1):
        if not _match(n):
            continue
        # prioridade: pendente ciclo, núcleo, baixa, pool núcleo×baixa, resto
        if n in pendentes:
            prio = 0
        elif n in nucleo:
            prio = 1
        elif n in baixa:
            prio = 2
        elif n in nucleo_x_baixa:
            prio = 3
        else:
            prio = 4
        buckets.append((prio, -scores.get(n, 0.0), -freq.get(n, 0), n))
    buckets.sort()
    return [n for _p, _s, _f, n in buckets]


def _pior_para_remover(inicial: int, atuais: Sequence[int], rec: Dict[str, Any]) -> Optional[int]:
    """Remove a dezena da inicial com menor alinhamento núcleo × baixa."""
    cand = [int(d) for d in atuais if (int(d) // 10) == int(inicial)]
    if not cand:
        return None
    ranked = _ranking_candidatas(inicial, [], rec)
    pos = {n: i for i, n in enumerate(ranked)}
    cand.sort(key=lambda n: (-pos.get(n, 10_000), n))
    return cand[0]


def _pick_inicial(
    dig: int,
    qtd: int,
    pool_set: set,
    rec: Dict[str, Any],
    rng: random.Random,
    usados: Sequence[int],
) -> Optional[List[int]]:
    """Faltantes do ciclo primeiro (obrigatórios se a inicial entra no padrão); resto do universo."""
    used = {int(x) for x in usados}
    falt = [
        n for n in _faltantes_ciclo(rec, pool_set)
        if (int(n) // 10) == int(dig) and n not in used
    ]
    take = falt[: int(qtd)]
    if len(take) >= int(qtd):
        return take[: int(qtd)]
    ranked = [
        n for n in _ranking_candidatas(dig, list(used) + take, rec)
        if n in pool_set and n not in take
    ]
    rng.shuffle(ranked)
    take.extend(ranked[: int(qtd) - len(take)])
    if len(take) < int(qtd):
        return None
    return take


def _montar_por_padrao_ciclo(
    pool: Sequence[int],
    padrao: Sequence[int],
    rec: Dict[str, Any],
    rng: random.Random,
) -> Optional[List[int]]:
    pool_set = {int(x) for x in pool}
    need = Counter(int(x) for x in padrao)
    pick: List[int] = []
    for dig, qtd in sorted(need.items()):
        escolhidos = _pick_inicial(dig, qtd, pool_set, rec, rng, pick)
        if not escolhidos or len(escolhidos) != qtd:
            return None
        pick.extend(escolhidos)
    if len(pick) != len(padrao):
        return None
    if not aposta_pertence_ao_pool(pick, pool):
        return None
    return sorted(pick)


def sugerir_complementacao(
    dezenas: Sequence[int],
    padroes: Sequence[str],
    rec: Dict[str, Any],
    *,
    k: int = K_DEFAULT,
    alvo: int = ALVO_UNIVERSO,
) -> Dict[str, Any]:
    atuais = list(dict.fromkeys(int(x) for x in dezenas))
    val = validar_universo(atuais, padroes, k=k, alvo=alvo)
    nec = val["max_need"]
    sugestoes: List[Dict[str, Any]] = []
    working = list(atuais)

    def _counts(nums: Sequence[int]) -> Dict[int, int]:
        c = {int(i): 0 for i in INICIAIS}
        for d in nums:
            i = int(d) // 10
            if i in c:
                c[i] += 1
        return c

    guard = 0
    while guard < 32:
        guard += 1
        counts = _counts(working)
        faltas = _faltas(counts, nec)
        if not faltas and len(working) == int(alvo):
            break
        if faltas:
            f = faltas[0]
            dig = int(f["inicial"])
            ranked = _ranking_candidatas(dig, working, rec)
            if not ranked:
                sugestoes.append({
                    "inicial": dig,
                    "necessario": f["necessario"],
                    "disponivel": f["disponivel"],
                    "falta": f["falta"],
                    "sugestao": None,
                    "motivo": "sem_candidata",
                })
                break
            entra = ranked[0]
            sai = None
            if len(working) >= int(alvo):
                surplus = [i for i in INICIAIS if counts[int(i)] > int(nec.get(int(i), 0))]
                if not surplus:
                    sugestoes.append({
                        "inicial": dig,
                        "necessario": f["necessario"],
                        "disponivel": f["disponivel"],
                        "falta": f["falta"],
                        "sugestao": entra,
                        "motivo": "sem_folga_para_troca",
                    })
                    break
                sai = _pior_para_remover(surplus[0], working, rec)
                if sai is None:
                    break
                working = [d for d in working if d != sai]
            working.append(entra)
            sugestoes.append({
                "inicial": dig,
                "necessario": f["necessario"],
                "disponivel": f["disponivel"],
                "falta": f["falta"],
                "sugestao": entra,
                "sai": sai,
                "motivo": "add" if sai is None else "troca",
            })
            continue
        if len(working) < int(alvo):
            added = False
            for dig in INICIAIS:
                ranked = _ranking_candidatas(dig, working, rec)
                if ranked:
                    working.append(ranked[0])
                    sugestoes.append({
                        "inicial": int(dig),
                        "sugestao": ranked[0],
                        "sai": None,
                        "motivo": "completar_tamanho",
                    })
                    added = True
                    break
            if not added:
                break
            continue
        break

    working = sorted(set(int(x) for x in working))
    val_depois = validar_universo(working, padroes, k=k, alvo=alvo)
    return {
        "dezenas_antes": sorted(set(int(x) for x in atuais)),
        "dezenas": working,
        "sugestoes": sugestoes,
        "validacao": val_depois,
        "possivel": bool(val_depois.get("gerar_liberado")) or (
            val_depois.get("universo_ok") and not val_depois.get("faltas")
        ),
    }


def completar_universo(
    dezenas: Sequence[int],
    padroes: Sequence[str],
    rec: Dict[str, Any],
    **kwargs,
) -> Dict[str, Any]:
    out = sugerir_complementacao(dezenas, padroes, rec, **kwargs)
    out["ok"] = bool(out.get("possivel"))
    return out


def gerar_apostas_padroes_recorrencia(
    modality_key: str,
    *,
    dezenas: Sequence[int],
    padroes: Sequence[str],
    mes_num=None,
    seed: Optional[int] = None,
    k: int = K_DEFAULT,
    rec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    spec = get_ciclo_spec(modality_key)
    k_use = int(k if k is not None else spec.sorteadas or K_DEFAULT)
    pool = sorted({int(x) for x in dezenas})
    pad_list = [_norm_padrao(p) for p in (padroes or [])]
    val = validar_universo(pool, pad_list, k=k_use)
    if not val["gerar_liberado"]:
        return {
            "ok": False,
            "sucesso": False,
            "erro_codigo": "universo_insuficiente",
            "erro": (
                "⚠️ NÃO É POSSÍVEL GERAR AS 10 APOSTAS. "
                "As 16 dezenas atuais não conseguem atender aos padrões selecionados. "
                "Escolha outros padrões ou complete as 16 dezenas."
            ),
            "validacao": val,
        }

    rec_use = rec if isinstance(rec, dict) else {}
    faltantes = _faltantes_ciclo(rec_use, pool)
    rng = random.Random(seed)
    apostas: List[Dict[str, Any]] = []
    vistos: set = set()
    for i, pstr in enumerate(pad_list, start=1):
        digs = parse_padrao(pstr)
        escolhida = None
        for _try in range(80):
            if rec_use:
                pick = _montar_por_padrao_ciclo(pool, digs, rec_use, rng)
            else:
                pick = _montar_por_padrao(pool, digs, rng)
            if not pick:
                continue
            if len(set(pick)) != k_use:
                continue
            if not aposta_pertence_ao_pool(pick, pool):
                continue
            key = frozenset(pick)
            if key in vistos and _try < 40:
                continue
            escolhida = pick
            vistos.add(key)
            break
        if not escolhida:
            return {
                "ok": False,
                "sucesso": False,
                "erro_codigo": "falha_montagem",
                "erro": (
                    f"⚠️ NÃO É POSSÍVEL GERAR AS 10 APOSTAS. "
                    f"Falha ao montar a aposta {i:02d} no padrão {pstr}."
                ),
                "validacao": val,
            }
        apostas.append({
            "numero": i,
            "dezenas": escolhida,
            "dezenas_fmt": " ".join(f"{d:02d}" for d in escolhida),
            "padrao": pstr,
            "padrao_inicial": padrao_inicial_de(escolhida),
        })

    if mes_num is not None and mes_num != "":
        from .pos_geracao import aplicar_mes_apostas
        apostas = aplicar_mes_apostas(apostas, mes_num)

    return {
        "ok": True,
        "sucesso": True,
        "geradas": len(apostas),
        "apostas": apostas,
        "universo": pool,
        "universo_fmt": " ".join(f"{d:02d}" for d in pool),
        "padroes": pad_list,
        "faltantes_ciclo": faltantes,
        "validacao": val,
        "reutilizacao_entre_apostas": True,
        "duplicacao_interna_bloqueada": True,
    }


def _rec_ou_analisar(modality_key: str, n: Optional[int], rec: Optional[dict]) -> Dict[str, Any]:
    if rec and rec.get("ok"):
        return rec
    from .recorrencia_service import analisar_recorrencia
    return analisar_recorrencia(modality_key, n=n or 4)


def validar_request(modality_key: str, data: dict) -> Dict[str, Any]:
    rec = _rec_ou_analisar(modality_key, data.get("n"), data.get("recorrencia"))
    dezenas = data.get("dezenas") or ((rec.get("conjunto_construtor") or {}).get("dezenas") or [])
    padroes = data.get("padroes") or []
    val = validar_universo(dezenas, padroes)
    clf = val["classificacao"]
    return {
        "ok": True,
        "validacao": val,
        "classificacao": clf,
        "universo": clf["dezenas"],
        "faltas": val["faltas"],
        "recorrencia_ok": bool(rec.get("ok")),
    }


def completar_request(modality_key: str, data: dict) -> Dict[str, Any]:
    rec = _rec_ou_analisar(modality_key, data.get("n"), data.get("recorrencia"))
    if not rec.get("ok"):
        return {"ok": False, "erro": rec.get("erro") or "Recorrência indisponível."}
    dezenas = data.get("dezenas") or ((rec.get("conjunto_construtor") or {}).get("dezenas") or [])
    padroes = data.get("padroes") or []
    out = completar_universo(dezenas, padroes, rec)
    out["ok"] = True
    return out


def gerar_request(modality_key: str, data: dict) -> Dict[str, Any]:
    rec = _rec_ou_analisar(modality_key, data.get("n"), data.get("recorrencia"))
    dezenas = data.get("dezenas") or ((rec.get("conjunto_construtor") or {}).get("dezenas") or [])
    padroes = data.get("padroes") or []
    seed = data.get("seed")
    try:
        seed = int(seed) if seed not in (None, "") else None
    except (TypeError, ValueError):
        seed = None
    return gerar_apostas_padroes_recorrencia(
        modality_key,
        dezenas=dezenas,
        padroes=padroes,
        mes_num=data.get("mes_num") or data.get("mes"),
        seed=seed,
        rec=rec,
    )
