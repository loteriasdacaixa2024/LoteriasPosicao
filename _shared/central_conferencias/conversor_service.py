# -*- coding: utf-8 -*-
"""Conversor TXT ↔ JSON parametrizado por modalidade."""
import json
import re
from typing import Dict, List, Optional

from .config import get_conf

MESES_ABREV = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

_MES_LOOKUP = {
    "1": "Jan", "jan": "Jan", "janeiro": "Jan",
    "2": "Fev", "fev": "Fev", "fevereiro": "Fev",
    "3": "Mar", "mar": "Mar", "marco": "Mar", "março": "Mar",
    "4": "Abr", "abr": "Abr", "abril": "Abr",
    "5": "Mai", "mai": "Mai", "maio": "Mai",
    "6": "Jun", "jun": "Jun", "junho": "Jun",
    "7": "Jul", "jul": "Jul", "julho": "Jul",
    "8": "Ago", "ago": "Ago", "agosto": "Ago",
    "9": "Set", "set": "Set", "setembro": "Set",
    "10": "Out", "out": "Out", "outubro": "Out",
    "11": "Nov", "nov": "Nov", "novembro": "Nov",
    "12": "Dez", "dez": "Dez", "dezembro": "Dez",
}


def normalizar_mes(valor) -> Optional[str]:
    """Converte nome, abreviação ou número (1–12) para abreviação canônica (Jan…Dez)."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, int):
        return MESES_ABREV.get(valor)
    key = str(valor).strip().lower().replace("ç", "c")
    if not key:
        return None
    if key in _MES_LOOKUP:
        return _MES_LOOKUP[key]
    if key[:3] in _MES_LOOKUP:
        return _MES_LOOKUP[key[:3]]
    return None


class ConversorApostasService:
    def __init__(self, modality_key: str):
        self.cfg = get_conf(modality_key)
        self.min_d = self.cfg["pick_min"]
        self.max_d = self.cfg["pick_max"]
        self.dmin = self.cfg["dezena_min"]
        self.dmax = self.cfg["dezena_max"]
        self.has_mes = bool(self.cfg.get("has_mes"))

    def extrair_numeros_linha(self, linha: str) -> List[int]:
        resultado = []
        for num_str in re.findall(r"\d+", linha):
            try:
                num = int(num_str)
                if self.dmin <= num <= self.dmax:
                    resultado.append(num)
            except ValueError:
                continue
        return resultado

    def extrair_mes_linha(self, linha: str) -> Optional[str]:
        for tok in re.findall(r"[A-Za-zÀ-ÿ]+", linha or ""):
            mes = normalizar_mes(tok)
            if mes:
                return mes
        return None

    def _aposta_com_mes(self, numero: int, numeros: List[int], mes: Optional[str]) -> Dict:
        item = {"numero": numero, "numeros": numeros}
        if mes:
            item["mes"] = mes
        return item

    def texto_para_json(self, texto: str, concurso: int) -> Dict:
        if self.has_mes:
            return self._texto_para_json_com_mes(texto, concurso)

        linhas = texto.strip().split("\n")
        apostas = []
        numero_aposta = 1
        buffer: List[int] = []

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            numeros_linha = self.extrair_numeros_linha(linha)
            if numeros_linha:
                buffer.extend(numeros_linha)
            while len(buffer) >= self.min_d:
                qtd = min(len(buffer), self.max_d)
                apostas.append({"numero": numero_aposta, "numeros": buffer[:qtd]})
                numero_aposta += 1
                buffer = buffer[qtd:]

        return {"concurso": concurso, "apostas": apostas}

    def _texto_para_json_com_mes(self, texto: str, concurso: int) -> Dict:
        """Uma linha = uma aposta; o mês (Out, Janeiro, …) fica no campo mes."""
        apostas = []
        numero_aposta = 1
        for linha in texto.strip().split("\n"):
            linha = linha.strip()
            if not linha:
                continue
            numeros = self.extrair_numeros_linha(linha)
            if not numeros:
                continue
            apostas.append(self._aposta_com_mes(
                numero_aposta, numeros, self.extrair_mes_linha(linha),
            ))
            numero_aposta += 1
        return {"concurso": concurso, "apostas": apostas}

    def json_para_texto(self, dados_json: Dict) -> str:
        linhas = []
        for aposta in dados_json.get("apostas", []):
            numeros = aposta.get("numeros", [])
            if self.cfg["key"] == "supersete":
                linha = " ".join(str(n) for n in numeros)
            else:
                linha = " ".join(f"{n:02d}" for n in numeros)
            mes = normalizar_mes(aposta.get("mes"))
            if mes:
                linha = f"{linha} {mes}"
            linhas.append(linha)
        return "\n".join(linhas)

    def _normalizar_aposta(self, aposta: Dict, idx: int) -> Dict:
        numeros = aposta.get("numeros", [])
        if isinstance(numeros, str):
            numeros = self.extrair_numeros_linha(numeros)
        return self._aposta_com_mes(
            aposta.get("numero", idx),
            numeros,
            normalizar_mes(aposta.get("mes")),
        )

    def normalizar_json(self, dados: Dict) -> Dict:
        apostas = []
        for i, aposta in enumerate(dados.get("apostas", []), 1):
            apostas.append(self._normalizar_aposta(aposta, i))
        return {"concurso": dados.get("concurso", 1), "apostas": apostas}

    def validar_apostas(self, dados: Dict) -> Dict:
        erros = []
        avisos = []
        apostas = dados.get("apostas", [])
        if not apostas:
            erros.append("Nenhuma aposta encontrada.")
        for ap in apostas:
            nums = ap.get("numeros", [])
            if len(nums) < self.min_d:
                erros.append(f"Aposta {ap.get('numero')}: mínimo {self.min_d} números.")
            if len(nums) > self.max_d:
                erros.append(f"Aposta {ap.get('numero')}: máximo {self.max_d} números.")
            for n in nums:
                if n < self.dmin or n > self.dmax:
                    erros.append(f"Aposta {ap.get('numero')}: número {n} fora do volante.")
            if self.has_mes and not ap.get("mes"):
                avisos.append(f"Aposta {ap.get('numero')}: mês não informado.")
        return {
            "valido": len(erros) == 0,
            "erros": erros,
            "avisos": avisos,
            "total_apostas": len(apostas),
        }

    def processar_arquivo_upload(self, conteudo: str, tipo: str, concurso: int) -> Dict:
        try:
            if tipo == "json":
                dados = json.loads(conteudo)
                dados = self.normalizar_json(dados)
            else:
                dados = self.texto_para_json(conteudo, concurso)
            validacao = self.validar_apostas(dados)
            return {"sucesso": True, "dados": dados, "validacao": validacao}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    def formatar_json_download(self, dados: Dict) -> str:
        dados = self.normalizar_json(dados)
        apostas = dados.get("apostas") or []
        linhas = [
            "{",
            f'  "concurso": {int(dados.get("concurso") or 1)},',
            '  "apostas": [',
        ]
        for i, a in enumerate(apostas):
            nums = ", ".join(str(n) for n in a.get("numeros", []))
            mes = a.get("mes")
            mes_part = f', "mes": "{mes}"' if mes else ""
            virg = "," if i < len(apostas) - 1 else ""
            linhas.append(
                f'    {{"numero": {a.get("numero")}, "numeros": [{nums}]{mes_part}}}{virg}'
            )
        linhas.extend(["  ]", "}"])
        return "\n".join(linhas)
