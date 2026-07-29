"""Leitura/gravação do JSON central e cálculo proporcional de bolão."""

import json

import os

from datetime import datetime

from typing import Any, Dict, List, Optional



import requests



from configuracoes.caixa_live_service import buscar_ao_vivo, limpar_cache as limpar_cache_caixa
from configuracoes.catalog_loader import obter_catalogo_modalidade
from configuracoes.config import MODALITIES



_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_JSON_PATH = os.path.join(_LOTERIAS, "config_modalidades.json")





def _json_path() -> str:

    return _JSON_PATH





def _default_store() -> Dict[str, Any]:

    store = {}

    for key, meta in MODALITIES.items():

        store[key] = {

            "preco_simples": meta["preco_simples_default"],

            "preco_bolao": None,

            "atualizado_em": None,

        }

    return store





from configuracoes.fmt_utils import fmt_moeda, fmt_numero_br, parse_preco





def carregar_store() -> Dict[str, Any]:

    path = _json_path()

    if not os.path.isfile(path):

        data = _default_store()

        salvar_store(data)

        return data

    try:

        with open(path, "r", encoding="utf-8") as f:

            data = json.load(f)

    except Exception:

        data = _default_store()

    base = _default_store()

    for key, defaults in base.items():

        if key not in data:

            data[key] = defaults

        else:

            if "preco_simples" not in data[key]:

                data[key]["preco_simples"] = defaults["preco_simples"]

            if "preco_bolao" not in data[key]:

                data[key]["preco_bolao"] = None

    return data





def salvar_store(data: Dict[str, Any]) -> bool:

    try:

        with open(_json_path(), "w", encoding="utf-8") as f:

            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:

        print(f"[CONFIG] Erro ao salvar: {e}")

        return False





def _calcular_bolao(preco_simples: float, meta: Dict[str, Any], preco_bolao_override: Optional[float] = None) -> Dict[str, Any]:

    b = meta["bolao"]

    ps = float(preco_simples)

    if preco_bolao_override is not None and preco_bolao_override > 0:

        valor_min = round(float(preco_bolao_override), 2)

        manual = True

    else:

        valor_min = round(ps * b["fator_valor_minimo"], 2)

        manual = False

    preco_cota = round(ps * b["fator_por_cota"], 2)

    return {

        "cotas_min": b["cotas_min"],

        "cotas_max": b["cotas_max"],

        "valor_minimo": valor_min,

        "preco_por_cota": preco_cota,

        "fator_valor_minimo": b["fator_valor_minimo"],

        "fator_por_cota": b["fator_por_cota"],

        "manual": manual,

    }





def obter_preco_simples(modality_key: str) -> float:

    store = carregar_store()

    meta = MODALITIES.get(modality_key, {})

    row = store.get(modality_key, {})

    return float(row.get("preco_simples", meta.get("preco_simples_default", 0)))





def salvar_preco_simples(modality_key: str, preco: float) -> bool:

    store = carregar_store()

    if modality_key not in MODALITIES:

        return False

    store.setdefault(modality_key, {})

    store[modality_key]["preco_simples"] = round(float(preco), 2)

    store[modality_key]["atualizado_em"] = datetime.now().isoformat(timespec="seconds")

    return salvar_store(store)





def salvar_precos_modalidade(

    modality_key: str,

    preco_simples: float,

    preco_bolao: Optional[float] = None,

) -> bool:

    store = carregar_store()

    if modality_key not in MODALITIES:

        return False

    store.setdefault(modality_key, {})

    store[modality_key]["preco_simples"] = round(float(preco_simples), 2)

    if preco_bolao is not None and preco_bolao > 0:

        store[modality_key]["preco_bolao"] = round(float(preco_bolao), 2)

    else:

        store[modality_key]["preco_bolao"] = None

    store[modality_key]["atualizado_em"] = datetime.now().isoformat(timespec="seconds")

    return salvar_store(store)





def montar_modalidade(modality_key: str, concurso: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

    meta = MODALITIES[modality_key]

    store = carregar_store()

    row = store.get(modality_key, {})

    preco = float(row.get("preco_simples", meta["preco_simples_default"]))

    pb_raw = row.get("preco_bolao")

    preco_bolao_override = float(pb_raw) if pb_raw not in (None, "", 0) else None

    bolao = _calcular_bolao(preco, meta, preco_bolao_override)



    site = 0

    if concurso:

        site = int(

            concurso.get("ultimo_concurso_api")

            or concurso.get("concurso_maximo")

            or 0

        )

    app = site + 1 if site else 0



    return {

        "key": modality_key,

        "nome": meta["nome"],

        "porta": meta["porta"],

        "link_caixa": meta["link_caixa"],

        "preco_simples": preco,

        "preco_simples_fmt": fmt_moeda(preco),

        "preco_simples_input": fmt_numero_br(preco),

        "preco_bolao": preco_bolao_override,

        "preco_bolao_input": fmt_numero_br(bolao["valor_minimo"]) if bolao["valor_minimo"] else "",

        "bolao": bolao,

        "bolao_valor_minimo_fmt": fmt_moeda(bolao["valor_minimo"]),

        "bolao_preco_cota_fmt": fmt_moeda(bolao["preco_por_cota"]),

        "bolao_manual": bolao.get("manual", False),

        "aposta": meta["aposta"],

        "concurso_site": site,

        "concurso_app": app,

        "atualizado_em": row.get("atualizado_em"),

        "concurso_raw": concurso or {},

    }





def listar_todas_modalidades() -> List[Dict[str, Any]]:

    out = []

    for key in MODALITIES:

        conc = buscar_concurso_remoto(key)

        out.append(montar_modalidade(key, conc))

    return out





def buscar_concurso_remoto(modality_key: str, timeout: int = 5) -> Dict[str, Any]:

    meta = MODALITIES.get(modality_key)

    if not meta:

        return {}

    porta = meta["porta"]

    try:

        r = requests.get(f"http://127.0.0.1:{porta}/api/status-banco", timeout=timeout)

        if r.status_code == 200:

            data = r.json()

            if data.get("status") == "success":

                return data

    except Exception:

        pass

    return {}







def montar_perfil_completo(
    modality_key: str,
    concurso: Optional[Dict[str, Any]] = None,
    incluir_caixa_live: bool = False,
) -> Dict[str, Any]:
    """Perfil unificado: preços editáveis + catálogo oficial + banco local + API Caixa."""
    base = montar_modalidade(modality_key, concurso)
    catalogo = obter_catalogo_modalidade(modality_key)
    caixa_live = buscar_ao_vivo(modality_key) if incluir_caixa_live else {}

    if incluir_caixa_live and not caixa_live.get("ok") and concurso:
        ult_local = int(concurso.get("ultimo_concurso_api") or concurso.get("concurso_maximo") or 0)
        if ult_local:
            from configuracoes.caixa_live_service import _url_api
            caixa_live = {
                **caixa_live,
                "ok": True,
                "numero": ult_local,
                "api_url": _url_api(modality_key),
                "mensagem": "Concurso via banco local (API Caixa direta sem resposta nesta consulta).",
            }

    if caixa_live.get("ok") and caixa_live.get("numero"):
        site_api = int(caixa_live["numero"])
        if site_api > (base.get("concurso_site") or 0):
            base["concurso_site"] = site_api
            base["concurso_app"] = site_api + 1
            base["concurso_fonte_api"] = True

    return {
        **base,
        "catalogo": catalogo,
        "caixa_live": caixa_live,
        "meta_expansao": {
            "versao_catalogo": "1.0",
            "atualizavel_via_json": True,
            "api_oficial": caixa_live.get("api_url") or f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{catalogo.get('api_slug', modality_key)}/",
        },
    }


def listar_perfis_completos(
    refresh_caixa: bool = False,
    incluir_caixa_live: bool = False,
) -> List[Dict[str, Any]]:
    if refresh_caixa:
        limpar_cache_caixa()
    return [
        montar_perfil_completo(
            k,
            buscar_concurso_remoto(k),
            incluir_caixa_live=incluir_caixa_live or refresh_caixa,
        )
        for k in MODALITIES
    ]

