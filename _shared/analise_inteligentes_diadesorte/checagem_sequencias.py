# -*- coding: utf-8 -*-
"""Checagem de Sequências — parse, prefixo e sugestão (aba 8)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import combinations, product
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from analise_inteligentes_diadesorte.diagonais_volante import diagonais_na_aposta
from analise_inteligentes_diadesorte.soma_media import classificar_soma


def padrao_inicial(dezenas: Sequence[int]) -> str:
    return " ".join(str(int(d) // 10) for d in dezenas)


def pool_por_digito_universo(min_dezena: int = 1, max_dezena: int = 31) -> Dict[int, List[int]]:
    out: Dict[int, List[int]] = defaultdict(list)
    for n in range(int(min_dezena), int(max_dezena) + 1):
        out[int(n) // 10].append(int(n))
    return dict(out)


def descricao_bma_do_padrao(padrao: str) -> str:
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if x.strip().isdigit()]
    b = sum(1 for d in digs if d == 0)
    m = sum(1 for d in digs if d == 1)
    a = sum(1 for d in digs if d >= 2)
    return f"{b}B + {m}M + {a}A"

MES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
MES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
_MES_ALIASES = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "marco": 3, "março": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}
_MES_TOKEN_RE = re.compile(
    r"\b(Janeiro|Fevereiro|Março|Marco|Abril|Maio|Junho|Julho|Agosto|"
    r"Setembro|Outubro|Novembro|Dezembro|"
    r"Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)\b",
    re.IGNORECASE,
)


def fmt_dezenas(dezenas: Sequence[int]) -> str:
    return " ".join(f"{int(d):02d}" for d in dezenas)


def chave_dezenas(src: Any) -> str:
    if isinstance(src, (list, tuple)):
        nums = [int(x) for x in src if str(x).strip() != ""]
    else:
        nums = [int(x) for x in re.findall(r"\d+", str(src or ""))]
    if not nums:
        return ""
    return fmt_dezenas(sorted(nums))


def normalizar_padrao(padrao: str) -> str:
    digs = [x for x in str(padrao or "").replace(",", " ").split() if x.strip().isdigit()]
    return " ".join(digs)


def resolver_mes_token(token: str) -> Optional[int]:
    raw = (token or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        n = int(raw)
        return n if 1 <= n <= 12 else None
    key = raw.lower().replace("ç", "c")
    return _MES_ALIASES.get(key) or _MES_ALIASES.get(raw.lower())


def mes_abrev(mes_num: Optional[int]) -> str:
    if not mes_num:
        return ""
    return MES_ABREV.get(int(mes_num), "")


def extrair_nums(texto: str) -> List[int]:
    return [int(x) for x in re.findall(r"\d+", texto or "")]


def parse_linha_aposta(
    texto: str,
    *,
    sorteadas: int = 7,
    min_dezena: int = 1,
    max_dezena: int = 31,
) -> Dict[str, Any]:
    raw = (texto or "").strip()
    if not raw:
        return {"ok": False, "erro": "Linha vazia."}

    mes_num = None
    mes_colado = ""
    m = _MES_TOKEN_RE.search(raw)
    if m:
        mes_colado = m.group(0)
        mes_num = resolver_mes_token(mes_colado)
        raw_nums = _MES_TOKEN_RE.sub(" ", raw)
    else:
        raw_nums = raw

    nums = extrair_nums(raw_nums)
    if len(nums) == sorteadas + 1 and 1 <= nums[-1] <= 12:
        mes_num = nums[-1]
        mes_colado = mes_colado or MES_ABREV.get(mes_num, str(mes_num))
        nums = nums[:sorteadas]

    if len(nums) != sorteadas:
        return {
            "ok": False,
            "erro": f"Esperado {sorteadas} dezenas, veio {len(nums)}.",
            "mes_colado": mes_colado,
            "mes_num": mes_num,
        }

    vistos: Set[int] = set()
    for n in nums:
        if n < min_dezena or n > max_dezena:
            return {
                "ok": False,
                "erro": f"Dezena {n:02d} fora de {min_dezena:02d}–{max_dezena:02d}.",
                "mes_colado": mes_colado,
                "mes_num": mes_num,
            }
        if n in vistos:
            return {
                "ok": False,
                "erro": f"Dezena {n:02d} repetida.",
                "mes_colado": mes_colado,
                "mes_num": mes_num,
            }
        vistos.add(n)

    dezenas = sorted(nums)
    return {
        "ok": True,
        "dezenas": dezenas,
        "dezenas_fmt": fmt_dezenas(dezenas),
        "padrao": padrao_inicial(dezenas),
        "mes_colado": mes_colado,
        "mes_num": mes_num,
        "erro": None,
    }


def parse_lote_apostas(
    texto: str,
    *,
    sorteadas: int = 7,
    min_dezena: int = 1,
    max_dezena: int = 31,
) -> Dict[str, Any]:
    raw = (texto or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return {"ok": False, "erro": "Cole ou arraste as apostas.", "apostas": []}

    linhas = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    apostas: List[Dict[str, Any]] = []
    erros: List[str] = []

    if len(linhas) == 1:
        unico = parse_linha_aposta(
            linhas[0], sorteadas=sorteadas, min_dezena=min_dezena, max_dezena=max_dezena,
        )
        if unico.get("ok"):
            unico["linha"] = 1
            return {"ok": True, "apostas": [unico], "erros": []}
        compacto = extrair_nums(_MES_TOKEN_RE.sub(" ", linhas[0]))
        if len(compacto) >= sorteadas and len(compacto) % sorteadas == 0:
            linhas = []
            for i in range(0, len(compacto), sorteadas):
                bloco = compacto[i:i + sorteadas]
                linhas.append(" ".join(f"{n:02d}" for n in bloco))
        else:
            unico["linha"] = 1
            return {"ok": False, "erro": unico.get("erro"), "apostas": [unico], "erros": [unico.get("erro")]}

    for i, ln in enumerate(linhas, 1):
        item = parse_linha_aposta(
            ln, sorteadas=sorteadas, min_dezena=min_dezena, max_dezena=max_dezena,
        )
        item["linha"] = i
        item["texto"] = ln
        apostas.append(item)
        if not item.get("ok"):
            erros.append(f"Linha {i}: {item.get('erro')}")

    ok = any(a.get("ok") for a in apostas)
    return {
        "ok": ok,
        "erro": None if ok else (erros[0] if erros else "Nenhuma aposta válida."),
        "apostas": apostas,
        "erros": erros,
    }


def expandir_jogos_contendo(
    padrao: str,
    obrigatorias: Sequence[int],
    *,
    min_dezena: int = 1,
    max_dezena: int = 31,
    tamanho_jogo: int = 7,
) -> List[Dict[str, Any]]:
    """Jogos do padrão que contêm todas as dezenas obrigatórias."""
    digs = [int(x) for x in str(padrao or "").replace(",", " ").split() if x.strip().isdigit()]
    padrao_norm = " ".join(str(d) for d in digs)
    if len(digs) != tamanho_jogo:
        return []

    obr = sorted({int(x) for x in obrigatorias})
    if len(obr) > tamanho_jogo:
        return []
    if any(n < min_dezena or n > max_dezena for n in obr):
        return []

    need = Counter(digs)
    used = Counter()
    for n in obr:
        d = int(n) // 10
        if used[d] >= need.get(d, 0):
            return []
        used[d] += 1

    remain_need = need - used
    pools = pool_por_digito_universo(min_dezena, max_dezena)
    used_nums = set(obr)
    remain_parts: List[List[Tuple[int, ...]]] = []
    for d, qtd in sorted(remain_need.items()):
        if qtd <= 0:
            continue
        pool = [x for x in (pools.get(d) or []) if x not in used_nums]
        if len(pool) < qtd:
            return []
        remain_parts.append(list(combinations(pool, qtd)))

    jogos: List[Dict[str, Any]] = []
    if not remain_parts:
        dezenas = list(obr)
        if len(dezenas) == tamanho_jogo and padrao_inicial(dezenas) == padrao_norm:
            jogos.append({
                "dezenas": dezenas,
                "dezenas_fmt": fmt_dezenas(dezenas),
                "soma": sum(dezenas),
                "padrao_inicial": padrao_norm,
            })
        return jogos

    for combo_parts in product(*remain_parts):
        extra = [int(x) for part in combo_parts for x in part]
        dezenas = sorted(obr + extra)
        if len(dezenas) != tamanho_jogo:
            continue
        jogos.append({
            "dezenas": dezenas,
            "dezenas_fmt": fmt_dezenas(dezenas),
            "soma": sum(dezenas),
            "padrao_inicial": padrao_norm,
        })
    return jogos


def jogo_no_filtro(
    jogo: Dict[str, Any],
    filtro: str,
    historico_keys: Set[str],
) -> bool:
    st = str(jogo.get("status_media") or "fora")
    chave = chave_dezenas(jogo.get("dezenas") or jogo.get("dezenas_fmt"))
    ja = chave in historico_keys
    f = (filtro or "dentro_novos").strip().lower()
    if f == "all":
        return True
    if f == "alinhadas":
        return st in ("dentro", "proxima")
    if f in ("proxima", "fora"):
        return st == f
    if st != "dentro":
        return False
    if f == "dentro_ja":
        return ja
    if f == "dentro":
        return True
    return not ja  # dentro_novos


def distancia_sugestao(
    alvo: Sequence[int],
    cand: Sequence[int],
    prefixo_n: int,
) -> Tuple[int, int, Tuple[int, ...]]:
    a = [int(x) for x in alvo]
    c = [int(x) for x in cand]
    obr = set(a[: max(0, int(prefixo_n))])
    a_rest = sorted(x for x in a if x not in obr)
    c_rest = sorted(x for x in c if x not in obr)
    comuns = len(set(a_rest) & set(c_rest))
    n = max(len(a_rest), len(c_rest))
    dist = 0
    for i in range(n):
        av = a_rest[i] if i < len(a_rest) else 0
        cv = c_rest[i] if i < len(c_rest) else 0
        dist += abs(av - cv)
    return (-comuns, dist, tuple(c))


def sugerir_proxima(
    alvo: Sequence[int],
    candidatos: Sequence[Dict[str, Any]],
    prefixo_n: int,
) -> Optional[Dict[str, Any]]:
    if not candidatos:
        return None
    alvo_k = chave_dezenas(alvo)
    ranked = []
    for j in candidatos:
        dez = j.get("dezenas") or []
        if chave_dezenas(dez) == alvo_k:
            continue
        ranked.append((distancia_sugestao(alvo, dez, prefixo_n), j))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0])
    best = ranked[0][1]
    return {
        "dezenas": list(best.get("dezenas") or []),
        "dezenas_fmt": best.get("dezenas_fmt") or fmt_dezenas(best.get("dezenas") or []),
        "soma": best.get("soma"),
        "status_media": best.get("status_media"),
        "status_media_label": best.get("status_media_label"),
        "motivo": "Mesmas primeiras dezenas · menor diferença nas restantes",
    }


def observar_ultimas(
    alvo: Sequence[int],
    candidatos: Sequence[Dict[str, Any]],
    prefixo_n: int,
) -> List[Dict[str, Any]]:
    n = max(0, int(prefixo_n))
    rest = [int(x) for x in alvo[n:]]
    presentes: Set[int] = set()
    for j in candidatos:
        presentes.update(int(x) for x in (j.get("dezenas") or []))
    out = []
    pos0 = n
    for i, dez in enumerate(rest):
        out.append({
            "posicao": pos0 + i + 1,
            "dezena": dez,
            "dezena_fmt": f"{dez:02d}",
            "existe": dez in presentes,
        })
    return out


def resumo_jogo(j: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dezenas": list(j.get("dezenas") or []),
        "dezenas_fmt": j.get("dezenas_fmt") or "",
        "soma": j.get("soma"),
        "status_media": j.get("status_media"),
        "status_media_label": j.get("status_media_label"),
        "distancia": j.get("distancia"),
    }


def montar_resultado_linha(
    aposta: Dict[str, Any],
    *,
    prefixo_n: int,
    filtro: str,
    jogos_enriquecidos: Sequence[Dict[str, Any]],
    historico_keys: Set[str],
    limite_matches: int = 12,
    faixa: Optional[Dict[str, Any]] = None,
    min_dezena: int = 1,
    max_dezena: int = 31,
) -> Dict[str, Any]:
    if not aposta.get("ok"):
        return {
            "linha": aposta.get("linha"),
            "ok": False,
            "erro": aposta.get("erro") or "Aposta inválida.",
            "texto": aposta.get("texto") or "",
            "dezenas_fmt": "",
            "padrao": "",
        }

    dezenas = list(aposta["dezenas"])
    n = max(2, min(int(prefixo_n or 5), len(dezenas)))
    prefixo = dezenas[:n]
    padrao = aposta.get("padrao") or padrao_inicial(dezenas)
    chave = chave_dezenas(dezenas)
    soma = sum(int(x) for x in dezenas)
    cls_soma = classificar_soma(soma, faixa)
    diags = diagonais_na_aposta(dezenas, dmin=min_dezena, dmax=max_dezena)

    universo = [j for j in jogos_enriquecidos if jogo_no_filtro(j, filtro, historico_keys)]
    matches = [
        j for j in universo
        if set(prefixo).issubset({int(x) for x in (j.get("dezenas") or [])})
    ]
    exata = next((j for j in matches if chave_dezenas(j.get("dezenas")) == chave), None)
    ultimas = observar_ultimas(dezenas, matches, n)
    sugestao = None if exata else sugerir_proxima(dezenas, matches, n)

    matches_ord = sorted(
        matches,
        key=lambda j: (0 if chave_dezenas(j.get("dezenas")) == chave else 1, j.get("soma") or 0),
    )

    return {
        "linha": aposta.get("linha"),
        "ok": True,
        "erro": None,
        "dezenas": dezenas,
        "dezenas_fmt": aposta.get("dezenas_fmt") or fmt_dezenas(dezenas),
        "mes_colado": aposta.get("mes_colado") or "",
        "mes_num_colado": aposta.get("mes_num"),
        "padrao": padrao,
        "descricao": descricao_bma_do_padrao(padrao),
        "prefixo_n": n,
        "prefixo": prefixo,
        "prefixo_fmt": fmt_dezenas(prefixo),
        "existe_exata": bool(exata),
        "status_exata": (exata or {}).get("status_media"),
        "status_exata_label": (exata or {}).get("status_media_label"),
        "soma": soma,
        "status_media": cls_soma.get("status_media"),
        "status_media_label": cls_soma.get("status_media_label"),
        "soma_media": cls_soma.get("media"),
        "distancia": cls_soma.get("distancia"),
        "diagonais": diags,
        "n_diagonais": len(diags),
        "soma_exata": (exata or {}).get("soma") if exata else soma,
        "ja_saiu": chave in historico_keys,
        "ultimas": ultimas,
        "qtd_prefixo": len(matches),
        "matches": [resumo_jogo(j) for j in matches_ord[:limite_matches]],
        "sugestao": sugestao,
    }
