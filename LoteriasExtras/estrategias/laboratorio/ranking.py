from laboratorio.config import PRIZE_TIERS, GAME_COST, DRAW_NUMBERS
from laboratorio.analyzer import dezenas_of


class LotteryRanking:
    PRIZES = {k: v["reward"] for k, v in PRIZE_TIERS.items()}
    COST_PER_GAME = GAME_COST

    @staticmethod
    def evaluate_strategy(games, real_results):
        total_spent = len(games) * LotteryRanking.COST_PER_GAME
        total_won = 0
        hits_count = {i: 0 for i in range(DRAW_NUMBERS + 1)}
        sample = real_results[-50:]
        for res in sample:
            res_nums = set(dezenas_of(res))
            for game in games:
                hits = len(set(game).intersection(res_nums))
                hits_count[hits] = hits_count.get(hits, 0) + 1
                total_won += LotteryRanking.PRIZES.get(hits, 0)
        denom = len(games) * max(1, min(50, len(real_results)))
        avg_hits = sum(k * v for k, v in hits_count.items()) / denom if games and real_results else 0
        high_prizes = sum(hits_count.get(h, 0) for h in LotteryRanking.PRIZES)
        return {
            "high_prizes": high_prizes,
            "avg_hits": avg_hits,
            "financial_return": total_won - total_spent,
            "hits_summary": hits_count,
        }

    @staticmethod
    def rank_strategies(strategies_results, criterion):
        return sorted(
            strategies_results.items(),
            key=lambda x: x[1].get(criterion, 0),
            reverse=True,
        )
