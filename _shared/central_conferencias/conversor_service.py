# -*- coding: utf-8 -*-
"""Conversor TXT ↔ JSON parametrizado por modalidade."""
import importlib
import json
import re
from typing import Dict, List

from .config import get_conf


class ConversorApostasService:
    def __init__(self, modality_key: str):
        self.cfg = get_conf(modality_key)
        self.min_d = self.cfg["pick_min"]
        self.max_d = self.cfg["pick_max"]
        self.dmin = self.cfg["dezena_min"]
        self.dmax = self.cfg["dezena_max"]

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

    def texto_para_json(self, texto: str, concurso: int) -> Dict:
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

    def json_para_texto(self, dados_json: Dict) -> str:
        linhas = []
        for aposta in dados_json.get("apostas", []):
            numeros = aposta.get("numeros", [])
            if self.cfg["key"] == "supersete":
                linhas.append(" ".join(str(n) for n in numeros))
            else:
                linhas.append(" ".join(f"{n:02d}" for n in numeros))
        return "\n".join(linhas)

    def _normalizar_aposta(self, aposta: Dict, idx: int) -> Dict:
        numeros = aposta.get("numeros", [])
        if isinstance(numeros, str):
            numeros = self.extrair_numeros_linha(numeros)
        return {"numero": aposta.get("numero", idx), "numeros": numeros}

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
        return {"valido": len(erros) == 0, "erros": erros, "avisos": avisos}

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
        return json.dumps(self.normalizar_json(dados), ensure_ascii=False, indent=2)
