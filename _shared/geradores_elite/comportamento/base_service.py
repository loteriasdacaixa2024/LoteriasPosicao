# -*- coding: utf-8 -*-
"""Motor compartilhado — Comportamento → Apostas."""
from __future__ import annotations

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from models.shared import db
from sqlalchemy import desc

from geradores_elite.comportamento.specs import (
    BASES_ESTATISTICA,
    BASES_ESTATISTICA_LABEL,
    MESES_NOME,
    MESES_ABREV,
    MOTORES_GERACAO,
    MOTOR_LABELS,
    ComportamentoSpec,
)
from geradores_elite.validacao.apostas_ineditas import (
    aposta_ja_sorteada,
    carregar_combinacoes_historicas,
)


def _contar_sequencias(dezenas: List[int]) -> int:
    ordenadas = sorted(dezenas)
    grupos = 0
    i = 0
    while i < len(ordenadas):
        j = i
        while j + 1 < len(ordenadas) and ordenadas[j + 1] - ordenadas[j] == 1:
            j += 1
        if j > i:
            grupos += 1
        i = j + 1
    return grupos


class ComportamentoBaseService:
    SPEC: ComportamentoSpec
    SorteioModel: Type[Any]

    @classmethod
    def _spec(cls) -> ComportamentoSpec:
        return cls.SPEC

    @classmethod
    def _usa_meses_indicados(cls) -> bool:
        sp = cls._spec()
        return sp.modality_key == "diadesorte" and sp.has_mes

    @classmethod
    def _meses_indicados_analise(cls) -> Dict[str, Any]:
        from diadesorte.meses_indicados import carregar_meses_indicados

        return carregar_meses_indicados(cls.SorteioModel)

    @classmethod
    def _aplicar_mes_indicado_aposta(
        cls,
        aposta_item: Dict[str, Any],
        idx: int,
        analise_ms: Dict[str, Any],
    ) -> None:
        from diadesorte.meses_indicados import anexar_mes_abrev_texto, extra_mes_ciclo

        extra = extra_mes_ciclo(analise_ms, idx)
        if not extra:
            return
        aposta_item["mes"] = extra["mes"]
        aposta_item["mes_num"] = extra["mes_num"]
        aposta_item["mes_nome"] = extra["mes_nome"]
        aposta_item["mes_abrev"] = extra["mes_abrev"]
        aposta_item["texto"] = anexar_mes_abrev_texto(
            aposta_item.get("texto", ""), extra["mes_abrev"],
        )

    @classmethod
    def _sem_ms(cls, ativos: List[str]) -> List[str]:
        if cls._usa_meses_indicados():
            return [c for c in ativos if c != "MS"]
        return ativos

    @classmethod
    def _dezena_range(cls) -> range:
        sp = cls._spec()
        return range(sp.dezena_min, sp.universo + 1)

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        if hasattr(s, "dezenas_lista"):
            return list(s.dezenas_lista())
        dz = s.dezenas()
        return list(dz) if isinstance(dz, list) else sorted(dz)

    @classmethod
    def _extras_from_sorteio(cls, s: Any) -> Dict[str, int]:
        sp = cls._spec()
        out: Dict[str, int] = {}
        if sp.has_mes:
            mn = getattr(s, "mes_num", None)
            if mn:
                out["MS"] = int(mn)
        if sp.has_time:
            tn = getattr(s, "time_num", None)
            if tn:
                out["TM"] = int(tn)
        if sp.has_trevos and hasattr(s, "trevos_lista"):
            tv = sorted(s.trevos_lista())
            if len(tv) >= 2:
                out["T1"], out["T2"] = int(tv[0]), int(tv[1])
        return out

    @classmethod
    def _contar_sequencias(cls, dezenas: List[int]) -> int:
        return _contar_sequencias(dezenas)

    @classmethod
    def _calcular_indicadores(
        cls,
        dezenas: List[int],
        prev_dezenas: Optional[List[int]] = None,
        extras: Optional[Dict[str, int]] = None,
    ) -> Dict[str, int]:
        sp = cls._spec()
        pa = sum(1 for d in dezenas if d % 2 == 0)
        im = len(dezenas) - pa
        pr = sum(1 for d in dezenas if d in sp.primos)
        rt = len(set(dezenas) & set(prev_dezenas)) if prev_dezenas else 0
        mo = sum(1 for d in dezenas if d in sp.moldura)
        sq = cls._contar_sequencias(dezenas)
        m3 = sum(1 for d in dezenas if d in sp.multiplos_3)
        fb = sum(1 for d in dezenas if d in sp.fibonacci)
        out = {
            "PA": pa,
            "IM": im,
            "PR": pr,
            "RT": rt,
            "MO": mo,
            "SQ": sq,
            "M3": m3,
            "FB": fb,
        }
        if extras:
            for k, v in extras.items():
                if k in sp.indicadores:
                    out[k] = int(v)
        return out

    @classmethod
    def _valor_indicador_aposta(
        cls,
        dezenas: List[int],
        codigo: str,
        prev_dezenas: Optional[List[int]] = None,
        extras: Optional[Dict[str, int]] = None,
    ) -> int:
        return cls._calcular_indicadores(dezenas, prev_dezenas, extras)[codigo]

    @classmethod
    def _dezenas_por_categoria(cls) -> Dict[str, Set[int]]:
        sp = cls._spec()
        universo = set(cls._dezena_range())
        return {
            "par": {d for d in universo if d % 2 == 0},
            "impar": {d for d in universo if d % 2 != 0},
            "primo": set(sp.primos),
            "nao_primo": universo - set(sp.primos),
            "moldura": set(sp.moldura),
            "centro": universo - set(sp.moldura),
            "m3": set(sp.multiplos_3),
            "nao_m3": universo - set(sp.multiplos_3),
            "fb": set(sp.fibonacci),
            "nao_fb": universo - set(sp.fibonacci),
        }

    @classmethod
    def _normalizar_base_estatistica(cls, base: Optional[str]) -> str:
        b = (base or "geral").strip().lower()
        if b not in BASES_ESTATISTICA:
            return "geral"
        return b

    @classmethod
    def _model_suporta_bases(cls) -> bool:
        return hasattr(cls.SorteioModel, "filtro_base") and hasattr(
            cls.SorteioModel, "ganhadores_7"
        )

    @classmethod
    def _meta_bases_dados(cls) -> Dict[str, Any]:
        if not cls._model_suporta_bases():
            total = db.session.query(cls.SorteioModel).count()
            return {
                "suporta_bases": False,
                "total_geral": total,
                "total_vencedores": None,
                "total_acumulados": None,
                "pendentes_ganhadores": None,
            }
        total = db.session.query(cls.SorteioModel).count()
        q = db.session.query(cls.SorteioModel)
        total_v = cls.SorteioModel.filtro_base(q, "vencedores").count()
        total_a = cls.SorteioModel.filtro_base(q, "acumulados").count()
        pend = (
            db.session.query(cls.SorteioModel)
            .filter(cls.SorteioModel.ganhadores_7.is_(None))
            .count()
        )
        classificados = total_v + total_a
        pct_v = pct_a = None
        if classificados > 0:
            pct_v = round(100.0 * total_v / classificados, 1)
            pct_a = round(100.0 * total_a / classificados, 1)
        return {
            "suporta_bases": True,
            "total_geral": total,
            "total_vencedores": total_v,
            "total_acumulados": total_a,
            "pendentes_ganhadores": pend,
            "ganhadores_preenchidos": classificados,
            "bases_completas": pend == 0 and total > 0,
            "pct_vencedores": pct_v,
            "pct_acumulados": pct_a,
        }

    @classmethod
    def _aviso_base_pendentes(cls, meta: Dict[str, Any], base: str) -> Optional[str]:
        if not meta.get("suporta_bases"):
            return None
        pend = int(meta.get("pendentes_ganhadores") or 0)
        if pend <= 0:
            return None
        if base in ("vencedores", "acumulados"):
            return (
                f"{pend} concurso(s) sem classificação de ganhadores (ganhadores_7 nulo) — "
                "excluídos das bases Vencedores/Acumulados. Execute o backfill de ganhadores."
            )
        return (
            f"{pend} concurso(s) ainda sem ganhadores_7 no banco — "
            "recomendado executar backfill para bases filtradas completas."
        )

    @classmethod
    def _carregar_sorteios_asc(cls, base_estatistica: str = "geral") -> List[Any]:
        base = cls._normalizar_base_estatistica(base_estatistica)
        q = db.session.query(cls.SorteioModel).order_by(cls.SorteioModel.concurso.asc())
        if base != "geral" and cls._model_suporta_bases():
            q = cls.SorteioModel.filtro_base(q, base)
        return q.all()

    @classmethod
    def listar_concursos(cls, limit: int = 150) -> List[Dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        rows = (
            db.session.query(cls.SorteioModel)
            .order_by(desc(cls.SorteioModel.concurso))
            .limit(lim)
            .all()
        )
        out = []
        for s in rows:
            item = {
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": cls._dezenas_from_sorteio(s),
            }
            ex = cls._extras_from_sorteio(s)
            if cls._spec().has_mes and "MS" in ex:
                item["mes_num"] = ex["MS"]
                item["mes_nome"] = getattr(s, "mes_nome", None) or MESES_NOME.get(ex["MS"], "")
            if cls._spec().has_time and "TM" in ex:
                item["time_num"] = ex["TM"]
                item["time_nome"] = getattr(s, "time_nome", None) or ""
            if cls._spec().has_trevos and "T1" in ex:
                item["trevos"] = [ex["T1"], ex["T2"]]
            out.append(item)
        return out

    @classmethod
    def _aplicar_filtros_linhas(
        cls,
        linhas: List[Dict[str, Any]],
        filtros: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        if not filtros:
            return linhas
        inds = cls._spec().indicadores
        out = []
        for row in linhas:
            ok = True
            for k, v in filtros.items():
                if k not in inds:
                    continue
                if row.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(row)
        return out

    @classmethod
    def _resumo_indicadores(cls, linhas: List[Dict[str, Any]]) -> Dict[str, Any]:
        sp = cls._spec()
        total = len(linhas)
        resumo: Dict[str, Any] = {}
        for cod in sp.indicadores:
            vals = [row[cod] for row in linhas if cod in row]
            if not vals:
                resumo[cod] = {
                    "moda": 0,
                    "media": 0,
                    "distribuicao": {},
                    "faixa_quente": [],
                    "ultimo": 0,
                }
                continue
            cnt = Counter(vals)
            moda, moda_freq = cnt.most_common(1)[0]
            media = round(sum(vals) / len(vals), 2)
            dist = {str(k): v for k, v in sorted(cnt.items())}
            quentes = [k for k, _ in cnt.most_common(3)]
            resumo[cod] = {
                "moda": moda,
                "moda_pct": round(moda_freq / total * 100, 1) if total else 0,
                "media": media,
                "distribuicao": dist,
                "faixa_quente": quentes,
                "ultimo": linhas[-1].get(cod, 0) if linhas else 0,
            }
        return resumo

    @classmethod
    def _criterios_sugeridos(cls, resumo: Dict[str, Any]) -> Dict[str, Any]:
        sp = cls._spec()
        alvos = {cod: resumo[cod]["moda"] for cod in sp.indicadores if cod in resumo}
        return {
            "modo": "moda_janela",
            "alvos": alvos,
            "descricao": "Valores moda observados na janela selecionada",
        }

    @classmethod
    def _pool_dezenas(cls, linhas: List[Dict[str, Any]]) -> List[Tuple[int, float]]:
        sp = cls._spec()
        freq: Counter = Counter()
        for row in linhas:
            for d in row.get("dezenas") or []:
                freq[d] += 1
        total = max(sum(freq.values()), 1)
        return [(d, (freq[d] / total) * 100 + 1.0) for d in cls._dezena_range()]

    @classmethod
    def _pool_dezenas_linha(cls, row: Dict[str, Any]) -> List[Tuple[int, float]]:
        dz = set(row.get("dezenas") or [])
        return [(d, 55.0 if d in dz else 1.0) for d in cls._dezena_range()]

    @classmethod
    def _alvos_de_linha(cls, row: Dict[str, Any]) -> Dict[str, int]:
        sp = cls._spec()
        return {cod: int(row.get(cod, 0)) for cod in sp.indicadores}

    @classmethod
    def _perfil_referencia(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        sp = cls._spec()
        comp = cls._alvos_de_linha(row)
        vals = " · ".join(f"{c} {comp[c]}" for c in sp.indicadores)
        return {
            "concurso": row.get("concurso"),
            "data": row.get("data"),
            "comportamento": comp,
            "texto": f"#{row.get('concurso')} ({row.get('data') or '—'}) — {vals}",
            "texto_curto": f"#{row.get('concurso')} — {vals}",
        }

    @classmethod
    def _motor_exclui_ultimo_concurso(cls, modo_motor: str) -> bool:
        """Perfil real e híbrido ignoram o último sorteio na rotação de perfis."""
        return modo_motor in ("perfil_sorteio", "hibrido")

    @classmethod
    def _linhas_para_geracao(
        cls,
        analise: Dict[str, Any],
        filtros: Optional[Dict[str, int]] = None,
        excluir_ultimo: bool = False,
    ) -> List[Dict[str, Any]]:
        linhas = list(analise.get("linhas") or [])
        if filtros:
            linhas = [r for r in linhas if all(r.get(fk) == fv for fk, fv in filtros.items())]
        if excluir_ultimo and linhas:
            linhas = linhas[1:]
        return linhas

    @classmethod
    def _prev_dezenas_historica_linha(
        cls,
        linhas_ordenadas: List[Dict[str, Any]],
        linha_ref: Dict[str, Any],
    ) -> Optional[List[int]]:
        """
        Dezenas do concurso imediatamente anterior ao perfil copiado.
        linhas_ordenadas: mais recente primeiro (como analise.linhas).
        """
        concurso = linha_ref.get("concurso")
        idx = next(
            (i for i, r in enumerate(linhas_ordenadas) if r.get("concurso") == concurso),
            -1,
        )
        if idx < 0 or idx + 1 >= len(linhas_ordenadas):
            return None
        return list(linhas_ordenadas[idx + 1].get("dezenas") or [])

    @classmethod
    def _motor_aposta_indice(cls, modo_motor: str, indice: int) -> str:
        if modo_motor == "perfil_sorteio":
            return "perfil_sorteio"
        if modo_motor == "moda":
            return "moda"
        return "perfil_sorteio" if indice % 2 == 0 else "moda"

    @classmethod
    def _sorteio_ponderado(cls, pesos: List[Tuple[int, float]], k: int) -> List[int]:
        pool = list(pesos)
        escolhidas: List[int] = []
        while len(escolhidas) < k and pool:
            total_w = sum(w for _, w in pool)
            r = random.random() * total_w
            acc = 0.0
            idx_pick = len(pool) - 1
            for i, (_, w) in enumerate(pool):
                acc += w
                if r <= acc:
                    idx_pick = i
                    break
            d, _ = pool.pop(idx_pick)
            escolhidas.append(d)
        return escolhidas

    @classmethod
    def _ajustar_indicador(
        cls,
        escolhidas: List[int],
        k: int,
        codigo: str,
        alvo: int,
        prev_dezenas: Optional[List[int]] = None,
        candidatos: Optional[List[int]] = None,
    ) -> List[int]:
        sp = cls._spec()
        if codigo not in sp.indicadores_dezena:
            return sorted(escolhidas[:k])

        cats = cls._dezenas_por_categoria()
        cand = candidatos or list(cls._dezena_range())
        escolhidas = list(escolhidas)[:k]

        mapa_swap = {
            "PA": ("par", "impar"),
            "IM": ("impar", "par"),
            "PR": ("primo", "nao_primo"),
            "MO": ("moldura", "centro"),
            "M3": ("m3", "nao_m3"),
            "FB": ("fb", "nao_fb"),
        }

        tent = 0
        while tent < 120:
            tent += 1
            atual = cls._valor_indicador_aposta(escolhidas, codigo, prev_dezenas, None)
            if atual == alvo:
                break
            precisa_mais = atual < alvo

            if codigo in mapa_swap:
                fav, desfav = mapa_swap[codigo]
                if precisa_mais:
                    fora = [d for d in escolhidas if d in cats[desfav]]
                    dentro = [d for d in cand if d in cats[fav] and d not in escolhidas]
                else:
                    fora = [d for d in escolhidas if d in cats[fav]]
                    dentro = [d for d in cand if d in cats[desfav] and d not in escolhidas]
                if fora and dentro:
                    escolhidas[escolhidas.index(fora[0])] = random.choice(dentro)
                    continue

            if codigo == "RT" and prev_dezenas:
                rep_set = set(prev_dezenas)
                if precisa_mais:
                    fora = [d for d in escolhidas if d not in rep_set]
                    dentro = [d for d in rep_set if d not in escolhidas]
                else:
                    fora = [d for d in escolhidas if d in rep_set]
                    dentro = [d for d in cand if d not in rep_set and d not in escolhidas]
                if fora and dentro:
                    escolhidas[escolhidas.index(fora[0])] = random.choice(dentro)
                    continue

            if codigo == "SQ":
                if precisa_mais and len(escolhidas) >= 2:
                    base = random.choice(escolhidas)
                    viz = [base - 1, base + 1]
                    viz = [v for v in viz if sp.dezena_min <= v <= sp.universo and v not in escolhidas]
                    fora = random.choice(escolhidas)
                    if viz:
                        escolhidas[escolhidas.index(fora)] = random.choice(viz)
                        continue
                break
            break

        while len(escolhidas) < k:
            rest = [c for c in cand if c not in escolhidas]
            if not rest:
                break
            escolhidas.append(random.choice(rest))
        return sorted(escolhidas[:k])

    @classmethod
    def _regras_ativas(cls, regras: Dict[str, Any]) -> List[str]:
        sp = cls._spec()
        return [cod for cod in sp.indicadores if regras.get(f"usar_{cod}")]

    @classmethod
    def _score_aposta(
        cls,
        dezenas: List[int],
        alvos: Dict[str, int],
        ativos: List[str],
        prev_dezenas: Optional[List[int]],
        extras: Optional[Dict[str, int]] = None,
    ) -> int:
        ind = cls._calcular_indicadores(dezenas, prev_dezenas, extras)
        score = 0
        for cod in ativos:
            if cod not in ind:
                continue
            diff = abs(ind[cod] - alvos.get(cod, ind[cod]))
            if diff == 0:
                score += 10
            elif diff == 1:
                score += 5
        return score

    @classmethod
    def _tentar_montar_aposta(
        cls,
        k: int,
        alvos: Dict[str, int],
        ativos: List[str],
        pesos_base: List[Tuple[int, float]],
        ultimo_prev: Optional[List[int]],
        perfil: str,
        score_min: int,
        candidatos: List[int],
        extras_alvo: Optional[Dict[str, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        sp = cls._spec()
        ativos_dez = [c for c in ativos if c in sp.indicadores_dezena]
        alvos_dez = {c: alvos[c] for c in ativos_dez if c in alvos}

        jitter = random.random() * 8
        pesos = [(d, w + jitter * random.random()) for d, w in pesos_base]

        if perfil == "conservador":
            pesos = sorted(pesos, key=lambda x: -x[1])
        elif perfil == "agressivo":
            pesos = sorted(pesos, key=lambda x: x[1] + random.random() * 30)
        else:
            random.shuffle(pesos)

        pick = cls._sorteio_ponderado(pesos, k)
        if len(pick) < k:
            return None

        for cod in ativos_dez:
            pick = cls._ajustar_indicador(
                pick, k, cod, alvos_dez.get(cod, 0), ultimo_prev, candidatos,
            )

        extras_pick: Dict[str, int] = {}
        if extras_alvo:
            for cod in ("MS", "TM", "T1", "T2"):
                if cod in ativos and cod in extras_alvo:
                    extras_pick[cod] = int(extras_alvo[cod])

        score = cls._score_aposta(pick, alvos, ativos, ultimo_prev, extras_pick or None)
        if score < score_min:
            return None

        ind_aposta = cls._calcular_indicadores(pick, ultimo_prev, extras_pick or None)
        sobreposicao = len(set(pick) & set(ultimo_prev)) if ultimo_prev else 0
        out = {
            "dezenas": sorted(pick),
            "comportamento": ind_aposta,
            "sobreposicao": sobreposicao,
            "score_comportamento": score,
            "alvos_aposta": dict(alvos),
        }
        if sp.has_mes and "MS" in extras_pick:
            out["mes"] = extras_pick["MS"]
            out["mes_nome"] = MESES_NOME.get(extras_pick["MS"], str(extras_pick["MS"]))
        if sp.has_time and "TM" in extras_pick:
            out["time"] = extras_pick["TM"]
            out["time_num"] = extras_pick["TM"]
        if sp.has_trevos and "T1" in extras_pick:
            out["trevos"] = [extras_pick["T1"], extras_pick["T2"]]
            out["t1"] = extras_pick["T1"]
            out["t2"] = extras_pick["T2"]
        return out

    @classmethod
    def analisar(
        cls,
        janela: int = 10,
        filtros: Optional[Dict[str, int]] = None,
        base_estatistica: str = "geral",
        relaxar_janela: bool = False,
    ) -> Dict[str, Any]:
        sp = cls._spec()
        if not relaxar_janela and janela not in sp.janelas_validas:
            janela = sp.janela_default
        elif relaxar_janela and janela < 0:
            janela = sp.janela_default

        base_estat = cls._normalizar_base_estatistica(base_estatistica)
        meta = cls._meta_bases_dados()
        sorteios = cls._carregar_sorteios_asc(base_estat)
        if not sorteios:
            label = BASES_ESTATISTICA_LABEL.get(base_estat, base_estat)
            return {
                "sucesso": False,
                "erro": f"Nenhum sorteio na base «{label}».",
                "base_estatistica": base_estat,
                "base_label": label,
                "meta_bases": meta,
            }

        janela_sorteios = sorteios if janela == 0 else sorteios[-janela:]
        linhas: List[Dict[str, Any]] = []
        for i, s in enumerate(janela_sorteios):
            dz = cls._dezenas_from_sorteio(s)
            prev = cls._dezenas_from_sorteio(janela_sorteios[i - 1]) if i > 0 else None
            ex = cls._extras_from_sorteio(s)
            ind = cls._calcular_indicadores(dz, prev, ex or None)
            for cod in sp.indicadores:
                ind.setdefault(cod, 0)
            row = {
                "concurso": s.concurso,
                "data": s.data,
                "dezenas": dz,
                **ind,
            }
            if sp.has_mes and "MS" in ex:
                row["mes_num"] = ex["MS"]
                row["mes_nome"] = getattr(s, "mes_nome", None) or MESES_NOME.get(ex["MS"], "")
                row["mes_abrev"] = MESES_ABREV.get(ex["MS"], "")
            if sp.has_time and "TM" in ex:
                row["time_num"] = ex["TM"]
                row["time_nome"] = getattr(s, "time_nome", None) or ""
            linhas.append(row)

        linhas_filtradas = cls._aplicar_filtros_linhas(linhas, filtros)
        resumo_base = cls._resumo_indicadores(linhas)
        resumo_filtro = cls._resumo_indicadores(linhas_filtradas) if filtros else None

        ultimo = sorteios[-1]
        ultimo_prev = cls._dezenas_from_sorteio(sorteios[-2]) if len(sorteios) > 1 else None
        ultimo_ex = cls._extras_from_sorteio(ultimo)
        ultimo_ind = cls._calcular_indicadores(
            cls._dezenas_from_sorteio(ultimo), ultimo_prev, ultimo_ex or None,
        )

        aviso = cls._aviso_base_pendentes(meta, base_estat)
        out: Dict[str, Any] = {
            "sucesso": True,
            "base_estatistica": base_estat,
            "base_label": BASES_ESTATISTICA_LABEL.get(base_estat, base_estat),
            "meta_bases": meta,
            "janela": janela,
            "janela_label": "Todos" if janela == 0 else f"Últimos {janela}",
            "total_concursos": len(sorteios),
            "total_concursos_base": len(sorteios),
            "total_concursos_geral": int(meta.get("total_geral") or len(sorteios)),
            "total_janela": len(linhas),
            "ultimo_concurso": ultimo.concurso,
            "linhas": list(reversed(linhas)),
            "linhas_filtradas_count": len(linhas_filtradas),
            "filtros_ativos": filtros or {},
            "resumo": resumo_base,
            "resumo_filtrado": resumo_filtro,
            "criterios_sugeridos": cls._criterios_sugeridos(resumo_base),
            "ultimo_indicadores": ultimo_ind,
            "indicadores": [
                {"codigo": c, "label": sp.indicador_labels[c]} for c in sp.indicadores
            ],
            "pool_pesos": cls._pool_dezenas(linhas_filtradas or linhas),
        }
        if aviso:
            out["aviso_base"] = aviso
        return out

    @classmethod
    def _regras_automaticas_interno(cls, analise: Dict[str, Any]) -> Dict[str, Any]:
        sp = cls._spec()
        resumo = analise.get("resumo") or {}
        ultimo = analise.get("ultimo_indicadores") or {}
        regras: Dict[str, Any] = {}

        for cod in sp.indicadores:
            moda = resumo.get(cod, {}).get("moda")
            moda_pct = resumo.get(cod, {}).get("moda_pct", 0)
            ult = ultimo.get(cod)
            usar = moda_pct >= 18 or (ult is not None and ult == moda)
            regras[f"usar_{cod}"] = usar
            regras[f"alvo_{cod}"] = moda

        if not any(regras.get(f"usar_{c}") for c in sp.indicadores):
            for cod in sp.regras_fallback:
                regras[f"usar_{cod}"] = True
                regras[f"alvo_{cod}"] = resumo.get(cod, {}).get("moda", 0)

        return regras

    @classmethod
    def gerar_apostas(
        cls,
        quantidade: int = 10,
        dezenas_por_jogo: Optional[int] = None,
        janela: int = 10,
        perfil: str = "equilibrado",
        modo_geracao: str = "automatico",
        modo_motor: str = "perfil_sorteio",
        regras_manuais: Optional[Dict[str, Any]] = None,
        filtros: Optional[Dict[str, int]] = None,
        analise: Optional[Dict[str, Any]] = None,
        base_estatistica: str = "geral",
    ) -> Dict[str, Any]:
        sp = cls._spec()
        base = cls._normalizar_base_estatistica(
            (analise or {}).get("base_estatistica") or base_estatistica
        )
        if analise is None:
            analise = cls.analisar(janela, filtros, base_estatistica=base)
        if not analise.get("sucesso"):
            return analise

        if modo_motor not in MOTORES_GERACAO:
            modo_motor = "perfil_sorteio"

        k = max(sp.dezenas_min, min(int(dezenas_por_jogo or sp.dezenas_default), sp.dezenas_max))
        quantidade = max(1, min(int(quantidade), 200))

        sorteios_geral = cls._carregar_sorteios_asc("geral")
        ultimo_prev = (
            cls._dezenas_from_sorteio(sorteios_geral[-2]) if len(sorteios_geral) > 1 else None
        )

        excluir_ultimo = cls._motor_exclui_ultimo_concurso(modo_motor)
        analise_geracao = analise
        if excluir_ultimo and janela > 0:
            janela_geracao = janela + 1
            if len(analise.get("linhas") or []) < janela_geracao:
                extra = cls.analisar(
                    janela_geracao,
                    filtros,
                    base_estatistica=base,
                    relaxar_janela=True,
                )
                if extra.get("sucesso"):
                    analise_geracao = extra

        linhas_todas = list(analise_geracao.get("linhas") or [])
        linhas_ref = cls._linhas_para_geracao(
            analise_geracao, filtros, excluir_ultimo=excluir_ultimo,
        )
        ultimo_ignorado = None
        if excluir_ultimo and linhas_todas:
            ultimo_ignorado = linhas_todas[0].get("concurso")

        if excluir_ultimo and linhas_ref:
            resumo_ref = cls._resumo_indicadores(linhas_ref)
            alvos_moda = {
                cod: (resumo_ref.get(cod) or {}).get("moda", 0)
                for cod in sp.indicadores
            }
        else:
            alvos_moda = dict(analise["criterios_sugeridos"]["alvos"])

        if modo_geracao == "automatico":
            regras = regras_manuais or cls._regras_automaticas_interno(analise)
        else:
            regras = dict(regras_manuais or {})
            for cod in sp.indicadores:
                regras.setdefault(f"usar_{cod}", True)

        if not linhas_ref and modo_motor in ("perfil_sorteio", "hibrido"):
            return {
                "sucesso": False,
                "erro": "Nenhum sorteio na janela/filtro para usar como perfil real.",
            }

        pesos_janela = cls._pool_dezenas(linhas_ref)
        candidatos = list(cls._dezena_range())
        historico_combos = carregar_combinacoes_historicas(
            cls.SorteioModel, cls._dezenas_from_sorteio,
        )
        descartadas_historico = 0

        apostas: List[Dict[str, Any]] = []
        vistos: Set[Tuple[int, ...]] = set()

        ms_analise = cls._meses_indicados_analise() if cls._usa_meses_indicados() else None
        aviso_ms = None
        if ms_analise and ms_analise.get("sem_indicados"):
            aviso_ms = (
                "Nenhum mês ausente nos últimos 10 concursos — "
                "Mês da Sorte não foi atribuído automaticamente."
            )

        def _extras_alvo_de(alvos_dict: Dict[str, int]) -> Optional[Dict[str, int]]:
            ex: Dict[str, int] = {}
            for cod in ("MS", "TM", "T1", "T2"):
                if cod == "MS" and cls._usa_meses_indicados():
                    continue
                if cod in alvos_dict:
                    ex[cod] = int(alvos_dict[cod])
            return ex or None

        for idx in range(quantidade):
            motor_aposta = cls._motor_aposta_indice(modo_motor, idx)
            linha_ref = linhas_ref[idx % len(linhas_ref)] if linhas_ref else None

            if motor_aposta == "perfil_sorteio" and linha_ref:
                alvos = cls._alvos_de_linha(linha_ref)
                ativos = cls._sem_ms(list(sp.indicadores))
                pesos_base = cls._pool_dezenas_linha(linha_ref)
                score_min = len(ativos) * 10
                perfil_ref = cls._perfil_referencia(linha_ref)
                extras_alvo = _extras_alvo_de(alvos)
            else:
                alvos = dict(alvos_moda)
                if regras_manuais:
                    for cod in sp.indicadores:
                        manual = regras_manuais.get(f"alvo_{cod}")
                        if manual is not None and str(manual) != "":
                            alvos[cod] = int(manual)
                ativos = cls._sem_ms(cls._regras_ativas(regras))
                if not ativos:
                    ativos = cls._sem_ms(list(sp.indicadores))
                pesos_base = pesos_janela
                score_min = len(ativos) * 5
                perfil_ref = None
                extras_alvo = _extras_alvo_de({c: alvos[c] for c in ativos if c in alvos})

            if modo_geracao == "manual" and motor_aposta == "perfil_sorteio":
                ativos = cls._sem_ms(cls._regras_ativas(regras) or list(sp.indicadores))
                alvos = {c: alvos[c] for c in ativos if c in alvos}
                score_min = len(ativos) * 10
                extras_alvo = _extras_alvo_de(alvos)

            if motor_aposta == "perfil_sorteio" and linha_ref:
                prev_rt = cls._prev_dezenas_historica_linha(linhas_todas, linha_ref)
            else:
                prev_rt = ultimo_prev

            tentativas = 0
            max_tent = 1200 if motor_aposta == "perfil_sorteio" else 600
            montada = None

            while tentativas < max_tent and montada is None:
                tentativas += 1
                montada = cls._tentar_montar_aposta(
                    k, alvos, ativos, pesos_base, prev_rt, perfil, score_min, candidatos, extras_alvo,
                )
                if montada is None:
                    continue
                chave = tuple(montada["dezenas"])
                if chave in vistos:
                    montada = None
                    continue
                if aposta_ja_sorteada(montada["dezenas"], historico_combos):
                    descartadas_historico += 1
                    montada = None
                    continue

            if montada is None:
                continue

            vistos.add(tuple(montada["dezenas"]))
            ind_aposta = montada["comportamento"]
            fmt = (lambda n: f"{n:02d}") if sp.dezena_min == 0 else (lambda n: f"{n:02d}")
            aposta_item: Dict[str, Any] = {
                "numero": len(apostas) + 1,
                "dezenas": montada["dezenas"],
                "quantidade": k,
                "texto": " ".join(fmt(n) for n in montada["dezenas"]),
                "comportamento": ind_aposta,
                "sobreposicao": montada["sobreposicao"],
                "do_ultimo_par": montada["sobreposicao"],
                "pares": ind_aposta["PA"],
                "impares": ind_aposta["IM"],
                "score_comportamento": montada["score_comportamento"],
                "modo_motor_aposta": motor_aposta,
                "perfil_referencia": perfil_ref,
                "alvos_aposta": montada["alvos_aposta"],
            }
            if sp.has_mes and montada.get("mes") is not None and not cls._usa_meses_indicados():
                aposta_item["mes"] = montada["mes"]
                aposta_item["mes_nome"] = montada.get("mes_nome", "")
            if sp.has_time and montada.get("time") is not None:
                aposta_item["time"] = montada["time"]
                aposta_item["time_num"] = montada.get("time_num", montada["time"])
            if sp.has_trevos and montada.get("trevos"):
                aposta_item["trevos"] = montada["trevos"]
                aposta_item["t1"] = montada.get("t1")
                aposta_item["t2"] = montada.get("t2")
            if ms_analise:
                cls._aplicar_mes_indicado_aposta(aposta_item, idx, ms_analise)
            apostas.append(aposta_item)

        aviso = None
        if len(apostas) < quantidade:
            partes = [
                f"Geradas {len(apostas)} de {quantidade} apostas.",
            ]
            if descartadas_historico:
                partes.append(
                    f"{descartadas_historico} combinação(ões) descartada(s) por já existirem no histórico oficial."
                )
            partes.append(
                "Alguns perfis reais da tabela são difíceis de reproduzir — "
                "tente outro período, modo híbrido ou menos apostas."
            )
            aviso = " ".join(partes)
        if aviso_ms:
            aviso = f"{aviso_ms} {aviso or ''}".strip()

        return {
            "sucesso": True,
            "base_estatistica": base,
            "base_label": BASES_ESTATISTICA_LABEL.get(base, base),
            "apostas": apostas,
            "total_geradas": len(apostas),
            "solicitados": quantidade,
            "aviso": aviso,
            "meses_indicados": ms_analise,
            "alvos": alvos_moda,
            "regras_aplicadas": regras,
            "modo_motor": modo_motor,
            "modo_motor_label": MOTOR_LABELS.get(modo_motor, modo_motor),
            "janela": janela,
            "filtros_ativos": filtros or {},
            "perfis_disponiveis": len(linhas_ref),
            "descartadas_historico": descartadas_historico,
            "validacao_ineditas": True,
            "excluiu_ultimo_concurso": excluir_ultimo,
            "ultimo_concurso_ignorado": ultimo_ignorado,
        }

    @classmethod
    def gerar_apostas_panorama_top(
        cls,
        quantidade: int = 10,
        dezenas_por_jogo: Optional[int] = None,
        perfil: str = "equilibrado",
        base_estatistica: str = "geral",
        rank_escolhido: int = 1,
        analise: Optional[Dict[str, Any]] = None,
        pool_dezenas: Optional[List[int]] = None,
        modo_validacao: str = "estrito",
    ) -> Dict[str, Any]:
        from geradores_elite.comportamento.panorama_indicadores import calcular_panorama_indicadores
        from geradores_elite.comportamento.panorama_top_geracao import (
            label_rank_escolhido,
            montar_alvos_por_rank,
            normalizar_rank_escolhido,
            score_minimo_panorama,
        )

        sp = cls._spec()
        base = cls._normalizar_base_estatistica(base_estatistica)
        rank_escolhido = normalizar_rank_escolhido(rank_escolhido)
        rank_label = label_rank_escolhido(rank_escolhido)

        if analise is None:
            analise = cls.analisar(janela=0, base_estatistica=base)
        if not analise.get("sucesso"):
            return analise

        linhas = list(analise.get("linhas") or [])
        panorama = calcular_panorama_indicadores(
            linhas, sp.indicadores, sp.indicador_labels,
        )
        indicadores_out = panorama.get("indicadores") or []
        alvos_fixos, alvos_meta_fixos = montar_alvos_por_rank(
            indicadores_out, list(sp.indicadores), rank_escolhido,
        )
        if not alvos_fixos:
            return {
                "sucesso": False,
                "erro": f"Nenhum alvo disponível para o {rank_label} na base selecionada.",
            }

        k = max(sp.dezenas_min, min(int(dezenas_por_jogo or sp.dezenas_default), sp.dezenas_max))
        quantidade = max(1, min(int(quantidade), 200))
        modo_val = (modo_validacao or "estrito").strip().lower()
        if modo_val not in ("estrito", "relaxar"):
            modo_val = "estrito"

        pool_set: Optional[Set[int]] = None
        if pool_dezenas:
            pool_set = {int(d) for d in pool_dezenas}
            if len(pool_set) < k:
                return {
                    "sucesso": False,
                    "erro": (
                        f"Pool com {len(pool_set)} dezena(s) — insuficiente para apostas de {k}."
                    ),
                }

        sorteios_geral = cls._carregar_sorteios_asc("geral")
        ultimo_prev = (
            cls._dezenas_from_sorteio(sorteios_geral[-2]) if len(sorteios_geral) > 1 else None
        )

        linhas_ref = cls._linhas_para_geracao(analise, None) or linhas
        pesos_janela = cls._pool_dezenas(linhas_ref)
        if pool_set:
            pesos_janela = [(d, w) for d, w in pesos_janela if d in pool_set]
            candidatos = sorted(pool_set)
        else:
            candidatos = list(cls._dezena_range())
        historico_combos = carregar_combinacoes_historicas(
            cls.SorteioModel, cls._dezenas_from_sorteio,
        )

        ativos = cls._sem_ms(list(sp.indicadores))
        ativos_dez = [c for c in ativos if c in sp.indicadores_dezena]
        score_min = score_minimo_panorama(len(ativos_dez), rank_escolhido, modo_val)
        extras_alvo = None
        ex: Dict[str, int] = {}
        for cod in ("MS", "TM", "T1", "T2"):
            if cod == "MS" and cls._usa_meses_indicados():
                continue
            if cod in alvos_fixos:
                ex[cod] = int(alvos_fixos[cod])
        if ex:
            extras_alvo = ex

        ms_analise = cls._meses_indicados_analise() if cls._usa_meses_indicados() else None
        aviso_ms = None
        if ms_analise and ms_analise.get("sem_indicados"):
            aviso_ms = (
                "Nenhum mês ausente nos últimos 10 concursos — "
                "Mês da Sorte não foi atribuído automaticamente."
            )

        descartadas_historico = 0
        apostas: List[Dict[str, Any]] = []
        vistos: Set[Tuple[int, ...]] = set()

        for idx in range(quantidade):
            tentativas = 0
            max_tent = 800
            montada = None

            while tentativas < max_tent and montada is None:
                tentativas += 1
                montada = cls._tentar_montar_aposta(
                    k, alvos_fixos, ativos, pesos_janela, ultimo_prev, perfil,
                    score_min, candidatos, extras_alvo,
                )
                if montada is None:
                    continue
                chave = tuple(montada["dezenas"])
                if chave in vistos:
                    montada = None
                    continue
                if aposta_ja_sorteada(montada["dezenas"], historico_combos):
                    descartadas_historico += 1
                    montada = None
                    continue

            if montada is None:
                continue

            vistos.add(tuple(montada["dezenas"]))
            ind_aposta = montada["comportamento"]
            fmt = (lambda n: f"{n:02d}") if sp.dezena_min == 0 else (lambda n: f"{n:02d}")
            aposta_item: Dict[str, Any] = {
                "numero": len(apostas) + 1,
                "dezenas": montada["dezenas"],
                "quantidade": k,
                "texto": " ".join(fmt(n) for n in montada["dezenas"]),
                "comportamento": ind_aposta,
                "sobreposicao": montada["sobreposicao"],
                "do_ultimo_par": montada["sobreposicao"],
                "pares": ind_aposta["PA"],
                "impares": ind_aposta["IM"],
                "score_comportamento": montada["score_comportamento"],
                "modo_motor_aposta": "panorama_top",
                "perfil_referencia": None,
                "alvos_aposta": dict(alvos_fixos),
                "alvos_panorama_meta": dict(alvos_meta_fixos),
                "rank_escolhido": rank_escolhido,
                "rank_escolhido_label": rank_label,
            }
            if sp.has_mes and montada.get("mes") is not None and not cls._usa_meses_indicados():
                aposta_item["mes"] = montada["mes"]
                aposta_item["mes_nome"] = montada.get("mes_nome", "")
            if sp.has_time and montada.get("time") is not None:
                aposta_item["time"] = montada["time"]
                aposta_item["time_num"] = montada.get("time_num", montada["time"])
            if sp.has_trevos and montada.get("trevos"):
                aposta_item["trevos"] = montada["trevos"]
                aposta_item["t1"] = montada.get("t1")
                aposta_item["t2"] = montada.get("t2")
            if ms_analise:
                cls._aplicar_mes_indicado_aposta(aposta_item, idx, ms_analise)
            apostas.append(aposta_item)

        aviso = None
        if len(apostas) < quantidade:
            partes = [f"Geradas {len(apostas)} de {quantidade} apostas (Panorama Top-3)."]
            if descartadas_historico:
                partes.append(
                    f"{descartadas_historico} combinação(ões) descartada(s) por já existirem no histórico."
                )
            partes.append(
                f"Tente outro ranking ou menos apostas se a combinação de alvos for muito restritiva."
            )
            aviso = " ".join(partes)
        if aviso_ms:
            aviso = f"{aviso_ms} {aviso or ''}".strip()

        return {
            "sucesso": True,
            "base_estatistica": base,
            "base_label": BASES_ESTATISTICA_LABEL.get(base, base),
            "apostas": apostas,
            "total_geradas": len(apostas),
            "solicitados": quantidade,
            "aviso": aviso,
            "modo_geracao": "panorama_top",
            "modo_motor": "panorama_top",
            "modo_motor_label": f"Panorama — {rank_label}",
            "rank_escolhido": rank_escolhido,
            "rank_escolhido_label": rank_label,
            "alvos_panorama": alvos_fixos,
            "alvos_panorama_meta": alvos_meta_fixos,
            "panorama": panorama,
            "score_min_usado": score_min,
            "modo_validacao": modo_val,
            "pool_dezenas": sorted(pool_set) if pool_set else None,
            "descartadas_historico": descartadas_historico,
            "validacao_ineditas": True,
        }

    @classmethod
    def ultimo_sorteio_info(cls) -> Dict[str, Any]:
        sorteios = cls._carregar_sorteios_asc("geral")
        if not sorteios:
            return {"concurso": None, "data": "", "dezenas": []}
        ult = sorteios[-1]
        return {
            "concurso": ult.concurso,
            "data": getattr(ult, "data", "") or "",
            "dezenas": cls._dezenas_from_sorteio(ult),
        }

    @classmethod
    def panorama_selecao_contexto(
        cls,
        base_estatistica: str = "geral",
        rank_escolhido: int = 1,
        analise: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from geradores_elite.comportamento.panorama_indicadores import calcular_panorama_indicadores
        from geradores_elite.comportamento.panorama_selecao import listar_categorias_dezenas
        from geradores_elite.comportamento.panorama_top_geracao import (
            label_rank_escolhido,
            montar_alvos_por_rank,
            normalizar_rank_escolhido,
        )

        sp = cls._spec()
        base = cls._normalizar_base_estatistica(base_estatistica)
        rank_escolhido = normalizar_rank_escolhido(rank_escolhido)

        if analise is None:
            analise = cls.analisar(janela=0, base_estatistica=base)
        if not analise.get("sucesso"):
            return analise

        linhas = list(analise.get("linhas") or [])
        panorama = calcular_panorama_indicadores(
            linhas, sp.indicadores, sp.indicador_labels,
        )
        alvos, alvos_meta = montar_alvos_por_rank(
            panorama.get("indicadores") or [], list(sp.indicadores), rank_escolhido,
        )
        sorteios = cls._carregar_sorteios_asc("geral")
        ultimo = sorteios[-1] if sorteios else None
        ultimo_dz = cls._dezenas_from_sorteio(ultimo) if ultimo else []
        ultimo_prev = (
            cls._dezenas_from_sorteio(sorteios[-2]) if len(sorteios) > 1 else None
        )
        cats = cls._dezenas_por_categoria()
        categorias = listar_categorias_dezenas(cls._dezena_range(), cats, ultimo_dz)

        cotas = []
        for cod in sp.indicadores:
            if cod not in alvos:
                continue
            meta = alvos_meta.get(cod) or {}
            cotas.append({
                "codigo": cod,
                "label": sp.indicador_labels.get(cod, cod),
                "alvo": alvos[cod],
                "valor_label": meta.get("valor_label", str(alvos[cod])),
                "percentual": meta.get("percentual"),
            })

        mes_info = None
        if sp.has_mes and "MS" in alvos:
            mn = int(alvos["MS"])
            mes_info = {
                "num": mn,
                "nome": MESES_NOME.get(mn, str(mn)),
                "abrev": MESES_ABREV.get(mn, ""),
            }

        return {
            "sucesso": True,
            "base_estatistica": base,
            "base_label": BASES_ESTATISTICA_LABEL.get(base, base),
            "rank_escolhido": rank_escolhido,
            "rank_escolhido_label": label_rank_escolhido(rank_escolhido),
            "alvos": alvos,
            "alvos_meta": alvos_meta,
            "cotas": cotas,
            "categorias": categorias,
            "ultimo_sorteio": {
                "concurso": ultimo.concurso if ultimo else None,
                "data": getattr(ultimo, "data", "") if ultimo else "",
                "dezenas": ultimo_dz,
            },
            "ultimo_prev_dezenas": ultimo_prev or [],
            "dezenas_por_jogo": sp.dezenas_default,
            "dezenas_min": sp.dezenas_min,
            "dezenas_max": sp.dezenas_max,
            "pool_max": sp.pool_panorama,
            "universo_max": sp.universo,
            "dezena_min": sp.dezena_min,
            "mes_alvo": mes_info,
        }

    @classmethod
    def validar_selecao_panorama_api(
        cls,
        dezenas: List[int],
        base_estatistica: str = "geral",
        rank_escolhido: int = 1,
        modo: str = "estrito",
        dezenas_por_jogo: Optional[int] = None,
        analise: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from geradores_elite.comportamento.panorama_selecao import validar_selecao_panorama

        sp = cls._spec()
        ctx = cls.panorama_selecao_contexto(
            base_estatistica=base_estatistica,
            rank_escolhido=rank_escolhido,
            analise=analise,
        )
        if not ctx.get("sucesso"):
            return ctx

        k = max(
            sp.dezenas_min,
            min(int(dezenas_por_jogo or sp.dezenas_default), sp.dezenas_max),
        )
        alvos = ctx.get("alvos") or {}
        extras: Dict[str, int] = {}
        if sp.has_mes and "MS" in alvos:
            extras["MS"] = int(alvos["MS"])

        sorteios = cls._carregar_sorteios_asc("geral")
        ultimo_prev = (
            cls._dezenas_from_sorteio(sorteios[-2]) if len(sorteios) > 1 else None
        )

        def _calc(dz, prev, ex):
            return cls._calcular_indicadores(dz, prev, ex)

        result = validar_selecao_panorama(
            dezenas,
            k,
            alvos,
            tuple(sp.indicadores_dezena),
            _calc,
            ultimo_prev,
            extras or None,
            modo,
        )
        result["sucesso"] = True
        result["rank_escolhido"] = ctx.get("rank_escolhido")
        result["rank_escolhido_label"] = ctx.get("rank_escolhido_label")
        result["alvos"] = alvos
        result["mes_alvo"] = ctx.get("mes_alvo")
        return result

    @classmethod
    def gerar_apostas_por_linhas(
        cls,
        quantidade: int = 10,
        dezenas_por_jogo: Optional[int] = None,
        janela: int = 0,
        base_estatistica: str = "geral",
        top_n: int = 3,
        linhas_ids: Optional[List[str]] = None,
        modo_peso: str = "frequencia",
    ) -> Dict[str, Any]:
        """
        Gera apostas ponderando dezenas pelas linhas L1–L10 mais frequentes.
        Reutiliza LinhasUniversoService (mesma regra de /analise/linhas-dd-du/).
        """
        from linhas_universo.core import dezenas_da_linha, linhas_para_modalidade
        from linhas_universo.service import LinhasUniversoService

        sp = cls._spec()
        base = cls._normalizar_base_estatistica(base_estatistica)
        k = max(sp.dezenas_min, min(int(dezenas_por_jogo or sp.dezenas_default), sp.dezenas_max))
        quantidade = max(1, min(int(quantidade), 200))
        top_n = max(1, min(int(top_n or 3), 10))
        if modo_peso not in ("frequencia", "uniforme", "so_top1"):
            modo_peso = "frequencia"

        analise = LinhasUniversoService.analisar(
            sp.modality_key, janela=janela, base_estatistica=base,
        )
        if not analise.get("sucesso"):
            return analise

        freq = list(analise.get("frequencia_linhas") or [])
        ranking = sorted(
            freq,
            key=lambda x: (-int(x.get("ocorrencias") or 0), str(x.get("linha") or "")),
        )
        for i, row in enumerate(ranking, start=1):
            row["posicao"] = i

        if linhas_ids:
            ids = {str(x).upper() for x in linhas_ids if x}
            selecionadas = [r for r in ranking if str(r.get("linha") or "").upper() in ids]
        elif modo_peso == "so_top1":
            selecionadas = ranking[:1]
        else:
            selecionadas = ranking[:top_n]

        if not selecionadas:
            return {
                "sucesso": False,
                "erro": "Nenhuma linha selecionada no ranking para gerar apostas.",
            }

        mapa = linhas_para_modalidade(sp.modality_key)
        dmin, dmax = int(mapa["dezena_min"]), int(mapa["dezena_max"])

        # peso por dezena (partição L1–L10 → cada dezena pertence a 1 linha)
        peso_dez: Dict[int, float] = {}
        linhas_usadas = []
        for r in selecionadas:
            lid = r["linha"]
            occ = max(1, int(r.get("ocorrencias") or 1))
            peso_linha = float(occ) if modo_peso == "frequencia" else 1.0
            dezs = dezenas_da_linha(lid, dmin, dmax)
            linhas_usadas.append({
                "linha": lid,
                "label": r.get("label"),
                "posicao": r.get("posicao"),
                "ocorrencias": occ,
                "pct": r.get("pct"),
                "qtd_dezenas": len(dezs),
            })
            for d in dezs:
                peso_dez[int(d)] = max(peso_dez.get(int(d), 0.0), peso_linha)

        pool = [(d, w) for d, w in peso_dez.items() if w > 0]
        if len(pool) < k:
            return {
                "sucesso": False,
                "erro": (
                    f"Pool insuficiente: {len(pool)} dezenas nas linhas escolhidas "
                    f"(precisa de pelo menos {k}). Amplie o Top-N ou selecione mais linhas."
                ),
                "linhas_usadas": linhas_usadas,
            }

        historico_combos = carregar_combinacoes_historicas(
            cls.SorteioModel, cls._dezenas_from_sorteio,
        )
        ms_analise = cls._meses_indicados_analise() if cls._usa_meses_indicados() else None
        fmt = lambda n: f"{int(n):02d}"
        apostas: List[Dict[str, Any]] = []
        vistos: Set[Tuple[int, ...]] = set()
        descartadas_historico = 0

        for idx in range(quantidade * 40):
            if len(apostas) >= quantidade:
                break
            items = list(pool)
            uniq: List[int] = []
            for _ in range(k):
                if not items:
                    break
                nums = [d for d, _ in items]
                weights = [w for _, w in items]
                pick = random.choices(nums, weights=weights, k=1)[0]
                uniq.append(pick)
                items = [(d, w) for d, w in items if d != pick]
            if len(uniq) < k:
                continue
            uniq = sorted(uniq)
            chave = tuple(uniq)
            if chave in vistos:
                continue
            if aposta_ja_sorteada(uniq, historico_combos):
                descartadas_historico += 1
                continue
            vistos.add(chave)
            item: Dict[str, Any] = {
                "numero": len(apostas) + 1,
                "dezenas": uniq,
                "quantidade": k,
                "texto": " ".join(fmt(n) for n in uniq),
                "modo_motor_aposta": "linhas_ranking",
                "linhas_origem": [x["linha"] for x in linhas_usadas],
                "criterios": [
                    f"Linhas {', '.join(x['linha'] for x in linhas_usadas)}",
                    f"Peso: {modo_peso}",
                ],
                "marcas": [],
            }
            if ms_analise:
                cls._aplicar_mes_indicado_aposta(item, len(apostas), ms_analise)
            apostas.append(item)

        aviso = None
        if len(apostas) < quantidade:
            aviso = f"Geradas {len(apostas)} de {quantidade} apostas inéditas com o pool das linhas."

        return {
            "sucesso": True,
            "apostas": apostas,
            "total_geradas": len(apostas),
            "solicitados": quantidade,
            "aviso": aviso,
            "modo_geracao": "linhas_ranking",
            "modo_motor": "linhas_ranking",
            "modo_motor_label": "Comportamento das Linhas (L1–L10)",
            "modo_peso": modo_peso,
            "top_n": top_n,
            "linhas_usadas": linhas_usadas,
            "ranking": ranking,
            "descartadas_historico": descartadas_historico,
            "base_estatistica": base,
            "base_label": analise.get("base_label", base),
            "janela": analise.get("janela", janela),
            "primeiro_concurso": analise.get("primeiro_concurso"),
            "ultimo_concurso": analise.get("ultimo_concurso"),
            "total_concursos": analise.get("total_concursos"),
            "link_analise": "/analise/linhas-dd-du/",
        }
