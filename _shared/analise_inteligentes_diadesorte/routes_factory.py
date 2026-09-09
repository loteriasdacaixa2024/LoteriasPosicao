# -*- coding: utf-8 -*-
"""Rotas — Resultados & Padrões (Análises Inteligentes)."""
from __future__ import annotations

import os

from flask import Blueprint, Response, jsonify, redirect, render_template, request, send_from_directory

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
    try:
        from gerador_escolha_tubular.service import tem_gerador_escolha_tubular as _tem_get
        tubular_geracao_elite = bool(_tem_get(modality_key))
    except Exception:
        # Fallback: mesma regra do gerador Elite (Super Sete fica nas Análises).
        tubular_geracao_elite = modality_key != "supersete"
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
        "escolha_tubular_url": "/geradores-elite/escolha-tubular-apostas/",
        "tubular_geracao_elite": tubular_geracao_elite,
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
        elif aba in ("panorama", "historico", "historico-completo", "panorama-historico"):
            aba = "panorama"
        elif aba in ("combinacoes", "combinações"):
            aba = "combinacoes"
        elif aba not in (
            "resultados", "combinacoes", "padroes", "padroes-ii",
            "jogos-padrao", "tubular", "panorama",
        ):
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

    @analise_bp.route("/api/inteligentes/resumo-operacional-padroes")
    def api_inteligentes_resumo_operacional_padroes():
        """Tabela operacional: para apostar / já saíram / dentro·próximas·fora por padrão."""
        try:
            base = request.args.get("base", "geral")
            out = Svc.resumo_operacional_padroes(base=base)
            return jsonify(out), (200 if out.get("sucesso") else 400)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/jogos-padrao")
    def api_inteligentes_jogos_padrao():
        """Lista as apostas possíveis de um padrão (coluna Jogos → aba Apostas)."""
        try:
            padrao = (request.args.get("padrao") or "").strip()
            if not padrao:
                return jsonify({"sucesso": False, "erro": "Informe padrao="}), 400
            limite = request.args.get("limite", type=int)
            offset = request.args.get("offset", 0, type=int) or 0
            base = request.args.get("base", "geral")
            formato = (request.args.get("formato") or "json").strip().lower()
            out = Svc.listar_jogos_padrao(padrao, limite=limite, offset=offset, base=base)
            if not out.get("sucesso"):
                return jsonify(out), 400
            if formato in ("txt", "text", "plain"):
                out = Svc.listar_jogos_padrao(padrao, limite=None, offset=0, base=base)
                if not out.get("sucesso"):
                    return jsonify(out), 400
                lines = [j["dezenas_fmt"] for j in (out.get("jogos") or [])]
                header = (
                    f"# Padrao: {out.get('padrao')} ({out.get('descricao')})\n"
                    f"# Total: {out.get('total')}\n"
                    f"# Soma media: {out.get('soma_media')}\n"
                )
                body = header + "\n".join(lines) + ("\n" if lines else "")
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
            if formato in ("xlsx", "excel"):
                exported = Svc.exportar_jogos_padrao_xlsx(padrao, base=base)
                if not exported.get("sucesso"):
                    return jsonify(exported), 400
                return Response(
                    exported["content"],
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="{exported.get("filename") or "apostas.xlsx"}"'
                        )
                    },
                )
            return jsonify(out)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/jogos-padrao/export", methods=["POST"])
    def api_inteligentes_jogos_padrao_export():
        """Exporta CSV/XLSX das apostas (escopo: todas, marcadas ou página)."""
        try:
            data = request.get_json(silent=True) or {}
            padrao = (data.get("padrao") or request.args.get("padrao") or "").strip()
            if not padrao:
                return jsonify({"sucesso": False, "erro": "Informe padrao"}), 400
            formato = (data.get("formato") or "csv").strip().lower()
            base = data.get("base") or "geral"
            dezenas_fmt = data.get("dezenas_fmt") or data.get("dezenas") or None
            ids = data.get("ids")

            out = Svc.listar_jogos_padrao(padrao, limite=None, offset=0, base=base)
            if not out.get("sucesso"):
                return jsonify(out), 400
            jogos = list(out.get("jogos") or [])
            payload_jogos = data.get("jogos")
            if isinstance(payload_jogos, list) and payload_jogos:
                # Interface envia o mesmo recorte exibido (inclui concurso)
                by_dez = {str(j.get("dezenas_fmt") or ""): j for j in jogos}
                merged = []
                for item in payload_jogos:
                    dez = str((item or {}).get("dezenas_fmt") or "").strip()
                    base_j = dict(by_dez.get(dez) or {})
                    if not base_j and item:
                        base_j = dict(item)
                    if item:
                        if item.get("concurso") not in (None, ""):
                            base_j["concurso"] = item.get("concurso")
                        for k in ("soma", "media", "distancia", "status_media", "status_media_label", "id"):
                            if item.get(k) is not None and base_j.get(k) is None:
                                base_j[k] = item.get(k)
                    if base_j.get("dezenas_fmt") or dez:
                        base_j["dezenas_fmt"] = base_j.get("dezenas_fmt") or dez
                        merged.append(base_j)
                jogos = merged
            elif dezenas_fmt:
                want = {str(x).strip() for x in dezenas_fmt if str(x).strip()}
                jogos = [j for j in jogos if str(j.get("dezenas_fmt") or "") in want]
            elif ids:
                want_ids = {int(x) for x in ids}
                jogos = [j for j in jogos if int(j.get("id") or 0) in want_ids]

            modality_nome = out.get("modality_nome") or modality_key
            pad = out.get("padrao") or padrao
            desc = out.get("descricao") or ""

            if formato in ("xlsx", "excel"):
                from analise_inteligentes_diadesorte.soma_media import (
                    build_xlsx_apostas,
                    safe_filename_padrao,
                )
                blob = build_xlsx_apostas(
                    modality_key=out.get("modality_key") or modality_key,
                    modality_nome=modality_nome,
                    padrao=pad,
                    descricao=desc,
                    faixa=out.get("soma_faixa"),
                    jogos=jogos,
                )
                fname = f"apostas_padrao_{safe_filename_padrao(pad)}_{modality_key}.xlsx"
                return Response(
                    blob,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'},
                )

            # CSV — cabeçalhos em MAIÚSCULO; mesma regra da interface
            import csv
            import io
            buf = io.StringIO()
            buf.write("\ufeff")
            w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
            w.writerow([
                "MODALIDADE", "PADRÃO", "DESCRIÇÃO", "APOSTA", "SOMA", "MÉDIA",
                "DISTÂNCIA DA MÉDIA", "STATUS", "CONCURSO", "ID",
            ])
            for j in jogos:
                dist = j.get("distancia")
                dist_s = "" if dist is None else (f"+{dist}" if int(dist) > 0 else str(dist))
                w.writerow([
                    modality_nome,
                    pad,
                    desc,
                    j.get("dezenas_fmt") or "",
                    j.get("soma"),
                    j.get("media") if j.get("media") is not None else "",
                    dist_s,
                    j.get("status_media_label") or "",
                    j.get("concurso") or "",
                    j.get("id") or "",
                ])
            from analise_inteligentes_diadesorte.soma_media import safe_filename_padrao
            fname = f"apostas_padrao_{safe_filename_padrao(pad)}_{modality_key}.csv"
            return Response(
                buf.getvalue().encode("utf-8"),
                mimetype="text/csv; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            )
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

    @analise_bp.route("/api/inteligentes/historico-status")
    def api_inteligentes_historico_status():
        """Status do Panorama Histórico (nível 1 — silencioso)."""
        try:
            from analise_inteligentes_diadesorte.historico_service import status_historico
            out = status_historico()
            return jsonify(out), (200 if out.get("sucesso") else 500)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/historico-backfill", methods=["POST", "GET"])
    def api_inteligentes_historico_backfill():
        """Backfill do histórico a partir dos sorteios já no banco (lotes)."""
        try:
            from analise_inteligentes_diadesorte.historico_service import backfill_historico
            data = request.get_json(silent=True) or {}
            limite = data.get("limite") or request.args.get("limite", type=int) or 300
            apenas = data.get("apenas_faltantes")
            if apenas is None:
                apenas = request.args.get("apenas_faltantes", "1") not in ("0", "false", "False")
            out = backfill_historico(
                limite=int(limite),
                modality_key=modality_key,
                apenas_faltantes=bool(apenas),
            )
            return jsonify(out), (200 if out.get("sucesso") else 500)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/panorama")
    def api_inteligentes_panorama():
        """Panorama Histórico — resumo (nível 2)."""
        try:
            from analise_inteligentes_diadesorte.historico_service import panorama_resumo
            out = panorama_resumo()
            return jsonify(out), (200 if out.get("sucesso") else 500)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500

    @analise_bp.route("/api/inteligentes/historico")
    def api_inteligentes_historico():
        """Histórico completo paginado (nível 3)."""
        try:
            from analise_inteligentes_diadesorte.historico_service import listar_historico
            out = listar_historico(
                offset=request.args.get("offset", 0, type=int) or 0,
                limit=request.args.get("limit", 50, type=int) or 50,
                padrao=(request.args.get("padrao") or "").strip(),
                busca=(request.args.get("busca") or "").strip(),
                ordem=(request.args.get("ordem") or "desc").strip(),
            )
            return jsonify(out), (200 if out.get("sucesso") else 500)
        except Exception as e:
            return jsonify({"sucesso": False, "erro": str(e)}), 500
