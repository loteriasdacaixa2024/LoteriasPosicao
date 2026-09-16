import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

# Add parent directory to sys.path to access central config
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

try:
    from lotteries_config import LOTTERIES
    lotofacil_config = LOTTERIES["lotofacil"]
except ImportError:
    # Fallback default configuration if central config is missing
    lotofacil_config = {
        "name": "Lotofácil",
        "icon": "🟣",
        "port": 5565,
        "database": "data/lotofacil.db",
        "folder": "lotofacil",
        "caixa_api": "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil",
        "colors": {
            "primary": "#672666",
            "secondary": "#BA45B8",
            "accent": "#953793",
            "background": "#F8ECF8"
        }
    }

# =========================================
# IDENTIDADE DO APLICATIVO
# =========================================

APP_NAME = "Lotofácil Estratégias"
APP_VERSION = "1.0.0"
APP_TYPE = "Simulação Estatística Modular"
LOTTERY_NAME = lotofacil_config.get("name", "Lotofácil")

# =========================================
# SERVIDOR
# =========================================

HOST = "0.0.0.0"
PORT = lotofacil_config.get("port", 5565)

# =========================================
# AMBIENTE
# =========================================

ENV = os.getenv("FLASK_ENV", "production")
DEBUG = ENV in ("development", "dev")

# =========================================
# CACHE
# =========================================

CACHE_VERSION = "v1"
VERSION = "1.0"

# =========================================
# CAMINHOS
# =========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
# Alias for compatibility if needed
EXPORT_DIR = EXPORTS_DIR

folder = str(lotofacil_config.get("folder", ""))
DATABASE_PATH = str(lotofacil_config.get("database", os.path.join(DATA_DIR, "lotofacil.db")))

if not os.path.isabs(DATABASE_PATH):
    # If folder is provided, the database is relative to PARENT_DIR/folder
    if folder:
        DATABASE_PATH = os.path.join(PARENT_DIR, folder, DATABASE_PATH)
    else:
        DATABASE_PATH = os.path.join(PARENT_DIR, DATABASE_PATH)

# Ensure directories exist
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# =========================================
# API LOTERIAS CAIXA
# =========================================

CAIXA_API_URL = lotofacil_config.get("caixa_api", "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil")
API_TIMEOUT = 10

# =========================================
# SEGURANÇA
# =========================================

SECRET_KEY = os.getenv("SECRET_KEY", "lotofacil-secret-key-2026")

# =========================================
# CORES E IDENTIDADE VISUAL
# =========================================

COLORS = lotofacil_config.get("colors", {
    "primary": "#672666",
    "secondary": "#BA45B8",
    "accent": "#953793",
    "background": "#F8ECF8"
})

# =========================================
# FAIXA DE PREMIAÇÃO
# =========================================

PRIZE_TIERS = {
    15: {"name": "15 acertos", "value": "Prêmio Principal", "reward": 1500000.0},
    14: {"name": "14 acertos", "value": "2ª Faixa", "reward": 1500.0},
    13: {"name": "13 acertos", "value": "3ª Faixa", "reward": 30.0},
    12: {"name": "12 acertos", "value": "4ª Faixa", "reward": 12.0},
    11: {"name": "11 acertos", "value": "5ª Faixa", "reward": 6.0}
}

GAME_COST = 3.0
