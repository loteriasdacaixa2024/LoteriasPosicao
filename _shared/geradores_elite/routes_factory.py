"""Factory de blueprint Flask — Geradores de Elite / Engine Final."""
import os

from flask import Blueprint, jsonify, render_template, request

from .ball_styles import get_ball_ui
from .engine_final_core import (
    backtest_apostas_engine,
    conferir_apostas_engine,
    formatar_export_txt,
    gerar_apostas,
    get_config,
)
from .otimizador import MODALIDADES_OTIMIZADOR, otimizar_apostas
from .inteligente import (
    get_comportamento_service,
    get_inteligente_service,
    tem_gerador_comportamento,
    tem_gerador_inteligente,
)
from .construtor import get_construtor_service, tem_construtor
from .inteligente_page import page_context
from .modality_config import MODALITIES


def build_geradores_elite_blueprint(modality_key: str) -> Blueprint:
    if modality_key not in MODALITIES:
        raise ValueError(f"Modalidade inválida: {modality_key}")

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    bp = Blueprint(
        "geradores_elite",
        __name__,
        template_folder=os.path.join(pkg_dir, "templates"),
        static_folder=os.path.join(pkg_dir, "static"),
        url_prefix="/geradores-elite",
    )
    cfg = get_config(modality_key)

    def _pipeline_elite(resultado, origem: str, data=None):
        """Camada obrigatória: histórico oficial + back test (serviço global)."""
        from geradores_elite.validacao.pipeline import pipeline_from_request

        if not isinstance(resultado, dict):
            return resultado
        return pipeline_from_request(
            resultado,
            modality_key=modality_key,
            origem=origem,
            data=data if isinstance(data, dict) else {},
        )

    @bp.route("/")
    def index():
        return render_template(
            "geradores_elite_index.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            cfg=cfg,
        )

    def _render_apostas_inteligentes():
        try:
            ctx = page_context(modality_key)
        except ValueError:
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        return render_template("apostas_inteligentes.html", **ctx)

    @bp.route("/apostas-inteligentes/")
    def apostas_inteligentes_page():
        return _render_apostas_inteligentes()

    def _render_comportamento_apostas():
        if not tem_gerador_comportamento(modality_key):
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        from geradores_elite.comportamento.specs import COMPORTAMENTO_TITLES, SPECS
        from geradores_elite.inteligente_page import repeticao_cfg_for_page

        mod = MODALITIES[modality_key]
        rep_cfg = repeticao_cfg_for_page(modality_key)
        svc = get_comportamento_service(modality_key)
        spec = SPECS.get(modality_key)
        meses_cores = {}
        if cfg.get("meses_api") or modality_key == "diadesorte":
            try:
                from _shared.diadesorte.meses_cores import obter_meses_cores
                meses_cores = obter_meses_cores()
            except Exception:
                meses_cores = {}
        return render_template(
            "comportamento_apostas.html",
            modality_key=modality_key,
            modality_nome=mod["nome"],
            cfg=rep_cfg,
            api_base="/geradores-elite/api/comportamento",
            page_title=COMPORTAMENTO_TITLES.get(modality_key, "Comportamento → Apostas"),
            page_subtitle=spec.page_subtitle if spec else "",
            comportamento_ui=svc.ui_config() if svc else {},
            meses_cores=meses_cores,
        )

    @bp.route("/comportamento-apostas/")
    def comportamento_apostas_page():
        return _render_comportamento_apostas()

    @bp.route("/sniper-coluna-apostas/")
    def sniper_coluna_apostas_page():
        if modality_key != "supersete":
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        return _render_apostas_inteligentes()

    @bp.route("/repeticao-apostas/")
    def repeticao_apostas_page():
        if modality_key == "lotofacil":
            return render_template("repeticao_apostas_lotofacil.html")
        try:
            from analise_repeticao.repeticao_config import (
                get_repeticao_config,
                get_repeticao_ui_context,
            )

            rep_cfg = get_repeticao_config(modality_key)
            ui_ctx = get_repeticao_ui_context(modality_key)
        except ValueError:
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        return render_template(
            "repeticao_apostas.html",
            modality_key=modality_key,
            modality_nome=rep_cfg.get("nome", cfg["nome"]),
            cfg=rep_cfg,
            meses_cores=ui_ctx.get("meses_cores", {}),
        )

    @bp.route("/ciclo-apostas/")
    def ciclo_apostas_page():
        from ciclo_cobertura.specs import get_ciclo_spec, tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        spec = get_ciclo_spec(modality_key)
        meses_cores = {}
        try:
            from services.cores_meses_service import CoresMesesService
            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            meses_cores = {}
        meses = [
            {"num": i, "abrev": a, "nome": n}
            for i, (a, n) in enumerate([
                ("Jan", "Janeiro"), ("Fev", "Fevereiro"), ("Mar", "Março"),
                ("Abr", "Abril"), ("Mai", "Maio"), ("Jun", "Junho"),
                ("Jul", "Julho"), ("Ago", "Agosto"), ("Set", "Setembro"),
                ("Out", "Outubro"), ("Nov", "Novembro"), ("Dez", "Dezembro"),
            ], start=1)
        ]
        return render_template(
            "ciclo_apostas.html",
            modality_key=modality_key,
            modality_nome=spec.nome,
            pick_default=spec.pick_default,
            pick_min=spec.pick_min,
            pick_max=spec.pick_max,
            api_base="/geradores-elite/api/ciclo-apostas",
            meses_cores=meses_cores,
            meses=meses,
            has_mes=True,
        )

    @bp.route("/api/ciclo-apostas/contexto")
    def api_ciclo_apostas_contexto():
        from ciclo_cobertura.service import contexto_dois_ultimos, metricas_padrao_2n1r
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        ctx = contexto_dois_ultimos(modality_key)
        return jsonify({
            "ok": bool(ctx.get("ok")),
            "contexto": ctx,
            "metricas": metricas_padrao_2n1r(modality_key),
        })

    @bp.route("/api/ciclo-apostas/gerar", methods=["POST"])
    def api_ciclo_apostas_gerar():
        from ciclo_cobertura.gerador import gerar_apostas_ciclo
        from ciclo_cobertura.pos_geracao import pos_processar_geracao
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        data = request.get_json(silent=True) or {}
        out = gerar_apostas_ciclo(
            modality_key,
            quantidade=int(data.get("quantidade") or 10),
            pick=int(data["pick"]) if data.get("pick") is not None else None,
            filtro_faixas=bool(data.get("filtro_faixas")),
            filtro_soma=bool(data.get("filtro_soma")),
            filtro_digitos=bool(data.get("filtro_digitos")),
        )
        if out.get("ok"):
            out = pos_processar_geracao(
                out,
                modality_key,
                mes_num=data.get("mes_num") or data.get("mes"),
                descartar_historico=bool(data.get("descartar_historico")),
            )
        code = 200 if out.get("ok") else 400
        return jsonify(out), code

    @bp.route("/api/ciclo-apostas/ritmo/contexto")
    def api_ciclo_ritmo_contexto():
        from ciclo_cobertura.gerador_ritmo import contexto_ritmo
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        return jsonify(contexto_ritmo(modality_key))

    @bp.route("/api/ciclo-apostas/ritmo/gerar", methods=["POST"])
    def api_ciclo_ritmo_gerar():
        from ciclo_cobertura.gerador_ritmo import gerar_apostas_ritmo
        from ciclo_cobertura.pos_geracao import pos_processar_geracao
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        data = request.get_json(silent=True) or {}
        out = gerar_apostas_ritmo(
            modality_key,
            quantidade=int(data.get("quantidade") or 10),
            pick=int(data["pick"]) if data.get("pick") is not None else None,
        )
        if out.get("ok"):
            out = pos_processar_geracao(
                out,
                modality_key,
                mes_num=data.get("mes_num") or data.get("mes"),
                descartar_historico=bool(data.get("descartar_historico")),
            )
        code = 200 if out.get("ok") else 400
        return jsonify(out), code

    @bp.route("/api/ciclo-apostas/operacional/contexto")
    def api_ciclo_operacional_contexto():
        from ciclo_cobertura.gerador_operacional import contexto_operacional
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        return jsonify(contexto_operacional(modality_key))

    @bp.route("/api/ciclo-apostas/operacional/gerar", methods=["POST"])
    def api_ciclo_operacional_gerar():
        from ciclo_cobertura.gerador_operacional import gerar_apostas_operacional
        from ciclo_cobertura.pos_geracao import pos_processar_geracao
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        data = request.get_json(silent=True) or {}
        out = gerar_apostas_operacional(
            modality_key,
            quantidade=int(data.get("quantidade") or 10),
            pick=int(data["pick"]) if data.get("pick") is not None else None,
            modo=data.get("modo") or "auto",
        )
        if out.get("ok"):
            out = pos_processar_geracao(
                out,
                modality_key,
                mes_num=data.get("mes_num") or data.get("mes"),
                descartar_historico=bool(data.get("descartar_historico")),
                origem="ciclo_operacional",
            )
        code = 200 if out.get("ok") else 400
        return jsonify(out), code

    @bp.route("/api/ciclo-apostas/fechamento/contexto")
    def api_ciclo_fechamento_contexto():
        from ciclo_cobertura.gerador_fechamento import contexto_fechamento
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        return jsonify(contexto_fechamento(modality_key))

    @bp.route("/api/ciclo-apostas/fechamento/gerar", methods=["POST"])
    def api_ciclo_fechamento_gerar():
        from ciclo_cobertura.gerador_fechamento import gerar_apostas_fechamento
        from ciclo_cobertura.pos_geracao import pos_processar_geracao
        from ciclo_cobertura.specs import tem_ciclo_cobertura

        if not tem_ciclo_cobertura(modality_key):
            return jsonify({"ok": False, "erro": "Indisponível para esta modalidade."}), 404
        data = request.get_json(silent=True) or {}
        out = gerar_apostas_fechamento(
            modality_key,
            quantidade=int(data.get("quantidade") or 10),
            pick=int(data["pick"]) if data.get("pick") is not None else None,
            forcar=bool(data.get("forcar")),
        )
        if out.get("ok"):
            out = pos_processar_geracao(
                out,
                modality_key,
                mes_num=data.get("mes_num") or data.get("mes"),
                descartar_historico=bool(data.get("descartar_historico")),
                origem="ciclo_fechamento",
            )
        code = 200 if out.get("ok") else 400
        return jsonify(out), code

    @bp.route("/api/ciclo-apostas/export-txt", methods=["POST"])
    def api_ciclo_export_txt():
        try:
            body = request.get_json(silent=True) or {}
            apostas = body.get("apostas") or []
            if not apostas:
                return jsonify({"sucesso": False, "erro": "Nenhuma aposta para exportar."}), 400
            mes_num = body.get("mes_num") or body.get("mes")
            extra = body.get("extra") or {}
            from ciclo_cobertura.pos_geracao import MESES_ABREV, aplicar_mes_apostas, resolver_mes_entrada
            from diadesorte.mes_sorte_select import eh_criterio_aleatorio

            # Critério bruto para + Aleatório (distribuição por aposta)
            if mes_num is not None and mes_num != "":
                apostas = aplicar_mes_apostas(apostas, mes_num)
            mn = None
            if apostas and isinstance(apostas[0], dict) and apostas[0].get("mes_num"):
                mn = int(apostas[0]["mes_num"])
            elif not eh_criterio_aleatorio(mes_num):
                mn = resolver_mes_entrada(mes_num)
            if mn and not extra and not eh_criterio_aleatorio(mes_num):
                extra = {"tipo": "mes", "num": mn, "label": MESES_ABREV.get(mn, str(mn))}
            # Em aleatório, extras já vão por aposta — não forçar extra global
            if eh_criterio_aleatorio(mes_num):
                extra = {}
            texto = formatar_export_txt(modality_key, apostas, extra)
            nome = f"ciclo_apostas_{modality_key}_{len(apostas)}jg.txt"
            return jsonify({
                "sucesso": True,
                "texto": texto,
                "nome_arquivo": nome,
                "mes_num": mn,
                "mes_criterio": "aleatorio" if eh_criterio_aleatorio(mes_num) else None,
            })
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/ciclo-apostas/backtest", methods=["POST"])
    def api_ciclo_backtest():
        try:
            body = request.get_json(silent=True) or {}
            apostas = body.get("apostas") or []
            limite = int(body.get("limite") or 30)
            if not apostas:
                return jsonify({"sucesso": False, "erro": "Nenhuma aposta informada."}), 400
            resultado = backtest_apostas_engine(modality_key, apostas, limite=limite)
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/engine-final/")
    def engine_final_page():
        meses_cores = {}
        if cfg.get("meses_api"):
            try:
                from services.cores_meses_service import CoresMesesService

                meses_cores = CoresMesesService.obter_cores() or {}
            except Exception:
                meses_cores = {}
        ball_ui = get_ball_ui(modality_key)
        return render_template(
            "engine_final.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            cfg=cfg,
            meses_cores=meses_cores,
            ball_css=ball_ui["css"],
            ball_classes=ball_ui["classes"],
            otimizador_habilitado=modality_key in MODALIDADES_OTIMIZADOR,
            construtor_habilitado=tem_construtor(modality_key),
        )

    def _inteligente_svc():
        svc = get_inteligente_service(modality_key)
        if not svc:
            raise ValueError("Serviço inteligente indisponível")
        return svc

    def _api_inteligente_analise():
        try:
            return jsonify(_inteligente_svc().analise_completa_api())
        except ValueError as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 404
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    def _api_inteligente_concursos():
        limite = request.args.get("limit", 150)
        if modality_key == "lotofacil":
            from services.analise_repeticao_concursos_service import (
                AnaliseRepeticaoConcursosService,
            )

            return jsonify({
                "sucesso": True,
                "concursos": AnaliseRepeticaoConcursosService.listar_concursos(limite),
            })
        from analise_repeticao.repeticao_service import RepeticaoConcursosService

        svc = RepeticaoConcursosService(modality_key)
        return jsonify({"sucesso": True, "concursos": svc.listar_concursos(limite)})

    def _api_inteligente_gerar():
        data = request.get_json(silent=True) or {}
        try:
            svc = _inteligente_svc()
            kwargs = {
                "quantidade": int(data.get("quantidade", 10)),
                "perfil": data.get("perfil", "equilibrado"),
                "modo_geracao": data.get("modo_geracao", "automatico"),
                "regras_manuais": data.get("regras_manuais") or {},
                "usar_ultimo_par_chk": bool(data.get("usar_ultimo_par", True)),
            }
            if modality_key != "supersete":
                if data.get("dezenas_por_jogo") is not None:
                    kwargs["dezenas_por_jogo"] = int(data["dezenas_por_jogo"])
            out = svc.gerar(**kwargs)
            return jsonify(_pipeline_elite(out, "inteligente", data))
        except ValueError as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 404
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/inteligente/analise")
    def api_inteligente_analise():
        if not tem_gerador_inteligente(modality_key):
            return jsonify({"sucesso": False, "erro": "Modalidade sem gerador inteligente."}), 404
        return _api_inteligente_analise()

    @bp.route("/api/inteligente/concursos")
    def api_inteligente_concursos():
        if not tem_gerador_inteligente(modality_key):
            return jsonify({"sucesso": False}), 404
        return _api_inteligente_concursos()

    @bp.route("/api/inteligente/gerar", methods=["POST"])
    def api_inteligente_gerar():
        if not tem_gerador_inteligente(modality_key):
            return jsonify({"sucesso": False, "erro": "Modalidade sem gerador inteligente."}), 404
        return _api_inteligente_gerar()

    def _comportamento_svc():
        svc = get_comportamento_service(modality_key)
        if not svc:
            raise ValueError("Comportamento indisponível para esta modalidade.")
        return svc

    @bp.route("/api/comportamento/analise")
    def api_comportamento_analise():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Comportamento indisponível."}), 404
        try:
            svc = _comportamento_svc()
            ui = svc.ui_config()
            janela = int(request.args.get("janela", ui.get("janela_default", 10)))
            filtros = {}
            for cod in ui.get("indicadores") or []:
                v = request.args.get(cod)
                if v is not None and v != "":
                    filtros[cod] = int(v)
            base = request.args.get("base", "geral")
            return jsonify(svc.analise_completa_api(
                janela=janela, filtros=filtros or None, base_estatistica=base,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/concursos")
    def api_comportamento_concursos():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False}), 404
        limite = int(request.args.get("limit", 150))
        svc = _comportamento_svc()
        return jsonify({
            "sucesso": True,
            "concursos": svc._svc().listar_concursos(limite),
        })

    @bp.route("/api/comportamento/gerar", methods=["POST"])
    def api_comportamento_gerar():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Comportamento indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            svc = _comportamento_svc()
            ui = svc.ui_config()
            dez_default = ui.get("dezenas_default", 15)
            filtros = data.get("filtros") or {}
            return jsonify(_pipeline_elite(svc.gerar(
                quantidade=int(data.get("quantidade", 10)),
                perfil=data.get("perfil", "equilibrado"),
                modo_geracao=data.get("modo_geracao", "automatico"),
                modo_motor=data.get("modo_motor", "perfil_sorteio"),
                dezenas_por_jogo=int(data["dezenas_por_jogo"]) if data.get("dezenas_por_jogo") is not None else dez_default,
                janela=int(data.get("janela", ui.get("janela_default", 10))),
                regras_manuais=data.get("regras_manuais") or {},
                filtros=filtros or None,
                base_estatistica=data.get("base") or data.get("base_estatistica", "geral"),
            ), "comportamento", data))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/meses-indicados")
    def api_meses_indicados():
        if modality_key != "diadesorte":
            return jsonify({"sucesso": False, "erro": "Disponível só para Dia de Sorte."}), 404
        try:
            janela = int(request.args.get("janela", 10))
            from services.analise_diadesorte_service import AnaliseDiaDeSorteService

            dados = AnaliseDiaDeSorteService.meses_indicados(janela=janela)
            if not dados.get("sucesso"):
                return jsonify(dados), 404
            return jsonify(dados)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/mes-sorte-opcoes")
    def api_mes_sorte_opcoes():
        """Select padronizado: + Atrasado, + Frequente, meses, + Aleatório."""
        if modality_key != "diadesorte":
            return jsonify({"sucesso": False, "erro": "Disponível só para Dia de Sorte."}), 404
        try:
            from diadesorte.mes_sorte_select import opcoes_mes_sorte_diadesorte
            return jsonify(opcoes_mes_sorte_diadesorte())
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/panorama-indicadores")
    def api_comportamento_panorama_indicadores():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Comportamento indisponível."}), 404
        try:
            svc = _comportamento_svc()
            base = request.args.get("base", "geral")
            return jsonify(svc.panorama_indicadores_api(base_estatistica=base))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/panorama-selecao-contexto")
    def api_comportamento_panorama_selecao_contexto():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Comportamento indisponível."}), 404
        try:
            svc = _comportamento_svc()
            base = request.args.get("base", "geral")
            rank = int(request.args.get("rank", request.args.get("rank_escolhido", 1)))
            return jsonify(svc.panorama_selecao_contexto_api(
                base_estatistica=base, rank_escolhido=rank,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/panorama-validar-selecao", methods=["POST"])
    def api_comportamento_panorama_validar_selecao():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Comportamento indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            svc = _comportamento_svc()
            ui = svc.ui_config()
            dez_default = ui.get("dezenas_default", 15)
            return jsonify(svc.validar_selecao_panorama_api(
                dezenas=data.get("dezenas") or [],
                base_estatistica=data.get("base") or data.get("base_estatistica", "geral"),
                rank_escolhido=int(data.get("rank_escolhido", data.get("rank", 1))),
                modo=data.get("modo_validacao", data.get("modo", "estrito")),
                dezenas_por_jogo=int(data["dezenas_por_jogo"]) if data.get("dezenas_por_jogo") is not None else dez_default,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/gerar-panorama-top", methods=["POST"])
    def api_comportamento_gerar_panorama_top():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Comportamento indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            svc = _comportamento_svc()
            ui = svc.ui_config()
            dez_default = ui.get("dezenas_default", 15)
            pool = data.get("pool_dezenas")
            if pool is not None:
                pool = [int(x) for x in pool]
            manuais = data.get("dezenas_manuais")
            if manuais is not None:
                manuais = [int(x) for x in manuais]
            return jsonify(_pipeline_elite(svc.gerar_panorama_top(
                quantidade=int(data.get("quantidade", 10)),
                perfil=data.get("perfil", "equilibrado"),
                dezenas_por_jogo=int(data["dezenas_por_jogo"]) if data.get("dezenas_por_jogo") is not None else dez_default,
                base_estatistica=data.get("base") or data.get("base_estatistica", "geral"),
                rank_escolhido=int(data.get("rank_escolhido", data.get("rank", 1))),
                pool_dezenas=pool,
                modo_validacao=data.get("modo_validacao", "estrito"),
                modo_panorama=data.get("modo_panorama", "automatico"),
                dezenas_manuais=manuais,
            ), "comportamento_panorama", data))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/export-composto", methods=["POST"])
    def api_comportamento_export_composto():
        if not tem_gerador_comportamento(modality_key):
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        itens = data.get("itens") or []
        if not itens:
            return jsonify({"sucesso": False, "erro": "Nenhum item na coleção."}), 400
        try:
            from geradores_elite.comportamento.export_composto import formatar_export_composto
            texto = formatar_export_composto(modality_key, itens)
            return jsonify({"sucesso": True, "texto": texto, "total": len(itens)})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    def _comportamento_estrategia_svc():
        if modality_key != "diadesorte":
            raise ValueError("Panorama de estratégias disponível apenas para Dia de Sorte.")
        from services.comportamento_estrategia_service import ComportamentoEstrategiaDiaDeSorteService
        return ComportamentoEstrategiaDiaDeSorteService

    @bp.route("/api/comportamento/conferir-estrategias", methods=["POST"])
    def api_comportamento_conferir_estrategias():
        if modality_key != "diadesorte":
            return jsonify({"sucesso": False, "erro": "Disponível apenas para Dia de Sorte."}), 404
        data = request.get_json(silent=True) or {}
        try:
            concurso = int(data.get("concurso", 0))
            apostas = data.get("apostas_por_base") or {}
            return jsonify(_comportamento_estrategia_svc().conferir_estrategias(concurso, apostas))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/registrar-conferencia-estrategias", methods=["POST"])
    def api_comportamento_registrar_conferencia():
        if modality_key != "diadesorte":
            return jsonify({"sucesso": False, "erro": "Disponível apenas para Dia de Sorte."}), 404
        data = request.get_json(silent=True) or {}
        try:
            concurso = int(data.get("concurso", 0))
            apostas = data.get("apostas_por_base") or {}
            return jsonify(_comportamento_estrategia_svc().registrar_conferencia(concurso, apostas))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/comportamento/panorama-estrategias")
    def api_comportamento_panorama_estrategias():
        if modality_key != "diadesorte":
            return jsonify({"sucesso": False, "erro": "Disponível apenas para Dia de Sorte."}), 404
        try:
            limit = int(request.args.get("limit", 50))
            return jsonify(_comportamento_estrategia_svc().panorama(limit=limit))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/sniper-coluna/analise")
    def api_sniper_analise():
        if modality_key != "supersete":
            return jsonify({"sucesso": False, "erro": "Use /api/inteligente/analise nesta modalidade."}), 404
        return _api_inteligente_analise()

    @bp.route("/api/sniper-coluna/concursos")
    def api_sniper_concursos():
        if modality_key != "supersete":
            return jsonify({"sucesso": False}), 404
        return _api_inteligente_concursos()

    @bp.route("/api/sniper-coluna/gerar", methods=["POST"])
    def api_sniper_gerar():
        if modality_key != "supersete":
            return jsonify({"sucesso": False, "erro": "Use /api/inteligente/gerar nesta modalidade."}), 404
        return _api_inteligente_gerar()

    @bp.route("/api/conferir-txt-historico", methods=["POST"])
    def api_conferir_txt_historico():
        if modality_key != "lotofacil":
            return jsonify({"sucesso": False, "mensagem": "Recurso disponível só para Lotofácil."}), 404
        try:
            from central_conferencias.folder_service import ConferenciaApostasFolderService

            data = request.get_json(silent=True) or {}
            texto = (data.get("texto") or "").strip()
            if not texto and "file" in request.files:
                arq = request.files["file"]
                texto = arq.read().decode("utf-8", errors="replace").strip()
            min_ac = data.get("min_acertos", 11)
            resultado = ConferenciaApostasFolderService(modality_key).conferir_txt_historico(
                texto, min_acertos=int(min_ac)
            )
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "mensagem": str(e)}), 500

    @bp.route("/api/engine-final/gerar", methods=["POST"])
    def api_gerar():
        try:
            body = request.get_json(silent=True) or {}
            resultado = gerar_apostas(
                modality_key,
                quantidade=body.get("quantidade", 5),
                qtd_dezenas=body.get("dezenas"),
                modo=body.get("modo", "convergencia"),
                extra_criterio=body.get("extra_criterio", "atrasado"),
                mes_manual=body.get("mes_manual"),
                sessao_id=body.get("sessao_id"),
            )
            return jsonify(_pipeline_elite(resultado, "engine_final", body)), 200
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/engine-final/export-txt", methods=["POST"])
    def api_export_txt():
        try:
            body = request.get_json(silent=True) or {}
            apostas = body.get("apostas") or []
            extra = body.get("extra") or {}
            texto = formatar_export_txt(modality_key, apostas, extra)
            return jsonify({"sucesso": True, "texto": texto}), 200
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/engine-final/conferir", methods=["POST"])
    def api_engine_final_conferir():
        try:
            body = request.get_json(silent=True) or {}
            apostas = body.get("apostas") or []
            concurso = body.get("concurso")
            if not apostas:
                return jsonify({"sucesso": False, "erro": "Nenhuma aposta informada."}), 400
            if not concurso:
                return jsonify({"sucesso": False, "erro": "Informe o concurso."}), 400
            resultado = conferir_apostas_engine(modality_key, apostas, int(concurso))
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/engine-final/backtest", methods=["POST"])
    def api_engine_final_backtest():
        try:
            body = request.get_json(silent=True) or {}
            apostas = body.get("apostas") or []
            limite = int(body.get("limite") or 30)
            if not apostas:
                return jsonify({"sucesso": False, "erro": "Nenhuma aposta informada."}), 400
            resultado = backtest_apostas_engine(modality_key, apostas, limite=limite)
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/engine-final/otimizar", methods=["POST"])
    def api_engine_final_otimizar():
        if modality_key not in MODALIDADES_OTIMIZADOR:
            return jsonify({
                "sucesso": False,
                "erro": "Otimizador indisponível para esta modalidade.",
            }), 404
        try:
            body = request.get_json(silent=True) or {}
            apostas = body.get("apostas") or []
            if not apostas:
                return jsonify({"sucesso": False, "erro": "Nenhuma aposta informada."}), 400
            resultado = otimizar_apostas(
                modality_key,
                apostas,
                modo=body.get("modo", "restrito"),
                iteracoes=int(body.get("iteracoes") or 5000),
                janela_historico=int(body.get("janela_historico") or 30),
            )
            if resultado.get("sucesso"):
                bt_orig = backtest_apostas_engine(
                    modality_key, resultado.get("apostas_originais") or apostas,
                    limite=int(body.get("janela_historico") or 30),
                )
                bt_opt = backtest_apostas_engine(
                    modality_key, resultado.get("apostas") or [],
                    limite=int(body.get("janela_historico") or 30),
                )
                resultado["backtest_antes"] = bt_orig
                resultado["backtest_depois"] = bt_opt
            status = 200 if resultado.get("sucesso") else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    def _construtor_svc():
        svc = get_construtor_service(modality_key)
        if not svc:
            raise ValueError(f"Construtor de Construções indisponível para {modality_key}.")
        return svc

    def _construtor_ok():
        return tem_construtor(modality_key)

    @bp.route("/construtor-construcoes/")
    def construtor_construcoes_page():
        if not _construtor_ok():
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        svc = _construtor_svc()
        meses_cores = {}
        if modality_key == "diadesorte":
            try:
                from _shared.diadesorte.meses_cores import obter_meses_cores
                meses_cores = obter_meses_cores()
            except Exception:
                meses_cores = {}
        ball_ui = get_ball_ui(modality_key)
        ultimo_sorteio = svc.obter_ultimo_sorteio()
        if not ultimo_sorteio.get("sucesso"):
            ultimo_sorteio = None
        return render_template(
            "construtor_construcoes.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            cfg=cfg,
            ui_config=svc.ui_config(),
            api_base="/geradores-elite/api/construtor-construcoes",
            meses_cores=meses_cores,
            ultimo_sorteio=ultimo_sorteio,
            ball_css=ball_ui["css"],
            ball_classes=ball_ui["classes"],
            digitos_habilitado=True,
        )

    @bp.route("/gerador-digitos-inteligente/")
    def gerador_digitos_inteligente_page():
        if not _construtor_ok():
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        svc = _construtor_svc()
        ball_ui = get_ball_ui(modality_key)
        return render_template(
            "gerador_digitos_inteligente.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            cfg=cfg,
            ui_config=svc.ui_config(),
            api_base="/geradores-elite/api/construtor-construcoes",
            ball_css=ball_ui["css"],
            ball_classes=ball_ui["classes"],
        )

    def _ai_service():
        from analise_inteligentes_diadesorte.service import make_inteligentes_service
        return make_inteligentes_service(modality_key)

    @bp.route("/gerador-gc/")
    def gerador_gc_page():
        digitos = (request.args.get("digitos") or "").strip()
        concurso = request.args.get("concurso", type=int)
        return render_template(
            "gerador_gc.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            cfg=cfg,
            api_base="/geradores-elite/api/inteligentes",
            digitos_inicial=digitos,
            concurso_inicial=concurso or "",
        )

    @bp.route("/gerador-elite/")
    def gerador_elite_page():
        n = request.args.get("n", type=int)
        digitos = (request.args.get("digitos") or "").strip()
        concurso = request.args.get("concurso", type=int)
        return render_template(
            "gerador_elite.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            cfg=cfg,
            api_base="/geradores-elite/api/inteligentes",
            n_inicial=n or "",
            digitos_inicial=digitos,
            concurso_inicial=concurso or "",
        )

    @bp.route("/api/inteligentes/gerar-gc", methods=["POST"])
    def api_ge_inteligentes_gerar_gc():
        try:
            data = request.get_json(silent=True) or {}
            digitos = data.get("digitos") or []
            if isinstance(digitos, str):
                digitos = [x.strip() for x in digitos.replace(";", ",").split(",") if x.strip() != ""]
            qtd = int(data.get("qtd_jogos") or 10)
            seed = data.get("seed")
            concurso = data.get("concurso")
            concurso = int(concurso) if concurso not in (None, "", 0, "0") else None
            out = _ai_service().gerar_gc(
                digitos, qtd_jogos=qtd, seed=seed, concurso=concurso,
            )
            return jsonify(_pipeline_elite(out, "inteligentes_gc", data)), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/inteligentes/gerar-elite", methods=["POST"])
    def api_ge_inteligentes_gerar_elite():
        try:
            data = request.get_json(silent=True) or {}
            n = int(data.get("n_digitos") or data.get("n") or 6)
            digitos = data.get("digitos")
            if isinstance(digitos, str):
                digitos = [x.strip() for x in digitos.replace(";", ",").split(",") if x.strip() != ""]
            qtd = int(data.get("qtd_jogos") or 10)
            seed = data.get("seed")
            concurso = data.get("concurso")
            concurso = int(concurso) if concurso not in (None, "", 0, "0") else None
            out = _ai_service().gerar_elite(
                n_digitos=n, digitos=digitos, qtd_jogos=qtd, seed=seed, concurso=concurso,
            )
            return jsonify(_pipeline_elite(out, "inteligentes_elite", data)), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/ciclo")
    def api_construtor_ciclo():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            tipo = request.args.get("tipo", "sorteadas")
            return jsonify(_construtor_svc().importar_ciclo(tipo))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/analise-sugestao")
    def api_construtor_analise():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            qtd = int(request.args.get("quantidade", 16))
            criterio = request.args.get("criterio", "atraso")
            return jsonify(_construtor_svc().importar_analise(qtd, criterio))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/comportamento-resumo")
    def api_construtor_comportamento():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            janela = int(request.args.get("janela", 10))
            return jsonify(_construtor_svc().comportamento_resumo(janela))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessoes", methods=["GET"])
    def api_construtor_listar_sessoes():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            return jsonify({"sucesso": True, "sessoes": _construtor_svc().listar_sessoes()})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessao/<int:sessao_id>", methods=["GET"])
    def api_construtor_buscar_sessao(sessao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            data = _construtor_svc().buscar_sessao(sessao_id)
            if not data:
                return jsonify({"sucesso": False, "erro": "Sessão não encontrada."}), 404
            return jsonify({"sucesso": True, "sessao": data})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessao/<int:sessao_id>", methods=["DELETE"])
    def api_construtor_deletar_sessao(sessao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            if not _construtor_svc().deletar_sessao(sessao_id):
                return jsonify({"sucesso": False, "erro": "Sessão não encontrada."}), 404
            return jsonify({"sucesso": True})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessao", methods=["POST"])
    def api_construtor_salvar_sessao():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            svc = _construtor_svc()
            pick_def = svc.ui_config().get("pick_default", 7)
            regras = data.get("regras_somas_digitos")
            if not isinstance(regras, dict):
                regras = None
            return jsonify(svc.salvar_sessao(
                nome=data.get("nome", ""),
                conjunto_base=data.get("conjunto_base") or [],
                dezenas_por_aposta=int(data.get("dezenas_por_aposta", pick_def)),
                origem_conjunto=data.get("origem_conjunto", "manual"),
                sessao_id=data.get("sessao_id"),
                regras_somas_digitos=regras,
            ))
        except ValueError as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 400
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/estatisticas-somas-digitos")
    def api_construtor_estatisticas_somas_digitos():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            from analise_somas_digitos.service import AnaliseSomasDigitosService
            raw = request.args.get("dezenas", "")
            pool = [int(x) for x in raw.replace(";", ",").split(",") if x.strip().isdigit()]
            janela = request.args.get("janela", 0, type=int)
            base = request.args.get("base", "geral")
            return jsonify(AnaliseSomasDigitosService.estatisticas_conjunto(
                modality_key,
                conjunto_base=pool or None,
                janela=janela,
                base_estatistica=base,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/guia")
    def api_construtor_digitos_guia():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            return jsonify(ConstrutorDigitosService.guia(modality_key))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/avaliar", methods=["GET", "POST"])
    def api_construtor_digitos_avaliar():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            if request.method == "POST":
                data = request.get_json(silent=True) or {}
                pool = data.get("pool") or []
                k = data.get("dezenas_por_aposta")
            else:
                raw = request.args.get("pool", "")
                pool = [int(x) for x in raw.replace(";", ",").split(",") if x.strip().isdigit()]
                k = request.args.get("dezenas_por_aposta", type=int)
            return jsonify(ConstrutorDigitosService.avaliar_pool(modality_key, pool, k))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/diagnosticar", methods=["POST"])
    def api_construtor_digitos_diagnosticar():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            exigir = data.get("exigir_qtd_digitos")
            if exigir is not None and exigir != "":
                exigir = int(exigir)
            else:
                exigir = None
            return jsonify(ConstrutorDigitosService.diagnosticar(
                modality_key,
                data.get("pool") or [],
                dezenas_por_aposta=data.get("dezenas_por_aposta"),
                exigir_qtd_digitos=exigir,
                qtd_apostas=int(data.get("qtd_apostas") or 1),
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/sugerir")
    def api_construtor_digitos_sugerir():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            criterio = request.args.get("criterio", "frequencia")
            qtd = int(request.args.get("quantidade", 4))
            return jsonify(ConstrutorDigitosService.sugerir_pool(modality_key, criterio, qtd))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/sessoes", methods=["GET"])
    def api_construtor_digitos_sessoes():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            return jsonify({
                "sucesso": True,
                "sessoes": ConstrutorDigitosService.listar_sessoes_digitos(modality_key),
            })
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/sessao", methods=["POST"])
    def api_construtor_digitos_salvar_sessao():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            pick_def = _construtor_svc().ui_config().get("pick_default", 7)
            return jsonify(ConstrutorDigitosService.salvar_sessao_digitos(
                modality_key,
                nome=data.get("nome", ""),
                pool=data.get("pool") or data.get("conjunto_base") or [],
                dezenas_por_aposta=int(data.get("dezenas_por_aposta", pick_def)),
                origem_conjunto=data.get("origem_conjunto", "manual"),
                sessao_id=data.get("sessao_id"),
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/gerar", methods=["POST"])
    def api_construtor_digitos_gerar():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            exigir = data.get("exigir_qtd_digitos")
            if exigir is not None and exigir != "":
                exigir = int(exigir)
            else:
                exigir = None
            return jsonify(_pipeline_elite(ConstrutorDigitosService.gerar_inteligente(
                modality_key,
                data.get("pool") or [],
                dezenas_por_aposta=data.get("dezenas_por_aposta"),
                qtd_apostas=int(data.get("qtd_apostas", 10)),
                modo=data.get("modo", "frequencia"),
                exigir_qtd_digitos=exigir,
                salvar_sessao=bool(data.get("salvar_sessao")),
                nome_sessao=data.get("nome", ""),
                sessao_id=data.get("sessao_id"),
            ), "construtor_digitos", data))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/combinacoes", methods=["POST"])
    def api_construtor_digitos_combinacoes():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            return jsonify(ConstrutorDigitosService.listar_combinacoes(
                modality_key,
                data.get("pool") or [],
                data.get("dezenas_por_aposta"),
                incluir_apostas=bool(data.get("incluir_apostas", True)),
                limite=data.get("limite"),
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/digitos/export-txt", methods=["POST"])
    def api_construtor_digitos_export_txt():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            from geradores_elite.construtor.universes.digitos_service import ConstrutorDigitosService
            # Mantém critério bruto (atrasado|frequente|aleatorio|N) — serviço resolve
            mes = data.get("mes_num")
            if mes == "":
                mes = None
            return jsonify(ConstrutorDigitosService.exportar_txt(
                modality_key,
                modo=data.get("modo", "lote"),
                pool=data.get("pool") or [],
                dezenas_por_aposta=data.get("dezenas_por_aposta"),
                apostas=data.get("apostas"),
                mes_num=mes,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/gerar", methods=["POST"])
    def api_construtor_gerar():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            sessao_id = int(data["sessao_id"])
            personalizada = data.get("personalizada")
            if personalizada:
                personalizada = {
                    "baixas": int(personalizada.get("baixas", 0)),
                    "medias": int(personalizada.get("medias", 0)),
                    "altas": int(personalizada.get("altas", 0)),
                }
            sim_min = data.get("similaridade_min_pct")
            if sim_min is not None:
                sim_min = float(sim_min)
            # Validação histórico/memória já feita em gerar_construcao — resposta direta (rápido)
            out = _construtor_svc().gerar_construcao(
                sessao_id,
                data.get("estrategia", "conforme_comportamento"),
                personalizada=personalizada,
                janela_comportamento=int(data.get("janela_comportamento", 10)),
                similaridade_min_pct=sim_min,
            )
            return jsonify(out)
        except KeyError:
            return jsonify({"sucesso": False, "erro": "sessao_id obrigatório."}), 400
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/conferir", methods=["POST"])
    def api_construtor_conferir():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(_construtor_svc().conferir_sessao(
                int(data["sessao_id"]),
                int(data["concurso"]),
            ))
        except KeyError:
            return jsonify({"sucesso": False, "erro": "sessao_id e concurso obrigatórios."}), 400
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/ultimo-sorteio")
    def api_construtor_ultimo_sorteio():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            return jsonify(_construtor_svc().obter_ultimo_sorteio())
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/concursos")
    def api_construtor_concursos():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            limite = int(request.args.get("limit", 150))
            return jsonify({"sucesso": True, "concursos": _construtor_svc().listar_concursos(limite)})
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/construcao/<int:construcao_id>", methods=["PUT"])
    def api_construtor_atualizar_construcao(construcao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            mes = data.get("mes_num")
            if mes is not None and mes != "":
                from diadesorte.mes_sorte_select import resolver_mes_sorte
                mes = resolver_mes_sorte(mes)
            else:
                mes = None
            extra = {}
            if data.get("time_num") is not None:
                extra["time_num"] = int(data["time_num"])
            if data.get("trevos"):
                extra["trevos"] = data["trevos"]
            return jsonify(_construtor_svc().atualizar_construcao(
                construcao_id,
                data.get("apostas") or [],
                mes_num=mes,
                extra=extra or None,
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/construcao/<int:construcao_id>", methods=["DELETE"])
    def api_construtor_deletar_construcao(construcao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            return jsonify(_construtor_svc().deletar_construcao(construcao_id))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/construcao/<int:construcao_id>/export-txt", methods=["POST"])
    def api_construtor_export_txt(construcao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            # Critério bruto: atrasado|frequente|aleatorio|N — serviço distribui
            mes = data.get("mes_num")
            if mes == "":
                mes = None
            extra = {}
            if data.get("time_num") is not None:
                extra["time_num"] = int(data["time_num"])
            if data.get("trevos"):
                extra["trevos"] = data["trevos"]
            return jsonify(_construtor_svc().exportar_txt(
                construcao_id, mes_num=mes, extra=extra or None
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessao/<int:sessao_id>/export-txt", methods=["POST"])
    def api_construtor_export_sessao_txt(sessao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            mes = data.get("mes_num")
            if mes == "":
                mes = None
            ids = data.get("construcao_ids")
            return jsonify(_construtor_svc().exportar_sessao_txt(
                sessao_id, mes_num=mes, construcao_ids=ids
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/construcao/<int:construcao_id>/conferir-historico", methods=["POST"])
    def api_construtor_conferir_historico(construcao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            incremental = bool(data.get("incremental", False))
            return jsonify(_construtor_svc().executar_conferencia_historico(
                construcao_id, incremental=incremental
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/construcao/<int:construcao_id>/conferencia-historico")
    def api_construtor_get_conferencia_historico(construcao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            incluir = request.args.get("itens", "").lower() in ("1", "true", "sim")
            return jsonify(_construtor_svc().obter_conferencia_historico(
                construcao_id, incluir_itens=incluir
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessao/<int:sessao_id>/conferir-historico", methods=["POST"])
    def api_construtor_conferir_sessao_historico(sessao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        data = request.get_json(silent=True) or {}
        try:
            incremental = bool(data.get("incremental", False))
            return jsonify(_construtor_svc().executar_conferencia_sessao(
                sessao_id, incremental=incremental
            ))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/panorama-conferencias")
    def api_construtor_panorama_conferencias():
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            return jsonify(_construtor_svc().panorama_conferencias())
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/construtor-construcoes/sessao/<int:sessao_id>/analise-comparativa")
    def api_construtor_analise_comparativa(sessao_id):
        if not _construtor_ok():
            return jsonify({"sucesso": False, "erro": "Indisponível."}), 404
        try:
            return jsonify(_construtor_svc().analisar_comparativo_sessao(sessao_id))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/gerador-por-posicao/")
    def gerador_por_posicao_page():
        from posicao_analise.specs import get_posicao_spec, tem_posicao_analise

        if not tem_posicao_analise(modality_key):
            return render_template(
                "geradores_elite_index.html",
                modality_key=modality_key,
                modality_nome=cfg["nome"],
                cfg=cfg,
            ), 404
        spec = get_posicao_spec(modality_key)
        meses_cores = {}
        if spec.extra_mes:
            try:
                from _shared.diadesorte.meses_cores import obter_meses_cores

                meses_cores = obter_meses_cores() or {}
            except Exception:
                try:
                    from services.cores_meses_service import CoresMesesService

                    meses_cores = CoresMesesService.obter_cores() or {}
                except Exception:
                    meses_cores = {}
        return render_template(
            "gerador_por_posicao.html",
            modality_key=modality_key,
            modality_nome=cfg["nome"],
            pos_cfg=spec.to_ui(),
            meses_cores=meses_cores,
        )

    def _posicao_service():
        from posicao_analise.service_factory import make_service

        return make_service(modality_key)

    @bp.route("/api/posicao/analise")
    def api_posicao_analise():
        from posicao_analise.specs import tem_posicao_analise

        if not tem_posicao_analise(modality_key):
            return jsonify({"sucesso": False, "erro": "Indisponível para esta modalidade."}), 404
        try:
            janela = int(request.args.get("janela", 50))
            sorteio = int(request.args.get("sorteio", 1))
            Svc = _posicao_service()
            return jsonify(Svc.analise_agregada(janela=janela, sorteio=sorteio))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/posicao/concursos")
    def api_posicao_concursos():
        from posicao_analise.specs import tem_posicao_analise

        if not tem_posicao_analise(modality_key):
            return jsonify({"sucesso": False}), 404
        try:
            limite = int(request.args.get("limit", 150))
            sorteio = int(request.args.get("sorteio", 1))
            Svc = _posicao_service()
            return jsonify({
                "sucesso": True,
                "concursos": Svc.listar_concursos(limite, sorteio=sorteio),
            })
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @bp.route("/api/posicao/gerar", methods=["POST"])
    def api_posicao_gerar():
        from posicao_analise.specs import tem_posicao_analise

        if not tem_posicao_analise(modality_key):
            return jsonify({"sucesso": False, "erro": "Indisponível para esta modalidade."}), 404
        data = request.get_json(silent=True) or {}
        try:
            Svc = _posicao_service()
            return jsonify(_pipeline_elite(Svc.gerar_apostas(
                quantidade=int(data.get("quantidade", 10)),
                perfil=data.get("perfil", "equilibrado"),
                janela=int(data.get("janela", 50)),
                filtrar_dig_soma=bool(data.get("filtrar_dig_soma", False)),
                preset=data.get("preset", "manual"),
                usar_repeticao=bool(data.get("usar_repeticao", False)),
                usar_sniper=bool(data.get("usar_sniper", False)),
                usar_comportamento=bool(data.get("usar_comportamento", False)),
                modo_comportamento=data.get("modo_comportamento", "relaxar"),
                sorteio=int(data.get("sorteio", 1)),
            ), "posicao", data))
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    from concentracao_acertos.routes_factory import register_concentracao_gerador
    register_concentracao_gerador(bp, modality_key, cfg["nome"])

    return bp
