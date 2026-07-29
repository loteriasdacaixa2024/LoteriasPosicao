# Metadados por modalidade — fatores de bolão proporcionais ao preço simples.
# Valores editáveis ficam em config_modalidades.json (preco_simples).

MODALITIES = {
    "lotofacil": {
        "key": "lotofacil",
        "nome": "Lotofácil",
        "porta": 5152,
        "api_slug": "lotofacil",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Lotofacil.aspx",
        "preco_simples_default": 3.50,
        "aposta": {"simples": 15, "min": 15, "max": 20, "universo": "01 a 25"},
        "bolao": {
            "fator_valor_minimo": 12.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "diadesorte": {
        "key": "diadesorte",
        "nome": "Dia de Sorte",
        "porta": 5153,
        "api_slug": "diadesorte",
        "api_url": "https://servicebus2.caixa.gov.br/portaldeloterias/api/diadesorte",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Dia-de-Sorte.aspx",
        "preco_simples_default": 2.50,
        "aposta": {"simples": 7, "min": 7, "max": 15, "universo": "01 a 31", "extra": "Mês da Sorte"},
        "bolao": {
            "fator_valor_minimo": 10.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 80,
        },
    },
    "lotomania": {
        "key": "lotomania",
        "nome": "Lotomania",
        "porta": 5154,
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Lotomania.aspx",
        "preco_simples_default": 3.00,
        "aposta": {"simples": 50, "min": 50, "max": 50, "universo": "00 a 99"},
        "bolao": {
            "fator_valor_minimo": 50.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "quina": {
        "key": "quina",
        "nome": "Quina",
        "porta": 5155,
        "api_slug": "quina",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Quina.aspx",
        "preco_simples_default": 3.00,
        "aposta": {"simples": 5, "min": 5, "max": 15, "universo": "01 a 80"},
        "bolao": {
            "fator_valor_minimo": 8.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "megasena": {
        "key": "megasena",
        "nome": "Mega-Sena",
        "porta": 5156,
        "api_slug": "megasena",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx",
        "preco_simples_default": 6.00,
        "aposta": {"simples": 6, "min": 6, "max": 20, "universo": "01 a 60"},
        "bolao": {
            "fator_valor_minimo": 8.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "maismilionaria": {
        "key": "maismilionaria",
        "nome": "+Milionária",
        "porta": 5157,
        "api_slug": "maismilionaria",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Mais-Milionaria.aspx",
        "preco_simples_default": 6.00,
        "aposta": {"simples": 6, "min": 6, "max": 12, "universo": "01 a 50", "extra": "2 a 6 Trevos"},
        "bolao": {
            "fator_valor_minimo": 10.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "duplasena": {
        "key": "duplasena",
        "nome": "Dupla Sena",
        "porta": 5158,
        "api_slug": "duplasena",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Dupla-Sena.aspx",
        "preco_simples_default": 3.00,
        "aposta": {"simples": 6, "min": 6, "max": 15, "universo": "01 a 50", "extra": "2 sorteios"},
        "bolao": {
            "fator_valor_minimo": 8.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "timemania": {
        "key": "timemania",
        "nome": "Timemania",
        "porta": 5159,
        "api_slug": "timemania",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Timemania.aspx",
        "preco_simples_default": 3.50,
        "aposta": {"simples": 10, "min": 10, "max": 10, "universo": "01 a 80", "extra": "Time do Coração"},
        "bolao": {
            "fator_valor_minimo": 10.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 100,
        },
    },
    "supersete": {
        "key": "supersete",
        "nome": "Super Sete",
        "porta": 5160,
        "api_slug": "supersete",
        "link_caixa": "https://loterias.caixa.gov.br/Paginas/Super-Sete.aspx",
        "preco_simples_default": 3.00,
        "aposta": {"simples": 7, "min": 7, "max": 7, "universo": "7 colunas (0-9)"},
        "bolao": {
            "fator_valor_minimo": 7.0,
            "fator_por_cota": 1.0,
            "cotas_min": 2,
            "cotas_max": 80,
        },
    },
}

CENTRAL_PORT = 8083

# Concursos especiais com numeração paralela (venda no site; sorteio em data própria).
# A API /{slug}/ retorna só o último da série regular — ex.: Quina 7039, não o 7051 (São João).
CONCURSOS_ESPECIAIS = {
    "quina": [
        {
            "concurso": 7051,
            "label": "Quina de São João 2026",
            "data_sorteio": "27/06/2026",
        },
    ],
}
