# -*- coding: utf-8 -*-
"""Auditoria Seção 11 — geração baseada em resultados reais do Dia de Sorte."""
from __future__ import annotations

import json
import math
import random
import sqlite3
import statistics
import sys
from collections import Counter
from pathlib import Path

DB = Path(r"D:\Loterias\LoteriasPosicao\AnalisePorPosicao--DiaDeSorte-Only\instance\diadesorte.db")
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
DEZ_MIN, DEZ_MAX, SORTEADAS = 1, 31, 7


def fmt2(n: int) -> str:
    return f"{int(n):02d}"


def analyze_sequences(nums):
    sequences = []
    i = 0
    while i < len(nums) - 1:
        if nums[i + 1] == nums[i] + 1:
            seq_end = i + 1
            while seq_end < len(nums) - 1 and nums[seq_end + 1] == nums[seq_end] + 1:
                seq_end += 1
            sequences.append({"length": seq_end - i + 1, "numbers": nums[i : seq_end + 1]})
            i = seq_end
        i += 1
    return sequences


def complete_analysis(numbers, month_name=""):
    nums = sorted(int(x) for x in numbers)
    sequences = analyze_sequences(nums)
    if len(sequences) == 1:
        seq_qtde = sequences[0]["length"]
    elif len(sequences) > 1:
        seq_qtde = len(sequences)
    else:
        seq_qtde = 0
    if sequences:
        parts = []
        for seq in sequences:
            if seq["length"] >= 3:
                parts.append(f"{fmt2(seq['numbers'][0])}-{fmt2(seq['numbers'][-1])}")
            else:
                parts.append(",".join(fmt2(n) for n in seq["numbers"]))
        seq_quais = " ".join(parts)
    else:
        seq_quais = "-"
    finais = {}
    for num in nums:
        finais.setdefault(num % 10, []).append(num)
    fin_rep = [g for g in finais.values() if len(g) > 1]
    pares = sum(1 for n in nums if n % 2 == 0)
    digitos = sorted({int(d) for n in nums for d in f"{n:02d}"})
    return {
        "seq": seq_qtde,
        "seqQuais": seq_quais,
        "finais": len(fin_rep),
        "finaisQuais": " ".join(",".join(fmt2(x) for x in g) for g in fin_rep) if fin_rep else "-",
        "soma": sum(nums),
        "pares": pares,
        "impares": len(nums) - pares,
        "inicial": " ".join(str(n // 10) for n in nums),
        "final": " ".join(str(n % 10) for n in nums),
        "qtde": len(digitos),
        "key": "-".join(fmt2(n) for n in nums),
        "monthName": month_name or "",
        "numbers": nums,
    }


def repetitions(current, previous):
    if not previous:
        return {"count": 0, "list": [], "reptKey": "∅"}
    lst = [n for n in current if n in previous]
    return {
        "count": len(lst),
        "list": lst,
        "reptKey": ",".join(fmt2(n) for n in sorted(lst)) if lst else "∅",
    }


def fp_aposta(nums, month_name, prev_nums):
    an = complete_analysis(nums, month_name)
    rept = repetitions(an["numbers"], [int(x) for x in (prev_nums or [])])
    an["reptKey"] = rept["reptKey"]
    an["reptCount"] = rept["count"]
    return an


def load_real_draws():
    if not DB.exists():
        raise SystemExit(f"DB não encontrado: {DB}")
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    sql = (
        "SELECT concurso, d1, d2, d3, d4, d5, d6, d7, mes_num, mes_nome "
        "FROM sorteio_diadesorte ORDER BY concurso ASC"
    )
    rows = []
    for r in con.execute(sql):
        nums = sorted(int(r[f"d{i}"]) for i in range(1, 8))
        mes = (r["mes_nome"] or "").strip()
        if not mes and r["mes_num"] and 1 <= int(r["mes_num"]) <= 12:
            mes = MESES[int(r["mes_num"]) - 1]
        rows.append({"contest": int(r["concurso"]), "numbers": nums, "monthName": mes})
    con.close()
    return rows


def too_similar(a, b):
    if a["key"] == b["key"]:
        return True
    hits = 0
    for k in ("soma", "pares", "seq", "finais", "inicial", "final"):
        if a.get(k) == b.get(k):
            hits += 1
    if a.get("monthName") and b.get("monthName") and a["monthName"] == b["monthName"]:
        hits += 1
    return hits >= 4


def build_forbid(recent, chrono):
    forbid_seq, forbid_fin, forbid_rept = set(), set(), set()
    for i, c in enumerate(recent):
        if i > 0:
            prev = recent[i - 1]["numbers"]
        elif len(chrono) > len(recent):
            prev = chrono[len(chrono) - len(recent) - 1]["numbers"]
        else:
            prev = []
        fp = fp_aposta(c["numbers"], c["monthName"], prev)
        forbid_seq.add(f"{fp['seq']}|{fp['seqQuais']}")
        forbid_fin.add(f"{fp['finais']}|{fp['finaisQuais']}")
        forbid_rept.add(fp["reptKey"])
    return forbid_seq, forbid_fin, forbid_rept


def pick_weighted(items, weights):
    total = sum(weights)
    if total <= 0:
        return random.choice(items)
    r = random.random() * total
    for it, w in zip(items, weights):
        r -= w
        if r <= 0:
            return it
    return items[-1]


def weight_map(hist):
    return dict(Counter(hist))


def quota_bag(alvo, weights, fallback=1, smooth=True):
    """Espelha _paresQuotaBag: cotas proporcionais às frequências reais."""
    items = [k for k, w in weights.items() if w and w > 0]
    if not items:
        return [fallback] * alvo
    total_w = sum(weights[k] for k in items)
    raw = {k: (weights[k] / total_w) * alvo for k in items}
    counts = {k: int(math.floor(raw[k])) for k in items}
    rem = alvo - sum(counts.values())
    frac = sorted(items, key=lambda k: (raw[k] - counts[k]), reverse=True)
    for i in range(rem):
        counts[frac[i % len(frac)]] += 1
    bag = []
    for k in sorted(items):
        bag.extend([k] * counts[k])
    if smooth and len(bag) > 1:
        # embaralha leve mantendo proporção
        random.shuffle(bag)
    return bag[:alvo]


def try_build(want_pares, freq, last_nums, want_rept):
    """Monta aposta com exatamente want_rept overlaps com o último sorteio."""
    pool = list(range(DEZ_MIN, DEZ_MAX + 1))
    weights = [1 + freq.get(n, 0) * 2 for n in pool]
    picked = []
    local_pool = pool[:]
    local_w = weights[:]
    last_set = set(last_nums)
    need_rept = max(0, min(int(want_rept or 0), len(last_nums), SORTEADAS))

    # 1) Semeia EXATAMENTE need_rept dezenas do último
    if need_rept > 0 and last_nums:
        seeds = last_nums[:]
        random.shuffle(seeds)
        for n in seeds:
            if len(picked) >= need_rept:
                break
            if n not in local_pool:
                continue
            need_par = sum(1 for x in picked if x % 2 == 0)
            is_par = n % 2 == 0
            if is_par and need_par >= want_pares:
                continue
            if (not is_par) and (len(picked) - need_par) >= (SORTEADAS - want_pares):
                continue
            ix = local_pool.index(n)
            picked.append(n)
            local_pool.pop(ix)
            local_w.pop(ix)

    # 2) Remove o restante do último → evita Rept 3/4/5 acidental
    for i in range(len(local_pool) - 1, -1, -1):
        if local_pool[i] in last_set:
            local_pool.pop(i)
            local_w.pop(i)

    while len(picked) < SORTEADAS and local_pool:
        need_par = sum(1 for n in picked if n % 2 == 0)
        remain = SORTEADAS - len(picked)
        need_imp = SORTEADAS - want_pares - (len(picked) - need_par)
        cands = list(zip(local_pool, local_w))
        if need_par >= want_pares:
            cands = [(n, w) for n, w in cands if n % 2 == 1]
        elif need_imp <= 0:
            cands = [(n, w) for n, w in cands if n % 2 == 0]
        elif remain == 1:
            if need_par < want_pares:
                cands = [(n, w) for n, w in cands if n % 2 == 0]
            else:
                cands = [(n, w) for n, w in cands if n % 2 == 1]
        if not cands:
            cands = list(zip(local_pool, local_w))
        choice = pick_weighted([n for n, _ in cands], [w for _, w in cands])
        ix = local_pool.index(choice)
        picked.append(choice)
        local_pool.pop(ix)
        local_w.pop(ix)
    return sorted(picked)


def generate_batch(chrono, janela, qtd, pares_mode="fix_4", soma_mode="padrao", existing=None, max_tries=None):
    existing = set(existing or [])
    recent = chrono[-janela:] if janela > 0 else chrono[:]
    last = chrono[-1]
    last_nums = last["numbers"]
    prev_last = chrono[-2]["numbers"] if len(chrono) > 1 else []
    last_fp = fp_aposta(last_nums, last["monthName"], prev_last)
    forbid_seq, forbid_fin, forbid_rept = build_forbid(recent, chrono)

    freq = Counter()
    pares_hist, soma_hist, mes_hist = [], [], []
    rept_count_hist = []
    for i, c in enumerate(recent):
        if i > 0:
            prev = recent[i - 1]["numbers"]
        elif len(chrono) > len(recent):
            prev = chrono[len(chrono) - len(recent) - 1]["numbers"]
        else:
            prev = []
        fp = fp_aposta(c["numbers"], c["monthName"], prev)
        for n in c["numbers"]:
            freq[n] += 1
        pares_hist.append(fp["pares"])
        soma_hist.append(fp["soma"])
        rept_count_hist.append(fp["reptCount"])
        if c["monthName"]:
            mes_hist.append(c["monthName"])

    if pares_mode.startswith("fix_"):
        want_fixed = int(pares_mode.split("_")[1])
        bag = [want_fixed] * qtd
        exact_pares = True
    elif pares_mode == "aleatorio":
        # viés dos resultados reais da janela
        cnt = Counter(pares_hist)
        weights = {p: max(0.35, float(cnt.get(p, 0))) for p in range(0, SORTEADAS + 1)}
        items = list(weights.keys())
        ws = [weights[i] for i in items]
        bag = [pick_weighted(items, ws) for _ in range(qtd)]
        exact_pares = True
    else:
        cnt = Counter(pares_hist)
        items = list(cnt.keys()) or [4]
        ws = [cnt[i] for i in items]
        bag = [pick_weighted(items, ws) for _ in range(qtd)]
        exact_pares = True

    # Cotas de Rept por frequência REAL da janela
    rept_weights = weight_map(rept_count_hist)
    if "∅" in forbid_rept:
        rept_weights.pop(0, None)
    if not rept_weights:
        rept_weights = {1: 4, 2: 4, 3: 1}
    rept_bag = quota_bag(qtd, rept_weights, fallback=1, smooth=True)
    real_rept_dist = dict(sorted(Counter(rept_count_hist).items()))

    # soma
    soma_target = None
    soma_tol = 35
    soma_mode_chk = "soft"
    if soma_mode == "frequente" and soma_hist:
        soma_target = Counter(soma_hist).most_common(1)[0][0]
        soma_mode_chk = "exact"
        soma_tol = 0
    elif soma_mode == "alta" and soma_hist:
        soma_target = max(soma_hist)
        span = max(soma_hist) - min(soma_hist)
        soma_tol = max(3, span // 5 or 3)
        soma_mode_chk = "min"
    elif soma_mode == "baixa" and soma_hist:
        soma_target = min(soma_hist)
        span = max(soma_hist) - min(soma_hist)
        soma_tol = max(3, span // 5 or 3)
        soma_mode_chk = "max"
    elif soma_mode == "media" and soma_hist:
        avg = statistics.mean(soma_hist)
        soma_target = round(avg)
        std = statistics.pstdev(soma_hist) if len(soma_hist) > 1 else 4
        soma_tol = max(2, round(std or 4))
        soma_mode_chk = "near"

    max_tries = max_tries or max(qtd * 4000, 20000)
    aprovadas = []
    tries = 0
    bag_i = 0
    rept_i = 0
    fail_streak = 0

    def soma_ok(s):
        if soma_target is None or soma_mode_chk == "soft":
            if soma_mode == "padrao" and soma_hist:
                soft = Counter(soma_hist).most_common(1)[0][0]
                return abs(s - soft) <= 35
            return True
        if soma_mode_chk == "exact":
            return s == soma_target
        if soma_mode_chk == "min":
            return s >= soma_target - soma_tol
        if soma_mode_chk == "max":
            return s <= soma_target + soma_tol
        if soma_mode_chk == "near":
            return abs(s - soma_target) <= soma_tol
        return True

    while len(aprovadas) < qtd and tries < max_tries:
        tries += 1
        want = bag[bag_i] if bag_i < len(bag) else pick_weighted(
            list(range(0, SORTEADAS + 1)),
            [max(0.35, float(Counter(pares_hist).get(p, 0))) for p in range(0, SORTEADAS + 1)],
        )
        if rept_i < len(rept_bag):
            want_rept = rept_bag[rept_i]
        else:
            items = list(rept_weights.keys()) or [1]
            ws = [rept_weights[k] for k in items]
            want_rept = pick_weighted(items, ws)
        nums = try_build(want, freq, last_nums, want_rept)
        if len(nums) != SORTEADAS or len(set(nums)) != SORTEADAS:
            fail_streak += 1
            if fail_streak >= 120:
                bag_i += 1
                rept_i += 1
                fail_streak = 0
            continue
        key = "-".join(fmt2(n) for n in nums)
        if key in existing or any(a["key"] == key for a in aprovadas):
            fail_streak += 1
            if fail_streak >= 120:
                bag_i += 1
                rept_i += 1
                fail_streak = 0
            continue
        mes_name = ""
        if mes_hist:
            cand = [m for m in mes_hist if m != last["monthName"]] or mes_hist
            mes_name = random.choice(cand)
        fp = fp_aposta(nums, mes_name, last_nums)
        rejected = (
            fp["reptCount"] != want_rept
            or f"{fp['seq']}|{fp['seqQuais']}" in forbid_seq
            or f"{fp['finais']}|{fp['finaisQuais']}" in forbid_fin
            or fp["reptKey"] in forbid_rept
            or too_similar(fp, last_fp)
            or (exact_pares and fp["pares"] != want)
            or (not soma_ok(fp["soma"]))
        )
        if rejected:
            fail_streak += 1
            if fail_streak >= 120:
                bag_i += 1
                rept_i += 1
                fail_streak = 0
            continue
        existing.add(key)
        aprovadas.append(fp)
        bag_i += 1
        rept_i += 1
        fail_streak = 0

    return {
        "aprovadas": aprovadas,
        "tries": tries,
        "forbid_seq": forbid_seq,
        "forbid_fin": forbid_fin,
        "forbid_rept": forbid_rept,
        "last_fp": last_fp,
        "recent": recent,
        "qtd_ok": len(aprovadas) == qtd,
        "real_rept_dist": real_rept_dist,
    }


def audit_batch(result, label):
    fails = []
    oks = []
    aprovadas = result["aprovadas"]
    forbid_seq = result["forbid_seq"]
    forbid_fin = result["forbid_fin"]
    forbid_rept = result["forbid_rept"]

    keys = [a["key"] for a in aprovadas]
    if len(keys) != len(set(keys)):
        fails.append("DUPLICIDADE no lote")
    else:
        oks.append("sem duplicidade no lote")

    for a in aprovadas:
        # recalcular indicadores
        again = complete_analysis(a["numbers"], a["monthName"])
        for field in ("soma", "pares", "impares", "seq", "finais", "inicial", "final", "qtde"):
            if again[field] != a[field]:
                fails.append(f"indicador {field} incoerente em {a['key']}")
        seq_key = f"{a['seq']}|{a['seqQuais']}"
        fin_key = f"{a['finais']}|{a['finaisQuais']}"
        if seq_key in forbid_seq:
            fails.append(f"SEQ proibido: {seq_key} em {a['key']}")
        if fin_key in forbid_fin:
            fails.append(f"FINAIS proibido: {fin_key} em {a['key']}")
        if a["reptKey"] in forbid_rept:
            fails.append(f"REPT proibido: {a['reptKey']} em {a['key']}")

    pares_dist = Counter(a["pares"] for a in aprovadas)
    rept_dist = Counter(a["reptCount"] for a in aprovadas)
    high_rept = sum(v for k, v in rept_dist.items() if k >= 3)
    # Alerta: geradas com Rept>=3 não devem dominar (padrão real = 1–2)
    if aprovadas and high_rept > max(1, len(aprovadas) // 4):
        fails.append(f"REPT alto demais: {dict(rept_dist)} (janela real {result.get('real_rept_dist')})")
    else:
        oks.append(f"rept_dist={dict(sorted(rept_dist.items()))} vs real={result.get('real_rept_dist')}")
    return {
        "label": label,
        "geradas": len(aprovadas),
        "alvo_ok": result["qtd_ok"],
        "tries": result["tries"],
        "pares_dist": dict(sorted(pares_dist.items())),
        "rept_dist": dict(sorted(rept_dist.items())),
        "real_rept_dist": result.get("real_rept_dist"),
        "fails": fails,
        "oks": oks,
        "ok": result["qtd_ok"] and not fails,
    }


def main():
    random.seed(42)
    chrono = load_real_draws()
    print(f"RESULTADOS REAIS carregados: {len(chrono)} concursos")
    print(f"Ultimo: {chrono[-1]['contest']} -> {chrono[-1]['numbers']} ({chrono[-1]['monthName']})")

    reports = []
    existing = set()

    # 1) geração padrão 5 ciclos x 10 com fix_4 e janela 10
    for i in range(5):
        r = generate_batch(chrono, 10, 10, "fix_4", "padrao", existing)
        for a in r["aprovadas"]:
            existing.add(a["key"])
        rep = audit_batch(r, f"GERAR10 ciclo{i+1} fix_4 janela10")
        reports.append(rep)
        print(
            rep["label"], "geradas", rep["geradas"], "ok" if rep["ok"] else "FALHA",
            "pares", rep["pares_dist"], "rept", rep["rept_dist"], "real", rep["real_rept_dist"],
            "tries", rep["tries"],
        )
        if rep["fails"][:3]:
            print("  fails:", rep["fails"][:3])

    # 2) geração adicional +50 aleatorio
    r = generate_batch(chrono, 10, 50, "aleatorio", "padrao", existing)
    for a in r["aprovadas"]:
        existing.add(a["key"])
    rep = audit_batch(r, "GERAR+50 aleatorio janela10")
    reports.append(rep)
    print(
        rep["label"], "geradas", rep["geradas"], "ok" if rep["ok"] else "FALHA",
        "pares", rep["pares_dist"], "rept", rep["rept_dist"], "real", rep["real_rept_dist"],
    )

    # 3) soma frequente / alta / media
    for sm in ("frequente", "alta", "baixa", "media"):
        r = generate_batch(chrono, 10, 10, "fix_4", sm, set(existing))
        rep = audit_batch(r, f"SOMA {sm} fix_4 x10")
        reports.append(rep)
        somas = [a["soma"] for a in r["aprovadas"]]
        print(rep["label"], "geradas", rep["geradas"], "somas", somas[:5], "..." if len(somas) > 5 else "", "ok" if rep["ok"] else "FALHA")

    # 4) janela 20 — o caso problemático
    r = generate_batch(chrono, 20, 10, "aleatorio", "padrao", set())
    rep = audit_batch(r, "GERAR10 aleatorio janela20")
    reports.append(rep)
    print(rep["label"], "geradas", rep["geradas"], "ok" if rep["ok"] else "FALHA", "tries", rep["tries"], "pares", rep["pares_dist"], "rept", rep["rept_dist"], "real", rep["real_rept_dist"])
    if rep["fails"][:5]:
        print("  fails:", rep["fails"][:5])

    # 5) fix_3 diversidade forçada
    r = generate_batch(chrono, 10, 20, "fix_3", "padrao", set())
    rep = audit_batch(r, "fix_3 x20")
    reports.append(rep)
    print(rep["label"], "geradas", rep["geradas"], "pares", rep["pares_dist"], "rept", rep["rept_dist"], "ok" if rep["ok"] else "FALHA")

    # 6) acumulação total keys
    print("TOTAL keys únicas acumuladas nos testes sequenciais:", len(existing))

    # resumo
    print("\n=== CHECKLIST ===")
    falhas = [r for r in reports if not r["ok"]]
    print(f"Cenários OK: {len(reports) - len(falhas)}/{len(reports)}")
    for r in falhas:
        print("FALHA:", r["label"], "geradas", r["geradas"], r["fails"][:5])

    out = Path(__file__).with_name("_audit_secao11_report.json")
    out.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Relatório:", out)
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
