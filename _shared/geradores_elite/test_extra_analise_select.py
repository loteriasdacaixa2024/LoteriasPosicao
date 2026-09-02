# -*- coding: utf-8 -*-
import unittest
from types import SimpleNamespace

from extra_analise_select import (
    montar_opcoes_time_coracao,
    montar_opcoes_trevos,
    resolver_time_para_lote,
    resolver_trevos_para_lote,
    estatisticas_trevos_from_rows,
    estatisticas_times_from_rows,
)


class TestExtraAnaliseSelect(unittest.TestCase):
    def test_time_opcoes_ordem(self):
        stats = [
            {"time_num": 1, "time_nome": "ABC", "freq": 10, "atraso": 1, "pct": 1.0},
            {"time_num": 36, "time_nome": "Flamengo", "freq": 3, "atraso": 80, "pct": 0.3},
            {"time_num": 55, "time_nome": "Palmeiras", "freq": 40, "atraso": 2, "pct": 4.0},
        ]
        out = montar_opcoes_time_coracao(stats)
        self.assertTrue(out["sucesso"])
        vals = [o["value"] for o in out["opcoes"]]
        self.assertEqual(vals[0], "atrasado")
        self.assertEqual(vals[1], "frequente")
        self.assertEqual(vals[-1], "aleatorio")
        self.assertEqual(out["atrasado"]["time_num"], 36)
        self.assertEqual(out["frequente"]["time_num"], 55)
        lote = resolver_time_para_lote("frequente", 3, opcoes_payload=out)
        self.assertEqual([t["time_num"] for t in lote], [55, 55, 55])
        alea = resolver_time_para_lote("aleatorio", 80, opcoes_payload=out)
        self.assertEqual(len(alea), 80)

    def test_trevos_par_e_aleatorio(self):
        stats = [
            {"trevo": 1, "freq": 100, "atraso": 1},
            {"trevo": 2, "freq": 90, "atraso": 2},
            {"trevo": 3, "freq": 5, "atraso": 40},
            {"trevo": 4, "freq": 4, "atraso": 50},
            {"trevo": 5, "freq": 3, "atraso": 3},
            {"trevo": 6, "freq": 2, "atraso": 4},
        ]
        out = montar_opcoes_trevos(stats)
        self.assertTrue(out["sucesso"])
        self.assertEqual(out["frequente"]["trevos"], [1, 2])
        self.assertEqual(out["atrasado"]["trevos"], [3, 4])
        lote = resolver_trevos_para_lote("atrasado", 2, opcoes_payload=out)
        self.assertEqual(lote, [[3, 4], [3, 4]])
        alea = resolver_trevos_para_lote("aleatorio", 15, opcoes_payload=out)
        self.assertEqual(len(alea), 15)
        self.assertTrue(all(len(p) == 2 for p in alea))

    def test_stats_from_rows(self):
        catalog = {1: "ABC", 2: "Bahia"}
        rows = [
            SimpleNamespace(concurso=10, time_num=1),
            SimpleNamespace(concurso=9, time_num=2),
            SimpleNamespace(concurso=8, time_num=1),
        ]
        times = estatisticas_times_from_rows(rows, catalog)
        by = {t["time_num"]: t for t in times}
        self.assertEqual(by[1]["freq"], 2)
        self.assertEqual(by[2]["atraso"], 1)

        trows = [
            SimpleNamespace(concurso=5, t1=1, t2=2, trevos_lista=lambda: [1, 2]),
            SimpleNamespace(concurso=4, t1=1, t2=3, trevos_lista=lambda: [1, 3]),
        ]
        trevos = estatisticas_trevos_from_rows(trows)
        by_t = {t["trevo"]: t for t in trevos}
        self.assertEqual(by_t[1]["freq"], 2)
        self.assertEqual(by_t[2]["atraso"], 0)


if __name__ == "__main__":
    unittest.main()
