# -*- coding: utf-8 -*-
"""DNA estatístico da modalidade — histórico real, sem previsão."""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from resumo_modalidade.specs import ResumoSpec, faixa_de, get_resumo_spec, tem_resumo_modalidade


def _fmt2(n: int) -> str:
    return f"{int(n):02d}"


def _fmt_lista(nums: Sequence[int]) -> str:
    return ", ".join(_fmt2(x) for x in nums)


def _pct(n: int, total: int, nd: int = 1) -> float:
    if not total:
        return 0.0
    return round(100.0 * n / total, nd)


def _moda(counter: Counter):
    if not counter:
        return None, 0, 0.0
    val, q = counter.most_common(1)[0]
    return val, q, _pct(q, sum(counter.values()))


def _dist(counter: Counter, total: int, top: Optional[int] = None) -> List[Dict[str, Any]]:
    items = counter.most_common(top) if top else counter.most_common()
    return [{"valor": k, "qtd": int(v), "pct": _pct(v, total)} for k, v in items]


def _sequencias(nums: Sequence[int]) -> List[List[int]]:
    ordenadas = sorted(int(x) for x in nums)
    seqs: List[List[int]] = []
    i = 0
    while i < len(ordenadas):
        j = i
        while j + 1 < len(ordenadas) and ordenadas[j + 1] - ordenadas[j] == 1:
            j += 1
        if j > i:
            seqs.append(ordenadas[i : j + 1])
        i = j + 1
    return seqs


def _soma_bin(s: int) -> str:
    lo = (int(s) // 10) * 10
    return f"{lo}–{lo + 9}"


def _lag_rate(flags: Sequence[int], k: int) -> Optional[Dict[str, Any]]:
    if len(flags) <= k:
        return None
    both = 0
    prev = 0
    for i in range(k, len(flags)):
        if flags[i - k]:
            prev += 1
            if flags[i]:
                both += 1
    base = sum(1 for x in flags if x) / len(flags)
    if not prev:
        return None
    cond = both / prev
    return {
        "lag": k,
        "baseline_pct": round(base * 100, 1),
        "condicional_pct": round(cond * 100, 1),
        "delta_pp": round((cond - base) * 100, 1),
        "n_prev": prev,
    }


def _dezenas_row(s: Any) -> List[int]:
    if hasattr(s, "dezenas_lista"):
        try:
            dz = s.dezenas_lista()
        except TypeError:
            dz = s.dezenas_lista
        return [int(x) for x in dz]
    if hasattr(s, "digitos"):
        try:
            return [int(x) for x in s.digitos()]
        except TypeError:
            return [int(x) for x in s.digitos]
    if hasattr(s, "dezenas"):
        dz = s.dezenas() if callable(s.dezenas) else s.dezenas
        if isinstance(dz, set):
            return sorted(int(x) for x in dz)
        return [int(x) for x in dz]
    return []


def _carregar_sorteios(spec: ResumoSpec) -> List[Dict[str, Any]]:
    import importlib

    from models.shared import db

    if not spec.model_import:
        raise RuntimeError(f"Resumo {spec.modality_key} sem model_import")
    mod_name, cls_name = spec.model_import
    Model = getattr(importlib.import_module(mod_name), cls_name)
    rows = db.session.query(Model).order_by(Model.concurso.asc()).all()
    out: List[Dict[str, Any]] = []
    for s in rows:
        dez = _dezenas_row(s)
        if not dez:
            continue
        out.append({
            "concurso": int(s.concurso),
            "data": getattr(s, "data", "") or "",
            "dezenas": dez,
            "mes_num": getattr(s, "mes_num", None),
            "mes_nome": getattr(s, "mes_nome", None) or "",
        })
    return out


def _ciclos(sorteios: List[Dict[str, Any]], dmin: int, dmax: int) -> List[Dict[str, Any]]:
    ciclos: List[Dict[str, Any]] = []
    atuais: Dict[str, Any] = {
        "numero": 1,
        "inicio": None,
        "fim": None,
        "vistos": set(),
        "n": 0,
        "det": [],
        "aberto": True,
    }
    uni = set(range(int(dmin), int(dmax) + 1))
    universo = len(uni)
    for s in sorteios:
        dzs = set(int(x) for x in s["dezenas"])
        novas = dzs - atuais["vistos"]
        if atuais["inicio"] is None:
            atuais["inicio"] = s["concurso"]
        atuais["vistos"].update(dzs)
        atuais["n"] += 1
        atuais["det"].append({
            "concurso": s["concurso"],
            "novas": len(novas),
            "novas_lista": sorted(int(x) for x in novas),
            "preenchido": len(atuais["vistos"]),
            "faltam": universo - len(atuais["vistos"]),
        })
        if len(atuais["vistos"]) >= universo:
            atuais["fim"] = s["concurso"]
            atuais["aberto"] = False
            atuais["pendentes"] = []
            ciclos.append(atuais)
            atuais = {
                "numero": len(ciclos) + 1,
                "inicio": None,
                "fim": None,
                "vistos": set(),
                "n": 0,
                "det": [],
                "aberto": True,
            }
    if atuais["n"] > 0:
        atuais["pendentes"] = sorted(uni - atuais["vistos"])
        ciclos.append(atuais)
    return ciclos


def _faixa_stats(counter: Counter, series: List[int], n: int) -> Dict[str, Any]:
    mv, _q, mp = _moda(counter)
    return {
        "min": min(series) if series else 0,
        "max": max(series) if series else 0,
        "media": round(statistics.mean(series), 2) if series else 0,
        "moda": mv,
        "moda_pct": mp,
        "dist": _dist(counter, n),
    }


class ResumoModalidadeService:
    @classmethod
    def calcular(cls, modality_key: str = "diadesorte") -> Dict[str, Any]:
        if not tem_resumo_modalidade(modality_key):
            return {"sucesso": False, "erro": f"Resumo não habilitado para {modality_key}"}
        spec = get_resumo_spec(modality_key)
        try:
            sorteios = _carregar_sorteios(spec)
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}
        if not sorteios:
            return {"sucesso": False, "erro": "Sem sorteios no banco. Sincronize a modalidade."}
        return {"sucesso": True, **cls._analisar(spec, sorteios)}

    @classmethod
    def _analisar(cls, spec: ResumoSpec, sorteios: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(sorteios)
        n_s = spec.sorteadas
        uni = spec.dezena_max - spec.dezena_min + 1
        faixa_codigos = [f[0] for f in spec.faixas]
        faixa_labels = {f[0]: f[3] for f in spec.faixas}

        somas: List[int] = []
        pi: Counter = Counter()
        bma: Counter = Counter()
        cnt_f: Dict[str, Counter] = {c: Counter() for c in faixa_codigos}
        series_f: Dict[str, List[int]] = {c: [] for c in faixa_codigos}
        seq_qtd: Counter = Counter()
        seq_tam: Counter = Counter()
        tem_seq = 0
        finais_grupos: Counter = Counter()
        tem_final_igual = 0
        padrao_ocup: Counter = Counter()
        padrao_inicial: Counter = Counter()
        reps_ant: List[int] = []
        pares_list: List[int] = []
        impar_list: List[int] = []
        flags_seq: List[int] = []
        flags_final: List[int] = []
        flags_soma_alta: List[int] = []
        flags_b_ge3: List[int] = []
        flags_rep_ge2: List[int] = []

        prev: Optional[List[int]] = None
        freq_dez: Counter = Counter()
        last_idx: Dict[int, int] = {}
        for i_s, s in enumerate(sorteios):
            dz = sorted(int(x) for x in s["dezenas"])[:n_s]
            sm = sum(dz)
            somas.append(sm)
            pares = sum(1 for d in dz if d % 2 == 0)
            imp = len(dz) - pares
            pi[(pares, imp)] += 1
            pares_list.append(pares)
            impar_list.append(imp)
            for d in dz:
                freq_dez[d] += 1
                last_idx[d] = i_s

            counts = {c: 0 for c in faixa_codigos}
            for d in dz:
                c = faixa_de(d, spec)
                if c:
                    counts[c] += 1
            key_bma = tuple(counts[c] for c in faixa_codigos)
            bma[key_bma] += 1
            for c in faixa_codigos:
                cnt_f[c][counts[c]] += 1
                series_f[c].append(counts[c])

            seqs = _sequencias(dz)
            seq_qtd[len(seqs)] += 1
            if seqs:
                tem_seq += 1
                for g in seqs:
                    seq_tam[len(g)] += 1
            flags_seq.append(1 if seqs else 0)

            fins = Counter(d % 10 for d in dz)
            n_grupos = sum(1 for c in fins.values() if c >= 2)
            finais_grupos[n_grupos] += 1
            if n_grupos:
                tem_final_igual += 1
            flags_final.append(1 if n_grupos else 0)
            padrao_ocup["-".join(str(x) for x in sorted(fins.values(), reverse=True))] += 1
            padrao_inicial["-".join(str(d // 10) for d in dz)] += 1

            r = None
            if prev is not None:
                r = len(set(dz) & set(prev))
                reps_ant.append(r)
            flags_rep_ge2.append(1 if (r or 0) >= 2 else 0)
            prev = dz
            flags_b_ge3.append(1 if counts.get("B", 0) >= 3 else 0)

        med_soma = statistics.median(somas)
        flags_soma_alta = [1 if s >= med_soma else 0 for s in somas]

        ciclos = _ciclos(sorteios, spec.dezena_min, spec.dezena_max)
        completos = [c for c in ciclos if not c["aberto"]]
        aberto = next((c for c in ciclos if c["aberto"]), None)
        duracoes = [c["n"] for c in completos]
        novas_all: List[int] = []
        novas_por_pos: Dict[int, List[int]] = defaultdict(list)
        novas_fech: List[int] = []
        for c in ciclos:
            for i, d in enumerate(c["det"]):
                novas_all.append(d["novas"])
                novas_por_pos[i + 1].append(d["novas"])
                faltavam_antes = d["faltam"] + d["novas"]
                if 1 <= faltavam_antes <= 5:
                    novas_fech.append(d["novas"])

        novas_c = Counter(novas_all)
        n_novas = len(novas_all)
        q_novas_1ou2 = sum(v for k, v in novas_c.items() if k in (1, 2))
        novas_fech_c = Counter(novas_fech)

        n_rep = len(reps_ant)
        rep_c = Counter(reps_ant)
        q_1ou2 = sum(v for k, v in rep_c.items() if k in (1, 2))

        ss = sorted(somas)
        p10 = ss[int(0.10 * (n - 1))]
        p20 = ss[int(0.20 * (n - 1))]
        p80 = ss[int(0.80 * (n - 1))]
        p90 = ss[int(0.90 * (n - 1))]
        soma_faixa = Counter(_soma_bin(s) for s in somas)
        moda_soma_fx = soma_faixa.most_common(1)[0]

        moda_pi_v, _q, moda_pi_pct = _moda(pi)
        moda_seq, _q, moda_seq_pct = _moda(seq_qtd)
        moda_rep, _q, moda_rep_pct = _moda(rep_c)
        moda_tam, _q, moda_tam_pct = _moda(seq_tam) if seq_tam else (None, 0, 0.0)

        bma_rows = []
        for key, q in bma.most_common():
            parts = [f"{key[i]}{faixa_codigos[i]}" for i in range(len(faixa_codigos))]
            bma_rows.append({
                "dist": " + ".join(parts),
                "counts": list(key),
                "qtd": q,
                "pct": _pct(q, n),
                "tem_zero": any(v == 0 for v in key),
            })

        pi_rows = [
            {"dist": f"{p}P / {i}I", "pares": p, "impares": i, "qtd": q, "pct": _pct(q, n)}
            for (p, i), q in pi.most_common()
        ]
        top_ini = _dist(padrao_inicial, n, 8)
        hip = spec.padrao_hipotese or ""
        hip_q = padrao_inicial.get(hip, 0) if hip else 0
        moda_ini = top_ini[0] if top_ini else None

        pct_seq = _pct(tem_seq, n)
        pct_final = _pct(tem_final_igual, n)
        pct_rep_1ou2 = _pct(q_1ou2, n_rep) if n_rep else 0.0
        pct_novas_1ou2 = _pct(q_novas_1ou2, n_novas) if n_novas else 0.0

        media_pares = round(statistics.mean(pares_list), 2)
        media_impares = round(statistics.mean(impar_list), 2)
        medias_f = {c: round(statistics.mean(series_f[c]), 2) if series_f[c] else 0 for c in faixa_codigos}

        temporal_confirmados = []
        for name, flags in (
            ("tem_sequencia", flags_seq),
            ("tem_final_igual", flags_final),
            ("soma_acima_mediana", flags_soma_alta),
            ("baixas_ge3", flags_b_ge3),
            ("rep_ge2", flags_rep_ge2),
        ):
            for k in range(1, 7):
                r = _lag_rate(flags, k)
                if r and abs(r["delta_pp"]) >= 8 and r["n_prev"] >= 80:
                    temporal_confirmados.append({"evento": name, **r})

        ult = sorteios[-1]
        ult_dz = sorted(int(x) for x in ult["dezenas"])[:n_s]
        ult_seq = _sequencias(ult_dz)
        ult_counts = {c: 0 for c in faixa_codigos}
        for d in ult_dz:
            c = faixa_de(d, spec)
            if c:
                ult_counts[c] += 1
        ult_pares = [d for d in ult_dz if d % 2 == 0]
        ult_impares = [d for d in ult_dz if d % 2 == 1]
        ult_p = len(ult_pares)
        ult_rep_nums: List[int] = []
        if n >= 2:
            ult_rep_nums = sorted(set(ult_dz) & set(int(x) for x in sorteios[-2]["dezenas"]))
        ult_por_faixa: Dict[str, List[int]] = {c: [] for c in faixa_codigos}
        for d in ult_dz:
            c = faixa_de(d, spec)
            if c:
                ult_por_faixa[c].append(d)
        ult_fins = Counter(d % 10 for d in ult_dz)
        ult_fin_grupos = []
        for fin, qtd in sorted(ult_fins.items()):
            if qtd >= 2:
                nums = [d for d in ult_dz if d % 10 == fin]
                ult_fin_grupos.append({"final": fin, "dezenas": [_fmt2(x) for x in nums]})
        ult_seq_txt = ["–".join(_fmt2(x) for x in g) for g in ult_seq]
        ult_soma = sum(ult_dz)
        ult_padrao = "-".join(str(d // 10) for d in ult_dz)
        ult_bma = " + ".join(f"{ult_counts[c]}{c}" for c in faixa_codigos)

        ciclo_atual = None
        if aberto:
            ciclo_atual = {
                "numero": aberto["numero"],
                "inicio": aberto["inicio"],
                "concursos": aberto["n"],
                "saidas": len(aberto["vistos"]),
                "pendentes_qtd": uni - len(aberto["vistos"]),
                "pct": _pct(len(aberto["vistos"]), uni),
                "pendentes": [_fmt2(x) for x in (aberto.get("pendentes") or [])],
                "pendentes_num": [int(x) for x in (aberto.get("pendentes") or [])],
                "vistos_num": sorted(int(x) for x in (aberto.get("vistos") or [])),
            }

        ult_novas: List[int] = []
        for cyc in reversed(ciclos):
            dets = cyc.get("det") or []
            if dets and dets[-1]["concurso"] == ult["concurso"]:
                ult_novas = list(dets[-1].get("novas_lista") or [])
                break

        if ult_seq_txt:
            neste_seq = f"{len(ult_seq)} · {', '.join(ult_seq_txt)}"
        else:
            neste_seq = "nenhuma"
        neste_rep = (
            f"{len(ult_rep_nums)} · {_fmt_lista(ult_rep_nums)}"
            if ult_rep_nums else "0"
        )
        neste_pi = (
            f"{ult_p}P / {n_s - ult_p}I · "
            f"P {_fmt_lista(ult_pares) or '—'} · I {_fmt_lista(ult_impares) or '—'}"
        )
        neste_bma = ult_bma + " · " + " · ".join(
            f"{c} {_fmt_lista(ult_por_faixa[c]) or '—'}" for c in faixa_codigos
        )
        if ult_fin_grupos:
            neste_fin = "; ".join(
                f"final {g['final']}: {', '.join(g['dezenas'])}" for g in ult_fin_grupos
            )
        else:
            neste_fin = "todos distintos"
        if p20 <= ult_soma <= p80:
            neste_soma = f"{ult_soma} · na faixa operacional {p20}–{p80}"
        elif p10 <= ult_soma <= p90:
            neste_soma = f"{ult_soma} · no núcleo {p10}–{p90}"
        else:
            neste_soma = f"{ult_soma} · fora do núcleo {p10}–{p90}"
        neste_pad = f"{ult_padrao} · {ult_bma}"
        if ciclo_atual:
            neste_ciclo = (
                f"ciclo {ciclo_atual['numero']} · {ciclo_atual['concursos']} conc. · "
                f"{ciclo_atual['pct']}% · {ciclo_atual['pendentes_qtd']} pendentes"
                + (f" ({', '.join(ciclo_atual['pendentes'])})" if ciclo_atual["pendentes"] else "")
            )
        else:
            neste_ciclo = "—"
        neste_novas = (
            f"{len(ult_novas)} · {_fmt_lista(ult_novas)}" if ult_novas else "0"
        )

        moda_bma = bma_rows[0] if bma_rows else None
        faixas_out = {
            c: {
                "label": faixa_labels[c],
                **_faixa_stats(cnt_f[c], series_f[c], n),
            }
            for c in faixa_codigos
        }

        checklist = [
            {
                "criterio": "Sequências",
                "ref": (
                    f"≥1 em {pct_seq}% · moda {moda_seq} ({moda_seq_pct}%)"
                    + (f" · tamanho {moda_tam}" if moda_tam else "")
                ),
                "neste": neste_seq,
                "uso": "Coloque pelo menos um par consecutivo. 3 sequências é raro.",
                "tipo": "frequente" if pct_seq >= 55 else "atencao",
            },
            {
                "criterio": "Repetição do anterior",
                "ref": (
                    f"moda {moda_rep} ({moda_rep_pct}%) · 1 ou 2 em {pct_rep_1ou2}% "
                    f"· média {round(statistics.mean(reps_ant), 2) if reps_ant else 0}"
                ),
                "neste": neste_rep,
                "uso": "Leve 1 ou 2 dezenas do último concurso. 4+ é exceção.",
                "tipo": "frequente" if pct_rep_1ou2 >= 55 else "atencao",
            },
            {
                "criterio": "Pares / ímpares",
                "ref": (
                    f"{moda_pi_v[0]}P / {moda_pi_v[1]}I ({moda_pi_pct}%) · "
                    f"média {media_pares}P e {media_impares}I"
                ),
                "neste": neste_pi,
                "uso": (
                    f"Fique perto de {moda_pi_v[0]}P / {moda_pi_v[1]}I no {spec.nome}."
                    if moda_pi_v else f"Equilibre pares e ímpares nas {n_s} dezenas do {spec.nome}."
                ),
                "tipo": "frequente",
            },
            {
                "criterio": "Faixas " + " / ".join(faixa_codigos),
                "ref": (
                    f"top {moda_bma['dist']} ({moda_bma['pct']}%) · "
                    f"média {' + '.join(f'{medias_f[c]}{c}' for c in faixa_codigos)}"
                    if moda_bma else "—"
                ),
                "neste": neste_bma,
                "uso": "Não zere nenhuma faixa. Prefira a distribuição mais frequente do ranking.",
                "tipo": "frequente",
            },
            {
                "criterio": "Finais repetidos",
                "ref": f"≥1 final repetido em {pct_final}%",
                "neste": neste_fin,
                "uso": "Repita pelo menos um final (ex.: 03 e 13).",
                "tipo": "frequente" if pct_final >= 55 else "atencao",
            },
            {
                "criterio": "Soma",
                "ref": (
                    f"média {round(statistics.mean(somas), 2)} · "
                    f"mire {p20}–{p80} · núcleo {p10}–{p90}"
                ),
                "neste": neste_soma,
                "uso": f"Mire {p20}–{p80} (percentis 20–80). Núcleo {p10}–{p90}.",
                "tipo": "frequente",
            },
            {
                "criterio": "Padrão inicial",
                "ref": (
                    f"{moda_ini['valor']} ({moda_ini['pct']}%)"
                    if moda_ini else "—"
                ),
                "neste": neste_pad,
                "uso": (
                    (
                        f"{hip} é o 3º ({_pct(hip_q, n)}%) — não é o mais frequente."
                        if (moda_ini or {}).get("valor") != hip
                        else "Padrão líder confirmado."
                    )
                    if hip else "Use o padrão inicial mais frequente como referência, não como regra."
                ),
                "tipo": "tendencia",
            },
            {
                "criterio": "Ciclo (universo)",
                "ref": (
                    f"fecha em {round(statistics.mean(duracoes), 1)} concursos "
                    f"(mín {min(duracoes)} · máx {max(duracoes)} · {len(completos)} ciclos)"
                    if duracoes else "—"
                ),
                "neste": neste_ciclo,
                "uso": (
                    f"Ciclo atual nº {ciclo_atual['numero']}: {ciclo_atual['concursos']} concursos, "
                    f"{ciclo_atual['pct']}% fechado, {ciclo_atual['pendentes_qtd']} pendentes."
                    if ciclo_atual else "Sem ciclo em andamento."
                ),
                "tipo": "info",
            },
            {
                "criterio": "Dezenas novas no ciclo",
                "ref": (
                    f"moda {_moda(novas_c)[0]} ({_moda(novas_c)[2]}%) · "
                    f"1 ou 2 em {pct_novas_1ou2}%"
                ),
                "neste": neste_novas,
                "uso": "Não force 1–2 novas em todo concurso. No fim do ciclo a moda é 0.",
                "tipo": "atencao" if pct_novas_1ou2 < 55 else "frequente",
            },
        ]

        regras = []
        if pct_seq >= 55:
            regras.append({
                "n": 1, "tipo": "frequente",
                "texto": f"Inclua pelo menos 1 sequência de 2 dezenas ({pct_seq}% dos concursos).",
            })
        else:
            regras.append({
                "n": 1, "tipo": "nao_confirmado",
                "texto": f"Hipótese 'sempre tem sequência' não confirmada ({pct_seq}%).",
            })
        regras.append({
            "n": 2, "tipo": "frequente",
            "texto": (
                f"Leve 1 ou 2 dezenas do concurso anterior ({pct_rep_1ou2}%). "
                f"Moda {moda_rep} ({moda_rep_pct}%)."
            ),
        })
        regras.append({
            "n": 3, "tipo": "frequente" if pct_final >= 55 else "nao_confirmado",
            "texto": (
                f"A maioria dos concursos ({pct_final}%) tem pelo menos dois números com o mesmo final."
                if pct_final >= 55
                else f"Hipótese 'sempre há finais iguais' não confirmada como maioria ({pct_final}%)."
            ),
        })
        regras.append({
            "n": 4, "tipo": "frequente",
            "texto": (
                f"Par/ímpar de referência: {moda_pi_v[0]}P / {moda_pi_v[1]}I ({moda_pi_pct}%). "
                f"Ímpares puxam um pouco (média {media_impares} vs {media_pares})."
            ),
        })
        regras.append({
            "n": 5, "tipo": "frequente",
            "texto": (
                f"Faixas: use {moda_bma['dist']} ({moda_bma['pct']}%) ou as duas seguintes do ranking. "
                "Não zere uma faixa."
            ) if moda_bma else "Faixas indisponíveis.",
        })
        regras.append({
            "n": 6, "tipo": "frequente",
            "texto": (
                f"Soma entre {p20} e {p80}. Média {round(statistics.mean(somas), 1)}. "
                f"Mínimo histórico {min(somas)} e máximo {max(somas)} são exceções."
            ),
        })
        if hip and moda_ini and moda_ini["valor"] == hip:
            regras.append({
                "n": 7, "tipo": "frequente",
                "texto": f"Padrão inicial mais frequente confirmado: {hip} ({moda_ini['pct']}%).",
            })
        elif hip:
            regras.append({
                "n": 7, "tipo": "nao_confirmado",
                "texto": (
                    f"Hipótese '{hip}' como mais frequente não confirmada "
                    f"({_pct(hip_q, n)}%). Líder: {(moda_ini or {}).get('valor')} "
                    f"({(moda_ini or {}).get('pct')}%)."
                ),
            })
        elif moda_ini:
            regras.append({
                "n": 7, "tipo": "tendencia",
                "texto": (
                    f"Padrão inicial mais frequente no {spec.nome}: "
                    f"{moda_ini['valor']} ({moda_ini['pct']}%)."
                ),
            })
        regras.append({
            "n": 8, "tipo": "info",
            "texto": (
                f"Ciclo fecha em média {round(statistics.mean(duracoes), 1)} concursos "
                f"(mín {min(duracoes)}, máx {max(duracoes)})."
                if duracoes else "Sem ciclos completos."
            ),
        })
        regras.append({
            "n": 9, "tipo": "nao_confirmado" if pct_novas_1ou2 < 55 else "frequente",
            "texto": (
                f"Hipótese '1 ou 2 dezenas novas por concurso' não confirmada no ciclo inteiro "
                f"({pct_novas_1ou2}%). Moda {_moda(novas_c)[0]} novas ({_moda(novas_c)[2]}%)."
            ),
        })
        if novas_fech:
            regras.append({
                "n": 10, "tipo": "info",
                "texto": (
                    f"Perto do fechamento (1–5 pendentes): média {round(statistics.mean(novas_fech), 2)} "
                    f"dezenas novas; 0 novas em {_pct(novas_fech_c.get(0, 0), len(novas_fech))}%."
                ),
            })
        if temporal_confirmados:
            regras.append({
                "n": 11, "tipo": "tendencia",
                "texto": "Há desvio pontual de periodicidade (ver seção temporal) — não trate como ciclo rígido.",
            })
        else:
            regras.append({
                "n": 11, "tipo": "nao_confirmado",
                "texto": "Periodicidade a cada 2, 3 ou 4 concursos não confirmada (lags 1–6, desvio < 8 pp).",
            })
        regras.append({
            "n": 12, "tipo": "limite",
            "texto": "Frequência histórica é filtro de construção, não previsão do próximo resultado.",
        })

        inicio_ciclo = []
        for pos in (1, 2, 3):
            vals = novas_por_pos.get(pos) or []
            if not vals:
                continue
            inicio_ciclo.append({
                "pos": pos,
                "media": round(statistics.mean(vals), 2),
                "moda": _moda(Counter(vals))[0],
                "n": len(vals),
            })

        return {
            "meta": {
                "modalidade": spec.nome,
                "key": spec.modality_key,
                "universo": (
                    f"{n_s} colunas de {spec.dezena_min}–{spec.dezena_max}"
                    if spec.motor == "colunas"
                    else f"{n_s} dezenas de {spec.dezena_min}–{spec.dezena_max}"
                )
                + (f" + {spec.extra_label}" if spec.extra_label else ""),
                "total_concursos": n,
                "primeiro": sorteios[0]["concurso"],
                "primeiro_data": str(sorteios[0].get("data") or ""),
                "ultimo": ult["concurso"],
                "ultimo_data": str(ult.get("data") or ""),
                "faixas": [{"codigo": f[0], "label": f[3], "lo": f[1], "hi": f[2]} for f in spec.faixas],
            },
            "ultimo": {
                "concurso": ult["concurso"],
                "data": str(ult.get("data") or ""),
                "dezenas": [_fmt2(x) for x in ult_dz],
                "soma": ult_soma,
                "par_impar": f"{ult_p}P / {n_s - ult_p}I",
                "pares": [_fmt2(x) for x in ult_pares],
                "impares": [_fmt2(x) for x in ult_impares],
                "bma": ult_bma,
                "faixas": {c: [_fmt2(x) for x in ult_por_faixa[c]] for c in faixa_codigos},
                "sequencias": len(ult_seq),
                "sequencias_quais": ult_seq_txt,
                "padrao_inicial": ult_padrao,
                "rep_anterior": len(ult_rep_nums),
                "rep_dezenas": [_fmt2(x) for x in ult_rep_nums],
                "finais_quais": ult_fin_grupos,
                "novas_ciclo": [_fmt2(x) for x in ult_novas],
            },
            "kpis": {
                "soma_media": round(statistics.mean(somas), 1),
                "par_impar_moda": f"{moda_pi_v[0]}P / {moda_pi_v[1]}I" if moda_pi_v else "—",
                "par_impar_pct": moda_pi_pct,
                "pct_seq": pct_seq,
                "pct_final": pct_final,
                "pct_rep_1ou2": pct_rep_1ou2,
            },
            "soma": {
                "media": round(statistics.mean(somas), 2),
                "mediana": med_soma,
                "min": min(somas),
                "max": max(somas),
                "p10": p10, "p20": p20, "p80": p80, "p90": p90,
                "recomendavel": f"{p20}–{p80}",
                "nucleo": f"{p10}–{p90}",
                "faixa_mais_freq": {
                    "faixa": moda_soma_fx[0],
                    "qtd": moda_soma_fx[1],
                    "pct": _pct(moda_soma_fx[1], n),
                },
                "top_faixas": _dist(soma_faixa, n, 8),
            },
            "par_impar": {
                "media_pares": media_pares,
                "media_impares": media_impares,
                "predominio": "impares" if media_impares >= media_pares else "pares",
                "moda": f"{moda_pi_v[0]}P / {moda_pi_v[1]}I" if moda_pi_v else None,
                "moda_pct": moda_pi_pct,
                "top": pi_rows[:6],
                "todos": pi_rows,
            },
            "faixas": {
                "medias": medias_f,
                "detalhe": faixas_out,
                "top8": bma_rows[:8],
                "top3": bma_rows[:3],
                "raras_lt1": sum(1 for x in bma_rows if x["pct"] < 1),
                "extremas": [x for x in bma_rows if x["tem_zero"]][:8],
            },
            "sequencias": {
                "pct_com_pelo_menos_uma": pct_seq,
                "qtd_mais_freq": moda_seq,
                "qtd_mais_freq_pct": moda_seq_pct,
                "dist_qtd": _dist(seq_qtd, n),
                "tamanho_mais_freq": moda_tam,
                "tamanho_pct": moda_tam_pct,
                "dist_tamanho": _dist(seq_tam, sum(seq_tam.values())) if seq_tam else [],
            },
            "finais": {
                "pct_pelo_menos_um": pct_final,
                "dist_grupos": _dist(finais_grupos, n),
                "padrao_ocupacao_top": _dist(padrao_ocup, n, 6),
            },
            "repeticao": {
                "n_pares": n_rep,
                "min": min(reps_ant) if reps_ant else 0,
                "max": max(reps_ant) if reps_ant else 0,
                "media": round(statistics.mean(reps_ant), 2) if reps_ant else 0,
                "moda": moda_rep,
                "moda_pct": moda_rep_pct,
                "pct_1_ou_2": pct_rep_1ou2,
                "pct_zero": _pct(rep_c.get(0, 0), n_rep) if n_rep else 0,
                "dist": _dist(rep_c, n_rep) if n_rep else [],
            },
            "padrao_inicial": {
                "mais_freq": moda_ini,
                "top5": top_ini[:5],
                "distintos": len(padrao_inicial),
                "hipotese": {
                    "padrao": hip,
                    "qtd": hip_q,
                    "pct": _pct(hip_q, n),
                    "confirmado_lider": (moda_ini or {}).get("valor") == hip,
                },
            },
            "ciclo": {
                "completos": len(completos),
                "duracao_media": round(statistics.mean(duracoes), 2) if duracoes else None,
                "duracao_mediana": statistics.median(duracoes) if duracoes else None,
                "min": min(duracoes) if duracoes else None,
                "max": max(duracoes) if duracoes else None,
                "moda": _moda(Counter(duracoes))[0] if duracoes else None,
                "bins": {
                    "6-8": sum(1 for x in duracoes if 6 <= x <= 8),
                    "9-10": sum(1 for x in duracoes if 9 <= x <= 10),
                    "11-12": sum(1 for x in duracoes if 11 <= x <= 12),
                    "13-15": sum(1 for x in duracoes if 13 <= x <= 15),
                    "16+": sum(1 for x in duracoes if x >= 16),
                },
                "novas": {
                    "media": round(statistics.mean(novas_all), 2) if novas_all else 0,
                    "moda": _moda(novas_c)[0],
                    "moda_pct": _moda(novas_c)[2],
                    "pct_1_ou_2": pct_novas_1ou2,
                    "dist": _dist(novas_c, n_novas) if n_novas else [],
                },
                "inicio": inicio_ciclo,
                "fechamento_1a5": {
                    "n": len(novas_fech),
                    "media": round(statistics.mean(novas_fech), 2) if novas_fech else None,
                    "dist": _dist(novas_fech_c, len(novas_fech)) if novas_fech else [],
                },
                "atual": ciclo_atual,
            },
            "temporal": {
                "confirmados": temporal_confirmados,
                "confirmado": bool(temporal_confirmados),
            },
            "checklist": checklist,
            "regras": regras,
            "dezenas": {
                "universo": list(range(spec.dezena_min, spec.dezena_max + 1)),
                "stats": [
                    {
                        "dezena": d,
                        "qtd": int(freq_dez.get(d, 0)),
                        "pct": _pct(freq_dez.get(d, 0), n),
                        "atraso": (n - 1 - last_idx[d]) if d in last_idx else n,
                    }
                    for d in range(spec.dezena_min, spec.dezena_max + 1)
                ],
            },
        }

    @classmethod
    def regras_para_comportamento(cls, modality_key: str = "diadesorte") -> Dict[str, Any]:
        """Traduz o DNA em regras do gerador Comportamento → Apostas."""
        data = cls.calcular(modality_key)
        if not data.get("sucesso"):
            return data
        spec = get_resumo_spec(modality_key)
        pi = data.get("par_impar") or {}
        moda_pi = str(pi.get("moda") or "3P / 4I")
        pares, impares = 3, spec.sorteadas - 3
        try:
            left, right = moda_pi.replace(" ", "").split("/")
            pares = int(left.replace("P", ""))
            impares = int(right.replace("I", ""))
        except (ValueError, AttributeError):
            pass
        seq = data.get("sequencias") or {}
        rep = data.get("repeticao") or {}
        soma = data.get("soma") or {}
        regras = {
            "usar_PA": True, "alvo_PA": pares,
            "usar_IM": True, "alvo_IM": impares,
            "usar_SQ": True, "alvo_SQ": int(seq.get("qtd_mais_freq") or 1),
            "usar_RT": True, "alvo_RT": int(rep.get("moda") or 1),
            "usar_PR": False, "usar_MO": False, "usar_M3": False, "usar_FB": False, "usar_MS": False,
        }
        extras = {
            "soma_min": int(soma.get("p20") or 0),
            "soma_max": int(soma.get("p80") or 0),
            "exige_sequencia": bool(seq.get("pct_com_pelo_menos_uma", 0) >= 55),
            "exige_final_repetido": bool((data.get("finais") or {}).get("pct_pelo_menos_um", 0) >= 55),
            "bma_2a3": True,
        }
        labels = [
            f"{pares}P / {impares}I",
            f"SQ {regras['alvo_SQ']}",
            f"RT {regras['alvo_RT']}",
            f"soma {extras['soma_min']}–{extras['soma_max']}",
        ]
        if extras["exige_sequencia"]:
            labels.append("≥1 sequência")
        if extras["exige_final_repetido"]:
            labels.append("final repetido")
        if extras["bma_2a3"]:
            labels.append("2–3 em cada faixa B/M/A")
        return {
            "sucesso": True,
            "regras": regras,
            "extras": extras,
            "labels": labels,
            "checklist": data.get("checklist") or [],
            "meta": data.get("meta") or {},
            "ultimo": data.get("ultimo") or {},
        }

    @classmethod
    def aposta_alinha_dna(cls, dezenas: Sequence[int], extras: Dict[str, Any], modality_key: str) -> bool:
        """Filtro extra do DNA (soma, sequência, finais, faixas)."""
        if not extras:
            return True
        spec = get_resumo_spec(modality_key)
        dz = sorted(int(x) for x in dezenas)
        sm = sum(dz)
        lo = extras.get("soma_min")
        hi = extras.get("soma_max")
        if lo and sm < int(lo):
            return False
        if hi and sm > int(hi):
            return False
        if extras.get("exige_sequencia") and not _sequencias(dz):
            return False
        if extras.get("exige_final_repetido"):
            fins = Counter(d % 10 for d in dz)
            if not any(v >= 2 for v in fins.values()):
                return False
        if extras.get("bma_2a3"):
            counts = Counter(faixa_de(d, spec) for d in dz)
            for codigo, _lo, _hi, _lbl in spec.faixas:
                n = counts.get(codigo, 0)
                if n < 2 or n > 3:
                    return False
        return True

