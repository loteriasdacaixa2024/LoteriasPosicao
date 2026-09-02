from models.shared import db
from models.sorteio_timemania import SorteioTimemania

TOTAL = 80


class CicloTimemaniaService:
    @staticmethod
    def obter_ciclo_atual():
        try:
            sorteios = db.session.query(SorteioTimemania).order_by(
                SorteioTimemania.concurso.asc()
            ).all()
        except Exception:
            sorteios = []
        ciclo_num = 1
        dezenas_sorteadas = set()
        concursos_no_ciclo = 0
        for s in sorteios:
            dezenas = getattr(s, "dezenas_lista")()
            dezenas_sorteadas.update(dezenas)
            concursos_no_ciclo += 1
            if len(dezenas_sorteadas) >= TOTAL:
                ciclo_num += 1
                dezenas_sorteadas = set()
                concursos_no_ciclo = 0
        base = 0 if "timemania" == "lotomania" else 1
        faltantes = sorted(set(range(base, TOTAL + 1)) - dezenas_sorteadas)
        return {
            "ciclo_num": ciclo_num,
            "dezenas_sorteadas": sorted(dezenas_sorteadas),
            "dezenas_faltantes": faltantes,
            "total_sorteadas": len(dezenas_sorteadas),
            "total_faltantes": len(faltantes),
            "concursos_no_ciclo": concursos_no_ciclo,
        }
