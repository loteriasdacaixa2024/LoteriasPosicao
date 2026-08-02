# -*- coding: utf-8 -*-
"""Serviço — Pool de Dígitos + Gerador Inteligente (Dia de Sorte e Spec)."""
from __future__ import annotations

import json
import random
from datetime import datetime
from itertools import combinations
from typing import Any, Dict, List, Optional

from geradores_elite.construtor.construcoes_core import QTD_APOSTAS_FIXA
from geradores_elite.construtor.models import ConstrutorAposta, ConstrutorConstrucao, ConstrutorSessao
from geradores_elite.construtor.universes import (
    POOL_MIN_RECOMENDADO,
    dezena_compativel,
    digitos_da_dezena,
    diagnosticar_filtros_digitos,
    expandir_elegiveis,
    normalizar_pool_digitos,
    resumo_pool,
)
from geradores_elite.engine_final_core import formatar_export_txt
from geradores_elite.modality_config import MESES_ABREV
from models.shared import db

TIPO_DIGITOS = "digitos"
TIPO_DEZENAS = "dezenas"

# Limite de segurança para enumerar/exportar TODAS as combinações
MAX_COMBOS_LISTAR = 2000
MAX_COMBOS_EXPORTAR = 5000



class ConstrutorDigitosService:
    """
    Pool de dígitos / Gerador Inteligente — independentes do fluxo de dezenas.
    Estatísticas: Análise Dígitos com janela=0 (todos os sorteios).
    """

    @classmethod
    def _base_svc(cls, modality_key: str):
        from geradores_elite.construtor import get_construtor_service
        svc = get_construtor_service(modality_key)
        if not svc:
            raise ValueError(f"Construtor indisponível: {modality_key}")
        return svc

    @classmethod
    def _spec(cls, modality_key: str):
        return cls._base_svc(modality_key)._spec()

    @classmethod
    def _analise_digitos(cls, modality_key: str) -> Dict[str, Any]:
        try:
            from analise_somas_digitos.service import AnaliseSomasDigitosService
            return AnaliseSomasDigitosService.analisar_digitos(
                modality_key, janela=0, base_estatistica="geral",
            )
        except Exception as exc:
            return {
                "sucesso": False,
                "erro": str(exc),
                "painel_digitos": [],
                "resumo": {},
                "resumo_por_quantidade": [],
            }

    @classmethod
    def _scores_dezenas(
        cls,
        modality_key: str,
        elegiveis: List[int],
        modo: str = "frequencia",
        pad_width: int = 2,
    ) -> Dict[int, float]:
        guia = cls._analise_digitos(modality_key)
        painel = {str(p["digito"]): p for p in (guia.get("painel_digitos") or [])}
        scores: Dict[int, float] = {}
        for n in elegiveis:
            digs = digitos_da_dezena(n, pad_width)
            if modo == "atraso":
                # menor presença → maior score
                vals = [100.0 - float(painel.get(str(d), {}).get("pct", 0) or 0) for d in digs]
            else:
                vals = [float(painel.get(str(d), {}).get("pct", 0) or 0) for d in digs]
            base = (sum(vals) / max(len(vals), 1)) if vals else 1.0
            scores[n] = base + random.random() * 0.01
        return scores

    @classmethod
    def guia(cls, modality_key: str) -> Dict[str, Any]:
        """Guia histórico completo para pool de dígitos e gerador inteligente."""
        sp = cls._spec(modality_key)
        dig = cls._analise_digitos(modality_key)
        if not dig.get("sucesso"):
            return dig
        resumo = dig.get("resumo") or {}
        return {
            "sucesso": True,
            "total_concursos": dig.get("total_concursos"),
            "ultimo_concurso": dig.get("ultimo_concurso"),
            "janela": 0,
            "base_estatistica": "geral",
            "min_pool_recomendado": POOL_MIN_RECOMENDADO,
            "qtd_recomendada": resumo.get("qtd_recomendada"),
            "qtd_recomendada_pct": resumo.get("qtd_recomendada_pct"),
            "media_qtd": resumo.get("media_qtd"),
            "digito_mais_frequente": resumo.get("digito_mais_frequente"),
            "digito_menos_frequente": resumo.get("digito_menos_frequente"),
            "digitos_ausentes_ultimo": resumo.get("digitos_ausentes_ultimo") or [],
            "resumo_por_quantidade": dig.get("resumo_por_quantidade") or [],
            "painel_digitos": dig.get("painel_digitos") or [],
            "universo": {
                "dezena_min": sp.dezena_min,
                "dezena_max": sp.universo,
                "pick_min": sp.pick_min,
                "pick_max": sp.pick_max,
                "pick_default": sp.pick_default,
                "pad_width": sp.dezena_fmt_width,
            },
            "link_analise": "/analise/somas-digitos/",
            "nota": "Estatísticas de todos os sorteios (janela completa).",
        }

    @classmethod
    def sugerir_pool(cls, modality_key: str, criterio: str = "frequencia", quantidade: int = 4) -> Dict[str, Any]:
        guia = cls.guia(modality_key)
        if not guia.get("sucesso"):
            return guia
        qtd = max(1, min(10, int(quantidade)))
        painel = list(guia.get("painel_digitos") or [])
        if criterio == "atraso":
            # menos frequentes ≈ mais “frios” no painel ordenado por presença
            ordenados = sorted(painel, key=lambda x: (x.get("concursos", 0), int(x["digito"])))
        elif criterio == "pares":
            ordenados = [{"digito": str(d)} for d in (0, 2, 4, 6, 8)]
        elif criterio == "impares":
            ordenados = [{"digito": str(d)} for d in (1, 3, 5, 7, 9)]
        else:
            ordenados = sorted(
                painel,
                key=lambda x: (-x.get("concursos", 0), int(x["digito"])),
            )
        pool = [int(p["digito"]) for p in ordenados[:qtd]]
        return {
            "sucesso": True,
            "pool": sorted(set(pool)),
            "origem": f"analise_{criterio}",
            "criterio": criterio,
            **cls.avaliar_pool(modality_key, pool, guia["universo"]["pick_default"]),
        }

    @classmethod
    def avaliar_pool(
        cls,
        modality_key: str,
        pool: List[int],
        dezenas_por_aposta: Optional[int] = None,
    ) -> Dict[str, Any]:
        sp = cls._spec(modality_key)
        k = dezenas_por_aposta if dezenas_por_aposta is not None else sp.pick_default
        k = max(sp.pick_min, min(int(k), sp.pick_max))
        res = resumo_pool(pool, sp.dezena_min, sp.universo, k, sp.dezena_fmt_width)
        return {"sucesso": True, **res}

    @classmethod
    def diagnosticar(
        cls,
        modality_key: str,
        pool: List[int],
        *,
        dezenas_por_aposta: Optional[int] = None,
        exigir_qtd_digitos: Optional[int] = None,
        qtd_apostas: int = 1,
    ) -> Dict[str, Any]:
        """Validação preventiva de filtros — mesma lógica usada em gerar_inteligente."""
        if modality_key == "supersete":
            pool_n = sorted(set(int(d) for d in pool if 0 <= int(d) <= 9))
            exigir = int(exigir_qtd_digitos) if exigir_qtd_digitos is not None else None
            conflitos = []
            if not pool_n:
                conflitos.append({
                    "codigo": "pool_vazio",
                    "mensagem": "Informe ao menos 1 dígito (0–9).",
                    "filtros": ["pool"],
                    "sugestoes": ["Selecione dígitos no pool."],
                })
            if exigir is not None and (exigir < 1 or exigir > 7):
                conflitos.append({
                    "codigo": "exigir_fora_faixa",
                    "mensagem": "Qtd de dígitos distintos deve ser 1–7 no Super Sete.",
                    "filtros": ["exigir_qtd_digitos"],
                    "sugestoes": ["Use um valor entre 1 e 7."],
                })
            if exigir is not None and pool_n and exigir > len(pool_n):
                conflitos.append({
                    "codigo": "exigir_maior_que_pool",
                    "mensagem": (
                        f"Impossível exigir {exigir} distintos com pool de {len(pool_n)}."
                    ),
                    "filtros": ["pool", "exigir_qtd_digitos"],
                    "sugestoes": ["Amplie o pool ou reduza a exigência."],
                })
            ok = not conflitos
            msg = conflitos[0]["mensagem"] if conflitos else (
                "Super Sete posicional: 7 colunas, repetição livre entre colunas."
            )
            return {
                "sucesso": True,
                "ok": ok,
                "mensagem": msg,
                "conflitos": conflitos,
                "avaliacao": {
                    "pool": pool_n,
                    "qtd_pool": len(pool_n),
                    "elegiveis": pool_n,
                    "qtd_elegiveis": len(pool_n),
                    "colunas": 7,
                    "dezenas_por_aposta": 7,
                    "modo": "posicional_supersete",
                    "repeticao_livre": True,
                    "pode_gerar": bool(pool_n) and ok,
                    "combinacoes_possiveis": (len(pool_n) ** 7) if pool_n else 0,
                },
            }
        sp = cls._spec(modality_key)
        k = dezenas_por_aposta if dezenas_por_aposta is not None else sp.pick_default
        k = max(sp.pick_min, min(int(k), sp.pick_max))
        diag = diagnosticar_filtros_digitos(
            pool,
            sp.dezena_min,
            sp.universo,
            k,
            sp.dezena_fmt_width,
            exigir_qtd_digitos=exigir_qtd_digitos,
            qtd_apostas=qtd_apostas,
        )
        return {"sucesso": True, **diag}

    @classmethod
    def salvar_sessao_digitos(
        cls,
        modality_key: str,
        nome: str,
        pool: List[int],
        dezenas_por_aposta: int,
        origem_conjunto: str = "manual",
        sessao_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        sp = cls._spec(modality_key)
        pool_n = normalizar_pool_digitos(pool)
        if not pool_n:
            return {"sucesso": False, "erro": "Selecione ao menos 1 dígito no pool."}
        k = max(sp.pick_min, min(int(dezenas_por_aposta), sp.pick_max))
        aval = resumo_pool(pool_n, sp.dezena_min, sp.universo, k, sp.dezena_fmt_width)
        conj_str = ",".join(str(d) for d in pool_n)
        if sessao_id:
            sessao = db.session.get(ConstrutorSessao, sessao_id)
            if not sessao:
                return {"sucesso": False, "erro": "Sessão não encontrada."}
            if (getattr(sessao, "tipo_universo", None) or TIPO_DEZENAS) != TIPO_DIGITOS:
                return {"sucesso": False, "erro": "Sessão não é do tipo dígitos."}
            sessao.nome = nome.strip() or sessao.nome
            sessao.conjunto_base = conj_str
            sessao.dezenas_por_aposta = k
            sessao.origem_conjunto = origem_conjunto
            sessao.tipo_universo = TIPO_DIGITOS
        else:
            sessao = ConstrutorSessao(
                nome=nome.strip() or f"Pool dígitos {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                conjunto_base=conj_str,
                dezenas_por_aposta=k,
                origem_conjunto=origem_conjunto,
                tipo_universo=TIPO_DIGITOS,
            )
            db.session.add(sessao)
        db.session.commit()
        base = cls._base_svc(modality_key)
        out = base._serializar_sessao(sessao, incluir_construcoes=True)
        out["tipo_universo"] = TIPO_DIGITOS
        out["avaliacao"] = aval
        return {"sucesso": True, "sessao": out, "avaliacao": aval}

    @classmethod
    def listar_sessoes_digitos(cls, modality_key: str) -> List[Dict[str, Any]]:
        base = cls._base_svc(modality_key)
        rows = (
            db.session.query(ConstrutorSessao)
            .filter(ConstrutorSessao.tipo_universo == TIPO_DIGITOS)
            .order_by(ConstrutorSessao.id.desc())
            .all()
        )
        out = []
        for s in rows:
            data = base._serializar_sessao(s, incluir_construcoes=False)
            data["tipo_universo"] = TIPO_DIGITOS
            out.append(data)
        return out

    @classmethod
    def _gerar_supersete_posicional(
        cls,
        pool: List[int],
        *,
        qtd: int,
        modo: str,
        exigir: Optional[int],
    ) -> Dict[str, Any]:
        """
        Super Sete: 7 colunas independentes.
        O pool de dígitos 0–9 define candidatos válidos em TODAS as colunas.
        Repetições entre colunas são livres (regra Caixa).
        """
        pool_n = sorted(set(int(d) for d in pool if 0 <= int(d) <= 9))
        if not pool_n:
            return {"sucesso": False, "erro": "Informe um pool de dígitos (0–9)."}
        if exigir is not None:
            exigir = int(exigir)
            if exigir < 1 or exigir > 7:
                return {
                    "sucesso": False,
                    "erro": "No Super Sete, a qtd de dígitos distintos deve ser entre 1 e 7.",
                }
            if exigir > len(pool_n):
                return {
                    "sucesso": False,
                    "erro": (
                        f"Impossível exigir {exigir} dígitos distintos com pool de "
                        f"{len(pool_n)} dígito(s)."
                    ),
                }

        scores = cls._scores_dezenas("supersete", pool_n, modo=modo, pad_width=1)
        rng = random.Random()
        apostas: List[List[int]] = []
        vistos = set()
        tentativas = 0
        max_tent = max(2000, qtd * 200)

        # Preferência ponderada pelos scores (frequência/atraso).
        pesos = [max(0.05, float(scores.get(d, 0.05))) for d in pool_n]

        while len(apostas) < qtd and tentativas < max_tent:
            tentativas += 1
            if tentativas % 11 == 0:
                ap = [rng.choice(pool_n) for _ in range(7)]
            else:
                ap = []
                for _ in range(7):
                    # choice ponderado sem numpy
                    total = sum(pesos)
                    r = rng.random() * total
                    acc = 0.0
                    escolhido = pool_n[-1]
                    for d, w in zip(pool_n, pesos):
                        acc += w
                        if r <= acc:
                            escolhido = d
                            break
                    ap.append(escolhido)
            if exigir is not None and len(set(ap)) != exigir:
                continue
            chave = tuple(ap)
            if chave in vistos:
                continue
            vistos.add(chave)
            apostas.append(ap)

        if not apostas:
            return {
                "sucesso": False,
                "erro": (
                    "Não foi possível montar apostas Super Sete com os filtros atuais. "
                    "Amplie o pool ou ajuste a qtd de dígitos distintos (1–7)."
                ),
                "avaliacao": {
                    "pool": pool_n,
                    "elegiveis": pool_n,
                    "colunas": 7,
                    "modo": "posicional_supersete",
                    "combinacoes_possiveis": len(pool_n) ** 7,
                },
            }

        apostas.sort(
            key=lambda a: (
                -sum(scores.get(d, 0.0) for d in a) / 7.0,
                -len(set(a)),
                a,
            )
        )
        return {
            "sucesso": True,
            "apostas": [
                {"numero": i, "dezenas": ap, "extras": {}}
                for i, ap in enumerate(apostas[:qtd], start=1)
            ],
            "quantidade": min(qtd, len(apostas)),
            "avaliacao": {
                "pool": pool_n,
                "elegiveis": pool_n,
                "colunas": 7,
                "modo": "posicional_supersete",
                "repeticao_livre": True,
                "combinacoes_possiveis": len(pool_n) ** 7,
                "tentativas": tentativas,
            },
            "aviso": (
                "Super Sete: cada aposta tem 7 colunas; o mesmo dígito pode "
                "aparecer em várias colunas (regra oficial Caixa)."
            ),
        }

    @classmethod
    def gerar_inteligente(
        cls,
        modality_key: str,
        pool: List[int],
        *,
        dezenas_por_aposta: Optional[int] = None,
        qtd_apostas: int = QTD_APOSTAS_FIXA,
        modo: str = "frequencia",
        exigir_qtd_digitos: Optional[int] = None,
        salvar_sessao: bool = False,
        nome_sessao: str = "",
        sessao_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gerador Inteligente — gera apostas a partir do pool em memória (não exige sessão do Construtor).
        Opcionalmente persiste sessão digitos + construção.
        """
        if modality_key == "supersete":
            qtd_req = max(1, min(int(qtd_apostas), QTD_APOSTAS_FIXA * 2))
            exigir = int(exigir_qtd_digitos) if exigir_qtd_digitos is not None else None
            gen = cls._gerar_supersete_posicional(
                pool, qtd=qtd_req, modo=modo, exigir=exigir,
            )
            if not gen.get("sucesso"):
                return gen
            apostas_list = [a["dezenas"] for a in gen["apostas"]]
            pool_n = sorted(set(int(d) for d in pool if 0 <= int(d) <= 9))
            result = {
                "sucesso": True,
                "apostas": gen["apostas"],
                "quantidade": gen["quantidade"],
                "avaliacao": gen.get("avaliacao"),
                "aviso": gen.get("aviso"),
            }
            if salvar_sessao or sessao_id:
                saved = cls.salvar_sessao_digitos(
                    modality_key,
                    nome_sessao or f"Inteligente SS {datetime.now().strftime('%d/%m %H:%M')}",
                    pool_n,
                    7,
                    origem_conjunto=f"inteligente_ss_{modo}",
                    sessao_id=sessao_id,
                )
                if not saved.get("sucesso"):
                    result["aviso_persistencia"] = saved.get("erro")
                    return result
                try:
                    sessao = db.session.get(ConstrutorSessao, saved["sessao"]["id"])
                    numero = len(sessao.construcoes) + 1
                    construcao = ConstrutorConstrucao(
                        sessao_id=sessao.id,
                        numero=numero,
                        estrategia="digitos_inteligente_ss",
                        estrategia_params=json.dumps({
                            "modo": modo,
                            "exigir_qtd_digitos": exigir,
                            "pool": pool_n,
                            "posicional_supersete": True,
                        }, ensure_ascii=False),
                        distribuicao="",
                    )
                    db.session.add(construcao)
                    db.session.flush()
                    for i, ap in enumerate(apostas_list, start=1):
                        db.session.add(ConstrutorAposta(
                            construcao_id=construcao.id,
                            linha=i,
                            dezenas=",".join(str(d) for d in ap),
                        ))
                    db.session.commit()
                    base = cls._base_svc(modality_key)
                    result["sessao"] = base._serializar_sessao(sessao, incluir_construcoes=True)
                    result["construcao"] = base._serializar_construcao(construcao)
                except Exception as exc:
                    db.session.rollback()
                    result["aviso_persistencia"] = str(exc)
            return result

        sp = cls._spec(modality_key)
        pool_n = normalizar_pool_digitos(pool)
        if not pool_n:
            return {"sucesso": False, "erro": "Informe um pool de dígitos."}
        k = dezenas_por_aposta if dezenas_por_aposta is not None else sp.pick_default
        k = max(sp.pick_min, min(int(k), sp.pick_max))
        qtd_req = max(1, min(int(qtd_apostas), QTD_APOSTAS_FIXA * 2))

        diag = diagnosticar_filtros_digitos(
            pool_n,
            sp.dezena_min,
            sp.universo,
            k,
            sp.dezena_fmt_width,
            exigir_qtd_digitos=exigir_qtd_digitos,
            qtd_apostas=qtd_req,
        )
        aval = diag["avaliacao"]
        if not diag["ok"]:
            return {
                "sucesso": False,
                "erro": diag["mensagem"],
                "avaliacao": aval,
                "diagnostico": diag,
            }

        elegiveis = aval["elegiveis"]
        scores = cls._scores_dezenas(
            modality_key, elegiveis, modo=modo, pad_width=sp.dezena_fmt_width
        )
        qtd = max(1, min(qtd_req, aval["combinacoes_possiveis"]))
        apostas: List[List[int]] = []
        vistos = set()
        tentativas = 0
        max_tent = max(500, qtd * 80)
        pad_w = sp.dezena_fmt_width
        exigir = int(exigir_qtd_digitos) if exigir_qtd_digitos is not None else None

        # Caminho determinístico: evita falso negativo quando o espaço cabe em memória.
        # Enumera C(n,k) e filtra por exigir_qtd_digitos (se houver).
        MAX_ENUM_GERAR = 5000
        if aval["combinacoes_possiveis"] <= MAX_ENUM_GERAR:
            candidatas: List[List[int]] = []
            for combo in combinations(elegiveis, k):
                pick = sorted(combo)
                if exigir is not None:
                    digs: set = set()
                    for n in pick:
                        digs.update(digitos_da_dezena(n, pad_w))
                    if len(digs) != exigir:
                        continue
                candidatas.append(pick)
            candidatas.sort(
                key=lambda ap: (-sum(scores.get(n, 0.0) for n in ap) / max(len(ap), 1), ap)
            )
            if exigir is not None and not candidatas:
                # Diagnóstico já deveria ter barrado; reforço defensivo.
                diag2 = diagnosticar_filtros_digitos(
                    pool_n, sp.dezena_min, sp.universo, k, pad_w,
                    exigir_qtd_digitos=exigir, qtd_apostas=qtd_req,
                )
                return {
                    "sucesso": False,
                    "erro": diag2["mensagem"],
                    "avaliacao": aval,
                    "diagnostico": diag2,
                }
            apostas = candidatas[:qtd]
            tentativas = len(candidatas)
        else:
            while len(apostas) < qtd and tentativas < max_tent:
                tentativas += 1
                ranked = sorted(elegiveis, key=lambda n: -scores[n])
                if tentativas % 7 == 0:
                    random.shuffle(ranked)
                pick: List[int] = []
                restantes = list(ranked)
                while len(pick) < k and restantes:
                    top = restantes[: max(8, len(restantes) // 2)]
                    pesos = [max(0.05, scores[n]) for n in top]
                    total = sum(pesos)
                    r = random.random() * total
                    acc = 0.0
                    escolhido = top[0]
                    for n, w in zip(top, pesos):
                        acc += w
                        if r <= acc:
                            escolhido = n
                            break
                    pick.append(escolhido)
                    restantes = [x for x in restantes if x != escolhido]

                if len(pick) != k:
                    continue
                pick = sorted(pick)
                if not all(dezena_compativel(n, pool_n, pad_w) for n in pick):
                    continue
                if exigir is not None:
                    digs = set()
                    for n in pick:
                        digs.update(digitos_da_dezena(n, pad_w))
                    if len(digs) != exigir:
                        continue
                chave = tuple(pick)
                if chave in vistos:
                    continue
                vistos.add(chave)
                apostas.append(pick)

        if len(apostas) < 1:
            if exigir is not None:
                msg = (
                    f"Nenhuma aposta encontrada com exatamente {exigir} dígito(s) "
                    f"distinto(s) após {tentativas} tentativa(s). "
                    "O filtro «Exigir qtd dígitos» eliminou os candidatos gerados."
                )
                hints = [
                    "Desmarque «Exigir qtd dígitos» ou escolha um valor compatível com o pool.",
                    "Amplie o pool de dígitos (0–9).",
                    "Reduza a quantidade de apostas pedida.",
                ]
                filtros = ["exigir_qtd_digitos", "pool"]
            else:
                msg = (
                    f"Zero apostas montadas após {tentativas} tentativa(s) "
                    f"com pool [{aval.get('pool_fmt')}] e {k} dezena(s)/aposta. "
                    "Restrições do pool de dígitos resultaram em candidatos insuficientes."
                )
                hints = [
                    "Amplie o pool de dígitos (selecione mais valores de 0 a 9).",
                    "Altere o modo (Frequência / Atraso).",
                    "Reduza a quantidade de apostas.",
                ]
                filtros = ["pool", "modo", "qtd_apostas"]
            diag_fail = {
                "ok": False,
                "avaliacao": aval,
                "conflitos": [{
                    "codigo": "busca_esgotada",
                    "mensagem": msg,
                    "filtros": filtros,
                    "sugestoes": hints,
                }],
                "sugestoes": hints,
                "mensagem": msg,
                "filtros_em_conflito": filtros,
                "tentativas": tentativas,
            }
            return {
                "sucesso": False,
                "erro": msg,
                "avaliacao": aval,
                "diagnostico": diag_fail,
            }

        guia = cls.guia(modality_key)
        result: Dict[str, Any] = {
            "sucesso": True,
            "pool": pool_n,
            "avaliacao": aval,
            "modo": modo,
            "apostas": [
                {"linha": i + 1, "dezenas": ap}
                for i, ap in enumerate(apostas)
            ],
            "qtd_geradas": len(apostas),
            "insights": {
                "qtd_recomendada": guia.get("qtd_recomendada"),
                "digito_mais_frequente": guia.get("digito_mais_frequente"),
                "abaixo_recomendado": aval.get("abaixo_recomendado"),
            },
        }
        try:
            from geradores_elite.validacao.validador_global import ValidadorGeradoresElite
            result = ValidadorGeradoresElite.aplicar(
                result,
                origem="construtor_digitos",
                modality_key=modality_key,
                campo="apostas",
            )
            result["qtd_geradas"] = len(result.get("apostas") or [])
            if result["qtd_geradas"] == 0:
                return {
                    "sucesso": False,
                    "erro": (
                        "Todas as apostas montadas foram rejeitadas pela validação global "
                        "da modalidade. Relaxe o pool ou desative restrições adicionais."
                    ),
                    "avaliacao": aval,
                    "diagnostico": {
                        "ok": False,
                        "avaliacao": aval,
                        "conflitos": [{
                            "codigo": "validacao_global",
                            "mensagem": (
                                "Validação global eliminou 100% das apostas geradas."
                            ),
                            "filtros": ["validacao_global", "pool"],
                            "sugestoes": [
                                "Altere o pool de dígitos.",
                                "Desmarque «Exigir qtd dígitos».",
                                "Tente outro modo (Frequência / Atraso).",
                            ],
                        }],
                        "sugestoes": [
                            "Altere o pool de dígitos.",
                            "Desmarque «Exigir qtd dígitos».",
                            "Tente outro modo (Frequência / Atraso).",
                        ],
                        "mensagem": "Validação global eliminou 100% das apostas geradas.",
                        "filtros_em_conflito": ["validacao_global", "pool"],
                    },
                    "validacao_global": result.get("validacao_global"),
                }
        except Exception:
            pass

        if salvar_sessao or sessao_id:
            saved = cls.salvar_sessao_digitos(
                modality_key,
                nome_sessao or f"Inteligente {datetime.now().strftime('%d/%m %H:%M')}",
                pool_n,
                k,
                origem_conjunto=f"inteligente_{modo}",
                sessao_id=sessao_id,
            )
            if not saved.get("sucesso"):
                result["aviso_persistencia"] = saved.get("erro")
                return result
            sessao = db.session.get(ConstrutorSessao, saved["sessao"]["id"])
            numero = len(sessao.construcoes) + 1
            params = {
                "modo": modo,
                "exigir_qtd_digitos": exigir_qtd_digitos,
                "pool": pool_n,
            }
            construcao = ConstrutorConstrucao(
                sessao_id=sessao.id,
                numero=numero,
                estrategia="digitos_inteligente",
                estrategia_params=json.dumps(params, ensure_ascii=False),
                distribuicao="",
            )
            db.session.add(construcao)
            db.session.flush()
            fmt = cls._base_svc(modality_key)._fmt_dezena
            for i, ap in enumerate(apostas, start=1):
                db.session.add(ConstrutorAposta(
                    construcao_id=construcao.id,
                    linha=i,
                    dezenas=",".join(fmt(d) for d in ap),
                ))
            db.session.commit()
            base = cls._base_svc(modality_key)
            result["sessao"] = base._serializar_sessao(sessao, incluir_construcoes=True)
            result["construcao"] = base._serializar_construcao(construcao)

        return result

    @classmethod
    def listar_combinacoes(
        cls,
        modality_key: str,
        pool: List[int],
        dezenas_por_aposta: Optional[int] = None,
        *,
        incluir_apostas: bool = True,
        limite: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Lista dezenas elegíveis + todas as apostas C(n,k) quando couber no limite.
        Híbrido: sempre devolve contagem; apostas só se total <= limite.
        """
        sp = cls._spec(modality_key)
        pool_n = normalizar_pool_digitos(pool)
        k = dezenas_por_aposta if dezenas_por_aposta is not None else sp.pick_default
        k = max(sp.pick_min, min(int(k), sp.pick_max))
        aval = resumo_pool(pool_n, sp.dezena_min, sp.universo, k, sp.dezena_fmt_width)
        lim = int(limite) if limite is not None else MAX_COMBOS_LISTAR
        lim = max(1, min(lim, MAX_COMBOS_EXPORTAR))
        total = aval["combinacoes_possiveis"]
        out: Dict[str, Any] = {
            "sucesso": True,
            "avaliacao": aval,
            "total_combinacoes": total,
            "limite_listagem": lim,
            "limite_exportacao": MAX_COMBOS_EXPORTAR,
            "pode_listar_todas": total > 0 and total <= lim,
            "pode_exportar_todas": total > 0 and total <= MAX_COMBOS_EXPORTAR,
            "elegiveis": aval["elegiveis"],
            "apostas": [],
            "truncado": False,
        }
        if not incluir_apostas or total <= 0:
            return out
        if total > lim:
            out["truncado"] = True
            out["aviso"] = (
                f"Há {total:,} combinações — acima do limite de listagem ({lim:,}). "
                f"Exporte o lote gerado no Gerador Inteligente ou reduza o pool / tamanho da aposta. "
                f"Exportação de todas liberada até {MAX_COMBOS_EXPORTAR:,}."
            ).replace(",", ".")
            return out

        apostas = [
            {"linha": i, "dezenas": list(combo)}
            for i, combo in enumerate(combinations(aval["elegiveis"], k), start=1)
        ]
        out["apostas"] = apostas
        out["qtd_listadas"] = len(apostas)
        return out

    @classmethod
    def exportar_txt(
        cls,
        modality_key: str,
        *,
        modo: str = "lote",
        pool: Optional[List[int]] = None,
        dezenas_por_aposta: Optional[int] = None,
        apostas: Optional[List[Any]] = None,
        mes_num: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        modo=lote  → usa lista `apostas` já gerada
        modo=todas → enumera C(n,k) do pool (até MAX_COMBOS_EXPORTAR)
        modo=elegiveis → uma linha com todas as dezenas elegíveis (matéria-prima)
        """
        sp = cls._spec(modality_key)
        modo = (modo or "lote").strip().lower()
        export_extra: Dict[str, Any] = {}
        usar_aleatorio = False
        if sp.has_mes and mes_num is not None and mes_num != "":
            from diadesorte.mes_sorte_select import eh_criterio_aleatorio, resolver_mes_sorte
            if eh_criterio_aleatorio(mes_num):
                usar_aleatorio = True
            else:
                mn = resolver_mes_sorte(mes_num) if not isinstance(mes_num, int) else int(mes_num)
                if mn is not None:
                    export_extra = {
                        "tipo": "mes",
                        "num": int(mn),
                        "label": MESES_ABREV.get(int(mn), str(mn)),
                    }

        linhas_apostas: List[Dict[str, Any]] = []
        sufixo = "lote"
        pool_n = normalizar_pool_digitos(pool or [])

        if modo == "elegiveis":
            if not pool_n:
                return {"sucesso": False, "erro": "Informe o pool de dígitos."}
            k = dezenas_por_aposta if dezenas_por_aposta is not None else sp.pick_default
            k = max(sp.pick_min, min(int(k), sp.pick_max))
            aval = resumo_pool(pool_n, sp.dezena_min, sp.universo, k, sp.dezena_fmt_width)
            if not aval["elegiveis"]:
                return {"sucesso": False, "erro": "Nenhuma dezena elegível para este pool."}
            # Uma linha com o universo elegível (referência) + comentário no nome
            fmt = cls._base_svc(modality_key)._fmt_dezena
            texto_ref = " ".join(fmt(d) for d in aval["elegiveis"])
            cab = (
                f"# Pool digitos: {','.join(str(d) for d in pool_n)}\n"
                f"# Elegiveis: {aval['qtd_elegiveis']} | Combinacoes C({aval['qtd_elegiveis']},{k})="
                f"{aval['combinacoes_possiveis']}\n"
                f"{texto_ref}\n"
            )
            nome = f"digitos_elegiveis_pool_{''.join(str(d) for d in pool_n)}.txt"
            return {
                "sucesso": True,
                "texto": cab,
                "nome_arquivo": nome,
                "qtd_apostas": 0,
                "qtd_elegiveis": aval["qtd_elegiveis"],
                "modo": "elegiveis",
            }

        if modo == "todas":
            if not pool_n:
                return {"sucesso": False, "erro": "Informe o pool de dígitos."}
            listed = cls.listar_combinacoes(
                modality_key, pool_n, dezenas_por_aposta,
                incluir_apostas=True, limite=MAX_COMBOS_EXPORTAR,
            )
            if not listed.get("pode_exportar_todas"):
                return {
                    "sucesso": False,
                    "erro": listed.get("aviso") or (
                        f"Demasiadas combinações ({listed.get('total_combinacoes')}). "
                        f"Máximo para exportar todas: {MAX_COMBOS_EXPORTAR}."
                    ),
                    "total_combinacoes": listed.get("total_combinacoes"),
                    "avaliacao": listed.get("avaliacao"),
                }
            linhas_apostas = listed["apostas"]
            sufixo = f"todas_{listed['total_combinacoes']}"
        else:
            # lote
            raw = apostas or []
            for i, ap in enumerate(raw, start=1):
                if isinstance(ap, dict):
                    dz = ap.get("dezenas") or []
                else:
                    dz = ap
                dz = sorted(int(x) for x in dz)
                if pool_n and not all(dezena_compativel(n, pool_n, sp.dezena_fmt_width) for n in dz):
                    return {
                        "sucesso": False,
                        "erro": f"Aposta {i}: dezena fora do pool (regra estrita).",
                    }
                linhas_apostas.append({"linha": i, "dezenas": dz})
            if not linhas_apostas:
                return {"sucesso": False, "erro": "Nenhuma aposta no lote para exportar. Gere antes."}
            sufixo = f"lote_{len(linhas_apostas)}"

        linhas_fmt: List[Dict[str, Any]] = [{"dezenas": a["dezenas"]} for a in linhas_apostas]
        if usar_aleatorio:
            from diadesorte.mes_sorte_select import resolver_meses_para_lote
            meses = resolver_meses_para_lote("aleatorio", len(linhas_fmt))
            for ap, mn in zip(linhas_fmt, meses):
                ap["extras"] = {
                    "tipo": "mes",
                    "num": int(mn),
                    "label": MESES_ABREV.get(int(mn), str(mn)),
                }
            export_extra = {}

        texto = formatar_export_txt(modality_key, linhas_fmt, export_extra)
        pool_tag = "".join(str(d) for d in pool_n) if pool_n else "x"
        nome = f"digitos_{sufixo}_pool_{pool_tag}.txt"
        return {
            "sucesso": True,
            "texto": texto,
            "nome_arquivo": nome,
            "qtd_apostas": len(linhas_apostas),
            "modo": modo,
            "pool": pool_n,
        }
