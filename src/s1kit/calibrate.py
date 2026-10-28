"""Pick the confidence cutoff per provider and question that hits a target precision."""

from collections import defaultdict


def threshold_for(records, target):
    """Lowest cutoff whose accepted answers are at least `target` precise.

    Returns None when no cutoff gets there: that question should always escalate.
    """
    scored = sorted(((r.confidence, r.correct) for r in records if r.error is None), reverse=True)
    best = None
    correct = 0
    for i, (confidence, ok) in enumerate(scored, 1):
        correct += ok
        if i < len(scored) and scored[i][0] == confidence:
            continue  # only cut between distinct confidence values
        precision = correct / i
        if precision >= target:
            best = {
                "threshold": round(confidence, 4),
                "precision": round(precision, 4),
                "coverage": round(i / len(scored), 4),
                "n": len(scored),
            }
    return best


def calibrate(records, target):
    groups = defaultdict(list)
    for r in records:
        groups[(r.provider, r.question)].append(r)
    providers = defaultdict(dict)
    for (provider, question), group in sorted(groups.items()):
        providers[provider][question] = threshold_for(group, target)
    return {"target_precision": target, "providers": dict(providers)}
