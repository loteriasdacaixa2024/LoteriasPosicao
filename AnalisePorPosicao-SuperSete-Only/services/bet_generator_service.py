"""
bet_generator_service.py
========================
Gerador de apostas inteligente para Super Sete.

Super Sete: 7 colunas independentes, cada coluna sorteia 1 dígito (0-9).
Uma aposta = escolher 1 dígito por coluna = 7 dígitos.

O gerador utiliza dados das análises já calculadas:
  - Dígitos frequentes por coluna
  - Dígitos atrasados por coluna
  - Último resultado
  - Repetições entre sorteios
"""

import random
from typing import List, Dict, Any, Optional


class BetGeneratorSuperSete:
    """Gera apostas para Super Sete baseado em análise estatística."""

    @staticmethod
    def generate(
        analise: Dict,
        last_draw: List[int],
        qty_games: int = 5,
        fixed: Optional[Dict[int, int]] = None,
        excluded: Optional[Dict[int, List[int]]] = None,
        min_repetitions: int = 0,
        max_repetitions: int = 7,
        strategy: str = 'balanced'
    ) -> List[Dict[str, Any]]:
        """
        Gera apostas para Super Sete.

        Args:
            analise: Dict com análise por coluna (resultado de analise_por_coluna())
            last_draw: Lista com 7 dígitos do último sorteio [c1, c2, ..., c7]
            qty_games: Quantidade de jogos a gerar
            fixed: Dict {coluna: digito} — dígitos fixos por coluna (1-indexed)
            excluded: Dict {coluna: [digitos]} — dígitos excluídos por coluna
            min_repetitions: Mínimo de repetições do último sorteio
            max_repetitions: Máximo de repetições do último sorteio
            strategy: 'balanced' | 'frequent' | 'delayed' | 'random'

        Returns:
            Lista de dicts com: numbers, sum, pairs, odds, repetitions, frequent_used, delayed_used, strategy_info
        """
        if not analise:
            return []

        fixed = fixed or {}
        excluded = excluded or {}
        generated = []
        attempts = 0
        max_attempts = qty_games * 200

        while len(generated) < qty_games and attempts < max_attempts:
            attempts += 1
            combo = []
            freq_used = 0
            delay_used = 0
            strategy_details = []

            for col in range(1, 8):
                # Se há dígito fixo para esta coluna, usa ele
                if col in fixed:
                    combo.append(fixed[col])
                    strategy_details.append(f"C{col}: {fixed[col]} (fixo)")
                    continue

                # Pool de dígitos disponíveis (0-9 menos excluídos)
                col_excluded = set(excluded.get(col, []))
                pool = [d for d in range(10) if d not in col_excluded]

                if not pool:
                    pool = list(range(10))  # fallback

                col_data = analise.get(col, {})
                rank_freq = col_data.get('rank_freq', list(range(10)))
                rank_atraso = col_data.get('rank_atraso', list(range(10)))

                # Filtrar pelos disponíveis
                freq_pool = [d for d in rank_freq if d in pool]
                delay_pool = [d for d in rank_atraso if d in pool]

                if strategy == 'frequent':
                    # Pega do top 3 frequentes
                    top = freq_pool[:3] if freq_pool else pool
                    chosen = random.choice(top)
                    strategy_details.append(f"C{col}: {chosen} (freq)")
                elif strategy == 'delayed':
                    # Pega do top 3 atrasados
                    top = delay_pool[:3] if delay_pool else pool
                    chosen = random.choice(top)
                    strategy_details.append(f"C{col}: {chosen} (atraso)")
                elif strategy == 'balanced':
                    # Alterna: colunas ímpares = frequentes, pares = atrasados
                    if col % 2 == 1:
                        top = freq_pool[:4] if freq_pool else pool
                    else:
                        top = delay_pool[:4] if delay_pool else pool
                    chosen = random.choice(top)
                    strategy_details.append(f"C{col}: {chosen} (bal)")
                else:  # random
                    chosen = random.choice(pool)
                    strategy_details.append(f"C{col}: {chosen} (rand)")

                combo.append(chosen)

                # Contabilizar uso
                if freq_pool and chosen in freq_pool[:3]:
                    freq_used += 1
                if delay_pool and chosen in delay_pool[:3]:
                    delay_used += 1

            # Validar repetições
            reps = sum(1 for i in range(7) if i < len(last_draw) and combo[i] == last_draw[i])
            if reps < min_repetitions or reps > max_repetitions:
                continue

            # Evitar duplicatas
            combo_tuple = tuple(combo)
            if any(tuple(g['numbers']) == combo_tuple for g in generated):
                continue

            evens = sum(1 for d in combo if d % 2 == 0)
            odds = 7 - evens

            bet = {
                "numbers": combo,
                "sum": sum(combo),
                "pairs": evens,
                "odds": odds,
                "repetitions": reps,
                "frequent_used": freq_used,
                "delayed_used": delay_used,
                "strategy_info": strategy_details,
            }
            generated.append(bet)

        return generated
