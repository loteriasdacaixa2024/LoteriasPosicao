import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    load_dotenv()
except ImportError:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from lotteries_config import LOTTERIES, get_lottery_config

SLUG = os.getenv("LOTTERY_SLUG", "lotofacil")
CFG = LOTTERIES.get(SLUG)
if not CFG:
    raise RuntimeError(f"Modalidade desconhecida: {SLUG}")

OBJ = get_lottery_config(SLUG)

APP_NAME = f"{CFG['name']} Estratégias"
APP_VERSION = "1.0.0"
LOTTERY_NAME = CFG["name"]
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", str(CFG.get("port", 5565))))
ENV = os.getenv("FLASK_ENV", "production")
DEBUG = ENV in ("development", "dev")
SECRET_KEY = os.getenv("SECRET_KEY", f"{SLUG}-secret-key-2026")

TOTAL_NUMBERS = int(CFG["total_numbers"])
DRAW_NUMBERS = int(CFG["draw_numbers"])
NUMBER_MIN = 0 if SLUG == "lotomania" else 1
NUMBER_MAX = NUMBER_MIN + TOTAL_NUMBERS - 1
GRID_ROWS = int(CFG["grid"]["rows"])
GRID_COLS = int(CFG["grid"]["columns"])
COLORS = CFG.get("colors", {})
CAIXA_API_URL = CFG.get("caixa_api", "")
API_TIMEOUT = 10
FOLDER = str(CFG.get("folder", SLUG))

BASE_DIR = os.path.join(ROOT_DIR, FOLDER)
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
DATABASE_PATH = str(CFG.get("database", os.path.join("data", f"{SLUG}.db")))
if not os.path.isabs(DATABASE_PATH):
    DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_PATH)

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

GAME_COST = {
    "lotofacil": 3.0, "dia_de_sorte": 2.5, "quina": 2.5, "megasena": 5.0,
    "lotomania": 3.0, "timemania": 3.5, "duplasena": 2.5, "maismilionaria": 6.0,
}.get(SLUG, 3.0)

PRIZE_TIERS = {}
for hits, label in (CFG.get("prizes") or {}).items():
    PRIZE_TIERS[int(hits)] = {
        "name": label if isinstance(label, str) else f"{hits} acertos",
        "reward": float(10 ** max(0, int(hits) - 3)),
    }

TEMPLATE_CONFIG = dict(CFG)
TEMPLATE_CONFIG["slug"] = SLUG
TEMPLATE_CONFIG["number_min"] = NUMBER_MIN
TEMPLATE_CONFIG["number_max"] = NUMBER_MAX
