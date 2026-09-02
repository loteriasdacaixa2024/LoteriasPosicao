# -*- coding: utf-8 -*-
from typing import Any, Dict, List


def gerar_insight(row: Dict[str, Any]) -> Dict[str, str]:
    if row.get("total_concursos", 0) == 0:
        return {
            "titulo": "Sem dados",
            "texto": row.get("erro", "Sincronize a modalidade na Caixa."),
            "acao": "Sincronizar na home da modalidade",
        }

    partes = []
    acoes = []

    if row.get("grupo") == "supersete":
        partes.append(row.get("nota", "Análise por coluna C1–C7, dígitos 0–9."))
        partes.append(
            f"No histórico, {row.get('pct_mesmo_digito_2colunas')}% dos concursos repetiram o mesmo dígito "
            f"em 2+ colunas; {row.get('pct_7_digitos_distintos')}% tiveram 7 dígitos todos distintos."
        )
        partes.append(
            f"Par/ímpar (entre os 7 dígitos): {row.get('par_impar_moda')}; "
            f"ciclo médio: faltam {row.get('ciclo_faltantes_media')} dígitos por coluna (0–9)."
        )
        if row.get("ultimo_digitos"):
            partes.append(f"Último concurso: {' · '.join(f'C{i+1}={d}' for i, d in enumerate(row['ultimo_digitos']))}.")
        acoes.append("Use Sniper por Colunas C1–C7 e Gerador Elite na modalidade Super Sete.")
        return {
            "titulo": f"Insight — {row['nome']}",
            "texto": " ".join(partes),
            "acao": " · ".join(acoes),
        }

    if row.get("key") == "quina" and row.get("concursos_especiais"):
        for esp in row["concursos_especiais"]:
            partes.append(
                f"O site destaca o concurso {esp.get('concurso')} ({esp.get('label')}) — "
                f"numeração paralela à série regular (último sorteado: {row.get('ultimo_oficial_api')}). "
                f"Estatísticas usam a série 1..{row.get('ultimo_oficial_api')}."
            )

    if row.get("desatualizado") or row.get("tem_lacunas"):
        api = row.get("ultimo_oficial_api") or "?"
        max_l = row.get("concurso_max_local") or row.get("ultimo_concurso") or "?"
        falt = row.get("faltantes_qtd") or 0
        partes.append(
            f"Base desatualizada: site Caixa no concurso {api}, "
            f"gravado até {max_l} ({falt} lacuna(s) na faixa 1..{api}). "
            f"Use Sincronizar todas para varrer e importar os faltantes."
        )

    if row.get("layout") != "posicional":
        pct = row.get("pct_coluna_2plus")
        if pct is not None:
            partes.append(
                f"No histórico, {pct}% dos concursos tiveram 2+ dezenas no mesmo final "
                f"(teórico {row.get('teorico_pct_coluna_2plus')}%)."
            )
            if row.get("ultimo_tem_coluna_2plus"):
                partes.append("Último sorteio repetiu final — padrão colunar ativo.")
            else:
                partes.append("Último sorteio espalhou finais — favorece cobertura ampla.")

    partes.append(
        f"Par/ímpar mais frequente: {row.get('par_impar_moda')}; "
        f"primos (moda {row.get('primos_moda')}, média {row.get('primos_media')})."
    )

    if row.get("ciclo_faltantes") is not None:
        partes.append(
            f"Ciclo atual: faltam {row['ciclo_faltantes']} de {row.get('aposta_label', '').split()[-1] if row.get('aposta_label') else '?'} "
            f"dezenas ({row.get('ciclo_pct')}% fechado)."
        )
        if row["ciclo_faltantes"] <= 15 and row.get("ciclo_faltantes_amostra"):
            partes.append(f"Faltantes: {', '.join(row['ciclo_faltantes_amostra'])}…")

    if row.get("linha_mais_freq"):
        partes.append(f"Linha (faixa) mais sorteada no agregado: {row['linha_mais_freq']}.")

    acoes.append("Use o Gerador Sniper → Apostas com essas evidências.")
    if row["key"] in ("quina", "megasena", "duplasena"):
        acoes.append("Desdobramento especial por colunas para fechar estrutura PAR/ÍMPAR.")

    return {
        "titulo": f"Insight — {row['nome']}",
        "texto": " ".join(partes),
        "acao": " · ".join(acoes),
    }


def enriquecer_linhas(linhas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in linhas:
        ins = gerar_insight(row)
        out.append({**row, "insight": ins})
    return out
