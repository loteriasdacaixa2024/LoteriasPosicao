# -*- coding: utf-8 -*-
"""Gerador Escolha/Tubular — apostas a partir do perfil de um concurso (Escolha)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from analise_escolha_visual.enriquecimento.motor import conjuntos_concurso
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos
from geradores_elite.modality_config import MODALITIES


def tem_gerador_escolha_tubular(modality_key: str) -> bool:
    # Super Sete (colunas) fica para depois
    if modality_key == "supersete":
        return False
    return tem_analise_estudos(modality_key) and modality_key in MODALITIES


def _tem_sequencia(nums: Sequence[int]) -> bool:
    s = sorted(int(x) for x in nums)
    return any(s[i + 1] - s[i] == 1 for i in range(len(s) - 1))


def _max_run_consecutiva(nums: Sequence[int]) -> int:
    s = sorted(int(x) for x in nums)
    if not s:
        return 0
    best = cur = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1] + 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def _tem_finais_iguais(nums: Sequence[int]) -> bool:
    seen: Dict[int, int] = {}
    for n in nums:
        d = int(n) % 10
        seen[d] = seen.get(d, 0) + 1
        if seen[d] > 1:
            return True
    return False


def _digitos_unicos(nums: Sequence[int]) -> int:
    return len({int(d) for n in nums for d in f"{int(n):02d}"})


def _perfil_de_conjuntos(det: Dict[str, Any]) -> Dict[str, Any]:
    b = det.get("basicos") or {}
    cruz = det.get("cruzamentos") or []
    return {
        "pares": int((b.get("pares") or {}).get("quantidade") or 0),
        "impares": int((b.get("impares") or {}).get("quantidade") or 0),
        "repetidos": int((b.get("repetidos") or {}).get("quantidade") or 0),
        "sequencias_qtd": int((b.get("sequencias") or {}).get("quantidade") or 0),
        "sequencias_grupos": int(((b.get("sequencias") or {}).get("detalhe") or {}).get("qtd_grupos") or 0),
        "finais_qtd": int((b.get("finais") or {}).get("quantidade") or 0),
        "quer_sequencia": int((b.get("sequencias") or {}).get("quantidade") or 0) > 0,
        "quer_finais": int((b.get("finais") or {}).get("quantidade") or 0) > 0,
        "basicos": b,
        "cruzamentos": cruz,
        "soma": int(det.get("soma") or 0),
        "padroes_resumo": {
            "pares": f"{(b.get('pares') or {}).get('quantidade', 0)} ({', '.join(f'{d:02d}' for d in (b.get('pares') or {}).get('dezenas') or [])})",
            "impares": f"{(b.get('impares') or {}).get('quantidade', 0)} ({', '.join(f'{d:02d}' for d in (b.get('impares') or {}).get('dezenas') or [])})",
            "repetidos": f"{(b.get('repetidos') or {}).get('quantidade', 0)} ({', '.join(f'{d:02d}' for d in (b.get('repetidos') or {}).get('dezenas') or [])})",
            "sequencias": f"{(b.get('sequencias') or {}).get('quantidade', 0)}",
            "finais": f"{(b.get('finais') or {}).get('quantidade', 0)} ({', '.join(f'{d:02d}' for d in (b.get('finais') or {}).get('dezenas') or [])})",
        },
    }


def _carregar_rows(modality_key: str, base: str):
    Base = make_estudos_base(modality_key)
    rows = Base.carregar_sorteios_asc(base_estatistica=base, janela=0)
    return Base, rows


def _ancora_info(Base, rows) -> Dict[str, Any]:
    """Último / penúltimo / antepenúltimo com padrão inicial (ex.: 0 0 1 1 2 2 2)."""
    from geradores_elite.construtor.construcoes_core import padrao_inicial_de

    def _um(idx: int) -> Optional[Dict[str, Any]]:
        if idx < 0 or idx >= len(rows):
            return None
        r = rows[idx]
        dz = [int(x) for x in Base.dezenas_ordem(r)]
        return {
            "concurso": int(r.concurso),
            "dezenas": dz,
            "padrao": padrao_inicial_de(dz) if dz else "",
        }

    n = len(rows)
    return {
        "ultimo": _um(n - 1),
        "penultimo": _um(n - 2),
        "antepenultimo": _um(n - 3),
    }


def contexto_gerador(
    modality_key: str,
    *,
    janela: int = 0,
    base: str = "geral",
    concurso_ref: Optional[int] = None,
) -> Dict[str, Any]:
    if not tem_gerador_escolha_tubular(modality_key):
        return {"sucesso": False, "erro": "Indisponível para esta modalidade."}

    cfg = get_estudos_config(modality_key)
    mod = MODALITIES[modality_key]
    Base, rows = _carregar_rows(modality_key, base)
    if not rows:
        return {"sucesso": False, "erro": "Sem concursos na base."}

    # lista recente para o select (mais novos primeiro)
    lista = []
    for r in reversed(rows[-80:]):
        lista.append({
            "concurso": int(r.concurso),
            "data": getattr(r, "data", "") or "",
            "dezenas": [int(x) for x in Base.dezenas_ordem(r)],
        })

    # índice do concurso de referência no histórico ascendente
    idx_ref = len(rows) - 1
    if concurso_ref is not None:
        for i, r in enumerate(rows):
            if int(r.concurso) == int(concurso_ref):
                idx_ref = i
                break
    row_ref = rows[idx_ref]
    nums_ref = [int(x) for x in Base.dezenas_ordem(row_ref)]
    nums_ant = [int(x) for x in Base.dezenas_ordem(rows[idx_ref - 1])] if idx_ref > 0 else []
    # pool de repetidos para a PRÓXIMA aposta = dezenas do concurso ref (último sorteado)
    # (apostando no próximo, "repetidos" vêm do último oficial)
    ultimo_oficial = [int(x) for x in Base.dezenas_ordem(rows[-1])]
    det = conjuntos_concurso(nums_ref, nums_ant)
    perfil = _perfil_de_conjuntos(det)
    ancoras = _ancora_info(Base, rows)
    padroes_hist = []
    for r in rows[-250:]:
        dz = [int(x) for x in Base.dezenas_ordem(r)]
        if dz:
            from geradores_elite.construtor.construcoes_core import padrao_inicial_de
            padroes_hist.append(padrao_inicial_de(dz))

    return {
        "sucesso": True,
        "modality_key": modality_key,
        "modality_nome": cfg["nome"],
        "dezena_min": mod["dezena_min"],
        "dezena_max": mod["dezena_max"],
        "pick_default": mod["pick_default"],
        "pick_min": mod["pick_min"],
        "pick_max": mod["pick_max"],
        "sorteadas": mod["sorteadas"],
        "extra_mes": bool(cfg.get("extra_mes")),
        "extra_time": bool(cfg.get("extra_time")),
        "extra_trevo": bool(cfg.get("extra_trevo")),
        "volante_cols": int(cfg.get("volante_cols") or 10),
        "janela": janela,
        "base": base,
        "concursos": lista,
        "concurso_ref": int(row_ref.concurso),
        "concurso_ref_data": getattr(row_ref, "data", "") or "",
        "dezenas_ref": nums_ref,
        "perfil": perfil,
        "ancoras": ancoras,
        "padroes_historicos": padroes_hist,
        "ultimo_sorteio": {
            "concurso": int(rows[-1].concurso),
            "dezenas": ultimo_oficial,
        },
        "pool_repetidos": ultimo_oficial,
        "analise_links": {
            "escolha": "/analise/escolha-visual/",
            "tubular": "/analise/analise-tubular/",
        },
        "modo": "perfil_concurso",
        "explicacao": (
            "Cada aposta tenta reproduzir, numa única jogada, o perfil estrutural "
            "do concurso de referência (pares/ímpares, sequência, finais iguais, "
            "qtd de repetidos do último sorteio)."
        ),
    }


def _pick_one(rng: random.Random, candidatos: List[int], proibidos: Set[int]) -> Optional[int]:
    livres = [x for x in candidatos if x not in proibidos]
    if not livres:
        return None
    return rng.choice(livres)


def _construir_aposta(
    rng: random.Random,
    *,
    pick_n: int,
    dmin: int,
    dmax: int,
    perfil: Dict[str, Any],
    pool_rep: List[int],
    usar_pi: bool,
    usar_seq: bool,
    usar_finais: bool,
    usar_rep: bool,
    padrao_digs: Optional[Sequence[int]] = None,
    dezenas_altas: bool = False,
    max_run_permitida: Optional[int] = None,
) -> Optional[List[int]]:
    """Monta 1 aposta com TODOS os atributos do perfil na mesma jogada."""
    from geradores_elite.construtor.construcoes_core import (
        _montar_por_padrao,
        padrao_inicial_de,
        padrao_viavel,
    )

    escolhidos: Set[int] = set()
    universo = list(range(dmin, dmax + 1))
    if dezenas_altas:
        universo = [x for x in universo if x >= 10]

    # Se há padrão inicial forçado, monta a aposta inteira por ele
    if padrao_digs is not None:
        digs = [int(x) for x in padrao_digs]
        if len(digs) != pick_n:
            return None
        if dezenas_altas and any(d == 0 for d in digs):
            return None
        if not padrao_viavel(digs, universo):
            return None
        nums = _montar_por_padrao(universo, digs, rng)
        if not nums or len(nums) != pick_n:
            return None
        if dezenas_altas and min(nums) < 10:
            return None
        # Padrão gerado deve bater com o padrão real usado (sem improvisar)
        alvo_pstr = " ".join(str(int(x)) for x in digs)
        if padrao_inicial_de(nums) != alvo_pstr:
            return None
        # Validação dura dos atributos pedidos
        alvo_pares = int(perfil.get("pares") or 0) if usar_pi else None
        alvo_rep = int(perfil.get("repetidos") or 0) if usar_rep else 0
        quer_seq = bool(perfil.get("quer_sequencia")) if usar_seq else False
        quer_fin = bool(perfil.get("quer_finais")) if usar_finais else False
        if usar_pi and alvo_pares is not None:
            if sum(1 for n in nums if n % 2 == 0) != alvo_pares:
                return None
        if usar_seq and quer_seq and not _tem_sequencia(nums):
            return None
        if usar_finais and quer_fin and not _tem_finais_iguais(nums):
            return None
        if usar_rep and alvo_rep > 0:
            reps = sum(1 for n in nums if n in set(pool_rep))
            if reps != alvo_rep:
                return None
        if max_run_permitida is not None and _max_run_consecutiva(nums) > int(max_run_permitida):
            return None
        return nums

    # Sem padrão histórico: não improvisar — o gerador Escolha/Tubular exige padrão real
    return None


def _avaliar_aposta(nums: List[int], pool_rep: List[int], perfil: Dict[str, Any]) -> Dict[str, Any]:
    from geradores_elite.construtor.construcoes_core import padrao_inicial_de

    pares = sum(1 for n in nums if n % 2 == 0)
    det = conjuntos_concurso(nums, pool_rep)
    return {
        "dezenas": nums,
        "soma": sum(nums),
        "pares": pares,
        "impares": len(nums) - pares,
        "tem_sequencia": _tem_sequencia(nums),
        "tem_finais_iguais": _tem_finais_iguais(nums),
        "digitos_unicos": _digitos_unicos(nums),
        "padrao_inicial": padrao_inicial_de(nums),
        "repetidas_ultimo": [n for n in nums if n in set(pool_rep)],
        "basicos": det.get("basicos"),
        "cruzamentos": [
            {
                "label": c["label"],
                "quantidade": c["quantidade"],
                "dezenas": c["dezenas"],
            }
            for c in (det.get("cruzamentos") or [])
            if c.get("quantidade")
        ],
        "perfil_ok": {
            "pares": pares == int(perfil.get("pares") or -1),
            "sequencia": (not perfil.get("quer_sequencia")) or _tem_sequencia(nums),
            "finais": (not perfil.get("quer_finais")) or _tem_finais_iguais(nums),
            "repetidos": len([n for n in nums if n in set(pool_rep)]) == int(perfil.get("repetidos") or 0),
        },
    }


def gerar_apostas(
    modality_key: str,
    *,
    quantidade: int = 10,
    pick: Optional[int] = None,
    janela: int = 0,
    base: str = "geral",
    concurso_ref: Optional[int] = None,
    usar_pares_impares: bool = True,
    usar_soma: bool = True,  # mantido na assinatura; soma vira alvo suave opcional
    usar_sequencia: bool = True,
    usar_finais: bool = True,
    usar_repetidos: bool = True,
    usar_digitos: bool = True,
    mes_num: Any = None,
    seed: Optional[int] = None,
    ancora_padrao: Optional[str] = None,
    dezenas_altas: bool = False,
) -> Dict[str, Any]:
    from geradores_elite.construtor.construcoes_core import (
        parse_padrao,
        selecionar_padroes_lote,
    )

    ancora = (ancora_padrao or "").strip().lower() or None
    if ancora and ancora not in ("ultimo", "penultimo", "antepenultimo"):
        ancora = None

    # Pré-contexto para resolver âncora → concurso_ref
    ctx0 = contexto_gerador(modality_key, janela=janela, base=base, concurso_ref=concurso_ref)
    if not ctx0.get("sucesso"):
        return ctx0

    if ancora:
        ref_a = (ctx0.get("ancoras") or {}).get(ancora)
        if not ref_a or not ref_a.get("concurso"):
            return {"sucesso": False, "erro": f"Âncora '{ancora}' indisponível (histórico insuficiente)."}
        concurso_ref = int(ref_a["concurso"])

    ctx = contexto_gerador(
        modality_key, janela=janela, base=base, concurso_ref=concurso_ref,
    )
    if not ctx.get("sucesso"):
        return ctx

    pick_n = int(pick if pick is not None else ctx["pick_default"])
    pick_n = max(int(ctx["pick_min"]), min(int(ctx["pick_max"]), pick_n))
    qtd = max(1, min(int(quantidade or 10), 500))
    perfil = ctx["perfil"]
    pool_rep = list(ctx.get("pool_repetidos") or [])
    dmin = int(ctx["dezena_min"])
    dmax = int(ctx["dezena_max"])
    dezenas_ref = list(ctx.get("dezenas_ref") or [])
    # Teto de sequência = o que o concurso de referência (análise) realmente teve
    max_run_ref = _max_run_consecutiva(dezenas_ref) if dezenas_ref else None
    if max_run_ref is not None and max_run_ref < 1:
        max_run_ref = 1
    sorteadas_oficial = int(ctx.get("sorteadas") or pick_n)
    # Ajuste: se pick != tamanho do perfil original, escala paridade proporcional
    sorteadas_ref = int(perfil.get("pares") or 0) + int(perfil.get("impares") or 0)
    if usar_pares_impares and sorteadas_ref and pick_n != sorteadas_ref:
        ratio = pick_n / float(sorteadas_ref)
        perfil = dict(perfil)
        perfil["pares"] = max(0, min(pick_n, int(round(int(perfil["pares"]) * ratio))))
        perfil["impares"] = pick_n - int(perfil["pares"])
        # repetidos não pode passar do pick
        perfil["repetidos"] = min(int(perfil.get("repetidos") or 0), pick_n)

    rng = random.Random(seed)
    universo = list(range(dmin, dmax + 1))
    if dezenas_altas:
        universo = [x for x in universo if x >= 10]

    # Lista de padrões por aposta — SOMENTE padrões de sorteios reais (Escolha Visual)
    padroes_por_aposta: List[Optional[List[int]]] = [None] * qtd
    padrao_label = "mix"
    if ancora:
        ref_a = (ctx.get("ancoras") or {}).get(ancora) or {}
        digs = parse_padrao(ref_a.get("padrao") or "")
        if len(digs) > pick_n:
            digs = digs[:pick_n]
        if len(digs) != pick_n:
            return {
                "sucesso": False,
                "erro": (
                    f"Padrão da âncora ({ref_a.get('padrao') or '—'}) tem {len(digs)} posições; "
                    f"use {len(digs)} dezenas (sorteio oficial) ou outra âncora."
                ),
            }
        if dezenas_altas and any(d == 0 for d in digs):
            return {
                "sucesso": False,
                "erro": (
                    f"Padrão '{ref_a.get('padrao')}' exige dezena < 10, "
                    "incompatível com Dezenas altas (≥10)."
                ),
            }
        padroes_por_aposta = [digs] * qtd
        padrao_label = ref_a.get("padrao") or ancora
        if ref_a.get("dezenas"):
            max_run_ref = _max_run_consecutiva(ref_a["dezenas"])
    else:
        hist = list(ctx.get("padroes_historicos") or [])
        if dezenas_altas:
            hist = [p for p in hist if 0 not in parse_padrao(p)]
        hist_mesmo_tamanho = [p for p in hist if len(parse_padrao(p)) == pick_n]
        if not hist_mesmo_tamanho:
            return {
                "sucesso": False,
                "erro": (
                    f"Não há padrões de sorteios reais com {pick_n} dezenas. "
                    f"O sorteio oficial desta modalidade usa {sorteadas_oficial} dezenas — "
                    f"ajuste o campo Dezenas para {sorteadas_oficial} para usar a Escolha Visual."
                ),
            }
        escolhidos = selecionar_padroes_lote(
            hist_mesmo_tamanho, universo, pick_n, qtd, rng, permitir_sinteticos=False,
        )
        if not escolhidos:
            return {
                "sucesso": False,
                "erro": (
                    "Não foi possível obter padrões viáveis a partir dos sorteios reais "
                    "(Escolha Visual). Tente outro concurso de referência ou desmarque alguma exigência."
                ),
            }
        base_p = list(escolhidos)
        i = 0
        while len(escolhidos) < qtd:
            escolhidos.append(base_p[i % len(base_p)])
            i += 1
        padroes_por_aposta = escolhidos[:qtd]

    apostas: List[Dict[str, Any]] = []
    vistos: Set[Tuple[int, ...]] = set()
    tentativas = max(qtd * 400, 800)
    idx_alvo = 0

    for _ in range(tentativas):
        if len(apostas) >= qtd:
            break
        pad_digs = padroes_por_aposta[min(idx_alvo, qtd - 1)] if padroes_por_aposta else None
        if not pad_digs:
            break
        nums = _construir_aposta(
            rng,
            pick_n=pick_n,
            dmin=dmin,
            dmax=dmax,
            perfil=perfil,
            pool_rep=pool_rep,
            usar_pi=usar_pares_impares,
            usar_seq=usar_sequencia,
            usar_finais=usar_finais,
            usar_rep=usar_repetidos,
            padrao_digs=pad_digs,
            dezenas_altas=bool(dezenas_altas),
            max_run_permitida=max_run_ref,
        )
        if not nums:
            # Nunca improvisar sem padrão — só tenta de novo com o mesmo padrão real
            continue
        key = tuple(nums)
        if key in vistos:
            continue
        vistos.add(key)
        item = _avaliar_aposta(nums, pool_rep, perfil)
        item["ancora_padrao"] = ancora or "mix"
        item["padrao_fonte"] = "sorteio_real"
        # score: quanto mais atributos ok, melhor; bônus leve por soma próxima
        ok = item["perfil_ok"]
        sc = 10.0 * sum(1 for v in ok.values() if v)
        if usar_soma and perfil.get("soma"):
            sc -= abs(item["soma"] - int(perfil["soma"])) * 0.05
        item["score"] = round(sc, 2)
        apostas.append(item)
        idx_alvo += 1

    if not apostas:
        return {
            "sucesso": False,
            "erro": (
                "Não foi possível montar apostas só com padrões/perfil dos sorteios reais "
                "(Escolha Visual). Afrouxe uma exigência ou mude o concurso de referência."
            ),
        }

    apostas.sort(key=lambda a: a["score"], reverse=True)
    apostas = apostas[:qtd]
    for i, a in enumerate(apostas, start=1):
        a["indice"] = i

    mes_criterio = mes_num
    mes_resolvido = None
    if mes_criterio not in (None, "", 0, "0") and ctx.get("extra_mes"):
        try:
            from diadesorte.mes_sorte_select import (
                MESES_ABREV,
                MESES_NOME,
                eh_criterio_aleatorio,
                resolver_meses_para_lote,
            )
            meses_lote = resolver_meses_para_lote(mes_criterio, len(apostas))
            for a, mn in zip(apostas, meses_lote):
                a["mes_num"] = int(mn)
                a["mes_abrev"] = MESES_ABREV.get(int(mn), "")
                a["mes_nome"] = MESES_NOME.get(int(mn), "")
            if meses_lote:
                mes_resolvido = int(meses_lote[0]) if not eh_criterio_aleatorio(mes_criterio) else None
        except Exception:
            pass

    # Time do Coração (Timemania) — automático (sem select +Atrasado/+Frequente; isso é só Mês)
    if ctx.get("extra_time") and apostas:
        try:
            catalog: List[Dict[str, Any]] = []
            try:
                from models.sorteio_timemania import TIMES_DO_CORACAO
                if isinstance(TIMES_DO_CORACAO, dict):
                    catalog = [
                        {"num": int(k), "nome": str(v)}
                        for k, v in TIMES_DO_CORACAO.items()
                    ]
            except Exception:
                catalog = []
            if not catalog:
                catalog = [{"num": i, "nome": f"Time {i}"} for i in range(1, 81)]
            for a in apostas:
                escolha = rng.choice(catalog)
                tnum = int(escolha.get("num") or 1)
                tnome = escolha.get("nome") or f"Time {tnum}"
                a["time_num"] = tnum
                a["time_nome"] = tnome
                a["extras"] = dict(a.get("extras") or {}, time_num=tnum, time_nome=tnome)
        except Exception:
            for a in apostas:
                a.setdefault("time_num", 1)
                a.setdefault("time_nome", "Time")

    # Trevos (+Milionária) — 2 trevos por aposta
    if ctx.get("extra_trevo") and apostas:
        try:
            from geradores_elite.engine_final_core import _pick_extra_trevos
            meta = {}
            try:
                mod_path, cls_name, _ = MODALITIES[modality_key]["service_import"]
                svc_mod = __import__(mod_path, fromlist=[cls_name])
                Svc = getattr(svc_mod, cls_name)
                if hasattr(Svc, "analise_geral"):
                    raw = Svc.analise_geral() or {}
                    meta["trevos_stats"] = raw.get("dados_trevos") or []
            except Exception:
                pass
            qtd_t = int((MODALITIES.get(modality_key) or {}).get("trevo_pick") or 2)
            for a in apostas:
                trevos = _pick_extra_trevos(meta, qtd_t)
                a["trevos"] = trevos
                a["extras"] = dict(a.get("extras") or {}, trevos=trevos)
        except Exception:
            import random as _rnd
            for a in apostas:
                a["trevos"] = sorted(_rnd.sample(range(1, 7), 2))

    return {
        "sucesso": True,
        "ok": True,
        "modality_key": modality_key,
        "quantidade": len(apostas),
        "pick": pick_n,
        "janela": janela,
        "base": base,
        "modo": "perfil_concurso",
        "concurso_ref": ctx.get("concurso_ref"),
        "perfil": perfil,
        "ancora_padrao": ancora or "",
        "dezenas_altas": bool(dezenas_altas),
        "padrao_usado": padrao_label,
        "alvo": {"padroes_resumo": perfil.get("padroes_resumo"), "mes_sugerido": None},
        "mes_num": mes_resolvido,
        "mes_criterio": str(mes_criterio) if mes_criterio not in (None, "") else None,
        "apostas": apostas,
        "contexto": {
            "padroes_resumo": perfil.get("padroes_resumo"),
            "ultimo_sorteio": ctx.get("ultimo_sorteio"),
            "concurso_ref": ctx.get("concurso_ref"),
            "ancoras": ctx.get("ancoras"),
            "explicacao": ctx.get("explicacao"),
        },
    }
