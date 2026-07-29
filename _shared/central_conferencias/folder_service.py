# -*- coding: utf-8 -*-
"""Concursos em conferencia_apostas/NUMERO/apostas.json — versão multi-modalidade."""
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


def _app_base_dir() -> str:
    """Raiz do app Flask atual (cwd ao rodar o servidor)."""
    return os.getcwd()


def _base_dir() -> str:
    return os.path.join(_app_base_dir(), "conferencia_apostas")


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


def _classificar_faixa(acertos: int, cfg: dict) -> Optional[str]:
    for min_ac, label in cfg["faixas"]:
        if acertos >= min_ac:
            return label
    return None


def _analisar_aposta(
    numeros: List[int],
    sorteadas,
    cfg: dict,
) -> Dict[str, Any]:
    combo = cfg["combo_size"]

    # Super Sete: acertos coluna a coluna (repetições permitidas).
    if _scoring_positional(cfg):
        seq = normalizar_aposta_ss(numeros, colunas=combo)
        sort_list = list(sorteadas)
        ac = contar_acertos_posicional(seq, sort_list, colunas=combo)
        hits = digitos_acertados(seq, sort_list, colunas=combo)
        faixa = _classificar_faixa(ac, cfg)
        faixas_unicas = [faixa] if faixa else []
        return {
            "valor_aposta": float(combo),
            "valor_premio": 0.0,
            "valor_ganho": 0.0,
            "resultado": {
                "acertos": ac,
                "acertos_volante": ac,
                "numeros_acertados": hits,
                "faixa": faixa,
                "faixas_atingidas": faixas_unicas,
                "detalhes_premios": [],
                "valor_premio": 0.0,
                "premiado": ac >= cfg["faixas"][-1][0] if cfg["faixas"] else False,
            },
        }

    sorteadas_set: Set[int] = set(sorteadas) if not isinstance(sorteadas, set) else sorteadas
    unicos = sorted(set(numeros))
    qtd = len(unicos)
    valor_aposta = float(qtd)  # simplificado; Mega usa tabela Caixa
    volante_set = set(unicos)
    hits_volante = sorted(volante_set & sorteadas_set)
    acertos_volante = len(hits_volante)

    if qtd == combo:
        combos: List[Tuple[int, ...]] = [tuple(unicos)]
    elif qtd > combo:
        combos = list(combinations(unicos, combo))
    else:
        combos = []

    max_acertos = 0
    faixas_atingidas: List[str] = []
    for c in combos:
        ac = len(set(c) & sorteadas_set)
        max_acertos = max(max_acertos, ac)
        faixa = _classificar_faixa(ac, cfg)
        if faixa:
            faixas_atingidas.append(faixa)

    faixas_unicas = list(dict.fromkeys(faixas_atingidas))
    faixa_display = " + ".join(faixas_unicas) if faixas_unicas else None

    return {
        "valor_aposta": valor_aposta,
        "valor_premio": 0.0,
        "valor_ganho": 0.0,
        "resultado": {
            "acertos": max_acertos,
            "acertos_volante": acertos_volante,
            "numeros_acertados": hits_volante,
            "faixa": faixa_display,
            "faixas_atingidas": faixas_unicas,
            "detalhes_premios": [],
            "valor_premio": 0.0,
            "premiado": max_acertos >= cfg["faixas"][-1][0] if cfg["faixas"] else False,
        },
    }


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

    def listar_concursos_disponiveis(self) -> List[Dict[str, Any]]:
        base = _base_dir()
        if not os.path.isdir(base):
            os.makedirs(base, exist_ok=True)
            return []
        concursos = []
        for nome in os.listdir(base):
            pasta = os.path.join(base, nome)
            if not os.path.isdir(pasta):
                continue
            try:
                numero = int(nome)
            except ValueError:
                continue
            arquivo_json = os.path.join(pasta, "apostas.json")
            tem_json = os.path.isfile(arquivo_json)
            total_apostas = 0
            if tem_json:
                try:
                    with open(arquivo_json, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    total_apostas = len(dados.get("apostas", []))
                except Exception:
                    total_apostas = 0
            sorteio = self.Sorteo.query.filter_by(concurso=numero).first()
            dezenas_banco = _sorteadas(sorteio, self.cfg) if sorteio else None
            concursos.append({
                "numero_concurso": numero,
                "tem_json": tem_json,
                "total_apostas": total_apostas,
                "resultado_disponivel": sorteio is not None,
                "data_sorteio": sorteio.data if sorteio else None,
                "dezenas_banco": dezenas_banco,
                "pasta": nome,
            })
        concursos.sort(key=lambda x: x["numero_concurso"], reverse=True)
        return concursos

    def processar_concurso(self, numero_concurso: int) -> Dict[str, Any]:
        pasta = os.path.join(_base_dir(), str(numero_concurso))
        if not os.path.isdir(pasta):
            return {
                "sucesso": False,
                "mensagem": f"Pasta conferencia_apostas/{numero_concurso} não encontrada.",
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
        arquivo_json = os.path.join(pasta, "apostas.json")
        if not os.path.isfile(arquivo_json):
            return {
                "sucesso": False,
                "mensagem": f"Arquivo apostas.json não encontrado em conferencia_apostas/{numero_concurso}/",
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
        apostas_out: List[Dict[str, Any]] = []
        erros: List[str] = []
        total_investido = 0.0

        for idx, aposta in enumerate(dados.get("apostas", []), 1):
            numeros = aposta.get("numeros", [])
            if isinstance(numeros, str):
                numeros = [int(x) for x in re.findall(r"\d+", numeros)]
            if _scoring_positional(self.cfg):
                ok, msg, numeros = validar_aposta_ss(numeros, colunas=self.combo)
                if not ok:
                    erros.append(f"Aposta {idx}: {msg}")
                    continue
            elif len(numeros) < self.min_d or len(numeros) > self.max_d:
                erros.append(
                    f"Aposta {idx}: deve ter entre {self.min_d} e {self.max_d} números."
                )
                continue
            invalidas = [n for n in numeros if n < self.dmin or n > self.dmax]
            if invalidas:
                erros.append(f"Aposta {idx}: número(s) fora do volante: {invalidas}")
                continue
            analise = _analisar_aposta(numeros, sorteadas, self.cfg)
            total_investido += analise["valor_aposta"]
            fmt = (
                (lambda n: str(n))
                if self.cfg["key"] == "supersete"
                else (lambda n: f"{n:02d}")
            )
            apostas_out.append({
                "numero_aposta": aposta.get("numero", idx),
                "numeros_apostados": numeros,
                "numeros": [fmt(n) for n in numeros],
                "valor_aposta": analise["valor_aposta"],
                "valor_ganho": 0.0,
                "acertos": analise["resultado"]["acertos"],
                "dezenas_acertadas": [fmt(n) for n in analise["resultado"]["numeros_acertados"]],
                "premiacao": analise["resultado"]["faixa"]
                or f"{analise['resultado']['acertos']}/{self.combo}",
                "resultado": analise["resultado"],
            })

        dezenas_display = (
            sorteadas_list
            if _scoring_positional(self.cfg)
            else sorted(sorteadas)
        )
        return {
            "sucesso": True,
            "concurso": numero_concurso,
            "dezenas_sorteadas": [
                (str(n) if self.cfg["key"] == "supersete" else f"{n:02d}")
                for n in dezenas_display
            ],
            "data_sorteio": sorteio.data,
            "resumo": {
                "total_apostas_validas": len(apostas_out),
                "total_apostas": len(apostas_out),
                "total_investido": round(total_investido, 2),
                "total_ganho": 0.0,
                "lucro": round(-total_investido, 2),
                "roi": 0.0,
            },
            "erros": erros,
            "apostas": apostas_out,
        }


def proximo_concurso(modality_key: str) -> Dict[str, Any]:
    cfg = get_conf(modality_key)
    Sorteo = _load_sorteio_model(cfg)
    ultimo = db.session.query(func.max(Sorteo.concurso)).scalar()
    if ultimo is None:
        return {"sucesso": False, "erro": "Nenhum concurso no banco. Sincronize na página inicial."}
    ultimo = int(ultimo)
    return {"sucesso": True, "ultimo_concurso_banco": ultimo, "proximo_concurso": ultimo + 1}
