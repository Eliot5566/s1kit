from s1kit.protocol import expected_label, normalize

CHOICE = {"type": "choice", "criteria": {"a": "", "b": ""}}
SCORE = {"type": "score", "criteria": ["Calm", "Frustrated", "Very angry"]}
NOUL = {"type": "noul"}


def test_choice_uses_reported_choice_and_confidence():
    answer = {"choice": "b", "confidence": 0.7, "probabilities": {"a": 0.3, "b": 0.7}}
    assert normalize(CHOICE, answer) == ("b", 0.7)


def test_choice_falls_back_to_most_likely_option():
    assert normalize(CHOICE, {"probabilities": {"a": 0.2, "b": 0.8}}) == ("b", 0.8)


def test_score_rounds_mean_to_level_label():
    answer = {"score": 1.6, "confidence": 0.5, "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7}}
    assert normalize(SCORE, answer) == ("Very angry", 0.5)


def test_noul_confidence_is_distance_from_coin_flip():
    assert normalize(NOUL, {"noul": 0.2}) == (False, 0.8)


def test_expected_values_are_normalized():
    assert expected_label(SCORE, 1) == "Frustrated"
    assert expected_label(SCORE, "Calm") == "Calm"
    assert expected_label(NOUL, "yes") is True
    assert expected_label(CHOICE, "a") == "a"
