# -*- coding: utf-8 -*-
"""Lista os concursos para os cartões e para as dezenas deslocadas."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Tuple

from models.shared import db

_DIAS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
_BACKFILL_LOCK = threading.Lock()
_BACKFILL_RODANDO = False


def _data_parts(valor: Any) -> Tuple[str, str]:
    bruto = str(valor or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(bruto[:10], fmt)
        except ValueError:
            continue
        return dt.strftime("%d/%m/%Y"), _DIAS[dt.weekday()]
    return bruto, ""


def _reais(valor: Any) -> str:
    try:
        n = float(valor or 0)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    txt = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


def _rateios(modality_key: str) -> Dict[int, float]:
    if modality_key != "diadesorte":
        return {}
    try:
        from models.caixa_excel_premiacao import CaixaExcelPremiacaoDiaDeSorte
    except Exception:
        return {}
    out: Dict[int, float] = {}
    try:
        rows = db.session.query(CaixaExcelPremiacaoDiaDeSorte).all()
    except Exception:
        db.session.rollback()
        return {}
    for row in rows:
        try:
            out[int(row.concurso)] = float(row.rateio_7 or 0)
        except (TypeError, ValueError):
            continue
    return out


def listar_resultados(modality_key: str) -> Dict[str, Any]:
    from analise_estudos.base_service import AnaliseEstudosBase
    from analise_estudos.specs import get_estudos_config

    cfg = get_estudos_config(modality_key)

    class _Base(AnaliseEstudosBase):
        pass

    _Base.modality_key = modality_key
    rows = _Base.carregar_sorteios_asc("geral", 0)
    premios = _rateios(modality_key)
    campo_g = cfg.get("ganhadores_field") or ""
    posicional = modality_key == "supersete"
    caixa_mapa = {} if modality_key == "diadesorte" else _mapa_caixa()
    linhas: List[Dict[str, Any]] = []
    for row in rows:
        nums = [int(n) for n in _Base.dezenas_ordem(row)]
        if not posicional:
            nums = sorted(nums)
        data, dia = _data_parts(getattr(row, "data", ""))
        g = getattr(row, campo_g, None) if campo_g else None
        try:
            ganhadores = None if g is None else int(g)
        except (TypeError, ValueError):
            ganhadores = None
        concurso = int(row.concurso)
        mes_num = getattr(row, "mes_num", None)
        caixa = caixa_mapa.get(concurso)
        if caixa is not None:
            data_prox, dia_prox = _data_parts(caixa["data_proximo"] or "")
            estimativa_fmt = _reais(caixa["estimativa"])
            if caixa["ganhadores"] is not None:
                ganhadores = int(caixa["ganhadores"])
            premio_txt = _reais(caixa["premio"])
        else:
            data_prox, dia_prox = _data_parts(getattr(row, "data_proximo", "") or "")
            estimativa_fmt = _reais(getattr(row, "estimativa_proximo", None))
            premio_txt = _reais(premios.get(concurso))
        segundo = []
        if hasattr(row, "sorteio2_lista"):
            segundo = sorted(int(n) for n in row.sorteio2_lista())
        extra = ""
        if hasattr(row, "trevos_lista"):
            trevos = [int(n) for n in row.trevos_lista()]
            if trevos:
                extra = "Trevos " + " ".join(f"{n:02d}" for n in sorted(trevos))
        elif getattr(row, "time_nome", None):
            extra = str(row.time_nome)
        linhas.append({
            "concurso": concurso,
            "data": data,
            "dia": dia,
            "dezenas": nums,
            "segundo": segundo,
            "extra": extra,
            "mes_num": int(mes_num) if mes_num else None,
            "mes_nome": getattr(row, "mes_nome", "") or "" if cfg.get("extra_mes") else "",
            "ganhadores_7": ganhadores,
            "premio": premio_txt,
            "estimativa_fmt": estimativa_fmt,
            "data_proximo": data_prox,
            "dia_proximo": dia_prox,
        })
    linhas.sort(key=lambda item: item["concurso"], reverse=True)
    por_concurso = {item["concurso"]: item for item in linhas}
    ultimo = linhas[0]["concurso"] if linhas else None
    for item in linhas:
        seguinte = por_concurso.get(item["concurso"] + 1)
        estimado = item.get("estimativa_fmt") or ""
        if seguinte:
            item["proximo"] = {
                "concurso": seguinte["concurso"],
                "data": seguinte["data"] or item.get("data_proximo") or "",
                "dia": seguinte["dia"] or item.get("dia_proximo") or "",
                "sorteado": True,
                "estimado": estimado,
            }
        elif ultimo is not None and item["concurso"] == ultimo:
            data_prox = item.get("data_proximo") or ""
            item["proximo"] = {
                "concurso": item["concurso"] + 1,
                "data": data_prox,
                "dia": item.get("dia_proximo") or "",
                "sorteado": bool(data_prox),
                "estimado": estimado,
            }
        else:
            item["proximo"] = None
    return {
        "sucesso": True,
        "total": len(linhas),
        "ultimo": ultimo,
        "dezena_min": int(cfg.get("dezena_min") or 1),
        "dezena_max": int(cfg.get("dezena_max") or 31),
        "sorteadas": int(cfg.get("sorteadas") or 6),
        "tem_mes": bool(cfg.get("extra_mes")),
        "posicional": posicional,
        "pad": 1 if int(cfg.get("dezena_max") or 31) < 10 else 2,
        "linhas": linhas,
    }


_SLUG_CAIXA = {
    "diadesorte": "diadesorte",
    "megasena": "megasena",
    "quina": "quina",
    "lotofacil": "lotofacil",
    "lotomania": "lotomania",
    "duplasena": "duplasena",
    "maismilionaria": "maismilionaria",
    "timemania": "timemania",
    "supersete": "supersete",
}


def _ensure_caixa() -> None:
    db.session.execute(db.text(
        """
        CREATE TABLE IF NOT EXISTS resultado_caixa (
            concurso INTEGER PRIMARY KEY,
            estimativa_proximo FLOAT,
            data_proximo VARCHAR(20),
            ganhadores INTEGER,
            premio FLOAT
        )
        """
    ))
    db.session.commit()


def _mapa_caixa() -> Dict[int, Dict[str, Any]]:
    _ensure_caixa()
    linhas = db.session.execute(db.text(
        "SELECT concurso, estimativa_proximo, data_proximo, ganhadores, premio FROM resultado_caixa"
    )).fetchall()
    out: Dict[int, Dict[str, Any]] = {}
    for concurso, estimativa, data, ganhadores, premio in linhas:
        out[int(concurso)] = {
            "estimativa": estimativa,
            "data_proximo": data or "",
            "ganhadores": ganhadores,
            "premio": premio,
        }
    return out


def _buscar_proximo_caixa(item):
    numero, slug = item
    import certifi
    import requests

    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}/{int(numero)}"
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        try:
            resp = requests.get(url, headers=headers, timeout=25, verify=certifi.where())
        except requests.exceptions.SSLError:
            resp = requests.get(url, headers=headers, timeout=25, verify=False)
    except Exception:
        return int(numero), None, "", None, None, False
    if resp.status_code != 200:
        return int(numero), None, "", None, None, False
    try:
        dados = resp.json()
    except Exception:
        return int(numero), None, "", None, None, False
    bruto = dados.get("valorEstimadoProximoConcurso")
    try:
        estimativa = 0.0 if bruto is None or bruto == "" else float(bruto)
    except (TypeError, ValueError):
        estimativa = 0.0
    data = str(dados.get("dataProximoConcurso") or "").strip()
    ganhadores = None
    premio = None
    faixa = (dados.get("listaRateioPremio") or [None])[0]
    if isinstance(faixa, dict):
        try:
            ganhadores = int(faixa.get("numeroDeGanhadores"))
        except (TypeError, ValueError):
            ganhadores = None
        try:
            premio = float(faixa.get("valorPremio") or 0)
        except (TypeError, ValueError):
            premio = None
    return int(numero), estimativa, data, ganhadores, premio, True


def _preencher_diadesorte(limite: int) -> int:
    from models.sorteio_diadesorte import SorteioDiaDeSorte

    rows = (
        db.session.query(SorteioDiaDeSorte)
        .filter(SorteioDiaDeSorte.estimativa_proximo.is_(None))
        .order_by(SorteioDiaDeSorte.concurso.desc())
        .limit(limite)
        .all()
    )
    if not rows:
        return 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        achados = list(pool.map(
            _buscar_proximo_caixa,
            [(int(row.concurso), "diadesorte") for row in rows],
        ))
    por_id = {int(row.concurso): row for row in rows}
    gravados = 0
    for concurso, estimativa, data, _ganhadores, _premio, ok in achados:
        if not ok:
            continue
        row = por_id.get(concurso)
        if row is None:
            continue
        row.estimativa_proximo = estimativa
        row.data_proximo = data or ""
        gravados += 1
    if gravados:
        db.session.commit()
    return gravados


def _preencher_tabela(modality_key: str, limite: int) -> int:
    from analise_estudos.base_service import AnaliseEstudosBase

    slug = _SLUG_CAIXA.get(modality_key)
    if not slug:
        return 0
    _ensure_caixa()

    class _Base(AnaliseEstudosBase):
        pass

    _Base.modality_key = modality_key
    Model = _Base._model()
    ja = {
        int(r[0])
        for r in db.session.execute(db.text("SELECT concurso FROM resultado_caixa")).fetchall()
    }
    ids = [
        int(row.concurso)
        for row in db.session.query(Model).order_by(Model.concurso.desc()).all()
        if int(row.concurso) not in ja
    ][:limite]
    if not ids:
        return 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        achados = list(pool.map(_buscar_proximo_caixa, [(n, slug) for n in ids]))
    gravados = 0
    for concurso, estimativa, data, ganhadores, premio, ok in achados:
        if not ok:
            continue
        db.session.execute(db.text(
            """
            INSERT INTO resultado_caixa
                (concurso, estimativa_proximo, data_proximo, ganhadores, premio)
            VALUES (:concurso, :estimativa, :data, :ganhadores, :premio)
            """
        ), {
            "concurso": concurso,
            "estimativa": estimativa,
            "data": data or "",
            "ganhadores": ganhadores,
            "premio": premio,
        })
        gravados += 1
    if gravados:
        db.session.commit()
    return gravados


def preencher_estimativas(modality_key: str, limite: int) -> int:
    """Grava a estimativa da Caixa nos concursos que ainda não têm."""
    limite = max(1, int(limite))
    if modality_key == "diadesorte":
        return _preencher_diadesorte(limite)
    return _preencher_tabela(modality_key, limite)


def _faltam_estimativas(modality_key: str) -> int:
    if modality_key == "diadesorte":
        from models.sorteio_diadesorte import SorteioDiaDeSorte
        return (
            db.session.query(SorteioDiaDeSorte)
            .filter(SorteioDiaDeSorte.estimativa_proximo.is_(None))
            .count()
        )
    from analise_estudos.base_service import AnaliseEstudosBase

    class _Base(AnaliseEstudosBase):
        pass

    _Base.modality_key = modality_key
    Model = _Base._model()
    total = db.session.query(Model).count()
    _ensure_caixa()
    gravados = db.session.execute(db.text("SELECT COUNT(*) FROM resultado_caixa")).scalar() or 0
    return max(0, int(total) - int(gravados))


def _backfill_restante(app, modality_key: str) -> None:
    global _BACKFILL_RODANDO
    try:
        with app.app_context():
            while preencher_estimativas(modality_key, 40):
                pass
    except Exception:
        db.session.rollback()
    finally:
        with _BACKFILL_LOCK:
            _BACKFILL_RODANDO = False


def garantir_estimativas(app, modality_key: str, imediato: int = 24) -> None:
    """Preenche a primeira leva na hora e segue o restante em segundo plano."""
    global _BACKFILL_RODANDO
    try:
        preencher_estimativas(modality_key, imediato)
    except Exception:
        db.session.rollback()
    try:
        faltam = _faltam_estimativas(modality_key)
    except Exception:
        db.session.rollback()
        return
    if not faltam:
        return
    with _BACKFILL_LOCK:
        if _BACKFILL_RODANDO:
            return
        _BACKFILL_RODANDO = True
    threading.Thread(
        target=_backfill_restante,
        args=(app, modality_key),
        daemon=True,
    ).start()
