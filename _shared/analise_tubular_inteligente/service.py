# -*- coding: utf-8 -*-
"""Agregação estatística dos padrões da Visualização Tubular."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

from analise_estudos.service_factory import make_estudos_base
from analise_estudos.specs import get_estudos_config, tem_analise_estudos

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def _analisar_sequencias(nums: Sequence[int]) -> List[Dict[str, Any]]:
    sequences: List[Dict[str, Any]] = []
    n = [int(x) for x in nums]
    i = 0
    while i < len(n) - 1:
        if n[i + 1] == n[i] + 1:
            end = i + 1
            while end < len(n) - 1 and n[end + 1] == n[end] + 1:
                end += 1
            sequences.append({
                "length": end - i + 1,
                "numbers": n[i:end + 1],
            })
            i = end + 1
        else:
            i += 1
    return sequences


def _assinatura_sequencias(seqs: List[Dict[str, Any]]) -> str:
    if not seqs:
        return "Sem sequência"
    parts = []
    for s in seqs:
        nums = s["numbers"]
        if s["length"] >= 3:
            parts.append(f"{nums[0]}-{nums[-1]}")
        else:
            parts.append(",".join(str(x) for x in nums))
    if len(seqs) == 1:
        return f"Sequência de {seqs[0]['length']} ({parts[0]})"
    return f"{len(seqs)} sequências ({' · '.join(parts)})"


def _finais_iguais(nums: Sequence[int]) -> Tuple[bool, str]:
    grupos: Dict[int, List[int]] = {}
    for n in nums:
        grupos.setdefault(int(n) % 10, []).append(int(n))
    reps = [g for g in grupos.values() if len(g) > 1]
    if not reps:
        return False, "Sem finais iguais"
    quais = " · ".join(",".join(str(x) for x in g) for g in reps)
    return True, f"{len(reps)} grupo(s): {quais}"


def _digitos_unicos(nums: Sequence[int]) -> Tuple[int, str]:
    digs = sorted({int(d) for n in nums for d in f"{int(n):02d}"})
    return len(digs), " ".join(str(d) for d in digs)


def _status_lista(items: List[Dict[str, Any]]) -> None:
    if not items:
        return
    freqs = [int(i["frequencia"]) for i in items]
    media = sum(freqs) / max(1, len(freqs))
    for i in items:
        f = int(i["frequencia"])
        if f > media * 1.15:
            i["status"] = "MAIS"
        elif f < media * 0.85:
            i["status"] = "MENOS"
        else:
            i["status"] = "MÉDIO"


def _rank_counter(counter: Counter, total: int, top: int = 12) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for desc, freq in counter.most_common(top):
        out.append({
            "descricao": str(desc),
            "frequencia": int(freq),
            "percentual": round(100.0 * freq / max(1, total), 1),
            "status": "MÉDIO",
        })
    _status_lista(out)
    return out


class AnaliseTubularInteligenteService:
    @classmethod
    def analisar(
        cls,
        modality_key: str,
        *,
        base_estatistica: str = "geral",
        janela: int = 0,
    ) -> Dict[str, Any]:
        if not tem_analise_estudos(modality_key):
            return {"sucesso": False, "erro": "Modalidade não suportada."}

        Base = make_estudos_base(modality_key)
        cfg = get_estudos_config(modality_key)
        rows = Base.carregar_sorteios_asc(base_estatistica=base_estatistica, janela=janela)
        total = len(rows)
        if total == 0:
            return {"sucesso": False, "erro": "Sem concursos na base selecionada."}

        cnt_seq = Counter()
        cnt_finais = Counter()
        cnt_somas = Counter()
        cnt_pi = Counter()
        cnt_ini_fim = Counter()
        cnt_meses = Counter()
        cnt_digitos = Counter()
        draws_com_seq = 0
        repeticoes = 0

        prev_nums: Optional[List[int]] = None
        for r in rows:
            # Análise tubular usa dezenas em ordem crescente (como a visualização)
            nums = sorted(int(x) for x in Base.dezenas_ordem(r))
            seqs = _analisar_sequencias(nums)
            if seqs:
                draws_com_seq += 1
            cnt_seq[_assinatura_sequencias(seqs)] += 1

            tem_fin, desc_fin = _finais_iguais(nums)
            if tem_fin:
                cnt_finais[desc_fin] += 1

            soma = sum(nums)
            cnt_somas[f"Soma {soma}"] += 1

            pares = sum(1 for n in nums if n % 2 == 0)
            impares = len(nums) - pares
            cnt_pi[f"{pares}P / {impares}I"] += 1

            iniciais = " ".join(str(n // 10) for n in nums)
            finais_d = " ".join(str(n % 10) for n in nums)
            cnt_ini_fim[f"I:[{iniciais}] F:[{finais_d}]"] += 1

            qtd_dig, _ = _digitos_unicos(nums)
            cnt_digitos[f"{qtd_dig} dígitos únicos"] += 1

            if cfg.get("extra_mes"):
                mes_num = int(getattr(r, "mes_num", 0) or 0)
                mes_nome = getattr(r, "mes_nome", "") or MESES.get(mes_num, "")
                if mes_nome:
                    cnt_meses[mes_nome] += 1

            if prev_nums is not None:
                if any(n in prev_nums for n in nums):
                    repeticoes += 1
            prev_nums = nums

        # Finais: ranking por padrão dominante; também lista por dígito final
        finais_rank = _rank_counter(cnt_finais, total, top=10)
        if not finais_rank:
            finais_rank = [{
                "descricao": "Sem finais iguais",
                "frequencia": 0,
                "percentual": 0.0,
                "status": "MENOS",
            }]

        seq_padroes = _rank_counter(cnt_seq, total, top=10)
        somas = _rank_counter(cnt_somas, total, top=8)
        pares_impares = _rank_counter(cnt_pi, total, top=8)
        padroes_if = _rank_counter(cnt_ini_fim, total, top=8)
        digitos_unicos = _rank_counter(cnt_digitos, total, top=10)
        meses = _rank_counter(cnt_meses, total, top=12) if cfg.get("extra_mes") else []

        rep_pct = round(100.0 * repeticoes / max(1, total - 1 if total > 1 else 1), 1)
        # base de comparação: % de concursos com repetição (excluindo o 1º)
        base_rep = max(1, total - 1)
        rep_status = "MAIS" if repeticoes > base_rep * 0.55 else ("MENOS" if repeticoes < base_rep * 0.35 else "MÉDIO")

        return {
            "sucesso": True,
            "modality_key": modality_key,
            "modality_nome": cfg["nome"],
            "total_concursos": total,
            "janela": janela,
            "base": base_estatistica,
            "extra_mes": bool(cfg.get("extra_mes")),
            "sequencias": {
                "total": draws_com_seq,
                "padroes": seq_padroes,
            },
            "finais": finais_rank,
            "repeticoes": {
                "total": repeticoes,
                "percentual": rep_pct,
                "status": rep_status,
            },
            "somas": {"padroes": somas},
            "pares_impares": pares_impares,
            "padroes_iniciais_finais": padroes_if,
            "meses": meses,
            "digitos_unicos": digitos_unicos,
        }
