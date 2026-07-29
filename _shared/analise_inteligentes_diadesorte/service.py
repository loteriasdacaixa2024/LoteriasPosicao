# -*- coding: utf-8 -*-
"""
Lógica Dia de Sorte (01–31, 7 dezenas + mês).
Reaproveita extração de dígitos do núcleo posicional; adapta catálogo indexN/gcN.
"""
from __future__ import annotations

import math
import random
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from analise_estudos.service_factory import make_estudos_base
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
            sorteios.append({
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
            })
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


def make_inteligentes_service(modality_key: str):
    """Factory — serviço de GC/Elite parametrizado pela modalidade."""
    class _Svc(AnaliseInteligentesService):
        pass
    _Svc.modality_key = modality_key
    _Svc.__name__ = f"AnaliseInteligentes_{modality_key}"
    return _Svc
