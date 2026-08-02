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
_POS_ROOT = _cc_os.path.abspath(_cc_os.path.join(_cc_os.path.dirname(__file__), ".."))
for _p in (_CC_ROOT, _POS_ROOT):
    if _p not in _cc_sys.path:
        _cc_sys.path.insert(0, _p)
from central_conferencias.app_integration import extend_app as cc_extend_app, register_conferencia_extras
from routes.config_routes import config_bp
from configuracoes.app_integration import extend_config_app
from auto_sync import start_auto_sync_once
from analise_comparar.routes_factory import register_comparar
from analise_repeticao.routes_factory import register_repeticao
from analise_estudos.app_integration import extend_analise_estudos_app
from analise_escolha_visual.app_integration import extend_analise_escolha_visual_app
from analise_tubular_inteligente.app_integration import extend_analise_tubular_inteligente_app
from menu.app_integration import extend_nav_app
from posicao_analise.app_integration import extend_posicao_app
from services.analise_duplasena_service import AnaliseDuplaSenaService
from services.ciclo_service import CicloDuplaSenaService
from services.desdobramento_service import DesdobramentoDuplaSenaService
from _shared.desdobramento_especial.app_integration import register_desdobramento_especial

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sniper_duplasena_secret'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'sqlite:///' + os.path.join(basedir, 'instance', 'duplasena.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    db.init_app(app)
    extend_config_app(app)
    cc_extend_app(app, 'duplasena')
    extend_nav_app(app, 'duplasena')
    extend_analise_estudos_app(app)
    extend_analise_escolha_visual_app(app)
    extend_analise_tubular_inteligente_app(app)
    extend_posicao_app(app, 'duplasena')
    app.register_blueprint(index_bp)
    app.register_blueprint(analise_bp,     url_prefix='/analise')
    register_conferencia_extras(conferencia_bp, 'duplasena')
    app.register_blueprint(conferencia_bp, url_prefix='/central-conferencias')
    app.register_blueprint(modelos_bp,     url_prefix='/modelos')
    app.register_blueprint(desdobramento_bp, url_prefix='/desdobramento')
    app.register_blueprint(config_bp, url_prefix='/configuracoes')
    app.register_blueprint(geradores_elite_bp)
    with app.app_context():
        import models.sorteio_duplasena
        import models.desdobramento
        import models.construtor_construcoes
        db.create_all()
        try:
            db.session.execute(db.text(
                "ALTER TABLE construtor_construcoes ADD COLUMN extra_json TEXT DEFAULT '{}'"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
    start_auto_sync_once(
        app,
        "services.api_duplasena_service",
        "ApiDuplaSenaService",
    )
    register_comparar(app, 'duplasena')
    register_repeticao(app, 'duplasena')
    register_desdobramento_especial(
        app,
        'duplasena',
        CicloDuplaSenaService,
        DesdobramentoDuplaSenaService,
        analise_service_class=AnaliseDuplaSenaService,
    )
    return app

if __name__ == '__main__':
    app = create_app()
    porta = int(os.getenv('PORT', 5158))
    print("===========================================================")
    print(f"[OK] Servidor Dupla Sena rodando na porta {porta}")
    print(f"[URL] Acesse:      http://localhost:{porta}")
    print(f"[URL] Análise:     http://localhost:{porta}/analise/")
    print(f"[URL] Modelos:     http://localhost:{porta}/modelos/")
    print(f"[URL] Conferência: http://localhost:{porta}/central-conferencias/")
    print(f"[URL] Desdobramento: http://localhost:{porta}/desdobramento/")
    print("===========================================================")
    app.run(host='0.0.0.0', port=porta, debug=False)
