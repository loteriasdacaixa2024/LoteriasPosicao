# -*- coding: utf-8 -*-
"""Melhores grupos no tamanho máximo da aposta — busca local, por modalidade.

O tamanho é o máximo de dezenas que a modalidade permite marcar (Dia de Sorte
15, Mega-Sena 20, Lotofácil 20, e assim por diante). Não enumera as
combinações. Sobe a partir das dezenas mais frequentes e troca uma dezena
por vez enquanto aumentam os concursos com o prêmio inteiro dentro do grupo
(e, no empate, os que ficaram a uma dezena).
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

_GUARD = threading.Lock()
_RODANDO = set()
_FALHA_EM = {}


def _cache_path(modality_key: str) -> str:
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    os.makedirs(pasta, exist_ok=True)
    seguro = "".join(c for c in str(modality_key) if c.isalnum() or c in "-_") or "mod"
    return os.path.join(pasta, f"melhores15_{seguro}.json")


def ler_cache(modality_key: str) -> Optional[Dict[str, Any]]:
    path = _cache_path(modality_key)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _gravar(modality_key: str, payload: Dict[str, Any]) -> None:
    path = _cache_path(modality_key)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    os.replace(tmp, path)


def tamanho_pool(cfg: Dict[str, Any]) -> int:
    """Máximo de dezenas permitido numa aposta desta modalidade."""
    return int(cfg.get("pick_max") or 0)


def elegivel(cfg: Dict[str, Any]) -> bool:
    """O grupo máximo precisa caber o sorteio inteiro e existir no volante."""
    if cfg.get("layout") == "colunas":
        return False
    pool = tamanho_pool(cfg)
    alvo = int(cfg.get("sorteadas") or 0)
    universo = int(cfg.get("dezena_max") or 0) - int(cfg.get("dezena_min") or 0) + 1
    return pool >= 1 and alvo >= 1 and pool >= alvo and universo >= pool


def _bit(n: int) -> int:
    return 1 << int(n)


def _pop(n: int) -> int:
    return n.bit_count() if hasattr(int, "bit_count") else bin(n).count("1")


def _preparar(concursos: Sequence[Dict[str, Any]], dmin: int, dmax: int):
    draws: List[int] = []
    conc_n: List[int] = []
    freq = {n: 0 for n in range(dmin, dmax + 1)}
    for c in concursos:
        nums = []
        mask = 0
        for raw in c.get("dezenas") or []:
            n = int(raw)
            if dmin <= n <= dmax and not (mask & _bit(n)):
                mask |= _bit(n)
                nums.append(n)
                freq[n] += 1
        if nums:
            draws.append(mask)
            conc_n.append(int(c.get("concurso") or 0))
    return draws, conc_n, freq


def _score(mask: int, draws: Sequence[int], alvo: int) -> Tuple[int, int]:
    cheio = quase = 0
    for d in draws:
        c = _pop(d & mask)
        if c == alvo:
            cheio += 1
        elif c == alvo - 1:
            quase += 1
    return cheio, quase


def _escolher(mask: int, nums: Sequence[int], k: int) -> List[int]:
    return [n for n in nums if mask & _bit(n)][:k]


def _subir(mask: int, nums: Sequence[int], draws: Sequence[int], alvo: int, budget: int) -> Tuple[int, Tuple[int, int], int]:
    score = _score(mask, draws, alvo)
    dentro = [n for n in nums if mask & _bit(n)]
    fora = [n for n in nums if not (mask & _bit(n))]
    evals = 1
    melhorou = True
    while melhorou and evals < budget:
        melhorou = False
        random.shuffle(dentro)
        random.shuffle(fora)
        for sai in dentro:
            bit_sai = _bit(sai)
            for entra in fora:
                trial = (mask & ~bit_sai) | _bit(entra)
                sc = _score(trial, draws, alvo)
                evals += 1
                if sc > score:
                    mask, score = trial, sc
                    dentro = [n for n in nums if mask & _bit(n)]
                    fora = [n for n in nums if not (mask & _bit(n))]
                    melhorou = True
                    break
                if evals >= budget:
                    break
            if melhorou or evals >= budget:
                break
    return mask, score, evals


def _greedy(nums: Sequence[int], draws: Sequence[int], alvo: int, freq: Dict[int, int], pool: int) -> int:
    mask = 0
    resto = sorted(nums, key=lambda n: (-freq.get(n, 0), n))
    for _ in range(min(pool, len(resto))):
        melhor_n = None
        melhor_sc = (-1, -1)
        for n in resto:
            if mask & _bit(n):
                continue
            sc = _score(mask | _bit(n), draws, alvo)
            if sc > melhor_sc or (sc == melhor_sc and (melhor_n is None or freq.get(n, 0) > freq.get(melhor_n, 0))):
                melhor_sc = sc
                melhor_n = n
        if melhor_n is None:
            break
        mask |= _bit(melhor_n)
    return mask


def _medir(mask: int, draws: Sequence[int], conc_n: Sequence[int], alvo: int) -> Dict[str, Any]:
    faixas: Dict[int, int] = {}
    soma = 0
    melhores: List[int] = []
    for mask_d, conc in zip(draws, conc_n):
        c = _pop(mask_d & mask)
        faixas[c] = faixas.get(c, 0) + 1
        soma += c
        if c == alvo and conc:
            melhores.append(conc)
    n = len(draws)
    melhores.sort(reverse=True)
    return {
        "faixas": {str(k): v for k, v in sorted(faixas.items())},
        "qtd_alvo": int(faixas.get(alvo, 0)),
        "qtd_quase": int(faixas.get(alvo - 1, 0)),
        "melhor_acerto": max(faixas) if faixas else 0,
        "media": round(soma / n, 2) if n else 0.0,
        "concursos_alvo": melhores[:40],
        "qtd_concursos_alvo": len(melhores),
    }


def _saltar(mask: int, nums: Sequence[int], rng: random.Random) -> int:
    dentro = [n for n in nums if mask & _bit(n)]
    fora = [n for n in nums if not (mask & _bit(n))]
    if len(dentro) < 2 or len(fora) < 2:
        return mask
    for n in rng.sample(dentro, 2):
        mask &= ~_bit(n)
    for n in rng.sample(fora, 2):
        mask |= _bit(n)
    return mask


def buscar(
    concursos: Sequence[Dict[str, Any]],
    dmin: int,
    dmax: int,
    alvo: int,
    pool: int,
    top: int = 8,
) -> List[Dict[str, Any]]:
    draws, conc_n, freq = _preparar(concursos, dmin, dmax)
    nums = list(range(dmin, dmax + 1))
    if len(nums) < pool or not draws or alvo < 1 or pool < 1:
        return []
    vistos: Dict[int, Tuple[int, int]] = {}

    def guardar(mask: int, sc: Tuple[int, int]) -> None:
        if _pop(mask) != pool:
            return
        prev = vistos.get(mask)
        if prev is None or sc > prev:
            vistos[mask] = sc

    base = _greedy(nums, draws, alvo, freq, pool)
    sc = _score(base, draws, alvo)
    guardar(base, sc)
    subiu, sc2, _ = _subir(base, nums, draws, alvo, budget=2500)
    guardar(subiu, sc2)

    ordenados = sorted(nums, key=lambda n: (-freq.get(n, 0), n))
    freq_mask = 0
    for n in ordenados[:pool]:
        freq_mask |= _bit(n)
    guardar(freq_mask, _score(freq_mask, draws, alvo))
    freq_sub, freq_sc, _ = _subir(freq_mask, nums, draws, alvo, budget=1200)
    guardar(freq_sub, freq_sc)

    rng = random.Random(alvo * 1000 + len(draws) + pool)
    melhor = subiu if sc2 >= sc else base
    for _ in range(10):
        amostra = rng.sample(nums, pool)
        mask = 0
        for n in amostra:
            mask |= _bit(n)
        mask2, sc3, _ = _subir(mask, nums, draws, alvo, budget=900)
        guardar(mask2, sc3)
        if sc3 > vistos.get(melhor, (-1, -1)):
            melhor = mask2
    for _ in range(6):
        mask = _saltar(melhor, nums, rng)
        mask2, sc3, _ = _subir(mask, nums, draws, alvo, budget=900)
        guardar(mask2, sc3)
        if sc3 > vistos.get(melhor, (-1, -1)):
            melhor = mask2

    rankeados = sorted(vistos.items(), key=lambda item: (-item[1][0], -item[1][1], item[0]))[:top]
    saida = []
    for i, (mask, _) in enumerate(rankeados, 1):
        dez = sorted(_escolher(mask, nums, pool))
        med = _medir(mask, draws, conc_n, alvo)
        saida.append({
            "posicao": i,
            "dezenas": dez,
            "referencia": False,
            **med,
        })
    return saida


def _ultimo_concurso(modality_key: str) -> int:
    from .compare_service import CompararConcursosService

    svc = CompararConcursosService(modality_key)
    hist = svc.historico_indicados(limit=1)
    concursos = hist.get("concursos") or []
    if not concursos:
        return 0
    return int(concursos[0].get("concurso") or 0)


def calcular_e_salvar(modality_key: str) -> Dict[str, Any]:
    from .compare_config import get_compare_config
    from .compare_service import CompararConcursosService

    cfg = get_compare_config(modality_key)
    pool = tamanho_pool(cfg)
    if not elegivel(cfg):
        return {"sucesso": False, "erro": "Esta modalidade não entra neste rastreio."}
    dmin = int(cfg["dezena_min"])
    dmax = int(cfg["dezena_max"])
    alvo = int(cfg.get("sorteadas") or 0) or 7
    if dmax - dmin + 1 < pool:
        return {"sucesso": False, "erro": "Universo menor que %s dezenas." % pool}
    svc = CompararConcursosService(modality_key)
    hist = svc.historico_indicados(limit=0)
    concursos = hist.get("concursos") or []
    if not concursos:
        return {"sucesso": False, "erro": "Sem concursos no histórico."}
    concurso_ate = max(int(c.get("concurso") or 0) for c in concursos)
    ranking = buscar(concursos, dmin, dmax, alvo, pool)
    payload = {
        "sucesso": True,
        "modality": modality_key,
        "concurso_ate": concurso_ate,
        "alvo": alvo,
        "pool_size": pool,
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "concursos_testados": len(concursos),
        "ranking": ranking,
    }
    _gravar(modality_key, payload)
    return payload


def em_andamento(modality_key: str) -> bool:
    with _GUARD:
        return modality_key in _RODANDO


def agendar_melhores15(modality_key: str, app=None) -> bool:
    """Dispara a busca em segundo plano. Uma por modalidade."""
    try:
        from .compare_config import get_compare_config
        if not elegivel(get_compare_config(modality_key)):
            return False
    except Exception:
        return False
    if app is None:
        try:
            from flask import current_app
            app = current_app._get_current_object()
        except Exception:
            return False
    with _GUARD:
        if modality_key in _RODANDO:
            return False
        _RODANDO.add(modality_key)

    def _job():
        try:
            with app.app_context():
                out = calcular_e_salvar(modality_key)
            if not out.get("sucesso"):
                with _GUARD:
                    _FALHA_EM[modality_key] = time.time()
        except Exception:
            with _GUARD:
                _FALHA_EM[modality_key] = time.time()
            try:
                app.logger.exception("[melhores15] falha ao calcular %s", modality_key)
            except Exception:
                pass
        finally:
            with _GUARD:
                _RODANDO.discard(modality_key)

    threading.Thread(target=_job, daemon=True, name=f"melhores15-{modality_key}").start()
    return True


def consultar(modality_key: str) -> Dict[str, Any]:
    atual = 0
    pool = 0
    try:
        from .compare_config import get_compare_config
        cfg = get_compare_config(modality_key)
        pool = tamanho_pool(cfg)
        if not elegivel(cfg):
            return {
                "sucesso": True,
                "pronto": False,
                "atualizando": False,
                "concurso_ate": 0,
                "concurso_atual": 0,
                "alvo": int(cfg.get("sorteadas") or 0),
                "pool_size": pool,
                "gerado_em": "",
                "concursos_testados": 0,
                "ranking": [],
            }
    except Exception:
        pool = 0
    try:
        atual = _ultimo_concurso(modality_key)
    except Exception:
        atual = 0
    cache = ler_cache(modality_key) or {}
    ate = int(cache.get("concurso_ate") or 0)
    cache_pool = int(cache.get("pool_size") or 15)
    pool_errado = pool > 0 and bool(cache.get("ranking")) and cache_pool != pool
    desatualizado = atual > 0 and ate < atual
    rodando = em_andamento(modality_key)
    precisa = pool_errado or desatualizado or (atual > 0 and not cache.get("ranking"))
    if precisa and not rodando:
        recente = time.time() - _FALHA_EM.get(modality_key, 0) < 45
        if not recente:
            agendar_melhores15(modality_key)
            rodando = True
    ranking = [] if pool_errado else (cache.get("ranking") or [])
    return {
        "sucesso": True,
        "pronto": bool(ranking),
        "atualizando": bool(precisa or rodando),
        "concurso_ate": 0 if pool_errado else ate,
        "concurso_atual": atual,
        "alvo": cache.get("alvo"),
        "pool_size": pool or cache_pool,
        "gerado_em": "" if pool_errado else (cache.get("gerado_em") or ""),
        "concursos_testados": 0 if pool_errado else (cache.get("concursos_testados") or 0),
        "ranking": ranking,
    }
