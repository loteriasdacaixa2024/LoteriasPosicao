import certifi
import requests
import time
from typing import Dict, Any, Optional, Set

from models.shared import db
from models.sorteio_diadesorte import SorteioDiaDeSorte, MESES_DO_ANO
from services.sorteio_premio_diadesorte import extrair_ganhadores_7

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/diadesorte/"
_NOME_P_NUM = {v.lower(): k for k, v in MESES_DO_ANO.items()}


class ApiDiaDeSorteService:
    @staticmethod
    def get_headers():
        return {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    @staticmethod
    def _get(url: str, timeout: int = 30):
        kwargs = {"headers": ApiDiaDeSorteService.get_headers(), "timeout": timeout}
        try:
            return requests.get(url, verify=certifi.where(), **kwargs)
        except requests.exceptions.SSLError:
            return requests.get(url, verify=False, **kwargs)

    @staticmethod
    def buscar_ultimo_concurso(timeout: int = 30) -> int:
        try:
            r = ApiDiaDeSorteService._get(BASE_URL, timeout=timeout)
            if r.status_code != 200:
                return 0
            d = r.json()
            return int(d.get("numero") or d.get("numeroConcurso") or 0)
        except Exception as e:
            print(f"[API Caixa] Erro: {e}")
        return 0

    @staticmethod
    def buscar_concurso_especifico(
        numero: int,
        tentativas: int = 3,
        pausa_retry: float = 1.5,
    ) -> Optional[dict]:
        url = f"{BASE_URL}{numero}"
        for tentativa in range(max(1, tentativas)):
            try:
                r = ApiDiaDeSorteService._get(url)
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (429, 502, 503, 504) and tentativa + 1 < tentativas:
                    time.sleep(pausa_retry * (tentativa + 1))
                    continue
                return None
            except Exception:
                if tentativa + 1 < tentativas:
                    time.sleep(pausa_retry * (tentativa + 1))
                    continue
                return None
        return None

    @staticmethod
    def _concursos_no_banco() -> Set[int]:
        return {r[0] for r in db.session.query(SorteioDiaDeSorte.concurso).all()}

    @staticmethod
    def _resolver_mes(dados: dict):
        num = dados.get("mesSorte")
        nome = (
            dados.get("nomeTimeCoracaoMesSorte")
            or dados.get("nomeMesSorte")
            or dados.get("mesSorteNome")
            or ""
        )
        if isinstance(nome, (int, float)):
            nome = str(int(nome))
        else:
            nome = str(nome).strip()

        # Dia de Sorte: a API costuma enviar o número do mês (1–12) em nomeTimeCoracaoMesSorte
        if not num and nome.isdigit():
            n = int(nome)
            if 1 <= n <= 12:
                num = n
                nome = MESES_DO_ANO.get(n, nome)

        if nome and not num:
            num = _NOME_P_NUM.get(nome.lower(), 0)
        if num and not nome:
            nome = MESES_DO_ANO.get(int(num), "Desconhecido")
        try:
            num = int(num)
        except (TypeError, ValueError):
            num = 0
        return num, nome

    @staticmethod
    def status_ganhadores() -> Dict[str, Any]:
        total = SorteioDiaDeSorte.query.count()
        sem_dado = SorteioDiaDeSorte.query.filter(
            SorteioDiaDeSorte.ganhadores_7.is_(None)
        ).count()
        com_vencedor = SorteioDiaDeSorte.query.filter(
            SorteioDiaDeSorte.ganhadores_7 >= 1
        ).count()
        acumulados = SorteioDiaDeSorte.query.filter(
            SorteioDiaDeSorte.ganhadores_7 == 0
        ).count()
        preenchidos = total - sem_dado
        return {
            "total_concursos": total,
            "ganhadores_preenchidos": preenchidos,
            "ganhadores_pendentes": sem_dado,
            "concursos_com_vencedor_7": com_vencedor,
            "concursos_acumulados_7": acumulados,
            "completo": sem_dado == 0 and total > 0,
        }

    @staticmethod
    def status_banco() -> Dict[str, Any]:
        total = SorteioDiaDeSorte.query.count()
        min_local = db.session.query(db.func.min(SorteioDiaDeSorte.concurso)).scalar()
        max_local = db.session.query(db.func.max(SorteioDiaDeSorte.concurso)).scalar()
        ultimo_api = ApiDiaDeSorteService.buscar_ultimo_concurso(timeout=8)
        alvo = ultimo_api or max_local or 0
        faltantes = 0
        if alvo:
            gravados = db.session.query(SorteioDiaDeSorte.concurso).filter(
                SorteioDiaDeSorte.concurso >= 1, SorteioDiaDeSorte.concurso <= alvo
            ).count()
            faltantes = max(0, alvo - gravados)
        api_offline = ultimo_api == 0 and (max_local or 0) > 0
        completo = faltantes == 0 and total > 0 and (min_local or 0) == 1 and ultimo_api > 0
        return {
            "total_registros": total, "concurso_minimo": min_local or 0, "concurso_maximo": max_local or 0,
            "ultimo_concurso_api": ultimo_api, "alvo_sincronizacao": alvo, "concursos_faltantes": faltantes,
            "api_offline": api_offline, "completo": completo, "precisa_sincronizar": faltantes > 0 or total == 0,
            **ApiDiaDeSorteService.status_ganhadores(),
        }

    @staticmethod
    def _salvar_concurso(concurso: int, dados: dict) -> bool:
        raw = dados.get("dezenasSorteadasOrdemSorteio") or dados.get("listaDezenas")
        if not raw or len(raw) < 7:
            return False
        dz = [int(x) for x in raw[:7]]
        m_num, m_nome = ApiDiaDeSorteService._resolver_mes(dados)
        g7 = extrair_ganhadores_7(dados)
        db.session.merge(SorteioDiaDeSorte(
            concurso=concurso, data=dados.get("dataApuracao", "") or dados.get("data", ""),
            d1=dz[0], d2=dz[1], d3=dz[2], d4=dz[3], d5=dz[4], d6=dz[5], d7=dz[6],
            mes_num=m_num, mes_nome=m_nome,
            ganhadores_7=g7,
        ))
        try:
            from analise_inteligentes_diadesorte.historico_service import upsert_de_sorteio
            upsert_de_sorteio(
                concurso=concurso,
                data=dados.get("dataApuracao", "") or dados.get("data", "") or "",
                dezenas_ordem=dz,
                mes_num=m_num,
                mes_nome=m_nome or "",
                commit=False,
            )
        except Exception:
            pass
        try:
            from services.caixa_excel_service import upsert_premiacao_from_api
            upsert_premiacao_from_api(concurso, dados)
        except Exception:
            pass
        return True

    @classmethod
    def atualizar_ganhadores_concurso(cls, concurso: int, dados: Optional[dict] = None) -> bool:
        """Atualiza ganhadores_7 de um concurso já gravado (backfill)."""
        g7 = extrair_ganhadores_7(dados) if dados else None
        if g7 is None:
            if dados is None:
                dados = cls.buscar_concurso_especifico(concurso)
            if not dados:
                return False
            g7 = extrair_ganhadores_7(dados)
        if g7 is None:
            return False
        row = db.session.get(SorteioDiaDeSorte, concurso)
        if not row:
            return False
        row.ganhadores_7 = g7
        return True

    @classmethod
    def backfill_ganhadores(
        cls,
        limite: int = 80,
        apenas_pendentes: bool = True,
        pausa_entre: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Preenche ganhadores_7 consultando a API Caixa.
        Por padrão processa só concursos com ganhadores_7 NULL.
        """
        limite = max(1, min(int(limite or 80), 200))
        q = db.session.query(SorteioDiaDeSorte.concurso)
        if apenas_pendentes:
            q = q.filter(SorteioDiaDeSorte.ganhadores_7.is_(None))
        pendentes = [r[0] for r in q.order_by(SorteioDiaDeSorte.concurso.asc()).all()]
        if not pendentes:
            st = cls.status_ganhadores()
            return {
                "status": "success",
                "message": "Todos os concursos já possuem ganhadores_7 preenchido.",
                "processados": 0,
                "sucessos": 0,
                "falhas": 0,
                "pendentes_restantes": 0,
                **st,
            }
        lote = pendentes[:limite]
        sucessos = falhas = 0
        pausa = max(0.0, float(pausa_entre or 0))
        for i, concurso in enumerate(lote):
            if i > 0 and pausa:
                time.sleep(pausa)
            dados = cls.buscar_concurso_especifico(concurso, tentativas=4, pausa_retry=2.0)
            if dados and cls.atualizar_ganhadores_concurso(concurso, dados):
                sucessos += 1
            else:
                falhas += 1
        db.session.commit()
        st = cls.status_ganhadores()
        restantes = st["ganhadores_pendentes"]
        return {
            "status": "progress" if restantes > 0 else "success",
            "message": (
                f"{sucessos} concurso(s) atualizado(s). "
                f"Restam {restantes} de {len(pendentes)} pendente(s)."
                if restantes > 0
                else f"Backfill concluído neste lote: {sucessos} atualizado(s)."
            ),
            "processados": len(lote),
            "sucessos": sucessos,
            "falhas": falhas,
            "pendentes_restantes": restantes,
            "pendentes_total": len(pendentes),
            "continuar": restantes > 0,
            **st,
        }

    @staticmethod
    def status_meses() -> Dict[str, Any]:
        total = SorteioDiaDeSorte.query.count()
        sem_mes = SorteioDiaDeSorte.query.filter(
            db.or_(
                SorteioDiaDeSorte.mes_num.is_(None),
                SorteioDiaDeSorte.mes_num < 1,
                SorteioDiaDeSorte.mes_num > 12,
            )
        ).count()
        com_mes = total - sem_mes
        return {
            "total_concursos": total,
            "meses_preenchidos": com_mes,
            "meses_pendentes": sem_mes,
            "completo": sem_mes == 0 and total > 0,
        }

    @classmethod
    def atualizar_mes_concurso(cls, concurso: int, dados: Optional[dict] = None) -> bool:
        """Atualiza mes_num/mes_nome de um concurso já gravado (backfill)."""
        if dados is None:
            dados = cls.buscar_concurso_especifico(concurso)
        if not dados:
            return False
        m_num, m_nome = cls._resolver_mes(dados)
        if not (1 <= int(m_num) <= 12):
            return False
        row = db.session.get(SorteioDiaDeSorte, concurso)
        if not row:
            return False
        row.mes_num = int(m_num)
        row.mes_nome = m_nome or MESES_DO_ANO.get(int(m_num), "")
        return True

    @classmethod
    def backfill_meses(
        cls,
        limite: int = 80,
        apenas_pendentes: bool = True,
    ) -> Dict[str, Any]:
        """Preenche mes_num/mes_nome consultando a API Caixa."""
        limite = max(1, min(int(limite or 80), 200))
        q = db.session.query(SorteioDiaDeSorte.concurso)
        if apenas_pendentes:
            q = q.filter(
                db.or_(
                    SorteioDiaDeSorte.mes_num.is_(None),
                    SorteioDiaDeSorte.mes_num < 1,
                    SorteioDiaDeSorte.mes_num > 12,
                )
            )
        pendentes = [r[0] for r in q.order_by(SorteioDiaDeSorte.concurso.asc()).all()]
        if not pendentes:
            st = cls.status_meses()
            return {
                "status": "success",
                "message": "Todos os concursos já possuem mês da sorte preenchido.",
                "processados": 0,
                "sucessos": 0,
                "falhas": 0,
                "pendentes_restantes": 0,
                **st,
            }
        lote = pendentes[:limite]
        sucessos = falhas = 0
        for concurso in lote:
            if cls.atualizar_mes_concurso(concurso):
                sucessos += 1
            else:
                falhas += 1
        db.session.commit()
        restantes = len(pendentes) - len(lote)
        st = cls.status_meses()
        return {
            "status": "progress" if restantes > 0 else "success",
            "message": (
                f"{sucessos} concurso(s) com mês atualizado(s). "
                f"Restam {restantes} de {len(pendentes)} pendente(s)."
                if restantes > 0
                else f"Backfill de meses concluído neste lote: {sucessos} atualizado(s)."
            ),
            "processados": len(lote),
            "sucessos": sucessos,
            "falhas": falhas,
            "pendentes_restantes": restantes,
            "pendentes_total": len(pendentes),
            "continuar": restantes > 0,
            **st,
        }

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
            print(f"[API Caixa] Dia de Sorte {concurso}/{ultimo_oficial}...", end="", flush=True)
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
