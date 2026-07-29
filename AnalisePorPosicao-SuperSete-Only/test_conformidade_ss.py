# -*- coding: utf-8 -*-
"""Testes de conformidade Super Sete — execução standalone."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "_shared"
sys.path.insert(0, str(SHARED))
sys.path.insert(0, str(ROOT / "AnalisePorPosicao-SuperSete-Only"))

from configuracoes.acertos_posicionais import (  # noqa: E402
    contar_acertos_posicional,
    digitos_acertados,
    validar_aposta_ss,
)
from concentracao_acertos.core import (  # noqa: E402
    backtest_conjunto_posicional,
    gerar_apostas_supersete,
)
from geradores_elite.construtor.universes.digitos_service import (  # noqa: E402
    ConstrutorDigitosService,
)
from geradores_elite.comportamento.conferencia_estrategias import (  # noqa: E402
    conferir_apostas_pontual,
)
from central_conferencias.folder_service import _analisar_aposta  # noqa: E402
from central_conferencias.config import get_conf  # noqa: E402


def _ok(nome: str, cond: bool, detalhe: str = "") -> None:
    status = "OK" if cond else "FALHOU"
    print(f"[{status}] {nome}" + (f" — {detalhe}" if detalhe else ""))
    if not cond:
        raise AssertionError(nome)


def main() -> None:
    # 1) Acertos posicionais
    sort877 = [0, 0, 5, 5, 1, 7, 3]
    _ok(
        "aposta idêntica ao 877 = 7 acertos",
        contar_acertos_posicional(sort877, sort877) == 7,
    )
    _ok(
        "sete zeros vs 877 = 2 acertos",
        contar_acertos_posicional([0] * 7, sort877) == 2,
    )
    _ok(
        "set intersection erraria (5); posicional = 7",
        len(set(sort877) & set(sort877)) == 5
        and contar_acertos_posicional(sort877, sort877) == 7,
    )

    # 2) Central conferências
    cfg = get_conf("supersete")
    _ok("faixas incluem 3 e 4", {3, 4, 5, 6, 7} <= {f[0] for f in cfg["faixas"]})
    ana = _analisar_aposta(sort877, sort877, cfg)
    _ok("Central: 7 acertos na aposta idêntica", ana["resultado"]["acertos"] == 7)
    ana2 = _analisar_aposta([7] * 7, sort877, cfg)
    _ok("Central: sete iguais válidos", ana2["resultado"]["acertos"] == 1)
    ok, msg, seq = validar_aposta_ss([1, 1, 1, 1, 1, 1, 1])
    _ok("validar sete iguais", ok and len(seq) == 7, msg)

    # 3) conferir_apostas_pontual positional
    pont = conferir_apostas_pontual(
        [{"numero": 1, "dezenas": sort877}],
        sort877,
        7,
        positional=True,
    )
    _ok("pontual positional = 7", pont["apostas"][0]["acertos"] == 7)

    # 4) Gerador dígitos SS
    gen = ConstrutorDigitosService._gerar_supersete_posicional(
        list(range(10)), qtd=20, modo="frequencia", exigir=None,
    )
    _ok("gerador SS sucesso", gen.get("sucesso") is True, str(gen.get("erro")))
    apostas = [a["dezenas"] for a in gen["apostas"]]
    _ok("gerador SS 7 colunas", all(len(a) == 7 for a in apostas))
    tem_rep = any(len(set(a)) < 7 for a in apostas)
    _ok("gerador SS permite repetição (amostra)", tem_rep or len(apostas) < 5)

    gen1 = ConstrutorDigitosService._gerar_supersete_posicional(
        [4], qtd=5, modo="frequencia", exigir=1,
    )
    _ok("gerador SS todos iguais (pool {4})", gen1.get("sucesso") is True)
    if gen1.get("sucesso"):
        _ok(
            "apostas = 4,4,4,4,4,4,4",
            all(a["dezenas"] == [4] * 7 for a in gen1["apostas"]),
        )

    diag = ConstrutorDigitosService.diagnosticar(
        "supersete", [0, 1, 5], exigir_qtd_digitos=2, qtd_apostas=5,
    )
    _ok("diagnóstico SS ok", diag.get("ok") is True)

    # 5) Concentração SS
    gconc = gerar_apostas_supersete([0, 1, 2, 5, 7, 8, 9], quantidade=10, seed=42)
    _ok("concentração gerar SS", gconc.get("sucesso") is True)
    class Fake:
        def __init__(self, c, d):
            self.concurso = c
            self.data = "x"
            self._d = d
        def digitos(self):
            return list(self._d)
        def dezenas(self):
            return list(self._d)

    rows = [
        Fake(877, sort877),
        Fake(874, [5, 9, 1, 5, 1, 8, 8]),
        Fake(21, [7, 8, 7, 9, 9, 8, 8]),
    ]
    bt = backtest_conjunto_posicional(
        [sort877, [0] * 7],
        rows,
        max_acertos=7,
        pico_destaque=3,
    )
    _ok("backtest posicional", bt.get("sucesso") is True)
    linha877 = next(l for l in bt["linhas"] if l["concurso"] == 877)
    _ok("backtest 877 max=7", linha877["max_acertos"] == 7)

    # 6) Limites construtor / desdobramento
    from geradores_elite.construtor.construtor_specs import SUPERSETE_CONSTRUTOR
    _ok("max_digitos_por_coluna=3", SUPERSETE_CONSTRUTOR.max_digitos_por_coluna == 3)

    # 7) Modelo dezenas() é lista
    from models.sorteio_supersete import SorteioSuperSete
    s = SorteioSuperSete(
        concurso=0, data="t",
        coluna_1=4, coluna_2=4, coluna_3=4, coluna_4=4,
        coluna_5=4, coluna_6=4, coluna_7=4,
    )
    dz = s.dezenas()
    _ok("dezenas() é lista", isinstance(dz, list) and dz == [4] * 7)

    print("\nRESULTADO: TODAS AS VERIFICAÇÕES OK")


if __name__ == "__main__":
    main()
