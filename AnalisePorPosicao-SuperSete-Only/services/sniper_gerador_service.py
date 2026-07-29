# -*- coding: utf-8 -*-
"""Gerador inteligente Super Sete — evidências, auto/manual, rastreabilidade."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from services.analise_supersete_service import AnaliseSuperSeteService, DIGITOS, NUM_COLUNAS


def _pct(n: int, total: int) -> float:
    return round(n / total * 100, 1) if total else 0.0


class SniperGeradorService:
    """Monta evidências e gera apostas com critérios rastreáveis."""

    @classmethod
    def montar_contexto(cls) -> Dict[str, Any]:
        from analise_repeticao.repeticao_service import RepeticaoConcursosService

        seq = RepeticaoConcursosService("supersete").analisar_completo("posicional")
        volante = AnaliseSuperSeteService.analise_por_coluna()
        intrasorte = AnaliseSuperSeteService.analise_repeticoes()
        if not seq.get("sucesso") or not volante or not intrasorte:
            return {"sucesso": False, "erro": "Dados insuficientes no banco."}
        return {
            "sucesso": True,
            "sequencial": seq,
            "volante": volante,
            "intrasorte": intrasorte,
        }

    @classmethod
    def painel_evidencias(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        intra = ctx["intrasorte"]
        vol = ctx["volante"]
        seq = ctx["sequencial"]
        total = intra["total_analisado"]
        rq = intra.get("resumo_qtd_digitos_repetidos") or {}
        tipos_raw = intra.get("tipos") or {}
        com_rep_qtd = total - tipos_raw.get("0_repeticao", 0)

        repeticoes = {
            "com_repeticao": {
                "pct": intra["perc_com_repeticao"],
                "qtd": com_rep_qtd,
                "label": "Com repetição no sorteio",
            },
            "1_digito_distinto": {
                "pct": _pct(rq.get(1, 0), total),
                "qtd": int(rq.get(1, 0)),
                "label": "1 dígito repetido (ex.: uma dupla)",
            },
            "2_digitos_distintos": {
                "pct": _pct(rq.get(2, 0), total),
                "qtd": int(rq.get(2, 0)),
                "label": "2 dígitos repetidos",
            },
            "3_ou_mais": {
                "pct": _pct(rq.get(3, 0), total),
                "qtd": int(rq.get(3, 0)),
                "label": "3+ dígitos repetidos",
            },
        }

        tipos = tipos_raw
        labels = intra.get("tipo_labels") or {}
        tipos_sorteio = [
            {
                "chave": k,
                "label": labels.get(k, k),
                "pct": _pct(tipos.get(k, 0), total),
                "vezes": tipos.get(k, 0),
            }
            for k in ("1_dupla", "2_duplas", "1_trinca", "outros", "0_repeticao")
        ]
        tipos_sorteio.sort(key=lambda x: -x["pct"])

        freq_global = {d: 0 for d in DIGITOS}
        atraso_global = {d: 0 for d in DIGITOS}
        for col in range(1, NUM_COLUNAS + 1):
            dcol = vol[col]
            for d in DIGITOS:
                freq_global[d] += dcol["freq"][d]
                atraso_global[d] += dcol["atraso"][d]

        rank_freq = sorted(DIGITOS, key=lambda d: -freq_global[d])
        rank_frio = sorted(DIGITOS, key=lambda d: -atraso_global[d])

        numeros_fortes = [
            {"posicao": i + 1, "digito": d, "ocorrencias": freq_global[d]}
            for i, d in enumerate(rank_freq[:3])
        ]
        numeros_frios = [
            {"posicao": i + 1, "digito": d, "atraso_medio": round(atraso_global[d] / NUM_COLUNAS, 1)}
            for i, d in enumerate(rank_frio[:3])
        ]

        detalhe_seq = seq.get("dezenas") or []
        cols_rank = sorted(
            detalhe_seq,
            key=lambda r: -float(r.get("freq_repeticao_pct") or 0),
        )
        colunas_fortes = [
            {
                "coluna": r["dezena"],
                "label": r.get("label", f"C{r['dezena']}"),
                "pct": r.get("freq_repeticao_pct", 0),
                "vezes": int(r.get("freq_repeticao_vezes") or 0),
            }
            for r in cols_rank[:3]
        ]
        colunas_fracas = [
            {
                "coluna": r["dezena"],
                "label": r.get("label", f"C{r['dezena']}"),
                "pct": r.get("freq_repeticao_pct", 0),
                "vezes": int(r.get("freq_repeticao_vezes") or 0),
            }
            for r in sorted(detalhe_seq, key=lambda r: float(r.get("freq_repeticao_pct") or 0))[:3]
        ]

        ciclo = {}
        try:
            from services.ciclo_service import CicloService  # type: ignore

            if hasattr(CicloService, "obter_ciclo_atual"):
                ciclo = CicloService.obter_ciclo_atual() or {}
        except Exception:
            pass

        return {
            "total_concursos": total,
            "repeticoes": repeticoes,
            "tipos_sorteio": tipos_sorteio,
            "numeros_fortes": numeros_fortes,
            "numeros_frios": numeros_frios,
            "colunas_fortes": colunas_fortes,
            "colunas_fracas": colunas_fracas,
            "top_pares_colunas": intra.get("top_pares_colunas") or [],
            "ultimo_par": seq.get("resumo_ultimo_par", {}).get("posicional", {}),
            "ciclo": ciclo,
        }

    @classmethod
    def regras_automaticas(cls, evidencias: Dict[str, Any]) -> Dict[str, Any]:
        rep = evidencias["repeticoes"]
        tipos = evidencias["tipos_sorteio"]
        tipo_dom = tipos[0] if tipos else None

        regras = {
            "usar_repeticao": rep["com_repeticao"]["pct"] >= 55,
            "usar_dupla": False,
            "usar_trinca": False,
            "usar_numeros_quentes": True,
            "usar_numeros_frios": False,
            "usar_colunas_fortes": True,
            "usar_colunas_fracas": False,
            "usar_ciclo": bool(evidencias.get("ciclo")),
            "usar_atraso": True,
            "usar_sequencial": True,
            "usar_ultimo_par": True,
            "usar_pares_colunas": len(evidencias.get("top_pares_colunas") or []) > 0,
            "forcar_par_colunas": True,
            "tipo_sorteio_alvo": "",
            "digito_foco": None,
            "par_colunas_idx": 0,
        }

        if tipo_dom:
            ch = tipo_dom["chave"]
            if ch == "1_dupla" and tipo_dom["pct"] >= 40:
                regras["usar_dupla"] = True
                regras["tipo_sorteio_alvo"] = "1_dupla"
            elif ch == "2_duplas" and tipo_dom["pct"] >= 25:
                regras["usar_dupla"] = True
                regras["tipo_sorteio_alvo"] = "2_duplas"
            elif ch == "1_trinca" and tipo_dom["pct"] >= 15:
                regras["usar_trinca"] = True
                regras["tipo_sorteio_alvo"] = "1_trinca"
            elif rep["com_repeticao"]["pct"] >= 70 and not regras["tipo_sorteio_alvo"]:
                regras["tipo_sorteio_alvo"] = "1_dupla"

        tops = evidencias.get("numeros_fortes") or []
        if tops:
            regras["digito_foco"] = tops[0]["digito"]

        return regras

    @classmethod
    def _regras_para_sniper_opts(
        cls,
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
    ) -> Dict[str, Any]:
        tipo_alvo = regras.get("tipo_sorteio_alvo") or ""
        if regras.get("usar_trinca") and not tipo_alvo:
            tipo_alvo = "1_trinca"
        elif regras.get("usar_dupla") and not tipo_alvo:
            tipo_alvo = "1_dupla"

        return {
            "usar_sequencial": bool(regras.get("usar_sequencial", True)),
            "usar_volante_atraso": bool(regras.get("usar_atraso", True)),
            "usar_top_digitos": bool(regras.get("usar_numeros_quentes", False)),
            "usar_pares_colunas": bool(regras.get("usar_pares_colunas", False)),
            "forcar_par_colunas": bool(regras.get("forcar_par_colunas", True)),
            "par_colunas_idx": regras.get("par_colunas_idx"),
            "tipo_sorteio_alvo": tipo_alvo,
            "digito_foco": regras.get("digito_foco"),
            "usar_colunas_fortes": bool(regras.get("usar_colunas_fortes", False)),
            "usar_colunas_fracas": bool(regras.get("usar_colunas_fracas", False)),
            "usar_numeros_frios": bool(regras.get("usar_numeros_frios", False)),
            "regras_ativas": regras,
            "evidencias": evidencias,
        }

    @classmethod
    def _analisar_aposta(
        cls,
        digits: List[int],
        regras: Dict[str, Any],
        evidencias: Dict[str, Any],
        seq: Dict[str, Any],
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        criterios: List[Dict[str, str]] = []
        marcas: Dict[str, Any] = {
            "digitos": {},
            "colunas": {},
        }

        tipo, label, repetidos, qtd_dist, _txt = AnaliseSuperSeteService._classificar_intrasorte(digits)
        contagem: Dict[int, int] = {}
        for d in digits:
            contagem[d] = contagem.get(d, 0) + 1
        rep_intra = {d for d, q in contagem.items() if q > 1}

        if qtd_dist >= 1 or rep_intra:
            criterios.append({"codigo": "repeticao", "texto": "Repetição no sorteio"})
        if tipo == "1_dupla":
            criterios.append({"codigo": "dupla", "texto": "1 dupla"})
        elif tipo == "2_duplas":
            criterios.append({"codigo": "dupla", "texto": "2 duplas"})
        elif tipo == "1_trinca":
            criterios.append({"codigo": "trinca", "texto": "1 trinca"})
        elif tipo == "outros":
            criterios.append({"codigo": "trinca", "texto": "Múltiplas repetições"})

        quentes = {x["digito"] for x in evidencias.get("numeros_fortes") or []}
        frios = {x["digito"] for x in evidencias.get("numeros_frios") or []}
        cols_fortes = {x["coluna"] for x in evidencias.get("colunas_fortes") or []}
        cols_fracas = {x["coluna"] for x in evidencias.get("colunas_fracas") or []}

        rep_ult = {
            x["posicao"]: x["dezena"]
            for x in (seq.get("resumo_ultimo_par", {}).get("posicional", {}).get("itens") or [])
        }

        quentes_usados: List[int] = []
        for i, d in enumerate(digits, 1):
            if d in rep_intra:
                marcas["digitos"][str(d)] = marcas["digitos"].get(str(d)) or "rep-intra"
            if d in quentes:
                marcas["digitos"][str(d)] = "quente"
                quentes_usados.append(d)
            if d in frios and regras.get("usar_numeros_frios"):
                marcas["digitos"][str(d)] = "frio"
            if i in rep_ult and rep_ult[i] == d:
                marcas["digitos"][str(d)] = marcas["digitos"].get(str(d), "seq-rep") or "seq-rep"
            if i in cols_fortes:
                marcas["colunas"][str(i)] = "forte"
            if i in cols_fracas and regras.get("usar_colunas_fracas"):
                marcas["colunas"][str(i)] = "fraca"

        if quentes_usados and regras.get("usar_numeros_quentes"):
            u = sorted(set(quentes_usados))
            criterios.append({
                "codigo": "quente",
                "texto": f"Números quentes: {', '.join(str(x) for x in u)}",
            })

        if rep_ult and regras.get("usar_ultimo_par"):
            n = sum(1 for i, d in enumerate(digits, 1) if rep_ult.get(i) == d)
            if n:
                criterios.append({"codigo": "ultimo_par", "texto": f"Último par ({n} col.)"})

        for cf in evidencias.get("colunas_fortes") or []:
            if regras.get("usar_colunas_fortes"):
                criterios.append({
                    "codigo": "col_forte",
                    "texto": f"Coluna {cf['label']} forte ({cf['pct']}%)",
                })

        det = {c["codigo"]: c for c in criterios}
        criterios = list(det.values())

        if regras.get("usar_sequencial"):
            criterios.insert(0, {"codigo": "sequencial", "texto": "Repetição sequencial C1–C7"})
        if regras.get("usar_atraso"):
            criterios.append({"codigo": "atraso", "texto": "Atraso / volante por coluna"})

        return criterios, marcas

    @classmethod
    def _labels_regras_auto(cls, regras: Dict[str, Any]) -> List[str]:
        out = []
        mapa = [
            ("usar_repeticao", "Repetição"),
            ("usar_dupla", "Priorizar dupla"),
            ("usar_trinca", "Priorizar trinca"),
            ("usar_numeros_quentes", "Números quentes"),
            ("usar_numeros_frios", "Números frios"),
            ("usar_colunas_fortes", "Colunas fortes"),
            ("usar_colunas_fracas", "Colunas fracas"),
            ("usar_sequencial", "Sequencial"),
            ("usar_ultimo_par", "Último par"),
            ("usar_pares_colunas", "Par de colunas"),
            ("usar_atraso", "Atraso"),
            ("usar_ciclo", "Ciclo"),
        ]
        for k, lbl in mapa:
            if regras.get(k):
                out.append(lbl)
        if regras.get("tipo_sorteio_alvo"):
            out.append(f"Tipo alvo: {regras['tipo_sorteio_alvo']}")
        return out

    @classmethod
    def gerar(
        cls,
        quantidade: int,
        perfil: str,
        modo_geracao: str,
        regras_manuais: Optional[Dict[str, Any]] = None,
        usar_ultimo_par_chk: bool = True,
    ) -> Dict[str, Any]:
        ctx = cls.montar_contexto()
        if not ctx.get("sucesso"):
            return ctx

        evidencias = cls.painel_evidencias(ctx)
        if modo_geracao == "automatico":
            regras = cls.regras_automaticas(evidencias)
            criterios_auto = cls._labels_regras_auto(regras)
        else:
            regras = dict(regras_manuais or {})
            regras.setdefault("usar_sequencial", True)
            regras["usar_ultimo_par"] = bool(
                regras.get("usar_ultimo_par", usar_ultimo_par_chk)
            )
            criterios_auto = []

        sniper_opts = cls._regras_para_sniper_opts(regras, evidencias)

        from analise_repeticao.repeticao_service import RepeticaoConcursosService

        svc = RepeticaoConcursosService("supersete")
        analise = ctx["sequencial"]
        volante = ctx["volante"] if sniper_opts.get("usar_volante_atraso") else None

        raw = svc.gerar_apostas(
            quantidade=quantidade,
            dezenas_por_jogo=7,
            modo="posicional",
            perfil=perfil,
            usar_ultimo_par=bool(regras.get("usar_ultimo_par", True)),
            respeitar_par_impar=False,
            analise=analise,
            volante_colunas=volante,
            sniper_opts=sniper_opts,
            intrasorte=ctx["intrasorte"],
        )
        if not raw.get("sucesso"):
            return raw

        apostas_out = []
        for a in raw.get("apostas") or []:
            digs = a["dezenas"]
            crit, marcas = cls._analisar_aposta(digs, regras, evidencias, analise)
            apostas_out.append({
                **a,
                "criterios": crit,
                "marcas": marcas,
                "tipo_sorteio": AnaliseSuperSeteService._classificar_intrasorte(digs)[0],
            })

        return {
            "sucesso": True,
            "apostas": apostas_out,
            "total_geradas": len(apostas_out),
            "solicitados": quantidade,
            "aviso": raw.get("aviso"),
            "modo_geracao": modo_geracao,
            "evidencias": evidencias,
            "regras_aplicadas": regras,
            "criterios_modo_auto": criterios_auto,
            "motor": "sniper_inteligente",
        }

    @classmethod
    def analise_completa_api(cls) -> Dict[str, Any]:
        ctx = cls.montar_contexto()
        if not ctx.get("sucesso"):
            return ctx
        ev = cls.painel_evidencias(ctx)
        auto = cls.regras_automaticas(ev)
        return {
            "sucesso": True,
            "evidencias": ev,
            "regras_automaticas": auto,
            "criterios_auto_preview": cls._labels_regras_auto(auto),
            "sequencial": ctx["sequencial"],
            "intrasorte": ctx["intrasorte"],
            "motor": "sniper_inteligente",
        }
