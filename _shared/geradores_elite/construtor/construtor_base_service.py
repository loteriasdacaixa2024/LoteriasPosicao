# -*- coding: utf-8 -*-
"""Serviço base — Construtor de Construções (todas as modalidades volante)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Type

from geradores_elite.construtor.construcoes_core import (
    QTD_APOSTAS_FIXA,
    calcular_similaridade,
    distribuicao_historica_moda,
    estrategias_ui,
    gerar_construcao,
    padrao_inicial_de,
    pool_por_faixa,
)
from geradores_elite.construtor.construtor_specs import ConstrutorSpec, meses_ui
from geradores_elite.construtor.models import (
    ConstrutorAposta,
    ConstrutorConstrucao,
    ConstrutorConferenciaHistorico,
    ConstrutorConferenciaHistoricoItem,
    ConstrutorSessao,
)
from geradores_elite.engine_final_core import formatar_export_txt
from geradores_elite.modality_config import MESES_ABREV
from geradores_elite.validacao.apostas_ineditas import (
    aposta_ja_sorteada,
    carregar_combinacoes_historicas,
)
from models.shared import db


class ConstrutorBaseService:
    SPEC: ConstrutorSpec
    SorteioModel: Type[Any] = None
    _sorteio_model_path: Optional[tuple] = None

    @classmethod
    def _model(cls) -> Type[Any]:
        if cls.SorteioModel is None and cls._sorteio_model_path:
            mod_name, cls_name = cls._sorteio_model_path
            mod = __import__(mod_name, fromlist=[cls_name])
            cls.SorteioModel = getattr(mod, cls_name)
        if cls.SorteioModel is None:
            raise NotImplementedError(f"SorteioModel não configurado para {cls.__name__}")
        return cls.SorteioModel

    @classmethod
    def _spec(cls) -> ConstrutorSpec:
        return cls.SPEC

    @classmethod
    def _faixa_limites(cls) -> Dict[str, tuple]:
        return cls._spec().faixa_limites()

    @classmethod
    def _fmt_dezena(cls, n: int) -> str:
        w = cls._spec().dezena_fmt_width
        return f"{n:0{w}d}"

    @classmethod
    def _dezenas_from_sorteio(cls, s: Any) -> List[int]:
        if hasattr(s, "dezenas_lista"):
            return list(s.dezenas_lista())
        if hasattr(s, "dezenas"):
            dz = s.dezenas()
            return sorted(dz) if isinstance(dz, set) else list(dz)
        return []

    @classmethod
    def _ciclo_service(cls):
        raise NotImplementedError

    @classmethod
    def _analise_service(cls):
        return None

    @classmethod
    def _comportamento_service(cls):
        raise NotImplementedError

    @classmethod
    def ui_config(cls) -> Dict[str, Any]:
        sp = cls._spec()
        faixas = sp.faixas_ui()
        tiers = sp.acertos_tiers()
        out = {
            "modality_key": sp.modality_key,
            "qtd_apostas_fixa": QTD_APOSTAS_FIXA,
            "pick_min": sp.pick_min,
            "pick_max": sp.pick_max,
            "pick_default": sp.pick_default,
            "total_dezenas": sp.universo,
            "dezena_min": sp.dezena_min,
            "max_conjunto_base": sp.max_conjunto_base,
            "volante_cols": sp.volante_cols,
            "acertos_por_sorteio": sp.acertos_por_sorteio,
            "acertos_min_relevante": sp.acertos_min_relevante,
            "acertos_max_possivel": sp.acertos_max_possivel,
            "acertos_tiers": list(tiers),
            "estrategias": estrategias_ui(faixas),
            "similaridade_min_default": 80,
            "faixas": faixas,
            "faixa_limites": {k: list(v) for k, v in sp.faixa_limites().items()},
            "colinha": sp.colinha(),
            "has_mes": sp.has_mes,
            "has_time": sp.has_time,
            "has_trevos": sp.has_trevos,
            "positional": sp.positional,
            "pad_width": sp.dezena_fmt_width,
            "unidade_aposta": "dezenas",
            "unidade_label_singular": "dezena",
            "unidade_label_plural": "dezenas",
        }
        if sp.has_mes:
            out["meses"] = meses_ui()
        return out

    @classmethod
    def _limitar_conjunto(cls, dezenas: List[int]) -> tuple[List[int], bool]:
        sp = cls._spec()
        ordenadas = sorted(set(dezenas))
        if len(ordenadas) <= sp.max_conjunto_base:
            return ordenadas, False
        return ordenadas[: sp.max_conjunto_base], True

    @classmethod
    def _parse_conjunto(cls, numeros) -> List[int]:
        sp = cls._spec()
        if isinstance(numeros, str):
            raw = [int(x.strip()) for x in numeros.split(",") if x.strip()]
        else:
            raw = [int(x) for x in numeros]
        vistos = set()
        out = []
        for n in raw:
            if n < sp.dezena_min or n > sp.universo:
                raise ValueError(
                    f"Dezena {cls._fmt_dezena(n)} fora do intervalo "
                    f"{cls._fmt_dezena(sp.dezena_min)}–{cls._fmt_dezena(sp.universo)}."
                )
            if n not in vistos:
                vistos.add(n)
                out.append(n)
        return sorted(out)

    @classmethod
    def _validar_tamanho_conjunto(
        cls, pool: List[int], origem_conjunto: str = "manual"
    ) -> Optional[str]:
        sp = cls._spec()
        # Modo "10 apostas × 7": união das dezenas pode passar do máx. do volante.
        max_ok = (
            sp.universo
            if (origem_conjunto or "").strip() == "apostas_10x7"
            else sp.max_conjunto_base
        )
        if len(pool) > max_ok:
            return (
                f"Conjunto-base limitado a {max_ok} dezenas "
                f"(selecionadas: {len(pool)})."
            )
        if len(pool) < sp.pick_min:
            return f"Conjunto-base precisa de ao menos {sp.pick_min} dezenas."
        return None

    @classmethod
    def _dados_analise_dezenas(cls) -> Optional[Dict[str, Any]]:
        analise_svc = cls._analise_service()
        if analise_svc and hasattr(analise_svc, "analise_geral"):
            return analise_svc.analise_geral()
        sp = cls._spec()
        sorteios = (
            db.session.query(cls._model())
            .order_by(cls._model().concurso.desc())
            .all()
        )
        if not sorteios:
            return None
        total = len(sorteios)
        ultimo = sorteios[0].concurso
        freq = {d: 0 for d in range(sp.dezena_min, sp.universo + 1)}
        visto = {d: 0 for d in range(sp.dezena_min, sp.universo + 1)}
        for s in sorteios:
            for d in cls._dezenas_from_sorteio(s):
                if d in freq:
                    freq[d] += 1
                    if visto[d] == 0:
                        visto[d] = s.concurso
        dados = []
        for d in range(sp.dezena_min, sp.universo + 1):
            atraso = (ultimo - visto[d]) if visto[d] > 0 else total
            dados.append({"dezena": d, "freq": freq[d], "atraso": atraso})
        return {"dados": dados, "ultimo_concurso": ultimo}

    @classmethod
    def importar_ciclo(cls, tipo: str = "sorteadas") -> Dict[str, Any]:
        sp = cls._spec()
        ciclo = cls._ciclo_service().obter_ciclo_atual()
        if tipo == "faltantes":
            dezenas = ciclo.get("dezenas_faltantes") or []
            origem = "ciclo_faltantes"
        else:
            dezenas = ciclo.get("dezenas_sorteadas") or []
            origem = "ciclo_sorteadas"
        dezenas, cortado = cls._limitar_conjunto(dezenas)
        out = {
            "sucesso": True,
            "dezenas": dezenas,
            "origem": origem,
            "ciclo_num": ciclo.get("ciclo_num"),
            "total": len(dezenas),
        }
        if cortado:
            out["aviso"] = (
                f"Ciclo tinha mais de {sp.max_conjunto_base} dezenas; "
                f"foram mantidas as {sp.max_conjunto_base} primeiras."
            )
        return out

    @classmethod
    def importar_analise(cls, quantidade: int = 16, criterio: str = "atraso") -> Dict[str, Any]:
        sp = cls._spec()
        analise = cls._dados_analise_dezenas()
        if not analise:
            return {"sucesso": False, "erro": "Sem dados de análise."}
        dados = analise.get("dados") or []
        qtd = max(sp.pick_min, min(int(quantidade), sp.max_conjunto_base))
        if criterio == "frequencia":
            ordenados = sorted(dados, key=lambda x: (-x["freq"], x["dezena"]))
        else:
            ordenados = sorted(dados, key=lambda x: (-x["atraso"], x["dezena"]))
        dezenas = [d["dezena"] for d in ordenados[:qtd]]
        return {
            "sucesso": True,
            "dezenas": sorted(dezenas),
            "origem": f"analise_{criterio}",
            "total": len(dezenas),
            "ultimo_concurso": analise.get("ultimo_concurso"),
        }

    @classmethod
    def comportamento_resumo(cls, janela: int = 10) -> Dict[str, Any]:
        sp = cls._spec()
        limites = cls._faixa_limites()
        analise = cls._comportamento_service().analisar(janela=janela)
        if not analise.get("sucesso"):
            return analise
        q = db.session.query(cls._model()).order_by(cls._model().concurso.desc())
        if janela > 0:
            sorteios = q.limit(janela).all()
            sorteios = list(reversed(sorteios))
        else:
            sorteios = (
                db.session.query(cls._model())
                .order_by(cls._model().concurso.asc())
                .all()
            )
        dezenas_hist = [cls._dezenas_from_sorteio(s) for s in sorteios]
        moda_bma = distribuicao_historica_moda(dezenas_hist, limites)
        resumo = analise.get("resumo") or {}
        criterios = analise.get("criterios_sugeridos") or {}
        return {
            "sucesso": True,
            "janela": janela,
            "moda_bma": moda_bma,
            "criterios_sugeridos": criterios,
            "resumo_indicadores": {
                cod: {"moda": info.get("moda"), "moda_pct": info.get("moda_pct")}
                for cod, info in resumo.items()
                if isinstance(info, dict)
            },
        }

    @classmethod
    def _validar_somas_digitos_opcional(
        cls,
        pool: List[int],
        regras: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Gate opcional de soma/dígitos no conjunto-base (não altera geração)."""
        if not regras:
            return None
        try:
            from analise_somas_digitos.service import AnaliseSomasDigitosService
        except Exception:
            return None
        soma_min = regras.get("soma_min")
        soma_max = regras.get("soma_max")
        digitos_exigidos = regras.get("digitos_exigidos")
        exigir_digitos = bool(regras.get("exigir_digitos"))
        if soma_min is None and soma_max is None and not exigir_digitos:
            return None
        out = AnaliseSomasDigitosService.validar_conjunto_base(
            cls._spec().modality_key,
            pool,
            soma_min=int(soma_min) if soma_min is not None and soma_min != "" else None,
            soma_max=int(soma_max) if soma_max is not None and soma_max != "" else None,
            digitos_exigidos=int(digitos_exigidos) if digitos_exigidos not in (None, "") else None,
            exigir_digitos=exigir_digitos,
        )
        if out.get("valido"):
            return None
        return " ".join(out.get("erros") or ["Conjunto-base fora das regras de soma/dígitos."])

    @classmethod
    def salvar_sessao(
        cls,
        nome: str,
        conjunto_base: List[int],
        dezenas_por_aposta: int,
        origem_conjunto: str = "manual",
        sessao_id: Optional[int] = None,
        regras_somas_digitos: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sp = cls._spec()
        pool = cls._parse_conjunto(conjunto_base)
        err = cls._validar_tamanho_conjunto(pool, origem_conjunto)
        if err:
            return {"sucesso": False, "erro": err}
        err_sd = cls._validar_somas_digitos_opcional(pool, regras_somas_digitos)
        if err_sd:
            return {"sucesso": False, "erro": err_sd}
        k = max(sp.pick_min, min(int(dezenas_por_aposta), sp.pick_max))
        conj_str = ",".join(cls._fmt_dezena(d) for d in pool)
        if sessao_id:
            sessao = db.session.get(ConstrutorSessao, sessao_id)
            if not sessao:
                return {"sucesso": False, "erro": "Sessão não encontrada."}
            tipo = getattr(sessao, "tipo_universo", None) or "dezenas"
            if tipo not in ("dezenas", "", None):
                return {"sucesso": False, "erro": "Sessão não é do tipo dezenas (Aba 1)."}
            sessao.nome = nome.strip() or sessao.nome
            sessao.conjunto_base = conj_str
            sessao.dezenas_por_aposta = k
            sessao.origem_conjunto = origem_conjunto
            sessao.tipo_universo = "dezenas"
        else:
            sessao = ConstrutorSessao(
                nome=nome.strip() or f"Construção {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                conjunto_base=conj_str,
                dezenas_por_aposta=k,
                origem_conjunto=origem_conjunto,
                tipo_universo="dezenas",
            )
            db.session.add(sessao)
        db.session.commit()
        return {"sucesso": True, "sessao": cls._serializar_sessao(sessao, incluir_construcoes=True)}

    @classmethod
    def _padroes_iniciais_historicos(cls, limite: int = 500) -> List[str]:
        """Lista padrao_inicial dos concursos (dezenas ordenadas), mais recentes primeiro."""
        Model = cls._model()
        rows = (
            db.session.query(Model)
            .order_by(Model.concurso.desc())
            .limit(max(50, int(limite)))
            .all()
        )
        out: List[str] = []
        for s in rows:
            dz = cls._dezenas_from_sorteio(s)
            if dz:
                out.append(padrao_inicial_de(sorted(dz)))
        return out

    @classmethod
    def gerar_construcao(
        cls,
        sessao_id: int,
        estrategia: str,
        *,
        personalizada: Optional[Dict[str, int]] = None,
        janela_comportamento: int = 10,
        similaridade_min_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        limites = cls._faixa_limites()
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        tipo = getattr(sessao, "tipo_universo", None) or "dezenas"
        if tipo == "digitos":
            return {"sucesso": False, "erro": "Use o Gerador Inteligente por Dígitos para sessões de dígitos."}
        pool = sessao.conjunto_lista()
        k = sessao.dezenas_por_aposta
        comportamento_moda = None
        if estrategia == "conforme_comportamento":
            comp = cls.comportamento_resumo(janela_comportamento)
            if not comp.get("sucesso"):
                return comp
            comportamento_moda = comp.get("moda_bma")
        anteriores = [[a.dezenas_lista() for a in c.apostas] for c in sessao.construcoes]
        # Apostas já usadas na sessão (evita repetir o mesmo jogo em outro clique)
        excluidas: Set = set()
        for c in sessao.construcoes:
            for a in c.apostas:
                excluidas.add(frozenset(a.dezenas_lista()))
        historico = carregar_combinacoes_historicas(cls._model(), cls._dezenas_from_sorteio)
        padroes_hist = cls._padroes_iniciais_historicos()
        sim_min = similaridade_min_pct if similaridade_min_pct is not None else 80.0
        sim_max = 1.0 - (sim_min / 100.0)

        # Preenche até QTD_APOSTAS_FIXA com retry + sobregeneração (sobrevive à validação global)
        MAX_ROUNDS = 10
        apostas_ok: List[List[int]] = []
        ultimo_resultado: Optional[Dict[str, Any]] = None
        rejeitadas_vg = 0
        modality_key = cls._spec().modality_key

        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
        except Exception:
            ValidadorGeradoresElite = None  # type: ignore

        for round_i in range(MAX_ROUNDS):
            faltam = QTD_APOSTAS_FIXA - len(apostas_ok)
            if faltam <= 0:
                break
            # Pede extras para compensar rejeições de histórico/memória
            pedir = min(24, max(faltam + 8, faltam * 2))
            tentativas_core = 80 if round_i > 0 else 220

            resultado = gerar_construcao(
                pool, k, estrategia,
                personalizada=personalizada,
                comportamento_moda=comportamento_moda,
                construcoes_anteriores=anteriores,
                similaridade_max=sim_max,
                limites=limites,
                historico_sorteados=historico,
                apostas_excluidas=excluidas,
                padroes_historicos=padroes_hist,
                quantidade=pedir,
                max_tentativas=tentativas_core,
            )
            if not resultado.get("sucesso") and pedir != faltam:
                resultado = gerar_construcao(
                    pool, k, estrategia,
                    personalizada=personalizada,
                    comportamento_moda=comportamento_moda,
                    construcoes_anteriores=anteriores,
                    similaridade_max=sim_max,
                    limites=limites,
                    historico_sorteados=historico,
                    apostas_excluidas=excluidas,
                    padroes_historicos=padroes_hist,
                    quantidade=faltam,
                    max_tentativas=tentativas_core + 80,
                )
            if not resultado.get("sucesso"):
                if apostas_ok:
                    continue
                return resultado
            ultimo_resultado = resultado

            candidatas: List[List[int]] = []
            for ap in resultado.get("apostas") or []:
                dz = [int(x) for x in ap]
                chave = frozenset(dz)
                if chave in excluidas:
                    continue
                if aposta_ja_sorteada(dz, historico):
                    excluidas.add(chave)
                    continue
                candidatas.append(dz)

            if not candidatas:
                continue

            if ValidadorGeradoresElite is not None:
                vg = ValidadorGeradoresElite.validar_lote(
                    candidatas,
                    origem="construtor_construcoes",
                    modality_key=modality_key,
                    sorteio_model=cls._model(),
                    dezenas_fn=cls._dezenas_from_sorteio,
                    registrar_aprovadas=False,
                )
                rejeitadas_vg += len(vg.get("rejeitadas") or [])
                for rej in vg.get("rejeitadas") or []:
                    ch = rej.get("chave")
                    if ch:
                        excluidas.add(frozenset(int(x) for x in ch))
                novos = vg.get("aprovados") or []
            else:
                novos = candidatas

            for ap in novos:
                dz = [int(x) for x in ap]
                chave = frozenset(dz)
                if chave in excluidas:
                    continue
                apostas_ok.append(dz)
                excluidas.add(chave)
                if len(apostas_ok) >= QTD_APOSTAS_FIXA:
                    break

        if len(apostas_ok) < QTD_APOSTAS_FIXA:
            return {
                "sucesso": False,
                "erro": (
                    "Não foi possível completar "
                    f"{QTD_APOSTAS_FIXA} apostas inéditas após novas tentativas "
                    f"(obtidas {len(apostas_ok)}). "
                    "Amplie o conjunto-base ou gere novamente."
                ),
                "qtd_obtidas": len(apostas_ok),
                "rejeitadas_validacao": rejeitadas_vg,
            }

        apostas_ok = apostas_ok[:QTD_APOSTAS_FIXA]
        resultado = ultimo_resultado or {}

        # Registra só o lote final na memória compartilhada
        if ValidadorGeradoresElite is not None:
            try:
                ValidadorGeradoresElite.validar_lote(
                    apostas_ok,
                    origem="construtor_construcoes",
                    modality_key=modality_key,
                    sorteio_model=cls._model(),
                    dezenas_fn=cls._dezenas_from_sorteio,
                    registrar_aprovadas=True,
                    checar_historico=False,
                    checar_memoria=False,
                )
            except Exception:
                pass

        numero = len(sessao.construcoes) + 1
        params = {
            "personalizada": personalizada,
            "janela_comportamento": janela_comportamento,
            "similaridade_min_pct": sim_min,
            "comportamento_moda": comportamento_moda,
            "padroes_iniciais": resultado.get("padroes_iniciais"),
            "qtd_padroes_distintos": resultado.get("qtd_padroes_distintos"),
        }
        dist = resultado.get("distribuicao") or {}
        construcao = ConstrutorConstrucao(
            sessao_id=sessao.id,
            numero=numero,
            estrategia=estrategia,
            estrategia_params=json.dumps(params, ensure_ascii=False),
            distribuicao=",".join(f"{dist.get(f, 0)}" for f in ("baixas", "medias", "altas")),
            similaridade_anterior=resultado.get("similaridade_max_anterior"),
            diferenca_pct=resultado.get("diferenca_min_pct"),
        )
        db.session.add(construcao)
        db.session.flush()
        for i, ap in enumerate(apostas_ok, start=1):
            db.session.add(ConstrutorAposta(
                construcao_id=construcao.id,
                linha=i,
                dezenas=",".join(cls._fmt_dezena(d) for d in ap),
            ))
        db.session.commit()
        qtd_sessao = numero
        aviso = resultado.get("aviso")
        if rejeitadas_vg:
            extra = (
                f"{rejeitadas_vg} candidata(s) trocadas automaticamente "
                "(histórico/outro gerador)."
            )
            aviso = f"{aviso} {extra}".strip() if aviso else extra
        return {
            "sucesso": True,
            "construcao": cls._serializar_construcao(construcao),
            "aviso": aviso,
            "distribuicao": dist,
            "pool_faixas": pool_por_faixa(pool, limites),
            "padroes_iniciais": resultado.get("padroes_iniciais"),
            "qtd_padroes_distintos": resultado.get("qtd_padroes_distintos"),
            "matriz_similaridade": cls._matriz_similaridade(sessao),
            "qtd_apostas": len(apostas_ok),
            "qtd_construcoes": qtd_sessao,
            "qtd_construcoes_sessao": qtd_sessao,
            "rejeitadas_validacao_trocadas": rejeitadas_vg,
        }

    @classmethod
    def _matriz_similaridade(cls, sessao: ConstrutorSessao) -> List[Dict[str, Any]]:
        matrix = []
        construcoes = sessao.construcoes
        for i, ca in enumerate(construcoes):
            apostas_a = [a.dezenas_lista() for a in ca.apostas]
            for j, cb in enumerate(construcoes):
                if j >= i:
                    continue
                sim = calcular_similaridade(apostas_a, [a.dezenas_lista() for a in cb.apostas])
                matrix.append({"de": ca.numero, "para": cb.numero, **sim})
        return matrix

    @classmethod
    def listar_sessoes(cls) -> List[Dict[str, Any]]:
        """Aba 1 — apenas sessões de dezenas (legado sem tipo = dezenas)."""
        from sqlalchemy import or_
        rows = (
            db.session.query(ConstrutorSessao)
            .filter(
                or_(
                    ConstrutorSessao.tipo_universo == "dezenas",
                    ConstrutorSessao.tipo_universo.is_(None),
                    ConstrutorSessao.tipo_universo == "",
                )
            )
            .order_by(ConstrutorSessao.id.desc())
            .all()
        )
        return [cls._serializar_sessao(s, incluir_construcoes=False) for s in rows]

    @classmethod
    def buscar_sessao(cls, sessao_id: int) -> Optional[Dict[str, Any]]:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return None
        data = cls._serializar_sessao(sessao, incluir_construcoes=True)
        data["matriz_similaridade"] = cls._matriz_similaridade(sessao)
        return data

    @classmethod
    def deletar_construcao(cls, construcao_id: int) -> Dict[str, Any]:
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        sessao_id = construcao.sessao_id
        db.session.delete(construcao)
        db.session.flush()
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if sessao:
            for i, rem in enumerate(sorted(sessao.construcoes, key=lambda x: x.numero), start=1):
                rem.numero = i
        db.session.commit()
        return {"sucesso": True, "sessao": cls.buscar_sessao(sessao_id)}

    @classmethod
    def _validar_apostas_edicao(
        cls, pool: List[int], k: int, apostas: List[Dict[str, Any]]
    ) -> Optional[str]:
        if len(apostas) != QTD_APOSTAS_FIXA:
            return f"Cada construção deve ter exatamente {QTD_APOSTAS_FIXA} apostas."
        pool_set = set(pool)
        vistos: set = set()
        for ap in apostas:
            dz = sorted(int(d) for d in (ap.get("dezenas") or []))
            if len(dz) != k:
                return f"Aposta {ap.get('linha', '?')}: esperado {k} dezenas, recebido {len(dz)}."
            if len(set(dz)) != k:
                return f"Aposta {ap.get('linha', '?')}: dezenas repetidas."
            for d in dz:
                if d not in pool_set:
                    return f"Aposta {ap.get('linha', '?')}: dezena {cls._fmt_dezena(d)} fora do conjunto-base."
            chave = tuple(dz)
            if chave in vistos:
                return f"Apostas duplicadas na construção (linha {ap.get('linha')})."
            vistos.add(chave)
        return None

    @classmethod
    def atualizar_construcao(
        cls,
        construcao_id: int,
        apostas: List[Dict[str, Any]],
        mes_num: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        sessao = construcao.sessao
        pool = sessao.conjunto_lista()
        k = sessao.dezenas_por_aposta
        err = cls._validar_apostas_edicao(pool, k, apostas)
        if err:
            return {"sucesso": False, "erro": err}
        sp = cls._spec()
        if sp.has_mes and mes_num is not None:
            from diadesorte.mes_sorte_select import resolver_mes_sorte
            mes_num = resolver_mes_sorte(mes_num)
            if mes_num is None or mes_num < 1 or mes_num > 12:
                return {"sucesso": False, "erro": "Mês da Sorte deve ser entre 1 e 12."}
            construcao.mes_num = mes_num
        if extra:
            if sp.has_time and extra.get("time_num") is not None:
                construcao.mes_num = int(extra["time_num"])
            if sp.has_trevos:
                ex = construcao.extra_dict()
                if extra.get("trevos"):
                    ex["trevos"] = sorted(int(t) for t in extra["trevos"])
                construcao.extra_json = json.dumps(ex, ensure_ascii=False)
        for ap in construcao.apostas:
            db.session.delete(ap)
        db.session.flush()
        for i, ap in enumerate(sorted(apostas, key=lambda x: int(x.get("linha", 0))), start=1):
            dz = sorted(int(d) for d in ap["dezenas"])
            db.session.add(ConstrutorAposta(
                construcao_id=construcao.id,
                linha=i,
                dezenas=",".join(cls._fmt_dezena(d) for d in dz),
            ))
        db.session.commit()
        return {
            "sucesso": True,
            "construcao": cls._serializar_construcao(construcao),
            "sessao": cls.buscar_sessao(sessao.id),
        }

    @classmethod
    def _resolver_meses_export(
        cls,
        mes_raw: Any,
        qtd_apostas: int,
        construcao: Any,
        *,
        meses_pre: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Resolve critério do select → lista de meses (1 por aposta).
        meses_pre: fatia já distribuída (export de sessão com + Aleatório).
        """
        from diadesorte.mes_sorte_select import (
            eh_criterio_aleatorio,
            resolver_mes_sorte,
            resolver_meses_para_lote,
        )

        sp = cls._spec()
        if meses_pre is not None:
            if len(meses_pre) != qtd_apostas:
                return {"sucesso": False, "erro": "Distribuição de meses inconsistente."}
            return {"sucesso": True, "meses": [int(m) for m in meses_pre], "criterio": "aleatorio"}

        raw = mes_raw if mes_raw is not None and mes_raw != "" else construcao.mes_num
        if raw is None or raw == "":
            if sp.modality_key == "diadesorte":
                from diadesorte.meses_indicados import carregar_meses_indicados, mes_ciclo
                from models.sorteio_diadesorte import SorteioDiaDeSorte

                analise_ms = carregar_meses_indicados(SorteioDiaDeSorte)
                if analise_ms.get("sem_indicados"):
                    return {
                        "sucesso": False,
                        "erro": (
                            "Nenhum mês indicado nos últimos 10 concursos. "
                            "Selecione o mês manualmente no export."
                        ),
                    }
                nums = analise_ms.get("meses_indicados_nums") or []
                mn = mes_ciclo(nums, max(0, int(construcao.numero) - 1))
                if mn is None:
                    return {"sucesso": False, "erro": "Selecione o Mês da Sorte para exportar."}
                return {"sucesso": True, "meses": [int(mn)] * qtd_apostas, "criterio": "indicado"}
            analise = cls._dados_analise_dezenas()
            meses = (analise or {}).get("dados_meses") or []
            if meses:
                mn = int(max(meses, key=lambda m: m.get("atraso", 0)).get("mes_num", 1))
            else:
                mn = 1
            return {"sucesso": True, "meses": [mn] * qtd_apostas, "criterio": "atrasado"}

        if isinstance(raw, (list, tuple)):
            meses = [int(m) for m in raw]
            if len(meses) != qtd_apostas or any(m < 1 or m > 12 for m in meses):
                return {"sucesso": False, "erro": "Mês da Sorte inválido."}
            return {"sucesso": True, "meses": meses, "criterio": "lista"}

        if eh_criterio_aleatorio(raw):
            meses = resolver_meses_para_lote(raw, qtd_apostas)
            return {"sucesso": True, "meses": meses, "criterio": "aleatorio"}

        mn = resolver_mes_sorte(raw) if not isinstance(raw, int) else int(raw)
        if mn is None or mn < 1 or mn > 12:
            return {"sucesso": False, "erro": "Mês da Sorte inválido."}
        criterio = "fixo"
        if isinstance(raw, str):
            low = raw.strip().lower()
            if low in ("atrasado", "frequente"):
                criterio = low
        return {"sucesso": True, "meses": [int(mn)] * qtd_apostas, "criterio": criterio}

    @classmethod
    def exportar_txt(
        cls,
        construcao_id: int,
        mes_num: Any = None,
        extra: Optional[Dict[str, Any]] = None,
        *,
        meses_pre: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        sp = cls._spec()
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        apostas = [{"dezenas": a.dezenas_lista()} for a in construcao.apostas]
        export_extra: Dict[str, Any] = {}
        meses_export: Optional[List[int]] = None
        if sp.has_mes:
            resolvido = cls._resolver_meses_export(
                mes_num, len(apostas), construcao, meses_pre=meses_pre
            )
            if not resolvido.get("sucesso"):
                return resolvido
            meses_export = resolvido["meses"]
            for ap, mn in zip(apostas, meses_export):
                ap["extras"] = {
                    "tipo": "mes",
                    "num": int(mn),
                    "label": MESES_ABREV.get(int(mn), str(mn)),
                }
            # Persistência: critério fixo → mês único; aleatório → 1º do lote
            mn_store = int(meses_export[0]) if meses_export else None
            if mn_store and construcao.mes_num != mn_store:
                construcao.mes_num = mn_store
            export_extra = {
                "tipo": "mes",
                "num": mn_store,
                "label": MESES_ABREV.get(mn_store, str(mn_store)) if mn_store else "",
            }
        elif sp.has_time:
            tn = (extra or {}).get("time_num") or construcao.mes_num
            if tn is None:
                return {"sucesso": False, "erro": "Selecione o Time do Coração."}
            tn = int(tn)
            label = cls._time_label(tn)
            export_extra = {"tipo": "time", "num": tn, "label": label}
            construcao.mes_num = tn
        elif sp.has_trevos:
            ex = construcao.extra_dict()
            tr = (extra or {}).get("trevos") or ex.get("trevos") or [1, 2]
            tr = sorted(int(t) for t in tr)[:2]
            if len(tr) < 2:
                return {"sucesso": False, "erro": "Selecione 2 trevos."}
            export_extra = {"tipo": "trevo", "numeros": tr}
            construcao.extra_json = json.dumps({"trevos": tr}, ensure_ascii=False)
        texto = formatar_export_txt(sp.modality_key, apostas, export_extra)
        db.session.commit()
        sessao = construcao.sessao
        nome_arq = f"construcao_{construcao.numero}_{sessao.nome[:30].replace(' ', '_')}.txt"
        out = {"sucesso": True, "texto": texto, "nome_arquivo": nome_arq, "construcao_numero": construcao.numero}
        if sp.has_mes and meses_export:
            out.update({
                "mes_num": meses_export[0],
                "mes_abrev": MESES_ABREV.get(meses_export[0], ""),
                "meses_por_aposta": meses_export,
            })
        return out

    @classmethod
    def exportar_sessao_txt(
        cls,
        sessao_id: int,
        mes_num: Any = None,
        construcao_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Exporta uma ou todas as construções da sessão em um único TXT."""
        from diadesorte.mes_sorte_select import eh_criterio_aleatorio, resolver_meses_para_lote

        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        construcoes = list(sessao.construcoes or [])
        if construcao_ids:
            ids = {int(x) for x in construcao_ids}
            construcoes = [c for c in construcoes if c.id in ids]
        if not construcoes:
            return {"sucesso": False, "erro": "Nenhuma construção para exportar."}

        # + Aleatório: distribuição contínua no total de apostas da sessão
        fatias: Optional[List[List[int]]] = None
        if eh_criterio_aleatorio(mes_num):
            counts = [len(list(c.apostas or [])) for c in construcoes]
            total = sum(counts)
            todos = resolver_meses_para_lote("aleatorio", total)
            fatias = []
            i = 0
            for n in counts:
                fatias.append(todos[i:i + n])
                i += n

        blocos: List[str] = []
        for idx, c in enumerate(construcoes):
            kwargs: Dict[str, Any] = {"mes_num": mes_num}
            if fatias is not None:
                kwargs["meses_pre"] = fatias[idx]
            r = cls.exportar_txt(c.id, **kwargs)
            if not r.get("sucesso"):
                return r
            blocos.append(f"# Construção {c.numero}\n{r['texto'].rstrip()}")
        texto = "\n\n".join(blocos) + "\n"
        nome = f"construcoes_{sessao.nome[:30].replace(' ', '_')}.txt"
        return {
            "sucesso": True,
            "texto": texto,
            "nome_arquivo": nome,
            "qtd_construcoes": len(construcoes),
        }

    @classmethod
    def _time_label(cls, time_num: int) -> str:
        return str(time_num)

    @classmethod
    def deletar_sessao(cls, sessao_id: int) -> bool:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return False
        db.session.delete(sessao)
        db.session.commit()
        return True

    @classmethod
    def _contar_acertos(cls, dezenas: List[int], sorteadas: Set[int]) -> int:
        sp = cls._spec()
        return min(len(set(dezenas) & sorteadas), sp.acertos_max_possivel)

    @classmethod
    def _acertos_linha_sorteio(cls, dezenas: List[int], sorteio: Any) -> int:
        return cls._contar_acertos(dezenas, set(cls._dezenas_from_sorteio(sorteio)))

    @classmethod
    def conferir_sessao(cls, sessao_id: int, concurso: int) -> Dict[str, Any]:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        sorteio = db.session.get(cls._model(), concurso)
        if not sorteio:
            return {"sucesso": False, "erro": f"Concurso {concurso} não encontrado."}
        sorteadas = set(cls._dezenas_from_sorteio(sorteio))
        ranking = []
        for construcao in sessao.construcoes:
            apostas_scores = []
            for aposta in construcao.apostas:
                dz = aposta.dezenas_lista()
                acertos = cls._acertos_linha_sorteio(dz, sorteio)
                apostas_scores.append({
                    "linha": aposta.linha,
                    "dezenas": dz,
                    "acertos": acertos,
                    "acertadas": sorted(set(dz) & sorteadas),
                })
            max_acertos = max((a["acertos"] for a in apostas_scores), default=0)
            total_acertos = sum(a["acertos"] for a in apostas_scores)
            media_acertos = round(total_acertos / len(apostas_scores), 2) if apostas_scores else 0
            ranking.append({
                "construcao_numero": construcao.numero,
                "construcao_id": construcao.id,
                "estrategia": construcao.estrategia,
                "estrategia_params": construcao.params_dict(),
                "distribuicao": cls._distribuicao_dict(construcao),
                "max_acertos": max_acertos,
                "total_acertos": total_acertos,
                "media_acertos": media_acertos,
                "apostas": apostas_scores,
            })
        ranking.sort(key=lambda x: (-x["max_acertos"], -x["total_acertos"], -x["media_acertos"]))
        out = {
            "sucesso": True,
            "concurso": concurso,
            "data": getattr(sorteio, "data", ""),
            "sorteadas": sorted(sorteadas),
            "ranking": ranking,
            "melhor_construcao": ranking[0]["construcao_numero"] if ranking else None,
        }
        out.update(cls._extras_ultimo_sorteio(sorteio))
        return out

    @classmethod
    def _extras_ultimo_sorteio(cls, sorteio: Any) -> Dict[str, Any]:
        sp = cls._spec()
        out: Dict[str, Any] = {}
        if sp.has_mes:
            mn = getattr(sorteio, "mes_num", None)
            if mn:
                out["mes_num"] = mn
                out["mes_abrev"] = MESES_ABREV.get(mn, "")
        return out

    @classmethod
    def obter_ultimo_sorteio(cls) -> Dict[str, Any]:
        sorteio = (
            db.session.query(cls._model())
            .order_by(cls._model().concurso.desc())
            .first()
        )
        if not sorteio:
            return {"sucesso": False, "erro": "Nenhum sorteio no banco."}
        out = {
            "sucesso": True,
            "concurso": sorteio.concurso,
            "data": getattr(sorteio, "data", ""),
            "dezenas": cls._dezenas_from_sorteio(sorteio),
        }
        out.update(cls._extras_ultimo_sorteio(sorteio))
        return out

    @classmethod
    def listar_concursos(cls, limit: int = 150) -> List[Dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        rows = (
            db.session.query(cls._model())
            .order_by(cls._model().concurso.desc())
            .limit(lim)
            .all()
        )
        return [{"concurso": s.concurso, "data": getattr(s, "data", ""), "dezenas": cls._dezenas_from_sorteio(s)} for s in rows]

    @classmethod
    def _scores_construcao_sorteios(
        cls, construcao: ConstrutorConstrucao, sorteios: List[Any]
    ) -> List[Dict[str, Any]]:
        apostas = [a.dezenas_lista() for a in construcao.apostas]
        if not apostas:
            return []
        out = []
        for sorteio in sorteios:
            scores = [cls._acertos_linha_sorteio(dz, sorteio) for dz in apostas]
            max_a = max(scores)
            out.append({
                "concurso": sorteio.concurso,
                "data": getattr(sorteio, "data", "") or "",
                "max_acertos": max_a,
                "media_acertos": round(sum(scores) / len(scores), 2),
                "total_acertos": sum(scores),
                "melhor_linha": scores.index(max_a) + 1,
            })
        return out

    @classmethod
    def _resumo_conferencia_items(cls, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        tiers = cls._spec().acertos_tiers()
        if not items:
            base = {
                "total_pontos": 0,
                "media_max_acertos": 0.0,
                "concursos_total": 0,
                "distribuicao_max": {},
                "melhor_concurso": None,
            }
            for t in tiers:
                base[f"concursos_{t}"] = 0
            base[f"concursos_{tiers[0]}_a_{tiers[-1]}"] = 0
            return base
        total_pontos = sum(i["max_acertos"] for i in items)
        media_max = round(total_pontos / len(items), 2)
        dist: Dict[str, int] = {}
        for i in items:
            k = str(i["max_acertos"])
            dist[k] = dist.get(k, 0) + 1
        melhor = max(items, key=lambda x: (x["max_acertos"], -x["concurso"]))
        out = {
            "total_pontos": total_pontos,
            "media_max_acertos": media_max,
            "concursos_total": len(items),
            "distribuicao_max": dist,
            "melhor_concurso": {
                "concurso": melhor["concurso"],
                "data": melhor.get("data", ""),
                "max_acertos": melhor["max_acertos"],
                "melhor_linha": melhor.get("melhor_linha"),
            },
        }
        for t in tiers:
            out[f"concursos_{t}"] = sum(1 for i in items if i["max_acertos"] == t)
        out[f"concursos_{tiers[0]}_a_{tiers[-1]}"] = sum(out[f"concursos_{t}"] for t in tiers)
        return out

    @classmethod
    def _normalizar_resumo(cls, resumo: Dict[str, Any]) -> Dict[str, Any]:
        tiers = cls._spec().acertos_tiers()
        r = dict(resumo or {})
        dist = r.get("distribuicao_max") or {}
        for t in tiers:
            r[f"concursos_{t}"] = int(dist.get(str(t), r.get(f"concursos_{t}", 0)))
        r[f"concursos_{tiers[0]}_a_{tiers[-1]}"] = sum(r[f"concursos_{t}"] for t in tiers)
        return r

    @classmethod
    def _chave_desempenho_acertos(cls, row: Dict[str, Any]) -> tuple:
        tiers = cls._spec().acertos_tiers()
        chave = tuple(row.get(f"concursos_{t}", 0) for t in reversed(tiers))
        return chave + (row.get("media_max_acertos", 0),)

    @classmethod
    def _ultima_conferencia(cls, construcao_id: int) -> Optional[ConstrutorConferenciaHistorico]:
        return (
            db.session.query(ConstrutorConferenciaHistorico)
            .filter_by(construcao_id=construcao_id)
            .order_by(ConstrutorConferenciaHistorico.data_execucao.desc())
            .first()
        )

    @classmethod
    def _serializar_conferencia(
        cls, conf: ConstrutorConferenciaHistorico, incluir_itens: bool = False, limite_itens: int = 50
    ) -> Dict[str, Any]:
        resumo = cls._normalizar_resumo(conf.resumo_dict())
        out = {
            "id": conf.id,
            "construcao_id": conf.construcao_id,
            "sessao_id": conf.sessao_id,
            "data_execucao": conf.data_execucao,
            "modo": conf.modo,
            "concurso_min": conf.concurso_min,
            "concurso_max": conf.concurso_max,
            "total_concursos": conf.total_concursos,
            "resumo": resumo,
            "acertos_tiers": list(cls._spec().acertos_tiers()),
        }
        if incluir_itens:
            itens = conf.itens
            if limite_itens and len(itens) > limite_itens:
                itens = itens[-limite_itens:]
            out["itens"] = [
                {
                    "concurso": it.concurso,
                    "data": it.data_sorteio,
                    "max_acertos": it.max_acertos,
                    "media_acertos": it.media_acertos,
                    "total_acertos": it.total_acertos,
                    "melhor_linha": it.melhor_linha,
                }
                for it in itens
            ]
            out["itens_truncados"] = len(conf.itens) > limite_itens
        return out

    @classmethod
    def executar_conferencia_historico(cls, construcao_id: int, incremental: bool = False) -> Dict[str, Any]:
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        if not construcao.apostas:
            return {"sucesso": False, "erro": "Construção sem apostas."}
        existente = cls._ultima_conferencia(construcao_id)
        novos_itens: List[Dict[str, Any]] = []
        if incremental and existente:
            conf = existente
            sorteios = (
                db.session.query(cls._model())
                .filter(cls._model().concurso > conf.concurso_max)
                .order_by(cls._model().concurso.asc())
                .all()
            )
            if not sorteios:
                return {
                    "sucesso": True,
                    "mensagem": "Conferência já está atualizada com o histórico disponível.",
                    "conferencia": cls._serializar_conferencia(conf),
                    "construcao_numero": construcao.numero,
                }
            novos_itens = cls._scores_construcao_sorteios(construcao, sorteios)
            for row in novos_itens:
                db.session.add(ConstrutorConferenciaHistoricoItem(
                    conferencia_id=conf.id,
                    concurso=row["concurso"],
                    data_sorteio=row["data"],
                    max_acertos=row["max_acertos"],
                    media_acertos=row["media_acertos"],
                    total_acertos=row["total_acertos"],
                    melhor_linha=row["melhor_linha"],
                ))
            todos = [
                {
                    "concurso": it.concurso,
                    "data": it.data_sorteio,
                    "max_acertos": it.max_acertos,
                    "media_acertos": it.media_acertos,
                    "total_acertos": it.total_acertos,
                    "melhor_linha": it.melhor_linha,
                }
                for it in conf.itens
            ] + novos_itens
            conf.concurso_max = max(i["concurso"] for i in todos)
            conf.total_concursos = len(todos)
            conf.modo = "incremental"
            conf.data_execucao = datetime.now().isoformat()
            conf.resumo_json = json.dumps(cls._resumo_conferencia_items(todos), ensure_ascii=False)
            db.session.commit()
            return {
                "sucesso": True,
                "mensagem": f"Atualizado com {len(novos_itens)} concurso(s) novo(s).",
                "conferencia": cls._serializar_conferencia(conf),
                "construcao_numero": construcao.numero,
                "novos_concursos": len(novos_itens),
            }
        if existente:
            db.session.delete(existente)
            db.session.flush()
        sorteios = db.session.query(cls._model()).order_by(cls._model().concurso.asc()).all()
        if not sorteios:
            return {"sucesso": False, "erro": "Nenhum sorteio no banco para conferir."}
        novos_itens = cls._scores_construcao_sorteios(construcao, sorteios)
        resumo = cls._resumo_conferencia_items(novos_itens)
        conf = ConstrutorConferenciaHistorico(
            construcao_id=construcao.id,
            sessao_id=construcao.sessao_id,
            modo="completo",
            concurso_min=sorteios[0].concurso,
            concurso_max=sorteios[-1].concurso,
            total_concursos=len(novos_itens),
            resumo_json=json.dumps(resumo, ensure_ascii=False),
        )
        db.session.add(conf)
        db.session.flush()
        for row in novos_itens:
            db.session.add(ConstrutorConferenciaHistoricoItem(
                conferencia_id=conf.id,
                concurso=row["concurso"],
                data_sorteio=row["data"],
                max_acertos=row["max_acertos"],
                media_acertos=row["media_acertos"],
                total_acertos=row["total_acertos"],
                melhor_linha=row["melhor_linha"],
            ))
        db.session.commit()
        return {
            "sucesso": True,
            "mensagem": f"Conferência salva — {len(novos_itens)} concursos analisados.",
            "conferencia": cls._serializar_conferencia(conf),
            "construcao_numero": construcao.numero,
            "novos_concursos": len(novos_itens),
        }

    @classmethod
    def executar_conferencia_sessao(cls, sessao_id: int, incremental: bool = False) -> Dict[str, Any]:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        if not sessao.construcoes:
            return {"sucesso": False, "erro": "Sessão sem construções."}
        resultados, erros = [], []
        for c in sessao.construcoes:
            r = cls.executar_conferencia_historico(c.id, incremental=incremental)
            if r.get("sucesso"):
                resultados.append({
                    "construcao_id": c.id,
                    "construcao_numero": c.numero,
                    "estrategia": c.estrategia,
                    "conferencia": r.get("conferencia"),
                    "mensagem": r.get("mensagem"),
                })
            else:
                erros.append({"construcao_numero": c.numero, "erro": r.get("erro")})
        analise = cls.analisar_comparativo_sessao(sessao_id)
        return {
            "sucesso": True,
            "processadas": len(resultados),
            "resultados": resultados,
            "erros": erros,
            "analise": analise.get("analise") if analise.get("sucesso") else None,
        }

    @classmethod
    def obter_conferencia_historico(cls, construcao_id: int, incluir_itens: bool = False) -> Dict[str, Any]:
        construcao = db.session.get(ConstrutorConstrucao, construcao_id)
        if not construcao:
            return {"sucesso": False, "erro": "Construção não encontrada."}
        conf = cls._ultima_conferencia(construcao_id)
        if not conf:
            return {"sucesso": True, "tem_conferencia": False, "construcao_numero": construcao.numero}
        return {
            "sucesso": True,
            "tem_conferencia": True,
            "construcao_numero": construcao.numero,
            "estrategia": construcao.estrategia,
            "conferencia": cls._serializar_conferencia(conf, incluir_itens=incluir_itens),
        }

    @classmethod
    def analisar_comparativo_sessao(cls, sessao_id: int) -> Dict[str, Any]:
        sessao = db.session.get(ConstrutorSessao, sessao_id)
        if not sessao:
            return {"sucesso": False, "erro": "Sessão não encontrada."}
        tiers = cls._spec().acertos_tiers()
        linhas, sem_conferencia = [], []
        for c in sessao.construcoes:
            conf = cls._ultima_conferencia(c.id)
            if not conf:
                sem_conferencia.append(c.numero)
                continue
            resumo = cls._normalizar_resumo(conf.resumo_dict())
            linhas.append({
                "construcao_id": c.id,
                "construcao_numero": c.numero,
                "estrategia": c.estrategia,
                "distribuicao": cls._distribuicao_dict(c),
                "data_execucao": conf.data_execucao,
                "total_concursos": conf.total_concursos,
                **resumo,
            })
        if not linhas:
            return {
                "sucesso": True,
                "analise": {
                    "tem_dados": False,
                    "sem_conferencia": sem_conferencia,
                    "mensagem": "Nenhuma construção conferida ainda. Use Conferir histórico.",
                    "acertos_tiers": list(tiers),
                },
            }

        def _pick(campo: str, reverse: bool = True):
            ordenada = sorted(
                linhas,
                key=lambda x: (x.get(campo, 0), -x.get("construcao_numero", 0)),
                reverse=reverse,
            )
            top = ordenada[0]
            return {
                "construcao_numero": top["construcao_numero"],
                "construcao_id": top["construcao_id"],
                "estrategia": top["estrategia"],
                "valor": top.get(campo),
            }

        por_estrategia: Dict[str, List[Dict[str, Any]]] = {}
        for ln in linhas:
            por_estrategia.setdefault(ln["estrategia"], []).append(ln)
        estrategia_stats = []
        for nome, grupo in por_estrategia.items():
            n = len(grupo)
            stat = {
                "estrategia": nome,
                "qtd_construcoes": n,
                "media_pontos": round(sum(g["total_pontos"] for g in grupo) / n, 1),
                "media_max_acertos": round(sum(g["media_max_acertos"] for g in grupo) / n, 2),
            }
            for t in tiers:
                stat[f"concursos_{t}"] = sum(g.get(f"concursos_{t}", 0) for g in grupo)
            stat[f"total_{tiers[0]}_a_{tiers[-1]}"] = sum(
                g.get(f"concursos_{tiers[0]}_a_{tiers[-1]}", 0) for g in grupo
            )
            estrategia_stats.append(stat)
        estrategia_stats.sort(key=lambda x: cls._chave_desempenho_acertos(x), reverse=True)
        ranking_acertos = sorted(linhas, key=lambda x: cls._chave_desempenho_acertos(x), reverse=True)
        melhor_acertos = ranking_acertos[0] if ranking_acertos else None
        melhor_acertos_info = None
        if melhor_acertos:
            melhor_acertos_info = {
                "construcao_numero": melhor_acertos["construcao_numero"],
                "construcao_id": melhor_acertos["construcao_id"],
                "estrategia": melhor_acertos["estrategia"],
            }
            for t in tiers:
                melhor_acertos_info[f"concursos_{t}"] = melhor_acertos.get(f"concursos_{t}", 0)
            melhor_acertos_info[f"total_{tiers[0]}_a_{tiers[-1]}"] = melhor_acertos.get(
                f"concursos_{tiers[0]}_a_{tiers[-1]}", 0
            )
        return {
            "sucesso": True,
            "analise": {
                "tem_dados": True,
                "conjunto_base": sessao.conjunto_lista(),
                "total_construcoes": len(sessao.construcoes),
                "conferidas": len(linhas),
                "sem_conferencia": sem_conferencia,
                "acertos_tiers": list(tiers),
                "perguntas": {
                    "mais_pontos": _pick("total_pontos"),
                    "melhor_acertos": melhor_acertos_info,
                    "maior_media": _pick("media_max_acertos"),
                    "melhor_estrategia": estrategia_stats[0] if estrategia_stats else None,
                },
                "ranking_pontos": sorted(linhas, key=lambda x: (-x["total_pontos"], -x["media_max_acertos"])),
                "ranking_acertos": ranking_acertos,
                "ranking_media": sorted(linhas, key=lambda x: (-x["media_max_acertos"], -x["total_pontos"])),
                "estrategias": estrategia_stats,
            },
        }

    @classmethod
    def panorama_conferencias(cls) -> Dict[str, Any]:
        tiers = cls._spec().acertos_tiers()
        linhas: List[Dict[str, Any]] = []
        construcoes = (
            db.session.query(ConstrutorConstrucao)
            .join(ConstrutorSessao)
            .order_by(ConstrutorSessao.id.desc(), ConstrutorConstrucao.numero.asc())
            .all()
        )
        for c in construcoes:
            conf = cls._ultima_conferencia(c.id)
            if not conf:
                continue
            sessao = c.sessao
            resumo = cls._normalizar_resumo(conf.resumo_dict())
            linhas.append({
                "sessao_id": sessao.id,
                "sessao_nome": sessao.nome,
                "conjunto_base_qtd": len(sessao.conjunto_lista()),
                "construcao_id": c.id,
                "construcao_numero": c.numero,
                "estrategia": c.estrategia,
                "data_execucao": conf.data_execucao,
                "total_concursos": conf.total_concursos,
                **resumo,
            })
        linhas.sort(key=lambda x: cls._chave_desempenho_acertos(x), reverse=True)
        por_estrategia: Dict[str, List[Dict[str, Any]]] = {}
        for ln in linhas:
            por_estrategia.setdefault(ln["estrategia"], []).append(ln)
        estrategia_stats = []
        for nome, grupo in por_estrategia.items():
            n = len(grupo)
            stat = {
                "estrategia": nome,
                "qtd_construcoes": n,
                "qtd_sessoes": len({g["sessao_id"] for g in grupo}),
                "total_pontos": sum(g["total_pontos"] for g in grupo),
                "media_max_acertos": round(sum(g["media_max_acertos"] for g in grupo) / n, 2),
            }
            for t in tiers:
                stat[f"concursos_{t}"] = sum(g.get(f"concursos_{t}", 0) for g in grupo)
            stat[f"total_{tiers[0]}_a_{tiers[-1]}"] = sum(
                g.get(f"concursos_{tiers[0]}_a_{tiers[-1]}", 0) for g in grupo
            )
            estrategia_stats.append(stat)
        estrategia_stats.sort(key=lambda x: cls._chave_desempenho_acertos(x), reverse=True)
        return {
            "sucesso": True,
            "total": len(linhas),
            "ranking": linhas,
            "melhor_estrategia": estrategia_stats[0] if estrategia_stats else None,
            "estrategias": estrategia_stats,
            "acertos_tiers": list(tiers),
        }

    @classmethod
    def _distribuicao_dict(cls, c: ConstrutorConstrucao) -> Dict[str, int]:
        parts = (c.distribuicao or "0,0,0").split(",")
        return {
            "baixas": int(parts[0]) if len(parts) > 0 else 0,
            "medias": int(parts[1]) if len(parts) > 1 else 0,
            "altas": int(parts[2]) if len(parts) > 2 else 0,
        }

    @classmethod
    def _serializar_construcao(cls, c: ConstrutorConstrucao) -> Dict[str, Any]:
        sp = cls._spec()
        dist = cls._distribuicao_dict(c)
        conf = cls._ultima_conferencia(c.id)
        conf_resumo = None
        if conf:
            conf_resumo = {
                "data_execucao": conf.data_execucao,
                "total_concursos": conf.total_concursos,
                **cls._normalizar_resumo(conf.resumo_dict()),
            }
        out = {
            "id": c.id,
            "numero": c.numero,
            "estrategia": c.estrategia,
            "estrategia_params": c.params_dict(),
            "distribuicao": dist,
            "similaridade_anterior": c.similaridade_anterior,
            "diferenca_pct": c.diferenca_pct,
            "data_criacao": c.data_criacao,
            "conferencia_historico": conf_resumo,
            "apostas": [{"linha": a.linha, "dezenas": a.dezenas_lista()} for a in c.apostas],
        }
        if sp.has_mes and c.mes_num:
            out["mes_num"] = c.mes_num
            out["mes_abrev"] = MESES_ABREV.get(c.mes_num, "")
        if sp.has_time and c.mes_num:
            out["time_num"] = c.mes_num
            out["time_label"] = cls._time_label(c.mes_num)
        if sp.has_trevos:
            out["trevos"] = c.extra_dict().get("trevos", [])
        return out

    @classmethod
    def _serializar_sessao(cls, s: ConstrutorSessao, incluir_construcoes: bool) -> Dict[str, Any]:
        limites = cls._faixa_limites()
        out = {
            "id": s.id,
            "nome": s.nome,
            "data_criacao": s.data_criacao,
            "conjunto_base": s.conjunto_lista(),
            "dezenas_por_aposta": s.dezenas_por_aposta,
            "origem_conjunto": s.origem_conjunto,
            "tipo_universo": getattr(s, "tipo_universo", None) or "dezenas",
            "total_construcoes": len(s.construcoes),
            "pool_faixas": pool_por_faixa(s.conjunto_lista(), limites),
        }
        if incluir_construcoes:
            out["construcoes"] = [cls._serializar_construcao(c) for c in s.construcoes]
        return out
