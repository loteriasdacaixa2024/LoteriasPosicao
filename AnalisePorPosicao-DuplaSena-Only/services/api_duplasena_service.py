import certifi
import requests
from typing import Dict, Any, Optional, Set

from models.shared import db
from models.sorteio_duplasena import SorteiosDuplaSena

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/duplasena/"


class ApiDuplaSenaService:
    @staticmethod
    def get_headers():
        return {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    @staticmethod
    def _get(url: str, timeout: int = 30):
        kwargs = {"headers": ApiDuplaSenaService.get_headers(), "timeout": timeout}
        try:
            return requests.get(url, verify=certifi.where(), **kwargs)
        except requests.exceptions.SSLError:
            return requests.get(url, verify=False, **kwargs)

    @staticmethod
    def buscar_ultimo_concurso(timeout: int = 30) -> int:
        try:
            r = ApiDuplaSenaService._get(BASE_URL, timeout=timeout)
            if r.status_code != 200:
                return 0
            d = r.json()
            return int(d.get("numero") or d.get("numeroConcurso") or 0)
        except Exception as e:
            print(f"[API Caixa] Erro: {e}")
        return 0

    @staticmethod
    def buscar_concurso_especifico(numero: int) -> Optional[dict]:
        try:
            r = ApiDuplaSenaService._get(f"{BASE_URL}{numero}")
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    @staticmethod
    def _concursos_no_banco() -> Set[int]:
        return {r[0] for r in db.session.query(SorteiosDuplaSena.concurso).all()}

    @staticmethod
    def status_banco() -> Dict[str, Any]:
        total = SorteiosDuplaSena.query.count()
        min_local = db.session.query(db.func.min(SorteiosDuplaSena.concurso)).scalar()
        max_local = db.session.query(db.func.max(SorteiosDuplaSena.concurso)).scalar()
        ultimo_api = ApiDuplaSenaService.buscar_ultimo_concurso(timeout=8)
        alvo = ultimo_api or max_local or 0
        faltantes = 0
        if alvo:
            gravados = db.session.query(SorteiosDuplaSena.concurso).filter(
                SorteiosDuplaSena.concurso >= 1, SorteiosDuplaSena.concurso <= alvo
            ).count()
            faltantes = max(0, alvo - gravados)
        api_offline = ultimo_api == 0 and (max_local or 0) > 0
        completo = faltantes == 0 and total > 0 and (min_local or 0) == 1 and ultimo_api > 0
        return {
            "total_registros": total, "concurso_minimo": min_local or 0, "concurso_maximo": max_local or 0,
            "ultimo_concurso_api": ultimo_api, "alvo_sincronizacao": alvo, "concursos_faltantes": faltantes,
            "api_offline": api_offline, "completo": completo, "precisa_sincronizar": faltantes > 0 or total == 0,
        }

    @staticmethod
    def _salvar_concurso(concurso: int, dados: dict) -> bool:
        dezenas1 = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas") or dados.get("listaDezenas1")
        dezenas2 = dados.get("listaDezenasSegundoSorteio") or dados.get("listaDezenas2")
        if dezenas1 and len(dezenas1) == 12:
            dezenas2 = dezenas1[6:12]
            dezenas1 = dezenas1[0:6]
        if not (dezenas1 and len(dezenas1) == 6 and dezenas2 and len(dezenas2) == 6):
            return False
        d1 = [int(x) for x in dezenas1]
        d2 = [int(x) for x in dezenas2]
        db.session.merge(SorteiosDuplaSena(
            concurso=concurso, data=dados.get("dataApuracao", "") or dados.get("data", ""),
            s1_d1=d1[0], s1_d2=d1[1], s1_d3=d1[2], s1_d4=d1[3], s1_d5=d1[4], s1_d6=d1[5],
            s2_d1=d2[0], s2_d2=d2[1], s2_d3=d2[2], s2_d4=d2[3], s2_d5=d2[4], s2_d6=d2[5],
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
        candidatos = list(range(max_local + 1, ultimo_oficial + 1)) if modo == "incremental" else [i for i in range(1, ultimo_oficial + 1) if i not in presentes]
        if not candidatos:
            st = cls.status_banco()
            return {"status": "info", "message": f"Base completa: {st['total_registros']} concursos (1 a {ultimo_oficial}).", "news": 0, "continuar": False, **st}
        lote = candidatos[:limite]
        sucessos = falhas = 0
        for concurso in lote:
            print(f"[API Caixa] Dupla Sena {concurso}/{ultimo_oficial}...", end="", flush=True)
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
