"""Providers: anything with a name and decide(state, questions) -> answers."""

import json
import math
import os
import re
import urllib.request

ENDPOINT = "/v1/systemone"


class HttpProvider:
    """Any server that speaks /v1/systemone: Jev, Laya serve, kev, llama.cpp, Ollama."""

    def __init__(self, name, base_url, model, api_key_env=None, timeout=30):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout

    def decide(self, state, questions):
        body = json.dumps({"model": self.model, "state": state, "questions": questions}).encode()
        headers = {"Content-Type": "application/json", "User-Agent": "s1kit"}
        key = os.environ.get(self.api_key_env) if self.api_key_env else None
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(self.base_url + ENDPOINT, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        return data.get("answers", data)


_WORD = re.compile(r"\w+")


def _words(text):
    return {w.lower() for w in _WORD.findall(text) if len(w) > 2}


def _softmax(scores):
    peak = max(scores.values())
    exps = {k: math.exp(v - peak) for k, v in scores.items()}
    total = sum(exps.values())
    return {k: v / total for k, v in exps.items()}


class KeywordProvider:
    """Offline baseline: scores options by word overlap with the state.

    Needs no network or API key. Useful for trying s1kit and as the bar a real
    model has to beat.
    """

    def __init__(self, name="keyword"):
        self.name = name

    def decide(self, state, questions):
        text = _words(state if isinstance(state, str) else json.dumps(state))
        answers = {}
        for qid, q in questions.items():
            criteria = q.get("criteria") or {}
            if q["type"] == "choice":
                options = criteria if isinstance(criteria, dict) else {o: "" for o in criteria}
                probs = _softmax({k: len(text & _words(f"{k} {v}")) for k, v in options.items()})
                best = max(probs, key=probs.get)
                answers[qid] = {"choice": best, "confidence": probs[best], "probabilities": probs}
            elif q["type"] == "score":
                probs = _softmax({str(i): len(text & _words(str(level))) for i, level in enumerate(criteria)})
                best = max(probs, key=probs.get)
                answers[qid] = {
                    "score": sum(int(i) * p for i, p in probs.items()),
                    "legend": {str(i): str(level) for i, level in enumerate(criteria)},
                    "probabilities": probs,
                    "confidence": probs[best],
                }
            elif q["type"] == "noul":
                hits = len(text & _words(q.get("instructions", "")))
                answers[qid] = {"noul": (hits + 0.5) / (hits + 1.5)}
            else:
                raise ValueError(f"unknown question type: {q['type']!r}")
        return answers


def from_config(cfg):
    kind = cfg.get("type", "http")
    if kind == "keyword":
        return KeywordProvider(cfg.get("name", "keyword"))
    if kind == "http":
        return HttpProvider(
            cfg["name"], cfg["base_url"], cfg["model"], cfg.get("api_key_env"), cfg.get("timeout", 30)
        )
    raise ValueError(f"unknown provider type: {kind!r}")
