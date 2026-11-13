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


@pytest.mark.parametrize("confidence", [0.80004, 0.80006])
def test_threshold_preserves_the_acceptance_boundary(confidence):
    records = [rec(confidence, True), rec(0.8, False)]
    cut = threshold_for(records, 0.9)
    accepted = [r for r in records if r.confidence >= cut["threshold"]]
    assert len(accepted) == 1
    assert sum(r.correct for r in accepted) / len(accepted) >= 0.9
    assert len(accepted) / len(records) == cut["coverage"]


def test_calibrated_threshold_survives_yaml_and_routes_boundary_cases():
    import yaml

    records = [rec(0.80004, True, "cheap"), rec(0.8, False, "cheap")]
    thresholds = yaml.safe_load(yaml.safe_dump(calibrate(records, 0.9)))
    for confidence, expected_provider in [(0.8, "big"), (0.80004, "cheap")]:
        result = Router([Fake("cheap", confidence), Fake("big", 0.99)], thresholds).decide("s", {"q": CHOICE})
        assert result.provider == expected_provider


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
