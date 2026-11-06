# -*- coding: utf-8 -*-
"""Concursos em conferencia_apostas/<modalidade>/<numero>/apostas.json."""
import heapq
import importlib
import json
import os
import re
from collections import Counter
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import desc, func

from models.shared import db

from .config import get_conf

try:
    from configuracoes.acertos_posicionais import (
        contar_acertos_posicional,
        digitos_acertados,
        normalizar_aposta_ss,
        validar_aposta_ss,
    )
except ImportError:
    from _shared.configuracoes.acertos_posicionais import (  # type: ignore
        contar_acertos_posicional,
        digitos_acertados,
        normalizar_aposta_ss,
        validar_aposta_ss,
    )


def _scoring_positional(cfg: dict) -> bool:
    return cfg.get("scoring") == "positional" or cfg.get("key") == "supersete"


def _repo_root() -> str:
    """Raiz do repositório (pai de _shared), independente do cwd do app."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _apostas_root() -> str:
    return os.path.join(_repo_root(), "conferencia_apostas")


def pasta_modalidade(cfg: dict) -> str:
    slug = cfg.get("pasta_apostas") or cfg["key"]
    return os.path.join(_apostas_root(), slug)


def _contar_screenshots(pasta: str) -> int:
    try:
        nomes = os.listdir(pasta)
    except OSError:
        return 0
    return sum(1 for nome in nomes if nome.lower().endswith((".jpg", ".jpeg", ".png")))


def _arquivo_json(pasta: str) -> Optional[str]:
    """apostas.json do conversor; se não houver, o primeiro *.json que não é cópia."""
    preferido = os.path.join(pasta, "apostas.json")
    if os.path.isfile(preferido):
        return preferido
    extras = []
    try:
        nomes = os.listdir(pasta)
    except OSError:
        return None
    for nome in nomes:
        baixo = nome.lower()
        if not baixo.endswith(".json"):
            continue
        if "copia" in baixo or baixo.startswith("apostas_"):
            continue
        extras.append(os.path.join(pasta, nome))
    extras.sort()
    return extras[0] if extras else None


def _load_sorteio_model(cfg: dict):
    mod = importlib.import_module(cfg["sorteio_model"][0])
    return getattr(mod, cfg["sorteio_model"][1])


def _sorteadas(sorteio, cfg: dict) -> List[int]:
    method = cfg["dezenas_method"]
    if hasattr(sorteio, method):
        return list(getattr(sorteio, method)())
    if hasattr(sorteio, "dezenas_lista"):
        return list(sorteio.dezenas_lista())
    if hasattr(sorteio, "dezenas"):
        d = sorteio.dezenas()
        return sorted(d) if isinstance(d, set) else list(d)
    return []


def _ordem_sorteio(sorteio, cfg: dict) -> List[int]:
    """Ordem em que as dezenas saíram (d1…dn). Cai na lista oficial se o modelo não guardar a ordem."""
    if sorteio is not None and hasattr(sorteio, "dezenas_ordem_lista"):
        try:
            ordem = [int(n) for n in sorteio.dezenas_ordem_lista()]
        except (TypeError, ValueError):
            ordem = []
        if ordem:
            return ordem
    return list(_sorteadas(sorteio, cfg))


_CFG_PRECO = {"diasorte": "diadesorte"}

_MESES = {
    "jan": 1, "janeiro": 1, "fev": 2, "fevereiro": 2, "mar": 3, "marco": 3, "março": 3,
    "abr": 4, "abril": 4, "mai": 5, "maio": 5, "jun": 6, "junho": 6,
    "jul": 7, "julho": 7, "ago": 8, "agosto": 8, "set": 9, "setembro": 9,
    "out": 10, "outubro": 10, "nov": 11, "novembro": 11, "dez": 12, "dezembro": 12,
}


def _chave_preco(cfg: dict) -> str:
    return _CFG_PRECO.get(cfg["key"], cfg["key"])


def _mes_num(valor) -> Optional[int]:
    if valor is None:
        return None
    if isinstance(valor, int) and 1 <= valor <= 12:
        return valor
    txt = str(valor).strip().lower()
    if txt.isdigit():
        n = int(txt)
        return n if 1 <= n <= 12 else None
    return _MESES.get(txt)


_PRECO_VOLANTE_CACHE: Dict[Tuple[str, int], float] = {}


def _preco_volante(cfg: dict, n_dezenas: int) -> float:
    """Preço oficial da página Configurações (aposta simples editável + tabela Caixa)."""
    chave = _chave_preco(cfg)
    cache_key = (chave, int(n_dezenas))
    if cache_key in _PRECO_VOLANTE_CACHE:
        return _PRECO_VOLANTE_CACHE[cache_key]
    valor = float(n_dezenas)
    try:
        from configuracoes.regras_modalidade import preco_aposta
        from configuracoes.settings_service import obter_preco_simples
        from configuracoes.config import MODALITIES

        tabela = preco_aposta(chave, int(n_dezenas))
        meta = MODALITIES.get(chave) or {}
        simples_n = int((meta.get("aposta") or {}).get("simples") or cfg["combo_size"])
        catalogo = preco_aposta(chave, simples_n)
        atual = float(obter_preco_simples(chave))
        if tabela is not None and catalogo:
            valor = round(float(tabela) * (atual / float(catalogo)), 2)
        elif tabela is not None:
            valor = round(float(tabela), 2)
        elif atual:
            valor = round(atual, 2)
    except Exception:
        valor = float(n_dezenas)
    _PRECO_VOLANTE_CACHE[cache_key] = valor
    return valor


# Caixa: 5 acertos, 4 acertos e Mês da Sorte são prêmios fixos.
# 7 e 6 vêm do rateio do concurso. O mês acumula com qualquer faixa de dezenas.
_FIXOS_DIASORTE = {5: 25.0, 4: 5.0, 0: 2.5}


_API_SLUG = {
    "lotofacil": "lotofacil",
    "quina": "quina",
    "megasena": "megasena",
    "maismilionaria": "maismilionaria",
    "duplasena": "duplasena",
    "timemania": "timemania",
    "lotomania": "lotomania",
    "supersete": "supersete",
}
_RATEIO_CACHE: Dict[Tuple[str, int], Dict[Any, float]] = {}


def _rateios_concurso(cfg: dict, numero: int) -> Dict[Any, float]:
    if cfg.get("key") == "diasorte":
        out: Dict[Any, float] = dict(_FIXOS_DIASORTE)
        try:
            from models.caixa_excel_premiacao import CaixaExcelPremiacaoDiaDeSorte
            row = CaixaExcelPremiacaoDiaDeSorte.query.filter_by(concurso=int(numero)).first()
        except Exception:
            return out
        if not row:
            return out
        out[7] = float(row.rateio_7 or 0)
        out[6] = float(row.rateio_6 or 0)
        return out
    chave = (cfg.get("key") or "", int(numero))
    if chave in _RATEIO_CACHE:
        return dict(_RATEIO_CACHE[chave])
    faixas = _faixas_api(cfg, numero) or _faixas_complemento(numero)
    indexed = _indexar_rateios(cfg.get("key") or "", faixas)
    _RATEIO_CACHE[chave] = indexed
    return dict(indexed)


def _faixas_complemento(numero: int) -> List[Dict[str, Any]]:
    try:
        from sqlalchemy import text
        row = db.session.execute(
            text("SELECT payload_json FROM caixa_excel_complemento WHERE concurso = :c"),
            {"c": int(numero)},
        ).fetchone()
    except Exception:
        return []
    if not row:
        return []
    try:
        payload = json.loads(row[0] or "{}")
    except (TypeError, json.JSONDecodeError):
        return []
    return list(payload.get("faixas") or [])


def _faixas_api(cfg: dict, numero: int) -> List[Dict[str, Any]]:
    slug = _API_SLUG.get(cfg.get("key") or "")
    if not slug:
        return []
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}/{int(numero)}"
    try:
        import requests
        resp = requests.get(
            url,
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
            timeout=12,
            verify=False,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []
    out = []
    for item in data.get("listaRateioPremio") or []:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("descricaoFaixa") or "").strip()
        if not nome:
            continue
        try:
            valor = float(item.get("valorPremio") or 0)
        except (TypeError, ValueError):
            valor = 0.0
        out.append({"nome": nome, "rateio": valor})
    return out


def _indexar_rateios(key: str, faixas: List[Dict[str, Any]]) -> Dict[Any, float]:
    out: Dict[Any, float] = {}
    if key == "duplasena" and faixas and not any(str(f.get("nome") or "").upper().startswith("S") for f in faixas):
        metade = max(1, len(faixas) // 2)
        for i, faixa in enumerate(faixas):
            lado = 1 if i < metade else 2
            m = re.search(r"(\d+)", str(faixa.get("nome") or ""))
            if not m:
                continue
            n = int(m.group(1))
            valor = float(faixa.get("rateio") or 0)
            rotulo = f"S{lado} {n} acertos"
            out[rotulo] = valor
            out[(lado, n)] = valor
        return out
    for faixa in faixas:
        nome = str(faixa.get("nome") or "").strip()
        if not nome:
            continue
        valor = float(faixa.get("rateio") or 0)
        out[nome] = valor
        if nome.lower().startswith("time"):
            out["Time"] = valor
        m = re.match(r"^(\d+)\s+acertos$", nome, re.I)
        if m and key != "duplasena":
            out[int(m.group(1))] = valor
        m2 = re.match(r"^S([12])\s+(\d+)\s+acertos$", nome, re.I)
        if m2:
            out[(int(m2.group(1)), int(m2.group(2)))] = valor
    return out


def _valor_unit(rateios: Optional[Dict[Any, float]], minimo, rotulo: Optional[str]) -> float:
    if not rateios:
        return 0.0
    if rotulo and rotulo in rateios:
        return float(rateios.get(rotulo) or 0)
    if minimo in rateios:
        return float(rateios.get(minimo) or 0)
    return 0.0


def _classificar_faixa(acertos: int, cfg: dict) -> Optional[str]:
    for min_ac, label in cfg["faixas"]:
        if acertos >= min_ac:
            return label
    return None


def _faixa_combo(acertos: int, mes_ok: bool, cfg: dict):
    """Melhor faixa de dezenas. No Dia de Sorte, 5 (R$ 25) e 4 (R$ 5) são fixos e não exigem o mês.
    6 e 7 saem do rateio e exigem o mês. O mês (R$ 2,50) soma em qualquer faixa."""
    faixas = cfg.get("faixas") or []
    if cfg.get("has_mes"):
        exige_mes = {6, 7}
        for minimo, label in faixas:
            if acertos >= minimo and (minimo not in exige_mes or mes_ok):
                return minimo, label
        if mes_ok:
            return 0, "Mês"
        return None, None
    if cfg.get("premio_zero") and acertos == 0:
        return 0, "0 acertos"
    vistos = set()
    for minimo, label in faixas:
        if minimo in vistos or minimo == 0:
            continue
        vistos.add(minimo)
        if acertos >= minimo:
            return minimo, label
    return None, None


def _norm_txt(valor) -> str:
    txt = str(valor or "").strip().lower()
    txt = re.sub(r"\s+", " ", txt)
    txt = txt.split("/")[0].strip()
    trocas = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
    return txt.translate(trocas)


def _time_confere(aposta, sorteio) -> bool:
    a = _norm_txt(aposta)
    s = _norm_txt(sorteio)
    if not a or not s:
        return False
    return a == s or a in s or s in a


def _faixa_maismilionaria(acertos: int, trevos: int) -> Optional[str]:
    if acertos == 6 and trevos >= 2:
        return "6 acertos + 2 trevos"
    if acertos == 6:
        return "6 acertos + 1 ou nenhum trevo"
    if acertos == 5 and trevos >= 2:
        return "5 acertos + 2 trevos"
    if acertos == 5:
        return "5 acertos + 1 ou nenhum trevo"
    if acertos == 4 and trevos >= 2:
        return "4 acertos + 2 trevos"
    if acertos == 4:
        return "4 acertos + 1 ou nenhum trevo"
    if acertos == 3 and trevos >= 2:
        return "3 acertos + 2 trevos"
    if acertos == 3 and trevos == 1:
        return "3 acertos + 1 trevo"
    if acertos == 2 and trevos >= 2:
        return "2 acertos + 2 trevos"
    if acertos == 2 and trevos == 1:
        return "2 acertos + 1 trevo"
    return None


def _pacote_aposta(valor_aposta, acertos, acertos_volante, hits, detalhes, cfg, extra=None):
    valor_ganho = round(sum(float(d.get("valor") or 0) for d in detalhes), 2)
    faixas_unicas = [d["descricao"] for d in detalhes if d.get("descricao")]
    extra = extra or {}
    resultado = {
        "acertos": acertos,
        "acertos_volante": acertos_volante,
        "numeros_acertados": hits,
        "faixa": " + ".join(faixas_unicas) if faixas_unicas else None,
        "faixas_atingidas": faixas_unicas,
        "detalhes_premios": detalhes,
        "valor_premio": valor_ganho,
        "premiado": bool(faixas_unicas),
        "destaque": bool(faixas_unicas),
        "premio_maximo": bool(extra.get("premio_maximo")),
    }
    resultado.update({k: v for k, v in extra.items() if k != "premio_maximo"})
    return {
        "valor_aposta": valor_aposta,
        "valor_premio": valor_ganho,
        "valor_ganho": valor_ganho,
        "resultado": resultado,
    }


def _analisar_aposta(
    numeros: List[int],
    sorteadas,
    cfg: dict,
    mes_aposta=None,
    mes_sorteio=None,
    rateios: Optional[Dict[Any, float]] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    combo = cfg["combo_size"]
    extras = extras or {}

    # Super Sete: acertos coluna a coluna (repetições permitidas).
    if _scoring_positional(cfg):
        seq = normalizar_aposta_ss(numeros, colunas=combo)
        sort_list = list(sorteadas)
        ac = contar_acertos_posicional(seq, sort_list, colunas=combo)
        hits = digitos_acertados(seq, sort_list, colunas=combo)
        minimo, faixa = _faixa_combo(ac, True, cfg)
        unit = _valor_unit(rateios, minimo, faixa) if faixa else 0.0
        detalhes = []
        if faixa:
            detalhes.append({"descricao": faixa, "quantidade": 1, "valor": round(unit, 2)})
        topo = cfg["faixas"][0][0] if cfg.get("faixas") else combo
        return _pacote_aposta(
            _preco_volante(cfg, combo), ac, ac, hits, detalhes, cfg,
            {"premio_maximo": bool(faixa) and minimo == topo},
        )

    sorteadas_set: Set[int] = set(sorteadas) if not isinstance(sorteadas, set) else sorteadas
    unicos = sorted(set(numeros))
    qtd = len(unicos)
    valor_aposta = _preco_volante(cfg, qtd)
    volante_set = set(unicos)
    hits_volante = sorted(volante_set & sorteadas_set)
    acertos_volante = len(hits_volante)
    mes_ok = True
    if cfg.get("has_mes"):
        n_ap = _mes_num(mes_aposta)
        n_so = _mes_num(mes_sorteio)
        mes_ok = n_ap is not None and n_so is not None and n_ap == n_so

    if cfg.get("key") == "lotomania":
        minimo, faixa = _faixa_combo(acertos_volante, True, cfg)
        detalhes = []
        if faixa:
            unit = _valor_unit(rateios, minimo, faixa)
            detalhes.append({"descricao": faixa, "quantidade": 1, "valor": round(unit, 2)})
        topo = cfg["faixas"][0][0] if cfg.get("faixas") else combo
        return _pacote_aposta(
            valor_aposta, acertos_volante, acertos_volante, hits_volante, detalhes, cfg,
            {"premio_maximo": bool(faixa) and minimo == topo},
        )

    if cfg.get("dois_sorteios"):
        return _analisar_duplasena(unicos, sorteadas_set, cfg, valor_aposta, hits_volante, acertos_volante, rateios, extras)

    if cfg.get("has_trevos"):
        return _analisar_maismilionaria(unicos, sorteadas_set, cfg, valor_aposta, hits_volante, acertos_volante, rateios, extras)

    if qtd == combo:
        combos: List[Tuple[int, ...]] = [tuple(unicos)]
    elif qtd > combo:
        combos = list(combinations(unicos, combo))
    else:
        combos = []

    max_acertos = 0
    contagem: Dict[str, Dict[str, Any]] = {}
    for c in combos:
        ac = len(set(c) & sorteadas_set)
        max_acertos = max(max_acertos, ac)
        minimo, faixa = _faixa_combo(ac, mes_ok, cfg)
        if not faixa:
            continue
        item = contagem.setdefault(faixa, {"minimo": minimo, "quantidade": 0})
        item["quantidade"] += 1

    detalhes = []
    valor_ganho = 0.0
    for faixa, item in contagem.items():
        unit = _valor_unit(rateios, item["minimo"], faixa)
        valor = round(unit * item["quantidade"], 2)
        valor_ganho += valor
        detalhes.append({
            "descricao": faixa,
            "quantidade": item["quantidade"],
            "valor": valor,
        })
    detalhes.sort(key=lambda d: -d["quantidade"])
    if cfg.get("has_mes") and mes_ok and not any(d["descricao"] == "Mês" for d in detalhes):
        unit_mes = _valor_unit(rateios, 0, "Mês") or float(_FIXOS_DIASORTE[0])
        if unit_mes:
            detalhes.append({"descricao": "Mês", "quantidade": 1, "valor": round(unit_mes, 2)})
    if cfg.get("has_time"):
        time_ok = _time_confere(extras.get("time_aposta"), extras.get("time_sorteio"))
        if time_ok and not any(str(d["descricao"]).lower().startswith("time") for d in detalhes):
            unit_time = _valor_unit(rateios, "Time", "Time")
            detalhes.append({"descricao": "Time do Coração", "quantidade": 1, "valor": round(unit_time, 2)})
    topo = cfg["faixas"][0][0] if cfg.get("faixas") else combo
    premio_maximo = any(item.get("minimo") == topo for item in contagem.values())
    extra = {"premio_maximo": premio_maximo}
    if cfg.get("has_mes"):
        extra["mes_ok"] = mes_ok
    if cfg.get("has_time"):
        extra["time_ok"] = _time_confere(extras.get("time_aposta"), extras.get("time_sorteio"))
    return _pacote_aposta(
        valor_aposta, max_acertos, acertos_volante, hits_volante, detalhes, cfg, extra,
    )


def _contar_combos(unicos: List[int], sorteadas_set: Set[int], combo: int):
    qtd = len(unicos)
    if qtd == combo:
        combos = [tuple(unicos)]
    elif qtd > combo:
        combos = list(combinations(unicos, combo))
    else:
        combos = []
    max_acertos = 0
    por_ac: Dict[int, int] = {}
    for c in combos:
        ac = len(set(c) & sorteadas_set)
        max_acertos = max(max_acertos, ac)
        por_ac[ac] = por_ac.get(ac, 0) + 1
    return max_acertos, por_ac


def _analisar_duplasena(unicos, sorteadas_set, cfg, valor_aposta, hits_volante, acertos_volante, rateios, extras):
    combo = cfg["combo_size"]
    lados = [(1, sorteadas_set, "S1")]
    s2 = extras.get("sorteio2") or []
    if s2:
        lados.append((2, set(s2), "S2"))
    detalhes = []
    max_acertos = 0
    premio_maximo = False
    for lado, alvo, prefixo in lados:
        melhor, por_ac = _contar_combos(unicos, alvo, combo)
        max_acertos = max(max_acertos, melhor)
        for ac, qtd in sorted(por_ac.items(), reverse=True):
            minimo, _faixa = _faixa_combo(ac, True, cfg)
            if not _faixa:
                continue
            rotulo = f"{prefixo} {minimo} acertos"
            unit = _valor_unit(rateios, (lado, minimo), rotulo)
            detalhes.append({"descricao": rotulo, "quantidade": qtd, "valor": round(unit * qtd, 2)})
            if minimo == (cfg["faixas"][0][0] if cfg.get("faixas") else combo):
                premio_maximo = True
    hits2 = sorted(set(unicos) & set(s2)) if s2 else []
    hits = sorted(set(hits_volante) | set(hits2))
    return _pacote_aposta(
        valor_aposta, max_acertos, max(acertos_volante, len(hits2)), hits, detalhes, cfg,
        {"premio_maximo": premio_maximo, "numeros_acertados_s2": hits2},
    )


def _analisar_maismilionaria(unicos, sorteadas_set, cfg, valor_aposta, hits_volante, acertos_volante, rateios, extras):
    combo = cfg["combo_size"]
    trevos_sorte = {int(n) for n in (extras.get("trevos_sorteio") or [])}
    trevos_ap = {int(n) for n in (extras.get("trevos_aposta") or []) if str(n).strip()}
    n_trevos = len(trevos_ap & trevos_sorte)
    _melhor, por_ac = _contar_combos(unicos, sorteadas_set, combo)
    contagem: Dict[str, int] = {}
    for ac, qtd in por_ac.items():
        rotulo = _faixa_maismilionaria(ac, n_trevos)
        if not rotulo:
            continue
        contagem[rotulo] = contagem.get(rotulo, 0) + qtd
    detalhes = []
    for rotulo, qtd in contagem.items():
        unit = _valor_unit(rateios, rotulo, rotulo)
        detalhes.append({"descricao": rotulo, "quantidade": qtd, "valor": round(unit * qtd, 2)})
    detalhes.sort(key=lambda d: -d["quantidade"])
    return _pacote_aposta(
        valor_aposta, acertos_volante, acertos_volante, hits_volante, detalhes, cfg,
        {
            "premio_maximo": "6 acertos + 2 trevos" in contagem,
            "trevos_acertados": n_trevos,
        },
    )


class ConferenciaApostasFolderService:
    def __init__(self, modality_key: str):
        self.cfg = get_conf(modality_key)
        self.Sorteo = _load_sorteio_model(self.cfg)
        self.min_d = self.cfg["pick_min"]
        self.max_d = self.cfg["pick_max"]
        self.dmin = self.cfg["dezena_min"]
        self.dmax = self.cfg["dezena_max"]
        self.combo = self.cfg["combo_size"]

    def historico_aposta_volante(self, numeros: List[int], min_acertos: int = None) -> Dict[str, Any]:
        if min_acertos is None:
            min_acertos = self.cfg["faixas"][-1][0] if self.cfg["faixas"] else self.combo
        if isinstance(numeros, str):
            numeros = [int(x) for x in re.findall(r"\d+", numeros)]

        if _scoring_positional(self.cfg):
            ok, msg, seq = validar_aposta_ss(numeros, colunas=self.combo)
            if not ok:
                return {"sucesso": False, "mensagem": msg}
            rows = db.session.query(self.Sorteo).order_by(desc(self.Sorteo.concurso)).all()
            historico: List[Dict[str, Any]] = []
            for s in rows:
                sorteadas = list(_sorteadas(s, self.cfg))
                ac = contar_acertos_posicional(seq, sorteadas, colunas=self.combo)
                if ac >= min_acertos:
                    faixa = _classificar_faixa(ac, self.cfg) or f"{ac}/{self.combo}"
                    historico.append({
                        "concurso": s.concurso,
                        "data": s.data,
                        "acertos": ac,
                        "faixa": faixa,
                        "sorteados": sorteadas,
                    })
            return {
                "sucesso": True,
                "numeros_apostados": seq,
                "min_acertos": min_acertos,
                "total": len(historico),
                "historico": historico,
            }

        unicos = sorted(set(int(n) for n in numeros))
        if len(unicos) < self.min_d:
            return {
                "sucesso": False,
                "mensagem": f"Informe pelo menos {self.min_d} números distintos.",
            }
        aposta_set = set(unicos)
        rows = db.session.query(self.Sorteo).order_by(desc(self.Sorteo.concurso)).all()
        historico = []
        for s in rows:
            sorteadas = set(_sorteadas(s, self.cfg))
            ac = len(aposta_set & sorteadas)
            if ac >= min_acertos:
                faixa = _classificar_faixa(ac, self.cfg) or f"{ac}/{self.combo}"
                historico.append({
                    "concurso": s.concurso,
                    "data": s.data,
                    "acertos": ac,
                    "faixa": faixa,
                    "sorteados": sorted(sorteadas),
                })
        return {
            "sucesso": True,
            "numeros_apostados": unicos,
            "min_acertos": min_acertos,
            "total": len(historico),
            "historico": historico,
        }

    def conferir_txt_historico(self, texto: str, min_acertos: int = 11) -> Dict[str, Any]:
        """Importa TXT (1 linha = 1 aposta) e confere cada jogo contra todos os sorteios do banco."""
        from .conversor_service import ConversorApostasService

        texto = (texto or "").strip()
        if not texto:
            return {"sucesso": False, "mensagem": "Arquivo ou texto vazio."}

        conv = ConversorApostasService(self.cfg["key"])
        parsed = conv.texto_para_json(texto, concurso=0)
        validacao = conv.validar_apostas(parsed)
        if not validacao.get("valido"):
            return {
                "sucesso": False,
                "mensagem": "TXT inválido.",
                "erros": validacao.get("erros") or [],
                "avisos": validacao.get("avisos") or [],
            }

        apostas_in = parsed.get("apostas") or []
        if not apostas_in:
            return {"sucesso": False, "mensagem": "Nenhuma aposta encontrada no TXT."}

        if min_acertos is None:
            min_acertos = self.cfg["faixas"][-1][0] if self.cfg["faixas"] else self.combo
        min_acertos = int(min_acertos)

        sorteios = db.session.query(self.Sorteo).order_by(desc(self.Sorteo.concurso)).all()
        if not sorteios:
            return {"sucesso": False, "mensagem": "Nenhum sorteio no banco. Sincronize na página inicial."}

        positional = _scoring_positional(self.cfg)
        if positional:
            cache_sorteios = [
                (s.concurso, s.data, list(_sorteadas(s, self.cfg)))
                for s in sorteios
            ]
        else:
            cache_sorteios = [
                (s.concurso, s.data, set(_sorteadas(s, self.cfg)))
                for s in sorteios
            ]

        faixas_ordem = [f[0] for f in self.cfg.get("faixas") or []]
        apostas_out: List[Dict[str, Any]] = []

        for ap in apostas_in:
            raw = ap.get("numeros") or []
            if positional:
                nums = normalizar_aposta_ss(raw, colunas=self.combo)
                if len(nums) != self.combo:
                    continue
            else:
                nums = sorted(set(int(n) for n in raw))
            aposta_set = set(nums)
            resumo = {str(f): 0 for f in faixas_ordem}
            detalhes: List[Dict[str, Any]] = []

            for concurso, data, sorteadas in cache_sorteios:
                if positional:
                    ac = contar_acertos_posicional(nums, sorteadas, colunas=self.combo)
                else:
                    ac = len(aposta_set & sorteadas)
                if ac < min_acertos:
                    continue
                faixa = _classificar_faixa(ac, self.cfg) or f"{ac}/{self.combo}"
                if str(ac) in resumo:
                    resumo[str(ac)] += 1
                detalhes.append({
                    "concurso": concurso,
                    "data": data,
                    "acertos": ac,
                    "faixa": faixa,
                })

            detalhes.sort(key=lambda x: (-x["acertos"], -x["concurso"]))
            melhor = detalhes[0] if detalhes else None
            apostas_out.append({
                "numero": ap.get("numero"),
                "dezenas": nums,
                "resumo": resumo,
                "total_premios": len(detalhes),
                "melhor": melhor,
                "detalhes": detalhes[:40],
            })

        apostas_out.sort(
            key=lambda x: (
                -(x["melhor"]["acertos"] if x["melhor"] else 0),
                -x["total_premios"],
            )
        )

        return {
            "sucesso": True,
            "total_apostas": len(apostas_out),
            "total_sorteios": len(cache_sorteios),
            "min_acertos": min_acertos,
            "apostas": apostas_out,
        }

    def pasta_base(self) -> str:
        return pasta_modalidade(self.cfg)

    def _numeros_pastas(self) -> List[int]:
        base = self.pasta_base()
        if not os.path.isdir(base):
            return []
        numeros = []
        for nome in os.listdir(base):
            pasta = os.path.join(base, nome)
            if not os.path.isdir(pasta):
                continue
            try:
                numeros.append(int(nome))
            except ValueError:
                continue
        numeros.sort(reverse=True)
        return numeros

    def ultimo_concurso_apurado(self, numeros: Optional[List[int]] = None) -> Optional[int]:
        """Maior concurso que já tem pasta e resultado oficial no banco."""
        if numeros is None:
            numeros = self._numeros_pastas()
        if not numeros:
            return None
        sorteio = (
            self.Sorteo.query.filter(self.Sorteo.concurso.in_(numeros))
            .order_by(self.Sorteo.concurso.desc())
            .first()
        )
        return int(sorteio.concurso) if sorteio else None

    def listar_indice_concursos(self) -> Dict[str, Any]:
        """Lista concursos sem ler apostas.json — usado pelo seletor de alcance."""
        numeros = self._numeros_pastas()
        sorteios = {}
        if numeros:
            for sorteio in self.Sorteo.query.filter(self.Sorteo.concurso.in_(numeros)).all():
                sorteios[int(sorteio.concurso)] = sorteio
        base = self.pasta_base()
        concursos = []
        for numero in numeros:
            pasta = os.path.join(base, str(numero))
            sorteio = sorteios.get(numero)
            concursos.append({
                "numero_concurso": numero,
                "tem_json": _arquivo_json(pasta) is not None,
                "resultado_disponivel": sorteio is not None,
                "data_sorteio": sorteio.data if sorteio else None,
            })
        apurados = [n for n in numeros if n in sorteios]
        return {
            "concursos": concursos,
            "total": len(concursos),
            "ultimo_apurado": max(apurados) if apurados else None,
        }

    def listar_concursos_disponiveis(
        self,
        escopo: str = "todos",
        concurso: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Lista pastas de conferencia_apostas.

        escopo=todos lê cada apostas.json (comportamento anterior, sem parâmetro).
        escopo=ultimo lê só o último concurso que já tem resultado oficial.
        escopo=especifico lê só o concurso informado.
        """
        base = self.pasta_base()
        if not os.path.isdir(base):
            return []
        escopo_norm = (escopo or "todos").strip().lower()
        if escopo_norm not in ("todos", "especifico", "ultimo"):
            escopo_norm = "todos"

        numeros = self._numeros_pastas()
        if escopo_norm == "especifico":
            try:
                alvo = int(concurso)
            except (TypeError, ValueError):
                return []
            numeros_alvo = [alvo] if alvo in numeros else []
        elif escopo_norm == "ultimo":
            alvo = self.ultimo_concurso_apurado(numeros)
            numeros_alvo = [alvo] if alvo else []
        else:
            numeros_alvo = list(numeros)

        if not numeros_alvo:
            return []

        sorteios = {
            int(s.concurso): s
            for s in self.Sorteo.query.filter(self.Sorteo.concurso.in_(numeros_alvo)).all()
        }
        slug = self.cfg.get("pasta_apostas") or self.cfg["key"]
        concursos = []
        for numero in numeros_alvo:
            pasta = os.path.join(base, str(numero))
            if not os.path.isdir(pasta):
                continue
            arquivo_json = _arquivo_json(pasta)
            tem_json = arquivo_json is not None
            total_apostas = 0
            total_screenshots = _contar_screenshots(pasta)
            if tem_json:
                try:
                    with open(arquivo_json, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    if isinstance(dados, dict):
                        total_apostas = len(dados.get("apostas", []))
                    elif isinstance(dados, list):
                        total_apostas = len(dados)
                except Exception:
                    total_apostas = 0
            sorteio = sorteios.get(numero)
            dezenas_banco = _sorteadas(sorteio, self.cfg) if sorteio else None
            concursos.append({
                "numero_concurso": numero,
                "tem_json": tem_json,
                "arquivo": os.path.basename(arquivo_json) if arquivo_json else None,
                "total_apostas": total_apostas,
                "total_screenshots": total_screenshots,
                "resultado_disponivel": sorteio is not None,
                "data_sorteio": sorteio.data if sorteio else None,
                "dezenas_banco": dezenas_banco,
                "pasta": f"{slug}/{numero}",
            })
        concursos.sort(key=lambda x: x["numero_concurso"], reverse=True)
        return concursos

    def processar_concurso(self, numero_concurso: int) -> Dict[str, Any]:
        slug = self.cfg.get("pasta_apostas") or self.cfg["key"]
        pasta = os.path.join(self.pasta_base(), str(numero_concurso))
        if not os.path.isdir(pasta):
            return {
                "sucesso": False,
                "mensagem": f"Pasta conferencia_apostas/{slug}/{numero_concurso} não encontrada.",
            }
        sorteio = self.Sorteo.query.filter_by(concurso=numero_concurso).first()
        if not sorteio:
            return {
                "sucesso": False,
                "mensagem": (
                    f"Concurso {numero_concurso} não está no banco. "
                    "Sincronize os sorteios antes de conferir."
                ),
            }
        arquivo_json = _arquivo_json(pasta)
        if not arquivo_json:
            return {
                "sucesso": False,
                "mensagem": f"Arquivo apostas.json não encontrado em conferencia_apostas/{slug}/{numero_concurso}/",
            }
        try:
            with open(arquivo_json, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except json.JSONDecodeError as e:
            return {"sucesso": False, "mensagem": str(e)}

        if "apostas" not in dados:
            return {"sucesso": False, "mensagem": 'JSON deve conter o campo "apostas".'}

        sorteadas_list = list(_sorteadas(sorteio, self.cfg))
        sorteadas = sorteadas_list if _scoring_positional(self.cfg) else set(sorteadas_list)
        mes_sorteio = None
        if self.cfg.get("has_mes"):
            if hasattr(sorteio, "mes_abrev"):
                mes_sorteio = sorteio.mes_abrev()
            else:
                mes_sorteio = getattr(sorteio, "mes_nome", None) or getattr(sorteio, "mes_num", None)
        rateios = _rateios_concurso(self.cfg, numero_concurso)
        extras_base: Dict[str, Any] = {}
        if self.cfg.get("dois_sorteios") and hasattr(sorteio, "sorteio2_lista"):
            extras_base["sorteio2"] = [int(n) for n in sorteio.sorteio2_lista()]
        if self.cfg.get("has_trevos") and hasattr(sorteio, "trevos_lista"):
            extras_base["trevos_sorteio"] = [int(n) for n in sorteio.trevos_lista()]
        if self.cfg.get("has_time"):
            extras_base["time_sorteio"] = getattr(sorteio, "time_nome", None) or getattr(sorteio, "time_num", None)
        apostas_brutas = dados.get("apostas") or []
        # Acima disso a resposta com cada aposta estoura o proxy (HTML 500) e o navegador.
        limite_lista = 500
        grande = len(apostas_brutas) > limite_lista
        apostas_out: List[Dict[str, Any]] = []
        vencedoras: List[Tuple[Any, ...]] = []
        melhores_abs: List[Tuple[Any, ...]] = []
        reserva_abs: List[Tuple[Any, ...]] = []
        erros: List[str] = []
        erros_ocultos = 0
        total_investido = 0.0
        total_ganho = 0.0
        total_validas = 0
        premiadas_total = 0
        distribuicao: Dict[str, Dict[str, Any]] = {}
        freq: Counter = Counter()
        meses_cnt: Counter = Counter()
        dist_ac: Counter = Counter()
        abs_hist: Counter = Counter()
        soma_acertos = 0
        acertou_mes = False
        cobertura: Set[int] = set()
        melhor: Optional[Tuple[int, int, List[int], List[int]]] = None
        abs_stats = {
            nome: {"apostas": 0, "tiers": {}, "mes": 0, "time": 0}
            for nome in ("verde", "amarelo", "neutro")
        }
        fmt = (lambda n: str(n)) if self.cfg["key"] == "supersete" else (lambda n: f"{n:02d}")
        posicional = _scoring_positional(self.cfg)
        sorteados_abs = list(sorteadas_list) if posicional else sorted(int(n) for n in sorteadas_list)

        def _anotar_erro(texto: str) -> None:
            nonlocal erros_ocultos
            if len(erros) < 40:
                erros.append(texto)
            else:
                erros_ocultos += 1

        def _montar_item(numeros_ok, analise_ok, numero_aposta) -> Dict[str, Any]:
            resultado_ap = analise_ok["resultado"]
            return {
                "numero_aposta": numero_aposta,
                "numeros_apostados": numeros_ok,
                "numeros": [fmt(n) for n in numeros_ok],
                "valor_aposta": analise_ok["valor_aposta"],
                "valor_ganho": analise_ok["valor_ganho"],
                "mes": aposta.get("mes"),
                "trevos": [int(n) for n in (aposta.get("trevos") or [])],
                "time": aposta.get("time") or aposta.get("time_coracao"),
                "acertos": resultado_ap["acertos"],
                "dezenas_acertadas": [fmt(n) for n in resultado_ap["numeros_acertados"]],
                "premiacao": resultado_ap["faixa"] or f"{resultado_ap['acertos']}/{self.combo}",
                "resultado": resultado_ap,
            }

        def _soma_abs(numeros_ok) -> Optional[int]:
            seq = list(numeros_ok) if posicional else sorted(int(n) for n in numeros_ok)
            n = min(self.combo, len(seq), len(sorteados_abs))
            if n <= 0:
                return None
            return sum(abs(int(seq[i]) - int(sorteados_abs[i])) for i in range(n))

        for idx, aposta in enumerate(apostas_brutas, 1):
            try:
                numeros = aposta.get("numeros", [])
                if isinstance(numeros, str):
                    numeros = [int(x) for x in re.findall(r"\d+", numeros)]
                else:
                    numeros = [int(n) for n in numeros]
                if posicional:
                    ok, msg, numeros = validar_aposta_ss(numeros, colunas=self.combo)
                    if not ok:
                        _anotar_erro(f"Aposta {idx}: {msg}")
                        continue
                elif len(numeros) < self.min_d or len(numeros) > self.max_d:
                    _anotar_erro(
                        f"Aposta {idx}: deve ter entre {self.min_d} e {self.max_d} números."
                    )
                    continue
                invalidas = [n for n in numeros if n < self.dmin or n > self.dmax]
                if invalidas:
                    _anotar_erro(f"Aposta {idx}: número(s) fora do volante: {invalidas}")
                    continue
                extras = dict(extras_base)
                extras["trevos_aposta"] = aposta.get("trevos") or []
                extras["time_aposta"] = aposta.get("time") or aposta.get("time_coracao")
                analise = _analisar_aposta(
                    numeros,
                    sorteadas,
                    self.cfg,
                    mes_aposta=aposta.get("mes"),
                    mes_sorteio=mes_sorteio,
                    rateios=rateios,
                    extras=extras,
                )
                resultado_ap = analise["resultado"]
                total_investido += analise["valor_aposta"]
                total_ganho += analise["valor_ganho"]
                total_validas += 1
                if resultado_ap.get("premiado"):
                    premiadas_total += 1
                for det in resultado_ap.get("detalhes_premios") or []:
                    faixa = det.get("descricao") or "Prêmio"
                    slot = distribuicao.setdefault(faixa, {"quantidade": 0, "total_ganho": 0.0})
                    slot["quantidade"] += int(det.get("quantidade") or 0)
                    slot["total_ganho"] = round(slot["total_ganho"] + float(det.get("valor") or 0), 2)
                if not grande:
                    apostas_out.append(_montar_item(numeros, analise, aposta.get("numero", idx)))
                    continue

                acertos = int(resultado_ap.get("acertos") or 0)
                unicos = sorted(set(int(n) for n in numeros))
                for n in unicos:
                    freq[n] += 1
                    cobertura.add(n)
                mes_txt = aposta.get("mes")
                if mes_txt not in (None, ""):
                    meses_cnt[str(mes_txt)] += 1
                dist_ac[acertos] += 1
                soma_acertos += acertos
                if resultado_ap.get("mes_ok"):
                    acertou_mes = True
                hits = [int(n) for n in (resultado_ap.get("numeros_acertados") or [])]
                numero_aposta = int(aposta.get("numero", idx) or idx)
                if melhor is None or acertos > melhor[0] or (acertos == melhor[0] and numero_aposta < melhor[1]):
                    melhor = (acertos, numero_aposta, unicos, hits)
                soma_abs = _soma_abs(numeros)
                if soma_abs is not None:
                    abs_hist[soma_abs] += 1
                    nome_bucket = "verde" if soma_abs <= 7 else "amarelo" if soma_abs <= 14 else "neutro"
                    bucket = abs_stats[nome_bucket]
                    bucket["apostas"] += 1
                    vistas = set()
                    for det in resultado_ap.get("detalhes_premios") or []:
                        desc = str(det.get("descricao") or "").strip()
                        if desc and desc not in vistas:
                            vistas.add(desc)
                            bucket["tiers"][desc] = int(bucket["tiers"].get(desc) or 0) + 1
                    if resultado_ap.get("mes_ok"):
                        bucket["mes"] += 1
                    if resultado_ap.get("time_ok"):
                        bucket["time"] += 1
                ganho_ap = float(analise["valor_ganho"] or 0)
                guarda_premio = bool(resultado_ap.get("premiado")) or ganho_ap > 0
                guarda_verde = soma_abs is not None and soma_abs <= 7
                chave_reserva = (-int(soma_abs or 0), -numero_aposta)
                guarda_reserva = (
                    soma_abs is not None
                    and not guarda_verde
                    and (
                        len(reserva_abs) < 200
                        or chave_reserva > (reserva_abs[0][0], reserva_abs[0][1])
                    )
                )
                if guarda_premio or guarda_verde or guarda_reserva:
                    item = _montar_item(numeros, analise, numero_aposta)
                    if guarda_premio:
                        vencedoras.append((acertos, ganho_ap, numero_aposta, item))
                    if guarda_verde:
                        melhores_abs.append((int(soma_abs), numero_aposta, item))
                    elif guarda_reserva:
                        pacote = (chave_reserva[0], chave_reserva[1], item)
                        if len(reserva_abs) < 200:
                            heapq.heappush(reserva_abs, pacote)
                        else:
                            heapq.heapreplace(reserva_abs, pacote)
            except (TypeError, ValueError) as exc:
                _anotar_erro(f"Aposta {idx}: {exc}")

        if erros_ocultos:
            erros.append(f"... e mais {erros_ocultos} aposta(s) ignorada(s).")

        variancia_amostra: List[Dict[str, Any]] = []
        premio_cortado = False
        if grande:
            if len(vencedoras) > 8000:
                vencedoras = sorted(vencedoras, key=lambda t: (t[0], t[1], t[2]), reverse=True)[:8000]
                premio_cortado = True
            else:
                vencedoras.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
            apostas_out = [t[3] for t in vencedoras]
            if melhores_abs:
                melhores_abs.sort(key=lambda t: (t[0], t[1]))
                if len(melhores_abs) > 1500:
                    melhores_abs = melhores_abs[:1500]
                variancia_amostra = [t[2] for t in melhores_abs]
            else:
                reserva_abs.sort(key=lambda t: (-t[0], -t[1]))
                variancia_amostra = [t[2] for t in reserva_abs]

        dezenas_display = (
            sorteadas_list
            if posicional
            else sorted(sorteadas)
        )
        fmt_dez = (lambda n: str(n)) if self.cfg["key"] == "supersete" else (lambda n: f"{int(n):02d}")
        ordem_sorteio = _ordem_sorteio(sorteio, self.cfg)
        resposta: Dict[str, Any] = {
            "sucesso": True,
            "concurso": numero_concurso,
            "dezenas_sorteadas": [fmt_dez(n) for n in dezenas_display],
            "dezenas_ordem_sorteio": [fmt_dez(n) for n in ordem_sorteio],
            "data_sorteio": sorteio.data,
            "modalidade": self.cfg["nome"],
            "mes_sorteado": mes_sorteio,
            "trevos_sorteados": [f"{int(n):02d}" for n in extras_base.get("trevos_sorteio") or []],
            "time_sorteado": extras_base.get("time_sorteio"),
            "dezenas_sorteio2": [fmt_dez(n) for n in (extras_base.get("sorteio2") or [])],
            "dezenas_oficiais": self.combo,
            "resumo": {
                "total_apostas_validas": total_validas,
                "total_apostas": total_validas,
                "total_investido": round(total_investido, 2),
                "total_ganho": round(total_ganho, 2),
                "lucro": round(total_ganho - total_investido, 2),
                "roi": round((total_ganho - total_investido) / total_investido * 100, 2) if total_investido else 0.0,
                "distribuicao_faixas": distribuicao,
                "premiadas": premiadas_total,
            },
            "erros": erros,
            "apostas": apostas_out,
        }
        if grande:
            melhor_payload = None
            if melhor is not None:
                melhor_payload = {
                    "numero": melhor[1],
                    "numeros": melhor[2],
                    "acertos": melhor[0],
                    "hits": melhor[3],
                }
            resposta.update({
                "lista_parcial": True,
                "aviso_lista": (
                    f"Conferidas {total_validas} apostas. "
                    f"A lista mostra as {len(apostas_out)} premiadas"
                    f"{' de maior prêmio' if premio_cortado else ''} "
                    f"(5 acertos R$ 25, 4 acertos R$ 5 e mês R$ 2,50). "
                    f"A variância lista as {len(variancia_amostra)} melhores, as de menor ABS. "
                    "Investido, ganho e faixas usam o arquivo inteiro."
                ),
                "cobertura_dezenas": sorted(cobertura),
                "apostas_variancia": variancia_amostra,
                "abs_contagem": {str(k): int(v) for k, v in abs_hist.items()},
                "estatisticas": {
                    "total": total_validas,
                    "freq": {str(k): int(v) for k, v in freq.items()},
                    "meses": {str(k): int(v) for k, v in meses_cnt.items()},
                    "dist_acertos": {str(k): int(v) for k, v in dist_ac.items()},
                    "soma_acertos": soma_acertos,
                    "acertou_mes": acertou_mes,
                    "melhor": melhor_payload,
                    "abs": abs_stats,
                },
            })
        return resposta

    def _arquivos_retroativos(self) -> List[Tuple[str, int, str]]:
        """(origem, concurso_da_pasta, caminho). Origem é a pasta, não o campo do JSON."""
        base = self.pasta_base()
        if not os.path.isdir(base):
            return []
        achados: List[Tuple[str, int, str]] = []
        for nome in os.listdir(base):
            pasta = os.path.join(base, nome)
            if not os.path.isdir(pasta):
                continue
            try:
                numero = int(nome)
            except ValueError:
                continue
            raiz = _arquivo_json(pasta)
            if raiz:
                achados.append((str(numero), numero, raiz))
            try:
                filhos = os.listdir(pasta)
            except OSError:
                continue
            for filho in filhos:
                sub = os.path.join(pasta, filho)
                if not os.path.isdir(sub):
                    continue
                try:
                    int(filho)
                except ValueError:
                    continue
                arq = _arquivo_json(sub)
                if arq:
                    achados.append((f"{numero}/{filho}", numero, arq))
        achados.sort(key=lambda item: (-item[1], item[0]))
        return achados

    def _cache_sorteios_retro(self) -> List[Dict[str, Any]]:
        rows = db.session.query(self.Sorteo).order_by(self.Sorteo.concurso).all()
        cache: List[Dict[str, Any]] = []
        for sorteio in rows:
            dezenas = [int(n) for n in _sorteadas(sorteio, self.cfg)]
            item: Dict[str, Any] = {
                "concurso": int(sorteio.concurso),
                "dezenas": dezenas,
                "conjunto": set(dezenas),
                "data": getattr(sorteio, "data", None),
            }
            if self.cfg.get("dois_sorteios") and hasattr(sorteio, "sorteio2_lista"):
                s2 = [int(n) for n in sorteio.sorteio2_lista()]
                item["dezenas2"] = s2
                item["s2"] = set(s2)
            if self.cfg.get("has_trevos") and hasattr(sorteio, "trevos_lista"):
                item["trevos"] = [int(n) for n in sorteio.trevos_lista()]
            if self.cfg.get("has_mes"):
                if hasattr(sorteio, "mes_abrev"):
                    item["mes"] = sorteio.mes_abrev()
                else:
                    item["mes"] = getattr(sorteio, "mes_nome", None) or getattr(sorteio, "mes_num", None)
                item["mes_num"] = _mes_num(item.get("mes"))
            if self.cfg.get("has_time"):
                item["time"] = getattr(sorteio, "time_nome", None) or getattr(sorteio, "time_num", None)
            cache.append(item)
        return cache

    def _preparar_retro(self, numeros: List[Any]) -> Optional[Tuple]:
        if _scoring_positional(self.cfg):
            ok, _msg, seq = validar_aposta_ss(numeros, colunas=self.combo)
            if not ok:
                return None
            return ("pos", seq)
        unicos: List[int] = []
        vistos: Set[int] = set()
        for n in numeros:
            try:
                valor = int(n)
            except (TypeError, ValueError):
                return None
            if valor < self.dmin or valor > self.dmax:
                return None
            if valor in vistos:
                continue
            vistos.add(valor)
            unicos.append(valor)
        unicos.sort()
        if len(unicos) < self.min_d or len(unicos) > self.max_d:
            return None
        return ("set", unicos, set(unicos))

    def _acertos_retro(self, preparado: Tuple, draw: Dict[str, Any], com_hits: bool = False):
        if preparado[0] == "pos":
            seq = preparado[1]
            ac = contar_acertos_posicional(seq, draw["dezenas"], colunas=self.combo)
            hits = digitos_acertados(seq, draw["dezenas"], colunas=self.combo) if com_hits else []
            return ac, hits
        unicos, conjunto = preparado[1], preparado[2]
        alvo = draw["conjunto"]
        if self.cfg.get("dois_sorteios"):
            s2 = draw.get("s2") or set()
            if len(unicos) > self.combo:
                ac1, _ = _contar_combos(unicos, alvo, self.combo)
                ac2, _ = _contar_combos(unicos, s2, self.combo) if s2 else (0, {})
                ac = max(ac1, ac2)
            else:
                ac = max(len(conjunto & alvo), len(conjunto & s2))
            hits = sorted((conjunto & alvo) | (conjunto & s2)) if com_hits else []
            return ac, hits
        if len(unicos) > self.combo and self.cfg.get("key") != "lotomania" and not self.cfg.get("has_trevos"):
            ac, _ = _contar_combos(unicos, alvo, self.combo)
            hits = sorted(conjunto & alvo) if com_hits else []
            return ac, hits
        inter = conjunto & alvo
        return len(inter), (sorted(inter) if com_hits else [])

    def _ler_apostas_origem(self, caminho: str) -> List[Dict[str, Any]]:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, dict):
            apostas = dados.get("apostas") or []
        elif isinstance(dados, list):
            apostas = dados
        else:
            apostas = []
        return apostas if isinstance(apostas, list) else []

    def analise_retroativa(self) -> Dict[str, Any]:
        """Compara cada aposta salva só com concursos anteriores da mesma modalidade."""
        import time

        inicio = time.perf_counter()
        cache = self._cache_sorteios_retro()
        if not cache:
            return {"sucesso": False, "mensagem": "Nenhum sorteio no banco. Sincronize na página inicial."}
        arquivos = self._arquivos_retroativos()
        if not arquivos:
            return {"sucesso": False, "mensagem": "Nenhum apostas.json encontrado nas pastas desta modalidade."}

        ranking: List[Dict[str, Any]] = []
        grupos: Dict[str, Dict[str, Any]] = {}
        ignoradas = 0
        tem_mes = bool(self.cfg.get("has_mes"))
        for origem, concurso_origem, caminho in arquivos:
            try:
                apostas = self._ler_apostas_origem(caminho)
            except (OSError, json.JSONDecodeError):
                ignoradas += 1
                continue
            for idx, aposta in enumerate(apostas, 1):
                if not isinstance(aposta, dict):
                    ignoradas += 1
                    continue
                numeros = aposta.get("numeros", [])
                if isinstance(numeros, str):
                    numeros = [int(x) for x in re.findall(r"\d+", numeros)]
                preparado = self._preparar_retro(numeros)
                if preparado is None:
                    ignoradas += 1
                    continue
                freq = [0] * (self.combo + 1)
                soma = 0
                n = 0
                melhor = 0
                real = None
                meses = 0
                mes_aposta = _mes_num(aposta.get("mes")) if tem_mes else None
                for draw in cache:
                    concurso = draw["concurso"]
                    if concurso > concurso_origem:
                        break
                    ac, _hits = self._acertos_retro(preparado, draw, False)
                    if concurso == concurso_origem:
                        real = ac
                        continue
                    if ac >= len(freq):
                        ac = len(freq) - 1
                    freq[ac] += 1
                    soma += ac
                    n += 1
                    if ac > melhor:
                        melhor = ac
                    if mes_aposta is not None and draw.get("mes_num") == mes_aposta:
                        meses += 1
                numeros_out = preparado[1]
                item = {
                    "origem": origem,
                    "concurso_origem": concurso_origem,
                    "numero": aposta.get("numero", idx),
                    "numeros": numeros_out,
                    "mes": aposta.get("mes"),
                    "trevos": aposta.get("trevos") or [],
                    "time": aposta.get("time") or aposta.get("time_coracao"),
                    "melhor": melhor,
                    "no_melhor": freq[melhor] if n and melhor < len(freq) else 0,
                    "media": round(soma / n, 2) if n else 0.0,
                    "concursos": n,
                    "freq": freq,
                    "real": real,
                    "meses": meses if tem_mes else None,
                }
                ranking.append(item)
                grupo = grupos.setdefault(origem, {
                    "origem": origem,
                    "concurso_origem": concurso_origem,
                    "apostas": 0,
                    "melhor": 0,
                    "soma_media": 0.0,
                })
                grupo["apostas"] += 1
                grupo["soma_media"] += item["media"]
                if melhor > grupo["melhor"]:
                    grupo["melhor"] = melhor

        ranking.sort(key=lambda a: (-a["melhor"], -a["no_melhor"], -a["media"], -a["concurso_origem"], a["numero"]))
        conjuntos = []
        for grupo in grupos.values():
            qtd = grupo["apostas"] or 1
            conjuntos.append({
                "origem": grupo["origem"],
                "concurso_origem": grupo["concurso_origem"],
                "apostas": grupo["apostas"],
                "melhor": grupo["melhor"],
                "media": round(grupo["soma_media"] / qtd, 2),
            })
        conjuntos.sort(key=lambda g: (-g["melhor"], -g["media"], -g["concurso_origem"]))
        return {
            "sucesso": True,
            "modalidade": self.cfg["nome"],
            "combo": self.combo,
            "resumo": {
                "total_apostas": len(ranking),
                "ignoradas": ignoradas,
                "arquivos": len(arquivos),
                "sorteios_banco": len(cache),
                "segundos": round(time.perf_counter() - inicio, 2),
            },
            "conjuntos": conjuntos,
            "ranking": ranking,
        }

    def detalhe_retroativo(self, origem: str, numero_aposta: int) -> Dict[str, Any]:
        if not re.fullmatch(r"\d+(?:/\d+)?", origem or ""):
            return {"sucesso": False, "mensagem": "Origem inválida."}
        concurso_origem = int(origem.split("/")[0])
        pasta = os.path.join(self.pasta_base(), *origem.split("/"))
        arquivo = _arquivo_json(pasta) if os.path.isdir(pasta) else None
        if not arquivo:
            return {"sucesso": False, "mensagem": f"apostas.json não encontrado em {origem}."}
        try:
            apostas = self._ler_apostas_origem(arquivo)
        except (OSError, json.JSONDecodeError) as e:
            return {"sucesso": False, "mensagem": str(e)}
        escolhida = None
        for idx, aposta in enumerate(apostas, 1):
            if isinstance(aposta, dict) and int(aposta.get("numero", idx)) == int(numero_aposta):
                escolhida = aposta
                break
        if not escolhida:
            return {"sucesso": False, "mensagem": f"Aposta {numero_aposta} não encontrada em {origem}."}
        numeros = escolhida.get("numeros", [])
        if isinstance(numeros, str):
            numeros = [int(x) for x in re.findall(r"\d+", numeros)]
        preparado = self._preparar_retro(numeros)
        if preparado is None:
            return {"sucesso": False, "mensagem": "Aposta fora do volante desta modalidade."}
        cache = self._cache_sorteios_retro()
        fmt = (lambda n: str(n)) if self.cfg["key"] == "supersete" else (lambda n: f"{int(n):02d}")
        real = None
        linhas = []
        for draw in cache:
            concurso = draw["concurso"]
            if concurso > concurso_origem:
                break
            ac, hits = self._acertos_retro(preparado, draw, True)
            linha = {
                "concurso": concurso,
                "data": draw.get("data"),
                "acertos": ac,
                "coincidiram": [fmt(n) for n in hits],
                "sorteadas": [fmt(n) for n in draw["dezenas"]],
            }
            if concurso == concurso_origem:
                real = linha
            else:
                linhas.append(linha)
        linhas.sort(key=lambda row: (-row["acertos"], -row["concurso"]))
        return {
            "sucesso": True,
            "modalidade": self.cfg["nome"],
            "origem": origem,
            "concurso_origem": concurso_origem,
            "numero": int(numero_aposta),
            "numeros": [fmt(n) for n in preparado[1]],
            "mes": escolhida.get("mes"),
            "real": real,
            "comparacoes": linhas,
        }

    def frequencia_abs_pasta(self) -> Dict[str, Any]:
        """Conta o ABS posicional de cada aposta da pasta, do primeiro concurso ao último."""
        numeros = self._numeros_pastas()
        if not numeros:
            return {
                "sucesso": True,
                "max_abs": 0,
                "total_apostas": 0,
                "total_concursos": 0,
                "contagem": {"0": 0},
            }
        sorteios = {
            int(s.concurso): s
            for s in self.Sorteo.query.filter(self.Sorteo.concurso.in_(numeros)).all()
        }
        contagem: Dict[int, int] = {}
        total_apostas = 0
        concursos_usados = 0
        base = self.pasta_base()
        for numero in numeros:
            sorteio = sorteios.get(numero)
            if not sorteio:
                continue
            arquivo = _arquivo_json(os.path.join(base, str(numero)))
            if not arquivo:
                continue
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            apostas = dados.get("apostas") if isinstance(dados, dict) else dados
            if not isinstance(apostas, list):
                continue
            sorteadas = sorted(int(n) for n in _sorteadas(sorteio, self.cfg))
            oficiais = len(sorteadas)
            if not oficiais:
                continue
            usou = False
            for aposta in apostas:
                bruto = aposta.get("numeros") if isinstance(aposta, dict) else None
                if bruto is None:
                    continue
                nums = []
                for n in bruto:
                    try:
                        nums.append(int(n))
                    except (TypeError, ValueError):
                        continue
                if len(nums) < oficiais:
                    continue
                ordenados = sorted(nums)
                soma = 0
                for i in range(oficiais):
                    soma += abs(ordenados[i] - sorteadas[i])
                contagem[soma] = contagem.get(soma, 0) + 1
                total_apostas += 1
                usou = True
            if usou:
                concursos_usados += 1
        max_abs = max(contagem) if contagem else 0
        return {
            "sucesso": True,
            "max_abs": max_abs,
            "total_apostas": total_apostas,
            "total_concursos": concursos_usados,
            "contagem": {str(i): contagem.get(i, 0) for i in range(max_abs + 1)},
        }


def proximo_concurso(modality_key: str) -> Dict[str, Any]:
    cfg = get_conf(modality_key)
    Sorteo = _load_sorteio_model(cfg)
    ultimo = db.session.query(func.max(Sorteo.concurso)).scalar()
    if ultimo is None:
        return {"sucesso": False, "erro": "Nenhum concurso no banco. Sincronize na página inicial."}
    ultimo = int(ultimo)
    return {"sucesso": True, "ultimo_concurso_banco": ultimo, "proximo_concurso": ultimo + 1}
