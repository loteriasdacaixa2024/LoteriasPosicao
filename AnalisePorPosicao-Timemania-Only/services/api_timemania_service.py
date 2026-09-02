import certifi
import requests
from typing import Dict, Any, Optional, Set

from models.shared import db
from models.sorteio_timemania import SorteioTimemania, TIMES_DO_CORACAO

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/timemania/"


class ApiTimemaniaSService:
    @staticmethod
    def get_headers():
        return {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    @staticmethod
    def _get(url: str, timeout: int = 30):
        kwargs = {"headers": ApiTimemaniaSService.get_headers(), "timeout": timeout}
        try:
            return requests.get(url, verify=certifi.where(), **kwargs)
        except requests.exceptions.SSLError:
            return requests.get(url, verify=False, **kwargs)

    @staticmethod
    def buscar_ultimo_concurso(timeout: int = 30) -> int:
        try:
            r = ApiTimemaniaSService._get(BASE_URL, timeout=timeout)
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
            r = ApiTimemaniaSService._get(f"{BASE_URL}{numero}")
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    @staticmethod
    def _concursos_no_banco() -> Set[int]:
        return {r[0] for r in db.session.query(SorteioTimemania.concurso).all()}

    @staticmethod
    def status_banco() -> Dict[str, Any]:
        total = SorteioTimemania.query.count()
        min_local = db.session.query(db.func.min(SorteioTimemania.concurso)).scalar()
        max_local = db.session.query(db.func.max(SorteioTimemania.concurso)).scalar()
        ultimo_api = ApiTimemaniaSService.buscar_ultimo_concurso(timeout=8)
        alvo = ultimo_api or max_local or 0
        faltantes = 0
        if alvo:
            gravados = db.session.query(SorteioTimemania.concurso).filter(
                SorteioTimemania.concurso >= 1, SorteioTimemania.concurso <= alvo
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
    def _resolver_time(dados: dict):
        nome = dados.get("nomeTimeCoracaoMesSorte") or dados.get("nomeTimeCoracao") or ""
        time_num = 0
        if nome:
            clean = nome.split("/")[0].strip().lower()
            for k, v in TIMES_DO_CORACAO.items():
                if v.split("/")[0].strip().lower() == clean:
                    time_num = k
                    break
        return time_num, nome

    @staticmethod
    def _extrair_dezenas(dados: dict):
        """Dezenas na ordem do sorteio; a API Caixa envia 7 (raro: 8)."""
        ordem = dados.get("dezenasSorteadasOrdemSorteio")
        if ordem and len(ordem) >= 7:
            return [int(x) for x in ordem]
        lista = dados.get("listaDezenas")
        if lista and len(lista) >= 7:
            return [int(x) for x in lista]
        return None

    @staticmethod
    def _salvar_concurso(concurso: int, dados: dict) -> bool:
        dez = ApiTimemaniaSService._extrair_dezenas(dados)
        if not dez:
            return False
        time_num, time_nome = ApiTimemaniaSService._resolver_time(dados)
        campos = {f"d{i}": (dez[i - 1] if i <= len(dez) else 0) for i in range(1, 11)}
        db.session.merge(SorteioTimemania(
            concurso=concurso, data=dados.get("dataApuracao", "") or dados.get("data", ""),
            time_num=time_num, time_nome=time_nome,
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
        candidatos = list(range(max_local + 1, ultimo_oficial + 1)) if modo == "incremental" else [i for i in range(1, ultimo_oficial + 1) if i not in presentes]
        if not candidatos:
            st = cls.status_banco()
            return {"status": "info", "message": f"Base completa: {st['total_registros']} concursos (1 a {ultimo_oficial}).", "news": 0, "continuar": False, **st}
        lote = candidatos[:limite]
        sucessos = falhas = 0
        for concurso in lote:
            print(f"[API Caixa] Timemania {concurso}/{ultimo_oficial}...", end="", flush=True)
            dados = cls.buscar_concurso_especifico(concurso)
            if dados and cls._salvar_concurso(concurso, dados):
                sucessos += 1
                print(" [OK]")
            else:
                falhas += 1
                o = (dados or {}).get("dezenasSorteadasOrdemSorteio")
                l = (dados or {}).get("listaDezenas")
                det = f" ordem={len(o) if o else 0} lista={len(l) if l else 0}" if dados else " sem resposta API"
                print(f" [FALHOU]{det}")
        db.session.commit()
        restantes = len(candidatos) - len(lote)
        st = cls.status_banco()
        msg = (f"{sucessos} concurso(s) importado(s) neste lote. Faltam {restantes} de {len(candidatos)} — continue a sincronização." if restantes > 0
               else f"Sincronização concluída! {sucessos} concurso(s) importado(s) neste lote.")
        return {"status": "progress" if restantes > 0 else "success", "message": msg, "news": sucessos, "falhas": falhas,
                "processados_lote": len(lote), "faltantes_restantes": restantes, "faltantes_total": len(candidatos),
                "ultimo_oficial": ultimo_oficial, "continuar": restantes > 0, **st}
