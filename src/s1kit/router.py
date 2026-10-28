"""Ask the cheapest provider first; escalate while confidence is below the calibrated cutoff."""

from dataclasses import dataclass

from .protocol import normalize


@dataclass
class RouterResult:
    answers: dict
    provider: str
    escalations: int


class Router:
    def __init__(self, providers, thresholds):
        """providers: cheapest first. thresholds: calibrate() output or its "providers" map."""
        self.providers = list(providers)
        self.cutoffs = thresholds.get("providers", thresholds)

    def _confident(self, provider, questions, answers):
        cutoffs = self.cutoffs.get(provider.name, {})
        for qid, q in questions.items():
            cutoff = cutoffs.get(qid)
            if cutoff is None or qid not in answers:
                return False
            if normalize(q, answers[qid])[1] < cutoff["threshold"]:
                return False
        return True

    def decide(self, state, questions):
        last_error = None
        for i, provider in enumerate(self.providers):
            is_last = i == len(self.providers) - 1
            try:
                answers = provider.decide(state, questions)
            except Exception as exc:
                last_error = exc
                continue
            if is_last or self._confident(provider, questions, answers):
                return RouterResult(answers, provider.name, i)
        raise RuntimeError("every provider failed") from last_error
