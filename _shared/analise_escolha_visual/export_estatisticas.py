# -*- coding: utf-8 -*-
"""Excel da seção 2 (Estatísticas Básicas).

Reusa as linhas já calculadas pelo enriquecimento. Não recalcula indicadores.
A cópia em disco fica em conferencia_apostas, sem expor o caminho do servidor.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import tempfile
import threading
import time
import unicodedata
import zipfile
from urllib.parse import urlencode
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from io import BytesIO
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

log = logging.getLogger("lp.estatisticas_excel")

ARQUIVO_MODALIDADE = "Estatisticas_Basicas.xlsx"
ARQUIVO_CONSOLIDADO = "Estatisticas_Todas_Modalidades.xlsx"
PASTA_PUBLICA = "conferencia_apostas"

_ALIAS_CONF = {"diadesorte": "diasorte"}
_SLUG_OK = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NOME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}\.xlsx$")
_DATA_BR = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_DATA_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_PLANILHA_INVALIDA = re.compile(r"[\[\]:*?/\\]")

# Colunas na ordem oficial do sorteio — a mesma de dezenas_ordem_lista.
_COLUNAS_ORDEM = {
    "lotofacil": [f"posicao_{i}" for i in range(1, 16)],
    "diadesorte": [f"d{i}" for i in range(1, 8)],
    "lotomania": [f"d{i:02d}" for i in range(1, 21)],
    "quina": [f"d{i}" for i in range(1, 6)],
    "megasena": [f"d{i}" for i in range(1, 7)],
    "maismilionaria": [f"d{i}" for i in range(1, 7)],
    "duplasena": [f"s1_d{i}" for i in range(1, 7)],
    "timemania": [f"d{i}" for i in range(1, 11)],
    "supersete": [f"coluna_{i}" for i in range(1, 8)],
}

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

COLUNAS = (
    ("conc", "Conc.", "C08B00", True),
    ("data", "Data", "996E00", False),
    ("sorteio", "Sorteio", "664A00", False),
    ("pares", "Pares", "28A745", False),
    ("impares", "Ímpares", "17A2B8", False),
    ("repetidos", "Repetidos", "9B59B6", False),
    ("sequencias", "Sequências", "4ADE80", False),
    ("finais", "Finais Iguais", "FFC107", False),
    ("diagonais", "Diagonais", "1E4B7B", False),
)

_locks_guard = threading.Lock()
_file_locks: Dict[str, threading.Lock] = {}
_geracao_consolidada = threading.Lock()


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def raiz_apostas() -> str:
    return os.path.join(_repo_root(), PASTA_PUBLICA)


def _lock_for(path: str) -> threading.Lock:
    chave = os.path.normcase(os.path.abspath(path))
    with _locks_guard:
        lk = _file_locks.get(chave)
        if lk is None:
            lk = threading.Lock()
            _file_locks[chave] = lk
        return lk


def _destino_permitido(destino: str) -> str:
    root = os.path.normcase(os.path.abspath(raiz_apostas()))
    dest = os.path.abspath(destino)
    dest_cmp = os.path.normcase(dest)
    if dest_cmp != root and not dest_cmp.startswith(root + os.sep):
        raise ValueError("destino invalido")
    nome = os.path.basename(dest)
    if not _NOME_OK.match(nome):
        raise ValueError("nome de arquivo invalido")
    return dest


def gravar_atomico(destino: str, conteudo: bytes) -> str:
    """Grava o xlsx pronto. Um arquivo temporário não fica com nome de planilha."""
    destino = _destino_permitido(destino)
    pasta = os.path.dirname(destino)
    os.makedirs(pasta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".estatisticas-", suffix=".tmp", dir=pasta)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(conteudo)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, destino)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise
    return destino


def slug_pasta(modality_key: str) -> str:
    from central_conferencias.config import CONF

    chave = (modality_key or "").strip().lower()
    conf_key = _ALIAS_CONF.get(chave, chave)
    cfg = CONF.get(conf_key) or {}
    slug = str(cfg.get("pasta_apostas") or "").strip().lower()
    if not _SLUG_OK.match(slug):
        raise ValueError("pasta de modalidade invalida")
    return slug


def nome_armazenado(limite: int = 0, ordem: str = "desc", base: str = "geral") -> str:
    partes = ["Estatisticas_Basicas"]
    if int(limite or 0) > 0:
        partes.append(f"ultimos_{int(limite)}")
    if (ordem or "desc") == "asc":
        partes.append("asc")
    if (base or "geral") != "geral":
        partes.append(str(base))
    nome = "_".join(partes) + ".xlsx"
    if not _NOME_OK.match(nome):
        raise ValueError("nome de arquivo invalido")
    return nome


def caminho_exibicao(
    modality_key: str,
    *,
    limite: int = 0,
    ordem: str = "desc",
    base: str = "geral",
) -> str:
    """Caminho relativo, sem unidade de disco."""
    return f"{PASTA_PUBLICA}/{slug_pasta(modality_key)}/{nome_armazenado(limite, ordem, base)}"


def caminho_modalidade_disco(
    modality_key: str,
    *,
    limite: int = 0,
    ordem: str = "desc",
    base: str = "geral",
) -> str:
    return os.path.join(
        raiz_apostas(),
        slug_pasta(modality_key),
        nome_armazenado(limite, ordem, base),
    )


def caminho_consolidado_exibicao() -> str:
    return f"{PASTA_PUBLICA}/{ARQUIVO_CONSOLIDADO}"


def caminho_consolidado_disco() -> str:
    return os.path.join(raiz_apostas(), ARQUIVO_CONSOLIDADO)


def normalizar_consulta(ordem: str, limite: int, base: str) -> Tuple[str, int, str]:
    ordem_n = (ordem or "desc").strip().lower()
    if ordem_n not in ("asc", "desc"):
        ordem_n = "desc"
    base_n = (base or "geral").strip().lower()
    if base_n not in ("geral", "vencedores", "acumulados"):
        base_n = "geral"
    try:
        lim = int(limite or 0)
    except (TypeError, ValueError):
        lim = 0
    if lim < 0:
        lim = 0
    if lim > 10000:
        lim = 10000
    return ordem_n, lim, base_n


def nome_arquivo_download(nome: str) -> str:
    base = unicodedata.normalize("NFD", str(nome or "Modalidade"))
    base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
    base = base.replace("+", "Mais ")
    base = re.sub(r"[^\w\s-]", "", base)
    base = re.sub(r"[\s-]+", "_", base).strip("_") or "Modalidade"
    return f"{base}_Estatisticas_Basicas.xlsx"


def nome_planilha(nome: str, usados: set) -> str:
    limpo = _PLANILHA_INVALIDA.sub(" ", str(nome or "Modalidade"))
    limpo = re.sub(r"\s+", " ", limpo).strip() or "Modalidade"
    limpo = limpo[:31]
    candidato = limpo
    n = 2
    while candidato.casefold() in usados:
        sufixo = f" {n}"
        candidato = limpo[: 31 - len(sufixo)].rstrip() + sufixo
        n += 1
    usados.add(candidato.casefold())
    return candidato


def _fmt(n: int, pad: int) -> str:
    return str(int(n)).zfill(max(1, int(pad)))


def _nums(arr: Optional[Sequence[Any]], pad: int) -> str:
    lista: List[int] = []
    for item in arr or []:
        try:
            lista.append(int(item))
        except (TypeError, ValueError):
            continue
    if not lista:
        return "—"
    return " ".join(_fmt(n, pad) for n in lista)


def _celula_grupo(chave: str, bloco: Optional[dict], pad: int) -> str:
    bloco = bloco or {}
    if chave in ("sequencias", "finais"):
        detalhe = bloco.get("detalhe") or {}
        grupos = detalhe.get("grupos") or []
        if not grupos:
            return "—"
        sep = "-" if chave == "sequencias" else ","
        partes: List[str] = []
        for grupo in grupos:
            nums = []
            for item in grupo or []:
                try:
                    nums.append(_fmt(int(item), pad))
                except (TypeError, ValueError):
                    continue
            if nums:
                partes.append(sep.join(nums))
        return " · ".join(partes) if partes else "—"
    if chave == "diagonais":
        return _celula_diagonais(bloco, pad)
    return _nums(bloco.get("dezenas"), pad)


def _celula_diagonais(bloco: Optional[dict], pad: int) -> str:
    detalhe = (bloco or {}).get("detalhe") or {}
    partes: List[str] = []
    for grupo in detalhe.get("grupos") or []:
        if isinstance(grupo, dict):
            bruto = grupo.get("nums") or []
            sym = str(grupo.get("dir_sym") or "").strip()
        else:
            bruto = grupo
            sym = ""
        nums = []
        for item in bruto:
            try:
                nums.append(_fmt(int(item), pad))
            except (TypeError, ValueError):
                continue
        if not nums:
            continue
        texto = "-".join(nums)
        partes.append(f"{sym} | {texto}".strip() if sym else texto)
    return " · ".join(partes) if partes else "—"


def valor_data(texto: Any) -> Any:
    s = str(texto or "").strip()
    if not s or s == "—":
        return "—"
    bruto = (
        (_DATA_BR, (3, 2, 1)),
        (_DATA_ISO, (1, 2, 3)),
    )
    for regex, ordem in bruto:
        m = regex.match(s)
        if not m:
            continue
        ano = int(m.group(ordem[0]))
        mes = int(m.group(ordem[1]))
        dia = int(m.group(ordem[2]))
        try:
            return date(ano, mes, dia)
        except ValueError:
            return s
    return s


def linha_valores(linha: dict, pad: int) -> List[Any]:
    concurso = linha.get("concurso")
    try:
        conc: Any = int(concurso)
    except (TypeError, ValueError):
        conc = concurso if concurso not in (None, "") else "—"
    return [
        conc,
        valor_data(linha.get("data")),
        _nums(linha.get("numeros"), pad),
        _celula_grupo("pares", linha.get("pares"), pad),
        _celula_grupo("impares", linha.get("impares"), pad),
        _celula_grupo("repetidos", linha.get("repetidos"), pad),
        _celula_grupo("sequencias", linha.get("sequencias"), pad),
        _celula_grupo("finais", linha.get("finais"), pad),
        _celula_grupo("diagonais", linha.get("diagonais"), pad),
    ]


def _hex_rgb(cor: str) -> Tuple[int, int, int]:
    h = cor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _texto_sobre(cor: str) -> str:
    r, g, b = _hex_rgb(cor)
    y = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "1A0A00" if y > 0.62 else "FFFFFF"


def _xml(texto: Any) -> str:
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _coluna(n: int) -> str:
    letras = ""
    while n:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _celula_xml(ref: str, valor: Any, estilo: int = 0, estilo_data: int = 0) -> str:
    if isinstance(valor, datetime):
        valor = valor.date()
    if isinstance(valor, date):
        serial = (valor - date(1899, 12, 30)).days
        marca = f' s="{estilo_data}"' if estilo_data else ""
        return f'<c r="{ref}"{marca}><v>{serial}</v></c>'
    marca = f' s="{estilo}"' if estilo else ""
    if isinstance(valor, int) and not isinstance(valor, bool):
        return f'<c r="{ref}"{marca}><v>{valor}</v></c>'
    texto = _xml(valor)
    espaco = ' xml:space="preserve"' if texto[:1].isspace() or texto[-1:].isspace() else ""
    return f'<c r="{ref}"{marca} t="inlineStr"><is><t{espaco}>{texto}</t></is></c>'


def _planilha_xml(
    linhas: Sequence[Sequence[Any]],
    larguras: Sequence[float],
    estilos_cab: Sequence[int],
    estilo_data: int,
) -> str:
    ncol = max((len(linha) for linha in linhas), default=1)
    nlin = max(1, len(linhas))
    ultima = _coluna(ncol)
    cols = "".join(
        f'<col min="{i}" max="{i}" width="{largura:.2f}" customWidth="1"/>'
        for i, largura in enumerate(larguras, start=1)
    )
    rows = []
    for r, linha in enumerate(linhas, start=1):
        cells = []
        for c, valor in enumerate(linha, start=1):
            if valor is None or valor == "":
                continue
            estilo = estilos_cab[c - 1] if r == 1 and c <= len(estilos_cab) else 0
            cells.append(_celula_xml(f"{_coluna(c)}{r}", valor, estilo, estilo_data))
        rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    ref = f"A1:{ultima}{nlin}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{ref}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<cols>{cols}</cols>'
        f'<sheetData>{"".join(rows)}</sheetData>'
        f'<autoFilter ref="{ref}"/>'
        '</worksheet>'
    )


def _estilos_xml(cores: Dict[str, str]) -> Tuple[str, Dict[str, int], int]:
    fills = [
        '<fill><patternFill patternType="none"/></fill>',
        '<fill><patternFill patternType="gray125"/></fill>',
    ]
    fonts = [
        '<font><sz val="11"/><name val="Calibri"/></font>',
        '<font><b/><sz val="11"/><color rgb="FF1A0A00"/><name val="Calibri"/></font>',
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>',
    ]
    xfs = ['<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>']
    indice: Dict[str, int] = {}
    for cor, fonte in cores.items():
        fills.append(
            '<fill><patternFill patternType="solid">'
            f'<fgColor rgb="FF{cor}"/>'
            '</patternFill></fill>'
        )
        font_id = 2 if fonte.upper() == "FFFFFF" else 1
        xfs.append(
            f'<xf numFmtId="0" fontId="{font_id}" fillId="{len(fills) - 1}" '
            'borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">'
            '<alignment horizontal="center" vertical="center"/>'
            '</xf>'
        )
        indice[cor] = len(xfs) - 1
    xfs.append(
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    )
    estilo_data = len(xfs) - 1
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="1"><numFmt numFmtId="164" formatCode="DD/MM/YYYY"/></numFmts>'
        f'<fonts count="{len(fonts)}">{"".join(fonts)}</fonts>'
        f'<fills count="{len(fills)}">{"".join(fills)}</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )
    return xml, indice, estilo_data


def _xlsx_bytes(abas: Sequence[dict]) -> bytes:
    cores: Dict[str, str] = {}
    for aba in abas:
        for cor in aba.get("cores") or []:
            if cor not in cores:
                cores[cor] = _texto_sobre(cor)
    estilos, indice, estilo_data = _estilos_xml(cores)
    partes = []
    for aba in abas:
        estilos_cab = [indice.get(cor, 0) for cor in (aba.get("cores") or [])]
        partes.append((
            aba["nome"],
            _planilha_xml(aba["linhas"], aba["larguras"], estilos_cab, estilo_data),
        ))
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as pacote:
        pacote.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(partes) + 1)
            )
            + '</Types>',
        )
        pacote.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        pacote.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(partes) + 1)
            )
            + f'<Relationship Id="rId{len(partes) + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            '</Relationships>',
        )
        pacote.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            + "".join(
                f'<sheet name="{_xml(nome)}" sheetId="{i}" r:id="rId{i}"/>'
                for i, (nome, _xml_aba) in enumerate(partes, start=1)
            )
            + '</sheets></workbook>',
        )
        pacote.writestr("xl/styles.xml", estilos)
        for i, (_nome, xml_aba) in enumerate(partes, start=1):
            pacote.writestr(f"xl/worksheets/sheet{i}.xml", xml_aba)
    return bio.getvalue()


def _aba_basicos(titulo: str, linhas: Sequence[dict], pad: int) -> dict:
    cores = [fundo for _chave, _nome, fundo, _negrito in COLUNAS]
    cab = [nome for _chave, nome, _fundo, _negrito in COLUNAS]
    larguras = [float(len(nome)) for nome in cab]
    corpo = [cab]
    for linha in linhas:
        valores = linha_valores(linha, pad)
        for i, valor in enumerate(valores):
            tamanho = len(str(valor))
            if tamanho > larguras[i]:
                larguras[i] = float(tamanho)
        corpo.append(valores)
    return {
        "nome": titulo,
        "linhas": corpo,
        "larguras": [min(62.0, max(12.0, largura + 2)) for largura in larguras],
        "cores": cores,
    }


def bytes_modalidade(nome: str, linhas: Sequence[dict], pad: int) -> bytes:
    return _xlsx_bytes([_aba_basicos(nome_planilha(nome, set()), linhas, pad)])


def bytes_consolidado(folhas: Sequence[dict], pendencias: Sequence[dict]) -> bytes:
    """Um único arquivo. Cada modalidade fica numa aba."""
    usados: set = set()
    abas = []
    if pendencias:
        linhas = [("Modalidade", "Situação")]
        for item in pendencias:
            linhas.append((
                str(item.get("nome") or "Modalidade"),
                str(item.get("situacao") or "Dados indisponíveis no momento."),
            ))
        abas.append({
            "nome": nome_planilha("Pendências", usados),
            "linhas": linhas,
            "larguras": [28.0, 42.0],
            "cores": ["F4E4B3", "F4E4B3"],
        })
    for folha in folhas:
        titulo = nome_planilha(str(folha.get("nome") or "Modalidade"), usados)
        pad = int(folha.get("pad") or 2)
        abas.append(_aba_basicos(titulo, folha.get("linhas") or [], pad))
    if not abas:
        abas.append({
            "nome": "Pendências",
            "linhas": [("Modalidade", "Situação")],
            "larguras": [28.0, 42.0],
            "cores": ["F4E4B3", "F4E4B3"],
        })
    return _xlsx_bytes(abas)


def preparar_download_modalidade(
    modality_key: str,
    *,
    ordem: str = "desc",
    limite: int = 0,
    base: str = "geral",
) -> Dict[str, Any]:
    from analise_escolha_visual.service import AnaliseEscolhaVisualService

    ordem_n, limite_n, base_n = normalizar_consulta(ordem, limite, base)
    out = AnaliseEscolhaVisualService.enriquecimento(
        modality_key,
        ordem=ordem_n,
        limite=limite_n,
        base_estatistica=base_n,
    )
    if not out.get("sucesso"):
        log.warning("Exportação de %s recusada.", modality_key)
        return {
            "ok": False,
            "vazio": False,
            "mensagem": "Não foi possível preparar as estatísticas desta modalidade.",
        }
    linhas = out.get("linhas_basicas") or []
    if not linhas:
        return {
            "ok": False,
            "vazio": True,
            "mensagem": "Não há sorteios para exportar.",
        }
    nome = str(out.get("modality_nome") or modality_key)
    try:
        pad = int(out.get("pad_width") or 2)
    except (TypeError, ValueError):
        pad = 2
    conteudo = bytes_modalidade(nome, linhas, pad)
    destino = caminho_modalidade_disco(
        modality_key, limite=limite_n, ordem=ordem_n, base=base_n,
    )
    aviso = ""
    try:
        with _lock_for(destino):
            gravar_atomico(destino, conteudo)
    except Exception:
        log.exception("Falha ao gravar o Excel de %s.", modality_key)
        aviso = "O download foi gerado, mas a cópia no acervo não pôde ser gravada."
    return {
        "ok": True,
        "conteudo": conteudo,
        "download_name": nome_arquivo_download(nome),
        "mensagem": aviso,
        "caminho": caminho_exibicao(
            modality_key, limite=limite_n, ordem=ordem_n, base=base_n,
        ),
    }


def modalidades_consolidacao() -> List[dict]:
    from analise_estudos.specs import tem_analise_estudos
    from configuracoes.config import MODALITIES

    vistos = set()
    chaves: List[str] = []
    for key in ORDEM_MODALIDADES:
        if key in MODALITIES and tem_analise_estudos(key):
            chaves.append(key)
            vistos.add(key)
    for key in MODALITIES:
        if key not in vistos and tem_analise_estudos(key):
            chaves.append(key)
    saida = []
    for key in chaves:
        meta = MODALITIES[key]
        saida.append({
            "key": key,
            "porta": int(meta["porta"]),
            "nome": meta.get("nome") or key,
        })
    return saida


def _numeros_da_linha(key: str, valores: Sequence[Any]) -> List[int]:
    nums: List[int] = []
    for valor in valores:
        if valor is None:
            continue
        try:
            n = int(valor)
        except (TypeError, ValueError):
            continue
        if key == "timemania" and not (1 <= n <= 80):
            continue
        nums.append(n)
    return nums


def _folha_do_banco(key: str, nome: str) -> Optional[dict]:
    """Mesmo motor da seção 2, lendo o banco da modalidade. Um arquivo, várias abas."""
    from analise_escolha_visual.enriquecimento.motor import linhas_basicas
    from analise_estudos.specs import get_estudos_config
    from analises_gerais.registry import SPECS_BY_KEY

    spec = SPECS_BY_KEY.get(key)
    cols = _COLUNAS_ORDEM.get(key)
    if spec is None or not cols:
        return None
    cfg = get_estudos_config(key)
    path = os.path.join(_repo_root(), spec.app_dir, "instance", spec.db_filename)
    if not os.path.isfile(path) and key == "diadesorte":
        legado = os.path.join(
            _repo_root(),
            "AnalisePorPosicao---DiaDeSorte-Only",
            "instance",
            spec.db_filename,
        )
        if os.path.isfile(legado):
            path = legado
    if not os.path.isfile(path):
        log.warning("Banco ausente para %s.", key)
        return None
    sql = (
        f"SELECT concurso, data, {', '.join(cols)} "
        f"FROM {spec.table} ORDER BY concurso DESC"
    )
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA query_only = ON")
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    minimo = 7 if key == "timemania" else int(spec.sorteadas)
    sorteios: List[dict] = []
    for row in rows:
        nums = _numeros_da_linha(key, row[2:])
        if len(nums) < minimo:
            continue
        sorteios.append({
            "concurso": int(row[0]),
            "data": "" if row[1] is None else str(row[1]),
            "numeros": nums,
        })
    linhas = linhas_basicas(
        sorteios,
        ordem="desc",
        dmin=int(cfg.get("dezena_min") or 1),
        dmax=int(cfg.get("dezena_max") or 31),
        cols=int(cfg.get("volante_cols") or 10),
        com_diagonais=int(cfg.get("volante_rows") or 1) > 1,
    )
    if not linhas:
        return None
    try:
        pad = int(cfg.get("pad_width") or 2)
    except (TypeError, ValueError):
        pad = 2
    return {
        "key": key,
        "nome": str(cfg.get("nome") or nome or key),
        "linhas": linhas,
        "pad": pad,
    }


def _buscar_local(key: str, porta: int, nome: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        folha = _folha_do_banco(key, nome)
    except Exception:
        log.exception("Leitura local das estatísticas de %s falhou.", key)
        folha = None
    if folha:
        return folha, None
    return _buscar_http(key, porta, nome)


def _buscar_http(key: str, porta: int, nome: str) -> Tuple[Optional[dict], Optional[str]]:
    # urllib, e não requests: o servidor de desenvolvimento corta respostas
    # grandes no meio da leitura em blocos.
    qs = urlencode({"ordem": "desc", "limite": "0", "base": "geral"})
    url = (
        f"http://127.0.0.1:{int(porta)}"
        f"/analise/api/escolha-visual/enriquecimento?{qs}"
    )
    data = None
    for tentativa in (1, 2, 3):
        try:
            with urlopen(url, timeout=180) as resp:
                bruto = resp.read()
            data = json.loads(bruto.decode("utf-8"))
            break
        except Exception:
            if tentativa < 3:
                log.warning("Releitura das estatísticas básicas de %s.", key)
                time.sleep(1.5)
                continue
            log.exception("Falha ao ler estatísticas básicas de %s.", key)
            return None, "Dados indisponíveis no momento."
    if not isinstance(data, dict) or not data.get("sucesso"):
        log.warning("Estatísticas básicas de %s sem sucesso.", key)
        return None, "Dados indisponíveis no momento."
    linhas = data.get("linhas_basicas") or []
    if not linhas:
        log.warning("Estatísticas básicas de %s sem sorteios.", key)
        return None, "Sem sorteios para exportar."
    try:
        pad = int(data.get("pad_width") or 2)
    except (TypeError, ValueError):
        pad = 2
    return {
        "key": key,
        "nome": str(data.get("modality_nome") or nome or key),
        "linhas": linhas,
        "pad": pad,
    }, None


def gerar_consolidado(
    buscar: Optional[Callable[[str, int, str], Tuple[Optional[dict], Optional[str]]]] = None,
) -> Dict[str, Any]:
    """Uma geração por vez. A segunda chamada não mistura arquivos no meio da gravação."""
    if not _geracao_consolidada.acquire(blocking=False):
        return {
            "ok": False,
            "conteudo": None,
            "mensagem": "Já existe uma geração em andamento. Aguarde alguns instantes e tente novamente.",
            "incluidas": [],
            "pendencias": [],
        }
    try:
        return _montar_consolidado(buscar)
    finally:
        _geracao_consolidada.release()


def _montar_consolidado(
    buscar: Optional[Callable[[str, int, str], Tuple[Optional[dict], Optional[str]]]] = None,
) -> Dict[str, Any]:
    buscar_fn = buscar or _buscar_local
    mods = modalidades_consolidacao()
    if not mods:
        return {
            "ok": False,
            "conteudo": None,
            "mensagem": "Não há modalidades disponíveis para exportar.",
            "incluidas": [],
            "pendencias": [],
        }

    resultados: Dict[str, Tuple[Optional[dict], str, str]] = {}
    # Uma modalidade por vez. O servidor de cada app é single-thread e
    # corta a resposta quando várias leituras grandes acontecem juntas.
    with ThreadPoolExecutor(max_workers=1) as pool:
        futuros = {
            pool.submit(buscar_fn, m["key"], m["porta"], m["nome"]): m
            for m in mods
        }
        for fut, meta in futuros.items():
            try:
                folha, situacao = fut.result()
            except Exception:
                log.exception("Falha inesperada ao consolidar %s.", meta["key"])
                folha, situacao = None, "Dados indisponíveis no momento."
            resultados[meta["key"]] = (
                folha,
                situacao or "Dados indisponíveis no momento.",
                meta["nome"],
            )

    folhas: List[dict] = []
    pendencias: List[dict] = []
    for meta in mods:
        folha, situacao, nome = resultados[meta["key"]]
        if folha and folha.get("linhas"):
            folhas.append(folha)
        else:
            pendencias.append({"nome": nome, "situacao": situacao})

    if not folhas:
        log.warning(
            "Consolidação sem planilhas. Pendências: %s.",
            ", ".join(p["nome"] for p in pendencias),
        )
        return {
            "ok": False,
            "conteudo": None,
            "mensagem": "Não foi possível gerar o arquivo. Nenhuma modalidade pôde ser incluída.",
            "incluidas": [],
            "pendencias": pendencias,
        }

    conteudo = bytes_consolidado(folhas, pendencias)
    aviso = ""
    if pendencias:
        nomes = ", ".join(p["nome"] for p in pendencias)
        aviso = (
            "O arquivo foi gerado, mas estas modalidades não puderam ser incluídas: "
            f"{nomes}."
        )
        log.warning("Consolidação parcial. Fora do arquivo: %s.", nomes)
    destino = caminho_consolidado_disco()
    try:
        with _lock_for(destino):
            gravar_atomico(destino, conteudo)
    except Exception:
        log.exception("Falha ao gravar o Excel consolidado.")
        extra = "O download foi gerado, mas a cópia no acervo não pôde ser gravada."
        aviso = f"{aviso} {extra}".strip()
    return {
        "ok": True,
        "conteudo": conteudo,
        "mensagem": aviso,
        "incluidas": [str(f.get("nome") or "") for f in folhas],
        "pendencias": pendencias,
    }


def iter_nomes_planilha(nomes: Iterable[str]) -> List[str]:
    usados: set = set()
    return [nome_planilha(nome, usados) for nome in nomes]
