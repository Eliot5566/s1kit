"""Run every case against every provider and record what each one decided."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

from .protocol import expected_label, normalize


@dataclass
class Record:
    provider: str
    case: str
    question: str
    expected: object
    label: object
    confidence: float
    correct: bool
    latency_ms: float
    error: str = None


def _ask(provider, case, questions):
    asked = {qid: questions[qid] for qid in case.expect}
    start = time.perf_counter()
    try:
        answers, request_error = provider.decide(case.state, asked), None
    except Exception as exc:  # one failing case must not stop the run
        answers, request_error = {}, f"{type(exc).__name__}: {exc}"
    latency = (time.perf_counter() - start) * 1000
    records = []
    for qid, q in asked.items():
        want = expected_label(q, case.expect[qid])
        error = request_error
        if qid in answers:
            label, confidence = normalize(q, answers[qid])
        else:
            label, confidence = None, 0.0
            error = error or f"no answer for {qid!r}"
        records.append(Record(provider.name, case.id, qid, want, label, confidence,
                              label == want, round(latency, 2), error))
    return records


def run(suite, providers=None, concurrency=1):
    """Ask every provider about every case. Records come back in suite order
    whatever the concurrency, so two runs of the same suite diff cleanly."""
    jobs = [(p, c) for p in (suite.providers if providers is None else providers) for c in suite.cases]
    if concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            batches = list(pool.map(lambda job: _ask(*job, suite.questions), jobs))
    else:
        batches = [_ask(p, c, suite.questions) for p, c in jobs]
    return [r for batch in batches for r in batch]


def save(records, path):
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [Record(**json.loads(line)) for line in fh if line.strip()]
