# -*- coding: utf-8 -*-
"""Lote de apostas preso a um concurso fixo — Comparador de Apostas."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from analise_estudos.specs import get_estudos_config
from models.shared import db

LIMITE_APOSTAS = 200
PAINEIS = (
    ("escolha", "1 Escolha Visual"),
    ("checagem", "2 Checagem"),
    ("manual", "3 Manual"),
    ("gaps", "4 Gaps"),
)


class ComparadorLoteConcurso(db.Model):
    """Um concurso, um lote. Gravar de novo substitui só esse número."""

    __tablename__ = "comparador_lotes_concurso"

    concurso = db.Column(db.Integer, primary_key=True)
    apostas_json = db.Column(db.Text, nullable=False, default="[]")
    quantidade = db.Column(db.Integer, nullable=False, default=0)
    atualizado_em = db.Column(db.String(40), nullable=False, default="")

    def blocos(self) -> Dict[str, List[List[int]]]:
        vazio = {chave: [] for chave, _nome in PAINEIS}
        try:
            bruto = json.loads(self.apostas_json or "{}")
        except json.JSONDecodeError:
            return vazio
        if isinstance(bruto, list):
            vazio["gaps"] = _linhas_int(bruto)
            return vazio
        if not isinstance(bruto, dict):
            return vazio
        for chave, _nome in PAINEIS:
            vazio[chave] = _linhas_int(bruto.get(chave) or [])
        return vazio

    def contagens(self) -> Dict[str, int]:
        return {chave: len(linhas) for chave, linhas in self.blocos().items()}


def _linhas_int(bruto: Any) -> List[List[int]]:
    out: List[List[int]] = []
    if not isinstance(bruto, list):
        return out
    for linha in bruto:
        if isinstance(linha, list):
            out.append([int(n) for n in linha])
    return out


def garantir_tabela() -> None:
    ComparadorLoteConcurso.__table__.create(db.engine, checkfirst=True)


def _modelo_sorteio(modality_key: str):
    est = get_estudos_config(modality_key)
    mod = __import__(est["model_module"], fromlist=[est["model_class"]])
    return getattr(mod, est["model_class"])


def _ultimo(modelo) -> Any:
    return db.session.query(modelo).order_by(modelo.concurso.desc()).first()


def _seguinte(modality_key: str) -> Tuple[Optional[int], Optional[int]]:
    ultimo = _ultimo(_modelo_sorteio(modality_key))
    if ultimo is None:
        return None, None
    numero = int(ultimo.concurso)
    return numero, numero + 1


def _limites(modality_key: str) -> Tuple[int, int, int]:
    est = get_estudos_config(modality_key)
    return int(est["dezena_min"]), int(est["dezena_max"]), int(est["sorteadas"])


def normalizar_apostas(
    texto: str,
    dezena_min: int,
    dezena_max: int,
    pick: int,
    limite: int = LIMITE_APOSTAS,
) -> Tuple[List[List[int]], List[str]]:
    apostas: List[List[int]] = []
    erros: List[str] = []
    for i, linha in enumerate(str(texto or "").splitlines(), 1):
        if not linha.strip():
            continue
        if len(apostas) >= limite:
            erros.append(f"O lote aceita no máximo {limite} apostas.")
            break
        nums = [
            int(m)
            for m in re.findall(r"\d{1,2}", linha)
            if dezena_min <= int(m) <= dezena_max
        ]
        if len(nums) != len(set(nums)):
            erros.append(f"Linha {i}: há dezena repetida.")
            continue
        if len(nums) != pick:
            erros.append(
                f"Linha {i}: precisa de {pick} dezenas entre {dezena_min:02d} e {dezena_max:02d}."
            )
            continue
        apostas.append(nums)
    return apostas, erros


def _listar() -> List[Dict[str, Any]]:
    rows = (
        db.session.query(ComparadorLoteConcurso)
        .order_by(ComparadorLoteConcurso.concurso.desc())
        .all()
    )
    return [
        {
            "concurso": int(row.concurso),
            "quantidade": int(row.quantidade or 0),
            "atualizado_em": row.atualizado_em or "",
            "paineis": row.contagens(),
        }
        for row in rows
    ]


def estado_lotes(modality_key: str) -> Dict[str, Any]:
    garantir_tabela()
    ultimo, seguinte = _seguinte(modality_key)
    if seguinte is None:
        return {"sucesso": False, "erro": "Nenhum concurso na base."}
    return {
        "sucesso": True,
        "ultimo": ultimo,
        "seguinte": seguinte,
        "lotes": _listar(),
    }


def _textos_paineis(texto: str, paineis: Any) -> Dict[str, str]:
    if isinstance(paineis, dict):
        return {chave: str(paineis.get(chave) or "") for chave, _nome in PAINEIS}
    return {chave: (texto if chave == "gaps" else "") for chave, _nome in PAINEIS}


def guardar_lote(modality_key: str, texto: str, concurso: Any, paineis: Any = None) -> Dict[str, Any]:
    garantir_tabela()
    ultimo, seguinte = _seguinte(modality_key)
    if seguinte is None:
        return {"sucesso": False, "erro": "Nenhum concurso na base."}
    try:
        alvo = int(concurso)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Informe o concurso."}
    if alvo < 1:
        return {"sucesso": False, "erro": "Informe o concurso.", "ultimo": ultimo, "seguinte": seguinte}
    dmin, dmax, pick = _limites(modality_key)
    blocos: Dict[str, List[List[int]]] = {}
    erros: List[str] = []
    for chave, nome in PAINEIS:
        apostas, erros_painel = normalizar_apostas(_textos_paineis(texto, paineis)[chave], dmin, dmax, pick)
        if erros_painel:
            erros.append(nome + ": " + " ".join(erros_painel))
            continue
        blocos[chave] = apostas
    if erros:
        return {"sucesso": False, "erro": " ".join(erros), "seguinte": seguinte}
    if not any(blocos.values()):
        return {
            "sucesso": False,
            "erro": "Nenhuma aposta nos comparadores 1, 2, 3 e 4.",
            "seguinte": seguinte,
        }
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    row = db.session.get(ComparadorLoteConcurso, alvo)
    if row is None:
        row = ComparadorLoteConcurso(concurso=alvo)
        db.session.add(row)
    row.apostas_json = json.dumps(blocos, separators=(",", ":"))
    row.quantidade = sum(len(linhas) for linhas in blocos.values())
    row.atualizado_em = agora
    db.session.commit()
    return {
        "sucesso": True,
        "concurso": alvo,
        "quantidade": int(row.quantidade or 0),
        "paineis": {chave: len(linhas) for chave, linhas in blocos.items()},
        "atualizado_em": agora,
        "ultimo": ultimo,
        "seguinte": seguinte,
        "lotes": _listar(),
    }


def _ordem_sorteio(sorteio: Any, pick: int) -> List[int]:
    if hasattr(sorteio, "dezenas_ordem_lista"):
        ordem = [int(n) for n in sorteio.dezenas_ordem_lista()]
        if len(ordem) == pick:
            return ordem
    nums: List[int] = []
    for i in range(1, pick + 1):
        if hasattr(sorteio, f"d{i}"):
            nums.append(int(getattr(sorteio, f"d{i}")))
    if len(nums) == pick:
        return nums
    if hasattr(sorteio, "dezenas_lista"):
        return [int(n) for n in sorteio.dezenas_lista()]
    return nums


def _mes(sorteio: Any) -> Dict[str, str]:
    abrev = ""
    if hasattr(sorteio, "mes_abrev"):
        try:
            abrev = str(sorteio.mes_abrev() or "")
        except Exception:
            abrev = ""
    nome = str(getattr(sorteio, "mes_nome", "") or "")
    return {"mes_abrev": abrev, "mes_nome": nome}


def ler_lote(modality_key: str, concurso: Any) -> Dict[str, Any]:
    garantir_tabela()
    try:
        alvo = int(concurso)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Concurso inválido."}
    row = db.session.get(ComparadorLoteConcurso, alvo)
    blocos = row.blocos() if row is not None else {}
    if row is None or not any(blocos.values()):
        return {"sucesso": False, "erro": f"Nada guardado para o concurso {alvo}.", "concurso": alvo}
    paineis = [
        {
            "id": chave,
            "nome": nome,
            "quantidade": len(blocos[chave]),
            "linhas": blocos[chave],
        }
        for chave, nome in PAINEIS
    ]
    return {
        "sucesso": True,
        "concurso": alvo,
        "quantidade": int(row.quantidade or 0),
        "atualizado_em": row.atualizado_em or "",
        "paineis": paineis,
    }


def apagar_lote(modality_key: str, concurso: Any) -> Dict[str, Any]:
    garantir_tabela()
    ultimo, seguinte = _seguinte(modality_key)
    try:
        alvo = int(concurso)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Concurso inválido."}
    row = db.session.get(ComparadorLoteConcurso, alvo)
    if row is None:
        return {"sucesso": False, "erro": f"Nada guardado para o concurso {alvo}.", "concurso": alvo}
    db.session.delete(row)
    db.session.commit()
    return {
        "sucesso": True,
        "concurso": alvo,
        "ultimo": ultimo,
        "seguinte": seguinte,
        "lotes": _listar(),
    }


def conferir_lote(modality_key: str, concurso: Any) -> Dict[str, Any]:
    garantir_tabela()
    try:
        alvo = int(concurso)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "Concurso inválido."}
    row = db.session.get(ComparadorLoteConcurso, alvo)
    blocos = row.blocos() if row is not None else {}
    if row is None or not any(blocos.values()):
        return {
            "sucesso": False,
            "erro": f"Nada guardado para o concurso {alvo}.",
            "concurso": alvo,
        }
    modelo = _modelo_sorteio(modality_key)
    sorteio = db.session.get(modelo, alvo)
    if sorteio is None:
        return {
            "sucesso": True,
            "concurso": alvo,
            "saiu": False,
            "quantidade": int(row.quantidade or 0),
            "paineis": row.contagens(),
            "mensagem": f"O concurso {alvo} ainda não saiu. Os comparadores 1, 2, 3 e 4 continuam guardados neste número.",
        }
    _dmin, _dmax, pick = _limites(modality_key)
    ordem = _ordem_sorteio(sorteio, pick)
    oficiais = set(ordem)
    paineis_out = []
    for chave, nome in PAINEIS:
        linhas = []
        for aposta in blocos[chave]:
            acertadas = [n for n in aposta if n in oficiais]
            linhas.append({
                "ordem": aposta,
                "acertos": len(acertadas),
                "dezenas_acerto": acertadas,
            })
        paineis_out.append({
            "id": chave,
            "nome": nome,
            "quantidade": len(linhas),
            "linhas": linhas,
        })
    resultado = {
        "concurso": alvo,
        "data": str(getattr(sorteio, "data", "") or ""),
        "ordem": ordem,
        "classificado": sorted(ordem),
    }
    resultado.update(_mes(sorteio))
    return {
        "sucesso": True,
        "concurso": alvo,
        "saiu": True,
        "quantidade": int(row.quantidade or 0),
        "resultado": resultado,
        "paineis": paineis_out,
    }
