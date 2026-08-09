import os
from flask import Flask
from models.shared import db
from routes.index_routes import index_bp
from routes.analise_routes import analise_bp
from routes.conferencia_routes import conferencia_bp
from routes.modelos_routes import modelos_bp
from routes.desdobramento_routes import desdobramento_bp
from routes.geradores_elite_routes import geradores_elite_bp


import os as _cc_os
import sys as _cc_sys
_CC_ROOT = _cc_os.path.abspath(_cc_os.path.join(_cc_os.path.dirname(__file__), "..", "_shared"))
if _CC_ROOT not in _cc_sys.path:
    _cc_sys.path.insert(0, _CC_ROOT)
from central_conferencias.app_integration import extend_app as cc_extend_app, register_conferencia_extras
from routes.config_routes import config_bp
from configuracoes.app_integration import extend_config_app
from auto_sync import start_auto_sync_once
from analise_comparar.routes_factory import register_comparar
from analise_repeticao.routes_factory import register_repeticao
from menu.app_integration import extend_nav_app
from posicao_analise.app_integration import extend_posicao_app
from analise_estudos.app_integration import extend_analise_estudos_app
from linhas_universo.app_integration import extend_camadas_linhas_dd_du_app
from concentracao_acertos.app_integration import extend_concentracao_app
from geradores_elite.comportamento_analise_integration import extend_comportamento_analise_app
from analise_somas_digitos.app_integration import extend_analise_somas_digitos_app
from analise_inteligentes_diadesorte.app_integration import extend_analise_inteligentes_app

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'sniper_supersete_secret'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'sqlite:///' + os.path.join(basedir, 'instance', 'supersete.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    db.init_app(app)
    extend_config_app(app)
    cc_extend_app(app, 'supersete')
    extend_nav_app(app, 'supersete')
    extend_posicao_app(app, 'supersete')
    extend_concentracao_app(app, 'supersete')
    extend_analise_estudos_app(app)
    extend_camadas_linhas_dd_du_app(app)
    extend_comportamento_analise_app(app)
    extend_analise_somas_digitos_app(app)
    extend_analise_inteligentes_app(app)

    app.register_blueprint(index_bp)
    app.register_blueprint(analise_bp,    url_prefix='/analise')
    register_conferencia_extras(conferencia_bp, 'supersete')
    app.register_blueprint(conferencia_bp, url_prefix='/central-conferencias')
    app.register_blueprint(modelos_bp,    url_prefix='/modelos')
    app.register_blueprint(desdobramento_bp, url_prefix='/desdobramento')
    app.register_blueprint(config_bp, url_prefix='/configuracoes')
    app.register_blueprint(geradores_elite_bp)

    with app.app_context():
        import models.sorteio_supersete
        import models.construtor_construcoes
        db.create_all()
        from geradores_elite.construtor.schema_ensure import ensure_construtor_schema
        ensure_construtor_schema()

    start_auto_sync_once(
        app,
        "services.api_supersete_service",
        "ApiSuperSeteService",
    )

    register_comparar(app, 'supersete')
    register_repeticao(app, 'supersete')

    return app

if __name__ == '__main__':
    app = create_app()
    porta = int(os.getenv('PORT', 5160))
    print("===========================================================")
    print(f"[OK] Servidor Super Sete rodando em DESENVOLVIMENTO na porta {porta}")
    print(f"[URL] Acesse:      http://localhost:{porta}")
    print(f"[URL] Análise:     http://localhost:{porta}/analise/")
    print(f"[URL] Modelos:     http://localhost:{porta}/modelos/")
    print(f"[URL] Conferência: http://localhost:{porta}/central-conferencias/")
    print(f"[URL] Construtor:    http://localhost:{porta}/geradores-elite/construtor-construcoes/")
    print("===========================================================")
    app.run(host='0.0.0.0', port=porta, debug=False)
