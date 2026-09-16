import os
import sys

try:
    from dotenv import load_dotenv
    _env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env)
except ImportError:
    pass

# Porta oficial de estratégias (lotteries_config): Super Sete → 5573
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PARENT_DIR not in sys.path:
    sys.path.append(_PARENT_DIR)

_DEFAULT_PORT = 5573
try:
    from lotteries_config import LOTTERIES
    _DEFAULT_PORT = int(LOTTERIES.get("supersete", {}).get("port", 5573))
except Exception:
    pass


class Config:
    """Configuração base do sistema."""

    # ── Identidade ──────────────────────────────────
    APP_NAME = "Super 7 - Estratégias"
    APP_VERSION = "1.0.0"
    APP_TYPE = "Simulação Modular"

    # ── Servidor ────────────────────────────────────
    PORT = int(os.getenv("PORT", str(_DEFAULT_PORT)))
    HOST = os.getenv("HOST", "0.0.0.0")
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_ENV", "production") in ("dev", "development")
    
    # ── Cache ─────────────────────────
    VERSION = "1.0"

    # ── Caminhos ────────────────────────────────────
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    DATABASE_PATH = os.path.join(DATA_DIR, "supersete.db")
    EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

    # ── Banco de Dados ──────────────────────────────
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Segurança ───────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "superset-e1-dev-secret-key-2024")

    # ── Super Sete — Faixas de Premiação (estimado) ─
    PRIZE_TIERS = {
        3: {"name": "3 acertos", "value": "R$ 5,00"},
        4: {"name": "4 acertos", "value": "R$ 50,00"},
        5: {"name": "5 acertos", "value": "R$ 1.000,00"},
        6: {"name": "6 acertos", "value": "R$ 20.000,00"},
        7: {"name": "7 acertos", "value": "Prêmio Principal"},
    }

    # ── Constantes do Jogo ──────────────────────────
    COLUMNS = 7
    DIGITS = list(range(10))  # 0-9

    # ── API (Caixa Econômica) ───────────────────────
    CAIXA_API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/supersete"
    API_TIMEOUT = 10  # segundos


class ProductionConfig(Config):
    """Configuração para produção."""
    DEBUG = False
    ENV = "prod"


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento."""
    DEBUG = True
    ENV = "dev"
