# -*- coding: utf-8 -*-
"""Gerador Resumo Geral → Apostas.

Lê o painel do Resumo Geral. Não recalcula outra lista de regras.
Corte, ponto e exibição saem do tipo que o painel já gravou.
"""
from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional, Sequence, Set

from analise_gaps_ciclo.core import analisar_regua_combinacoes, gaps_de
from resumo_modalidade.concurso import (
    _mes_curto,
    _texto_diagonais,
    _texto_finais,
    _texto_regua,
    _texto_sequencias,
)
from resumo_modalidade.perfis import _amostra, _faixa_p, _ja_sorteada
from resumo_modalidade.service import ResumoModalidadeService, _carregar_sorteios, _sequencias
from resumo_modalidade.specs import ResumoSpec, faixa_de, get_resumo_spec, tem_resumo_modalidade

_CORTES = {
    "Pares × ímpares",
    "Repetidas do anterior",
    "Soma",
    "Média dos gaps",
    "Finais iguais",
}

# Informação no Resumo; na geração entram só como nota, sem eliminar jogo.
_PONTO_EXTRA = {
    "Dezenas pendentes do ciclo",
    "Mais atrasadas",
}


def _papel(item: Dict[str, Any]) -> str:
    if item.get("criterio") in _PONTO_EXTRA:
        return "ponto"
    tipo = item.get("tipo") or "info"
    if tipo in ("info", "nao_confirmado"):
        return "exibe"
    if tipo == "tendencia":
        return "ponto"
    if tipo == "frequente" and item.get("criterio") in _CORTES:
        return "corte"
    if tipo == "frequente":
        return "ponto"
    return "exibe"


def _ligado_padrao(item: Dict[str, Any], papel: str) -> bool:
    if item.get("criterio") == "Repetidas do anterior":
        return False
    if item.get("criterio") in _PONTO_EXTRA:
        return True
    if papel == "exibe":
        return False
    if papel == "corte":
        return True
    return item.get("uso") in ("geracao", "filtro") or item.get("tipo") == "tendencia"


def _fmt(n: int) -> str:
    return f"{int(n):02d}"


def _linhas(dz: Sequence[int]) -> int:
    return len({((int(n) - 1) // 10) + 1 for n in dz})


def _dd_du(dz: Sequence[int]) -> tuple:
    dd = {int(n) // 10 for n in dz}
    du = {int(n) % 10 for n in dz}
    return len(dd), len(du)


def _finais_ok(dz: Sequence[int]) -> bool:
    fins = [int(n) % 10 for n in dz]
    return len(fins) != len(set(fins))


def _ctx(spec: ResumoSpec, data: Dict[str, Any], sorteios: List[Dict[str, Any]]) -> Dict[str, Any]:
    draws = []
    for s in sorteios:
        dz = sorted(int(x) for x in s["dezenas"])[: spec.sorteadas]
        if len(dz) == spec.sorteadas:
            draws.append(dz)
    ultimo = draws[-1] if draws else []
    gap_medios = []
    amps = []
    linhas_c: Dict[int, int] = {}
    dd_c: Dict[int, int] = {}
    du_c: Dict[int, int] = {}
    for dz in draws:
        gs = gaps_de(dz)
        if gs:
            gap_medios.append(sum(gs) / len(gs))
        amps.append(max(dz) - min(dz))
        l = _linhas(dz)
        linhas_c[l] = linhas_c.get(l, 0) + 1
        dd, du = _dd_du(dz)
        dd_c[dd] = dd_c.get(dd, 0) + 1
        du_c[du] = du_c.get(du, 0) + 1
    glo, ghi = _faixa_p(gap_medios)
    alo, ahi = _faixa_p(amps)
    regua = analisar_regua_combinacoes(list(reversed(draws)), limite_linhas=0)
    refs = [
        int(r["referencia"])
        for r in (regua.get("referencias") or [])
        if r.get("referencia") is not None
    ]
    pi = data.get("par_impar") or {}
    soma = data.get("soma") or {}
    seq = data.get("sequencias") or {}
    fin = data.get("finais") or {}
    faixas = data.get("faixas") or {}
    pad = (data.get("padrao_inicial") or {}).get("mais_freq") or {}
    stats = (data.get("dezenas") or {}).get("stats") or []
    freq = {int(r["dezena"]): int(r["qtd"]) for r in stats}
    rank = sorted(freq, key=lambda d: -freq[d])
    sp = None
    try:
        from geradores_elite.comportamento.specs import SPECS
        sp = SPECS.get(spec.modality_key)
    except Exception:
        sp = None
    meses = [int(s["mes_num"]) for s in sorteios if s.get("mes_num")]
    mes_num = max(set(meses), key=meses.count) if meses else None
    mes_nome = ""
    if mes_num:
        for s in reversed(sorteios):
            if int(s.get("mes_num") or 0) == mes_num and s.get("mes_nome"):
                mes_nome = str(s["mes_nome"])
                break
    return {
        "spec": spec,
        "prev": set(ultimo),
        "historico": {frozenset(dz) for dz in draws},
        "pares": int(str(pi.get("moda") or "3P").split("P")[0].strip() or 3),
        "soma_lo": int(soma.get("p20") or 0),
        "soma_hi": int(soma.get("p80") or 0),
        "gap_lo": glo,
        "gap_hi": ghi,
        "amp_lo": alo,
        "amp_hi": ahi,
        "refs": refs,
        "bma_top": [tuple(x.get("counts") or []) for x in (faixas.get("top3") or [])],
        "seq_minima": float(seq.get("pct_com_pelo_menos_uma") or 0) >= 55,
        "linhas_moda": max(linhas_c, key=linhas_c.get) if linhas_c else None,
        "dd_moda": max(dd_c, key=dd_c.get) if dd_c else None,
        "du_moda": max(du_c, key=du_c.get) if du_c else None,
        "padrao": str(pad.get("valor") or ""),
        "quentes": set(rank[: max(8, spec.sorteadas)]),
        "sp": sp,
        "mes_num": mes_num,
        "mes_nome": mes_nome,
        "grupo_moda": {},
        "pendentes": _pendentes_ciclo(data),
        "atrasadas": _atrasadas(data),
    }


def _pendentes_ciclo(data: Dict[str, Any]) -> Set[int]:
    atual = ((data.get("ciclo") or {}).get("atual") or {})
    bruto = atual.get("pendentes_num") or atual.get("pendentes") or []
    saida = set()
    for item in bruto:
        try:
            saida.add(int(item))
        except (TypeError, ValueError):
            continue
    return saida


def _atrasadas(data: Dict[str, Any], limite: int = 5) -> Set[int]:
    stats = ((data.get("dezenas") or {}).get("stats") or [])
    ordem = sorted(
        stats,
        key=lambda r: (-int(r.get("atraso") or 0), int(r.get("dezena") or 0)),
    )
    saida = set()
    for r in ordem[:limite]:
        try:
            saida.add(int(r["dezena"]))
        except (TypeError, ValueError, KeyError):
            continue
    return saida


def _grupo_n(dz: Sequence[int], conjunto: Set[int]) -> int:
    return sum(1 for n in dz if int(n) in conjunto)


def _cumpre(nome: str, dz: Sequence[int], ctx: Dict[str, Any]) -> Optional[bool]:
    spec: ResumoSpec = ctx["spec"]
    if nome == "Pares × ímpares":
        return sum(1 for n in dz if int(n) % 2 == 0) == ctx["pares"]
    if nome == "Repetidas do anterior":
        nrep = len(set(dz) & ctx["prev"])
        return 1 <= nrep <= 2
    if nome == "Soma":
        sm = sum(dz)
        return ctx["soma_lo"] <= sm <= ctx["soma_hi"]
    if nome == "Média dos gaps":
        gs = gaps_de(list(dz))
        if not gs:
            return False
        media = sum(gs) / len(gs)
        return ctx["gap_lo"] <= media <= ctx["gap_hi"]
    if nome == "Finais iguais":
        return _finais_ok(dz)
    if nome == "Sequências":
        return len(_sequencias(dz)) >= 1
    if nome == "Faixas B/M/A":
        bag: Dict[str, int] = {}
        for n in dz:
            cod = faixa_de(int(n), spec)
            bag[cod] = bag.get(cod, 0) + 1
        chave = tuple(bag.get(c, 0) for c, _lo, _hi, _lbl in spec.faixas)
        if any(v == 0 for v in chave):
            return False
        return chave in ctx["bma_top"] if ctx["bma_top"] else True
    if nome == "Linhas (blocos de 10)":
        return ctx["linhas_moda"] is not None and _linhas(dz) == ctx["linhas_moda"]
    if nome == "Régua (deslocamento)":
        refs = ctx["refs"]
        if len(refs) < spec.sorteadas:
            return None
        perto = sum(
            1 for n, ref in zip(sorted(dz), refs) if abs(int(n) - int(ref)) <= 3
        )
        return perto >= max(3, spec.sorteadas - 3)
    if nome == "Diagonais do volante":
        try:
            from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
            return bool(diagonais_na_aposta(dz, dmin=spec.dezena_min, dmax=spec.dezena_max))
        except Exception:
            return None
    if nome == "Distribuição dos finais":
        return ctx["du_moda"] is not None and len({int(n) % 10 for n in dz}) == ctx["du_moda"]
    if nome == "DD distintos (dezena)":
        dd, _du = _dd_du(dz)
        return ctx["dd_moda"] is not None and dd == ctx["dd_moda"]
    if nome == "DU distintos (unidade)":
        _dd, du = _dd_du(dz)
        return ctx["du_moda"] is not None and du == ctx["du_moda"]
    if nome == "Padrão inicial":
        if not ctx["padrao"]:
            return None
        atual = "-".join(str(int(n) // 10) for n in sorted(dz))
        return atual == ctx["padrao"]
    if nome == "Amplitude (máx − mín)":
        amp = max(dz) - min(dz)
        return ctx["amp_lo"] <= amp <= ctx["amp_hi"]
    if nome == "Mais frequentes no histórico":
        return len(set(dz) & ctx["quentes"]) >= spec.sorteadas // 2
    if nome == "Dezenas pendentes do ciclo":
        pend = ctx.get("pendentes") or set()
        if not pend:
            return None
        return len(set(int(n) for n in dz) & set(pend)) >= 1
    if nome == "Mais atrasadas":
        atras = ctx.get("atrasadas") or set()
        if not atras:
            return None
        return len(set(int(n) for n in dz) & set(atras)) >= 1
    if nome == "Mês da Sorte":
        if "meses_indicados" in ctx:
            return int(ctx.get("mes_num") or 0) in set(ctx.get("meses_indicados") or [])
        return bool(ctx.get("mes_nome"))
    sp = ctx.get("sp")
    if sp is None:
        return None
    if nome == "Primos":
        return None
    if nome == "Moldura":
        return None
    if nome == "Múltiplos de 3":
        return None
    if nome == "Fibonacci":
        return None
    return None


def _preparar_grupos(ctx: Dict[str, Any], itens: List[Dict[str, Any]], draws_fn) -> None:
    """A moda de primos, moldura, múltiplos e fibonacci sai dos mesmos sorteios."""
    sp = ctx.get("sp")
    if sp is None:
        return
    mapas = {
        "Primos": set(sp.primos),
        "Moldura": set(sp.moldura),
        "Múltiplos de 3": set(sp.multiplos_3),
        "Fibonacci": set(sp.fibonacci),
    }
    nomes = {i["criterio"] for i in itens}
    contagens: Dict[str, Dict[int, int]] = {k: {} for k in mapas if k in nomes}
    if not contagens:
        return
    for dz in draws_fn:
        for nome, conjunto in mapas.items():
            if nome not in contagens:
                continue
            q = _grupo_n(dz, conjunto)
            contagens[nome][q] = contagens[nome].get(q, 0) + 1
    ctx["grupo_moda"] = {
        nome: max(bag, key=bag.get) for nome, bag in contagens.items() if bag
    }
    ctx["grupos"] = mapas

    def grupo(nome: str, dz: Sequence[int]) -> Optional[bool]:
        moda = ctx["grupo_moda"].get(nome)
        if moda is None:
            return None
        return _grupo_n(dz, mapas[nome]) == moda

    ctx["grupo_fn"] = grupo


def _num(media: float) -> str:
    if abs(media - round(media)) < 0.05:
        return str(int(round(media)))
    return f"{media:.1f}"


def _leitura(nome: str, dz: Sequence[int], ctx: Dict[str, Any]) -> str:
    """O que esta aposta tem neste critério, no lugar da palavra cumprido."""
    spec: ResumoSpec = ctx["spec"]
    ordenada = sorted(int(n) for n in dz)
    if nome == "Pares × ímpares":
        pares = sum(1 for n in ordenada if n % 2 == 0)
        return f"{pares}P / {len(ordenada) - pares}I"
    if nome == "Repetidas do anterior":
        rep = sorted(set(ordenada) & set(ctx.get("prev") or []))
        return " ".join(_fmt(n) for n in rep) if rep else "0"
    if nome == "Soma":
        return str(sum(ordenada))
    if nome == "Média dos gaps":
        gs = gaps_de(ordenada)
        if not gs:
            return "—"
        return _num(sum(gs) / len(gs))
    if nome == "Finais iguais":
        bag: Dict[int, List[int]] = {}
        for n in ordenada:
            bag.setdefault(n % 10, []).append(n)
        return _texto_finais([v for v in bag.values() if len(v) >= 2])
    if nome == "Sequências":
        return _texto_sequencias(_sequencias(ordenada))
    if nome == "Faixas B/M/A":
        conta: Dict[str, int] = {}
        for n in ordenada:
            cod = faixa_de(n, spec)
            if cod:
                conta[cod] = conta.get(cod, 0) + 1
        return " ".join(f"{c}{conta.get(c, 0)}" for c, _lo, _hi, _lbl in spec.faixas)
    if nome == "Linhas (blocos de 10)":
        return str(_linhas(ordenada))
    if nome == "Régua (deslocamento)":
        refs = ctx.get("refs") or []
        if len(refs) < spec.sorteadas:
            return "—"
        posicoes = [
            {"posicao": i + 1, "dezena": n, "deslocamento": int(n) - int(ref)}
            for i, (n, ref) in enumerate(zip(ordenada, refs))
        ]
        return _texto_regua(posicoes)
    if nome == "Diagonais do volante":
        try:
            from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
            grupos = diagonais_na_aposta(ordenada, dmin=spec.dezena_min, dmax=spec.dezena_max)
        except Exception:
            return "—"
        return _texto_diagonais(grupos)
    if nome in ("Distribuição dos finais", "DU distintos (unidade)"):
        digs = sorted({n % 10 for n in ordenada})
        return f"{len(digs)} | {' '.join(str(d) for d in digs)}"
    if nome == "DD distintos (dezena)":
        digs = sorted({n // 10 for n in ordenada})
        return f"{len(digs)} | {' '.join(str(d) for d in digs)}"
    if nome == "Padrão inicial":
        return "-".join(str(n // 10) for n in ordenada)
    if nome == "Amplitude (máx − mín)":
        return str(max(ordenada) - min(ordenada)) if ordenada else "—"
    if nome == "Mais frequentes no histórico":
        hit = [n for n in ordenada if n in (ctx.get("quentes") or set())]
        return f"{len(hit)} | {' '.join(_fmt(n) for n in hit)}" if hit else "0"
    if nome == "Dezenas pendentes do ciclo":
        hit = [n for n in ordenada if n in (ctx.get("pendentes") or set())]
        return f"{len(hit)} | {' '.join(_fmt(n) for n in hit)}" if hit else "0"
    if nome == "Mais atrasadas":
        hit = [n for n in ordenada if n in (ctx.get("atrasadas") or set())]
        return f"{len(hit)} | {' '.join(_fmt(n) for n in hit)}" if hit else "0"
    if nome in ("Primos", "Moldura", "Múltiplos de 3", "Fibonacci"):
        conjunto = (ctx.get("grupos") or {}).get(nome) or set()
        nums = [n for n in ordenada if n in conjunto]
        return f"{len(nums)} | {' '.join(_fmt(n) for n in nums)}" if nums else "0"
    if nome == "Mês da Sorte":
        return _mes_curto(ctx.get("mes_nome") or "")
    return "—"


def criterios_de(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    painel = data.get("painel") or {}
    saida = []
    for cat in painel.get("categorias") or []:
        for item in cat.get("itens") or []:
            papel = _papel(item)
            saida.append({
                "criterio": item.get("criterio"),
                "categoria": cat.get("titulo"),
                "tipo": item.get("tipo") or "info",
                "uso": item.get("uso"),
                "papel": papel,
                "ligado": _ligado_padrao(item, papel),
                "historico": item.get("historico") or "",
                "regra": item.get("regra") or "",
            })
    return saida


_PACK: Dict[str, Dict[str, Any]] = {}
_QTD_MAX = 500


def _limites_aposta(modality_key: str, spec: ResumoSpec) -> tuple:
    """Mínimo e máximo de dezenas que a modalidade deixa marcar."""
    lo = int(spec.sorteadas)
    hi = int(spec.sorteadas)
    try:
        from configuracoes.config import MODALITIES
        aposta = (MODALITIES.get(modality_key) or {}).get("aposta") or {}
        if aposta.get("min") is not None:
            lo = int(aposta["min"])
        if aposta.get("max") is not None:
            hi = int(aposta["max"])
    except Exception:
        pass
    universo = int(spec.dezena_max) - int(spec.dezena_min) + 1
    hi = max(lo, min(hi, universo))
    lo = min(max(1, lo), hi)
    return lo, hi


def _avalia(nome: str, dz: Sequence[int], ctx: Dict[str, Any]) -> Optional[bool]:
    if nome in ("Primos", "Moldura", "Múltiplos de 3", "Fibonacci"):
        fn = ctx.get("grupo_fn")
        return fn(nome, dz) if fn else None
    return _cumpre(nome, dz, ctx)


def _montar_pack(modality_key: str) -> Dict[str, Any]:
    agora = time.time()
    hit = _PACK.get(modality_key)
    if hit and agora - float(hit.get("t") or 0) < 180:
        return hit
    if not tem_resumo_modalidade(modality_key):
        return {"erro": "Resumo Geral indisponível nesta modalidade."}
    spec = get_resumo_spec(modality_key)
    if spec.motor == "colunas":
        return {"erro": "Este gerador usa conjunto de dezenas."}
    data = ResumoModalidadeService.calcular(modality_key)
    if not data.get("sucesso"):
        return {"erro": data.get("erro") or "Não foi possível ler o Resumo Geral."}
    catalogo = criterios_de(data)
    sorteios = _carregar_sorteios(spec)
    ctx = _ctx(spec, data, sorteios)
    draws = []
    ocorrencias = []
    for s in sorteios:
        dz = sorted(int(x) for x in s["dezenas"])[: spec.sorteadas]
        if len(dz) != spec.sorteadas:
            continue
        draws.append(dz)
        ocorrencias.append({
            "concurso": int(s["concurso"]),
            "data": s.get("data") or "",
            "dz": frozenset(dz),
        })
    ctx["ocorrencias"] = ocorrencias
    _preparar_grupos(ctx, catalogo, draws)
    pack = {
        "t": agora,
        "spec": spec,
        "catalogo": catalogo,
        "ctx": ctx,
        "historico": ctx["historico"],
        "erro": "",
    }
    _PACK[modality_key] = pack
    return pack


def _pool_meses_indicados(modality_key: str) -> Optional[List[int]]:
    """Meses que não saíram nos últimos 10 concursos. None fora do Dia de Sorte."""
    if (modality_key or "").strip().lower() != "diadesorte":
        return None
    try:
        from diadesorte.meses_indicados import carregar_meses_indicados
        from models.sorteio_diadesorte import SorteioDiaDeSorte

        analise = carregar_meses_indicados(SorteioDiaDeSorte)
    except Exception:
        return []
    if not analise.get("sucesso"):
        return []
    return [int(n) for n in (analise.get("meses_indicados_nums") or [])]


def _distribuir_meses_indicados(
    pool: Sequence[int],
    quantidade: int,
    rng: random.Random,
    bloco: int = 10,
) -> List[int]:
    """Cada bloco de 10 recebe os meses indicados, em ordem aleatória.

    O bloco repete o grupo embaralhado até completar 10. Assim Mai, Ago, Jul
    e Dez, por exemplo, entram em cada dezena de apostas. O bloco incompleto
    no fim usa o mesmo grupo.
    """
    nums: List[int] = []
    vistos: Set[int] = set()
    for bruto in pool or []:
        try:
            n = int(bruto)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 12 and n not in vistos:
            vistos.add(n)
            nums.append(n)
    total = max(0, int(quantidade or 0))
    if not nums or total <= 0:
        return []
    tamanho = max(1, int(bloco or 10))
    out: List[int] = []
    while len(out) < total:
        falta = min(tamanho, total - len(out))
        pedaco: List[int] = []
        while len(pedaco) < falta:
            giro = list(nums)
            rng.shuffle(giro)
            pedaco.extend(giro)
        out.extend(pedaco[:falta])
    return out


def _ctx_com_mes(
    ctx: Dict[str, Any],
    mes: Optional[Dict[str, Any]],
    indicados: Optional[Sequence[int]],
) -> Dict[str, Any]:
    if indicados is None and not mes:
        return ctx
    novo = dict(ctx)
    if indicados is not None:
        novo["meses_indicados"] = {int(n) for n in indicados}
    if mes:
        novo["mes_num"] = int(mes["mes_num"])
        novo["mes_nome"] = mes.get("mes_nome") or ""
    return novo


def _normalizar(dezenas: Sequence[Any], spec: ResumoSpec) -> List[int]:
    saida = []
    vistos = set()
    for bruto in dezenas or []:
        try:
            n = int(bruto)
        except (TypeError, ValueError):
            continue
        if n < spec.dezena_min or n > spec.dezena_max or n in vistos:
            continue
        vistos.add(n)
        saida.append(n)
    saida.sort()
    return saida


def _ficha(
    dz: Sequence[int],
    catalogo: Sequence[Dict[str, Any]],
    ativos: Sequence[str],
    ctx: Dict[str, Any],
) -> Dict[str, Any]:
    por_nome = {c["criterio"]: c for c in catalogo}
    escolhidos = [por_nome[n] for n in ativos if n in por_nome and por_nome[n]["papel"] != "exibe"]
    nomes = {c["criterio"] for c in escolhidos}
    checklist = []
    acertos = []
    falhas = []
    pts = 0
    for c in catalogo:
        nome = c["criterio"]
        if c["papel"] == "exibe":
            checklist.append({"criterio": nome, "status": "info", "papel": "exibe", "valor": ""})
            continue
        if nome not in nomes:
            checklist.append({"criterio": nome, "status": "desligado", "papel": c["papel"], "valor": ""})
            continue
        ok = _avalia(nome, dz, ctx)
        status = "cumprido" if ok else ("nao_medido" if ok is None else "nao")
        if ok is True and c["papel"] == "corte":
            pts += 10
        elif ok is True and c["papel"] == "ponto":
            pts += 6
            acertos.append(nome)
        elif ok is False:
            falhas.append(nome)
        checklist.append({
            "criterio": nome,
            "status": status,
            "papel": c["papel"],
            "valor": _leitura(nome, dz, ctx),
        })
    mes_nome = ctx.get("mes_nome") or ""
    spec: ResumoSpec = ctx["spec"]
    alvo = frozenset(int(n) for n in dz)
    ocor = ctx.get("ocorrencias") or []
    if len(alvo) == spec.sorteadas:
        hits = [o for o in ocor if o["dz"] == alvo]
    elif len(alvo) > spec.sorteadas:
        hits = [o for o in ocor if o["dz"] <= alvo]
    else:
        hits = []
    ultima = hits[-1] if hits else {}
    return {
        "dezenas": [_fmt(n) for n in dz],
        "pontos": pts,
        "acertos": acertos,
        "falhas": falhas,
        "mes_nome": mes_nome,
        "mes": _mes_curto(mes_nome) if mes_nome else "",
        "mes_num": ctx.get("mes_num") or 0,
        "checklist": checklist,
        "qtd": len(dz),
        "ja_sorteada": bool(hits),
        "concurso_historico": ultima.get("concurso"),
        "data_historico": ultima.get("data") or "",
        "ocorrencias_historico": len(hits),
    }


def criterios_para_tela(modality_key: str) -> Dict[str, Any]:
    if not tem_resumo_modalidade(modality_key):
        return {"sucesso": False, "erro": "Resumo Geral indisponível nesta modalidade."}
    data = ResumoModalidadeService.calcular(modality_key)
    if not data.get("sucesso"):
        return data
    spec = get_resumo_spec(modality_key)
    lo, hi = _limites_aposta(modality_key, spec)
    return {
        "sucesso": True,
        "criterios": criterios_de(data),
        "meta": data.get("meta") or {},
        "dezenas_min": lo,
        "dezenas_max": hi,
        "dezenas_padrao": int(spec.sorteadas),
        "quantidade_max": _QTD_MAX,
        "universo_min": int(spec.dezena_min),
        "universo_max": int(spec.dezena_max),
        "volante_cols": 5 if modality_key == "lotofacil" else 10,
    }


def gerar_resumo_geral(
    modality_key: str,
    ativos: Sequence[str],
    quantidade: int = 10,
    dezenas_por_aposta: int = 0,
) -> Dict[str, Any]:
    pack = _montar_pack(modality_key)
    if pack.get("erro"):
        return {"sucesso": False, "erro": pack["erro"]}
    spec = pack["spec"]
    catalogo = pack["catalogo"]
    ctx = pack["ctx"]
    por_nome = {c["criterio"]: c for c in catalogo}
    escolhidos = [por_nome[n] for n in ativos if n in por_nome and por_nome[n]["papel"] != "exibe"]
    if not escolhidos:
        return {"sucesso": False, "erro": "Marque pelo menos um critério de corte ou de pontuação."}
    cortes = [c for c in escolhidos if c["papel"] == "corte"]
    pontos = [c for c in escolhidos if c["papel"] == "ponto"]

    def avalia(nome: str, dz: Sequence[int]) -> Optional[bool]:
        return _avalia(nome, dz, ctx)

    lo, hi = _limites_aposta(modality_key, spec)
    try:
        k = int(dezenas_por_aposta or spec.sorteadas)
    except (TypeError, ValueError):
        k = int(spec.sorteadas)
    k = max(lo, min(k, hi))
    rng = random.Random()
    ranked: List[Dict[str, Any]] = []
    vistos: Set[frozenset] = set()
    qtd = max(1, min(int(quantidade or 10), _QTD_MAX))
    teto = min(20000, max(4000, qtd * 4))
    tentativas = min(120000, max(25000, qtd * 40))
    universo = list(range(spec.dezena_min, spec.dezena_max + 1))
    prev = {int(n) for n in (ctx.get("prev") or set())}
    exige_repetidas = any(c["criterio"] == "Repetidas do anterior" for c in cortes)
    livre = [n for n in universo if n not in prev] if (prev and not exige_repetidas) else universo

    def completar(nucleo: Sequence[int]) -> List[int]:
        base = [int(n) for n in nucleo]
        falta = k - len(base)
        if falta <= 0:
            return sorted(base[:k])
        resto = [n for n in livre if n not in set(base)]
        if falta > len(resto):
            return sorted(base)
        return sorted(base + rng.sample(resto, falta))

    for _ in range(tentativas):
        if len(livre) < spec.sorteadas:
            break
        nucleo = sorted(rng.sample(livre, spec.sorteadas))
        if _ja_sorteada(nucleo, pack["historico"], spec.motor):
            continue
        dz = completar(nucleo)
        if any(avalia(c["criterio"], dz) is False for c in cortes):
            continue
        if prev and not exige_repetidas and (set(dz) & prev):
            continue
        chave = frozenset(dz)
        if chave in vistos:
            continue
        vistos.add(chave)
        pts = 10 * len(cortes)
        for c in pontos:
            ok = avalia(c["criterio"], dz)
            if ok is True:
                pts += 6
        ranked.append({"nums": dz, "pontos": pts})
        if len(ranked) >= teto:
            break
    ranked.sort(key=lambda r: -r["pontos"])
    limite = max(2, k - 3)
    escolhidos_jogos: List[Dict[str, Any]] = []
    for row in ranked:
        dzs = set(row["nums"])
        if any(len(dzs & set(o["nums"])) > limite for o in escolhidos_jogos):
            continue
        escolhidos_jogos.append(row)
        if len(escolhidos_jogos) >= qtd:
            break
    if len(escolhidos_jogos) < qtd:
        ja = {tuple(r["nums"]) for r in escolhidos_jogos}
        for row in ranked:
            if tuple(row["nums"]) in ja:
                continue
            escolhidos_jogos.append(row)
            ja.add(tuple(row["nums"]))
            if len(escolhidos_jogos) >= qtd:
                break
    if not escolhidos_jogos:
        return {
            "sucesso": False,
            "erro": "Nenhuma combinação passou nos cortes marcados. Desmarque um corte e tente de novo.",
        }
    indicados = _pool_meses_indicados(modality_key)
    meses_lote = (
        _distribuir_meses_indicados(indicados, len(escolhidos_jogos), rng)
        if indicados
        else []
    )
    item_mes = None
    if meses_lote:
        from diadesorte.meses_indicados import _item_mes
        item_mes = _item_mes
    apostas = []
    for i, row in enumerate(escolhidos_jogos, start=1):
        mes = item_mes(meses_lote[i - 1]) if item_mes else None
        ctx_ap = _ctx_com_mes(ctx, mes, indicados)
        ficha = _ficha(row["nums"], catalogo, ativos, ctx_ap)
        ficha["ordem"] = i
        apostas.append(ficha)
    return {
        "sucesso": True,
        "quantidade": len(apostas),
        "examinadas": len(ranked),
        "cortes": [c["criterio"] for c in cortes],
        "pontos": [c["criterio"] for c in pontos],
        "apostas": apostas,
        "aviso": "A nota mede aderência ao costume histórico, não chance de acerto.",
        "dezenas_por_aposta": k,
        "pedidas": qtd,
    }


def avaliar_resumo_geral(
    modality_key: str,
    dezenas: Sequence[Any],
    ativos: Sequence[str],
    mes_num: Any = None,
) -> Dict[str, Any]:
    pack = _montar_pack(modality_key)
    if pack.get("erro"):
        return {"sucesso": False, "erro": pack["erro"]}
    spec: ResumoSpec = pack["spec"]
    lo, hi = _limites_aposta(modality_key, spec)
    dz = _normalizar(dezenas, spec)
    if len(dz) < lo:
        return {"sucesso": False, "erro": f"Mínimo de {lo} dezenas."}
    if len(dz) > hi:
        return {"sucesso": False, "erro": f"Máximo de {hi} dezenas nesta modalidade."}
    indicados = _pool_meses_indicados(modality_key)
    mes = None
    try:
        mn = int(mes_num or 0)
    except (TypeError, ValueError):
        mn = 0
    if 1 <= mn <= 12:
        from diadesorte.meses_indicados import _item_mes
        mes = _item_mes(mn)
    ctx_ap = _ctx_com_mes(pack["ctx"], mes, indicados)
    ficha = _ficha(dz, pack["catalogo"], ativos, ctx_ap)
    ficha["sucesso"] = True
    ficha["bolao"] = len(dz) > spec.sorteadas
    return ficha
