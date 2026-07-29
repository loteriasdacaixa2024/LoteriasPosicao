"""
analise_diadesorte_service.py
==============================
31 dezenas (01-31) → freq/atraso por dezena
12 meses         → freq/atraso por mês
"""
from models.shared import db
from models.sorteio_diadesorte import SorteioDiaDeSorte, MESES_DO_ANO, mes_abrev_de
from sqlalchemy import desc

TOTAL_DEZ    = 31
NUM_SORT_DEZ = 7
TOTAL_MESES  = 12

class AnaliseDiaDeSorteService:

    @staticmethod
    def analise_geral():
        sorteios = db.session.query(SorteioDiaDeSorte).order_by(
            desc(SorteioDiaDeSorte.concurso)
        ).all()

        if not sorteios:
            return None

        total  = len(sorteios)
        ultimo = sorteios[0].concurso

        freq_dez  = {d: 0 for d in range(1, TOTAL_DEZ + 1)}
        visto_dez = {d: 0 for d in range(1, TOTAL_DEZ + 1)}
        freq_mes  = {m: 0 for m in range(1, TOTAL_MESES + 1)}
        visto_mes = {m: 0 for m in range(1, TOTAL_MESES + 1)}

        for s in sorteios:
            for d in s.dezenas():
                freq_dez[d] += 1
                if visto_dez[d] == 0: visto_dez[d] = s.concurso
            if s.mes_num and 1 <= s.mes_num <= TOTAL_MESES:
                freq_mes[s.mes_num] += 1
                if visto_mes[s.mes_num] == 0: visto_mes[s.mes_num] = s.concurso

        dados_dez = []
        for d in range(1, TOTAL_DEZ + 1):
            atraso = (ultimo - visto_dez[d]) if visto_dez[d] > 0 else total
            pct    = round(freq_dez[d] / total * 100, 1) if total > 0 else 0
            dados_dez.append({
                "dezena": d, "dezena_fmt": f"{d:02d}",
                "freq": freq_dez[d], "atraso": atraso, "pct": pct
            })

        dados_mes = []
        for m in range(1, TOTAL_MESES + 1):
            atraso = (ultimo - visto_mes[m]) if visto_mes[m] > 0 else total
            pct    = round(freq_mes[m] / total * 100, 1) if total > 0 else 0
            mes_nome = MESES_DO_ANO.get(m, f"Mês {m}")
            dados_mes.append({
                "mes_num":  m,
                "mes_nome": mes_nome,
                "mes_abrev": mes_abrev_de(m, mes_nome),
                "freq":  freq_mes[m],
                "atraso": atraso,
                "pct":   pct,
            })

        return {
            "dados":            dados_dez,
            "dados_meses":      dados_mes,
            "total_sorteios":   total,
            "ultimo_concurso":  ultimo,
            "esperado_pct_dez": round(NUM_SORT_DEZ / TOTAL_DEZ  * 100, 1),
            "esperado_pct_mes": round(1            / TOTAL_MESES * 100, 1),
        }

    @staticmethod
    def ultimos_sorteios():
        sorteios = db.session.query(SorteioDiaDeSorte).order_by(
            desc(SorteioDiaDeSorte.concurso)
        ).all()
        return [
            {
                "concurso":      s.concurso,
                "data":          s.data,
                "dezenas":       s.dezenas_lista(),
                "dezenas_ordem": s.dezenas_ordem_lista(),
                "mes_num":       s.mes_num,
                "mes_nome":      s.mes_nome,
                "mes_abrev":     s.mes_abrev(),
            }
            for s in sorteios
        ]

    @staticmethod
    def meses_indicados(janela: int = 10):
        from diadesorte.meses_indicados import carregar_meses_indicados

        return carregar_meses_indicados(SorteioDiaDeSorte, janela=janela)
