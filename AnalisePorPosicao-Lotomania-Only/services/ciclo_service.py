from models.shared import db
from models.sorteio_lotomania import SorteioLotomania

# Universo oficial Lotomania: 00 a 99 (100 dezenas). NÃO incluir 100.
DEZENA_MIN = 0
DEZENA_MAX = 99
TOTAL = DEZENA_MAX - DEZENA_MIN + 1  # 100


class CicloLotomaniaService:
    @staticmethod
    def obter_ciclo_atual():
        try:
            sorteios = db.session.query(SorteioLotomania).order_by(
                SorteioLotomania.concurso.asc()
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
        faltantes = sorted(set(range(DEZENA_MIN, DEZENA_MAX + 1)) - dezenas_sorteadas)
        return {
            "ciclo_num": ciclo_num,
            "dezenas_sorteadas": sorted(dezenas_sorteadas),
            "dezenas_faltantes": faltantes,
            "total_sorteadas": len(dezenas_sorteadas),
            "total_faltantes": len(faltantes),
            "concursos_no_ciclo": concursos_no_ciclo,
        }
