import os
from flask import Flask
from models.shared import db
from routes.index_routes import index_bp
from routes.analise_routes import analise_bp
from routes.conferencia_routes import conferencia_bp
from routes.modelos_routes import modelos_bp
from routes.config_routes import config_bp
from routes.desdobramento_routes import desdobramento_bp
from routes.geradores_elite_routes import geradores_elite_bp
from services.cores_meses_service import CoresMesesService
from flask import Response, redirect


import os as _cc_os
import sys as _cc_sys
_CC_ROOT = _cc_os.path.abspath(_cc_os.path.join(_cc_os.path.dirname(__file__), "..", "_shared"))
if _CC_ROOT not in _cc_sys.path:
    _cc_sys.path.insert(0, _CC_ROOT)
from central_conferencias.app_integration import extend_app as cc_extend_app, register_conferencia_extras
from auto_sync import start_auto_sync_once
from analise_comparar.routes_factory import register_comparar
from analise_repeticao.routes_factory import register_repeticao
from menu.app_integration import extend_nav_app
from posicao_analise.app_integration import extend_posicao_app
from concentracao_acertos.app_integration import extend_concentracao_app
from analise_estudos.app_integration import extend_analise_estudos_app
from linhas_universo.app_integration import extend_camadas_linhas_dd_du_app
from analise_somas_digitos.app_integration import extend_analise_somas_digitos_app
from analise_inteligentes_diadesorte.app_integration import extend_analise_inteligentes_app
from analise_escolha_visual.app_integration import extend_analise_escolha_visual_app
from analise_tubular_inteligente.app_integration import extend_analise_tubular_inteligente_app
from configuracoes.app_integration import extend_config_app
from ciclo_cobertura.app_integration import extend_ciclo_cobertura_app
from resumo_modalidade.app_integration import extend_resumo_modalidade_app

def create_app():
    app = Flask(__name__)
    
    @app.route('/cores-meses.css')
    def cores_meses_css():
        css = CoresMesesService.gerar_css()
        return Response(css, mimetype='text/css')
    app.config['SECRET_KEY'] = 'sniper_diadesorte_secret'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'sqlite:///' + os.path.join(basedir, 'instance', 'diadesorte.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    db.init_app(app)
    extend_config_app(app)
    cc_extend_app(app, 'diasorte')
    extend_nav_app(app, 'diadesorte')
    extend_posicao_app(app, 'diadesorte')
    extend_concentracao_app(app, 'diadesorte')
    extend_analise_estudos_app(app)
    extend_camadas_linhas_dd_du_app(app)
    extend_analise_somas_digitos_app(app)
    extend_analise_inteligentes_app(app)
    extend_analise_escolha_visual_app(app)
    extend_analise_tubular_inteligente_app(app)
    extend_ciclo_cobertura_app(app, 'diadesorte')
    extend_resumo_modalidade_app(app)
    from menu.app_integration import _merge_template_dirs
    _merge_template_dirs(app, [os.path.join(_CC_ROOT, 'geradores_elite', 'templates')])
    _merge_template_dirs(app, [os.path.join(_CC_ROOT, 'ciclo_cobertura', 'templates')])
    app.register_blueprint(index_bp)
    app.register_blueprint(analise_bp,     url_prefix='/analise')
    register_conferencia_extras(conferencia_bp, 'diasorte')
    app.register_blueprint(conferencia_bp, url_prefix='/central-conferencias')
    app.register_blueprint(modelos_bp,     url_prefix='/modelos')
    app.register_blueprint(config_bp,      url_prefix='/configuracoes')
    app.register_blueprint(desdobramento_bp, url_prefix='/desdobramento')
    app.register_blueprint(geradores_elite_bp)

    @app.route('/gerador-especial/')
    @app.route('/gerador-especial/<path:subpath>')
    def redirect_gerador_especial(subpath=''):
        return redirect('/desdobramento/' + subpath, code=302)
    with app.app_context():
        import models.sorteio_diadesorte
        import models.caixa_excel_premiacao
        import models.desdobramento
        import models.construtor_construcoes
        import models.comportamento_estrategia
        db.create_all()
        try:
            db.session.execute(db.text(
                "ALTER TABLE sorteio_diadesorte ADD COLUMN ganhadores_7 INTEGER"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
        from geradores_elite.construtor.schema_ensure import ensure_construtor_schema
        ensure_construtor_schema()

    start_auto_sync_once(
        app,
        "services.api_diadesorte_service",
        "ApiDiaDeSorteService",
    )

    register_comparar(app, 'diadesorte')
    register_repeticao(app, 'diadesorte')

    return app

if __name__ == '__main__':
    app = create_app()
    porta = int(os.getenv('PORT', 5153))
    print("===========================================================")
    print(f"[OK] Servidor Dia de Sorte rodando na porta {porta}")
    print(f"[URL] Acesse:      http://localhost:{porta}")
    print(f"[URL] Análise:     http://localhost:{porta}/analise/")
    print(f"[URL] Resumo Geral: http://localhost:{porta}/analise/resumo-geral/")
    print(f"[URL] Análise Comp: http://localhost:{porta}/analise/comportamento/")
    print(f"[URL] Análise Pos.: http://localhost:{porta}/analise/por-posicao/")
    print(f"[URL] Ciclo Cob.:  http://localhost:{porta}/analise/ciclo-cobertura/")
    print(f"[URL] Ciclo->Apostas: http://localhost:{porta}/geradores-elite/ciclo-apostas/")
    print(f"[URL] Modelos:     http://localhost:{porta}/modelos/")
    print(f"[URL] Conferência: http://localhost:{porta}/central-conferencias/")
    print(f"[URL] Desdobramento: http://localhost:{porta}/desdobramento/")
    print(f"[URL] Construtor:    http://localhost:{porta}/geradores-elite/construtor-construcoes/")
    print("===========================================================")
    app.run(host='0.0.0.0', port=porta, debug=False)
