# -*- coding: utf-8 -*-
"""Corte e pontuação do Resumo Geral só valem quando o checkbox está marcado."""
import os
import random
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.abspath(_HERE)
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from resumo_modalidade.gerador_menu import (  # noqa: E402
    _ctx,
    _ctx_com_mes,
    _cumpre,
    _distribuir_meses_indicados,
    _ligado_padrao,
    _papel,
    gerar_resumo_geral,
)
from resumo_modalidade.specs import ResumoSpec  # noqa: E402
import resumo_modalidade.gerador_menu as gm  # noqa: E402


def _spec():
    return ResumoSpec(
        modality_key="teste",
        nome="Teste",
        enabled=True,
        dezena_min=1,
        dezena_max=15,
        sorteadas=4,
        faixas=(("B", 1, 5, "B"), ("M", 6, 10, "M"), ("A", 11, 15, "A")),
        motor="conjunto",
    )


def _item(nome, papel):
    return {"criterio": nome, "papel": papel, "tipo": "frequente", "uso": "geracao"}


CATALOGO = [
    _item("Pares × ímpares", "corte"),
    _item("Repetidas do anterior", "corte"),
    _item("Soma", "corte"),
    _item("Média dos gaps", "corte"),
    _item("Finais iguais", "corte"),
    _item("Sequências", "ponto"),
    _item("Linhas (blocos de 10)", "ponto"),
    _item("Faixas B/M/A", "exibe"),
]


def _ctx_teste():
    return {
        "spec": _spec(),
        "prev": {1, 2, 3},
        "historico": set(),
        "pares": 4,
        "soma_lo": 40,
        "soma_hi": 52,
        "gap_lo": 1,
        "gap_hi": 1.5,
        "amp_lo": 0,
        "amp_hi": 99,
        "refs": [],
        "bma_top": [],
        "seq_minima": False,
        "linhas_moda": 2,
        "dd_moda": 2,
        "du_moda": 4,
        "padrao": "",
        "quentes": set(),
        "sp": None,
        "mes_num": None,
        "mes_nome": "",
        "grupo_moda": {},
        "ocorrencias": [],
    }


def _dezenas(ap):
    return [int(x) for x in ap["dezenas"]]


class TestConcursoAnterior(unittest.TestCase):
    def test_prev_e_o_ultimo_sorteio(self):
        spec = _spec()
        sorteios = [
            {"dezenas": [1, 2, 3, 4], "concurso": 1},
            {"dezenas": [5, 6, 7, 8], "concurso": 2},
            {"dezenas": [9, 10, 11, 12], "concurso": 3},
        ]
        ctx = _ctx(spec, {}, sorteios)
        self.assertEqual(ctx["prev"], {9, 10, 11, 12})


class TestFlagsDaGeracao(unittest.TestCase):
    def setUp(self):
        self.pack = {
            "spec": _spec(),
            "catalogo": CATALOGO,
            "ctx": _ctx_teste(),
            "historico": set(),
            "erro": "",
        }
        self._montar = gm._montar_pack
        self._random = gm.random.Random
        original = self._random
        gm._montar_pack = lambda _key: self.pack
        gm.random.Random = lambda *a, **k: original(7)

    def tearDown(self):
        gm._montar_pack = self._montar
        gm.random.Random = self._random

    def _gerar(self, ativos, quantidade=30):
        out = gerar_resumo_geral("teste", ativos, quantidade, 4)
        self.assertTrue(out.get("sucesso"), out.get("erro"))
        return out

    def test_repetidas_desmarcada_nao_e_chamada(self):
        vistos = []
        real = gm._cumpre

        def spy(nome, dz, ctx):
            vistos.append(nome)
            return real(nome, dz, ctx)

        gm._cumpre = spy
        try:
            off = self._gerar(["Soma"])
            self.assertNotIn("Repetidas do anterior", vistos)
            self.assertNotIn("Repetidas do anterior", off["cortes"])
            vistos.clear()
            on = self._gerar(["Repetidas do anterior"])
            self.assertIn("Repetidas do anterior", vistos)
            self.assertEqual(on["cortes"], ["Repetidas do anterior"])
        finally:
            gm._cumpre = real

    def test_repetidas_marcada_corta_fora_de_1_ou_2(self):
        prev = set(self.pack["ctx"]["prev"])
        on = self._gerar(["Repetidas do anterior"])
        offs = []
        for ap in on["apostas"]:
            nrep = len(set(_dezenas(ap)) & prev)
            self.assertTrue(1 <= nrep <= 2, ap["dezenas"])
        off = self._gerar(["Soma"])
        for ap in off["apostas"]:
            offs.append(len(set(_dezenas(ap)) & prev))
        self.assertTrue(offs)
        self.assertTrue(all(n == 0 for n in offs), offs)

    def test_cada_corte_muda_o_conjunto(self):
        ctx = self.pack["ctx"]

        def pares(ap):
            return sum(1 for n in _dezenas(ap) if n % 2 == 0)

        def soma(ap):
            return sum(_dezenas(ap))

        def gaps(ap):
            dz = sorted(_dezenas(ap))
            gs = [b - a for a, b in zip(dz, dz[1:])]
            return sum(gs) / len(gs)

        def finais(ap):
            fins = [n % 10 for n in _dezenas(ap)]
            return len(fins) != len(set(fins))

        casos = [
            ("Pares × ímpares", lambda ap: pares(ap) == ctx["pares"], lambda ap: pares(ap) != ctx["pares"]),
            ("Soma", lambda ap: ctx["soma_lo"] <= soma(ap) <= ctx["soma_hi"], lambda ap: not (ctx["soma_lo"] <= soma(ap) <= ctx["soma_hi"])),
            ("Média dos gaps", lambda ap: ctx["gap_lo"] <= gaps(ap) <= ctx["gap_hi"], lambda ap: not (ctx["gap_lo"] <= gaps(ap) <= ctx["gap_hi"])),
            ("Finais iguais", finais, lambda ap: not finais(ap)),
        ]
        for nome, dentro, fora in casos:
            marcado = self._gerar([nome], 40)
            self.assertEqual(marcado["cortes"], [nome])
            self.assertTrue(all(dentro(ap) for ap in marcado["apostas"]), nome)
            livre = self._gerar(["Linhas (blocos de 10)"], 40)
            self.assertNotIn(nome, livre["cortes"])
            self.assertNotIn(nome, livre["pontos"])
            self.assertTrue(any(fora(ap) for ap in livre["apostas"]), nome)

    def test_pontuacao_desmarcada_nao_entra_na_nota(self):
        ctx = dict(self.pack["ctx"])
        ctx["soma_lo"] = 0
        ctx["soma_hi"] = 999
        self.pack["ctx"] = ctx
        sem = self._gerar(["Soma"])
        self.assertEqual(sem["pontos"], [])
        self.assertTrue(all(ap["pontos"] == 10 for ap in sem["apostas"]))
        com = self._gerar(["Soma", "Sequências"])
        self.assertEqual(com["pontos"], ["Sequências"])
        self.assertTrue(any(ap["pontos"] > 10 for ap in com["apostas"]))
        self.assertTrue(all(ap["pontos"] >= 10 for ap in com["apostas"]))

    def test_checklist_nao_filtra(self):
        ctx = dict(self.pack["ctx"])
        ctx["soma_lo"] = 0
        ctx["soma_hi"] = 999
        self.pack["ctx"] = ctx
        base = self._gerar(["Soma"])
        com_info = self._gerar(["Soma", "Faixas B/M/A"])
        self.assertEqual(com_info["cortes"], ["Soma"])
        self.assertEqual(com_info["pontos"], [])
        self.assertEqual(
            [ap["dezenas"] for ap in base["apostas"]],
            [ap["dezenas"] for ap in com_info["apostas"]],
        )
        so_info = gerar_resumo_geral("teste", ["Faixas B/M/A"], 10, 4)
        self.assertFalse(so_info.get("sucesso"))

    def test_pendentes_e_atrasadas_sao_pontuacao(self):
        self.assertEqual(
            _papel({"criterio": "Dezenas pendentes do ciclo", "tipo": "info"}),
            "ponto",
        )
        self.assertEqual(_papel({"criterio": "Mais atrasadas", "tipo": "info"}), "ponto")
        self.assertEqual(_papel({"criterio": "Ciclo de cobertura", "tipo": "info"}), "exibe")
        self.assertFalse(_ligado_padrao(
            {"criterio": "Repetidas do anterior", "tipo": "frequente", "uso": "geracao"},
            "corte",
        ))
        self.assertTrue(_ligado_padrao(
            {"criterio": "Soma", "tipo": "frequente", "uso": "filtro"},
            "corte",
        ))
        ctx = _ctx_teste()
        ctx["pendentes"] = {8, 9}
        ctx["atrasadas"] = {14, 15}
        self.assertTrue(_cumpre("Dezenas pendentes do ciclo", [8, 4, 5, 6], ctx))
        self.assertFalse(_cumpre("Dezenas pendentes do ciclo", [4, 5, 6, 7], ctx))
        self.assertTrue(_cumpre("Mais atrasadas", [14, 4, 5, 6], ctx))
        self.assertFalse(_cumpre("Mais atrasadas", [4, 5, 6, 7], ctx))
        self.assertIsNone(_cumpre("Dezenas pendentes do ciclo", [8, 4, 5, 6], _ctx_teste()))

        jogo = dict(self.pack["ctx"])
        jogo["soma_lo"] = 0
        jogo["soma_hi"] = 999
        jogo["pendentes"] = {15}
        jogo["atrasadas"] = {14}
        self.pack["ctx"] = jogo
        self.pack["catalogo"] = list(CATALOGO) + [
            _item("Dezenas pendentes do ciclo", "ponto"),
            _item("Mais atrasadas", "ponto"),
        ]
        out = self._gerar(["Soma", "Dezenas pendentes do ciclo", "Mais atrasadas"], 40)
        self.assertEqual(
            out["pontos"],
            ["Dezenas pendentes do ciclo", "Mais atrasadas"],
        )
        self.assertEqual(out["cortes"], ["Soma"])
        notas = [ap["pontos"] for ap in out["apostas"]]
        self.assertTrue(any(p == 10 for p in notas), notas)
        self.assertTrue(any(p > 10 for p in notas), notas)


class TestMesesIndicadosNoLote(unittest.TestCase):
    def test_cada_bloco_de_10_recebe_os_indicados(self):
        pool = [5, 8, 7, 12]
        meses = _distribuir_meses_indicados(pool, 23, random.Random(3))
        self.assertEqual(len(meses), 23)
        self.assertTrue(set(meses) <= set(pool))
        for inicio in (0, 10):
            bloco = meses[inicio:inicio + 10]
            self.assertEqual(set(bloco), set(pool))
        self.assertTrue(set(meses[20:]) <= set(pool))

    def test_mes_da_sorte_so_pontua_se_estiver_indicado(self):
        ctx = _ctx_teste()
        ctx = _ctx_com_mes(ctx, {"mes_num": 5, "mes_nome": "Maio"}, [5, 8, 7, 12])
        self.assertTrue(_cumpre("Mês da Sorte", [1, 2, 3, 4], ctx))
        fora = _ctx_com_mes(_ctx_teste(), {"mes_num": 6, "mes_nome": "Junho"}, [5, 8, 7, 12])
        self.assertFalse(_cumpre("Mês da Sorte", [1, 2, 3, 4], fora))
