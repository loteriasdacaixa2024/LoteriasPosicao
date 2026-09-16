import random
from laboratorio.analyzer import LotteryAnalyzer, dezenas_of
from laboratorio.config import DRAW_NUMBERS, NUMBER_MIN, NUMBER_MAX, GRID_COLS, GRID_ROWS


class LotteryStrategies:
    def __init__(self, historical_results):
        self.results = historical_results
        self.draw = DRAW_NUMBERS
        self.min_n = NUMBER_MIN
        self.max_n = NUMBER_MAX
        self.pool = list(range(self.min_n, self.max_n + 1))
        self.analyzer = LotteryAnalyzer()
        self.stats = self._get_base_stats()

    def _get_base_stats(self):
        if not self.results:
            return None
        return {
            "freq": self.analyzer.analyze_frequency(self.results),
            "struct": self.analyzer.analyze_structure(self.results),
            "comp": self.analyzer.analyze_composition(self.results),
            "rep": self.analyzer.analyze_repetition(self.results),
            "temporal": self.analyzer.analyze_temporal(self.results),
        }

    def _sample(self, source, k):
        k = min(k, len(source))
        if k <= 0:
            return []
        return random.sample(source, k)

    def _fill(self, selection):
        sel = set(selection)
        while len(sel) < self.draw:
            n = random.choice(self.pool)
            sel.add(n)
        return sorted(list(sel)[:self.draw])

    def strategy_1_balance(self):
        latest = set(dezenas_of(self.results[-1])) if self.results else set()
        target_par = max(1, self.draw // 2)
        for _ in range(80):
            selection = sorted(self._sample(self.pool, self.draw))
            pares = len([n for n in selection if n % 2 == 0])
            repetidos = len(set(selection).intersection(latest)) if latest else target_par
            if abs(pares - target_par) <= 1 and (not latest or abs(repetidos - target_par) <= max(2, self.draw // 4)):
                return selection
        return self._fill([])

    def strategy_2_frequency(self):
        freq_data = self.stats["freq"]["most_frequent"]
        top = [x[0] for x in freq_data[: max(3, self.draw // 2 + 2)]]
        mid = [x[0] for x in freq_data[len(top): len(top) + max(2, self.draw // 3)]]
        rest = [x[0] for x in freq_data[len(top) + len(mid):]]
        n_top = min(len(top), max(2, int(self.draw * 0.5)))
        n_mid = min(len(mid), max(1, self.draw - n_top - 1))
        n_rest = self.draw - n_top - n_mid
        selection = self._sample(top, n_top) + self._sample(mid, n_mid) + self._sample(rest, n_rest)
        return self._fill(selection)

    def strategy_3_delays(self):
        temporal = self.stats["temporal"]
        delayed = [n for n, a in temporal.items() if a > 0]
        not_delayed = [n for n, a in temporal.items() if a == 0]
        n_hot = min(len(not_delayed), max(1, self.draw // 2))
        selection = self._sample(not_delayed, n_hot)
        return self._fill(selection + self._sample(delayed, self.draw))

    def strategy_4_structure(self):
        cols = max(1, GRID_COLS)
        rows = max(1, GRID_ROWS)
        per_row = max(1, self.draw // rows)
        selection = []
        for i in range(rows):
            start = self.min_n + i * cols
            row_nums = [n for n in range(start, start + cols) if n <= self.max_n]
            if row_nums:
                selection += self._sample(row_nums, min(per_row, len(row_nums)))
        return self._fill(selection)

    def strategy_5_reduction(self, universe):
        if not universe or len(universe) < self.draw:
            universe = self.pool
        return sorted(self._sample(list(set(universe)), self.draw))

    def strategy_6_wheeling(self, wheeling_nums, wheeling_type):
        if not wheeling_nums or len(wheeling_nums) < self.draw:
            wheeling_nums = self.pool[: min(len(self.pool), self.draw + 3)]
        wheeling_nums = sorted(wheeling_nums)
        count = 24
        if wheeling_type and wheeling_type.startswith("19"):
            count = 30
        elif wheeling_type and wheeling_type.startswith("20"):
            count = 20
        games = []
        n = len(wheeling_nums)
        for i in range(count):
            indices = [(i + j) % n for j in range(self.draw)]
            games.append(sorted([wheeling_nums[idx] for idx in indices]))
        return games

    def strategy_7_fixed(self, fixed_nums):
        fixed_nums = list(fixed_nums or [])[: max(1, self.draw - 1)]
        available = [n for n in self.pool if n not in set(fixed_nums)]
        freq_data = self.stats["freq"]["most_frequent"]
        pool = [x[0] for x in freq_data if x[0] in available] or available
        selection = set(fixed_nums)
        while len(selection) < self.draw and pool:
            selection.add(random.choice(pool))
        return self._fill(selection)

    def strategy_8_trend(self):
        freq_top = [x[0] for x in self.stats["freq"]["most_frequent"][: max(self.draw, 8)]]
        temporal = self.stats["temporal"]
        trends = [n for n in freq_top if temporal.get(n, 0) >= 1]
        if len(trends) >= self.draw:
            return sorted(self._sample(trends, self.draw))
        return self._fill(trends)

    def strategy_9_topology(self):
        cols = max(1, GRID_COLS)
        moldura, centro = [], []
        for n in self.pool:
            idx = n - self.min_n
            r, c = idx // cols, idx % cols
            if r == 0 or c == 0 or c == cols - 1 or n + cols > self.max_n:
                moldura.append(n)
            else:
                centro.append(n)
        if not centro:
            centro = moldura[:]
        q_m = min(len(moldura), max(1, int(self.draw * 0.6)))
        return self._fill(self._sample(moldura, q_m) + self._sample(centro, self.draw))

    def strategy_10_affinity(self):
        freq_top = [x[0] for x in self.stats["freq"]["most_frequent"][:5]] or self.pool[:5]
        ancora = random.choice(freq_top)
        afinidades = {n: 0 for n in self.pool}
        for draw in self.results:
            dezenas = dezenas_of(draw)
            if ancora in dezenas:
                for d in dezenas:
                    if d != ancora:
                        afinidades[d] = afinidades.get(d, 0) + 1
        sorted_af = sorted(afinidades.keys(), key=lambda k: afinidades[k], reverse=True)
        return self._fill([ancora] + sorted_af[: self.draw])

    def strategy_11_inversion(self):
        freq_data = self.stats["freq"]["most_frequent"]
        cut = max(3, len(freq_data) // 3)
        top = [x[0] for x in freq_data[:cut]]
        bottom = [x[0] for x in freq_data[cut:]] or top
        n_bottom = min(len(bottom), max(1, int(self.draw * 0.7)))
        return self._fill(self._sample(bottom, n_bottom) + self._sample(top, self.draw))

    def generate_games(self, strategy_id, count, universe=None, fixed_numbers=None, wheeling_numbers=None, wheeling_type=None):
        if strategy_id == 6:
            all_games = self.strategy_6_wheeling(wheeling_numbers, wheeling_type)
            return [all_games[i % len(all_games)] for i in range(count)]
        strategy_map = {
            1: self.strategy_1_balance,
            2: self.strategy_2_frequency,
            3: self.strategy_3_delays,
            4: self.strategy_4_structure,
            5: lambda: self.strategy_5_reduction(universe),
            7: lambda: self.strategy_7_fixed(fixed_numbers),
            8: self.strategy_8_trend,
            9: self.strategy_9_topology,
            10: self.strategy_10_affinity,
            11: self.strategy_11_inversion,
        }
        func = strategy_map.get(strategy_id, self.strategy_1_balance)
        return [func() for _ in range(count)]
