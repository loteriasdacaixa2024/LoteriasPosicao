"""
Conversor de apostas Mega-Sena: TXT ↔ JSON.
Aceita de 6 a 15 dezenas por aposta (volante 01–60).
"""
import json
import re
from typing import Dict, List

MIN_DEZENAS = 6
MAX_DEZENAS = 15
DEZENA_MIN = 1
DEZENA_MAX = 60


class ConversorApostasService:

    @staticmethod
    def extrair_numeros_linha(linha: str) -> List[int]:
        resultado = []
        for num_str in re.findall(r"\d+", linha):
            try:
                num = int(num_str)
                if DEZENA_MIN <= num <= DEZENA_MAX:
                    resultado.append(num)
            except ValueError:
                continue
        return resultado

    @staticmethod
    def texto_para_json(texto: str, concurso: int) -> Dict:
        linhas = texto.strip().split("\n")
        apostas = []
        numero_aposta = 1
        buffer: List[int] = []

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            numeros_linha = ConversorApostasService.extrair_numeros_linha(linha)
            if numeros_linha:
                buffer.extend(numeros_linha)

            while len(buffer) >= MIN_DEZENAS:
                qtd = min(len(buffer), MAX_DEZENAS)
                apostas.append({
                    "numero": numero_aposta,
                    "numeros": buffer[:qtd],
                })
                numero_aposta += 1
                buffer = buffer[qtd:]

        return {"concurso": concurso, "apostas": apostas}

    @staticmethod
    def json_para_texto(dados_json: Dict) -> str:
        linhas = []
        for aposta in dados_json.get("apostas", []):
            numeros = aposta.get("numeros", [])
            linhas.append(" ".join(f"{n:02d}" for n in numeros))
        return "\n".join(linhas)

    @staticmethod
    def _normalizar_aposta(aposta: Dict, idx: int) -> Dict:
        numeros = aposta.get("numeros", [])
        if isinstance(numeros, str):
            numeros = ConversorApostasService.extrair_numeros_linha(numeros)
        return {
            "numero": aposta.get("numero", idx),
            "numeros": numeros,
        }

    @staticmethod
    def normalizar_json(dados: Dict) -> Dict:
        """Remove campos de outras modalidades (ex.: mês do Dia de Sorte)."""
        apostas = []
        for i, aposta in enumerate(dados.get("apostas", []), 1):
            apostas.append(ConversorApostasService._normalizar_aposta(aposta, i))
        return {
            "concurso": int(dados.get("concurso", 0)),
            "apostas": apostas,
        }

    @staticmethod
    def validar_apostas(dados_json: Dict) -> Dict:
        erros = []

        if "concurso" not in dados_json:
            erros.append('Campo "concurso" obrigatório')

        if "apostas" not in dados_json:
            erros.append('Campo "apostas" obrigatório')
            return {"valido": False, "erros": erros, "total_apostas": 0}

        for idx, aposta in enumerate(dados_json["apostas"], 1):
            if "numeros" not in aposta:
                erros.append(f'Aposta {idx}: campo "numeros" obrigatório')
                continue

            numeros = aposta["numeros"]
            qtd = len(numeros)

            if qtd < MIN_DEZENAS or qtd > MAX_DEZENAS:
                erros.append(
                    f"Aposta {idx}: deve ter entre {MIN_DEZENAS} e {MAX_DEZENAS} "
                    f"dezenas (tem {qtd})"
                )

            for num in numeros:
                if not isinstance(num, int) or num < DEZENA_MIN or num > DEZENA_MAX:
                    erros.append(
                        f"Aposta {idx}: dezena {num} inválida "
                        f"(use {DEZENA_MIN:02d} a {DEZENA_MAX:02d})"
                    )
                    break

            if len(set(numeros)) != len(numeros):
                erros.append(f"Aposta {idx}: dezenas duplicadas")

        return {
            "valido": len(erros) == 0,
            "erros": erros,
            "total_apostas": len(dados_json.get("apostas", [])),
        }

    @staticmethod
    def processar_arquivo_upload(arquivo_conteudo: str, tipo_arquivo: str, concurso: int) -> Dict:
        try:
            if tipo_arquivo == "json":
                dados = ConversorApostasService.normalizar_json(
                    json.loads(arquivo_conteudo)
                )
                dados["concurso"] = concurso
            elif tipo_arquivo == "txt":
                dados = ConversorApostasService.texto_para_json(arquivo_conteudo, concurso)
            else:
                return {"sucesso": False, "erro": f"Tipo não suportado: {tipo_arquivo}"}

            validacao = ConversorApostasService.validar_apostas(dados)
            return {
                "sucesso": True,
                "dados": dados,
                "validacao": validacao,
                "tipo_origem": tipo_arquivo,
            }
        except json.JSONDecodeError as e:
            return {"sucesso": False, "erro": f"JSON inválido: {e}"}
        except Exception as e:
            return {"sucesso": False, "erro": f"Erro ao processar: {e}"}

    @staticmethod
    def formatar_json_download(dados: Dict) -> str:
        linhas = ["{\n", f'  "concurso": {dados["concurso"]},\n', '  "apostas": [\n']
        apostas = dados.get("apostas", [])
        for index, aposta in enumerate(apostas):
            nums = ", ".join(str(n) for n in aposta["numeros"])
            sufixo = "" if index == len(apostas) - 1 else ","
            linhas.append(
                f'    {{"numero": {aposta["numero"]}, "numeros": [{nums}]}}{sufixo}\n'
            )
        linhas.append("  ]\n}\n")
        return "".join(linhas)
