"""Formatação numérica/moeda BR (sem dependências circulares)."""
from typing import Any


def fmt_numero_br(valor: float, casas: int = 2) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_moeda(valor: float) -> str:
    return f"R$ {fmt_numero_br(valor)}"


def parse_preco(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("R$", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)
