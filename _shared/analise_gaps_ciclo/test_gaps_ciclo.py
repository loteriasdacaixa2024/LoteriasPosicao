# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import unittest
import unittest.mock

_SHARED = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from analise_gaps_ciclo.core import (
    analisar_regua_combinacoes,
    combinacoes_regua,
    deslocamentos_regua,
    gaps_de,
    gaps_sequencia,
    montar_por_ciclos,
    montar_ranking_comparativo,
    parse_padrao_gaps,
    viavel,
)
from analise_gaps_ciclo.gerador import gerar_apostas
from analise_gaps_ciclo.specs import get_gaps_ciclo_spec


class TestCoreGaps(unittest.TestCase):
    def test_exemplo_spec(self):
        self.assertEqual(gaps_de([1, 3, 7, 11, 15, 20, 29]), [2, 4, 4, 4, 5, 9])

    def test_ordem_sorteio_com_sinal(self):
        # mesma dezenas, ordem diferente da classificada
        ordem = [20, 7, 11, 29, 15, 22, 23]
        self.assertEqual(gaps_sequencia(ordem), [-13, 4, 18, -14, 7, 1])
        self.assertEqual(gaps_de(ordem), [4, 4, 5, 2, 1, 6])
        self.assertNotEqual(gaps_sequencia(ordem), gaps_de(ordem))

    def test_sorteio_ja_classificado_coincide(self):
        seq = [7, 11, 15, 20, 22, 23, 29]
        self.assertEqual(gaps_sequencia(seq), gaps_de(seq))

    def test_parse_gap_negativo(self):
        self.assertEqual(parse_padrao_gaps("-13 4 18 -14 7 1"), [-13, 4, 18, -14, 7, 1])

    def test_ranking_comparativo_bonus_ambos(self):
        from collections import Counter
        rank = montar_ranking_comparativo(
            Counter({"2 4 4": 3, "1 1 1": 5}),
            Counter({"2 4 4": 2, "9 1 1": 4}),
        )
        self.assertEqual(rank[0]["padrao"], "2 4 4")
        self.assertTrue(rank[0]["em_ambos"])
        self.assertEqual(rank[0]["fonte"], "ambos")
        self.assertEqual(rank[0]["score"], 3 + 2 + 2)

    def test_progressao_posicao_a_posicao(self):
        # 07 11 15 20 22 23 29 → ciclos 4,4,5,2,1,6
        ciclos = gaps_de([7, 11, 15, 20, 22, 23, 29])
        self.assertEqual(ciclos, [4, 4, 5, 2, 1, 6])
        ap = montar_por_ciclos(2, ciclos, dezena_min=1, dezena_max=31)
        self.assertEqual(ap, [2, 6, 10, 15, 17, 18, 24])

    def test_estouro_invalida(self):
        self.assertIsNone(montar_por_ciclos(28, [4, 4, 4, 4, 4, 4], dezena_min=1, dezena_max=31))


class TestRegua(unittest.TestCase):
    def test_exemplo_posicao_1_seis_acima(self):
        jogo = [10, 14, 18, 22, 26, 30, 31]
        self.assertEqual(gaps_de(jogo), [4, 4, 4, 4, 4, 1])
        refs = [4, 8, 12, 16, 20, 24, 25]
        deltas = deslocamentos_regua(jogo, refs)
        self.assertEqual(deltas[0], 6)
        self.assertEqual(deltas, [6, 6, 6, 6, 6, 6, 6])
        self.assertEqual(gaps_de(jogo), gaps_de(refs))

    def test_moda_e_conjunto_deslocado(self):
        ref = [4, 8, 12, 16, 20, 24, 25]
        jogo = [10, 14, 18, 22, 26, 30, 31]
        out = analisar_regua_combinacoes([jogo, ref, ref])
        self.assertEqual(out["referencias"][0]["referencia"], 4)
        self.assertEqual(out["referencias"][0]["vezes"], 2)
        ult = out["ultimo"]
        self.assertEqual(ult["posicoes"][0]["deslocamento"], 6)
        self.assertEqual(ult["posicoes"][0]["sentido"], "acima")
        self.assertTrue(ult["conjunto_uniforme"])
        self.assertEqual(ult["deslocamento_conjunto"], 6)
        self.assertEqual(len(out["linhas"]), 3)

    def test_empate_de_moda_escolhe_menor(self):
        a = [7, 11, 15, 20, 22, 23, 29]
        b = [4, 11, 15, 20, 22, 23, 29]
        out = analisar_regua_combinacoes([a, b])
        self.assertEqual(out["referencias"][0]["referencia"], 4)
        self.assertEqual(out["referencias"][0]["vezes"], 1)

    def test_combinacao_regua_e_a_moda(self):
        ref = [4, 8, 12, 16, 20, 24, 25]
        jogo = [10, 14, 18, 22, 26, 30, 31]
        self.assertEqual(combinacoes_regua([jogo, ref, ref], quantidade=1), [ref])


class TestSpecInicial(unittest.TestCase):
    def test_diadesorte_exclui_27_a_31(self):
        spec = get_gaps_ciclo_spec("diadesorte")
        self.assertEqual(spec["inicial_min"], 1)
        self.assertEqual(spec["inicial_max"], 26)
        self.assertNotIn(27, spec["iniciais_permitidas"])
        self.assertNotIn(31, spec["iniciais_permitidas"])
        self.assertIn(1, spec["iniciais_permitidas"])
        self.assertIn(10, spec["iniciais_permitidas"])
        self.assertIn(26, spec["iniciais_permitidas"])

    def test_viavel_requer_k(self):
        self.assertTrue(viavel(1, [1, 1, 1, 1, 1, 1], dezena_min=1, dezena_max=31, sorteadas=7))


_GAPS_MOCK = {
    "sucesso": True,
    "top_padroes": [
        {"padrao": "1 1 1 1 1 1", "gaps": [1, 1, 1, 1, 1, 1], "frequencia": 10},
        {"padrao": "2 2 2 2 2 2", "gaps": [2, 2, 2, 2, 2, 2], "frequencia": 4},
    ],
    "ultimo": {"gaps": [4, 4, 5, 2, 1, 6]},
    "moda_por_passo": [{"passo": i + 1, "moda": 3, "vezes": 2} for i in range(6)],
    "linhas": [
        {"dezenas_classificado": [4, 8, 12, 16, 20, 24, 25]},
        {"dezenas_classificado": [4, 8, 12, 16, 20, 24, 25]},
    ],
}
_REGUA = [4, 8, 12, 16, 20, 24, 25]


class TestGeradorSessoes(unittest.TestCase):
    def test_nenhuma_sessao(self):
        out = gerar_apostas("diadesorte", sessao1=False, sessao2=False, inicial=2)
        self.assertFalse(out.get("ok"))

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_sessao2_nao_exige_inicial(self, _m):
        out = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=None)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["apostas"][0]["dezenas"], _REGUA)

    def test_inicial_alta_bloqueada(self):
        out = gerar_apostas(
            "diadesorte", sessao1=True, sessao2=False, inicial=27,
            padrao="1 1 1 1 1 1",
        )
        self.assertFalse(out.get("ok"))

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_somente_sessao1(self, _m):
        out = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=3)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["sessoes"], {"gaps": True, "regua": False})
        self.assertEqual(out["apostas"][0]["dezenas"], [2, 3, 4, 5, 6, 7, 8])
        self.assertNotEqual(out["apostas"][0]["dezenas"], [2, 6, 10, 15, 17, 18, 24])

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_somente_sessao2(self, _m):
        out = gerar_apostas(
            "diadesorte", sessao1=False, sessao2=True, inicial=2, perfil="ultimo",
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["sessoes"], {"gaps": False, "regua": True})
        self.assertEqual(out["apostas"][0]["dezenas"], _REGUA)
        self.assertEqual(out["apostas"][0]["origem"], "regua")

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_duas_sessoes(self, _m):
        out = gerar_apostas("diadesorte", sessao1=True, sessao2=True, inicial=2, quantidade=2)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["sessoes"], {"gaps": True, "regua": True})
        self.assertEqual(out["apostas"][1]["dezenas"], _REGUA)
        self.assertEqual(out["apostas"][0]["inicial"], 2)
        self.assertEqual(out["apostas"][0]["dezenas"], [2, 3, 4, 5, 6, 7, 8])

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_troca_inicial_recalcula(self, _m):
        a = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=2)
        b = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=5)
        self.assertEqual(a["apostas"][0]["dezenas"], _REGUA)
        self.assertEqual(b["apostas"][0]["dezenas"], _REGUA)

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_sessao1_desligada_nao_usa_top_padroes(self, _m):
        out = gerar_apostas("diadesorte", sessao1=False, sessao2=True, inicial=2, perfil="ultimo")
        dezenas = [tuple(a["dezenas"]) for a in out["apostas"]]
        self.assertNotIn((2, 3, 4, 5, 6, 7, 8), dezenas)

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps", return_value=_GAPS_MOCK)
    def test_sessao2_desligada_nao_trava_no_ciclo_ultimo(self, _m):
        out = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1)
        self.assertNotEqual(out["apostas"][0]["dezenas"], [2, 6, 10, 15, 17, 18, 24])

    @unittest.mock.patch("analise_gaps_ciclo.gerador._analisar_gaps")
    def test_leitura_escolhe_fonte_dos_padroes(self, mock_ag):
        mock_ag.return_value = {
            "sucesso": True,
            "top_padroes": [{"padrao": "1 1 1 1 1 1", "gaps": [1, 1, 1, 1, 1, 1]}],
            "top_padroes_sorteio": [{"padrao": "2 2 2 2 2 2", "gaps": [2, 2, 2, 2, 2, 2]}],
            "ranking_comparativo": [{"padrao": "3 3 3 3 3 3", "gaps": [3, 3, 3, 3, 3, 3]}],
            "ultimo": {"gaps": [1, 1, 1, 1, 1, 1], "gaps_sorteio": [2, 2, 2, 2, 2, 2]},
        }
        a = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1, leitura="classificado")
        b = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1, leitura="sorteio")
        c = gerar_apostas("diadesorte", sessao1=True, sessao2=False, inicial=2, quantidade=1, leitura="ambos")
        self.assertEqual(a["apostas"][0]["ciclos"], [1, 1, 1, 1, 1, 1])
        self.assertEqual(b["apostas"][0]["ciclos"], [2, 2, 2, 2, 2, 2])
        self.assertEqual(c["apostas"][0]["ciclos"], [3, 3, 3, 3, 3, 3])


class TestGeometria(unittest.TestCase):
    """O volante validado do Dia de Sorte não muda. As outras grades só parametrizam."""

    def test_diadesorte_permanece_igual_ao_volante_validado(self):
        from analise_gaps_ciclo.geometria import indicadores_de, layout_de, legenda_layout

        lay = layout_de("diadesorte")
        self.assertEqual(lay.isolado, 31)
        self.assertEqual(lay.volante[-1], (31,))
        self.assertEqual(
            legenda_layout(lay),
            "linhas 01–10, 11–20, 21–30 e o 31 isolado",
        )
        amostras = [
            [4, 8, 15, 16, 23, 30, 31],
            [1, 2, 3, 4, 5, 6, 7],
            [10, 20, 21, 22, 29, 30, 31],
            [5, 14, 15, 16, 25, 26, 27],
            [31],
            [],
        ]
        for dezenas in amostras:
            novo = indicadores_de(dezenas, lay)
            velho = _legado_diadesorte(dezenas)
            for chave in (
                "linhas", "linhas_fmt", "tem_31", "colunas", "colunas_distintas",
                "colunas_repetidas", "concentracao", "dispersao", "sequencias",
                "diagonais", "distancias", "centro", "analise_31",
            ):
                self.assertEqual(novo[chave], velho[chave], f"{dezenas} · {chave}")

    def test_grades_das_outras_modalidades(self):
        from analise_gaps_ciclo.geometria import indicadores_de, layout_de

        lf = layout_de("lotofacil")
        self.assertIsNone(lf.isolado)
        self.assertEqual(lf.cols, 5)
        self.assertEqual(lf.rows, 5)
        ind = indicadores_de([1, 2, 5, 6, 25], lf)
        self.assertEqual(ind["linhas"], [3, 1, 0, 0, 1])
        self.assertFalse(ind["tem_31"])
        self.assertIn("01-02", ind["sequencias"])

        mega = layout_de("megasena")
        self.assertEqual(mega.rows, 6)
        self.assertEqual(mega.cols, 10)
        self.assertEqual(indicadores_de([60], mega)["linhas"], [0, 0, 0, 0, 0, 1])

        lm = layout_de("lotomania")
        self.assertEqual(lm.volante[0][0], 0)
        self.assertEqual(lm.volante[-1][-1], 99)
        self.assertEqual(indicadores_de([0, 99], lm)["linhas"][0], 1)
        self.assertEqual(indicadores_de([0, 99], lm)["linhas"][-1], 1)

        ss = layout_de("supersete")
        self.assertTrue(ss.posicional)
        self.assertEqual(ss.cols, 7)
        self.assertEqual(ss.rows, 10)
        ind_ss = indicadores_de([5, 5, 5, 0, 9, 3, 4], ss)
        self.assertEqual(ind_ss["linhas"][5], 3)
        self.assertTrue(any(s.startswith("05-05") for s in ind_ss["sequencias"]))
        self.assertIn("5,0", ind_ss["celulas"])
        self.assertIn("0,3", ind_ss["celulas"])


def _legado_diadesorte(dezenas):
    """Cópia da leitura validada do Dia de Sorte, antes do compartilhamento."""
    import math
    from collections import Counter, defaultdict

    def coord(n):
        v = int(n)
        if v == 31:
            return (3, 0)
        if 1 <= v <= 30:
            return ((v - 1) // 10, (v - 1) % 10)
        return None

    def fmt(n):
        return f"{int(n):02d}"

    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    nums = sorted({int(n) for n in dezenas if coord(int(n)) is not None})
    coords = {n: coord(n) for n in nums}
    linhas = [
        sum(1 for n in nums if coords[n][0] == 0),
        sum(1 for n in nums if coords[n][0] == 1),
        sum(1 for n in nums if coords[n][0] == 2),
        1 if 31 in coords else 0,
    ]
    no_grid = [n for n in nums if n != 31]
    colunas = [coords[n][1] + 1 for n in no_grid]
    cont_col = Counter(colunas)
    repetidas = [
        {
            "coluna": col,
            "qtd": qtd,
            "dezenas": [n for n in no_grid if coords[n][1] + 1 == col],
        }
        for col, qtd in sorted(cont_col.items())
        if qtd > 1
    ]
    faixas = {"esquerda": 0, "centro": 0, "direita": 0}
    for n in no_grid:
        col = coords[n][1] + 1
        if col <= 3:
            faixas["esquerda"] += 1
        elif col <= 7:
            faixas["centro"] += 1
        else:
            faixas["direita"] += 1
    faixa_mais = max(faixas, key=lambda nome: (faixas[nome], nome))
    linha_contagens = linhas[:3]
    linha_max = max(linha_contagens) if linha_contagens else 0
    linhas_mais = [i + 1 for i, qtd in enumerate(linha_contagens) if qtd == linha_max and qtd]
    pontos = [coords[n] for n in nums]
    if len(pontos) >= 2:
        pares = []
        maior = 0.0
        par_maior = [nums[0], nums[1]]
        for i, a in enumerate(nums):
            for b in nums[i + 1:]:
                d = dist(coords[a], coords[b])
                pares.append(d)
                if d > maior:
                    maior = d
                    par_maior = [a, b]
        media = sum(pares) / len(pares)
    else:
        media = 0.0
        maior = 0.0
        par_maior = []
    media_r = sum(p[0] for p in pontos) / len(pontos) if pontos else 0.0
    media_c = sum(p[1] for p in pontos) / len(pontos) if pontos else 0.0
    if len(pontos) >= 2:
        desvio_r = math.sqrt(sum((p[0] - media_r) ** 2 for p in pontos) / len(pontos))
        desvio_c = math.sqrt(sum((p[1] - media_c) ** 2 for p in pontos) / len(pontos))
    else:
        desvio_r = 0.0
        desvio_c = 0.0
    indice = int(round(min(100.0, (media / math.hypot(3, 9)) * 100))) if pontos else 0
    por_linha = defaultdict(list)
    for n in dezenas:
        if int(n) == 31:
            continue
        c = coord(int(n))
        if c is None or c[0] > 2:
            continue
        por_linha[c[0]].append(int(n))
    sequencias = []
    for grupo_nums in por_linha.values():
        ordenados = sorted(set(grupo_nums))
        grupo = [ordenados[0]] if ordenados else []
        for atual in ordenados[1:]:
            if atual == grupo[-1] + 1:
                grupo.append(atual)
                continue
            if len(grupo) >= 2:
                sequencias.append("-".join(fmt(x) for x in grupo))
            grupo = [atual]
        if len(grupo) >= 2:
            sequencias.append("-".join(fmt(x) for x in grupo))
    viz = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    celulas = {}
    for n in dezenas:
        if int(n) == 31:
            continue
        c = coord(int(n))
        if c is None or c[0] > 2:
            continue
        celulas[c] = int(n)
    vistos = set()
    diagonais = []
    for origem in celulas:
        if origem in vistos:
            continue
        pilha = [origem]
        comp = []
        vistos.add(origem)
        while pilha:
            atual = pilha.pop()
            comp.append(atual)
            for dr, dc in viz:
                nb = (atual[0] + dr, atual[1] + dc)
                if nb in celulas and nb not in vistos:
                    vistos.add(nb)
                    pilha.append(nb)
        if len(comp) < 2:
            continue
        comp.sort()
        diagonais.append("-".join(fmt(celulas[p]) for p in comp))
    if media_r >= 2.5:
        linha_txt = "linha do 31"
    else:
        linha_txt = f"linha {int(round(media_r)) + 1}"
    outras = [n for n in nums if n != 31]
    if 31 in coords and outras:
        dist_31 = [dist(coords[31], coords[n]) for n in outras]
        media_31 = sum(dist_31) / len(dist_31)
        outras_linhas = [
            sum(1 for n in outras if coords[n][0] == 0),
            sum(1 for n in outras if coords[n][0] == 1),
            sum(1 for n in outras if coords[n][0] == 2),
        ]
    else:
        media_31 = None
        outras_linhas = []
    return {
        "linhas": linhas,
        "linhas_fmt": " - ".join(str(x) for x in linhas),
        "tem_31": 31 in coords,
        "colunas": colunas,
        "colunas_distintas": len(cont_col),
        "colunas_repetidas": repetidas,
        "concentracao": {
            "linhas_mais": linhas_mais,
            "faixas": faixas,
            "faixa_mais": faixa_mais,
        },
        "dispersao": {
            "desvio_linha": round(desvio_r, 2),
            "desvio_coluna": round(desvio_c, 2),
            "indice": indice,
        },
        "sequencias": sequencias,
        "diagonais": diagonais,
        "distancias": {
            "media": round(media, 2),
            "maior": round(maior, 2),
            "par_maior": par_maior,
        },
        "centro": {
            "linha": round(media_r, 2),
            "coluna": round(media_c, 2),
            "rotulo": f"{linha_txt} · coluna {int(round(media_c)) + 1}",
        },
        "analise_31": {
            "presente": 31 in coords,
            "outras_linhas": outras_linhas,
            "distancia_media": None if media_31 is None else round(media_31, 2),
        },
    }


if __name__ == "__main__":
    unittest.main()
