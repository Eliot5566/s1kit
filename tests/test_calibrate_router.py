import pytest

from s1kit.calibrate import calibrate, threshold_for
from s1kit.router import Router
from s1kit.runner import Record

CHOICE = {"type": "choice", "criteria": {"x": "", "y": ""}}


def rec(confidence, correct, provider="p", question="q"):
    return Record(provider, "c", question, "x", "x" if correct else "y", confidence, correct, 1.0)


def test_threshold_is_lowest_cutoff_reaching_target():
    records = [rec(0.95, True), rec(0.9, True), rec(0.8, True), rec(0.7, False), rec(0.6, False)]
    cut = threshold_for(records, 0.9)
    assert cut == {"threshold": 0.8, "precision": 1.0, "coverage": 0.6, "n": 5}


def test_threshold_none_when_target_unreachable():
    assert threshold_for([rec(0.9, False), rec(0.8, True)], 0.99) is None


def test_ties_are_not_split():
    records = [rec(0.9, True), rec(0.9, False), rec(0.5, False)]
    assert threshold_for(records, 0.6) is None


def test_errors_are_ignored():
    bad = Record("p", "c", "q", "x", None, 0.0, False, 1.0, error="timeout")
    assert threshold_for([rec(0.9, True), bad], 0.9)["n"] == 1


def test_calibrate_groups_by_provider_and_question():
    result = calibrate([rec(0.9, True, "a", "q1"), rec(0.9, False, "b", "q1")], 0.9)
    assert result["providers"]["a"]["q1"]["threshold"] == 0.9
    assert result["providers"]["b"]["q1"] is None


class Fake:
    def __init__(self, name, confidence=None, fail=False):
        self.name, self.confidence, self.fail, self.calls = name, confidence, fail, 0

    def decide(self, state, questions):
        self.calls += 1
        if self.fail:
            raise TimeoutError("down")
        return {"q": {"choice": "x", "confidence": self.confidence}}


THRESHOLDS = {"providers": {"cheap": {"q": {"threshold": 0.8}}, "mid": {"q": {"threshold": 0.8}}}}


def test_router_stops_at_first_confident_provider():
    cheap, big = Fake("cheap", 0.9), Fake("big", 0.99)
    result = Router([cheap, big], THRESHOLDS).decide("s", {"q": CHOICE})
    assert (result.provider, result.escalations, big.calls) == ("cheap", 0, 0)


def test_router_escalates_on_low_confidence_and_failure():
    providers = [Fake("cheap", 0.5), Fake("mid", fail=True), Fake("big", 0.6)]
    result = Router(providers, THRESHOLDS).decide("s", {"q": CHOICE})
    assert (result.provider, result.escalations) == ("big", 2)


def test_router_escalates_when_question_has_no_cutoff():
    result = Router([Fake("other", 0.99), Fake("big", 0.5)], THRESHOLDS).decide("s", {"q": CHOICE})
    assert result.provider == "big"


def test_router_raises_when_everyone_fails():
    with pytest.raises(RuntimeError):
        Router([Fake("a", fail=True)], {}).decide("s", {"q": CHOICE})
