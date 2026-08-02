# -*- coding: utf-8 -*-
"""Motor de enriquecimento — conjuntos, cruzamentos e agregados (reutilizável)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

CRUZAMENTOS = (
    ("pares", "sequencias", "Pares × Sequências"),
    ("pares", "repetidos", "Pares × Repetidos"),
    ("pares", "finais", "Pares × Finais Iguais"),
    ("impares", "sequencias", "Ímpares × Sequências"),
    ("impares", "repetidos", "Ímpares × Repetidos"),
    ("impares", "finais", "Ímpares × Finais Iguais"),
    ("repetidos", "sequencias", "Repetidos × Sequências"),
    ("repetidos", "finais", "Repetidos × Finais Iguais"),
    ("sequencias", "finais", "Sequências × Finais Iguais"),
)

GRUPOS = ("pares", "impares", "repetidos", "sequencias", "finais")


def _seqs_grupos(nums: Sequence[int]) -> List[List[int]]:
    sorted_n = sorted(int(x) for x in nums)
    grupos: List[List[int]] = []
    i = 0
    while i < len(sorted_n):
        if i < len(sorted_n) - 1 and sorted_n[i + 1] - sorted_n[i] == 1:
            g = [sorted_n[i]]
            while i < len(sorted_n) - 1 and sorted_n[i + 1] - sorted_n[i] == 1:
                i += 1
                g.append(sorted_n[i])
            grupos.append(g)
        i += 1
    return grupos


def _finais_grupos(nums: Sequence[int]) -> List[List[int]]:
    by_d: Dict[int, List[int]] = {}
    for n in nums:
        by_d.setdefault(int(n) % 10, []).append(int(n))
    return [sorted(g) for g in by_d.values() if len(g) > 1]


def _bloco(nome: str, itens: Sequence[int], *, extra: Any = None) -> Dict[str, Any]:
    lista = sorted(int(x) for x in itens)
    out: Dict[str, Any] = {
        "nome": nome,
        "quantidade": len(lista),
        "dezenas": lista,
    }
    if extra is not None:
        out["detalhe"] = extra
    return out


def conjuntos_concurso(
    numeros: Sequence[int],
    anterior: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    nums = [int(x) for x in numeros]
    ant = {int(x) for x in (anterior or [])}

    pares = [n for n in nums if n % 2 == 0]
    impares = [n for n in nums if n % 2 != 0]
    repetidos = [n for n in nums if n in ant]
    seq_grupos = _seqs_grupos(nums)
    seq_flat = sorted({n for g in seq_grupos for n in g})
    fin_grupos = _finais_grupos(nums)
    fin_flat = sorted({n for g in fin_grupos for n in g})

    sets: Dict[str, Set[int]] = {
        "pares": set(pares),
        "impares": set(impares),
        "repetidos": set(repetidos),
        "sequencias": set(seq_flat),
        "finais": set(fin_flat),
    }

    basicos = {
        "pares": _bloco("Pares", pares),
        "impares": _bloco("Ímpares", impares),
        "repetidos": _bloco("Repetidos", repetidos),
        "sequencias": _bloco(
            "Sequências",
            seq_flat,
            extra={"grupos": seq_grupos, "qtd_grupos": len(seq_grupos)},
        ),
        "finais": _bloco(
            "Finais Iguais",
            fin_flat,
            extra={"grupos": fin_grupos, "qtd_grupos": len(fin_grupos)},
        ),
    }

    cruzamentos = []
    for a, b, label in CRUZAMENTOS:
        inter = sorted(sets[a] & sets[b])
        denom = max(1, len(nums))
        cruzamentos.append({
            "id": f"{a}_x_{b}",
            "label": label,
            "grupo_a": a,
            "grupo_b": b,
            "quantidade": len(inter),
            "dezenas": inter,
            "percentual_concurso": round(100.0 * len(inter) / denom, 1),
        })

    return {
        "numeros": nums,
        "soma": sum(nums),
        "amplitude": (max(nums) - min(nums)) if nums else 0,
        "digitos_unicos": sorted({int(d) for n in nums for d in f"{n:02d}"}),
        "basicos": basicos,
        "cruzamentos": cruzamentos,
        "sets_sizes": {k: len(v) for k, v in sets.items()},
    }


def _anterior_na_lista(
    lista: List[Dict[str, Any]],
    index: int,
    ordem: str,
) -> Optional[List[int]]:
    if ordem == "desc":
        if index < len(lista) - 1:
            return [int(x) for x in lista[index + 1].get("numeros") or []]
    else:
        if index > 0:
            return [int(x) for x in lista[index - 1].get("numeros") or []]
    return None


def analisar_janela(
    sorteios: List[Dict[str, Any]],
    *,
    ordem: str = "desc",
    concurso_foco: Optional[int] = None,
) -> Dict[str, Any]:
    """Analisa a lista já filtrada (mesma da aba Escolha)."""
    if not sorteios:
        return {"sucesso": False, "erro": "Sem sorteios na janela."}

    detalhes: List[Dict[str, Any]] = []
    cruz_freq = Counter()  # id -> concursos com interseção > 0
    cruz_sum_qtd = Counter()
    medias = Counter()
    cont_tem = Counter()

    for i, s in enumerate(sorteios):
        nums = [int(x) for x in s.get("numeros") or []]
        ant = _anterior_na_lista(sorteios, i, ordem)
        det = conjuntos_concurso(nums, ant)
        det["concurso"] = int(s["concurso"])
        det["data"] = s.get("data") or ""
        det["index"] = i
        detalhes.append(det)

        for g in GRUPOS:
            q = int(det["basicos"][g]["quantidade"])
            medias[g] += q
            if q > 0:
                cont_tem[g] += 1
        for c in det["cruzamentos"]:
            cruz_sum_qtd[c["id"]] += c["quantidade"]
            if c["quantidade"] > 0:
                cruz_freq[c["id"]] += 1

    n = len(sorteios)
    resumo = {
        "total_sorteios": n,
        "medias": {g: round(medias[g] / n, 2) for g in GRUPOS},
        "pct_com": {g: round(100.0 * cont_tem[g] / n, 1) for g in GRUPOS},
        "cruzamentos_janela": [
            {
                "id": f"{a}_x_{b}",
                "label": label,
                "concursos_com_intersecao": int(cruz_freq[f"{a}_x_{b}"]),
                "percentual_janela": round(100.0 * cruz_freq[f"{a}_x_{b}"] / n, 1),
                "media_dezenas": round(cruz_sum_qtd[f"{a}_x_{b}"] / n, 2),
            }
            for a, b, label in CRUZAMENTOS
        ],
    }

    # heatmap 5x5 (simétrico, diagonal = tamanho médio do grupo)
    labels = list(GRUPOS)
    matrix = [[0.0 for _ in labels] for _ in labels]
    for i, ga in enumerate(labels):
        for j, gb in enumerate(labels):
            if i == j:
                matrix[i][j] = resumo["medias"][ga]
            else:
                found = next(
                    (x for x in resumo["cruzamentos_janela"]
                     if x["id"] in (f"{ga}_x_{gb}", f"{gb}_x_{ga}")),
                    None,
                )
                matrix[i][j] = found["percentual_janela"] if found else 0.0

    # foco: último da lista (primeiro se desc = mais recente)
    if concurso_foco is not None:
        foco = next((d for d in detalhes if d["concurso"] == int(concurso_foco)), None)
    else:
        foco = detalhes[0] if ordem == "desc" else detalhes[-1]
    if foco is None:
        foco = detalhes[0]

    return {
        "sucesso": True,
        "ordem": ordem,
        "resumo": resumo,
        "heatmap": {"labels": labels, "matrix": matrix},
        "concurso_foco": foco,
        "concursos": [{"concurso": d["concurso"], "data": d["data"]} for d in detalhes],
        # série para gráficos: qtd por grupo ao longo da lista (ordem da tela)
        "series": {
            g: [d["basicos"][g]["quantidade"] for d in detalhes]
            for g in GRUPOS
        },
        "series_concursos": [d["concurso"] for d in detalhes],
    }
