# -*- coding: utf-8 -*-
"""One-shot: sync each modality base.html :root with temas_modalidade.TEMAS."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from _shared.configuracoes.temas_modalidade import TEMAS  # noqa: E402

MAP = {
    "lotofacil": ROOT / "AnalisePorPosicao-Lotofacil-Only" / "templates" / "base.html",
    "megasena": ROOT / "AnalisePorPosicao-MegaSena-Only" / "templates" / "base.html",
    "quina": ROOT / "AnalisePorPosicao-Quina-Only" / "templates" / "base.html",
    "lotomania": ROOT / "AnalisePorPosicao-Lotomania-Only" / "templates" / "base.html",
    "timemania": ROOT / "AnalisePorPosicao-Timemania-Only" / "templates" / "base.html",
    "diadesorte": ROOT / "AnalisePorPosicao--DiaDeSorte-Only" / "templates" / "base.html",
    "supersete": ROOT / "AnalisePorPosicao-SuperSete-Only" / "templates" / "base.html",
    "duplasena": ROOT / "AnalisePorPosicao-DuplaSena-Only" / "templates" / "base.html",
    "maismilionaria": ROOT / "AnalisePorPosicao-MaisMilionaria-Only" / "templates" / "base.html",
}

THEME_PROPS = {
    "primary",
    "primary-dark",
    "primary-xdark",
    "accent",
    "accent-light",
    "on-accent",
    "bg",
    "surface",
    "accent-mes",
    "accent-time",
    "accent-trevo",
    "accent2",
}

MAPPING = [
    ("primary", "--primary"),
    ("primary_dark", "--primary-dark"),
    ("primary_xdark", "--primary-xdark"),
    ("accent", "--accent"),
    ("accent_light", "--accent-light"),
    ("on_accent", "--on-accent"),
    ("bg", "--bg"),
    ("surface", "--surface"),
    ("accent_mes", "--accent-mes"),
    ("accent_time", "--accent-time"),
    ("accent_trevo", "--accent-trevo"),
    ("accent2", "--accent2"),
]


def main() -> None:
    for key, path in MAP.items():
        text = path.read_text(encoding="utf-8")
        m = re.search(r":root\s*\{([^}]*)\}", text, re.S)
        if not m:
            print("NO :root", key)
            continue
        t = TEMAS[key]
        kept = []
        for line in m.group(1).splitlines():
            s = line.strip()
            if not s or s.startswith("/*"):
                continue
            prop = s.split(":", 1)[0].strip().lstrip("-")
            # prop like "primary" from "--primary"
            css_name = s.split(":", 1)[0].strip()
            name = css_name[2:] if css_name.startswith("--") else ""
            if name in THEME_PROPS:
                continue
            if s.startswith("--"):
                kept.append("            " + s.rstrip(";") + ";")

        lines = ["        :root {"]
        lines.append(
            f"            /* Identidade {t['nome']} — espelha configuracoes.temas_modalidade */"
        )
        for k, css in MAPPING:
            if k in t:
                lines.append(f"            {css}: {t[k]};")
        for x in kept:
            # normalize indent of kept props
            prop = x.strip()
            lines.append(f"            {prop}")
        if not any("--radius" in x for x in kept):
            lines.append("            --radius: 12px;")
        if not any("--nav-h" in x for x in kept):
            lines.append("            --nav-h: 62px;")
        lines.append("        }")
        new_root = "\n".join(lines)
        path.write_text(text[: m.start()] + new_root + text[m.end() :], encoding="utf-8")
        print("UPDATED", key)


if __name__ == "__main__":
    main()
