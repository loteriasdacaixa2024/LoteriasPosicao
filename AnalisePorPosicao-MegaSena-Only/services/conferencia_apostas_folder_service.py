"""
Concursos em conferencia_apostas/NUMERO/apostas.json conferidos com o banco Mega-Sena.
Inclui prêmios da API Caixa, valor investido e estrutura para UI de resultados.
"""
import json
import os
import re
from collections import Counter
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import desc

from models.shared import db
from models.sorteio_megasena import SorteioMegaSena
from services.api_megasena_service import ApiMegaSenaService

MIN_DEZENAS = 6
MAX_DEZENAS = 20

# Tabela oficial Mega-Sena (valor da aposta por quantidade de dezenas no volante) — Caixa
# Fonte: loterias.caixa.gov.br/Paginas/Mega-Sena.aspx — marque de 6 a 20 números
TABELA_PRECOS: Dict[int, float] = {
    6: 6.00,
    7: 42.00,
    8: 168.00,
    9: 504.00,
    10: 1260.00,
    11: 2772.00,
    12: 5544.00,
    13: 10296.00,
    14: 18018.00,
    15: 30030.00,
    16: 48048.00,
    17: 74256.00,
    18: 111384.00,
    19: 162792.00,
    20: 232560.00,
}

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "conferencia_apostas",
)


def _classificar_faixa(acertos: int) -> Optional[str]:
    if acertos >= 6:
        return "Sena (6 acertos)"
    if acertos == 5:
        return "Quina (5 acertos)"
    if acertos == 4:
        return "Quadra (4 acertos)"
    return None


def _calcular_valor_aposta(qtd: int) -> float:
    if qtd < MIN_DEZENAS or qtd > MAX_DEZENAS:
        return TABELA_PRECOS[6]
    return TABELA_PRECOS.get(qtd, TABELA_PRECOS[6])


def _obter_premios_concurso(numero_concurso: int) -> Dict[str, float]:
    """Busca valores de quadra/quina/sena na API Caixa."""
    premios = {"quadra": 0.0, "quina": 0.0, "sena": 0.0}
    dados = ApiMegaSenaService.buscar_concurso_especifico(numero_concurso)
    if not dados:
        return premios
    for item in dados.get("listaRateioPremio") or []:
        desc = (item.get("descricaoFaixa") or "").lower()
        valor = float(item.get("valorPremio") or 0)
        if "6 acertos" in desc or "sena" in desc:
            premios["sena"] = valor
        elif "5 acertos" in desc or "quina" in desc:
            premios["quina"] = valor
        elif "4 acertos" in desc or "quadra" in desc:
            premios["quadra"] = valor
    return premios


def _valor_premio_por_acertos(acertos: int, premios: Dict[str, float]) -> float:
    if acertos >= 6:
        return premios.get("sena", 0.0)
    if acertos == 5:
        return premios.get("quina", 0.0)
    if acertos == 4:
        return premios.get("quadra", 0.0)
    return 0.0


def _melhor_categoria(max_acertos: int) -> str:
    if max_acertos >= 6:
        return "sena"
    if max_acertos == 5:
        return "quina"
    if max_acertos == 4:
        return "quadra"
    return "outro"


def _analisar_aposta(
    numeros: List[int],
    sorteadas: Set[int],
    premios: Dict[str, float],
) -> Dict[str, Any]:
    """Analisa uma aposta (simples ou com múltiplas combinações de 6 dezenas)."""
    unicos = sorted(set(numeros))
    qtd = len(unicos)
    valor_aposta = _calcular_valor_aposta(qtd)
    volante_set = set(unicos)
    # Todas as dezenas do volante que saíram no sorteio (para destaque na UI)
    hits_volante = sorted(volante_set & sorteadas)
    acertos_volante = len(hits_volante)

    combos: List[Tuple[int, ...]]
    if qtd == 6:
        combos = [tuple(unicos)]
    else:
        combos = list(combinations(unicos, 6))

    max_acertos = 0
    faixas_atingidas: List[str] = []
    detalhes_premios: List[Dict[str, Any]] = []
    valor_premio_total = 0.0
    contagem_faixas: Counter = Counter()

    for combo in combos:
        acertos = len(set(combo) & sorteadas)
        max_acertos = max(max_acertos, acertos)
        faixa = _classificar_faixa(acertos)
        if faixa:
            valor = _valor_premio_por_acertos(acertos, premios)
            if valor > 0:
                valor_premio_total += valor
                contagem_faixas[faixa] += 1
                faixas_atingidas.append(faixa)
                detalhes_premios.append({
                    "descricao": faixa,
                    "valor": valor,
                    "faixa": faixa,
                })

    faixas_unicas = list(dict.fromkeys(faixas_atingidas))
    faixa_display = " + ".join(faixas_unicas) if faixas_unicas else None

    return {
        "valor_aposta": valor_aposta,
        "valor_premio": valor_premio_total,
        "valor_ganho": valor_premio_total,
        "contagem_faixas": contagem_faixas,
        "resultado": {
            "acertos": max_acertos,
            "acertos_volante": acertos_volante,
            "numeros_acertados": hits_volante,
            "melhor_categoria": _melhor_categoria(max_acertos),
            "faixa": faixa_display,
            "faixas_atingidas": faixas_unicas,
            "detalhes_premios": detalhes_premios,
            "valor_premio": valor_premio_total,
            "premiado": valor_premio_total > 0,
        },
    }


class ConferenciaApostasFolderService:

    @staticmethod
    def historico_aposta_volante(numeros: List[int], min_acertos: int = 4) -> Dict[str, Any]:
        """
        Histórico no banco local: concursos em que o volante (todas as dezenas apostadas)
        cruzado com o sorteio teve pelo menos ``min_acertos`` acertos (padrão: 4 = Quadra+).
        """
        if isinstance(numeros, str):
            numeros = [int(x) for x in re.findall(r"\d+", numeros)]
        unicos = sorted(set(int(n) for n in numeros))
        if len(unicos) < MIN_DEZENAS:
            return {
                "sucesso": False,
                "mensagem": f"Informe pelo menos {MIN_DEZENAS} dezenas distintas.",
            }
        if len(unicos) > MAX_DEZENAS:
            return {
                "sucesso": False,
                "mensagem": f"No máximo {MAX_DEZENAS} dezenas por aposta.",
            }
        aposta_set = set(unicos)
        rows = (
            db.session.query(SorteioMegaSena)
            .order_by(desc(SorteioMegaSena.concurso))
            .all()
        )
        historico: List[Dict[str, Any]] = []
        for s in rows:
            sorteadas = set(s.dezenas_lista())
            ac = len(aposta_set & sorteadas)
            if ac >= min_acertos:
                faixa = _classificar_faixa(ac) or f"{ac}/6"
                historico.append({
                    "concurso": s.concurso,
                    "data": s.data,
                    "acertos": ac,
                    "faixa": faixa,
                    "sorteados": sorted(sorteadas),
                })
        return {
            "sucesso": True,
            "numeros_apostados": unicos,
            "min_acertos": min_acertos,
            "total": len(historico),
            "historico": historico,
        }

    @staticmethod
    def listar_concursos_disponiveis() -> List[Dict[str, Any]]:
        if not os.path.isdir(BASE_DIR):
            os.makedirs(BASE_DIR, exist_ok=True)
            return []

        concursos = []
        for nome in os.listdir(BASE_DIR):
            pasta = os.path.join(BASE_DIR, nome)
            if not os.path.isdir(pasta):
                continue
            try:
                numero = int(nome)
            except ValueError:
                continue

            arquivo_json = os.path.join(pasta, "apostas.json")
            tem_json = os.path.isfile(arquivo_json)
            total_apostas = 0
            if tem_json:
                try:
                    with open(arquivo_json, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    total_apostas = len(dados.get("apostas", []))
                except Exception:
                    total_apostas = 0

            screenshots = [
                f for f in os.listdir(pasta)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            sorteio = SorteioMegaSena.query.filter_by(concurso=numero).first()
            dezenas_banco = sorteio.dezenas_lista() if sorteio else None

            concursos.append({
                "numero_concurso": numero,
                "tem_json": tem_json,
                "total_apostas": total_apostas,
                "total_screenshots": len(screenshots),
                "resultado_disponivel": sorteio is not None,
                "data_sorteio": sorteio.data if sorteio else None,
                "dezenas_banco": [f"{d:02d}" for d in dezenas_banco] if dezenas_banco else [],
                "pasta": nome,
            })

        concursos.sort(key=lambda x: x["numero_concurso"], reverse=True)
        return concursos

    @staticmethod
    def processar_concurso(numero_concurso: int) -> Dict[str, Any]:
        pasta = os.path.join(BASE_DIR, str(numero_concurso))
        if not os.path.isdir(pasta):
            return {
                "sucesso": False,
                "erro": "pasta_nao_encontrada",
                "mensagem": f"Pasta conferencia_apostas/{numero_concurso} não encontrada.",
            }

        sorteio = SorteioMegaSena.query.filter_by(concurso=numero_concurso).first()
        if not sorteio:
            return {
                "sucesso": False,
                "erro": "concurso_nao_encontrado",
                "mensagem": (
                    f"Concurso {numero_concurso} não está no banco. "
                    "Sincronize os sorteios antes de conferir."
                ),
            }

        arquivo_json = os.path.join(pasta, "apostas.json")
        if not os.path.isfile(arquivo_json):
            return {
                "sucesso": False,
                "erro": "sem_json",
                "mensagem": f"Arquivo apostas.json não encontrado em conferencia_apostas/{numero_concurso}/",
            }

        try:
            with open(arquivo_json, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
            if not conteudo:
                return {
                    "sucesso": False,
                    "erro": "json_vazio",
                    "mensagem": "O arquivo apostas.json está vazio.",
                }
            dados = json.loads(conteudo)
        except json.JSONDecodeError as e:
            return {"sucesso": False, "erro": "json_invalido", "mensagem": str(e)}

        if "apostas" not in dados:
            return {
                "sucesso": False,
                "erro": "json_invalido",
                "mensagem": 'JSON deve conter o campo "apostas".',
            }

        sorteadas = set(sorteio.dezenas_lista())
        sorteadas_lista = sorted(sorteadas)
        premios = _obter_premios_concurso(numero_concurso)

        apostas_out: List[Dict[str, Any]] = []
        distribuicao_faixas: Dict[str, Dict[str, float]] = {}
        total_investido = 0.0
        total_ganho = 0.0
        faixas_resumo = Counter()
        erros: List[str] = []

        for idx, aposta in enumerate(dados.get("apostas", []), 1):
            numeros = aposta.get("numeros", [])
            if isinstance(numeros, str):
                numeros = [int(x) for x in re.findall(r"\d+", numeros)]

            if len(numeros) < MIN_DEZENAS or len(numeros) > MAX_DEZENAS:
                erros.append(
                    f"Aposta {idx}: deve ter entre {MIN_DEZENAS} e {MAX_DEZENAS} dezenas."
                )
                continue

            if len(set(numeros)) != len(numeros):
                erros.append(f"Aposta {idx}: dezenas duplicadas.")
                continue

            invalidas = [n for n in numeros if n < 1 or n > 60]
            if invalidas:
                erros.append(f"Aposta {idx}: dezena(s) fora do volante: {invalidas}")
                continue

            analise = _analisar_aposta(numeros, sorteadas, premios)
            total_investido += analise["valor_aposta"]
            total_ganho += analise["valor_premio"]

            for det in analise["resultado"]["detalhes_premios"]:
                faixa = det["faixa"]
                if faixa not in distribuicao_faixas:
                    distribuicao_faixas[faixa] = {"quantidade": 0, "total_ganho": 0.0}
                distribuicao_faixas[faixa]["quantidade"] += 1
                distribuicao_faixas[faixa]["total_ganho"] += det["valor"]
                if "Sena" in faixa:
                    faixas_resumo["Sena"] += 1
                elif "Quina" in faixa:
                    faixas_resumo["Quina"] += 1
                elif "Quadra" in faixa:
                    faixas_resumo["Quadra"] += 1

            apostas_out.append({
                "numero_aposta": aposta.get("numero", idx),
                "fonte": "JSON",
                "numeros_apostados": numeros,
                "numeros": [f"{n:02d}" for n in numeros],
                "valor_aposta": analise["valor_aposta"],
                "valor_ganho": analise["valor_ganho"],
                "acertos": analise["resultado"]["acertos"],
                "dezenas_acertadas": [
                    f"{n:02d}" for n in analise["resultado"]["numeros_acertados"]
                ],
                "premiacao": analise["resultado"]["faixa"] or f"{analise['resultado']['acertos']}/6",
                "resultado": analise["resultado"],
            })

        lucro = total_ganho - total_investido
        roi = (lucro / total_investido * 100) if total_investido > 0 else 0.0

        return {
            "sucesso": True,
            "concurso": numero_concurso,
            "origem": "JSON",
            "fonte_dados": "JSON",
            "dezenas_sorteadas": [f"{d:02d}" for d in sorteadas_lista],
            "data_sorteio": sorteio.data,
            "resultado_sorteio": {
                "concurso": numero_concurso,
                "data": sorteio.data,
                "numeros": sorteadas_lista,
            },
            "premios_concurso": premios,
            "resumo": {
                "total_apostas_arquivo": len(dados.get("apostas", [])),
                "total_apostas_validas": len(apostas_out),
                "total_apostas": len(apostas_out),
                "total_investido": round(total_investido, 2),
                "total_ganho": round(total_ganho, 2),
                "lucro": round(lucro, 2),
                "roi": round(roi, 2),
                "senas": faixas_resumo.get("Sena", 0),
                "quinas": faixas_resumo.get("Quina", 0),
                "quadras": faixas_resumo.get("Quadra", 0),
                "distribuicao_faixas": distribuicao_faixas,
                "erros_parse": len(erros),
            },
            "erros": erros,
            "apostas": apostas_out,
        }
