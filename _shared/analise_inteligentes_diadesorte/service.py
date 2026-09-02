# -*- coding: utf-8 -*-
"""
Lógica Dia de Sorte (01–31, 7 dezenas + mês).
Reaproveita extração de dígitos do núcleo posicional; adapta catálogo indexN/gcN.
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from itertools import combinations, product
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from analise_estudos.service_factory import make_estudos_base
from analise_inteligentes_diadesorte.soma_media import (
    calcular_faixa_soma,
    classificar_soma,
    enriquecer_jogos_com_media,
    resumo_status,
    somas_historicas_do_padrao,
)
from posicao_analise.core import extrair_digitos

MAX_DEZENA = 31
TAMANHO_JOGO = 7
DIGITOS = [str(i) for i in range(10)]
MESES_ABREV = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ",
}


def _fmt(n: int) -> str:
    return f"{int(n):02d}"


def combinacoes_n(n: int, k: int) -> int:
    if k < 0 or n < k:
        return 0
    return math.comb(n, k)


def pode_formar_numero(n: int, digitos: Iterable[str]) -> bool:
    s = set(str(d) for d in digitos)
    return all(ch in s for ch in _fmt(n))


def numeros_validos(
    digitos: Sequence[str],
    max_dezena: int = MAX_DEZENA,
    min_dezena: int = 1,
    pad: int = 2,
) -> List[int]:
    s = set(str(d) for d in digitos)

    def _ok(n: int) -> bool:
        txt = f"{int(n):0{pad}d}"
        return all(ch in s for ch in txt)

    return [n for n in range(min_dezena, max_dezena + 1) if _ok(n)]


def nao_sairam(
    dezenas: Sequence[int],
    max_dezena: int = MAX_DEZENA,
    min_dezena: int = 1,
) -> List[int]:
    usados = {int(d) for d in dezenas}
    return [n for n in range(min_dezena, max_dezena + 1) if n not in usados]


def digitos_de_dezenas(dezenas: Sequence[int]) -> List[str]:
    """Dígitos na ordem das dezenas (com repetição possível entre dezenas)."""
    out: List[str] = []
    for d in dezenas:
        out.extend(extrair_digitos(int(d), 2))
    return out


def digitos_pares_inicial_final(dezenas: Sequence[int]) -> List[str]:
    """Pares 'inicial,final' de cada dezena (ex.: 25 → '2,5')."""
    pares: List[str] = []
    for d in dezenas:
        digs = extrair_digitos(int(d), 2)
        if len(digs) >= 2:
            pares.append(f"{digs[0]},{digs[1]}")
        elif digs:
            pares.append(f"{digs[0]},{digs[0]}")
    return pares


def digitos_ordenados_unicos(dezenas: Sequence[int]) -> List[str]:
    s: Set[str] = set()
    for d in dezenas:
        s.update(extrair_digitos(int(d), 2))
    return sorted(s, key=lambda x: int(x))


def padrao_inicial(dezenas: Sequence[int]) -> str:
    """Primeiro dígito de cada dezena, na sequência recebida (sem reordenar de novo)."""
    return " ".join(str(int(d) // 10) for d in dezenas)


def padrao_final(dezenas: Sequence[int]) -> str:
    """Último dígito de cada dezena, na sequência recebida (sem reordenar de novo)."""
    return " ".join(str(int(d) % 10) for d in dezenas)


def disponibilidade_digito_inicial(
    min_dezena: int = 1,
    max_dezena: int = MAX_DEZENA,
) -> Dict[int, int]:
    """Quantidade de dezenas por dígito inicial no universo."""
    disp: Dict[int, int] = defaultdict(int)
    for n in range(int(min_dezena), int(max_dezena) + 1):
        disp[int(n) // 10] += 1
    return dict(disp)


def descricao_bma_do_padrao(padrao: str) -> str:
    """Traduz padrão inicial em distribuição Baixas/Médias/Altas (0→B, 1→M, ≥2→A)."""
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if x.strip().isdigit()]
    b = sum(1 for d in digs if d == 0)
    m = sum(1 for d in digs if d == 1)
    a = sum(1 for d in digs if d >= 2)
    return f"{b}B + {m}M + {a}A"


def jogos_possiveis_padrao(
    padrao: str,
    *,
    min_dezena: int = 1,
    max_dezena: int = MAX_DEZENA,
) -> int:
    """Volume teórico C por multiplicidade de dígito inicial no universo."""
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if x.strip().isdigit()]
    if not digs:
        return 0
    disp = disponibilidade_digito_inicial(min_dezena, max_dezena)
    need = Counter(digs)
    total = 1
    for dig, qtd in need.items():
        disponivel = int(disp.get(dig, 0))
        if qtd > disponivel:
            return 0
        total *= combinacoes_n(disponivel, qtd)
    return int(total)


def pool_por_digito_universo(
    min_dezena: int = 1,
    max_dezena: int = MAX_DEZENA,
) -> Dict[int, List[int]]:
    out: Dict[int, List[int]] = defaultdict(list)
    for n in range(int(min_dezena), int(max_dezena) + 1):
        out[int(n) // 10].append(int(n))
    return dict(out)


def expandir_jogos_padrao(
    padrao: str,
    *,
    min_dezena: int = 1,
    max_dezena: int = MAX_DEZENA,
    limite: Optional[int] = None,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Lista as apostas (7 dezenas) que realizam o padrão inicial.
    Ex.: '0 0 0 0 0 1 1' → todas C(01–09,5)×C(10–19,2).
    """
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if x.strip().isdigit()]
    padrao_norm = " ".join(str(d) for d in digs)
    if not digs:
        return {
            "sucesso": False,
            "erro": "Padrão inválido.",
            "padrao": padrao_norm,
            "total": 0,
            "jogos": [],
        }

    need = Counter(digs)
    pools = pool_por_digito_universo(min_dezena, max_dezena)
    for dig, qtd in need.items():
        if len(pools.get(dig) or []) < qtd:
            return {
                "sucesso": False,
                "erro": f"Universo insuficiente para dígito {dig} (pede {qtd}).",
                "padrao": padrao_norm,
                "total": 0,
                "jogos": [],
            }

    total = jogos_possiveis_padrao(padrao_norm, min_dezena=min_dezena, max_dezena=max_dezena)
    digitos_ord = sorted(need.keys())
    partes = [list(combinations(pools[d], need[d])) for d in digitos_ord]

    off = max(0, int(offset or 0))
    lim = int(limite) if limite not in (None, "", 0, "0") else None
    jogos: List[Dict[str, Any]] = []
    idx = 0
    for combo_parts in product(*partes):
        if idx < off:
            idx += 1
            continue
        if lim is not None and len(jogos) >= lim:
            break
        dezenas = sorted(int(x) for part in combo_parts for x in part)
        jogos.append({
            "id": idx + 1,
            "dezenas": dezenas,
            "dezenas_fmt": " ".join(f"{d:02d}" for d in dezenas),
            "soma": sum(dezenas),
            "padrao_inicial": padrao_norm,
        })
        idx += 1

    return {
        "sucesso": True,
        "padrao": padrao_norm,
        "descricao": descricao_bma_do_padrao(padrao_norm),
        "total": total,
        "offset": off,
        "limit": lim,
        "retornados": len(jogos),
        "tem_mais": (off + len(jogos)) < total,
        "jogos": jogos,
        "min_dezena": min_dezena,
        "max_dezena": max_dezena,
        "tamanho_jogo": len(digs),
    }


def _chave_dezenas(dezenas: Sequence[int]) -> str:
    return " ".join(f"{int(d):02d}" for d in sorted(int(x) for x in dezenas))


def contar_operacional_padrao(
    padrao: str,
    *,
    min_dezena: int = 1,
    max_dezena: int = MAX_DEZENA,
    faixa: Optional[Dict[str, Any]] = None,
    hist_keys: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Conta jogos teóricos do padrão por status da média e quantos já saíram.
    Não materializa a lista completa — só agregados (rápido o bastante p/ ~200k).
    """
    digs = [int(x) for x in str(padrao).replace(",", " ").split() if x.strip().isdigit()]
    padrao_norm = " ".join(str(d) for d in digs)
    if not digs:
        return {
            "padrao": padrao_norm,
            "sucesso": False,
            "erro": "Padrão inválido",
            "jogos_possiveis": 0,
            "dentro": 0,
            "proxima": 0,
            "fora": 0,
            "ja_sairam_dentro": 0,
            "para_apostar": 0,
        }

    need = Counter(digs)
    pools = pool_por_digito_universo(min_dezena, max_dezena)
    for dig, qtd in need.items():
        if len(pools.get(dig) or []) < qtd:
            return {
                "padrao": padrao_norm,
                "sucesso": False,
                "erro": f"Universo insuficiente para dígito {dig}",
                "jogos_possiveis": 0,
                "dentro": 0,
                "proxima": 0,
                "fora": 0,
                "ja_sairam_dentro": 0,
                "para_apostar": 0,
            }

    digitos_ord = sorted(need.keys())
    partes = [list(combinations(pools[d], need[d])) for d in digitos_ord]

    # Se não há faixa histórica, 1ª passagem só para média teórica
    faixa_local = faixa
    if not faixa_local or faixa_local.get("media") is None:
        somas: List[int] = []
        for combo_parts in product(*partes):
            soma = 0
            for part in combo_parts:
                for x in part:
                    soma += int(x)
            somas.append(soma)
        faixa_local = calcular_faixa_soma(somas, fonte="teorico")
        dentro = proxima = fora = 0
        for soma in somas:
            st = (classificar_soma(soma, faixa_local) or {}).get("status_media") or "fora"
            if st == "dentro":
                dentro += 1
            elif st == "proxima":
                proxima += 1
            else:
                fora += 1
        total = len(somas)
    else:
        dentro = proxima = fora = 0
        total = 0
        for combo_parts in product(*partes):
            soma = 0
            for part in combo_parts:
                for x in part:
                    soma += int(x)
            total += 1
            st = (classificar_soma(soma, faixa_local) or {}).get("status_media") or "fora"
            if st == "dentro":
                dentro += 1
            elif st == "proxima":
                proxima += 1
            else:
                fora += 1

    # Já saíram dentro: caller pode passar hist_keys só do próprio padrão
    ja_dentro = 0
    if hist_keys and faixa_local:
        for key in hist_keys:
            try:
                dez = [int(x) for x in str(key).split() if x.strip().isdigit()]
                if not dez:
                    continue
                st = (classificar_soma(sum(dez), faixa_local) or {}).get("status_media") or "fora"
                if st == "dentro":
                    ja_dentro += 1
            except Exception:
                continue

    return {
        "padrao": padrao_norm,
        "sucesso": True,
        "jogos_possiveis": total,
        "dentro": dentro,
        "proxima": proxima,
        "fora": fora,
        "ja_sairam_dentro": ja_dentro,
        "para_apostar": max(0, dentro - ja_dentro),
        "soma_faixa": faixa_local,
        "soma_media": (faixa_local or {}).get("media"),
        "fonte_media": (faixa_local or {}).get("fonte"),
    }


def _gerar_padroes_teoricos(
    tamanho: int,
    *,
    min_dezena: int = 1,
    max_dezena: int = MAX_DEZENA,
) -> List[str]:
    """Todos os padrões iniciais viáveis (dígitos não-decrescentes) no universo."""
    disp = disponibilidade_digito_inicial(min_dezena, max_dezena)
    digitos = sorted(disp.keys())
    out: List[str] = []

    def rec(i: int, restante: int, atual: List[int]) -> None:
        if i == len(digitos):
            if restante == 0 and atual:
                out.append(" ".join(str(x) for x in atual))
            return
        dig = digitos[i]
        max_n = min(restante, int(disp.get(dig, 0)))
        for qtd in range(0, max_n + 1):
            rec(i + 1, restante - qtd, atual + ([dig] * qtd))

    rec(0, int(tamanho), [])
    return out


def status_padrao(frequencia: int, atraso: Optional[int], atraso_mediano: float) -> str:
    if int(frequencia) <= 0:
        return "faltante"
    if atraso is None:
        return "frequente"
    if int(atraso) <= max(3, int(atraso_mediano)):
        return "frequente"
    return "atrasado"


def pares_impares(dezenas: Sequence[int]) -> Dict[str, int]:
    pares = sum(1 for d in dezenas if int(d) % 2 == 0)
    return {"pares": pares, "impares": len(dezenas) - pares}


def analisar_concurso_linha(
    concurso: int,
    data: str,
    dezenas_ordem: Sequence[int],
    mes_num: Optional[int] = None,
    mes_nome: str = "",
    *,
    tamanho_jogo: int = TAMANHO_JOGO,
    max_dezena: int = MAX_DEZENA,
    min_dezena: int = 1,
    pad: int = 2,
) -> Dict[str, Any]:
    # ordem_caixa: ordem oficial do sorteio — uso interno / tubular
    ordem_caixa = [int(d) for d in dezenas_ordem[:tamanho_jogo]]
    # Dezenas da aba Padrões / Resultados: sempre crescentes (como o resultado publicado)
    dezenas = sorted(ordem_caixa)
    digs_ord = digitos_ordenados_unicos(dezenas)
    digs_pares = digitos_pares_inicial_final(dezenas)
    pi = pares_impares(dezenas)
    validos = numeros_validos(digs_ord, max_dezena=max_dezena, min_dezena=min_dezena, pad=pad)
    n = len(digs_ord)
    mes_abrev = MESES_ABREV.get(int(mes_num or 0), "")
    faltantes = nao_sairam(dezenas, max_dezena=max_dezena, min_dezena=min_dezena)
    # Conjunto-base típico do construtor: 16 dezenas
    faltantes_16 = faltantes[:16]
    return {
        "concurso": int(concurso),
        "data": data or "",
        "dezenas": dezenas,
        "dezenas_ordem_caixa": ordem_caixa,
        "dezenas_ordem_caixa_fmt": " ".join(_fmt(d) for d in ordem_caixa),
        "dezenas_fmt": " ".join(_fmt(d) for d in dezenas),
        "mes_num": int(mes_num or 0) or None,
        "mes_nome": mes_nome or "",
        "mes_abrev": mes_abrev,
        "digitos": digs_pares,
        "digitos_fmt": "|".join(digs_pares),
        "digitos_ordenados": digs_ord,
        "digitos_ordenados_fmt": " ".join(digs_ord),
        "qtd_digitos": n,
        "numeros_validos": validos,
        "qtd_numeros_validos": len(validos),
        "volume_combinacoes": combinacoes_n(len(validos), tamanho_jogo),
        # Padrões Inicial/Final: mesma sequência da coluna Dezenas (crescente)
        "padrao_inicial": padrao_inicial(dezenas),
        "padrao_final": padrao_final(dezenas),
        "pares": pi["pares"],
        "impares": pi["impares"],
        "pares_impares_fmt": f"{pi['pares']}P / {pi['impares']}I",
        "nao_sairam": faltantes,
        "nao_sairam_fmt": " ".join(_fmt(x) for x in faltantes),
        "qtd_nao_sairam": len(faltantes),
        "nao_sairam_16": faltantes_16,
        "nao_sairam_16_fmt": " ".join(_fmt(x) for x in faltantes_16),
        "soma": sum(dezenas),
        "acoes": {
            "ver_combinacoes": n >= 1,
            "gerar_gc": n >= 3,
            "gerador_elite": 3 <= n <= 9,
            "n": n,
        },
    }


def catalogo_combinacoes_digitos(
    n_digitos: int,
    *,
    max_dezena: int = MAX_DEZENA,
    min_dezena: int = 1,
    tamanho_jogo: int = TAMANHO_JOGO,
    pad: int = 2,
) -> List[Dict[str, Any]]:
    """Equivalente a indexN: todas C(10, N) com números válidos da modalidade."""
    n = max(1, min(10, int(n_digitos)))
    rows: List[Dict[str, Any]] = []
    for i, combo in enumerate(combinations(DIGITOS, n), 1):
        digs = list(combo)
        validos = numeros_validos(digs, max_dezena=max_dezena, min_dezena=min_dezena, pad=pad)
        rows.append({
            "indice": i,
            "digitos": digs,
            "digitos_fmt": ", ".join(digs),
            "qtd_numeros_validos": len(validos),
            "numeros_validos": validos,
            "numeros_validos_fmt": " ".join(_fmt(x) for x in validos),
            "volume_combinacoes": combinacoes_n(len(validos), tamanho_jogo),
            "pode_gerar_jogo": len(validos) >= tamanho_jogo,
        })
    return rows


def resumo_catalogo(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    insuf = baixo = medio = alto = 0
    for r in rows:
        v = int(r.get("volume_combinacoes") or 0)
        if v <= 0:
            insuf += 1
        elif v < 100:
            baixo += 1
        elif v < 1000:
            medio += 1
        else:
            alto += 1
    return {
        "total": len(rows),
        "insuficientes": insuf,
        "baixo_volume": baixo,
        "medio_volume": medio,
        "alto_volume": alto,
    }


def _score_jogo_perfil(
    dezenas: Sequence[int],
    perfil: Optional[Dict[str, Any]],
) -> float:
    """Quanto o jogo se aproxima do perfil do concurso real (maior = melhor)."""
    if not perfil:
        return 0.0
    score = 0.0
    soma = sum(int(x) for x in dezenas)
    pi = pares_impares(dezenas)
    soma_alvo = perfil.get("soma")
    if soma_alvo is not None:
        # tolerância típica ±12: dentro da faixa pontua alto
        dist = abs(soma - int(soma_alvo))
        score += max(0.0, 40.0 - dist * 2.0)
    pares_alvo = perfil.get("pares")
    if pares_alvo is not None:
        score += max(0.0, 20.0 - abs(pi["pares"] - int(pares_alvo)) * 8.0)
    # bias leve para dezenas do conjunto "não saíram 16" (base construtor)
    base16 = perfil.get("nao_sairam_16") or []
    if base16:
        s16 = {int(x) for x in base16}
        inter = sum(1 for d in dezenas if int(d) in s16)
        score += inter * 2.5
    return score


def gerar_jogos_por_digitos(
    digitos: Sequence[str],
    qtd_jogos: int = 10,
    seed: Optional[int] = None,
    perfil: Optional[Dict[str, Any]] = None,
    *,
    max_dezena: int = MAX_DEZENA,
    min_dezena: int = 1,
    tamanho_jogo: int = TAMANHO_JOGO,
    pad: int = 2,
    modality_key: str = "diadesorte",
) -> Dict[str, Any]:
    """Geração tipo gcN: amostragem no pool, preferindo perfil do concurso real."""
    digs = [str(d) for d in digitos]
    pool = numeros_validos(digs, max_dezena=max_dezena, min_dezena=min_dezena, pad=pad)
    if len(pool) < tamanho_jogo:
        return {
            "sucesso": False,
            "erro": f"Pool insuficiente: {len(pool)} números válidos (mínimo {tamanho_jogo}).",
            "digitos": digs,
            "pool": pool,
            "jogos": [],
            "perfil_analise": perfil,
        }
    rng = random.Random(seed)
    qtd = max(1, min(500, int(qtd_jogos)))
    candidatos: List[Dict[str, Any]] = []
    vistos: Set[tuple] = set()
    # gera sobreamostra e ranqueia pelo perfil dos resultados reais
    alvo_cand = max(qtd * 12, qtd + 20) if perfil else qtd
    tentativas = 0
    max_tent = alvo_cand * 40
    while len(candidatos) < alvo_cand and tentativas < max_tent:
        tentativas += 1
        amostra = sorted(rng.sample(pool, tamanho_jogo))
        chave = tuple(amostra)
        if chave in vistos:
            continue
        vistos.add(chave)
        pi = pares_impares(amostra)
        sc = _score_jogo_perfil(amostra, perfil)
        candidatos.append({
            "dezenas": amostra,
            "dezenas_fmt": " ".join(_fmt(x) for x in amostra),
            "soma": sum(amostra),
            "pares": pi["pares"],
            "impares": pi["impares"],
            "score_perfil": round(sc, 2),
            "mes_sugerido": (perfil or {}).get("mes_num"),
            "mes_nome": (perfil or {}).get("mes_nome") or "",
        })
    if perfil:
        candidatos.sort(key=lambda j: (-j["score_perfil"], j["soma"]))
    escolhidos = candidatos[:qtd]
    jogos = []
    for i, j in enumerate(escolhidos, 1):
        row = dict(j)
        row["id"] = i
        jogos.append(row)
    out = {
        "sucesso": True,
        "digitos": digs,
        "digitos_fmt": ",".join(digs),
        "pool": pool,
        "qtd_pool": len(pool),
        "volume_teorico": combinacoes_n(len(pool), tamanho_jogo),
        "jogos": jogos,
        "qtd_gerados": len(jogos),
        "perfil_analise": perfil,
        "usa_perfil_real": bool(perfil),
    }
    try:
        from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
        out = ValidadorGeradoresElite.aplicar(
            out, origem="gerador_gc_elite", modality_key=modality_key, campo="jogos",
        )
    except Exception:
        pass
    return out


class AnaliseInteligentesService:
    modality_key = "diadesorte"

    @classmethod
    def _limites(cls) -> Dict[str, int]:
        try:
            from geradores_elite.modality_config import MODALITIES
            m = MODALITIES.get(cls.modality_key) or {}
        except Exception:
            m = {}
        dmax = int(m.get("dezena_max", MAX_DEZENA))
        dmin = int(m.get("dezena_min", 1))
        tamanho = int(m.get("pick_default", TAMANHO_JOGO))
        pad = 1 if dmax < 10 else 2
        return {
            "max_dezena": dmax,
            "min_dezena": dmin,
            "tamanho_jogo": tamanho,
            "pad": pad,
        }

    @classmethod
    def perfil_do_concurso(cls, concurso: int, base: str = "geral") -> Optional[Dict[str, Any]]:
        """Extrai perfil do concurso real para orientar a geração de apostas."""
        dados = cls.listar_resultados(janela=0, base=base, concurso=int(concurso))
        linhas = dados.get("linhas") or []
        if not linhas:
            return None
        l = linhas[0]
        return {
            "concurso": l["concurso"],
            "data": l.get("data") or "",
            "digitos": list(l.get("digitos_ordenados") or []),
            "qtd_digitos": l.get("qtd_digitos"),
            "soma": l.get("soma"),
            "pares": l.get("pares"),
            "impares": l.get("impares"),
            "mes_num": l.get("mes_num"),
            "mes_nome": l.get("mes_nome") or l.get("mes_abrev") or "",
            "padrao_inicial": l.get("padrao_inicial"),
            "padrao_final": l.get("padrao_final"),
            "nao_sairam_16": list(l.get("nao_sairam_16") or []),
            "nao_sairam_16_fmt": l.get("nao_sairam_16_fmt") or "",
            "dezenas_fmt": l.get("dezenas_fmt") or "",
        }

    @classmethod
    def listar_resultados(
        cls,
        janela: int = 0,
        base: str = "geral",
        concurso: Optional[int] = None,
    ) -> Dict[str, Any]:
        lim = cls._limites()
        Base = make_estudos_base(cls.modality_key)
        rows = Base.carregar_sorteios_asc(base_estatistica=base, janela=0)
        if concurso:
            rows = [r for r in rows if int(r.concurso) == int(concurso)]
        elif janela and janela > 0:
            rows = rows[-int(janela):]

        linhas = []
        for r in reversed(rows):  # mais recente primeiro
            ordem = Base.dezenas_ordem(r)
            linhas.append(analisar_concurso_linha(
                concurso=r.concurso,
                data=getattr(r, "data", "") or "",
                dezenas_ordem=ordem,
                mes_num=getattr(r, "mes_num", None),
                mes_nome=getattr(r, "mes_nome", "") or "",
                tamanho_jogo=lim["tamanho_jogo"],
                max_dezena=lim["max_dezena"],
                min_dezena=lim["min_dezena"],
                pad=lim["pad"],
            ))

        concursos = [int(l["concurso"]) for l in linhas] if linhas else []
        return {
            "sucesso": True,
            "total": len(linhas),
            "janela": janela,
            "base": base,
            "linhas": linhas,
            "primeiro_concurso": min(concursos) if concursos else None,
            "ultimo_concurso": max(concursos) if concursos else None,
        }

    @classmethod
    def catalogo(cls, n_digitos: int) -> Dict[str, Any]:
        lim = cls._limites()
        n = max(1, min(10, int(n_digitos)))
        rows = catalogo_combinacoes_digitos(
            n,
            max_dezena=lim["max_dezena"],
            min_dezena=lim["min_dezena"],
            tamanho_jogo=lim["tamanho_jogo"],
            pad=lim["pad"],
        )
        return {
            "sucesso": True,
            "n_digitos": n,
            "tamanho_jogo": lim["tamanho_jogo"],
            "max_dezena": lim["max_dezena"],
            "linhas": rows,
            "resumo": resumo_catalogo(rows),
            "gc_disponivel": n >= 3,
        }

    @classmethod
    def gerar_gc(
        cls,
        digitos: Sequence[str],
        qtd_jogos: int = 10,
        seed: Optional[int] = None,
        concurso: Optional[int] = None,
        perfil: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lim = cls._limites()
        perfil_uso = perfil
        digs = [str(d) for d in digitos] if digitos else []
        if concurso and not perfil_uso:
            perfil_uso = cls.perfil_do_concurso(int(concurso))
        if perfil_uso and not digs:
            digs = [str(d) for d in (perfil_uso.get("digitos") or [])]
        return gerar_jogos_por_digitos(
            digs,
            qtd_jogos=qtd_jogos,
            seed=seed,
            perfil=perfil_uso,
            max_dezena=lim["max_dezena"],
            min_dezena=lim["min_dezena"],
            tamanho_jogo=lim["tamanho_jogo"],
            pad=lim["pad"],
            modality_key=cls.modality_key,
        )

    @classmethod
    def gerar_elite(
        cls,
        n_digitos: int,
        digitos: Optional[Sequence[str]] = None,
        qtd_jogos: int = 10,
        seed: Optional[int] = None,
        concurso: Optional[int] = None,
        perfil: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lim = cls._limites()
        n = max(3, min(9, int(n_digitos)))
        perfil_uso = perfil
        if concurso and not perfil_uso:
            perfil_uso = cls.perfil_do_concurso(int(concurso))
        if digitos:
            digs = [str(d) for d in digitos][:n]
        elif perfil_uso and perfil_uso.get("digitos"):
            digs = [str(d) for d in perfil_uso["digitos"]][:n]
            n = max(3, min(9, len(digs) or n))
        else:
            # modo automático: usa dígitos do último concurso se N bater; senão amostra
            dados = cls.listar_resultados(janela=1, base="geral")
            linhas = dados.get("linhas") or []
            if linhas and int(linhas[0].get("qtd_digitos") or 0) == n:
                digs = list(linhas[0].get("digitos_ordenados") or [])
            else:
                digs = [str(i) for i in random.sample(range(10), n)]
        out = gerar_jogos_por_digitos(
            digs,
            qtd_jogos=qtd_jogos,
            seed=seed,
            perfil=perfil_uso,
            max_dezena=lim["max_dezena"],
            min_dezena=lim["min_dezena"],
            tamanho_jogo=lim["tamanho_jogo"],
            pad=lim["pad"],
            modality_key=cls.modality_key,
        )
        out["modo"] = f"{n}d"
        out["n_digitos"] = n
        return out

    @classmethod
    def listar_tubular(cls, base: str = "geral") -> Dict[str, Any]:
        """Payload para Visualização Tubular (histórico completo)."""
        Base = make_estudos_base(cls.modality_key)
        rows = Base.carregar_sorteios_asc(base_estatistica=base, janela=0)
        sorteios = []
        for r in rows:
            ordem = Base.dezenas_ordem(r)
            crescentes = sorted(int(x) for x in ordem)
            mes_num = getattr(r, "mes_num", None)
            mes_nome = getattr(r, "mes_nome", "") or ""
            item = {
                "numero": int(r.concurso),
                "concurso": int(r.concurso),
                "data": getattr(r, "data", "") or "",
                "dataApuracao": getattr(r, "data", "") or "",
                "listaDezenas": crescentes,
                "dezenas": " ".join(f"{d:02d}" for d in crescentes),
                "dezenasSorteadasOrdemSorteio": " ".join(f"{d:02d}" for d in ordem),
                "ordem_caixa": [int(x) for x in ordem],
                "mesSorte": int(mes_num or 0) or None,
                "mes_num": int(mes_num or 0) or None,
                "mesSorteNome": mes_nome,
                "nomeMesSorte": mes_nome,
            }
            tn = getattr(r, "time_num", None)
            try:
                tn_i = int(tn or 0)
            except (TypeError, ValueError):
                tn_i = 0
            if tn_i:
                item["time_num"] = tn_i
                item["time_nome"] = getattr(r, "time_nome", "") or ""
            trevos = []
            if hasattr(r, "trevos_lista"):
                try:
                    trevos = [int(x) for x in (r.trevos_lista() or [])]
                except Exception:
                    trevos = []
            if not trevos:
                for attr in ("t1", "t2"):
                    v = getattr(r, attr, None)
                    try:
                        vi = int(v or 0)
                    except (TypeError, ValueError):
                        vi = 0
                    if vi:
                        trevos.append(vi)
            if trevos:
                item["trevos"] = trevos
            sorteios.append(item)
        return {
            "sucesso": True,
            "total": len(sorteios),
            "sorteios": sorteios,
            "primeiro_concurso": sorteios[0]["concurso"] if sorteios else None,
            "ultimo_concurso": sorteios[-1]["concurso"] if sorteios else None,
        }

    @classmethod
    def estatisticas_historico(cls, base: str = "geral") -> Dict[str, Any]:
        """Freq. de qtd_digitos e volumes no histórico (Aba Combinações)."""
        dados = cls.listar_resultados(janela=0, base=base)
        linhas = dados.get("linhas") or []
        freq_n: Dict[int, int] = {}
        volumes_por_n: Dict[int, List[int]] = {}
        for l in linhas:
            n = int(l.get("qtd_digitos") or 0)
            freq_n[n] = freq_n.get(n, 0) + 1
            volumes_por_n.setdefault(n, []).append(int(l.get("volume_combinacoes") or 0))
        dist = []
        for n in sorted(freq_n.keys()):
            vols = volumes_por_n.get(n) or [0]
            dist.append({
                "n_digitos": n,
                "frequencia": freq_n[n],
                "pct": round(100.0 * freq_n[n] / max(1, len(linhas)), 1),
                "volume_medio": int(sum(vols) / max(1, len(vols))),
                "volume_min": min(vols),
                "volume_max": max(vols),
            })
        return {
            "sucesso": True,
            "total_concursos": len(linhas),
            "distribuicao_n": dist,
            "primeiro_concurso": dados.get("primeiro_concurso"),
            "ultimo_concurso": dados.get("ultimo_concurso"),
        }

    @classmethod
    def catalogo_padroes(cls, base: str = "geral") -> Dict[str, Any]:
        """
        Catálogo agregado de padrões iniciais (aba Padrões II).
        Mesma fonte consumida pelo Construtor / Geradores Elite.
        """
        lim = cls._limites()
        k = int(lim["tamanho_jogo"])
        dmin = int(lim["min_dezena"])
        dmax = int(lim["max_dezena"])

        dados = cls.listar_resultados(janela=0, base=base)
        linhas = list(dados.get("linhas") or [])
        # listar_resultados vem mais recente primeiro
        total_sorteios = len(linhas)

        ocorrencias: Dict[str, List[int]] = defaultdict(list)
        ultimo_resultado = None
        atraso_por_padrao: Dict[str, int] = {}
        for idx, l in enumerate(linhas):
            p = str(l.get("padrao_inicial") or "").strip()
            if not p:
                dez = l.get("dezenas") or []
                p = padrao_inicial(sorted(int(x) for x in dez))
            if not p:
                continue
            ocorrencias[p].append(int(l.get("concurso") or 0))
            if p not in atraso_por_padrao:
                atraso_por_padrao[p] = idx
            if idx == 0:
                ultimo_resultado = {
                    "concurso": l.get("concurso"),
                    "data": l.get("data") or "",
                    "dezenas": l.get("dezenas") or [],
                    "dezenas_fmt": l.get("dezenas_fmt") or "",
                    "numeros_formatados": [
                        f"{int(x):02d}" for x in (l.get("dezenas") or [])
                    ],
                    "padrao": p,
                    "descricao": descricao_bma_do_padrao(p),
                    "mes_num": l.get("mes_num"),
                    "mes_abrev": l.get("mes_abrev") or "",
                    "mes_nome": l.get("mes_nome") or "",
                }

        atrasos_com_freq = list(atraso_por_padrao.values())
        atraso_mediano = 10.0
        if atrasos_com_freq:
            orden = sorted(atrasos_com_freq)
            mid = len(orden) // 2
            atraso_mediano = float(orden[mid]) if len(orden) % 2 else (orden[mid - 1] + orden[mid]) / 2.0

        teoricos = _gerar_padroes_teoricos(k, min_dezena=dmin, max_dezena=dmax)
        padroes_set = set(teoricos) | set(ocorrencias.keys())

        # Somas históricas por padrão (para média operacional)
        somas_por_padrao: Dict[str, List[int]] = defaultdict(list)
        for l in linhas:
            p = str(l.get("padrao_inicial") or "").strip()
            if not p:
                dez = l.get("dezenas") or []
                p = padrao_inicial(sorted(int(x) for x in dez)) if dez else ""
            if not p:
                continue
            try:
                somas_por_padrao[p].append(int(l.get("soma") or 0))
            except (TypeError, ValueError):
                continue

        catalogo: List[Dict[str, Any]] = []
        for p in sorted(padroes_set):
            freq = len(ocorrencias.get(p) or [])
            atraso = atraso_por_padrao.get(p) if freq > 0 else None
            st = status_padrao(freq, atraso, atraso_mediano)
            jogos = jogos_possiveis_padrao(p, min_dezena=dmin, max_dezena=dmax)
            eh_ultimo = bool(ultimo_resultado and ultimo_resultado.get("padrao") == p)
            faixa = calcular_faixa_soma(somas_por_padrao.get(p) or [], fonte="historico")
            catalogo.append({
                "padrao": p,
                "descricao": descricao_bma_do_padrao(p),
                "jogos_possiveis": jogos,
                "frequencia": freq,
                "percentual_concursos": round(100.0 * freq / max(1, total_sorteios), 2),
                "atraso": atraso,
                "status": st,
                "eh_padrao_ultimo_concurso": eh_ultimo,
                "ultimo_concurso": max(ocorrencias[p]) if freq else None,
                "soma_media": (faixa or {}).get("media"),
                "soma_faixa": faixa,
            })

        # Ordenação padrão: frequência desc, depois jogos
        catalogo.sort(key=lambda r: (-int(r["frequencia"]), -int(r["jogos_possiveis"]), r["padrao"]))

        top_frequencia = [
            {
                "padrao": r["padrao"],
                "descricao": r["descricao"],
                "frequencia": r["frequencia"],
                "percentual_concursos": r["percentual_concursos"],
                "atraso": r["atraso"],
                "status": r["status"],
                "jogos_possiveis": r["jogos_possiveis"],
            }
            for r in catalogo if r["frequencia"] > 0
        ][:3]

        faltantes = sum(1 for r in catalogo if r["status"] == "faltante")
        total_jogos = sum(int(r["jogos_possiveis"]) for r in catalogo)

        return {
            "sucesso": True,
            "base": base,
            "tamanho_jogo": k,
            "min_dezena": dmin,
            "max_dezena": dmax,
            "total_sorteios_analisados": total_sorteios,
            "total_padroes": len(catalogo),
            "total_padroes_com_frequencia": sum(1 for r in catalogo if r["frequencia"] > 0),
            "total_padroes_faltantes": faltantes,
            "total_jogos_possiveis": total_jogos,
            "ultimo_resultado": ultimo_resultado,
            "top_frequencia": top_frequencia,
            "padroes": catalogo,
            "api": "/analise/api/inteligentes/catalogo-padroes",
            "consumo": {
                "construtor": "/geradores-elite/construtor-construcoes/",
                "param_gerar": "padroes_selecionados",
                "jogos_padrao": "/analise/api/inteligentes/jogos-padrao",
            },
        }

    @classmethod
    def listar_jogos_padrao(
        cls,
        padrao: str,
        *,
        limite: Optional[int] = None,
        offset: int = 0,
        base: str = "geral",
    ) -> Dict[str, Any]:
        lim = cls._limites()
        out = expandir_jogos_padrao(
            padrao,
            min_dezena=lim["min_dezena"],
            max_dezena=lim["max_dezena"],
            limite=limite,
            offset=offset,
        )
        if not out.get("sucesso"):
            return out

        # Média do próprio padrão: histórico primeiro; fallback teórico
        dados = cls.listar_resultados(janela=0, base=base)
        hist = somas_historicas_do_padrao(dados.get("linhas") or [], out.get("padrao") or padrao)
        faixa = calcular_faixa_soma(hist, fonte="historico")
        if not faixa:
            somas_teo = [int(j.get("soma") or 0) for j in (out.get("jogos") or [])]
            # Se a página veio paginada, recalcula amostra teórica completa sem limite
            if (limite not in (None, "", 0, "0")) or int(offset or 0):
                full = expandir_jogos_padrao(
                    out.get("padrao") or padrao,
                    min_dezena=lim["min_dezena"],
                    max_dezena=lim["max_dezena"],
                    limite=None,
                    offset=0,
                )
                somas_teo = [int(j.get("soma") or 0) for j in (full.get("jogos") or [])]
            faixa = calcular_faixa_soma(somas_teo, fonte="teorico")

        jogos = enriquecer_jogos_com_media(out.get("jogos") or [], faixa)
        out["jogos"] = jogos
        out["soma_faixa"] = faixa
        out["soma_media"] = (faixa or {}).get("media")
        out["resumo_status"] = resumo_status(jogos)
        out["modality_key"] = cls.modality_key
        try:
            from geradores_elite.modality_config import MODALITIES
            out["modality_nome"] = (MODALITIES.get(cls.modality_key) or {}).get("nome") or cls.modality_key
        except Exception:
            out["modality_nome"] = cls.modality_key
        return out

    @classmethod
    def exportar_jogos_padrao_xlsx(
        cls,
        padrao: str,
        *,
        base: str = "geral",
        ids: Optional[Sequence[int]] = None,
        dezenas_fmt: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Exporta apostas do padrão em XLSX (mesma regra da interface)."""
        from analise_inteligentes_diadesorte.soma_media import (
            build_xlsx_apostas,
            safe_filename_padrao,
        )

        out = cls.listar_jogos_padrao(padrao, limite=None, offset=0, base=base)
        if not out.get("sucesso"):
            return out
        jogos = list(out.get("jogos") or [])
        if dezenas_fmt:
            want = {str(x).strip() for x in dezenas_fmt if str(x).strip()}
            jogos = [j for j in jogos if str(j.get("dezenas_fmt") or "") in want]
        elif ids:
            want_ids = {int(x) for x in ids}
            jogos = [j for j in jogos if int(j.get("id") or 0) in want_ids]
        blob = build_xlsx_apostas(
            modality_key=out.get("modality_key") or cls.modality_key,
            modality_nome=out.get("modality_nome") or cls.modality_key,
            padrao=out.get("padrao") or padrao,
            descricao=out.get("descricao") or "",
            faixa=out.get("soma_faixa"),
            jogos=jogos,
        )
        fname = (
            f"apostas_padrao_{safe_filename_padrao(out.get('padrao') or padrao)}"
            f"_{cls.modality_key}.xlsx"
        )
        return {
            "sucesso": True,
            "filename": fname,
            "content": blob,
            "total": len(jogos),
            "soma_faixa": out.get("soma_faixa"),
        }

    @classmethod
    def resumo_operacional_padroes(cls, base: str = "geral") -> Dict[str, Any]:
        """
        Tabela operacional (aba 4): por padrão — para apostar, já saíram, dentro/próximas/fora.
        """
        import time

        t0 = time.perf_counter()
        lim = cls._limites()
        dmin = int(lim["min_dezena"])
        dmax = int(lim["max_dezena"])

        cat = cls.catalogo_padroes(base=base)
        if not cat.get("sucesso"):
            return cat

        dados = cls.listar_resultados(janela=0, base=base)
        linhas = list(dados.get("linhas") or [])
        hist_keys_por_padrao: Dict[str, Set[str]] = defaultdict(set)
        somas_por_padrao: Dict[str, List[int]] = defaultdict(list)
        for l in linhas:
            dez = l.get("dezenas") or []
            p = str(l.get("padrao_inicial") or "").strip()
            if not p and dez:
                p = padrao_inicial(sorted(int(x) for x in dez))
            if not p:
                continue
            try:
                somas_por_padrao[p].append(int(l.get("soma") or 0))
            except (TypeError, ValueError):
                continue
            if dez:
                try:
                    hist_keys_por_padrao[p].add(_chave_dezenas(dez))
                except Exception:
                    pass

        rows: List[Dict[str, Any]] = []
        for pinfo in (cat.get("padroes") or []):
            p = str(pinfo.get("padrao") or "").strip()
            if not p:
                continue
            faixa = calcular_faixa_soma(somas_por_padrao.get(p) or [], fonte="historico")
            op = contar_operacional_padrao(
                p,
                min_dezena=dmin,
                max_dezena=dmax,
                faixa=faixa,
                hist_keys=hist_keys_por_padrao.get(p) or set(),
            )
            rows.append({
                "padrao": p,
                "descricao": pinfo.get("descricao") or descricao_bma_do_padrao(p),
                "frequencia": int(pinfo.get("frequencia") or 0),
                "atraso": pinfo.get("atraso"),
                "status": pinfo.get("status"),
                "jogos_possiveis": int(op.get("jogos_possiveis") or pinfo.get("jogos_possiveis") or 0),
                "para_apostar": int(op.get("para_apostar") or 0),
                "ja_sairam_dentro": int(op.get("ja_sairam_dentro") or 0),
                "dentro": int(op.get("dentro") or 0),
                "proxima": int(op.get("proxima") or 0),
                "fora": int(op.get("fora") or 0),
                "soma_media": op.get("soma_media"),
                "tol_proxima": (op.get("soma_faixa") or {}).get("tol_proxima"),
                "fonte_media": op.get("fonte_media"),
                "eh_padrao_ultimo_concurso": bool(pinfo.get("eh_padrao_ultimo_concurso")),
            })

        # Ordena: mais para apostar primeiro; empate por frequência
        rows.sort(key=lambda r: (-int(r["para_apostar"]), -int(r["frequencia"]), r["padrao"]))

        # --- Checagem de consistência / probabilidade ---
        total_universo = combinacoes_n(dmax - dmin + 1, int(lim["tamanho_jogo"]))
        total_jogos_soma = sum(int(r["jogos_possiveis"]) for r in rows)
        total_freq = sum(int(r["frequencia"]) for r in rows)
        total_concursos = int(cat.get("total_sorteios_analisados") or len(linhas) or 0)
        total_dentro = sum(int(r["dentro"]) for r in rows)
        total_proxima = sum(int(r["proxima"]) for r in rows)
        total_fora = sum(int(r["fora"]) for r in rows)
        total_para = sum(int(r["para_apostar"]) for r in rows)
        total_ja = sum(int(r["ja_sairam_dentro"]) for r in rows)

        inconsistencias_linha: List[str] = []
        for r in rows:
            jp = int(r["jogos_possiveis"])
            dpf = int(r["dentro"]) + int(r["proxima"]) + int(r["fora"])
            if jp != dpf:
                inconsistencias_linha.append(
                    f"{r['padrao']}: dentro+próx+fora={dpf} ≠ jogos={jp}"
                )
            if int(r["para_apostar"]) + int(r["ja_sairam_dentro"]) != int(r["dentro"]):
                inconsistencias_linha.append(
                    f"{r['padrao']}: apostar+já≠dentro"
                )
            # probabilidade teórica do padrão
            r["prob_teorica_pct"] = round(100.0 * jp / max(1, total_universo), 4)
            r["prob_empirica_pct"] = round(
                100.0 * int(r["frequencia"]) / max(1, total_concursos), 4
            )

        checks = [
            {
                "id": "universo",
                "label": f"Soma dos jogos dos padrões = C({dmax - dmin + 1},{lim['tamanho_jogo']})",
                "esperado": total_universo,
                "obtido": total_jogos_soma,
                "ok": total_jogos_soma == total_universo,
            },
            {
                "id": "concursos",
                "label": "Soma das frequências = concursos apurados",
                "esperado": total_concursos,
                "obtido": total_freq,
                "ok": total_freq == total_concursos,
            },
            {
                "id": "particao_status",
                "label": "Soma (dentro+próximas+fora) = total de jogos",
                "esperado": total_jogos_soma,
                "obtido": total_dentro + total_proxima + total_fora,
                "ok": (total_dentro + total_proxima + total_fora) == total_jogos_soma,
            },
            {
                "id": "apostar",
                "label": "Soma (para apostar + já saíram) = soma (dentro)",
                "esperado": total_dentro,
                "obtido": total_para + total_ja,
                "ok": (total_para + total_ja) == total_dentro,
            },
            {
                "id": "padroes",
                "label": "Qtd. padrões no resumo = catálogo",
                "esperado": int(cat.get("total_padroes") or 0),
                "obtido": len(rows),
                "ok": len(rows) == int(cat.get("total_padroes") or 0),
            },
        ]
        n_ok = sum(1 for c in checks if c["ok"])
        checagem = {
            "ok": n_ok == len(checks) and not inconsistencias_linha,
            "checks": checks,
            "inconsistencias_linha": inconsistencias_linha[:20],
            "total_universo": total_universo,
            "total_jogos_padroes": total_jogos_soma,
            "total_concursos": total_concursos,
            "total_frequencias": total_freq,
            "total_dentro": total_dentro,
            "total_proxima": total_proxima,
            "total_fora": total_fora,
            "total_para_apostar": total_para,
            "total_ja_sairam_dentro": total_ja,
            "pct_universo_coberto": round(100.0 * total_jogos_soma / max(1, total_universo), 4),
            "min_dezena": dmin,
            "max_dezena": dmax,
            "tamanho_jogo": int(lim["tamanho_jogo"]),
            "modality_key": cls.modality_key,
        }

        return {
            "sucesso": True,
            "base": base,
            "total_padroes": len(rows),
            "total_para_apostar": total_para,
            "total_ja_sairam_dentro": total_ja,
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "padroes": rows,
            "checagem": checagem,
            "api": "/analise/api/inteligentes/resumo-operacional-padroes",
        }


def make_inteligentes_service(modality_key: str):
    """Factory — serviço de GC/Elite parametrizado pela modalidade."""
    class _Svc(AnaliseInteligentesService):
        pass
    _Svc.modality_key = modality_key
    _Svc.__name__ = f"AnaliseInteligentes_{modality_key}"
    return _Svc
