# -*- coding: utf-8 -*-
"""
Panorama Histórico — memória por concurso.

Nível 1: persiste o que `analisar_concurso_linha` já calcula.
Níveis 2–3: leitura (resumo + listagem) — não altera ABA 4–5.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence


def _model():
    from models.historico_analise_inteligente import HistoricoAnaliseInteligente
    return HistoricoAnaliseInteligente


def _db():
    from models.shared import db
    return db


def linha_para_registro(linha: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza saída de analisar_concurso_linha (+ B/M/A) para upsert."""
    from analise_inteligentes_diadesorte.service import descricao_bma_do_padrao

    pad = str(linha.get("padrao_inicial") or "").strip()
    return {
        "concurso": int(linha["concurso"]),
        "data": str(linha.get("data") or ""),
        "dezenas_fmt": str(linha.get("dezenas_fmt") or ""),
        "dezenas_ordem_caixa_fmt": str(linha.get("dezenas_ordem_caixa_fmt") or ""),
        "padrao_inicial": pad,
        "padrao_final": str(linha.get("padrao_final") or ""),
        "descricao_bma": descricao_bma_do_padrao(pad) if pad else "",
        "soma": int(linha.get("soma") or 0),
        "pares": linha.get("pares"),
        "impares": linha.get("impares"),
        "pares_impares_fmt": str(linha.get("pares_impares_fmt") or ""),
        "digitos_ordenados_fmt": str(linha.get("digitos_ordenados_fmt") or ""),
        "qtd_digitos": linha.get("qtd_digitos"),
        "volume_combinacoes": linha.get("volume_combinacoes"),
        "mes_num": linha.get("mes_num"),
        "mes_nome": str(linha.get("mes_nome") or ""),
        "mes_abrev": str(linha.get("mes_abrev") or ""),
        "atualizado_em": datetime.utcnow(),
    }


def upsert_de_linha(linha: Dict[str, Any], *, commit: bool = False) -> bool:
    """Grava/atualiza um concurso no histórico. Retorna True se ok."""
    if not linha or linha.get("concurso") is None:
        return False
    try:
        Historico = _model()
        db = _db()
        payload = linha_para_registro(linha)
        db.session.merge(Historico(**payload))
        if commit:
            db.session.commit()
        return True
    except Exception:
        try:
            _db().session.rollback()
        except Exception:
            pass
        return False


def upsert_de_sorteio(
    concurso: int,
    data: str,
    dezenas_ordem: Sequence[int],
    mes_num: Optional[int] = None,
    mes_nome: str = "",
    *,
    modality_key: str = "diadesorte",
    commit: bool = False,
) -> bool:
    """Calcula com a análise existente e persiste."""
    try:
        from analise_inteligentes_diadesorte.service import (
            analisar_concurso_linha,
            make_inteligentes_service,
        )
        Svc = make_inteligentes_service(modality_key)
        lim = Svc._limites()
        linha = analisar_concurso_linha(
            concurso=int(concurso),
            data=data or "",
            dezenas_ordem=list(dezenas_ordem),
            mes_num=mes_num,
            mes_nome=mes_nome or "",
            tamanho_jogo=lim["tamanho_jogo"],
            max_dezena=lim["max_dezena"],
            min_dezena=lim["min_dezena"],
            pad=lim["pad"],
        )
        return upsert_de_linha(linha, commit=commit)
    except Exception:
        return False


def upsert_apos_salvar_sorteio(sorteio_row, *, commit: bool = False) -> bool:
    """Hook conveniente após merge de SorteioDiaDeSorte."""
    if sorteio_row is None:
        return False
    try:
        ordem = sorteio_row.dezenas_ordem_lista()
    except Exception:
        ordem = [
            getattr(sorteio_row, f"d{i}", None) for i in range(1, 8)
        ]
        ordem = [int(x) for x in ordem if x is not None]
    if len(ordem) < 7:
        return False
    return upsert_de_sorteio(
        concurso=int(sorteio_row.concurso),
        data=getattr(sorteio_row, "data", "") or "",
        dezenas_ordem=ordem,
        mes_num=getattr(sorteio_row, "mes_num", None),
        mes_nome=getattr(sorteio_row, "mes_nome", "") or "",
        commit=commit,
    )


def status_historico() -> Dict[str, Any]:
    """Contagens para diagnóstico (sem UI)."""
    try:
        from models.sorteio_diadesorte import SorteioDiaDeSorte
        Historico = _model()
        total_sorteios = int(SorteioDiaDeSorte.query.count() or 0)
        total_hist = int(Historico.query.count() or 0)
        ultimo = (
            Historico.query.order_by(Historico.concurso.desc()).first()
        )
        return {
            "sucesso": True,
            "total_sorteios": total_sorteios,
            "total_historico": total_hist,
            "faltantes": max(0, total_sorteios - total_hist),
            "ultimo_concurso": int(ultimo.concurso) if ultimo else None,
            "ultimo_padrao": (ultimo.padrao_inicial if ultimo else None),
            "ultimo_soma": (ultimo.soma if ultimo else None),
            "api": "/analise/api/inteligentes/historico-status",
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def backfill_historico(
    limite: int = 200,
    *,
    modality_key: str = "diadesorte",
    apenas_faltantes: bool = True,
) -> Dict[str, Any]:
    """
    Preenche histórico a partir dos sorteios já no banco.
    Processa em lotes (limite) — chamar de novo até faltantes=0.
    """
    limite = max(1, min(int(limite or 200), 500))
    try:
        from models.sorteio_diadesorte import SorteioDiaDeSorte
        Historico = _model()
        db = _db()

        presentes = {
            int(r[0])
            for r in db.session.query(Historico.concurso).all()
        }
        q = SorteioDiaDeSorte.query.order_by(SorteioDiaDeSorte.concurso.asc())
        rows = q.all()
        if apenas_faltantes:
            candidatos = [r for r in rows if int(r.concurso) not in presentes]
        else:
            candidatos = list(rows)

        lote = candidatos[:limite]
        ok = falhas = 0
        for r in lote:
            if upsert_apos_salvar_sorteio(r, commit=False):
                ok += 1
            else:
                falhas += 1
        db.session.commit()

        st = status_historico()
        restantes = int(st.get("faltantes") or 0)
        return {
            "sucesso": True,
            "processados": len(lote),
            "gravados": ok,
            "falhas": falhas,
            "faltantes_restantes": restantes,
            "continuar": restantes > 0,
            **{k: v for k, v in st.items() if k != "sucesso"},
        }
    except Exception as e:
        try:
            _db().session.rollback()
        except Exception:
            pass
        return {"sucesso": False, "erro": str(e)}


def _row_to_dict(r, *, ultimo_concurso: Optional[int] = None) -> Dict[str, Any]:
    conc = int(r.concurso)
    return {
        "concurso": conc,
        "data": r.data or "",
        "dezenas_fmt": r.dezenas_fmt or "",
        "dezenas_ordem_caixa_fmt": r.dezenas_ordem_caixa_fmt or "",
        "padrao_inicial": r.padrao_inicial or "",
        "padrao_final": r.padrao_final or "",
        "descricao_bma": r.descricao_bma or "",
        "soma": int(r.soma or 0),
        "pares": r.pares,
        "impares": r.impares,
        "pares_impares_fmt": r.pares_impares_fmt or "",
        "digitos_ordenados_fmt": r.digitos_ordenados_fmt or "",
        "qtd_digitos": r.qtd_digitos,
        "volume_combinacoes": r.volume_combinacoes,
        "mes_num": r.mes_num,
        "mes_nome": r.mes_nome or "",
        "mes_abrev": r.mes_abrev or "",
    }


def panorama_resumo() -> Dict[str, Any]:
    """Faixa do Panorama (nível 2): totais, último, mais frequente, mais atrasado."""
    try:
        Historico = _model()
        rows = Historico.query.order_by(Historico.concurso.asc()).all()
        total = len(rows)
        if total == 0:
            return {
                "sucesso": True,
                "total_concursos": 0,
                "padroes_distintos": 0,
                "ultimo": None,
                "mais_frequente": None,
                "mais_atrasado": None,
                "top_frequentes": [],
                "top_atrasados": [],
                "sequencia_recente": [],
                "soma_media": None,
                "api": "/analise/api/inteligentes/panorama",
            }

        ultimo_row = rows[-1]
        ultimo_conc = int(ultimo_row.concurso)
        counts: Counter = Counter()
        last_seen: Dict[str, int] = {}
        bma_counts: Counter = Counter()
        soma_total = 0
        for r in rows:
            pad = (r.padrao_inicial or "").strip()
            if not pad:
                continue
            counts[pad] += 1
            last_seen[pad] = int(r.concurso)
            bma = (r.descricao_bma or "").strip()
            if bma:
                bma_counts[bma] += 1
            soma_total += int(r.soma or 0)

        top_freq = [
            {
                "padrao": pad,
                "frequencia": freq,
                "pct": round(100.0 * freq / total, 1),
                "ultimo_concurso": last_seen.get(pad),
                "atraso": max(0, ultimo_conc - int(last_seen.get(pad) or ultimo_conc)),
            }
            for pad, freq in counts.most_common(5)
        ]
        atrasados = sorted(
            (
                {
                    "padrao": pad,
                    "atraso": max(0, ultimo_conc - int(last_seen[pad])),
                    "frequencia": counts[pad],
                    "ultimo_concurso": last_seen[pad],
                }
                for pad in counts
            ),
            key=lambda x: (-x["atraso"], -x["frequencia"], x["padrao"]),
        )
        top_atras = atrasados[:5]
        sequencia = [
            {
                "concurso": int(r.concurso),
                "padrao": r.padrao_inicial or "",
                "soma": int(r.soma or 0),
                "descricao_bma": r.descricao_bma or "",
                "dezenas_fmt": r.dezenas_fmt or "",
            }
            for r in rows[-10:]
        ]

        return {
            "sucesso": True,
            "total_concursos": total,
            "primeiro_concurso": int(rows[0].concurso),
            "ultimo_concurso": ultimo_conc,
            "padroes_distintos": len(counts),
            "soma_media": round(soma_total / total, 1) if total else None,
            "ultimo": {
                "concurso": ultimo_conc,
                "data": ultimo_row.data or "",
                "dezenas_fmt": ultimo_row.dezenas_fmt or "",
                "padrao_inicial": ultimo_row.padrao_inicial or "",
                "descricao_bma": ultimo_row.descricao_bma or "",
                "soma": int(ultimo_row.soma or 0),
                "pares_impares_fmt": ultimo_row.pares_impares_fmt or "",
            },
            "mais_frequente": top_freq[0] if top_freq else None,
            "mais_atrasado": top_atras[0] if top_atras else None,
            "top_frequentes": top_freq,
            "top_atrasados": top_atras,
            "bma_distribuicao": [
                {"descricao": k, "frequencia": v, "pct": round(100.0 * v / total, 1)}
                for k, v in bma_counts.most_common(8)
            ],
            "sequencia_recente": sequencia,
            "api": "/analise/api/inteligentes/panorama",
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


def listar_historico(
    *,
    offset: int = 0,
    limit: int = 50,
    padrao: str = "",
    busca: str = "",
    ordem: str = "desc",
) -> Dict[str, Any]:
    """Listagem paginada do histórico completo (nível 3)."""
    try:
        Historico = _model()
        offset = max(0, int(offset or 0))
        limit = max(1, min(int(limit or 50), 5000))
        ordem = (ordem or "desc").strip().lower()
        if ordem not in ("asc", "desc"):
            ordem = "desc"

        q = Historico.query
        pad = (padrao or "").strip()
        if pad:
            q = q.filter(Historico.padrao_inicial == pad)
        b = (busca or "").strip()
        if b:
            like = f"%{b}%"
            q = q.filter(
                (Historico.padrao_inicial.like(like))
                | (Historico.descricao_bma.like(like))
                | (Historico.dezenas_fmt.like(like))
                | (Historico.data.like(like))
            )

        total = int(q.count() or 0)
        ultimo_global = Historico.query.order_by(Historico.concurso.desc()).first()
        ultimo_conc = int(ultimo_global.concurso) if ultimo_global else None

        order_col = (
            Historico.concurso.desc() if ordem == "desc" else Historico.concurso.asc()
        )
        rows = q.order_by(order_col).offset(offset).limit(limit).all()
        itens = [_row_to_dict(r) for r in rows]

        last_by_pad: Dict[str, int] = {}
        for r in Historico.query.with_entities(
            Historico.padrao_inicial, Historico.concurso
        ).all():
            p = (r[0] or "").strip()
            c = int(r[1])
            if p and (p not in last_by_pad or c > last_by_pad[p]):
                last_by_pad[p] = c
        for it in itens:
            p = it.get("padrao_inicial") or ""
            last = last_by_pad.get(p)
            it["atraso_padrao"] = (
                max(0, int(ultimo_conc) - int(last))
                if ultimo_conc is not None and last is not None
                else None
            )

        return {
            "sucesso": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "ordem": ordem,
            "itens": itens,
            "api": "/analise/api/inteligentes/historico",
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
