"""Silencia banner do Flask/Werkzeug e avisos de SSL. Mantém o log de cada GET."""
import logging


class _SkipStartupNoise(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        skip = (
            "development server" in msg
            or "Running on" in msg
            or "Debug mode" in msg
            or "Serving Flask" in msg
            or "Press CTRL+C" in msg
            or "WARNING: This is a development server" in msg
        )
        return not skip


def silence_startup():
    try:
        import flask.cli
        flask.cli.show_server_banner = lambda *a, **k: None
    except Exception:
        pass
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass
    log = logging.getLogger("werkzeug")
    log.addFilter(_SkipStartupNoise())
