# Prefixos públicos via Nginx (X-Forwarded-Prefix / ProxyFix).
from werkzeug.middleware.proxy_fix import ProxyFix


def apply_proxy(app):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    return app
