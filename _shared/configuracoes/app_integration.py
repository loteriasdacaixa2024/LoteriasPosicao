import os
import sys

from jinja2 import ChoiceLoader, FileSystemLoader


def extend_config_app(app):
    """Adiciona templates compartilhados de configurações ao Flask app."""
    shared_tpl = os.path.join(os.path.dirname(__file__), "templates")
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    if shared_tpl not in sys.path:
        sys.path.insert(0, os.path.dirname(__file__))

    loaders = [app.jinja_loader]
    if not isinstance(app.jinja_loader, ChoiceLoader):
        loaders = [app.jinja_loader]
    else:
        loaders = list(app.jinja_loader.loaders)

    shared_loader = FileSystemLoader(shared_tpl)
    if not any(
        getattr(ld, "searchpath", None) == shared_loader.searchpath
        for ld in loaders
        if hasattr(ld, "searchpath")
    ):
        loaders.insert(0, shared_loader)
    app.jinja_loader = ChoiceLoader(loaders)
