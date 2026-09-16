import os
import sys


def boot(slug):
    os.environ["LOTTERY_SLUG"] = slug
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    from laboratorio.server import app, HOST, PORT, DEBUG
    from quiet_terminal import silence_startup
    silence_startup()
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)
