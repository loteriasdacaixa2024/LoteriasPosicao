# -*- coding: utf-8 -*-
"""Concursos em conferencia_apostas/<modalidade>/<numero>/apostas.json."""
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


def _preco_volante(cfg: dict, n_dezenas: int) -> float:
    """Preço oficial da página Configurações (aposta simples editável + tabela Caixa)."""
    chave = _chave_preco(cfg)
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
            return round(float(tabela) * (atual / float(catalogo)), 2)
        if tabela is not None:
            return round(float(tabela), 2)
        if atual:
            return round(atual, 2)
    except Exception:
        pass
    return float(n_dezenas)


# Caixa: 5 acertos, 4 acertos e Mês da Sorte são prêmios fixos.
# 7 e 6 vêm do rateio do concurso. O mês acumula com qualquer faixa de dezenas.
_FIXOS_DIASORTE = {5: 25.0, 4: 5.0, 0: 2.5}


def _rateios_concurso(cfg: dict, numero: int) -> Dict[int, float]:
    if cfg.get("key") != "diasorte":
        return {}
    out = dict(_FIXOS_DIASORTE)
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


def _classificar_faixa(acertos: int, cfg: dict) -> Optional[str]:
    for min_ac, label in cfg["faixas"]:
        if acertos >= min_ac:
            return label
    return None


def _faixa_combo(acertos: int, mes_ok: bool, cfg: dict):
    """Melhor faixa de uma aposta simples. No Dia de Sorte, 5+ exige o mês; 4 não."""
    faixas = cfg.get("faixas") or []
    if cfg.get("has_mes"):
        exige_mes = {5, 6, 7}
        for minimo, label in faixas:
            if acertos >= minimo and (minimo not in exige_mes or mes_ok):
                return minimo, label
        if mes_ok:
            return 0, "Mês"
        return None, None
    for minimo, label in faixas:
        if acertos >= minimo:
            return minimo, label
    return None, None


def _analisar_aposta(
    numeros: List[int],
    sorteadas,
    cfg: dict,
    mes_aposta=None,
    mes_sorteio=None,
    rateios: Optional[Dict[int, float]] = None,
) -> Dict[str, Any]:
    combo = cfg["combo_size"]

    # Super Sete: acertos coluna a coluna (repetições permitidas).
    if _scoring_positional(cfg):
        seq = normalizar_aposta_ss(numeros, colunas=combo)
        sort_list = list(sorteadas)
        ac = contar_acertos_posicional(seq, sort_list, colunas=combo)
        hits = digitos_acertados(seq, sort_list, colunas=combo)
        minimo, faixa = _faixa_combo(ac, True, cfg)
        faixas_unicas = [faixa] if faixa else []
        unit = float((rateios or {}).get(minimo, 0) or 0) if minimo is not None else 0.0
        detalhes = []
        if faixa:
            detalhes.append({"descricao": faixa, "quantidade": 1, "valor": round(unit, 2)})
        return {
            "valor_aposta": _preco_volante(cfg, combo),
            "valor_premio": round(unit, 2),
            "valor_ganho": round(unit, 2),
            "resultado": {
                "acertos": ac,
                "acertos_volante": ac,
                "numeros_acertados": hits,
                "faixa": faixa,
                "faixas_atingidas": faixas_unicas,
                "detalhes_premios": detalhes,
                "valor_premio": round(unit, 2),
                "premiado": bool(faixa),
                "destaque": ac > 0,
                "premio_maximo": bool(faixa) and minimo == (cfg["faixas"][0][0] if cfg.get("faixas") else combo),
            },
        }

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
        unit = float((rateios or {}).get(item["minimo"], 0) or 0)
        valor = round(unit * item["quantidade"], 2)
        valor_ganho += valor
        detalhes.append({
            "descricao": faixa,
            "quantidade": item["quantidade"],
            "valor": valor,
        })
    detalhes.sort(key=lambda d: -d["quantidade"])
    if cfg.get("has_mes") and mes_ok and not any(d["descricao"] == "Mês" for d in detalhes):
        unit_mes = float((rateios or {}).get(0, _FIXOS_DIASORTE[0]) or 0)
        if unit_mes:
            valor_ganho += unit_mes
            detalhes.append({"descricao": "Mês", "quantidade": 1, "valor": round(unit_mes, 2)})
    faixas_unicas = [d["descricao"] for d in detalhes]
    faixa_display = " + ".join(faixas_unicas) if faixas_unicas else None
    topo = cfg["faixas"][0][0] if cfg.get("faixas") else combo
    premio_maximo = any(item.get("minimo") == topo for item in contagem.values())

    return {
        "valor_aposta": valor_aposta,
        "valor_premio": round(valor_ganho, 2),
        "valor_ganho": round(valor_ganho, 2),
        "resultado": {
            "acertos": max_acertos,
            "acertos_volante": acertos_volante,
            "numeros_acertados": hits_volante,
            "faixa": faixa_display,
            "faixas_atingidas": faixas_unicas,
            "detalhes_premios": detalhes,
            "valor_premio": round(valor_ganho, 2),
            "premiado": bool(faixas_unicas),
            "mes_ok": mes_ok if cfg.get("has_mes") else None,
            "destaque": max_acertos >= 4 or acertos_volante >= 4 or bool(cfg.get("has_mes") and mes_ok),
            "premio_maximo": premio_maximo,
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
        apostas_out: List[Dict[str, Any]] = []
        erros: List[str] = []
        total_investido = 0.0
        total_ganho = 0.0
        distribuicao: Dict[str, Dict[str, Any]] = {}

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
            analise = _analisar_aposta(
                numeros,
                sorteadas,
                self.cfg,
                mes_aposta=aposta.get("mes"),
                mes_sorteio=mes_sorteio,
                rateios=rateios,
            )
            total_investido += analise["valor_aposta"]
            total_ganho += analise["valor_ganho"]
            for det in analise["resultado"].get("detalhes_premios") or []:
                faixa = det.get("descricao") or "Prêmio"
                slot = distribuicao.setdefault(faixa, {"quantidade": 0, "total_ganho": 0.0})
                slot["quantidade"] += int(det.get("quantidade") or 0)
                slot["total_ganho"] = round(slot["total_ganho"] + float(det.get("valor") or 0), 2)
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
                "valor_ganho": analise["valor_ganho"],
                "mes": aposta.get("mes"),
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
        fmt_dez = (lambda n: str(n)) if self.cfg["key"] == "supersete" else (lambda n: f"{int(n):02d}")
        ordem_sorteio = _ordem_sorteio(sorteio, self.cfg)
        return {
            "sucesso": True,
            "concurso": numero_concurso,
            "dezenas_sorteadas": [fmt_dez(n) for n in dezenas_display],
            "dezenas_ordem_sorteio": [fmt_dez(n) for n in ordem_sorteio],
            "data_sorteio": sorteio.data,
            "modalidade": self.cfg["nome"],
            "mes_sorteado": mes_sorteio,
            "dezenas_oficiais": self.combo,
            "resumo": {
                "total_apostas_validas": len(apostas_out),
                "total_apostas": len(apostas_out),
                "total_investido": round(total_investido, 2),
                "total_ganho": round(total_ganho, 2),
                "lucro": round(total_ganho - total_investido, 2),
                "roi": round((total_ganho - total_investido) / total_investido * 100, 2) if total_investido else 0.0,
                "distribuicao_faixas": distribuicao,
                "premiadas": sum(1 for a in apostas_out if (a.get("resultado") or {}).get("premiado")),
            },
            "erros": erros,
            "apostas": apostas_out,
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
