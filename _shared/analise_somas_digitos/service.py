# -*- coding: utf-8 -*-
"""Estatísticas de soma das dezenas e dígitos distintos (histórico oficial)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

from analise_estudos.core.digitos import analisar_digitos_concurso
from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import BASES_LABEL, get_estudos_config


def faixas_soma_para(modality_key: str):
    """Gera faixas de soma a partir do universo e quantidade sorteada."""
    cfg = get_estudos_config(modality_key)
    n = int(cfg["sorteadas"])
    dmin = int(cfg["dezena_min"])
    dmax = int(cfg["dezena_max"])
    lo = n * dmin
    hi = n * dmax
    # ~7 faixas proporcionais (legado Dia: 7–217 em 7 faixas)
    span = max(1, hi - lo)
    step = max(1, span // 7)
    faixas = []
    cur = lo
    while cur <= hi:
        nxt = min(hi, cur + step - 1)
        if len(faixas) == 6:
            nxt = hi
        label = f"{cur}–{nxt}"
        faixas.append((label, cur, nxt))
        if nxt >= hi:
            break
        cur = nxt + 1
    return tuple(faixas)


# Compatibilidade legado Dia de Sorte
FAIXAS_SOMA = (
    ("7–70", 7, 70),
    ("71–90", 71, 90),
    ("91–110", 91, 110),
    ("111–130", 111, 130),
    ("131–150", 131, 150),
    ("151–170", 151, 170),
    ("171–217", 171, 217),
)


def faixa_da_soma(soma: int, faixas=None) -> str:
    tabela = faixas or FAIXAS_SOMA
    for label, lo, hi in tabela:
        if lo <= soma <= hi:
            return label
    if soma < tabela[0][1]:
        return tabela[0][0]
    return tabela[-1][0]


def digitos_de_pool(dezenas: List[int], pad_width: int = 2) -> Dict[str, Any]:
    """Dígitos distintos. pad_width<=1: cada valor já é um dígito (Super Sete)."""
    digs: Set[str] = set()
    for n in dezenas:
        if pad_width <= 1:
            digs.add(str(int(n)))
            continue
        s = f"{int(n):0{pad_width}d}"
        for ch in s:
            if ch.isdigit():
                digs.add(ch)
    ordenados = sorted(digs, key=lambda x: int(x))
    return {
        "digitos": ordenados,
        "digitos_fmt": ",".join(ordenados),
        "qtd": len(ordenados),
        "soma": sum(int(d) for d in dezenas),
    }


class AnaliseSomasDigitosService:
    """Análises históricas (sorteios oficiais) + métricas do conjunto-base."""

    @classmethod
    def _base(cls, modality_key: str):
        return make_estudos_base(modality_key)

    @classmethod
    def _carregar(cls, modality_key: str, janela: int, base: str):
        Base = cls._base(modality_key)
        janela = Base._normalizar_janela(janela)
        base = Base._normalizar_base(base)
        sorteios = Base.carregar_sorteios_asc(base, janela if janela > 0 else 0)
        return Base, janela, base, sorteios

    @classmethod
    def analisar_somas(
        cls,
        modality_key: str,
        janela: int = 0,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        Base, janela, base, sorteios = cls._carregar(modality_key, janela, base_estatistica)
        if not sorteios:
            return {"sucesso": False, "erro": f"Nenhum sorteio na base «{base}»."}

        faixas = faixas_soma_para(modality_key)
        linhas: List[Dict[str, Any]] = []
        somas: List[int] = []
        for s in sorteios:
            dz = Base.dezenas_ordem(s)
            soma = sum(dz)
            somas.append(soma)
            linhas.append({
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                "soma": soma,
                "faixa": faixa_da_soma(soma, faixas),
                "par_impar": "Par" if soma % 2 == 0 else "Ímpar",
            })

        total = len(somas)
        cnt_soma = Counter(somas)
        cnt_faixa = Counter(faixa_da_soma(x, faixas) for x in somas)
        moda_soma, moda_n = cnt_soma.most_common(1)[0]
        faixa_top = cnt_faixa.most_common(1)[0][0] if cnt_faixa else "—"
        faixa_bot = min(cnt_faixa.items(), key=lambda x: x[1])[0] if cnt_faixa else "—"

        distribuicao_faixas = []
        for label, lo, hi in faixas:
            n = cnt_faixa.get(label, 0)
            distribuicao_faixas.append({
                "faixa": label,
                "min": lo,
                "max": hi,
                "ocorrencias": n,
                "pct": round(n / total * 100, 2) if total else 0,
                "destaque": label == faixa_top,
            })

        ranking_somas = [
            {
                "soma": k,
                "ocorrencias": v,
                "pct": round(v / total * 100, 2) if total else 0,
            }
            for k, v in cnt_soma.most_common(25)
        ]

        media = round(sum(somas) / total, 2) if total else 0
        return {
            "sucesso": True,
            "aba": "somas",
            "base_estatistica": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "total_concursos": total,
            "ultimo_concurso": sorteios[-1].concurso,
            "resumo": {
                "soma_minima": min(somas),
                "soma_maxima": max(somas),
                "soma_media": media,
                "soma_moda": moda_soma,
                "soma_moda_pct": round(moda_n / total * 100, 2) if total else 0,
                "faixa_mais_frequente": faixa_top,
                "faixa_menos_frequente": faixa_bot,
                "pares": sum(1 for x in somas if x % 2 == 0),
                "impares": sum(1 for x in somas if x % 2 == 1),
            },
            "distribuicao_faixas": distribuicao_faixas,
            "ranking_somas": ranking_somas,
            "linhas": list(reversed(linhas)),
            "meta_bases": Base.meta_bases(),
        }

    @classmethod
    def analisar_digitos(
        cls,
        modality_key: str,
        janela: int = 0,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        Base, janela, base, sorteios = cls._carregar(modality_key, janela, base_estatistica)
        if not sorteios:
            return {"sucesso": False, "erro": f"Nenhum sorteio na base «{base}»."}

        linhas: List[Dict[str, Any]] = []
        qtds: List[int] = []
        presenca: Counter[str] = Counter()
        freq_apar: Counter[str] = Counter()

        for s in sorteios:
            dz = Base.dezenas_ordem(s)
            dig = analisar_digitos_concurso(dz, modality_key)
            qtd = dig["qtd_digitos_distintos"]
            qtds.append(qtd)
            digs = dig["digitos_distintos"]
            for d in digs:
                presenca[d] += 1
                freq_apar[d] += 1
            linhas.append({
                "concurso": s.concurso,
                "data": getattr(s, "data", "") or "",
                "dezenas": dz,
                "digitos": digs,
                "digitos_fmt": dig.get("digitos_distintos_fmt") or ",".join(digs),
                "qtd_digitos": qtd,
                "soma_dezenas": dig.get("soma_dezenas", sum(dz)),
            })

        total = len(qtds)
        cnt_qtd = Counter(qtds)
        moda_qtd, moda_n = cnt_qtd.most_common(1)[0] if cnt_qtd else (7, 0)

        # Tabela principal: 4–9 dígitos (o que o usuário mais gostou)
        resumo_qtd = []
        for q in range(4, 10):
            n = cnt_qtd.get(q, 0)
            resumo_qtd.append({
                "qtd_digitos": q,
                "ocorrencias": n,
                "pct": round(n / total * 100, 2) if total else 0,
                "destaque": q == moda_qtd,
                "recomendado": q == moda_qtd,
            })

        painel_digitos = []
        for d in [str(i) for i in range(10)]:
            n = presenca.get(d, 0)
            painel_digitos.append({
                "digito": d,
                "concursos": n,
                "pct": round(n / total * 100, 1) if total else 0,
                "aparicoes": freq_apar.get(d, 0),
            })
        painel_digitos.sort(key=lambda x: (-x["concursos"], int(x["digito"])))
        if painel_digitos:
            painel_digitos[0]["destaque"] = True
            for p in painel_digitos[1:]:
                p["destaque"] = False

        ausentes_ultimo = []
        if linhas:
            usados = set(linhas[-1]["digitos"])  # chronological last before reverse
            # linhas built chrono; last item is latest
            usados = set(linhas[-1]["digitos"])
            ausentes_ultimo = [d for d in [str(i) for i in range(10)] if d not in usados]

        return {
            "sucesso": True,
            "aba": "digitos",
            "base_estatistica": base,
            "base_label": BASES_LABEL.get(base, base),
            "janela": janela,
            "total_concursos": total,
            "ultimo_concurso": sorteios[-1].concurso,
            "resumo": {
                "qtd_recomendada": moda_qtd,
                "qtd_recomendada_pct": round(moda_n / total * 100, 2) if total else 0,
                "media_qtd": round(sum(qtds) / total, 2) if total else 0,
                "digito_mais_frequente": painel_digitos[0]["digito"] if painel_digitos else "—",
                "digito_menos_frequente": painel_digitos[-1]["digito"] if painel_digitos else "—",
                "digitos_ausentes_ultimo": ausentes_ultimo,
            },
            "resumo_por_quantidade": resumo_qtd,
            "painel_digitos": painel_digitos,
            "linhas": list(reversed(linhas)),
            "meta_bases": Base.meta_bases(),
        }

    @classmethod
    def estatisticas_conjunto(
        cls,
        modality_key: str,
        conjunto_base: Optional[List[int]] = None,
        janela: int = 0,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        """Guia histórico (7 dz) + métricas atuais do conjunto-base (até 16)."""
        somas = cls.analisar_somas(modality_key, janela=janela, base_estatistica=base_estatistica)
        digitos = cls.analisar_digitos(modality_key, janela=janela, base_estatistica=base_estatistica)
        if not somas.get("sucesso") or not digitos.get("sucesso"):
            return {
                "sucesso": False,
                "erro": somas.get("erro") or digitos.get("erro") or "Erro ao calcular estatísticas.",
            }

        Base = cls._base(modality_key)
        cfg = Base._cfg()
        pad = cfg.get("pad_width", 2)
        atual = None
        if conjunto_base:
            pool = sorted({int(x) for x in conjunto_base})
            atual = digitos_de_pool(pool, pad)
            atual["dezenas"] = pool
            atual["qtd_dezenas"] = len(pool)
            atual["faixa_soma_historica"] = faixa_da_soma(atual["soma"])  # só referência

        return {
            "sucesso": True,
            "historico_somas": somas["resumo"],
            "distribuicao_faixas": somas["distribuicao_faixas"],
            "historico_digitos": digitos["resumo"],
            "resumo_por_quantidade": digitos["resumo_por_quantidade"],
            "painel_digitos": digitos["painel_digitos"],
            "conjunto_atual": atual,
            "total_concursos": somas["total_concursos"],
            "ultimo_concurso": somas["ultimo_concurso"],
            "janela": somas["janela"],
            "base_estatistica": somas["base_estatistica"],
            "nota": (
                "Referência histórica = soma e dígitos dos sorteios oficiais (7 dezenas). "
                "A soma atual do conjunto-base usa todas as dezenas selecionadas."
            ),
        }

    @classmethod
    def validar_conjunto_base(
        cls,
        modality_key: str,
        conjunto_base: List[int],
        *,
        soma_min: Optional[int] = None,
        soma_max: Optional[int] = None,
        digitos_exigidos: Optional[int] = None,
        exigir_digitos: bool = False,
    ) -> Dict[str, Any]:
        """
        Valida o conjunto-base (soma das N dezenas + qtd de dígitos distintos).
        Não altera geração — apenas gate de salvamento.
        """
        Base = cls._base(modality_key)
        cfg = Base._cfg()
        pad = cfg.get("pad_width", 2)
        pool = sorted({int(x) for x in conjunto_base})
        atual = digitos_de_pool(pool, pad)
        erros: List[str] = []
        avisos: List[str] = []

        if soma_min is not None and atual["soma"] < int(soma_min):
            erros.append(
                f"Soma atual {atual['soma']} abaixo do mínimo permitido ({soma_min})."
            )
        if soma_max is not None and atual["soma"] > int(soma_max):
            erros.append(
                f"Soma atual {atual['soma']} acima do máximo permitido ({soma_max})."
            )
        if exigir_digitos and digitos_exigidos is not None:
            if atual["qtd"] != int(digitos_exigidos):
                erros.append(
                    f"Exigidos {digitos_exigidos} dígitos distintos; "
                    f"o conjunto tem {atual['qtd']} ({atual['digitos_fmt']})."
                )

        ok = len(erros) == 0
        return {
            "sucesso": ok,
            "valido": ok,
            "erros": erros,
            "avisos": avisos,
            "conjunto": {
                "dezenas": pool,
                "soma": atual["soma"],
                "qtd_digitos": atual["qtd"],
                "digitos": atual["digitos"],
                "digitos_fmt": atual["digitos_fmt"],
            },
            "regras": {
                "soma_min": soma_min,
                "soma_max": soma_max,
                "digitos_exigidos": digitos_exigidos if exigir_digitos else None,
                "exigir_digitos": bool(exigir_digitos),
            },
        }
