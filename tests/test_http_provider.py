"""HttpProvider against a local server that answers like laya-serve and Jev."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from s1kit import runner, suite
from s1kit.protocol import normalize
from s1kit.providers import HttpProvider, ProviderError

QUESTIONS = {
    "team": {"type": "choice", "instructions": "Which team?",
             "criteria": {"billing": "charges", "tech": "bugs"}},
    "mood": {"type": "score", "instructions": "How upset?", "criteria": ["calm", "annoyed", "furious"]},
    "urgent": {"type": "noul", "instructions": "Is it urgent?"},
}

# What laya-serve sends back under LAYA_JEV_STRICT, plus the x_jev_confidence it adds by default.
ANSWERS = {
    "team": {"type": "choice", "choice": "billing", "confidence": 0.91,
             "probabilities": {"billing": 0.91, "tech": 0.09}, "x_jev_confidence": 0.88},
    "mood": {"type": "score", "score": 1.2, "confidence": 0.7,
             "probabilities": {"0": 0.1, "1": 0.6, "2": 0.3},
             "legend": {"0": "calm", "1": "annoyed", "2": "furious"}},
    "urgent": {"type": "noul", "noul": 0.83},
}


class FakeServer:
    """Answers POST /v1/systemone. `script` is a list of (status, headers, body) to send first."""

    def __init__(self):
        self.requests = []
        self.script = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                server.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
                if server.script:
                    status, headers, payload = server.script.pop(0)
                else:
                    asked = body["questions"]
                    status, headers = 200, {}
                    payload = {"model": body.get("model", "laya"),
                               "answers": {q: ANSWERS[q] for q in asked},
                               "usage": {"input_tokens": 12, "output_tokens": 3}}
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = FakeServer()
    yield s
    s.close()


def test_request_matches_the_wire_protocol(server, monkeypatch):
    monkeypatch.setenv("LAYA_API_KEY", "sk-test")
    provider = HttpProvider("laya", server.url + "/", "laya", api_key_env="LAYA_API_KEY")
    answers = provider.decide({"body": "charged twice"}, QUESTIONS)

    sent = server.requests[0]
    assert sent["path"] == "/v1/systemone"
    assert sent["headers"]["Authorization"] == "Bearer sk-test"
    assert sent["headers"]["Content-Type"] == "application/json"
    assert sent["body"] == {"model": "laya", "state": {"body": "charged twice"}, "questions": QUESTIONS}
    assert normalize(QUESTIONS["team"], answers["team"]) == ("billing", 0.91)
    assert normalize(QUESTIONS["mood"], answers["mood"]) == ("annoyed", 0.7)
    assert normalize(QUESTIONS["urgent"], answers["urgent"]) == (True, 0.83)


def test_model_is_optional(server):
    HttpProvider("laya", server.url).decide("hi", {"urgent": QUESTIONS["urgent"]})
    assert "model" not in server.requests[0]["body"]


def test_suite_runs_end_to_end_over_http(server, tmp_path):
    path = tmp_path / "suite.yaml"
    path.write_text(json.dumps({
        "providers": [{"name": "laya", "base_url": server.url, "model": "laya"}],
        "questions": QUESTIONS,
        "cases": [{"state": "charged twice", "expect": {"team": "billing", "mood": 1, "urgent": True}},
                  {"state": "app crashes", "expect": {"team": "tech"}}],
    }))
    records = runner.run(suite.load(path), concurrency=2)
    assert [(r.case, r.question, r.correct) for r in records] == [
        ("1", "team", True), ("1", "mood", True), ("1", "urgent", True), ("2", "team", False)]
    assert all(r.error is None for r in records)


def test_retries_rate_limits_and_server_errors(server):
    server.script = [(429, {"Retry-After": "0"}, {"detail": "slow down"}),
                     (503, {}, {"detail": "loading"})]
    answers = HttpProvider("laya", server.url, retries=2, backoff=0).decide("hi", {"urgent": QUESTIONS["urgent"]})
    assert answers["urgent"]["noul"] == 0.83
    assert len(server.requests) == 3


def test_gives_up_after_retries(server):
    server.script = [(503, {}, {"detail": "loading"})] * 2
    with pytest.raises(ProviderError, match=r"HTTP 503 .*loading"):
        HttpProvider("laya", server.url, retries=1, backoff=0).decide("hi", {"urgent": QUESTIONS["urgent"]})
    assert len(server.requests) == 2


def test_auth_errors_are_not_retried_and_explain_themselves(server, monkeypatch):
    monkeypatch.delenv("LAYA_API_KEY", raising=False)
    server.script = [(401, {}, {"detail": "invalid or missing bearer token"})]
    provider = HttpProvider("laya", server.url, api_key_env="LAYA_API_KEY", backoff=0)
    with pytest.raises(ProviderError, match=r"HTTP 401 .*is LAYA_API_KEY set\?.*invalid or missing bearer token"):
        provider.decide("hi", {"urgent": QUESTIONS["urgent"]})
    assert len(server.requests) == 1


def test_non_json_reply(server):
    server.script = [(200, {}, b"<html>proxy login</html>")]
    with pytest.raises(ProviderError, match="did not answer JSON"):
        HttpProvider("laya", server.url).decide("hi", {"urgent": QUESTIONS["urgent"]})


def test_server_down_fails_fast_with_a_hint():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.server_close()  # nothing listens on this port now
    with pytest.raises(ProviderError, match="cannot reach .*is the server running"):
        HttpProvider("laya", url, backoff=10).decide("hi", {"urgent": QUESTIONS["urgent"]})
