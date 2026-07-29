# -*- coding: utf-8 -*-
"""
Identidade visual oficial por modalidade (Loterias Caixa).

ÚNICA fonte de verdade para tokens CSS usados na interface.
Os `base.html` de cada app devem espelhar estes valores em `:root`.

Referência de associação visual habitual das Loterias Caixa:
  Lotofácil     → roxo / magenta
  Mega-Sena     → verde
  Quina         → violeta
  Lotomania     → laranja
  Timemania     → laranja + verde (time)
  Dia de Sorte  → amarelo / ouro  (única modalidade amarela)
  Super Sete    → verde-limão
  Dupla Sena    → vermelho
  +Milionária   → dourado + verde (trevo)
"""
from __future__ import annotations

from typing import Any, Dict

# Tokens mínimos esperados em toda modalidade
TEMA_KEYS = (
    "primary",
    "primary_dark",
    "primary_xdark",
    "accent",
    "accent_light",
    "on_accent",
    "bg",
    "surface",
)

TEMAS: Dict[str, Dict[str, str]] = {
    "lotofacil": {
        "nome": "Lotofácil",
        "primary": "#672666",
        "primary_dark": "#4a1c4a",
        "primary_xdark": "#2d0a2d",
        "accent": "#930089",       # roxo oficial (NÃO amarelo)
        "accent_light": "#f3ecf8",
        "on_accent": "#ffffff",
        "bg": "#f3ecf8",
        "surface": "#ffffff",
        "shadow_rgb": "147, 0, 137",
    },
    "megasena": {
        "nome": "Mega-Sena",
        "primary": "#0a6b1a",
        "primary_dark": "#07520f",
        "primary_xdark": "#04350a",
        "accent": "#1ec83a",
        "accent_light": "#e8faea",
        "on_accent": "#ffffff",
        "bg": "#f4fbf5",
        "surface": "#ffffff",
        "shadow_rgb": "30, 200, 58",
    },
    "quina": {
        "nome": "Quina",
        "primary": "#6a0dad",
        "primary_dark": "#520a9a",
        "primary_xdark": "#350666",
        "accent": "#9b30e8",
        "accent_light": "#f3e8ff",
        "on_accent": "#ffffff",
        "bg": "#f8f4fc",
        "surface": "#ffffff",
        "shadow_rgb": "155, 48, 232",
    },
    "lotomania": {
        "nome": "Lotomania",
        "primary": "#c45c00",
        "primary_dark": "#9e4900",
        "primary_xdark": "#6e3200",
        "accent": "#f5820a",
        "accent_light": "#fef0e0",
        "on_accent": "#ffffff",
        "bg": "#fff8f2",
        "surface": "#ffffff",
        "shadow_rgb": "245, 130, 10",
    },
    "timemania": {
        "nome": "Timemania",
        "primary": "#8b3a00",
        "primary_dark": "#6e2d00",
        "primary_xdark": "#441a00",
        "accent": "#e07000",
        "accent_light": "#fff3e0",
        "on_accent": "#ffffff",
        "bg": "#fffaf5",
        "surface": "#ffffff",
        "accent_time": "#00695c",
        "shadow_rgb": "224, 112, 0",
    },
    "diadesorte": {
        "nome": "Dia de Sorte",
        "primary": "#c08b00",
        "primary_dark": "#996e00",
        "primary_xdark": "#664a00",
        "accent": "#e6a800",
        "accent_light": "#fffaf0",
        "on_accent": "#1a0a00",
        "bg": "#fffdf5",
        "surface": "#ffffff",
        "accent_mes": "#196f3d",
        "shadow_rgb": "230, 168, 0",
    },
    "supersete": {
        "nome": "Super Sete",
        "primary": "#708e25",
        "primary_dark": "#50651a",
        "primary_xdark": "#303d10",
        "accent": "#a9cf46",
        "accent_light": "#ecf5d6",
        "on_accent": "#1a2600",
        "bg": "#f6faeb",
        "surface": "#ffffff",
        "shadow_rgb": "169, 207, 70",
    },
    "duplasena": {
        "nome": "Dupla Sena",
        "primary": "#8b0000",
        "primary_dark": "#6e0000",
        "primary_xdark": "#450000",
        "accent": "#d42020",
        "accent_light": "#fff0f0",
        "on_accent": "#ffffff",
        "bg": "#fffafa",
        "surface": "#ffffff",
        "accent2": "#e85500",
        "shadow_rgb": "212, 32, 32",
    },
    "maismilionaria": {
        "nome": "+Milionária",
        "primary": "#8b6914",
        "primary_dark": "#6e520e",
        "primary_xdark": "#4a3508",
        "accent": "#d4a017",
        "accent_light": "#fdf4d0",
        "on_accent": "#1a0a00",
        "bg": "#fdfaf0",
        "surface": "#ffffff",
        "accent_trevo": "#1a7a3a",
        "shadow_rgb": "212, 160, 23",
    },
}


def get_tema(modality_key: str) -> Dict[str, Any]:
    if modality_key not in TEMAS:
        raise KeyError(f"Tema não definido: {modality_key}")
    return dict(TEMAS[modality_key])


def css_root_block(modality_key: str) -> str:
    """Gera bloco `:root { ... }` para injeção / documentação."""
    t = get_tema(modality_key)
    lines = [":root {"]
    mapping = [
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
    for key, css_var in mapping:
        if key in t:
            lines.append(f"    {css_var}: {t[key]};")
    lines.append("    --radius: 12px;")
    lines.append("    --nav-h: 62px;")
    lines.append("}")
    return "\n".join(lines)
