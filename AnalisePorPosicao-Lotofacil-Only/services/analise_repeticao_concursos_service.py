"""
Análise de repetição entre concursos consecutivos — Lotofácil.
Volante (interseção 15×15), posicional (P1–P15) e híbrido.
Alimenta gerador de apostas 15–20 dezenas.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from models.sorteio_lotofacil import SorteioLotofacil
from models.shared import db
from services.ciclo_service import CicloLotofacilService
from sqlalchemy import desc

UNIVERSO = 25
DEZENAS_MIN = 15
DEZENAS_MAX = 20


def _pares_impares(dezenas: List[int]) -> Tuple[int, int]:
    p = sum(1 for d in dezenas if d % 2 == 0)
    return p, len(dezenas) - p


def _faixa(d: int) -> str:
    if d <= 8:
        return 'baixa'
    if d <= 17:
        return 'media'
    return 'alta'


class AnaliseRepeticaoConcursosService:
    @staticmethod
    def _build_stats_dezenas() -> Dict[int, Dict[str, Any]]:
        """Frequência, atraso, posição predominante e ciclo — tooltips do volante."""
        sorteios = (
            db.session.query(SorteioLotofacil)
            .order_by(SorteioLotofacil.concurso.desc())
            .all()
        )
        if not sorteios:
            return {}

        ultimo_concurso = sorteios[0].concurso
        total_sorteios = len(sorteios)
        freq: Counter = Counter()
        pos_por_dezena: Dict[int, Counter] = defaultdict(Counter)
        visto: Dict[int, int] = {}

        for s in reversed(sorteios):
            for i, d in enumerate(s.dezenas(), start=1):
                freq[d] += 1
                pos_por_dezena[d][i] += 1
                if d not in visto:
                    visto[d] = s.concurso

        ciclo = CicloLotofacilService.obter_ciclo_atual()
        no_ciclo = set(ciclo.get('dezenas_sorteadas') or [])
        faltantes = set(ciclo.get('dezenas_faltantes') or [])

        stats: Dict[int, Dict[str, Any]] = {}
        slots_totais = total_sorteios * 15
        for d in range(1, UNIVERSO + 1):
            pos_pred = None
            if pos_por_dezena[d]:
                pos_pred = max(pos_por_dezena[d].items(), key=lambda x: x[1])[0]
            atraso = ultimo_concurso if d not in visto else ultimo_concurso - visto[d]
            if d in no_ciclo:
                ciclo_txt = f"No ciclo {ciclo.get('ciclo_num', 1)} (já sorteada)"
            elif d in faltantes:
                ciclo_txt = f"No ciclo {ciclo.get('ciclo_num', 1)} (faltante)"
            else:
                ciclo_txt = '—'
            stats[d] = {
                'frequencia': freq[d],
                'freq_pct': round((freq[d] / slots_totais) * 100, 2) if slots_totais else 0,
                'atraso': atraso,
                'posicao_predominante': pos_pred,
                'ciclo': ciclo_txt,
            }
        return stats

    @staticmethod
    def listar_concursos(limit: int = 120) -> List[Dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        rows = (
            db.session.query(SorteioLotofacil)
            .order_by(desc(SorteioLotofacil.concurso))
            .limit(lim)
            .all()
        )
        return [
            {
                'concurso': s.concurso,
                'data': s.data,
                'dezenas': s.dezenas(),
            }
            for s in rows
        ]

    @staticmethod
    def obter_concurso(concurso: int) -> Optional[Dict[str, Any]]:
        s = db.session.get(SorteioLotofacil, int(concurso))
        if not s:
            return None
        return {
            'concurso': s.concurso,
            'data': s.data,
            'dezenas': s.dezenas(),
        }

    @staticmethod
    def _carregar_sorteios_asc() -> List[SorteioLotofacil]:
        return (
            db.session.query(SorteioLotofacil)
            .order_by(SorteioLotofacil.concurso.asc())
            .all()
        )

    @staticmethod
    def _repetidas_volante(a: Set[int], b: Set[int]) -> Set[int]:
        return a & b

    @staticmethod
    def _repetidas_posicional(s_ant: SorteioLotofacil, s_at: SorteioLotofacil) -> List[Dict[str, int]]:
        out = []
        for i in range(1, 16):
            da = getattr(s_ant, f'posicao_{i}')
            db_ = getattr(s_at, f'posicao_{i}')
            if da == db_:
                out.append({'posicao': i, 'dezena': da})
        return out

    @staticmethod
    def _classificar_tendencia(taxa_permanencia: float, media_global: float) -> str:
        if taxa_permanencia >= media_global + 8:
            return 'permanencia'
        if taxa_permanencia <= media_global - 8:
            return 'saida'
        return 'neutra'

    @staticmethod
    def analisar_completo(modo: str = 'volante') -> Dict[str, Any]:
        modo = modo if modo in ('volante', 'posicional', 'hibrido') else 'volante'
        sorteios = AnaliseRepeticaoConcursosService._carregar_sorteios_asc()
        if len(sorteios) < 2:
            return {'sucesso': False, 'erro': 'É necessário ao menos 2 concursos no banco.'}

        total_pares = len(sorteios) - 1

        # Histórico: quantas dezenas repetiram por par (volante)
        qtd_rep_por_par: List[int] = []
        contagem_dezena_em_repeticao = Counter()
        permanencia_depois = defaultdict(lambda: {'eventos': 0, 'permaneceu': 0})

        for i in range(1, len(sorteios)):
            ant_set = set(sorteios[i - 1].dezenas())
            at_set = set(sorteios[i].dezenas())
            rep = ant_set & at_set
            qtd_rep_por_par.append(len(rep))
            for d in rep:
                contagem_dezena_em_repeticao[d] += 1
                if i + 1 < len(sorteios):
                    permanencia_depois[d]['eventos'] += 1
                    prox = set(sorteios[i + 1].dezenas())
                    if d in prox:
                        permanencia_depois[d]['permaneceu'] += 1

        media_qtd_rep = round(sum(qtd_rep_por_par) / len(qtd_rep_por_par), 2) if qtd_rep_por_par else 0

        # Padrões par/ímpar quando houve repetição (volante)
        pares_quando_rep: List[int] = []
        impares_quando_rep: List[int] = []
        for i in range(1, len(sorteios)):
            rep = list(set(sorteios[i - 1].dezenas()) & set(sorteios[i].dezenas()))
            if rep:
                p, im = _pares_impares(rep)
                pares_quando_rep.append(p)
                impares_quando_rep.append(im)

        media_pares_rep = (
            round(sum(pares_quando_rep) / len(pares_quando_rep), 2) if pares_quando_rep else 0
        )
        media_impares_rep = (
            round(sum(impares_quando_rep) / len(impares_quando_rep), 2) if impares_quando_rep else 0
        )

        # Taxa média de permanência (todas dezenas)
        taxas_perm = []
        for d in range(1, UNIVERSO + 1):
            ev = permanencia_depois[d]['eventos']
            if ev > 0:
                taxas_perm.append(permanencia_depois[d]['permaneceu'] / ev * 100)
        media_perm_global = round(sum(taxas_perm) / len(taxas_perm), 1) if taxas_perm else 0

        ult = sorteios[-1]
        pen = sorteios[-2]
        ult_set = set(ult.dezenas())
        pen_set = set(pen.dezenas())
        rep_ultimo_volante = sorted(ult_set & pen_set)
        rep_posicional = AnaliseRepeticaoConcursosService._repetidas_posicional(pen, ult)

        # Posicional histórico: quantas posições repetiram por par
        qtd_pos_rep_por_par = []
        for i in range(1, len(sorteios)):
            n = len(AnaliseRepeticaoConcursosService._repetidas_posicional(sorteios[i - 1], sorteios[i]))
            qtd_pos_rep_por_par.append(n)
        media_pos_rep = (
            round(sum(qtd_pos_rep_por_par) / len(qtd_pos_rep_por_par), 2) if qtd_pos_rep_por_par else 0
        )

        p_ult, im_ult = _pares_impares(rep_ultimo_volante)

        dezenas_detalhe = []
        for d in range(1, UNIVERSO + 1):
            ev = permanencia_depois[d]['eventos']
            perm = permanencia_depois[d]['permaneceu']
            taxa = round(perm / ev * 100, 1) if ev else 0
            freq_rep = contagem_dezena_em_repeticao[d]
            pct_freq = round(freq_rep / total_pares * 100, 2) if total_pares else 0
            tendencia = AnaliseRepeticaoConcursosService._classificar_tendencia(taxa, media_perm_global)
            dezenas_detalhe.append({
                'dezena': d,
                'par': d % 2 == 0,
                'freq_repeticao_vezes': freq_rep,
                'freq_repeticao_pct': pct_freq,
                'permanencia_eventos': ev,
                'permanencia_vezes': perm,
                'permanencia_pct': taxa,
                'tendencia': tendencia,
                'repetiu_ultimo_par_volante': d in rep_ultimo_volante,
                'repetiu_ultimo_par_posicional': any(x['dezena'] == d for x in rep_posicional),
            })

        dezenas_detalhe.sort(key=lambda x: (-x['freq_repeticao_vezes'], x['dezena']))

        ranking_freq = sorted(
            range(1, UNIVERSO + 1),
            key=lambda d: -contagem_dezena_em_repeticao[d],
        )[:10]

        return {
            'sucesso': True,
            'modo': modo,
            'total_pares_analisados': total_pares,
            'ultimo_concurso': ult.concurso,
            'penultimo_concurso': pen.concurso,
            'ultimo_sorteio': ult.dezenas(),
            'penultimo_sorteio': pen.dezenas(),
            'resumo_ultimo_par': {
                'volante': {
                    'quantidade': len(rep_ultimo_volante),
                    'dezenas': rep_ultimo_volante,
                    'pares': p_ult,
                    'impares': im_ult,
                },
                'posicional': {
                    'quantidade': len(rep_posicional),
                    'itens': rep_posicional,
                },
                'media_historica_quantidade_volante': media_qtd_rep,
                'media_historica_posicional': media_pos_rep,
            },
            'padroes_grupo': {
                'media_pares_quando_repete': media_pares_rep,
                'media_impares_quando_repete': media_impares_rep,
                'media_permanencia_apos_repeticao_pct': media_perm_global,
            },
            'ranking_mais_repetem': [
                {
                    'dezena': d,
                    'vezes': contagem_dezena_em_repeticao[d],
                    'pct': round(contagem_dezena_em_repeticao[d] / total_pares * 100, 2),
                }
                for d in ranking_freq
            ],
            'dezenas': dezenas_detalhe,
            'stats_dezenas': AnaliseRepeticaoConcursosService._build_stats_dezenas(),
        }

    @staticmethod
    def comparar_concursos(
        concurso_a: Optional[int] = None,
        concurso_b: Optional[int] = None,
        modo: str = 'volante',
    ) -> Dict[str, Any]:
        """Comparação visual entre dois concursos (sorteio real, sem gerador)."""
        modo = modo if modo in ('volante', 'posicional', 'hibrido') else 'volante'
        sorteios = AnaliseRepeticaoConcursosService._carregar_sorteios_asc()
        if len(sorteios) < 2:
            return {'sucesso': False, 'erro': 'É necessário ao menos 2 concursos no banco.'}

        if concurso_a is None or concurso_b is None:
            if concurso_a is None:
                concurso_a = sorteios[-2].concurso
            if concurso_b is None:
                concurso_b = sorteios[-1].concurso

        s_a = db.session.get(SorteioLotofacil, int(concurso_a))
        s_b = db.session.get(SorteioLotofacil, int(concurso_b))
        if not s_a or not s_b:
            return {'sucesso': False, 'erro': 'Concurso não encontrado.'}
        if s_a.concurso == s_b.concurso:
            return {'sucesso': False, 'erro': 'Selecione dois concursos diferentes.'}

        if s_a.concurso > s_b.concurso:
            s_a, s_b = s_b, s_a

        set_a = set(s_a.dezenas())
        set_b = set(s_b.dezenas())
        rep_v = sorted(set_a & set_b)
        rep_pos = AnaliseRepeticaoConcursosService._repetidas_posicional(s_a, s_b)
        rep_pos_dezenas = {x['dezena'] for x in rep_pos}
        pares, impares = _pares_impares(rep_v)

        pos_map_a = {d: i for i, d in enumerate(s_a.dezenas(), start=1)}
        pos_map_b = {d: i for i, d in enumerate(s_b.dezenas(), start=1)}

        grade = []
        for d in range(1, UNIVERSO + 1):
            grade.append({
                'dezena': d,
                'em_a': d in set_a,
                'em_b': d in set_b,
                'repetiu_volante': d in rep_v,
                'repetiu_posicional': d in rep_pos_dezenas,
                'posicao_a': pos_map_a.get(d),
                'posicao_b': pos_map_b.get(d),
            })

        def _pack(s: SorteioLotofacil) -> Dict[str, Any]:
            return {
                'concurso': s.concurso,
                'data': s.data,
                'dezenas': s.dezenas(),
            }

        return {
            'sucesso': True,
            'modo': modo,
            'concurso_a': _pack(s_a),
            'concurso_b': _pack(s_b),
            'resumo': {
                'volante': {
                    'quantidade': len(rep_v),
                    'dezenas': rep_v,
                    'pares': pares,
                    'impares': impares,
                },
                'posicional': {
                    'quantidade': len(rep_pos),
                    'detalhe': rep_pos,
                },
            },
            'grade': grade,
        }

    @staticmethod
    def _pool_dezenas(
        analise: Dict[str, Any],
        modo: str,
        usar_ultimo_par: bool,
        so_permanencia: bool,
        jitter: float = 0.0,
    ) -> List[Tuple[int, float]]:
        """Pesos para as 25 dezenas. Priorizar repetidas = bônus de peso, não cortar o universo."""
        pesos: List[Tuple[int, float]] = []
        media_perm = analise['padroes_grupo']['media_permanencia_apos_repeticao_pct']

        for row in analise['dezenas']:
            d = row['dezena']
            w = row['freq_repeticao_pct'] * 0.35 + row['permanencia_pct'] * 0.45 + jitter

            rep_vol = row['repetiu_ultimo_par_volante']
            rep_pos = row['repetiu_ultimo_par_posicional']
            if usar_ultimo_par:
                if modo == 'volante' and rep_vol:
                    w += 45
                elif modo == 'posicional' and rep_pos:
                    w += 42
                elif modo == 'hibrido' and (rep_vol or rep_pos):
                    w += 44
                else:
                    w += 4

            if so_permanencia:
                if row['tendencia'] == 'permanencia':
                    w += 25
                elif row['tendencia'] == 'saida':
                    w *= 0.12
                else:
                    w *= 0.45

            if row['tendencia'] == 'permanencia':
                w += 12
            elif row['tendencia'] == 'saida':
                w -= 8

            if row['permanencia_pct'] > media_perm:
                w += 5

            pesos.append((d, max(0.5, w)))

        return pesos

    @staticmethod
    def _sorteio_ponderado_sem_repeticao(
        pesos: List[Tuple[int, float]], k: int,
    ) -> List[int]:
        """Escolhe k dezenas distintas por sorteio ponderado."""
        pool = list(pesos)
        escolhidas: List[int] = []
        while len(escolhidas) < k and pool:
            total_w = sum(w for _, w in pool)
            r = random.random() * total_w
            acc = 0.0
            idx_pick = len(pool) - 1
            for i, (d, w) in enumerate(pool):
                acc += w
                if r <= acc:
                    idx_pick = i
                    break
            d, _ = pool.pop(idx_pick)
            escolhidas.append(d)
        return escolhidas

    @staticmethod
    def _ajustar_par_impar(
        escolhidas: List[int],
        k: int,
        alvo_pares: int,
        candidatos: List[int],
    ) -> List[int]:
        escolhidas = list(escolhidas)
        while len(escolhidas) < k:
            restantes = [c for c in candidatos if c not in escolhidas]
            if not restantes:
                break
            random.shuffle(restantes)
            escolhidas.append(restantes[0])
        escolhidas = escolhidas[:k]

        def n_pares(lst):
            return sum(1 for x in lst if x % 2 == 0)

        tent = 0
        while n_pares(escolhidas) != alvo_pares and tent < 80 and len(escolhidas) == k:
            tent += 1
            pares_idx = [i for i, x in enumerate(escolhidas) if x % 2 == 0]
            imp_idx = [i for i, x in enumerate(escolhidas) if x % 2 != 0]
            if n_pares(escolhidas) < alvo_pares and imp_idx:
                for c in candidatos:
                    if c % 2 == 0 and c not in escolhidas:
                        escolhidas[imp_idx[0]] = c
                        break
            elif n_pares(escolhidas) > alvo_pares and pares_idx:
                for c in candidatos:
                    if c % 2 != 0 and c not in escolhidas:
                        escolhidas[pares_idx[0]] = c
                        break
            else:
                break
        return sorted(escolhidas)

    @staticmethod
    def gerar_apostas(
        quantidade: int = 10,
        dezenas_por_jogo: int = 15,
        modo: str = 'volante',
        perfil: str = 'equilibrado',
        usar_ultimo_par: bool = True,
        so_permanencia: bool = False,
        respeitar_par_impar: bool = True,
        analise: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if analise is None:
            analise = AnaliseRepeticaoConcursosService.analisar_completo(modo)
        if not analise.get('sucesso'):
            return analise

        k = max(DEZENAS_MIN, min(int(dezenas_por_jogo), DEZENAS_MAX))
        quantidade = max(1, min(int(quantidade), 200))

        rep_vol = analise['resumo_ultimo_par']['volante']['dezenas']
        alvo_pares = analise['resumo_ultimo_par']['volante']['pares']
        if respeitar_par_impar and not rep_vol:
            alvo_pares = round(analise['padroes_grupo']['media_pares_quando_repete'])

        pesos = AnaliseRepeticaoConcursosService._pool_dezenas(
            analise, modo, usar_ultimo_par, so_permanencia,
        )

        universo = list(range(1, UNIVERSO + 1))

        apostas = []
        vistos = set()
        tentativas = 0
        max_tent = max(quantidade * 400, 800)

        while len(apostas) < quantidade and tentativas < max_tent:
            tentativas += 1
            jitter = random.random() * 12
            pesos_tent = AnaliseRepeticaoConcursosService._pool_dezenas(
                analise, modo, usar_ultimo_par, so_permanencia, jitter=jitter,
            )

            if perfil == 'conservador':
                pesos_tent = sorted(pesos_tent, key=lambda x: -x[1])
            elif perfil == 'agressivo':
                pesos_tent = sorted(
                    pesos_tent,
                    key=lambda x: x[1] + random.random() * 25,
                )
            else:
                random.shuffle(pesos_tent)

            pick = AnaliseRepeticaoConcursosService._sorteio_ponderado_sem_repeticao(
                pesos_tent, k,
            )

            if len(pick) < k:
                continue

            if respeitar_par_impar:
                pick = AnaliseRepeticaoConcursosService._ajustar_par_impar(
                    pick, k, alvo_pares, universo,
                )
            else:
                pick = sorted(pick)

            chave = tuple(pick)
            if len(pick) != k or chave in vistos:
                continue
            vistos.add(chave)

            do_ultimo = len(set(pick) & set(rep_vol))
            p, im = _pares_impares(pick)
            apostas.append({
                'numero': len(apostas) + 1,
                'dezenas': pick,
                'quantidade': k,
                'pares': p,
                'impares': im,
                'do_ultimo_par': do_ultimo,
                'texto': ' '.join(f'{n:02d}' for n in pick),
            })

        aviso = None
        if len(apostas) < quantidade:
            aviso = (
                f'Solicitados {quantidade} apostas; gerados {len(apostas)}. '
                'Tente desmarcar filtros restritivos ou mude o perfil.'
            )

        return {
            'sucesso': True,
            'apostas': apostas,
            'total_geradas': len(apostas),
            'solicitados': quantidade,
            'aviso': aviso,
            'parametros': {
                'quantidade': quantidade,
                'dezenas_por_jogo': k,
                'modo': modo,
                'perfil': perfil,
                'usar_ultimo_par': usar_ultimo_par,
                'so_permanencia': so_permanencia,
                'respeitar_par_impar': respeitar_par_impar,
            },
        }
