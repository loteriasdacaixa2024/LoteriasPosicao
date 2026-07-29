from models.shared import db
from models.sorteio_duplasena import SorteiosDuplaSena

TOTAL = 50


class CicloDuplaSenaService:
    @staticmethod
    def obter_ciclo_atual():
        try:
            sorteios = db.session.query(SorteiosDuplaSena).order_by(
                SorteiosDuplaSena.concurso.asc()
            ).all()
        except Exception:
            sorteios = []
        ciclo_num = 1
        dezenas_sorteadas = set()
        concursos_no_ciclo = 0
        for s in sorteios:
            dezenas_sorteadas.update(s.sorteio1())
            dezenas_sorteadas.update(s.sorteio2())
            concursos_no_ciclo += 1
            if len(dezenas_sorteadas) == TOTAL:
                ciclo_num += 1
                dezenas_sorteadas = set()
                concursos_no_ciclo = 0
        faltantes = sorted(set(range(1, TOTAL + 1)) - dezenas_sorteadas)
        return {
            "ciclo_num": ciclo_num,
            "dezenas_sorteadas": sorted(dezenas_sorteadas),
            "dezenas_faltantes": faltantes,
            "total_sorteadas": len(dezenas_sorteadas),
            "total_faltantes": len(faltantes),
            "concursos_no_ciclo": concursos_no_ciclo,
        }
