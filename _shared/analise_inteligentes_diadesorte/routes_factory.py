# -*- coding: utf-8 -*-
"""Rotas — Resultados & Padrões (Análises Inteligentes)."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory

from analise_inteligentes_diadesorte.service import make_inteligentes_service
from geradores_elite.modality_config import MODALITIES

_PKG = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(_PKG, "static")


def _page_context(modality_key: str) -> dict:
    mod = MODALITIES.get(modality_key) or {}
    nome = mod.get("nome") or modality_key
    dmin = int(mod.get("dezena_min", 1))
    dmax = int(mod.get("dezena_max", 31))
    sorteadas = int(mod.get("sorteadas", mod.get("pick_default", 7)))
    nao_sairam_qtd = max(0, dmax - dmin + 1 - sorteadas)
    extra_mes = (mod.get("extra") == "mes") or (modality_key == "diadesorte")
    meses_cores = {}
    if extra_mes:
        try:
            from services.cores_meses_service import CoresMesesService
            meses_cores = CoresMesesService.obter_cores() or {}
        except Exception:
            try:
                from diadesorte.meses_cores import obter_meses_cores
                meses_cores = obter_meses_cores() or {}
            except Exception:
                meses_cores = {}
    return {
        "modality_key": modality_key,
        "modality_nome": nome,
        "page_title": f"Resultados & Padrões — {nome}",
        "page_subtitle": "Análise · Padrões II alimenta o Construtor e Geradores Elite",
        "api_base": "/analise/api/inteligentes",
        "gerador_gc_url": "/geradores-elite/gerador-gc/",
        "gerador_elite_url": "/geradores-elite/gerador-elite/",
        "geradores_elite_home": "/geradores-elite/",
        "construtor_url": "/geradores-elite/construtor-construcoes/",
        "meses_cores": meses_cores,
        "extra_mes": bool(extra_mes),
        "dezena_min": dmin,
        "dezena_max": dmax,
        "sorteadas": sorteadas,
        "nao_sairam_qtd": nao_sairam_qtd,
    }


def register_analise_inteligentes(analise_bp: Blueprint, modality_key: str) -> None:
    Svc = make_inteligentes_service(modality_key)

    @analise_bp.route("/analises-inteligentes/")
    def analises_inteligentes_page():
        aba = (request.args.get("aba") or "resultados").strip().lower()
        n = request.args.get("n", type=int)
        digitos = (request.args.get("digitos") or "").strip()
        concurso = request.args.get("concurso", type=int)

        if aba in ("gc", "gerar-gc", "gerador-gc"):
            q = []
            if digitos:
                q.append(f"digitos={digitos}")
            qs = ("?" + "&".join(q)) if q else ""
            return redirect(f"/geradores-elite/gerador-gc/{qs}")
        if aba in ("elite", "gerador-elite"):
            q = []
            if n:
                q.append(f"n={n}")
            if digitos:
                q.append(f"digitos={digitos}")
            qs = ("?" + "&".join(q)) if q else ""
            return redirect(f"/geradores-elite/gerador-elite/{qs}")

        if aba in ("padroes", "padrões", "padroes-i", "padroes1"):
            aba = "padroes"
        elif aba in ("padroes-ii", "padroes2", "padrões-ii", "catalogo-padroes", "padroes_ii"):
            aba = "padroes-ii"
        elif aba in ("jogos-padrao", "jogos", "apostas-padrao"):
            aba = "jogos-padrao"
        elif aba in ("tubular", "visualizacao", "visualizacao-tubular"):
            aba = "tubular"
        elif aba in ("combinacoes", "combinações"):
            aba = "combinacoes"
        elif aba not in ("resultados", "combinacoes", "padroes", "padroes-ii", "jogos-padrao", "tubular"):
            aba = "resultados"

        return render_template(
            "analises_inteligentes.html",
            **_page_context(modality_key),
            aba_inicial=aba,
            n_inicial=n or "",
            digitos_inicial=digitos,
            concurso_inicial=concurso or "",
        )

    @analise_bp.route("/api/inteligentes/assets/<path:filename>")
    def api_inteligentes_assets(filename):
        return send_from_directory(_STATIC, filename)

    @analise_bp.route("/api/inteligentes/resultados")
    def api_inteligentes_resultados():
        try:
            janela = request.args.get("janela", 0, type=int) or 0
            base = request.args.get("base", "geral")
            concurso = request.args.get("concurso", type=int)
            out = Svc.listar_resultados(janela=janela, base=base, concurso=concurso)
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/catalogo")
    def api_inteligentes_catalogo():
        try:
            n = request.args.get("n", 8, type=int)
            out = Svc.catalogo(n or 8)
            return jsonify(out)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/estatisticas-historico")
    def api_inteligentes_estatisticas_historico():
        try:
            base = request.args.get("base", "geral")
            out = Svc.estatisticas_historico(base=base)
            return jsonify(out)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/catalogo-padroes")
    def api_inteligentes_catalogo_padroes():
        """Catálogo agregado (Padrões II) — mesma API para Análise e Construtor/Elite."""
        try:
            base = request.args.get("base", "geral")
            out = Svc.catalogo_padroes(base=base)
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/jogos-padrao")
    def api_inteligentes_jogos_padrao():
        """Lista as apostas possíveis de um padrão (coluna Jogos → aba 6)."""
        try:
            padrao = (request.args.get("padrao") or "").strip()
            if not padrao:
                return jsonify({"sucesso": False, "erro": "Informe padrao="}), 400
            limite = request.args.get("limite", type=int)
            offset = request.args.get("offset", 0, type=int) or 0
            formato = (request.args.get("formato") or "json").strip().lower()
            out = Svc.listar_jogos_padrao(padrao, limite=limite, offset=offset)
            if not out.get("sucesso"):
                return jsonify(out), 400
            if formato in ("txt", "text", "plain"):
                out = Svc.listar_jogos_padrao(padrao, limite=None, offset=0)
                if not out.get("sucesso"):
                    return jsonify(out), 400
                lines = [j["dezenas_fmt"] for j in (out.get("jogos") or [])]
                header = (
                    f"# Padrao: {out.get('padrao')} ({out.get('descricao')})\n"
                    f"# Total: {out.get('total')}\n"
                )
                body = header + "\n".join(lines) + ("\n" if lines else "")
                from flask import Response
                return Response(
                    body,
                    mimetype="text/plain; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f"attachment; filename=jogos_padrao_"
                            f"{str(out.get('padrao','')).replace(' ', '')}.txt"
                        )
                    },
                )
            return jsonify(out)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/tubular")
    def api_inteligentes_tubular():
        try:
            base = request.args.get("base", "geral")
            out = Svc.listar_tubular(base=base)
            return jsonify(out)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/gerar-gc", methods=["POST"])
    def api_inteligentes_gerar_gc():
        try:
            data = request.get_json(silent=True) or {}
            digitos = data.get("digitos") or []
            if isinstance(digitos, str):
                digitos = [x.strip() for x in digitos.replace(";", ",").split(",") if x.strip() != ""]
            qtd = int(data.get("qtd_jogos") or 10)
            seed = data.get("seed")
            concurso = data.get("concurso")
            concurso = int(concurso) if concurso not in (None, "", 0, "0") else None
            out = Svc.gerar_gc(digitos, qtd_jogos=qtd, seed=seed, concurso=concurso)
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/gerar-elite", methods=["POST"])
    def api_inteligentes_gerar_elite():
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
            out = Svc.gerar_elite(
                n_digitos=n, digitos=digitos, qtd_jogos=qtd, seed=seed, concurso=concurso,
            )
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
