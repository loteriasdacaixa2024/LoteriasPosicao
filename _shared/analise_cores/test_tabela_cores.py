# -*- coding: utf-8 -*-
import os
import sqlite3
import unittest

from analise_cores.service import analisar, contar


def linha(concurso, ordem, mes=1):
    return {"concurso": concurso, "data": "", "ordem": ordem, "mes": mes, "mes_nome": ""}


class TestTabelaCores(unittest.TestCase):
    def test_vermelha_tem_quatro_e_o_mes_nao_entra_na_dezena(self):
        qtd = contar([1, 11, 21, 31, 2, 12, 22])
        self.assertEqual(qtd[0], 4)
        self.assertEqual(qtd[1], 3)
        self.assertEqual(sum(qtd), 7)

        out = analisar([linha(1, [1, 2, 3, 4, 5, 6, 7], mes=6)], de=1, ate=1)
        self.assertEqual(out["linhas"][0]["quantidades"][5], 1)
        self.assertEqual(out["linhas"][0]["mes"]["id"], "rosa")
        self.assertEqual(out["meses"][5]["vezes"], 1)
        self.assertEqual(out["totais"][5], 1)

    def test_meses_10_11_e_12(self):
        out = analisar([
            linha(1, [1, 2, 3, 4, 5, 6, 7], mes=10),
            linha(2, [1, 2, 3, 4, 5, 6, 7], mes=11),
            linha(3, [1, 2, 3, 4, 5, 6, 7], mes=12),
        ], de=1, ate=3)
        meses = {row["concurso"]: row["mes"]["id"] for row in out["linhas"]}
        self.assertEqual(meses[1], "branca")
        self.assertEqual(meses[2], "vermelha")
        self.assertEqual(meses[3], "amarela")

    def test_repeticao_e_intervalo(self):
        out = analisar([
            linha(10, [1, 2, 3, 4, 5, 6, 7]),
            linha(11, [11, 12, 13, 14, 15, 16, 17]),
            linha(12, [8, 9, 10, 18, 19, 20, 28]),
        ], de=10, ate=12)
        self.assertEqual(out["linhas"][1]["repetiu_cores"], 7)
        self.assertEqual(out["linhas"][1]["repetiu_bolas"], 7)
        self.assertEqual(out["linhas"][2]["repetiu_cores"], 0)
        vermelha = out["intervalos"][0]
        self.assertEqual(vermelha["presencas"], 2)
        self.assertEqual(vermelha["intervalo_medio"], 1)
        self.assertEqual(vermelha["atraso"], 1)
        self.assertIsNone(out["linhas"][0]["repetiu_cores"])

    def test_janela_padrao_e_os_dez_ultimos(self):
        base = [linha(n, [1, 2, 3, 4, 5, 6, 7]) for n in range(1, 13)]
        out = analisar(base)
        self.assertEqual(out["total"], 10)
        self.assertEqual(out["de"], 3)
        self.assertEqual(out["ate"], 12)

    def test_soma_do_banco_fecha_em_sete(self):
        caminho = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..",
            "AnalisePorPosicao--DiaDeSorte-Only", "instance", "diadesorte.db",
        ))
        if not os.path.exists(caminho):
            self.skipTest("banco do Dia de Sorte ausente")
        con = sqlite3.connect(caminho)
        try:
            rows = con.execute(
                "SELECT concurso, d1, d2, d3, d4, d5, d6, d7, mes_num "
                "FROM sorteio_diadesorte ORDER BY concurso DESC LIMIT 10"
            ).fetchall()
        finally:
            con.close()
        if len(rows) < 10:
            self.skipTest("menos de 10 concursos")
        linhas = [{
            "concurso": r[0], "data": "", "ordem": list(r[1:8]), "mes": r[8] or 0, "mes_nome": "",
        } for r in rows]
        out = analisar(linhas, de=min(r[0] for r in rows), ate=max(r[0] for r in rows))
        self.assertEqual(sum(out["totais"]), 70)
        self.assertEqual(out["grupos"][0]["bolas"][0]["rotulo"], "01")
        self.assertEqual(len(out["grupos"][0]["bolas"]), 4)
        self.assertEqual(len(out["grupos"][1]["bolas"]), 3)


if __name__ == "__main__":
    unittest.main()
