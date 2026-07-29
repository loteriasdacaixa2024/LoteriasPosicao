"""Factory para serviço de desdobramento (dezenas 1-50/60 e trevos +Milionária)."""
import os
import sys
from datetime import datetime
from itertools import combinations
from typing import Any, Dict, List, Optional

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)

from _shared.desdobramento_fechamento import (
    final_coluna,
    gerar_fechamento,
    gerar_fechamento_trevos,
)


def build_desdobramento_service(
    analise_service_class,
    max_dezena: int = 60,
    suporta_trevo: bool = False,
    dezena_min: int = 1,
):
    from models.desdobramento import ApostaDesdobramento, Desdobramento, GrupoDesdobramento
    from models.shared import db

    class DesdobramentoService:
        MAX_DEZENA = max_dezena
        DEZENA_MIN = dezena_min

        @classmethod
        def gerar_fechamento(cls, numeros, modo="bronze"):
            return gerar_fechamento(numeros, modo)

        @classmethod
        def gerar_fechamento_trevos(cls, trevos):
            if not suporta_trevo:
                raise ValueError("Trevos não suportados nesta modalidade.")
            return gerar_fechamento_trevos(trevos)

        @staticmethod
        def _persistir(nome, resultado, tipo="dezenas"):
            desd = Desdobramento(
                nome=nome,
                data_criacao=datetime.now().isoformat(),
                numeros=",".join(map(str, resultado["numeros"])),
                total_apostas=resultado["total_apostas"],
                modo=resultado.get("modo", "bronze"),
                tipo=tipo,
            )
            db.session.add(desd)
            db.session.flush()
            for idx, gp in enumerate(resultado.get("grupos", []), 1):
                db.session.add(
                    GrupoDesdobramento(
                        desdobramento_id=desd.id,
                        grupo_numero=idx,
                        numeros=",".join(map(str, gp)),
                    )
                )
            for idx, ap in enumerate(resultado["apostas"]):
                db.session.add(
                    ApostaDesdobramento(
                        desdobramento_id=desd.id,
                        linha=(idx // 4) + 1,
                        aposta_numero=(idx % 4) + 1,
                        dezenas=",".join(map(str, ap)),
                    )
                )
            db.session.commit()
            return desd.id

        @classmethod
        def salvar_desdobramento(cls, nome, numeros, modo="bronze"):
            return cls._persistir(nome, cls.gerar_fechamento(numeros, modo), "dezenas")

        @classmethod
        def salvar_desdobramento_trevos(cls, nome, trevos):
            return cls._persistir(nome, cls.gerar_fechamento_trevos(trevos), "trevo")

        @staticmethod
        def listar_todos(tipo=None):
            q = db.session.query(Desdobramento).order_by(Desdobramento.data_criacao.desc())
            if tipo:
                q = q.filter(Desdobramento.tipo == tipo)
            return [
                {
                    "id": d.id,
                    "nome": d.nome,
                    "data_criacao": d.data_criacao,
                    "numeros": d.numeros,
                    "total_apostas": d.total_apostas,
                    "modo": d.modo,
                    "tipo": getattr(d, "tipo", "dezenas"),
                }
                for d in q.all()
            ]

        @staticmethod
        def buscar_por_id(id_):
            d = db.session.query(Desdobramento).filter(Desdobramento.id == id_).first()
            if not d:
                return None
            grupos_db = (
                db.session.query(GrupoDesdobramento)
                .filter(GrupoDesdobramento.desdobramento_id == id_)
                .order_by(GrupoDesdobramento.grupo_numero)
                .all()
            )
            grupos = [[int(x) for x in g.numeros.split(",")] for g in grupos_db]
            apostas_db = (
                db.session.query(ApostaDesdobramento)
                .filter(ApostaDesdobramento.desdobramento_id == id_)
                .order_by(ApostaDesdobramento.id)
                .all()
            )
            apostas = [[int(x) for x in a.dezenas.split(",")] for a in apostas_db]
            pares = [[list(p) for p in combinations(gp, 2)] for gp in grupos] if grupos else []
            return {
                "id": d.id,
                "nome": d.nome,
                "data_criacao": d.data_criacao,
                "numeros": d.numeros,
                "total_apostas": d.total_apostas,
                "modo": d.modo,
                "tipo": getattr(d, "tipo", "dezenas"),
                "grupos": grupos,
                "pares": pares,
                "apostas": apostas,
            }

        @staticmethod
        def deletar_por_id(id_):
            d = db.session.query(Desdobramento).filter(Desdobramento.id == id_).first()
            if not d:
                return False
            db.session.delete(d)
            db.session.commit()
            return True

        @staticmethod
        def obter_sugestoes_colunas():
            dados = analise_service_class.analise_geral()
            lo = dezena_min
            hi = max_dezena
            if not dados or "dados" not in dados:
                fb = list(range(lo, min(lo + 16, hi + 1)))
                return {
                    "quentes": {"colunas": [1, 2, 3, 4], "dezenas": fb},
                    "atrasadas": {"colunas": [5, 6, 7, 8], "dezenas": fb},
                    "balanceadas": {"colunas": [1, 2, 5, 6], "dezenas": fb},
                }
            stats = {d["dezena"]: d for d in dados["dados"]}

            def col_stats():
                cols = []
                for c in range(1, 11):
                    dezs = [d for d in range(lo, hi + 1) if final_coluna(d) == c]
                    freq = sum(stats[d]["freq"] for d in dezs if d in stats)
                    atraso = max((stats[d]["atraso"] for d in dezs if d in stats), default=0)
                    cols.append({"coluna": c, "freq": freq, "atraso": atraso})
                return cols

            colunas_lista = col_stats()
            quentes_cols = sorted(
                c["coluna"]
                for c in sorted(colunas_lista, key=lambda x: x["freq"], reverse=True)[:4]
            )
            atrasadas_cols = sorted(
                c["coluna"]
                for c in sorted(colunas_lista, key=lambda x: x["atraso"], reverse=True)[:4]
            )
            balanceadas_cols = sorted(
                list(dict.fromkeys(quentes_cols[:2] + atrasadas_cols[:2]))[:4]
            )
            while len(balanceadas_cols) < 4:
                for c in range(1, 11):
                    if c not in balanceadas_cols:
                        balanceadas_cols.append(c)
                    if len(balanceadas_cols) == 4:
                        break
            balanceadas_cols = sorted(balanceadas_cols)

            def escolher(colunas, criterio):
                sel = []
                for col in colunas:
                    dezs = sorted(d for d in range(dezena_min, max_dezena + 1) if final_coluna(d) == col)
                    if criterio == "quentes":
                        ordem = sorted(dezs, key=lambda x: stats[x]["freq"], reverse=True)
                    elif criterio == "atrasadas":
                        ordem = sorted(dezs, key=lambda x: stats[x]["atraso"], reverse=True)
                    else:
                        q = sorted(dezs, key=lambda x: stats[x]["freq"], reverse=True)[:2]
                        rest = [x for x in dezs if x not in q]
                        a = sorted(rest, key=lambda x: stats[x]["atraso"], reverse=True)[:2]
                        ordem = q + a
                    sel.extend(sorted(ordem[:4]))
                return sorted(sel)

            return {
                "quentes": {"colunas": quentes_cols, "dezenas": escolher(quentes_cols, "quentes")},
                "atrasadas": {"colunas": atrasadas_cols, "dezenas": escolher(atrasadas_cols, "atrasadas")},
                "balanceadas": {
                    "colunas": balanceadas_cols,
                    "dezenas": escolher(balanceadas_cols, "balanceadas"),
                },
            }

    return DesdobramentoService
