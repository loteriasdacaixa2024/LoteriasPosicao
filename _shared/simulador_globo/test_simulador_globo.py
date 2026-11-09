# -*- coding: utf-8 -*-
"""Regras de cor, integridade do sorteio e gravação no SQLite."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from simulador_globo.cores import cor_da_dezena
from simulador_globo.historico_service import caminho_sqlite
from simulador_globo.regras_globo import (
    ORDEM_MODALIDADES,
    montar_painel,
    novo_estado,
    simular_completo,
    sortear_proxima,
)


class Sequencial:
    def randrange(self, n):
        return 0


class TestCores(unittest.TestCase):
    def test_finais_oficiais_ate_60(self):
        esperados = {
            1: "vermelha", 2: "amarela", 3: "verde", 4: "marrom", 5: "azul",
            6: "rosa", 7: "preta", 8: "cinza", 9: "laranja", 10: "branca",
            11: "vermelha", 20: "branca", 31: "vermelha", 60: "branca",
        }
        for numero, cor in esperados.items():
            self.assertEqual(cor_da_dezena(numero)["id"], cor, numero)

    def test_extensao_alem_de_60_e_zero(self):
        self.assertEqual(cor_da_dezena(0)["id"], "branca")
        self.assertEqual(cor_da_dezena(61)["id"], "vermelha")
        self.assertEqual(cor_da_dezena(80)["id"], "branca")
        self.assertEqual(cor_da_dezena(99)["id"], "laranja")

    def test_quantidades_por_modalidade(self):
        mega = {c["id"]: c["quantidade"] for c in montar_painel("megasena")["cores"]}
        self.assertEqual(set(mega.values()), {6})
        self.assertEqual(montar_painel("megasena")["universo"], 60)

        quina = {c["quantidade"] for c in montar_painel("quina")["cores"]}
        self.assertEqual(quina, {8})

        loto = {c["id"]: c["quantidade"] for c in montar_painel("lotofacil")["cores"]}
        self.assertEqual(loto["vermelha"], 3)
        self.assertEqual(loto["azul"], 3)
        self.assertEqual(loto["branca"], 2)
        self.assertEqual(sum(loto.values()), 25)

        dia = {c["id"]: c["quantidade"] for c in montar_painel("diadesorte")["cores"]}
        self.assertEqual(dia["vermelha"], 4)
        self.assertEqual(sum(dia.values()), 31)

        mania = montar_painel("lotomania")
        self.assertEqual(mania["universo"], 100)
        self.assertTrue(all(c["quantidade"] == 10 for c in mania["cores"]))
        self.assertIn("00", next(c["dezenas"] for c in mania["cores"] if c["id"] == "branca"))

        sete = montar_painel("supersete")
        self.assertEqual(sete["universo"], 70)
        self.assertTrue(all(c["quantidade"] == 7 and c["percentual"] == 10.0 for c in sete["cores"]))


class TestSorteio(unittest.TestCase):
    def test_mega_sem_repetir_e_deixa_54_no_globo(self):
        estado = novo_estado("megasena")
        vistos = []
        ultimo = None
        for _ in range(6):
            ultimo = sortear_proxima(estado)
            vistos.append(ultimo["bola"]["numero"])
        self.assertTrue(ultimo["concluida"])
        self.assertEqual(len(vistos), len(set(vistos)))
        self.assertTrue(all(1 <= n <= 60 for n in vistos))
        self.assertEqual(ultimo["restantes_globo"], 54)
        self.assertEqual(ultimo["faltam"], 0)

    def test_varias_extrações_nao_repetem_dentro_do_sorteio(self):
        for _ in range(25):
            seq = simular_completo("megasena")
            nums = [b["numero"] for b in seq]
            self.assertEqual(len(nums), 6)
            self.assertEqual(len(nums), len(set(nums)))

    def test_dupla_sena_recarrega_e_pode_repetir_entre_sorteios(self):
        seq = simular_completo("duplasena", rng=Sequencial())
        self.assertEqual(len(seq), 12)
        primeiro = [b["numero"] for b in seq if b["fase_id"] == "dezenas_1"]
        segundo = [b["numero"] for b in seq if b["fase_id"] == "dezenas_2"]
        self.assertEqual(primeiro, [1, 2, 3, 4, 5, 6])
        self.assertEqual(segundo, [1, 2, 3, 4, 5, 6])

    def test_supersete_permite_o_mesmo_digito_em_colunas(self):
        seq = simular_completo("supersete", rng=Sequencial())
        self.assertEqual(len(seq), 7)
        self.assertEqual([b["numero"] for b in seq], [0, 0, 0, 0, 0, 0, 0])
        self.assertEqual([b["coluna"] for b in seq], [1, 2, 3, 4, 5, 6, 7])

    def test_extras_e_universo(self):
        dia = simular_completo("diadesorte")
        self.assertEqual(len(dia), 8)
        self.assertEqual(len({b["numero"] for b in dia[:7]}), 7)
        self.assertEqual(dia[-1]["grupo"], "mes")

        mil = simular_completo("maismilionaria")
        self.assertEqual(len(mil), 8)
        self.assertEqual(len({b["numero"] for b in mil[:6]}), 6)
        self.assertEqual([b["grupo"] for b in mil[-2:]], ["trevo", "trevo"])
        self.assertNotEqual(mil[-1]["numero"], mil[-2]["numero"])

        time = simular_completo("timemania")
        self.assertEqual(len(time), 8)
        self.assertEqual(len({b["numero"] for b in time[:7]}), 7)
        self.assertEqual(time[-1]["grupo"], "time")

        loto = simular_completo("lotofacil")
        self.assertEqual(len(loto), 15)
        self.assertEqual(len({b["numero"] for b in loto}), 15)

        mania = simular_completo("lotomania")
        self.assertEqual(len(mania), 20)
        self.assertEqual(len({b["numero"] for b in mania}), 20)
        self.assertTrue(all(0 <= b["numero"] <= 99 for b in mania))

        quina = simular_completo("quina")
        self.assertEqual(len(quina), 5)

    def test_todas_as_modalidades_encerram(self):
        for key in ORDEM_MODALIDADES:
            seq = simular_completo(key)
            self.assertGreaterEqual(len(seq), 5, key)


class TestHistorico(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sim.db")
        uri = "sqlite:///" + self.path.replace("\\", "/")
        self.assertEqual(caminho_sqlite(uri).replace("\\", "/"), self.path.replace("\\", "/"))
        from flask import Flask
        from simulador_globo.app_integration import extend_simulador_globo_app

        base = os.path.join(self.tmp.name, "templates")
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "base.html"), "w", encoding="utf-8") as fh:
            fh.write(
                "<!DOCTYPE html><html><body>{% block content %}{% endblock %}"
                "{% block scripts %}{% endblock %}</body></html>"
            )
        self.app = Flask(__name__, template_folder=base)
        self.app.config["SQLALCHEMY_DATABASE_URI"] = uri
        self.app.config["TESTING"] = True
        extend_simulador_globo_app(self.app, "megasena")
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pagina_e_fluxo_sqlite(self):
        pagina = self.client.get("/simulador-globo/")
        self.assertEqual(pagina.status_code, 200)
        self.assertIn("Painel de Cores".encode(), pagina.data)
        self.assertIn("Preparar Bolas".encode(), pagina.data)

        painel = self.client.get("/simulador-globo/api/painel/lotofacil").get_json()
        self.assertEqual(painel["universo"], 25)

        prep = self.client.post("/simulador-globo/api/preparar", json={"velocidade_ms": 5000})
        self.assertEqual(prep.status_code, 200)
        corpo = prep.get_json()
        self.assertEqual(len(corpo["fase"]["bolas"]), 60)
        sim_id = corpo["id"]

        numeros = []
        ultimo = None
        for _ in range(6):
            resp = self.client.post("/simulador-globo/api/proxima", json={"id": sim_id, "velocidade_ms": 1000})
            self.assertEqual(resp.status_code, 200, resp.data)
            ultimo = resp.get_json()
            numeros.append(ultimo["bola"]["numero"])
        self.assertTrue(ultimo["concluida"])
        self.assertEqual(len(numeros), len(set(numeros)))
        self.assertEqual(ultimo["restantes_globo"], 54)

        de_novo = self.client.post("/simulador-globo/api/proxima", json={"id": sim_id})
        self.assertEqual(de_novo.status_code, 409)

        hist = self.client.get("/simulador-globo/api/historico").get_json()["itens"]
        self.assertEqual(len(hist), 1)
        detalhe = self.client.get(f"/simulador-globo/api/historico/{sim_id}").get_json()
        self.assertEqual([b["numero"] for b in detalhe["sequencia"]], numeros)
        self.assertEqual(detalhe["velocidade_ms"], 1000)
        self.assertNotIn("estado", detalhe)

    def test_finalizar_grava_so_o_que_saiu(self):
        sim_id = self.client.post("/simulador-globo/api/preparar", json={}).get_json()["id"]
        self.client.post("/simulador-globo/api/proxima", json={"id": sim_id})
        fim = self.client.post("/simulador-globo/api/finalizar", json={"id": sim_id}).get_json()
        self.assertEqual(fim["status"], "interrompida")
        self.assertEqual(len(fim["sequencia"]), 1)
        self.assertEqual(self.client.post("/simulador-globo/api/proxima", json={"id": sim_id}).status_code, 409)


if __name__ == "__main__":
    unittest.main()
