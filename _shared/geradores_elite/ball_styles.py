"""
Estilos de bolas/números — cópia fiel do painel principal (/) de cada modalidade.
Layout de linha/centralização fica em engine_final.html (comum a todas).
"""

BALL_STYLES = {
    "lotofacil": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 32px; height: 32px; border-radius: 50%;
            background: var(--accent); color: var(--on-accent, #fff);
            font-weight: 800; font-size: .82rem;
            box-shadow: 0 2px 6px rgba(147, 0, 137, .35);
        }
    """,
    "supersete": """
        #ge-engine-final .coluna-badge {
            display: inline-flex; align-items: center; justify-content: center;
            width: 36px; height: 36px; border-radius: 8px;
            background: var(--accent); color: #1a2600;
            font-weight: 900; font-size: 1.1rem; margin: 2px;
            box-shadow: 0 2px 6px rgba(116, 184, 21, .35);
        }
    """,
    "lotomania": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 34px; height: 34px; border-radius: 50%;
            background: var(--accent); color: #fff;
            font-weight: 800; font-size: .82rem;
            box-shadow: 0 2px 6px rgba(245, 130, 10, .35);
        }
    """,
    "quina": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; border-radius: 50%;
            background: var(--accent); color: #fff;
            font-weight: 800; font-size: .9rem;
            box-shadow: 0 2px 8px rgba(155, 48, 232, .4);
        }
    """,
    "megasena": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; border-radius: 50%;
            background: var(--accent); color: #fff;
            font-weight: 800; font-size: .9rem;
            box-shadow: 0 2px 8px rgba(30, 200, 58, .4);
        }
    """,
    "maismilionaria": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 38px; height: 38px; border-radius: 50%;
            background: var(--accent); color: #fff;
            font-weight: 800; font-size: .88rem;
            box-shadow: 0 2px 6px rgba(212, 160, 23, .4);
        }
        #ge-engine-final .trevo-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 30px; height: 30px; border-radius: 50%;
            background: var(--accent-trevo); color: #fff;
            font-weight: 800; font-size: .75rem;
            box-shadow: 0 2px 6px rgba(26, 122, 58, .4);
        }
    """,
    "duplasena": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 34px; height: 34px; border-radius: 50%;
            background: var(--accent); color: #fff;
            font-weight: 800; font-size: .82rem;
            box-shadow: 0 2px 5px rgba(212, 32, 32, .4);
        }
    """,
    "timemania": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 36px; height: 36px; border-radius: 50%;
            background: var(--accent); color: #fff;
            font-weight: 800; font-size: .82rem;
            box-shadow: 0 2px 5px rgba(224, 112, 0, .4);
        }
        #ge-engine-final .time-badge {
            display: inline-flex; align-items: center; gap: 5px;
            background: var(--accent-time); color: #fff;
            font-weight: 700; border-radius: 12px;
            padding: 6px 12px; font-size: .85rem;
        }
        #ge-engine-final .time-badge .tb-icon { font-size: .9rem; }
    """,
    "diadesorte": """
        #ge-engine-final .dez-ball {
            display: inline-flex; align-items: center; justify-content: center;
            width: 36px; height: 36px; border-radius: 50%;
            background: var(--accent); color: #2d2d2d;
            font-weight: 800; font-size: .82rem;
            box-shadow: 0 2px 5px rgba(230, 168, 0, .4);
        }
        #ge-engine-final .mes-badge {
            display: inline-flex; align-items: center; gap: 5px;
            font-weight: 700; border-radius: 12px;
            padding: 6px 12px; font-size: .85rem;
            color: #fff !important;
        }
        #ge-engine-final .mes-badge:not([class*="mes-nome-"]) {
            background: #6c757d !important;
        }
    """,
}

BALL_CLASSES = {
    "lotofacil": {"dezena": "dez-ball", "extra": None},
    "supersete": {"dezena": "coluna-badge", "extra": None},
    "lotomania": {"dezena": "dez-ball", "extra": None},
    "quina": {"dezena": "dez-ball", "extra": None},
    "megasena": {"dezena": "dez-ball", "extra": None},
    "maismilionaria": {"dezena": "dez-ball", "trevo": "trevo-ball", "extra": "trevo"},
    "duplasena": {"dezena": "dez-ball", "extra": None},
    "timemania": {"dezena": "dez-ball", "extra": "time", "extra_class": "time-badge"},
    "diadesorte": {"dezena": "dez-ball", "extra": "mes", "extra_class": "mes-badge"},
}


def get_ball_ui(modality_key: str):
    return {
        "css": BALL_STYLES.get(modality_key, BALL_STYLES["megasena"]),
        "classes": BALL_CLASSES.get(modality_key, BALL_CLASSES["megasena"]),
    }
