# -*- coding: utf-8 -*-
"""O Nº da sequência segue a ordenação padrão da aba 5 (distância da média)."""
from __future__ import annotations

import os
import sys
import unittest

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "AnalisePorPosicao--DiaDeSorte-Only"))
for _p in (_APP, _SHARED):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analise_inteligentes_diadesorte.sequencias_sorteadas import (  # noqa: E402
    mapa_sequencia_no_padrao,
)
from analise_inteligentes_diadesorte.service import expandir_jogos_padrao  # noqa: E402
from analise_inteligentes_diadesorte.soma_media import (  # noqa: E402
    calcular_faixa_soma,
    classificar_soma,
    enriquecer_jogos_com_media,
)


def _rank_aba5(jogos):
    """Mesma chave da aba 5: |distância| asc, soma asc, ordem original estável."""
    decorado = list(enumerate(jogos))

    def chave(item):
        i, j = item
        dist = j.get("distancia")
        try:
            ad = abs(int(dist))
        except (TypeError, ValueError):
            ad = 99999
        return (ad, int(j.get("soma") or 0), i)

    ordenado = sorted(decorado, key=chave)
    return {
        tuple(j["dezenas"]): n
        for n, (_i, j) in enumerate(ordenado, 1)
    }


class TestMapaSequencia(unittest.TestCase):
    def test_coincide_com_ordenacao_da_aba5(self):
        pad = "0 0 0 0 0 0 3"
        out = expandir_jogos_padrao(pad, min_dezena=1, max_dezena=31)
        self.assertTrue(out.get("sucesso"))
        jogos = out["jogos"]
        somas = [int(j["soma"]) for j in jogos[::7]]
        faixa = calcular_faixa_soma(somas, fonte="historico")
        ricos = enriquecer_jogos_com_media(jogos, faixa)
        esperado = _rank_aba5(ricos)
        alvos = [j["dezenas"] for j in jogos[::11]]
        got = mapa_sequencia_no_padrao(pad, alvos, faixa, min_dezena=1, max_dezena=31)
        for dez in alvos:
            chave = tuple(dez)
            self.assertEqual(got[chave], esperado[chave], msg=dez)

    def test_empate_de_soma_preserva_ordem_original(self):
        pad = "0 3"
        out = expandir_jogos_padrao(pad, min_dezena=1, max_dezena=31)
        jogos = out["jogos"]
        faixa = calcular_faixa_soma([100], fonte="historico")
        ricos = enriquecer_jogos_com_media(jogos, faixa)
        esperado = _rank_aba5(ricos)
        got = mapa_sequencia_no_padrao(
            pad, [j["dezenas"] for j in jogos], faixa, min_dezena=1, max_dezena=31,
        )
        self.assertEqual(got, esperado)
        cls = classificar_soma(jogos[0]["soma"], faixa)
        self.assertIsNotNone(cls.get("distancia"))


if __name__ == "__main__":
    unittest.main()
