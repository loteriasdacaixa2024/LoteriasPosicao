"""
modelos_service.py
==================
Serviço de Geração pelos 6 Modelos Estratégicos para Lotofácil (15 dezenas).

Escala dos modelos originais (7 componentes / Dia de Sorte)
para Lotofácil (15 dezenas):

MODELO 1 — Conservador
  Original : 2A + 2F + 2FIX + 1VAR  = 7
  Lotofácil: 4A + 4F + 4FIX + 3VAR  = 15

MODELO 2 — Atraso Controlado
  Original : 3A + 2F + 1FIX + 1VAR  = 7
  Lotofácil: 6A + 4F + 2FIX + 3VAR  = 15

MODELO 3 — Núcleo Forte
  Original : 4FIX + 1A + 1F + 1VAR  = 7
  Lotofácil: 8FIX + 2A + 2F + 3VAR  = 15

MODELO 4 — Rotação Inteligente
  Original : 2A + 2QA + 2FIX + 1VAR = 7
  Lotofácil: 4A + 4QA + 4FIX + 3VAR = 15

MODELO 5 — Frequência Dominante
  Original : 3F + 2N + 1A + 1VAR    = 7
  Lotofácil: 6F + 4N + 2A + 3VAR    = 15

MODELO 6 — Ciclo Anterior (NOVO)
  Baseia-se no padrão estatístico de que 7-10 dezenas do concurso
  anterior sempre se repetem. Usa 8 dezenas do último sorteio como
  âncora + 4 atrasados posicionais + 3 variáveis.
  Lotofácil: 8ANT + 4A + 3VAR = 15
"""

import random
from models.shared import db
from models.sorteio_lotofacil import SorteioLotofacil
from sqlalchemy import desc

# ---------------------------------------------------------------------------
# DEFINIÇÕES DOS MODELOS
# ---------------------------------------------------------------------------
MODELOS = {
    1: {
        "nome": "Conservador",
        "emoji": "🔹",
        "subtitulo": "Equilíbrio forte — ideal pra consistência",
        "cor": "#1a6e3c",
        "qtd_atrasados": 4,
        "qtd_frequentes": 4,
        "qtd_fixos": 4,
        "qtd_quasi_atrasados": 0,
        "qtd_neutros": 0,
        "qtd_variaveis": 3,
        "estrutura": "4A + 4F + 4FIX + 3VAR",
    },
    2: {
        "nome": "Atraso Controlado",
        "emoji": "🔸",
        "subtitulo": "Apostando nos atrasados sem exagerar",
        "cor": "#c47a1e",
        "qtd_atrasados": 6,
        "qtd_frequentes": 4,
        "qtd_fixos": 2,
        "qtd_quasi_atrasados": 0,
        "qtd_neutros": 0,
        "qtd_variaveis": 3,
        "estrutura": "6A + 4F + 2FIX + 3VAR",
    },
    3: {
        "nome": "Núcleo Forte",
        "emoji": "🔥",
        "subtitulo": "Máxima concentração — o mais poderoso",
        "cor": "#8b1a1a",
        "qtd_atrasados": 2,
        "qtd_frequentes": 2,
        "qtd_fixos": 8,
        "qtd_quasi_atrasados": 0,
        "qtd_neutros": 0,
        "qtd_variaveis": 3,
        "estrutura": "8FIX + 2A + 2F + 3VAR",
    },
    4: {
        "nome": "Rotação Inteligente",
        "emoji": "🔄",
        "subtitulo": "Usa posição e quasi-atrasados do jeito certo",
        "cor": "#1a3a8b",
        "qtd_atrasados": 4,
        "qtd_frequentes": 0,
        "qtd_fixos": 4,
        "qtd_quasi_atrasados": 4,
        "qtd_neutros": 0,
        "qtd_variaveis": 3,
        "estrutura": "4A + 4QA + 4FIX + 3VAR",
    },
    5: {
        "nome": "Frequência Dominante",
        "emoji": "📈",
        "subtitulo": "Fugindo do risco — frequentes no comando",
        "cor": "#5a1a8b",
        "qtd_atrasados": 2,
        "qtd_frequentes": 6,
        "qtd_fixos": 0,
        "qtd_quasi_atrasados": 0,
        "qtd_neutros": 4,
        "qtd_variaveis": 3,
        "estrutura": "6F + 4N + 2A + 3VAR",
    },
    6: {
        "nome": "Ciclo Anterior",
        "emoji": "♻️",
        "subtitulo": "8-9 dezenas do concurso anterior tendêm a repetir",
        "cor": "#1a5c6e",
        "qtd_atrasados": 4,     # complemento positional
        "qtd_frequentes": 0,
        "qtd_fixos": 0,
        "qtd_quasi_atrasados": 0,
        "qtd_neutros": 0,
        "qtd_variaveis": 3,
        "qtd_anterior": 8,      # dezenas ancora do último sorteio
        "estrutura": "8ANT + 4A + 3VAR",
    },
}

NUM_APOSTAS = 24   # apostas por modelo
UNIVERSO     = 25  # dezenas 01..25


class ModelosService:
    # -----------------------------------------------------------------------
    # DADOS BASE: ranking por atraso e frequência
    # -----------------------------------------------------------------------
    @staticmethod
    def _build_base_rankings():
        """
        Retorna, para o banco de dados atual:
          - ranking_atraso : lista de dezenas (1..25) ordenadas por maior atraso global
          - ranking_freq   : lista de dezenas (1..25) ordenadas por maior frequência global
        O atraso global é simples: quantos concursos a dezena NÃO saiu desde a última vez que saiu.
        A frequência global é: quantas vezes a dezena apareceu no histórico total.
        """
        sorteios = db.session.query(SorteioLotofacil).order_by(
            desc(SorteioLotofacil.concurso)
        ).all()

        if not sorteios:
            return None, None, None

        ultimo_concurso = sorteios[0].concurso
        total_sorteios  = len(sorteios)

        # Frequência e último concurso visto por dezena
        freq    = {d: 0  for d in range(1, UNIVERSO + 1)}
        visto   = {d: 0  for d in range(1, UNIVERSO + 1)}  # concurso mais recente

        for s in sorteios:
            for d in s.dezenas():
                freq[d] += 1
                if visto[d] == 0:
                    visto[d] = s.concurso

        atraso_global = {}
        for d in range(1, UNIVERSO + 1):
            if visto[d] == 0:
                atraso_global[d] = ultimo_concurso  # nunca saiu
            else:
                atraso_global[d] = ultimo_concurso - visto[d]

        # De maior atraso → menor atraso  (1ª posição = mais atrasado)
        ranking_atraso = sorted(range(1, UNIVERSO + 1), key=lambda d: -atraso_global[d])
        # De maior frequência → menor frequência
        ranking_freq   = sorted(range(1, UNIVERSO + 1), key=lambda d: -freq[d])
        # "Neutros" = frequência mediana → meio da lista de frequência
        # Pega índices 8..16 do ranking_freq (meio do universo 25)
        ranking_neutro = ranking_freq[8:18]

        return ranking_atraso, ranking_freq, ranking_neutro, atraso_global, freq, ultimo_concurso, total_sorteios

    @staticmethod
    def _get_ultimo_sorteio_dezenas():
        """
        Retorna as dezenas do último concurso na ordem original (sem sort).
        Usado exclusivamente pelo Modelo 6.
        """
        ultimo = db.session.query(SorteioLotofacil).order_by(
            desc(SorteioLotofacil.concurso)
        ).first()
        if not ultimo:
            return []
        return list(ultimo.dezenas())  # ordem exata do globo (NUNCA sorted)

    # -----------------------------------------------------------------------
    # SELEÇÃO DE DEZENAS PARA UM MODELO
    # -----------------------------------------------------------------------
    @staticmethod
    def _selecionar_pool(modelo_id: int, rank_atraso, rank_freq, rank_neutro):
        """
        Devolve dicionário com os pools para cada categoria do modelo.
        Quasi-atrasados = 2º e 3º da fila de atraso (posições 4..12 do ranking).
        Fixos = intersecção dos mais atrasados COM os mais frequentes
                (os que aparecem nos top-N de ambos os rankings).
        """
        cfg = MODELOS[modelo_id]

        # Pool FIXOS: top-N que aparecem tanto no top-12 atraso como top-12 freq
        top_atraso_set = set(rank_atraso[:14])
        top_freq_set   = set(rank_freq[:14])
        pool_fixos     = [d for d in rank_atraso if d in top_atraso_set & top_freq_set]
        if len(pool_fixos) < cfg["qtd_fixos"]:
            # completa com mais atrasados caso necessário
            for d in rank_atraso:
                if d not in pool_fixos:
                    pool_fixos.append(d)
                if len(pool_fixos) >= max(cfg["qtd_fixos"] + 4, 10):
                    break

        # Pool ATRASADOS: os mais atrasados (exceto os já nos fixos se possível)
        pool_atrasados = [d for d in rank_atraso if d not in pool_fixos[:cfg["qtd_fixos"]]]

        # Pool QUASI-ATRASADOS: posições 5..15 do ranking de atraso
        pool_quasi = rank_atraso[4:16]

        # Pool FREQUENTES: os mais frequentes (exceto os fixos)
        pool_freq  = [d for d in rank_freq if d not in pool_fixos[:cfg["qtd_fixos"]]]

        # Pool NEUTROS: ranking_neutro
        pool_neutro = rank_neutro

        # Pool VARIÁVEIS: todo o universo (candidatos de menor prioridade)
        pool_var = list(range(1, UNIVERSO + 1))

        return {
            "fixos":     pool_fixos,
            "atrasados": pool_atrasados,
            "quasi":     pool_quasi,
            "freq":      pool_freq,
            "neutro":    pool_neutro,
            "var":       pool_var,
        }

    # -----------------------------------------------------------------------
    # MODELO 6: geração especial com âncora do concurso anterior
    # -----------------------------------------------------------------------
    @staticmethod
    def _gerar_aposta_m6(dezenas_anterior, rank_atraso, seed_offset: int):
        """
        Monta uma aposta do Modelo 6:
          - 8 dezenas âncora sorteadas aleatoriamente das 15 do concurso anterior
          - 4 dezenas das mais atrasadas que NÃO estão na âncora
          - 3 dezenas variáveis do universo restante
        Total = 15 dezenas únicas.
        """
        rng = random.Random(seed_offset)

        # 1) Âncora: sorteia 8 das 15 do concurso anterior
        anterior_shuffled = dezenas_anterior[:]
        rng.shuffle(anterior_shuffled)
        ancora = set(anterior_shuffled[:8])

        dezenas = list(ancora)
        usadas  = set(ancora)

        # 2) Atrasados que não estão na âncora
        atrasados_excl = [d for d in rank_atraso if d not in usadas]
        rng.shuffle(atrasados_excl[:8])  # shuffle dos top-8 para diversidade
        for d in atrasados_excl:
            if len(dezenas) >= 12:
                break
            dezenas.append(d)
            usadas.add(d)

        # 3) Variáveis: qualquer dezena restante
        variaveis = [d for d in range(1, UNIVERSO + 1) if d not in usadas]
        rng.shuffle(variaveis)
        for d in variaveis:
            if len(dezenas) >= 15:
                break
            dezenas.append(d)
            usadas.add(d)

        dezenas_ord = sorted(dezenas[:15])
        return [f"{d:02d}" for d in dezenas_ord]

    # -----------------------------------------------------------------------
    # GERAR UMA ÚNICA APOSTA (modelos 1-5)
    # -----------------------------------------------------------------------
    @staticmethod
    def _gerar_uma_aposta(cfg, pools, seed_offset: int):
        """
        Monta uma aposta de 15 dezenas únicas conforme a estrutura do modelo.
        seed_offset varia para garantir diversidade entre as 24 apostas.
        """
        rng = random.Random(seed_offset)

        dezenas = []
        usadas  = set()

        def pegar(pool, qtd, shuffle=True):
            candidatos = [d for d in pool if d not in usadas]
            if shuffle:
                candidatos = candidatos[:]
                rng.shuffle(candidatos)
            selecionados = candidatos[:qtd]
            dezenas.extend(selecionados)
            usadas.update(selecionados)

        pegar(pools["fixos"],     cfg["qtd_fixos"],           shuffle=False)
        pegar(pools["atrasados"], cfg["qtd_atrasados"],        shuffle=True)
        pegar(pools["quasi"],     cfg["qtd_quasi_atrasados"],  shuffle=True)
        pegar(pools["freq"],      cfg["qtd_frequentes"],       shuffle=True)
        pegar(pools["neutro"],    cfg["qtd_neutros"],          shuffle=True)
        pegar(pools["var"],       cfg["qtd_variaveis"],        shuffle=True)

        # Garantir exatamente 15 dezenas únicas
        dezenas_unicas = list(dict.fromkeys(dezenas))  # preserva ordem, sem dup.
        if len(dezenas_unicas) < 15:
            for d in range(1, 26):
                if d not in usadas:
                    dezenas_unicas.append(d)
                    usadas.add(d)
                if len(dezenas_unicas) == 15:
                    break

        dezenas_unicas = dezenas_unicas[:15]
        dezenas_ord    = sorted(dezenas_unicas)
        dezenas_fmt    = [f"{d:02d}" for d in dezenas_ord]
        return dezenas_fmt

    # -----------------------------------------------------------------------
    # GERAR 24 APOSTAS DE UM MODELO
    # -----------------------------------------------------------------------
    @staticmethod
    def gerar_apostas_modelo(modelo_id: int):
        result = ModelosService._build_base_rankings()
        if result[0] is None:
            return {"error": "Sem dados no banco de dados."}

        rank_atraso, rank_freq, rank_neutro, atraso_global, freq, ultimo_concurso, total_sorteios = result
        cfg = MODELOS[modelo_id]

        # ══ MODELO 6: lógica especial de ciclo anterior ══
        if modelo_id == 6:
            dezenas_anterior = ModelosService._get_ultimo_sorteio_dezenas()
            if not dezenas_anterior:
                return {"error": "Não foi possível obter o último sorteio."}

            apostas = []
            vistos  = set()
            tentativas = 0
            while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 15:
                dez = ModelosService._gerar_aposta_m6(
                    dezenas_anterior, rank_atraso,
                    seed_offset=tentativas + 6000
                )
                chave = tuple(dez)
                if chave not in vistos:
                    vistos.add(chave)
                    apostas.append({
                        "aposta_num":        len(apostas) + 1,
                        "dezenas_formatadas": dez,
                        "tamanho":            len(dez),
                    })
                tentativas += 1

            pool_info = {
                "fixos_exibicao":  [f"{d:02d}" for d in dezenas_anterior],
                "atrasados_top5": [f"{d:02d}" for d in rank_atraso[:5]],
                "freq_top5":      [f"{d:02d}" for d in rank_freq[:5]],
            }
            return {
                "modelo_id":       6,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "ultimo_concurso": ultimo_concurso,
                "total_geradas":   len(apostas),
                "apostas":         apostas,
                "pool_info":       pool_info,
            }

        # ══ MODELOS 1-5: lógica padrão ══
        pools = ModelosService._selecionar_pool(modelo_id, rank_atraso, rank_freq, rank_neutro)

        apostas = []
        vistos  = set()

        tentativas = 0
        while len(apostas) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 10:
            dez = ModelosService._gerar_uma_aposta(cfg, pools, seed_offset=tentativas + modelo_id * 1000)
            chave = tuple(dez)
            if chave not in vistos:
                vistos.add(chave)
                apostas.append({
                    "aposta_num":        len(apostas) + 1,
                    "dezenas_formatadas": dez,
                    "tamanho":           len(dez),
                })
            tentativas += 1

        pool_info = {
            "fixos_exibicao":  [f"{d:02d}" for d in pools["fixos"][:cfg["qtd_fixos"] + 2]],
            "atrasados_top5": [f"{d:02d}" for d in pools["atrasados"][:5]],
            "freq_top5":      [f"{d:02d}" for d in pools["freq"][:5]],
        }

        return {
            "modelo_id":      modelo_id,
            "modelo_nome":    cfg["nome"],
            "modelo_emoji":   cfg["emoji"],
            "estrutura":      cfg["estrutura"],
            "ultimo_concurso": ultimo_concurso,
            "total_geradas":  len(apostas),
            "apostas":        apostas,
            "pool_info":      pool_info,
        }

    # -----------------------------------------------------------------------
    # BACKTESTING: qual modelo mais pontuou no passado?
    # -----------------------------------------------------------------------
    @staticmethod
    def backtesting_modelos():
        """
        Para cada um dos 5 modelos, gera as 24 apostas (determinísticas via seed)
        e verifica quantos acertos cada aposta teria tido em TODA a base histórica.
        Retorna um ranking dos modelos por prêmios acumulados (11-15 acertos).
        """
        result = ModelosService._build_base_rankings()
        if result[0] is None:
            return {"error": "Sem dados no banco de dados."}

        rank_atraso, rank_freq, rank_neutro, atraso_global, freq, ultimo_concurso, total_sorteios = result

        # Carrega todos os sorteios uma única vez
        sorteios = db.session.query(SorteioLotofacil).all()
        sorteios_sets = [
            (s.concurso, s.data, set(s.dezenas()))
            for s in sorteios
        ]

        ranking_modelos = []

        for modelo_id in range(1, 7):  # inclui M6
            cfg   = MODELOS[modelo_id]

            # M6 usa lógica própria
            if modelo_id == 6:
                dezenas_anterior = ModelosService._get_ultimo_sorteio_dezenas()
                if not dezenas_anterior:
                    continue
                apostas_sets = []
                vistos = set()
                tentativas = 0
                while len(apostas_sets) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 15:
                    dez = ModelosService._gerar_aposta_m6(
                        dezenas_anterior, rank_atraso,
                        seed_offset=tentativas + 6000
                    )
                    chave = tuple(dez)
                    if chave not in vistos:
                        vistos.add(chave)
                        apostas_sets.append(set(int(d) for d in dez))
                    tentativas += 1
            else:
                pools = ModelosService._selecionar_pool(modelo_id, rank_atraso, rank_freq, rank_neutro)
                apostas_sets = []
                vistos = set()
                tentativas = 0
                while len(apostas_sets) < NUM_APOSTAS and tentativas < NUM_APOSTAS * 10:
                    dez = ModelosService._gerar_uma_aposta(cfg, pools, seed_offset=tentativas + modelo_id * 1000)
                    chave = tuple(dez)
                    if chave not in vistos:
                        vistos.add(chave)
                        apostas_sets.append(set(int(d) for d in dez))
                    tentativas += 1

            # Counters
            hits = {15: 0, 14: 0, 13: 0, 12: 0, 11: 0}
            total_premios = 0
            melhor_concurso = None
            melhor_acerto = 0

            for concurso, data, sorteio_set in sorteios_sets:
                for aposta_set in apostas_sets:
                    acertos = len(aposta_set & sorteio_set)
                    if acertos >= 11:
                        hits[acertos if acertos <= 15 else 15] += 1
                        total_premios += 1
                        if acertos > melhor_acerto:
                            melhor_acerto   = acertos
                            melhor_concurso = concurso

            ranking_modelos.append({
                "modelo_id":       modelo_id,
                "modelo_nome":     cfg["nome"],
                "modelo_emoji":    cfg["emoji"],
                "estrutura":       cfg["estrutura"],
                "cor":             cfg["cor"],
                "total_premios":   total_premios,
                "hits_15":         hits[15],
                "hits_14":         hits[14],
                "hits_13":         hits[13],
                "hits_12":         hits[12],
                "hits_11":         hits[11],
                "melhor_acerto":   melhor_acerto,
                "melhor_concurso": melhor_concurso,
                "score":           hits[15]*100 + hits[14]*20 + hits[13]*5 + hits[12]*2 + hits[11],
            })

        # Ordena por score decrescente
        ranking_modelos.sort(key=lambda x: -x["score"])
        for i, m in enumerate(ranking_modelos):
            m["posicao"] = i + 1

        return {
            "ultimo_concurso":  ultimo_concurso,
            "total_sorteios":   total_sorteios,
            "ranking":          ranking_modelos,
        }

    # -----------------------------------------------------------------------
    # INFORMAÇÕES DE TODOS OS MODELOS (para listagem)
    # -----------------------------------------------------------------------
    @staticmethod
    def listar_modelos():
        return [
            {
                "id":        mid,
                "nome":      cfg["nome"],
                "emoji":     cfg["emoji"],
                "subtitulo": cfg["subtitulo"],
                "cor":       cfg["cor"],
                "estrutura": cfg["estrutura"],
            }
            for mid, cfg in MODELOS.items()
        ]
