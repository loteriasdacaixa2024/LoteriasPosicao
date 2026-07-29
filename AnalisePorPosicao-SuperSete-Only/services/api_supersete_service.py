import requests
from typing import Any, Dict

from models.shared import db
from models.sorteio_supersete import SorteioSuperSete

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/supersete/"

class ApiSuperSeteService:
    @staticmethod
    def get_headers(): return {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    @staticmethod
    def buscar_ultimo_concurso(timeout: int = 10) -> int:
        try:
            r = requests.get(BASE_URL, headers=ApiSuperSeteService.get_headers(), timeout=timeout)
            if r.status_code == 200:
                j = r.json()
                for key in ("numero", "numeroConcurso", "numeroConcursoUltimo", "concurso"):
                    if j.get(key):
                        return int(j[key])
        except Exception:
            pass
        return 0

    @staticmethod
    def status_banco() -> Dict[str, Any]:
        total = SorteioSuperSete.query.count()
        min_local = db.session.query(db.func.min(SorteioSuperSete.concurso)).scalar()
        max_local = db.session.query(db.func.max(SorteioSuperSete.concurso)).scalar()
        ultimo_api = ApiSuperSeteService.buscar_ultimo_concurso(timeout=8)
        alvo = ultimo_api or max_local or 0
        faltantes = 0
        api_offline = ultimo_api == 0 and (max_local or 0) > 0
        if alvo:
            gravados = (
                db.session.query(SorteioSuperSete.concurso)
                .filter(SorteioSuperSete.concurso >= 1, SorteioSuperSete.concurso <= alvo)
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
    def buscar_concurso_especifico(numero):
        try:
            r = requests.get(f"{BASE_URL}{numero}", headers=ApiSuperSeteService.get_headers(), timeout=10)
            if r.status_code == 200: return r.json()
        except: pass
        return None

    @staticmethod
    def sincronizar_banco(teto_concurso=None):
        ultimo_oficial = teto_concurso or ApiSuperSeteService.buscar_ultimo_concurso()
        if not ultimo_oficial: return {"status": "error", "message": "API offline"}
        ultimo_local = db.session.query(db.func.max(SorteioSuperSete.concurso)).scalar() or 0
        if ultimo_local >= ultimo_oficial: return {"status": "info", "message": "Atualizado"}

        sucessos = 0
        for concurso in range(ultimo_local + 1, ultimo_oficial + 1):
            print(f"[API Caixa] SuperSete {concurso}/{ultimo_oficial}...", end="", flush=True)
            dados = ApiSuperSeteService.buscar_concurso_especifico(concurso)
            if dados:
                dezenas_raw = dados.get('dezenasSorteadasOrdemSorteio') or dados.get('listaDezenas')
                if dezenas_raw and len(dezenas_raw) == 7:
                    dezenas = [int(d) for d in dezenas_raw]
                    novo = SorteioSuperSete(concurso=concurso, data=dados.get('dataApuracao', ''),
                        coluna_1=dezenas[0], coluna_2=dezenas[1], coluna_3=dezenas[2], 
                        coluna_4=dezenas[3], coluna_5=dezenas[4], coluna_6=dezenas[5], coluna_7=dezenas[6])
                    db.session.merge(novo)
                    sucessos += 1
                    print(f" [OK]")
                else: print(" [SKIP]")
            else: print(" [FALHOU]")
            if concurso % 20 == 0: db.session.commit()
        db.session.commit()
        return {"status": "success", "message": f"{sucessos} sorteios novos cadastrados.", "news": sucessos}
