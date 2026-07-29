# -*- coding: utf-8 -*-
"""Exportação TXT/CSV por aba — Análises Gerais."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _cabecalho_txt(data: Dict[str, Any], titulo: str) -> List[str]:
    linhas = [
        titulo,
        f"Modalidade: {data.get('modality_nome', '—')}",
        f"Base: {data.get('base_label', data.get('base_estatistica', '—'))}",
        f"Janela: {data.get('janela_label', data.get('janela', '—'))}",
        f"Concursos: {data.get('total_concursos', 0)}",
        f"Último concurso: #{data.get('ultimo_concurso', '—')}",
        f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
    ]
    insights = data.get("insights") or []
    if insights:
        linhas.append("Insights:")
        for t in insights:
            linhas.append(f"  • {t.replace('**', '')}")
        linhas.append("")
    return linhas


def _csv_string(rows: List[List[Any]], delimiter: str = ";") -> str:
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, delimiter=delimiter, lineterminator="\r\n")
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def _nome_arquivo(data: Dict[str, Any], aba_id: str, ext: str) -> str:
    base = data.get("base_estatistica", "geral")
    janela = data.get("janela", 0)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"analises_gerais_{aba_id}_{base}_j{janela}_{stamp}.{ext}"


def export_classificacao(data: Dict[str, Any], formato: str) -> Tuple[str, str, str]:
    inds = [i["codigo"] for i in (data.get("indicadores") or [])]
    labels = {i["codigo"]: i.get("label", i["codigo"]) for i in (data.get("indicadores") or [])}
    linhas = data.get("linhas") or []

    if formato == "csv":
        head = ["concurso", "data", "dezenas"] + inds
        rows = [head]
        for row in linhas:
            dez = "-".join(f"{d:02d}" for d in (row.get("dezenas") or []))
            rows.append([
                row.get("concurso", ""),
                row.get("data", ""),
                dez,
                *[row.get(c, "") for c in inds],
            ])
        content = _csv_string(rows)
        return content, _nome_arquivo(data, "classificacao", "csv"), "text/csv; charset=utf-8"

    out = _cabecalho_txt(data, "CLASSIFICAÇÃO DOS NÚMEROS — Análises Gerais")
    hdr = "Concurso | Data | Dezenas | " + " | ".join(inds)
    out.append(hdr)
    out.append("-" * min(len(hdr), 120))
    for row in linhas:
        dez = " ".join(f"{d:02d}" for d in (row.get("dezenas") or []))
        vals = " | ".join(str(row.get(c, "")) for c in inds)
        out.append(f"#{row.get('concurso', '')} | {row.get('data', '')} | {dez} | {vals}")

    resumo = data.get("resumo") or {}
    if resumo:
        out.append("")
        out.append("Resumo por indicador:")
        for cod in inds:
            r = resumo.get(cod, {})
            out.append(
                f"  {cod} ({labels.get(cod, cod)}): moda {r.get('moda', '—')} "
                f"({r.get('moda_pct', 0)}%), média {r.get('media', '—')}"
            )
    return "\n".join(out), _nome_arquivo(data, "classificacao", "txt"), "text/plain; charset=utf-8"


def export_digitos(data: Dict[str, Any], formato: str) -> Tuple[str, str, str]:
    linhas = data.get("linhas") or []
    painel = data.get("painel_digitos") or []

    if formato == "csv":
        rows = [["concurso", "data", "digitos", "qtd", "rep_anterior"]]
        for row in linhas:
            rows.append([
                row.get("concurso", ""),
                row.get("data", ""),
                row.get("digitos_distintos_fmt", ""),
                row.get("qtd_digitos_distintos", ""),
                row.get("digitos_repetidos_concurso_anterior", ""),
            ])
        rows.append([])
        rows.append(["digito", "concursos", "pct", "freq_aparicoes"])
        for p in painel:
            rows.append([
                p.get("digito", ""),
                p.get("concursos_com_digito", ""),
                p.get("pct_concursos", ""),
                p.get("freq_aparicoes", ""),
            ])
        content = _csv_string(rows)
        return content, _nome_arquivo(data, "digitos", "csv"), "text/csv; charset=utf-8"

    out = _cabecalho_txt(data, "DÍGITOS UTILIZADOS — Análises Gerais")
    out.append("Painel por dígito:")
    out.append("Díg. | Concursos | % | Aparições")
    for p in painel:
        out.append(
            f"  {p.get('digito', '')} | {p.get('concursos_com_digito', '')} | "
            f"{p.get('pct_concursos', '')}% | {p.get('freq_aparicoes', '')}"
        )
    out.append("")
    out.append("Histórico:")
    out.append("Concurso | Dígitos | Qtd | Rep. anterior")
    for row in linhas:
        out.append(
            f"#{row.get('concurso', '')} | {row.get('digitos_distintos_fmt', '')} | "
            f"{row.get('qtd_digitos_distintos', '')} | "
            f"{row.get('digitos_repetidos_concurso_anterior', '')}"
        )
    return "\n".join(out), _nome_arquivo(data, "digitos", "txt"), "text/plain; charset=utf-8"


def export_soma(data: Dict[str, Any], formato: str) -> Tuple[str, str, str]:
    linhas = data.get("linhas") or []
    dist = data.get("distribuicao_soma_total") or []

    if formato == "csv":
        rows = [["concurso", "data", "soma_digitos", "media_dez", "soma_dezenas", "paridade"]]
        for row in linhas:
            rows.append([
                row.get("concurso", ""),
                row.get("data", ""),
                row.get("soma_total_digitos", ""),
                row.get("media_soma_digitos", ""),
                row.get("soma_dezenas", ""),
                "Par" if row.get("soma_par") else "Ímpar",
            ])
        rows.append([])
        rows.append(["soma_total", "ocorrencias", "pct"])
        for d in dist:
            rows.append([d.get("valor", ""), d.get("ocorrencias", ""), d.get("pct", "")])
        content = _csv_string(rows)
        return content, _nome_arquivo(data, "soma", "csv"), "text/csv; charset=utf-8"

    out = _cabecalho_txt(data, "SOMA DOS DÍGITOS — Análises Gerais")
    out.append("Distribuição soma total:")
    for d in dist:
        out.append(f"  {d.get('valor', '')}: {d.get('ocorrencias', '')}× ({d.get('pct', '')}%)")
    out.append("")
    out.append("Histórico:")
    out.append("Concurso | Soma díg. | Média/dez | Soma dez. | Paridade")
    for row in linhas:
        par = "Par" if row.get("soma_par") else "Ímpar"
        out.append(
            f"#{row.get('concurso', '')} | {row.get('soma_total_digitos', '')} | "
            f"{row.get('media_soma_digitos', '')} | {row.get('soma_dezenas', '')} | {par}"
        )
    return "\n".join(out), _nome_arquivo(data, "soma", "txt"), "text/plain; charset=utf-8"


def export_comparativo(data: Dict[str, Any], formato: str) -> Tuple[str, str, str]:
    aba_id = data.get("aba_id", "comparativo")
    linhas_cmp = data.get("linhas_comparativo") or []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"analises_gerais_{aba_id}_venc_vs_acum_j{data.get('janela', 0)}_{stamp}.{formato}"

    if formato == "csv":
        rows = [["indicador", "vencedores", "acumulados", "delta"]]
        for row in linhas_cmp:
            rows.append([
                row.get("label", row.get("codigo", "")),
                row.get("vencedores", ""),
                row.get("acumulados", ""),
                row.get("delta", ""),
            ])
        return _csv_string(rows), fname, "text/csv; charset=utf-8"

    out = [
        f"COMPARATIVO VENCEDORES × ACUMULADOS — {data.get('aba_titulo', aba_id)}",
        f"Modalidade: {data.get('modality_nome', '—')}",
        f"Janela: {data.get('janela_label', data.get('janela', '—'))}",
        f"Vencedores: {data.get('total_vencedores', 0)} concursos",
        f"Acumulados: {data.get('total_acumulados', 0)} concursos",
        f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "Indicador | Vencedores | Acumulados | Δ",
        "-" * 60,
    ]
    for row in linhas_cmp:
        out.append(
            f"{row.get('label', row.get('codigo', ''))} | "
            f"{row.get('vencedores', '')} | {row.get('acumulados', '')} | "
            f"{row.get('delta', '')}"
        )
    return "\n".join(out), fname, "text/plain; charset=utf-8"


def _apostas_diferencial_pares(data: Dict[str, Any]) -> Tuple[List[int], List[int], bool]:
    bo = data.get("bloco_ordenado") or {}
    bp = data.get("bloco_posicional") or {}
    ordenadas = sorted(int(d) for d in (bo.get("numeros_apostar_ordenados") or []))
    posicional = sorted(int(d) for d in (bp.get("numeros_apostar_ordenados") or []))
    iguais = ordenadas == posicional
    return ordenadas, posicional, iguais


def export_diferencial_apostas(data: Dict[str, Any], formato: str) -> Tuple[str, str, str]:
    pad = int(data.get("pad_width", 2))
    ordenadas, posicional, iguais = _apostas_diferencial_pares(data)

    def fmt(dz: List[int]) -> str:
        return " ".join(f"{int(d):0{pad}d}" for d in dz)

    ultimo = data.get("ultimo_concurso", "")
    penultimo = data.get("penultimo_concurso", "")

    if formato == "csv":
        rows = [["tipo", "dezenas"]]
        rows.append(["ORDENADAS", fmt(ordenadas)])
        if not iguais:
            rows.append(["SORTEIO", fmt(posicional)])
        content = _csv_string(rows)
        fname = _nome_arquivo(data, "diferencial_apostas", "csv")
        return content, fname, "text/csv; charset=utf-8"

    out = [
        f"DIFERENCIAL CRUZADO — À apostar — #{ultimo} vs #{penultimo}",
        f"Modalidade: {data.get('modality_nome', '—')}",
        f"Base: {data.get('base_label', data.get('base_estatistica', '—'))}",
        f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        f"ORDENADAS:   {fmt(ordenadas)}",
    ]
    if not iguais:
        out.append(f"SORTEIO:     {fmt(posicional)}")
    return "\r\n".join(out), _nome_arquivo(data, "diferencial_apostas", "txt"), "text/plain; charset=utf-8"


def export_diferencial(data: Dict[str, Any], formato: str) -> Tuple[str, str, str]:
    pad = int(data.get("pad_width", 2))
    bo = data.get("bloco_ordenado") or {}
    bp = data.get("bloco_posicional") or {}
    hist = data.get("historico") or []

    def fmt(dz):
        return " ".join(f"{int(d):0{pad}d}" for d in (dz or []))

    if formato == "csv":
        rows = [
            ["modo", "ultimo", "penultimo", "subtracao", "resultado", "aposta_ordenada", "aposta_posicional"],
            ["ordenado", fmt(bo.get("ultimo")), fmt(bo.get("penultimo")),
             fmt(bo.get("subtracao_abs")), fmt(bo.get("resultado")),
             fmt(bo.get("numeros_apostar_ordenados")), fmt(bo.get("numeros_apostar_posicional"))],
            ["posicional", fmt(bp.get("ultimo")), fmt(bp.get("penultimo")),
             fmt(bp.get("subtracao_abs")), fmt(bp.get("resultado")),
             fmt(bp.get("numeros_apostar_ordenados")), fmt(bp.get("numeros_apostar_posicional"))],
            [],
            ["concurso", "penultimo", "ultimo_ordem", "aposta_ordenada", "ajuste"],
        ]
        for row in hist:
            rows.append([
                row.get("concurso", ""),
                row.get("penultimo_concurso", ""),
                row.get("ultimo_fmt", ""),
                row.get("aposta_ordenada_fmt", ""),
                "sim" if row.get("teve_ajuste") else "nao",
            ])
        content = _csv_string(rows)
        return content, _nome_arquivo(data, "diferencial", "csv"), "text/csv; charset=utf-8"

    out = _cabecalho_txt(data, "DIFERENCIAL CRUZADO — Análises Gerais")
    out.append(f"Último #{data.get('ultimo_concurso')} vs Penúltimo #{data.get('penultimo_concurso')}")
    out.append("")
    for label, blk in (("ORDENADAS", bo), ("POSICIONAL", bp)):
        out.append(f"--- {label} ---")
        out.append(f"Último:     {fmt(blk.get('ultimo'))}")
        out.append(f"Penúltimo:  {fmt(blk.get('penultimo'))}")
        out.append(f"Subtração:  {fmt(blk.get('subtracao_abs'))}")
        out.append(f"Resultado:  {fmt(blk.get('resultado'))}")
        out.append(f"À apostar:  {fmt(blk.get('numeros_apostar_ordenados'))}")
        out.append("")
    avisos = data.get("avisos") or []
    if avisos:
        out.append("Ajustes na normalização:")
        for a in avisos:
            out.append(f"  • {a}")
        out.append("")
    out.append("Histórico (ordem posicional):")
    for row in hist:
        out.append(
            f"#{row.get('concurso')} ← #{row.get('penultimo_concurso')} | "
            f"{row.get('ultimo_fmt', '')} → aposta {row.get('aposta_ordenada_fmt', '')}"
        )
    return "\n".join(out), _nome_arquivo(data, "diferencial", "txt"), "text/plain; charset=utf-8"


_EXPORTERS = {
    "classificacao-numeros": export_classificacao,
    "digitos-utilizados": export_digitos,
    "soma-digitos": export_soma,
    "diferencial-cruzado": export_diferencial,
}


def formatar_export(
    aba_id: str,
    data: Dict[str, Any],
    formato: str = "txt",
    tipo: str = "completo",
) -> Tuple[str, str, str]:
    fmt = (formato or "txt").strip().lower()
    if fmt not in ("txt", "csv"):
        raise ValueError("Formato deve ser txt ou csv.")
    if data.get("comparativo"):
        return export_comparativo(data, fmt)
    if aba_id == "diferencial-cruzado" and (tipo or "completo").strip().lower() == "apostas":
        return export_diferencial_apostas(data, fmt)
    fn = _EXPORTERS.get(aba_id)
    if not fn:
        raise ValueError(f"Exportação indisponível para aba: {aba_id}")
    return fn(data, fmt)
