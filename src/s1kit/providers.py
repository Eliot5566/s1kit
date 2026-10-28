"""Providers: anything with a name and decide(state, questions) -> answers."""

import json
import math
import os
import re
import socket
import time
import urllib.error
import urllib.request

from . import __version__

ENDPOINT = "/v1/systemone"


class ProviderError(RuntimeError):
    """A provider could not answer: unreachable, an HTTP error, or a reply that is not JSON."""


RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_WAIT = 30


class HttpProvider:
    """Any server that speaks /v1/systemone: Jev, Laya serve, kev, llama.cpp, Ollama.

    Retries rate limits (429), server errors (5xx) and dropped connections with
    exponential backoff, honouring Retry-After. A refused connection or a
    timeout fails at once, so a server that is down does not stall the run.
    """

    def __init__(self, name, base_url, model=None, api_key_env=None, timeout=30, retries=2, backoff=0.5):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def _wait(self, attempt, retry_after=None):
        if retry_after and retry_after.strip().isdigit():
            return min(int(retry_after), MAX_WAIT)
        return min(self.backoff * 2 ** attempt, MAX_WAIT)

    def decide(self, state, questions):
        url = self.base_url + ENDPOINT
        payload = {"state": state, "questions": questions}
        if self.model:
            payload["model"] = self.model
        headers = {"Content-Type": "application/json", "User-Agent": f"s1kit/{__version__}"}
        key = os.environ.get(self.api_key_env) if self.api_key_env else None
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = json.dumps(payload).encode()
        attempts = max(self.retries, 0) + 1
        for attempt in range(attempts):
            last = attempt == attempts - 1
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code in RETRY_STATUS and not last:
                    time.sleep(self._wait(attempt, exc.headers.get("Retry-After")))
                    continue
                detail = exc.read(500).decode("utf-8", "replace").strip()
                hint = f" (is {self.api_key_env} set?)" if exc.code == 401 and self.api_key_env and not key else ""
                raise ProviderError(f"HTTP {exc.code} from {url}{hint}" + (f": {detail}" if detail else "")) from None
            except OSError as exc:  # URLError, timeouts, dropped connections
                reason = getattr(exc, "reason", exc)
                if isinstance(reason, (socket.timeout, TimeoutError)):
                    raise ProviderError(f"no answer from {url} within {self.timeout}s "
                                        "(raise timeout: in the suite for slow models)") from None
                if isinstance(reason, ConnectionResetError) and not last:
                    time.sleep(self._wait(attempt))
                    continue
                raise ProviderError(f"cannot reach {url} ({reason}); is the server running?") from None
        try:
            data = json.loads(raw)
        except ValueError:
            raise ProviderError(f"{url} did not answer JSON: {raw[:200]!r}") from None
        if not isinstance(data, dict):
            raise ProviderError(f"{url} answered {type(data).__name__}, expected an object with answers")
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
            cfg["name"], cfg["base_url"], cfg.get("model"), cfg.get("api_key_env"),
            timeout=cfg.get("timeout", 30), retries=cfg.get("retries", 2),
        )
    raise ValueError(f"unknown provider type: {kind!r}")
