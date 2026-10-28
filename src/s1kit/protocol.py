"""Turn raw /v1/systemone answers into a comparable (label, confidence) pair."""


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "y", "1"}


def _score_label(question, index):
    levels = question.get("criteria")
    if isinstance(levels, list) and 0 <= index < len(levels):
        return str(levels[index])
    return str(index)


def normalize(question, answer):
    """Return (label, confidence) for one answer.

    choice -> the chosen option; score -> the level nearest the mean score;
    noul -> True/False with confidence max(p, 1 - p).
    """
    qtype = question["type"]
    probs = answer.get("probabilities") or {}
    if qtype == "choice":
        label = answer.get("choice")
        if label is None and probs:
            label = max(probs, key=probs.get)
        confidence = answer.get("confidence", probs.get(label, 0.0))
        return str(label), float(confidence)
    if qtype == "score":
        index = int(round(float(answer["score"])))
        confidence = answer.get("confidence", max(probs.values(), default=0.0))
        return _score_label(question, index), float(confidence)
    if qtype == "noul":
        p = float(answer["noul"])
        return p >= 0.5, max(p, 1.0 - p)
    raise ValueError(f"unknown question type: {qtype!r}")


def expected_label(question, expected):
    """Bring a test case's expected value into the same form normalize() returns."""
    qtype = question["type"]
    if qtype == "noul":
        return _truthy(expected)
    if qtype == "score" and isinstance(expected, int) and not isinstance(expected, bool):
        return _score_label(question, expected)
    return str(expected)
