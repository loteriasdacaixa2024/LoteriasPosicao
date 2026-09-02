"""Consulta dados ao vivo na API oficial Caixa (último concurso)."""
from typing import Any, Dict, Optional

import requests

try:
    import certifi
except ImportError:
    certifi = None

from configuracoes.catalog_loader import obter_catalogo_modalidade
from configuracoes.config import MODALITIES
from configuracoes.fmt_utils import fmt_moeda

BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api"
_HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (LoteriasPosicao)"}
_cache: Dict[str, Dict[str, Any]] = {}


def _url_api(modality_key: str) -> str:
    meta = MODALITIES.get(modality_key, {})
    cat = obter_catalogo_modalidade(modality_key)
    slug = meta.get("api_slug") or cat.get("api_slug") or modality_key
    custom = meta.get("api_url")
    if custom:
        return custom if custom.endswith("/") else f"{custom}/"
    return f"{BASE}/{slug}/"


def _get(url: str, timeout: int = 12) -> Optional[dict]:
    """Mesmo padrão das apps: certifi e, se falhar, sem verificação SSL."""
    kwargs = {"headers": _HEADERS, "timeout": timeout}
    tentativas = []
    if certifi:
        tentativas.append(certifi.where())
    tentativas.append(False)

    vistos = set()
    for verify in tentativas:
        if verify in vistos:
            continue
        vistos.add(verify)
        try:
            r = requests.get(url, verify=verify, **kwargs)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue
    return None


def _numero_concurso(data: dict) -> int:
    for key in ("numero", "numeroConcurso", "numeroConcursoUltimo", "concurso", "id"):
        if data.get(key) is not None:
            try:
                return int(data[key])
            except (TypeError, ValueError):
                pass
    return 0


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def buscar_ao_vivo(modality_key: str, use_cache: bool = True) -> Dict[str, Any]:
    if use_cache and modality_key in _cache:
        return _cache[modality_key]

    url = _url_api(modality_key)

    out: Dict[str, Any] = {
        "ok": False,
        "api_url": url,
        "numero": 0,
        "data_apuracao": None,
        "data_proximo": None,
        "valor_estimado_proximo": None,
        "valor_estimado_proximo_fmt": None,
        "valor_acumulado": None,
        "valor_acumulado_fmt": None,
        "valor_arrecadacao": None,
        "valor_arrecadacao_fmt": None,
        "rateio": [],
        "lista_dezenas": [],
        "mes_sorte": None,
        "nome_mes_sorte": None,
        "localizacao": None,
        "mensagem": "API indisponível ou sem resposta.",
    }

    try:
        data = _get(url)
        if not data:
            _cache[modality_key] = out
            return out

        out["ok"] = True
        out["mensagem"] = "Dados obtidos da API Caixa."
        out["numero"] = _numero_concurso(data)
        out["data_apuracao"] = data.get("dataApuracao") or data.get("dataApuracaoFormatada")
        out["data_proximo"] = data.get("dataProximoConcurso") or data.get("dataProximoConcursoFormatada")

        for field, target in (
            ("valorEstimadoProximoConcurso", "valor_estimado_proximo"),
            ("valorAcumuladoProximoConcurso", "valor_acumulado"),
            ("valorArrecadacao", "valor_arrecadacao"),
        ):
            fv = _safe_float(data.get(field))
            if fv is not None:
                out[target] = fv
                out[f"{target}_fmt"] = fmt_moeda(fv)

        if out["valor_acumulado"] is None and data.get("acumulado") is True:
            out["acumulado_proximo"] = True

        rateio_raw = data.get("listaRateioPremio")
        if isinstance(rateio_raw, list):
            for r in rateio_raw[:8]:
                if not isinstance(r, dict):
                    continue
                vp = _safe_float(r.get("valorPremio"))
                out["rateio"].append({
                    "faixa": r.get("faixa") or r.get("descricaoFaixa"),
                    "numero_ganhadores": r.get("numeroDeGanhadores"),
                    "valor_premio": vp,
                    "valor_premio_fmt": fmt_moeda(vp) if vp is not None else None,
                })

        dezenas = data.get("dezenasSorteadasOrdemSorteio") or data.get("listaDezenas")
        if isinstance(dezenas, list):
            out["lista_dezenas"] = dezenas

        out["mes_sorte"] = data.get("mesSorte")
        out["nome_mes_sorte"] = (
            data.get("nomeTimeCoracaoMesSorte")
            or data.get("nomeMesSorte")
            or data.get("mesSorteNome")
        )
        out["localizacao"] = data.get("localidade") or data.get("nomeMunicipioUFSorteio") or data.get("localSorteio")

    except Exception as e:
        out["ok"] = False
        out["mensagem"] = f"Erro ao consultar API: {e}"

    _cache[modality_key] = out
    return out


def limpar_cache(modality_key: Optional[str] = None) -> None:
    if modality_key:
        _cache.pop(modality_key, None)
    else:
        _cache.clear()


def buscar_todos_ao_vivo() -> Dict[str, Dict[str, Any]]:
    limpar_cache()
    return {k: buscar_ao_vivo(k, use_cache=False) for k in MODALITIES}
