import certifi
import requests
from typing import List, Dict, Any, Optional, Set

from models.shared import db
from models.sorteio_lotofacil import SorteioLotofacil

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/"


class ApiLotofacilService:
    @staticmethod
    def get_headers():
        return {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    @staticmethod
    def _get(url: str, timeout: int = 30):
        kwargs = {"headers": ApiLotofacilService.get_headers(), "timeout": timeout}
        try:
            return requests.get(url, verify=certifi.where(), **kwargs)
        except requests.exceptions.SSLError:
            return requests.get(url, verify=False, **kwargs)

    @staticmethod
    def buscar_ultimo_concurso(timeout: int = 30) -> int:
        try:
            r = ApiLotofacilService._get(BASE_URL, timeout=timeout)
            if r.status_code != 200:
                return 0
            data = r.json()
            return int(data.get("numero") or data.get("numeroConcurso") or 0)
        except Exception as e:
            print(f"[API Caixa] Erro ao buscar último concurso: {e}")
        return 0

    @staticmethod
    def buscar_concurso_especifico(numero: int) -> Optional[dict]:
        try:
            r = ApiLotofacilService._get(f"{BASE_URL}{numero}")
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @staticmethod
    def _concursos_no_banco() -> Set[int]:
        rows = db.session.query(SorteioLotofacil.concurso).all()
        return {r[0] for r in rows}

    @staticmethod
    def status_banco() -> Dict[str, Any]:
        total = SorteioLotofacil.query.count()
        min_local = db.session.query(db.func.min(SorteioLotofacil.concurso)).scalar()
        max_local = db.session.query(db.func.max(SorteioLotofacil.concurso)).scalar()
        ultimo_api = ApiLotofacilService.buscar_ultimo_concurso(timeout=8)
        alvo = ultimo_api or max_local or 0
        faltantes = 0
        api_offline = ultimo_api == 0 and (max_local or 0) > 0
        if alvo:
            gravados = (
                db.session.query(SorteioLotofacil.concurso)
                .filter(SorteioLotofacil.concurso >= 1, SorteioLotofacil.concurso <= alvo)
                .count()
            )
            faltantes = max(0, alvo - gravados)
        completo = faltantes == 0 and total > 0 and (min_local or 0) == 1 and ultimo_api > 0
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
    def _salvar_concurso(concurso: int, dados: dict) -> bool:
        raw = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas")
        if not raw or len(raw) != 15:
            return False
        dez = [int(d) for d in raw]
        campos = {f"posicao_{i + 1}": dez[i] for i in range(15)}
        db.session.merge(SorteioLotofacil(
            concurso=concurso,
            data=dados.get("dataApuracao", "") or dados.get("data", ""),
            **campos,
        ))
        return True

    @classmethod
    def sincronizar_banco(cls, modo: str = "completo", limite: int = 60, teto_concurso: Optional[int] = None) -> Dict[str, Any]:
        limite = max(1, min(int(limite or 60), 200))
        ultimo_oficial = teto_concurso or cls.buscar_ultimo_concurso()
        if not ultimo_oficial:
            return {"status": "error", "message": "Não foi possível consultar a API da Caixa. Verifique sua conexão."}
        presentes = cls._concursos_no_banco()
        max_local = max(presentes) if presentes else 0
        if modo == "incremental":
            candidatos = list(range(max_local + 1, ultimo_oficial + 1))
        else:
            candidatos = [i for i in range(1, ultimo_oficial + 1) if i not in presentes]
        if not candidatos:
            st = cls.status_banco()
            return {"status": "info", "message": f"Base completa: {st['total_registros']} concursos (1 a {ultimo_oficial}).", "news": 0, "continuar": False, **st}
        lote = candidatos[:limite]
        sucessos = falhas = 0
        for concurso in lote:
            print(f"[API Caixa] Lotofácil {concurso}/{ultimo_oficial}...", end="", flush=True)
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
        msg = (f"{sucessos} concurso(s) importado(s) neste lote. Faltam {restantes} de {len(candidatos)} — continue a sincronização." if restantes > 0
               else f"Sincronização concluída! {sucessos} concurso(s) importado(s) neste lote.")
        return {"status": "progress" if restantes > 0 else "success", "message": msg, "news": sucessos, "falhas": falhas,
                "processados_lote": len(lote), "faltantes_restantes": restantes, "faltantes_total": len(candidatos),
                "ultimo_oficial": ultimo_oficial, "continuar": restantes > 0, **st}
