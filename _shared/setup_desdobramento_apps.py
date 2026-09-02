#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Copia desdobramento Mega-Sena para +Milionária e Dupla Sena (volante 1-50)."""
import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
MEGA = os.path.join(BASE, "..", "AnalisePorPosicao-MegaSena-Only")

APPS = [
    {
        "dir": os.path.join(BASE, "..", "AnalisePorPosicao-MaisMilionaria-Only"),
        "nome": "+Milionária",
        "slug": "maismilionaria",
        "max": 50,
        "linhas": 5,
        "ciclo": 50,
        "service_class": "DesdobramentoMaisMilionariaService",
        "ciclo_class": "CicloMaisMilionariaService",
        "analise_class": "AnaliseMaisMilionariaService",
        "sorteio_model": "sorteio_maismilionaria",
        "sorteio_class": "SorteioMaisMilionaria",
    },
    {
        "dir": os.path.join(BASE, "..", "AnalisePorPosicao-DuplaSena-Only"),
        "nome": "Dupla Sena",
        "slug": "duplasena",
        "max": 50,
        "linhas": 5,
        "ciclo": 50,
        "service_class": "DesdobramentoDuplaSenaService",
        "ciclo_class": "CicloDuplaSenaService",
        "analise_class": "AnaliseDuplaSenaService",
        "sorteio_model": "sorteio_duplasena",
        "sorteio_class": "SorteioDuplaSena",
    },
]


def patch_html(text: str, cfg: dict) -> str:
    t = text
    t = t.replace("Mega-Sena", cfg["nome"])
    t = t.replace("Mega Sena", cfg["nome"])
    t = t.replace("mega-sena", cfg["slug"])
    t = t.replace("var(--mega-green)", "var(--primary)")
    t = t.replace("var(--mega-dark)", "var(--primary-dark, #04250a)")
    t = t.replace("var(--mega-light)", "var(--accent)")
    t = t.replace("60 dezenas", f"{cfg['ciclo']} dezenas")
    t = t.replace("/ 60 * 100", f"/ {cfg['ciclo']} * 100")
    t = t.replace("de 60", f"de {cfg['ciclo']}")
    t = t.replace("num < 1 || num > 60", f"num < 1 || num > {cfg['max']}")
    t = t.replace("entre 01 e 60", f"entre 01 e {cfg['max']:02d}")
    t = re.sub(
        r"for \(let linha = 0; linha < 6; linha\+\+\)",
        f"for (let linha = 0; linha < {cfg['linhas']}; linha++)",
        t,
    )
    t = re.sub(
        r"for \(let row = 1; row <= 6; row\+\+\)",
        f"for (let row = 1; row <= {cfg['linhas']}; row++)",
        t,
    )
    t = re.sub(
        r"vLine\.style\.gridRow = '3 / span 6'",
        f"vLine.style.gridRow = '3 / span {cfg['linhas']}'",
        t,
    )
    t = t.replace("Sena", "6 acertos").replace("sena", "max")
    t = t.replace(".premiado-sena", ".premiado-max")
    t = t.replace(".hit-badge-aposta.n-6", ".hit-badge-aposta.n-6")
    return t


def write_ciclo_service(path: str, cfg: dict):
    content = f'''from models.shared import db
from models.{cfg["sorteio_model"]} import {cfg["sorteio_class"]}


class {cfg["ciclo_class"]}:
    @staticmethod
    def obter_ciclo_atual():
        try:
            sorteios = db.session.query({cfg["sorteio_class"]}).order_by(
                {cfg["sorteio_class"]}.concurso.asc()
            ).all()
        except Exception:
            sorteios = []
        ciclo_num = 1
        dezenas_sorteadas = set()
        concursos_no_ciclo = 0
        total = {cfg["ciclo"]}
        for s in sorteios:
            dezenas_sorteadas.update(s.dezenas())
            concursos_no_ciclo += 1
            if len(dezenas_sorteadas) == total:
                ciclo_num += 1
                dezenas_sorteadas = set()
                concursos_no_ciclo = 0
        faltantes = sorted(set(range(1, total + 1)) - dezenas_sorteadas)
        return {{
            "ciclo_num": ciclo_num,
            "dezenas_sorteadas": sorted(dezenas_sorteadas),
            "dezenas_faltantes": faltantes,
            "total_sorteadas": len(dezenas_sorteadas),
            "total_faltantes": len(faltantes),
            "concursos_no_ciclo": concursos_no_ciclo,
        }}
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_desdobramento_service(path: str, cfg: dict):
    content = f'''import sys
import os
from datetime import datetime
from itertools import combinations
from typing import List, Dict, Any, Optional

_LOTERIAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _LOTERIAS not in sys.path:
    sys.path.insert(0, _LOTERIAS)
from _shared.desdobramento_fechamento import gerar_fechamento, gerar_fechamento_trevos, final_coluna

from models.shared import db
from models.desdobramento import Desdobramento, GrupoDesdobramento, ApostaDesdobramento
from services.{cfg["analise_class"].replace("Service", "_service").lower().replace("analisemais", "analise_mais").replace("analisedupla", "analise_dupla")} import {cfg["analise_class"]}

MAX_DEZENA = {cfg["max"]}


class {cfg["service_class"]}:
    @classmethod
    def gerar_fechamento(cls, numeros, modo="bronze"):
        return gerar_fechamento(numeros, modo)

    @classmethod
    def gerar_fechamento_trevos(cls, trevos):
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
            db.session.add(GrupoDesdobramento(
                desdobramento_id=desd.id, grupo_numero=idx, numeros=",".join(map(str, gp)),
            ))
        for idx, ap in enumerate(resultado["apostas"]):
            db.session.add(ApostaDesdobramento(
                desdobramento_id=desd.id,
                linha=(idx // 4) + 1,
                aposta_numero=(idx % 4) + 1,
                dezenas=",".join(map(str, ap)),
            ))
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
        return [{{
            "id": d.id, "nome": d.nome, "data_criacao": d.data_criacao,
            "numeros": d.numeros, "total_apostas": d.total_apostas, "modo": d.modo, "tipo": d.tipo,
        }} for d in q.all()]

    @staticmethod
    def buscar_por_id(id_):
        d = db.session.query(Desdobramento).filter(Desdobramento.id == id_).first()
        if not d:
            return None
        grupos_db = db.session.query(GrupoDesdobramento).filter(
            GrupoDesdobramento.desdobramento_id == id_
        ).order_by(GrupoDesdobramento.grupo_numero).all()
        grupos = [[int(x) for x in g.numeros.split(",")] for g in grupos_db]
        apostas_db = db.session.query(ApostaDesdobramento).filter(
            ApostaDesdobramento.desdobramento_id == id_
        ).order_by(ApostaDesdobramento.id).all()
        apostas = [[int(x) for x in a.dezenas.split(",")] for a in apostas_db]
        pares = [[list(p) for p in combinations(gp, 2)] for gp in grupos] if grupos else []
        return {{
            "id": d.id, "nome": d.nome, "data_criacao": d.data_criacao,
            "numeros": d.numeros, "total_apostas": d.total_apostas, "modo": d.modo, "tipo": d.tipo,
            "grupos": grupos, "pares": pares, "apostas": apostas,
        }}

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
        dados = {cfg["analise_class"]}.analise_geral()
        if not dados or "dados" not in dados:
            fb = list(range(1, MAX_DEZENA + 1))[:16]
            return {{
                "quentes": {{"colunas": [1, 2, 3, 4], "dezenas": fb}},
                "atrasadas": {{"colunas": [5, 6, 7, 8], "dezenas": fb}},
                "balanceadas": {{"colunas": [1, 2, 5, 6], "dezenas": fb}},
            }}
        stats = {{d["dezena"]: d for d in dados["dados"]}}

        def col_stats():
            cols = []
            for c in range(1, 11):
                dezs = [d for d in range(1, MAX_DEZENA + 1) if final_coluna(d) == c]
                freq = sum(stats[d]["freq"] for d in dezs if d in stats)
                atraso = max(stats[d]["atraso"] for d in dezs if d in stats) if dezs else 0
                cols.append({{"coluna": c, "freq": freq, "atraso": atraso}})
            return cols

        colunas_lista = col_stats()
        quentes_cols = sorted([c["coluna"] for c in sorted(colunas_lista, key=lambda x: x["freq"], reverse=True)[:4]])
        atrasadas_cols = sorted([c["coluna"] for c in sorted(colunas_lista, key=lambda x: x["atraso"], reverse=True)[:4]])
        balanceadas_cols = sorted(list(dict.fromkeys(quentes_cols[:2] + atrasadas_cols[:2]))[:4])
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
                dezs = sorted(d for d in range(1, MAX_DEZENA + 1) if final_coluna(d) == col)
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

        return {{
            "quentes": {{"colunas": quentes_cols, "dezenas": escolher(quentes_cols, "quentes")}},
            "atrasadas": {{"colunas": atrasadas_cols, "dezenas": escolher(atrasadas_cols, "atrasadas")}},
            "balanceadas": {{"colunas": balanceadas_cols, "dezenas": escolher(balanceadas_cols, "balanceadas")}},
        }}
'''
    # fix import path for analise service
    analise_file = {
        "AnaliseMaisMilionariaService": "analise_maismilionaria_service",
        "AnaliseDuplaSenaService": "analise_duplasena_service",
    }[cfg["analise_class"]]
    content = content.replace(
        f'from services.{cfg["analise_class"].replace("Service", "_service").lower().replace("analisemais", "analise_mais").replace("analisedupla", "analise_dupla")} import',
        f"from services.{analise_file} import",
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    mega_model = open(os.path.join(MEGA, "models", "desdobramento.py"), encoding="utf-8").read()
    mega_model = mega_model.replace(
        "class Desdobramento(db.Model):",
        "class Desdobramento(db.Model):\n    tipo = db.Column(db.String(20), default='dezenas')  # dezenas | trevo",
        1,
    )
    mega_routes = open(os.path.join(MEGA, "routes", "desdobramento_routes.py"), encoding="utf-8").read()

    for cfg in APPS:
        app_dir = cfg["dir"]
        os.makedirs(os.path.join(app_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(app_dir, "routes"), exist_ok=True)
        os.makedirs(os.path.join(app_dir, "services"), exist_ok=True)
        os.makedirs(os.path.join(app_dir, "templates"), exist_ok=True)

        with open(os.path.join(app_dir, "models", "desdobramento.py"), "w", encoding="utf-8") as f:
            f.write(mega_model)

        write_ciclo_service(os.path.join(app_dir, "services", "ciclo_service.py"), cfg)
        write_desdobramento_service(os.path.join(app_dir, "services", "desdobramento_service.py"), cfg)

        routes = mega_routes.replace("DesdobramentoMegaSenaService", cfg["service_class"])
        routes = routes.replace("CicloMegaSenaService", cfg["ciclo_class"])
        routes = routes.replace("Mega-Sena", cfg["nome"])
        routes = routes.replace("num > 60", f"num > {cfg['max']}")
        routes = routes.replace("01 e 60", f"01 e {cfg['max']:02d}")
        with open(os.path.join(app_dir, "routes", "desdobramento_routes.py"), "w", encoding="utf-8") as f:
            f.write(routes)

        html = open(os.path.join(MEGA, "templates", "desdobramento.html"), encoding="utf-8").read()
        html = patch_html(html, cfg)
        with open(os.path.join(app_dir, "templates", "desdobramento.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("OK", cfg["nome"])


if __name__ == "__main__":
    main()
