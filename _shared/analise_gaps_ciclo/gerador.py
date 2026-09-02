# -*- coding: utf-8 -*-
"""Um gerador — Sessão 1 (gaps) e/ou Sessão 2 (inicial + ciclo)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from analise_gaps_ciclo.core import ciclos_perfil, montar_por_ciclos, norm_leitura, padrao_gaps, parse_padrao_gaps
from analise_gaps_ciclo.specs import get_gaps_ciclo_spec


def _fmt(n: int, pad: int) -> str:
    return str(int(n)).zfill(int(pad))


def _montar_item(i: int, dezenas: Sequence[int], origem: str, pad: int, ciclos: Sequence[int]) -> Dict[str, Any]:
    dz = [int(x) for x in dezenas]
    return {
        "numero": i,
        "dezenas": dz,
        "dezenas_fmt": " ".join(_fmt(d, pad) for d in dz),
        "origem": origem,
        "ciclos": list(ciclos),
        "padrao_gaps": padrao_gaps(ciclos),
        "inicial": dz[0] if dz else None,
    }


def _analisar_gaps(modality_key, **kwargs):
    from analise_gaps_ciclo.service import analisar_gaps
    return analisar_gaps(modality_key, **kwargs)


def gerar_apostas(
    modality_key: str,
    *,
    sessao1: bool = True,
    sessao2: bool = True,
    inicial: Optional[int] = None,
    perfil: str = "ultimo",
    padrao: Optional[str] = None,
    padroes: Optional[Sequence[str]] = None,
    janela: int = 0,
    base: str = "geral",
    quantidade: int = 10,
    mes_num=None,
    leitura: str = "ambos",
) -> Dict[str, Any]:
    spec = get_gaps_ciclo_spec(modality_key)
    pad = int(spec["pad_width"])
    k = int(spec["sorteadas"])
    dmin, dmax = int(spec["dezena_min"]), int(spec["dezena_max"])
    qtd = max(1, min(int(quantidade or spec["qtd_apostas_default"]), int(spec["qtd_apostas_max"])))
    s1, s2 = bool(sessao1), bool(sessao2)
    lei = norm_leitura(leitura)
    if not s1 and not s2:
        return {
            "sucesso": False, "ok": False,
            "erro": "Ative a Sessão 1 (Gaps), a Sessão 2 (Inicial + Ciclo) ou as duas.",
        }

    permitidas = list(spec["iniciais_permitidas"])
    ini_user = None
    if inicial not in (None, ""):
        try:
            ini_user = int(inicial)
        except (TypeError, ValueError):
            return {"sucesso": False, "ok": False, "erro": "Número inicial inválido."}
        if ini_user not in permitidas:
            return {
                "sucesso": False, "ok": False,
                "erro": (
                    f"Inicial {_fmt(ini_user, pad)} não permitida. "
                    f"Use {_fmt(spec['inicial_min'], pad)}–{_fmt(spec['inicial_max'], pad)}."
                ),
            }

    if s2 and ini_user is None:
        return {
            "sucesso": False, "ok": False,
            "erro": "Sessão 2 ligada: escolha o número inicial.",
        }

    gaps_info = _analisar_gaps(modality_key, janela=janela, base=base)
    if not gaps_info.get("sucesso"):
        return {"sucesso": False, "ok": False, "erro": gaps_info.get("erro") or "Falha na análise de gaps."}

    ciclos_lista: List[List[int]] = []

    def _push(g: Sequence[int], front: bool = False) -> None:
        seq = [int(x) for x in g]
        if len(seq) != k - 1 or seq in ciclos_lista:
            return
        if front:
            ciclos_lista.insert(0, seq)
        else:
            ciclos_lista.append(seq)

    if s1:
        if padroes:
            for raw in padroes:
                _push(parse_padrao_gaps(raw))
        if padrao:
            _push(parse_padrao_gaps(padrao), front=True)
        if lei == "sorteio":
            fonte_padroes = gaps_info.get("top_padroes_sorteio") or []
        elif lei == "ambos":
            fonte_padroes = gaps_info.get("ranking_comparativo") or gaps_info.get("top_padroes") or []
        else:
            fonte_padroes = gaps_info.get("top_padroes") or []
        for t in fonte_padroes:
            _push(t.get("gaps") or parse_padrao_gaps(t.get("padrao") or ""))
    elif s2:
        _push(ciclos_perfil(gaps_info, perfil=perfil, padrao=padrao, leitura=lei), front=True)

    if not ciclos_lista:
        return {"sucesso": False, "ok": False, "erro": "Não há perfil de ciclo/gaps viável na janela."}

    if s2:
        iniciais = [ini_user]
    elif ini_user is not None:
        iniciais = [ini_user]
    else:
        iniciais = list(permitidas)

    origem = "gaps+ciclo" if (s1 and s2) else ("ciclo" if s2 else "gaps")
    apostas: List[Dict[str, Any]] = []
    vistos = set()
    for ini in iniciais:
        for ciclos in ciclos_lista:
            if len(apostas) >= qtd:
                break
            ap = montar_por_ciclos(ini, ciclos, dezena_min=dmin, dezena_max=dmax)
            if not ap or len(ap) != k:
                continue
            key = tuple(ap)
            if key in vistos:
                continue
            vistos.add(key)
            apostas.append(_montar_item(len(apostas) + 1, ap, origem, pad, ciclos))
        if len(apostas) >= qtd:
            break

    if not apostas:
        return {
            "sucesso": False, "ok": False,
            "erro": "Nenhuma aposta coube no universo com o inicial e os ciclos atuais.",
            "sessoes": {"gaps": s1, "ciclo": s2},
            "leitura": lei,
        }

    if spec.get("extra_mes") and mes_num not in (None, ""):
        from ciclo_cobertura.pos_geracao import aplicar_mes_apostas
        apostas = aplicar_mes_apostas(apostas, mes_num)

    return {
        "sucesso": True,
        "ok": True,
        "geradas": len(apostas),
        "apostas": apostas,
        "sessoes": {"gaps": s1, "ciclo": s2},
        "origem": origem,
        "inicial": ini_user,
        "leitura": lei,
        "perfil": perfil if s2 and not s1 else ("padroes_gaps" if s1 else perfil),
        "spec": spec,
    }
