# -*- coding: utf-8 -*-
"""Cards de cada modalidade e do ciclo dela, reunidos numa página.

Lê o SQLite de cada app. Não usa o pacote resumo_modalidades.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CICLO_LOCK = threading.Lock()

# Ordem da página: Dia de Sorte (app atual) e, em seguida, as outras oito.
_ORDEM = (
    "diadesorte",
    "megasena",
    "quina",
    "maismilionaria",
    "lotofacil",
    "lotomania",
    "duplasena",
    "timemania",
    "supersete",
)

# Cards fixos da home de cada modalidade, na ordem em que aparecem lá.
# Concursos, último e a aposta simples entram à parte.
_FIXOS: Dict[str, List[Dict[str, str]]] = {
    "diadesorte": [
        {"valor": "31", "rotulo": "Dezenas", "tom": "verde"},
        {"valor": "12", "rotulo": "Meses de Sorte", "tom": "verde"},
    ],
    "megasena": [
        {"valor": "6", "rotulo": "Dezenas Sorteadas", "tom": "verde"},
        {"valor": "60", "rotulo": "Total de Dezenas", "tom": "verde"},
    ],
    "quina": [
        {"valor": "5", "rotulo": "Dezenas Sorteadas", "tom": "verde"},
        {"valor": "80", "rotulo": "Total de Dezenas", "tom": "verde"},
    ],
    "maismilionaria": [
        {"valor": "6+2", "rotulo": "dez + trevos", "tom": "verde"},
        {"valor": "7", "rotulo": "Categorias de prêmio", "tom": "verde"},
    ],
    "lotofacil": [
        {"valor": "15", "rotulo": "Dezenas Sorteadas", "tom": "verde"},
        {"valor": "15", "rotulo": "Você Marca", "tom": "verde"},
    ],
    "lotomania": [
        {"valor": "20", "rotulo": "Dezenas Sorteadas", "tom": "verde"},
        {"valor": "50", "rotulo": "Você Marca", "tom": "verde"},
    ],
    "duplasena": [
        {"valor": "2×", "rotulo": "Chances por aposta", "tom": "verde"},
    ],
    "timemania": [
        {"valor": "80", "rotulo": "Dezenas totais", "tom": "verde"},
        {"valor": "80", "rotulo": "Times cadastrados", "tom": "verde"},
    ],
    "supersete": [
        {"valor": "7", "rotulo": "Colunas independentes", "tom": "verde"},
        {"valor": "10M", "rotulo": "Combinações possíveis", "tom": "verde"},
    ],
}

_ULTIMO_CURTO = {"diadesorte", "timemania"}


def _spec_fonte(key: str) -> Dict[str, Any]:
    """Caminho do banco, tabela e colunas das dezenas de cada modalidade."""
    from ciclo_cobertura.specs import get_ciclo_spec
    from configuracoes.config import MODALITIES

    pastas = {
        "diadesorte": "AnalisePorPosicao--DiaDeSorte-Only",
        "megasena": "AnalisePorPosicao-MegaSena-Only",
        "quina": "AnalisePorPosicao-Quina-Only",
        "maismilionaria": "AnalisePorPosicao-MaisMilionaria-Only",
        "lotofacil": "AnalisePorPosicao-Lotofacil-Only",
        "lotomania": "AnalisePorPosicao-Lotomania-Only",
        "duplasena": "AnalisePorPosicao-DuplaSena-Only",
        "timemania": "AnalisePorPosicao-Timemania-Only",
        "supersete": "AnalisePorPosicao-SuperSete-Only",
    }
    spec = get_ciclo_spec(key)
    meta = MODALITIES[key]
    if key == "lotofacil":
        cols = [f"posicao_{i}" for i in range(1, 16)]
    elif key == "lotomania":
        cols = [f"d{i:02d}" for i in range(1, 21)]
    elif key == "duplasena":
        cols = [f"s1_d{i}" for i in range(1, 7)] + [f"s2_d{i}" for i in range(1, 7)]
    elif key == "timemania":
        cols = [f"d{i}" for i in range(1, 11)]
    elif key == "supersete":
        cols = [f"coluna_{i}" for i in range(1, 8)]
    else:
        cols = [f"d{i}" for i in range(1, spec.sorteadas + 1)]
    pasta = pastas[key]
    return {
        "key": key,
        "nome": meta["nome"],
        "porta": int(meta["porta"]),
        "db": os.path.join(_RAIZ, pasta, "instance", f"{key}.db"),
        "tabela": f"sorteio_{key}",
        "cols": cols,
        "lo": spec.dezena_min,
        "hi": spec.dezena_max,
        "universo": spec.universo_size,
        "ciclo": bool(spec.enabled and spec.motor == "conjunto"),
        "sorteios_dobro": key == "duplasena",
    }


def _tinta(cor: str) -> str:
    h = cor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    luz = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#1a1a1a" if luz > 0.52 else "#ffffff"


def _tema_vars(key: str) -> Dict[str, str]:
    try:
        from configuracoes.temas_modalidade import get_tema

        tema = get_tema(key)
    except Exception:
        tema = {"primary": "#6b6256", "primary_dark": "#3d3832", "bg": "#f7f5f2"}
    return {
        "cor": tema["primary"],
        "cor_ciclo": tema["primary_dark"],
        "cor_suave": tema.get("bg") or "#f7f5f2",
        "tinta": _tinta(tema["primary"]),
        "tinta_ciclo": _tinta(tema["primary_dark"]),
    }


def _milhar(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def _preco(key: str) -> str:
    from configuracoes.config import MODALITIES
    from configuracoes.fmt_utils import fmt_moeda

    try:
        from configuracoes.settings_service import obter_preco_simples

        valor = obter_preco_simples(key)
    except Exception:
        valor = float(MODALITIES[key]["preco_simples_default"])
    return fmt_moeda(valor)


def _ler_sorteios(fonte: Dict[str, Any]) -> Tuple[int, int, List[dict]]:
    if not os.path.isfile(fonte["db"]):
        raise FileNotFoundError(fonte["db"])
    cols = fonte["cols"]
    sql = "SELECT concurso, " + ", ".join(cols) + f" FROM {fonte['tabela']} ORDER BY concurso ASC"
    con = sqlite3.connect(f"file:{fonte['db']}?mode=ro", uri=True)
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()
    lo, hi = fonte["lo"], fonte["hi"]
    sorteios: List[dict] = []
    ultimo = 0
    for row in rows:
        concurso = int(row[0])
        ultimo = concurso
        dezenas = []
        vistos = set()
        for valor in row[1:]:
            if valor is None:
                continue
            n = int(valor)
            if lo <= n <= hi and n not in vistos:
                vistos.add(n)
                dezenas.append(n)
        if dezenas:
            sorteios.append({"concurso": concurso, "data": "", "dezenas": dezenas})
    return len(rows), ultimo, sorteios


def _links(porta: int) -> List[Dict[str, str]]:
    base = f"http://localhost:{porta}"
    return [
        {"titulo": "Comparar Concursos", "href": f"{base}/analise/comparar-concursos/"},
        {
            "titulo": "Comparar Apostas",
            "href": f"{base}/geradores-elite/comparador-apostas/",
        },
    ]


def _cards_identidade(fonte: Dict[str, Any], total: int, ultimo: int) -> List[Dict[str, str]]:
    key = fonte["key"]
    rotulo_ultimo = "Último" if key in _ULTIMO_CURTO else "Último Concurso"
    cards = [
        {"valor": _milhar(total), "rotulo": "Concursos", "tom": "ouro"},
        {"valor": f"#{ultimo}" if ultimo else "—", "rotulo": rotulo_ultimo, "tom": "ouro"},
    ]
    if fonte["sorteios_dobro"]:
        cards.append({
            "valor": _milhar(total * 2),
            "rotulo": "Total de Sorteios",
            "tom": "verde",
        })
    cards.extend(dict(c) for c in _FIXOS.get(key, []))
    cards.append({"valor": _preco(key), "rotulo": "Aposta simples", "tom": "verde"})
    return cards


def _ciclo_local(fonte: Dict[str, Any], sorteios: Sequence[dict]) -> Optional[dict]:
    """Mesma regra do ciclo oficial: fecha quando o universo inteiro já saiu."""
    if not sorteios:
        return None
    alvo = int(fonte["universo"])
    todas = set(range(int(fonte["lo"]), int(fonte["hi"]) + 1))
    numero = 1
    saidas: set = set()
    inicio = None
    qtd = 0
    ultimo = None
    fechado = None
    for sorteio in sorteios:
        dezenas = {int(x) for x in sorteio["dezenas"]}
        if inicio is None:
            inicio = sorteio["concurso"]
        saidas.update(dezenas)
        qtd += 1
        ultimo = sorteio["concurso"]
        if len(saidas) >= alvo:
            fechado = {
                "numero_ciclo": numero,
                "quantidade_concursos": qtd,
                "dezenas_saidas": sorted(saidas),
                "concurso_atual": ultimo,
                "em_andamento": False,
            }
            numero += 1
            saidas = set()
            inicio = None
            qtd = 0
    if qtd > 0:
        atual = {
            "numero_ciclo": numero,
            "quantidade_concursos": qtd,
            "dezenas_saidas": sorted(saidas),
            "concurso_atual": ultimo,
            "em_andamento": True,
        }
    else:
        atual = fechado
    if not atual:
        return None
    saidas_set = set(atual["dezenas_saidas"])
    pendentes = sorted(todas - saidas_set)
    atual["universo"] = alvo
    atual["total_dezenas_saidas"] = len(saidas_set)
    atual["dezenas_pendentes"] = pendentes
    return atual


def _indicadas(key: str, sorteios: Sequence[dict], ciclo: dict) -> List[int]:
    """Top 3 do mesmo placar de dezenas do ciclo, só entre as pendentes."""
    import ciclo_cobertura.inteligencia_service as intel

    pendentes = [int(n) for n in ciclo.get("dezenas_pendentes") or []]

    def _carregar(_modality_key: str = key):
        return list(sorteios)

    with _CICLO_LOCK:
        antigo = intel.carregar_sorteios_asc
        intel.carregar_sorteios_asc = _carregar
        try:
            scores = intel.CicloInteligenciaService._scores_dezenas(ciclo, pendentes, key)
        except Exception:
            scores = []
        finally:
            intel.carregar_sorteios_asc = antigo
    top = [int(s["dezena"]) for s in scores if s.get("pendente")]
    if not top:
        top = pendentes
    return top[:3]


def _vazio(nome: str, key: str, erro: str) -> Dict[str, Any]:
    bloco = {
        "sucesso": False,
        "nome": nome,
        "modality_key": key,
        "cards_modalidade": [],
        "cards_ciclo": [],
        "pendentes": [],
        "n_pendentes": 0,
        "links": [],
        "erro": erro,
    }
    bloco.update(_tema_vars(key))
    return bloco


def montar_bloco(modality_key: str) -> Dict[str, Any]:
    fonte = _spec_fonte(modality_key)
    total, ultimo, sorteios = _ler_sorteios(fonte)
    bloco: Dict[str, Any] = {
        "sucesso": True,
        "nome": fonte["nome"],
        "modality_key": fonte["key"],
        "cards_modalidade": _cards_identidade(fonte, total, ultimo),
        "cards_ciclo": [],
        "pendentes": [],
        "n_pendentes": 0,
        "links": _links(fonte["porta"]),
        "erro": None,
    }
    bloco.update(_tema_vars(fonte["key"]))
    if not fonte["ciclo"]:
        bloco["erro"] = (
            "Super Sete sorteia um dígito por coluna. Não há ciclo único de dezenas."
        )
        return bloco
    if not sorteios:
        bloco["sucesso"] = False
        bloco["erro"] = "Nenhum sorteio encontrado neste banco."
        return bloco

    ciclo = _ciclo_local(fonte, sorteios)
    indicadas = _indicadas(fonte["key"], sorteios, ciclo) if ciclo else []
    if not ciclo:
        bloco["sucesso"] = False
        bloco["erro"] = "Nenhum ciclo encontrado."
        return bloco

    universo = int(ciclo.get("universo") or fonte["universo"])
    saidas = int(ciclo.get("total_dezenas_saidas") or 0)
    pendentes = [int(x) for x in (ciclo.get("dezenas_pendentes") or [])]
    bloco["n_pendentes"] = len(pendentes)
    bloco["cards_ciclo"] = [
        {"valor": f"#{ciclo.get('numero_ciclo')}", "rotulo": "Ciclo Atual", "tom": "azul"},
        {"valor": str(ciclo.get("quantidade_concursos") or 0), "rotulo": "Concursos no Ciclo", "tom": "azul"},
        {"valor": f"{saidas}/{universo}", "rotulo": "Dezenas Saídas", "tom": "verde"},
        {"valor": str(len(pendentes)), "rotulo": "Dezenas Pendentes", "tom": "verde"},
    ]
    faltam = set(pendentes)
    ranks: Dict[int, int] = {}
    for n in indicadas:
        if n in faltam and n not in ranks:
            ranks[n] = len(ranks) + 1
        if len(ranks) == 3:
            break
    bloco["pendentes"] = [
        {"txt": str(n).zfill(2), "rank": ranks.get(n)}
        for n in pendentes
    ]
    return bloco


def montar_blocos(modality_keys: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    blocos = []
    for key in modality_keys or _ORDEM:
        try:
            blocos.append(montar_bloco(key))
        except Exception as exc:
            blocos.append(_vazio(key, key, str(exc)))
    return blocos


def montar_todos() -> List[Dict[str, Any]]:
    return montar_blocos(_ORDEM)
