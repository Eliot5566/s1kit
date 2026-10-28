"""Side-by-side summary of a run: accuracy and latency per provider and question."""

from collections import defaultdict


def _p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))] if ordered else 0.0


def summarize(records):
    groups = defaultdict(list)
    for r in records:
        groups[(r.provider, r.question)].append(r)
    rows = []
    for (provider, question), group in sorted(groups.items()):
        latencies = [r.latency_ms for r in group]
        rows.append({
            "provider": provider,
            "question": question,
            "n": len(group),
            "accuracy": sum(r.correct for r in group) / len(group),
            "errors": sum(r.error is not None for r in group),
            "p50_ms": sorted(latencies)[len(latencies) // 2],
            "p95_ms": _p95(latencies),
        })
    return rows


def render(rows):
    header = f"{'provider':<16} {'question':<16} {'n':>4} {'accuracy':>9} {'errors':>6} {'p50 ms':>8} {'p95 ms':>8}"
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r['provider']:<16} {r['question']:<16} {r['n']:>4} {r['accuracy']:>9.1%} "
            f"{r['errors']:>6} {r['p50_ms']:>8.1f} {r['p95_ms']:>8.1f}"
        )
    return "\n".join(lines)


def overall(records):
    """One line per provider, most accurate first: the headline of a comparison."""
    totals = defaultdict(lambda: [0, 0, 0])
    for r in records:
        t = totals[r.provider]
        t[0] += r.correct
        t[1] += 1
        t[2] += r.error is not None
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1][0] / kv[1][1], kv[0]))
    return "\n".join(
        f"{provider}: {correct}/{n} correct ({correct / n:.1%})" + (f", {errors} errors" if errors else "")
        for provider, (correct, n, errors) in ranked
    )
