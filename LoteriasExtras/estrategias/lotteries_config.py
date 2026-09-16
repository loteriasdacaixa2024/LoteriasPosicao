# --- LOTTERIES CONFIGURATION MASTER -----
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class GridConfig:
    rows: int
    columns: int
    layout: List[str]

@dataclass
class ColorPalette:
    primary: str
    secondary: str
    accent: str
    background: str
    scale: Dict[str, str] = field(default_factory=dict)  # Stores 0% to 100% variations
    pares: str = "#2ecc71"
    impares: str = "#f39c12"
    repetidos: str = "#8e44ad"
    sequencias: str = "#000000"
    meses: Dict[int, str] = field(default_factory=dict)
    times: str = "#FFF600" # Default Yellow for Timemania/Teams

@dataclass
class TabConfig:
    name: str
    sub_tabs: List[str]

@dataclass
class LotteryConfig:
    slug: str
    name: str
    icon: str
    total_numbers: int
    draw_numbers: int
    port: int
    database: str
    api_endpoint: str
    caixa_api_url: str
    folder: str
    grid: GridConfig
    colors: ColorPalette
    tabs: Dict[str, TabConfig]
    logo: str = ""
    game_type: str = "standard"  # standard, digit, special, football
    extra_info: Dict[str, Any] = field(default_factory=dict)
    prizes: Dict[int, str] = field(default_factory=dict)
    extra_cols: List[str] = field(default_factory=list)

    def get_db_path(self) -> str:
        return f"data/{self.slug}.db"

    def get_folder_path(self) -> str:
        return self.folder

    def get_patterns_file(self) -> str:
        """Returns the path to the Padrões file."""
        clean_name = self.name.replace(" ", "").replace("+", "Mais").replace("á", "a")
        if self.slug == "dia_de_sorte": return f"{self.folder}/Padrões-DiaDesorte.txt"
        return f"{self.folder}/Padrões-{clean_name}.txt"

    def get_campos_file(self) -> str:
        """Returns the path to the Campos file."""
        clean_name = self.name.replace(" ", "").replace("+", "Mais")
        if self.slug == "maismilionaria": return f"{self.folder}/Campos-MaisMilionária.txt"
        if self.slug == "dia_de_sorte": return f"{self.folder}/Campos-DiadDeSorte.txt"
        return f"{self.folder}/Campos-{clean_name}.txt"

# --- DEFAULT TABS ---
DEFAULT_LAYERS = ["Camada 1", "Camada 2", "Camada 3", "Camada 4", "Camada 5", "Camada 6"]
DEFAULT_STRATEGIES = ["Estratégia 1", "Estratégia 2", "Estratégia 3", "Estratégia 4", "Estratégia 5", "Estratégia 6", "Estratégia 7", "Estratégia 8"]

def create_default_tabs(layers=None, strategies=None):
    return {
        "analysis": TabConfig(name="Análise", sub_tabs=layers or DEFAULT_LAYERS),
        "strategies": TabConfig(name="Estratégia", sub_tabs=strategies or DEFAULT_STRATEGIES)
    }

# --- LOTTERY DEFINITIONS ---

LOTOFACIL = LotteryConfig(
    slug="lotofacil",
    name="Lotofácil",
    icon="🟣",
    # logo="static/img/logo_lotofacil.png",
    total_numbers=25,
    draw_numbers=15,
    port=5565,
    database="data/lotofacil.db",
    api_endpoint="/lotofacil",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil",
    folder="lotofacil",
    grid=GridConfig(rows=3, columns=10, layout=["01-10", "11-20", "21-25"]),
    colors=ColorPalette(
        primary="#7B1FA2",
        secondary="#BA45B8",
        accent="#953793",
        background="#F8ECF8",
        pares="#2ecc71",
        impares="#f39c12",
        repetidos="#8e44ad",
        sequencias="#000000",
        scale={
            "100%": "#ffffff", "95%": "#f8ecf8", "90%": "#f1daf1", "85%": "#eac7ea",
            "80%": "#e3b5e3", "75%": "#dda2dc", "70%": "#d68fd5", "65%": "#cf7dcd",
            "60%": "#c86ac6", "55%": "#c157bf", "50%": "#ba45b8", "45%": "#a83ea6",
            "40%": "#953793", "35%": "#823081", "30%": "#70296f", "28%": "#672666",
            "25%": "#5d225c", "20%": "#4a1c4a", "15%": "#381537", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(
        layers=["Frequência", "Estrutura", "Composição", "Repetição", "Padrões", "Temporal"]
    ),
    extra_info={"remote_logo": "https://i.postimg.cc/s2P0JvqG/logo-Lotofacil.png"},
    prizes={15: '15 Pts', 14: '14 Pts', 13: '13 Pts', 12: '12 Pts', 11: '11 Pts'}
)

MEGASENA = LotteryConfig(
    slug="megasena",
    name="Mega-Sena",
    icon="🟢",
    # logo="static/img/logo_megasena.png",
    total_numbers=60,
    draw_numbers=6,
    port=5568,
    database="data/megasena.db",
    api_endpoint="/megasena",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
    folder="megasena",
    grid=GridConfig(rows=6, columns=10, layout=["01-10", "11-20", "21-30", "31-40", "41-50", "51-60"]),
    colors=ColorPalette(
        primary="#1B9A67",
        secondary="#2E7D32",
        accent="#4CAF50",
        background="#E8F5E9",
        scale={
            "100%": "#ffffff", "95%": "#e9fbf4", "90%": "#d4f7e9", "85%": "#bef4de",
            "80%": "#a8f0d3", "75%": "#93ecc8", "70%": "#7de8bd", "65%": "#67e4b2",
            "60%": "#52e0a7", "55%": "#3cdd9c", "50%": "#26d991", "45%": "#22c383",
            "40%": "#1fad74", "35%": "#1b9a67", "30%": "#178257", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={"remote_logo": "https://i.postimg.cc/VkSZr7z6/megasena.png"},
    prizes={6: 'Sena', 5: 'Quina', 4: 'Quadra'}
)

QUINA = LotteryConfig(
    slug="quina",
    name="Quina",
    icon="🔵",
    # logo="static/img/logo_quina.png",
    total_numbers=80,
    draw_numbers=5,
    port=5567,
    database="data/quina.db",
    api_endpoint="/quina",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/quina",
    folder="quina",
    grid=GridConfig(rows=8, columns=10, layout=["01-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71-80"]),
    colors=ColorPalette(
        primary="#260184",
        secondary="#4903FC",
        accent="#9268FD",
        background="#EDE6FF",
        scale={
            "100%": "#ffffff", "95%": "#ede6ff", "90%": "#dbcdfe", "85%": "#c9b3fe",
            "80%": "#b69afe", "75%": "#a481fe", "70%": "#9268fd", "65%": "#804efd",
            "60%": "#6e35fd", "55%": "#5c1cfd", "50%": "#4903fc", "45%": "#4202e3",
            "40%": "#3b02ca", "35%": "#3302b1", "30%": "#2c0297", "26%": "#260184", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={"remote_logo": "https://i.postimg.cc/G3PvK6cN/quina.png"},
    prizes={5: 'Quina', 4: 'Quadra', 3: 'Terno', 2: 'Duque'}
)

LOTOMANIA = LotteryConfig(
    slug="lotomania",
    name="Lotomania",
    icon="🟠",
    # logo="static/img/logo_lotomania.png",
    total_numbers=100,
    draw_numbers=20,
    port=5569,
    database="data/lotomania.db",
    api_endpoint="/lotomania",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/lotomania",
    folder="lotomania",
    grid=GridConfig(rows=10, columns=10, layout=["00-09", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90-99"]),
    colors=ColorPalette(
        primary="#E68527",
        secondary="#FB8C00",
        accent="#FFA726",
        background="#FFF3E0",
        scale={
            "100%": "#ffffff", "95%": "#fcf2e8", "90%": "#fae6d1", "85%": "#f7d9bb",
            "80%": "#f4cca4", "75%": "#f2bf8d", "70%": "#efb376", "65%": "#eca65f",
            "60%": "#ea9948", "55%": "#e78c32", "53%": "#e68527", "50%": "#e4801b",
            "45%": "#cd7318", "40%": "#b76615", "35%": "#a05913", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={"remote_logo": "https://i.postimg.cc/BbM7Dk88/lotomania.png"},
    prizes={20: '20 Pts', 19: '19 Pts', 18: '18 Pts', 17: '17 Pts', 16: '16 Pts', 15: '15 Pts', 0: '0 Pts'}
)

TIMEMANIA = LotteryConfig(
    slug="timemania",
    name="Timemania",
    icon="🟡",
    # logo="static/img/logo_timemania.png",
    total_numbers=80,
    draw_numbers=7,
    port=5570,
    database="data/timemania.db",
    api_endpoint="/timemania",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/timemania",
    folder="timemania",
    grid=GridConfig(rows=8, columns=10, layout=["01-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71-80"]),
    colors=ColorPalette(
        primary="#FFF600",
        secondary="#12923D",
        accent="#FFF176",
        background="#FFFDE7",
        scale={
            "100%": "#ffffff", "50%": "#fff600", "32%": "#12923d", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    prizes={7: '7 Pts', 6: '6 Pts', 5: '5 Pts', 4: '4 Pts', 3: '3 Pts'},
    extra_info={
        "remote_logo": "https://i.postimg.cc/W4g9ShFc/timemania.png",
        "has_team": True
    },
    extra_cols=["time_coracao"]
)

DIA_DE_SORTE = LotteryConfig(
    slug="dia_de_sorte",
    name="Dia de Sorte",
    icon="🌟",
    # logo="static/img/logo_diadesorte.png",
    total_numbers=31,
    draw_numbers=7,
    port=5566,
    database="data/diadesorte.db",
    api_endpoint="/diadesorte",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/diadesorte",
    folder="diadesorte",
    grid=GridConfig(rows=4, columns=10, layout=["01-10", "11-20", "21-30", "31-31"]),
    colors=ColorPalette(
        primary="#D4B31A",
        secondary="#E3BE1C",
        accent="#FFD700",
        background="#FCF9E8",
        pares="#2ecc71",
        impares="#f39c12",
        repetidos="#8e44ad",
        sequencias="#000000",
        meses={
            1: "#FF5252", 2: "#FF4081", 3: "#E040FB", 4: "#7C4DFF",
            5: "#536DFE", 6: "#448AFF", 7: "#40C4FF", 8: "#18FFFF",
            9: "#64FFDA", 10: "#B2FF59", 11: "#FFEB3B", 12: "#FF9100"
        },
        scale={
            "100%": "#ffffff", "95%": "#fcf9e8", "90%": "#f9f2d2", "85%": "#f7ecbb",
            "80%": "#f4e5a4", "75%": "#f1df8e", "70%": "#eed877", "65%": "#ebd260",
            "60%": "#e9cb49", "55%": "#e6c533", "50%": "#e3be1c", "47%": "#d4b31a",
            "45%": "#ccab19", "40%": "#b69816", "35%": "#9f8514", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(
        layers=["Frequência", "Estrutura", "Composição", "Repetição", "Padrões", "Temporal"]
    ),
    extra_info={
        "remote_logo": "https://i.postimg.cc/3R2PytCp/diadesorte.png",
        "has_month": True
    },
    prizes={7: '7 Pts', 6: '6 Pts', 5: '5 Pts', 4: '4 Pts'},
    extra_cols=["mes_sorte"]
)

DUPLASENA = LotteryConfig(
    slug="duplasena",
    name="Dupla Sena",
    icon="🔴",
    # logo="static/img/logo_duplasena.png",
    total_numbers=50,
    draw_numbers=6,
    port=5571,
    database="data/duplasena.db",
    api_endpoint="/duplasena",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/duplasena",
    folder="duplasena",
    grid=GridConfig(rows=5, columns=10, layout=["01-10", "11-20", "21-30", "31-40", "41-50"]),
    colors=ColorPalette(
        primary="#BA184A",
        secondary="#E21D5C",
        accent="#EF5350",
        background="#FCE8EF",
        scale={
            "100%": "#ffffff", "95%": "#fce8ef", "90%": "#f9d2de", "85%": "#f6bbce",
            "50%": "#e21d5c", "41%": "#ba184a", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={
        "remote_logo": "https://i.postimg.cc/hPDHjbJz/dupla-sena.jpg",
        "has_second_draw": True
    },
    prizes={6: 'Sena', 5: 'Quina', 4: 'Quadra', 3: 'Terno'}
)

MAISMILIONARIA = LotteryConfig(
    slug="maismilionaria",
    name="+Milionária",
    icon="💎",
    # logo="static/img/logo_maismilionaria.png",
    total_numbers=50,
    draw_numbers=6,
    port=5572,
    database="data/maismilionaria.db",
    api_endpoint="/maismilionaria",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/maismilionaria",
    folder="maismilionaria",
    grid=GridConfig(rows=5, columns=10, layout=["01-10", "11-20", "21-30", "31-40", "41-50"]),
    colors=ColorPalette(
        primary="#31357C",
        secondary="#494EB6",
        accent="#AB47BC",
        background="#EDEDF8",
        scale={
            "100%": "#ffffff", "95%": "#ededf8", "50%": "#494eb6", "34%": "#31357c", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={
        "remote_logo": "https://i.postimg.cc/DywMFvD1/mais-Milionaria.png",
        "trevos": 6,
        "selection": {"numbers": 6, "trevos": 2}
    },
    prizes={6: '6 Pts', 5: '5 Pts', 4: '4 Pts'},
    extra_cols=["trevo1", "trevo2"]
)

SUPERSETE = LotteryConfig(
    slug="supersete",
    name="Super Sete",
    icon="7️⃣",
    # logo="static/img/logo_supersete.png",
    total_numbers=10,
    draw_numbers=7,
    port=5573,
    database="data/supersete.db",
    api_endpoint="/supersete",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/supersete",
    folder="supersete",
    game_type="digit",
    grid=GridConfig(rows=1, columns=10, layout=["0-9"]),
    colors=ColorPalette(
        primary="#A9CF46",
        secondary="#8E24AA",
        accent="#D9EAAE",
        background="#F6FAEB",
        scale={
            "100%": "#ffffff", "95%": "#f6faeb", "54%": "#a9cf46", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={
        "remote_logo": "https://i.postimg.cc/wBthkvvc/supersete.png",
        "columns": 7,
        "digits_per_column": 10
    },
    prizes={7: '7 Pts', 6: '6 Pts', 5: '5 Pts', 4: '4 Pts', 3: '3 Pts'}
)

FEDERAL = LotteryConfig(
    slug="federal",
    name="Federal",
    icon="🏦",
    # logo="static/img/logo_federal.png",
    total_numbers=5,
    draw_numbers=5,
    port=5574,
    database="data/federal.db",
    api_endpoint="/federal",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/federal",
    folder="federal",
    game_type="special",
    grid=GridConfig(rows=1, columns=5, layout=["00000-99999"]),
    colors=ColorPalette(
        primary="#0065B3",
        secondary="#4192BE",
        accent="#8DBED8",
        background="#E5F0F6",
        scale={
            "100%": "#ffffff", "93%": "#e5f0f6", "35%": "#0065b3", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={"remote_logo": "https://i.postimg.cc/cJnzjFzj/federal.png"}
)

LOTECA = LotteryConfig(
    slug="loteca",
    name="Loteca",
    icon="⚽",
    # logo="static/img/logo_loteca.png",
    total_numbers=14,
    draw_numbers=14,
    port=5575,
    database="data/loteca.db",
    api_endpoint="/loteca",
    caixa_api_url="https://servicebus2.caixa.gov.br/portaldeloterias/api/loteca",
    folder="loteca",
    game_type="football",
    grid=GridConfig(rows=14, columns=3, layout=["V-E-D"]),
    colors=ColorPalette(
        primary="#0066B3",
        secondary="#F81A03",
        accent="#0091FF",
        background="#E6F4FF",
        scale={
            "100%": "#ffffff", "35%": "#0066b3", "49%": "#f81a03", "0%": "#000000"
        }
    ),
    tabs=create_default_tabs(),
    extra_info={"remote_logo": "https://i.postimg.cc/pr21mRdb/loteca.png"}
)

# --- COLLECTIONS ---

LIST_LOTTERIES = [
    LOTOFACIL, DIA_DE_SORTE, QUINA, MEGASENA, LOTOMANIA,
    TIMEMANIA, DUPLASENA, MAISMILIONARIA, SUPERSETE,
    FEDERAL, LOTECA
]

# Modalidades da Central de Estratégias (ordem e portas 5565–5573)
# Modalidade       Porta  Pasta            Logo remoto (postimg)                                      App
# Lotofácil        5565   lotofacil        https://i.postimg.cc/s2P0JvqG/logo-Lotofacil.png           laboratório
# Dia de Sorte     5566   diadesorte       https://i.postimg.cc/3R2PytCp/diadesorte.png               laboratório
# Quina            5567   quina            https://i.postimg.cc/G3PvK6cN/quina.png                    laboratório
# Mega-Sena        5568   megasena         https://i.postimg.cc/VkSZr7z6/megasena.png                 laboratório
# Lotomania        5569   lotomania        https://i.postimg.cc/BbM7Dk88/lotomania.png                laboratório
# Timemania        5570   timemania        https://i.postimg.cc/W4g9ShFc/timemania.png                laboratório
# Dupla Sena       5571   duplasena        https://i.postimg.cc/hPDHjbJz/dupla-sena.jpg               laboratório
# Mais Milionária  5572   maismilionaria   https://i.postimg.cc/DywMFvD1/mais-Milionaria.png          laboratório
# Super Sete       5573   supersete        https://i.postimg.cc/wBthkvvc/supersete.png                app próprio
ESTRATEGIAS_SLUGS = [
    "lotofacil", "dia_de_sorte", "quina", "megasena", "lotomania",
    "timemania", "duplasena", "maismilionaria", "supersete"
]

PUBLIC_BASE_URL = "https://marciofernandomaia.com.br/estrategias"


def public_url(folder: str) -> str:
    """URL pública HTTPS da modalidade (pasta no reverse proxy)."""
    url = f"{PUBLIC_BASE_URL.rstrip('/')}/{str(folder).strip('/')}/"
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url

# Backward Compatibility Dictionary
LOTTERIES = { config.slug: {
    "slug": config.slug,
    "name": config.name,
    "icon": config.icon,
    "logo": config.logo,
    "total_numbers": config.total_numbers,
    "draw_numbers": config.draw_numbers,
    "port": config.port,
    "database": config.database,
    "api": config.api_endpoint,
    "caixa_api": config.caixa_api_url,
    "folder": config.folder,
    "game_type": config.game_type,
    "grid": {
        "rows": config.grid.rows,
        "columns": config.grid.columns,
        "layout": config.grid.layout
    },
    "colors": {
        "primary": config.colors.primary,
        "secondary": config.colors.secondary,
        "accent": config.colors.accent,
        "background": config.colors.background,
        "scale": config.colors.scale,
        "pares": config.colors.pares,
        "impares": config.colors.impares,
        "repetidos": config.colors.repetidos,
        "sequencias": config.colors.sequencias,
        "meses": config.colors.meses,
        "times": config.colors.times
    },
    "tabs": {
        tab_id: {"name": tab.name, "sub_tabs": tab.sub_tabs}
        for tab_id, tab in config.tabs.items()
    },
    "prizes": config.prizes,
    "extra": config.extra_info,
    "extra_cols": config.extra_cols
} for config in LIST_LOTTERIES }

# Backward Compatibility Global Mapping
PRIZE_TIERS = { config.slug: config.prizes for config in LIST_LOTTERIES }

def get_lottery_config(slug: str) -> Optional[LotteryConfig]:
    """Helper to get the full config object."""
    for config in LIST_LOTTERIES:
        if config.slug == slug:
            return config
    return None

def get_menu_items():
    """Returns a list of lotteries for menu generation."""
    return [{"slug": c.slug, "name": c.name, "icon": c.icon} for c in LIST_LOTTERIES]

#----------------------conferencias (portas reservadas)
#Lotofácil       → 5555 | Dia de Sorte     → 5556 | Quina          → 5557
#Mega-Sena       → 5558 | Lotomania        → 5559 | Timemania      → 5560
#Dupla Sena      → 5561 | Mais Milionária  → 5562 | Super Sete     → 5563
#----------------------estratégias (sequência oficial)
#Central         → 8084
#Lotofácil       → 5565 | Dia de Sorte     → 5566 | Quina          → 5567
#Mega-Sena       → 5568 | Lotomania        → 5569 | Timemania      → 5570
#Dupla Sena      → 5571 | Mais Milionária  → 5572 | Super Sete     → 5573
#Federal         → 5574 | Loteca           → 5575
#Ativas: as 9 de ESTRATEGIAS_SLUGS (5565–5573) + Central 8084
#----------------------------------------