# -*- coding: utf-8 -*-
"""Serviço genérico — repetição entre concursos + gerador de apostas."""
from __future__ import annotations

import importlib
import random
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import desc

from models.shared import db

from analise_comparar.compare_service import (
    _dezenas_ordered,
    _dezenas_set,
    _load_model,
    _pares_impares,
    _repetidas_posicional,
)

from .repeticao_config import get_repeticao_config
from .repeticao_extra import (
    _pick_um,
    analisar_extra,
    enrich_concurso_payload,
    formatar_texto_aposta,
    gerar_extra,
)


def _classificar_tendencia(taxa: float, media: float) -> str:
    if taxa >= media + 8:
        return "permanencia"
    if taxa <= media - 8:
        return "saida"
    return "neutra"


def _obter_ciclo() -> Dict[str, Any]:
    try:
        mod = importlib.import_module("services.ciclo_service")
        for name in dir(mod):
            if not name.startswith("Ciclo"):
                continue
            cls = getattr(mod, name)
            if hasattr(cls, "obter_ciclo_atual"):
                return cls.obter_ciclo_atual() or {}
    except Exception:
        pass
    return {}


class RepeticaoConcursosService:
    def __init__(self, modality_key: str):
        self.modality_key = modality_key
        self.cfg = get_repeticao_config(modality_key)
        self.Model = _load_model(self.cfg)
        self._time_names: Dict[int, str] = {}
        if self.cfg.get("extra_time"):
            try:
                from models.sorteio_timemania import TIMES_DO_CORACAO

                self._time_names = {int(k): str(v) for k, v in TIMES_DO_CORACAO.items()}
            except Exception:
                pass

    def _sorteio_idx(self) -> int:
        return int(self.cfg.get("default_sorteio", 1))

    def _carregar_sorteios_asc(self) -> List[Any]:
        return (
            db.session.query(self.Model)
            .order_by(self.Model.concurso.asc())
            .all()
        )

    def _set_dezenas(self, row: Any) -> Set[int]:
        return _dezenas_set(row, self.cfg, self._sorteio_idx())

    def _ord_dezenas(self, row: Any) -> List[int]:
        return _dezenas_ordered(row, self.cfg, self._sorteio_idx())

    def _posicional(self, a: Any, b: Any) -> List[Dict[str, int]]:
        modos = self.cfg.get("modos") or ["volante"]
        if "posicional" not in modos and "hibrido" not in modos:
            return []
        if self.cfg.get("layout") == "colunas":
            ca = _dezenas_ordered(a, self.cfg)
            cb = _dezenas_ordered(b, self.cfg)
            return _repetidas_posicional(ca, cb)
        if self.cfg.get("ordered_fields"):
            return _repetidas_posicional(
                [getattr(a, f) for f in self.cfg["ordered_fields"]],
                [getattr(b, f) for f in self.cfg["ordered_fields"]],
            )
        return _repetidas_posicional(self._ord_dezenas(a), self._ord_dezenas(b))

    def _build_stats_dezenas(self) -> Dict[Any, Dict[str, Any]]:
        cfg = self.cfg
        if cfg.get("layout") == "colunas":
            return {}

        sorteios = (
            db.session.query(self.Model)
            .order_by(self.Model.concurso.desc())
            .all()
        )
        if not sorteios:
            return {}

        ultimo = sorteios[0].concurso
        total = len(sorteios)
        freq: Counter = Counter()
        pos_por: Dict[int, Counter] = defaultdict(Counter)
        visto: Dict[int, int] = {}
        slots = cfg["slots_por_concurso"]

        for s in reversed(sorteios):
            ordered = self._ord_dezenas(s)
            for i, d in enumerate(ordered, start=1):
                freq[d] += 1
                pos_por[d][i] += 1
                if d not in visto:
                    visto[d] = s.concurso

        ciclo = _obter_ciclo()
        no_ciclo = set(ciclo.get("dezenas_sorteadas") or [])
        faltantes = set(ciclo.get("dezenas_faltantes") or [])
        slots_totais = total * slots
        stats: Dict[Any, Dict[str, Any]] = {}

        for d in range(cfg["dezena_min"], cfg["dezena_max"] + 1):
            pos_pred = None
            if pos_por[d]:
                pos_pred = max(pos_por[d].items(), key=lambda x: x[1])[0]
            atraso = ultimo if d not in visto else ultimo - visto[d]
            if d in no_ciclo:
                ciclo_txt = f"No ciclo {ciclo.get('ciclo_num', 1)} (já sorteada)"
            elif d in faltantes:
                ciclo_txt = f"No ciclo {ciclo.get('ciclo_num', 1)} (faltante)"
            else:
                ciclo_txt = "—"
            stats[d] = {
                "frequencia": freq[d],
                "freq_pct": round((freq[d] / slots_totais) * 100, 2) if slots_totais else 0,
                "atraso": atraso,
                "posicao_predominante": pos_pred,
                "ciclo": ciclo_txt,
            }
        return stats

    def listar_concursos(self, limit: int = 150) -> List[Dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        rows = (
            db.session.query(self.Model)
            .order_by(desc(self.Model.concurso))
            .limit(lim)
            .all()
        )
        out = []
        for s in rows:
            item = {
                "concurso": s.concurso,
                "data": getattr(s, "data", None),
                "dezenas": sorted(self._set_dezenas(s)),
            }
            if self.cfg.get("layout") == "colunas":
                item["colunas"] = _dezenas_ordered(s, self.cfg)
            enrich_concurso_payload(s, self.cfg, item)
            out.append(item)
        return out

    def obter_concurso(self, concurso: int) -> Optional[Dict[str, Any]]:
        s = db.session.get(self.Model, int(concurso))
        if not s:
            return None
        row = {
            "concurso": s.concurso,
            "data": getattr(s, "data", None),
            "dezenas": sorted(self._set_dezenas(s)),
        }
        if self.cfg.get("layout") == "colunas":
            row["colunas"] = _dezenas_ordered(s, self.cfg)
        enrich_concurso_payload(s, self.cfg, row)
        return row

    def analisar_completo(self, modo: str = "volante") -> Dict[str, Any]:
        cfg = self.cfg
        modos = cfg.get("modos") or ["volante"]
        modo = modo if modo in modos else modos[0]

        if cfg.get("layout") == "colunas":
            return self._analisar_colunas(modo)

        sorteios = self._carregar_sorteios_asc()
        if len(sorteios) < 2:
            return {"sucesso": False, "erro": "É necessário ao menos 2 concursos no banco."}

        total_pares = len(sorteios) - 1
        dmin, dmax = cfg["dezena_min"], cfg["dezena_max"]

        qtd_rep_por_par: List[int] = []
        contagem = Counter()
        permanencia = defaultdict(lambda: {"eventos": 0, "permaneceu": 0})

        for i in range(1, len(sorteios)):
            ant = self._set_dezenas(sorteios[i - 1])
            at = self._set_dezenas(sorteios[i])
            rep = ant & at
            qtd_rep_por_par.append(len(rep))
            for d in rep:
                contagem[d] += 1
                if i + 1 < len(sorteios):
                    permanencia[d]["eventos"] += 1
                    if d in self._set_dezenas(sorteios[i + 1]):
                        permanencia[d]["permaneceu"] += 1

        media_qtd = round(sum(qtd_rep_por_par) / len(qtd_rep_por_par), 2) if qtd_rep_por_par else 0

        pares_rep: List[int] = []
        impares_rep: List[int] = []
        for i in range(1, len(sorteios)):
            rep = list(self._set_dezenas(sorteios[i - 1]) & self._set_dezenas(sorteios[i]))
            if rep:
                p, im = _pares_impares(rep)
                pares_rep.append(p)
                impares_rep.append(im)

        media_pares = round(sum(pares_rep) / len(pares_rep), 2) if pares_rep else 0
        media_impares = round(sum(impares_rep) / len(impares_rep), 2) if impares_rep else 0

        taxas = []
        for d in range(dmin, dmax + 1):
            ev = permanencia[d]["eventos"]
            if ev:
                taxas.append(permanencia[d]["permaneceu"] / ev * 100)
        media_perm = round(sum(taxas) / len(taxas), 1) if taxas else 0

        ult, pen = sorteios[-1], sorteios[-2]
        ante = sorteios[-3] if len(sorteios) >= 3 else None
        rep_v = sorted(self._set_dezenas(ult) & self._set_dezenas(pen))
        rep_pos = self._posicional(pen, ult)
        p_ult, im_ult = _pares_impares(rep_v)

        qtd_pos: List[int] = []
        for i in range(1, len(sorteios)):
            n = len(self._posicional(sorteios[i - 1], sorteios[i]))
            qtd_pos.append(n)
        media_pos = round(sum(qtd_pos) / len(qtd_pos), 2) if qtd_pos else 0

        detalhe = []
        for d in range(dmin, dmax + 1):
            ev = permanencia[d]["eventos"]
            perm = permanencia[d]["permaneceu"]
            taxa = round(perm / ev * 100, 1) if ev else 0
            freq = contagem[d]
            detalhe.append({
                "dezena": d,
                "par": d % 2 == 0,
                "freq_repeticao_vezes": freq,
                "freq_repeticao_pct": round(freq / total_pares * 100, 2) if total_pares else 0,
                "permanencia_eventos": ev,
                "permanencia_vezes": perm,
                "permanencia_pct": taxa,
                "tendencia": _classificar_tendencia(taxa, media_perm),
                "repetiu_ultimo_par_volante": d in rep_v,
                "repetiu_ultimo_par_posicional": any(x["dezena"] == d for x in rep_pos),
            })
        detalhe.sort(key=lambda x: (-x["freq_repeticao_vezes"], x["dezena"]))

        ranking = sorted(range(dmin, dmax + 1), key=lambda d: -contagem[d])[:10]

        payload = {
            "sucesso": True,
            "modo": modo,
            "total_pares_analisados": total_pares,
            "ultimo_concurso": ult.concurso,
            "penultimo_concurso": pen.concurso,
            "antepenultimo_concurso": ante.concurso if ante is not None else None,
            "ultimo_sorteio": self._ord_dezenas(ult),
            "penultimo_sorteio": self._ord_dezenas(pen),
            "antepenultimo_sorteio": self._ord_dezenas(ante) if ante is not None else [],
            "resumo_ultimo_par": {
                "volante": {
                    "quantidade": len(rep_v),
                    "dezenas": rep_v,
                    "pares": p_ult,
                    "impares": im_ult,
                },
                "posicional": {"quantidade": len(rep_pos), "itens": rep_pos},
                "media_historica_quantidade_volante": media_qtd,
                "media_historica_posicional": media_pos,
            },
            "padroes_grupo": {
                "media_pares_quando_repete": media_pares,
                "media_impares_quando_repete": media_impares,
                "media_permanencia_apos_repeticao_pct": media_perm,
            },
            "ranking_mais_repetem": [
                {
                    "dezena": d,
                    "vezes": contagem[d],
                    "pct": round(contagem[d] / total_pares * 100, 2),
                }
                for d in ranking
            ],
            "dezenas": detalhe,
            "stats_dezenas": self._build_stats_dezenas(),
        }
        extra = analisar_extra(cfg, sorteios, ult, pen, total_pares, self._time_names)
        if extra:
            payload["extra"] = extra
        return payload

    def _analisar_colunas(self, modo: str) -> Dict[str, Any]:
        cfg = self.cfg
        sorteios = self._carregar_sorteios_asc()
        if len(sorteios) < 2:
            return {"sucesso": False, "erro": "É necessário ao menos 2 concursos no banco."}

        total_pares = len(sorteios) - 1
        n_col = cfg["colunas"]
        contagem_col = [Counter() for _ in range(n_col)]
        qtd_rep: List[int] = []

        for i in range(1, len(sorteios)):
            ca = _dezenas_ordered(sorteios[i - 1], cfg)
            cb = _dezenas_ordered(sorteios[i], cfg)
            rep = _repetidas_posicional(ca, cb)
            qtd_rep.append(len(rep))
            for item in rep:
                contagem_col[item["posicao"] - 1][item["dezena"]] += 1

        ult, pen = sorteios[-1], sorteios[-2]
        rep_ult = self._posicional(pen, ult)
        media_rep = round(sum(qtd_rep) / len(qtd_rep), 2) if qtd_rep else 0

        detalhe = []
        for col in range(1, n_col + 1):
            c = contagem_col[col - 1]
            top = c.most_common(1)
            contagem_dict = {d: c.get(d, 0) for d in range(cfg.get("digito_min", 0), cfg.get("digito_max", 9) + 1)}
            detalhe.append({
                "dezena": col,
                "label": f"C{col}",
                "par": col % 2 == 0,
                "freq_repeticao_vezes": sum(c.values()),
                "freq_repeticao_pct": round(sum(c.values()) / total_pares * 100, 2) if total_pares else 0,
                "permanencia_eventos": 0,
                "permanencia_vezes": 0,
                "permanencia_pct": 0,
                "tendencia": "neutra",
                "repetiu_ultimo_par_volante": False,
                "repetiu_ultimo_par_posicional": any(x["posicao"] == col for x in rep_ult),
                "digito_mais_repete": top[0][0] if top else None,
                "digito_mais_repete_vezes": top[0][1] if top else 0,
                "contagem_quando_repete": contagem_dict,
            })

        return {
            "sucesso": True,
            "modo": modo,
            "layout": "colunas",
            "total_pares_analisados": total_pares,
            "ultimo_concurso": ult.concurso,
            "penultimo_concurso": pen.concurso,
            "ultimo_sorteio": _dezenas_ordered(ult, cfg),
            "penultimo_sorteio": _dezenas_ordered(pen, cfg),
            "resumo_ultimo_par": {
                "volante": {"quantidade": 0, "dezenas": [], "pares": 0, "impares": 0},
                "posicional": {"quantidade": len(rep_ult), "itens": rep_ult},
                "media_historica_quantidade_volante": media_rep,
                "media_historica_posicional": media_rep,
            },
            "padroes_grupo": {
                "media_pares_quando_repete": 0,
                "media_impares_quando_repete": 0,
                "media_permanencia_apos_repeticao_pct": 0,
            },
            "ranking_mais_repetem": [],
            "dezenas": detalhe,
            "stats_dezenas": {},
        }

    def _pool_dezenas(
        self,
        analise: Dict[str, Any],
        modo: str,
        usar_ultimo_par: bool,
        so_permanencia: bool,
        jitter: float = 0.0,
        sniper_opts: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[int, float]]:
        cfg = self.cfg
        media_perm = analise["padroes_grupo"]["media_permanencia_apos_repeticao_pct"]
        pesos: List[Tuple[int, float]] = []
        ev = (sniper_opts or {}).get("evidencias") or {}
        quentes: Set[int] = set()
        frios: Set[int] = set()
        if sniper_opts and sniper_opts.get("usar_top_digitos"):
            for item in ev.get("numeros_fortes") or []:
                d = item.get("dezena", item.get("digito"))
                if d is not None:
                    quentes.add(int(d))
        if sniper_opts and sniper_opts.get("usar_numeros_frios"):
            for item in ev.get("numeros_frios") or []:
                d = item.get("dezena", item.get("digito"))
                if d is not None:
                    frios.add(int(d))
        foco = sniper_opts.get("dezena_foco") if sniper_opts else None
        if foco is None and sniper_opts:
            foco = sniper_opts.get("digito_foco")
        try:
            foco_int = int(foco) if foco is not None and foco != "" else None
        except (TypeError, ValueError):
            foco_int = None

        for row in analise["dezenas"]:
            d = row["dezena"]
            w = row["freq_repeticao_pct"] * 0.35 + row["permanencia_pct"] * 0.45 + jitter
            rv = row["repetiu_ultimo_par_volante"]
            rp = row["repetiu_ultimo_par_posicional"]
            if usar_ultimo_par:
                if modo == "volante" and rv:
                    w += 45
                elif modo == "posicional" and rp:
                    w += 42
                elif modo == "hibrido" and (rv or rp):
                    w += 44
                else:
                    w += 4
            if so_permanencia:
                if row["tendencia"] == "permanencia":
                    w += 25
                elif row["tendencia"] == "saida":
                    w *= 0.12
                else:
                    w *= 0.45
            if row["tendencia"] == "permanencia":
                w += 12
            elif row["tendencia"] == "saida":
                w -= 8
            if row["permanencia_pct"] > media_perm:
                w += 5
            if d in quentes:
                w += 22.0
            if d in frios:
                w += 14.0
            if foco_int is not None and d == foco_int:
                w += 28.0
            if sniper_opts and sniper_opts.get("so_permanencia"):
                if row["tendencia"] != "permanencia":
                    w *= 0.2
            pesos.append((d, max(0.5, w)))
        return pesos

    @staticmethod
    def _sorteio_ponderado(pesos: List[Tuple[int, float]], k: int) -> List[int]:
        pool = list(pesos)
        out: List[int] = []
        while len(out) < k and pool:
            total = sum(w for _, w in pool)
            r = random.random() * total
            acc = 0.0
            idx = len(pool) - 1
            for i, (d, w) in enumerate(pool):
                acc += w
                if r <= acc:
                    idx = i
                    break
            d, _ = pool.pop(idx)
            out.append(d)
        return out

    def _ajustar_par_impar(
        self, pick: List[int], k: int, alvo_pares: int, universo: List[int],
    ) -> List[int]:
        pick = list(pick)
        while len(pick) < k:
            rest = [c for c in universo if c not in pick]
            if not rest:
                break
            pick.append(random.choice(rest))
        pick = pick[:k]

        def n_pares(lst):
            return sum(1 for x in lst if x % 2 == 0)

        tent = 0
        while n_pares(pick) != alvo_pares and tent < 80 and len(pick) == k:
            tent += 1
            p_idx = [i for i, x in enumerate(pick) if x % 2 == 0]
            i_idx = [i for i, x in enumerate(pick) if x % 2 != 0]
            if n_pares(pick) < alvo_pares and i_idx:
                for c in universo:
                    if c % 2 == 0 and c not in pick:
                        pick[i_idx[0]] = c
                        break
            elif n_pares(pick) > alvo_pares and p_idx:
                for c in universo:
                    if c % 2 != 0 and c not in pick:
                        pick[p_idx[0]] = c
                        break
            else:
                break
        return sorted(pick)

    @staticmethod
    def _tipo_aposta_digitos(digits: List[int]) -> str:
        try:
            from services.analise_supersete_service import AnaliseSuperSeteService

            return AnaliseSuperSeteService._classificar_intrasorte(digits)[0]
        except Exception:
            contagem: Dict[int, int] = {}
            for d in digits:
                contagem[d] = contagem.get(d, 0) + 1
            duplas = sum(1 for q in contagem.values() if q == 2)
            trincas = sum(1 for q in contagem.values() if q == 3)
            outros = sum(1 for q in contagem.values() if q > 3)
            if duplas == 0 and trincas == 0 and outros == 0:
                return "0_repeticao"
            if duplas == 1 and trincas == 0 and outros == 0:
                return "1_dupla"
            if duplas == 2 and trincas == 0 and outros == 0:
                return "2_duplas"
            if trincas == 1 and duplas == 0 and outros == 0:
                return "1_trinca"
            return "outros"

    def _aplicar_pesos_intrasorte(
        self,
        col: int,
        pesos: Dict[int, float],
        sniper_opts: Optional[Dict[str, Any]],
        intrasorte: Optional[Dict[str, Any]],
    ) -> None:
        if not sniper_opts or not intrasorte:
            return
        if sniper_opts.get("usar_top_digitos"):
            for i, item in enumerate(intrasorte.get("top_3_repetidos") or []):
                d = item.get("digito")
                if d is not None and d in pesos:
                    pesos[d] += max(int(item.get("qtd_sorteios", 0)), 1) * (18.0 - i * 5)
        foco = sniper_opts.get("digito_foco")
        if foco is not None and foco != "" and int(foco) in pesos:
            pesos[int(foco)] += 28.0

        ev = sniper_opts.get("evidencias") or {}
        if sniper_opts.get("usar_numeros_frios"):
            for item in ev.get("numeros_frios") or []:
                d = item.get("digito")
                if d is not None and d in pesos:
                    pesos[d] += 14.0
        if sniper_opts.get("usar_colunas_fortes") and col <= len(ev.get("colunas_fortes") or []):
            top_cols = {x["coluna"] for x in ev.get("colunas_fortes") or []}
            if col in top_cols:
                for d in pesos:
                    pesos[d] += 6.0

    def _par_colunas_sniper(
        self,
        sniper_opts: Optional[Dict[str, Any]],
        intrasorte: Optional[Dict[str, Any]],
    ) -> Optional[Tuple[int, int]]:
        if not sniper_opts or not sniper_opts.get("usar_pares_colunas") or not intrasorte:
            return None
        pares = intrasorte.get("top_pares_colunas") or []
        if not pares:
            return None
        idx = sniper_opts.get("par_colunas_idx")
        try:
            idx = int(idx) if idx is not None and idx != "" else 0
        except (TypeError, ValueError):
            idx = 0
        if idx < 0 or idx >= len(pares):
            idx = 0
        p = pares[idx]
        return int(p["c1"]), int(p["c2"])

    def _aplicar_pesos_volante(
        self,
        col: int,
        pesos: Dict[int, float],
        volante_colunas: Optional[Dict[Any, Any]],
    ) -> None:
        if not volante_colunas:
            return
        dados = volante_colunas.get(col) or volante_colunas.get(str(col))
        if not dados:
            return
        for i, dig in enumerate((dados.get("rank_atraso") or [])[:3]):
            if dig in pesos:
                pesos[dig] += (3 - i) * 12.0
        rank_freq = dados.get("rank_freq") or []
        if rank_freq and rank_freq[0] in pesos:
            pesos[rank_freq[0]] += 8.0
        atual = dados.get("digito_atual")
        if atual is not None and atual in pesos:
            pesos[atual] += 4.0

    def _pick_digito_coluna(
        self,
        col: int,
        analise: Dict[str, Any],
        usar_ultimo_par: bool,
        perfil: str,
        volante_colunas: Optional[Dict[Any, Any]] = None,
        sniper_opts: Optional[Dict[str, Any]] = None,
        intrasorte: Optional[Dict[str, Any]] = None,
        prefer_digit: Optional[int] = None,
    ) -> int:
        cfg = self.cfg
        dig_min = cfg.get("digito_min", 0)
        dig_max = cfg.get("digito_max", 9)
        opts = list(range(dig_min, dig_max + 1))
        usar_seq = bool(
            sniper_opts.get("usar_sequencial", True) if sniper_opts else usar_ultimo_par
        )

        if prefer_digit is not None and prefer_digit in opts:
            if sniper_opts and sniper_opts.get("forcar_par_colunas"):
                return prefer_digit
            opts_weighted = {d: (55.0 if d == prefer_digit else 1.0) for d in opts}
            return _pick_um(list(opts_weighted.items()))

        if not usar_ultimo_par and not usar_seq:
            pesos = {d: 1.0 for d in opts}
            self._aplicar_pesos_volante(col, pesos, volante_colunas)
            self._aplicar_pesos_intrasorte(col, pesos, sniper_opts, intrasorte)
            lista = list(pesos.items())
            if perfil == "agressivo":
                lista = [(d, w + random.random() * 20) for d, w in lista]
            elif perfil == "conservador":
                lista = sorted(lista, key=lambda x: -x[1])
            else:
                random.shuffle(lista)
            return _pick_um(lista)

        rep_itens = analise["resumo_ultimo_par"]["posicional"].get("itens") or []
        rep_map = {x["posicao"]: x["dezena"] for x in rep_itens}
        ult_cols = analise.get("ultimo_sorteio") or []
        pesos = {d: 1.0 for d in opts}
        detalhe = analise.get("dezenas") or []
        if usar_seq and col <= len(detalhe):
            row = detalhe[col - 1]
            dm = row.get("digito_mais_repete")
            if dm is not None and dm in pesos:
                pesos[dm] += float(row.get("freq_repeticao_vezes", 0)) * 0.4
        if usar_ultimo_par and col in rep_map and rep_map[col] in pesos:
            pesos[rep_map[col]] += 35
        if usar_ultimo_par and col <= len(ult_cols) and ult_cols[col - 1] in pesos:
            pesos[ult_cols[col - 1]] += 18

        self._aplicar_pesos_volante(col, pesos, volante_colunas)
        self._aplicar_pesos_intrasorte(col, pesos, sniper_opts, intrasorte)

        lista = list(pesos.items())
        if perfil == "agressivo":
            lista = [(d, w + random.random() * 20) for d, w in lista]
        elif perfil == "conservador":
            lista = sorted(lista, key=lambda x: -x[1])
        else:
            random.shuffle(lista)
        return _pick_um(lista)

    def _gerar_colunas(
        self,
        analise: Dict[str, Any],
        quantidade: int,
        perfil: str,
        usar_ultimo_par: bool,
        volante_colunas: Optional[Dict[Any, Any]] = None,
        sniper_opts: Optional[Dict[str, Any]] = None,
        intrasorte: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cfg = self.cfg
        n_col = cfg["colunas"]
        rep_itens = analise["resumo_ultimo_par"]["posicional"].get("itens") or []
        rep_map = {x["posicao"]: x["dezena"] for x in rep_itens}
        par = self._par_colunas_sniper(sniper_opts, intrasorte)
        tipo_alvo = (sniper_opts or {}).get("tipo_sorteio_alvo") or ""
        if tipo_alvo in ("", "any", "qualquer"):
            tipo_alvo = ""

        apostas = []
        vistos = set()
        join = cfg.get("export_join", " ")
        max_tent = max(quantidade * 600, 2500)

        for _ in range(max_tent):
            if len(apostas) >= quantidade:
                break
            digits_map: Dict[int, int] = {}
            for col in range(1, n_col + 1):
                prefer = None
                if par:
                    c1, c2 = par
                    if col == c2 and c1 in digits_map:
                        prefer = digits_map[c1]
                d = self._pick_digito_coluna(
                    col,
                    analise,
                    usar_ultimo_par,
                    perfil,
                    volante_colunas,
                    sniper_opts=sniper_opts,
                    intrasorte=intrasorte,
                    prefer_digit=prefer,
                )
                digits_map[col] = d
            digits = [digits_map[i] for i in range(1, n_col + 1)]
            if tipo_alvo and self._tipo_aposta_digitos(digits) != tipo_alvo:
                continue
            chave = tuple(digits)
            if chave in vistos:
                continue
            vistos.add(chave)
            texto = join.join(str(d) for d in digits)
            apostas.append({
                "numero": len(apostas) + 1,
                "dezenas": digits,
                "quantidade": len(digits),
                "pares": sum(1 for d in digits if d % 2 == 0),
                "impares": sum(1 for d in digits if d % 2 != 0),
                "do_ultimo_par": sum(1 for i, d in enumerate(digits, 1) if rep_map.get(i) == d),
                "texto": texto,
            })

        aviso = None
        if len(apostas) < quantidade:
            aviso = f"Solicitados {quantidade}; gerados {len(apostas)}."
        return {"sucesso": True, "apostas": apostas, "total_geradas": len(apostas), "solicitados": quantidade, "aviso": aviso}

    def gerar_apostas(
        self,
        quantidade: int = 10,
        dezenas_por_jogo: Optional[int] = None,
        modo: str = "volante",
        perfil: str = "equilibrado",
        usar_ultimo_par: bool = True,
        so_permanencia: bool = False,
        respeitar_par_impar: bool = True,
        analise: Optional[Dict[str, Any]] = None,
        volante_colunas: Optional[Dict[Any, Any]] = None,
        sniper_opts: Optional[Dict[str, Any]] = None,
        intrasorte: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cfg = self.cfg
        if analise is None:
            analise = self.analisar_completo(modo)
        if not analise.get("sucesso"):
            return analise

        quantidade = max(1, min(int(quantidade), 200))
        k_default = cfg["dezenas_default"]
        k = max(cfg["dezenas_min"], min(int(dezenas_por_jogo or k_default), cfg["dezenas_max"]))

        if cfg.get("layout") == "colunas":
            r = self._gerar_colunas(
                analise,
                quantidade,
                perfil,
                usar_ultimo_par,
                volante_colunas=volante_colunas,
                sniper_opts=sniper_opts,
                intrasorte=intrasorte,
            )
            r["parametros"] = {
                "quantidade": quantidade,
                "modo": modo,
                "perfil": perfil,
                "volante_sniper": bool(volante_colunas),
                "sniper_opts": sniper_opts or {},
            }
            return r

        rep_vol = analise["resumo_ultimo_par"]["volante"]["dezenas"]
        alvo_pares = analise["resumo_ultimo_par"]["volante"]["pares"]
        if respeitar_par_impar and not rep_vol:
            alvo_pares = round(analise["padroes_grupo"]["media_pares_quando_repete"])

        universo = list(range(cfg["dezena_min"], cfg["dezena_max"] + 1))
        apostas = []
        vistos = set()
        tentativas = 0
        max_tent = max(quantidade * 400, 800)

        while len(apostas) < quantidade and tentativas < max_tent:
            tentativas += 1
            jitter = random.random() * 12
            pesos = self._pool_dezenas(
                analise, modo, usar_ultimo_par, so_permanencia, jitter, sniper_opts=sniper_opts,
            )
            if perfil == "conservador":
                pesos = sorted(pesos, key=lambda x: -x[1])
            elif perfil == "agressivo":
                pesos = sorted(pesos, key=lambda x: x[1] + random.random() * 25)
            else:
                random.shuffle(pesos)

            pick = self._sorteio_ponderado(pesos, k)
            if len(pick) < k:
                continue
            if respeitar_par_impar:
                pick = self._ajustar_par_impar(pick, k, alvo_pares, universo)
            else:
                pick = sorted(pick)

            chave = tuple(pick)
            if len(pick) != k or chave in vistos:
                continue
            vistos.add(chave)
            p, im = _pares_impares(pick)
            do_ult = len(set(pick) & set(rep_vol))
            extra_fields = gerar_extra(
                cfg, analise, usar_ultimo_par, perfil, self._time_names, aposta_idx=len(apostas),
            )
            texto = formatar_texto_aposta(cfg, pick, extra_fields)
            item = {
                "numero": len(apostas) + 1,
                "dezenas": pick,
                "quantidade": k,
                "pares": p,
                "impares": im,
                "do_ultimo_par": do_ult,
                "texto": texto,
            }
            item.update(extra_fields)
            apostas.append(item)

        aviso = None
        if len(apostas) < quantidade:
            aviso = (
                f"Solicitados {quantidade} apostas; gerados {len(apostas)}. "
                "Tente desmarcar filtros restritivos ou mude o perfil."
            )

        out = {
            "sucesso": True,
            "apostas": apostas,
            "total_geradas": len(apostas),
            "solicitados": quantidade,
            "aviso": aviso,
            "parametros": {
                "quantidade": quantidade,
                "dezenas_por_jogo": k,
                "modo": modo,
                "perfil": perfil,
                "usar_ultimo_par": usar_ultimo_par,
                "so_permanencia": so_permanencia,
                "respeitar_par_impar": respeitar_par_impar,
            },
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            out = ValidadorGeradoresElite.aplicar(
                out,
                origem="repeticao_apostas",
                modality_key=self.modality_key,
                campo="apostas",
                sorteio_model=self.Model,
                dezenas_fn=lambda s: list(self._ord_dezenas(s) or sorted(self._set_dezenas(s))),
            )
        except Exception:
            pass
        return out
