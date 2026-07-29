# -*- coding: utf-8 -*-
"""Configuração centralizada de menus — estrutura idêntica, textos por modalidade."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

# Títulos do item Sniper no menu Análise (padrão por modalidade).
SNIPER_MENU_TITLE_PADRAO = "Sniper por Dezenas"
SNIPER_MENU_TITLES: Dict[str, str] = {
    "lotofacil": "Sniper por Posição",
    "supersete": "Sniper por Colunas",
    "diadesorte": "Sniper por Dezenas + Mês da Sorte",
    "timemania": "Sniper por Dezenas + Timemania",
    "maismilionaria": "Sniper por Dezenas + Trevo",
}


def sniper_menu_title(modality_key: str) -> str:
    return SNIPER_MENU_TITLES.get(modality_key, SNIPER_MENU_TITLE_PADRAO)


def _comportamento_nav(suffix: str, desc: str) -> Dict[str, Any]:
    comp = {
        "href": "/geradores-elite/comportamento-apostas/",
        "title": "Comportamento → Apostas",
        "desc": desc,
        "icon": "fas fa-chart-line",
    }
    return {
        "analise_extras": [{
            "title": f"Comportamento {suffix}",
            "desc": desc,
            "href": "/geradores-elite/comportamento-apostas/",
            "icon": "fas fa-chart-line",
            "icon_bg": "#e8f4fd",
            "icon_color": "#1565c0",
        }],
        "geradores_elite": {
            "items": [
                {
                    "href": "/geradores-elite/engine-final/",
                    "title": "Engine Final",
                    "desc": "Gerador pensante com análises integradas",
                    "icon": "fas fa-brain",
                },
                {
                    "href": "/geradores-elite/repeticao-apostas/",
                    "title": "Repetição → Apostas",
                    "desc": "Gerador baseado na repetição entre concursos",
                    "icon": "fas fa-dice",
                },
                {
                    "href": "/geradores-elite/apostas-inteligentes/",
                    "title": "Sniper → Apostas",
                    "desc": "Evidências · automático ou manual",
                    "icon": "fas fa-crosshairs",
                },
                comp,
                {
                    "href": "/geradores-elite/construtor-construcoes/",
                    "title": "Construtor de Construções",
                    "desc": "Mesmo conjunto-base · múltiplas engenharias",
                    "icon": "fas fa-layer-group",
                },
            ],
        },
    }


_DEFAULT = {
    "sync": {
        "title": "Sincronizar Dados",
        "desc": "Atualiza o banco via API da Caixa",
    },
    "comparar": {
        "title": "Comparar concursos",
        "desc": "Dois volantes lado a lado — só sorteios reais",
    },
    "repeticao": {
        "title": "Repetição entre concursos",
        "desc": "Freq. de repetição, par/ímpar e tendência de permanência",
    },
    "stats": {
        "title": "Análise Estatística",
        "desc": "Frequência e atraso das dezenas",
        "href": "/analise/",
        "icon": "fas fa-table-list",
        "icon_bg": "#eafaf1",
        "icon_color": "#196f3d",
    },
    "sniper": {
        "title": SNIPER_MENU_TITLE_PADRAO,
        "desc": "Frequência, atraso e repetição entre concursos",
        "href": "/analise/",
        "icon": "fas fa-crosshairs",
        "icon_bg": "#fad7d7",
        "icon_color": "#8b1a1a",
    },
    "modelos": {
        "badge": "6 MODELOS",
        "desc": "Conservador, Atraso, Frequência...",
        "href": "/modelos/",
    },
    "backtesting": {
        "title": "Backtesting Histórico",
        "desc": "Qual modelo mais acertou?",
        "href": "/modelos/#pane-bt",
    },
    "geradores_elite": {
        "title": "Geradores de Elite",
        "items": [
            {
                "href": "/geradores-elite/engine-final/",
                "title": "Engine Final",
                "desc": "Gerador pensante com análises integradas",
                "icon": "fas fa-brain",
            },
            {
                "href": "/geradores-elite/repeticao-apostas/",
                "title": "Repetição → Apostas",
                "desc": "Gerador baseado na repetição entre concursos",
                "icon": "fas fa-dice",
            },
            {
                "href": "/geradores-elite/apostas-inteligentes/",
                "title": "Sniper → Apostas",
                "desc": "Evidências · automático ou manual",
                "icon": "fas fa-crosshairs",
            },
        ],
    },
    "dados_extras": [],
    "analise_extras": [],
    "desdobramento": {
        "mode": "single",
        "href": "/desdobramento/",
        "title": "Desdobramentos",
    },
}

_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "lotofacil": {
        "stats": {
            "title": "Atrasos Posicionais",
            "desc": "Ranking de atraso por posição (P1–P15)",
            "href": "/analise/atrasos",
            "icon": "fas fa-hourglass-half",
            "icon_bg": "#fff3cd",
            "icon_color": "#856404",
        },
        "repeticao": {
            "desc": "Freq. de repetição e par/ímpar entre concursos",
        },
        "sniper": {
            "href": "/analise/atrasos",
            "desc": "Por posição P1–P15 · rank vertical",
        },
        "modelos": {
            "badge": "5 MODELOS",
            "desc": "Conservador, Núcleo Forte, Rotação...",
        },
        "backtesting": {
            "desc": "Qual modelo mais pontuou no passado?",
        },
        "desdobramento": {
            "mode": "dropdown",
            "title": "Desdobramentos",
            "items": [
                {
                    "href": "/desdobramento/",
                    "title": "Desdobramento Inteligente",
                    "desc": "Fechamento de 16 dezenas (padrão)",
                    "icon": "fas fa-sparkles",
                },
                {
                    "href": "/desdobramento-especial/",
                    "title": "Lotofácil da Independência",
                    "desc": "PAR/ÍMPAR por colunas — 6 a 10 dezenas",
                    "icon": "fas fa-flag",
                },
            ],
        },
        "analise_extras": [
            {
                "title": "Comportamento LF",
                "desc": "PA · PR · RT · MO · SQ · M3 · FB → apostas",
                "href": "/geradores-elite/comportamento-apostas/",
                "icon": "fas fa-chart-line",
                "icon_bg": "#e8f4fd",
                "icon_color": "#1565c0",
            },
        ],
        "geradores_elite": {
            "items": [
                {
                    "href": "/geradores-elite/engine-final/",
                    "title": "Engine Final",
                    "desc": "Gerador pensante com análises integradas",
                    "icon": "fas fa-brain",
                },
                {
                    "href": "/geradores-elite/repeticao-apostas/",
                    "title": "Repetição → Apostas",
                    "desc": "Gerador baseado na repetição entre concursos",
                    "icon": "fas fa-dice",
                },
                {
                    "href": "/geradores-elite/apostas-inteligentes/",
                    "title": "Sniper → Apostas",
                    "desc": "Evidências · automático ou manual",
                    "icon": "fas fa-crosshairs",
                },
                {
                    "href": "/geradores-elite/comportamento-apostas/",
                    "title": "Comportamento → Apostas",
                    "desc": "Padrões PA/PR/RT/MO/SQ/M3/FB · inteligente",
                    "icon": "fas fa-chart-line",
                },
                {
                    "href": "/geradores-elite/construtor-construcoes/",
                    "title": "Construtor de Construções",
                    "desc": "Mesmo conjunto-base · múltiplas engenharias",
                    "icon": "fas fa-layer-group",
                },
            ],
        },
    },
    "diadesorte": {
        "sync": {"desc": "Sorteios da Caixa"},
        "stats": {"desc": "Freq/atraso 31 dez + 12 meses"},
        "sniper": {"desc": "Dezenas e mês da sorte · heatmap"},
        "modelos": {"badge": "6", "desc": "7 dez + 1 mês por aposta"},
        "backtesting": {"desc": "Prêmios de 4 a 7 dezenas + mês"},
        "analise_extras": [
            {
                "title": "Resultados & Padrões",
                "desc": "Concursos reais · perfil · combinações · tubular (abre GC/Elite)",
                "href": "/analise/analises-inteligentes/",
                "icon": "fas fa-table-list",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
            {
                "title": "Análises Gerais",
                "desc": "Classificação · Diferencial Cruzado · Soma dígitos · Dígitos utilizados",
                "href": "/analise/analises-gerais/",
                "icon": "fas fa-microscope",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
            {
                "title": "Análise de Somas e Dígitos",
                "desc": "Soma das dezenas · dígitos distintos · tabelas de frequência",
                "href": "/analise/somas-digitos/",
                "icon": "fas fa-calculator",
                "icon_bg": "#fff8e1",
                "icon_color": "#c08b00",
            },
            {
                "title": "Análise por Posição",
                "desc": "Matriz 01–31 · ordem oficial · dígitos e soma",
                "href": "/analise/por-posicao/",
                "icon": "fas fa-table-cells",
                "icon_bg": "#fff8e1",
                "icon_color": "#664a00",
            },
            {
                "title": "Concentração de Acertos",
                "desc": "Experimental — maximizar acertos em uma aposta",
                "href": "/analise/concentracao-acertos/",
                "icon": "fas fa-bullseye",
                "icon_bg": "#fff8e1",
                "icon_color": "#664a00",
            },
            {
                "title": "Análise de Ciclos das Dezenas",
                "desc": "Ciclo atual · métricas · inteligência operacional",
                "href": "/analise/ciclo-cobertura/",
                "icon": "fas fa-sync-alt",
                "icon_bg": "#e7f1ff",
                "icon_color": "#0d6efd",
            },
            {
                "title": "Análise Comportamental",
                "desc": "Geral · Vencedores · Acumulados — PA/PR/RT/MO/MS",
                "href": "/analise/comportamento/",
                "icon": "fas fa-chart-pie",
                "icon_bg": "#e8f4fd",
                "icon_color": "#1565c0",
            },
            {
                "title": "Comportamento DS",
                "desc": "Gerador — PA · PR · RT · MO · MS → apostas",
                "href": "/geradores-elite/comportamento-apostas/",
                "icon": "fas fa-chart-line",
                "icon_bg": "#fff8e1",
                "icon_color": "#f57f17",
            },
        ],
        "geradores_elite": {
            "items": [
                {
                    "href": "/geradores-elite/engine-final/",
                    "title": "Engine Final",
                    "desc": "Gerador pensante com análises integradas",
                    "icon": "fas fa-brain",
                },
                {
                    "href": "/geradores-elite/gerador-gc/",
                    "title": "Gerador Pro / GC",
                    "desc": "gcN · amostragem no pool de dígitos (mín. 3)",
                    "icon": "fas fa-magic",
                },
                {
                    "href": "/geradores-elite/gerador-elite/",
                    "title": "Gerador Elite",
                    "desc": "Geração por quantidade de dígitos (3d–9d)",
                    "icon": "fas fa-brain",
                },
                {
                    "href": "/geradores-elite/repeticao-apostas/",
                    "title": "Repetição → Apostas",
                    "desc": "Gerador baseado na repetição entre concursos",
                    "icon": "fas fa-dice",
                },
                {
                    "href": "/geradores-elite/ciclo-apostas/",
                    "title": "Ciclo → Apostas",
                    "desc": "2+1 · Ritmo de Evolução (análise oficial)",
                    "icon": "fas fa-sync-alt",
                },
                {
                    "href": "/geradores-elite/gerador-por-posicao/",
                    "title": "Análise por Posição → Apostas",
                    "desc": "Matriz 01–31 · ordem oficial · dígitos e soma",
                    "icon": "fas fa-table-cells",
                },
                {
                    "href": "/geradores-elite/gerador-concentracao/",
                    "title": "Gerador por Concentração",
                    "desc": "Experimental — pool 16/18/20 dezenas · concentração de acertos",
                    "icon": "fas fa-bullseye",
                },
                {
                    "href": "/geradores-elite/apostas-inteligentes/",
                    "title": "Sniper → Apostas",
                    "desc": "Evidências · automático ou manual",
                    "icon": "fas fa-crosshairs",
                },
                {
                    "href": "/geradores-elite/comportamento-apostas/",
                    "title": "Comportamento → Apostas",
                    "desc": "Padrões PA/PR/RT/MO/MS · inteligente",
                    "icon": "fas fa-chart-line",
                },
                {
                    "href": "/geradores-elite/construtor-construcoes/",
                    "title": "Construtor de Construções",
                    "desc": "Pool dezenas · pool dígitos · múltiplas engenharias",
                    "icon": "fas fa-layer-group",
                },
                {
                    "href": "/geradores-elite/gerador-digitos-inteligente/",
                    "title": "Gerador Inteligente por Dígitos",
                    "desc": "Pool 0–9 · combinações · export TXT para apostar",
                    "icon": "fas fa-brain",
                },
            ],
        },
        "dados_extras": [
            {
                "title": "Mês da Sorte",
                "desc": "Freq. e atraso dos 12 meses",
                "href": "/analise/#mes",
                "icon": "fas fa-calendar-days",
                "icon_bg": "#fff3cd",
                "icon_color": "#856404",
            },
        ],
    },
    "lotomania": {
        "stats": {"desc": "Frequência e atraso — 100 dezenas"},
        "comparar": {"desc": "Dois volantes 10×10 — só sorteios reais"},
        "sniper": {"desc": "100 dezenas · heatmap 10×10"},
        "modelos": {"desc": "Conservador, Atraso, Freq, Misto..."},
        **_comportamento_nav("LM", "Perfil das 20 sorteadas → apostas de 50"),
        "dados_extras": [
            {
                "title": "Repetição Consecutiva",
                "desc": "Dezenas que repetem entre concursos seguidos",
                "href": "/analise/#repconsec",
                "icon": "fas fa-arrows-rotate",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
        ],
    },
    "quina": {
        "stats": {"desc": "Frequência e atraso — 80 dezenas"},
        "sniper": {"desc": "80 dezenas · heatmap e repetição"},
        **_comportamento_nav("QN", "PA · PR · RT · MO · SQ → apostas"),
        "desdobramento": {
            "mode": "dropdown",
            "title": "Desdobramentos",
            "items": [
                {
                    "href": "/desdobramento/",
                    "title": "Desdobramento Inteligente",
                    "desc": "Fechamento de 16 dezenas (padrão)",
                    "icon": "fas fa-sparkles",
                },
                {
                    "href": "/desdobramento-especial/",
                    "title": "Quina de São João",
                    "desc": "PAR/ÍMPAR por colunas — 5 a 15 dezenas",
                    "icon": "fas fa-sun",
                },
            ],
        },
        "dados_extras": [
            {
                "title": "Repetição Consecutiva",
                "desc": "Dezenas que repetem entre concursos seguidos",
                "href": "/analise/#repconsec",
                "icon": "fas fa-arrows-rotate",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
        ],
    },
    "megasena": {
        "stats": {"desc": "Frequência e atraso — 60 dezenas"},
        "sniper": {"desc": "60 dezenas · heatmap e repetição"},
        "analise_extras": [
            {
                "title": "Comportamento MS",
                "desc": "PA · PR · RT · MO · SQ → apostas",
                "href": "/geradores-elite/comportamento-apostas/",
                "icon": "fas fa-chart-line",
                "icon_bg": "#e8f4fd",
                "icon_color": "#1565c0",
            },
        ],
        "geradores_elite": {
            "items": [
                {
                    "href": "/geradores-elite/engine-final/",
                    "title": "Engine Final",
                    "desc": "Gerador pensante com análises integradas",
                    "icon": "fas fa-brain",
                },
                {
                    "href": "/geradores-elite/repeticao-apostas/",
                    "title": "Repetição → Apostas",
                    "desc": "Gerador baseado na repetição entre concursos",
                    "icon": "fas fa-dice",
                },
                {
                    "href": "/geradores-elite/apostas-inteligentes/",
                    "title": "Sniper → Apostas",
                    "desc": "Evidências · automático ou manual",
                    "icon": "fas fa-crosshairs",
                },
                {
                    "href": "/geradores-elite/comportamento-apostas/",
                    "title": "Comportamento → Apostas",
                    "desc": "Padrões PA/PR/RT/MO/SQ · inteligente",
                    "icon": "fas fa-chart-line",
                },
                {
                    "href": "/geradores-elite/construtor-construcoes/",
                    "title": "Construtor de Construções",
                    "desc": "Mesmo conjunto-base · múltiplas engenharias",
                    "icon": "fas fa-layer-group",
                },
            ],
        },
        "dados_extras": [
            {
                "title": "Repetição Consecutiva",
                "desc": "Dezenas que repetem entre concursos seguidos",
                "href": "/analise/#repconsec",
                "icon": "fas fa-arrows-rotate",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
        ],
        "desdobramento": {
            "mode": "dropdown",
            "title": "Desdobramentos",
            "items": [
                {
                    "href": "/desdobramento/",
                    "title": "Des1 — Desdobramento Inteligente",
                    "desc": "Fechamento matemático avançado de 16 dezenas",
                    "icon": "fas fa-sparkles",
                },
                {
                    "href": "/des2/",
                    "title": "Des2 — Desdobramento Estrutural",
                    "desc": "Desdobramento por colunas/finais com backtesting",
                    "icon": "fas fa-columns",
                },
                {
                    "href": "/desdobramento-especial/",
                    "title": "Mega da Virada",
                    "desc": "PAR/ÍMPAR por colunas — 6 a 15 dezenas",
                    "icon": "fas fa-champagne-glasses",
                },
            ],
        },
    },
    "maismilionaria": {
        "stats": {"desc": "Frequência e atraso — dezenas + trevos"},
        "sniper": {"desc": "Dezenas + trevos · heatmap"},
        **_comportamento_nav("+M", "PA · PR · RT · T1 · T2 → apostas"),
        "dados_extras": [
            {
                "title": "Análise de Trevos",
                "desc": "Freq. e atraso dos 6 trevos",
                "href": "/analise/#trevo",
                "icon": "fas fa-clover",
                "icon_bg": "#fff9e6",
                "icon_color": "#856404",
            },
        ],
        "desdobramento": {
            "mode": "dropdown",
            "title": "Desdobramentos",
            "items": [
                {
                    "href": "/desdobramento/",
                    "title": "Desdobramento Inteligente",
                    "desc": "16 dezenas (6) + fechamento de trevos",
                    "icon": "fas fa-sparkles",
                },
            ],
        },
    },
    "duplasena": {
        "sync": {"desc": "Baixa os 2 sorteios por concurso"},
        "stats": {"desc": "Frequência e atraso — 50 dezenas"},
        "sniper": {"desc": "50 dezenas · 1º ou 2º sorteio"},
        "comparar": {"desc": "Dois sorteios lado a lado — 1º ou 2º sorteio"},
        "modelos": {"desc": "Backtesting em 2 sorteios"},
        **_comportamento_nav("DS2", "1º sorteio · PA · PR · RT → apostas"),
        "backtesting": {
            "title": "Backtesting · Prêmio Duplo",
            "desc": "Simulação nos dois sorteios do concurso",
        },
        "desdobramento": {
            "mode": "dropdown",
            "title": "Desdobramentos",
            "items": [
                {
                    "href": "/desdobramento/",
                    "title": "Desdobramento Inteligente",
                    "desc": "Fechamento de 16 dezenas (padrão)",
                    "icon": "fas fa-sparkles",
                },
                {
                    "href": "/desdobramento-especial/",
                    "title": "Dupla de Páscoa",
                    "desc": "PAR/ÍMPAR por colunas — 6 a 15 dezenas",
                    "icon": "fas fa-egg",
                },
            ],
        },
        "dados_extras": [
            {
                "title": "2º Sorteio",
                "desc": "Freq/atraso separado do 2º sorteio",
                "href": "/analise/#sorteio2",
                "icon": "fas fa-layer-group",
                "icon_bg": "#ffe8e8",
                "icon_color": "#c62828",
            },
        ],
    },
    "timemania": {
        "sync": {"desc": "Dezenas + Time do Coração"},
        "stats": {"desc": "Frequência e atraso — 80 dezenas + times"},
        "sniper": {"desc": "80 dezenas + time · heatmap 8×10"},
        **_comportamento_nav("TM", "PA · PR · RT · TM → apostas"),
        "dados_extras": [
            {
                "title": "Ranking de Times",
                "desc": "80 times — freq. e atraso",
                "href": "/analise/#times",
                "icon": "fas fa-futbol",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
        ],
        "backtesting": {
            "title": "Backtesting · 8 prêmios",
            "desc": "Qual modelo rendeu mais?",
        },
    },
    "supersete": {
        "comparar": {"desc": "Dois sorteios lado a lado — 7 colunas · só reais"},
        "repeticao": {
            "desc": "Resumo repetição C1–C7 — link para o Sniper",
        },
        "stats": {
            "title": "Análise Estatística",
            "desc": "Atalho: mesmo destino do Sniper (freq/atraso)",
            "href": "/analise/",
            "icon": "fas fa-table-list",
            "icon_bg": "#eafaf1",
            "icon_color": "#196f3d",
        },
        "sniper": {
            "desc": "Por coluna C1–C7 · matriz 7×10 e repetição sequencial",
            "href": "/analise/",
        },
        "geradores_elite": {
            "items": [
                {
                    "href": "/geradores-elite/engine-final/",
                    "title": "Engine Final",
                    "desc": "Gerador pensante com análises integradas",
                    "icon": "fas fa-brain",
                },
                {
                    "href": "/geradores-elite/repeticao-apostas/",
                    "title": "Repetição → Apostas",
                    "desc": "Gerador genérico (repetição entre concursos)",
                    "icon": "fas fa-dice",
                },
                {
                    "href": "/geradores-elite/apostas-inteligentes/",
                    "title": "Sniper → Apostas",
                    "desc": "Evidências C1–C7 · automático ou manual",
                    "icon": "fas fa-crosshairs",
                },
                {
                    "href": "/geradores-elite/comportamento-apostas/",
                    "title": "Comportamento → Apostas",
                    "desc": "PA · RP · EX por coluna C1–C7",
                    "icon": "fas fa-chart-line",
                },
                {
                    "href": "/geradores-elite/construtor-construcoes/",
                    "title": "Construtor de Construções",
                    "desc": "Pools por coluna · engenharias posicionais",
                    "icon": "fas fa-layer-group",
                },
            ],
        },
        "analise_extras": [{
            "title": "Comportamento SS",
            "desc": "PA · RP · EX · SQ por coluna",
            "href": "/geradores-elite/comportamento-apostas/",
            "icon": "fas fa-chart-line",
            "icon_bg": "#e8f4fd",
            "icon_color": "#1565c0",
        }],
        "modelos": {"desc": "Conservador, Atraso, Frequência..."},
        "backtesting": {"desc": "Qual modelo mais acertou colunas?"},
        "dados_extras": [
            {
                "title": "Repetição de Dígitos",
                "desc": "Análise de duplas e trincas",
                "href": "/analise/#repeticoes",
                "icon": "fas fa-clone",
                "icon_bg": "#e0f2f1",
                "icon_color": "#00695c",
            },
        ],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_nav_config(modality_key: str) -> dict:
    cfg = deepcopy(_DEFAULT)
    if modality_key in _OVERRIDES:
        cfg = _deep_merge(cfg, _OVERRIDES[modality_key])
    cfg["key"] = modality_key
    if isinstance(cfg.get("sniper"), dict):
        cfg["sniper"]["title"] = sniper_menu_title(modality_key)
    _inject_posicao_nav(cfg, modality_key)
    _inject_analises_novas_nav(cfg, modality_key)
    return cfg


def _inject_analises_novas_nav(cfg: dict, modality_key: str) -> None:
    """Injeta Análises Gerais / Somas / Concentração / Comportamental e geradores DDS-paridade."""
    if modality_key == "diadesorte":
        return  # já listados manualmente em _OVERRIDES

    try:
        from configuracoes.temas_modalidade import get_tema

        tema = get_tema(modality_key)
        accent = tema["accent"]
        accent_light = tema["accent_light"]
        primary_dark = tema["primary_dark"]
    except Exception:
        accent, accent_light, primary_dark = "#672666", "#f3ecf8", "#4a1c4a"

    extras = cfg.setdefault("analise_extras", [])
    ge = cfg.setdefault("geradores_elite", {})
    items = ge.setdefault("items", [])

    try:
        from analise_estudos.specs import tem_analise_estudos
    except ImportError:
        tem_analise_estudos = lambda _k: False  # noqa: E731

    try:
        from concentracao_acertos.specs import tem_concentracao_acertos
    except ImportError:
        tem_concentracao_acertos = lambda _k: False  # noqa: E731

    try:
        from geradores_elite.inteligente import tem_gerador_comportamento
    except ImportError:
        tem_gerador_comportamento = lambda _k: False  # noqa: E731

    novos_analise = []
    # Paridade com Dia de Sorte: Resultados & Padrões
    novos_analise.append({
        "title": "Resultados & Padrões",
        "desc": "Concursos reais · perfil · combinações · tubular (abre GC/Elite)",
        "href": "/analise/analises-inteligentes/",
        "icon": "fas fa-table-list",
        "icon_bg": "#e8f5e9",
        "icon_color": "#2e7d32",
    })
    if tem_analise_estudos(modality_key):
        novos_analise.extend([
            {
                "title": "Análises Gerais",
                "desc": "Classificação · Diferencial Cruzado · Soma dígitos · Dígitos utilizados",
                "href": "/analise/analises-gerais/",
                "icon": "fas fa-microscope",
                "icon_bg": "#e8f5e9",
                "icon_color": "#2e7d32",
            },
            {
                "title": "Análise de Somas e Dígitos",
                "desc": "Soma das dezenas · dígitos distintos · tabelas de frequência",
                "href": "/analise/somas-digitos/",
                "icon": "fas fa-calculator",
                "icon_bg": accent_light,
                "icon_color": accent,
            },
        ])
    if tem_concentracao_acertos(modality_key):
        novos_analise.append({
            "title": "Concentração de Acertos",
            "desc": "Experimental — maximizar acertos em uma aposta",
            "href": "/analise/concentracao-acertos/",
            "icon": "fas fa-bullseye",
            "icon_bg": accent_light,
            "icon_color": primary_dark,
        })
    if tem_gerador_comportamento(modality_key):
        novos_analise.append({
            "title": "Análise Comportamental",
            "desc": "PA · PR · RT · MO · SQ — janelas e bases",
            "href": "/analise/comportamento/",
            "icon": "fas fa-chart-pie",
            "icon_bg": "#e8f4fd",
            "icon_color": "#1565c0",
        })

    # Inserir após Análise por Posição (se existir), senão no início
    insert_at = 0
    for i, it in enumerate(extras):
        if it.get("href") == "/analise/por-posicao/":
            insert_at = i + 1
            break
    for item in reversed(novos_analise):
        if not any(x.get("href") == item["href"] for x in extras):
            extras.insert(insert_at, item)

    # Geradores paridade com Dia de Sorte (exceto itens exclusivos de MS)
    novos_ge = [
        {
            "href": "/geradores-elite/gerador-gc/",
            "title": "Gerador Pro / GC",
            "desc": "gcN · amostragem no pool de dígitos (mín. 3)",
            "icon": "fas fa-magic",
            "after": "/geradores-elite/engine-final/",
        },
        {
            "href": "/geradores-elite/gerador-elite/",
            "title": "Gerador Elite",
            "desc": "Geração por quantidade de dígitos (3d–9d)",
            "icon": "fas fa-brain",
            "after": "/geradores-elite/gerador-gc/",
        },
        {
            "href": "/geradores-elite/gerador-digitos-inteligente/",
            "title": "Gerador Inteligente por Dígitos",
            "desc": "Pool 0–9 · combinações · export TXT para apostar",
            "icon": "fas fa-brain",
            "after": None,
        },
    ]
    if tem_concentracao_acertos(modality_key):
        novos_ge.insert(2, {
            "href": "/geradores-elite/gerador-concentracao/",
            "title": "Gerador por Concentração",
            "desc": "Pool restrito · concentração de acertos",
            "icon": "fas fa-bullseye",
            "after": "/geradores-elite/gerador-por-posicao/",
        })

    for item in novos_ge:
        href = item["href"]
        if any(x.get("href") == href for x in items):
            continue
        after = item.get("after")
        pos = len(items)
        if after:
            for i, it in enumerate(items):
                if it.get("href") == after:
                    pos = i + 1
                    break
        clean = {k: v for k, v in item.items() if k != "after"}
        items.insert(pos, clean)


def _inject_posicao_nav(cfg: dict, modality_key: str) -> None:
    try:
        from posicao_analise.specs import tem_posicao_analise, posicao_nav_desc
    except ImportError:
        return
    if not tem_posicao_analise(modality_key):
        return
    if modality_key == "diadesorte":
        return

    desc = posicao_nav_desc(modality_key)
    analise_item = {
        "title": "Análise por Posição",
        "desc": desc,
        "href": "/analise/por-posicao/",
        "icon": "fas fa-table-cells",
        "icon_bg": "#fff8e1",
        "icon_color": "#664a00",
    }
    extras = cfg.setdefault("analise_extras", [])
    if not any(x.get("href") == analise_item["href"] for x in extras):
        extras.insert(0, analise_item)

    ge = cfg.setdefault("geradores_elite", {})
    items = ge.setdefault("items", [])
    gerador_item = {
        "href": "/geradores-elite/gerador-por-posicao/",
        "title": "Análise por Posição → Apostas",
        "desc": desc,
        "icon": "fas fa-table-cells",
    }
    if not any(x.get("href") == gerador_item["href"] for x in items):
        insert_at = 2 if len(items) >= 2 else len(items)
        items.insert(insert_at, gerador_item)
