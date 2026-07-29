from models.shared import db
from models.sorteio_megasena import SorteioMegaSena

class CicloMegaSenaService:
    @staticmethod
    def obter_ciclo_atual():
        """
        Calcula os ciclos da Mega-Sena em ordem cronológica.
        O ciclo reinicia toda vez que todas as 60 dezenas distintas forem sorteadas.
        Retorna as dezenas que já saíram no ciclo atual e as que faltam.
        """
        try:
            sorteios = db.session.query(SorteioMegaSena).order_by(
                SorteioMegaSena.concurso.asc()
            ).all()
        except Exception as e:
            print(f"Erro ao consultar sorteios para ciclo: {e}")
            sorteios = []

        ciclo_num = 1
        dezenas_sorteadas = set()
        concursos_no_ciclo = 0

        for s in sorteios:
            dezenas_sorteio = s.dezenas()  # Retorna o set {d1, d2, d3, d4, d5, d6}
            dezenas_sorteadas.update(dezenas_sorteio)
            concursos_no_ciclo += 1

            if len(dezenas_sorteadas) == 60:
                # O ciclo completou!
                ciclo_num += 1
                dezenas_sorteadas = set()
                concursos_no_ciclo = 0

        # Para o ciclo ativo atual
        dezenas_sorteadas_list = sorted(list(dezenas_sorteadas))
        dezenas_faltantes = sorted(list(set(range(1, 61)) - dezenas_sorteadas))

        return {
            "ciclo_num": ciclo_num,
            "dezenas_sorteadas": dezenas_sorteadas_list,
            "dezenas_faltantes": dezenas_faltantes,
            "total_sorteadas": len(dezenas_sorteadas_list),
            "total_faltantes": len(dezenas_faltantes),
            "concursos_no_ciclo": concursos_no_ciclo
        }
