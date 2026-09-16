from collections import Counter
from laboratorio.config import DRAW_NUMBERS, NUMBER_MIN, NUMBER_MAX, GRID_COLS, GRID_ROWS


def dezenas_of(res, draw_n=DRAW_NUMBERS):
    if res.get("dezenas") and isinstance(res["dezenas"], (list, tuple)):
        return list(res["dezenas"])
    return [res[f"dezena{i}"] for i in range(1, draw_n + 1) if res.get(f"dezena{i}") is not None]


class LotteryAnalyzer:
    @staticmethod
    def analyze_frequency(results):
        all_numbers = []
        for res in results:
            all_numbers.extend(dezenas_of(res))
        counts = Counter(all_numbers)
        frequencies = {i: counts.get(i, 0) for i in range(NUMBER_MIN, NUMBER_MAX + 1)}
        recent_results = results[-10:] if len(results) >= 10 else results
        recent_numbers = []
        for res in recent_results:
            recent_numbers.extend(dezenas_of(res))
        recent_counts = Counter(recent_numbers)
        recent_frequencies = {i: recent_counts.get(i, 0) for i in range(NUMBER_MIN, NUMBER_MAX + 1)}
        return {
            "historical": frequencies,
            "recent": recent_frequencies,
            "most_frequent": sorted(frequencies.items(), key=lambda x: x[1], reverse=True),
            "least_frequent": sorted(frequencies.items(), key=lambda x: x[1]),
        }

    @staticmethod
    def analyze_structure(results):
        lines_analysis = []
        cols_analysis = []
        all_nums_freq = Counter()
        cols = max(1, GRID_COLS)
        rows = max(1, GRID_ROWS)
        for res in results:
            dezenas = dezenas_of(res)
            all_nums_freq.update(dezenas)
            line_counts = [0] * rows
            col_counts = [0] * cols
            for d in dezenas:
                idx = d - NUMBER_MIN
                if idx < 0:
                    continue
                r = min(idx // cols, rows - 1)
                c = idx % cols
                line_counts[r] += 1
                col_counts[c] += 1
            lines_analysis.append(tuple(line_counts))
            cols_analysis.append(col_counts)

        line_patterns = Counter(lines_analysis)
        most_common_pattern = [list(p) for p, _ in line_patterns.most_common(3)]
        per_line_details = []
        for i in range(rows):
            start = NUMBER_MIN + i * cols
            line_numbers = [n for n in range(start, start + cols) if n <= NUMBER_MAX]
            if not line_numbers:
                continue
            line_freqs = {n: all_nums_freq.get(n, 0) for n in line_numbers}
            sorted_nums = sorted(line_freqs.items(), key=lambda x: x[1], reverse=True)
            per_line_details.append({
                "line": i + 1,
                "most_frequent": sorted_nums[0][0],
                "least_frequent": sorted_nums[-1][0],
                "avg_count": (sum(x[i] for x in lines_analysis) / len(lines_analysis)) if lines_analysis else 0,
                "top_subsets": [],
            })
        return {
            "lines_avg": [d["avg_count"] for d in per_line_details],
            "cols_avg": [sum(x) / len(x) for x in zip(*cols_analysis)] if cols_analysis else [0] * cols,
            "latest_lines": list(lines_analysis[-1]) if lines_analysis else [0] * rows,
            "latest_cols": cols_analysis[-1] if cols_analysis else [0] * cols,
            "per_line_details": per_line_details,
            "most_common_patterns": most_common_pattern,
        }

    @staticmethod
    def analyze_composition(results):
        counts_parity = Counter()
        counts_range = Counter()
        stats = []
        mid = (NUMBER_MIN + NUMBER_MAX) // 2
        primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97}
        for res in results:
            dezenas = dezenas_of(res)
            pares = len([d for d in dezenas if d % 2 == 0])
            impares = len(dezenas) - pares
            baixos = len([d for d in dezenas if d <= mid])
            altos = len(dezenas) - baixos
            primos = len([d for d in dezenas if d in primes])
            soma = sum(dezenas)
            counts_parity.update([f"{pares}P / {impares}I"])
            counts_range.update([f"{baixos}B / {altos}A"])
            stats.append({"pares": pares, "impares": impares, "baixos": baixos, "altos": altos, "primos": primos, "soma": soma})
        prime_counts = Counter([s["primos"] for s in stats])
        sum_ranges = Counter([f"{(s['soma'] // 10) * 10}-{(s['soma'] // 10) * 10 + 9}" for s in stats])
        return {
            "all_stats": stats,
            "most_common_parity": counts_parity.most_common(1)[0] if counts_parity else None,
            "most_common_range": counts_range.most_common(1)[0] if counts_range else None,
            "most_common_primes": prime_counts.most_common(3) if prime_counts else [],
            "most_common_sum_range": sum_ranges.most_common(3) if sum_ranges else [],
            "parity_distribution": counts_parity.most_common(5),
            "range_distribution": counts_range.most_common(5),
        }

    @staticmethod
    def analyze_repetition(results):
        if len(results) < 2:
            return []
        repetitions = []
        for i in range(1, len(results)):
            prev = set(dezenas_of(results[i - 1]))
            curr = set(dezenas_of(results[i]))
            repetitions.append(len(curr.intersection(prev)))
        return repetitions

    @staticmethod
    def analyze_patterns(results):
        seq_stats = []
        all_ending_reps = []
        for res in results:
            dezenas = sorted(dezenas_of(res))
            max_seq = 1
            current_seq = 1
            for j in range(len(dezenas) - 1):
                if dezenas[j + 1] == dezenas[j] + 1:
                    current_seq += 1
                else:
                    max_seq = max(max_seq, current_seq)
                    current_seq = 1
            max_seq = max(max_seq, current_seq)
            seq_stats.append(max_seq)
            ends = [d % 10 for d in dezenas]
            end_counts = Counter(ends)
            all_ending_reps.append(max(end_counts.values()) if end_counts else 0)
        return {
            "max_sequences": seq_stats,
            "avg_max_sequence": sum(seq_stats) / len(seq_stats) if seq_stats else 0,
            "common_ending_patterns": Counter(all_ending_reps).most_common(3),
        }

    @staticmethod
    def analyze_temporal(results):
        if not results:
            return {}
        atrasos = {i: 0 for i in range(NUMBER_MIN, NUMBER_MAX + 1)}
        for num in range(NUMBER_MIN, NUMBER_MAX + 1):
            count = 0
            found = False
            for res in reversed(results):
                if num in dezenas_of(res):
                    found = True
                    break
                count += 1
            atrasos[num] = count if found else len(results)
        return atrasos
