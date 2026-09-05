# -*- coding: utf-8 -*-
"""Geometria de diagonais no volante (mesma regra da Seção 12/13)."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

_Dir = str  # "down" | "up"


def volante_rows(dmin: int = 1, dmax: int = 31, cols: int = 10) -> List[Tuple[int, int]]:
    if int(dmin) == 1 and int(dmax) == 31:
        return [(1, 10), (11, 20), (21, 30), (31, 31)]
    out: List[Tuple[int, int]] = []
    d = int(dmin)
    step = max(1, int(cols))
    while d <= int(dmax):
        out.append((d, min(int(dmax), d + step - 1)))
        d += step
    return out


def pos_map(rows: Sequence[Tuple[int, int]]) -> Dict[int, Tuple[int, int]]:
    m: Dict[int, Tuple[int, int]] = {}
    for r, (a, b) in enumerate(rows):
        for n in range(a, b + 1):
            m[n] = (r, n - a)
    return m


def geom_dir(nums: Sequence[int], pmap: Dict[int, Tuple[int, int]]) -> _Dir:
    cells = [pmap[int(n)] for n in nums if int(n) in pmap]
    if len(cells) < 2:
        return "down"
    cells.sort(key=lambda x: (x[0], x[1]))
    first, last = cells[0], cells[-1]
    if last[1] > first[1]:
        return "down"
    if last[1] < first[1]:
        return "up"
    return "down"


def order_by_geom(nums: Sequence[int], pmap: Dict[int, Tuple[int, int]]) -> List[int]:
    return sorted(
        (int(n) for n in nums if int(n) in pmap),
        key=lambda n: (pmap[n][0], pmap[n][1], n),
    )


def seg_key(dir_: str, nums: Sequence[int]) -> str:
    return f"{dir_}:{'-'.join(str(int(x)) for x in nums)}"


def diag_lines(rows: Sequence[Tuple[int, int]]) -> List[Dict[str, Any]]:
    down: Dict[int, List[Dict[str, int]]] = defaultdict(list)
    up: Dict[int, List[Dict[str, int]]] = defaultdict(list)
    for r, (a, b) in enumerate(rows):
        for n in range(a, b + 1):
            c = n - a
            down[c - r].append({"n": n, "r": r, "c": c})
            up[c + r].append({"n": n, "r": r, "c": c})
    pmap = pos_map(rows)
    lines: List[Dict[str, Any]] = []

    def flush(mapa: Dict[int, List[Dict[str, int]]], family: str) -> None:
        for arr in mapa.values():
            arr.sort(key=lambda x: (x["r"], x["c"]))
            run: List[Dict[str, int]] = []
            for cell in arr:
                if not run or cell["r"] == run[-1]["r"] + 1:
                    run.append(cell)
                else:
                    if len(run) >= 2:
                        nums = [x["n"] for x in run]
                        lines.append({"dir": geom_dir(nums, pmap), "nums": nums, "family": family})
                    run = [cell]
            if len(run) >= 2:
                nums = [x["n"] for x in run]
                lines.append({"dir": geom_dir(nums, pmap), "nums": nums, "family": family})

    flush(down, "down")
    flush(up, "up")
    return lines


def diag_runs_in_draw(
    chosen: Set[int],
    lines: Sequence[Dict[str, Any]],
    pmap: Dict[int, Tuple[int, int]],
) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for line in lines:
        cur: List[int] = []
        for n in (line.get("nums") or []):
            if n in chosen:
                cur.append(int(n))
            else:
                if len(cur) >= 2:
                    nums = order_by_geom(cur, pmap)
                    dir_ = geom_dir(nums, pmap)
                    key = seg_key(dir_, nums)
                    if key not in seen:
                        seen.add(key)
                        runs.append({"dir": dir_, "nums": nums, "key": key, "len": len(nums)})
                cur = []
        if len(cur) >= 2:
            nums = order_by_geom(cur, pmap)
            dir_ = geom_dir(nums, pmap)
            key = seg_key(dir_, nums)
            if key not in seen:
                seen.add(key)
                runs.append({"dir": dir_, "nums": nums, "key": key, "len": len(nums)})
    return runs


def padrao_de(nums: Sequence[int]) -> str:
    return " ".join(str(int(n) // 10) for n in sorted(int(x) for x in nums))


def padrao_compativel(padrao: str, nums: Sequence[int]) -> bool:
    digs = [int(x) for x in str(padrao).replace(",", " ").replace("-", " ").split() if x.strip().isdigit()]
    if not digs:
        return False
    need = Counter(digs)
    have = Counter(int(n) // 10 for n in nums)
    return all(need[d] >= have[d] for d in have)


def _fmt2(n: int) -> str:
    return f"{int(n):02d}"


def _pack_seg(key: str, vezes: int, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta = meta or {}
    nums = list(meta.get("nums") or [])
    if not nums and ":" in key:
        try:
            nums = [int(x) for x in key.split(":", 1)[1].split("-") if x]
        except ValueError:
            nums = []
    dir_ = str(meta.get("dir") or (key.split(":", 1)[0] if ":" in key else "down"))
    ln = int(meta.get("len") or len(nums) or 2)
    tipo = "trinca" if ln >= 3 else "dupla"
    return {
        "key": key,
        "dir": dir_,
        "dir_sym": "↘" if dir_ == "down" else "↗",
        "nums": nums,
        "nums_fmt": "-".join(_fmt2(x) for x in nums),
        "len": ln,
        "tipo": tipo,
        "vezes": int(vezes),
    }


def cruzar_linhas(
    linhas: Iterable[Dict[str, Any]],
    *,
    dmin: int = 1,
    dmax: int = 31,
    cols: int = 10,
    top_n: int = 3,
) -> Dict[str, Any]:
    """Por padrão inicial: quantas vezes saiu com diagonal e quais segmentos mais acompanharam."""
    rows = volante_rows(dmin, dmax, cols)
    lines = diag_lines(rows)
    pmap = pos_map(rows)
    por: Dict[str, Dict[str, Any]] = {}
    ranking: Counter = Counter()
    meta_global: Dict[str, Dict[str, Any]] = {}
    n_draws = 0
    n_com = 0
    for l in linhas:
        dez = [int(x) for x in (l.get("dezenas") or [])]
        if not dez:
            continue
        n_draws += 1
        p = str(l.get("padrao_inicial") or "").strip() or padrao_de(dez)
        runs = [r for r in diag_runs_in_draw(set(dez), lines, pmap) if 2 <= int(r.get("len") or 0) <= 3]
        bucket = por.setdefault(p, {"n": 0, "n_diag": 0, "segs": Counter(), "meta": {}})
        bucket["n"] += 1
        if not runs:
            continue
        n_com += 1
        bucket["n_diag"] += 1
        for r in runs:
            k = r["key"]
            bucket["segs"][k] += 1
            ranking[k] += 1
            bucket["meta"][k] = r
            meta_global[k] = r

    por_out: Dict[str, Dict[str, Any]] = {}
    for p, b in por.items():
        top = [_pack_seg(k, v, b["meta"].get(k)) for k, v in b["segs"].most_common(top_n)]
        n = int(b["n"])
        nd = int(b["n_diag"])
        por_out[p] = {
            "n_com_diagonal": nd,
            "pct_com_diagonal": round(100.0 * nd / max(1, n), 1),
            "top_diagonais": top,
        }

    ranking_top = [_pack_seg(k, v, meta_global.get(k)) for k, v in ranking.most_common(12)]
    return {
        "por_padrao": por_out,
        "ranking_diagonais": ranking_top,
        "n_concursos": n_draws,
        "n_com_diagonal": n_com,
        "pct_com_diagonal": round(100.0 * n_com / max(1, n_draws), 1),
    }
