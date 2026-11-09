# -*- coding: utf-8 -*-
"""Fases do globo, painel de cores e sorteio uniforme sem reposição."""
from __future__ import annotations

import secrets
from typing import Dict, List, Optional

from simulador_globo.cores import PALETA, cor_da_dezena, percentual
from simulador_globo.dados_times import TIMES_DO_CORACAO

_RNG = secrets.SystemRandom()

ORDEM_MODALIDADES = (
    "lotofacil",
    "diadesorte",
    "lotomania",
    "quina",
    "megasena",
    "maismilionaria",
    "duplasena",
    "timemania",
    "supersete",
)

MESES = (
    (1, "Janeiro", "Jan", "#1565C0"),
    (2, "Fevereiro", "Fev", "#6A1B9A"),
    (3, "Março", "Mar", "#2E7D32"),
    (4, "Abril", "Abr", "#EF6C00"),
    (5, "Maio", "Mai", "#AD1457"),
    (6, "Junho", "Jun", "#00838F"),
    (7, "Julho", "Jul", "#F9A825"),
    (8, "Agosto", "Ago", "#4E342E"),
    (9, "Setembro", "Set", "#37474F"),
    (10, "Outubro", "Out", "#C62828"),
    (11, "Novembro", "Nov", "#4527A0"),
    (12, "Dezembro", "Dez", "#1B5E20"),
)

NOTAS = {
    "megasena": "60 bolas e 6 saem. A cor segue o algarismo final — configuração inicial, igual para cada dezena com o mesmo final.",
    "lotofacil": "25 bolas e 15 saem. O universo não é múltiplo de 10, então as cores não ficam com a mesma quantidade.",
    "quina": "80 bolas e 5 saem. Cada cor reúne 8 dezenas.",
    "lotomania": "100 bolas, de 00 a 99, e 20 saem. O 00 entra na cor branca.",
    "timemania": "80 bolas e 7 dezenas saem. Em seguida é sorteado 1 Time do Coração entre 80, fora da paleta das dezenas.",
    "diadesorte": "31 bolas e 7 dezenas saem. O 31 soma mais uma bola vermelha. Depois sai 1 Mês da Sorte entre 12.",
    "duplasena": "50 bolas. Há dois sorteios independentes de 6. O globo é recarregado antes do 2º sorteio, e um número pode sair nos dois.",
    "supersete": "Sete colunas, cada uma com os dígitos 0 a 9. A cor é a do dígito. O mesmo dígito pode sair em colunas diferentes.",
    "maismilionaria": "50 bolas e 6 dezenas saem. Em seguida saem 2 trevos entre 6, num globo separado.",
}

AVISO = (
    "Simulação experimental e educativa. O resultado é aleatório, "
    "independe do histórico oficial e não representa, antecipa ou prevê "
    "o sorteio da Caixa Econômica Federal."
)


class SorteioEncerrado(Exception):
    pass


def _rotulo_dezena(numero: int, modalidade: str) -> str:
    if modalidade == "supersete":
        return str(int(numero))
    return f"{int(numero):02d}"


def _bola_dezena(numero: int, modalidade: str, *, chave: Optional[str] = None, coluna=None) -> dict:
    cor = cor_da_dezena(numero, modalidade)
    return {
        "chave": chave or str(int(numero)),
        "numero": int(numero),
        "rotulo": _rotulo_dezena(numero, modalidade),
        "grupo": "digito" if modalidade == "supersete" else "dezena",
        "cor_id": cor["id"],
        "cor_nome": cor["nome"],
        "hex": cor["hex"],
        "texto": cor["texto"],
        "coluna": coluna,
    }


def _fase_globo(modality_key: str, regras: dict, *, fase_id: str, titulo: str) -> dict:
    bolas = [
        _bola_dezena(n, modality_key)
        for n in range(int(regras["dezena_min"]), int(regras["dezena_max"]) + 1)
    ]
    return {
        "id": fase_id,
        "titulo": titulo,
        "tipo": "globo",
        "quantidade": int(regras["sorteadas"]),
        "extraido": 0,
        "restantes": bolas,
    }


def _fase_colunas() -> dict:
    colunas = []
    for indice in range(1, 8):
        bolas = [
            _bola_dezena(dig, "supersete", chave=f"c{indice}-{dig}", coluna=indice)
            for dig in range(10)
        ]
        colunas.append({
            "indice": indice,
            "titulo": f"Coluna {indice}",
            "restantes": bolas,
        })
    return {
        "id": "colunas",
        "titulo": "Colunas",
        "tipo": "colunas",
        "quantidade": 7,
        "extraido": 0,
        "colunas": colunas,
    }


def _fase_meses() -> dict:
    bolas = []
    for numero, nome, abrev, hex_cor in MESES:
        bolas.append({
            "chave": f"m{numero}",
            "numero": numero,
            "rotulo": abrev,
            "nome": nome,
            "grupo": "mes",
            "cor_id": f"mes-{numero}",
            "cor_nome": nome,
            "hex": hex_cor,
            "texto": "#ffffff" if numero != 7 else "#212121",
            "coluna": None,
        })
    return {
        "id": "mes",
        "titulo": "Mês da Sorte",
        "tipo": "globo",
        "quantidade": 1,
        "extraido": 0,
        "restantes": bolas,
    }


def _fase_trevos() -> dict:
    total, pick = 6, 2
    try:
        from geradores_elite.modality_config import MODALITIES
        cfg = MODALITIES.get("maismilionaria") or {}
        total = int(cfg.get("trevo_total") or 6)
        pick = int(cfg.get("trevo_pick") or 2)
    except Exception:
        pass
    bolas = [
        {
            "chave": f"v{n}",
            "numero": n,
            "rotulo": str(n),
            "grupo": "trevo",
            "cor_id": "trevo",
            "cor_nome": "Trevo",
            "hex": "#1B8A3E",
            "texto": "#ffffff",
            "coluna": None,
        }
        for n in range(1, total + 1)
    ]
    return {
        "id": "trevos",
        "titulo": "Trevos",
        "tipo": "globo",
        "quantidade": pick,
        "extraido": 0,
        "restantes": bolas,
    }


def _fase_times() -> dict:
    bolas = [
        {
            "chave": f"t{numero}",
            "numero": numero,
            "rotulo": nome,
            "grupo": "time",
            "cor_id": "time",
            "cor_nome": "Time do Coração",
            "hex": "#00695C",
            "texto": "#ffffff",
            "coluna": None,
        }
        for numero, nome in TIMES_DO_CORACAO.items()
    ]
    return {
        "id": "time",
        "titulo": "Time do Coração",
        "tipo": "lista",
        "quantidade": 1,
        "extraido": 0,
        "restantes": bolas,
    }


def construir_fases(modality_key: str) -> List[dict]:
    from configuracoes.regras_modalidade import get_regras

    key = (modality_key or "").strip().lower()
    if key == "supersete":
        return [_fase_colunas()]
    regras = get_regras(key)
    if key == "duplasena":
        return [
            _fase_globo(key, regras, fase_id="dezenas_1", titulo="1º sorteio"),
            _fase_globo(key, regras, fase_id="dezenas_2", titulo="2º sorteio"),
        ]
    fases = [_fase_globo(key, regras, fase_id="dezenas", titulo="Dezenas")]
    if key == "diadesorte":
        fases.append(_fase_meses())
    elif key == "maismilionaria":
        fases.append(_fase_trevos())
    elif key == "timemania":
        fases.append(_fase_times())
    return fases


def _contar_fase(fase: dict) -> int:
    if fase.get("tipo") == "colunas":
        return sum(len(c.get("restantes") or []) for c in fase.get("colunas") or [])
    return len(fase.get("restantes") or [])


def restantes_globo(estado: dict) -> int:
    fases = estado.get("fases") or []
    idx = int(estado.get("fase_idx") or 0)
    if idx >= len(fases):
        return 0
    return _contar_fase(fases[idx])


def previstas_de(estado: dict) -> int:
    return sum(int(f.get("quantidade") or 0) for f in estado.get("fases") or [])


def novo_estado(modality_key: str) -> dict:
    fases = construir_fases(modality_key)
    return {
        "modalidade": modality_key,
        "universo": _contar_fase(fases[0]),
        "fases": fases,
        "fase_idx": 0,
        "ordem": 0,
    }


def serializar_fase(fase: dict) -> dict:
    if fase.get("tipo") == "colunas":
        return {
            "id": fase["id"],
            "titulo": fase["titulo"],
            "tipo": "colunas",
            "quantidade": fase["quantidade"],
            "colunas": [
                {
                    "indice": c["indice"],
                    "titulo": c["titulo"],
                    "bolas": [dict(b) for b in c["restantes"]],
                }
                for c in fase["colunas"]
            ],
        }
    return {
        "id": fase["id"],
        "titulo": fase["titulo"],
        "tipo": fase["tipo"],
        "quantidade": fase["quantidade"],
        "bolas": [dict(b) for b in fase["restantes"]],
    }


def fases_publicas(modality_key: str) -> List[dict]:
    return [serializar_fase(f) for f in construir_fases(modality_key)]


def _extrair(fase: dict, rng) -> dict:
    if fase.get("tipo") == "colunas":
        indice = int(fase.get("extraido") or 0)
        colunas = fase["colunas"]
        if indice >= len(colunas):
            raise SorteioEncerrado("Não há coluna restante.")
        coluna = colunas[indice]
        pool = coluna["restantes"]
        if not pool:
            raise SorteioEncerrado("A coluna está vazia.")
        escolhida = dict(pool.pop(rng.randrange(len(pool))))
        escolhida["coluna"] = coluna["indice"]
        escolhida["coluna_titulo"] = coluna["titulo"]
        return escolhida
    pool = fase["restantes"]
    if not pool:
        raise SorteioEncerrado("Não há bola restante nesta etapa.")
    return dict(pool.pop(rng.randrange(len(pool))))


def sortear_proxima(estado: dict, rng=None) -> dict:
    rng = rng or _RNG
    fases = estado["fases"]
    idx = int(estado["fase_idx"])
    if idx >= len(fases):
        raise SorteioEncerrado("Este sorteio já foi encerrado.")
    fase = fases[idx]
    bola = _extrair(fase, rng)
    estado["ordem"] = int(estado.get("ordem") or 0) + 1
    bola["ordem"] = estado["ordem"]
    bola["fase_id"] = fase["id"]
    bola["fase_titulo"] = fase["titulo"]
    fase["extraido"] = int(fase.get("extraido") or 0) + 1
    encerrou_fase = fase["extraido"] >= int(fase["quantidade"])
    proxima = None
    concluida = False
    if encerrou_fase:
        estado["fase_idx"] = idx + 1
        if estado["fase_idx"] >= len(fases):
            concluida = True
        else:
            proxima = serializar_fase(fases[estado["fase_idx"]])
    previstas = previstas_de(estado)
    if concluida:
        restantes = _contar_fase(fases[-1])
    else:
        restantes = _contar_fase(fases[estado["fase_idx"]])
    return {
        "bola": bola,
        "fase_encerrada": bool(encerrou_fase and not concluida),
        "proxima_fase": proxima,
        "concluida": concluida,
        "sorteadas": estado["ordem"],
        "previstas": previstas,
        "faltam": max(0, previstas - estado["ordem"]),
        "restantes_globo": restantes,
        "fase_titulo": bola["fase_titulo"],
    }


def aplicar_proxima(registro: dict, velocidade_ms: Optional[int] = None) -> dict:
    if registro["status"] in ("completa", "interrompida"):
        raise SorteioEncerrado("Este sorteio já foi encerrado.")
    evento = sortear_proxima(registro["estado"])
    registro["sequencia"].append(evento["bola"])
    registro["status"] = "completa" if evento["concluida"] else "em_andamento"
    registro["bolas_restantes"] = int(evento["restantes_globo"])
    if velocidade_ms:
        registro["velocidade_ms"] = int(velocidade_ms)
    registro["evento"] = evento
    return registro


def aplicar_finalizar(registro: dict) -> dict:
    if registro["status"] != "completa":
        registro["status"] = "interrompida"
    return registro


def simular_completo(modality_key: str, rng=None) -> List[dict]:
    estado = novo_estado(modality_key)
    saida = []
    for _ in range(500):
        evento = sortear_proxima(estado, rng=rng)
        saida.append(evento["bola"])
        if evento["concluida"]:
            return saida
    raise RuntimeError(f"Sorteio de {modality_key} não encerrou.")


def _resumo(key: str, fases: List[dict]) -> str:
    if key == "supersete":
        return "7 colunas, 1 dígito em cada"
    partes = []
    for fase in fases:
        if fase["tipo"] == "lista":
            partes.append(fase["titulo"])
        elif fase["id"] == "mes":
            partes.append("1 mês")
        elif fase["id"] == "trevos":
            partes.append(f"{fase['quantidade']} trevos")
        else:
            partes.append(f"{fase['quantidade']} no {fase['titulo'].lower()}" if key == "duplasena"
                          else f"{fase['quantidade']} dezenas")
    return " + ".join(partes)


def montar_painel(modality_key: str) -> dict:
    from configuracoes.regras_modalidade import get_regras

    key = (modality_key or "").strip().lower()
    regras = get_regras(key)
    fases = construir_fases(key)
    universo = _contar_fase(fases[0])
    grupos: Dict[str, List[str]] = {item["id"]: [] for item in PALETA}
    if key == "supersete":
        for dig in range(10):
            cor = cor_da_dezena(dig, key)
            grupos[cor["id"]].append(str(dig))
        quantidades = {cid: 7 for cid in grupos}
    else:
        quantidades = {cid: 0 for cid in grupos}
        inicio = int(regras["dezena_min"])
        fim = int(regras["dezena_max"])
        for n in range(inicio, fim + 1):
            cor = cor_da_dezena(n, key)
            rotulo = f"{n:02d}"
            grupos[cor["id"]].append(rotulo)
            quantidades[cor["id"]] += 1
    cores = []
    for item in PALETA:
        qtd = int(quantidades[item["id"]])
        cores.append({
            "id": item["id"],
            "nome": item["nome"],
            "hex": item["hex"],
            "texto": item["texto"],
            "quantidade": qtd,
            "percentual": percentual(qtd, universo),
            "dezenas": grupos[item["id"]],
            "detalhe": "uma em cada coluna" if key == "supersete" else "",
        })
    return {
        "key": key,
        "nome": regras["nome"],
        "universo": universo,
        "universo_label": regras["universo_label"],
        "dezenas_sorteadas": int(regras["sorteadas"]),
        "sorteadas": sum(int(f["quantidade"]) for f in fases),
        "resumo": _resumo(key, fases),
        "nota": NOTAS.get(key, ""),
        "aviso": AVISO,
        "porta": int(regras["porta"]),
        "cores": cores,
    }


def listar_modalidades() -> List[dict]:
    saida = []
    for key in ORDEM_MODALIDADES:
        painel = montar_painel(key)
        saida.append({
            "key": painel["key"],
            "nome": painel["nome"],
            "universo": painel["universo"],
            "universo_label": painel["universo_label"],
            "resumo": painel["resumo"],
            "porta": painel["porta"],
            "nota": painel["nota"],
        })
    return saida
