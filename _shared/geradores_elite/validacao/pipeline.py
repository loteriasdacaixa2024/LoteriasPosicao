# -*- coding: utf-8 -*-
"""
Pipeline global pós-geração dos Geradores Elite.

Fluxo único:
  apostas geradas → validação histórico oficial → política → back test → resposta

Não altera algoritmos de geração. Consumido por todos os endpoints /gerar.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Set, Type

from geradores_elite.validacao.validador_global import (
    ValidadorGeradoresElite,
    _extrair_dezenas,
    _load_model,
    _normalizar_chave,
    dezenas_padrao_sorteio,
)

PoliticaHistorico = Literal["marcar", "manter", "descartar"]

_MAPA_CACHE: Dict[str, Dict[frozenset, List[Dict[str, Any]]]] = {}


def carregar_mapa_historico_detalhado(
    modality_key: str,
    *,
    sorteio_model: Optional[Type[Any]] = None,
    dezenas_fn: Optional[Callable[[Any], List[int]]] = None,
    force: bool = False,
) -> Dict[frozenset, List[Dict[str, Any]]]:
    """
    frozenset(dezenas) → lista de ocorrências {concurso, data}.
    Cache em memória por modalidade.
    """
    key = (modality_key or "").strip().lower()
    if not force and key in _MAPA_CACHE:
        return _MAPA_CACHE[key]

    model = sorteio_model or _load_model(key)
    if model is None:
        _MAPA_CACHE[key] = {}
        return _MAPA_CACHE[key]

    from models.shared import db

    fn = dezenas_fn or dezenas_padrao_sorteio
    mapa: Dict[frozenset, List[Dict[str, Any]]] = defaultdict(list)
    try:
        rows = db.session.query(model).order_by(model.concurso.asc()).all()
    except Exception:
        _MAPA_CACHE[key] = {}
        return _MAPA_CACHE[key]

    for s in rows:
        dz = fn(s)
        if not dz:
            continue
        chave = frozenset(int(x) for x in dz)
        mapa[chave].append({
            "concurso": int(getattr(s, "concurso", 0) or 0),
            "data": getattr(s, "data", "") or "",
        })

    out = dict(mapa)
    _MAPA_CACHE[key] = out
    # Alinha o cache set do ValidadorGeradoresElite
    ValidadorGeradoresElite.invalidar_cache_historico(key)
    try:
        from geradores_elite.validacao import validador_global as vg
        with vg._LOCK:
            vg._HIST_CACHE[key] = set(out.keys())
    except Exception:
        pass
    return out


def invalidar_cache_pipeline(modality_key: Optional[str] = None) -> None:
    if modality_key:
        _MAPA_CACHE.pop((modality_key or "").strip().lower(), None)
        ValidadorGeradoresElite.invalidar_cache_historico(modality_key)
    else:
        _MAPA_CACHE.clear()
        ValidadorGeradoresElite.invalidar_cache_historico()


def _resolver_politica(raw: Any, descartar_flag: Any = None) -> PoliticaHistorico:
    if descartar_flag is True:
        return "descartar"
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in ("descartar", "remover", "drop"):
            return "descartar"
        if v in ("manter", "keep"):
            return "manter"
        if v in ("marcar", "flag", "anotar", "confirmar"):
            return "marcar"
    # padrão: marcar (mantém + destaca) — seguro e transparente
    return "marcar"


def _chave_lista_apostas(resultado: Dict[str, Any], campo: Optional[str] = None) -> Optional[str]:
    if campo and isinstance(resultado.get(campo), list):
        return campo
    for cand in ("apostas", "jogos", "apostas_com_mes"):
        if isinstance(resultado.get(cand), list):
            return cand
    return None


def _obter_lista_mutavel(
    resultado: Dict[str, Any],
    campo_lista: Optional[str] = None,
) -> tuple:
    """
    Retorna (chave_path, lista, setter).
    chave_path: 'apostas' | 'jogos' | 'construcao.apostas'
    """
    chave = _chave_lista_apostas(resultado, campo_lista)
    if chave:
        return chave, list(resultado.get(chave) or []), None

    const = resultado.get("construcao")
    if isinstance(const, dict) and isinstance(const.get("apostas"), list):
        return "construcao.apostas", list(const.get("apostas") or []), "construcao"
    return None, [], None


def _gravar_lista(resultado: Dict[str, Any], path: str, lista: List[Any]) -> None:
    if path == "construcao.apostas":
        if isinstance(resultado.get("construcao"), dict):
            resultado["construcao"] = dict(resultado["construcao"])
            resultado["construcao"]["apostas"] = lista
        return
    resultado[path] = lista


def _resultado_ok(resultado: Dict[str, Any]) -> bool:
    if not isinstance(resultado, dict):
        return False
    if resultado.get("sucesso") is False or resultado.get("ok") is False:
        return False
    if resultado.get("sucesso") is True or resultado.get("ok") is True:
        return True
    # alguns serviços só retornam apostas
    return _chave_lista_apostas(resultado) is not None


def anotar_e_aplicar_politica(
    apostas: Sequence[Any],
    modality_key: str,
    *,
    politica: PoliticaHistorico = "marcar",
    campo_dezenas: str = "dezenas",
) -> Dict[str, Any]:
    """Anota cada aposta e aplica política (marcar/manter/descartar)."""
    mapa = carregar_mapa_historico_detalhado(modality_key)
    mantidas: List[Any] = []
    ja_sorteadas_itens: List[Dict[str, Any]] = []
    modality = (modality_key or "").strip().lower()

    for item in apostas or []:
        dz = _extrair_dezenas(item, campo_dezenas)
        if dz is None:
            mantidas.append(item)
            continue
        chave = _normalizar_chave(dz)
        ocorrencias = mapa.get(chave) or []
        if isinstance(item, dict):
            novo = dict(item)
        else:
            novo = {"dezenas": list(dz), "_raw": item}

        if ocorrencias:
            ultima = ocorrencias[-1]
            novo["ja_sorteada"] = True
            novo["concurso_historico"] = ultima.get("concurso")
            novo["data_historico"] = ultima.get("data") or ""
            novo["ocorrencias_historico"] = len(ocorrencias)
            novo["historico_ocorrencias"] = list(ocorrencias)
            novo["modalidade_historico"] = modality
            ja_sorteadas_itens.append({
                "dezenas": sorted(chave),
                "concurso": ultima.get("concurso"),
                "data": ultima.get("data") or "",
                "ocorrencias": len(ocorrencias),
                "ocorrencias_detalhe": list(ocorrencias),
                "modalidade": modality,
            })
            if politica == "descartar":
                continue
            mantidas.append(novo)
        else:
            novo["ja_sorteada"] = False
            novo["concurso_historico"] = None
            novo["data_historico"] = ""
            novo["ocorrencias_historico"] = 0
            novo["historico_ocorrencias"] = []
            mantidas.append(novo)

    for idx, ap in enumerate(mantidas, 1):
        if isinstance(ap, dict):
            ap["numero"] = idx

    return {
        "apostas": mantidas,
        "ja_sorteadas_count": len(ja_sorteadas_itens),
        "ja_sorteadas": ja_sorteadas_itens,
        "descartadas": len(ja_sorteadas_itens) if politica == "descartar" else 0,
        "total_antes": len(list(apostas or [])),
        "politica": politica,
        "modalidade": modality,
    }


def _rodar_backtest(
    modality_key: str,
    apostas: List[Any],
    limite: int = 30,
) -> Dict[str, Any]:
    if not apostas:
        return {"sucesso": False, "erro": "Nenhuma aposta para back test.", "pulado": True}
    try:
        from geradores_elite.engine_final_core import backtest_apostas_engine

        # normaliza formato
        norm = []
        for ap in apostas:
            if isinstance(ap, dict):
                item = dict(ap)
                if "dezenas" not in item:
                    dz = _extrair_dezenas(ap)
                    if dz:
                        item["dezenas"] = dz
                norm.append(item)
            else:
                dz = _extrair_dezenas(ap)
                if dz:
                    norm.append({"dezenas": dz})
        return backtest_apostas_engine(modality_key, norm, limite=limite)
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def pipeline_pos_geracao(
    resultado: Dict[str, Any],
    *,
    modality_key: str,
    origem: str = "elite",
    politica_historico: Any = "marcar",
    descartar_historico: Any = None,
    executar_backtest: bool = True,
    limite_backtest: int = 30,
    campo_lista: Optional[str] = None,
    campo_dezenas: str = "dezenas",
    checar_memoria_geradores: bool = False,
) -> Dict[str, Any]:
    """
    Ponto único de entrada pós-geração.

    - Anota / filtra apostas já sorteadas no histórico oficial.
    - Opcionalmente aplica memória entre geradores (off por padrão para não surpreender).
    - Executa back test nas apostas aprovadas.
    """
    if not _resultado_ok(resultado):
        return resultado

    out = dict(resultado)
    politica = _resolver_politica(politica_historico, descartar_historico)
    path, itens, _nested = _obter_lista_mutavel(out, campo_lista)
    if not path:
        out["validacao_historico"] = {
            "aplicada": False,
            "motivo": "Lista de apostas não encontrada no resultado.",
        }
        return out

    anot = anotar_e_aplicar_politica(
        itens,
        modality_key,
        politica=politica,
        campo_dezenas=campo_dezenas,
    )
    aprovados = anot["apostas"]

    # Memória entre geradores (opcional) — só remove, não anota histórico
    if checar_memoria_geradores and aprovados:
        vg = ValidadorGeradoresElite.validar_lote(
            aprovados,
            origem=origem,
            modality_key=modality_key,
            campo_dezenas=campo_dezenas,
            checar_historico=False,
            checar_memoria=True,
            registrar_aprovadas=True,
        )
        aprovados = vg["aprovados"]
        out["validacao_memoria"] = vg["stats"]

    _gravar_lista(out, path, aprovados)

    # Contadores comuns
    for k in ("quantidade", "qtd_gerados", "total_geradas", "geradas", "qtd_geradas"):
        if k in out:
            out[k] = len(aprovados)

    validacao = {
        "aplicada": True,
        "origem": origem,
        "modalidade": modality_key,
        "politica": politica,
        "analisadas": anot["total_antes"],
        "aprovadas": len(aprovados),
        "ja_sorteadas_count": anot["ja_sorteadas_count"],
        "descartadas": anot["descartadas"],
        "itens_ja_sorteados": anot["ja_sorteadas"],
        "campo_lista": path,
        "data_hora": datetime.now().isoformat(timespec="seconds"),
    }
    out["validacao_historico"] = validacao
    # Compatibilidade com UIs que já leem estes campos
    out["historico"] = {
        "ja_sorteadas_count": anot["ja_sorteadas_count"],
        "descartadas": anot["descartadas"],
        "total_antes": anot["total_antes"],
        "itens": anot["ja_sorteadas"],
        "politica": politica,
    }
    out["descartadas_historico"] = anot["descartadas"]

    partes_aviso = []
    if out.get("aviso"):
        partes_aviso.append(str(out["aviso"]))
    if anot["ja_sorteadas_count"]:
        if politica == "descartar":
            partes_aviso.append(
                f"{anot['descartadas']} aposta(s) descartada(s) por já existirem "
                f"no histórico oficial ({modality_key})."
            )
        else:
            partes_aviso.append(
                f"{anot['ja_sorteadas_count']} aposta(s) já sorteada(s) no histórico "
                f"oficial — marcadas com concurso/data."
            )
    if partes_aviso:
        out["aviso"] = " ".join(partes_aviso)

    if executar_backtest:
        bt = _rodar_backtest(modality_key, aprovados, limite=int(limite_backtest or 30))
        out["backtest"] = bt
    else:
        out["backtest"] = {"sucesso": False, "pulado": True}

    return out


def pipeline_from_request(
    resultado: Dict[str, Any],
    *,
    modality_key: str,
    origem: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Lê flags do body JSON do request e aplica o pipeline."""
    data = data or {}
    exec_bt = data.get("executar_backtest")
    if exec_bt is None:
        exec_bt = True
    return pipeline_pos_geracao(
        resultado,
        modality_key=modality_key,
        origem=origem,
        politica_historico=data.get("politica_historico"),
        descartar_historico=data.get("descartar_historico"),
        executar_backtest=bool(exec_bt),
        limite_backtest=int(data.get("limite_backtest") or 30),
        checar_memoria_geradores=bool(data.get("checar_memoria_geradores")),
    )
