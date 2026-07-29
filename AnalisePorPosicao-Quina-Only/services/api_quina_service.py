import certifi
import requests
from typing import List, Dict, Any, Optional, Set

from models.shared import db
from models.sorteio_quina import SorteioQuina

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/quina/"


class ApiQuinaService:
    @staticmethod
    def get_headers():
        return {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    @staticmethod
    def _get(url: str, timeout: int = 30):
        kwargs = {
            "headers": ApiQuinaService.get_headers(),
            "timeout": timeout,
        }
        try:
            return requests.get(url, verify=certifi.where(), **kwargs)
        except requests.exceptions.SSLError:
            return requests.get(url, verify=False, **kwargs)

    @staticmethod
    def buscar_ultimo_concurso(timeout: int = 30) -> int:
        try:
            r = ApiQuinaService._get(BASE_URL, timeout=timeout)
            if r.status_code != 200:
                return 0
            try:
                data = r.json()
            except ValueError:
                return 0
            numero = data.get("numero") or data.get("numeroConcurso") or 0
            return int(numero)
        except Exception as e:
            print(f"[API Caixa] Erro ao buscar último concurso: {e}")
        return 0

    @staticmethod
    def buscar_concurso_especifico(numero: int) -> Optional[dict]:
        try:
            r = ApiQuinaService._get(f"{BASE_URL}{numero}")
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @staticmethod
    def _concursos_no_banco() -> Set[int]:
        rows = db.session.query(SorteioQuina.concurso).all()
        return {r[0] for r in rows}

    @staticmethod
    def status_banco() -> Dict[str, Any]:
        total = SorteioQuina.query.count()
        min_local = db.session.query(db.func.min(SorteioQuina.concurso)).scalar()
        max_local = db.session.query(db.func.max(SorteioQuina.concurso)).scalar()
        # Consulta rápida na API (só para status da página)
        ultimo_api = ApiQuinaService.buscar_ultimo_concurso(timeout=8)

        alvo = ultimo_api or max_local or 0
        faltantes = 0
        api_offline = ultimo_api == 0 and (max_local or 0) > 0

        if alvo:
            gravados_no_intervalo = (
                db.session.query(SorteioQuina.concurso)
                .filter(SorteioQuina.concurso >= 1, SorteioQuina.concurso <= alvo)
                .count()
            )
            faltantes = max(0, alvo - gravados_no_intervalo)

        completo = (
            faltantes == 0
            and total > 0
            and (min_local or 0) == 1
            and ultimo_api > 0
        )

        return {
            "total_registros": total,
            "concurso_minimo": min_local or 0,
            "concurso_maximo": max_local or 0,
            "ultimo_concurso_api": ultimo_api,
            "alvo_sincronizacao": alvo,
            "concursos_faltantes": faltantes,
            "api_offline": api_offline,
            "completo": completo,
            "precisa_sincronizar": faltantes > 0 or total == 0,
        }

    @staticmethod
    def _extrair_dezenas(dados: dict) -> Optional[List[int]]:
        dezenas_raw = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas")
        if dezenas_raw and len(dezenas_raw) == 5:
            return [int(d) for d in dezenas_raw]
        return None

    @staticmethod
    def _salvar_concurso(concurso: int, dados: dict) -> bool:
        dezenas = ApiQuinaService._extrair_dezenas(dados)
        if not dezenas:
            return False
        novo = SorteioQuina(
            concurso=concurso,
            data=dados.get("dataApuracao", "") or dados.get("data", ""),
            d1=dezenas[0],
            d2=dezenas[1],
            d3=dezenas[2],
            d4=dezenas[3],
            d5=dezenas[4],
        )
        db.session.merge(novo)
        return True

    @staticmethod
    def listar_faltantes(ate: Optional[int] = None) -> List[int]:
        ultimo = ate or ApiQuinaService.buscar_ultimo_concurso()
        if not ultimo:
            max_local = db.session.query(db.func.max(SorteioQuina.concurso)).scalar() or 0
            ultimo = max_local
        if not ultimo:
            return []
        presentes = ApiQuinaService._concursos_no_banco()
        return [i for i in range(1, ultimo + 1) if i not in presentes]

    @classmethod
    def sincronizar_banco(
        cls,
        modo: str = "completo",
        limite: int = 60,
        teto_concurso: Optional[int] = None,
    ) -> Dict[str, Any]:
        limite = max(1, min(int(limite or 60), 200))
        ultimo_oficial = teto_concurso or cls.buscar_ultimo_concurso()
        if not ultimo_oficial:
            return {
                "status": "error",
                "message": "Não foi possível consultar a API da Caixa. Verifique sua conexão.",
            }

        presentes = cls._concursos_no_banco()
        max_local = max(presentes) if presentes else 0

        if modo == "incremental":
            candidatos = list(range(max_local + 1, ultimo_oficial + 1))
        else:
            candidatos = [i for i in range(1, ultimo_oficial + 1) if i not in presentes]

        if not candidatos:
            st = cls.status_banco()
            return {
                "status": "info",
                "message": f"Base completa: {st['total_registros']} concursos (1 a {ultimo_oficial}).",
                "news": 0,
                "continuar": False,
                **st,
            }

        lote = candidatos[:limite]
        sucessos = 0
        falhas = 0

        for concurso in lote:
            print(f"[API Caixa] Quina {concurso}/{ultimo_oficial}...", end="", flush=True)
            dados = cls.buscar_concurso_especifico(concurso)
            if dados and cls._salvar_concurso(concurso, dados):
                sucessos += 1
                print(" [OK]")
            else:
                falhas += 1
                print(" [FALHOU]")

        db.session.commit()

        restantes = len(candidatos) - len(lote)
        st = cls.status_banco()

        if restantes > 0:
            msg = (
                f"{sucessos} concurso(s) importado(s) neste lote. "
                f"Faltam {restantes} de {len(candidatos)} — continue a sincronização."
            )
            status = "progress"
        else:
            msg = f"Sincronização concluída! {sucessos} concurso(s) importado(s) neste lote."
            status = "success"

        return {
            "status": status,
            "message": msg,
            "news": sucessos,
            "falhas": falhas,
            "processados_lote": len(lote),
            "faltantes_restantes": restantes,
            "faltantes_total": len(candidatos),
            "ultimo_oficial": ultimo_oficial,
            "continuar": restantes > 0,
            **st,
        }
