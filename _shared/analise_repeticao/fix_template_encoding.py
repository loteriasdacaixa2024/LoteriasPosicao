# -*- coding: utf-8 -*-
"""Corrige mojibake linha a linha em templates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED_REP = Path(__file__).resolve().parent / "templates"
LOTofacil_REP = ROOT / "AnalisePorPosicao-Lotofacil-Only" / "templates"

FILES = [
    SHARED_REP / "analise_repeticao_concursos.html",
    SHARED_REP / "repeticao_gerador_card.html",
    SHARED_REP / "repeticao_gerador_page_script.html",
    SHARED_REP / "repeticao_gerador_estilos.html",
    LOTofacil_REP / "analise_repeticao_concursos.html",
    LOTofacil_REP / "repeticao_gerador_card.html",
    LOTofacil_REP / "repeticao_gerador_page_script_lotofacil.html",
]

MOJIBAKE_MARKERS = ("Ã", "â€", "Â·", "â†")


def fix_line(line: str) -> str:
    if not any(m in line for m in MOJIBAKE_MARKERS):
        return line
    for enc in ("cp1252", "latin-1"):
        try:
            return line.encode(enc).decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue
    return line


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    fixed_lines = [fix_line(ln) for ln in lines]
    fixed = "".join(fixed_lines)
    if fixed != text:
        path.write_text(fixed, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> int:
    for path in FILES:
        if not path.exists():
            print("skip", path.name)
            continue
        print("fixed" if fix_file(path) else "ok   ", path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
