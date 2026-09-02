# -*- coding: utf-8 -*-
"""
Validador global dos Geradores de Elite.

Camada ADICIONAL pós-geração — não altera algoritmos dos geradores.
Valida:
  1) combinação já sorteada no histórico oficial;
  2) duplicata interna no lote (ordem irrelevante);
  3) combinação já liberada por outro gerador (memória compartilhada).

Uso típico (após o gerador montar a lista):

    from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
    resultado = ValidadorGeradoresElite.aplicar(resultado, origem="sniper", modality_key="diadesorte")
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Type

from geradores_elite.validacao.apostas_ineditas import (
    aposta_ja_sorteada,
    carregar_combinacoes_historicas,
)

_LOCK = threading.RLock()
_HIST_CACHE: Dict[str, Set[frozenset]] = {}
_MEMORIA: Dict[str, Set[frozenset]] = {}  # modality -> combinações já liberadas por geradores

# Mapa modality_key → (module, class) do modelo de sorteio
_MODELOS = {
    "diadesorte": ("models.sorteio_diadesorte", "SorteioDiaDeSorte"),
    "megasena": ("models.sorteio_megasena", "SorteioMegaSena"),
    "quina": ("models.sorteio_quina", "SorteioQuina"),
    "lotofacil": ("models.sorteio_lotofacil", "SorteioLotofacil"),
    "lotomania": ("models.sorteio_lotomania", "SorteioLotomania"),
    "timemania": ("models.sorteio_timemania", "SorteioTimemania"),
    "duplasena": ("models.sorteio_duplasena", "SorteioDuplaSena"),
    "maismilionaria": ("models.sorteio_maismilionaria", "SorteioMaisMilionaria"),
}


def dezenas_padrao_sorteio(sorteio: Any) -> List[int]:
    """Extrator genérico de dezenas de um registro de sorteio."""
    if sorteio is None:
        return []
    if hasattr(sorteio, "dezenas_ordem_lista"):
        try:
            return [int(x) for x in sorteio.dezenas_ordem_lista()]
        except Exception:
            pass
    if hasattr(sorteio, "dezenas_lista"):
        try:
            return [int(x) for x in sorteio.dezenas_lista()]
        except Exception:
            pass
    if hasattr(sorteio, "dezenas") and callable(sorteio.dezenas):
        try:
            dz = sorteio.dezenas()
            if isinstance(dz, (set, frozenset)):
                return sorted(int(x) for x in dz)
            return [int(x) for x in dz]
        except Exception:
            pass
    return []


def _load_model(modality_key: str) -> Optional[Type[Any]]:
    key = (modality_key or "").strip().lower()
    tip = _MODELOS.get(key)
    if not tip:
        return None
    mod_name, cls_name = tip
    try:
        mod = __import__(mod_name, fromlist=[cls_name])
        return getattr(mod, cls_name)
    except Exception:
        return None


def _normalizar_chave(dezenas: Sequence[int]) -> frozenset:
    return frozenset(int(d) for d in dezenas)


def _extrair_dezenas(item: Any, campo: str = "dezenas") -> Optional[List[int]]:
    if item is None:
        return None
    if isinstance(item, (list, tuple)) and item and not isinstance(item[0], dict):
        try:
            return [int(x) for x in item]
        except Exception:
            return None
    if isinstance(item, dict):
        for key in (campo, "dezenas", "dezenas_ordem", "nums", "numeros"):
            if key in item and item[key] is not None:
                try:
                    return [int(x) for x in item[key]]
                except Exception:
                    return None
    return None


def _memoria_path(modality_key: str) -> Path:
    base = Path(tempfile.gettempdir()) / "loterias_geradores_elite"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"memoria_{modality_key}.json"


def _log_path(modality_key: str) -> Path:
    base = Path(tempfile.gettempdir()) / "loterias_geradores_elite"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"auditoria_{modality_key}.jsonl"


def _carregar_memoria_disco(modality_key: str) -> Set[frozenset]:
    path = _memoria_path(modality_key)
    if not path.exists():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        out: Set[frozenset] = set()
        for item in raw.get("combinacoes") or []:
            out.add(frozenset(int(x) for x in item))
        return out
    except Exception:
        return set()


def _salvar_memoria_disco(modality_key: str, memoria: Set[frozenset]) -> None:
    path = _memoria_path(modality_key)
    payload = {
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "qtd": len(memoria),
        "combinacoes": [sorted(c) for c in memoria],
    }
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _append_log(modality_key: str, registro: Dict[str, Any]) -> None:
    path = _log_path(modality_key)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception:
        pass


class ValidadorGeradoresElite:
    """Serviço central de auditoria pós-geração dos Geradores de Elite."""

    @classmethod
    def limpar_memoria(cls, modality_key: str = "diadesorte") -> None:
        with _LOCK:
            _MEMORIA[modality_key] = set()
            _salvar_memoria_disco(modality_key, set())

    @classmethod
    def _memoria(cls, modality_key: str) -> Set[frozenset]:
        with _LOCK:
            if modality_key not in _MEMORIA:
                _MEMORIA[modality_key] = _carregar_memoria_disco(modality_key)
            return _MEMORIA[modality_key]

    @classmethod
    def _historico(
        cls,
        modality_key: str,
        sorteio_model: Optional[Type[Any]] = None,
        dezenas_fn: Optional[Callable[[Any], List[int]]] = None,
    ) -> Set[frozenset]:
        with _LOCK:
            if modality_key in _HIST_CACHE:
                return _HIST_CACHE[modality_key]
        model = sorteio_model or _load_model(modality_key)
        if model is None:
            return set()
        fn = dezenas_fn or dezenas_padrao_sorteio
        try:
            hist = carregar_combinacoes_historicas(model, fn)
        except Exception:
            hist = set()
        with _LOCK:
            _HIST_CACHE[modality_key] = hist
        return hist

    @classmethod
    def invalidar_cache_historico(cls, modality_key: Optional[str] = None) -> None:
        with _LOCK:
            if modality_key:
                _HIST_CACHE.pop(modality_key, None)
            else:
                _HIST_CACHE.clear()

    @classmethod
    def validar_lote(
        cls,
        itens: Sequence[Any],
        *,
        origem: str,
        modality_key: str = "diadesorte",
        campo_dezenas: str = "dezenas",
        sorteio_model: Optional[Type[Any]] = None,
        dezenas_fn: Optional[Callable[[Any], List[int]]] = None,
        registrar_aprovadas: bool = True,
        checar_historico: bool = True,
        checar_memoria: bool = True,
    ) -> Dict[str, Any]:
        """
        Filtra o lote gerado. Não altera a forma dos itens aprovados.

        Retorna:
          aprovados, rejeitadas[{item, motivo, chave}], stats, log
        """
        historico = cls._historico(modality_key, sorteio_model, dezenas_fn) if checar_historico else set()
        memoria = cls._memoria(modality_key) if checar_memoria else set()

        aprovados: List[Any] = []
        rejeitadas: List[Dict[str, Any]] = []
        vistos_lote: Set[frozenset] = set()
        agora = datetime.now().isoformat(timespec="seconds")

        for item in itens:
            dz = _extrair_dezenas(item, campo_dezenas)
            if not dz:
                rejeitadas.append({
                    "item": item,
                    "motivo": "Rejeitada — dezenas inválidas/ausentes",
                    "chave": None,
                })
                continue
            chave = _normalizar_chave(dz)
            if chave in vistos_lote:
                rejeitadas.append({
                    "item": item,
                    "motivo": "Rejeitada — duplicada no mesmo lote (ordem irrelevante)",
                    "chave": sorted(chave),
                })
                continue
            if checar_historico and aposta_ja_sorteada(dz, historico):
                rejeitadas.append({
                    "item": item,
                    "motivo": "Rejeitada — combinação já sorteada anteriormente",
                    "chave": sorted(chave),
                })
                continue
            if checar_memoria and chave in memoria:
                rejeitadas.append({
                    "item": item,
                    "motivo": "Rejeitada — sequência já utilizada por outro gerador",
                    "chave": sorted(chave),
                })
                continue
            vistos_lote.add(chave)
            aprovados.append(item)

        if registrar_aprovadas and aprovados:
            with _LOCK:
                mem = cls._memoria(modality_key)
                for item in aprovados:
                    dz = _extrair_dezenas(item, campo_dezenas)
                    if dz:
                        mem.add(_normalizar_chave(dz))
                _salvar_memoria_disco(modality_key, mem)

        stats = {
            "analisadas": len(itens),
            "aprovadas": len(aprovados),
            "rejeitadas": len(rejeitadas),
            "origem": origem,
            "modality_key": modality_key,
            "data_hora": agora,
        }
        log = {
            **stats,
            "motivos": [r["motivo"] for r in rejeitadas],
            "detalhes_rejeicao": [
                {"motivo": r["motivo"], "dezenas": r.get("chave")}
                for r in rejeitadas
            ],
        }
        _append_log(modality_key, log)

        return {
            "aprovados": aprovados,
            "rejeitadas": rejeitadas,
            "stats": stats,
            "log": log,
        }

    @classmethod
    def aplicar(
        cls,
        resultado: Dict[str, Any],
        *,
        origem: str,
        modality_key: str = "diadesorte",
        campo: Optional[str] = None,
        campo_dezenas: str = "dezenas",
        sorteio_model: Optional[Type[Any]] = None,
        dezenas_fn: Optional[Callable[[Any], List[int]]] = None,
        renumerar: bool = True,
        checar_historico: bool = True,
        checar_memoria: bool = True,
        registrar_aprovadas: bool = True,
    ) -> Dict[str, Any]:
        """
        Aplica validação sobre um dict de resposta típico dos geradores.
        Detecta automaticamente a chave da lista: apostas | jogos | apostas_com_mes.
        """
        if not isinstance(resultado, dict) or not resultado.get("sucesso"):
            return resultado

        chave_lista = campo
        if not chave_lista:
            for cand in ("apostas", "jogos", "apostas_com_mes"):
                if isinstance(resultado.get(cand), list):
                    chave_lista = cand
                    break
        if not chave_lista or not isinstance(resultado.get(chave_lista), list):
            return resultado

        itens = list(resultado[chave_lista])
        campo_dz = campo_dezenas

        out = cls.validar_lote(
            itens,
            origem=origem,
            modality_key=modality_key,
            campo_dezenas=campo_dz,
            sorteio_model=sorteio_model,
            dezenas_fn=dezenas_fn,
            registrar_aprovadas=registrar_aprovadas,
            checar_historico=checar_historico,
            checar_memoria=checar_memoria,
        )
        aprovados = out["aprovados"]
        if renumerar:
            for i, item in enumerate(aprovados, 1):
                if isinstance(item, dict):
                    if "numero" in item:
                        item["numero"] = i
                    if "id" in item:
                        item["id"] = i
                    if "linha" in item:
                        item["linha"] = i

        resultado[chave_lista] = aprovados
        if "quantidade" in resultado:
            resultado["quantidade"] = len(aprovados)
        if "qtd_gerados" in resultado:
            resultado["qtd_gerados"] = len(aprovados)
        if "total_geradas" in resultado:
            resultado["total_geradas"] = len(aprovados)

        resultado["validacao_global"] = {
            **out["stats"],
            "rejeitadas_detalhe": out["log"].get("detalhes_rejeicao") or [],
        }
        if out["stats"]["rejeitadas"]:
            aviso_extra = (
                f"Validação global: {out['stats']['rejeitadas']} rejeitada(s) "
                f"de {out['stats']['analisadas']} analisada(s)."
            )
            if resultado.get("aviso"):
                resultado["aviso"] = f"{resultado['aviso']} {aviso_extra}"
            else:
                resultado["aviso"] = aviso_extra
        return resultado

    @classmethod
    def aplicar_em_listas(
        cls,
        listas: Dict[str, List[Any]],
        *,
        origem: str,
        modality_key: str = "diadesorte",
        campo_dezenas: str = "dezenas",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Valida a lista principal e espelha o filtro nas listas paralelas
        (ex.: apostas + apostas_com_mes) pelo índice / chave frozenset.
        """
        if not listas:
            return {"listas": listas, "stats": {}}
        principal_key = next(iter(listas.keys()))
        principal = listas[principal_key]
        out = cls.validar_lote(
            principal,
            origem=origem,
            modality_key=modality_key,
            campo_dezenas=campo_dezenas,
            **kwargs,
        )
        aprov_chaves = set()
        for item in out["aprovados"]:
            dz = _extrair_dezenas(item, campo_dezenas)
            if dz:
                aprov_chaves.add(_normalizar_chave(dz))

        novas: Dict[str, List[Any]] = {principal_key: out["aprovados"]}
        for k, lst in listas.items():
            if k == principal_key:
                continue
            filtrada = []
            for item in lst:
                dz = _extrair_dezenas(item, campo_dezenas)
                if dz and _normalizar_chave(dz) in aprov_chaves:
                    filtrada.append(item)
                elif isinstance(item, (list, tuple)):
                    try:
                        if _normalizar_chave(item) in aprov_chaves:
                            filtrada.append(item)
                    except Exception:
                        pass
            novas[k] = filtrada
        return {"listas": novas, "stats": out["stats"], "rejeitadas": out["rejeitadas"]}
